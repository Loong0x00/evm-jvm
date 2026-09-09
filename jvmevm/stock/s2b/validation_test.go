// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.
//
// This is the independent Stock S2b-L verifier. It does not use the S2b harness:
// artifacts are decoded again and every EVM operation is an ordinary signed
// transaction. The classfile builders/parsers below are assertion oracles for
// bounded trusted test inputs only; production receives only unchanged raw bytes.
package s2b

import (
	"bytes"
	"context"
	"crypto/ecdsa"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"math/big"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core"
	"github.com/ethereum/go-ethereum/core/rawdb"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/core/vm"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/jvmevm/stock"
	"github.com/ethereum/go-ethereum/jvmevm/stock/s2a"
	"github.com/ethereum/go-ethereum/params"
	gethtests "github.com/ethereum/go-ethereum/tests"
)

const (
	stockS2bLinkVerifyCreateGas = uint64(8_000_000)
	stockS2bLinkVerifyCallGas   = uint64(8_000_000)
	stockS2bLinkVerifyBlockGas  = uint64(30_000_000)
)

var stockS2bLinkVerifyOne = big.NewInt(1)

type stockS2bLinkVerifyCompiler struct {
	Version, EVMVersion string
	ViaIR               bool `json:"viaIR"`
	Optimizer           struct {
		Enabled bool
		Runs    int
	}
	Metadata struct {
		AppendCBOR   bool
		BytecodeHash string
	}
}

type stockS2bLinkVerifyImmutable struct{ Start, Length int }
type stockS2bLinkVerifyArtifactJSON struct {
	ContractName        string
	ABI                 json.RawMessage `json:"abi"`
	Bytecode            string
	DeployedBytecode    string
	ImmutableReferences map[string][]stockS2bLinkVerifyImmutable
	Compiler            stockS2bLinkVerifyCompiler
	SourceHashes        map[string]string
}
type stockS2bLinkVerifyArtifact struct {
	name       string
	abi        abi.ABI
	init       []byte
	runtime    []byte
	immutables map[string][]stockS2bLinkVerifyImmutable
}

func stockS2bLinkVerifyLoadArtifact(t *testing.T, name string) stockS2bLinkVerifyArtifact {
	t.Helper()
	path := filepath.Join("runtime", "artifacts", name+".json")
	blob, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read frozen %s artifact (S2b-L runtime integration dependency is absent): %v", name, err)
	}
	var doc stockS2bLinkVerifyArtifactJSON
	if err := json.Unmarshal(blob, &doc); err != nil {
		t.Fatalf("decode %s: %v", path, err)
	}
	if doc.ContractName != name || len(doc.ABI) == 0 || doc.Bytecode == "" || doc.DeployedBytecode == "" {
		t.Fatalf("incomplete artifact %s", path)
	}
	contractABI, err := abi.JSON(bytes.NewReader(doc.ABI))
	if err != nil {
		t.Fatalf("parse %s ABI: %v", name, err)
	}
	decode := func(field, text string) []byte {
		out, err := hex.DecodeString(strings.TrimPrefix(text, "0x"))
		if err != nil || len(out) == 0 {
			t.Fatalf("decode %s.%s: bytes=%d err=%v", name, field, len(out), err)
		}
		return out
	}
	if !strings.HasPrefix(doc.Compiler.Version, "0.8.30+commit.73712a01") || !doc.Compiler.ViaIR ||
		!doc.Compiler.Optimizer.Enabled || doc.Compiler.Optimizer.Runs != 200 || doc.Compiler.EVMVersion != "cancun" ||
		doc.Compiler.Metadata.AppendCBOR || doc.Compiler.Metadata.BytecodeHash != "none" || len(doc.SourceHashes) == 0 {
		t.Fatalf("%s compiler configuration is not frozen: %+v sources=%d", name, doc.Compiler, len(doc.SourceHashes))
	}
	for source, hash := range doc.SourceHashes {
		if source == "" || len(hash) != 64 {
			t.Fatalf("%s bad source hash %q=%q", name, source, hash)
		}
		if _, err := hex.DecodeString(hash); err != nil {
			t.Fatalf("%s bad source hash %q: %v", name, hash, err)
		}
	}
	return stockS2bLinkVerifyArtifact{name, contractABI, decode("bytecode", doc.Bytecode), decode("deployedBytecode", doc.DeployedBytecode), doc.ImmutableReferences}
}

func stockS2bLinkVerifyPage(t *testing.T) stockS2bLinkVerifyArtifact {
	t.Helper()
	a, err := stock.LoadArtifact(stock.ArtifactPage)
	if err != nil {
		t.Fatalf("load accepted ArtifactPage: %v", err)
	}
	return stockS2bLinkVerifyArtifact{name: stock.ArtifactPage, abi: a.ABI, init: a.InitCode, runtime: a.RuntimeCode}
}
func stockS2bLinkVerifyS2aParser(t *testing.T) stockS2bLinkVerifyArtifact {
	t.Helper()
	a, err := s2a.LoadArtifact(s2a.S2aClassParser)
	if err != nil {
		t.Fatalf("load accepted S2a parser: %v", err)
	}
	return stockS2bLinkVerifyArtifact{name: s2a.S2aClassParser, abi: a.ABI, init: a.InitCode, runtime: a.RuntimeCode}
}

type stockS2bLinkVerifyEnv struct {
	t       *testing.T
	state   gethtests.StateTestState
	key     *ecdsa.PrivateKey
	sender  common.Address
	signer  types.Signer
	block   vm.BlockContext
	gasUsed uint64
}
type stockS2bLinkVerifyTx struct {
	tx      *types.Transaction
	result  *core.ExecutionResult
	coreErr error
	address common.Address
	logs    []*types.Log
	receipt *types.Receipt
}

func stockS2bLinkVerifyNewEnv(t *testing.T) *stockS2bLinkVerifyEnv {
	t.Helper()
	key, err := crypto.HexToECDSA("52b152b152b152b152b152b152b152b152b152b152b152b152b152b152b152b1")
	if err != nil {
		t.Fatal(err)
	}
	sender := crypto.PubkeyToAddress(key.PublicKey)
	pre := gethtests.MakePreState(rawdb.NewMemoryDatabase(), types.GenesisAlloc{
		sender: {Balance: new(big.Int).Exp(big.NewInt(10), big.NewInt(30), nil)},
	}, false, rawdb.HashScheme)
	random := crypto.Keccak256Hash([]byte("JVMEVM:STOCK:S2B:LINK:VERIFY"))
	block := vm.BlockContext{CanTransfer: core.CanTransfer, Transfer: core.Transfer,
		GetHash:  func(n uint64) common.Hash { return crypto.Keccak256Hash(new(big.Int).SetUint64(n).Bytes()) },
		Coinbase: common.HexToAddress("0x0000000000000000000000000000000000001337"), BlockNumber: big.NewInt(1),
		Time: 1, Difficulty: new(big.Int), BaseFee: new(big.Int).Set(stockS2bLinkVerifyOne), GasLimit: stockS2bLinkVerifyBlockGas, Random: &random}
	return &stockS2bLinkVerifyEnv{t: t, state: pre, key: key, sender: sender,
		signer: types.MakeSigner(params.AllDevChainProtocolChanges, block.BlockNumber, block.Time), block: block}
}
func (e *stockS2bLinkVerifyEnv) close() { e.state.Close() }
func (e *stockS2bLinkVerifyEnv) apply(to *common.Address, input []byte, gas uint64) stockS2bLinkVerifyTx {
	e.t.Helper()
	nonce := e.state.StateDB.GetNonce(e.sender)
	tx := types.NewTx(&types.LegacyTx{Nonce: nonce, To: to, Gas: gas, GasPrice: big.NewInt(2), Data: append([]byte(nil), input...)})
	signed, err := types.SignTx(tx, e.signer, e.key)
	if err != nil {
		e.t.Fatal(err)
	}
	recovered, err := types.Sender(e.signer, signed)
	if err != nil || recovered != e.sender {
		e.t.Fatalf("sender=%s err=%v want=%s", recovered, err, e.sender)
	}
	msg, err := core.TransactionToMessage(signed, e.signer, e.block.BaseFee)
	if err != nil {
		e.t.Fatalf("TransactionToMessage: %v", err)
	}
	if msg.Nonce != nonce || msg.SkipNonceChecks || msg.SkipTransactionChecks {
		e.t.Fatalf("noncanonical message nonce=%d skip=(%v,%v)", msg.Nonce, msg.SkipNonceChecks, msg.SkipTransactionChecks)
	}
	e.state.StateDB.SetTxContext(signed.Hash(), 0)
	evm := vm.NewEVM(e.block, e.state.StateDB, params.AllDevChainProtocolChanges, vm.Config{})
	result, coreErr := core.ApplyMessage(evm, msg, new(core.GasPool).AddGas(stockS2bLinkVerifyBlockGas))
	address := common.Address{}
	if to == nil {
		address = crypto.CreateAddress(e.sender, nonce)
	}
	logs := e.state.StateDB.GetLogs(signed.Hash(), e.block.BlockNumber.Uint64(), common.Hash{}, e.block.Time)
	var receipt *types.Receipt
	if result != nil {
		e.gasUsed += result.UsedGas
		receipt = core.MakeReceipt(evm, result, e.state.StateDB, e.block.BlockNumber, common.Hash{}, e.block.Time, signed, e.gasUsed, nil)
		if receipt.TxHash != signed.Hash() || receipt.GasUsed != result.UsedGas || receipt.CumulativeGasUsed != e.gasUsed || receipt.ContractAddress != address || !reflect.DeepEqual(receipt.Logs, logs) {
			e.t.Fatal("receipt/core result mismatch")
		}
	}
	return stockS2bLinkVerifyTx{signed, result, coreErr, address, logs, receipt}
}
func stockS2bLinkVerifyResultErr(r *core.ExecutionResult) error {
	if r == nil {
		return nil
	}
	return r.Err
}
func stockS2bLinkVerifyResultData(r *core.ExecutionResult) []byte {
	if r == nil {
		return nil
	}
	return r.ReturnData
}
func (e *stockS2bLinkVerifyEnv) mustCreate(init []byte, gas uint64) (common.Address, stockS2bLinkVerifyTx) {
	e.t.Helper()
	r := e.apply(nil, init, gas)
	if r.coreErr != nil || r.result == nil || r.result.Err != nil || r.receipt == nil || r.receipt.Status != types.ReceiptStatusSuccessful || len(e.state.StateDB.GetCode(r.address)) == 0 {
		e.t.Fatalf("CREATE core=%v evm=%v data=%x receipt=%+v", r.coreErr, stockS2bLinkVerifyResultErr(r.result), stockS2bLinkVerifyResultData(r.result), r.receipt)
	}
	return r.address, r
}
func (e *stockS2bLinkVerifyEnv) mustCall(to common.Address, input []byte, gas uint64) stockS2bLinkVerifyTx {
	e.t.Helper()
	r := e.apply(&to, input, gas)
	if r.coreErr != nil || r.result == nil || r.result.Err != nil || r.receipt == nil || r.receipt.Status != types.ReceiptStatusSuccessful {
		e.t.Fatalf("CALL %s core=%v evm=%v data=%x", to, r.coreErr, stockS2bLinkVerifyResultErr(r.result), stockS2bLinkVerifyResultData(r.result))
	}
	return r
}

func stockS2bLinkVerifyConstructor(t *testing.T, a stockS2bLinkVerifyArtifact, args ...any) []byte {
	t.Helper()
	tail, err := a.abi.Pack("", args...)
	if err != nil {
		t.Fatalf("pack %s ctor: %v", a.name, err)
	}
	return append(append([]byte(nil), a.init...), tail...)
}
func stockS2bLinkVerifyCallData(t *testing.T, a stockS2bLinkVerifyArtifact, method string, args ...any) []byte {
	t.Helper()
	out, err := a.abi.Pack(method, args...)
	if err != nil {
		t.Fatalf("pack %s.%s: %v", a.name, method, err)
	}
	return out
}
func stockS2bLinkVerifyUnpack(t *testing.T, a stockS2bLinkVerifyArtifact, method string, data []byte) []any {
	t.Helper()
	out, err := a.abi.Unpack(method, data)
	if err != nil {
		t.Fatalf("unpack %s.%s %x: %v", a.name, method, data, err)
	}
	return out
}
func stockS2bLinkVerifyCustomError(signature string, words ...uint64) []byte {
	out := append([]byte(nil), crypto.Keccak256([]byte(signature))[:4]...)
	for _, v := range words {
		var word [32]byte
		binary.BigEndian.PutUint64(word[24:], v)
		out = append(out, word[:]...)
	}
	return out
}
func stockS2bLinkVerifyAssertRevert(t *testing.T, tx stockS2bLinkVerifyTx, signature string, words ...uint64) {
	t.Helper()
	if tx.coreErr != nil || tx.result == nil || !errors.Is(tx.result.Err, vm.ErrExecutionReverted) {
		t.Fatalf("want %s%v core=%v evm=%v data=%x", signature, words, tx.coreErr, stockS2bLinkVerifyResultErr(tx.result), stockS2bLinkVerifyResultData(tx.result))
	}
	if want := stockS2bLinkVerifyCustomError(signature, words...); !bytes.Equal(tx.result.ReturnData, want) {
		t.Fatalf("wrong revert have=%x want=%x", tx.result.ReturnData, want)
	}
	if len(tx.logs) != 0 || tx.receipt == nil || tx.receipt.Status != types.ReceiptStatusFailed {
		t.Fatalf("failed receipt/logs=%+v/%d", tx.receipt, len(tx.logs))
	}
}
func stockS2bLinkVerifyRawInit(runtime []byte) []byte {
	if len(runtime) > math.MaxUint16 {
		panic("runtime too large")
	}
	out := []byte{0x61, byte(len(runtime) >> 8), byte(len(runtime)), 0x61, 0, 15, 0x60, 0, 0x39, 0x61, byte(len(runtime) >> 8), byte(len(runtime)), 0x60, 0, 0xf3}
	return append(out, runtime...)
}

// The trusted builder emits ordinary Java 52 classfiles. Call operands are
// patched only into the test bytes; no such information accompanies registration.
type stockS2bLinkVerifyMethod struct {
	name, descriptor    string
	access              uint16
	code                []byte
	maxStack, maxLocals uint16
	codeCopies          int
	handlers            uint16
	calls               []stockS2bLinkVerifyCallPatch
}
type stockS2bLinkVerifyCallSymbol struct {
	owner, name, descriptor string
	tag                     byte
}
type stockS2bLinkVerifyCallPatch struct{ pc, symbol int }
type stockS2bLinkVerifyClass struct {
	bytes  []byte
	marks  map[string]int
	callCP []uint16
}
type stockS2bLinkVerifyCP struct {
	tag   byte
	body  []byte
	slots uint16
}

func stockS2bLinkVerifyU2(v uint16) []byte { return []byte{byte(v >> 8), byte(v)} }
func stockS2bLinkVerifyU4(v uint32) []byte {
	return []byte{byte(v >> 24), byte(v >> 16), byte(v >> 8), byte(v)}
}
func stockS2bLinkVerifyUtf8(s string) stockS2bLinkVerifyCP {
	return stockS2bLinkVerifyCP{1, append(stockS2bLinkVerifyU2(uint16(len(s))), []byte(s)...), 1}
}
func stockS2bLinkVerifyBuildClass(className string, methods []stockS2bLinkVerifyMethod, symbols []stockS2bLinkVerifyCallSymbol, cpPad int) stockS2bLinkVerifyClass {
	if className == "" {
		className = "S2bTrusted"
	}
	all := append([]stockS2bLinkVerifyMethod{{name: "<init>", descriptor: "()V", access: 1, code: []byte{0x2a, 0xb7, 0, 9, 0xb1}, maxStack: 1, maxLocals: 1, codeCopies: 1}}, methods...)
	cp := []stockS2bLinkVerifyCP{
		stockS2bLinkVerifyUtf8(className), {7, stockS2bLinkVerifyU2(1), 1}, stockS2bLinkVerifyUtf8("java/lang/Object"), {7, stockS2bLinkVerifyU2(3), 1},
		stockS2bLinkVerifyUtf8("<init>"), stockS2bLinkVerifyUtf8("()V"), stockS2bLinkVerifyUtf8("Code"), {12, append(stockS2bLinkVerifyU2(5), stockS2bLinkVerifyU2(6)...), 1},
		{10, append(stockS2bLinkVerifyU2(4), stockS2bLinkVerifyU2(8)...), 1}, {3, []byte{0x12, 0x34, 0x56, 0x78}, 1},
	}
	utf := map[string]uint16{className: 1, "java/lang/Object": 3, "<init>": 5, "()V": 6, "Code": 7}
	addUTF := func(s string) uint16 {
		if i, ok := utf[s]; ok {
			return i
		}
		i := uint16(len(cp) + 1)
		cp = append(cp, stockS2bLinkVerifyUtf8(s))
		utf[s] = i
		return i
	}
	for _, m := range methods {
		addUTF(m.name)
		addUTF(m.descriptor)
	}
	callCP := make([]uint16, len(symbols))
	for i, s := range symbols {
		name, desc := addUTF(s.name), addUTF(s.descriptor)
		nt := uint16(len(cp) + 1)
		cp = append(cp, stockS2bLinkVerifyCP{12, append(stockS2bLinkVerifyU2(name), stockS2bLinkVerifyU2(desc)...), 1})
		ownerName := addUTF(s.owner)
		ownerClass := uint16(len(cp) + 1)
		cp = append(cp, stockS2bLinkVerifyCP{7, stockS2bLinkVerifyU2(ownerName), 1})
		tag := s.tag
		if tag == 0 {
			tag = 10
		}
		callCP[i] = uint16(len(cp) + 1)
		cp = append(cp, stockS2bLinkVerifyCP{tag, append(stockS2bLinkVerifyU2(ownerClass), stockS2bLinkVerifyU2(nt)...), 1})
	}
	for len(cp)+1 < cpPad {
		cp = append(cp, stockS2bLinkVerifyCP{3, []byte{0, 0, 0, byte(len(cp))}, 1})
	}
	if len(cp)+1 > math.MaxUint16 {
		panic("CP too large")
	}
	marks := make(map[string]int)
	var out []byte
	put := func(b []byte) { out = append(out, b...) }
	mark := func(s string) { marks[s] = len(out) }
	put([]byte{0xca, 0xfe, 0xba, 0xbe, 0, 0, 0, 52})
	mark("version")
	marks["version"] = 6
	mark("cpCount")
	put(stockS2bLinkVerifyU2(uint16(len(cp) + 1)))
	for i, c := range cp {
		mark(fmt.Sprintf("cp%d.tag", i+1))
		put([]byte{c.tag})
		mark(fmt.Sprintf("cp%d.body", i+1))
		put(c.body)
	}
	mark("classAccess")
	put(stockS2bLinkVerifyU2(0x0021))
	put(stockS2bLinkVerifyU2(2))
	put(stockS2bLinkVerifyU2(4))
	mark("interfacesCount")
	put(stockS2bLinkVerifyU2(0))
	mark("fieldsCount")
	put(stockS2bLinkVerifyU2(0))
	mark("methodCount")
	put(stockS2bLinkVerifyU2(uint16(len(all))))
	for i, m := range all {
		prefix := fmt.Sprintf("method%d", i)
		copies := m.codeCopies
		if copies == 0 {
			copies = 1
		} else if copies < 0 {
			copies = 0
		}
		mark(prefix + ".access")
		put(stockS2bLinkVerifyU2(m.access))
		put(stockS2bLinkVerifyU2(utf[m.name]))
		put(stockS2bLinkVerifyU2(utf[m.descriptor]))
		mark(prefix + ".attrs")
		put(stockS2bLinkVerifyU2(uint16(copies)))
		code := append([]byte(nil), m.code...)
		for _, p := range m.calls {
			if p.symbol < 0 || p.symbol >= len(callCP) || p.pc < 0 || p.pc+2 >= len(code) || code[p.pc] != 0xb8 {
				panic("bad trusted call patch")
			}
			binary.BigEndian.PutUint16(code[p.pc+1:], callCP[p.symbol])
		}
		for n := 0; n < copies; n++ {
			p := fmt.Sprintf("%s.code%d", prefix, n)
			put(stockS2bLinkVerifyU2(7))
			put(stockS2bLinkVerifyU4(uint32(12 + len(code) + int(m.handlers)*8)))
			mark(p + ".maxStack")
			put(stockS2bLinkVerifyU2(m.maxStack))
			mark(p + ".maxLocals")
			put(stockS2bLinkVerifyU2(m.maxLocals))
			mark(p + ".codeLen")
			put(stockS2bLinkVerifyU4(uint32(len(code))))
			mark(p + ".bytes")
			put(code)
			mark(p + ".handlers")
			put(stockS2bLinkVerifyU2(m.handlers))
			put(make([]byte, int(m.handlers)*8))
			put(stockS2bLinkVerifyU2(0))
		}
	}
	put(stockS2bLinkVerifyU2(0))
	return stockS2bLinkVerifyClass{out, marks, callCP}
}
func stockS2bLinkVerifySimple(code []byte, stack, locals uint16, desc string) stockS2bLinkVerifyClass {
	if desc == "" {
		desc = "()I"
	}
	return stockS2bLinkVerifyBuildClass("S2bTrusted", []stockS2bLinkVerifyMethod{{"entry", desc, 9, code, stack, locals, 1, 0, nil}}, nil, 0)
}
func stockS2bLinkVerifyPatchByte(c stockS2bLinkVerifyClass, mark string, delta int, v byte) stockS2bLinkVerifyClass {
	out := stockS2bLinkVerifyClass{append([]byte(nil), c.bytes...), c.marks, append([]uint16(nil), c.callCP...)}
	out.bytes[out.marks[mark]+delta] = v
	return out
}
func stockS2bLinkVerifyPatchU2(c stockS2bLinkVerifyClass, mark string, v uint16) stockS2bLinkVerifyClass {
	out := stockS2bLinkVerifyClass{append([]byte(nil), c.bytes...), c.marks, append([]uint16(nil), c.callCP...)}
	binary.BigEndian.PutUint16(out.bytes[out.marks[mark]:], v)
	return out
}
func stockS2bLinkVerifyPatchU4(c stockS2bLinkVerifyClass, mark string, v uint32) stockS2bLinkVerifyClass {
	out := stockS2bLinkVerifyClass{append([]byte(nil), c.bytes...), c.marks, append([]uint16(nil), c.callCP...)}
	binary.BigEndian.PutUint32(out.bytes[out.marks[mark]:], v)
	return out
}

// Independent bounded decoder used only to assert metadata against raw bytes.
type stockS2bLinkVerifyCPEntry struct {
	tag    byte
	a, b   uint16
	utf    []byte
	bits   uint32
	offset int
}
type stockS2bLinkVerifyParsedMethod struct {
	index, access       uint16
	name, descriptor    []byte
	codeOffset          uint32
	code                []byte
	maxStack, maxLocals uint16
}
type stockS2bLinkVerifyParsed struct {
	name            []byte
	access, cpCount uint16
	cp              []stockS2bLinkVerifyCPEntry
	methods         []stockS2bLinkVerifyParsedMethod
}
type stockS2bLinkVerifyReader struct {
	b []byte
	p int
}

func (r *stockS2bLinkVerifyReader) take(n int) []byte {
	if n < 0 || r.p+n > len(r.b) {
		panic("trusted parse boundary")
	}
	v := r.b[r.p : r.p+n]
	r.p += n
	return v
}
func (r *stockS2bLinkVerifyReader) u1() byte   { return r.take(1)[0] }
func (r *stockS2bLinkVerifyReader) u2() uint16 { return binary.BigEndian.Uint16(r.take(2)) }
func (r *stockS2bLinkVerifyReader) u4() uint32 { return binary.BigEndian.Uint32(r.take(4)) }
func stockS2bLinkVerifyParseTrusted(raw []byte) stockS2bLinkVerifyParsed {
	r := &stockS2bLinkVerifyReader{b: raw}
	if !bytes.Equal(r.take(4), []byte{0xca, 0xfe, 0xba, 0xbe}) {
		panic("magic")
	}
	r.take(4)
	count := r.u2()
	cp := make([]stockS2bLinkVerifyCPEntry, count)
	for i := uint16(1); i < count; i++ {
		off := r.p
		tag := r.u1()
		cp[i].tag, cp[i].offset = tag, off
		switch tag {
		case 1:
			n := r.u2()
			cp[i].utf = append([]byte(nil), r.take(int(n))...)
		case 3, 4:
			cp[i].bits = r.u4()
		case 5, 6:
			r.take(8)
			i++
		case 7, 8, 16:
			cp[i].a = r.u2()
		case 9, 10, 11, 12, 18:
			cp[i].a, cp[i].b = r.u2(), r.u2()
		case 15:
			cp[i].a = uint16(r.u1())
			cp[i].b = r.u2()
		default:
			panic(fmt.Sprintf("trusted CP tag %d", tag))
		}
	}
	access, this := r.u2(), r.u2()
	r.u2()
	name := append([]byte(nil), cp[cp[this].a].utf...)
	interfaces := r.u2()
	r.take(int(interfaces) * 2)
	fields := r.u2()
	for i := uint16(0); i < fields; i++ {
		r.take(6)
		attrs := r.u2()
		for j := uint16(0); j < attrs; j++ {
			r.u2()
			r.take(int(r.u4()))
		}
	}
	n := r.u2()
	p := stockS2bLinkVerifyParsed{name: name, access: access, cpCount: count, cp: cp}
	for i := uint16(0); i < n; i++ {
		m := stockS2bLinkVerifyParsedMethod{index: i, access: r.u2()}
		ni, di := r.u2(), r.u2()
		m.name = append([]byte(nil), cp[ni].utf...)
		m.descriptor = append([]byte(nil), cp[di].utf...)
		attrs := r.u2()
		for j := uint16(0); j < attrs; j++ {
			ai, l := r.u2(), r.u4()
			start := r.p
			if string(cp[ai].utf) == "Code" {
				m.maxStack, m.maxLocals = r.u2(), r.u2()
				cl := r.u4()
				m.codeOffset = uint32(r.p)
				m.code = append([]byte(nil), r.take(int(cl))...)
				h := r.u2()
				r.take(int(h) * 8)
				na := r.u2()
				for k := uint16(0); k < na; k++ {
					r.u2()
					r.take(int(r.u4()))
				}
			} else {
				r.take(int(l))
			}
			if r.p-start != int(l) {
				panic("attribute length")
			}
		}
		p.methods = append(p.methods, m)
	}
	attrs := r.u2()
	for i := uint16(0); i < attrs; i++ {
		r.u2()
		r.take(int(r.u4()))
	}
	if r.p != len(raw) {
		panic("trailing")
	}
	return p
}
func stockS2bLinkVerifyWidth(op byte) int {
	switch op {
	case 0x10, 0x12, 0x15, 0x36:
		return 2
	case 0x11, 0x13, 0x84, 0x99, 0x9a, 0x9b, 0x9c, 0x9d, 0x9e, 0x9f, 0xa0, 0xa1, 0xa2, 0xa3, 0xa4, 0xa7, 0xb8:
		return 3
	}
	return 1
}
func stockS2bLinkVerifyDescriptor(desc []byte) (uint8, uint8, bool) {
	s := string(desc)
	if len(s) < 3 || s[0] != '(' {
		return 0, 0, false
	}
	close := strings.IndexByte(s, ')')
	if close < 1 || close != len(s)-2 || close-1 > 6 {
		return 0, 0, false
	}
	for _, c := range []byte(s[1:close]) {
		if c != 'I' {
			return 0, 0, false
		}
	}
	ret := uint8(0)
	if s[close+1] == 'I' {
		ret = 1
	} else if s[close+1] != 'V' {
		return 0, 0, false
	}
	return uint8(close - 1), ret, true
}
func stockS2bLinkVerifyResolveCall(p stockS2bLinkVerifyParsed, ix uint16) (owner, name, desc []byte, ok bool) {
	if ix == 0 || int(ix) >= len(p.cp) || p.cp[ix].tag != 10 {
		return
	}
	mr := p.cp[ix]
	if int(mr.a) >= len(p.cp) || int(mr.b) >= len(p.cp) || p.cp[mr.a].tag != 7 || p.cp[mr.b].tag != 12 {
		return
	}
	cl, nt := p.cp[mr.a], p.cp[mr.b]
	if int(cl.a) >= len(p.cp) || int(nt.a) >= len(p.cp) || int(nt.b) >= len(p.cp) || p.cp[cl.a].tag != 1 || p.cp[nt.a].tag != 1 || p.cp[nt.b].tag != 1 {
		return
	}
	return p.cp[cl.a].utf, p.cp[nt.a].utf, p.cp[nt.b].utf, true
}

type stockS2bLinkVerifyMetaMethod struct {
	nameHash, descHash                                            common.Hash
	index, access                                                 uint16
	codeOffset                                                    uint32
	codeLen                                                       uint16
	maxStack, maxLocals, argc, returnKind, errorDomain, errorCode uint8
	errorLocation                                                 uint32
	literalBase, literalCount, callBase, callCount                uint16
	starts                                                        *big.Int
	reserved                                                      common.Hash
}
type stockS2bLinkVerifyLiteral struct {
	method, pc uint16
	bits       uint32
}
type stockS2bLinkVerifyCall struct {
	caller, pc, cpIndex, target uint16
	argc, returnKind            uint8
	flags                       uint16
	reserved                    uint32
}
type stockS2bLinkVerifyMetadata struct {
	words    [8]common.Hash
	methods  []stockS2bLinkVerifyMetaMethod
	literals []stockS2bLinkVerifyLiteral
	calls    []stockS2bLinkVerifyCall
}

func stockS2bLinkVerifyField(v *big.Int, shift uint, bits uint) uint64 {
	x := new(big.Int).Rsh(new(big.Int).Set(v), shift)
	x.And(x, new(big.Int).Sub(new(big.Int).Lsh(big.NewInt(1), bits), big.NewInt(1)))
	return x.Uint64()
}
func stockS2bLinkVerifyDecodeMetadata(t *testing.T, code []byte) stockS2bLinkVerifyMetadata {
	t.Helper()
	if len(code) < 257 || code[0] != 0 {
		t.Fatalf("metadata prefix/size=%d", len(code))
	}
	b := code[1:]
	if len(b) < 256 {
		t.Fatal("short metadata")
	}
	var out stockS2bLinkVerifyMetadata
	for i := 0; i < 8; i++ {
		copy(out.words[i][:], b[i*32:(i+1)*32])
	}
	h5 := new(big.Int).SetBytes(out.words[5][:])
	methods := int(stockS2bLinkVerifyField(h5, 48, 16))
	lits := int(stockS2bLinkVerifyField(h5, 64, 16))
	calls := int(stockS2bLinkVerifyField(h5, 80, 16))
	want := 256 + methods*160 + lits*8 + calls*16
	if len(b) != want {
		t.Fatalf("metadata len=%d want=%d dimensions=%d/%d/%d", len(b), want, methods, lits, calls)
	}
	off := 256
	for i := 0; i < methods; i++ {
		var m stockS2bLinkVerifyMetaMethod
		copy(m.nameHash[:], b[off:off+32])
		copy(m.descHash[:], b[off+32:off+64])
		v := new(big.Int).SetBytes(b[off+64 : off+96])
		m.index = uint16(stockS2bLinkVerifyField(v, 0, 16))
		m.access = uint16(stockS2bLinkVerifyField(v, 16, 16))
		m.codeOffset = uint32(stockS2bLinkVerifyField(v, 32, 32))
		m.codeLen = uint16(stockS2bLinkVerifyField(v, 64, 16))
		m.maxStack = uint8(stockS2bLinkVerifyField(v, 80, 8))
		m.maxLocals = uint8(stockS2bLinkVerifyField(v, 88, 8))
		m.argc = uint8(stockS2bLinkVerifyField(v, 96, 8))
		m.returnKind = uint8(stockS2bLinkVerifyField(v, 104, 8))
		m.errorDomain = uint8(stockS2bLinkVerifyField(v, 112, 8))
		m.errorCode = uint8(stockS2bLinkVerifyField(v, 120, 8))
		m.errorLocation = uint32(stockS2bLinkVerifyField(v, 128, 32))
		m.literalBase = uint16(stockS2bLinkVerifyField(v, 160, 16))
		m.literalCount = uint16(stockS2bLinkVerifyField(v, 176, 16))
		m.callBase = uint16(stockS2bLinkVerifyField(v, 192, 16))
		m.callCount = uint16(stockS2bLinkVerifyField(v, 208, 16))
		if stockS2bLinkVerifyField(v, 224, 32) != 0 {
			t.Fatal("method high bits")
		}
		m.starts = new(big.Int).SetBytes(b[off+96 : off+128])
		copy(m.reserved[:], b[off+128:off+160])
		out.methods = append(out.methods, m)
		off += 160
	}
	for i := 0; i < lits; i++ {
		out.literals = append(out.literals, stockS2bLinkVerifyLiteral{binary.BigEndian.Uint16(b[off:]), binary.BigEndian.Uint16(b[off+2:]), binary.BigEndian.Uint32(b[off+4:])})
		off += 8
	}
	for i := 0; i < calls; i++ {
		out.calls = append(out.calls, stockS2bLinkVerifyCall{binary.BigEndian.Uint16(b[off:]), binary.BigEndian.Uint16(b[off+2:]), binary.BigEndian.Uint16(b[off+4:]), binary.BigEndian.Uint16(b[off+6:]), b[off+8], b[off+9], binary.BigEndian.Uint16(b[off+10:]), binary.BigEndian.Uint32(b[off+12:])})
		off += 16
	}
	return out
}

func stockS2bLinkVerifyDeployPage(t *testing.T, e *stockS2bLinkVerifyEnv, page stockS2bLinkVerifyArtifact, raw []byte) (common.Address, common.Hash, common.Hash, stockS2bLinkVerifyTx) {
	t.Helper()
	at, tx := e.mustCreate(stockS2bLinkVerifyConstructor(t, page, raw), stockS2bLinkVerifyCreateGas)
	code := append([]byte{0}, raw...)
	if !bytes.Equal(e.state.StateDB.GetCode(at), code) {
		t.Fatal("ArtifactPage bytes")
	}
	return at, crypto.Keccak256Hash(code), crypto.Keccak256Hash(raw), tx
}
func stockS2bLinkVerifyDeployRaw(t *testing.T, e *stockS2bLinkVerifyEnv, runtime []byte) (common.Address, stockS2bLinkVerifyTx) {
	t.Helper()
	at, tx := e.mustCreate(stockS2bLinkVerifyRawInit(runtime), stockS2bLinkVerifyCreateGas)
	if !bytes.Equal(e.state.StateDB.GetCode(at), runtime) {
		t.Fatal("raw CREATE bytes")
	}
	return at, tx
}
func stockS2bLinkVerifyDeployLinker(t *testing.T, e *stockS2bLinkVerifyEnv, a stockS2bLinkVerifyArtifact, analyzer common.Address, analyzerHash, legacyHash common.Hash) (common.Address, stockS2bLinkVerifyTx) {
	t.Helper()
	return e.mustCreate(stockS2bLinkVerifyConstructor(t, a, analyzer, analyzerHash, legacyHash), stockS2bLinkVerifyCreateGas)
}

type stockS2bLinkVerifyRegistration struct {
	id                       common.Hash
	metadata                 common.Address
	metadataHash             common.Hash
	methods, literals, calls uint16
	tx                       stockS2bLinkVerifyTx
}

func stockS2bLinkVerifyRegister(t *testing.T, e *stockS2bLinkVerifyEnv, a stockS2bLinkVerifyArtifact, at, page common.Address, pageHash, payloadHash common.Hash, gas uint64) stockS2bLinkVerifyRegistration {
	t.Helper()
	tx := e.mustCall(at, stockS2bLinkVerifyCallData(t, a, "registerClass", page, pageHash, payloadHash), gas)
	out := stockS2bLinkVerifyUnpack(t, a, "registerClass", tx.result.ReturnData)
	if len(out) != 6 {
		t.Fatalf("register outputs=%d", len(out))
	}
	return stockS2bLinkVerifyRegistration{common.Hash(out[0].([32]byte)), out[1].(common.Address), common.Hash(out[2].([32]byte)), out[3].(uint16), out[4].(uint16), out[5].(uint16), tx}
}
func stockS2bLinkVerifyAdapt(t *testing.T, e *stockS2bLinkVerifyEnv, a stockS2bLinkVerifyArtifact, at, oldParser common.Address, oldID common.Hash, gas uint64) stockS2bLinkVerifyRegistration {
	t.Helper()
	tx := e.mustCall(at, stockS2bLinkVerifyCallData(t, a, "registerFromS2a", oldParser, oldID), gas)
	out := stockS2bLinkVerifyUnpack(t, a, "registerFromS2a", tx.result.ReturnData)
	return stockS2bLinkVerifyRegistration{common.Hash(out[0].([32]byte)), out[1].(common.Address), common.Hash(out[2].([32]byte)), out[3].(uint16), out[4].(uint16), out[5].(uint16), tx}
}
func stockS2bLinkVerifyRecord(t *testing.T, e *stockS2bLinkVerifyEnv, a stockS2bLinkVerifyArtifact, at common.Address, id common.Hash) (common.Address, common.Hash) {
	t.Helper()
	tx := e.mustCall(at, stockS2bLinkVerifyCallData(t, a, "classRecord", id), 1_000_000)
	out := stockS2bLinkVerifyUnpack(t, a, "classRecord", tx.result.ReturnData)
	return out[0].(common.Address), common.Hash(out[1].([32]byte))
}
func stockS2bLinkVerifyABIHash(t *testing.T, typesText []string, values ...any) common.Hash {
	t.Helper()
	args := make(abi.Arguments, len(typesText))
	for i, s := range typesText {
		typ, err := abi.NewType(s, "", nil)
		if err != nil {
			t.Fatal(err)
		}
		args[i] = abi.Argument{Type: typ}
	}
	packed, err := args.Pack(values...)
	if err != nil {
		t.Fatal(err)
	}
	return crypto.Keccak256Hash(packed)
}
func stockS2bLinkVerifyClassID(t *testing.T, linkerHash, analyzerHash common.Hash, raw common.Address, pageHash, payloadHash, metadataHash common.Hash) common.Hash {
	return stockS2bLinkVerifyABIHash(t, []string{"bytes32", "uint32", "bytes32", "bytes32", "address", "bytes32", "bytes32", "bytes32"}, crypto.Keccak256Hash([]byte("JVMEVM:S2B:LINK:CLASS:4")), uint32(4), linkerHash, analyzerHash, raw, pageHash, payloadHash, metadataHash)
}
func stockS2bLinkVerifyRequireMethod(t *testing.T, a stockS2bLinkVerifyArtifact, name, sig, mutability string, in, out int) {
	t.Helper()
	m, ok := a.abi.Methods[name]
	if !ok || m.Sig != sig || m.StateMutability != mutability || len(m.Inputs) != in || len(m.Outputs) != out {
		t.Fatalf("%s.%s ABI present=%v sig=%q mut=%q in/out=%d/%d", a.name, name, ok, m.Sig, m.StateMutability, len(m.Inputs), len(m.Outputs))
	}
}
func stockS2bLinkVerifyRequireError(t *testing.T, a stockS2bLinkVerifyArtifact, name, sig string) {
	t.Helper()
	e, ok := a.abi.Errors[name]
	if !ok || e.Sig != sig {
		t.Fatalf("%s error %s present=%v sig=%q", a.name, name, ok, e.Sig)
	}
}
func stockS2bLinkVerifyGetter(t *testing.T, e *stockS2bLinkVerifyEnv, a stockS2bLinkVerifyArtifact, at common.Address, name string) any {
	t.Helper()
	tx := e.mustCall(at, stockS2bLinkVerifyCallData(t, a, name), 500_000)
	return stockS2bLinkVerifyUnpack(t, a, name, tx.result.ReturnData)[0]
}
func stockS2bLinkVerifyAssertTemplate(t *testing.T, actual []byte, a stockS2bLinkVerifyArtifact, minRefs int) {
	t.Helper()
	if len(actual) != len(a.runtime) || len(a.immutables) == 0 {
		t.Fatalf("%s actual/template/refs=%d/%d/%d", a.name, len(actual), len(a.runtime), len(a.immutables))
	}
	normalized := append([]byte(nil), actual...)
	refs := 0
	for _, locations := range a.immutables {
		for _, r := range locations {
			if r.Length != 32 || r.Start < 0 || r.Start+r.Length > len(normalized) {
				t.Fatalf("bad immutable %+v", r)
			}
			copy(normalized[r.Start:r.Start+r.Length], a.runtime[r.Start:r.Start+r.Length])
			refs++
		}
	}
	if refs < minRefs || !bytes.Equal(normalized, a.runtime) {
		t.Fatalf("%s differs outside %d immutable refs", a.name, refs)
	}
}
func stockS2bLinkVerifyMethodRecord(t *testing.T, m stockS2bLinkVerifyMetaMethod, domain, code uint8, location uint32) {
	t.Helper()
	if m.errorDomain != domain || m.errorCode != code || m.errorLocation != location {
		t.Fatalf("method%d error=%d/%d/%d want=%d/%d/%d", m.index, m.errorDomain, m.errorCode, m.errorLocation, domain, code, location)
	}
	if domain != 0 && (m.codeOffset != 0 || m.codeLen != 0 || m.maxStack != 0 || m.maxLocals != 0 || m.argc != 0 || m.returnKind != 0 || m.literalBase != 0 || m.literalCount != 0 || m.callBase != 0 || m.callCount != 0 || m.starts.Sign() != 0) {
		t.Fatalf("method%d ineligible fields leaked: %+v", m.index, m)
	}
}
func stockS2bLinkVerifyValidateMetadata(t *testing.T, raw []byte, rawAt common.Address, pageHash, payloadHash, analyzerHash common.Hash, code []byte) stockS2bLinkVerifyMetadata {
	t.Helper()
	p := stockS2bLinkVerifyParseTrusted(raw)
	m := stockS2bLinkVerifyDecodeMetadata(t, code)
	if m.words[0] != crypto.Keccak256Hash([]byte("JVMEVM:S2B:LINK:METADATA:4")) || m.words[2] != pageHash || m.words[3] != payloadHash || m.words[4] != crypto.Keccak256Hash(p.name) || m.words[6] != analyzerHash || m.words[7] != (common.Hash{}) {
		t.Fatalf("schema header mismatch %x", m.words)
	}
	h1 := new(big.Int).SetBytes(m.words[1][:])
	if common.BytesToAddress(m.words[1][12:]) != rawAt || stockS2bLinkVerifyField(h1, 160, 16) != uint64(p.access) || stockS2bLinkVerifyField(h1, 176, 80) != 0 {
		t.Fatalf("H1=%x", m.words[1])
	}
	h5 := new(big.Int).SetBytes(m.words[5][:])
	if stockS2bLinkVerifyField(h5, 0, 32) != uint64(len(raw)) || stockS2bLinkVerifyField(h5, 32, 16) != uint64(p.cpCount) || stockS2bLinkVerifyField(h5, 48, 16) != uint64(len(p.methods)) || stockS2bLinkVerifyField(h5, 96, 160) != 0 {
		t.Fatalf("H5=%x", m.words[5])
	}
	if len(m.methods) != len(p.methods) {
		t.Fatalf("methods=%d want=%d", len(m.methods), len(p.methods))
	}
	for i, mr := range m.methods {
		rm := p.methods[i]
		if mr.index != uint16(i) || mr.access != rm.access || mr.nameHash != crypto.Keccak256Hash(rm.name) || mr.descHash != crypto.Keccak256Hash(rm.descriptor) || mr.reserved != (common.Hash{}) {
			t.Fatalf("method%d identity/reserved mismatch", i)
		}
		if mr.errorDomain == 0 {
			argc, ret, ok := stockS2bLinkVerifyDescriptor(rm.descriptor)
			if !ok || mr.codeOffset != rm.codeOffset || mr.codeLen != uint16(len(rm.code)) || mr.maxStack != uint8(rm.maxStack) || mr.maxLocals != uint8(rm.maxLocals) || mr.argc != argc || mr.returnKind != ret || mr.errorCode != 0 || mr.errorLocation != 0 {
				t.Fatalf("eligible method%d envelope=%+v raw=%+v", i, mr, rm)
			}
		} else {
			stockS2bLinkVerifyMethodRecord(t, mr, mr.errorDomain, mr.errorCode, mr.errorLocation)
		}
	}
	lastMethod, lastPC := -1, -1
	for i, l := range m.literals {
		if int(l.method) < lastMethod || (int(l.method) == lastMethod && int(l.pc) <= lastPC) {
			t.Fatalf("unsorted literal%d", i)
		}
		if int(l.method) >= len(p.methods) || int(l.pc) >= len(p.methods[l.method].code) {
			t.Fatalf("literal%d bounds", i)
		}
		op := p.methods[l.method].code[l.pc]
		var ix uint16
		if op == 0x12 {
			ix = uint16(p.methods[l.method].code[l.pc+1])
		} else if op == 0x13 {
			ix = binary.BigEndian.Uint16(p.methods[l.method].code[l.pc+1:])
		} else {
			t.Fatalf("literal%d opcode=%x", i, op)
		}
		if int(ix) >= len(p.cp) || p.cp[ix].tag != 3 || p.cp[ix].bits != l.bits {
			t.Fatalf("literal%d CP", i)
		}
		lastMethod, lastPC = int(l.method), int(l.pc)
	}
	lastMethod, lastPC = -1, -1
	for i, c := range m.calls {
		if int(c.caller) < lastMethod || (int(c.caller) == lastMethod && int(c.pc) <= lastPC) {
			t.Fatalf("unsorted call%d", i)
		}
		if c.flags != 0 || c.reserved != 0 || int(c.caller) >= len(p.methods) || int(c.target) >= len(p.methods) {
			t.Fatalf("call%d canonical", i)
		}
		caller := p.methods[c.caller]
		if int(c.pc)+2 >= len(caller.code) || caller.code[c.pc] != 0xb8 || binary.BigEndian.Uint16(caller.code[c.pc+1:]) != c.cpIndex {
			t.Fatalf("call%d raw operand", i)
		}
		owner, name, desc, ok := stockS2bLinkVerifyResolveCall(p, c.cpIndex)
		if !ok || !bytes.Equal(owner, p.name) {
			t.Fatalf("call%d CP", i)
		}
		target := p.methods[c.target]
		argc, ret, ok := stockS2bLinkVerifyDescriptor(desc)
		if !ok || !bytes.Equal(name, target.name) || !bytes.Equal(desc, target.descriptor) || c.argc != argc || c.returnKind != ret {
			t.Fatalf("call%d target/effect", i)
		}
		lastMethod, lastPC = int(c.caller), int(c.pc)
	}
	return m
}

func TestStockS2bLinkVerifyFrozenABIArtifactsDeploymentAndSchema(t *testing.T) {
	page := stockS2bLinkVerifyPage(t)
	metaPage := stockS2bLinkVerifyLoadArtifact(t, "S2bMetadataPage")
	analyzer := stockS2bLinkVerifyLoadArtifact(t, "S2bAnalyzeModule")
	linker := stockS2bLinkVerifyLoadArtifact(t, "S2bClassLinker")
	legacy := stockS2bLinkVerifyS2aParser(t)
	if len(metaPage.abi.Constructor.Inputs) != 1 || metaPage.abi.Constructor.Inputs[0].Type.String() != "bytes" || len(metaPage.abi.Methods) != 0 {
		t.Fatal("metadata page is not constructor(bytes)-only")
	}
	if len(analyzer.abi.Constructor.Inputs) != 0 || len(analyzer.abi.Methods) != 1 {
		t.Fatalf("analyzer API=%v", analyzer.abi.Methods)
	}
	stockS2bLinkVerifyRequireMethod(t, analyzer, "analyze", "analyze(bytes,address,bytes32,bytes32)", "view", 4, 4)
	wantCtor := []string{"address", "bytes32", "bytes32"}
	if len(linker.abi.Constructor.Inputs) != len(wantCtor) {
		t.Fatalf("linker ctor=%v", linker.abi.Constructor.Inputs)
	}
	for i, w := range wantCtor {
		if linker.abi.Constructor.Inputs[i].Type.String() != w {
			t.Fatalf("linker ctor%d=%s", i, linker.abi.Constructor.Inputs[i].Type)
		}
	}
	stockS2bLinkVerifyRequireMethod(t, linker, "registerClass", "registerClass(address,bytes32,bytes32)", "nonpayable", 3, 6)
	stockS2bLinkVerifyRequireMethod(t, linker, "registerFromS2a", "registerFromS2a(address,bytes32)", "nonpayable", 2, 6)
	stockS2bLinkVerifyRequireMethod(t, linker, "classRecord", "classRecord(bytes32)", "view", 1, 2)
	for _, g := range []struct{ name, sig, typ string }{{"analyzer", "analyzer()", "address"}, {"analyzerCodeHash", "analyzerCodeHash()", "bytes32"}, {"acceptedS2aParserHash", "acceptedS2aParserHash()", "bytes32"}} {
		stockS2bLinkVerifyRequireMethod(t, linker, g.name, g.sig, "view", 0, 1)
		if linker.abi.Methods[g.name].Outputs[0].Type.String() != g.typ {
			t.Fatalf("getter %s", g.name)
		}
	}
	if len(linker.abi.Methods) != 6 {
		t.Fatalf("linker API count=%d", len(linker.abi.Methods))
	}
	for _, x := range []struct{ name, sig string }{{"StockPageError", "StockPageError(uint256)"}, {"S2bClassError", "S2bClassError(uint256,uint256)"}} {
		stockS2bLinkVerifyRequireError(t, analyzer, x.name, x.sig)
	}
	stockS2bLinkVerifyRequireError(t, linker, "S2bLinkError", "S2bLinkError(uint256)")
	event, ok := linker.abi.Events["ClassRegistered"]
	if !ok || event.Sig != "ClassRegistered(bytes32,address,address,bytes32,uint16,uint16,uint16)" || len(event.Inputs) != 7 || !event.Inputs[0].Indexed || !event.Inputs[1].Indexed {
		t.Fatalf("event=%v", event)
	}
	for _, a := range []stockS2bLinkVerifyArtifact{metaPage, analyzer, linker} {
		cap := 12 * 1024
		if a.name == "S2bAnalyzeModule" {
			cap = 20 * 1024
		}
		if len(a.runtime) > cap || len(a.init) > 24*1024 {
			t.Fatalf("%s init/runtime=%d/%d", a.name, len(a.init), len(a.runtime))
		}
		if a.name == "S2bClassLinker" && len(a.immutables) == 0 {
			t.Fatal("linker immutables absent")
		}
		if a.name != "S2bClassLinker" && len(a.immutables) != 0 {
			t.Fatalf("%s unexpected immutables", a.name)
		}
	}
	e := stockS2bLinkVerifyNewEnv(t)
	defer e.close()
	boundary, _ := e.mustCreate(stockS2bLinkVerifyConstructor(t, metaPage, make([]byte, 8191)), stockS2bLinkVerifyCreateGas)
	if len(e.state.StateDB.GetCode(boundary)) != 8192 {
		t.Fatal("metadata 8192 runtime boundary")
	}
	nonce := e.state.StateDB.GetNonce(e.sender)
	tooLarge := e.apply(nil, stockS2bLinkVerifyConstructor(t, metaPage, make([]byte, 8192)), stockS2bLinkVerifyCreateGas)
	stockS2bLinkVerifyAssertRevert(t, tooLarge, "S2bClassError(uint256,uint256)", 5, 0)
	if len(e.state.StateDB.GetCode(crypto.CreateAddress(e.sender, nonce))) != 0 {
		t.Fatal("metadata failure left code")
	}
	analyzerAt, analyzerTx := e.mustCreate(analyzer.init, stockS2bLinkVerifyCreateGas)
	actualAnalyzer := e.state.StateDB.GetCode(analyzerAt)
	if !bytes.Equal(actualAnalyzer, analyzer.runtime) {
		t.Fatal("analyzer differs from artifact")
	}
	analyzerHash := crypto.Keccak256Hash(actualAnalyzer)
	legacyHash := crypto.Keccak256Hash(legacy.runtime)
	linkerAt, linkerTx := stockS2bLinkVerifyDeployLinker(t, e, linker, analyzerAt, analyzerHash, legacyHash)
	actualLinker := e.state.StateDB.GetCode(linkerAt)
	stockS2bLinkVerifyAssertTemplate(t, actualLinker, linker, 3)
	linkerHash := crypto.Keccak256Hash(actualLinker)
	if stockS2bLinkVerifyGetter(t, e, linker, linkerAt, "analyzer").(common.Address) != analyzerAt || common.Hash(stockS2bLinkVerifyGetter(t, e, linker, linkerAt, "analyzerCodeHash").([32]byte)) != analyzerHash || common.Hash(stockS2bLinkVerifyGetter(t, e, linker, linkerAt, "acceptedS2aParserHash").([32]byte)) != legacyHash {
		t.Fatal("immutable getters")
	}
	class := stockS2bLinkVerifySimple([]byte{0x1a, 0x04, 0x60, 0xac}, 2, 1, "(I)I")
	rawAt, pageHash, payloadHash, _ := stockS2bLinkVerifyDeployPage(t, e, page, class.bytes)
	direct := e.mustCall(analyzerAt, stockS2bLinkVerifyCallData(t, analyzer, "analyze", class.bytes, rawAt, pageHash, payloadHash), stockS2bLinkVerifyCallGas)
	av := stockS2bLinkVerifyUnpack(t, analyzer, "analyze", direct.result.ReturnData)
	if av[1].(uint16) != 2 || av[2].(uint16) != 0 || av[3].(uint16) != 0 {
		t.Fatalf("analyze counts=%v", av[1:])
	}
	expectedMetadata := append([]byte{0}, av[0].([]byte)...)
	stockS2bLinkVerifyValidateMetadata(t, class.bytes, rawAt, pageHash, payloadHash, analyzerHash, expectedMetadata)
	reg := stockS2bLinkVerifyRegister(t, e, linker, linkerAt, rawAt, pageHash, payloadHash, stockS2bLinkVerifyCallGas)
	metadataCode := e.state.StateDB.GetCode(reg.metadata)
	if reg.methods != 2 || reg.literals != 0 || reg.calls != 0 || !bytes.Equal(metadataCode, expectedMetadata) || crypto.Keccak256Hash(metadataCode) != reg.metadataHash || reg.id != stockS2bLinkVerifyClassID(t, linkerHash, analyzerHash, rawAt, pageHash, payloadHash, reg.metadataHash) {
		t.Fatalf("registration=%+v", reg)
	}
	if len(reg.tx.logs) != 1 {
		t.Fatalf("registration events=%d", len(reg.tx.logs))
	}
	log := reg.tx.logs[0]
	if log.Address != linkerAt || len(log.Topics) != 3 || log.Topics[0] != event.ID || common.Hash(log.Topics[1]) != reg.id || common.BytesToAddress(log.Topics[2][12:]) != rawAt {
		t.Fatalf("event topics=%v", log.Topics)
	}
	data, err := event.Inputs.NonIndexed().Unpack(log.Data)
	if err != nil {
		t.Fatal(err)
	}
	if data[0].(common.Address) != reg.metadata || common.Hash(data[1].([32]byte)) != reg.metadataHash || data[2].(uint16) != 2 || data[3].(uint16) != 0 || data[4].(uint16) != 0 {
		t.Fatalf("event data=%v", data)
	}
	internalNonce := e.state.StateDB.GetNonce(linkerAt)
	retry := stockS2bLinkVerifyRegister(t, e, linker, linkerAt, rawAt, pageHash, payloadHash, stockS2bLinkVerifyCallGas)
	if retry.id != reg.id || retry.metadata != reg.metadata || retry.metadataHash != reg.metadataHash || retry.methods != reg.methods || retry.literals != reg.literals || retry.calls != reg.calls || len(retry.tx.logs) != 0 || e.state.StateDB.GetNonce(linkerAt) != internalNonce {
		t.Fatalf("idempotent retry=%+v", retry)
	}
	if at, h := stockS2bLinkVerifyRecord(t, e, linker, linkerAt, common.Hash{}); at != (common.Address{}) || h != (common.Hash{}) {
		t.Fatal("unknown record not zero")
	}
	if at, h := stockS2bLinkVerifyRecord(t, e, linker, linkerAt, reg.id); at != reg.metadata || h != reg.metadataHash {
		t.Fatal("issued record mismatch")
	}
	for _, tc := range []struct {
		name     string
		analyzer common.Address
		ah, lh   common.Hash
		code     uint64
	}{{"zero-analyzer", common.Address{}, analyzerHash, legacyHash, 1}, {"wrong-analyzer-hash", analyzerAt, common.Hash{}, legacyHash, 1}, {"zero-legacy", analyzerAt, analyzerHash, common.Hash{}, 3}} {
		t.Run(tc.name, func(t *testing.T) {
			n := e.state.StateDB.GetNonce(e.sender)
			tx := e.apply(nil, stockS2bLinkVerifyConstructor(t, linker, tc.analyzer, tc.ah, tc.lh), stockS2bLinkVerifyCreateGas)
			stockS2bLinkVerifyAssertRevert(t, tx, "S2bLinkError(uint256)", tc.code)
			if len(e.state.StateDB.GetCode(crypto.CreateAddress(e.sender, n))) != 0 {
				t.Fatal("bad ctor left code")
			}
		})
	}
	t.Logf("S2b-L analyzer=%dB hash=%s createGas=%d linker=%dB hash=%s createGas=%d registerGas=%d metadata=%dB", len(actualAnalyzer), analyzerHash, analyzerTx.result.UsedGas, len(actualLinker), linkerHash, linkerTx.result.UsedGas, reg.tx.result.UsedGas, len(metadataCode))
}

type stockS2bLinkVerifySetup struct {
	e                        *stockS2bLinkVerifyEnv
	page, analyzer, linker   stockS2bLinkVerifyArtifact
	analyzerAt, linkerAt     common.Address
	analyzerHash, linkerHash common.Hash
}

func stockS2bLinkVerifySetupRuntime(t *testing.T) *stockS2bLinkVerifySetup {
	t.Helper()
	s := &stockS2bLinkVerifySetup{e: stockS2bLinkVerifyNewEnv(t), page: stockS2bLinkVerifyPage(t), analyzer: stockS2bLinkVerifyLoadArtifact(t, "S2bAnalyzeModule"), linker: stockS2bLinkVerifyLoadArtifact(t, "S2bClassLinker")}
	s.analyzerAt, _ = s.e.mustCreate(s.analyzer.init, stockS2bLinkVerifyCreateGas)
	s.analyzerHash = crypto.Keccak256Hash(s.e.state.StateDB.GetCode(s.analyzerAt))
	legacy := stockS2bLinkVerifyS2aParser(t)
	s.linkerAt, _ = stockS2bLinkVerifyDeployLinker(t, s.e, s.linker, s.analyzerAt, s.analyzerHash, crypto.Keccak256Hash(legacy.runtime))
	s.linkerHash = crypto.Keccak256Hash(s.e.state.StateDB.GetCode(s.linkerAt))
	return s
}
func (s *stockS2bLinkVerifySetup) close() { s.e.close() }
func (s *stockS2bLinkVerifySetup) register(t *testing.T, c stockS2bLinkVerifyClass) (stockS2bLinkVerifyRegistration, stockS2bLinkVerifyMetadata, common.Address, common.Hash, common.Hash) {
	t.Helper()
	at, ph, pvh, _ := stockS2bLinkVerifyDeployPage(t, s.e, s.page, c.bytes)
	r := stockS2bLinkVerifyRegister(t, s.e, s.linker, s.linkerAt, at, ph, pvh, stockS2bLinkVerifyCallGas)
	code := s.e.state.StateDB.GetCode(r.metadata)
	if crypto.Keccak256Hash(code) != r.metadataHash {
		t.Fatal("metadata hash")
	}
	m := stockS2bLinkVerifyValidateMetadata(t, c.bytes, at, ph, pvh, s.analyzerHash, code)
	return r, m, at, ph, pvh
}
func stockS2bLinkVerifyCallClass(name string, target stockS2bLinkVerifyMethod, callerCode []byte, callerDesc string, symbol stockS2bLinkVerifyCallSymbol) stockS2bLinkVerifyClass {
	if symbol.owner == "" {
		symbol.owner = name
	}
	if symbol.name == "" {
		symbol.name = target.name
	}
	if symbol.descriptor == "" {
		symbol.descriptor = target.descriptor
	}
	return stockS2bLinkVerifyBuildClass(name, []stockS2bLinkVerifyMethod{target, {name: "caller", descriptor: callerDesc, access: 9, code: callerCode, maxStack: 8, maxLocals: 6, calls: []stockS2bLinkVerifyCallPatch{{pc: 0, symbol: 0}}}}, []stockS2bLinkVerifyCallSymbol{symbol}, 0)
}

func TestStockS2bLinkVerifyMethodAndCallErrorMatrix(t *testing.T) {
	s := stockS2bLinkVerifySetupRuntime(t)
	defer s.close()
	methodCases := []struct {
		name         string
		m            stockS2bLinkVerifyMethod
		domain, code uint8
		pc           uint32
	}{
		{"nonstatic", stockS2bLinkVerifyMethod{name: "bad", descriptor: "()I", access: 1, code: []byte{3, 0xac}, maxStack: 1}, 1, 3, 1},
		{"native", stockS2bLinkVerifyMethod{name: "bad", descriptor: "()I", access: 0x109, codeCopies: -1}, 1, 3, 1},
		{"abstract", stockS2bLinkVerifyMethod{name: "bad", descriptor: "()I", access: 0x409, codeCopies: -1}, 1, 3, 1},
		{"synchronized", stockS2bLinkVerifyMethod{name: "bad", descriptor: "()I", access: 0x29, code: []byte{3, 0xac}, maxStack: 1}, 1, 3, 1},
		{"reference-descriptor", stockS2bLinkVerifyMethod{name: "bad", descriptor: "(Ljava/lang/Object;)I", access: 9, code: []byte{3, 0xac}, maxStack: 1, maxLocals: 1}, 1, 4, 1},
		{"seven-args", stockS2bLinkVerifyMethod{name: "bad", descriptor: "(IIIIIII)I", access: 9, code: []byte{3, 0xac}, maxStack: 1, maxLocals: 7}, 1, 4, 1},
		{"no-Code", stockS2bLinkVerifyMethod{name: "bad", descriptor: "()I", access: 9, codeCopies: -1}, 1, 5, 1},
		{"duplicate-Code", stockS2bLinkVerifyMethod{name: "bad", descriptor: "()I", access: 9, code: []byte{3, 0xac}, maxStack: 1, codeCopies: 2}, 1, 5, 1},
		{"handlers", stockS2bLinkVerifyMethod{name: "bad", descriptor: "()I", access: 9, code: []byte{3, 0xac}, maxStack: 1, handlers: 1}, 1, 5, 1},
		{"locals-under-argc", stockS2bLinkVerifyMethod{name: "bad", descriptor: "(II)I", access: 9, code: []byte{3, 0xac}, maxStack: 1, maxLocals: 1}, 1, 5, 1},
		{"Code257", stockS2bLinkVerifyMethod{name: "bad", descriptor: "()I", access: 9, code: append(bytes.Repeat([]byte{0}, 255), 3, 0xac), maxStack: 1}, 1, 5, 1},
	}
	for _, tc := range methodCases {
		t.Run("method/"+tc.name, func(t *testing.T) {
			c := stockS2bLinkVerifyBuildClass("MethodErrors", []stockS2bLinkVerifyMethod{tc.m}, nil, 0)
			_, m, _, _, _ := s.register(t, c)
			stockS2bLinkVerifyMethodRecord(t, m.methods[1], tc.domain, tc.code, tc.pc)
			stockS2bLinkVerifyMethodRecord(t, m.methods[0], 1, 6, 0)
		})
	}
	// Private/package/protected methods, V returns, six arguments and overloads
	// are legal internal envelopes in schema 4.
	legal := stockS2bLinkVerifyBuildClass("LegalEnvelopes", []stockS2bLinkVerifyMethod{
		{name: "priv", descriptor: "()V", access: 0x0a, code: []byte{0xb1}},
		{name: "pkg", descriptor: "(IIIIII)I", access: 0x08, code: []byte{0x15, 5, 0xac}, maxStack: 1, maxLocals: 6},
		{name: "prot", descriptor: "(I)I", access: 0x0c, code: []byte{0x1a, 0xac}, maxStack: 1, maxLocals: 1},
		{name: "over", descriptor: "()I", access: 9, code: []byte{3, 0xac}, maxStack: 1},
		{name: "over", descriptor: "(I)I", access: 9, code: []byte{0x1a, 0xac}, maxStack: 1, maxLocals: 1},
	}, nil, 0)
	_, lm, _, _, _ := s.register(t, legal)
	for i := 1; i < len(lm.methods); i++ {
		stockS2bLinkVerifyMethodRecord(t, lm.methods[i], 0, 0, 0)
	}

	validTarget := stockS2bLinkVerifyMethod{name: "target", descriptor: "()I", access: 0x0a, code: []byte{4, 0xac}, maxStack: 1}
	callCases := []struct {
		name string
		c    stockS2bLinkVerifyClass
		code uint8
	}{
		{"interface-kind", stockS2bLinkVerifyCallClass("InterfaceKind", validTarget, []byte{0xb8, 0, 0, 0xac}, "()I", stockS2bLinkVerifyCallSymbol{tag: 11}), 1},
		{"operand-not-methodref", func() stockS2bLinkVerifyClass {
			c := stockS2bLinkVerifyCallClass("WrongTag", validTarget, []byte{0xb8, 0, 0, 0xac}, "()I", stockS2bLinkVerifyCallSymbol{})
			binary.BigEndian.PutUint16(c.bytes[c.marks["method2.code0.bytes"]+1:], 10)
			return c
		}(), 1},
		{"external-owner", stockS2bLinkVerifyCallClass("ExternalOwner", validTarget, []byte{0xb8, 0, 0, 0xac}, "()I", stockS2bLinkVerifyCallSymbol{owner: "Other"}), 2},
		{"missing-name", stockS2bLinkVerifyCallClass("MissingName", validTarget, []byte{0xb8, 0, 0, 0xac}, "()I", stockS2bLinkVerifyCallSymbol{name: "absent"}), 3},
		{"wrong-overload", stockS2bLinkVerifyCallClass("WrongOverload", validTarget, []byte{0xb8, 0, 0, 0xac}, "()I", stockS2bLinkVerifyCallSymbol{descriptor: "(I)I"}), 3},
		{"reserved-target", stockS2bLinkVerifyCallClass("ReservedTarget", validTarget, []byte{0xb8, 0, 0, 0xac}, "()I", stockS2bLinkVerifyCallSymbol{name: "<init>", descriptor: "()V"}), 4},
	}
	for _, tc := range callCases {
		t.Run("call/"+tc.name, func(t *testing.T) {
			_, m, _, _, _ := s.register(t, tc.c)
			stockS2bLinkVerifyMethodRecord(t, m.methods[2], 3, tc.code, 0)
			if len(m.calls) != 0 || m.methods[2].callCount != 0 {
				t.Fatal("ineligible caller leaked calls")
			}
		})
	}
	duplicate := stockS2bLinkVerifyBuildClass("Duplicate", []stockS2bLinkVerifyMethod{validTarget, validTarget, {name: "caller", descriptor: "()I", access: 9, code: []byte{0xb8, 0, 0, 0xac}, maxStack: 1, calls: []stockS2bLinkVerifyCallPatch{{0, 0}}}}, []stockS2bLinkVerifyCallSymbol{{owner: "Duplicate", name: "target", descriptor: "()I"}}, 0)
	_, dm, _, _, _ := s.register(t, duplicate)
	stockS2bLinkVerifyMethodRecord(t, dm.methods[3], 3, 3, 0)
	for _, tc := range []struct {
		name   string
		target stockS2bLinkVerifyMethod
	}{{"nonstatic", stockS2bLinkVerifyMethod{name: "target", descriptor: "()I", access: 1, code: []byte{3, 0xac}, maxStack: 1}}, {"native", stockS2bLinkVerifyMethod{name: "target", descriptor: "()I", access: 0x109, codeCopies: -1}}, {"abstract", stockS2bLinkVerifyMethod{name: "target", descriptor: "()I", access: 0x409, codeCopies: -1}}, {"sync", stockS2bLinkVerifyMethod{name: "target", descriptor: "()I", access: 0x29, code: []byte{3, 0xac}, maxStack: 1}}, {"bad-desc", stockS2bLinkVerifyMethod{name: "target", descriptor: "()J", access: 9, code: []byte{3, 0xac}, maxStack: 1}}, {"bad-Code", stockS2bLinkVerifyMethod{name: "target", descriptor: "()I", access: 9, codeCopies: -1}}} {
		t.Run("call/unusable-"+tc.name, func(t *testing.T) {
			c := stockS2bLinkVerifyCallClass("Unusable", tc.target, []byte{0xb8, 0, 0, 0xac}, "()I", stockS2bLinkVerifyCallSymbol{})
			_, m, _, _, _ := s.register(t, c)
			stockS2bLinkVerifyMethodRecord(t, m.methods[2], 3, 4, 0)
		})
	}
	// A final body error is deliberately not transitive. Both declaration orders
	// keep the caller eligible and cached; the callee retains its own error.
	type callerShape struct {
		codeLen                        uint16
		argc, returnKind, domain, code uint8
		callCount                      uint16
		starts                         string
	}
	var shapes []callerShape
	for _, targetFirst := range []bool{true, false} {
		t.Run(fmt.Sprintf("phaseA-order-target-first-%v", targetFirst), func(t *testing.T) {
			target := stockS2bLinkVerifyMethod{name: "target", descriptor: "()I", access: 0x0a, code: []byte{0xbb}, maxStack: 1}
			caller := stockS2bLinkVerifyMethod{name: "caller", descriptor: "()I", access: 9, code: []byte{0xb8, 0, 0, 0xac}, maxStack: 1, calls: []stockS2bLinkVerifyCallPatch{{0, 0}}}
			methods := []stockS2bLinkVerifyMethod{target, caller}
			targetIndex, callerIndex := 1, 2
			if !targetFirst {
				methods = []stockS2bLinkVerifyMethod{caller, target}
				targetIndex, callerIndex = 2, 1
			}
			c := stockS2bLinkVerifyBuildClass("BodyNotTransitive", methods, []stockS2bLinkVerifyCallSymbol{{owner: "BodyNotTransitive", name: "target", descriptor: "()I"}}, 0)
			_, m, _, _, _ := s.register(t, c)
			stockS2bLinkVerifyMethodRecord(t, m.methods[targetIndex], 2, 6, 0)
			stockS2bLinkVerifyMethodRecord(t, m.methods[callerIndex], 0, 0, 0)
			callerRecord := m.methods[callerIndex]
			if callerRecord.callCount != 1 || len(m.calls) != 1 || int(m.calls[0].target) != targetIndex || m.calls[0].argc != 0 || m.calls[0].returnKind != 1 {
				t.Fatalf("stable caller cache=%+v", m.calls)
			}
			shapes = append(shapes, callerShape{callerRecord.codeLen, callerRecord.argc, callerRecord.returnKind, callerRecord.errorDomain, callerRecord.errorCode, callerRecord.callCount, callerRecord.starts.Text(16)})
		})
	}
	if len(shapes) != 2 || shapes[0] != shapes[1] {
		t.Fatalf("declaration permutation changed caller metadata: %+v", shapes)
	}
	// A target whose own body has a CallError likewise does not poison a caller
	// of that target; only an unusable Phase-A envelope produced CallError(4).
	chain := stockS2bLinkVerifyBuildClass("BodyCallChain", []stockS2bLinkVerifyMethod{{name: "badBody", descriptor: "()I", access: 0x0a, code: []byte{0xb8, 0, 0, 0xac}, maxStack: 1, calls: []stockS2bLinkVerifyCallPatch{{0, 0}}}, {name: "outer", descriptor: "()I", access: 9, code: []byte{0xb8, 0, 0, 0xac}, maxStack: 1, calls: []stockS2bLinkVerifyCallPatch{{0, 1}}}}, []stockS2bLinkVerifyCallSymbol{{owner: "Elsewhere", name: "x", descriptor: "()I"}, {owner: "BodyCallChain", name: "badBody", descriptor: "()I"}}, 0)
	_, cm, _, _, _ := s.register(t, chain)
	stockS2bLinkVerifyMethodRecord(t, cm.methods[1], 3, 2, 0)
	stockS2bLinkVerifyMethodRecord(t, cm.methods[2], 0, 0, 0)
	if len(cm.calls) != 1 || cm.calls[0].caller != 2 || cm.calls[0].target != 1 {
		t.Fatalf("body-error transitive cache=%+v", cm.calls)
	}
}

func TestStockS2bLinkVerifyClassAndBytecodeErrors(t *testing.T) {
	s := stockS2bLinkVerifySetupRuntime(t)
	defer s.close()
	assertClass := func(t *testing.T, c stockS2bLinkVerifyClass, code uint64, off int) {
		t.Helper()
		at, ph, pvh, _ := stockS2bLinkVerifyDeployPage(t, s.e, s.page, c.bytes)
		tx := s.e.apply(&s.linkerAt, stockS2bLinkVerifyCallData(t, s.linker, "registerClass", at, ph, pvh), stockS2bLinkVerifyCallGas)
		stockS2bLinkVerifyAssertRevert(t, tx, "S2bClassError(uint256,uint256)", code, uint64(off))
	}
	base := stockS2bLinkVerifySimple([]byte{3, 0xac}, 1, 0, "()I")
	for _, tc := range []struct {
		name string
		c    stockS2bLinkVerifyClass
		code uint64
		off  int
	}{
		{"version", stockS2bLinkVerifyPatchU2(base, "version", 53), 2, 4},
		{"unknown-CP-tag", stockS2bLinkVerifyPatchByte(base, "cp10.tag", 0, 99), 3, base.marks["cp10.tag"]},
		{"bad-Class-chain", stockS2bLinkVerifyPatchU2(base, "cp2.body", 0), 3, base.marks["cp2.tag"]},
		{"interface", func() stockS2bLinkVerifyClass {
			c := stockS2bLinkVerifyPatchU2(base, "interfacesCount", 1)
			off := c.marks["interfacesCount"] + 2
			c.bytes = append(c.bytes, 0, 0)
			copy(c.bytes[off+2:], c.bytes[off:len(c.bytes)-2])
			binary.BigEndian.PutUint16(c.bytes[off:], 2)
			return c
		}(), 4, base.marks["classAccess"]},
		{"class-flags", stockS2bLinkVerifyPatchU2(base, "classAccess", 0x0601), 4, base.marks["classAccess"]},
	} {
		t.Run("class/"+tc.name, func(t *testing.T) { assertClass(t, tc.c, tc.code, tc.off) })
	}
	trailing := stockS2bLinkVerifyClass{bytes: append(append([]byte(nil), base.bytes...), 0), marks: base.marks}
	t.Run("class/trailing", func(t *testing.T) { assertClass(t, trailing, 1, len(base.bytes)) })
	clinit := stockS2bLinkVerifyBuildClass("HasClinit", []stockS2bLinkVerifyMethod{{name: "<clinit>", descriptor: "()V", access: 8, code: []byte{0xb1}}}, nil, 0)
	t.Run("class/clinit", func(t *testing.T) { assertClass(t, clinit, 4, clinit.marks["method1.access"]) })

	byteCases := []struct {
		name string
		m    stockS2bLinkVerifyMethod
		code uint8
		pc   uint32
	}{
		{"truncated-b8", stockS2bLinkVerifyMethod{name: "bad", descriptor: "()I", access: 9, code: []byte{0xb8, 0}, maxStack: 1}, 2, 0},
		{"pop-underflow", stockS2bLinkVerifyMethod{name: "bad", descriptor: "()V", access: 9, code: []byte{0x57, 0xb1}}, 3, 0},
		{"ireturn-empty", stockS2bLinkVerifyMethod{name: "bad", descriptor: "()I", access: 9, code: []byte{0xac}, maxStack: 1}, 5, 0},
		{"ireturn-two", stockS2bLinkVerifyMethod{name: "bad", descriptor: "()I", access: 9, code: []byte{3, 4, 0xac}, maxStack: 2}, 5, 2},
		{"return-nonempty", stockS2bLinkVerifyMethod{name: "bad", descriptor: "()V", access: 9, code: []byte{3, 0xb1}, maxStack: 1}, 5, 1},
		{"wrong-return-opcode-I", stockS2bLinkVerifyMethod{name: "bad", descriptor: "()I", access: 9, code: []byte{0xb1}}, 5, 0},
		{"wrong-return-opcode-V", stockS2bLinkVerifyMethod{name: "bad", descriptor: "()V", access: 9, code: []byte{3, 0xac}, maxStack: 1}, 5, 1},
		{"unreachable-unsupported", stockS2bLinkVerifyMethod{name: "bad", descriptor: "()I", access: 9, code: []byte{3, 0xac, 0xbb}, maxStack: 1}, 6, 2},
		{"fallthrough", stockS2bLinkVerifyMethod{name: "bad", descriptor: "()I", access: 9, code: []byte{3}, maxStack: 1}, 7, 0},
		{"local-range", stockS2bLinkVerifyMethod{name: "bad", descriptor: "()I", access: 9, code: []byte{0x15, 1, 0xac}, maxStack: 1, maxLocals: 1}, 8, 0},
		{"stack-capacity", stockS2bLinkVerifyMethod{name: "bad", descriptor: "()I", access: 9, code: []byte{3, 4, 0x60, 0xac}, maxStack: 1}, 9, 1},
		{"definite-init", stockS2bLinkVerifyMethod{name: "bad", descriptor: "(I)I", access: 9, code: []byte{0x1b, 0xac}, maxStack: 1, maxLocals: 2}, 11, 0},
		{"target-operand", stockS2bLinkVerifyMethod{name: "bad", descriptor: "()I", access: 9, code: []byte{0xa7, 0, 4, 0x11, 0, 1, 0xac}, maxStack: 1}, 15, 0},
		{"target-after-code", stockS2bLinkVerifyMethod{name: "bad", descriptor: "()I", access: 9, code: []byte{0xa7, 0, 3}, maxStack: 0}, 15, 0},
	}
	for _, tc := range byteCases {
		t.Run("bytecode/"+tc.name, func(t *testing.T) {
			c := stockS2bLinkVerifyBuildClass("ByteErrors", []stockS2bLinkVerifyMethod{tc.m}, nil, 0)
			_, m, _, _, _ := s.register(t, c)
			stockS2bLinkVerifyMethodRecord(t, m.methods[1], 2, tc.code, tc.pc)
		})
	}
	// Unsupported opcodes are predecoded even when unreachable; target checks
	// are independently covered above with otherwise supported instruction bytes.
	priority := stockS2bLinkVerifyBuildClass("UnsupportedPriority", []stockS2bLinkVerifyMethod{{name: "bad", descriptor: "()I", access: 9, code: []byte{3, 0xac, 0xa7, 0, 1, 0xbb}, maxStack: 1}}, nil, 0)
	_, pm, _, _, _ := s.register(t, priority)
	stockS2bLinkVerifyMethodRecord(t, pm.methods[1], 2, 6, 5)
	// Six arguments are consumed in order and a V target leaves no value.
	six := stockS2bLinkVerifyBuildClass("SixArgs", []stockS2bLinkVerifyMethod{{name: "sink", descriptor: "(IIIIII)V", access: 0x0a, code: []byte{0xb1}, maxLocals: 6}, {name: "caller", descriptor: "(IIIIII)V", access: 9, code: []byte{0x1a, 0x1b, 0x1c, 0x1d, 0x15, 4, 0x15, 5, 0xb8, 0, 0, 0xb1}, maxStack: 6, maxLocals: 6, calls: []stockS2bLinkVerifyCallPatch{{8, 0}}}}, []stockS2bLinkVerifyCallSymbol{{owner: "SixArgs", name: "sink", descriptor: "(IIIIII)V"}}, 0)
	_, sm, _, _, _ := s.register(t, six)
	stockS2bLinkVerifyMethodRecord(t, sm.methods[2], 0, 0, 0)
	if len(sm.calls) != 1 || sm.calls[0].argc != 6 || sm.calls[0].returnKind != 0 || sm.calls[0].target != 1 {
		t.Fatalf("sixarg cache=%+v", sm.calls)
	}
	under := stockS2bLinkVerifyBuildClass("InvokeUnderflow", []stockS2bLinkVerifyMethod{{name: "target", descriptor: "(II)I", access: 0x0a, code: []byte{0x1a, 0xac}, maxStack: 1, maxLocals: 2}, {name: "caller", descriptor: "()I", access: 9, code: []byte{3, 0xb8, 0, 0, 0xac}, maxStack: 2, calls: []stockS2bLinkVerifyCallPatch{{1, 0}}}}, []stockS2bLinkVerifyCallSymbol{{owner: "InvokeUnderflow", name: "target", descriptor: "(II)I"}}, 0)
	_, um, _, _, _ := s.register(t, under)
	stockS2bLinkVerifyMethodRecord(t, um.methods[2], 2, 3, 1)
}

func stockS2bLinkVerifyCommand(t *testing.T, command string, args ...string) string {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	out, err := exec.CommandContext(ctx, command, args...).CombinedOutput()
	if err != nil {
		t.Fatalf("%s %v: %v\n%s", command, args, err, out)
	}
	return string(out)
}
func stockS2bLinkVerifyCompile(t *testing.T, sources []string) (string, map[string][]byte) {
	t.Helper()
	dir := t.TempDir()
	args := []string{"--release", "8", "-d", dir}
	args = append(args, sources...)
	stockS2bLinkVerifyCommand(t, "javac", args...)
	out := make(map[string][]byte)
	for _, source := range sources {
		name := strings.TrimSuffix(filepath.Base(source), filepath.Ext(source))
		raw, err := os.ReadFile(filepath.Join(dir, name+".class"))
		if err != nil {
			t.Fatal(err)
		}
		out[name] = raw
	}
	return dir, out
}
func stockS2bLinkVerifyEnqueues(raw []byte, methodName string) (int, int) {
	p := stockS2bLinkVerifyParseTrusted(raw)
	var code []byte
	var argc uint8
	for _, m := range p.methods {
		if string(m.name) == methodName {
			code = m.code
			argc, _, _ = stockS2bLinkVerifyDescriptor(m.descriptor)
			break
		}
	}
	if len(code) == 0 {
		panic("method absent")
	}
	starts := make(map[int]bool)
	for pc := 0; pc < len(code); pc += stockS2bLinkVerifyWidth(code[pc]) {
		starts[pc] = true
	}
	states := make(map[int]uint8)
	queued := make(map[int]bool)
	queue := []int{0}
	states[0] = uint8((1 << argc) - 1)
	queued[0] = true
	enqueues := 1
	merge := func(pc int, mask uint8) {
		if !starts[pc] {
			panic("bad trusted target")
		}
		old, seen := states[pc]
		next := mask
		if seen {
			next = old & mask
		}
		if !seen || next != old {
			states[pc] = next
			if !queued[pc] {
				queue = append(queue, pc)
				queued[pc] = true
				enqueues++
			}
		}
	}
	for len(queue) > 0 {
		pc := queue[0]
		queue = queue[1:]
		queued[pc] = false
		mask := states[pc]
		op := code[pc]
		w := stockS2bLinkVerifyWidth(op)
		switch {
		case op >= 0x3b && op <= 0x3e:
			mask |= 1 << uint(op-0x3b)
		case op == 0x36:
			mask |= 1 << uint(code[pc+1])
		}
		if op == 0xac || op == 0xb1 {
			continue
		}
		if op == 0xa7 {
			merge(pc+int(int16(binary.BigEndian.Uint16(code[pc+1:]))), mask)
			continue
		}
		if op >= 0x99 && op <= 0xa4 {
			merge(pc+int(int16(binary.BigEndian.Uint16(code[pc+1:]))), mask)
			merge(pc+w, mask)
			continue
		}
		merge(pc+w, mask)
	}
	return enqueues, len(code)
}

func TestStockS2bLinkVerifyExactFourteenClassesAndCallCaches(t *testing.T) {
	names := []string{"M1Baseline", "Constants", "LocalsAndArithmetic", "Comparisons", "Loops", "IntegerArithmetic", "IntegerBitwise", "IntegerConstants", "IntegerConversions", "IntegerShifts", "WideIntegerConstant", "M3aFrames", "M3aRecursion", "M3aStaticCalls"}
	wantHash := map[string]string{"M1Baseline": "1e71a54ba434b943b44c8633a1fb9e4c52e4f435eaeffb5ebf47e546c49d0813", "Constants": "6b3473ae373a53d0c6a8a2a8df4b00b978a9c2db4890bacf14900717d60701a1", "LocalsAndArithmetic": "423ca06bab0adebb43e8d98df8438840fe4635bfa73e2e6c28b6397d1b195653", "Comparisons": "5c4a076b97e146ed73e14a5bea4f3722d3a18be284abd23bf0a56a5848d3cb9e", "Loops": "c9043994623a900a6c1f4ed096c9d1c23783842d2e5e1406646deea9db20fa38", "IntegerArithmetic": "69c6a01e0045efc1caa3e2a9c598a4dd75530fe74f5b4e2c378689feb1c27d43", "IntegerBitwise": "8cece8e7b75cf657b146eade5cd73d8616826f73ac14427e8e1f0c51fa9dc018", "IntegerConstants": "189ac9b47a7f09a080a64be3e662aba0045440ca78a6d65674256e0cb0aaf0fd", "IntegerConversions": "ba383508690bf9aab643b26af435077cc002d8b4ccd61cd6b52b734a82e7fd08", "IntegerShifts": "1cd887856a8e6922e14c5246c3c563dd5914d499511b0be0fc9b35178d9df2bc", "WideIntegerConstant": "fbf7d7498a50fa0ed8adba88ef74f702cdd4bc82fdab94ba75c8e54a77eb9137", "M3aFrames": "c1807e5289b9981e4804e1bc37575fd44dff1feebb914a235dbd5a32d173d5ad", "M3aRecursion": "3bfec29278c225bb553daf4bd242f61fafe6e7ea1c3a4e31c1fd699c912ac842", "M3aStaticCalls": "316f4878ac2fc59113ee81d20e76304f5eaa32575b3931088b1b1da1adb21156"}
	wantCalls := map[string]int{"M3aFrames": 14, "M3aRecursion": 16, "M3aStaticCalls": 21}
	wantLiterals := map[string]int{"IntegerConstants": 7, "WideIntegerConstant": 1, "M3aStaticCalls": 1}
	sources := make([]string, len(names))
	for i, n := range names {
		sources[i] = filepath.Join("..", "..", "testdata", "differential", n+".java")
	}
	_, classes := stockS2bLinkVerifyCompile(t, sources)
	s := stockS2bLinkVerifySetupRuntime(t)
	defer s.close()
	legacy := stockS2bLinkVerifyS2aParser(t)
	legacyAt, _ := s.e.mustCreate(legacy.init, stockS2bLinkVerifyCreateGas)
	legacyHash := crypto.Keccak256Hash(s.e.state.StateDB.GetCode(legacyAt))
	adapterLinker, _ := stockS2bLinkVerifyDeployLinker(t, s.e, s.linker, s.analyzerAt, s.analyzerHash, legacyHash)
	totalCalls := 0
	for _, name := range names {
		t.Run(name, func(t *testing.T) {
			raw := classes[name]
			if got := fmt.Sprintf("%x", sha256.Sum256(raw)); got != wantHash[name] {
				t.Fatalf("raw SHA-256=%s want=%s", got, wantHash[name])
			}
			r, m, rawAt, pageHash, payloadHash := s.register(t, stockS2bLinkVerifyClass{bytes: raw})
			if int(r.calls) != wantCalls[name] || len(m.calls) != wantCalls[name] || int(r.literals) != wantLiterals[name] {
				t.Fatalf("counts methods/literals/calls=%d/%d/%d", r.methods, r.literals, r.calls)
			}
			oldID, _, _, oldMethods, _ := stockS2bLinkVerifyS2aRegister(t, s.e, legacy, legacyAt, rawAt, pageHash, payloadHash)
			if oldMethods != r.methods {
				t.Fatalf("old/new method counts=%d/%d", oldMethods, r.methods)
			}
			adapted := stockS2bLinkVerifyAdapt(t, s.e, s.linker, adapterLinker, legacyAt, oldID, stockS2bLinkVerifyCallGas)
			if adapted.id != r.id || adapted.metadataHash != r.metadataHash || adapted.methods != r.methods || adapted.literals != r.literals || adapted.calls != r.calls || len(adapted.tx.logs) != 1 {
				t.Fatalf("adapter/direct mismatch direct=%+v adapter=%+v", r, adapted)
			}
			totalCalls += len(m.calls)
			if name == "WideIntegerConstant" {
				if len(m.methods) != 3 || m.methods[1].errorDomain != 1 || m.methods[1].errorCode != 5 || m.methods[1].literalCount != 0 || m.methods[2].literalCount != 1 {
					t.Fatalf("wide records=%+v", m.methods)
				}
			}
		})
	}
	if totalCalls != 51 {
		t.Fatalf("M3a call records=%d want51", totalCalls)
	}
}

func TestStockS2bLinkVerifyDenseRevisitedCFGJavaOracle(t *testing.T) {
	var slow, commonBody strings.Builder
	for i := 0; i < 30; i++ {
		slow.WriteString("x=-x;\n")
		commonBody.WriteString("x=-x;\n")
	}
	source := fmt.Sprintf(`public class S2bDenseRevisit {
 public static int revisit(int x) { int y; if(x==0){y=7;}else{%s} %s return x; }
 public static void main(String[] a){if(revisit(0)!=0||revisit(1)!=1)throw new AssertionError();System.out.print("dense-ok");}
}`, slow.String(), commonBody.String())
	dir := t.TempDir()
	javaFile := filepath.Join(dir, "S2bDenseRevisit.java")
	if err := os.WriteFile(javaFile, []byte(source), 0600); err != nil {
		t.Fatal(err)
	}
	stockS2bLinkVerifyCommand(t, "javac", "--release", "8", "-d", dir, javaFile)
	raw, err := os.ReadFile(filepath.Join(dir, "S2bDenseRevisit.class"))
	if err != nil {
		t.Fatal(err)
	}
	if got := strings.TrimSpace(stockS2bLinkVerifyCommand(t, "java", "-Xmx64m", "-Xss512k", "-Xverify:all", "-cp", dir, "S2bDenseRevisit")); got != "dense-ok" {
		t.Fatalf("Java oracle=%q", got)
	}
	// If a Java 8 runtime is locally installed, require it too; absence is logged,
	// not replaced by a fabricated oracle.
	var java8 string
	if home := os.Getenv("JAVA8_HOME"); home != "" {
		java8 = filepath.Join(home, "bin", "java")
	} else {
		matches, _ := filepath.Glob("/usr/lib/jvm/java-8*/bin/java")
		if len(matches) > 0 {
			java8 = matches[0]
		}
	}
	if java8 != "" {
		if got := strings.TrimSpace(stockS2bLinkVerifyCommand(t, java8, "-Xmx64m", "-Xss512k", "-Xverify:all", "-cp", dir, "S2bDenseRevisit")); got != "dense-ok" {
			t.Fatalf("Java8 oracle=%q", got)
		}
	} else {
		t.Log("Java 8 runtime unavailable; Java --release 8/current JVM -Xverify:all was used")
	}
	enqueues, codeLen := stockS2bLinkVerifyEnqueues(raw, "revisit")
	if codeLen > 256 || enqueues <= codeLen+1 {
		t.Fatalf("dense CFG code=%d cumulative enqueues=%d; fixture does not exceed obsolete len+1 bound", codeLen, enqueues)
	}
	s := stockS2bLinkVerifySetupRuntime(t)
	defer s.close()
	r, m, _, _, _ := s.register(t, stockS2bLinkVerifyClass{bytes: raw})
	var found bool
	for _, mm := range m.methods {
		if mm.nameHash == crypto.Keccak256Hash([]byte("revisit")) {
			stockS2bLinkVerifyMethodRecord(t, mm, 0, 0, 0)
			found = true
		}
	}
	if !found || r.methods < 2 {
		t.Fatal("dense method missing")
	}
	t.Logf("dense valid CFG code=%d cumulativeEnqueues=%d methods=%d", codeLen, enqueues, r.methods)
}

func stockS2bLinkVerifyFindFixture(t *testing.T, want string) []byte {
	t.Helper()
	root := filepath.Join("..", "..", "testdata", "stock", "s2b-link")
	var found [][]byte
	_ = filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil || info == nil || info.IsDir() || info.Size() > 20000 {
			return nil
		}
		blob, readErr := os.ReadFile(path)
		if readErr != nil {
			return nil
		}
		candidates := [][]byte{blob}
		trimmed := strings.TrimSpace(string(blob))
		if decoded, decodeErr := hex.DecodeString(strings.TrimPrefix(trimmed, "0x")); decodeErr == nil {
			candidates = append(candidates, decoded)
		}
		for _, candidate := range candidates {
			if fmt.Sprintf("%x", sha256.Sum256(candidate)) == want {
				found = append(found, append([]byte(nil), candidate...))
			}
		}
		return nil
	})
	if len(found) != 1 {
		t.Fatalf("shared S2b-L fixture SHA-256 %s matches=%d under %s (harness integration dependency is absent or ambiguous)", want, len(found), root)
	}
	return found[0]
}
func stockS2bLinkVerifyLiteralMethods(total int) []stockS2bLinkVerifyMethod {
	methods := make([]stockS2bLinkVerifyMethod, 31)
	remaining := total
	for i := range methods {
		n := remaining
		if n > 64 {
			n = 64
		}
		remaining -= n
		var code []byte
		for j := 0; j < n; j++ {
			code = append(code, 0x12, 10, 0x3b)
		}
		if n > 0 {
			code = append(code, 0x1a, 0xac)
		} else {
			code = append(code, 3, 0xac)
		}
		methods[i] = stockS2bLinkVerifyMethod{name: fmt.Sprintf("m%02d", i), descriptor: "()I", access: 9, code: code, maxStack: 1, maxLocals: 1}
	}
	if remaining != 0 {
		panic("literal fixture overflow")
	}
	return methods
}
func stockS2bLinkVerifyCallsClass(total int) stockS2bLinkVerifyClass {
	code := make([]byte, 0, total*4+2)
	patches := make([]stockS2bLinkVerifyCallPatch, total)
	for i := 0; i < total; i++ {
		patches[i] = stockS2bLinkVerifyCallPatch{len(code), 0}
		code = append(code, 0xb8, 0, 0, 0x57)
	}
	code = append(code, 3, 0xac)
	return stockS2bLinkVerifyBuildClass(fmt.Sprintf("Calls%d", total), []stockS2bLinkVerifyMethod{{name: "target", descriptor: "()I", access: 0x0a, code: []byte{3, 0xac}, maxStack: 1}, {name: "caller", descriptor: "()I", access: 9, code: code, maxStack: 1, calls: patches}}, []stockS2bLinkVerifyCallSymbol{{owner: fmt.Sprintf("Calls%d", total), name: "target", descriptor: "()I"}}, 0)
}

func TestStockS2bLinkVerifyCapsExactRawGasRollbackAndRetry(t *testing.T) {
	s := stockS2bLinkVerifySetupRuntime(t)
	defer s.close()
	code256 := append(bytes.Repeat([]byte{0}, 254), 3, 0xac)
	cp512 := stockS2bLinkVerifyBuildClass("CP512Code256", []stockS2bLinkVerifyMethod{{name: "edge", descriptor: "()I", access: 9, code: code256, maxStack: 1}}, nil, 512)
	if len(cp512.bytes) > 4096 {
		t.Fatalf("CP512 raw=%d", len(cp512.bytes))
	}
	_, bm, _, _, _ := s.register(t, cp512)
	if bm.methods[1].codeLen != 256 {
		t.Fatalf("Code boundary=%d", bm.methods[1].codeLen)
	}
	valid31 := make([]stockS2bLinkVerifyMethod, 31)
	for i := range valid31 {
		valid31[i] = stockS2bLinkVerifyMethod{name: fmt.Sprintf("m%02d", i), descriptor: "()I", access: 9, code: []byte{3, 0xac}, maxStack: 1}
	}
	methods32 := stockS2bLinkVerifyBuildClass("Methods32", valid31, nil, 0)
	r32, _, _, _, _ := s.register(t, methods32)
	if r32.methods != 32 {
		t.Fatalf("methods boundary=%d", r32.methods)
	}
	valid32 := append(append([]stockS2bLinkVerifyMethod(nil), valid31...), stockS2bLinkVerifyMethod{name: "extra", descriptor: "()I", access: 9, code: []byte{3, 0xac}, maxStack: 1})
	methods33 := stockS2bLinkVerifyBuildClass("Methods33", valid32, nil, 0)
	pa, ph, pvh, _ := stockS2bLinkVerifyDeployPage(t, s.e, s.page, methods33.bytes)
	tx := s.e.apply(&s.linkerAt, stockS2bLinkVerifyCallData(t, s.linker, "registerClass", pa, ph, pvh), stockS2bLinkVerifyCallGas)
	stockS2bLinkVerifyAssertRevert(t, tx, "S2bClassError(uint256,uint256)", 5, uint64(methods33.marks["methodCount"]))
	lit256 := stockS2bLinkVerifyBuildClass("Literals256", stockS2bLinkVerifyLiteralMethods(256), nil, 0)
	lr, _, _, _, _ := s.register(t, lit256)
	if lr.literals != 256 {
		t.Fatalf("literal boundary=%d", lr.literals)
	}
	lit257 := stockS2bLinkVerifyBuildClass("Literals257", stockS2bLinkVerifyLiteralMethods(257), nil, 0)
	pa, ph, pvh, _ = stockS2bLinkVerifyDeployPage(t, s.e, s.page, lit257.bytes)
	tx = s.e.apply(&s.linkerAt, stockS2bLinkVerifyCallData(t, s.linker, "registerClass", pa, ph, pvh), stockS2bLinkVerifyCallGas)
	stockS2bLinkVerifyAssertRevert(t, tx, "S2bClassError(uint256,uint256)", 5, 0)
	calls32 := stockS2bLinkVerifyCallsClass(32)
	cr, _, _, _, _ := s.register(t, calls32)
	if cr.calls != 32 {
		t.Fatalf("call boundary=%d", cr.calls)
	}
	calls33 := stockS2bLinkVerifyCallsClass(33)
	pa, ph, pvh, _ = stockS2bLinkVerifyDeployPage(t, s.e, s.page, calls33.bytes)
	tx = s.e.apply(&s.linkerAt, stockS2bLinkVerifyCallData(t, s.linker, "registerClass", pa, ph, pvh), stockS2bLinkVerifyCallGas)
	stockS2bLinkVerifyAssertRevert(t, tx, "S2bClassError(uint256,uint256)", 5, 0)

	cap := stockS2bLinkVerifyFindFixture(t, "0e3e962a3de46d9c019c8e8e3e846b304622fc969144713f9ad6922c33946f33")
	if len(cap) != 3574 {
		t.Fatalf("cap raw=%d", len(cap))
	}
	rawAt, pageHash, payloadHash, pageTx := stockS2bLinkVerifyDeployPage(t, s.e, s.page, cap)
	positive := stockS2bLinkVerifyRegister(t, s.e, s.linker, s.linkerAt, rawAt, pageHash, payloadHash, stockS2bLinkVerifyCreateGas)
	if positive.methods != 32 || positive.literals != 256 || positive.calls != 32 || positive.tx.result.UsedGas > stockS2bLinkVerifyCreateGas {
		t.Fatalf("cap registration counts/gas=%d/%d/%d/%d", positive.methods, positive.literals, positive.calls, positive.tx.result.UsedGas)
	}
	meta := s.e.state.StateDB.GetCode(positive.metadata)
	if len(meta) != 7937 || crypto.Keccak256Hash(meta) != positive.metadataHash {
		t.Fatalf("cap metadata=%d", len(meta))
	}
	stockS2bLinkVerifyValidateMetadata(t, cap, rawAt, pageHash, payloadHash, s.analyzerHash, meta)
	legacy := stockS2bLinkVerifyS2aParser(t)
	legacyAt, _ := s.e.mustCreate(legacy.init, stockS2bLinkVerifyCreateGas)
	legacyHash := crypto.Keccak256Hash(s.e.state.StateDB.GetCode(legacyAt))
	oldID, _, _, oldMethods, _ := stockS2bLinkVerifyS2aRegister(t, s.e, legacy, legacyAt, rawAt, pageHash, payloadHash)
	if oldMethods != 32 {
		t.Fatalf("cap old methods=%d", oldMethods)
	}
	adapterLinker, _ := stockS2bLinkVerifyDeployLinker(t, s.e, s.linker, s.analyzerAt, s.analyzerHash, legacyHash)
	capAdapter := stockS2bLinkVerifyAdapt(t, s.e, s.linker, adapterLinker, legacyAt, oldID, stockS2bLinkVerifyCreateGas)
	if capAdapter.id != positive.id || capAdapter.metadataHash != positive.metadataHash || capAdapter.methods != 32 || capAdapter.literals != 256 || capAdapter.calls != 32 || capAdapter.tx.result.UsedGas > stockS2bLinkVerifyCreateGas {
		t.Fatalf("cap adapter=%+v", capAdapter)
	}
	fresh, _ := stockS2bLinkVerifyDeployLinker(t, s.e, s.linker, s.analyzerAt, s.analyzerHash, legacyHash)
	if !bytes.Equal(s.e.state.StateDB.GetCode(fresh), s.e.state.StateDB.GetCode(s.linkerAt)) {
		t.Fatal("equivalent linker code differs")
	}
	beforeNonce := s.e.state.StateDB.GetNonce(fresh)
	internal := crypto.CreateAddress(fresh, beforeNonce)
	gas := positive.tx.result.UsedGas
	if gas == 0 {
		t.Fatal("zero cap gas")
	}
	failed := s.e.apply(&fresh, stockS2bLinkVerifyCallData(t, s.linker, "registerClass", rawAt, pageHash, payloadHash), gas-1)
	if failed.coreErr != nil || failed.result == nil || !errors.Is(failed.result.Err, vm.ErrOutOfGas) || len(failed.result.ReturnData) != 0 || len(failed.logs) != 0 {
		t.Fatalf("one-less gas core=%v evm=%v data=%x logs=%d", failed.coreErr, stockS2bLinkVerifyResultErr(failed.result), stockS2bLinkVerifyResultData(failed.result), len(failed.logs))
	}
	if s.e.state.StateDB.GetNonce(fresh) != beforeNonce || len(s.e.state.StateDB.GetCode(internal)) != 0 {
		t.Fatal("OOG retained internal CREATE nonce/page")
	}
	if at, h := stockS2bLinkVerifyRecord(t, s.e, s.linker, fresh, positive.id); at != (common.Address{}) || h != (common.Hash{}) {
		t.Fatal("OOG retained registry record")
	}
	retried := stockS2bLinkVerifyRegister(t, s.e, s.linker, fresh, rawAt, pageHash, payloadHash, stockS2bLinkVerifyCreateGas)
	if retried.id != positive.id || retried.metadataHash != positive.metadataHash || retried.methods != 32 || retried.literals != 256 || retried.calls != 32 || len(retried.tx.logs) != 1 {
		t.Fatalf("retry=%+v", retried)
	}
	nonce := s.e.state.StateDB.GetNonce(fresh)
	duplicate := stockS2bLinkVerifyRegister(t, s.e, s.linker, fresh, rawAt, pageHash, payloadHash, stockS2bLinkVerifyCreateGas)
	if duplicate.methods != 32 || duplicate.literals != 256 || duplicate.calls != 32 || len(duplicate.tx.logs) != 0 || s.e.state.StateDB.GetNonce(fresh) != nonce {
		t.Fatal("duplicate did not return real counts without CREATE/event")
	}
	t.Logf("cap pageGas=%d registrationGas=%d adapterGas=%d oneLess=%d retryGas=%d", pageTx.result.UsedGas, positive.tx.result.UsedGas, capAdapter.tx.result.UsedGas, gas-1, retried.tx.result.UsedGas)
}

func stockS2bLinkVerifyPutField(v *big.Int, x uint64, shift uint) {
	v.Or(v, new(big.Int).Lsh(new(big.Int).SetUint64(x), shift))
}
func stockS2bLinkVerifyReplaceField(v *big.Int, x uint64, shift, bits uint) {
	mask := new(big.Int).Lsh(new(big.Int).Sub(new(big.Int).Lsh(big.NewInt(1), bits), big.NewInt(1)), shift)
	v.AndNot(v, mask)
	stockS2bLinkVerifyPutField(v, x, shift)
}
func stockS2bLinkVerifySyntheticMetadata(raw []byte, rawAt common.Address, pageHash, payloadHash common.Hash, literals, calls uint16) []byte {
	p := stockS2bLinkVerifyParseTrusted(raw)
	words := make([][32]byte, 8+5*len(p.methods))
	words[0] = [32]byte(crypto.Keccak256Hash([]byte("JVMEVM:S2B:LINK:METADATA:4")))
	h1 := new(big.Int).SetBytes(rawAt[:])
	stockS2bLinkVerifyPutField(h1, uint64(p.access), 160)
	h1.FillBytes(words[1][:])
	words[2], words[3], words[4] = [32]byte(pageHash), [32]byte(payloadHash), [32]byte(crypto.Keccak256Hash(p.name))
	h5 := new(big.Int)
	stockS2bLinkVerifyPutField(h5, uint64(len(raw)), 0)
	stockS2bLinkVerifyPutField(h5, uint64(p.cpCount), 32)
	stockS2bLinkVerifyPutField(h5, uint64(len(p.methods)), 48)
	stockS2bLinkVerifyPutField(h5, uint64(literals), 64)
	stockS2bLinkVerifyPutField(h5, uint64(calls), 80)
	h5.FillBytes(words[5][:])
	for i, rm := range p.methods {
		base := 8 + 5*i
		words[base] = [32]byte(crypto.Keccak256Hash(rm.name))
		words[base+1] = [32]byte(crypto.Keccak256Hash(rm.descriptor))
		v := new(big.Int)
		stockS2bLinkVerifyPutField(v, uint64(i), 0)
		stockS2bLinkVerifyPutField(v, uint64(rm.access), 16)
		if i == 0 {
			stockS2bLinkVerifyPutField(v, 1, 112)
			stockS2bLinkVerifyPutField(v, 6, 120)
		} else {
			argc, ret, _ := stockS2bLinkVerifyDescriptor(rm.descriptor)
			stockS2bSet := stockS2bLinkVerifyPutField
			stockS2bSet(v, uint64(rm.codeOffset), 32)
			stockS2bSet(v, uint64(len(rm.code)), 64)
			stockS2bSet(v, uint64(rm.maxStack), 80)
			stockS2bSet(v, uint64(rm.maxLocals), 88)
			stockS2bSet(v, uint64(argc), 96)
			stockS2bSet(v, uint64(ret), 104)
			starts := new(big.Int)
			for pc := 0; pc < len(rm.code); pc += stockS2bLinkVerifyWidth(rm.code[pc]) {
				starts.SetBit(starts, pc, 1)
			}
			starts.FillBytes(words[base+3][:])
		}
		v.FillBytes(words[base+2][:])
	}
	var out []byte
	for _, w := range words {
		out = append(out, w[:]...)
	}
	out = append(out, make([]byte, int(literals)*8+int(calls)*16)...)
	return out
}
func stockS2bLinkVerifyMockReturnRuntime(data []byte, patchH6 bool) []byte {
	if len(data) > math.MaxUint16 {
		panic("mock return too large")
	}
	const prefix = 19
	out := []byte{0x61, byte(len(data) >> 8), byte(len(data)), 0x61, 0, prefix, 0x5f, 0x39, 0x30, 0x3f, 0x61, 0x01, 0x60, 0x52, 0x61, byte(len(data) >> 8), byte(len(data)), 0x5f, 0xf3}
	if !patchH6 {
		out[8], out[9], out[10], out[11], out[12], out[13] = 0x5f, 0x50, 0x5f, 0x50, 0x5f, 0x50
	}
	return append(out, data...)
}
func stockS2bLinkVerifyMockResponse(t *testing.T, analyzer stockS2bLinkVerifyArtifact, metadata []byte, methods, literals, calls uint16) []byte {
	t.Helper()
	out, err := analyzer.abi.Methods["analyze"].Outputs.Pack(metadata, methods, literals, calls)
	if err != nil {
		t.Fatal(err)
	}
	return out
}

func TestStockS2bLinkVerifyBoundedAnalyzerResponsesAndPinnedMockBoundary(t *testing.T) {
	page := stockS2bLinkVerifyPage(t)
	analyzer := stockS2bLinkVerifyLoadArtifact(t, "S2bAnalyzeModule")
	linker := stockS2bLinkVerifyLoadArtifact(t, "S2bClassLinker")
	e := stockS2bLinkVerifyNewEnv(t)
	defer e.close()
	class := stockS2bLinkVerifySimple([]byte{3, 0xac}, 1, 0, "()I")
	rawAt, pageHash, payloadHash, _ := stockS2bLinkVerifyDeployPage(t, e, page, class.bytes)
	baseMeta := stockS2bLinkVerifySyntheticMetadata(class.bytes, rawAt, pageHash, payloadHash, 0, 0)
	if len(baseMeta) != 576 {
		t.Fatalf("synthetic metadata=%d", len(baseMeta))
	}
	baseMeta[256] ^= 1 // Fabricated method name hash: linker must not redo per-record Java analysis.
	baseResponse := stockS2bLinkVerifyMockResponse(t, analyzer, baseMeta, 2, 0, 0)
	deploy := func(t *testing.T, response []byte, patch bool) (common.Address, common.Address, common.Hash) {
		t.Helper()
		runtime := stockS2bLinkVerifyMockReturnRuntime(response, patch)
		mock, _ := stockS2bLinkVerifyDeployRaw(t, e, runtime)
		mh := crypto.Keccak256Hash(runtime)
		legacy := crypto.Keccak256Hash([]byte("TEST-LEGACY-NONZERO"))
		at, _ := stockS2bLinkVerifyDeployLinker(t, e, linker, mock, mh, legacy)
		return mock, at, mh
	}
	_, configured, mockHash := deploy(t, baseResponse, true)
	ok := stockS2bLinkVerifyRegister(t, e, linker, configured, rawAt, pageHash, payloadHash, stockS2bLinkVerifyCallGas)
	if ok.methods != 2 || ok.literals != 0 || ok.calls != 0 || len(ok.tx.logs) != 1 {
		t.Fatalf("configured canonical mock=%+v", ok)
	}
	issued := e.state.StateDB.GetCode(ok.metadata)
	if len(issued) != 577 || common.Hash(issued[1+6*32:1+7*32]) != mockHash || issued[1+256] == crypto.Keccak256Hash(stockS2bLinkVerifyParseTrusted(class.bytes).methods[0].name)[0] {
		t.Fatal("mock response was not issued verbatim with actual H6")
	}
	cases := map[string]func([]byte) []byte{
		"offset":          func(b []byte) []byte { b = append([]byte(nil), b...); b[31] = 0x81; return b },
		"count-high-bits": func(b []byte) []byte { b = append([]byte(nil), b...); b[32] = 1; return b },
		"trailing":        func(b []byte) []byte { return append(append([]byte(nil), b...), 0) },
		"declared-byte-length": func(b []byte) []byte {
			b = append([]byte(nil), b...)
			binary.BigEndian.PutUint64(b[152:], uint64(len(baseMeta)+1))
			return b
		},
		"magic":          func(b []byte) []byte { b = append([]byte(nil), b...); b[160] ^= 1; return b },
		"H1-high":        func(b []byte) []byte { b = append([]byte(nil), b...); b[160+32] = 1; return b },
		"raw-hash":       func(b []byte) []byte { b = append([]byte(nil), b...); b[160+64] ^= 1; return b },
		"payload-hash":   func(b []byte) []byte { b = append([]byte(nil), b...); b[160+96] ^= 1; return b },
		"H5-high":        func(b []byte) []byte { b = append([]byte(nil), b...); b[160+160] = 1; return b },
		"H7":             func(b []byte) []byte { b = append([]byte(nil), b...); b[160+224+31] = 1; return b },
		"count-mismatch": func(b []byte) []byte { b = append([]byte(nil), b...); b[32+31] = 3; return b },
	}
	for name, mutate := range cases {
		t.Run(name, func(t *testing.T) {
			_, at, _ := deploy(t, mutate(baseResponse), true)
			nonce := e.state.StateDB.GetNonce(at)
			internal := crypto.CreateAddress(at, nonce)
			tx := e.apply(&at, stockS2bLinkVerifyCallData(t, linker, "registerClass", rawAt, pageHash, payloadHash), stockS2bLinkVerifyCallGas)
			stockS2bLinkVerifyAssertRevert(t, tx, "S2bLinkError(uint256)", 2)
			if e.state.StateDB.GetNonce(at) != nonce || len(e.state.StateDB.GetCode(internal)) != 0 {
				t.Fatal("malformed analyzer response partially committed")
			}
		})
	}
	t.Run("wrong-H6", func(t *testing.T) {
		_, at, _ := deploy(t, baseResponse, false)
		tx := e.apply(&at, stockS2bLinkVerifyCallData(t, linker, "registerClass", rawAt, pageHash, payloadHash), stockS2bLinkVerifyCallGas)
		stockS2bLinkVerifyAssertRevert(t, tx, "S2bLinkError(uint256)", 2)
	})
	t.Run("nonzero-padding", func(t *testing.T) {
		meta := stockS2bLinkVerifySyntheticMetadata(class.bytes, rawAt, pageHash, payloadHash, 1, 0)
		response := stockS2bLinkVerifyMockResponse(t, analyzer, meta, 2, 1, 0)
		response[len(response)-1] = 1
		_, at, _ := deploy(t, response, true)
		tx := e.apply(&at, stockS2bLinkVerifyCallData(t, linker, "registerClass", rawAt, pageHash, payloadHash), stockS2bLinkVerifyCallGas)
		stockS2bLinkVerifyAssertRevert(t, tx, "S2bLinkError(uint256)", 2)
	})
	t.Run("returndata-over-bound", func(t *testing.T) {
		_, at, _ := deploy(t, make([]byte, 8097), false)
		tx := e.apply(&at, stockS2bLinkVerifyCallData(t, linker, "registerClass", rawAt, pageHash, payloadHash), stockS2bLinkVerifyCallGas)
		stockS2bLinkVerifyAssertRevert(t, tx, "S2bLinkError(uint256)", 2)
	})
	methods33 := append([]byte(nil), baseMeta...)
	v := new(big.Int).SetBytes(methods33[5*32 : 6*32])
	stockS2bLinkVerifyReplaceField(v, 33, 48, 16)
	v.FillBytes(methods33[5*32 : 6*32])
	methods33 = append(methods33, make([]byte, 31*160)...)
	for _, tc := range []struct {
		name                     string
		metadata                 []byte
		methods, literals, calls uint16
	}{
		{"header-method-cap", methods33, 33, 0, 0},
		{"header-literal-cap", stockS2bLinkVerifySyntheticMetadata(class.bytes, rawAt, pageHash, payloadHash, 257, 0), 2, 257, 0},
		{"header-call-cap", stockS2bLinkVerifySyntheticMetadata(class.bytes, rawAt, pageHash, payloadHash, 0, 33), 2, 0, 33},
	} {
		t.Run(tc.name, func(t *testing.T) {
			response := stockS2bLinkVerifyMockResponse(t, analyzer, tc.metadata, tc.methods, tc.literals, tc.calls)
			_, at, _ := deploy(t, response, true)
			tx := e.apply(&at, stockS2bLinkVerifyCallData(t, linker, "registerClass", rawAt, pageHash, payloadHash), stockS2bLinkVerifyCallGas)
			stockS2bLinkVerifyAssertRevert(t, tx, "S2bLinkError(uint256)", 2)
		})
	}
}

func stockS2bLinkVerifyS2aRegister(t *testing.T, e *stockS2bLinkVerifyEnv, parser stockS2bLinkVerifyArtifact, at, raw common.Address, pageHash, payloadHash common.Hash) (common.Hash, common.Address, common.Hash, uint16, stockS2bLinkVerifyTx) {
	t.Helper()
	tx := e.mustCall(at, stockS2bLinkVerifyCallData(t, parser, "registerClass", raw, pageHash, payloadHash), stockS2bLinkVerifyCallGas)
	out := stockS2bLinkVerifyUnpack(t, parser, "registerClass", tx.result.ReturnData)
	return common.Hash(out[0].([32]byte)), out[1].(common.Address), common.Hash(out[2].([32]byte)), out[3].(uint16), tx
}
func stockS2bLinkVerifyS2aClassID(t *testing.T, parserHash common.Hash, raw common.Address, pageHash, payloadHash, metadataHash common.Hash) common.Hash {
	return stockS2bLinkVerifyABIHash(t, []string{"bytes32", "uint32", "bytes32", "address", "bytes32", "bytes32", "bytes32"}, crypto.Keccak256Hash([]byte("JVMEVM:S2A:CLASS")), uint32(3), parserHash, raw, pageHash, payloadHash, metadataHash)
}
func stockS2bLinkVerifyLegacyReply(t *testing.T, page common.Address, hash common.Hash) []byte {
	t.Helper()
	args := abi.Arguments{{Type: stockS2bLinkVerifyABIType("address")}, {Type: stockS2bLinkVerifyABIType("bytes32")}}
	out, err := args.Pack(page, hash)
	if err != nil {
		t.Fatal(err)
	}
	return out
}
func stockS2bLinkVerifyABIType(name string) abi.Type {
	typ, err := abi.NewType(name, "", nil)
	if err != nil {
		panic(err)
	}
	return typ
}

func TestStockS2bLinkVerifyS2aReparseAdapterAndNamespaces(t *testing.T) {
	page := stockS2bLinkVerifyPage(t)
	legacy := stockS2bLinkVerifyS2aParser(t)
	analyzer := stockS2bLinkVerifyLoadArtifact(t, "S2bAnalyzeModule")
	linker := stockS2bLinkVerifyLoadArtifact(t, "S2bClassLinker")
	e := stockS2bLinkVerifyNewEnv(t)
	defer e.close()
	legacyAt, _ := e.mustCreate(legacy.init, stockS2bLinkVerifyCreateGas)
	legacyHash := crypto.Keccak256Hash(e.state.StateDB.GetCode(legacyAt))
	analyzerAt, _ := e.mustCreate(analyzer.init, stockS2bLinkVerifyCreateGas)
	analyzerHash := crypto.Keccak256Hash(e.state.StateDB.GetCode(analyzerAt))
	class := stockS2bLinkVerifyBuildClass("AdapterProfile", []stockS2bLinkVerifyMethod{{name: "sink", descriptor: "(I)V", access: 0x0a, code: []byte{0x1a, 0x57, 0xb1}, maxStack: 1, maxLocals: 1}, {name: "id", descriptor: "(I)I", access: 0x0a, code: []byte{0x1a, 0xac}, maxStack: 1, maxLocals: 1}, {name: "caller", descriptor: "(I)I", access: 9, code: []byte{0x1a, 0xb8, 0, 0, 0xac}, maxStack: 1, maxLocals: 1, calls: []stockS2bLinkVerifyCallPatch{{1, 0}}}, {name: "useVoid", descriptor: "(I)I", access: 9, code: []byte{0x1a, 0xb8, 0, 0, 3, 0xac}, maxStack: 1, maxLocals: 1, calls: []stockS2bLinkVerifyCallPatch{{1, 1}}}}, []stockS2bLinkVerifyCallSymbol{{owner: "AdapterProfile", name: "id", descriptor: "(I)I"}, {owner: "AdapterProfile", name: "sink", descriptor: "(I)V"}}, 0)
	rawAt, pageHash, payloadHash, _ := stockS2bLinkVerifyDeployPage(t, e, page, class.bytes)
	oldID, oldMeta, oldMetaHash, oldMethods, _ := stockS2bLinkVerifyS2aRegister(t, e, legacy, legacyAt, rawAt, pageHash, payloadHash)
	if oldMethods != 5 || crypto.Keccak256Hash(e.state.StateDB.GetCode(oldMeta)) != oldMetaHash {
		t.Fatal("old S2a issuance")
	}
	linkerA, _ := stockS2bLinkVerifyDeployLinker(t, e, linker, analyzerAt, analyzerHash, legacyHash)
	direct := stockS2bLinkVerifyRegister(t, e, linker, linkerA, rawAt, pageHash, payloadHash, stockS2bLinkVerifyCallGas)
	nonce := e.state.StateDB.GetNonce(linkerA)
	adaptRetry := stockS2bLinkVerifyAdapt(t, e, linker, linkerA, legacyAt, oldID, stockS2bLinkVerifyCallGas)
	if adaptRetry.id != direct.id || adaptRetry.metadata != direct.metadata || adaptRetry.metadataHash != direct.metadataHash || adaptRetry.methods != direct.methods || adaptRetry.literals != direct.literals || adaptRetry.calls != direct.calls || len(adaptRetry.tx.logs) != 0 || e.state.StateDB.GetNonce(linkerA) != nonce {
		t.Fatalf("direct->adapter=%+v/%+v", direct, adaptRetry)
	}
	linkerB, _ := stockS2bLinkVerifyDeployLinker(t, e, linker, analyzerAt, analyzerHash, legacyHash)
	adapt := stockS2bLinkVerifyAdapt(t, e, linker, linkerB, legacyAt, oldID, stockS2bLinkVerifyCallGas)
	if adapt.methods != 5 || adapt.calls != 2 || len(adapt.tx.logs) != 1 || adapt.id != direct.id || adapt.metadataHash != direct.metadataHash {
		t.Fatalf("adapter-first=%+v", adapt)
	}
	meta := stockS2bLinkVerifyValidateMetadata(t, class.bytes, rawAt, pageHash, payloadHash, analyzerHash, e.state.StateDB.GetCode(adapt.metadata))
	for i := 1; i < len(meta.methods); i++ {
		stockS2bLinkVerifyMethodRecord(t, meta.methods[i], 0, 0, 0)
	}
	if len(meta.calls) != 2 || meta.calls[0].target != 2 || meta.calls[1].target != 1 || meta.calls[1].returnKind != 0 {
		t.Fatalf("adapter call records=%+v", meta.calls)
	}
	nonce = e.state.StateDB.GetNonce(linkerB)
	directRetry := stockS2bLinkVerifyRegister(t, e, linker, linkerB, rawAt, pageHash, payloadHash, stockS2bLinkVerifyCallGas)
	if directRetry.id != adapt.id || len(directRetry.tx.logs) != 0 || e.state.StateDB.GetNonce(linkerB) != nonce {
		t.Fatal("adapter->direct not idempotent")
	}
	if oldID == adapt.id {
		t.Fatal("S2a/S2b classId namespaces collided")
	}
	wrongParser := e.apply(&linkerA, stockS2bLinkVerifyCallData(t, linker, "registerFromS2a", analyzerAt, oldID), stockS2bLinkVerifyCallGas)
	stockS2bLinkVerifyAssertRevert(t, wrongParser, "S2bLinkError(uint256)", 3)
	unknown := e.apply(&linkerA, stockS2bLinkVerifyCallData(t, linker, "registerFromS2a", legacyAt, common.Hash{}), stockS2bLinkVerifyCallGas)
	stockS2bLinkVerifyAssertRevert(t, unknown, "S2bLinkError(uint256)", 4)
	namespace := e.apply(&linkerA, stockS2bLinkVerifyCallData(t, linker, "registerFromS2a", legacyAt, adapt.id), stockS2bLinkVerifyCallGas)
	stockS2bLinkVerifyAssertRevert(t, namespace, "S2bLinkError(uint256)", 4)
	// A normally deployed TEST registry can prove canonical old provenance without
	// pretending that an arbitrary code hash is the accepted S2a parser.
	legacyResponse := stockS2bLinkVerifyLegacyReply(t, oldMeta, oldMetaHash)
	mockRuntime := stockS2bLinkVerifyMockReturnRuntime(legacyResponse, false)
	mockAt, _ := stockS2bLinkVerifyDeployRaw(t, e, mockRuntime)
	mockHash := crypto.Keccak256Hash(mockRuntime)
	mockLinker, _ := stockS2bLinkVerifyDeployLinker(t, e, linker, analyzerAt, analyzerHash, mockHash)
	mockID := stockS2bLinkVerifyS2aClassID(t, mockHash, rawAt, pageHash, payloadHash, oldMetaHash)
	mockAdapt := stockS2bLinkVerifyAdapt(t, e, linker, mockLinker, mockAt, mockID, stockS2bLinkVerifyCallGas)
	if mockAdapt.metadataHash != direct.metadataHash || mockAdapt.calls != 2 {
		t.Fatal("canonical mock legacy provenance/reparse")
	}
	for _, tc := range []struct {
		name  string
		reply []byte
	}{{"short", legacyResponse[:63]}, {"trailing", append(append([]byte(nil), legacyResponse...), 0)}, {"address-high", func() []byte { b := append([]byte(nil), legacyResponse...); b[0] = 1; return b }()}, {"wrong-page-hash", func() []byte { b := append([]byte(nil), legacyResponse...); b[63] ^= 1; return b }()}, {"zero-page", make([]byte, 64)}} {
		t.Run("legacy-reply/"+tc.name, func(t *testing.T) {
			runtime := stockS2bLinkVerifyMockReturnRuntime(tc.reply, false)
			at, _ := stockS2bLinkVerifyDeployRaw(t, e, runtime)
			h := crypto.Keccak256Hash(runtime)
			l, _ := stockS2bLinkVerifyDeployLinker(t, e, linker, analyzerAt, analyzerHash, h)
			tx := e.apply(&l, stockS2bLinkVerifyCallData(t, linker, "registerFromS2a", at, mockID), stockS2bLinkVerifyCallGas)
			stockS2bLinkVerifyAssertRevert(t, tx, "S2bLinkError(uint256)", 4)
		})
	}
	badPayload := append([]byte(nil), e.state.StateDB.GetCode(oldMeta)[1:]...)
	badPayload[0] ^= 1
	badOldAt, _ := e.mustCreate(stockS2bLinkVerifyConstructor(t, stockS2bLinkVerifyArtifact{name: "ArtifactPage", abi: page.abi, init: page.init}, badPayload), stockS2bLinkVerifyCreateGas)
	badOldHash := crypto.Keccak256Hash(e.state.StateDB.GetCode(badOldAt))
	reply := stockS2bLinkVerifyLegacyReply(t, badOldAt, badOldHash)
	runtime := stockS2bLinkVerifyMockReturnRuntime(reply, false)
	badRegistry, _ := stockS2bLinkVerifyDeployRaw(t, e, runtime)
	badRegistryHash := crypto.Keccak256Hash(runtime)
	badLinker, _ := stockS2bLinkVerifyDeployLinker(t, e, linker, analyzerAt, analyzerHash, badRegistryHash)
	badID := stockS2bLinkVerifyS2aClassID(t, badRegistryHash, rawAt, pageHash, payloadHash, badOldHash)
	badHeader := e.apply(&badLinker, stockS2bLinkVerifyCallData(t, linker, "registerFromS2a", badRegistry, badID), stockS2bLinkVerifyCallGas)
	stockS2bLinkVerifyAssertRevert(t, badHeader, "S2bLinkError(uint256)", 5)
}

func TestStockS2bLinkVerifyRawPageAndGlobalCPPrecedence(t *testing.T) {
	s := stockS2bLinkVerifySetupRuntime(t)
	defer s.close()
	base := stockS2bLinkVerifySimple([]byte{3, 0xac}, 1, 0, "()I")
	rawAt, pageHash, payloadHash, _ := stockS2bLinkVerifyDeployPage(t, s.e, s.page, base.bytes)
	bad := pageHash
	bad[0] ^= 1
	stockS2bLinkVerifyAssertRevert(t, s.e.apply(&s.linkerAt, stockS2bLinkVerifyCallData(t, s.linker, "registerClass", rawAt, bad, payloadHash), stockS2bLinkVerifyCallGas), "StockPageError(uint256)", 3)
	bad = payloadHash
	bad[0] ^= 1
	stockS2bLinkVerifyAssertRevert(t, s.e.apply(&s.linkerAt, stockS2bLinkVerifyCallData(t, s.linker, "registerClass", rawAt, pageHash, bad), stockS2bLinkVerifyCallGas), "StockPageError(uint256)", 4)
	wrongPrefix, _ := stockS2bLinkVerifyDeployRaw(t, s.e, append([]byte{1}, base.bytes...))
	stockS2bLinkVerifyAssertRevert(t, s.e.apply(&s.linkerAt, stockS2bLinkVerifyCallData(t, s.linker, "registerClass", wrongPrefix, crypto.Keccak256Hash(s.e.state.StateDB.GetCode(wrongPrefix)), crypto.Keccak256Hash(base.bytes)), stockS2bLinkVerifyCallGas), "StockPageError(uint256)", 2)
	stockS2bLinkVerifyAssertRevert(t, s.e.apply(&s.linkerAt, stockS2bLinkVerifyCallData(t, s.linker, "registerClass", common.Address{}, common.Hash{}, common.Hash{}), stockS2bLinkVerifyCallGas), "StockPageError(uint256)", 1)
	call := stockS2bLinkVerifyCallClass("GlobalCP", stockS2bLinkVerifyMethod{name: "target", descriptor: "()I", access: 9, code: []byte{3, 0xac}, maxStack: 1}, []byte{0xb8, 0, 0, 0xac}, "()I", stockS2bLinkVerifyCallSymbol{})
	mr := call.callCP[0]
	malformed := []struct {
		name string
		c    stockS2bLinkVerifyClass
		off  int
	}{{"methodref-class-index", stockS2bLinkVerifyPatchU2(call, fmt.Sprintf("cp%d.body", mr), 0), call.marks[fmt.Sprintf("cp%d.tag", mr)]}, {"methodref-NT-index", func() stockS2bLinkVerifyClass {
		c := stockS2bLinkVerifyClass{bytes: append([]byte(nil), call.bytes...), marks: call.marks, callCP: call.callCP}
		binary.BigEndian.PutUint16(c.bytes[c.marks[fmt.Sprintf("cp%d.body", mr)]+2:], uint16(len(stockS2bLinkVerifyParseTrusted(call.bytes).cp)+1))
		return c
	}(), call.marks[fmt.Sprintf("cp%d.tag", mr)]}}
	for _, tc := range malformed {
		t.Run(tc.name, func(t *testing.T) {
			at, ph, pvh, _ := stockS2bLinkVerifyDeployPage(t, s.e, s.page, tc.c.bytes)
			tx := s.e.apply(&s.linkerAt, stockS2bLinkVerifyCallData(t, s.linker, "registerClass", at, ph, pvh), stockS2bLinkVerifyCallGas)
			stockS2bLinkVerifyAssertRevert(t, tx, "S2bClassError(uint256,uint256)", 3, uint64(tc.off))
		})
	}
}

type stockS2bLinkVerifyReplay struct {
	hashes                []common.Hash
	gas                   []uint64
	outputs, logs         [][]byte
	addresses             []common.Address
	codeHashes            []common.Hash
	recordAddress         common.Address
	recordHash, stateRoot common.Hash
}

func stockS2bLinkVerifyReplayOnce(t *testing.T) stockS2bLinkVerifyReplay {
	t.Helper()
	page := stockS2bLinkVerifyPage(t)
	analyzer := stockS2bLinkVerifyLoadArtifact(t, "S2bAnalyzeModule")
	linker := stockS2bLinkVerifyLoadArtifact(t, "S2bClassLinker")
	legacy := stockS2bLinkVerifyS2aParser(t)
	e := stockS2bLinkVerifyNewEnv(t)
	defer e.close()
	var out stockS2bLinkVerifyReplay
	capture := func(tx stockS2bLinkVerifyTx) {
		out.hashes = append(out.hashes, tx.tx.Hash())
		out.gas = append(out.gas, tx.result.UsedGas)
		out.outputs = append(out.outputs, append([]byte(nil), tx.result.ReturnData...))
		var log []byte
		for _, l := range tx.logs {
			log = append(log, l.Address[:]...)
			for _, topic := range l.Topics {
				log = append(log, topic[:]...)
			}
			log = append(log, l.Data...)
		}
		out.logs = append(out.logs, log)
	}
	anAt, tx := e.mustCreate(analyzer.init, stockS2bLinkVerifyCreateGas)
	capture(tx)
	anHash := crypto.Keccak256Hash(e.state.StateDB.GetCode(anAt))
	linkAt, tx := stockS2bLinkVerifyDeployLinker(t, e, linker, anAt, anHash, crypto.Keccak256Hash(legacy.runtime))
	capture(tx)
	class := stockS2bLinkVerifyBuildClass("Replay", []stockS2bLinkVerifyMethod{{name: "target", descriptor: "(I)I", access: 0x0a, code: []byte{0x1a, 0xac}, maxStack: 1, maxLocals: 1}, {name: "caller", descriptor: "(I)I", access: 9, code: []byte{0x1a, 0xb8, 0, 0, 0xac}, maxStack: 1, maxLocals: 1, calls: []stockS2bLinkVerifyCallPatch{{1, 0}}}}, []stockS2bLinkVerifyCallSymbol{{owner: "Replay", name: "target", descriptor: "(I)I"}}, 0)
	rawAt, ph, pvh, tx := stockS2bLinkVerifyDeployPage(t, e, page, class.bytes)
	capture(tx)
	reg := stockS2bLinkVerifyRegister(t, e, linker, linkAt, rawAt, ph, pvh, stockS2bLinkVerifyCallGas)
	capture(reg.tx)
	retry := stockS2bLinkVerifyRegister(t, e, linker, linkAt, rawAt, ph, pvh, stockS2bLinkVerifyCallGas)
	capture(retry.tx)
	out.addresses = []common.Address{anAt, linkAt, rawAt, reg.metadata}
	for _, at := range out.addresses {
		out.codeHashes = append(out.codeHashes, crypto.Keccak256Hash(e.state.StateDB.GetCode(at)))
	}
	out.recordAddress, out.recordHash = stockS2bLinkVerifyRecord(t, e, linker, linkAt, reg.id)
	out.stateRoot = e.state.StateDB.IntermediateRoot(true)
	return out
}
func TestStockS2bLinkVerifyDeterministicSignedApplyMessageReplay(t *testing.T) {
	a, b := stockS2bLinkVerifyReplayOnce(t), stockS2bLinkVerifyReplayOnce(t)
	if !reflect.DeepEqual(a, b) {
		t.Fatalf("replay differs\nA=%+v\nB=%+v", a, b)
	}
	if len(a.hashes) != 5 || len(a.addresses) != 4 || len(a.logs[3]) == 0 || len(a.logs[4]) != 0 {
		t.Fatalf("replay shape tx=%d addresses=%d logs=%v", len(a.hashes), len(a.addresses), a.logs)
	}
	var total uint64
	for _, g := range a.gas {
		total += g
	}
	t.Logf("signed S2b-L replay hashes=%v gas=%v total=%d addresses=%v codeHashes=%v record=%s/%s root=%s", a.hashes, a.gas, total, a.addresses, a.codeHashes, a.recordAddress, a.recordHash, a.stateRoot)
}
func TestStockS2bLinkVerifyOriginalProtocolLimitLayers(t *testing.T) {
	e := stockS2bLinkVerifyNewEnv(t)
	defer e.close()
	nonce := e.state.StateDB.GetNonce(e.sender)
	balance := e.state.StateDB.GetBalance(e.sender).ToBig()
	r := e.apply(nil, stockS2bLinkVerifyRawInit(make([]byte, 24577)), stockS2bLinkVerifyCreateGas)
	if r.coreErr != nil || r.result == nil || !errors.Is(r.result.Err, vm.ErrMaxCodeSizeExceeded) {
		t.Fatalf("EIP170 core=%v evm=%v", r.coreErr, stockS2bLinkVerifyResultErr(r.result))
	}
	if e.state.StateDB.GetNonce(e.sender) != nonce+1 || e.state.StateDB.GetBalance(e.sender).ToBig().Cmp(balance) >= 0 || len(e.state.StateDB.GetCode(crypto.CreateAddress(e.sender, nonce))) != 0 {
		t.Fatal("EIP170 state")
	}
	nonce = e.state.StateDB.GetNonce(e.sender)
	balance = e.state.StateDB.GetBalance(e.sender).ToBig()
	snap := e.state.StateDB.Snapshot()
	r = e.apply(nil, make([]byte, 49153), stockS2bLinkVerifyCreateGas)
	if !errors.Is(r.coreErr, core.ErrMaxInitCodeSizeExceeded) || r.result != nil {
		t.Fatalf("EIP3860 core=%v result=%v", r.coreErr, r.result)
	}
	debit := new(big.Int).Sub(balance, e.state.StateDB.GetBalance(e.sender).ToBig())
	want := new(big.Int).Mul(new(big.Int).SetUint64(stockS2bLinkVerifyCreateGas), big.NewInt(2))
	if e.state.StateDB.GetNonce(e.sender) != nonce || debit.Cmp(want) != 0 {
		t.Fatal("EIP3860 transition")
	}
	e.state.StateDB.RevertToSnapshot(snap)
	to := common.HexToAddress("0x7825")
	r = e.apply(&to, nil, params.MaxTxGas+1)
	if !errors.Is(r.coreErr, core.ErrGasLimitTooHigh) || r.result != nil {
		t.Fatalf("EIP7825 core=%v result=%v", r.coreErr, r.result)
	}
}
