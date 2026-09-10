// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.
//
// This program is free software: you can redistribute it and/or modify it under
// the terms of the GNU Lesser General Public License as published by the Free
// Software Foundation, either version 3 of the License, or (at your option) any
// later version.

// Package as0 is the opaque Go transport for the frozen MC-AS0 immutable EVM
// artifact store. Go only ABI-packs opaque bytes and transports committed EVM
// state. It does not parse ZIP, classify resources, install child page code, or
// make content decisions on behalf of the EVM controller.
package as0

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"strings"
	"sync"

	"github.com/ethereum/go-ethereum/accounts/abi"
	as0runtime "github.com/ethereum/go-ethereum/jvmevm/artifactstore/as0/runtime"
)

const (
	PageSize  = uint32(8192)
	MaxPages  = uint32(4096)
	MaxLength = uint32(33554432)
	MaxRead   = uint32(4096)
	MaxGas    = uint64(1_000_000_000)
)

type artifactJSON struct {
	ContractName     string          `json:"contractName"`
	ABI              json.RawMessage `json:"abi"`
	Bytecode         string          `json:"bytecode"`
	DeployedBytecode string          `json:"deployedBytecode"`
}

var (
	loadOnce sync.Once
	loadABI  abi.ABI
	loadRaw  []byte
	loadInit []byte
	loadRun  []byte
	loadErr  error
)

func loadArtifact() {
	loadOnce.Do(func() {
		var doc artifactJSON
		if err := json.Unmarshal(as0runtime.Artifact(), &doc); err != nil {
			loadErr = fmt.Errorf("as0: decode embedded artifact: %w", err)
			return
		}
		if doc.ContractName != "AS0ArtifactStore" {
			loadErr = fmt.Errorf("as0: unexpected embedded contract %q", doc.ContractName)
			return
		}
		if len(bytes.TrimSpace(doc.ABI)) == 0 || bytes.Equal(bytes.TrimSpace(doc.ABI), []byte("null")) {
			loadErr = fmt.Errorf("as0: embedded ABI is empty")
			return
		}
		contractABI, err := abi.JSON(bytes.NewReader(doc.ABI))
		if err != nil {
			loadErr = fmt.Errorf("as0: parse embedded ABI: %w", err)
			return
		}
		if err := validateABI(contractABI); err != nil {
			loadErr = err
			return
		}
		initCode, err := decodeCode("init", doc.Bytecode)
		if err != nil {
			loadErr = err
			return
		}
		runtimeCode, err := decodeCode("runtime", doc.DeployedBytecode)
		if err != nil {
			loadErr = err
			return
		}
		if len(initCode) > 49152 {
			loadErr = fmt.Errorf("as0: init code is %d bytes (frozen limit 49152)", len(initCode))
			return
		}
		if len(runtimeCode) > 24576 {
			loadErr = fmt.Errorf("as0: runtime is %d bytes (frozen limit 24576)", len(runtimeCode))
			return
		}
		loadABI, loadRaw = contractABI, append([]byte(nil), doc.ABI...)
		loadInit, loadRun = initCode, runtimeCode
	})
}

func decodeCode(label, encoded string) ([]byte, error) {
	encoded = strings.TrimPrefix(strings.TrimSpace(encoded), "0x")
	if encoded == "" || len(encoded)%2 != 0 {
		return nil, fmt.Errorf("as0: embedded %s code is empty or odd-length", label)
	}
	code, err := hex.DecodeString(encoded)
	if err != nil {
		return nil, fmt.Errorf("as0: decode embedded %s code: %w", label, err)
	}
	return code, nil
}

func validateABI(contract abi.ABI) error {
	if contract.HasFallback() || contract.HasReceive() {
		return fmt.Errorf("as0: frozen ABI has no fallback or receive")
	}
	type methodShape struct {
		sig, mutability                          string
		inputs, inputNames, outputs, outputNames []string
	}
	want := map[string]methodShape{
		"append":            {"append(uint32,bytes,bytes32)", "nonpayable", []string{"uint32", "bytes", "bytes32"}, []string{"expectedCursor", "raw", "expectedPageCommitment"}, nil, nil},
		"seal":              {"seal(uint32,bytes32)", "nonpayable", []string{"uint32", "bytes32"}, []string{"expectedCursor", "expectedChain"}, nil, nil},
		"read":              {"read(uint32,uint32)", "view", []string{"uint32", "uint32"}, []string{"offset", "length"}, []string{"bytes"}, []string{"out"}},
		"pageCount":         {"pageCount()", "view", nil, nil, []string{"uint256"}, []string{""}},
		"page":              {"page(uint256)", "view", []string{"uint256"}, []string{"index"}, []string{"address", "bytes32", "bytes32"}, []string{"", "", ""}},
		"owner":             {"owner()", "view", nil, nil, []string{"address"}, []string{""}},
		"declaredLength":    {"declaredLength()", "view", nil, nil, []string{"uint32"}, []string{""}},
		"cursor":            {"cursor()", "view", nil, nil, []string{"uint32"}, []string{""}},
		"isSealed":          {"isSealed()", "view", nil, nil, []string{"bool"}, []string{""}},
		"chainCommitment":   {"chainCommitment()", "view", nil, nil, []string{"bytes32"}, []string{""}},
		"contentCommitment": {"contentCommitment()", "view", nil, nil, []string{"bytes32"}, []string{""}},
		"PAGE_SIZE":         {"PAGE_SIZE()", "view", nil, nil, []string{"uint32"}, []string{""}},
		"MAX_PAGES":         {"MAX_PAGES()", "view", nil, nil, []string{"uint32"}, []string{""}},
		"MAX_LENGTH":        {"MAX_LENGTH()", "view", nil, nil, []string{"uint32"}, []string{""}},
	}
	if len(contract.Methods) != len(want) {
		return fmt.Errorf("as0: embedded ABI has %d methods, want exactly %d", len(contract.Methods), len(want))
	}
	for name, shape := range want {
		method, ok := contract.Methods[name]
		if !ok || method.RawName != name || method.Sig != shape.sig || method.StateMutability != shape.mutability || len(method.Inputs) != len(shape.inputs) || len(method.Outputs) != len(shape.outputs) {
			return fmt.Errorf("as0: embedded ABI method %s differs from frozen shape", name)
		}
		for i, input := range method.Inputs {
			if input.Type.String() != shape.inputs[i] || input.Name != shape.inputNames[i] {
				return fmt.Errorf("as0: embedded ABI method %s input %d differs from frozen name/type", name, i)
			}
		}
		for i, output := range method.Outputs {
			if output.Type.String() != shape.outputs[i] || output.Name != shape.outputNames[i] {
				return fmt.Errorf("as0: embedded ABI method %s output %d differs from frozen name/type", name, i)
			}
		}
	}
	if len(contract.Constructor.Inputs) != 1 || contract.Constructor.Inputs[0].Name != "length" || contract.Constructor.Inputs[0].Type.String() != "uint32" || contract.Constructor.StateMutability != "nonpayable" {
		return fmt.Errorf("as0: embedded ABI constructor differs from frozen shape")
	}
	errDef, ok := contract.Errors["AS0Error"]
	if !ok || len(contract.Errors) != 1 || errDef.Sig != "AS0Error(uint256)" || len(errDef.Inputs) != 1 || errDef.Inputs[0].Name != "code" {
		return fmt.Errorf("as0: embedded ABI must contain exactly AS0Error(uint256 code)")
	}
	page, ok := contract.Events["PageIssued"]
	pageNames := []string{"index", "page", "length", "codeHash", "pageCommitment", "chainCommitment"}
	if !ok || page.Anonymous || page.Sig != "PageIssued(uint32,address,uint32,bytes32,bytes32,bytes32)" || len(page.Inputs) != len(pageNames) || !page.Inputs[0].Indexed || !page.Inputs[1].Indexed {
		return fmt.Errorf("as0: embedded ABI PageIssued differs from frozen shape")
	}
	for i, input := range page.Inputs {
		if input.Name != pageNames[i] {
			return fmt.Errorf("as0: embedded ABI PageIssued field %d differs from frozen name", i)
		}
	}
	for i := 2; i < len(page.Inputs); i++ {
		if page.Inputs[i].Indexed {
			return fmt.Errorf("as0: embedded ABI PageIssued has unexpected indexed field")
		}
	}
	sealed, ok := contract.Events["Sealed"]
	sealedNames := []string{"length", "pages", "contentCommitment"}
	if !ok || sealed.Anonymous || len(contract.Events) != 2 || sealed.Sig != "Sealed(uint32,uint32,bytes32)" || len(sealed.Inputs) != len(sealedNames) {
		return fmt.Errorf("as0: embedded ABI Sealed differs from frozen shape")
	}
	for i, input := range sealed.Inputs {
		if input.Indexed || input.Name != sealedNames[i] {
			return fmt.Errorf("as0: embedded ABI Sealed field %d differs from frozen shape", i)
		}
	}
	return nil
}

// Runtime returns a defensive copy of the fixed deployed controller runtime.
func Runtime() ([]byte, error) {
	loadArtifact()
	if loadErr != nil {
		return nil, loadErr
	}
	return append([]byte(nil), loadRun...), nil
}

// InitCode returns a defensive copy of the constructor bytecode without args.
func InitCode() ([]byte, error) {
	loadArtifact()
	if loadErr != nil {
		return nil, loadErr
	}
	return append([]byte(nil), loadInit...), nil
}

// ABI returns an independently parsed copy of the frozen contract ABI.
func ABI() (abi.ABI, error) {
	loadArtifact()
	if loadErr != nil {
		return abi.ABI{}, loadErr
	}
	out, err := abi.JSON(bytes.NewReader(loadRaw))
	if err != nil {
		return abi.ABI{}, fmt.Errorf("as0: copy embedded ABI: %w", err)
	}
	return out, nil
}

// RuntimeHash returns the lowercase SHA-256 transport pin of Runtime. EVM code
// identity uses Keccak and content authority remains the EVM-computed chain.
func RuntimeHash() (string, error) {
	code, err := Runtime()
	if err != nil {
		return "", err
	}
	hash := sha256.Sum256(code)
	return hex.EncodeToString(hash[:]), nil
}
