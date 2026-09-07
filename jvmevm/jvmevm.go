// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.
//
// This program is free software: you can redistribute it and/or modify it under
// the terms of the GNU Lesser General Public License as published by the Free
// Software Foundation, either version 3 of the License, or (at your option) any
// later version.

// Package jvmevm runs the generic, tiny JVM-subset interpreter whose checked-in
// Solidity-compiled runtime executes inside geth's EVM. The host only ABI-packs
// unchanged classfiles, explicit entry metadata, and int arguments.
package jvmevm

import (
	"bytes"
	"crypto/sha256"
	_ "embed"
	"encoding/hex"
	"errors"
	"fmt"
	"strings"
	"sync"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/core/tracing"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/core/vm"
	"github.com/ethereum/go-ethereum/core/vm/runtime"
	"github.com/ethereum/go-ethereum/crypto"
)

//go:embed runtime/JVMSubsetInterpreter.runtime.hex
var runtimeHex string

const interpreterABI = `[{"inputs":[{"internalType":"bytes","name":"rawClass","type":"bytes"},{"internalType":"string","name":"entry","type":"string"},{"internalType":"int32[]","name":"args","type":"int32[]"}],"name":"interpret","outputs":[{"internalType":"int32","name":"","type":"int32"}],"stateMutability":"pure","type":"function"},{"inputs":[{"internalType":"bytes[]","name":"rawClasses","type":"bytes[]"},{"internalType":"string","name":"entryClass","type":"string"},{"internalType":"string","name":"entry","type":"string"},{"internalType":"int32[]","name":"args","type":"int32[]"}],"name":"interpretClasses","outputs":[{"internalType":"int32","name":"","type":"int32"}],"stateMutability":"pure","type":"function"}]`

type Result struct {
	Value          int32
	ExceptionClass string
	GasUsed        uint64
	RuntimeSHA256  string
	RevertData     []byte
}

var javaExceptionSelector = crypto.Keccak256([]byte("JavaException(uint256)"))[:4]

func decodeJavaException(data []byte) (string, bool) {
	if len(data) != 4+32 || !bytes.Equal(data[:4], javaExceptionSelector) {
		return "", false
	}
	// The Solidity kind is uint256. Decode only exact frozen, known outcomes.
	for _, b := range data[4 : len(data)-1] {
		if b != 0 {
			return "", false
		}
	}
	switch data[len(data)-1] {
	case 1:
		return "java.lang.ArithmeticException", true
	case 2:
		return "java.lang.StackOverflowError", true
	default:
		return "", false
	}
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
	return run("interpret", gasLimit, classfile, method, args)
}

// RunClasses ABI-encodes unchanged classfile bytes and the explicit JVM internal
// entry-class name. Class declarations and call owners are inspected and linked
// only by the EVM runtime.
func RunClasses(classfiles [][]byte, entryClass, method string, args []int32, gasLimit uint64) (Result, error) {
	return run("interpretClasses", gasLimit, classfiles, entryClass, method, args)
}

func run(method string, gasLimit uint64, inputs ...interface{}) (Result, error) {
	code, contract, err := loadRuntime()
	if err != nil {
		return Result{}, err
	}
	hash, _ := RuntimeHash()
	result := Result{RuntimeSHA256: hash}
	if gasLimit == 0 {
		return result, fmt.Errorf("gas limit must be greater than zero")
	}
	input, err := contract.Pack(method, inputs...)
	if err != nil {
		return result, fmt.Errorf("ABI-pack interpreter input: %w", err)
	}
	cfg := &runtime.Config{GasLimit: gasLimit, EVMConfig: vm.Config{Tracer: &tracing.Hooks{
		OnTxEnd: func(receipt *types.Receipt, _ error) { result.GasUsed = receipt.GasUsed },
	}}}
	output, _, execErr := runtime.Execute(code, input, cfg)
	if execErr != nil {
		result.RevertData = append([]byte(nil), output...)
		if errors.Is(execErr, vm.ErrExecutionReverted) {
			if exceptionClass, ok := decodeJavaException(output); ok {
				result.ExceptionClass = exceptionClass
				return result, nil
			}
		}
		return result, fmt.Errorf("interpreter EVM execution failed: %w (revert_data=0x%x)", execErr, output)
	}
	values, err := contract.Methods[method].Outputs.Unpack(output)
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
