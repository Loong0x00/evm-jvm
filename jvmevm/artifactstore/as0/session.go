// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.
//
// This program is free software: you can redistribute it and/or modify it under
// the terms of the GNU Lesser General Public License as published by the Free
// Software Foundation, either version 3 of the License, or (at your option) any
// later version.

package as0

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math/big"
	"os"
	"path/filepath"
	"strings"
	"sync"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/rawdb"
	"github.com/ethereum/go-ethereum/core/state"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/core/vm"
	evmruntime "github.com/ethereum/go-ethereum/core/vm/runtime"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/ethdb"
	"github.com/ethereum/go-ethereum/ethdb/leveldb"
	"github.com/ethereum/go-ethereum/params"
	"github.com/ethereum/go-ethereum/triedb"
)

const (
	storeFormat     = uint32(1)
	storeMarker     = "JVMEVM-MC-AS0-DISK-STORE-1\n"
	markerName      = "STORE-FORMAT"
	manifestName    = "durable-head.json"
	stateDirectory  = "state"
	contextID       = "all-dev-chain:block=1,time=1,coinbase=0000000000000000000000000000000000000000,value=0"
	manifestMaxSize = int64(4096)
)

type manifest struct {
	Format          uint32         `json:"format"`
	Context         string         `json:"context"`
	Owner           common.Address `json:"owner"`
	Controller      common.Address `json:"controller"`
	DeclaredLength  uint32         `json:"declaredLength"`
	RuntimeCodeHash common.Hash    `json:"runtimeCodeHash"`
	StateRoot       common.Hash    `json:"stateRoot"`
}

// Creation records the ordinary EVM CREATE which constructed a fresh store.
// Performed is false after reopen because no CREATE was performed then.
type Creation struct {
	Performed       bool
	Controller      common.Address
	GasUsed         uint64
	RuntimeCodeHash common.Hash
	StateRoot       common.Hash
}

// Operation is the durable result of Append or Seal. On EVM failure only
// GasUsed and RevertData are set. On publication failure only GasUsed is set.
type Operation struct {
	GasUsed    uint64
	StateRoot  common.Hash
	Logs       []*types.Log
	RevertData []byte
}

// Page is controller-issued metadata returned by the EVM page(index) getter.
type Page struct {
	Address    common.Address
	CodeHash   common.Hash
	Commitment common.Hash
	GasUsed    uint64
}

// Read is opaque bytes returned by EVM EXTCODECOPY and that view call's gas.
type Read struct {
	Bytes   []byte
	GasUsed uint64
}

// Head is assembled exclusively from EVM getter results against a StateDB copy.
// GasUsed is the sum of the distinct getter calls and excludes prior mutations.
type Head struct {
	Owner             common.Address
	Controller        common.Address
	DeclaredLength    uint32
	Cursor            uint32
	Sealed            bool
	PageCount         uint32
	ChainCommitment   common.Hash
	ContentCommitment common.Hash
	PageSize          uint32
	MaxPages          uint32
	MaxLength         uint32
	RuntimeCodeHash   common.Hash
	StateRoot         common.Hash
	GasUsed           uint64
}

type faultPoint uint8

const (
	faultAfterTrie faultPoint = iota + 1
	faultBeforeManifest
	faultAfterManifestRename
)

type durableDB interface {
	ethdb.Database
	SyncKeyValue() error
}

// Session serializes one controller. Its StateDB is the sole artifact authority;
// no host page map or host-installed page code exists.
type Session struct {
	mu sync.Mutex

	owner          common.Address
	declaredLength uint32
	controller     common.Address
	contractABI    abi.ABI
	initCode       []byte
	runtimeCode    []byte
	runtimeHash    common.Hash
	creation       Creation

	directory string
	disk      durableDB
	trieDB    *triedb.Database
	stateDB   *state.StateDB
	stateRoot common.Hash

	closed    bool
	uncertain error

	// Package tests may inject transport failures, never EVM/content decisions.
	testFault func(faultPoint) error
}

// NewMemory executes the pinned constructor with ordinary runtime.Create in an
// ephemeral StateDB. It never uses SetCode for the controller or child pages.
func NewMemory(owner common.Address, length uint32) (*Session, error) {
	if err := validateCreationInputs(owner, length); err != nil {
		return nil, err
	}
	initCode, runtimeCode, contractABI, err := loadSessionArtifacts()
	if err != nil {
		return nil, err
	}
	disk := rawdb.NewMemoryDatabase()
	session, err := newSession(owner, length, "", disk, initCode, runtimeCode, contractABI)
	if err != nil {
		disk.Close()
		return nil, err
	}
	if err := session.createController(); err != nil {
		session.Close()
		return nil, err
	}
	return session, nil
}

// Open creates a disk store in an empty directory or reopens the exact published
// manifest root. Metadata is validated before LevelDB is opened. Reopen never
// deploys the controller and never recreates or installs a page.
func Open(directory string, owner common.Address, length uint32) (*Session, error) {
	if err := validateCreationInputs(owner, length); err != nil {
		return nil, err
	}
	if directory == "" {
		return nil, errors.New("as0: directory must not be empty")
	}
	initCode, runtimeCode, contractABI, err := loadSessionArtifacts()
	if err != nil {
		return nil, err
	}
	directory, err = filepath.Abs(directory)
	if err != nil {
		return nil, fmt.Errorf("as0: resolve store directory: %w", err)
	}
	// The explicitly requested root may itself be an alias. Fixed entries below
	// it are checked with Lstat and are never followed when their shape is tested.
	if resolved, resolveErr := filepath.EvalSymlinks(directory); resolveErr == nil {
		directory = resolved
	} else if !errors.Is(resolveErr, os.ErrNotExist) {
		return nil, fmt.Errorf("as0: resolve store root: %w", resolveErr)
	}
	fresh, err := prepareDirectory(directory)
	if err != nil {
		return nil, err
	}
	runtimeHash := crypto.Keccak256Hash(runtimeCode)
	var published manifest
	if !fresh {
		published, err = diskMetadata(directory, owner, length, runtimeHash)
		if err != nil {
			return nil, err
		}
	}
	kv, err := leveldb.New(filepath.Join(directory, stateDirectory), 16, 16, "jvmevm/as0", false)
	if err != nil {
		return nil, fmt.Errorf("as0: open state database: %w", err)
	}
	disk := rawdb.NewDatabase(kv)
	session, err := newSession(owner, length, directory, disk, initCode, runtimeCode, contractABI)
	if err != nil {
		disk.Close()
		return nil, err
	}
	if fresh {
		if err := session.initializeDiskStore(); err != nil {
			session.Close()
			return nil, err
		}
		return session, nil
	}
	if err := session.reopen(published); err != nil {
		session.Close()
		return nil, err
	}
	return session, nil
}

func validateCreationInputs(owner common.Address, length uint32) error {
	if length == 0 || length > MaxLength {
		return errors.New("as0: declared length must be in 1..33554432")
	}
	if owner == (common.Address{}) {
		return errors.New("as0: owner must be nonzero")
	}
	return nil
}

func loadSessionArtifacts() ([]byte, []byte, abi.ABI, error) {
	initCode, err := InitCode()
	if err != nil {
		return nil, nil, abi.ABI{}, err
	}
	runtimeCode, err := Runtime()
	if err != nil {
		return nil, nil, abi.ABI{}, err
	}
	contractABI, err := ABI()
	if err != nil {
		return nil, nil, abi.ABI{}, err
	}
	return initCode, runtimeCode, contractABI, nil
}

func newSession(owner common.Address, length uint32, directory string, disk durableDB, initCode, runtimeCode []byte, contractABI abi.ABI) (*Session, error) {
	trieDB := triedb.NewDatabase(disk, triedb.HashDefaults)
	stateDB, err := state.New(types.EmptyRootHash, state.NewDatabase(trieDB, nil))
	if err != nil {
		trieDB.Close()
		return nil, fmt.Errorf("as0: create empty StateDB: %w", err)
	}
	return &Session{
		owner: owner, declaredLength: length, contractABI: contractABI,
		initCode: append([]byte(nil), initCode...), runtimeCode: append([]byte(nil), runtimeCode...), runtimeHash: crypto.Keccak256Hash(runtimeCode),
		directory: directory, disk: disk, trieDB: trieDB, stateDB: stateDB, stateRoot: types.EmptyRootHash,
	}, nil
}

func (s *Session) createController() error {
	args, err := s.contractABI.Pack("", s.declaredLength)
	if err != nil {
		return fmt.Errorf("as0: ABI-pack constructor: %w", err)
	}
	input := append(append([]byte(nil), s.initCode...), args...)
	const gas = uint64(100_000_000)
	output, address, left, createErr := evmruntime.Create(input, s.runtimeConfig(s.stateDB, gas))
	used := gas - left
	if createErr != nil {
		return fmt.Errorf("as0: EVM constructor failed after %d gas: %w (output=0x%x)", used, createErr, output)
	}
	if !bytes.Equal(output, s.runtimeCode) || !bytes.Equal(s.stateDB.GetCode(address), s.runtimeCode) || s.stateDB.GetCodeHash(address) != s.runtimeHash {
		return errors.New("as0: constructor returned or installed code differing from pinned runtime")
	}
	s.controller = address
	root, err := s.commitTrie()
	if err != nil {
		return fmt.Errorf("as0: commit constructed controller: %w", err)
	}
	if err := s.reload(root); err != nil {
		return fmt.Errorf("as0: reload constructed controller: %w", err)
	}
	s.creation = Creation{Performed: true, Controller: address, GasUsed: used, RuntimeCodeHash: s.runtimeHash, StateRoot: root}
	return nil
}

func (s *Session) initializeDiskStore() error {
	markerPath := filepath.Join(s.directory, markerName)
	if err := writeNewRegular(markerPath, []byte(storeMarker), 0o600); err != nil {
		return fmt.Errorf("as0: write store marker: %w", err)
	}
	if err := syncDirectory(s.directory); err != nil {
		return fmt.Errorf("as0: sync initial store layout: %w", err)
	}
	if err := s.createController(); err != nil {
		return err
	}
	if _, err := s.writeManifest(s.makeManifest(s.stateRoot)); err != nil {
		return fmt.Errorf("as0: publish initial manifest: %w", err)
	}
	return nil
}

func (s *Session) reopen(m manifest) error {
	if err := s.reload(m.StateRoot); err != nil {
		return fmt.Errorf("as0: load durable state root %s: %w", m.StateRoot, err)
	}
	s.controller = m.Controller
	if !bytes.Equal(s.stateDB.GetCode(s.controller), s.runtimeCode) || s.stateDB.GetCodeHash(s.controller) != s.runtimeHash {
		return errors.New("as0: committed controller code is missing or differs from pinned runtime")
	}
	head, err := s.headLocked(100_000_000)
	if err != nil {
		return fmt.Errorf("as0: verify reopened EVM getters: %w", err)
	}
	if head.Owner != s.owner || head.Controller != s.controller || head.DeclaredLength != s.declaredLength || head.RuntimeCodeHash != s.runtimeHash || head.StateRoot != m.StateRoot {
		return errors.New("as0: restored EVM getters differ from manifest identity")
	}
	// No CREATE was run while reopening. A zero gas value is therefore paired
	// with Performed=false rather than presented as deployment cost evidence.
	s.creation = Creation{Performed: false, Controller: s.controller, RuntimeCodeHash: s.runtimeHash, StateRoot: m.StateRoot}
	return nil
}

// Creation returns a copy of the fresh deployment record.
func (s *Session) Creation() (Creation, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if err := s.usable(); err != nil {
		return Creation{}, err
	}
	return s.creation, nil
}

// Append sends the exact expected cursor, opaque bytes, and transport assertion
// to the controller. A successful disk call publishes its root before returning.
func (s *Session) Append(expectedCursor uint32, raw []byte, expectedPageCommitment common.Hash, gas uint64) (Operation, error) {
	return s.mutate("append", gas, expectedCursor, append([]byte(nil), raw...), expectedPageCommitment)
}

// Seal asks the EVM to seal at the asserted cursor and ordered chain.
func (s *Session) Seal(expectedCursor uint32, expectedChain common.Hash, gas uint64) (Operation, error) {
	return s.mutate("seal", gas, expectedCursor, expectedChain)
}

func (s *Session) mutate(method string, gas uint64, inputs ...interface{}) (Operation, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var result Operation
	if err := s.usable(); err != nil {
		return result, err
	}
	if err := validateGas(gas); err != nil {
		return result, err
	}
	callData, err := s.contractABI.Pack(method, inputs...)
	if err != nil {
		return result, fmt.Errorf("as0: ABI-pack %s: %w", method, err)
	}
	oldRoot := s.stateRoot
	snapshot := s.stateDB.Snapshot()
	logCount := len(s.stateDB.Logs())
	output, left, callErr := evmruntime.Call(s.controller, callData, s.runtimeConfig(s.stateDB, gas))
	result.GasUsed = gas - left
	if callErr != nil {
		s.stateDB.RevertToSnapshot(snapshot)
		result.RevertData = append([]byte(nil), output...)
		return result, fmt.Errorf("as0: EVM %s failed: %w (revert_data=0x%x)", method, callErr, output)
	}
	if len(output) != 0 {
		s.stateDB.RevertToSnapshot(snapshot)
		return Operation{GasUsed: result.GasUsed}, fmt.Errorf("as0: EVM %s returned unexpected bytes", method)
	}
	logs := s.stateDB.Logs()
	if logCount > len(logs) {
		s.stateDB.RevertToSnapshot(snapshot)
		return Operation{GasUsed: result.GasUsed}, errors.New("as0: StateDB log accounting moved backwards")
	}
	newLogs := copyLogs(logs[logCount:])
	if len(newLogs) != 1 || newLogs[0].Address != s.controller {
		s.stateDB.RevertToSnapshot(snapshot)
		return Operation{GasUsed: result.GasUsed}, fmt.Errorf("as0: EVM %s emitted unexpected success logs", method)
	}
	wantEvent := s.contractABI.Events["PageIssued"].ID
	if method == "seal" {
		wantEvent = s.contractABI.Events["Sealed"].ID
	}
	if len(newLogs[0].Topics) == 0 || newLogs[0].Topics[0] != wantEvent {
		s.stateDB.RevertToSnapshot(snapshot)
		return Operation{GasUsed: result.GasUsed}, fmt.Errorf("as0: EVM %s emitted wrong success event", method)
	}
	root, err := s.persist(oldRoot)
	if err != nil {
		// No success-shaped root, logs, or page metadata escapes a failed publish.
		return Operation{GasUsed: result.GasUsed}, err
	}
	result.StateRoot, result.Logs = root, newLogs
	return result, nil
}

// Read returns only bytes produced by the sealed controller's EVM read method.
func (s *Session) Read(offset, length uint32, gas uint64) (Read, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var result Read
	if err := s.usable(); err != nil {
		return result, err
	}
	output, used, err := s.viewCall(s.stateDB.Copy(), "read", gas, offset, length)
	result.GasUsed = used
	if err != nil {
		return result, err
	}
	values, err := s.contractABI.Unpack("read", output)
	if err != nil || len(values) != 1 {
		return Read{GasUsed: used}, fmt.Errorf("as0: decode EVM read: %w", err)
	}
	data, ok := values[0].([]byte)
	if !ok || len(data) > int(MaxRead) || len(data) != int(length) {
		return Read{GasUsed: used}, errors.New("as0: EVM read returned a noncanonical byte result")
	}
	result.Bytes = append([]byte(nil), data...)
	return result, nil
}

// Page asks the EVM for bounded issued-page metadata on a copied StateDB.
func (s *Session) Page(index uint64, gas uint64) (Page, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var result Page
	if err := s.usable(); err != nil {
		return result, err
	}
	output, used, err := s.viewCall(s.stateDB.Copy(), "page", gas, new(big.Int).SetUint64(index))
	result.GasUsed = used
	if err != nil {
		return result, err
	}
	values, err := s.contractABI.Unpack("page", output)
	if err != nil || len(values) != 3 {
		return Page{GasUsed: used}, fmt.Errorf("as0: decode EVM page: %w", err)
	}
	address, ok0 := values[0].(common.Address)
	codeHash, ok1 := values[1].([32]byte)
	commitment, ok2 := values[2].([32]byte)
	if !ok0 || !ok1 || !ok2 || address == (common.Address{}) || common.Hash(codeHash) == (common.Hash{}) || common.Hash(commitment) == (common.Hash{}) {
		return Page{GasUsed: used}, errors.New("as0: EVM page returned noncanonical metadata")
	}
	result.Address, result.CodeHash, result.Commitment = address, common.Hash(codeHash), common.Hash(commitment)
	return result, nil
}

// Head calls all lifecycle and limit getters in the EVM against copied state.
func (s *Session) Head(gas uint64) (Head, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if err := s.usable(); err != nil {
		return Head{}, err
	}
	return s.headLocked(gas)
}

func (s *Session) headLocked(gas uint64) (Head, error) {
	if err := validateGas(gas); err != nil {
		return Head{}, err
	}
	copyState := s.stateDB.Copy()
	var head Head
	get := func(name string) (interface{}, error) {
		output, used, err := s.viewCall(copyState, name, gas)
		head.GasUsed += used
		if err != nil {
			return nil, err
		}
		values, err := s.contractABI.Unpack(name, output)
		if err != nil || len(values) != 1 {
			return nil, fmt.Errorf("as0: decode EVM %s getter: %w", name, err)
		}
		return values[0], nil
	}
	var err error
	if value, e := get("owner"); e != nil {
		err = e
	} else {
		head.Owner = value.(common.Address)
	}
	if err == nil {
		if value, e := get("declaredLength"); e != nil {
			err = e
		} else {
			head.DeclaredLength = value.(uint32)
		}
	}
	if err == nil {
		if value, e := get("cursor"); e != nil {
			err = e
		} else {
			head.Cursor = value.(uint32)
		}
	}
	if err == nil {
		if value, e := get("isSealed"); e != nil {
			err = e
		} else {
			head.Sealed = value.(bool)
		}
	}
	if err == nil {
		if value, e := get("pageCount"); e != nil {
			err = e
		} else if n, ok := value.(*big.Int); !ok || !n.IsUint64() || n.Uint64() > uint64(MaxPages) {
			err = errors.New("as0: EVM pageCount is out of range")
		} else {
			head.PageCount = uint32(n.Uint64())
		}
	}
	if err == nil {
		if value, e := get("chainCommitment"); e != nil {
			err = e
		} else {
			head.ChainCommitment = common.Hash(value.([32]byte))
		}
	}
	if err == nil {
		if value, e := get("contentCommitment"); e != nil {
			err = e
		} else {
			head.ContentCommitment = common.Hash(value.([32]byte))
		}
	}
	if err == nil {
		if value, e := get("PAGE_SIZE"); e != nil {
			err = e
		} else {
			head.PageSize = value.(uint32)
		}
	}
	if err == nil {
		if value, e := get("MAX_PAGES"); e != nil {
			err = e
		} else {
			head.MaxPages = value.(uint32)
		}
	}
	if err == nil {
		if value, e := get("MAX_LENGTH"); e != nil {
			err = e
		} else {
			head.MaxLength = value.(uint32)
		}
	}
	if err != nil {
		return Head{GasUsed: head.GasUsed}, err
	}
	head.Controller, head.RuntimeCodeHash, head.StateRoot = s.controller, s.runtimeHash, s.stateRoot
	if head.Owner == (common.Address{}) || head.Owner != s.owner || head.DeclaredLength != s.declaredLength || head.Cursor > head.DeclaredLength || head.PageSize != PageSize || head.MaxPages != MaxPages || head.MaxLength != MaxLength || head.ChainCommitment == (common.Hash{}) || uint64(head.PageCount)*uint64(PageSize) < uint64(head.Cursor) || uint64(head.PageCount)*uint64(PageSize) > uint64(head.Cursor)+uint64(PageSize-1) {
		return Head{GasUsed: head.GasUsed}, errors.New("as0: EVM getters violate frozen identity, limits, or page/cursor shape")
	}
	if head.Cursor != head.DeclaredLength && head.Cursor%PageSize != 0 {
		return Head{GasUsed: head.GasUsed}, errors.New("as0: EVM returned a partial page before the declared end")
	}
	wantPages := (head.DeclaredLength + PageSize - 1) / PageSize
	if head.Sealed {
		if head.Cursor != head.DeclaredLength || head.PageCount != wantPages || head.ContentCommitment == (common.Hash{}) {
			return Head{GasUsed: head.GasUsed}, errors.New("as0: EVM returned a noncanonical sealed head")
		}
	} else if head.ContentCommitment != (common.Hash{}) {
		return Head{GasUsed: head.GasUsed}, errors.New("as0: EVM returned content commitment before seal")
	}
	return head, nil
}

func (s *Session) viewCall(stateCopy *state.StateDB, method string, gas uint64, inputs ...interface{}) ([]byte, uint64, error) {
	if err := validateGas(gas); err != nil {
		return nil, 0, err
	}
	callData, err := s.contractABI.Pack(method, inputs...)
	if err != nil {
		return nil, 0, fmt.Errorf("as0: ABI-pack %s: %w", method, err)
	}
	output, left, callErr := evmruntime.Call(s.controller, callData, s.runtimeConfig(stateCopy, gas))
	used := gas - left
	if callErr != nil {
		return append([]byte(nil), output...), used, fmt.Errorf("as0: EVM %s failed: %w (revert_data=0x%x)", method, callErr, output)
	}
	return output, used, nil
}

func validateGas(gas uint64) error {
	if gas == 0 || gas > MaxGas {
		return errors.New("as0: gas must be in frozen range 1..1000000000")
	}
	return nil
}

// Close releases the StateDB backing store. It is idempotent.
func (s *Session) Close() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.closed {
		return nil
	}
	s.closed = true
	var errs []error
	if s.trieDB != nil {
		if err := s.trieDB.Close(); err != nil {
			errs = append(errs, err)
		}
	}
	if s.disk != nil {
		if err := s.disk.Close(); err != nil {
			errs = append(errs, err)
		}
	}
	return errors.Join(errs...)
}

func (s *Session) persist(oldRoot common.Hash) (common.Hash, error) {
	root, err := s.commitTrie()
	if err != nil {
		s.restoreOldRoot(oldRoot)
		return common.Hash{}, fmt.Errorf("as0: commit StateDB/trie/code: %w", err)
	}
	if s.directory == "" {
		if err := s.reload(root); err != nil {
			s.uncertain = fmt.Errorf("as0: committed memory state cannot be reloaded: %w", err)
			return common.Hash{}, s.uncertain
		}
		return root, nil
	}
	if err := s.inject(faultAfterTrie); err != nil {
		s.restoreOldRoot(oldRoot)
		return common.Hash{}, fmt.Errorf("as0: injected failure after trie/code sync: %w", err)
	}
	published, err := s.writeManifest(s.makeManifest(root))
	if err != nil {
		if published {
			s.uncertain = fmt.Errorf("as0: manifest publication fsync is ambiguous; close and reopen required: %w", err)
			return common.Hash{}, s.uncertain
		}
		s.restoreOldRoot(oldRoot)
		return common.Hash{}, fmt.Errorf("as0: publish durable manifest: %w", err)
	}
	if err := s.reload(root); err != nil {
		s.uncertain = fmt.Errorf("as0: published state cannot be reloaded; close and reopen required: %w", err)
		return common.Hash{}, s.uncertain
	}
	return root, nil
}

func (s *Session) commitTrie() (common.Hash, error) {
	root, err := s.stateDB.Commit(1, true, true)
	if err != nil {
		return common.Hash{}, err
	}
	if err := s.trieDB.Commit(root, false); err != nil {
		return common.Hash{}, err
	}
	// SyncKeyValue covers trie nodes and contract/page code written to the same DB.
	if err := s.disk.SyncKeyValue(); err != nil {
		return common.Hash{}, err
	}
	return root, nil
}

func (s *Session) reload(root common.Hash) error {
	stateDB, err := state.New(root, state.NewDatabase(s.trieDB, nil))
	if err != nil {
		return err
	}
	s.stateDB, s.stateRoot = stateDB, root
	return nil
}

func (s *Session) restoreOldRoot(root common.Hash) {
	if err := s.reload(root); err != nil {
		s.uncertain = fmt.Errorf("as0: failed to reload old published root %s; close and reopen required: %w", root, err)
	}
}

func (s *Session) runtimeConfig(stateDB *state.StateDB, gas uint64) *evmruntime.Config {
	zeroHash := common.Hash{}
	return &evmruntime.Config{
		ChainConfig: params.AllDevChainProtocolChanges,
		Difficulty:  new(big.Int), Origin: s.owner, Coinbase: common.Address{}, BlockNumber: big.NewInt(1), Time: 1,
		GasLimit: gas, GasPrice: new(big.Int), Value: new(big.Int), BaseFee: new(big.Int).SetUint64(params.InitialBaseFee),
		BlobBaseFee: new(big.Int).SetUint64(params.BlobTxMinBlobGasprice), Random: &zeroHash, State: stateDB,
		GetHashFn: func(uint64) common.Hash { return common.Hash{} }, EVMConfig: vm.Config{},
	}
}

func (s *Session) usable() error {
	if s.closed {
		return errors.New("as0: session is closed")
	}
	if s.uncertain != nil {
		return s.uncertain
	}
	return nil
}

func (s *Session) makeManifest(root common.Hash) manifest {
	return manifest{Format: storeFormat, Context: contextID, Owner: s.owner, Controller: s.controller, DeclaredLength: s.declaredLength, RuntimeCodeHash: s.runtimeHash, StateRoot: root}
}

func prepareDirectory(directory string) (bool, error) {
	info, err := os.Lstat(directory)
	if errors.Is(err, os.ErrNotExist) {
		if err := os.MkdirAll(directory, 0o700); err != nil {
			return false, fmt.Errorf("as0: create store directory: %w", err)
		}
		return true, nil
	}
	if err != nil {
		return false, fmt.Errorf("as0: inspect store directory: %w", err)
	}
	if !info.IsDir() {
		return false, errors.New("as0: store path is not a directory")
	}
	entries, err := os.ReadDir(directory)
	if err != nil {
		return false, fmt.Errorf("as0: list store directory: %w", err)
	}
	if len(entries) == 0 {
		return true, nil
	}
	seen := make(map[string]bool)
	for _, entry := range entries {
		entryInfo, err := entry.Info()
		if err != nil {
			return false, fmt.Errorf("as0: inspect store entry: %w", err)
		}
		name := entry.Name()
		if strings.HasPrefix(name, ".durable-head-") && entryInfo.Mode().IsRegular() {
			continue // preserve owned unpublished diagnostics
		}
		seen[name] = true
		switch name {
		case stateDirectory:
			if !entryInfo.IsDir() {
				return false, fmt.Errorf("as0: store entry %q must be a real directory", name)
			}
			// LevelDB opens its own files after this function returns. Reject
			// links below the state directory as well as fixed top-level links;
			// otherwise e.g. CURRENT could redirect that later open outside it.
			if err := filepath.WalkDir(filepath.Join(directory, name), func(path string, entry os.DirEntry, walkErr error) error {
				if walkErr != nil {
					return walkErr
				}
				if entry.Type()&os.ModeSymlink != 0 {
					return fmt.Errorf("as0: linked state entry %q is not supported", path)
				}
				return nil
			}); err != nil {
				return false, err
			}
		case markerName, manifestName:
			if !entryInfo.Mode().IsRegular() {
				return false, fmt.Errorf("as0: store entry %q must be a regular file", name)
			}
		default:
			return false, fmt.Errorf("as0: refuse unrelated nonempty directory (unexpected %q)", name)
		}
	}
	if !seen[markerName] || !seen[manifestName] || !seen[stateDirectory] {
		return false, errors.New("as0: incomplete nonempty AS0 directory; refusing to invent a root or overwrite")
	}
	return false, nil
}

func diskMetadata(directory string, owner common.Address, length uint32, runtimeHash common.Hash) (manifest, error) {
	marker, err := readRegular(filepath.Join(directory, markerName), int64(len(storeMarker)))
	if err != nil || string(marker) != storeMarker {
		return manifest{}, errors.New("as0: invalid store marker")
	}
	m, err := readManifest(filepath.Join(directory, manifestName))
	if err != nil {
		return manifest{}, err
	}
	if m.Format != storeFormat || m.Context != contextID || m.Owner != owner || m.Controller == (common.Address{}) || m.DeclaredLength != length || m.RuntimeCodeHash != runtimeHash || m.StateRoot == (common.Hash{}) {
		return manifest{}, errors.New("as0: manifest format, context, owner, controller, length, runtime, or root mismatch")
	}
	return m, nil
}

func readRegular(path string, limit int64) ([]byte, error) {
	info, err := os.Lstat(path)
	if err != nil {
		return nil, err
	}
	if !info.Mode().IsRegular() || info.Size() < 0 || info.Size() > limit {
		return nil, fmt.Errorf("as0: unsupported file type or oversized file at %s", path)
	}
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	opened, err := file.Stat()
	if err != nil {
		return nil, err
	}
	if !opened.Mode().IsRegular() || !os.SameFile(info, opened) || opened.Size() > limit {
		return nil, fmt.Errorf("as0: file changed while opening %s", path)
	}
	raw, err := io.ReadAll(io.LimitReader(file, limit+1))
	if err != nil {
		return nil, err
	}
	if int64(len(raw)) > limit {
		return nil, fmt.Errorf("as0: file exceeded byte bound while reading %s", path)
	}
	return raw, nil
}

func readManifest(path string) (manifest, error) {
	var m manifest
	raw, err := readRegular(path, manifestMaxSize)
	if err != nil {
		return m, fmt.Errorf("as0: read durable manifest: %w", err)
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&m); err != nil {
		return m, fmt.Errorf("as0: decode durable manifest: %w", err)
	}
	var trailing interface{}
	if err := decoder.Decode(&trailing); !errors.Is(err, io.EOF) {
		if err == nil {
			return m, errors.New("as0: trailing durable manifest data")
		}
		return m, fmt.Errorf("as0: decode trailing durable manifest data: %w", err)
	}
	return m, nil
}

func (s *Session) writeManifest(m manifest) (bool, error) {
	if err := s.inject(faultBeforeManifest); err != nil {
		return false, err
	}
	raw, err := json.MarshalIndent(m, "", "  ")
	if err != nil {
		return false, err
	}
	raw = append(raw, '\n')
	tmp, err := os.CreateTemp(s.directory, ".durable-head-*")
	if err != nil {
		return false, err
	}
	tmpName := tmp.Name()
	// On failure the owned regular temporary is intentionally preserved.
	if err := tmp.Chmod(0o600); err != nil {
		tmp.Close()
		return false, err
	}
	if _, err := tmp.Write(raw); err != nil {
		tmp.Close()
		return false, err
	}
	if err := tmp.Sync(); err != nil {
		tmp.Close()
		return false, err
	}
	if err := tmp.Close(); err != nil {
		return false, err
	}
	if err := os.Rename(tmpName, filepath.Join(s.directory, manifestName)); err != nil {
		return false, err
	}
	if err := s.inject(faultAfterManifestRename); err != nil {
		return true, err
	}
	if err := syncDirectory(s.directory); err != nil {
		return true, err
	}
	return true, nil
}

func writeNewRegular(path string, raw []byte, mode os.FileMode) error {
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, mode)
	if err != nil {
		return err
	}
	if _, err := file.Write(raw); err != nil {
		file.Close()
		return err
	}
	if err := file.Sync(); err != nil {
		file.Close()
		return err
	}
	return file.Close()
}

func syncDirectory(path string) error {
	dir, err := os.Open(path)
	if err != nil {
		return err
	}
	defer dir.Close()
	return dir.Sync()
}

func (s *Session) inject(point faultPoint) error {
	if s.testFault != nil {
		return s.testFault(point)
	}
	return nil
}

func copyLogs(logs []*types.Log) []*types.Log {
	out := make([]*types.Log, len(logs))
	for i, log := range logs {
		copyLog := *log
		copyLog.Topics = append([]common.Hash(nil), log.Topics...)
		copyLog.Data = append([]byte(nil), log.Data...)
		out[i] = &copyLog
	}
	return out
}
