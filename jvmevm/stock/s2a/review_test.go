// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.

package s2a

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"testing"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
)

type stockS2aReviewArtifactDocument struct {
	ContractName     string            `json:"contractName"`
	Bytecode         string            `json:"bytecode"`
	DeployedBytecode string            `json:"deployedBytecode"`
	SourceHashes     map[string]string `json:"sourceHashes"`
	Compiler         struct {
		Version    string `json:"version"`
		ViaIR      bool   `json:"viaIR"`
		EVMVersion string `json:"evmVersion"`
		Optimizer  struct {
			Enabled bool `json:"enabled"`
			Runs    int  `json:"runs"`
		} `json:"optimizer"`
		Metadata struct {
			AppendCBOR   bool   `json:"appendCBOR"`
			BytecodeHash string `json:"bytecodeHash"`
		} `json:"metadata"`
	} `json:"compiler"`
}

type stockS2aReviewArtifactIdentity struct {
	initBytes, runtimeBytes   int
	initSHA256, runtimeSHA256 string
	runtimeKeccak             string
}

type stockS2aReviewCatalogue struct {
	Schema         uint32 `json:"schema"`
	CatalogueCount uint16 `json:"catalogueCount"`
	CatalogueRoot  string `json:"catalogueRoot"`
	Cases          []struct {
		ID, ExpectedKind, ExpectedException string
		Expected                            *int32
		PC, FaultPC, CodeLength             uint32
		SP, Lifecycle, JavaFaultKind        uint8
		Stack                               []int32
	} `json:"cases"`
}

func stockS2aReviewDecodeHex(t *testing.T, label, text string) []byte {
	t.Helper()
	out, err := hex.DecodeString(text)
	if err != nil || len(out) == 0 {
		t.Fatalf("decode %s: bytes=%d err=%v", label, len(out), err)
	}
	return out
}

func stockS2aReviewSHA256(blob []byte) string {
	return fmt.Sprintf("%x", sha256.Sum256(blob))
}

// The catalogue stores MachineV3.result for every terminal row. For a Java
// fault that field is numeric zero, not JSON null; the lifecycle and preserved
// divisor distinguish it from a returned value.
func TestStockS2aReviewCatalogueFaultMachineEncoding(t *testing.T) {
	blob, err := os.ReadFile("../../testdata/stock/s2a/catalogue.json")
	if err != nil {
		t.Fatal(err)
	}
	var catalogue stockS2aReviewCatalogue
	if err := json.Unmarshal(blob, &catalogue); err != nil {
		t.Fatal(err)
	}
	if catalogue.Schema != 3 || catalogue.CatalogueCount != 201 || len(catalogue.Cases) != 201 || catalogue.CatalogueRoot != "0x1273f2302d2898a2eb0ff391f9cf7ff2c9b64749fd0821df891b921499aa8d0d" {
		t.Fatalf("catalogue header changed: schema=%d count=%d rows=%d root=%s", catalogue.Schema, catalogue.CatalogueCount, len(catalogue.Cases), catalogue.CatalogueRoot)
	}
	wantFault := map[string]bool{"m2b-idiv-zero-divisor": true, "m2b-irem-zero-divisor": true}
	faults, values := 0, 0
	for _, tc := range catalogue.Cases {
		if tc.ExpectedKind == "value" {
			values++
			continue
		}
		faults++
		if !wantFault[tc.ID] || tc.Expected == nil || *tc.Expected != 0 || tc.ExpectedException != "java.lang.ArithmeticException" || tc.Lifecycle != stockS2aVerifyJavaFault || tc.JavaFaultKind != stockS2aVerifyArithmeticFault || tc.PC != tc.FaultPC || tc.PC != 2 || tc.PC >= tc.CodeLength || tc.SP < 2 || int(tc.SP) > len(tc.Stack) || tc.Stack[tc.SP-1] != 0 {
			t.Fatalf("malformed catalogue fault row: %+v", tc)
		}
	}
	if values != 199 || faults != 2 {
		t.Fatalf("catalogue terminal kinds values=%d faults=%d", values, faults)
	}
}

// Pin artifact provenance independently of the package loader. In particular,
// every artifact must commit to the exact six local Solidity inputs, not merely
// contain well-formed 64-character source-hash strings.
func TestStockS2aReviewPinnedArtifactProvenanceAndHashes(t *testing.T) {
	want := map[string]stockS2aReviewArtifactIdentity{
		"S2aMetadataPage": {339, 3, "728282836fee88ff7739d925d991ef2c26f50e21794ee1c1af002d598f957a4f", "0668b20e4ee135e7cac4091998933a5123658a8e777994fdb4b4ee2d553e6438", "3c55237b3869f93f3e570793afec9785f20a4ee7cd0a7798a418838c833228e0"},
		"S2aClassParser":  {15685, 15659, "7309868e22cbafbec5c921066ab1da5d43b71d5623e45ce8a8f98aafd31baa2a", "8ae89c4943c83f7a138440a1227a094415a107f87bcf7a7e814bc4f911453b7d", "9746182e3ecdfeace27d26210aaf92997c1b8a74ae34f987bc2a4955433eae6e"},
		"S2aStepModule":   {9496, 9470, "6c13f3f52ac9ef5bc95ff148a3d6ebc6cf699606cbd8932cc4b1cefb9ec90262", "0f4e6a75ab95b7e289bd91ad8f587b63f9d5b2503934b10fbca5b498dd99129f", "d004fc0eae66bbf550a65449528b8ff2d96c7f46b5caeed9177b8a68b0164226"},
		"S2aCoordinator":  {13140, 7694, "a215165f52922752d099646feeb2ca4bc90a6dc47b191322e6c248fbd4e6a42f", "e464b3a2237b598de447d369f1cdcb9af568ba7eba2a06168ee1e12a44292212", "82bbb59342eaeedd9ee649102ed3d70917cafc9f7ec68417669cbe9f41658cc5"},
	}
	sources := []string{"S2aTypes.sol", "S2aMetadataPage.sol", "S2aCodec.sol", "S2aClassParser.sol", "S2aStepModule.sol", "S2aCoordinator.sol"}
	localHashes := make(map[string]string, len(sources))
	for _, name := range sources {
		blob, err := os.ReadFile(filepath.Join("runtime", name))
		if err != nil {
			t.Fatal(err)
		}
		localHashes[name] = stockS2aReviewSHA256(blob)
	}
	for name, identity := range want {
		t.Run(name, func(t *testing.T) {
			blob, err := os.ReadFile(filepath.Join("runtime", "artifacts", name+".json"))
			if err != nil {
				t.Fatal(err)
			}
			var doc stockS2aReviewArtifactDocument
			if err := json.Unmarshal(blob, &doc); err != nil {
				t.Fatal(err)
			}
			if doc.ContractName != name || doc.Compiler.Version != "0.8.30+commit.73712a01.Emscripten.clang" || !doc.Compiler.ViaIR || doc.Compiler.EVMVersion != "cancun" || !doc.Compiler.Optimizer.Enabled || doc.Compiler.Optimizer.Runs != 200 || doc.Compiler.Metadata.AppendCBOR || doc.Compiler.Metadata.BytecodeHash != "none" {
				t.Fatalf("artifact identity/compiler changed: contract=%q compiler=%+v", doc.ContractName, doc.Compiler)
			}
			if len(doc.SourceHashes) != len(localHashes) {
				t.Fatalf("source hash set has %d entries, want %d", len(doc.SourceHashes), len(localHashes))
			}
			for source, hash := range localHashes {
				if doc.SourceHashes[source] != hash {
					t.Fatalf("artifact source hash %s=%q want=%q", source, doc.SourceHashes[source], hash)
				}
			}
			init := stockS2aReviewDecodeHex(t, name+".bytecode", doc.Bytecode)
			runtime := stockS2aReviewDecodeHex(t, name+".deployedBytecode", doc.DeployedBytecode)
			if len(init) != identity.initBytes || len(runtime) != identity.runtimeBytes || stockS2aReviewSHA256(init) != identity.initSHA256 || stockS2aReviewSHA256(runtime) != identity.runtimeSHA256 || fmt.Sprintf("%x", crypto.Keccak256(runtime)) != identity.runtimeKeccak {
				t.Fatalf("artifact bytes changed: init=%d sha=%s runtime=%d sha=%s keccak=%x", len(init), stockS2aReviewSHA256(init), len(runtime), stockS2aReviewSHA256(runtime), crypto.Keccak256(runtime))
			}
		})
	}
}

func stockS2aReviewDirectStep(t *testing.T, e *stockS2aVerifyEnv, module stockS2aVerifyArtifact, moduleAt common.Address, program stockS2aVerifyProgram, before stockS2aVerifyMachine) stockS2aVerifyMachine {
	t.Helper()
	tx := stockS2aVerifyProgramCall(t, e, module, moduleAt, program, before, 1, stockS2aVerifyCallGas)
	if tx.coreErr != nil || tx.result == nil || tx.result.Failed() {
		t.Fatalf("direct step failed: core=%v evm=%v data=%x", tx.coreErr, stockS2aVerifyResultErr(tx.result), stockS2aVerifyResultData(tx.result))
	}
	out := stockS2aVerifyUnpack(t, module, "step", tx.result.ReturnData)
	if out[1].(uint16) != 1 {
		t.Fatalf("direct step count=%d want=1", out[1].(uint16))
	}
	return stockS2aVerifyMachineFrom(out[0])
}

func stockS2aReviewAssertOneInt(t *testing.T, after stockS2aVerifyMachine, pc uint32, want uint32) {
	t.Helper()
	if after.Pc != pc || after.Sp != 1 || after.Lifecycle != stockS2aVerifyRunnable || after.Result != 0 || after.JavaFaultKind != 0 || after.FaultPC != 0 || after.Stack[0].Cmp(stockS2aVerifyTagged(want)) != 0 {
		t.Fatalf("wrong one-step machine: %+v want pc=%d bits=%08x", after, pc, want)
	}
	for i := 1; i < len(after.Stack); i++ {
		if after.Stack[i].Sign() != 0 {
			t.Fatalf("inactive stack[%d]=%s", i, after.Stack[i])
		}
	}
}

func stockS2aReviewBinaryMachine(a, b uint32) stockS2aVerifyMachine {
	m := stockS2aVerifyZeroMachine()
	m.Pc, m.Sp = 2, 2
	m.Stack[0], m.Stack[1] = stockS2aVerifyTagged(a), stockS2aVerifyTagged(b)
	return m
}

func stockS2aReviewUnaryMachine(a uint32) stockS2aVerifyMachine {
	m := stockS2aVerifyZeroMachine()
	m.Pc, m.Sp = 1, 1
	m.Stack[0] = stockS2aVerifyTagged(a)
	return m
}

// Exercise the checked step artifact directly at each new opcode. This does not
// feed offsets or expected values to production: parser-issued ProgramContext is
// obtained from an ordinary coordinator, while expected arithmetic is calculated
// here from Java int rules.
func TestStockS2aReviewDirectIntegerOpcodeMatrix(t *testing.T) {
	page := stockS2aVerifyLoadPage(t)
	parser := stockS2aVerifyLoadArtifact(t, "S2aClassParser")
	module := stockS2aVerifyLoadArtifact(t, "S2aStepModule")
	coord := stockS2aVerifyLoadArtifact(t, "S2aCoordinator")
	e := stockS2aVerifyNewEnv(t)
	defer e.close()
	parserAt, _ := e.mustCreate(parser.init, stockS2aVerifyCreateGas)
	moduleAt, _ := e.mustCreate(module.init, stockS2aVerifyCreateGas)
	parserHash, moduleHash := crypto.Keccak256Hash(parser.runtime), crypto.Keccak256Hash(module.runtime)
	methods := []stockS2aVerifyMethod{
		{"div", "(II)I", 9, []byte{0x1a, 0x1b, 0x6c, 0xac}, 2, 2, 1, 0},
		{"rem", "(II)I", 9, []byte{0x1a, 0x1b, 0x70, 0xac}, 2, 2, 1, 0},
		{"shl", "(II)I", 9, []byte{0x1a, 0x1b, 0x78, 0xac}, 2, 2, 1, 0},
		{"shr", "(II)I", 9, []byte{0x1a, 0x1b, 0x7a, 0xac}, 2, 2, 1, 0},
		{"ushr", "(II)I", 9, []byte{0x1a, 0x1b, 0x7c, 0xac}, 2, 2, 1, 0},
		{"and", "(II)I", 9, []byte{0x1a, 0x1b, 0x7e, 0xac}, 2, 2, 1, 0},
		{"or", "(II)I", 9, []byte{0x1a, 0x1b, 0x80, 0xac}, 2, 2, 1, 0},
		{"xor", "(II)I", 9, []byte{0x1a, 0x1b, 0x82, 0xac}, 2, 2, 1, 0},
		{"i2b", "(I)I", 9, []byte{0x1a, 0x91, 0xac}, 1, 1, 1, 0},
		{"i2c", "(I)I", 9, []byte{0x1a, 0x92, 0xac}, 1, 1, 1, 0},
		{"i2s", "(I)I", 9, []byte{0x1a, 0x93, 0xac}, 1, 1, 1, 0},
	}
	class := stockS2aVerifyBuildClass("S2aReviewIntegerMatrix", methods, 0)
	_, _, _, classID, _, _, _ := stockS2aVerifyDeployRegistered(t, e, page, parser, parserAt, class.bytes)
	programs := make(map[string]stockS2aVerifyProgram, len(methods))
	for _, method := range methods {
		argc := 1
		if method.descriptor == "(II)I" {
			argc = 2
		}
		at, _ := stockS2aVerifyDeployCoordinator(t, e, coord, parserAt, parserHash, classID, moduleAt, moduleHash, method.name, make([]int32, argc), 64)
		programs[method.name] = stockS2aVerifyProgramContext(t, e, coord, at)
	}

	pairs := [][2]uint32{
		{0x80000000, 0xffffffff}, {0x80000000, 3}, {0xffffffff, 5},
		{0xffffffef, 0xfffffffb}, {0xffffffef, 5}, {17, 0xfffffffb},
		{0x7fffffff, 31}, {0x40000001, 33}, {0xaaaaaaaa, 0x55555555},
	}
	for i, pair := range pairs {
		a, b := pair[0], pair[1]
		if b != 0 {
			var q, r uint32
			if a == 0x80000000 && b == 0xffffffff {
				q, r = 0x80000000, 0
			} else {
				q = uint32(int64(int32(a)) / int64(int32(b)))
				r = uint32(int64(int32(a)) % int64(int32(b)))
			}
			t.Run(fmt.Sprintf("divrem-%d", i), func(t *testing.T) {
				stockS2aReviewAssertOneInt(t, stockS2aReviewDirectStep(t, e, module, moduleAt, programs["div"], stockS2aReviewBinaryMachine(a, b)), 3, q)
				stockS2aReviewAssertOneInt(t, stockS2aReviewDirectStep(t, e, module, moduleAt, programs["rem"], stockS2aReviewBinaryMachine(a, b)), 3, r)
			})
		}
		d := b & 31
		stockS2aReviewAssertOneInt(t, stockS2aReviewDirectStep(t, e, module, moduleAt, programs["shl"], stockS2aReviewBinaryMachine(a, b)), 3, a<<d)
		stockS2aReviewAssertOneInt(t, stockS2aReviewDirectStep(t, e, module, moduleAt, programs["shr"], stockS2aReviewBinaryMachine(a, b)), 3, uint32(int32(a)>>d))
		stockS2aReviewAssertOneInt(t, stockS2aReviewDirectStep(t, e, module, moduleAt, programs["ushr"], stockS2aReviewBinaryMachine(a, b)), 3, a>>d)
		stockS2aReviewAssertOneInt(t, stockS2aReviewDirectStep(t, e, module, moduleAt, programs["and"], stockS2aReviewBinaryMachine(a, b)), 3, a&b)
		stockS2aReviewAssertOneInt(t, stockS2aReviewDirectStep(t, e, module, moduleAt, programs["or"], stockS2aReviewBinaryMachine(a, b)), 3, a|b)
		stockS2aReviewAssertOneInt(t, stockS2aReviewDirectStep(t, e, module, moduleAt, programs["xor"], stockS2aReviewBinaryMachine(a, b)), 3, a^b)
	}
	for _, a := range []uint32{0, 0x7f, 0x80, 0xff, 0x100, 0x7fff, 0x8000, 0xffff, 0x10000, 0x80000000, 0xffffffff} {
		stockS2aReviewAssertOneInt(t, stockS2aReviewDirectStep(t, e, module, moduleAt, programs["i2b"], stockS2aReviewUnaryMachine(a)), 2, uint32(int32(int8(a))))
		stockS2aReviewAssertOneInt(t, stockS2aReviewDirectStep(t, e, module, moduleAt, programs["i2c"], stockS2aReviewUnaryMachine(a)), 2, uint32(uint16(a)))
		stockS2aReviewAssertOneInt(t, stockS2aReviewDirectStep(t, e, module, moduleAt, programs["i2s"], stockS2aReviewUnaryMachine(a)), 2, uint32(int32(int16(a))))
	}
}

// A divide fault after a prior successful checkpoint must preserve a lower
// stack value, both operands, and all locals. Dirty/reserve rejection must leave
// that prior checkpoint intact and permit an exact retry. The total-step cap is
// also checked immediately before and on the throwing instruction.
func TestStockS2aReviewFaultContinuationCapsAndRollback(t *testing.T) {
	page := stockS2aVerifyLoadPage(t)
	parser := stockS2aVerifyLoadArtifact(t, "S2aClassParser")
	module := stockS2aVerifyLoadArtifact(t, "S2aStepModule")
	coord := stockS2aVerifyLoadArtifact(t, "S2aCoordinator")
	e := stockS2aVerifyNewEnv(t)
	defer e.close()
	parserAt, _ := e.mustCreate(parser.init, stockS2aVerifyCreateGas)
	moduleAt, _ := e.mustCreate(module.init, stockS2aVerifyCreateGas)
	parserHash, moduleHash := crypto.Keccak256Hash(parser.runtime), crypto.Keccak256Hash(module.runtime)
	// iload_0; iconst_5; istore_2; iload_0; iload_1; idiv;
	// istore_2; ireturn. The normal path consumes the quotient and returns the
	// deliberately retained lower value; the fault path must execute neither.
	code := []byte{0x1a, 0x08, 0x3d, 0x1a, 0x1b, 0x6c, 0x3d, 0xac}
	class := stockS2aVerifyBuildClass("S2aReviewFaultContinuation", []stockS2aVerifyMethod{{"fault", "(II)I", 9, code, 3, 3, 1, 0}}, 0)
	_, _, _, classID, _, _, _ := stockS2aVerifyDeployRegistered(t, e, page, parser, parserAt, class.bytes)
	newCoordinator := func(t *testing.T, cap uint64) common.Address {
		t.Helper()
		at, _ := stockS2aVerifyDeployCoordinator(t, e, coord, parserAt, parserHash, classID, moduleAt, moduleHash, "fault", []int32{-17, 0}, cap)
		return at
	}

	at := newCoordinator(t, 64)
	first := stockS2aVerifyResume(t, e, coord, at, 0, 4, 32, stockS2aVerifyCallGas)
	if first.result == nil || first.result.Failed() {
		t.Fatalf("prefix resume: %v", stockS2aVerifyResultErr(first.result))
	}
	prefix := stockS2aVerifyCheckpointAt(t, e, coord, at)
	if prefix.Epoch != 1 || prefix.TotalSteps != 4 || prefix.Machine.Pc != 4 || prefix.Machine.Sp != 2 || prefix.Machine.Stack[0].Cmp(stockS2aVerifyTagged(0xffffffef)) != 0 || prefix.Machine.Stack[1].Cmp(stockS2aVerifyTagged(0xffffffef)) != 0 || prefix.Machine.Locals[2].Cmp(stockS2aVerifyTagged(5)) != 0 {
		t.Fatalf("wrong committed prefix: %+v", prefix)
	}
	reserve := stockS2aVerifyResume(t, e, coord, at, prefix.Epoch, 2, 32, stockS2aVerifyReserve-50_000)
	stockS2aVerifyAssertRevert(t, reserve, "S2aControlError(uint256)", 5)
	stockS2aVerifyAssertRollback(t, e, coord, at, prefix, reserve)
	dirty := stockS2aVerifyResume(t, e, coord, at, prefix.Epoch, 2, 1, stockS2aVerifyCallGas)
	stockS2aVerifyAssertRevert(t, dirty, "S2aControlError(uint256)", 6)
	stockS2aVerifyAssertRollback(t, e, coord, at, prefix, dirty)

	retry := stockS2aVerifyResume(t, e, coord, at, prefix.Epoch, 2, 32, stockS2aVerifyCallGas)
	if retry.result == nil || retry.result.Failed() {
		t.Fatalf("fault retry: %v", stockS2aVerifyResultErr(retry.result))
	}
	fault := stockS2aVerifyCheckpointAt(t, e, coord, at)
	wantStack := []uint32{0xffffffef, 0xffffffef, 0}
	if fault.Epoch != 2 || fault.TotalSteps != 6 || fault.Machine.Pc != 5 || fault.Machine.FaultPC != 5 || fault.Machine.Sp != 3 || fault.Machine.Lifecycle != stockS2aVerifyJavaFault || fault.Machine.JavaFaultKind != stockS2aVerifyArithmeticFault || fault.Machine.Result != 0 {
		t.Fatalf("wrong fault checkpoint: %+v", fault)
	}
	for i, want := range wantStack {
		if fault.Machine.Stack[i].Cmp(stockS2aVerifyTagged(want)) != 0 {
			t.Fatalf("fault stack[%d]=%s want tagged(%08x)", i, fault.Machine.Stack[i], want)
		}
	}
	for i, want := range []uint32{0xffffffef, 0, 5} {
		if fault.Machine.Locals[i].Cmp(stockS2aVerifyTagged(want)) != 0 {
			t.Fatalf("fault local[%d]=%s want tagged(%08x)", i, fault.Machine.Locals[i], want)
		}
	}
	terminal := stockS2aVerifyResume(t, e, coord, at, fault.Epoch, 0, 0, stockS2aVerifyCallGas)
	stockS2aVerifyAssertRevert(t, terminal, "S2aControlError(uint256)", 1)
	stockS2aVerifyAssertRollback(t, e, coord, at, fault, terminal)

	before := stockS2aVerifyRunEntry(t, e, coord, parserAt, parserHash, classID, moduleAt, moduleHash, "fault", []int32{-17, 0}, 5)
	if before.TotalSteps != 5 || before.Machine.Lifecycle != stockS2aVerifyStepLimit || before.Machine.Pc != 5 || before.Machine.Sp != 3 || before.Machine.Result != 0 || before.Machine.JavaFaultKind != 0 || before.Machine.FaultPC != 0 {
		t.Fatalf("cap immediately before fault: %+v", before)
	}
	on := stockS2aVerifyRunEntry(t, e, coord, parserAt, parserHash, classID, moduleAt, moduleHash, "fault", []int32{-17, 0}, 6)
	if on.TotalSteps != 6 || on.Machine.Lifecycle != stockS2aVerifyJavaFault || on.Machine.JavaFaultKind != 1 || on.Machine.Pc != 5 || on.Machine.FaultPC != 5 || on.Machine.Result != 0 {
		t.Fatalf("fault did not win at cap: %+v", on)
	}
}
