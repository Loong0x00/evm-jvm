// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.
//
// This program is free software: you can redistribute it and/or modify it under
// the terms of the GNU Lesser General Public License as published by the Free
// Software Foundation, either version 3 of the License, or (at your option) any
// later version.

// Package sc0 provides the LOCAL MC-SC0 EVM continuation transport. It treats
// classfiles, dynamic Java class-name bytes, and checkpoints as opaque bytes:
// Java parsing, execution, checkpoint validation, and head updates are performed
// by the pinned SC0 EVM runtime.
package sc0

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
	sc0assets "github.com/ethereum/go-ethereum/jvmevm/runtime/local/sc0"
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
	JavaClass             []byte
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
	sc0HarnessLoadOnce sync.Once
	sc0HarnessCode     []byte
	sc0HarnessABIRaw   []byte
	sc0HarnessABI      abi.ABI
	sc0HarnessLoadErr  error
)

func sc0HarnessLoad() ([]byte, abi.ABI, error) {
	sc0HarnessLoadOnce.Do(func() {
		var doc struct {
			ContractName     string          `json:"contractName"`
			ABI              json.RawMessage `json:"abi"`
			DeployedBytecode string          `json:"deployedBytecode"`
		}
		if err := json.Unmarshal(sc0assets.Artifact(), &doc); err != nil {
			sc0HarnessLoadErr = fmt.Errorf("sc0: decode embedded runtime artifact: %w", err)
			return
		}
		if doc.ContractName != "String0Interpreter" {
			sc0HarnessLoadErr = fmt.Errorf("sc0: unexpected embedded contract %q", doc.ContractName)
			return
		}
		encodedRuntime, rawABI := []byte(doc.DeployedBytecode), doc.ABI
		var err error
		if len(bytes.TrimSpace(rawABI)) == 0 || bytes.Equal(bytes.TrimSpace(rawABI), []byte("null")) {
			sc0HarnessLoadErr = fmt.Errorf("sc0: pinned ABI artifact is empty")
			return
		}
		sc0HarnessABIRaw = append([]byte(nil), rawABI...)
		sc0HarnessABI, err = abi.JSON(bytes.NewReader(sc0HarnessABIRaw))
		if err != nil {
			sc0HarnessLoadErr = fmt.Errorf("sc0: parse pinned ABI: %w", err)
			return
		}
		if err := sc0HarnessValidateABI(sc0HarnessABI); err != nil {
			sc0HarnessLoadErr = err
			return
		}
		encoded := strings.TrimPrefix(strings.TrimSpace(string(encodedRuntime)), "0x")
		if encoded == "" || len(encoded)%2 != 0 {
			sc0HarnessLoadErr = fmt.Errorf("sc0: pinned runtime artifact is empty or odd-length")
			return
		}
		sc0HarnessCode, err = hex.DecodeString(encoded)
		if err != nil {
			sc0HarnessLoadErr = fmt.Errorf("sc0: decode pinned runtime artifact: %w", err)
			return
		}
		if len(sc0HarnessCode) == 0 || len(sc0HarnessCode) > 256*1024 {
			sc0HarnessLoadErr = fmt.Errorf("sc0: runtime size %d is outside LOCAL range 1..262144", len(sc0HarnessCode))
		}
	})
	return sc0HarnessCode, sc0HarnessABI, sc0HarnessLoadErr
}

func sc0HarnessValidateABI(contract abi.ABI) error {
	tuple := "(uint32,uint8,uint64,bytes32,bytes32,uint64,uint64,uint64,uint32,int32,uint8,uint32,bytes)"
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
		return fmt.Errorf("sc0: pinned ABI has %d methods, want exactly %d", len(contract.Methods), len(want))
	}
	for name, shape := range want {
		method, ok := contract.Methods[name]
		if !ok || method.RawName != name || method.Sig != shape.signature || method.StateMutability != shape.mutability || len(method.Inputs) != len(shape.inputNames) || len(method.Outputs) != len(shape.outputs) {
			return fmt.Errorf("sc0: pinned ABI method %s has an unexpected shape", name)
		}
		for i, input := range method.Inputs {
			if input.Name != shape.inputNames[i] {
				return fmt.Errorf("sc0: pinned ABI method %s input %d is named %q, want %q", name, i, input.Name, shape.inputNames[i])
			}
		}
		for i, output := range method.Outputs {
			if output.Name != shape.outputNames[i] || output.Type.String() != shape.outputs[i] {
				return fmt.Errorf("sc0: pinned ABI method %s output %d differs from frozen ABI", name, i)
			}
		}
	}
	components := []string{"schema", "lifecycle", "epoch", "checkpointRoot", "machineStateRoot", "totalJvmSteps", "totalInternalSteps", "executedJvmSteps", "executedInternalSteps", "result", "javaKind", "javaRef", "javaClass"}
	for _, name := range []string{"start", "resume"} {
		if got := contract.Methods[name].Outputs[0].Type.TupleRawNames; len(got) != len(components) {
			return fmt.Errorf("sc0: pinned ABI method %s SliceResult has %d fields", name, len(got))
		} else {
			for i := range got {
				if got[i] != components[i] {
					return fmt.Errorf("sc0: pinned ABI method %s SliceResult field %d is %q, want %q", name, i, got[i], components[i])
				}
			}
		}
	}
	event, ok := contract.Events["CheckpointCommitted"]
	if !ok || len(contract.Events) != 1 || event.Sig != "CheckpointCommitted(bytes32,uint64,bytes32,bytes32,uint8,uint64,uint64)" || len(event.Inputs) != 7 {
		return fmt.Errorf("sc0: pinned ABI must contain exactly the frozen CheckpointCommitted event")
	}
	for i, input := range event.Inputs {
		if input.Indexed != (i < 2) {
			return fmt.Errorf("sc0: CheckpointCommitted indexed fields differ from frozen ABI")
		}
	}
	return nil
}

// Runtime returns a defensive copy of the pinned SC0 deployed runtime. It never
// falls back to the accepted legacy monolith or synthesizes runtime bytecode.
func Runtime() ([]byte, error) {
	code, _, err := sc0HarnessLoad()
	if err != nil {
		return nil, err
	}
	return append([]byte(nil), code...), nil
}

// RuntimeHash returns the lowercase SHA-256 of Runtime.
func RuntimeHash() (string, error) {
	code, _, err := sc0HarnessLoad()
	if err != nil {
		return "", err
	}
	hash := sha256.Sum256(code)
	return hex.EncodeToString(hash[:]), nil
}

// ABI returns an independently parsed copy of the pinned SC0 contract ABI.
func ABI() (abi.ABI, error) {
	if _, _, err := sc0HarnessLoad(); err != nil {
		return abi.ABI{}, err
	}
	contract, err := abi.JSON(bytes.NewReader(sc0HarnessABIRaw))
	if err != nil {
		return abi.ABI{}, fmt.Errorf("sc0: copy pinned ABI: %w", err)
	}
	return contract, nil
}
