// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.
//
// This program is free software: you can redistribute it and/or modify it under
// the terms of the GNU Lesser General Public License as published by the Free
// Software Foundation, either version 3 of the License, or (at your option) any
// later version.

package lc0

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math/big"
	"os"
	"path/filepath"
	"sync"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/rawdb"
	"github.com/ethereum/go-ethereum/core/state"
	"github.com/ethereum/go-ethereum/core/tracing"
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
	lc0HarnessStoreFormat       = uint32(1)
	lc0HarnessStoreMarker       = "JVMEVM-MC-LC0-DISK-STORE-1\n"
	lc0HarnessStoreMarkerName   = "STORE-FORMAT"
	lc0HarnessManifestName      = "durable-head.json"
	lc0HarnessStateDirectory    = "state"
	lc0HarnessBlobDirectory     = "checkpoints"
	lc0HarnessContextID         = "all-dev-chain:block=1,time=1,coinbase=0000000000000000000000000000000000000000,value=0"
	lc0HarnessHeadGas           = uint64(100_000_000)
	lc0HarnessMaxCheckpointSize = 1 << 20
)

var lc0HarnessContractAddress = common.HexToAddress("0x4a564d45564d4c433052554e54494d4500000001")

type lc0HarnessManifest struct {
	Format          uint32         `json:"format"`
	Owner           common.Address `json:"owner"`
	Contract        common.Address `json:"contract"`
	RuntimeCodeHash common.Hash    `json:"runtimeCodeHash"`
	StateRoot       common.Hash    `json:"stateRoot"`
	Context         string         `json:"context"`
}

type lc0HarnessFaultPoint uint8

const (
	lc0HarnessFaultAfterBlob lc0HarnessFaultPoint = iota + 1
	lc0HarnessFaultAfterTrie
	lc0HarnessFaultBeforeManifest
	lc0HarnessFaultAfterManifestRename
)

type lc0HarnessDisk interface {
	ethdb.Database
	SyncKeyValue() error
}

type Session struct {
	mu sync.Mutex

	owner       common.Address
	contract    common.Address
	code        []byte
	codeHash    common.Hash
	contractABI abi.ABI

	directory string
	disk      lc0HarnessDisk
	trieDB    *triedb.Database
	stateDB   *state.StateDB
	stateRoot common.Hash
	blobs     map[common.Hash][]byte

	closed    bool
	uncertain error

	// Tests may fail durable transport boundaries, never EVM or Java logic.
	testFault        func(lc0HarnessFaultPoint) error
	testCodeInstalls uint64
}

// NewMemory installs the pinned oversized runtime once into an ephemeral LOCAL
// StateDB account. This explicit harness installation is not CREATE/deployment
// evidence.
func NewMemory(owner common.Address) (*Session, error) {
	if owner == (common.Address{}) {
		return nil, errors.New("lc0: owner must be nonzero")
	}
	code, contractABI, err := lc0HarnessLoad()
	if err != nil {
		return nil, err
	}
	disk := rawdb.NewMemoryDatabase()
	session, err := lc0HarnessNewSession(owner, "", disk, code, contractABI)
	if err != nil {
		disk.Close()
		return nil, err
	}
	if err := session.lc0HarnessInstallCode(); err != nil {
		session.Close()
		return nil, err
	}
	return session, nil
}

// Open creates a new disk-backed LOCAL session only in an empty directory, or
// reopens an existing LC0 store. Reopen loads the manifest root and committed
// code; it never creates an account, installs code, or executes the runtime.
func Open(directory string, owner common.Address) (*Session, error) {
	if owner == (common.Address{}) {
		return nil, errors.New("lc0: owner must be nonzero")
	}
	if directory == "" {
		return nil, errors.New("lc0: directory must not be empty")
	}
	code, contractABI, err := lc0HarnessLoad()
	if err != nil {
		return nil, err
	}
	directory, err = filepath.Abs(directory)
	if err != nil {
		return nil, fmt.Errorf("lc0: resolve store directory: %w", err)
	}
	fresh, err := lc0HarnessPrepareDirectory(directory)
	if err != nil {
		return nil, err
	}
	kv, err := leveldb.New(filepath.Join(directory, lc0HarnessStateDirectory), 16, 16, "jvmevm/lc0", false)
	if err != nil {
		return nil, fmt.Errorf("lc0: open state database: %w", err)
	}
	disk := rawdb.NewDatabase(kv)
	session, err := lc0HarnessNewSession(owner, directory, disk, code, contractABI)
	if err != nil {
		disk.Close()
		return nil, err
	}
	if fresh {
		if err := session.lc0HarnessInitializeDiskStore(); err != nil {
			session.Close()
			return nil, err
		}
		return session, nil
	}
	if err := session.lc0HarnessReopen(); err != nil {
		session.Close()
		return nil, err
	}
	return session, nil
}

func lc0HarnessNewSession(owner common.Address, directory string, disk lc0HarnessDisk, code []byte, contractABI abi.ABI) (*Session, error) {
	trieDB := triedb.NewDatabase(disk, triedb.HashDefaults)
	stateDB, err := state.New(types.EmptyRootHash, state.NewDatabase(trieDB, nil))
	if err != nil {
		trieDB.Close()
		return nil, fmt.Errorf("lc0: create empty StateDB: %w", err)
	}
	return &Session{
		owner: owner, contract: lc0HarnessContractAddress,
		code: append([]byte(nil), code...), codeHash: crypto.Keccak256Hash(code), contractABI: contractABI,
		directory: directory, disk: disk, trieDB: trieDB, stateDB: stateDB,
		stateRoot: types.EmptyRootHash, blobs: make(map[common.Hash][]byte),
	}, nil
}

func (s *Session) lc0HarnessInstallCode() error {
	s.stateDB.CreateAccount(s.contract)
	s.stateDB.SetCode(s.contract, s.code, tracing.CodeChangeUnspecified)
	s.testCodeInstalls++
	root, err := s.lc0HarnessCommitTrie()
	if err != nil {
		return fmt.Errorf("lc0: commit installed runtime: %w", err)
	}
	s.stateRoot = root
	return s.lc0HarnessReload(root)
}

func (s *Session) lc0HarnessInitializeDiskStore() error {
	if err := os.WriteFile(filepath.Join(s.directory, lc0HarnessStoreMarkerName), []byte(lc0HarnessStoreMarker), 0o600); err != nil {
		return fmt.Errorf("lc0: write store marker: %w", err)
	}
	if err := os.Mkdir(filepath.Join(s.directory, lc0HarnessBlobDirectory), 0o700); err != nil {
		return fmt.Errorf("lc0: create checkpoint directory: %w", err)
	}
	if err := lc0HarnessSyncDirectory(s.directory); err != nil {
		return fmt.Errorf("lc0: sync store layout: %w", err)
	}
	if err := s.lc0HarnessInstallCode(); err != nil {
		return err
	}
	manifest := s.lc0HarnessManifest(s.stateRoot)
	if _, err := s.lc0HarnessWriteManifest(manifest); err != nil {
		return fmt.Errorf("lc0: publish initial manifest: %w", err)
	}
	return nil
}

func (s *Session) lc0HarnessReopen() error {
	marker, err := os.ReadFile(filepath.Join(s.directory, lc0HarnessStoreMarkerName))
	if err != nil || string(marker) != lc0HarnessStoreMarker {
		return fmt.Errorf("lc0: invalid store marker")
	}
	manifest, err := lc0HarnessReadManifest(filepath.Join(s.directory, lc0HarnessManifestName))
	if err != nil {
		return err
	}
	if manifest.Format != lc0HarnessStoreFormat || manifest.Owner != s.owner || manifest.Contract != s.contract || manifest.RuntimeCodeHash != s.codeHash || manifest.Context != lc0HarnessContextID {
		return errors.New("lc0: manifest format, owner, contract, runtime, or context mismatch")
	}
	if err := s.lc0HarnessReload(manifest.StateRoot); err != nil {
		return fmt.Errorf("lc0: load durable state root %s: %w", manifest.StateRoot, err)
	}
	if !bytes.Equal(s.stateDB.GetCode(s.contract), s.code) || s.stateDB.GetCodeHash(s.contract) != s.codeHash {
		return errors.New("lc0: committed runtime code is missing or differs from pinned artifact")
	}
	s.stateRoot = manifest.StateRoot
	return nil
}

// Start ABI-packs the unchanged raw classes and root inputs and calls the
// already-installed LC0 runtime. The returned checkpoint remains opaque to Go.
func (s *Session) Start(instance common.Hash, rawClasses [][]byte, entryClass, entry string, args []int32, maxJvmSteps uint64, maxInternalSteps uint32, gas uint64) (Result, error) {
	return s.lc0HarnessSlice("start", gas, instance, rawClasses, entryClass, entry, args, maxJvmSteps, maxInternalSteps)
}

// Resume transports the caller's opaque parent checkpoint back to the EVM.
func (s *Session) Resume(instance common.Hash, expectedEpoch uint64, expectedRoot common.Hash, rawClasses [][]byte, checkpoint []byte, maxJvmSteps uint64, maxInternalSteps uint32, gas uint64) (Result, error) {
	return s.lc0HarnessSlice("resume", gas, instance, expectedEpoch, expectedRoot, rawClasses, checkpoint, maxJvmSteps, maxInternalSteps)
}

func (s *Session) lc0HarnessSlice(method string, gas uint64, inputs ...interface{}) (Result, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var result Result
	if err := s.lc0HarnessUsable(); err != nil {
		return result, err
	}
	if gas == 0 || gas > 1_000_000_000 {
		return result, errors.New("lc0: gas must be in the frozen LOCAL range 1..1000000000")
	}
	callData, err := s.contractABI.Pack(method, inputs...)
	if err != nil {
		return result, fmt.Errorf("lc0: ABI-pack %s: %w", method, err)
	}
	oldRoot := s.stateRoot
	snapshot := s.stateDB.Snapshot()
	logCount := len(s.stateDB.Logs())
	output, left, callErr := evmruntime.Call(s.contract, callData, s.lc0HarnessRuntimeConfig(s.stateDB, gas))
	result.GasUsed = gas - left
	if callErr != nil {
		s.stateDB.RevertToSnapshot(snapshot)
		result.RevertData = append([]byte(nil), output...)
		return result, fmt.Errorf("lc0: EVM %s failed: %w (revert_data=0x%x)", method, callErr, output)
	}
	var checkpoint []byte
	if method == "start" {
		var decoded struct {
			Result     SliceResult
			Checkpoint []byte
		}
		if err := s.contractABI.UnpackIntoInterface(&decoded, method, output); err != nil {
			s.stateDB.RevertToSnapshot(snapshot)
			return result, fmt.Errorf("lc0: decode %s result: %w", method, err)
		}
		result.Slice, checkpoint = decoded.Result, decoded.Checkpoint
	} else {
		var decoded struct {
			Result          SliceResult
			ChildCheckpoint []byte
		}
		if err := s.contractABI.UnpackIntoInterface(&decoded, method, output); err != nil {
			s.stateDB.RevertToSnapshot(snapshot)
			return result, fmt.Errorf("lc0: decode %s result: %w", method, err)
		}
		result.Slice, checkpoint = decoded.Result, decoded.ChildCheckpoint
	}
	result.Checkpoint = append([]byte(nil), checkpoint...)
	if len(result.Checkpoint) == 0 || len(result.Checkpoint) > lc0HarnessMaxCheckpointSize || crypto.Keccak256Hash(result.Checkpoint) != result.Slice.CheckpointRoot {
		s.stateDB.RevertToSnapshot(snapshot)
		return result, errors.New("lc0: EVM returned a missing, oversized, or root-mismatched checkpoint")
	}
	logs := s.stateDB.Logs()
	if logCount > len(logs) {
		s.stateDB.RevertToSnapshot(snapshot)
		return result, errors.New("lc0: StateDB log accounting moved backwards")
	}
	result.Logs = lc0HarnessCopyLogs(logs[logCount:])
	if err := s.lc0HarnessPersist(oldRoot, result.Slice.CheckpointRoot, result.Checkpoint); err != nil {
		// A transport failure is not a successfully published slice receipt.
		// The opaque child bytes remain available for deterministic retry tests,
		// but do not expose an uncommitted/ambiguously committed child log.
		result.Logs = nil
		return result, err
	}
	return result, nil
}

// Head calls the runtime's view method against an independent StateDB copy.
func (s *Session) Head(instance common.Hash) (Head, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var head Head
	if err := s.lc0HarnessUsable(); err != nil {
		return head, err
	}
	input, err := s.contractABI.Pack("head", instance)
	if err != nil {
		return head, fmt.Errorf("lc0: ABI-pack head: %w", err)
	}
	output, _, callErr := evmruntime.Call(s.contract, input, s.lc0HarnessRuntimeConfig(s.stateDB.Copy(), lc0HarnessHeadGas))
	if callErr != nil {
		return head, fmt.Errorf("lc0: EVM head failed: %w (revert_data=0x%x)", callErr, output)
	}
	if err := s.contractABI.UnpackIntoInterface(&head, "head", output); err != nil {
		return head, fmt.Errorf("lc0: decode head: %w", err)
	}
	return head, nil
}

// ReadCheckpoint retrieves an exact EVM-returned checkpoint by its keccak root.
// The bytes are integrity checked but never parsed by production Go.
func (s *Session) ReadCheckpoint(root common.Hash) ([]byte, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if err := s.lc0HarnessUsable(); err != nil {
		return nil, err
	}
	if root == (common.Hash{}) {
		return nil, errors.New("lc0: zero checkpoint root")
	}
	var blob []byte
	var err error
	if s.directory == "" {
		blob = append([]byte(nil), s.blobs[root]...)
		if len(blob) == 0 {
			err = os.ErrNotExist
		}
	} else {
		blob, err = os.ReadFile(s.lc0HarnessBlobPath(root))
	}
	if err != nil {
		return nil, fmt.Errorf("lc0: read checkpoint %s: %w", root, err)
	}
	if len(blob) == 0 || len(blob) > lc0HarnessMaxCheckpointSize || crypto.Keccak256Hash(blob) != root {
		return nil, fmt.Errorf("lc0: checkpoint %s failed size/hash integrity", root)
	}
	return append([]byte(nil), blob...), nil
}

// Close releases the session's StateDB backing store. It is idempotent.
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

func (s *Session) lc0HarnessPersist(oldRoot, checkpointRoot common.Hash, checkpoint []byte) error {
	if s.directory == "" {
		s.blobs[checkpointRoot] = append([]byte(nil), checkpoint...)
		root, err := s.lc0HarnessCommitTrie()
		if err != nil {
			if reloadErr := s.lc0HarnessReload(oldRoot); reloadErr != nil {
				s.uncertain = fmt.Errorf("lc0: in-memory commit failed (%v) and old root reload failed: %w", err, reloadErr)
				return s.uncertain
			}
			return fmt.Errorf("lc0: commit StateDB: %w", err)
		}
		s.stateRoot = root
		if err := s.lc0HarnessReload(root); err != nil {
			s.uncertain = fmt.Errorf("lc0: committed in-memory state cannot be reloaded: %w", err)
			return s.uncertain
		}
		return nil
	}
	if err := s.lc0HarnessWriteBlob(checkpointRoot, checkpoint); err != nil {
		s.lc0HarnessRestoreOldRoot(oldRoot)
		return err
	}
	if err := s.lc0HarnessInject(lc0HarnessFaultAfterBlob); err != nil {
		s.lc0HarnessRestoreOldRoot(oldRoot)
		return fmt.Errorf("lc0: injected failure after durable checkpoint blob: %w", err)
	}
	root, err := s.lc0HarnessCommitTrie()
	if err != nil {
		s.lc0HarnessRestoreOldRoot(oldRoot)
		return fmt.Errorf("lc0: commit StateDB/trie: %w", err)
	}
	if err := s.lc0HarnessInject(lc0HarnessFaultAfterTrie); err != nil {
		s.lc0HarnessRestoreOldRoot(oldRoot)
		return fmt.Errorf("lc0: injected failure after trie commit: %w", err)
	}
	manifest := s.lc0HarnessManifest(root)
	published, err := s.lc0HarnessWriteManifest(manifest)
	if err != nil {
		if published {
			s.uncertain = fmt.Errorf("lc0: manifest publication fsync is ambiguous; close and reopen required: %w", err)
			return s.uncertain
		}
		s.lc0HarnessRestoreOldRoot(oldRoot)
		return fmt.Errorf("lc0: publish durable manifest: %w", err)
	}
	s.stateRoot = root
	if err := s.lc0HarnessReload(root); err != nil {
		s.uncertain = fmt.Errorf("lc0: published state cannot be reloaded; close and reopen required: %w", err)
		return s.uncertain
	}
	return nil
}

func (s *Session) lc0HarnessCommitTrie() (common.Hash, error) {
	root, err := s.stateDB.Commit(1, true, true)
	if err != nil {
		return common.Hash{}, err
	}
	if err := s.trieDB.Commit(root, false); err != nil {
		return common.Hash{}, err
	}
	if err := s.disk.SyncKeyValue(); err != nil {
		return common.Hash{}, err
	}
	return root, nil
}

func (s *Session) lc0HarnessReload(root common.Hash) error {
	stateDB, err := state.New(root, state.NewDatabase(s.trieDB, nil))
	if err != nil {
		return err
	}
	s.stateDB = stateDB
	s.stateRoot = root
	return nil
}

func (s *Session) lc0HarnessRestoreOldRoot(root common.Hash) {
	if err := s.lc0HarnessReload(root); err != nil {
		s.uncertain = fmt.Errorf("lc0: failed to reload old durable root %s; close and reopen required: %w", root, err)
	}
}

func (s *Session) lc0HarnessRuntimeConfig(stateDB *state.StateDB, gas uint64) *evmruntime.Config {
	zeroHash := common.Hash{}
	return &evmruntime.Config{
		ChainConfig: params.AllDevChainProtocolChanges,
		Difficulty:  new(big.Int), Origin: s.owner, Coinbase: common.Address{}, BlockNumber: big.NewInt(1), Time: 1,
		GasLimit: gas, GasPrice: new(big.Int), Value: new(big.Int), BaseFee: new(big.Int).SetUint64(params.InitialBaseFee),
		BlobBaseFee: new(big.Int).SetUint64(params.BlobTxMinBlobGasprice), Random: &zeroHash, State: stateDB,
		GetHashFn: func(uint64) common.Hash { return common.Hash{} }, EVMConfig: vm.Config{},
	}
}

func (s *Session) lc0HarnessUsable() error {
	if s.closed {
		return errors.New("lc0: session is closed")
	}
	if s.uncertain != nil {
		return s.uncertain
	}
	return nil
}

func (s *Session) lc0HarnessManifest(root common.Hash) lc0HarnessManifest {
	return lc0HarnessManifest{Format: lc0HarnessStoreFormat, Owner: s.owner, Contract: s.contract, RuntimeCodeHash: s.codeHash, StateRoot: root, Context: lc0HarnessContextID}
}

func lc0HarnessPrepareDirectory(directory string) (bool, error) {
	info, err := os.Stat(directory)
	if errors.Is(err, os.ErrNotExist) {
		if err := os.MkdirAll(directory, 0o700); err != nil {
			return false, fmt.Errorf("lc0: create store directory: %w", err)
		}
		return true, nil
	}
	if err != nil {
		return false, fmt.Errorf("lc0: inspect store directory: %w", err)
	}
	if !info.IsDir() {
		return false, errors.New("lc0: store path is not a directory")
	}
	entries, err := os.ReadDir(directory)
	if err != nil {
		return false, fmt.Errorf("lc0: list store directory: %w", err)
	}
	if len(entries) == 0 {
		return true, nil
	}
	allowed := map[string]bool{lc0HarnessStoreMarkerName: true, lc0HarnessManifestName: true, lc0HarnessStateDirectory: true, lc0HarnessBlobDirectory: true}
	for _, entry := range entries {
		if !allowed[entry.Name()] {
			return false, fmt.Errorf("lc0: refuse unrelated nonempty directory (unexpected %q)", entry.Name())
		}
	}
	if !lc0HarnessAllowedEntriesPresent(entries, lc0HarnessStoreMarkerName, lc0HarnessManifestName, lc0HarnessStateDirectory, lc0HarnessBlobDirectory) {
		return false, errors.New("lc0: incomplete nonempty LC0 directory; refusing to overwrite")
	}
	return false, nil
}

func lc0HarnessAllowedEntriesPresent(entries []os.DirEntry, names ...string) bool {
	seen := make(map[string]bool, len(entries))
	for _, entry := range entries {
		seen[entry.Name()] = true
	}
	for _, name := range names {
		if !seen[name] {
			return false
		}
	}
	return true
}

func lc0HarnessReadManifest(path string) (lc0HarnessManifest, error) {
	var manifest lc0HarnessManifest
	raw, err := os.ReadFile(path)
	if err != nil {
		return manifest, fmt.Errorf("lc0: read durable manifest: %w", err)
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&manifest); err != nil {
		return manifest, fmt.Errorf("lc0: decode durable manifest: %w", err)
	}
	var trailing interface{}
	if err := decoder.Decode(&trailing); !errors.Is(err, io.EOF) {
		if err == nil {
			return manifest, errors.New("lc0: trailing durable manifest data")
		}
		return manifest, fmt.Errorf("lc0: decode trailing durable manifest data: %w", err)
	}
	return manifest, nil
}

func (s *Session) lc0HarnessWriteManifest(manifest lc0HarnessManifest) (bool, error) {
	if err := s.lc0HarnessInject(lc0HarnessFaultBeforeManifest); err != nil {
		return false, err
	}
	raw, err := json.MarshalIndent(manifest, "", "  ")
	if err != nil {
		return false, err
	}
	raw = append(raw, '\n')
	tmp, err := os.CreateTemp(s.directory, ".durable-head-*")
	if err != nil {
		return false, err
	}
	tmpName := tmp.Name()
	defer os.Remove(tmpName)
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
	if err := os.Rename(tmpName, filepath.Join(s.directory, lc0HarnessManifestName)); err != nil {
		return false, err
	}
	if err := s.lc0HarnessInject(lc0HarnessFaultAfterManifestRename); err != nil {
		return true, err
	}
	if err := lc0HarnessSyncDirectory(s.directory); err != nil {
		return true, err
	}
	return true, nil
}

func (s *Session) lc0HarnessWriteBlob(root common.Hash, blob []byte) error {
	if crypto.Keccak256Hash(blob) != root {
		return errors.New("lc0: refusing checkpoint blob whose bytes do not match root")
	}
	path := s.lc0HarnessBlobPath(root)
	if existing, err := os.ReadFile(path); err == nil {
		if !bytes.Equal(existing, blob) {
			return fmt.Errorf("lc0: existing checkpoint blob %s differs", root)
		}
		return nil
	} else if !errors.Is(err, os.ErrNotExist) {
		return err
	}
	tmp, err := os.CreateTemp(filepath.Dir(path), ".checkpoint-*")
	if err != nil {
		return err
	}
	tmpName := tmp.Name()
	defer os.Remove(tmpName)
	if err := tmp.Chmod(0o600); err != nil {
		tmp.Close()
		return err
	}
	if _, err := tmp.Write(blob); err != nil {
		tmp.Close()
		return err
	}
	if err := tmp.Sync(); err != nil {
		tmp.Close()
		return err
	}
	if err := tmp.Close(); err != nil {
		return err
	}
	if err := os.Rename(tmpName, path); err != nil {
		return err
	}
	return lc0HarnessSyncDirectory(filepath.Dir(path))
}

func (s *Session) lc0HarnessBlobPath(root common.Hash) string {
	return filepath.Join(s.directory, lc0HarnessBlobDirectory, root.Hex()[2:]+".checkpoint")
}

func (s *Session) lc0HarnessInject(point lc0HarnessFaultPoint) error {
	if s.testFault != nil {
		return s.testFault(point)
	}
	return nil
}

func lc0HarnessSyncDirectory(path string) error {
	dir, err := os.Open(path)
	if err != nil {
		return err
	}
	defer dir.Close()
	return dir.Sync()
}

func lc0HarnessCopyLogs(logs []*types.Log) []*types.Log {
	out := make([]*types.Log, len(logs))
	for i, log := range logs {
		copyLog := *log
		copyLog.Topics = append([]common.Hash(nil), log.Topics...)
		copyLog.Data = append([]byte(nil), log.Data...)
		out[i] = &copyLog
	}
	return out
}
