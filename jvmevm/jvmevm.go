// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.
//
// This program is free software: you can redistribute it and/or modify it under
// the terms of the GNU Lesser General Public License as published by the Free
// Software Foundation, either version 3 of the License, or (at your option) any
// later version.

// Package jvmevm runs the generic, tiny JVM-subset interpreter whose checked-in
// Solidity-compiled runtime executes inside geth's EVM. The host only ABI-packs
// an unchanged classfile, method name, and int arguments.
package jvmevm

import (
	"crypto/sha256"
	_ "embed"
	"encoding/hex"
	"fmt"
	"strings"
	"sync"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/core/tracing"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/core/vm"
	"github.com/ethereum/go-ethereum/core/vm/runtime"
)

//go:embed runtime/JVMSubsetInterpreter.runtime.hex
var runtimeHex string

const interpreterABI = `[{"inputs":[{"internalType":"bytes","name":"rawClass","type":"bytes"},{"internalType":"string","name":"entry","type":"string"},{"internalType":"int32[]","name":"args","type":"int32[]"}],"name":"interpret","outputs":[{"internalType":"int32","name":"","type":"int32"}],"stateMutability":"pure","type":"function"}]`

type Result struct {
	Value         int32
	GasUsed       uint64
	RuntimeSHA256 string
	RevertData    []byte
}

var (
	loadOnce sync.Once
	code     []byte
	contract abi.ABI
	loadErr  error
)

func loadRuntime() ([]byte, abi.ABI, error) {
	loadOnce.Do(func() {
		code, loadErr = hex.DecodeString(strings.TrimSpace(runtimeHex))
		if loadErr != nil {
			loadErr = fmt.Errorf("decode embedded interpreter runtime: %w", loadErr)
			return
		}
		if len(code) == 0 {
			loadErr = fmt.Errorf("embedded interpreter runtime is empty")
			return
		}
		contract, loadErr = abi.JSON(strings.NewReader(interpreterABI))
		if loadErr != nil {
			loadErr = fmt.Errorf("parse interpreter ABI: %w", loadErr)
		}
	})
	return code, contract, loadErr
}

// Runtime returns a copy of the one generic EVM interpreter runtime artifact.
func Runtime() ([]byte, error) {
	code, _, err := loadRuntime()
	return append([]byte(nil), code...), err
}

// RuntimeHash returns the SHA-256 hash of the generic runtime artifact.
func RuntimeHash() (string, error) {
	code, _, err := loadRuntime()
	if err != nil {
		return "", err
	}
	hash := sha256.Sum256(code)
	return hex.EncodeToString(hash[:]), nil
}

// Run ABI-encodes raw classfile bytes, the entry name, and arguments, then calls
// the generic interpreter as EVM runtime bytecode. It does not inspect or alter
// the classfile and does not execute Java on the host.
func Run(classfile []byte, method string, args []int32, gasLimit uint64) (Result, error) {
	code, contract, err := loadRuntime()
	if err != nil {
		return Result{}, err
	}
	hash, _ := RuntimeHash()
	result := Result{RuntimeSHA256: hash}
	if gasLimit == 0 {
		return result, fmt.Errorf("gas limit must be greater than zero")
	}
	input, err := contract.Pack("interpret", classfile, method, args)
	if err != nil {
		return result, fmt.Errorf("ABI-pack interpreter input: %w", err)
	}
	cfg := &runtime.Config{GasLimit: gasLimit, EVMConfig: vm.Config{Tracer: &tracing.Hooks{
		OnTxEnd: func(receipt *types.Receipt, _ error) { result.GasUsed = receipt.GasUsed },
	}}}
	output, _, execErr := runtime.Execute(code, input, cfg)
	if execErr != nil {
		result.RevertData = append([]byte(nil), output...)
		return result, fmt.Errorf("interpreter EVM execution failed: %w (revert_data=0x%x)", execErr, output)
	}
	values, err := contract.Methods["interpret"].Outputs.Unpack(output)
	if err != nil {
		return result, fmt.Errorf("decode interpreter EVM result: %w", err)
	}
	if len(values) != 1 {
		return result, fmt.Errorf("interpreter returned %d values, want 1", len(values))
	}
	value, ok := values[0].(int32)
	if !ok {
		return result, fmt.Errorf("interpreter returned unexpected ABI type %T", values[0])
	}
	result.Value = value
	return result, nil
}
