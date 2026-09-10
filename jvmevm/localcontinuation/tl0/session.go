// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.
//
// This program is free software: you can redistribute it and/or modify it under
// the terms of the GNU Lesser General Public License as published by the Free
// Software Foundation, either version 3 of the License, or (at your option) any
// later version.

package tl0

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
	tl0HarnessStoreFormat       = uint32(1)
	tl0HarnessStoreMarker       = "JVMEVM-MC-TL0-DISK-STORE-1\n"
	tl0HarnessStoreMarkerName   = "STORE-FORMAT"
	tl0HarnessManifestName      = "durable-head.json"
	tl0HarnessStateDirectory    = "state"
	tl0HarnessBlobDirectory     = "checkpoints"
	tl0HarnessContextID         = "all-dev-chain:block=1,time=1,coinbase=0000000000000000000000000000000000000000,value=0"
	tl0HarnessHeadGas           = uint64(100_000_000)
	tl0HarnessMaxCheckpointSize = 1 << 20
)

var tl0HarnessContractAddress = common.HexToAddress("0x004a564d45564d544c3052554e54494d4500000001")

type tl0HarnessManifest struct {
	Format          uint32         `json:"format"`
	Owner           common.Address `json:"owner"`
	Contract        common.Address `json:"contract"`
	RuntimeCodeHash common.Hash    `json:"runtimeCodeHash"`
	StateRoot       common.Hash    `json:"stateRoot"`
	Context         string         `json:"context"`
}

type tl0HarnessFaultPoint uint8

const (
	tl0HarnessFaultAfterBlob tl0HarnessFaultPoint = iota + 1
	tl0HarnessFaultAfterTrie
	tl0HarnessFaultBeforeManifest
	tl0HarnessFaultAfterManifestRename
	tl0HarnessFaultBeforeExistingBlobSync
)

type tl0HarnessDisk interface {
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
	disk      tl0HarnessDisk
	trieDB    *triedb.Database
	stateDB   *state.StateDB
	stateRoot common.Hash
	blobs     map[common.Hash][]byte

	closed    bool
	uncertain error

	// Tests may fail durable transport boundaries, never EVM or Java logic.
	testFault        func(tl0HarnessFaultPoint) error
	testCodeInstalls uint64
}

// NewMemory installs the pinned oversized runtime once into an ephemeral LOCAL
// StateDB account. This explicit harness installation is not CREATE/deployment
// evidence.
func NewMemory(owner common.Address) (*Session, error) {
	if owner == (common.Address{}) {
		return nil, errors.New("tl0: owner must be nonzero")
	}
	code, contractABI, err := tl0HarnessLoad()
	if err != nil {
		return nil, err
	}
	disk := rawdb.NewMemoryDatabase()
	session, err := tl0HarnessNewSession(owner, "", disk, code, contractABI)
	if err != nil {
		disk.Close()
		return nil, err
	}
	if err := session.tl0HarnessInstallCode(); err != nil {
		session.Close()
		return nil, err
	}
	return session, nil
}

// Open creates a new disk-backed LOCAL session only in an empty directory, or
// reopens an existing TL0 store. Reopen loads the manifest root and committed
// code; it never creates an account, installs code, or executes the runtime.
func Open(directory string, owner common.Address) (*Session, error) {
	if owner == (common.Address{}) {
		return nil, errors.New("tl0: owner must be nonzero")
	}
	if directory == "" {
		return nil, errors.New("tl0: directory must not be empty")
	}
	code, contractABI, err := tl0HarnessLoad()
	if err != nil {
		return nil, err
	}
	directory, err = filepath.Abs(directory)
	if err != nil {
		return nil, fmt.Errorf("tl0: resolve store directory: %w", err)
	}
	// A caller may reopen the same store through a directory alias. Resolve the
	// explicitly requested root first; entries inside the store still have the
	// fixed regular-file/directory shape and are never followed as links.
	if resolved, resolveErr := filepath.EvalSymlinks(directory); resolveErr == nil {
		directory = resolved
	} else if !errors.Is(resolveErr, os.ErrNotExist) {
		return nil, fmt.Errorf("tl0: resolve store root: %w", resolveErr)
	}
	fresh, err := tl0HarnessPrepareDirectory(directory)
	if err != nil {
		return nil, err
	}
	// Refuse an invalid store before LevelDB can create locks, logs or manifests.
	if !fresh {
		if _, err := tl0HarnessDiskMetadata(directory, owner, crypto.Keccak256Hash(code)); err != nil {
			return nil, err
		}
	}
	kv, err := leveldb.New(filepath.Join(directory, tl0HarnessStateDirectory), 16, 16, "jvmevm/tl0", false)
	if err != nil {
		return nil, fmt.Errorf("tl0: open state database: %w", err)
	}
	disk := rawdb.NewDatabase(kv)
	session, err := tl0HarnessNewSession(owner, directory, disk, code, contractABI)
	if err != nil {
		disk.Close()
		return nil, err
	}
	if fresh {
		if err := session.tl0HarnessInitializeDiskStore(); err != nil {
			session.Close()
			return nil, err
		}
		return session, nil
	}
	if err := session.tl0HarnessReopen(); err != nil {
		session.Close()
		return nil, err
	}
	return session, nil
}

func tl0HarnessNewSession(owner common.Address, directory string, disk tl0HarnessDisk, code []byte, contractABI abi.ABI) (*Session, error) {
	trieDB := triedb.NewDatabase(disk, triedb.HashDefaults)
	stateDB, err := state.New(types.EmptyRootHash, state.NewDatabase(trieDB, nil))
	if err != nil {
		trieDB.Close()
		return nil, fmt.Errorf("tl0: create empty StateDB: %w", err)
	}
	return &Session{
		owner: owner, contract: tl0HarnessContractAddress,
		code: append([]byte(nil), code...), codeHash: crypto.Keccak256Hash(code), contractABI: contractABI,
		directory: directory, disk: disk, trieDB: trieDB, stateDB: stateDB,
		stateRoot: types.EmptyRootHash, blobs: make(map[common.Hash][]byte),
	}, nil
}

func (s *Session) tl0HarnessInstallCode() error {
	s.stateDB.CreateAccount(s.contract)
	s.stateDB.SetCode(s.contract, s.code, tracing.CodeChangeUnspecified)
	s.testCodeInstalls++
	root, err := s.tl0HarnessCommitTrie()
	if err != nil {
		return fmt.Errorf("tl0: commit installed runtime: %w", err)
	}
	s.stateRoot = root
	return s.tl0HarnessReload(root)
}

func (s *Session) tl0HarnessInitializeDiskStore() error {
	if err := os.WriteFile(filepath.Join(s.directory, tl0HarnessStoreMarkerName), []byte(tl0HarnessStoreMarker), 0o600); err != nil {
		return fmt.Errorf("tl0: write store marker: %w", err)
	}
	if err := os.Mkdir(filepath.Join(s.directory, tl0HarnessBlobDirectory), 0o700); err != nil {
		return fmt.Errorf("tl0: create checkpoint directory: %w", err)
	}
	if err := tl0HarnessSyncDirectory(s.directory); err != nil {
		return fmt.Errorf("tl0: sync store layout: %w", err)
	}
	if err := s.tl0HarnessInstallCode(); err != nil {
		return err
	}
	manifest := s.tl0HarnessManifest(s.stateRoot)
	if _, err := s.tl0HarnessWriteManifest(manifest); err != nil {
		return fmt.Errorf("tl0: publish initial manifest: %w", err)
	}
	return nil
}

func tl0HarnessDiskMetadata(directory string, owner common.Address, codeHash common.Hash) (tl0HarnessManifest, error) {
	marker, err := tl0HarnessReadRegular(filepath.Join(directory, tl0HarnessStoreMarkerName), int64(len(tl0HarnessStoreMarker)))
	if err != nil || string(marker) != tl0HarnessStoreMarker {
		return tl0HarnessManifest{}, errors.New("tl0: invalid store marker")
	}
	manifest, err := tl0HarnessReadManifest(filepath.Join(directory, tl0HarnessManifestName))
	if err != nil {
		return manifest, err
	}
	if manifest.Format != tl0HarnessStoreFormat || manifest.Owner != owner || manifest.Contract != tl0HarnessContractAddress || manifest.RuntimeCodeHash != codeHash || manifest.Context != tl0HarnessContextID || manifest.StateRoot == (common.Hash{}) {
		return manifest, errors.New("tl0: manifest format, owner, contract, runtime, context, or root mismatch")
	}
	return manifest, nil
}

func (s *Session) tl0HarnessReopen() error {
	manifest, err := tl0HarnessDiskMetadata(s.directory, s.owner, s.codeHash)
	if err != nil {
		return err
	}
	if err := s.tl0HarnessReload(manifest.StateRoot); err != nil {
		return fmt.Errorf("tl0: load durable state root %s: %w", manifest.StateRoot, err)
	}
	if !bytes.Equal(s.stateDB.GetCode(s.contract), s.code) || s.stateDB.GetCodeHash(s.contract) != s.codeHash {
		return errors.New("tl0: committed runtime code is missing or differs from pinned artifact")
	}
	s.stateRoot = manifest.StateRoot
	return nil
}

// Start ABI-packs the unchanged raw classes and root inputs and calls the
// already-installed TL0 runtime. The returned checkpoint remains opaque to Go.
func (s *Session) Start(instance common.Hash, rawClasses [][]byte, entryClass, entry string, args []int32, maxJvmSteps uint64, maxInternalSteps uint32, gas uint64) (Result, error) {
	return s.tl0HarnessSlice("start", gas, instance, rawClasses, entryClass, entry, args, maxJvmSteps, maxInternalSteps)
}

// Resume transports the caller's opaque parent checkpoint back to the EVM.
func (s *Session) Resume(instance common.Hash, expectedEpoch uint64, expectedRoot common.Hash, rawClasses [][]byte, checkpoint []byte, maxJvmSteps uint64, maxInternalSteps uint32, gas uint64) (Result, error) {
	return s.tl0HarnessSlice("resume", gas, instance, expectedEpoch, expectedRoot, rawClasses, checkpoint, maxJvmSteps, maxInternalSteps)
}

func (s *Session) tl0HarnessSlice(method string, gas uint64, inputs ...interface{}) (Result, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var result Result
	if err := s.tl0HarnessUsable(); err != nil {
		return result, err
	}
	if gas == 0 || gas > 1_000_000_000 {
		return result, errors.New("tl0: gas must be in the frozen LOCAL range 1..1000000000")
	}
	callData, err := s.contractABI.Pack(method, inputs...)
	if err != nil {
		return result, fmt.Errorf("tl0: ABI-pack %s: %w", method, err)
	}
	oldRoot := s.stateRoot
	snapshot := s.stateDB.Snapshot()
	logCount := len(s.stateDB.Logs())
	output, left, callErr := evmruntime.Call(s.contract, callData, s.tl0HarnessRuntimeConfig(s.stateDB, gas))
	result.GasUsed = gas - left
	if callErr != nil {
		s.stateDB.RevertToSnapshot(snapshot)
		result.RevertData = append([]byte(nil), output...)
		return result, fmt.Errorf("tl0: EVM %s failed: %w (revert_data=0x%x)", method, callErr, output)
	}
	var checkpoint []byte
	if method == "start" {
		var decoded struct {
			Result     SliceResult
			Checkpoint []byte
		}
		if err := s.contractABI.UnpackIntoInterface(&decoded, method, output); err != nil {
			s.stateDB.RevertToSnapshot(snapshot)
			return result, fmt.Errorf("tl0: decode %s result: %w", method, err)
		}
		result.Slice, checkpoint = decoded.Result, decoded.Checkpoint
	} else {
		var decoded struct {
			Result          SliceResult
			ChildCheckpoint []byte
		}
		if err := s.contractABI.UnpackIntoInterface(&decoded, method, output); err != nil {
			s.stateDB.RevertToSnapshot(snapshot)
			return result, fmt.Errorf("tl0: decode %s result: %w", method, err)
		}
		result.Slice, checkpoint = decoded.Result, decoded.ChildCheckpoint
	}
	if err := tl0HarnessValidateSliceResult(result.Slice); err != nil {
		s.stateDB.RevertToSnapshot(snapshot)
		return Result{GasUsed: result.GasUsed}, err
	}
	result.Checkpoint = append([]byte(nil), checkpoint...)
	if len(result.Checkpoint) == 0 || len(result.Checkpoint) > tl0HarnessMaxCheckpointSize || crypto.Keccak256Hash(result.Checkpoint) != result.Slice.CheckpointRoot {
		s.stateDB.RevertToSnapshot(snapshot)
		return Result{GasUsed: result.GasUsed}, errors.New("tl0: EVM returned a missing, oversized, or root-mismatched checkpoint")
	}
	logs := s.stateDB.Logs()
	if logCount > len(logs) {
		s.stateDB.RevertToSnapshot(snapshot)
		return Result{GasUsed: result.GasUsed}, errors.New("tl0: StateDB log accounting moved backwards")
	}
	result.Logs = tl0HarnessCopyLogs(logs[logCount:])
	if err := s.tl0HarnessPersist(oldRoot, result.Slice.CheckpointRoot, result.Checkpoint); err != nil {
		// A rolled-back or ambiguously published call is not a committed slice.
		// Preserve diagnostic gas only; callers must consult the durable EVM head
		// after reopening, not use uncommitted child bytes or a success-shaped tuple.
		return Result{GasUsed: result.GasUsed}, err
	}
	return result, nil
}

func tl0HarnessValidateSliceResult(result SliceResult) error {
	if result.Schema != 1 || len(result.JavaClass) > 65535 {
		return errors.New("tl0: EVM returned an invalid slice schema or oversized Java class name")
	}
	switch result.Lifecycle {
	case 1: // RUNNABLE
		if result.Result != 0 || result.JavaKind != 0 || result.JavaRef != 0 || len(result.JavaClass) != 0 {
			return errors.New("tl0: EVM returned a noncanonical RUNNABLE outcome")
		}
	case 2: // RETURNED
		if result.JavaKind != 0 || result.JavaRef != 0 || len(result.JavaClass) != 0 {
			return errors.New("tl0: EVM returned a noncanonical RETURNED outcome")
		}
	case 3: // UNCAUGHT_JAVA
		if result.Result != 0 || result.JavaRef == 0 || result.JavaKind > 12 {
			return errors.New("tl0: EVM returned an invalid uncaught Java outcome")
		}
		if (result.JavaKind == 0) != (len(result.JavaClass) != 0) {
			return errors.New("tl0: EVM returned a noncanonical dynamic Java class name")
		}
	default:
		return errors.New("tl0: EVM returned an unknown lifecycle")
	}
	return nil
}

// Head calls the runtime's view method against an independent StateDB copy.
func (s *Session) Head(instance common.Hash) (Head, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var head Head
	if err := s.tl0HarnessUsable(); err != nil {
		return head, err
	}
	input, err := s.contractABI.Pack("head", instance)
	if err != nil {
		return head, fmt.Errorf("tl0: ABI-pack head: %w", err)
	}
	output, _, callErr := evmruntime.Call(s.contract, input, s.tl0HarnessRuntimeConfig(s.stateDB.Copy(), tl0HarnessHeadGas))
	if callErr != nil {
		return head, fmt.Errorf("tl0: EVM head failed: %w (revert_data=0x%x)", callErr, output)
	}
	if err := s.contractABI.UnpackIntoInterface(&head, "head", output); err != nil {
		return head, fmt.Errorf("tl0: decode head: %w", err)
	}
	return head, nil
}

// ReadCheckpoint retrieves an exact EVM-returned checkpoint by its keccak root.
// The bytes are integrity checked but never parsed by production Go.
func (s *Session) ReadCheckpoint(root common.Hash) ([]byte, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if err := s.tl0HarnessUsable(); err != nil {
		return nil, err
	}
	if root == (common.Hash{}) {
		return nil, errors.New("tl0: zero checkpoint root")
	}
	var blob []byte
	var err error
	if s.directory == "" {
		blob = append([]byte(nil), s.blobs[root]...)
		if len(blob) == 0 {
			err = os.ErrNotExist
		}
	} else {
		blob, err = tl0HarnessReadRegular(s.tl0HarnessBlobPath(root), tl0HarnessMaxCheckpointSize)
	}
	if err != nil {
		return nil, fmt.Errorf("tl0: read checkpoint %s: %w", root, err)
	}
	if len(blob) == 0 || len(blob) > tl0HarnessMaxCheckpointSize || crypto.Keccak256Hash(blob) != root {
		return nil, fmt.Errorf("tl0: checkpoint %s failed size/hash integrity", root)
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

func (s *Session) tl0HarnessPersist(oldRoot, checkpointRoot common.Hash, checkpoint []byte) error {
	if s.directory == "" {
		s.blobs[checkpointRoot] = append([]byte(nil), checkpoint...)
		root, err := s.tl0HarnessCommitTrie()
		if err != nil {
			if reloadErr := s.tl0HarnessReload(oldRoot); reloadErr != nil {
				s.uncertain = fmt.Errorf("tl0: in-memory commit failed (%v) and old root reload failed: %w", err, reloadErr)
				return s.uncertain
			}
			return fmt.Errorf("tl0: commit StateDB: %w", err)
		}
		s.stateRoot = root
		if err := s.tl0HarnessReload(root); err != nil {
			s.uncertain = fmt.Errorf("tl0: committed in-memory state cannot be reloaded: %w", err)
			return s.uncertain
		}
		return nil
	}
	if err := s.tl0HarnessWriteBlob(checkpointRoot, checkpoint); err != nil {
		s.tl0HarnessRestoreOldRoot(oldRoot)
		return err
	}
	if err := s.tl0HarnessInject(tl0HarnessFaultAfterBlob); err != nil {
		s.tl0HarnessRestoreOldRoot(oldRoot)
		return fmt.Errorf("tl0: injected failure after durable checkpoint blob: %w", err)
	}
	root, err := s.tl0HarnessCommitTrie()
	if err != nil {
		s.tl0HarnessRestoreOldRoot(oldRoot)
		return fmt.Errorf("tl0: commit StateDB/trie: %w", err)
	}
	if err := s.tl0HarnessInject(tl0HarnessFaultAfterTrie); err != nil {
		s.tl0HarnessRestoreOldRoot(oldRoot)
		return fmt.Errorf("tl0: injected failure after trie commit: %w", err)
	}
	manifest := s.tl0HarnessManifest(root)
	published, err := s.tl0HarnessWriteManifest(manifest)
	if err != nil {
		if published {
			s.uncertain = fmt.Errorf("tl0: manifest publication fsync is ambiguous; close and reopen required: %w", err)
			return s.uncertain
		}
		s.tl0HarnessRestoreOldRoot(oldRoot)
		return fmt.Errorf("tl0: publish durable manifest: %w", err)
	}
	s.stateRoot = root
	if err := s.tl0HarnessReload(root); err != nil {
		s.uncertain = fmt.Errorf("tl0: published state cannot be reloaded; close and reopen required: %w", err)
		return s.uncertain
	}
	return nil
}

func (s *Session) tl0HarnessCommitTrie() (common.Hash, error) {
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

func (s *Session) tl0HarnessReload(root common.Hash) error {
	stateDB, err := state.New(root, state.NewDatabase(s.trieDB, nil))
	if err != nil {
		return err
	}
	s.stateDB = stateDB
	s.stateRoot = root
	return nil
}

func (s *Session) tl0HarnessRestoreOldRoot(root common.Hash) {
	if err := s.tl0HarnessReload(root); err != nil {
		s.uncertain = fmt.Errorf("tl0: failed to reload old durable root %s; close and reopen required: %w", root, err)
	}
}

func (s *Session) tl0HarnessRuntimeConfig(stateDB *state.StateDB, gas uint64) *evmruntime.Config {
	zeroHash := common.Hash{}
	return &evmruntime.Config{
		ChainConfig: params.AllDevChainProtocolChanges,
		Difficulty:  new(big.Int), Origin: s.owner, Coinbase: common.Address{}, BlockNumber: big.NewInt(1), Time: 1,
		GasLimit: gas, GasPrice: new(big.Int), Value: new(big.Int), BaseFee: new(big.Int).SetUint64(params.InitialBaseFee),
		BlobBaseFee: new(big.Int).SetUint64(params.BlobTxMinBlobGasprice), Random: &zeroHash, State: stateDB,
		GetHashFn: func(uint64) common.Hash { return common.Hash{} }, EVMConfig: vm.Config{},
	}
}

func (s *Session) tl0HarnessUsable() error {
	if s.closed {
		return errors.New("tl0: session is closed")
	}
	if s.uncertain != nil {
		return s.uncertain
	}
	return nil
}

func (s *Session) tl0HarnessManifest(root common.Hash) tl0HarnessManifest {
	return tl0HarnessManifest{Format: tl0HarnessStoreFormat, Owner: s.owner, Contract: s.contract, RuntimeCodeHash: s.codeHash, StateRoot: root, Context: tl0HarnessContextID}
}

func tl0HarnessPrepareDirectory(directory string) (bool, error) {
	info, err := os.Lstat(directory)
	if errors.Is(err, os.ErrNotExist) {
		if err := os.MkdirAll(directory, 0o700); err != nil {
			return false, fmt.Errorf("tl0: create store directory: %w", err)
		}
		return true, nil
	}
	if err != nil {
		return false, fmt.Errorf("tl0: inspect store directory: %w", err)
	}
	if !info.IsDir() {
		return false, errors.New("tl0: store path is not a directory")
	}
	entries, err := os.ReadDir(directory)
	if err != nil {
		return false, fmt.Errorf("tl0: list store directory: %w", err)
	}
	if len(entries) == 0 {
		return true, nil
	}
	allowed := map[string]bool{tl0HarnessStoreMarkerName: true, tl0HarnessManifestName: true, tl0HarnessStateDirectory: true, tl0HarnessBlobDirectory: true}
	for _, entry := range entries {
		info, err := entry.Info()
		if err != nil {
			return false, fmt.Errorf("tl0: inspect store entry: %w", err)
		}
		// A crash may leave our unpublished manifest temporary next to the old
		// durable manifest. Ignore (do not parse/delete) only regular owned temporaries.
		if strings.HasPrefix(entry.Name(), ".durable-head-") && info.Mode().IsRegular() {
			continue
		}
		if !allowed[entry.Name()] {
			return false, fmt.Errorf("tl0: refuse unrelated nonempty directory (unexpected %q)", entry.Name())
		}
		wantDir := entry.Name() == tl0HarnessStateDirectory || entry.Name() == tl0HarnessBlobDirectory
		if (wantDir && !info.IsDir()) || (!wantDir && !info.Mode().IsRegular()) {
			return false, fmt.Errorf("tl0: store entry %q has unsupported file type", entry.Name())
		}
	}
	if !tl0HarnessAllowedEntriesPresent(entries, tl0HarnessStoreMarkerName, tl0HarnessManifestName, tl0HarnessStateDirectory, tl0HarnessBlobDirectory) {
		return false, errors.New("tl0: incomplete nonempty TL0 directory; refusing to overwrite")
	}
	return false, nil
}

func tl0HarnessAllowedEntriesPresent(entries []os.DirEntry, names ...string) bool {
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

// Bound disk transport allocations and reject unsupported file types before read.
// Session serialization is protected by its mutex; this is not a filesystem
// isolation boundary against an external process concurrently replacing paths.
func tl0HarnessReadRegular(path string, limit int64) ([]byte, error) {
	info, err := os.Lstat(path)
	if err != nil {
		return nil, err
	}
	if !info.Mode().IsRegular() || info.Size() < 0 || info.Size() > limit {
		return nil, fmt.Errorf("tl0: unsupported file type or oversized file at %s", path)
	}
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	opened, err := f.Stat()
	if err != nil {
		return nil, err
	}
	if !opened.Mode().IsRegular() || !os.SameFile(info, opened) || opened.Size() > limit {
		return nil, fmt.Errorf("tl0: file changed while opening %s", path)
	}
	b, err := io.ReadAll(io.LimitReader(f, limit+1))
	if err != nil {
		return nil, err
	}
	if int64(len(b)) > limit {
		return nil, fmt.Errorf("tl0: file exceeded byte bound while reading %s", path)
	}
	return b, nil
}

func tl0HarnessReadManifest(path string) (tl0HarnessManifest, error) {
	var manifest tl0HarnessManifest
	raw, err := tl0HarnessReadRegular(path, 4096)
	if err != nil {
		return manifest, fmt.Errorf("tl0: read durable manifest: %w", err)
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&manifest); err != nil {
		return manifest, fmt.Errorf("tl0: decode durable manifest: %w", err)
	}
	var trailing interface{}
	if err := decoder.Decode(&trailing); !errors.Is(err, io.EOF) {
		if err == nil {
			return manifest, errors.New("tl0: trailing durable manifest data")
		}
		return manifest, fmt.Errorf("tl0: decode trailing durable manifest data: %w", err)
	}
	return manifest, nil
}

func (s *Session) tl0HarnessWriteManifest(manifest tl0HarnessManifest) (bool, error) {
	if err := s.tl0HarnessInject(tl0HarnessFaultBeforeManifest); err != nil {
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
	if err := os.Rename(tmpName, filepath.Join(s.directory, tl0HarnessManifestName)); err != nil {
		return false, err
	}
	if err := s.tl0HarnessInject(tl0HarnessFaultAfterManifestRename); err != nil {
		return true, err
	}
	if err := tl0HarnessSyncDirectory(s.directory); err != nil {
		return true, err
	}
	return true, nil
}

func (s *Session) tl0HarnessWriteBlob(root common.Hash, blob []byte) error {
	if crypto.Keccak256Hash(blob) != root {
		return errors.New("tl0: refusing checkpoint blob whose bytes do not match root")
	}
	path := s.tl0HarnessBlobPath(root)
	if existing, err := tl0HarnessReadRegular(path, tl0HarnessMaxCheckpointSize); err == nil {
		if !bytes.Equal(existing, blob) {
			return fmt.Errorf("tl0: existing checkpoint blob %s differs", root)
		}
		// An orphan's rename may have preceded a process stop before directory
		// fsync. Verify and durably sync it before publishing a head that uses it.
		if err := s.tl0HarnessInject(tl0HarnessFaultBeforeExistingBlobSync); err != nil {
			return err
		}
		f, err := os.Open(path)
		if err != nil {
			return err
		}
		syncErr := f.Sync()
		closeErr := f.Close()
		if syncErr != nil {
			return syncErr
		}
		if closeErr != nil {
			return closeErr
		}
		return tl0HarnessSyncDirectory(filepath.Dir(path))
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
	return tl0HarnessSyncDirectory(filepath.Dir(path))
}

func (s *Session) tl0HarnessBlobPath(root common.Hash) string {
	return filepath.Join(s.directory, tl0HarnessBlobDirectory, root.Hex()[2:]+".checkpoint")
}

func (s *Session) tl0HarnessInject(point tl0HarnessFaultPoint) error {
	if s.testFault != nil {
		return s.testFault(point)
	}
	return nil
}

func tl0HarnessSyncDirectory(path string) error {
	dir, err := os.Open(path)
	if err != nil {
		return err
	}
	defer dir.Close()
	return dir.Sync()
}

func tl0HarnessCopyLogs(logs []*types.Log) []*types.Log {
	out := make([]*types.Log, len(logs))
	for i, log := range logs {
		copyLog := *log
		copyLog.Topics = append([]common.Hash(nil), log.Topics...)
		copyLog.Data = append([]byte(nil), log.Data...)
		out[i] = &copyLog
	}
	return out
}
