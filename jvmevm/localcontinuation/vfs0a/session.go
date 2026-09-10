// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.
//
// This program is free software: you can redistribute it and/or modify it under
// the terms of the GNU Lesser General Public License as published by the Free
// Software Foundation, either version 3 of the License, or (at your option) any
// later version.

package vfs0a

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
	vfs0aHarnessStoreFormat       = uint32(1)
	vfs0aHarnessStoreMarker       = "JVMEVM-MC-VFS0A-DISK-STORE-1\n"
	vfs0aHarnessStoreMarkerName   = "STORE-FORMAT"
	vfs0aHarnessManifestName      = "durable-head.json"
	vfs0aHarnessStateDirectory    = "state"
	vfs0aHarnessBlobDirectory     = "checkpoints"
	vfs0aHarnessContextID         = "all-dev-chain:block=1,time=1,coinbase=0000000000000000000000000000000000000000,value=0"
	vfs0aHarnessHeadGas           = uint64(100_000_000)
	vfs0aHarnessMaxCheckpointSize = 1 << 20
)

var vfs0aHarnessContractAddress = common.HexToAddress("0x4a564d45564d564653304152554e54494d450001")

type vfs0aHarnessManifest struct {
	Format          uint32         `json:"format"`
	Owner           common.Address `json:"owner"`
	Contract        common.Address `json:"contract"`
	RuntimeCodeHash common.Hash    `json:"runtimeCodeHash"`
	StateRoot       common.Hash    `json:"stateRoot"`
	Context         string         `json:"context"`
}

type vfs0aHarnessFaultPoint uint8

const (
	vfs0aHarnessFaultAfterBlob vfs0aHarnessFaultPoint = iota + 1
	vfs0aHarnessFaultAfterTrie
	vfs0aHarnessFaultBeforeManifest
	vfs0aHarnessFaultAfterManifestRename
	vfs0aHarnessFaultBeforeExistingBlobSync
)

type vfs0aHarnessDisk interface {
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
	disk      vfs0aHarnessDisk
	trieDB    *triedb.Database
	stateDB   *state.StateDB
	stateRoot common.Hash
	blobs     map[common.Hash][]byte

	closed    bool
	uncertain error

	// Tests may fail durable transport boundaries, never EVM or Java logic.
	testFault        func(vfs0aHarnessFaultPoint) error
	testCodeInstalls uint64
}

// NewMemory installs the pinned oversized runtime once into an ephemeral LOCAL
// StateDB account. This explicit harness installation is not CREATE/deployment
// evidence.
func NewMemory(owner common.Address) (*Session, error) {
	if owner == (common.Address{}) {
		return nil, errors.New("vfs0a: owner must be nonzero")
	}
	code, contractABI, err := vfs0aHarnessLoad()
	if err != nil {
		return nil, err
	}
	disk := rawdb.NewMemoryDatabase()
	session, err := vfs0aHarnessNewSession(owner, "", disk, code, contractABI)
	if err != nil {
		disk.Close()
		return nil, err
	}
	if err := session.vfs0aHarnessInstallCode(); err != nil {
		session.Close()
		return nil, err
	}
	return session, nil
}

// Open creates a new disk-backed LOCAL session only in an empty directory, or
// reopens an existing VFS0a store. Reopen loads the manifest root and committed
// code; it never creates an account, installs code, or executes the runtime.
func Open(directory string, owner common.Address) (*Session, error) {
	if owner == (common.Address{}) {
		return nil, errors.New("vfs0a: owner must be nonzero")
	}
	if directory == "" {
		return nil, errors.New("vfs0a: directory must not be empty")
	}
	code, contractABI, err := vfs0aHarnessLoad()
	if err != nil {
		return nil, err
	}
	directory, err = filepath.Abs(directory)
	if err != nil {
		return nil, fmt.Errorf("vfs0a: resolve store directory: %w", err)
	}
	// A caller may reopen the same store through a directory alias. Resolve the
	// explicitly requested root first; entries inside the store still have the
	// fixed regular-file/directory shape and are never followed as links.
	if resolved, resolveErr := filepath.EvalSymlinks(directory); resolveErr == nil {
		directory = resolved
	} else if !errors.Is(resolveErr, os.ErrNotExist) {
		return nil, fmt.Errorf("vfs0a: resolve store root: %w", resolveErr)
	}
	fresh, err := vfs0aHarnessPrepareDirectory(directory)
	if err != nil {
		return nil, err
	}
	// Refuse an invalid store before LevelDB can create locks, logs or manifests.
	if !fresh {
		if _, err := vfs0aHarnessDiskMetadata(directory, owner, crypto.Keccak256Hash(code)); err != nil {
			return nil, err
		}
	}
	kv, err := leveldb.New(filepath.Join(directory, vfs0aHarnessStateDirectory), 16, 16, "jvmevm/vfs0a", false)
	if err != nil {
		return nil, fmt.Errorf("vfs0a: open state database: %w", err)
	}
	disk := rawdb.NewDatabase(kv)
	session, err := vfs0aHarnessNewSession(owner, directory, disk, code, contractABI)
	if err != nil {
		disk.Close()
		return nil, err
	}
	if fresh {
		if err := session.vfs0aHarnessInitializeDiskStore(); err != nil {
			session.Close()
			return nil, err
		}
		return session, nil
	}
	if err := session.vfs0aHarnessReopen(); err != nil {
		session.Close()
		return nil, err
	}
	return session, nil
}

func vfs0aHarnessNewSession(owner common.Address, directory string, disk vfs0aHarnessDisk, code []byte, contractABI abi.ABI) (*Session, error) {
	trieDB := triedb.NewDatabase(disk, triedb.HashDefaults)
	stateDB, err := state.New(types.EmptyRootHash, state.NewDatabase(trieDB, nil))
	if err != nil {
		trieDB.Close()
		return nil, fmt.Errorf("vfs0a: create empty StateDB: %w", err)
	}
	return &Session{
		owner: owner, contract: vfs0aHarnessContractAddress,
		code: append([]byte(nil), code...), codeHash: crypto.Keccak256Hash(code), contractABI: contractABI,
		directory: directory, disk: disk, trieDB: trieDB, stateDB: stateDB,
		stateRoot: types.EmptyRootHash, blobs: make(map[common.Hash][]byte),
	}, nil
}

func (s *Session) vfs0aHarnessInstallCode() error {
	s.stateDB.CreateAccount(s.contract)
	s.stateDB.SetCode(s.contract, s.code, tracing.CodeChangeUnspecified)
	s.testCodeInstalls++
	root, err := s.vfs0aHarnessCommitTrie()
	if err != nil {
		return fmt.Errorf("vfs0a: commit installed runtime: %w", err)
	}
	s.stateRoot = root
	return s.vfs0aHarnessReload(root)
}

func (s *Session) vfs0aHarnessInitializeDiskStore() error {
	if err := os.WriteFile(filepath.Join(s.directory, vfs0aHarnessStoreMarkerName), []byte(vfs0aHarnessStoreMarker), 0o600); err != nil {
		return fmt.Errorf("vfs0a: write store marker: %w", err)
	}
	if err := os.Mkdir(filepath.Join(s.directory, vfs0aHarnessBlobDirectory), 0o700); err != nil {
		return fmt.Errorf("vfs0a: create checkpoint directory: %w", err)
	}
	if err := vfs0aHarnessSyncDirectory(s.directory); err != nil {
		return fmt.Errorf("vfs0a: sync store layout: %w", err)
	}
	if err := s.vfs0aHarnessInstallCode(); err != nil {
		return err
	}
	manifest := s.vfs0aHarnessManifest(s.stateRoot)
	if _, err := s.vfs0aHarnessWriteManifest(manifest); err != nil {
		return fmt.Errorf("vfs0a: publish initial manifest: %w", err)
	}
	return nil
}

func vfs0aHarnessDiskMetadata(directory string, owner common.Address, codeHash common.Hash) (vfs0aHarnessManifest, error) {
	marker, err := vfs0aHarnessReadRegular(filepath.Join(directory, vfs0aHarnessStoreMarkerName), int64(len(vfs0aHarnessStoreMarker)))
	if err != nil || string(marker) != vfs0aHarnessStoreMarker {
		return vfs0aHarnessManifest{}, errors.New("vfs0a: invalid store marker")
	}
	manifest, err := vfs0aHarnessReadManifest(filepath.Join(directory, vfs0aHarnessManifestName))
	if err != nil {
		return manifest, err
	}
	if manifest.Format != vfs0aHarnessStoreFormat || manifest.Owner != owner || manifest.Contract != vfs0aHarnessContractAddress || manifest.RuntimeCodeHash != codeHash || manifest.Context != vfs0aHarnessContextID || manifest.StateRoot == (common.Hash{}) {
		return manifest, errors.New("vfs0a: manifest format, owner, contract, runtime, context, or root mismatch")
	}
	return manifest, nil
}

func (s *Session) vfs0aHarnessReopen() error {
	manifest, err := vfs0aHarnessDiskMetadata(s.directory, s.owner, s.codeHash)
	if err != nil {
		return err
	}
	if err := s.vfs0aHarnessReload(manifest.StateRoot); err != nil {
		return fmt.Errorf("vfs0a: load durable state root %s: %w", manifest.StateRoot, err)
	}
	if !bytes.Equal(s.stateDB.GetCode(s.contract), s.code) || s.stateDB.GetCodeHash(s.contract) != s.codeHash {
		return errors.New("vfs0a: committed runtime code is missing or differs from pinned artifact")
	}
	s.stateRoot = manifest.StateRoot
	return nil
}

// Start ABI-packs unchanged raw classes, root inputs, and raw seeds and calls the
// already-installed VFS0a runtime. Seed paths and data and the returned checkpoint
// remain opaque to production Go. Seeds are deliberately absent from Resume.
func (s *Session) Start(instance common.Hash, rawClasses [][]byte, entryClass, entry string, args []int32, seeds []SeedFile, maxJvmSteps uint64, maxInternalSteps uint32, gas uint64) (Result, error) {
	return s.vfs0aHarnessSlice("start", gas, maxJvmSteps, maxInternalSteps, instance, rawClasses, entryClass, entry, args, seeds, maxJvmSteps, maxInternalSteps)
}

// Resume transports the caller's opaque parent checkpoint back to the EVM.
func (s *Session) Resume(instance common.Hash, expectedEpoch uint64, expectedRoot common.Hash, rawClasses [][]byte, checkpoint []byte, maxJvmSteps uint64, maxInternalSteps uint32, gas uint64) (Result, error) {
	return s.vfs0aHarnessSlice("resume", gas, maxJvmSteps, maxInternalSteps, instance, expectedEpoch, expectedRoot, rawClasses, checkpoint, maxJvmSteps, maxInternalSteps)
}

func (s *Session) vfs0aHarnessSlice(method string, gas, maxJvmSteps uint64, maxInternalSteps uint32, inputs ...interface{}) (Result, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var result Result
	if err := s.vfs0aHarnessUsable(); err != nil {
		return result, err
	}
	if gas == 0 || gas > 1_000_000_000 {
		return result, errors.New("vfs0a: gas must be in the frozen LOCAL range 1..1000000000")
	}
	callData, err := s.contractABI.Pack(method, inputs...)
	if err != nil {
		return result, fmt.Errorf("vfs0a: ABI-pack %s: %w", method, err)
	}
	oldRoot := s.stateRoot
	snapshot := s.stateDB.Snapshot()
	logCount := len(s.stateDB.Logs())
	output, left, callErr := evmruntime.Call(s.contract, callData, s.vfs0aHarnessRuntimeConfig(s.stateDB, gas))
	result.GasUsed = gas - left
	if callErr != nil {
		s.stateDB.RevertToSnapshot(snapshot)
		result.RevertData = append([]byte(nil), output...)
		return result, fmt.Errorf("vfs0a: EVM %s failed: %w (revert_data=0x%x)", method, callErr, output)
	}
	var checkpoint []byte
	if method == "start" {
		var decoded struct {
			Result     SliceResult
			Checkpoint []byte
		}
		if err := s.contractABI.UnpackIntoInterface(&decoded, method, output); err != nil {
			s.stateDB.RevertToSnapshot(snapshot)
			return result, fmt.Errorf("vfs0a: decode %s result: %w", method, err)
		}
		result.Slice, checkpoint = decoded.Result, decoded.Checkpoint
	} else {
		var decoded struct {
			Result          SliceResult
			ChildCheckpoint []byte
		}
		if err := s.contractABI.UnpackIntoInterface(&decoded, method, output); err != nil {
			s.stateDB.RevertToSnapshot(snapshot)
			return result, fmt.Errorf("vfs0a: decode %s result: %w", method, err)
		}
		result.Slice, checkpoint = decoded.Result, decoded.ChildCheckpoint
	}
	if err := vfs0aHarnessValidateSliceResult(result.Slice, maxJvmSteps, maxInternalSteps); err != nil {
		s.stateDB.RevertToSnapshot(snapshot)
		return Result{GasUsed: result.GasUsed}, err
	}
	result.Checkpoint = append([]byte(nil), checkpoint...)
	if len(result.Checkpoint) == 0 || len(result.Checkpoint) > vfs0aHarnessMaxCheckpointSize || crypto.Keccak256Hash(result.Checkpoint) != result.Slice.CheckpointRoot {
		s.stateDB.RevertToSnapshot(snapshot)
		return Result{GasUsed: result.GasUsed}, errors.New("vfs0a: EVM returned a missing, oversized, or root-mismatched checkpoint")
	}
	logs := s.stateDB.Logs()
	if logCount > len(logs) {
		s.stateDB.RevertToSnapshot(snapshot)
		return Result{GasUsed: result.GasUsed}, errors.New("vfs0a: StateDB log accounting moved backwards")
	}
	result.Logs = vfs0aHarnessCopyLogs(logs[logCount:])
	if err := s.vfs0aHarnessPersist(oldRoot, result.Slice.CheckpointRoot, result.Checkpoint); err != nil {
		// A rolled-back or ambiguously published call is not a committed slice.
		// Preserve diagnostic gas only; callers must consult the durable EVM head
		// after reopening, not use uncommitted child bytes or a success-shaped tuple.
		return Result{GasUsed: result.GasUsed}, err
	}
	return result, nil
}

func vfs0aHarnessValidateSliceResult(result SliceResult, maxJvmSteps uint64, maxInternalSteps uint32) error {
	if result.Schema != 1 || result.Epoch == 0 || result.CheckpointRoot == (common.Hash{}) || result.MachineStateRoot == (common.Hash{}) || len(result.JavaClass) > 65535 || result.VFSStateRoot == (common.Hash{}) || result.InodeCount < 3 || result.InodeCount > 64 || result.DescriptorCount > 32 || result.LogicalFileBytes > 65536 {
		return errors.New("vfs0a: EVM returned an invalid slice schema, roots, VFS counters, or oversized Java class name")
	}
	if result.ExecutedJvmSteps > maxJvmSteps || result.ExecutedInternalSteps > maxInternalSteps || result.ExecutedJvmSteps > result.TotalJvmSteps || uint64(result.ExecutedInternalSteps) > result.TotalInternalSteps {
		return errors.New("vfs0a: EVM returned counters outside the requested slice budget or cumulative totals")
	}
	switch result.Lifecycle {
	case 1: // RUNNABLE
		if result.Result != 0 || result.JavaKind != 0 || result.JavaRef != 0 || len(result.JavaClass) != 0 {
			return errors.New("vfs0a: EVM returned a noncanonical RUNNABLE outcome")
		}
	case 2: // RETURNED
		if result.JavaKind != 0 || result.JavaRef != 0 || len(result.JavaClass) != 0 {
			return errors.New("vfs0a: EVM returned a noncanonical RETURNED outcome")
		}
	case 3: // UNCAUGHT_JAVA
		if result.Result != 0 || result.JavaRef == 0 || result.JavaKind > 12 {
			return errors.New("vfs0a: EVM returned an invalid uncaught Java outcome")
		}
		if (result.JavaKind == 0) != (len(result.JavaClass) != 0) {
			return errors.New("vfs0a: EVM returned a noncanonical dynamic Java class name")
		}
	default:
		return errors.New("vfs0a: EVM returned an unknown lifecycle")
	}
	return nil
}

// Head calls the runtime's view method against an independent StateDB copy.
func (s *Session) Head(instance common.Hash) (Head, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var head Head
	if err := s.vfs0aHarnessUsable(); err != nil {
		return head, err
	}
	input, err := s.contractABI.Pack("head", instance)
	if err != nil {
		return head, fmt.Errorf("vfs0a: ABI-pack head: %w", err)
	}
	output, _, callErr := evmruntime.Call(s.contract, input, s.vfs0aHarnessRuntimeConfig(s.stateDB.Copy(), vfs0aHarnessHeadGas))
	if callErr != nil {
		return head, fmt.Errorf("vfs0a: EVM head failed: %w (revert_data=0x%x)", callErr, output)
	}
	if err := s.contractABI.UnpackIntoInterface(&head, "head", output); err != nil {
		return head, fmt.Errorf("vfs0a: decode head: %w", err)
	}
	if head.Epoch == 0 {
		if head != (Head{}) {
			return Head{}, errors.New("vfs0a: EVM returned a noncanonical absent head")
		}
	} else if head.Owner == (common.Address{}) || head.CheckpointRoot == (common.Hash{}) || head.MachineStateRoot == (common.Hash{}) || head.VFSStateRoot == (common.Hash{}) || head.SeedRoot == (common.Hash{}) || head.ArtifactRoot == (common.Hash{}) || head.ConfigRoot == (common.Hash{}) || head.RuntimeCodeHash == (common.Hash{}) || head.Lifecycle < 1 || head.Lifecycle > 3 {
		return Head{}, errors.New("vfs0a: EVM returned an invalid committed head")
	}
	return head, nil
}

// InspectFile asks the EVM to validate the complete opaque checkpoint and return
// a bounded filesystem view. It runs against an independent StateDB copy, cannot
// publish a head or move a descriptor, and grants no authority to Resume.
func (s *Session) InspectFile(rawClasses [][]byte, checkpoint, path []byte, offset, maxBytes uint32) (FileInspection, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var inspection FileInspection
	if err := s.vfs0aHarnessUsable(); err != nil {
		return inspection, err
	}
	input, err := s.contractABI.Pack("inspectFile", rawClasses, checkpoint, path, offset, maxBytes)
	if err != nil {
		return inspection, fmt.Errorf("vfs0a: ABI-pack inspectFile: %w", err)
	}
	output, _, callErr := evmruntime.Call(s.contract, input, s.vfs0aHarnessRuntimeConfig(s.stateDB.Copy(), vfs0aHarnessHeadGas))
	if callErr != nil {
		return inspection, fmt.Errorf("vfs0a: EVM inspectFile failed: %w (revert_data=0x%x)", callErr, output)
	}
	if err := s.contractABI.UnpackIntoInterface(&inspection, "inspectFile", output); err != nil {
		return inspection, fmt.Errorf("vfs0a: decode inspectFile: %w", err)
	}
	if len(inspection.Data) > 4096 || len(inspection.Data) > int(maxBytes) {
		return FileInspection{}, errors.New("vfs0a: EVM returned an oversized file inspection")
	}
	if inspection.Kind == 0 {
		if inspection.EffectiveReadOnly || inspection.Inode != 0 || len(inspection.Data) != 0 || inspection.FileRoot != (common.Hash{}) {
			return FileInspection{}, errors.New("vfs0a: EVM returned a noncanonical missing-file inspection")
		}
	} else if inspection.Kind > 2 || inspection.Inode == 0 || inspection.FileRoot == (common.Hash{}) || (inspection.Kind == 1 && len(inspection.Data) != 0) {
		return FileInspection{}, errors.New("vfs0a: EVM returned an invalid file inspection")
	}
	return inspection, nil
}

// ReadCheckpoint retrieves an exact EVM-returned checkpoint by its keccak root.
// The bytes are integrity checked but never parsed by production Go.
func (s *Session) ReadCheckpoint(root common.Hash) ([]byte, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if err := s.vfs0aHarnessUsable(); err != nil {
		return nil, err
	}
	if root == (common.Hash{}) {
		return nil, errors.New("vfs0a: zero checkpoint root")
	}
	var blob []byte
	var err error
	if s.directory == "" {
		blob = append([]byte(nil), s.blobs[root]...)
		if len(blob) == 0 {
			err = os.ErrNotExist
		}
	} else {
		blob, err = vfs0aHarnessReadRegular(s.vfs0aHarnessBlobPath(root), vfs0aHarnessMaxCheckpointSize)
	}
	if err != nil {
		return nil, fmt.Errorf("vfs0a: read checkpoint %s: %w", root, err)
	}
	if len(blob) == 0 || len(blob) > vfs0aHarnessMaxCheckpointSize || crypto.Keccak256Hash(blob) != root {
		return nil, fmt.Errorf("vfs0a: checkpoint %s failed size/hash integrity", root)
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

func (s *Session) vfs0aHarnessPersist(oldRoot, checkpointRoot common.Hash, checkpoint []byte) error {
	if s.directory == "" {
		s.blobs[checkpointRoot] = append([]byte(nil), checkpoint...)
		root, err := s.vfs0aHarnessCommitTrie()
		if err != nil {
			if reloadErr := s.vfs0aHarnessReload(oldRoot); reloadErr != nil {
				s.uncertain = fmt.Errorf("vfs0a: in-memory commit failed (%v) and old root reload failed: %w", err, reloadErr)
				return s.uncertain
			}
			return fmt.Errorf("vfs0a: commit StateDB: %w", err)
		}
		s.stateRoot = root
		if err := s.vfs0aHarnessReload(root); err != nil {
			s.uncertain = fmt.Errorf("vfs0a: committed in-memory state cannot be reloaded: %w", err)
			return s.uncertain
		}
		return nil
	}
	if err := s.vfs0aHarnessWriteBlob(checkpointRoot, checkpoint); err != nil {
		s.vfs0aHarnessRestoreOldRoot(oldRoot)
		return err
	}
	if err := s.vfs0aHarnessInject(vfs0aHarnessFaultAfterBlob); err != nil {
		s.vfs0aHarnessRestoreOldRoot(oldRoot)
		return fmt.Errorf("vfs0a: injected failure after durable checkpoint blob: %w", err)
	}
	root, err := s.vfs0aHarnessCommitTrie()
	if err != nil {
		s.vfs0aHarnessRestoreOldRoot(oldRoot)
		return fmt.Errorf("vfs0a: commit StateDB/trie: %w", err)
	}
	if err := s.vfs0aHarnessInject(vfs0aHarnessFaultAfterTrie); err != nil {
		s.vfs0aHarnessRestoreOldRoot(oldRoot)
		return fmt.Errorf("vfs0a: injected failure after trie commit: %w", err)
	}
	manifest := s.vfs0aHarnessManifest(root)
	published, err := s.vfs0aHarnessWriteManifest(manifest)
	if err != nil {
		if published {
			s.uncertain = fmt.Errorf("vfs0a: manifest publication fsync is ambiguous; close and reopen required: %w", err)
			return s.uncertain
		}
		s.vfs0aHarnessRestoreOldRoot(oldRoot)
		return fmt.Errorf("vfs0a: publish durable manifest: %w", err)
	}
	s.stateRoot = root
	if err := s.vfs0aHarnessReload(root); err != nil {
		s.uncertain = fmt.Errorf("vfs0a: published state cannot be reloaded; close and reopen required: %w", err)
		return s.uncertain
	}
	return nil
}

func (s *Session) vfs0aHarnessCommitTrie() (common.Hash, error) {
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

func (s *Session) vfs0aHarnessReload(root common.Hash) error {
	stateDB, err := state.New(root, state.NewDatabase(s.trieDB, nil))
	if err != nil {
		return err
	}
	s.stateDB = stateDB
	s.stateRoot = root
	return nil
}

func (s *Session) vfs0aHarnessRestoreOldRoot(root common.Hash) {
	if err := s.vfs0aHarnessReload(root); err != nil {
		s.uncertain = fmt.Errorf("vfs0a: failed to reload old durable root %s; close and reopen required: %w", root, err)
	}
}

func (s *Session) vfs0aHarnessRuntimeConfig(stateDB *state.StateDB, gas uint64) *evmruntime.Config {
	zeroHash := common.Hash{}
	return &evmruntime.Config{
		ChainConfig: params.AllDevChainProtocolChanges,
		Difficulty:  new(big.Int), Origin: s.owner, Coinbase: common.Address{}, BlockNumber: big.NewInt(1), Time: 1,
		GasLimit: gas, GasPrice: new(big.Int), Value: new(big.Int), BaseFee: new(big.Int).SetUint64(params.InitialBaseFee),
		BlobBaseFee: new(big.Int).SetUint64(params.BlobTxMinBlobGasprice), Random: &zeroHash, State: stateDB,
		GetHashFn: func(uint64) common.Hash { return common.Hash{} }, EVMConfig: vm.Config{},
	}
}

func (s *Session) vfs0aHarnessUsable() error {
	if s.closed {
		return errors.New("vfs0a: session is closed")
	}
	if s.uncertain != nil {
		return s.uncertain
	}
	return nil
}

func (s *Session) vfs0aHarnessManifest(root common.Hash) vfs0aHarnessManifest {
	return vfs0aHarnessManifest{Format: vfs0aHarnessStoreFormat, Owner: s.owner, Contract: s.contract, RuntimeCodeHash: s.codeHash, StateRoot: root, Context: vfs0aHarnessContextID}
}

func vfs0aHarnessPrepareDirectory(directory string) (bool, error) {
	info, err := os.Lstat(directory)
	if errors.Is(err, os.ErrNotExist) {
		if err := os.MkdirAll(directory, 0o700); err != nil {
			return false, fmt.Errorf("vfs0a: create store directory: %w", err)
		}
		return true, nil
	}
	if err != nil {
		return false, fmt.Errorf("vfs0a: inspect store directory: %w", err)
	}
	if !info.IsDir() {
		return false, errors.New("vfs0a: store path is not a directory")
	}
	entries, err := os.ReadDir(directory)
	if err != nil {
		return false, fmt.Errorf("vfs0a: list store directory: %w", err)
	}
	if len(entries) == 0 {
		return true, nil
	}
	allowed := map[string]bool{vfs0aHarnessStoreMarkerName: true, vfs0aHarnessManifestName: true, vfs0aHarnessStateDirectory: true, vfs0aHarnessBlobDirectory: true}
	for _, entry := range entries {
		info, err := entry.Info()
		if err != nil {
			return false, fmt.Errorf("vfs0a: inspect store entry: %w", err)
		}
		// A crash may leave our unpublished manifest temporary next to the old
		// durable manifest. Ignore (do not parse/delete) only regular owned temporaries.
		if strings.HasPrefix(entry.Name(), ".durable-head-") && info.Mode().IsRegular() {
			continue
		}
		if !allowed[entry.Name()] {
			return false, fmt.Errorf("vfs0a: refuse unrelated nonempty directory (unexpected %q)", entry.Name())
		}
		wantDir := entry.Name() == vfs0aHarnessStateDirectory || entry.Name() == vfs0aHarnessBlobDirectory
		if (wantDir && !info.IsDir()) || (!wantDir && !info.Mode().IsRegular()) {
			return false, fmt.Errorf("vfs0a: store entry %q has unsupported file type", entry.Name())
		}
	}
	if !vfs0aHarnessAllowedEntriesPresent(entries, vfs0aHarnessStoreMarkerName, vfs0aHarnessManifestName, vfs0aHarnessStateDirectory, vfs0aHarnessBlobDirectory) {
		return false, errors.New("vfs0a: incomplete nonempty VFS0a directory; refusing to overwrite")
	}
	return false, nil
}

func vfs0aHarnessAllowedEntriesPresent(entries []os.DirEntry, names ...string) bool {
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
func vfs0aHarnessReadRegular(path string, limit int64) ([]byte, error) {
	info, err := os.Lstat(path)
	if err != nil {
		return nil, err
	}
	if !info.Mode().IsRegular() || info.Size() < 0 || info.Size() > limit {
		return nil, fmt.Errorf("vfs0a: unsupported file type or oversized file at %s", path)
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
		return nil, fmt.Errorf("vfs0a: file changed while opening %s", path)
	}
	b, err := io.ReadAll(io.LimitReader(f, limit+1))
	if err != nil {
		return nil, err
	}
	if int64(len(b)) > limit {
		return nil, fmt.Errorf("vfs0a: file exceeded byte bound while reading %s", path)
	}
	return b, nil
}

func vfs0aHarnessReadManifest(path string) (vfs0aHarnessManifest, error) {
	var manifest vfs0aHarnessManifest
	raw, err := vfs0aHarnessReadRegular(path, 4096)
	if err != nil {
		return manifest, fmt.Errorf("vfs0a: read durable manifest: %w", err)
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&manifest); err != nil {
		return manifest, fmt.Errorf("vfs0a: decode durable manifest: %w", err)
	}
	var trailing interface{}
	if err := decoder.Decode(&trailing); !errors.Is(err, io.EOF) {
		if err == nil {
			return manifest, errors.New("vfs0a: trailing durable manifest data")
		}
		return manifest, fmt.Errorf("vfs0a: decode trailing durable manifest data: %w", err)
	}
	return manifest, nil
}

func (s *Session) vfs0aHarnessWriteManifest(manifest vfs0aHarnessManifest) (bool, error) {
	if err := s.vfs0aHarnessInject(vfs0aHarnessFaultBeforeManifest); err != nil {
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
	if err := os.Rename(tmpName, filepath.Join(s.directory, vfs0aHarnessManifestName)); err != nil {
		return false, err
	}
	if err := s.vfs0aHarnessInject(vfs0aHarnessFaultAfterManifestRename); err != nil {
		return true, err
	}
	if err := vfs0aHarnessSyncDirectory(s.directory); err != nil {
		return true, err
	}
	return true, nil
}

func (s *Session) vfs0aHarnessWriteBlob(root common.Hash, blob []byte) error {
	if crypto.Keccak256Hash(blob) != root {
		return errors.New("vfs0a: refusing checkpoint blob whose bytes do not match root")
	}
	path := s.vfs0aHarnessBlobPath(root)
	if existing, err := vfs0aHarnessReadRegular(path, vfs0aHarnessMaxCheckpointSize); err == nil {
		if !bytes.Equal(existing, blob) {
			return fmt.Errorf("vfs0a: existing checkpoint blob %s differs", root)
		}
		// An orphan's rename may have preceded a process stop before directory
		// fsync. Verify and durably sync it before publishing a head that uses it.
		if err := s.vfs0aHarnessInject(vfs0aHarnessFaultBeforeExistingBlobSync); err != nil {
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
		return vfs0aHarnessSyncDirectory(filepath.Dir(path))
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
	return vfs0aHarnessSyncDirectory(filepath.Dir(path))
}

func (s *Session) vfs0aHarnessBlobPath(root common.Hash) string {
	return filepath.Join(s.directory, vfs0aHarnessBlobDirectory, root.Hex()[2:]+".checkpoint")
}

func (s *Session) vfs0aHarnessInject(point vfs0aHarnessFaultPoint) error {
	if s.testFault != nil {
		return s.testFault(point)
	}
	return nil
}

func vfs0aHarnessSyncDirectory(path string) error {
	dir, err := os.Open(path)
	if err != nil {
		return err
	}
	defer dir.Close()
	return dir.Sync()
}

func vfs0aHarnessCopyLogs(logs []*types.Log) []*types.Log {
	out := make([]*types.Log, len(logs))
	for i, log := range logs {
		copyLog := *log
		copyLog.Topics = append([]common.Hash(nil), log.Topics...)
		copyLog.Data = append([]byte(nil), log.Data...)
		out[i] = &copyLog
	}
	return out
}
