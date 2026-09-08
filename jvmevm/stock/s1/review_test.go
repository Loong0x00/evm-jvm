// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.

package s1

import (
	"bytes"
	"fmt"
	"testing"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core"
	"github.com/ethereum/go-ethereum/crypto"
)

func stockS1ReviewAggregateMethods(allEligible bool) []stockS1VerifyMethod {
	methods := make([]stockS1VerifyMethod, 31)
	for i := range methods {
		count := 0
		if i < 3 {
			count = 84
		} else if i == 3 {
			count = 4
		}
		var code []byte
		for j := 0; j < count; j++ {
			code = append(code, 0x12, 10, 0x3b)
		}
		if count == 0 && allEligible {
			code = append(code, 0x03, 0xac) // iconst_0; ireturn
		} else {
			code = append(code, 0x1a, 0xac) // iload_0; ireturn
		}
		methods[i] = stockS1VerifyMethod{fmt.Sprintf("m%02d", i), "()I", 0x0009, code, 1, 1, 1, 0}
	}
	return methods
}

func stockS1ReviewMethodStatus(runtime []byte, index uint16) (domain, code uint8, location uint32) {
	offset := 1 + 192 + int(index)*128 + 64
	packed := runtime[offset : offset+32]
	// Packed M2 is big-endian as a word. These fields are bits 104, 112 and
	// 120 from the least-significant end, hence bytes 18, 17 and 13..16.
	return packed[18], packed[17], uint32(packed[13])<<24 | uint32(packed[14])<<16 | uint32(packed[15])<<8 | uint32(packed[16])
}

// The original blocker must now succeed at the frozen 8M budget. A separately
// underfunded registration first proves internal CREATE/registry rollback.
func TestStockS1ReviewAggregateAtFrozenBudget(t *testing.T) {
	page := stockS1VerifyLoadPage(t)
	parser := stockS1VerifyLoadArtifact(t, "S1ClassParser")
	e := stockS1VerifyNewEnv(t)
	defer e.close()
	parserAt, _ := e.mustCreate(parser.init, stockS1VerifyCreateGas)

	// Unlike the original pre-integration fixture, all31 declared test methods
	// here are eligible; this isolates the production maximum.
	aggregate := stockS1VerifyBuildClass("S1Aggregate", stockS1ReviewAggregateMethods(true), 0)
	rawAt, pageHash, payloadHash, _ := stockS1VerifyDeployPage(t, e, page, aggregate.bytes)
	input := stockS1VerifyCallData(t, parser, "registerClass", rawAt, pageHash, payloadHash)
	expectedMetadata := append([]byte{0}, stockS1VerifyMetadataExpected(aggregate.bytes, rawAt, pageHash, payloadHash)...)
	expectedID := stockS1VerifyClassID(t, crypto.Keccak256Hash(parser.runtime), rawAt, pageHash, payloadHash, crypto.Keccak256Hash(expectedMetadata))
	parserNonce := e.state.StateDB.GetNonce(parserAt)
	internalPage := crypto.CreateAddress(parserAt, parserNonce)
	frozen := e.apply(&parserAt, input, 6_000_000)
	stockS1VerifyAssertRevert(t, frozen, "S1ClassError(uint256,uint256)", 6, 0)
	if e.state.StateDB.GetNonce(parserAt) != parserNonce || len(e.state.StateDB.GetCode(internalPage)) != 0 {
		t.Fatal("failed frozen registration retained parser nonce or metadata code")
	}
	if at, hash := stockS1VerifyClassRecord(t, e, parser, parserAt, expectedID); at != (common.Address{}) || hash != (common.Hash{}) {
		t.Fatal("failed frozen registration retained registry record")
	}
	diagnostic := e.apply(&parserAt, input, stockS1VerifyCreateGas)
	if diagnostic.coreErr != nil || diagnostic.result == nil || diagnostic.result.Err != nil {
		t.Fatalf("diagnostic registration: core=%v evm=%v data=%x", diagnostic.coreErr, stockS1VerifyResultErr(diagnostic.result), stockS1VerifyResultData(diagnostic.result))
	}
	out := stockS1VerifyUnpack(t, parser, "registerClass", diagnostic.result.ReturnData)
	metaAt := out[1].(common.Address)
	metadata := e.state.StateDB.GetCode(metaAt)
	if !bytes.Equal(metadata, expectedMetadata) {
		t.Fatalf("eligible aggregate metadata is not canonical: have=%s want=%s", crypto.Keccak256Hash(metadata), crypto.Keccak256Hash(expectedMetadata))
	}
	for i := uint16(1); i < 32; i++ {
		domain, code, location := stockS1ReviewMethodStatus(metadata, i)
		if domain != 0 || code != 0 || location != 0 {
			t.Fatalf("corrected method[%d] status=(%d,%d,%d), want eligible", i, domain, code, location)
		}
	}
	intrinsic, err := core.IntrinsicGas(input, nil, nil, false, true, true, true)
	if err != nil {
		t.Fatal(err)
	}
	if out[3].(uint16) != 32 || len(metadata) != 6337 || diagnostic.result.UsedGas > stockS1VerifyCreateGas || diagnostic.result.UsedGas <= intrinsic {
		t.Fatalf("aggregate count=%d metadata=%d gas=%d intrinsic=%d", out[3].(uint16), len(metadata), diagnostic.result.UsedGas, intrinsic)
	}
	t.Logf("review aggregate: frozenErr=%v frozenUsed=%d diagnosticUsed=%d executionUsed=%d intrinsic=%d raw=%d metadata=%d metadataHash=%s", frozen.result.Err, frozen.result.UsedGas, diagnostic.result.UsedGas, diagnostic.result.UsedGas-intrinsic, intrinsic, len(aggregate.bytes), len(metadata), crypto.Keccak256Hash(metadata))
}

// Retain the original invalid shape as an explicit classification negative.
// The bounded metadata helper is only an oracle for valid methods; it must not
// be used to assert eligibility of these deliberately uninitialized methods.
func TestStockS1ReviewIntegratedAggregateOracleClassification(t *testing.T) {
	page := stockS1VerifyLoadPage(t)
	parser := stockS1VerifyLoadArtifact(t, "S1ClassParser")
	e := stockS1VerifyNewEnv(t)
	defer e.close()
	parserAt, _ := e.mustCreate(parser.init, stockS1VerifyCreateGas)

	aggregate := stockS1VerifyBuildClass("S1Aggregate", stockS1ReviewAggregateMethods(false), 0)
	rawAt, pageHash, payloadHash, _ := stockS1VerifyDeployPage(t, e, page, aggregate.bytes)
	input := stockS1VerifyCallData(t, parser, "registerClass", rawAt, pageHash, payloadHash)
	diagnostic := e.apply(&parserAt, input, stockS1VerifyCreateGas)
	if diagnostic.coreErr != nil || diagnostic.result == nil || diagnostic.result.Err != nil {
		t.Fatalf("diagnostic registration: core=%v evm=%v data=%x", diagnostic.coreErr, stockS1VerifyResultErr(diagnostic.result), stockS1VerifyResultData(diagnostic.result))
	}
	out := stockS1VerifyUnpack(t, parser, "registerClass", diagnostic.result.ReturnData)
	actual := e.state.StateDB.GetCode(out[1].(common.Address))
	oracle := append([]byte{0}, stockS1VerifyMetadataExpected(aggregate.bytes, rawAt, pageHash, payloadHash)...)
	actualDomain, actualCode, actualPC := stockS1ReviewMethodStatus(actual, 5)
	oracleDomain, oracleCode, oraclePC := stockS1ReviewMethodStatus(oracle, 5)
	for index := uint16(5); index < 32; index++ {
		domain, code, pc := stockS1ReviewMethodStatus(actual, index)
		if domain != 2 || code != 11 || pc != 0 {
			t.Fatalf("parser method[%d] status=(%d,%d,%d), want BytecodeError(11,0)", index, domain, code, pc)
		}
	}
	module := stockS1VerifyLoadArtifact(t, "S1StepModule")
	coord := stockS1VerifyLoadArtifact(t, "S1Coordinator")
	moduleAt, _ := e.mustCreate(module.init, stockS1VerifyCreateGas)
	selection := e.apply(nil, stockS1VerifyConstructor(t, coord, parserAt, crypto.Keccak256Hash(parser.runtime), common.Hash(out[0].([32]byte)), moduleAt, crypto.Keccak256Hash(module.runtime), []byte("m04"), []int32{}, uint64(64)), stockS1VerifyCreateGas)
	stockS1VerifyAssertRevert(t, selection, "S1BytecodeError(uint256,uint256)", 11, 0)
	if oracleDomain != 0 || oracleCode != 0 || oraclePC != 0 || bytes.Equal(actual, oracle) {
		t.Fatalf("integrated oracle status=(%d,%d,%d) equal=%v", oracleDomain, oracleCode, oraclePC, bytes.Equal(actual, oracle))
	}
	if code := aggregate.bytes[aggregate.marks["method5.code0.bytes"]:]; len(code) < 2 || code[0] != 0x1a || code[1] != 0xac {
		t.Fatalf("integrated fixture method[5] is not iload_0;ireturn: %x", code[:2])
	}
	intrinsic, err := core.IntrinsicGas(input, nil, nil, false, true, true, true)
	if err != nil {
		t.Fatal(err)
	}
	t.Logf("review integrated fixture: diagnosticUsed=%d executionUsed=%d intrinsic=%d actualHash=%s oracleHash=%s method5Actual=(domain%d,code%d,pc%d) oracle=(domain%d,code%d,pc%d)", diagnostic.result.UsedGas, diagnostic.result.UsedGas-intrinsic, intrinsic, crypto.Keccak256Hash(actual), crypto.Keccak256Hash(oracle), actualDomain, actualCode, actualPC, oracleDomain, oracleCode, oraclePC)
}
