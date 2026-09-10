// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.
//
// This program is free software: you can redistribute it and/or modify it under
// the terms of the GNU Lesser General Public License as published by the Free
// Software Foundation, either version 3 of the License, or (at your option) any
// later version.

// Package vfs0a provides the LOCAL MC-VFS0a EVM continuation transport. It
// treats classfiles, seed paths/data, dynamic Java class-name bytes, checkpoints,
// and inspected file data as opaque bytes. Java and filesystem semantics,
// checkpoint validation, and head updates are performed by the pinned EVM runtime.
package vfs0a

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"strings"
	"sync"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	vfs0aassets "github.com/ethereum/go-ethereum/jvmevm/runtime/local/vfs0a"
)

// Runtime assets are embedded at build time. No source-tree path, current working
// directory, external compiler, or guest-state metadata is used by the loader.
// SeedFile is ABI transport data only. Go does not normalize or interpret Path
// or Data, and ReadOnly is passed unchanged to the EVM start call.
type SeedFile struct {
	Path     []byte `abi:"path"`
	Data     []byte `abi:"data"`
	ReadOnly bool   `abi:"readOnly"`
}

type SliceResult struct {
	Schema                uint32      `abi:"schema"`
	Lifecycle             uint8       `abi:"lifecycle"`
	Epoch                 uint64      `abi:"epoch"`
	CheckpointRoot        common.Hash `abi:"checkpointRoot"`
	MachineStateRoot      common.Hash `abi:"machineStateRoot"`
	TotalJvmSteps         uint64      `abi:"totalJvmSteps"`
	TotalInternalSteps    uint64      `abi:"totalInternalSteps"`
	ExecutedJvmSteps      uint64      `abi:"executedJvmSteps"`
	ExecutedInternalSteps uint32      `abi:"executedInternalSteps"`
	Result                int32       `abi:"result"`
	JavaKind              uint8       `abi:"javaKind"`
	JavaRef               uint32      `abi:"javaRef"`
	JavaClass             []byte      `abi:"javaClass"`
	VFSStateRoot          common.Hash `abi:"vfsStateRoot"`
	InodeCount            uint32      `abi:"inodeCount"`
	DescriptorCount       uint32      `abi:"descriptorCount"`
	LogicalFileBytes      uint64      `abi:"logicalFileBytes"`
}

type Head struct {
	Owner            common.Address `abi:"owner"`
	Epoch            uint64         `abi:"epoch"`
	CheckpointRoot   common.Hash    `abi:"checkpointRoot"`
	MachineStateRoot common.Hash    `abi:"machineStateRoot"`
	VFSStateRoot     common.Hash    `abi:"vfsStateRoot"`
	SeedRoot         common.Hash    `abi:"seedRoot"`
	ArtifactRoot     common.Hash    `abi:"artifactRoot"`
	ConfigRoot       common.Hash    `abi:"configRoot"`
	RuntimeCodeHash  common.Hash    `abi:"runtimeCodeHash"`
	Lifecycle        uint8          `abi:"lifecycle"`
}

// FileInspection is returned by the runtime's read-only full-checkpoint view.
type FileInspection struct {
	Kind              uint8       `abi:"kind"`
	EffectiveReadOnly bool        `abi:"effectiveReadOnly"`
	Inode             uint32      `abi:"inode"`
	Data              []byte      `abi:"data"`
	FileRoot          common.Hash `abi:"fileRoot"`
}

type Result struct {
	Slice      SliceResult
	Checkpoint []byte
	GasUsed    uint64
	RevertData []byte
	Logs       []*types.Log
}

var (
	vfs0aHarnessLoadOnce sync.Once
	vfs0aHarnessCode     []byte
	vfs0aHarnessABIRaw   []byte
	vfs0aHarnessABI      abi.ABI
	vfs0aHarnessLoadErr  error
)

func vfs0aHarnessLoad() ([]byte, abi.ABI, error) {
	vfs0aHarnessLoadOnce.Do(func() {
		var doc struct {
			ContractName     string          `json:"contractName"`
			ABI              json.RawMessage `json:"abi"`
			DeployedBytecode string          `json:"deployedBytecode"`
		}
		if err := json.Unmarshal(vfs0aassets.Artifact(), &doc); err != nil {
			vfs0aHarnessLoadErr = fmt.Errorf("vfs0a: decode embedded runtime artifact: %w", err)
			return
		}
		if doc.ContractName != "VFS0aInterpreter" {
			vfs0aHarnessLoadErr = fmt.Errorf("vfs0a: unexpected embedded contract %q", doc.ContractName)
			return
		}
		encodedRuntime, rawABI := []byte(doc.DeployedBytecode), doc.ABI
		var err error
		if len(bytes.TrimSpace(rawABI)) == 0 || bytes.Equal(bytes.TrimSpace(rawABI), []byte("null")) {
			vfs0aHarnessLoadErr = fmt.Errorf("vfs0a: pinned ABI artifact is empty")
			return
		}
		vfs0aHarnessABIRaw = append([]byte(nil), rawABI...)
		vfs0aHarnessABI, err = abi.JSON(bytes.NewReader(vfs0aHarnessABIRaw))
		if err != nil {
			vfs0aHarnessLoadErr = fmt.Errorf("vfs0a: parse pinned ABI: %w", err)
			return
		}
		if err := vfs0aHarnessValidateABI(vfs0aHarnessABI); err != nil {
			vfs0aHarnessLoadErr = err
			return
		}
		encoded := strings.TrimPrefix(strings.TrimSpace(string(encodedRuntime)), "0x")
		if encoded == "" || len(encoded)%2 != 0 {
			vfs0aHarnessLoadErr = fmt.Errorf("vfs0a: pinned runtime artifact is empty or odd-length")
			return
		}
		vfs0aHarnessCode, err = hex.DecodeString(encoded)
		if err != nil {
			vfs0aHarnessLoadErr = fmt.Errorf("vfs0a: decode pinned runtime artifact: %w", err)
			return
		}
		if len(vfs0aHarnessCode) == 0 || len(vfs0aHarnessCode) > 320*1024 {
			vfs0aHarnessLoadErr = fmt.Errorf("vfs0a: runtime size %d is outside LOCAL range 1..327680", len(vfs0aHarnessCode))
		}
	})
	return vfs0aHarnessCode, vfs0aHarnessABI, vfs0aHarnessLoadErr
}

func vfs0aHarnessValidateABI(contract abi.ABI) error {
	tuple := "(uint32,uint8,uint64,bytes32,bytes32,uint64,uint64,uint64,uint32,int32,uint8,uint32,bytes,bytes32,uint32,uint32,uint64)"
	want := map[string]struct {
		signature, mutability string
		inputNames, outputs   []string
		outputNames           []string
	}{
		"start": {
			"start(bytes32,bytes[],string,string,int32[],(bytes,bytes,bool)[],uint64,uint32)", "nonpayable",
			[]string{"instanceId", "rawClasses", "entryClass", "entry", "args", "seeds", "maxJvmSteps", "maxInternalSteps"},
			[]string{tuple, "bytes"}, []string{"result", "checkpoint"},
		},
		"resume": {
			"resume(bytes32,uint64,bytes32,bytes[],bytes,uint64,uint32)", "nonpayable",
			[]string{"instanceId", "expectedEpoch", "expectedCheckpointRoot", "rawClasses", "checkpoint", "maxJvmSteps", "maxInternalSteps"},
			[]string{tuple, "bytes"}, []string{"result", "childCheckpoint"},
		},
		"head": {
			"head(bytes32)", "view", []string{"instanceId"},
			[]string{"address", "uint64", "bytes32", "bytes32", "bytes32", "bytes32", "bytes32", "bytes32", "bytes32", "uint8"},
			[]string{"owner", "epoch", "checkpointRoot", "machineStateRoot", "vfsStateRoot", "seedRoot", "artifactRoot", "configRoot", "runtimeCodeHash", "lifecycle"},
		},
		"validateCheckpoint": {
			"validateCheckpoint(bytes[],bytes)", "view", []string{"rawClasses", "checkpoint"},
			[]string{"bytes32", "bytes32"}, []string{"machineStateRoot", "vfsStateRoot"},
		},
		"inspectFile": {
			"inspectFile(bytes[],bytes,bytes,uint32,uint32)", "view",
			[]string{"rawClasses", "checkpoint", "path", "offset", "maxBytes"},
			[]string{"uint8", "bool", "uint32", "bytes", "bytes32"},
			[]string{"kind", "effectiveReadOnly", "inode", "data", "fileRoot"},
		},
	}
	if len(contract.Methods) != len(want) {
		return fmt.Errorf("vfs0a: pinned ABI has %d methods, want exactly %d", len(contract.Methods), len(want))
	}
	for name, shape := range want {
		method, ok := contract.Methods[name]
		if !ok || method.RawName != name || method.Sig != shape.signature || method.StateMutability != shape.mutability || len(method.Inputs) != len(shape.inputNames) || len(method.Outputs) != len(shape.outputs) {
			return fmt.Errorf("vfs0a: pinned ABI method %s has an unexpected shape", name)
		}
		for i, input := range method.Inputs {
			if input.Name != shape.inputNames[i] {
				return fmt.Errorf("vfs0a: pinned ABI method %s input %d is named %q, want %q", name, i, input.Name, shape.inputNames[i])
			}
		}
		for i, output := range method.Outputs {
			if output.Name != shape.outputNames[i] || output.Type.String() != shape.outputs[i] {
				return fmt.Errorf("vfs0a: pinned ABI method %s output %d differs from frozen ABI", name, i)
			}
		}
	}
	seedType := contract.Methods["start"].Inputs[5].Type
	if seedType.Elem == nil {
		return fmt.Errorf("vfs0a: pinned ABI SeedFile is not a tuple array")
	}
	seedComponents := seedType.Elem.TupleRawNames
	if !equalVFS0aABINames(seedComponents, []string{"path", "data", "readOnly"}) {
		return fmt.Errorf("vfs0a: pinned ABI SeedFile fields differ from frozen ABI")
	}
	components := []string{"schema", "lifecycle", "epoch", "checkpointRoot", "machineStateRoot", "totalJvmSteps", "totalInternalSteps", "executedJvmSteps", "executedInternalSteps", "result", "javaKind", "javaRef", "javaClass", "vfsStateRoot", "inodeCount", "descriptorCount", "logicalFileBytes"}
	for _, name := range []string{"start", "resume"} {
		if got := contract.Methods[name].Outputs[0].Type.TupleRawNames; len(got) != len(components) {
			return fmt.Errorf("vfs0a: pinned ABI method %s SliceResult has %d fields", name, len(got))
		} else {
			for i := range got {
				if got[i] != components[i] {
					return fmt.Errorf("vfs0a: pinned ABI method %s SliceResult field %d is %q, want %q", name, i, got[i], components[i])
				}
			}
		}
	}
	event, ok := contract.Events["CheckpointCommitted"]
	eventNames := []string{"instanceId", "epoch", "checkpointRoot", "machineStateRoot", "vfsStateRoot", "lifecycle", "totalJvmSteps", "totalInternalSteps"}
	if !ok || len(contract.Events) != 1 || event.Sig != "CheckpointCommitted(bytes32,uint64,bytes32,bytes32,bytes32,uint8,uint64,uint64)" || len(event.Inputs) != len(eventNames) {
		return fmt.Errorf("vfs0a: pinned ABI must contain exactly the frozen CheckpointCommitted event")
	}
	for i, input := range event.Inputs {
		if input.Name != eventNames[i] || input.Indexed != (i < 2) {
			return fmt.Errorf("vfs0a: CheckpointCommitted fields differ from frozen ABI")
		}
	}
	return nil
}

func equalVFS0aABINames(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

// Runtime returns a defensive copy of the pinned VFS0a deployed runtime. It never
// falls back to the accepted legacy monolith or synthesizes runtime bytecode.
func Runtime() ([]byte, error) {
	code, _, err := vfs0aHarnessLoad()
	if err != nil {
		return nil, err
	}
	return append([]byte(nil), code...), nil
}

// RuntimeHash returns the lowercase SHA-256 of Runtime.
func RuntimeHash() (string, error) {
	code, _, err := vfs0aHarnessLoad()
	if err != nil {
		return "", err
	}
	hash := sha256.Sum256(code)
	return hex.EncodeToString(hash[:]), nil
}

// ABI returns an independently parsed copy of the pinned VFS0a contract ABI.
func ABI() (abi.ABI, error) {
	if _, _, err := vfs0aHarnessLoad(); err != nil {
		return abi.ABI{}, err
	}
	contract, err := abi.JSON(bytes.NewReader(vfs0aHarnessABIRaw))
	if err != nil {
		return abi.ABI{}, fmt.Errorf("vfs0a: copy pinned ABI: %w", err)
	}
	return contract, nil
}
