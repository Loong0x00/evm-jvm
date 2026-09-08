// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.
//
// This test deliberately does not use the stock harness. It loads the frozen
// Solidity artifacts, creates every contract with signed transactions, and
// treats class bytes as opaque constructor input to the deployed EVM code.
package stock

import (
	"bytes"
	"crypto/ecdsa"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"math/big"
	"os"
	"reflect"
	"sort"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core"
	"github.com/ethereum/go-ethereum/core/rawdb"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/core/vm"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/params"
	gethtests "github.com/ethereum/go-ethereum/tests"
)

const (
	stockVerifyCreateGas = uint64(8_000_000)
	stockVerifyCallGas   = uint64(2_000_000)
	stockVerifyBlockGas  = uint64(30_000_000)
)

var stockVerifyOne = big.NewInt(1)

type stockVerifyArtifactJSON struct {
	ContractName        string                            `json:"contractName"`
	ABI                 json.RawMessage                   `json:"abi"`
	Bytecode            string                            `json:"bytecode"`
	DeployedBytecode    string                            `json:"deployedBytecode"`
	ImmutableReferences map[string][]stockVerifyImmutable `json:"immutableReferences"`
	Compiler            stockVerifyCompiler               `json:"compiler"`
	SourceHashes        map[string]string                 `json:"sourceHashes"`
}

type stockVerifyCompiler struct {
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
}

type stockVerifyImmutable struct {
	Length int `json:"length"`
	Start  int `json:"start"`
}

type stockVerifyArtifact struct {
	name       string
	abi        abi.ABI
	init       []byte
	runtime    []byte
	immutables map[string][]stockVerifyImmutable
}

type stockVerifyMachine struct {
	Pc          uint32
	Sp          uint8
	Initialized uint8
	Stack       [8]*big.Int
	Locals      [4]*big.Int
	Done        bool
	Result      int32
}

func stockVerifyZeroMachine() stockVerifyMachine {
	m := stockVerifyMachine{}
	for i := range m.Stack {
		m.Stack[i] = new(big.Int)
	}
	for i := range m.Locals {
		m.Locals[i] = new(big.Int)
	}
	return m
}

func stockVerifyCloneMachine(in stockVerifyMachine) stockVerifyMachine {
	out := in
	for i := range out.Stack {
		out.Stack[i] = new(big.Int).Set(in.Stack[i])
	}
	for i := range out.Locals {
		out.Locals[i] = new(big.Int).Set(in.Locals[i])
	}
	return out
}

func stockVerifyTagged(bits uint32) *big.Int {
	return new(big.Int).Or(new(big.Int).Lsh(big.NewInt(1), 64), new(big.Int).SetUint64(uint64(bits)))
}

func stockVerifyLoadArtifact(t *testing.T, name string) stockVerifyArtifact {
	t.Helper()
	path := "runtime/artifacts/" + name + ".json"
	blob, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read frozen %s artifact (runtime/harness integration dependency must be present): %v", name, err)
	}
	var raw stockVerifyArtifactJSON
	if err := json.Unmarshal(blob, &raw); err != nil {
		t.Fatalf("decode %s: %v", path, err)
	}
	if raw.ContractName != name || len(raw.ABI) == 0 || raw.Bytecode == "" || raw.DeployedBytecode == "" {
		t.Fatalf("incomplete %s artifact metadata", name)
	}
	parsed, err := abi.JSON(bytes.NewReader(raw.ABI))
	if err != nil {
		t.Fatalf("parse %s ABI: %v", name, err)
	}
	decode := func(field, text string) []byte {
		t.Helper()
		text = strings.TrimPrefix(text, "0x")
		out, err := hex.DecodeString(text)
		if err != nil {
			t.Fatalf("decode %s %s: %v", name, field, err)
		}
		return out
	}
	if !strings.HasPrefix(raw.Compiler.Version, "0.8.30+commit.73712a01") || !raw.Compiler.Optimizer.Enabled || raw.Compiler.Optimizer.Runs != 200 || !raw.Compiler.ViaIR || raw.Compiler.EVMVersion != "cancun" || raw.Compiler.Metadata.AppendCBOR || raw.Compiler.Metadata.BytecodeHash != "none" {
		t.Fatalf("%s compiler settings are not frozen solc-0.8.30/optimizer200/viaIR/Cancun/metadata-disabled: %+v", name, raw.Compiler)
	}
	if len(raw.SourceHashes) == 0 {
		t.Fatalf("%s artifact has no source hash pins", name)
	}
	for source, hash := range raw.SourceHashes {
		if source == "" || len(hash) != 64 {
			t.Fatalf("%s invalid source hash %q=%q", name, source, hash)
		}
		if _, err := hex.DecodeString(hash); err != nil {
			t.Fatalf("%s invalid source hash %q=%q: %v", name, source, hash, err)
		}
	}
	return stockVerifyArtifact{name, parsed, decode("bytecode", raw.Bytecode), decode("deployedBytecode", raw.DeployedBytecode), raw.ImmutableReferences}
}

type stockVerifyEnv struct {
	t      *testing.T
	state  gethtests.StateTestState
	key    *ecdsa.PrivateKey
	sender common.Address
	signer types.Signer
	block  vm.BlockContext
}

type stockVerifyTxResult struct {
	tx      *types.Transaction
	result  *core.ExecutionResult
	coreErr error
	address common.Address
	logs    []*types.Log
}

func stockVerifyNewEnv(t *testing.T) *stockVerifyEnv {
	t.Helper()
	key, err := crypto.HexToECDSA("7e57c0de7e57c0de7e57c0de7e57c0de7e57c0de7e57c0de7e57c0de7e57c0de")
	if err != nil {
		t.Fatal(err)
	}
	sender := crypto.PubkeyToAddress(key.PublicKey)
	pre := gethtests.MakePreState(rawdb.NewMemoryDatabase(), types.GenesisAlloc{
		sender: {Balance: new(big.Int).Exp(big.NewInt(10), big.NewInt(30), nil)},
	}, false, rawdb.HashScheme)
	random := common.HexToHash("0x53544f434b2d5330")
	block := vm.BlockContext{
		CanTransfer: core.CanTransfer,
		Transfer:    core.Transfer,
		GetHash: func(n uint64) common.Hash {
			return crypto.Keccak256Hash(new(big.Int).SetUint64(n).Bytes())
		},
		Coinbase:    common.HexToAddress("0x0000000000000000000000000000000000001337"),
		BlockNumber: big.NewInt(1),
		Time:        1,
		Difficulty:  new(big.Int),
		BaseFee:     new(big.Int).Set(stockVerifyOne),
		GasLimit:    stockVerifyBlockGas,
		Random:      &random,
	}
	return &stockVerifyEnv{t: t, state: pre, key: key, sender: sender,
		signer: types.MakeSigner(params.AllDevChainProtocolChanges, block.BlockNumber, block.Time), block: block}
}

func (e *stockVerifyEnv) close() { e.state.Close() }

func (e *stockVerifyEnv) apply(to *common.Address, input []byte, gas uint64) stockVerifyTxResult {
	e.t.Helper()
	nonce := e.state.StateDB.GetNonce(e.sender)
	tx := types.NewTx(&types.LegacyTx{Nonce: nonce, To: to, Gas: gas, GasPrice: big.NewInt(2), Data: append([]byte(nil), input...)})
	signed, err := types.SignTx(tx, e.signer, e.key)
	if err != nil {
		e.t.Fatal(err)
	}
	recovered, err := types.Sender(e.signer, signed)
	if err != nil || recovered != e.sender {
		e.t.Fatalf("signed sender recovery: have %s err %v want %s", recovered, err, e.sender)
	}
	msg, err := core.TransactionToMessage(signed, e.signer, e.block.BaseFee)
	if err != nil {
		e.t.Fatalf("TransactionToMessage: %v", err)
	}
	if msg.Nonce != nonce || msg.SkipNonceChecks || msg.SkipTransactionChecks {
		e.t.Fatalf("noncanonical replay message: nonce=%d want=%d skipNonce=%v skipTx=%v", msg.Nonce, nonce, msg.SkipNonceChecks, msg.SkipTransactionChecks)
	}
	e.state.StateDB.SetTxContext(signed.Hash(), 0)
	evm := vm.NewEVM(e.block, e.state.StateDB, params.AllDevChainProtocolChanges, vm.Config{})
	result, coreErr := core.ApplyMessage(evm, msg, new(core.GasPool).AddGas(stockVerifyBlockGas))
	address := common.Address{}
	if to == nil {
		address = crypto.CreateAddress(e.sender, nonce)
	}
	logs := e.state.StateDB.GetLogs(signed.Hash(), e.block.BlockNumber.Uint64(), common.Hash{}, e.block.Time)
	return stockVerifyTxResult{signed, result, coreErr, address, logs}
}

func (e *stockVerifyEnv) mustCreate(init []byte, gas uint64) (common.Address, stockVerifyTxResult) {
	e.t.Helper()
	r := e.apply(nil, init, gas)
	if r.coreErr != nil || r.result == nil || r.result.Err != nil {
		e.t.Fatalf("CREATE failed: core=%v evm=%v return=%x", r.coreErr, stockVerifyResultErr(r.result), stockVerifyResultData(r.result))
	}
	if len(e.state.StateDB.GetCode(r.address)) == 0 {
		e.t.Fatalf("CREATE returned no code at %s", r.address)
	}
	return r.address, r
}

func (e *stockVerifyEnv) mustCall(to common.Address, data []byte, gas uint64) stockVerifyTxResult {
	e.t.Helper()
	r := e.apply(&to, data, gas)
	if r.coreErr != nil || r.result == nil || r.result.Err != nil {
		e.t.Fatalf("CALL %s failed: core=%v evm=%v return=%x", to, r.coreErr, stockVerifyResultErr(r.result), stockVerifyResultData(r.result))
	}
	return r
}

func stockVerifyResultErr(r *core.ExecutionResult) error {
	if r == nil {
		return nil
	}
	return r.Err
}
func stockVerifyResultData(r *core.ExecutionResult) []byte {
	if r == nil {
		return nil
	}
	return r.ReturnData
}

func stockVerifyConstructor(t *testing.T, a stockVerifyArtifact, args ...any) []byte {
	t.Helper()
	packed, err := a.abi.Pack("", args...)
	if err != nil {
		t.Fatalf("pack %s constructor: %v", a.name, err)
	}
	return append(append([]byte(nil), a.init...), packed...)
}

func stockVerifyCallData(t *testing.T, a stockVerifyArtifact, method string, args ...any) []byte {
	t.Helper()
	data, err := a.abi.Pack(method, args...)
	if err != nil {
		t.Fatalf("pack %s.%s: %v", a.name, method, err)
	}
	return data
}

func stockVerifyUnpack(t *testing.T, a stockVerifyArtifact, method string, data []byte) []any {
	t.Helper()
	out, err := a.abi.Unpack(method, data)
	if err != nil {
		t.Fatalf("unpack %s.%s output %x: %v", a.name, method, data, err)
	}
	return out
}

func stockVerifyCustomError(signature string, words ...uint64) []byte {
	out := append([]byte(nil), crypto.Keccak256([]byte(signature))[:4]...)
	for _, word := range words {
		var slot [32]byte
		binary.BigEndian.PutUint64(slot[24:], word)
		out = append(out, slot[:]...)
	}
	return out
}

func stockVerifyAssertRevert(t *testing.T, r stockVerifyTxResult, signature string, words ...uint64) {
	t.Helper()
	if r.coreErr != nil || r.result == nil || !errors.Is(r.result.Err, vm.ErrExecutionReverted) {
		t.Fatalf("want EVM revert %s%v, core=%v evm=%v return=%x", signature, words, r.coreErr, stockVerifyResultErr(r.result), stockVerifyResultData(r.result))
	}
	want := stockVerifyCustomError(signature, words...)
	if !bytes.Equal(r.result.ReturnData, want) {
		t.Fatalf("wrong revert for %s%v\nhave %x\nwant %x", signature, words, r.result.ReturnData, want)
	}
	if len(r.logs) != 0 {
		t.Fatalf("failed transaction emitted %d logs", len(r.logs))
	}
}

func stockVerifyPageHashes(payload []byte) (common.Hash, common.Hash, []byte) {
	code := append([]byte{0}, payload...)
	return crypto.Keccak256Hash(code), crypto.Keccak256Hash(payload), code
}

func stockVerifyDeployPage(t *testing.T, e *stockVerifyEnv, page stockVerifyArtifact, payload []byte) (common.Address, common.Hash, common.Hash) {
	t.Helper()
	addr, _ := e.mustCreate(stockVerifyConstructor(t, page, payload), stockVerifyCreateGas)
	pageHash, payloadHash, wantCode := stockVerifyPageHashes(payload)
	got := e.state.StateDB.GetCode(addr)
	if !bytes.Equal(got, wantCode) {
		t.Fatalf("page deployed bytes differ\nhave %x\nwant %x", got, wantCode)
	}
	if crypto.Keccak256Hash(got) != pageHash {
		t.Fatal("page extcode hash differs from STOP||payload hash")
	}
	return addr, pageHash, payloadHash
}

func stockVerifyRawInit(runtime []byte) []byte {
	if len(runtime) > 0xffff {
		panic("stockVerifyRawInit runtime too large")
	}
	// PUSH2 size; PUSH2 15; PUSH1 0; CODECOPY; PUSH2 size; PUSH1 0; RETURN.
	out := []byte{0x61, byte(len(runtime) >> 8), byte(len(runtime)), 0x61, 0, 15, 0x60, 0, 0x39, 0x61, byte(len(runtime) >> 8), byte(len(runtime)), 0x60, 0, 0xf3}
	return append(out, runtime...)
}

func stockVerifyDeployRaw(t *testing.T, e *stockVerifyEnv, runtime []byte) common.Address {
	t.Helper()
	addr, _ := e.mustCreate(stockVerifyRawInit(runtime), stockVerifyCreateGas)
	if !bytes.Equal(e.state.StateDB.GetCode(addr), runtime) {
		t.Fatal("raw CREATE runtime mismatch")
	}
	return addr
}

func stockVerifyMachineFrom(v any) stockVerifyMachine {
	return *abi.ConvertType(v, new(stockVerifyMachine)).(*stockVerifyMachine)
}

func stockVerifyMachineEqual(a, b stockVerifyMachine) bool {
	if a.Pc != b.Pc || a.Sp != b.Sp || a.Initialized != b.Initialized || a.Done != b.Done || a.Result != b.Result {
		return false
	}
	for i := range a.Stack {
		if a.Stack[i].Cmp(b.Stack[i]) != 0 {
			return false
		}
	}
	for i := range a.Locals {
		if a.Locals[i].Cmp(b.Locals[i]) != 0 {
			return false
		}
	}
	return true
}

func stockVerifyDirty(before, after stockVerifyMachine) uint8 {
	n := 3 // epoch, totalSteps, digest
	if before.Pc != after.Pc {
		n++
	}
	if before.Sp != after.Sp {
		n++
	}
	if before.Initialized != after.Initialized {
		n++
	}
	if before.Done != after.Done {
		n++
	}
	if before.Result != after.Result {
		n++
	}
	for i := range before.Stack {
		if before.Stack[i].Cmp(after.Stack[i]) != 0 {
			n++
		}
	}
	for i := range before.Locals {
		if before.Locals[i].Cmp(after.Locals[i]) != 0 {
			n++
		}
	}
	return uint8(n)
}

// stockVerifyClass is a tiny, trusted test-side classfile generator. The class
// bytes it returns are passed unchanged to ArtifactPage; no generated executable
// or parsed metadata is supplied to TinyJvmStepModule or VMCoordinator.
type stockVerifyClass struct {
	bytes []byte
	mark  map[string]int
	cp    map[string]uint16
}

type stockVerifyCP struct {
	name  string
	tag   byte
	body  []byte
	slots int
}

type stockVerifyClassOptions struct {
	code             []byte
	maxStack         uint16
	maxLocals        uint16
	rootAccess       uint16
	rootName         string
	rootDescriptor   string
	rootCodeCopies   int
	handlers         uint16
	duplicateRoot    bool
	clinit           bool
	allLegalCP       bool
	wideIntegerIndex bool
	classAttribute   bool
	codeAttribute    bool
}

func stockVerifyU2(v uint16) []byte { return []byte{byte(v >> 8), byte(v)} }
func stockVerifyU4(v uint32) []byte {
	return []byte{byte(v >> 24), byte(v >> 16), byte(v >> 8), byte(v)}
}
func stockVerifyCPUtf8(name, s string) stockVerifyCP {
	return stockVerifyCP{name, 1, append(stockVerifyU2(uint16(len(s))), []byte(s)...), 1}
}
func stockVerifyCPRef(name string, tag byte, a, b uint16) stockVerifyCP {
	return stockVerifyCP{name, tag, append(stockVerifyU2(a), stockVerifyU2(b)...), 1}
}

func stockVerifyBuildClass(opt stockVerifyClassOptions) stockVerifyClass {
	if opt.code == nil {
		opt.code = []byte{0x08, 0xac}
	}
	if opt.maxStack == 0 {
		opt.maxStack = 1
	}
	if opt.rootAccess == 0 {
		opt.rootAccess = 0x0009
	}
	if opt.rootName == "" {
		opt.rootName = "run"
	}
	if opt.rootDescriptor == "" {
		opt.rootDescriptor = "()I"
	}
	if opt.rootCodeCopies == 0 {
		opt.rootCodeCopies = 1
	}
	cp := []stockVerifyCP{
		stockVerifyCPUtf8("className", "S0Test"),            // 1
		{"thisClass", 7, stockVerifyU2(1), 1},               // 2
		stockVerifyCPUtf8("objectName", "java/lang/Object"), // 3
		{"superClass", 7, stockVerifyU2(3), 1},              // 4
		stockVerifyCPUtf8("initName", "<init>"),             // 5
		stockVerifyCPUtf8("voidDesc", "()V"),                // 6
		stockVerifyCPUtf8("codeName", "Code"),               // 7
		stockVerifyCPRef("initNT", 12, 5, 6),                // 8
		stockVerifyCPRef("objectInit", 10, 4, 8),            // 9
		stockVerifyCPUtf8("runName", "run"),                 // 10
		stockVerifyCPUtf8("intDesc", "()I"),                 // 11
	}
	if opt.allLegalCP {
		cp = append(cp,
			stockVerifyCP{"integer", 3, []byte{0, 0, 0, 42}, 1},
			stockVerifyCP{"float", 4, []byte{0x3f, 0x80, 0, 0}, 1},
			stockVerifyCP{"long", 5, make([]byte, 8), 2},
			stockVerifyCP{"double", 6, make([]byte, 8), 2},
			stockVerifyCP{"extraClass", 7, stockVerifyU2(1), 1},
			stockVerifyCP{"string", 8, stockVerifyU2(1), 1},
			stockVerifyCPRef("fieldref", 9, 2, 8),
			stockVerifyCPRef("methodref", 10, 4, 8),
			stockVerifyCPRef("interfaceMethodref", 11, 4, 8),
			stockVerifyCPRef("extraNT", 12, 5, 6),
			stockVerifyCP{"methodHandle", 15, []byte{5, 0, 21}, 1},
			stockVerifyCP{"methodType", 16, stockVerifyU2(6), 1},
			stockVerifyCP{"invokeDynamic", 18, []byte{0, 0, 0, 23}, 1},
		)
	}
	if opt.wideIntegerIndex {
		for i := 0; i < 245; i++ {
			cp = append(cp, stockVerifyCPUtf8(fmt.Sprintf("pad%d", i), "x"))
		}
		cp = append(cp, stockVerifyCP{"wideInteger", 3, []byte{0x7f, 0xff, 0xff, 0xff}, 1})
	}
	if opt.clinit {
		cp = append(cp, stockVerifyCPUtf8("clinitName", "<clinit>"))
	}
	if opt.classAttribute || opt.codeAttribute {
		cp = append(cp, stockVerifyCPUtf8("classAttrName", "S0Attr"))
	}

	index := uint16(1)
	cpIndex := make(map[string]uint16)
	for _, ent := range cp {
		cpIndex[ent.name] = index
		index += uint16(ent.slots)
	}
	out := make([]byte, 0, 512)
	marks := make(map[string]int)
	put := func(p []byte) { out = append(out, p...) }
	mark := func(s string) { marks[s] = len(out) }
	put([]byte{0xca, 0xfe, 0xba, 0xbe})
	mark("minor")
	put(stockVerifyU2(0))
	mark("major")
	put(stockVerifyU2(52))
	mark("cpCount")
	put(stockVerifyU2(index))
	for _, ent := range cp {
		mark("cp." + ent.name + ".tag")
		put([]byte{ent.tag})
		mark("cp." + ent.name + ".body")
		put(ent.body)
	}
	mark("classAccess")
	put(stockVerifyU2(0x0021))
	mark("thisIndex")
	put(stockVerifyU2(cpIndex["thisClass"]))
	mark("superIndex")
	put(stockVerifyU2(cpIndex["superClass"]))
	mark("interfaceCount")
	put(stockVerifyU2(0))
	mark("fieldCount")
	put(stockVerifyU2(0))
	methods := 2
	if opt.duplicateRoot {
		methods++
	}
	if opt.clinit {
		methods++
	}
	mark("methodCount")
	put(stockVerifyU2(uint16(methods)))

	writeMethod := func(prefix string, access, name, desc uint16, code []byte, maxStack, maxLocals uint16, copies int, handlers uint16) {
		mark(prefix + ".access")
		put(stockVerifyU2(access))
		mark(prefix + ".name")
		put(stockVerifyU2(name))
		mark(prefix + ".desc")
		put(stockVerifyU2(desc))
		mark(prefix + ".attrs")
		put(stockVerifyU2(uint16(copies)))
		for copyNo := 0; copyNo < copies; copyNo++ {
			p := prefix + fmt.Sprintf(".code%d", copyNo)
			mark(p + ".name")
			put(stockVerifyU2(cpIndex["codeName"]))
			attrLen := uint32(12 + len(code) + int(handlers)*8)
			if prefix == "root" && opt.codeAttribute {
				attrLen += 6
			}
			mark(p + ".attrLen")
			put(stockVerifyU4(attrLen))
			mark(p + ".maxStack")
			put(stockVerifyU2(maxStack))
			mark(p + ".maxLocals")
			put(stockVerifyU2(maxLocals))
			mark(p + ".codeLen")
			put(stockVerifyU4(uint32(len(code))))
			mark(p + ".bytes")
			put(code)
			mark(p + ".handlers")
			put(stockVerifyU2(handlers))
			for i := uint16(0); i < handlers; i++ {
				put(make([]byte, 8))
			}
			mark(p + ".nestedCount")
			if prefix == "root" && opt.codeAttribute {
				put(stockVerifyU2(1))
				mark(p + ".nested.name")
				put(stockVerifyU2(cpIndex["classAttrName"]))
				mark(p + ".nested.len")
				put(stockVerifyU4(0))
			} else {
				put(stockVerifyU2(0))
			}
		}
	}
	writeMethod("ctor", 0x0001, cpIndex["initName"], cpIndex["voidDesc"], []byte{0x2a, 0xb7, 0, 9, 0xb1}, 1, 1, 1, 0)
	rootName := cpIndex["runName"]
	if opt.rootName != "run" {
		rootName = cpIndex["initName"]
	}
	rootDesc := cpIndex["intDesc"]
	if opt.rootDescriptor != "()I" {
		rootDesc = cpIndex["voidDesc"]
	}
	writeMethod("root", opt.rootAccess, rootName, rootDesc, opt.code, opt.maxStack, opt.maxLocals, opt.rootCodeCopies, opt.handlers)
	if opt.duplicateRoot {
		writeMethod("duplicate", 0x0009, cpIndex["runName"], cpIndex["intDesc"], []byte{0x03, 0xac}, 1, 0, 1, 0)
	}
	if opt.clinit {
		writeMethod("clinit", 0x0008, cpIndex["clinitName"], cpIndex["voidDesc"], []byte{0xb1}, 0, 0, 1, 0)
	}
	mark("classAttrs")
	if opt.classAttribute {
		put(stockVerifyU2(1))
		mark("classAttr.name")
		put(stockVerifyU2(cpIndex["classAttrName"]))
		mark("classAttr.len")
		put(stockVerifyU4(0))
	} else {
		put(stockVerifyU2(0))
	}
	return stockVerifyClass{out, marks, cpIndex}
}

func stockVerifyPatchU2(c stockVerifyClass, mark string, value uint16) stockVerifyClass {
	out := stockVerifyClass{append([]byte(nil), c.bytes...), c.mark, c.cp}
	binary.BigEndian.PutUint16(out.bytes[c.mark[mark]:], value)
	return out
}
func stockVerifyPatchU4(c stockVerifyClass, mark string, value uint32) stockVerifyClass {
	out := stockVerifyClass{append([]byte(nil), c.bytes...), c.mark, c.cp}
	binary.BigEndian.PutUint32(out.bytes[c.mark[mark]:], value)
	return out
}
func stockVerifyPatchByte(c stockVerifyClass, offset int, value byte) stockVerifyClass {
	out := stockVerifyClass{append([]byte(nil), c.bytes...), c.mark, c.cp}
	out.bytes[offset] = value
	return out
}

func stockVerifyRequireMethod(t *testing.T, a stockVerifyArtifact, name, sig, mutability string, inputs, outputs int) {
	t.Helper()
	m, ok := a.abi.Methods[name]
	if !ok {
		t.Fatalf("%s ABI missing method %s", a.name, name)
	}
	if m.Sig != sig || m.StateMutability != mutability || len(m.Inputs) != inputs || len(m.Outputs) != outputs {
		t.Fatalf("%s.%s ABI mismatch: sig=%q mutability=%q inputs=%d outputs=%d", a.name, name, m.Sig, m.StateMutability, len(m.Inputs), len(m.Outputs))
	}
}

func stockVerifyRequireError(t *testing.T, a stockVerifyArtifact, name, sig string) {
	t.Helper()
	errABI, ok := a.abi.Errors[name]
	if !ok || errABI.Sig != sig {
		t.Fatalf("%s error %s mismatch: present=%v sig=%q want=%q", a.name, name, ok, errABI.Sig, sig)
	}
}

func stockVerifyCheckMachineTuple(t *testing.T, typ abi.Type) {
	t.Helper()
	if typ.T != abi.TupleTy {
		t.Fatalf("Machine is %s, want tuple", typ.String())
	}
	wantNames := []string{"pc", "sp", "initialized", "stack", "locals", "done", "result"}
	wantTypes := []string{"uint32", "uint8", "uint8", "uint256[8]", "uint256[4]", "bool", "int32"}
	if !reflect.DeepEqual(typ.TupleRawNames, wantNames) || len(typ.TupleElems) != len(wantTypes) {
		t.Fatalf("Machine fields=%v want=%v", typ.TupleRawNames, wantNames)
	}
	for i, elem := range typ.TupleElems {
		if elem.String() != wantTypes[i] {
			t.Fatalf("Machine.%s type=%s want=%s", wantNames[i], elem.String(), wantTypes[i])
		}
	}
}

func stockVerifyGetter(t *testing.T, e *stockVerifyEnv, a stockVerifyArtifact, at common.Address, name string) any {
	t.Helper()
	r := e.mustCall(at, stockVerifyCallData(t, a, name), stockVerifyCallGas)
	out := stockVerifyUnpack(t, a, name, r.result.ReturnData)
	if len(out) != 1 {
		t.Fatalf("%s getter returned %d values", name, len(out))
	}
	return out[0]
}

func TestStockVerifyFrozenABIArtifactsAndOrdinaryDeployment(t *testing.T) {
	page := stockVerifyLoadArtifact(t, "ArtifactPage")
	module := stockVerifyLoadArtifact(t, "TinyJvmStepModule")
	coord := stockVerifyLoadArtifact(t, "VMCoordinator")

	if len(page.abi.Constructor.Inputs) != 1 || page.abi.Constructor.Inputs[0].Type.String() != "bytes" {
		t.Fatalf("ArtifactPage constructor is not constructor(bytes): %v", page.abi.Constructor.Inputs)
	}
	if len(page.abi.Methods) != 0 {
		t.Fatalf("ArtifactPage exposes mutable/callable methods: %v", page.abi.Methods)
	}
	stockVerifyRequireError(t, page, "StockPageError", "StockPageError(uint256)")
	if len(module.abi.Constructor.Inputs) != 0 {
		t.Fatal("TinyJvmStepModule must have no constructor arguments")
	}
	if len(module.abi.Methods) != 2 {
		t.Fatalf("TinyJvmStepModule has extra methods/configuration: %v", module.abi.Methods)
	}
	stockVerifyRequireMethod(t, module, "inspect", "inspect(address,bytes32,bytes32)", "view", 3, 4)
	stockVerifyRequireMethod(t, module, "step", "step(address,bytes32,bytes32,(uint32,uint8,uint8,uint256[8],uint256[4],bool,int32),uint8)", "view", 5, 2)
	stockVerifyCheckMachineTuple(t, module.abi.Methods["step"].Inputs[3].Type)
	stockVerifyCheckMachineTuple(t, module.abi.Methods["step"].Outputs[0].Type)
	stockVerifyRequireError(t, module, "StockPageError", "StockPageError(uint256)")
	stockVerifyRequireError(t, module, "StockClassError", "StockClassError(uint256,uint256)")
	stockVerifyRequireError(t, module, "StockBytecodeError", "StockBytecodeError(uint256,uint256)")

	wantCtor := []string{"address", "address", "bytes32", "bytes32", "bytes32"}
	if len(coord.abi.Constructor.Inputs) != len(wantCtor) {
		t.Fatalf("coordinator constructor arity=%d", len(coord.abi.Constructor.Inputs))
	}
	for i, arg := range coord.abi.Constructor.Inputs {
		if arg.Type.String() != wantCtor[i] {
			t.Fatalf("coordinator constructor arg%d=%s want=%s", i, arg.Type.String(), wantCtor[i])
		}
	}
	if len(coord.abi.Methods) != 7 {
		t.Fatalf("VMCoordinator has extra methods/mutable configuration: %v", coord.abi.Methods)
	}
	stockVerifyRequireMethod(t, coord, "resume", "resume(uint64,uint8,uint8)", "nonpayable", 3, 5)
	stockVerifyRequireMethod(t, coord, "checkpoint", "checkpoint()", "view", 0, 4)
	stockVerifyCheckMachineTuple(t, coord.abi.Methods["checkpoint"].Outputs[3].Type)
	for _, getter := range []struct{ name, sig, typ string }{
		{"module", "module()", "address"}, {"page", "page()", "address"},
		{"expectedModuleHash", "expectedModuleHash()", "bytes32"}, {"expectedPageHash", "expectedPageHash()", "bytes32"},
		{"expectedPayloadHash", "expectedPayloadHash()", "bytes32"},
	} {
		stockVerifyRequireMethod(t, coord, getter.name, getter.sig, "view", 0, 1)
		if coord.abi.Methods[getter.name].Outputs[0].Type.String() != getter.typ {
			t.Fatalf("getter %s type mismatch", getter.name)
		}
	}
	stockVerifyRequireError(t, coord, "StockControlError", "StockControlError(uint256)")
	event, ok := coord.abi.Events["Checkpoint"]
	if !ok || event.Sig != "Checkpoint(uint64,uint64,uint32,uint8,bool,int32,uint8,uint8,bytes32)" || len(event.Inputs) != 9 {
		t.Fatalf("Checkpoint event mismatch: present=%v sig=%q", ok, event.Sig)
	}
	wantEventNames := []string{"epoch", "totalSteps", "pc", "sp", "done", "result", "executed", "dirtyWords", "stateDigest"}
	for i, input := range event.Inputs {
		if input.Name != wantEventNames[i] || input.Indexed != (i == 0) {
			t.Fatalf("Checkpoint field%d=%s indexed=%v", i, input.Name, input.Indexed)
		}
	}

	for _, a := range []stockVerifyArtifact{page, module, coord} {
		if len(a.runtime) > 12*1024 {
			t.Fatalf("%s runtime=%d exceeds 12KiB", a.name, len(a.runtime))
		}
		if len(a.init) > 24*1024 {
			t.Fatalf("%s initcode=%d exceeds 24KiB", a.name, len(a.init))
		}
	}

	e := stockVerifyNewEnv(t)
	defer e.close()
	moduleAddr, moduleTx := e.mustCreate(module.init, stockVerifyCreateGas)
	if moduleTx.result.UsedGas > stockVerifyCreateGas {
		t.Fatal("module CREATE exceeded cap")
	}
	actualModule := e.state.StateDB.GetCode(moduleAddr)
	if !bytes.Equal(actualModule, module.runtime) {
		t.Fatalf("module runtime differs from pinned artifact: actualHash=%s artifactHash=%s", crypto.Keccak256Hash(actualModule), crypto.Keccak256Hash(module.runtime))
	}
	class := stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x10, 0xef, 0xac}, maxStack: 1})
	pageAddr, pageHash, payloadHash := stockVerifyDeployPage(t, e, page, class.bytes)
	moduleHash := crypto.Keccak256Hash(actualModule)
	coordAddr, coordTx := e.mustCreate(stockVerifyConstructor(t, coord, moduleAddr, pageAddr, moduleHash, pageHash, payloadHash), stockVerifyCreateGas)
	if coordTx.result.UsedGas > stockVerifyCreateGas {
		t.Fatal("coordinator CREATE exceeded cap")
	}
	if got := stockVerifyGetter(t, e, coord, coordAddr, "module").(common.Address); got != moduleAddr {
		t.Fatalf("module getter=%s", got)
	}
	if got := stockVerifyGetter(t, e, coord, coordAddr, "page").(common.Address); got != pageAddr {
		t.Fatalf("page getter=%s", got)
	}
	for _, tc := range []struct {
		name string
		want common.Hash
	}{
		{"expectedModuleHash", moduleHash}, {"expectedPageHash", pageHash}, {"expectedPayloadHash", payloadHash},
	} {
		if got := stockVerifyGetter(t, e, coord, coordAddr, tc.name).([32]byte); common.Hash(got) != tc.want {
			t.Fatalf("%s getter=%x want=%s", tc.name, got, tc.want)
		}
	}

	actualCoord := append([]byte(nil), e.state.StateDB.GetCode(coordAddr)...)
	template := append([]byte(nil), coord.runtime...)
	if len(actualCoord) != len(template) || len(coord.immutables) == 0 {
		t.Fatalf("coordinator runtime/immutable metadata mismatch: actual=%d template=%d refs=%d", len(actualCoord), len(template), len(coord.immutables))
	}
	allowed := map[[32]byte]bool{}
	for _, v := range []common.Hash{moduleHash, pageHash, payloadHash} {
		allowed[[32]byte(v)] = true
	}
	var moduleWord, pageWord [32]byte
	copy(moduleWord[12:], moduleAddr[:])
	copy(pageWord[12:], pageAddr[:])
	allowed[moduleWord] = true
	allowed[pageWord] = true
	refCount := 0
	keys := make([]string, 0, len(coord.immutables))
	for key := range coord.immutables {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	for _, key := range keys {
		for _, ref := range coord.immutables[key] {
			if ref.Length != 32 || ref.Start < 0 || ref.Start+ref.Length > len(template) {
				t.Fatalf("bad immutable reference %s: %+v", key, ref)
			}
			var word [32]byte
			copy(word[:], actualCoord[ref.Start:ref.Start+32])
			if !allowed[word] {
				t.Fatalf("immutable %s at %d has unknown value %x", key, ref.Start, word)
			}
			copy(actualCoord[ref.Start:ref.Start+32], template[ref.Start:ref.Start+32])
			refCount++
		}
	}
	if refCount < 5 || !bytes.Equal(actualCoord, template) {
		t.Fatalf("coordinator differs outside compiler immutable references (refs=%d)", refCount)
	}
	t.Logf("deployed module bytes=%d codehash=%s createGas=%d; page bytes=%d codehash=%s; coordinator bytes=%d codehash=%s createGas=%d",
		len(e.state.StateDB.GetCode(moduleAddr)), moduleHash, moduleTx.result.UsedGas,
		len(e.state.StateDB.GetCode(pageAddr)), pageHash, len(e.state.StateDB.GetCode(coordAddr)),
		crypto.Keccak256Hash(e.state.StateDB.GetCode(coordAddr)), coordTx.result.UsedGas)

	inspect := e.mustCall(moduleAddr, stockVerifyCallData(t, module, "inspect", pageAddr, pageHash, payloadHash), stockVerifyCallGas)
	values := stockVerifyUnpack(t, module, "inspect", inspect.result.ReturnData)
	if values[0].(uint32) != uint32(class.mark["root.code0.bytes"]) || values[1].(uint32) != 3 || values[2].(uint8) != 1 || values[3].(uint8) != 0 {
		t.Fatalf("inspect metadata=%v, want offset=%d length=3 stack=1 locals=0", values, class.mark["root.code0.bytes"])
	}
}

func TestStockVerifyPageBoundaryAndHashes(t *testing.T) {
	page := stockVerifyLoadArtifact(t, "ArtifactPage")
	module := stockVerifyLoadArtifact(t, "TinyJvmStepModule")
	e := stockVerifyNewEnv(t)
	defer e.close()
	moduleAddr, _ := e.mustCreate(module.init, stockVerifyCreateGas)

	for _, size := range []int{0, 4097} {
		nonce := e.state.StateDB.GetNonce(e.sender)
		r := e.apply(nil, stockVerifyConstructor(t, page, make([]byte, size)), stockVerifyCreateGas)
		stockVerifyAssertRevert(t, r, "StockPageError(uint256)", 1)
		if len(e.state.StateDB.GetCode(crypto.CreateAddress(e.sender, nonce))) != 0 {
			t.Fatalf("rejected page size %d left contract code", size)
		}
	}

	// The EIP-3541-looking byte is payload, never the first deployed byte.
	payload := []byte{0xef, 0xca, 0xfe, 0xba, 0xbe}
	pageAddr, pageHash, payloadHash := stockVerifyDeployPage(t, e, page, payload)
	inspect := func(address common.Address, ph, payh common.Hash) stockVerifyTxResult {
		return e.apply(&moduleAddr, stockVerifyCallData(t, module, "inspect", address, ph, payh), stockVerifyCallGas)
	}
	// This payload is not a class, so reaching StockClassError proves page prefix,
	// length and both hashes passed. A page-level error here would be a regression.
	r := inspect(pageAddr, pageHash, payloadHash)
	stockVerifyAssertRevert(t, r, "StockClassError(uint256,uint256)", 1, 0)

	bad := pageHash
	bad[0] ^= 1
	stockVerifyAssertRevert(t, inspect(pageAddr, bad, payloadHash), "StockPageError(uint256)", 3)
	badPayload := payloadHash
	badPayload[0] ^= 1
	stockVerifyAssertRevert(t, inspect(pageAddr, pageHash, badPayload), "StockPageError(uint256)", 4)

	wrongPrefix := stockVerifyDeployRaw(t, e, []byte{0x01, 0xca})
	wrongPrefixHash := crypto.Keccak256Hash(e.state.StateDB.GetCode(wrongPrefix))
	stockVerifyAssertRevert(t, inspect(wrongPrefix, wrongPrefixHash, crypto.Keccak256Hash([]byte{0xca})), "StockPageError(uint256)", 2)
	short := stockVerifyDeployRaw(t, e, []byte{0x00})
	stockVerifyAssertRevert(t, inspect(short, crypto.Keccak256Hash([]byte{0}), crypto.Keccak256Hash(nil)), "StockPageError(uint256)", 1)
	long := stockVerifyDeployRaw(t, e, make([]byte, 4098))
	stockVerifyAssertRevert(t, inspect(long, crypto.Keccak256Hash(make([]byte, 4098)), common.Hash{}), "StockPageError(uint256)", 1)
}

type stockVerifyClassErrorCase struct {
	name   string
	class  stockVerifyClass
	code   uint64
	offset uint64
}

func TestStockVerifyClassParserExactErrors(t *testing.T) {
	page := stockVerifyLoadArtifact(t, "ArtifactPage")
	module := stockVerifyLoadArtifact(t, "TinyJvmStepModule")
	e := stockVerifyNewEnv(t)
	defer e.close()
	moduleAddr, _ := e.mustCreate(module.init, stockVerifyCreateGas)
	base := stockVerifyBuildClass(stockVerifyClassOptions{})

	copyClass := func(c stockVerifyClass, b []byte) stockVerifyClass {
		return stockVerifyClass{append([]byte(nil), b...), c.mark, c.cp}
	}
	invalidName := stockVerifyPatchByte(base, base.mark["cp.className.body"]+2+2, '.')
	badTag := stockVerifyPatchByte(base, base.mark["cp.className.tag"], 2)
	magic := stockVerifyPatchByte(base, 0, 0)
	version := stockVerifyPatchU2(base, "major", 53)
	truncated := copyClass(base, base.bytes[:len(base.bytes)-1])
	trailing := copyClass(base, append(append([]byte(nil), base.bytes...), 0))
	lastLong := stockVerifyClass{bytes: append([]byte{0xca, 0xfe, 0xba, 0xbe, 0, 0, 0, 52, 0, 2, 5}, make([]byte, 8)...), mark: map[string]int{}, cp: map[string]uint16{}}
	code257 := stockVerifyBuildClass(stockVerifyClassOptions{code: make([]byte, 257), maxStack: 1})
	clinit := stockVerifyBuildClass(stockVerifyClassOptions{clinit: true})
	duplicate := stockVerifyBuildClass(stockVerifyClassOptions{duplicateRoot: true})
	missing := stockVerifyBuildClass(stockVerifyClassOptions{rootName: "<init>"})
	badDesc := stockVerifyBuildClass(stockVerifyClassOptions{rootDescriptor: "()V"})
	badAccess := stockVerifyBuildClass(stockVerifyClassOptions{rootAccess: 0x0001})
	noCode := stockVerifyPatchU2(base, "root.attrs", 0)
	twoCode := stockVerifyBuildClass(stockVerifyClassOptions{rootCodeCopies: 2})
	handler := stockVerifyBuildClass(stockVerifyClassOptions{handlers: 1})
	maxStack := stockVerifyPatchU2(base, "root.code0.maxStack", 9)
	maxLocals := stockVerifyPatchU2(base, "root.code0.maxLocals", 5)
	outerIndex := stockVerifyPatchU2(base, "ctor.name", 0)
	outerLength := stockVerifyPatchU4(base, "ctor.code0.attrLen", 0xffffffff)
	classAttr := stockVerifyBuildClass(stockVerifyClassOptions{classAttribute: true})
	classAttr = stockVerifyPatchU4(classAttr, "classAttr.len", 1)
	codeAttr := stockVerifyBuildClass(stockVerifyClassOptions{codeAttribute: true})
	codeAttr = stockVerifyPatchU4(codeAttr, "root.code0.nested.len", 1)

	cases := []stockVerifyClassErrorCase{
		{"truncated-outer", truncated, 1, uint64(len(base.bytes) - 2)},
		{"trailing-byte", trailing, 1, uint64(len(base.bytes))},
		{"magic", magic, 2, 0},
		{"version", version, 2, uint64(base.mark["minor"])},
		{"cp-count-zero", stockVerifyPatchU2(base, "cpCount", 0), 3, uint64(base.mark["cpCount"])},
		{"cp-count-cap", stockVerifyPatchU2(base, "cpCount", 513), 3, uint64(base.mark["cpCount"])},
		{"cp-illegal-tag", badTag, 3, uint64(base.mark["cp.className.tag"])},
		{"cp-truncated", copyClass(base, base.bytes[:base.mark["cp.className.body"]+3]), 1, uint64(base.mark["cp.className.body"] + 2)},
		{"cp-two-slot-at-end", lastLong, 3, 10},
		{"cp-this-wrong-tag", stockVerifyPatchU2(base, "thisIndex", base.cp["className"]), 3, uint64(base.mark["thisIndex"])},
		{"cp-index-zero", stockVerifyPatchU2(base, "thisIndex", 0), 3, uint64(base.mark["thisIndex"])},
		{"cp-bad-name", invalidName, 3, uint64(base.mark["thisIndex"])},
		{"class-flags", stockVerifyPatchU2(base, "classAccess", 0x0201), 4, uint64(base.mark["classAccess"])},
		{"super-zero", stockVerifyPatchU2(base, "superIndex", 0), 3, uint64(base.mark["superIndex"])},
		{"interfaces", stockVerifyPatchU2(base, "interfaceCount", 1), 4, uint64(base.mark["classAccess"])},
		{"fields", stockVerifyPatchU2(base, "fieldCount", 1), 4, uint64(base.mark["fieldCount"])},
		{"clinit", clinit, 4, uint64(clinit.mark["clinit.access"])},
		{"root-missing", missing, 5, uint64(missing.mark["methodCount"])},
		{"root-ambiguous", duplicate, 5, uint64(duplicate.mark["duplicate.access"])},
		{"root-access", badAccess, 5, uint64(badAccess.mark["root.access"])},
		{"root-descriptor", badDesc, 5, uint64(badDesc.mark["root.desc"])},
		{"code-missing", noCode, 6, uint64(noCode.mark["root.attrs"])},
		{"code-duplicate", twoCode, 6, uint64(twoCode.mark["root.code1.name"])},
		{"code-length-cap", code257, 6, uint64(code257.mark["root.code0.codeLen"])},
		{"max-stack-cap", maxStack, 6, uint64(maxStack.mark["root.code0.maxStack"])},
		{"max-locals-cap", maxLocals, 6, uint64(maxLocals.mark["root.code0.maxLocals"])},
		{"handlers", handler, 6, uint64(handler.mark["root.code0.handlers"])},
		{"outer-member-index", outerIndex, 3, uint64(outerIndex.mark["ctor.name"])},
		{"outer-attribute-length", outerLength, 1, uint64(outerLength.mark["ctor.code0.maxStack"])},
		{"class-attribute-length", classAttr, 1, uint64(classAttr.mark["classAttr.len"] + 4)},
		{"code-nested-attribute-length", codeAttr, 1, uint64(codeAttr.mark["root.code0.nested.len"] + 4)},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			pageAddr, pageHash, payloadHash := stockVerifyDeployPage(t, e, page, tc.class.bytes)
			r := e.apply(&moduleAddr, stockVerifyCallData(t, module, "inspect", pageAddr, pageHash, payloadHash), stockVerifyCallGas)
			stockVerifyAssertRevert(t, r, "StockClassError(uint256,uint256)", tc.code, tc.offset)
		})
	}

	// All legal major-52 CP widths, two-slot entries, an unknown valid class
	// attribute and the javac-like constructor's unsupported body are skipped,
	// not entered as selected code.
	for _, valid := range []stockVerifyClass{
		stockVerifyBuildClass(stockVerifyClassOptions{allLegalCP: true}),
		stockVerifyBuildClass(stockVerifyClassOptions{classAttribute: true}),
		stockVerifyBuildClass(stockVerifyClassOptions{codeAttribute: true}),
	} {
		pageAddr, pageHash, payloadHash := stockVerifyDeployPage(t, e, page, valid.bytes)
		r := e.mustCall(moduleAddr, stockVerifyCallData(t, module, "inspect", pageAddr, pageHash, payloadHash), stockVerifyCallGas)
		if len(stockVerifyUnpack(t, module, "inspect", r.result.ReturnData)) != 4 {
			t.Fatal("valid class inspect arity")
		}
	}
}

func stockVerifyInspectResult(t *testing.T, e *stockVerifyEnv, pageArt, moduleArt stockVerifyArtifact, moduleAddr common.Address, class stockVerifyClass) (common.Address, common.Hash, common.Hash, stockVerifyTxResult) {
	t.Helper()
	pageAddr, pageHash, payloadHash := stockVerifyDeployPage(t, e, pageArt, class.bytes)
	r := e.apply(&moduleAddr, stockVerifyCallData(t, moduleArt, "inspect", pageAddr, pageHash, payloadHash), stockVerifyCallGas)
	return pageAddr, pageHash, payloadHash, r
}

func stockVerifyStepResult(t *testing.T, e *stockVerifyEnv, module stockVerifyArtifact, moduleAddr, pageAddr common.Address, pageHash, payloadHash common.Hash, machine stockVerifyMachine, budget uint8) stockVerifyTxResult {
	t.Helper()
	return e.apply(&moduleAddr, stockVerifyCallData(t, module, "step", pageAddr, pageHash, payloadHash, machine, budget), stockVerifyCallGas)
}

func TestStockVerifySelectedBytecodePredecodeAndMachine(t *testing.T) {
	page := stockVerifyLoadArtifact(t, "ArtifactPage")
	module := stockVerifyLoadArtifact(t, "TinyJvmStepModule")
	e := stockVerifyNewEnv(t)
	defer e.close()
	moduleAddr, _ := e.mustCreate(module.init, stockVerifyCreateGas)

	predecode := []struct {
		name     string
		class    stockVerifyClass
		code, pc uint64
	}{
		{"unsupported-unreachable", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x03, 0xac, 0xb1}}), 6, 2},
		{"truncated-bipush", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x10}}), 2, 0},
		{"truncated-sipush", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x11, 0x01}}), 2, 0},
		{"truncated-iinc", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x84, 0x00}, maxLocals: 1}), 2, 0},
		{"local-index", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x15, 0x04, 0xac}, maxLocals: 4}), 8, 0},
		{"implicit-local-index", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x1d, 0xac}, maxLocals: 3}), 8, 0},
	}
	for _, tc := range predecode {
		t.Run(tc.name, func(t *testing.T) {
			_, _, _, r := stockVerifyInspectResult(t, e, page, module, moduleAddr, tc.class)
			stockVerifyAssertRevert(t, r, "StockBytecodeError(uint256,uint256)", tc.code, tc.pc)
		})
	}

	legalCP := stockVerifyBuildClass(stockVerifyClassOptions{allLegalCP: true, code: []byte{0x12, 12, 0xac}})
	_, _, _, okInspect := stockVerifyInspectResult(t, e, page, module, moduleAddr, legalCP)
	if okInspect.coreErr != nil || okInspect.result.Err != nil {
		t.Fatalf("ldc integer inspect failed: %v %v", okInspect.coreErr, okInspect.result.Err)
	}
	wrongTag := stockVerifyBuildClass(stockVerifyClassOptions{allLegalCP: true, code: []byte{0x12, 13, 0xac}})
	_, _, _, wrong := stockVerifyInspectResult(t, e, page, module, moduleAddr, wrongTag)
	stockVerifyAssertRevert(t, wrong, "StockBytecodeError(uint256,uint256)", 6, 0)
	badIndex := stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x12, 0, 0xac}})
	_, _, _, wrong = stockVerifyInspectResult(t, e, page, module, moduleAddr, badIndex)
	stockVerifyAssertRevert(t, wrong, "StockBytecodeError(uint256,uint256)", 6, 0)

	wide := stockVerifyBuildClass(stockVerifyClassOptions{wideIntegerIndex: true, code: []byte{0x13, 0x01, 0x01, 0xac}})
	if wide.cp["wideInteger"] != 257 {
		t.Fatalf("wide ldc CP index=%d want257", wide.cp["wideInteger"])
	}
	pageAddr, pageHash, payloadHash, r := stockVerifyInspectResult(t, e, page, module, moduleAddr, wide)
	if r.coreErr != nil || r.result.Err != nil {
		t.Fatalf("ldc_w inspect failed: %v %v", r.coreErr, r.result.Err)
	}

	zero := stockVerifyZeroMachine()
	step := stockVerifyStepResult(t, e, module, moduleAddr, pageAddr, pageHash, payloadHash, zero, 16)
	if step.coreErr != nil || step.result.Err != nil {
		t.Fatalf("ldc_w step failed: %v %v", step.coreErr, step.result.Err)
	}
	out := stockVerifyUnpack(t, module, "step", step.result.ReturnData)
	got := stockVerifyMachineFrom(out[0])
	if out[1].(uint8) != 2 || !got.Done || got.Result != 2147483647 || got.Pc != 4 || got.Sp != 0 {
		t.Fatalf("ldc_w terminal machine=%+v executed=%v", got, out[1])
	}

	executionErrors := []struct {
		name     string
		class    stockVerifyClass
		machine  stockVerifyMachine
		code, pc uint64
	}{
		{"underflow", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x60, 0xac}, maxStack: 2}), zero, 3, 0},
		{"return-shape", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x03, 0x04, 0xac}, maxStack: 2}), zero, 5, 2},
		{"fallthrough", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x03}}), zero, 7, 1},
		{"stack-capacity", stockVerifyPatchU2(stockVerifyBuildClass(stockVerifyClassOptions{}), "root.code0.maxStack", 0), zero, 9, 0},
		{"uninitialized-load", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x1a, 0xac}, maxLocals: 1}), zero, 11, 0},
		{"uninitialized-iinc", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x84, 0, 1, 0x1a, 0xac}, maxLocals: 1}), zero, 11, 0},
	}
	for _, tc := range executionErrors {
		t.Run(tc.name, func(t *testing.T) {
			pa, ph, pvh, inspected := stockVerifyInspectResult(t, e, page, module, moduleAddr, tc.class)
			if inspected.coreErr != nil || inspected.result.Err != nil {
				t.Fatalf("inspect unexpectedly failed: %v %v", inspected.coreErr, inspected.result.Err)
			}
			failed := stockVerifyStepResult(t, e, module, moduleAddr, pa, ph, pvh, tc.machine, 16)
			stockVerifyAssertRevert(t, failed, "StockBytecodeError(uint256,uint256)", tc.code, tc.pc)
		})
	}

	bipush := stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x10, 7, 0xac}})
	pa, ph, pvh, inspected := stockVerifyInspectResult(t, e, page, module, moduleAddr, bipush)
	if inspected.result.Err != nil {
		t.Fatal(inspected.result.Err)
	}
	nonStart := stockVerifyZeroMachine()
	nonStart.Pc = 1
	stockVerifyAssertRevert(t, stockVerifyStepResult(t, e, module, moduleAddr, pa, ph, pvh, nonStart, 1), "StockBytecodeError(uint256,uint256)", 12, 1)
	outOfRange := stockVerifyZeroMachine()
	outOfRange.Pc = 3
	stockVerifyAssertRevert(t, stockVerifyStepResult(t, e, module, moduleAddr, pa, ph, pvh, outOfRange, 1), "StockBytecodeError(uint256,uint256)", 12, 3)

	malformed := []struct {
		name   string
		mutate func(*stockVerifyMachine)
	}{
		{"sp", func(m *stockVerifyMachine) { m.Sp = 9 }},
		{"initialized-high-bits", func(m *stockVerifyMachine) { m.Initialized = 0x10 }},
		{"active-untagged", func(m *stockVerifyMachine) { m.Sp = 1; m.Stack[0].SetUint64(7) }},
		{"inactive-stack", func(m *stockVerifyMachine) { m.Stack[7].Set(stockVerifyTagged(1)) }},
		{"uninitialized-local-cell", func(m *stockVerifyMachine) { m.Locals[0].Set(stockVerifyTagged(1)) }},
		{"nonzero-result", func(m *stockVerifyMachine) { m.Result = 1 }},
		{"premature-done", func(m *stockVerifyMachine) { m.Done = true }},
		{"tag-high-bits", func(m *stockVerifyMachine) { m.Sp = 1; m.Stack[0].Lsh(big.NewInt(1), 200) }},
	}
	for _, tc := range malformed {
		t.Run("machine-"+tc.name, func(t *testing.T) {
			m := stockVerifyZeroMachine()
			tc.mutate(&m)
			stockVerifyAssertRevert(t, stockVerifyStepResult(t, e, module, moduleAddr, pa, ph, pvh, m, 1), "StockBytecodeError(uint256,uint256)", 14, 0)
		})
	}

	one := stockVerifyStepResult(t, e, module, moduleAddr, pa, ph, pvh, zero, 1)
	oneOut := stockVerifyUnpack(t, module, "step", one.result.ReturnData)
	oneMachine := stockVerifyMachineFrom(oneOut[0])
	wantOne := stockVerifyZeroMachine()
	wantOne.Pc = 2
	wantOne.Sp = 1
	wantOne.Stack[0] = stockVerifyTagged(7)
	if oneOut[1].(uint8) != 1 || !stockVerifyMachineEqual(oneMachine, wantOne) {
		t.Fatalf("one-step machine=%+v executed=%v", oneMachine, oneOut[1])
	}
	last := stockVerifyStepResult(t, e, module, moduleAddr, pa, ph, pvh, oneMachine, 1)
	lastOut := stockVerifyUnpack(t, module, "step", last.result.ReturnData)
	terminal := stockVerifyMachineFrom(lastOut[0])
	wantTerminal := stockVerifyZeroMachine()
	wantTerminal.Pc = 3
	wantTerminal.Done = true
	wantTerminal.Result = 7
	if lastOut[1].(uint8) != 1 || !stockVerifyMachineEqual(terminal, wantTerminal) {
		t.Fatalf("terminal machine=%+v", terminal)
	}
}

func stockVerifyRunDirect(t *testing.T, e *stockVerifyEnv, page, module stockVerifyArtifact, moduleAddr common.Address, class stockVerifyClass) stockVerifyMachine {
	t.Helper()
	pa, ph, pvh, inspected := stockVerifyInspectResult(t, e, page, module, moduleAddr, class)
	if inspected.coreErr != nil || inspected.result.Err != nil {
		t.Fatalf("inspect: core=%v evm=%v data=%x", inspected.coreErr, inspected.result.Err, inspected.result.ReturnData)
	}
	r := stockVerifyStepResult(t, e, module, moduleAddr, pa, ph, pvh, stockVerifyZeroMachine(), 16)
	if r.coreErr != nil || r.result.Err != nil {
		t.Fatalf("step: core=%v evm=%v data=%x", r.coreErr, r.result.Err, r.result.ReturnData)
	}
	out := stockVerifyUnpack(t, module, "step", r.result.ReturnData)
	m := stockVerifyMachineFrom(out[0])
	if !m.Done {
		t.Fatalf("direct execution paused: %+v", m)
	}
	return m
}

func TestStockVerifyJavaInt32AndLocalInitialization(t *testing.T) {
	page := stockVerifyLoadArtifact(t, "ArtifactPage")
	module := stockVerifyLoadArtifact(t, "TinyJvmStepModule")
	e := stockVerifyNewEnv(t)
	defer e.close()
	moduleAddr, _ := e.mustCreate(module.init, stockVerifyCreateGas)
	wide := func(value uint32, tail []byte, locals uint16) stockVerifyClass {
		c := stockVerifyBuildClass(stockVerifyClassOptions{wideIntegerIndex: true, code: append([]byte{0x13, 1, 1}, tail...), maxStack: 2, maxLocals: locals})
		binary.BigEndian.PutUint32(c.bytes[c.mark["cp.wideInteger.body"]:], value)
		return c
	}
	cases := []struct {
		name  string
		class stockVerifyClass
		want  int32
	}{
		{"nop-iconst-m1", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x00, 0x02, 0xac}}), -1},
		{"iconst-0", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x03, 0xac}}), 0},
		{"iconst-1", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x04, 0xac}}), 1},
		{"iconst-2", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x05, 0xac}}), 2},
		{"iconst-3", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x06, 0xac}}), 3},
		{"iconst-4", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x07, 0xac}}), 4},
		{"iconst-5", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x08, 0xac}}), 5},
		{"generic-load-store", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x07, 0x36, 0x00, 0x15, 0x00, 0xac}, maxLocals: 1}), 4},
		{"local-0", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x03, 0x3b, 0x1a, 0xac}, maxLocals: 1}), 0},
		{"local-1", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x04, 0x3c, 0x1b, 0xac}, maxLocals: 2}), 1},
		{"local-2", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x05, 0x3d, 0x1c, 0xac}, maxLocals: 3}), 2},
		{"local-3", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x06, 0x3e, 0x1d, 0xac}, maxLocals: 4}), 3},
		{"isub", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x08, 0x05, 0x64, 0xac}, maxStack: 2}), 3},
		{"negative-iinc", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x03, 0x3b, 0x84, 0x00, 0xff, 0x1a, 0xac}, maxLocals: 1}), -1},
		{"overflow-add", wide(0x7fffffff, []byte{0x04, 0x60, 0xac}, 0), -2147483648},
		{"overflow-multiply", wide(0x7fffffff, []byte{0x05, 0x68, 0xac}, 0), -2},
		{"minimum-negation", wide(0x80000000, []byte{0x74, 0xac}, 0), -2147483648},
		{"iinc-wrap", wide(0x7fffffff, []byte{0x3b, 0x84, 0, 1, 0x1a, 0xac}, 1), -2147483648},
		{"signed-immediates", stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x10, 0xef, 0x11, 0xff, 0, 0x60, 0xac}, maxStack: 2}), -273},
		{"ldc", stockVerifyBuildClass(stockVerifyClassOptions{allLegalCP: true, code: []byte{0x12, 12, 0xac}}), 42},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := stockVerifyRunDirect(t, e, page, module, moduleAddr, tc.class)
			if got.Result != tc.want || got.Sp != 0 {
				t.Fatalf("result=%d want=%d machine=%+v", got.Result, tc.want, got)
			}
		})
	}
}

func stockVerifyCheckpoint(t *testing.T, e *stockVerifyEnv, coord stockVerifyArtifact, at common.Address) (uint64, uint64, common.Hash, stockVerifyMachine) {
	t.Helper()
	r := e.mustCall(at, stockVerifyCallData(t, coord, "checkpoint"), stockVerifyCallGas)
	out := stockVerifyUnpack(t, coord, "checkpoint", r.result.ReturnData)
	return out[0].(uint64), out[1].(uint64), common.Hash(out[2].([32]byte)), stockVerifyMachineFrom(out[3])
}

func stockVerifyDigest(t *testing.T, module stockVerifyArtifact, payloadHash, moduleHash common.Hash, m stockVerifyMachine, epoch, total uint64) common.Hash {
	t.Helper()
	u32, _ := abi.NewType("uint32", "", nil)
	b32, _ := abi.NewType("bytes32", "", nil)
	u64, _ := abi.NewType("uint64", "", nil)
	args := abi.Arguments{{Type: u32}, {Type: b32}, {Type: b32}, {Type: module.abi.Methods["step"].Inputs[3].Type}, {Type: u64}, {Type: u64}}
	packed, err := args.Pack(uint32(1), payloadHash, moduleHash, m, epoch, total)
	if err != nil {
		t.Fatal(err)
	}
	return crypto.Keccak256Hash(packed)
}

func stockVerifyCheckEvent(t *testing.T, coord stockVerifyArtifact, r stockVerifyTxResult, epoch, total uint64, m stockVerifyMachine, executed, dirty uint8, digest common.Hash) {
	t.Helper()
	if len(r.logs) != 1 {
		t.Fatalf("resume logs=%d want1", len(r.logs))
	}
	log := r.logs[0]
	event := coord.abi.Events["Checkpoint"]
	if len(log.Topics) != 2 || log.Topics[0] != event.ID || new(big.Int).SetBytes(log.Topics[1][:]).Uint64() != epoch {
		t.Fatalf("Checkpoint topics=%v", log.Topics)
	}
	vals, err := event.Inputs.NonIndexed().Unpack(log.Data)
	if err != nil {
		t.Fatal(err)
	}
	if vals[0].(uint64) != total || vals[1].(uint32) != m.Pc || vals[2].(uint8) != m.Sp || vals[3].(bool) != m.Done || vals[4].(int32) != m.Result || vals[5].(uint8) != executed || vals[6].(uint8) != dirty || common.Hash(vals[7].([32]byte)) != digest {
		t.Fatalf("Checkpoint data=%v", vals)
	}
}

func stockVerifyResume(t *testing.T, e *stockVerifyEnv, coord stockVerifyArtifact, at common.Address, epoch uint64, steps, dirty uint8, gas uint64) stockVerifyTxResult {
	t.Helper()
	return e.apply(&at, stockVerifyCallData(t, coord, "resume", epoch, steps, dirty), gas)
}

func stockVerifyBalance(e *stockVerifyEnv) *big.Int {
	return e.state.StateDB.GetBalance(e.sender).ToBig()
}

func stockVerifyAssertFailedRollback(t *testing.T, e *stockVerifyEnv, coord stockVerifyArtifact, at common.Address, beforeEpoch, beforeTotal uint64, beforeDigest common.Hash, before stockVerifyMachine, r stockVerifyTxResult) {
	t.Helper()
	if len(r.logs) != 0 {
		t.Fatalf("failed resume emitted %d logs", len(r.logs))
	}
	epoch, total, digest, after := stockVerifyCheckpoint(t, e, coord, at)
	if epoch != beforeEpoch || total != beforeTotal || digest != beforeDigest || !stockVerifyMachineEqual(before, after) {
		t.Fatalf("failed resume committed state: before=(%d,%d,%s,%+v) after=(%d,%d,%s,%+v)", beforeEpoch, beforeTotal, beforeDigest, before, epoch, total, digest, after)
	}
}

func TestStockVerifyCoordinatorAtomicityBudgetsDigestAndTerminal(t *testing.T) {
	page := stockVerifyLoadArtifact(t, "ArtifactPage")
	module := stockVerifyLoadArtifact(t, "TinyJvmStepModule")
	coord := stockVerifyLoadArtifact(t, "VMCoordinator")
	e := stockVerifyNewEnv(t)
	defer e.close()
	moduleAddr, _ := e.mustCreate(module.init, stockVerifyCreateGas)
	moduleHash := crypto.Keccak256Hash(e.state.StateDB.GetCode(moduleAddr))
	class := stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0x08, 0x3b, 0x1a, 0x10, 7, 0x60, 0xac}, maxStack: 2, maxLocals: 1})
	pageAddr, pageHash, payloadHash := stockVerifyDeployPage(t, e, page, class.bytes)
	coordAddr, _ := e.mustCreate(stockVerifyConstructor(t, coord, moduleAddr, pageAddr, moduleHash, pageHash, payloadHash), stockVerifyCreateGas)
	zero := stockVerifyZeroMachine()
	epoch, total, digest, m := stockVerifyCheckpoint(t, e, coord, coordAddr)
	if epoch != 0 || total != 0 || !stockVerifyMachineEqual(m, zero) || digest != stockVerifyDigest(t, module, payloadHash, moduleHash, zero, 0, 0) {
		t.Fatalf("initial checkpoint=(%d,%d,%s,%+v)", epoch, total, digest, m)
	}

	// Both failure modes are exercised before the first checkpoint commit. A
	// custom reserve failure is not relabelled as EVM OOG; both advance the EOA
	// nonce/charge gas while the coordinator and logs roll back.
	for _, probe := range []struct {
		name    string
		gas     uint64
		reserve bool
	}{{"low-reserve", 750_000, true}, {"actual-oog", 0, false}} {
		data := stockVerifyCallData(t, coord, "resume", uint64(0), uint8(3), uint8(32))
		gas := probe.gas
		if gas == 0 {
			floor, err := core.FloorDataGas(data)
			if err != nil {
				t.Fatal(err)
			}
			gas = floor
		}
		nonce := e.state.StateDB.GetNonce(e.sender)
		balance := stockVerifyBalance(e)
		r := e.apply(&coordAddr, data, gas)
		if probe.reserve {
			stockVerifyAssertRevert(t, r, "StockControlError(uint256)", 5)
		} else if r.coreErr != nil || r.result == nil || !errors.Is(r.result.Err, vm.ErrOutOfGas) || len(r.result.ReturnData) != 0 {
			t.Fatalf("actual OOG identity: core=%v evm=%v data=%x", r.coreErr, stockVerifyResultErr(r.result), stockVerifyResultData(r.result))
		}
		if e.state.StateDB.GetNonce(e.sender) != nonce+1 || stockVerifyBalance(e).Cmp(balance) >= 0 {
			t.Fatalf("failed %s did not preserve normal sender nonce/gas semantics", probe.name)
		}
		stockVerifyAssertFailedRollback(t, e, coord, coordAddr, epoch, total, digest, m, r)
	}

	for _, args := range [][3]uint64{{0, 0, 32}, {0, 17, 32}, {0, 1, 0}, {0, 1, 33}} {
		r := stockVerifyResume(t, e, coord, coordAddr, args[0], uint8(args[1]), uint8(args[2]), stockVerifyCallGas)
		stockVerifyAssertRevert(t, r, "StockControlError(uint256)", 4)
		stockVerifyAssertFailedRollback(t, e, coord, coordAddr, epoch, total, digest, m, r)
	}
	r := stockVerifyResume(t, e, coord, coordAddr, 0, 3, 1, stockVerifyCallGas)
	stockVerifyAssertRevert(t, r, "StockControlError(uint256)", 6)
	stockVerifyAssertFailedRollback(t, e, coord, coordAddr, epoch, total, digest, m, r)
	r = stockVerifyResume(t, e, coord, coordAddr, 1, 3, 32, stockVerifyCallGas)
	stockVerifyAssertRevert(t, r, "StockControlError(uint256)", 3)
	stockVerifyAssertFailedRollback(t, e, coord, coordAddr, epoch, total, digest, m, r)

	r = stockVerifyResume(t, e, coord, coordAddr, 0, 3, 32, stockVerifyCallGas)
	if r.coreErr != nil || r.result.Err != nil || r.result.UsedGas > stockVerifyCallGas {
		t.Fatalf("resume1 failed/gas: %v %v %d", r.coreErr, r.result.Err, r.result.UsedGas)
	}
	want1 := stockVerifyZeroMachine()
	want1.Pc = 3
	want1.Sp = 1
	want1.Initialized = 1
	want1.Stack[0] = stockVerifyTagged(5)
	want1.Locals[0] = stockVerifyTagged(5)
	dirty1 := stockVerifyDirty(zero, want1)
	out := stockVerifyUnpack(t, coord, "resume", r.result.ReturnData)
	if out[0].(uint64) != 1 || out[1].(bool) || out[2].(int32) != 0 || out[3].(uint8) != 3 || out[4].(uint8) != dirty1 {
		t.Fatalf("resume1 output=%v want dirty%d", out, dirty1)
	}
	epoch, total, digest, m = stockVerifyCheckpoint(t, e, coord, coordAddr)
	if epoch != 1 || total != 3 || !stockVerifyMachineEqual(m, want1) || digest != stockVerifyDigest(t, module, payloadHash, moduleHash, m, epoch, total) {
		t.Fatalf("checkpoint1 mismatch")
	}
	stockVerifyCheckEvent(t, coord, r, epoch, total, m, 3, dirty1, digest)

	// Repeat both rollback probes after a nonzero epoch.
	for _, probe := range []struct {
		name    string
		gas     uint64
		reserve bool
	}{{"low-reserve", 750_000, true}, {"actual-oog", 0, false}} {
		data := stockVerifyCallData(t, coord, "resume", uint64(1), uint8(16), uint8(32))
		gas := probe.gas
		if gas == 0 {
			floor, err := core.FloorDataGas(data)
			if err != nil {
				t.Fatal(err)
			}
			gas = floor
		}
		nonce := e.state.StateDB.GetNonce(e.sender)
		balance := stockVerifyBalance(e)
		failed := e.apply(&coordAddr, data, gas)
		if probe.reserve {
			stockVerifyAssertRevert(t, failed, "StockControlError(uint256)", 5)
		} else if failed.coreErr != nil || failed.result == nil || !errors.Is(failed.result.Err, vm.ErrOutOfGas) || len(failed.result.ReturnData) != 0 {
			t.Fatalf("post-progress actual OOG identity: %v %v", failed.coreErr, stockVerifyResultErr(failed.result))
		}
		if e.state.StateDB.GetNonce(e.sender) != nonce+1 || stockVerifyBalance(e).Cmp(balance) >= 0 {
			t.Fatalf("post-progress %s sender semantics", probe.name)
		}
		stockVerifyAssertFailedRollback(t, e, coord, coordAddr, epoch, total, digest, m, failed)
	}

	r = stockVerifyResume(t, e, coord, coordAddr, 1, 16, 32, stockVerifyCallGas)
	if r.coreErr != nil || r.result.Err != nil {
		t.Fatalf("resume2: %v %v", r.coreErr, r.result.Err)
	}
	want2 := stockVerifyCloneMachine(want1)
	want2.Pc = 7
	want2.Sp = 0
	want2.Stack[0].SetUint64(0)
	want2.Done = true
	want2.Result = 12
	dirty2 := stockVerifyDirty(want1, want2)
	out = stockVerifyUnpack(t, coord, "resume", r.result.ReturnData)
	if out[0].(uint64) != 2 || !out[1].(bool) || out[2].(int32) != 12 || out[3].(uint8) != 3 || out[4].(uint8) != dirty2 {
		t.Fatalf("resume2 output=%v", out)
	}
	epoch, total, digest, m = stockVerifyCheckpoint(t, e, coord, coordAddr)
	if epoch != 2 || total != 6 || !stockVerifyMachineEqual(m, want2) || digest != stockVerifyDigest(t, module, payloadHash, moduleHash, m, epoch, total) {
		t.Fatalf("terminal checkpoint mismatch")
	}
	stockVerifyCheckEvent(t, coord, r, epoch, total, m, 3, dirty2, digest)
	t.Logf("terminal result=%d epoch=%d totalSteps=%d digest=%s dirty=(%d,%d) terminalResumeGas=%d", m.Result, epoch, total, digest, dirty1, dirty2, r.result.UsedGas)
	r = stockVerifyResume(t, e, coord, coordAddr, 2, 1, 32, stockVerifyCallGas)
	stockVerifyAssertRevert(t, r, "StockControlError(uint256)", 1)
	stockVerifyAssertFailedRollback(t, e, coord, coordAddr, epoch, total, digest, m, r)
}

func stockVerifyFakeModuleRuntime(inspectSelector [4]byte, codeOffset, codeLength uint32, maxStack, maxLocals uint8) []byte {
	// Dispatch inspect(selector) to four ABI words; every other call returns 18
	// zero words. That is a decodable step response with executed=0 and must be
	// rejected by the coordinator as an invalid module result.
	out := []byte{0x60, 0, 0x35, 0x60, 0xe0, 0x1c, 0x63, inspectSelector[0], inspectSelector[1], inspectSelector[2], inspectSelector[3], 0x14, 0x61, 0, 0, 0x57, 0x61, 0x02, 0x40, 0x60, 0, 0xf3}
	dest := len(out)
	out[13] = byte(dest >> 8)
	out[14] = byte(dest)
	out = append(out, 0x5b)
	put := func(v uint32, offset byte) {
		out = append(out, 0x63, byte(v>>24), byte(v>>16), byte(v>>8), byte(v), 0x60, offset, 0x52)
	}
	put(codeOffset, 0)
	put(codeLength, 32)
	put(uint32(maxStack), 64)
	put(uint32(maxLocals), 96)
	out = append(out, 0x60, 0x80, 0x60, 0, 0xf3)
	return out
}

func TestStockVerifyCoordinatorPinnedInputsAndInvalidModuleResult(t *testing.T) {
	page := stockVerifyLoadArtifact(t, "ArtifactPage")
	module := stockVerifyLoadArtifact(t, "TinyJvmStepModule")
	coord := stockVerifyLoadArtifact(t, "VMCoordinator")
	e := stockVerifyNewEnv(t)
	defer e.close()
	moduleAddr, _ := e.mustCreate(module.init, stockVerifyCreateGas)
	moduleHash := crypto.Keccak256Hash(e.state.StateDB.GetCode(moduleAddr))
	class := stockVerifyBuildClass(stockVerifyClassOptions{})
	pageAddr, pageHash, payloadHash := stockVerifyDeployPage(t, e, page, class.bytes)
	for _, tc := range []struct {
		name   string
		module common.Address
		hash   common.Hash
	}{
		{"empty-module", common.Address{}, common.Hash{}}, {"module-hash", moduleAddr, common.HexToHash("0x01")},
	} {
		t.Run(tc.name, func(t *testing.T) {
			nonce := e.state.StateDB.GetNonce(e.sender)
			r := e.apply(nil, stockVerifyConstructor(t, coord, tc.module, pageAddr, tc.hash, pageHash, payloadHash), stockVerifyCreateGas)
			stockVerifyAssertRevert(t, r, "StockControlError(uint256)", 2)
			if len(e.state.StateDB.GetCode(crypto.CreateAddress(e.sender, nonce))) != 0 {
				t.Fatal("failed coordinator left code")
			}
		})
	}
	badPage := pageHash
	badPage[0] ^= 1
	r := e.apply(nil, stockVerifyConstructor(t, coord, moduleAddr, pageAddr, moduleHash, badPage, payloadHash), stockVerifyCreateGas)
	stockVerifyAssertRevert(t, r, "StockPageError(uint256)", 3)
	badPayload := payloadHash
	badPayload[0] ^= 1
	r = e.apply(nil, stockVerifyConstructor(t, coord, moduleAddr, pageAddr, moduleHash, pageHash, badPayload), stockVerifyCreateGas)
	stockVerifyAssertRevert(t, r, "StockPageError(uint256)", 4)

	selector := module.abi.Methods["inspect"].ID
	var sel [4]byte
	copy(sel[:], selector)
	fakeCode := stockVerifyFakeModuleRuntime(sel, uint32(class.mark["root.code0.bytes"]), 2, 1, 0)
	fake := stockVerifyDeployRaw(t, e, fakeCode)
	fakeHash := crypto.Keccak256Hash(fakeCode)
	fakeCoord, _ := e.mustCreate(stockVerifyConstructor(t, coord, fake, pageAddr, fakeHash, pageHash, payloadHash), stockVerifyCreateGas)
	r = stockVerifyResume(t, e, coord, fakeCoord, 0, 1, 32, stockVerifyCallGas)
	stockVerifyAssertRevert(t, r, "StockControlError(uint256)", 7)
}

type stockVerifyReplayRecord struct {
	txHashes        []common.Hash
	addresses       []common.Address
	gas             []uint64
	outputs         [][]byte
	logs            [][]byte
	finalCodeHashes []common.Hash
	root            common.Hash
}

func stockVerifyReplay(t *testing.T) stockVerifyReplayRecord {
	t.Helper()
	page := stockVerifyLoadArtifact(t, "ArtifactPage")
	module := stockVerifyLoadArtifact(t, "TinyJvmStepModule")
	coord := stockVerifyLoadArtifact(t, "VMCoordinator")
	e := stockVerifyNewEnv(t)
	defer e.close()
	rec := stockVerifyReplayRecord{}
	capture := func(r stockVerifyTxResult) {
		rec.txHashes = append(rec.txHashes, r.tx.Hash())
		rec.gas = append(rec.gas, r.result.UsedGas)
		rec.outputs = append(rec.outputs, append([]byte(nil), r.result.ReturnData...))
		var encoded []byte
		for _, log := range r.logs {
			encoded = append(encoded, log.Address.Bytes()...)
			for _, topic := range log.Topics {
				encoded = append(encoded, topic.Bytes()...)
			}
			encoded = append(encoded, log.Data...)
		}
		rec.logs = append(rec.logs, encoded)
	}
	moduleAddr, r := e.mustCreate(module.init, stockVerifyCreateGas)
	capture(r)
	rec.addresses = append(rec.addresses, moduleAddr)
	moduleHash := crypto.Keccak256Hash(e.state.StateDB.GetCode(moduleAddr))
	class := stockVerifyBuildClass(stockVerifyClassOptions{code: []byte{0, 0, 0, 0, 0, 0, 0, 0x08, 0xac}, maxStack: 1})
	pageAddr, pageTx := e.mustCreate(stockVerifyConstructor(t, page, class.bytes), stockVerifyCreateGas)
	capture(pageTx)
	pageHash, payloadHash, wantPage := stockVerifyPageHashes(class.bytes)
	if !bytes.Equal(e.state.StateDB.GetCode(pageAddr), wantPage) {
		t.Fatal("replay page bytes")
	}
	rec.addresses = append(rec.addresses, pageAddr)
	coordAddr, r := e.mustCreate(stockVerifyConstructor(t, coord, moduleAddr, pageAddr, moduleHash, pageHash, payloadHash), stockVerifyCreateGas)
	capture(r)
	rec.addresses = append(rec.addresses, coordAddr)
	for epoch := uint64(0); epoch < 3; epoch++ {
		r = stockVerifyResume(t, e, coord, coordAddr, epoch, 3, 32, stockVerifyCallGas)
		if r.coreErr != nil || r.result.Err != nil {
			t.Fatalf("replay resume%d: %v %v", epoch, r.coreErr, r.result.Err)
		}
		capture(r)
	}
	r = e.mustCall(coordAddr, stockVerifyCallData(t, coord, "checkpoint"), stockVerifyCallGas)
	capture(r)
	values := stockVerifyUnpack(t, coord, "checkpoint", r.result.ReturnData)
	epoch, total, digest, m := values[0].(uint64), values[1].(uint64), common.Hash(values[2].([32]byte)), stockVerifyMachineFrom(values[3])
	if epoch != 3 || total != 9 || !m.Done || m.Result != 5 || digest != stockVerifyDigest(t, module, payloadHash, moduleHash, m, epoch, total) {
		t.Fatalf("replay terminal checkpoint mismatch")
	}
	rec.finalCodeHashes = []common.Hash{crypto.Keccak256Hash(e.state.StateDB.GetCode(moduleAddr)), crypto.Keccak256Hash(e.state.StateDB.GetCode(pageAddr)), crypto.Keccak256Hash(e.state.StateDB.GetCode(coordAddr))}
	rec.root = e.state.StateDB.IntermediateRoot(true)
	return rec
}

func TestStockVerifyDeterministicSignedApplyMessageReplay(t *testing.T) {
	a := stockVerifyReplay(t)
	b := stockVerifyReplay(t)
	if !reflect.DeepEqual(a, b) {
		t.Fatalf("identical signed direct replays differ\nA=%+v\nB=%+v", a, b)
	}
	if len(a.addresses) != 3 || len(a.gas) != 7 {
		t.Fatalf("replay evidence incomplete: addresses=%d capturedTx=%d", len(a.addresses), len(a.gas))
	}
	var aggregate uint64
	for _, gas := range a.gas {
		aggregate += gas
	}
	if aggregate > 30_000_000 {
		t.Fatalf("canonical replay aggregate gas=%d exceeds 30M", aggregate)
	}
	t.Logf("identical signed replay: addresses=%v gas=%v aggregate=%d codehashes=%v root=%s", a.addresses, a.gas, aggregate, a.finalCodeHashes, a.root)
}

func TestStockVerifyStockProtocolLimitRejectionLayers(t *testing.T) {
	e := stockVerifyNewEnv(t)
	defer e.close()
	// EIP-170 is an EVM creation failure after a valid transaction: sender nonce
	// and gas change, while the would-be contract has no code.
	nonce := e.state.StateDB.GetNonce(e.sender)
	balance := stockVerifyBalance(e)
	runtime := make([]byte, 24577)
	r := e.apply(nil, stockVerifyRawInit(runtime), stockVerifyCreateGas)
	if r.coreErr != nil || r.result == nil || !errors.Is(r.result.Err, vm.ErrMaxCodeSizeExceeded) {
		t.Fatalf("EIP-170 layer: core=%v evm=%v", r.coreErr, stockVerifyResultErr(r.result))
	}
	if e.state.StateDB.GetNonce(e.sender) != nonce+1 || stockVerifyBalance(e).Cmp(balance) >= 0 || len(e.state.StateDB.GetCode(crypto.CreateAddress(e.sender, nonce))) != 0 {
		t.Fatal("EIP-170 nonce/gas/empty-code semantics")
	}
	// EIP-3860 is consensus precheck rejection. It does not execute or consume
	// sender nonce/balance and is not StockPageError(1).
	nonce = e.state.StateDB.GetNonce(e.sender)
	balance = stockVerifyBalance(e)
	snapshot := e.state.StateDB.Snapshot()
	r = e.apply(nil, make([]byte, 49153), stockVerifyCreateGas)
	if !errors.Is(r.coreErr, core.ErrMaxInitCodeSizeExceeded) || r.result != nil {
		t.Fatalf("EIP-3860 layer: core=%v result=%v", r.coreErr, r.result)
	}
	// ApplyMessage detects this consensus error after gas purchase but before
	// nonce increment/CREATE. A block/transaction caller discards that invalid
	// transition; make the raw layer and the discarded canonical state explicit.
	wantDebit := new(big.Int).Mul(new(big.Int).SetUint64(stockVerifyCreateGas), big.NewInt(2))
	gotDebit := new(big.Int).Sub(balance, stockVerifyBalance(e))
	if e.state.StateDB.GetNonce(e.sender) != nonce || gotDebit.Cmp(wantDebit) != 0 || len(e.state.StateDB.GetCode(crypto.CreateAddress(e.sender, nonce))) != 0 {
		t.Fatalf("EIP-3860 raw ApplyMessage state: nonce=%d want=%d gasDebit=%s want=%s code=%d", e.state.StateDB.GetNonce(e.sender), nonce, gotDebit, wantDebit, len(e.state.StateDB.GetCode(crypto.CreateAddress(e.sender, nonce))))
	}
	e.state.StateDB.RevertToSnapshot(snapshot)
	if e.state.StateDB.GetNonce(e.sender) != nonce || stockVerifyBalance(e).Cmp(balance) != 0 {
		t.Fatal("discarding invalid EIP-3860 transaction did not restore sender")
	}
	// Osaka EIP-7825 is likewise a transaction precheck, tested on an ordinary
	// call rather than through any S0 budget.
	nonce = e.state.StateDB.GetNonce(e.sender)
	balance = stockVerifyBalance(e)
	to := common.HexToAddress("0x7825")
	r = e.apply(&to, nil, params.MaxTxGas+1)
	if !errors.Is(r.coreErr, core.ErrGasLimitTooHigh) || r.result != nil {
		t.Fatalf("EIP-7825 layer: core=%v result=%v", r.coreErr, r.result)
	}
	if e.state.StateDB.GetNonce(e.sender) != nonce || stockVerifyBalance(e).Cmp(balance) != 0 {
		t.Fatal("EIP-7825 rejection changed sender state")
	}
}
