// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.
//
// This program is free software: you can redistribute it and/or modify it under
// the terms of the GNU Lesser General Public License as published by the Free
// Software Foundation, either version 3 of the License, or (at your option) any
// later version.

// Package lc0 provides the LOCAL MC-LC0 EVM continuation transport. It treats
// classfiles and checkpoints as opaque bytes: Java parsing, execution, checkpoint
// validation, and head updates are performed by the pinned LC0 EVM runtime.
package lc0

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
	lc0assets "github.com/ethereum/go-ethereum/jvmevm/runtime/local/lc0"
)

// Runtime assets are embedded at build time. No source-tree path, current working
// directory, external compiler, or guest-state metadata is used by the loader.
type SliceResult struct {
	Schema                uint32
	Lifecycle             uint8
	Epoch                 uint64
	CheckpointRoot        common.Hash
	MachineStateRoot      common.Hash
	TotalJvmSteps         uint64
	TotalInternalSteps    uint64
	ExecutedJvmSteps      uint64
	ExecutedInternalSteps uint32
	Result                int32
	JavaKind              uint8
	JavaRef               uint32
}

type Head struct {
	Owner            common.Address
	Epoch            uint64
	CheckpointRoot   common.Hash
	MachineStateRoot common.Hash
	ArtifactRoot     common.Hash
	ConfigRoot       common.Hash
	RuntimeCodeHash  common.Hash
	Lifecycle        uint8
}

type Result struct {
	Slice      SliceResult
	Checkpoint []byte
	GasUsed    uint64
	RevertData []byte
	Logs       []*types.Log
}

var (
	lc0HarnessLoadOnce sync.Once
	lc0HarnessCode     []byte
	lc0HarnessABIRaw   []byte
	lc0HarnessABI      abi.ABI
	lc0HarnessLoadErr  error
)

func lc0HarnessLoad() ([]byte, abi.ABI, error) {
	lc0HarnessLoadOnce.Do(func() {
		var doc struct {
			ContractName     string          `json:"contractName"`
			ABI              json.RawMessage `json:"abi"`
			DeployedBytecode string          `json:"deployedBytecode"`
		}
		if err := json.Unmarshal(lc0assets.Artifact(), &doc); err != nil {
			lc0HarnessLoadErr = fmt.Errorf("lc0: decode embedded runtime artifact: %w", err)
			return
		}
		if doc.ContractName != "LC0Interpreter" {
			lc0HarnessLoadErr = fmt.Errorf("lc0: unexpected embedded contract %q", doc.ContractName)
			return
		}
		encodedRuntime, rawABI := []byte(doc.DeployedBytecode), doc.ABI
		var err error
		if len(bytes.TrimSpace(rawABI)) == 0 || bytes.Equal(bytes.TrimSpace(rawABI), []byte("null")) {
			lc0HarnessLoadErr = fmt.Errorf("lc0: pinned ABI artifact is empty")
			return
		}
		lc0HarnessABIRaw = append([]byte(nil), rawABI...)
		lc0HarnessABI, err = abi.JSON(bytes.NewReader(lc0HarnessABIRaw))
		if err != nil {
			lc0HarnessLoadErr = fmt.Errorf("lc0: parse pinned ABI: %w", err)
			return
		}
		if err := lc0HarnessValidateABI(lc0HarnessABI); err != nil {
			lc0HarnessLoadErr = err
			return
		}
		encoded := strings.TrimPrefix(strings.TrimSpace(string(encodedRuntime)), "0x")
		if encoded == "" || len(encoded)%2 != 0 {
			lc0HarnessLoadErr = fmt.Errorf("lc0: pinned runtime artifact is empty or odd-length")
			return
		}
		lc0HarnessCode, err = hex.DecodeString(encoded)
		if err != nil {
			lc0HarnessLoadErr = fmt.Errorf("lc0: decode pinned runtime artifact: %w", err)
			return
		}
		if len(lc0HarnessCode) == 0 || len(lc0HarnessCode) > 256*1024 {
			lc0HarnessLoadErr = fmt.Errorf("lc0: runtime size %d is outside LOCAL range 1..262144", len(lc0HarnessCode))
		}
	})
	return lc0HarnessCode, lc0HarnessABI, lc0HarnessLoadErr
}

func lc0HarnessValidateABI(contract abi.ABI) error {
	tuple := "(uint32,uint8,uint64,bytes32,bytes32,uint64,uint64,uint64,uint32,int32,uint8,uint32)"
	want := map[string]struct {
		signature, mutability string
		inputNames, outputs   []string
		outputNames           []string
	}{
		"start": {
			"start(bytes32,bytes[],string,string,int32[],uint64,uint32)", "nonpayable",
			[]string{"instanceId", "rawClasses", "entryClass", "entry", "args", "maxJvmSteps", "maxInternalSteps"},
			[]string{tuple, "bytes"}, []string{"result", "checkpoint"},
		},
		"resume": {
			"resume(bytes32,uint64,bytes32,bytes[],bytes,uint64,uint32)", "nonpayable",
			[]string{"instanceId", "expectedEpoch", "expectedCheckpointRoot", "rawClasses", "checkpoint", "maxJvmSteps", "maxInternalSteps"},
			[]string{tuple, "bytes"}, []string{"result", "childCheckpoint"},
		},
		"head": {
			"head(bytes32)", "view", []string{"instanceId"},
			[]string{"address", "uint64", "bytes32", "bytes32", "bytes32", "bytes32", "bytes32", "uint8"},
			[]string{"owner", "epoch", "checkpointRoot", "machineStateRoot", "artifactRoot", "configRoot", "runtimeCodeHash", "lifecycle"},
		},
		"validateCheckpoint": {
			"validateCheckpoint(bytes[],bytes)", "view", []string{"rawClasses", "checkpoint"},
			[]string{"bytes32"}, []string{"machineStateRoot"},
		},
	}
	if len(contract.Methods) != len(want) {
		return fmt.Errorf("lc0: pinned ABI has %d methods, want exactly %d", len(contract.Methods), len(want))
	}
	for name, shape := range want {
		method, ok := contract.Methods[name]
		if !ok || method.RawName != name || method.Sig != shape.signature || method.StateMutability != shape.mutability || len(method.Inputs) != len(shape.inputNames) || len(method.Outputs) != len(shape.outputs) {
			return fmt.Errorf("lc0: pinned ABI method %s has an unexpected shape", name)
		}
		for i, input := range method.Inputs {
			if input.Name != shape.inputNames[i] {
				return fmt.Errorf("lc0: pinned ABI method %s input %d is named %q, want %q", name, i, input.Name, shape.inputNames[i])
			}
		}
		for i, output := range method.Outputs {
			if output.Name != shape.outputNames[i] || output.Type.String() != shape.outputs[i] {
				return fmt.Errorf("lc0: pinned ABI method %s output %d differs from frozen ABI", name, i)
			}
		}
	}
	components := []string{"schema", "lifecycle", "epoch", "checkpointRoot", "machineStateRoot", "totalJvmSteps", "totalInternalSteps", "executedJvmSteps", "executedInternalSteps", "result", "javaKind", "javaRef"}
	for _, name := range []string{"start", "resume"} {
		if got := contract.Methods[name].Outputs[0].Type.TupleRawNames; len(got) != len(components) {
			return fmt.Errorf("lc0: pinned ABI method %s SliceResult has %d fields", name, len(got))
		} else {
			for i := range got {
				if got[i] != components[i] {
					return fmt.Errorf("lc0: pinned ABI method %s SliceResult field %d is %q, want %q", name, i, got[i], components[i])
				}
			}
		}
	}
	event, ok := contract.Events["CheckpointCommitted"]
	if !ok || len(contract.Events) != 1 || event.Sig != "CheckpointCommitted(bytes32,uint64,bytes32,bytes32,uint8,uint64,uint64)" || len(event.Inputs) != 7 {
		return fmt.Errorf("lc0: pinned ABI must contain exactly the frozen CheckpointCommitted event")
	}
	for i, input := range event.Inputs {
		if input.Indexed != (i < 2) {
			return fmt.Errorf("lc0: CheckpointCommitted indexed fields differ from frozen ABI")
		}
	}
	return nil
}

// Runtime returns a defensive copy of the pinned LC0 deployed runtime. It never
// falls back to the accepted legacy monolith or synthesizes runtime bytecode.
func Runtime() ([]byte, error) {
	code, _, err := lc0HarnessLoad()
	if err != nil {
		return nil, err
	}
	return append([]byte(nil), code...), nil
}

// RuntimeHash returns the lowercase SHA-256 of Runtime.
func RuntimeHash() (string, error) {
	code, _, err := lc0HarnessLoad()
	if err != nil {
		return "", err
	}
	hash := sha256.Sum256(code)
	return hex.EncodeToString(hash[:]), nil
}

// ABI returns an independently parsed copy of the pinned LC0 contract ABI.
func ABI() (abi.ABI, error) {
	if _, _, err := lc0HarnessLoad(); err != nil {
		return abi.ABI{}, err
	}
	contract, err := abi.JSON(bytes.NewReader(lc0HarnessABIRaw))
	if err != nil {
		return abi.ABI{}, fmt.Errorf("lc0: copy pinned ABI: %w", err)
	}
	return contract, nil
}
