// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.
//
// This is the independent Stock S2a verifier. It intentionally does not use the
// S2a harness: artifacts are decoded again, all transactions are signed, and the
// only class analysis below is an assertion oracle for small trusted inputs.
package s2a

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
	"github.com/ethereum/go-ethereum/params"
	gethtests "github.com/ethereum/go-ethereum/tests"
)

const (
	stockS2aVerifyCreateGas = uint64(8_000_000)
	stockS2aVerifyCallGas   = uint64(2_000_000)
	stockS2aVerifyBlockGas  = uint64(30_000_000)
	stockS2aVerifyReserve   = uint64(800_000)
)

const (
	stockS2aVerifyRunnable  = uint8(0)
	stockS2aVerifyReturned  = uint8(1)
	stockS2aVerifyStepLimit = uint8(2)
	stockS2aVerifyJavaFault = uint8(3)

	stockS2aVerifyArithmeticFault = uint8(1)
)

var (
	stockS2aVerifyOne        = big.NewInt(1)
	stockS2aVerifyMaxUint256 = new(big.Int).Sub(new(big.Int).Lsh(big.NewInt(1), 256), big.NewInt(1))
)

type stockS2aVerifyCompiler struct {
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

type stockS2aVerifyImmutable struct {
	Start, Length int
}

func (r *stockS2aVerifyImmutable) UnmarshalJSON(blob []byte) error {
	var v struct{ Start, Length int }
	if err := json.Unmarshal(blob, &v); err != nil {
		return err
	}
	r.Start, r.Length = v.Start, v.Length
	return nil
}

type stockS2aVerifyArtifactJSON struct {
	ContractName        string                               `json:"contractName"`
	ABI                 json.RawMessage                      `json:"abi"`
	Bytecode            string                               `json:"bytecode"`
	DeployedBytecode    string                               `json:"deployedBytecode"`
	ImmutableReferences map[string][]stockS2aVerifyImmutable `json:"immutableReferences"`
	Compiler            stockS2aVerifyCompiler               `json:"compiler"`
	SourceHashes        map[string]string                    `json:"sourceHashes"`
}

type stockS2aVerifyArtifact struct {
	name       string
	abi        abi.ABI
	init       []byte
	runtime    []byte
	immutables map[string][]stockS2aVerifyImmutable
}

func stockS2aVerifyLoadArtifact(t *testing.T, name string) stockS2aVerifyArtifact {
	t.Helper()
	path := "runtime/artifacts/" + name + ".json"
	blob, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read frozen %s artifact (S2a runtime integration dependency is absent): %v", name, err)
	}
	var raw stockS2aVerifyArtifactJSON
	if err := json.Unmarshal(blob, &raw); err != nil {
		t.Fatalf("decode %s: %v", path, err)
	}
	if raw.ContractName != name || len(raw.ABI) == 0 || raw.Bytecode == "" || raw.DeployedBytecode == "" {
		t.Fatalf("incomplete artifact %s", path)
	}
	contractABI, err := abi.JSON(bytes.NewReader(raw.ABI))
	if err != nil {
		t.Fatalf("parse %s ABI: %v", name, err)
	}
	decode := func(field, value string) []byte {
		value = strings.TrimPrefix(value, "0x")
		out, err := hex.DecodeString(value)
		if err != nil || len(out) == 0 {
			t.Fatalf("decode %s.%s: bytes=%d err=%v", name, field, len(out), err)
		}
		return out
	}
	if !strings.HasPrefix(raw.Compiler.Version, "0.8.30+commit.73712a01") || !raw.Compiler.ViaIR ||
		!raw.Compiler.Optimizer.Enabled || raw.Compiler.Optimizer.Runs != 200 || raw.Compiler.EVMVersion != "cancun" ||
		raw.Compiler.Metadata.AppendCBOR || raw.Compiler.Metadata.BytecodeHash != "none" {
		t.Fatalf("%s compiler configuration is not frozen: %+v", name, raw.Compiler)
	}
	if len(raw.SourceHashes) == 0 {
		t.Fatalf("%s has no source hashes", name)
	}
	for source, hash := range raw.SourceHashes {
		if source == "" || len(hash) != 64 {
			t.Fatalf("%s bad source hash %q=%q", name, source, hash)
		}
		if _, err := hex.DecodeString(hash); err != nil {
			t.Fatalf("%s bad source hash: %v", name, err)
		}
	}
	return stockS2aVerifyArtifact{name, contractABI, decode("bytecode", raw.Bytecode), decode("deployedBytecode", raw.DeployedBytecode), raw.ImmutableReferences}
}

func stockS2aVerifyLoadPage(t *testing.T) stockS2aVerifyArtifact {
	t.Helper()
	a, err := stock.LoadArtifact(stock.ArtifactPage)
	if err != nil {
		t.Fatalf("load accepted S0 ArtifactPage: %v", err)
	}
	return stockS2aVerifyArtifact{stock.ArtifactPage, a.ABI, a.InitCode, a.RuntimeCode, nil}
}

type stockS2aVerifyMachine struct {
	Pc            uint32
	Sp            uint8
	Initialized   uint8
	Lifecycle     uint8
	Stack         [8]*big.Int
	Locals        [8]*big.Int
	Result        int32
	JavaFaultKind uint8
	FaultPC       uint32
}

type stockS2aVerifyProgram struct {
	Parser         common.Address
	ParserCodeHash [32]byte
	ClassId        [32]byte
	RawPage        common.Address
	RawPageHash    [32]byte
	PayloadHash    [32]byte
	MetadataPage   common.Address
	MetadataHash   [32]byte
	MethodIndex    uint16
	ProgramId      [32]byte
}

type stockS2aVerifyCheckpoint struct {
	Schema     uint32
	ClassID    common.Hash
	ProgramID  common.Hash
	InputRoot  common.Hash
	Epoch      uint64
	TotalSteps uint64
	Digest     common.Hash
	Machine    stockS2aVerifyMachine
}

func stockS2aVerifyZeroMachine() stockS2aVerifyMachine {
	m := stockS2aVerifyMachine{}
	for i := range m.Stack {
		m.Stack[i] = new(big.Int)
	}
	for i := range m.Locals {
		m.Locals[i] = new(big.Int)
	}
	return m
}

func stockS2aVerifyCloneMachine(m stockS2aVerifyMachine) stockS2aVerifyMachine {
	out := m
	for i := range out.Stack {
		out.Stack[i] = new(big.Int).Set(m.Stack[i])
	}
	for i := range out.Locals {
		out.Locals[i] = new(big.Int).Set(m.Locals[i])
	}
	return out
}

func stockS2aVerifyTagged(v uint32) *big.Int {
	return new(big.Int).Or(new(big.Int).Lsh(big.NewInt(1), 64), new(big.Int).SetUint64(uint64(v)))
}

func stockS2aVerifyMachineFrom(v any) stockS2aVerifyMachine {
	return *abi.ConvertType(v, new(stockS2aVerifyMachine)).(*stockS2aVerifyMachine)
}
func stockS2aVerifyProgramFrom(v any) stockS2aVerifyProgram {
	return *abi.ConvertType(v, new(stockS2aVerifyProgram)).(*stockS2aVerifyProgram)
}

func stockS2aVerifyMachineEqual(a, b stockS2aVerifyMachine) bool {
	if a.Pc != b.Pc || a.Sp != b.Sp || a.Initialized != b.Initialized || a.Lifecycle != b.Lifecycle || a.Result != b.Result || a.JavaFaultKind != b.JavaFaultKind || a.FaultPC != b.FaultPC {
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

func stockS2aVerifyDirty(a, b stockS2aVerifyMachine) uint8 {
	n := 3
	if a.Pc != b.Pc {
		n++
	}
	if a.Sp != b.Sp {
		n++
	}
	if a.Initialized != b.Initialized {
		n++
	}
	if a.Lifecycle != b.Lifecycle {
		n++
	}
	if a.Result != b.Result {
		n++
	}
	if a.JavaFaultKind != b.JavaFaultKind {
		n++
	}
	if a.FaultPC != b.FaultPC {
		n++
	}
	for i := range a.Stack {
		if a.Stack[i].Cmp(b.Stack[i]) != 0 {
			n++
		}
	}
	for i := range a.Locals {
		if a.Locals[i].Cmp(b.Locals[i]) != 0 {
			n++
		}
	}
	if n > 26 {
		panic("S2a dirty accounting exceeded frozen maximum")
	}
	return uint8(n)
}

type stockS2aVerifyEnv struct {
	t       *testing.T
	state   gethtests.StateTestState
	key     *ecdsa.PrivateKey
	sender  common.Address
	signer  types.Signer
	block   vm.BlockContext
	gasUsed uint64
}

type stockS2aVerifyTx struct {
	tx      *types.Transaction
	result  *core.ExecutionResult
	coreErr error
	address common.Address
	logs    []*types.Log
	receipt *types.Receipt
}

func stockS2aVerifyNewEnv(t *testing.T) *stockS2aVerifyEnv {
	t.Helper()
	key, err := crypto.HexToECDSA("51a151a151a151a151a151a151a151a151a151a151a151a151a151a151a151a1")
	if err != nil {
		t.Fatal(err)
	}
	sender := crypto.PubkeyToAddress(key.PublicKey)
	pre := gethtests.MakePreState(rawdb.NewMemoryDatabase(), types.GenesisAlloc{
		sender: {Balance: new(big.Int).Exp(big.NewInt(10), big.NewInt(30), nil)},
	}, false, rawdb.HashScheme)
	random := crypto.Keccak256Hash([]byte("JVMEVM:STOCK:S2A:VERIFY"))
	block := vm.BlockContext{
		CanTransfer: core.CanTransfer, Transfer: core.Transfer,
		GetHash:     func(n uint64) common.Hash { return crypto.Keccak256Hash(new(big.Int).SetUint64(n).Bytes()) },
		Coinbase:    common.HexToAddress("0x0000000000000000000000000000000000001337"),
		BlockNumber: big.NewInt(1), Time: 1, Difficulty: new(big.Int), BaseFee: new(big.Int).Set(stockS2aVerifyOne),
		GasLimit: stockS2aVerifyBlockGas, Random: &random,
	}
	return &stockS2aVerifyEnv{t: t, state: pre, key: key, sender: sender,
		signer: types.MakeSigner(params.AllDevChainProtocolChanges, block.BlockNumber, block.Time), block: block}
}
func (e *stockS2aVerifyEnv) close() { e.state.Close() }

func (e *stockS2aVerifyEnv) apply(to *common.Address, input []byte, gas uint64) stockS2aVerifyTx {
	e.t.Helper()
	nonce := e.state.StateDB.GetNonce(e.sender)
	tx := types.NewTx(&types.LegacyTx{Nonce: nonce, To: to, Gas: gas, GasPrice: big.NewInt(2), Data: append([]byte(nil), input...)})
	signed, err := types.SignTx(tx, e.signer, e.key)
	if err != nil {
		e.t.Fatal(err)
	}
	recovered, err := types.Sender(e.signer, signed)
	if err != nil || recovered != e.sender {
		e.t.Fatalf("signed sender=%s err=%v want=%s", recovered, err, e.sender)
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
	result, coreErr := core.ApplyMessage(evm, msg, new(core.GasPool).AddGas(stockS2aVerifyBlockGas))
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
			e.t.Fatalf("receipt/core result mismatch tx=%s", signed.Hash())
		}
	}
	return stockS2aVerifyTx{signed, result, coreErr, address, logs, receipt}
}

func stockS2aVerifyResultErr(r *core.ExecutionResult) error {
	if r == nil {
		return nil
	}
	return r.Err
}
func stockS2aVerifyResultData(r *core.ExecutionResult) []byte {
	if r == nil {
		return nil
	}
	return r.ReturnData
}

func (e *stockS2aVerifyEnv) mustCreate(init []byte, gas uint64) (common.Address, stockS2aVerifyTx) {
	e.t.Helper()
	r := e.apply(nil, init, gas)
	if r.coreErr != nil || r.result == nil || r.result.Err != nil {
		e.t.Fatalf("CREATE: core=%v evm=%v data=%x", r.coreErr, stockS2aVerifyResultErr(r.result), stockS2aVerifyResultData(r.result))
	}
	if len(e.state.StateDB.GetCode(r.address)) == 0 || r.receipt == nil || r.receipt.Status != types.ReceiptStatusSuccessful {
		e.t.Fatalf("CREATE %s has no successful receipt/code", r.address)
	}
	return r.address, r
}
func (e *stockS2aVerifyEnv) mustCall(to common.Address, input []byte, gas uint64) stockS2aVerifyTx {
	e.t.Helper()
	r := e.apply(&to, input, gas)
	if r.coreErr != nil || r.result == nil || r.result.Err != nil || r.receipt == nil || r.receipt.Status != types.ReceiptStatusSuccessful {
		e.t.Fatalf("CALL %s: core=%v evm=%v data=%x", to, r.coreErr, stockS2aVerifyResultErr(r.result), stockS2aVerifyResultData(r.result))
	}
	return r
}

func stockS2aVerifyConstructor(t *testing.T, a stockS2aVerifyArtifact, args ...any) []byte {
	t.Helper()
	tail, err := a.abi.Pack("", args...)
	if err != nil {
		t.Fatalf("pack %s constructor: %v", a.name, err)
	}
	return append(append([]byte(nil), a.init...), tail...)
}
func stockS2aVerifyCallData(t *testing.T, a stockS2aVerifyArtifact, method string, args ...any) []byte {
	t.Helper()
	out, err := a.abi.Pack(method, args...)
	if err != nil {
		t.Fatalf("pack %s.%s: %v", a.name, method, err)
	}
	return out
}
func stockS2aVerifyUnpack(t *testing.T, a stockS2aVerifyArtifact, method string, data []byte) []any {
	t.Helper()
	out, err := a.abi.Unpack(method, data)
	if err != nil {
		t.Fatalf("unpack %s.%s %x: %v", a.name, method, data, err)
	}
	return out
}

func stockS2aVerifyCustomError(signature string, values ...any) []byte {
	out := append([]byte(nil), crypto.Keccak256([]byte(signature))[:4]...)
	for _, value := range values {
		var word [32]byte
		switch value := value.(type) {
		case uint64:
			binary.BigEndian.PutUint64(word[24:], value)
		case int:
			binary.BigEndian.PutUint64(word[24:], uint64(value))
		case *big.Int:
			value.FillBytes(word[:])
		default:
			panic(fmt.Sprintf("unsupported custom-error word %T", value))
		}
		out = append(out, word[:]...)
	}
	return out
}
func stockS2aVerifyAssertRevert(t *testing.T, r stockS2aVerifyTx, signature string, words ...any) {
	t.Helper()
	if r.coreErr != nil || r.result == nil || !errors.Is(r.result.Err, vm.ErrExecutionReverted) {
		t.Fatalf("want %s%v: core=%v evm=%v data=%x", signature, words, r.coreErr, stockS2aVerifyResultErr(r.result), stockS2aVerifyResultData(r.result))
	}
	want := stockS2aVerifyCustomError(signature, words...)
	if !bytes.Equal(r.result.ReturnData, want) {
		t.Fatalf("wrong revert\nhave %x\nwant %x", r.result.ReturnData, want)
	}
	if len(r.logs) != 0 || r.receipt == nil || r.receipt.Status != types.ReceiptStatusFailed {
		t.Fatalf("failed transaction logs/receipt: logs=%d receipt=%+v", len(r.logs), r.receipt)
	}
}

func stockS2aVerifyRawInit(runtime []byte) []byte {
	if len(runtime) > math.MaxUint16 {
		panic("raw runtime too large")
	}
	out := []byte{0x61, byte(len(runtime) >> 8), byte(len(runtime)), 0x61, 0, 15, 0x60, 0, 0x39, 0x61, byte(len(runtime) >> 8), byte(len(runtime)), 0x60, 0, 0xf3}
	return append(out, runtime...)
}
func stockS2aVerifyDeployRaw(t *testing.T, e *stockS2aVerifyEnv, runtime []byte, gas uint64) (common.Address, stockS2aVerifyTx) {
	t.Helper()
	at, tx := e.mustCreate(stockS2aVerifyRawInit(runtime), gas)
	if !bytes.Equal(e.state.StateDB.GetCode(at), runtime) {
		t.Fatal("ordinary raw CREATE bytes differ")
	}
	return at, tx
}
func stockS2aVerifyDeployPage(t *testing.T, e *stockS2aVerifyEnv, page stockS2aVerifyArtifact, payload []byte) (common.Address, common.Hash, common.Hash, stockS2aVerifyTx) {
	t.Helper()
	at, tx := e.mustCreate(stockS2aVerifyConstructor(t, page, payload), stockS2aVerifyCreateGas)
	code := append([]byte{0}, payload...)
	pageHash, payloadHash := crypto.Keccak256Hash(code), crypto.Keccak256Hash(payload)
	if !bytes.Equal(e.state.StateDB.GetCode(at), code) {
		t.Fatal("ArtifactPage is not exact STOP||raw payload")
	}
	return at, pageHash, payloadHash, tx
}

func stockS2aVerifyRequireMethod(t *testing.T, a stockS2aVerifyArtifact, name, signature, mutability string, in, out int) {
	t.Helper()
	m, ok := a.abi.Methods[name]
	if !ok || m.Sig != signature || m.StateMutability != mutability || len(m.Inputs) != in || len(m.Outputs) != out {
		t.Fatalf("%s.%s ABI mismatch: present=%v sig=%q mut=%q in=%d out=%d", a.name, name, ok, m.Sig, m.StateMutability, len(m.Inputs), len(m.Outputs))
	}
}
func stockS2aVerifyRequireError(t *testing.T, a stockS2aVerifyArtifact, name, signature string) {
	t.Helper()
	e, ok := a.abi.Errors[name]
	if !ok || e.Sig != signature {
		t.Fatalf("%s error %s: present=%v sig=%q", a.name, name, ok, e.Sig)
	}
}
func stockS2aVerifyTuple(t *testing.T, typ abi.Type, names, typesWant []string) {
	t.Helper()
	if typ.T != abi.TupleTy || !reflect.DeepEqual(typ.TupleRawNames, names) || len(typ.TupleElems) != len(typesWant) {
		t.Fatalf("tuple fields=%v want=%v", typ.TupleRawNames, names)
	}
	for i := range typesWant {
		if typ.TupleElems[i].String() != typesWant[i] {
			t.Fatalf("tuple %s=%s want=%s", names[i], typ.TupleElems[i], typesWant[i])
		}
	}
}

// stockS2aVerifyClass is a bounded trusted classfile generator. Its output is
// passed unchanged to ArtifactPage. No offsets, starts, literals, or results are
// supplied to any production contract.
type stockS2aVerifyMethod struct {
	name, descriptor    string
	access              uint16
	code                []byte
	maxStack, maxLocals uint16
	codeCopies          int
	handlers            uint16
}
type stockS2aVerifyClass struct {
	bytes []byte
	marks map[string]int
}
type stockS2aVerifyCP struct {
	tag   byte
	body  []byte
	slots uint16
}

func stockS2aVerifyU2(v uint16) []byte { return []byte{byte(v >> 8), byte(v)} }
func stockS2aVerifyU4(v uint32) []byte {
	return []byte{byte(v >> 24), byte(v >> 16), byte(v >> 8), byte(v)}
}
func stockS2aVerifyUtf8(s string) stockS2aVerifyCP {
	return stockS2aVerifyCP{1, append(stockS2aVerifyU2(uint16(len(s))), []byte(s)...), 1}
}
func stockS2aVerifyBuildClass(className string, methods []stockS2aVerifyMethod, cpPad int) stockS2aVerifyClass {
	if className == "" {
		className = "S2aTrusted"
	}
	all := append([]stockS2aVerifyMethod{{"<init>", "()V", 0x0001, []byte{0x2a, 0xb7, 0, 9, 0xb1}, 1, 1, 1, 0}}, methods...)
	cp := []stockS2aVerifyCP{
		stockS2aVerifyUtf8(className), {7, stockS2aVerifyU2(1), 1},
		stockS2aVerifyUtf8("java/lang/Object"), {7, stockS2aVerifyU2(3), 1},
		stockS2aVerifyUtf8("<init>"), stockS2aVerifyUtf8("()V"), stockS2aVerifyUtf8("Code"),
		{12, append(stockS2aVerifyU2(5), stockS2aVerifyU2(6)...), 1},
		{10, append(stockS2aVerifyU2(4), stockS2aVerifyU2(8)...), 1},
		{3, []byte{0x12, 0x34, 0x56, 0x78}, 1},
	}
	utf := map[string]uint16{className: 1, "<init>": 5, "()V": 6, "Code": 7}
	next := uint16(11)
	for _, m := range methods {
		for _, s := range []string{m.name, m.descriptor} {
			if _, ok := utf[s]; !ok {
				utf[s] = next
				cp = append(cp, stockS2aVerifyUtf8(s))
				next++
			}
		}
	}
	for len(cp)+1 < cpPad {
		cp = append(cp, stockS2aVerifyCP{3, []byte{0, 0, 0, byte(len(cp))}, 1})
	}
	if len(cp)+1 > math.MaxUint16 {
		panic("constant pool too large")
	}
	var out []byte
	marks := make(map[string]int)
	put := func(p []byte) { out = append(out, p...) }
	mark := func(s string) { marks[s] = len(out) }
	put([]byte{0xca, 0xfe, 0xba, 0xbe, 0, 0, 0, 52})
	mark("cpCount")
	put(stockS2aVerifyU2(uint16(len(cp) + 1)))
	for _, c := range cp {
		put([]byte{c.tag})
		put(c.body)
	}
	mark("classAccess")
	put(stockS2aVerifyU2(0x0021))
	put(stockS2aVerifyU2(2))
	put(stockS2aVerifyU2(4))
	put(stockS2aVerifyU2(0))
	put(stockS2aVerifyU2(0))
	mark("methodCount")
	put(stockS2aVerifyU2(uint16(len(all))))
	for i, m := range all {
		prefix := fmt.Sprintf("method%d", i)
		if m.codeCopies == 0 {
			m.codeCopies = 1
		}
		mark(prefix + ".access")
		put(stockS2aVerifyU2(m.access))
		put(stockS2aVerifyU2(utf[m.name]))
		put(stockS2aVerifyU2(utf[m.descriptor]))
		mark(prefix + ".attrs")
		put(stockS2aVerifyU2(uint16(m.codeCopies)))
		for copyNo := 0; copyNo < m.codeCopies; copyNo++ {
			p := fmt.Sprintf("%s.code%d", prefix, copyNo)
			put(stockS2aVerifyU2(7))
			put(stockS2aVerifyU4(uint32(12 + len(m.code) + int(m.handlers)*8)))
			mark(p + ".maxStack")
			put(stockS2aVerifyU2(m.maxStack))
			mark(p + ".maxLocals")
			put(stockS2aVerifyU2(m.maxLocals))
			mark(p + ".codeLen")
			put(stockS2aVerifyU4(uint32(len(m.code))))
			mark(p + ".bytes")
			put(m.code)
			mark(p + ".handlers")
			put(stockS2aVerifyU2(m.handlers))
			put(make([]byte, int(m.handlers)*8))
			put(stockS2aVerifyU2(0))
		}
	}
	put(stockS2aVerifyU2(0))
	return stockS2aVerifyClass{out, marks}
}
func stockS2aVerifySimpleClass(code []byte, stack, locals uint16, descriptor string) stockS2aVerifyClass {
	if descriptor == "" {
		descriptor = "()I"
	}
	return stockS2aVerifyBuildClass("S2aTrusted", []stockS2aVerifyMethod{{"entry", descriptor, 0x0009, code, stack, locals, 1, 0}}, 0)
}
func stockS2aVerifyPatchU2(c stockS2aVerifyClass, mark string, v uint16) stockS2aVerifyClass {
	out := stockS2aVerifyClass{append([]byte(nil), c.bytes...), c.marks}
	binary.BigEndian.PutUint16(out.bytes[out.marks[mark]:], v)
	return out
}
func stockS2aVerifyPatchU4(c stockS2aVerifyClass, mark string, v uint32) stockS2aVerifyClass {
	out := stockS2aVerifyClass{append([]byte(nil), c.bytes...), c.marks}
	binary.BigEndian.PutUint32(out.bytes[out.marks[mark]:], v)
	return out
}

// stockS2aVerifyCommand is used only to make the generated aggregate fixture pass
// a real JVM verifier. It never supplies metadata or results to an EVM call.
func stockS2aVerifyCommand(t *testing.T, command string, args ...string) string {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	out, err := exec.CommandContext(ctx, command, args...).CombinedOutput()
	if err != nil {
		t.Fatalf("%s %v: %v\n%s", command, args, err, out)
	}
	return string(out)
}

func stockS2aVerifyAssertAggregateJVM(t *testing.T, raw []byte) {
	t.Helper()
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "S2aAggregate.class"), raw, 0600); err != nil {
		t.Fatal(err)
	}
	source := `public class StockS2aAggregateOracle {
 public static void main(String[] args) throws Exception {
  Class<?> c=Class.forName("S2aAggregate");
  for(int i=0;i<31;i++) {
   int got=((Integer)c.getMethod(String.format("m%02d",i)).invoke(null)).intValue();
   int want=i<4?0x12345678:0;
   if(got!=want)throw new AssertionError(i+":"+got);
  }
  System.out.print("31 methods verified");
 }}`
	javaFile := filepath.Join(dir, "StockS2aAggregateOracle.java")
	if err := os.WriteFile(javaFile, []byte(source), 0600); err != nil {
		t.Fatal(err)
	}
	stockS2aVerifyCommand(t, "javac", "--release", "8", "-d", dir, javaFile)
	if got := strings.TrimSpace(stockS2aVerifyCommand(t, "java", "-Xmx64m", "-Xss512k", "-Xverify:all", "-cp", dir, "StockS2aAggregateOracle")); got != "31 methods verified" {
		t.Fatalf("aggregate JVM oracle: %q", got)
	}
}

// Independent decoder for valid generated inputs. It computes the complete
// schema-3 metadata expectation from raw bytes, rather than from generator marks.
type stockS2aVerifyParsedMethod struct {
	index, access             uint16
	name, descriptor          []byte
	codeOffset                uint32
	code                      []byte
	maxStack, maxLocals, argc uint8
	starts                    *big.Int
	literals                  []stockS2aVerifyLiteral
	errorDomain, errorCode    uint8
	errorLocation             uint32
}
type stockS2aVerifyLiteral struct {
	method, pc uint16
	bits       uint32
}
type stockS2aVerifyParsed struct {
	className       []byte
	access, cpCount uint16
	methods         []stockS2aVerifyParsedMethod
	literals        []stockS2aVerifyLiteral
}
type stockS2aVerifyReader struct {
	b []byte
	p int
}

func (r *stockS2aVerifyReader) take(n int) []byte {
	if n < 0 || r.p+n > len(r.b) {
		panic("trusted class parser boundary")
	}
	v := r.b[r.p : r.p+n]
	r.p += n
	return v
}
func (r *stockS2aVerifyReader) u1() byte   { return r.take(1)[0] }
func (r *stockS2aVerifyReader) u2() uint16 { return binary.BigEndian.Uint16(r.take(2)) }
func (r *stockS2aVerifyReader) u4() uint32 { return binary.BigEndian.Uint32(r.take(4)) }
func stockS2aVerifyArgc(desc string) (uint8, bool) {
	if len(desc) < 3 || desc[0] != '(' || !strings.HasSuffix(desc, ")I") {
		return 0, false
	}
	inside := desc[1 : len(desc)-2]
	if len(inside) > 4 {
		return 0, false
	}
	for _, c := range []byte(inside) {
		if c != 'I' {
			return 0, false
		}
	}
	return uint8(len(inside)), true
}
func stockS2aVerifyOpcodeWidth(op byte) int {
	switch op {
	case 0x10, 0x12, 0x15, 0x36:
		return 2
	case 0x11, 0x13, 0x84, 0x99, 0x9a, 0x9b, 0x9c, 0x9d, 0x9e, 0x9f, 0xa0, 0xa1, 0xa2, 0xa3, 0xa4, 0xa7:
		return 3
	default:
		return 1
	}
}
func stockS2aVerifyParseTrusted(raw []byte) stockS2aVerifyParsed {
	r := &stockS2aVerifyReader{b: raw}
	if !bytes.Equal(r.take(4), []byte{0xca, 0xfe, 0xba, 0xbe}) {
		panic("magic")
	}
	r.take(4)
	cpCount := r.u2()
	utf := make([][]byte, cpCount)
	tags := make([]byte, cpCount)
	refs := make([]uint16, cpCount)
	ints := make([]uint32, cpCount)
	for i := uint16(1); i < cpCount; i++ {
		tag := r.u1()
		tags[i] = tag
		switch tag {
		case 1:
			n := r.u2()
			utf[i] = append([]byte(nil), r.take(int(n))...)
		case 3:
			ints[i] = r.u4()
		case 4:
			r.take(4)
		case 5, 6:
			r.take(8)
			i++
		case 7, 8, 16:
			refs[i] = r.u2()
		case 9, 10, 11, 12, 18:
			r.take(4)
		case 15:
			r.take(3)
		default:
			panic("unsupported trusted CP")
		}
	}
	access := r.u2()
	this := r.u2()
	r.u2()
	className := append([]byte(nil), utf[refs[this]]...)
	interfaces := r.u2()
	r.take(int(interfaces) * 2)
	fields := r.u2()
	if fields != 0 {
		panic("trusted fields")
	}
	methodCount := r.u2()
	parsed := stockS2aVerifyParsed{className: className, access: access, cpCount: cpCount}
	for i := uint16(0); i < methodCount; i++ {
		m := stockS2aVerifyParsedMethod{index: i, access: r.u2()}
		nameIndex, descIndex := r.u2(), r.u2()
		m.name = append([]byte(nil), utf[nameIndex]...)
		m.descriptor = append([]byte(nil), utf[descIndex]...)
		attrs := r.u2()
		for a := uint16(0); a < attrs; a++ {
			attrName := r.u2()
			length := r.u4()
			start := r.p
			if string(utf[attrName]) == "Code" {
				m.maxStack = uint8(r.u2())
				m.maxLocals = uint8(r.u2())
				n := r.u4()
				m.codeOffset = uint32(r.p)
				m.code = append([]byte(nil), r.take(int(n))...)
				handlers := r.u2()
				r.take(int(handlers) * 8)
				nested := r.u2()
				for j := uint16(0); j < nested; j++ {
					r.u2()
					r.take(int(r.u4()))
				}
			} else {
				r.take(int(length))
			}
			if r.p-start != int(length) {
				panic("trusted Code length")
			}
		}
		argc, descriptorOK := stockS2aVerifyArgc(string(m.descriptor))
		accessOK := m.access == 0x0009
		codeOK := len(m.code) > 0 && len(m.code) <= 256 && m.maxStack <= 8 && m.maxLocals <= 8 && m.maxLocals >= argc
		eligible := string(m.name) != "<init>" && accessOK && descriptorOK && codeOK
		if eligible {
			m.argc = argc
			m.starts = new(big.Int)
			for pc := 0; pc < len(m.code); {
				m.starts.SetBit(m.starts, pc, 1)
				op := m.code[pc]
				if op == 0x12 || op == 0x13 {
					var ix uint16
					if op == 0x12 {
						ix = uint16(m.code[pc+1])
					} else {
						ix = binary.BigEndian.Uint16(m.code[pc+1:])
					}
					if ix == 0 || int(ix) >= len(tags) || tags[ix] != 3 {
						panic("trusted literal")
					}
					lit := stockS2aVerifyLiteral{i, uint16(pc), ints[ix]}
					m.literals = append(m.literals, lit)
					parsed.literals = append(parsed.literals, lit)
				}
				pc += stockS2aVerifyOpcodeWidth(op)
			}
		} else {
			m.errorDomain, m.errorLocation = 1, uint32(i)
			switch {
			case string(m.name) == "<init>":
				m.errorCode = 6
			case !accessOK:
				m.errorCode = 3
			case !descriptorOK:
				m.errorCode = 4
			default:
				m.errorCode = 5
			}
		}
		parsed.methods = append(parsed.methods, m)
	}
	classAttrs := r.u2()
	for i := uint16(0); i < classAttrs; i++ {
		r.u2()
		r.take(int(r.u4()))
	}
	if r.p != len(raw) {
		panic("trusted trailing bytes")
	}
	return parsed
}

func stockS2aVerifyMetadataExpected(raw []byte, rawPage common.Address, pageHash, payloadHash common.Hash) []byte {
	p := stockS2aVerifyParseTrusted(raw)
	words := make([][32]byte, 0, 6+4*len(p.methods))
	putHash := func(h common.Hash) { words = append(words, [32]byte(h)) }
	putHash(crypto.Keccak256Hash([]byte("JVMEVM:S2A:METADATA:3")))
	var h1 [32]byte
	copy(h1[12:], rawPage[:])
	new(big.Int).Lsh(new(big.Int).SetUint64(uint64(p.access)), 160).Or(new(big.Int).SetBytes(h1[:]), new(big.Int).Lsh(new(big.Int).SetUint64(uint64(p.access)), 160)).FillBytes(h1[:])
	words = append(words, h1)
	putHash(pageHash)
	putHash(payloadHash)
	putHash(crypto.Keccak256Hash(p.className))
	var h5 [32]byte
	packed := new(big.Int).SetUint64(uint64(len(raw)) | uint64(p.cpCount)<<32 | uint64(len(p.methods))<<48)
	packed.Or(packed, new(big.Int).Lsh(new(big.Int).SetUint64(uint64(len(p.literals))), 64))
	packed.FillBytes(h5[:])
	words = append(words, h5)
	literalBase := 0
	for _, m := range p.methods {
		putHash(crypto.Keccak256Hash(m.name))
		putHash(crypto.Keccak256Hash(m.descriptor))
		var m2 [32]byte
		v := new(big.Int).SetUint64(uint64(m.index) | uint64(m.access)<<16)
		eligible := m.starts != nil
		if eligible {
			fields := []struct {
				v uint64
				s uint
			}{{uint64(m.codeOffset), 32}, {uint64(len(m.code)), 64}, {uint64(m.maxStack), 80}, {uint64(m.maxLocals), 88}, {uint64(m.argc), 96}, {uint64(literalBase), 152}, {uint64(len(m.literals)), 168}}
			for _, f := range fields {
				v.Or(v, new(big.Int).Lsh(new(big.Int).SetUint64(f.v), f.s))
			}
			literalBase += len(m.literals)
		} else {
			v.Or(v, new(big.Int).Lsh(new(big.Int).SetUint64(uint64(m.errorDomain)), 104))
			v.Or(v, new(big.Int).Lsh(new(big.Int).SetUint64(uint64(m.errorCode)), 112))
			v.Or(v, new(big.Int).Lsh(new(big.Int).SetUint64(uint64(m.errorLocation)), 120))
		}
		v.FillBytes(m2[:])
		words = append(words, m2)
		var m3 [32]byte
		if eligible {
			m.starts.FillBytes(m3[:])
		}
		words = append(words, m3)
	}
	out := make([]byte, 0, len(words)*32+len(p.literals)*8)
	for _, w := range words {
		out = append(out, w[:]...)
	}
	for _, l := range p.literals {
		out = append(out, byte(l.method>>8), byte(l.method), byte(l.pc>>8), byte(l.pc), byte(l.bits>>24), byte(l.bits>>16), byte(l.bits>>8), byte(l.bits))
	}
	return out
}

func stockS2aVerifyRegister(t *testing.T, e *stockS2aVerifyEnv, parser stockS2aVerifyArtifact, parserAt, rawAt common.Address, pageHash, payloadHash common.Hash) (common.Hash, common.Address, common.Hash, uint16, stockS2aVerifyTx) {
	t.Helper()
	tx := e.mustCall(parserAt, stockS2aVerifyCallData(t, parser, "registerClass", rawAt, pageHash, payloadHash), stockS2aVerifyCreateGas)
	out := stockS2aVerifyUnpack(t, parser, "registerClass", tx.result.ReturnData)
	if len(out) != 4 {
		t.Fatalf("registerClass outputs=%d", len(out))
	}
	return common.Hash(out[0].([32]byte)), out[1].(common.Address), common.Hash(out[2].([32]byte)), out[3].(uint16), tx
}
func stockS2aVerifyClassRecord(t *testing.T, e *stockS2aVerifyEnv, parser stockS2aVerifyArtifact, at common.Address, id common.Hash) (common.Address, common.Hash) {
	t.Helper()
	tx := e.mustCall(at, stockS2aVerifyCallData(t, parser, "classRecord", id), stockS2aVerifyCallGas)
	out := stockS2aVerifyUnpack(t, parser, "classRecord", tx.result.ReturnData)
	return out[0].(common.Address), common.Hash(out[1].([32]byte))
}
func stockS2aVerifyDeployRegistered(t *testing.T, e *stockS2aVerifyEnv, page, parser stockS2aVerifyArtifact, parserAt common.Address, raw []byte) (common.Address, common.Hash, common.Hash, common.Hash, common.Address, common.Hash, stockS2aVerifyTx) {
	t.Helper()
	rawAt, pageHash, payloadHash, _ := stockS2aVerifyDeployPage(t, e, page, raw)
	id, metaAt, metaHash, _, tx := stockS2aVerifyRegister(t, e, parser, parserAt, rawAt, pageHash, payloadHash)
	return rawAt, pageHash, payloadHash, id, metaAt, metaHash, tx
}
func stockS2aVerifyDeployCoordinator(t *testing.T, e *stockS2aVerifyEnv, coord stockS2aVerifyArtifact, parserAt common.Address, parserHash, classID common.Hash, moduleAt common.Address, moduleHash common.Hash, entry string, args []int32, cap uint64) (common.Address, stockS2aVerifyTx) {
	t.Helper()
	return e.mustCreate(stockS2aVerifyConstructor(t, coord, parserAt, parserHash, classID, moduleAt, moduleHash, []byte(entry), args, cap), stockS2aVerifyCreateGas)
}
func stockS2aVerifyCheckpointAt(t *testing.T, e *stockS2aVerifyEnv, coord stockS2aVerifyArtifact, at common.Address) stockS2aVerifyCheckpoint {
	t.Helper()
	tx := e.mustCall(at, stockS2aVerifyCallData(t, coord, "checkpoint"), stockS2aVerifyCallGas)
	out := stockS2aVerifyUnpack(t, coord, "checkpoint", tx.result.ReturnData)
	return stockS2aVerifyCheckpoint{out[0].(uint32), common.Hash(out[1].([32]byte)), common.Hash(out[2].([32]byte)), common.Hash(out[3].([32]byte)), out[4].(uint64), out[5].(uint64), common.Hash(out[6].([32]byte)), stockS2aVerifyMachineFrom(out[7])}
}
func stockS2aVerifyResume(t *testing.T, e *stockS2aVerifyEnv, coord stockS2aVerifyArtifact, at common.Address, epoch uint64, budget uint16, dirty uint8, gas uint64) stockS2aVerifyTx {
	t.Helper()
	return e.apply(&at, stockS2aVerifyCallData(t, coord, "resume", epoch, budget, dirty), gas)
}
func stockS2aVerifyAssertRollback(t *testing.T, e *stockS2aVerifyEnv, coord stockS2aVerifyArtifact, at common.Address, before stockS2aVerifyCheckpoint, tx stockS2aVerifyTx) {
	t.Helper()
	if len(tx.logs) != 0 {
		t.Fatalf("failed transaction retained %d logs", len(tx.logs))
	}
	after := stockS2aVerifyCheckpointAt(t, e, coord, at)
	if before.Schema != after.Schema || before.ClassID != after.ClassID || before.ProgramID != after.ProgramID || before.InputRoot != after.InputRoot || before.Epoch != after.Epoch || before.TotalSteps != after.TotalSteps || before.Digest != after.Digest || !stockS2aVerifyMachineEqual(before.Machine, after.Machine) {
		t.Fatalf("failed resume changed checkpoint\nbefore=%+v\nafter=%+v", before, after)
	}
}
func stockS2aVerifyABIHash(t *testing.T, typesText []string, values ...any) common.Hash {
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
func stockS2aVerifyClassID(t *testing.T, parserHash common.Hash, rawAt common.Address, pageHash, payloadHash, metadataHash common.Hash) common.Hash {
	return stockS2aVerifyABIHash(t, []string{"bytes32", "uint32", "bytes32", "address", "bytes32", "bytes32", "bytes32"}, crypto.Keccak256Hash([]byte("JVMEVM:S2A:CLASS")), uint32(3), parserHash, rawAt, pageHash, payloadHash, metadataHash)
}
func stockS2aVerifyProgramID(t *testing.T, classID common.Hash, index uint16, entry, desc []byte, moduleHash common.Hash) common.Hash {
	return stockS2aVerifyABIHash(t, []string{"bytes32", "uint32", "bytes32", "uint16", "bytes32", "bytes32", "bytes32"}, crypto.Keccak256Hash([]byte("JVMEVM:S2A:PROGRAM")), uint32(3), classID, index, crypto.Keccak256Hash(entry), crypto.Keccak256Hash(desc), moduleHash)
}
func stockS2aVerifyArgsHash(t *testing.T, args []int32) common.Hash {
	return stockS2aVerifyABIHash(t, []string{"int32[]"}, args)
}
func stockS2aVerifyInputRoot(t *testing.T, program, argsHash common.Hash, cap uint64) common.Hash {
	return stockS2aVerifyABIHash(t, []string{"bytes32", "bytes32", "bytes32", "uint64"}, crypto.Keccak256Hash([]byte("JVMEVM:S2A:INPUT")), program, argsHash, cap)
}
func stockS2aVerifyDigest(t *testing.T, input, parserHash, moduleHash common.Hash, m stockS2aVerifyMachine, epoch, total uint64, machineType abi.Type) common.Hash {
	t.Helper()
	u32, _ := abi.NewType("uint32", "", nil)
	b32, _ := abi.NewType("bytes32", "", nil)
	u64, _ := abi.NewType("uint64", "", nil)
	args := abi.Arguments{{Type: u32}, {Type: b32}, {Type: b32}, {Type: b32}, {Type: machineType}, {Type: u64}, {Type: u64}}
	packed, err := args.Pack(uint32(3), input, parserHash, moduleHash, m, epoch, total)
	if err != nil {
		t.Fatal(err)
	}
	return crypto.Keccak256Hash(packed)
}
func stockS2aVerifyCheckEvent(t *testing.T, coord stockS2aVerifyArtifact, tx stockS2aVerifyTx, c stockS2aVerifyCheckpoint, executed uint16, dirty uint8) {
	t.Helper()
	if len(tx.logs) != 1 {
		t.Fatalf("checkpoint logs=%d", len(tx.logs))
	}
	ev := coord.abi.Events["CheckpointV3"]
	log := tx.logs[0]
	if len(log.Topics) != 3 || log.Topics[0] != ev.ID || new(big.Int).SetBytes(log.Topics[1][:]).Uint64() != c.Epoch || common.Hash(log.Topics[2]) != c.ProgramID {
		t.Fatalf("bad event topics %v", log.Topics)
	}
	v, err := ev.Inputs.NonIndexed().Unpack(log.Data)
	if err != nil {
		t.Fatal(err)
	}
	if v[0].(uint64) != c.TotalSteps || v[1].(uint32) != c.Machine.Pc || v[2].(uint8) != c.Machine.Sp || v[3].(uint8) != c.Machine.Lifecycle || v[4].(uint8) != c.Machine.JavaFaultKind || v[5].(int32) != c.Machine.Result || v[6].(uint16) != executed || v[7].(uint8) != dirty || common.Hash(v[8].([32]byte)) != c.Digest {
		t.Fatalf("bad CheckpointV3 data %v", v)
	}
}

type stockS2aVerifyCatalogue struct {
	Schema               uint32                         `json:"schema"`
	CatalogueCount       uint16                         `json:"catalogueCount"`
	CatalogueRoot        string                         `json:"catalogueRoot"`
	LegacyManifestSHA256 string                         `json:"legacyManifestSha256"`
	Classes              []stockS2aVerifyCatalogueClass `json:"classes"`
	Cases                []stockS2aVerifyCatalogueCase  `json:"cases"`
}

type stockS2aVerifyCatalogueClass struct {
	Name, Source, SourceSHA256, ClassSHA256, RawPayloadHash string
	ClassBytes                                              int
}

type stockS2aVerifyCatalogueCase struct {
	Index             uint16
	ID, Stage         string
	Class, Entry      string
	Descriptor        string
	Args              []int32
	ArgsHash          string
	LegacyGasLimit    uint64
	Expected          *int32
	ExpectedKind      string
	ExpectedException string
	JavaFaultKind     uint8
	FaultPC           uint32
	PC                uint32
	SP                uint8
	Lifecycle         uint8
	CodeLength        uint32
	Stack             []int32
	Steps             uint64
	Leaf              string
}

type stockS2aVerifyLegacyCase struct {
	ID                string   `json:"id"`
	Stage             string   `json:"stage"`
	Class             string   `json:"class"`
	Method            string   `json:"method"`
	ExpectedKind      string   `json:"expected_kind"`
	ExpectedException string   `json:"expected_exception"`
	Sources           []string `json:"sources"`
	Args              []int32  `json:"args"`
	GasLimit          uint64   `json:"gas_limit"`
	Timeout           uint64   `json:"timeout_seconds"`
}

type stockS2aVerifyLegacyManifest struct {
	Cases []stockS2aVerifyLegacyCase `json:"cases"`
}

func stockS2aVerifyDecodeHash(t *testing.T, text string) common.Hash {
	t.Helper()
	if len(text) != 66 || !strings.HasPrefix(text, "0x") {
		t.Fatalf("noncanonical hash %q", text)
	}
	b, err := hex.DecodeString(text[2:])
	if err != nil {
		t.Fatal(err)
	}
	return common.BytesToHash(b)
}

func TestStockS2aVerifyFrozen201CatalogueCommitment(t *testing.T) {
	blob, err := os.ReadFile("../../testdata/stock/s2a/catalogue.json")
	if err != nil {
		t.Fatalf("read frozen S2a catalogue (harness integration dependency is absent): %v", err)
	}
	var catalogue stockS2aVerifyCatalogue
	if err := json.Unmarshal(blob, &catalogue); err != nil {
		t.Fatal(err)
	}
	if catalogue.Schema != 3 || catalogue.CatalogueCount != 201 || len(catalogue.Cases) != 201 || len(catalogue.Classes) != 11 {
		t.Fatalf("catalogue schema=%d count=%d rows=%d classes=%d", catalogue.Schema, catalogue.CatalogueCount, len(catalogue.Cases), len(catalogue.Classes))
	}
	manifestBlob, err := os.ReadFile("../../testdata/differential/cases.json")
	if err != nil {
		t.Fatal(err)
	}
	if got := fmt.Sprintf("%x", sha256.Sum256(manifestBlob)); got != catalogue.LegacyManifestSHA256 {
		t.Fatalf("legacy manifest hash=%s want=%s", got, catalogue.LegacyManifestSHA256)
	}
	var manifest stockS2aVerifyLegacyManifest
	if err := json.Unmarshal(manifestBlob, &manifest); err != nil {
		t.Fatal(err)
	}
	var legacy []stockS2aVerifyLegacyCase
	for _, tc := range manifest.Cases {
		if tc.Stage == "m1" || tc.Stage == "m2" || tc.Stage == "m2b" {
			legacy = append(legacy, tc)
		}
	}
	if len(legacy) != 201 {
		t.Fatalf("legacy M1/M2/M2b rows=%d", len(legacy))
	}
	payloads := make(map[string]common.Hash)
	compileDir := t.TempDir()
	compileArgs := []string{"--release", "8", "-d", compileDir}
	for _, class := range catalogue.Classes {
		if class.Name == "" || class.Source != class.Name+".java" || class.ClassBytes < 1 || class.ClassBytes > 4096 || len(class.SourceSHA256) != 64 || len(class.ClassSHA256) != 64 {
			t.Fatalf("invalid class commitment %+v", class)
		}
		sourcePath := filepath.Join("../../testdata/differential", class.Source)
		source, err := os.ReadFile(sourcePath)
		if err != nil {
			t.Fatal(err)
		}
		if got := fmt.Sprintf("%x", sha256.Sum256(source)); got != class.SourceSHA256 {
			t.Fatalf("%s source hash=%s", class.Name, got)
		}
		compileArgs = append(compileArgs, sourcePath)
		payloads[class.Name] = stockS2aVerifyDecodeHash(t, class.RawPayloadHash)
	}
	stockS2aVerifyCommand(t, "javac", compileArgs...)
	for _, class := range catalogue.Classes {
		raw, err := os.ReadFile(filepath.Join(compileDir, class.Name+".class"))
		if err != nil {
			t.Fatal(err)
		}
		if len(raw) != class.ClassBytes || fmt.Sprintf("%x", sha256.Sum256(raw)) != class.ClassSHA256 || crypto.Keccak256Hash(raw) != payloads[class.Name] {
			t.Fatalf("%s compiled identity bytes=%d sha=%x keccak=%s", class.Name, len(raw), sha256.Sum256(raw), crypto.Keccak256Hash(raw))
		}
	}
	leaves := make([][32]byte, len(catalogue.Cases))
	seen := make(map[string]bool)
	roots := make(map[string]bool)
	values, faults := 0, 0
	var attempted uint64
	for i, tc := range catalogue.Cases {
		old := legacy[i]
		if int(tc.Index) != i || seen[tc.ID] || tc.ID != old.ID || tc.Stage != old.Stage || tc.Class != old.Class || tc.Entry != old.Method || !reflect.DeepEqual(tc.Args, old.Args) || tc.LegacyGasLimit != old.GasLimit || len(old.Sources) != 1 || old.Sources[0] != tc.Class+".java" || old.Timeout == 0 {
			t.Fatalf("catalogue row %d changed legacy identity/limits: new=%+v old=%+v", i, tc, old)
		}
		seen[tc.ID] = true
		roots[tc.Class+"\x00"+tc.Entry+"\x00"+tc.Descriptor] = true
		attempted += tc.Steps
		if len(tc.Args) > 4 || tc.Descriptor != "("+strings.Repeat("I", len(tc.Args))+")I" {
			t.Fatalf("%s exceeds one-frame scalar root profile", tc.ID)
		}
		payload, ok := payloads[tc.Class]
		if !ok {
			t.Fatalf("%s unknown class %s", tc.ID, tc.Class)
		}
		argsHash := stockS2aVerifyArgsHash(t, tc.Args)
		if argsHash != stockS2aVerifyDecodeHash(t, tc.ArgsHash) {
			t.Fatalf("%s argsHash", tc.ID)
		}
		leaf := stockS2aVerifyABIHash(t, []string{"uint32", "uint16", "bytes32", "bytes32", "bytes32", "bytes32", "bytes32", "bytes32"}, uint32(3), uint16(i), crypto.Keccak256Hash([]byte(tc.ID)), payload, crypto.Keccak256Hash([]byte(tc.Class)), crypto.Keccak256Hash([]byte(tc.Entry)), crypto.Keccak256Hash([]byte(tc.Descriptor)), argsHash)
		if leaf != stockS2aVerifyDecodeHash(t, tc.Leaf) {
			t.Fatalf("%s leaf=%s", tc.ID, leaf)
		}
		leaves[i] = leaf
		switch old.ExpectedKind {
		case "value":
			values++
			if tc.Expected == nil || tc.ExpectedKind != "value" || tc.ExpectedException != "" || tc.JavaFaultKind != 0 || tc.FaultPC != 0 || tc.Lifecycle != 1 || tc.SP != 0 || tc.PC > tc.CodeLength {
				t.Fatalf("%s malformed value outcome", tc.ID)
			}
		case "java_exception":
			faults++
			// The catalogue mirrors MachineV3.result, which is canonically zero
			// for JAVA_FAULT, not a returned Java value. Require the fault state
			// and preserved zero-divisor operand rather than expecting JSON null.
			if old.ExpectedException != "java.lang.ArithmeticException" || tc.Expected == nil || *tc.Expected != 0 || tc.ExpectedKind != "java_exception" || tc.ExpectedException != old.ExpectedException || tc.JavaFaultKind != 1 || tc.Lifecycle != 3 || tc.PC != tc.FaultPC || tc.PC >= tc.CodeLength || tc.SP < 2 || tc.SP > 8 || len(tc.Stack) != 8 || tc.Stack[tc.SP-1] != 0 {
				t.Fatalf("%s malformed fault outcome", tc.ID)
			}
		default:
			t.Fatalf("%s forbidden expected kind %s", tc.ID, old.ExpectedKind)
		}
	}
	root := stockS2aVerifyABIHash(t, []string{"uint32", "uint16", "bytes32[]"}, uint32(3), uint16(201), leaves)
	if root != stockS2aVerifyDecodeHash(t, catalogue.CatalogueRoot) || values != 199 || faults != 2 || len(roots) != 60 || attempted != 2642 {
		t.Fatalf("catalogue root=%s values=%d faults=%d roots=%d attempted=%d", root, values, faults, len(roots), attempted)
	}
}

func TestStockS2aVerifyFrozenABIArtifactsMetadataAndDeployment(t *testing.T) {
	page := stockS2aVerifyLoadPage(t)
	metadata := stockS2aVerifyLoadArtifact(t, "S2aMetadataPage")
	parser := stockS2aVerifyLoadArtifact(t, "S2aClassParser")
	module := stockS2aVerifyLoadArtifact(t, "S2aStepModule")
	coord := stockS2aVerifyLoadArtifact(t, "S2aCoordinator")
	if len(page.runtime) > 12*1024 || len(page.init) > 24*1024 {
		t.Fatal("accepted S0 ArtifactPage limits changed")
	}
	if len(metadata.abi.Constructor.Inputs) != 1 || metadata.abi.Constructor.Inputs[0].Type.String() != "bytes" || len(metadata.abi.Methods) != 0 {
		t.Fatalf("metadata page ABI is not constructor(bytes)-only")
	}
	stockS2aVerifyRequireError(t, metadata, "S2aClassError", "S2aClassError(uint256,uint256)")
	if len(parser.abi.Constructor.Inputs) != 0 || len(module.abi.Constructor.Inputs) != 0 {
		t.Fatal("parser/module constructor gained configuration")
	}
	stockS2aVerifyRequireMethod(t, parser, "registerClass", "registerClass(address,bytes32,bytes32)", "nonpayable", 3, 4)
	stockS2aVerifyRequireMethod(t, parser, "classRecord", "classRecord(bytes32)", "view", 1, 2)
	if len(parser.abi.Methods) != 2 {
		t.Fatalf("parser exposes mutable/non-frozen API: %v", parser.abi.Methods)
	}
	machineNames := []string{"pc", "sp", "initialized", "lifecycle", "stack", "locals", "result", "javaFaultKind", "faultPC"}
	machineTypes := []string{"uint32", "uint8", "uint8", "uint8", "uint256[8]", "uint256[8]", "int32", "uint8", "uint32"}
	programNames := []string{"parser", "parserCodeHash", "classId", "rawPage", "rawPageHash", "payloadHash", "metadataPage", "metadataHash", "methodIndex", "programId"}
	programTypes := []string{"address", "bytes32", "bytes32", "address", "bytes32", "bytes32", "address", "bytes32", "uint16", "bytes32"}
	stockS2aVerifyRequireMethod(t, module, "step", "step((address,bytes32,bytes32,address,bytes32,bytes32,address,bytes32,uint16,bytes32),(uint32,uint8,uint8,uint8,uint256[8],uint256[8],int32,uint8,uint32),uint16)", "view", 3, 2)
	if len(module.abi.Methods) != 1 {
		t.Fatalf("module exposes configuration: %v", module.abi.Methods)
	}
	stockS2aVerifyTuple(t, module.abi.Methods["step"].Inputs[0].Type, programNames, programTypes)
	stockS2aVerifyTuple(t, module.abi.Methods["step"].Inputs[1].Type, machineNames, machineTypes)
	stockS2aVerifyTuple(t, module.abi.Methods["step"].Outputs[0].Type, machineNames, machineTypes)
	wantCtor := []string{"address", "bytes32", "bytes32", "address", "bytes32", "bytes", "int32[]", "uint64"}
	if len(coord.abi.Constructor.Inputs) != len(wantCtor) {
		t.Fatalf("coordinator ctor arity=%d", len(coord.abi.Constructor.Inputs))
	}
	for i, w := range wantCtor {
		if coord.abi.Constructor.Inputs[i].Type.String() != w {
			t.Fatalf("coordinator ctor arg%d=%s want=%s", i, coord.abi.Constructor.Inputs[i].Type, w)
		}
	}
	stockS2aVerifyRequireMethod(t, coord, "resume", "resume(uint64,uint16,uint8)", "nonpayable", 3, 6)
	stockS2aVerifyRequireMethod(t, coord, "checkpoint", "checkpoint()", "view", 0, 8)
	stockS2aVerifyRequireMethod(t, coord, "programContext", "programContext()", "view", 0, 1)
	stockS2aVerifyTuple(t, coord.abi.Methods["checkpoint"].Outputs[7].Type, machineNames, machineTypes)
	stockS2aVerifyTuple(t, coord.abi.Methods["programContext"].Outputs[0].Type, programNames, programTypes)
	for _, g := range []struct{ name, sig, typ string }{{"parser", "parser()", "address"}, {"expectedParserHash", "expectedParserHash()", "bytes32"}, {"classId", "classId()", "bytes32"}, {"module", "module()", "address"}, {"expectedModuleHash", "expectedModuleHash()", "bytes32"}, {"programId", "programId()", "bytes32"}, {"argsHash", "argsHash()", "bytes32"}, {"inputRoot", "inputRoot()", "bytes32"}, {"maxTotalSteps", "maxTotalSteps()", "uint64"}} {
		stockS2aVerifyRequireMethod(t, coord, g.name, g.sig, "view", 0, 1)
		if coord.abi.Methods[g.name].Outputs[0].Type.String() != g.typ {
			t.Fatalf("getter %s type=%s", g.name, coord.abi.Methods[g.name].Outputs[0].Type)
		}
	}
	if len(coord.abi.Methods) != 12 {
		t.Fatalf("coordinator API count=%d want12", len(coord.abi.Methods))
	}
	for _, a := range []stockS2aVerifyArtifact{parser, module, coord} {
		runtimeCap := 12 * 1024
		if a.name == "S2aClassParser" {
			runtimeCap = 16 * 1024
		}
		if len(a.runtime) > runtimeCap || len(a.init) > 24*1024 {
			t.Fatalf("%s sizes init=%d runtime=%d", a.name, len(a.init), len(a.runtime))
		}
	}
	for _, a := range []stockS2aVerifyArtifact{parser, module, coord} {
		for _, x := range []struct{ name, sig string }{{"S2aControlError", "S2aControlError(uint256)"}, {"S2aMethodError", "S2aMethodError(uint256,uint256)"}, {"S2aBytecodeError", "S2aBytecodeError(uint256,uint256)"}} {
			if _, ok := a.abi.Errors[x.name]; ok {
				stockS2aVerifyRequireError(t, a, x.name, x.sig)
			}
		}
	}
	stockS2aVerifyRequireError(t, parser, "StockPageError", "StockPageError(uint256)")
	stockS2aVerifyRequireError(t, parser, "S2aClassError", "S2aClassError(uint256,uint256)")
	stockS2aVerifyRequireError(t, coord, "S2aControlError", "S2aControlError(uint256)")
	event, ok := parser.abi.Events["ClassRegistered"]
	if !ok || event.Sig != "ClassRegistered(bytes32,address,address,bytes32,uint16)" || len(event.Inputs) != 5 || !event.Inputs[0].Indexed || !event.Inputs[1].Indexed {
		t.Fatalf("ClassRegistered ABI=%v", event)
	}
	checkpointEvent, ok := coord.abi.Events["CheckpointV3"]
	if !ok || checkpointEvent.Sig != "CheckpointV3(uint64,bytes32,uint64,uint32,uint8,uint8,uint8,int32,uint16,uint8,bytes32)" || len(checkpointEvent.Inputs) != 11 || !checkpointEvent.Inputs[0].Indexed || !checkpointEvent.Inputs[1].Indexed {
		t.Fatalf("CheckpointV3 ABI=%v", checkpointEvent)
	}

	e := stockS2aVerifyNewEnv(t)
	defer e.close()
	// Metadata payload 8,191 is the exact constructor boundary (8,192 bytes
	// including STOP). One more byte fails atomically as a metadata capacity error.
	metadataBoundary, _ := e.mustCreate(stockS2aVerifyConstructor(t, metadata, make([]byte, 8191)), stockS2aVerifyCreateGas)
	if len(e.state.StateDB.GetCode(metadataBoundary)) != 8192 {
		t.Fatal("metadata 8KiB boundary")
	}
	metadataNonce := e.state.StateDB.GetNonce(e.sender)
	metadataTooLarge := e.apply(nil, stockS2aVerifyConstructor(t, metadata, make([]byte, 8192)), stockS2aVerifyCreateGas)
	stockS2aVerifyAssertRevert(t, metadataTooLarge, "S2aClassError(uint256,uint256)", 5, 0)
	if len(e.state.StateDB.GetCode(crypto.CreateAddress(e.sender, metadataNonce))) != 0 {
		t.Fatal("rejected metadata page left code")
	}
	parserAt, parserTx := e.mustCreate(parser.init, stockS2aVerifyCreateGas)
	moduleAt, moduleTx := e.mustCreate(module.init, stockS2aVerifyCreateGas)
	parserHash := crypto.Keccak256Hash(e.state.StateDB.GetCode(parserAt))
	moduleHash := crypto.Keccak256Hash(e.state.StateDB.GetCode(moduleAt))
	if !bytes.Equal(e.state.StateDB.GetCode(parserAt), parser.runtime) || !bytes.Equal(e.state.StateDB.GetCode(moduleAt), module.runtime) {
		t.Fatal("deployed component differs from pinned artifact")
	}
	class := stockS2aVerifySimpleClass([]byte{0x1a, 0x04, 0x60, 0xac}, 2, 1, "(I)I")
	rawAt, pageHash, payloadHash, _ := stockS2aVerifyDeployPage(t, e, page, class.bytes)
	classID, metadataAt, metadataHash, declared, registerTx := stockS2aVerifyRegister(t, e, parser, parserAt, rawAt, pageHash, payloadHash)
	if declared != 2 || len(registerTx.logs) != 1 {
		t.Fatalf("registration declared=%d logs=%d", declared, len(registerTx.logs))
	}
	metadataCode := e.state.StateDB.GetCode(metadataAt)
	if len(metadataCode) < 2 || metadataCode[0] != 0 || len(metadataCode) > 8192 {
		t.Fatalf("metadata runtime size/prefix=%d/%x", len(metadataCode), metadataCode)
	}
	if crypto.Keccak256Hash(metadataCode) != metadataHash {
		t.Fatal("metadataHash is not actual code hash")
	}
	expectedPayload := stockS2aVerifyMetadataExpected(class.bytes, rawAt, pageHash, payloadHash)
	if !bytes.Equal(metadataCode[1:], expectedPayload) {
		t.Fatalf("parser-derived metadata mismatch\nhave=%x\nwant=%x", metadataCode[1:], expectedPayload)
	}
	if len(metadataCode) != 1+6*32+4*32*int(declared) {
		t.Fatalf("metadata exact length=%d", len(metadataCode))
	}
	wantClass := stockS2aVerifyClassID(t, parserHash, rawAt, pageHash, payloadHash, metadataHash)
	if classID != wantClass {
		t.Fatalf("classId=%s want=%s", classID, wantClass)
	}
	recordAt, recordHash := stockS2aVerifyClassRecord(t, e, parser, parserAt, classID)
	if recordAt != metadataAt || recordHash != metadataHash {
		t.Fatal("classRecord is not registration output")
	}
	log := registerTx.logs[0]
	if log.Address != parserAt || len(log.Topics) != 3 || log.Topics[0] != event.ID || common.Hash(log.Topics[1]) != classID || common.BytesToAddress(log.Topics[2][12:]) != rawAt {
		t.Fatalf("ClassRegistered topics=%v", log.Topics)
	}
	data, err := event.Inputs.NonIndexed().Unpack(log.Data)
	if err != nil {
		t.Fatal(err)
	}
	if data[0].(common.Address) != metadataAt || common.Hash(data[1].([32]byte)) != metadataHash || data[2].(uint16) != declared {
		t.Fatalf("ClassRegistered data=%v", data)
	}
	// Registration is append-only and idempotent: no second internal CREATE,
	// event, or write is permitted for the same page/hash tuple.
	parserNonce := e.state.StateDB.GetNonce(parserAt)
	id2, at2, hash2, n2, retry := stockS2aVerifyRegister(t, e, parser, parserAt, rawAt, pageHash, payloadHash)
	if id2 != classID || at2 != metadataAt || hash2 != metadataHash || n2 != declared || len(retry.logs) != 0 || e.state.StateDB.GetNonce(parserAt) != parserNonce {
		t.Fatal("registration was not idempotent")
	}
	args := []int32{math.MinInt32}
	coordAt, coordTx := stockS2aVerifyDeployCoordinator(t, e, coord, parserAt, parserHash, classID, moduleAt, moduleHash, "entry", args, 64)
	actualCoord := append([]byte(nil), e.state.StateDB.GetCode(coordAt)...)
	if len(actualCoord) != len(coord.runtime) || len(coord.immutables) == 0 {
		t.Fatalf("coordinator template/immutable refs actual=%d template=%d refs=%d", len(actualCoord), len(coord.runtime), len(coord.immutables))
	}
	template := append([]byte(nil), coord.runtime...)
	refs := 0
	for _, locations := range coord.immutables {
		for _, ref := range locations {
			if ref.Length != 32 || ref.Start < 0 || ref.Start+ref.Length > len(template) {
				t.Fatalf("bad immutable ref %+v", ref)
			}
			copy(actualCoord[ref.Start:ref.Start+32], template[ref.Start:ref.Start+32])
			refs++
		}
	}
	if refs < 9 || !bytes.Equal(actualCoord, template) {
		t.Fatal("coordinator differs outside compiler immutableReferences")
	}
	programTx := e.mustCall(coordAt, stockS2aVerifyCallData(t, coord, "programContext"), stockS2aVerifyCallGas)
	program := stockS2aVerifyProgramFrom(stockS2aVerifyUnpack(t, coord, "programContext", programTx.result.ReturnData)[0])
	wantProgram := stockS2aVerifyProgramID(t, classID, 1, []byte("entry"), []byte("(I)I"), moduleHash)
	wantArgs := stockS2aVerifyArgsHash(t, args)
	wantInput := stockS2aVerifyInputRoot(t, wantProgram, wantArgs, 64)
	if program.Parser != parserAt || common.Hash(program.ParserCodeHash) != parserHash || common.Hash(program.ClassId) != classID || program.RawPage != rawAt || common.Hash(program.RawPageHash) != pageHash || common.Hash(program.PayloadHash) != payloadHash || program.MetadataPage != metadataAt || common.Hash(program.MetadataHash) != metadataHash || program.MethodIndex != 1 || common.Hash(program.ProgramId) != wantProgram {
		t.Fatalf("programContext=%+v", program)
	}
	initial := stockS2aVerifyCheckpointAt(t, e, coord, coordAt)
	if initial.Schema != 3 || initial.ClassID != classID || initial.ProgramID != wantProgram || initial.InputRoot != wantInput || initial.Epoch != 0 || initial.TotalSteps != 0 || initial.Machine.Pc != 0 || initial.Machine.Sp != 0 || initial.Machine.Initialized != 1 || initial.Machine.Lifecycle != stockS2aVerifyRunnable || initial.Machine.Result != 0 || initial.Machine.JavaFaultKind != 0 || initial.Machine.FaultPC != 0 || initial.Machine.Locals[0].Cmp(stockS2aVerifyTagged(0x80000000)) != 0 {
		t.Fatalf("initial checkpoint=%+v", initial)
	}
	if initial.Digest != stockS2aVerifyDigest(t, wantInput, parserHash, moduleHash, initial.Machine, 0, 0, coord.abi.Methods["checkpoint"].Outputs[7].Type) {
		t.Fatal("initial stateDigest mismatch")
	}
	resume := stockS2aVerifyResume(t, e, coord, coordAt, 0, 128, 32, stockS2aVerifyCallGas)
	if resume.result == nil || resume.result.Err != nil || resume.result.UsedGas > stockS2aVerifyCallGas {
		t.Fatalf("resume failed %+v", resume)
	}
	final := stockS2aVerifyCheckpointAt(t, e, coord, coordAt)
	if final.Epoch != 1 || final.TotalSteps != 4 || final.Machine.Lifecycle != stockS2aVerifyReturned || final.Machine.Result != math.MinInt32+1 || final.Machine.Sp != 0 {
		t.Fatalf("terminal checkpoint=%+v", final)
	}
	dirty := stockS2aVerifyDirty(initial.Machine, final.Machine)
	stockS2aVerifyCheckEvent(t, coord, resume, final, 4, dirty)
	t.Logf("S2a deployed parser=%dB hash=%s gas=%d module=%dB hash=%s gas=%d raw=%dB metadata=%dB hash=%s registerGas=%d coordinator=%dB hash=%s gas=%d resumeGas=%d", len(parser.runtime), parserHash, parserTx.result.UsedGas, len(module.runtime), moduleHash, moduleTx.result.UsedGas, len(class.bytes), len(metadataCode), metadataHash, registerTx.result.UsedGas, len(e.state.StateDB.GetCode(coordAt)), crypto.Keccak256Hash(e.state.StateDB.GetCode(coordAt)), coordTx.result.UsedGas, resume.result.UsedGas)
}

func stockS2aVerifySelectedFailure(t *testing.T, e *stockS2aVerifyEnv, page, parser, coord, module stockS2aVerifyArtifact, parserAt, moduleAt common.Address, parserHash, moduleHash common.Hash, class stockS2aVerifyClass, entry string, args []int32, signature string, words ...any) {
	t.Helper()
	_, _, _, id, _, _, _ := stockS2aVerifyDeployRegistered(t, e, page, parser, parserAt, class.bytes)
	nonce := e.state.StateDB.GetNonce(e.sender)
	tx := e.apply(nil, stockS2aVerifyConstructor(t, coord, parserAt, parserHash, id, moduleAt, moduleHash, []byte(entry), args, uint64(64)), stockS2aVerifyCreateGas)
	stockS2aVerifyAssertRevert(t, tx, signature, words...)
	if len(e.state.StateDB.GetCode(crypto.CreateAddress(e.sender, nonce))) != 0 {
		t.Fatal("failed coordinator selection left code")
	}
}

func TestStockS2aVerifyParserCapsMetadataCanonicalityAndSelection(t *testing.T) {
	page := stockS2aVerifyLoadPage(t)
	parser := stockS2aVerifyLoadArtifact(t, "S2aClassParser")
	module := stockS2aVerifyLoadArtifact(t, "S2aStepModule")
	coord := stockS2aVerifyLoadArtifact(t, "S2aCoordinator")
	e := stockS2aVerifyNewEnv(t)
	defer e.close()
	parserAt, _ := e.mustCreate(parser.init, stockS2aVerifyCreateGas)
	moduleAt, _ := e.mustCreate(module.init, stockS2aVerifyCreateGas)
	parserHash := crypto.Keccak256Hash(parser.runtime)
	moduleHash := crypto.Keccak256Hash(module.runtime)
	// Retained CP=512 and selected Code=256 boundaries are genuine valid inputs.
	code256 := append(bytes.Repeat([]byte{0x00}, 254), 0x03, 0xac)
	boundary := stockS2aVerifyBuildClass("S2aBoundary", []stockS2aVerifyMethod{{"edge", "()I", 0x0009, code256, 1, 0, 1, 0}}, 512)
	rawAt, pageHash, payloadHash, _ := stockS2aVerifyDeployPage(t, e, page, boundary.bytes)
	id, metaAt, metaHash, n, _ := stockS2aVerifyRegister(t, e, parser, parserAt, rawAt, pageHash, payloadHash)
	if n != 2 || len(boundary.bytes) > 4096 {
		t.Fatalf("boundary class methods=%d bytes=%d", n, len(boundary.bytes))
	}
	if crypto.Keccak256Hash(e.state.StateDB.GetCode(metaAt)) != metaHash {
		t.Fatal("boundary metadata hash")
	}
	at, _ := stockS2aVerifyDeployCoordinator(t, e, coord, parserAt, parserHash, id, moduleAt, moduleHash, "edge", nil, 4096)
	r := stockS2aVerifyResume(t, e, coord, at, 0, 128, 32, stockS2aVerifyCallGas)
	if r.result.Err != nil {
		t.Fatal(r.result.Err)
	}
	// 32 declared methods and exactly 256 cached literal records produce the
	// maximum frozen aggregate metadata payload, 6,336 bytes, without trailing data.
	methods := make([]stockS2aVerifyMethod, 31)
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
		if count == 0 {
			// A quota fixture must be valid Java: no preceding store initializes
			// local0 in these methods. Keep their two-byte bodies, return zero.
			code = append(code, 0x03, 0xac)
		} else {
			code = append(code, 0x1a, 0xac)
		}
		methods[i] = stockS2aVerifyMethod{fmt.Sprintf("m%02d", i), "()I", 0x0009, code, 1, 1, 1, 0}
	}
	t.Run("declared32-literals256-metadata6336", func(t *testing.T) {
		aggregate := stockS2aVerifyBuildClass("S2aAggregate", methods, 0)
		stockS2aVerifyAssertAggregateJVM(t, aggregate.bytes)
		aggregateRawAt, aggregatePageHash, aggregatePayloadHash, _ := stockS2aVerifyDeployPage(t, e, page, aggregate.bytes)
		register := e.apply(&parserAt, stockS2aVerifyCallData(t, parser, "registerClass", aggregateRawAt, aggregatePageHash, aggregatePayloadHash), stockS2aVerifyCreateGas)
		if register.coreErr != nil || register.result == nil || register.result.Err != nil {
			t.Fatalf("exact aggregate registration must fit 8M: core=%v evm=%v data=%x", register.coreErr, stockS2aVerifyResultErr(register.result), stockS2aVerifyResultData(register.result))
		}
		values := stockS2aVerifyUnpack(t, parser, "registerClass", register.result.ReturnData)
		aggregateMetaAt, aggregateMetaHash, aggregateCount := values[1].(common.Address), common.Hash(values[2].([32]byte)), values[3].(uint16)
		metaCode := e.state.StateDB.GetCode(aggregateMetaAt)
		if aggregateCount != 32 || len(metaCode) != 1+6336 || len(metaCode) > 8192 || crypto.Keccak256Hash(metaCode) != aggregateMetaHash {
			t.Fatalf("aggregate methods=%d metadata=%d", aggregateCount, len(metaCode))
		}
		wantMeta := stockS2aVerifyMetadataExpected(aggregate.bytes, aggregateRawAt, aggregatePageHash, aggregatePayloadHash)
		if !bytes.Equal(metaCode[1:], wantMeta) {
			t.Fatal("aggregate metadata is not canonical parser-derived schema3")
		}
		t.Logf("aggregate registration gas=%d raw=%d metadata=%d", register.result.UsedGas, len(aggregate.bytes), len(metaCode))
		// Exercise each nonempty literal slice and the final zero-literal record,
		// not just successful page construction or host-side metadata comparison.
		aggregateID := common.Hash(values[0].([32]byte))
		for _, index := range []int{0, 1, 2, 3, 30} {
			instance, _ := stockS2aVerifyDeployCoordinator(t, e, coord, parserAt, parserHash, aggregateID, moduleAt, moduleHash, fmt.Sprintf("m%02d", index), nil, 512)
			state := stockS2aVerifyCheckpointAt(t, e, coord, instance)
			for state.Machine.Lifecycle == stockS2aVerifyRunnable {
				if state.Epoch >= 2 {
					t.Fatal("aggregate entry exceeded two 128-step resumes")
				}
				run := stockS2aVerifyResume(t, e, coord, instance, state.Epoch, 128, 32, stockS2aVerifyCallGas)
				if run.coreErr != nil || run.result == nil || run.result.Failed() {
					t.Fatalf("aggregate m%02d resume failed: %v/%v", index, run.coreErr, stockS2aVerifyResultErr(run.result))
				}
				state = stockS2aVerifyCheckpointAt(t, e, coord, instance)
			}
			want, steps := int32(0), uint64(2)
			if index < 3 {
				want, steps = 0x12345678, 170
			} else if index == 3 {
				want, steps = 0x12345678, 10
			}
			if state.Machine.Lifecycle != stockS2aVerifyReturned || state.Machine.Result != want || state.TotalSteps != steps {
				t.Fatalf("aggregate m%02d wrong terminal: %+v", index, state)
			}
		}
	})
	// One additional declared method fails at the raw method_count field.
	tooMany := stockS2aVerifyBuildClass("S2aMethods33", append(methods, stockS2aVerifyMethod{"extra", "()I", 0x0009, []byte{3, 0xac}, 1, 0, 1, 0}), 0)
	pa, ph, pvh, _ := stockS2aVerifyDeployPage(t, e, page, tooMany.bytes)
	tx := e.apply(&parserAt, stockS2aVerifyCallData(t, parser, "registerClass", pa, ph, pvh), stockS2aVerifyCreateGas)
	stockS2aVerifyAssertRevert(t, tx, "S2aClassError(uint256,uint256)", 5, uint64(tooMany.marks["methodCount"]))
	if at, h := stockS2aVerifyClassRecord(t, e, parser, parserAt, common.Hash{}); at != (common.Address{}) || h != (common.Hash{}) {
		t.Fatal("unknown record not zero")
	}
	// One extra literal remains individually valid but violates the aggregate cap.
	methods257 := append([]stockS2aVerifyMethod(nil), methods...)
	methods257[3].code = append([]byte{0x12, 10, 0x3b}, methods257[3].code...)
	literal257 := stockS2aVerifyBuildClass("S2aLiteral257", methods257, 0)
	pa, ph, pvh, _ = stockS2aVerifyDeployPage(t, e, page, literal257.bytes)
	tx = e.apply(&parserAt, stockS2aVerifyCallData(t, parser, "registerClass", pa, ph, pvh), stockS2aVerifyCreateGas)
	stockS2aVerifyAssertRevert(t, tx, "S2aClassError(uint256,uint256)", 5, 0)
	// cp_count itself is still capped at 512, independently of payload size.
	cp513 := stockS2aVerifyBuildClass("S2aCP513", []stockS2aVerifyMethod{{"entry", "()I", 0x0009, []byte{3, 0xac}, 1, 0, 1, 0}}, 513)
	pa, ph, pvh, _ = stockS2aVerifyDeployPage(t, e, page, cp513.bytes)
	tx = e.apply(&parserAt, stockS2aVerifyCallData(t, parser, "registerClass", pa, ph, pvh), stockS2aVerifyCreateGas)
	stockS2aVerifyAssertRevert(t, tx, "S2aClassError(uint256,uint256)", 3, uint64(cp513.marks["cpCount"]))
	// Code=257 and an unsupported opcode in an unused method are records, not
	// class-registration failures. Selecting them returns the recorded error.
	unused := stockS2aVerifyBuildClass("S2aUnused", []stockS2aVerifyMethod{{"good", "()I", 0x0009, []byte{0x08, 0xac}, 1, 0, 1, 0}, {"bad", "()I", 0x0009, []byte{0xb1}, 1, 0, 1, 0}, {"long", "()I", 0x0009, make([]byte, 257), 1, 0, 1, 0}}, 0)
	rawAt, pageHash, payloadHash, id, _, _, _ = stockS2aVerifyDeployRegistered(t, e, page, parser, parserAt, unused.bytes)
	good, _ := stockS2aVerifyDeployCoordinator(t, e, coord, parserAt, parserHash, id, moduleAt, moduleHash, "good", nil, 64)
	tx = stockS2aVerifyResume(t, e, coord, good, 0, 16, 32, stockS2aVerifyCallGas)
	if tx.result.Err != nil || stockS2aVerifyCheckpointAt(t, e, coord, good).Machine.Result != 5 {
		t.Fatal("unused invalid method poisoned valid selection")
	}
	stockS2aVerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, unused, "bad", nil, "S2aBytecodeError(uint256,uint256)", 6, 0)
	stockS2aVerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, unused, "long", nil, "S2aMethodError(uint256,uint256)", 5, 3)
	// Missing, ambiguity, invalid entry bytes and priority access->descriptor->Code->args.
	stockS2aVerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, unused, "missing", nil, "S2aMethodError(uint256,uint256)", 1, stockS2aVerifyMaxUint256)
	ambiguous := stockS2aVerifyBuildClass("S2aAmbiguous", []stockS2aVerifyMethod{{"same", "()I", 0x0009, []byte{3, 0xac}, 1, 0, 1, 0}, {"same", "(I)I", 0x0009, []byte{0x1a, 0xac}, 1, 1, 1, 0}}, 0)
	stockS2aVerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, ambiguous, "same", nil, "S2aMethodError(uint256,uint256)", 2, 2)
	for _, bad := range [][]byte{nil, {}, []byte("a/b"), []byte{'x', 0}, []byte{0x80}} {
		_, _, _, id, _, _, _ := stockS2aVerifyDeployRegistered(t, e, page, parser, parserAt, stockS2aVerifySimpleClass([]byte{3, 0xac}, 1, 0, "()I").bytes)
		tx = e.apply(nil, stockS2aVerifyConstructor(t, coord, parserAt, parserHash, id, moduleAt, moduleHash, bad, []int32{}, uint64(64)), stockS2aVerifyCreateGas)
		stockS2aVerifyAssertRevert(t, tx, "S2aMethodError(uint256,uint256)", 8, stockS2aVerifyMaxUint256)
	}
	priority := stockS2aVerifyBuildClass("S2aPriority", []stockS2aVerifyMethod{{"pick", "()V", 0x0001, nil, 0, 0, 1, 0}}, 0)
	stockS2aVerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, priority, "pick", []int32{1}, "S2aMethodError(uint256,uint256)", 3, 1)
	descriptor := stockS2aVerifyBuildClass("S2aDescriptor", []stockS2aVerifyMethod{{"pick", "()V", 0x0009, []byte{0xb1}, 0, 0, 1, 0}}, 0)
	stockS2aVerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, descriptor, "pick", []int32{1}, "S2aMethodError(uint256,uint256)", 4, 1)
	argsMismatch := stockS2aVerifySimpleClass([]byte{0x1a, 0xac}, 1, 1, "(I)I")
	stockS2aVerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, argsMismatch, "entry", nil, "S2aMethodError(uint256,uint256)", 7, 1)
	_ = module
}

func TestStockS2aVerifyWideUnusedCodeAndRealLdcW(t *testing.T) {
	source, err := os.ReadFile("../../testdata/differential/WideIntegerConstant.java")
	if err != nil {
		t.Fatal(err)
	}
	dir := t.TempDir()
	javaFile := filepath.Join(dir, "WideIntegerConstant.java")
	if err := os.WriteFile(javaFile, source, 0600); err != nil {
		t.Fatal(err)
	}
	// This is the frozen default-debug command. The resulting raw class is passed
	// unchanged; no host-derived offset or literal accompanies it.
	stockS2aVerifyCommand(t, "javac", "--release", "8", "-d", dir, javaFile)
	raw, err := os.ReadFile(filepath.Join(dir, "WideIntegerConstant.class"))
	if err != nil {
		t.Fatal(err)
	}
	if len(raw) != 3469 {
		t.Fatalf("unexpected wide fixture size=%d", len(raw))
	}
	sha := crypto.Keccak256Hash(raw)
	// Keccak is the production payload commitment; SHA-256 is the independently
	// pinned javac fixture identity from the frozen plan.
	if got := fmt.Sprintf("%x", sha256.Sum256(raw)); got != "fbf7d7498a50fa0ed8adba88ef74f702cdd4bc82fdab94ba75c8e54a77eb9137" {
		t.Fatalf("wide class sha256=%s", got)
	}
	parsed := stockS2aVerifyParseTrusted(raw)
	literalSites := 0
	for pc := 0; pc < len(parsed.methods[1].code); {
		op := parsed.methods[1].code[pc]
		if op == 0x12 || op == 0x13 {
			literalSites++
		}
		pc += stockS2aVerifyOpcodeWidth(op)
	}
	if parsed.cpCount != 277 || len(parsed.methods) != 3 || len(parsed.methods[1].code) != 793 || literalSites != 260 || literalSites+len(parsed.methods[2].literals) != 261 || len(parsed.methods[2].code) != 4 || parsed.methods[1].starts != nil || len(parsed.methods[1].literals) != 0 || parsed.methods[1].errorCode != 5 || parsed.methods[2].starts == nil || len(parsed.methods[2].literals) != 1 || !bytes.Contains(parsed.methods[2].code, []byte{0x13}) {
		t.Fatalf("wide parse cp=%d unusedSites=%d methods=%+v", parsed.cpCount, literalSites, parsed.methods)
	}
	page := stockS2aVerifyLoadPage(t)
	parser := stockS2aVerifyLoadArtifact(t, "S2aClassParser")
	module := stockS2aVerifyLoadArtifact(t, "S2aStepModule")
	coord := stockS2aVerifyLoadArtifact(t, "S2aCoordinator")
	e := stockS2aVerifyNewEnv(t)
	defer e.close()
	parserAt, _ := e.mustCreate(parser.init, stockS2aVerifyCreateGas)
	moduleAt, _ := e.mustCreate(module.init, stockS2aVerifyCreateGas)
	rawAt, pageHash, payloadHash, _ := stockS2aVerifyDeployPage(t, e, page, raw)
	id, metaAt, metaHash, declared, reg := stockS2aVerifyRegister(t, e, parser, parserAt, rawAt, pageHash, payloadHash)
	meta := e.state.StateDB.GetCode(metaAt)
	if declared != 3 || reg.result.UsedGas > stockS2aVerifyCreateGas || crypto.Keccak256Hash(meta) != metaHash || !bytes.Equal(meta[1:], stockS2aVerifyMetadataExpected(raw, rawAt, pageHash, payloadHash)) {
		t.Fatalf("wide metadata declared=%d bytes=%d payloadKeccak=%s classKeccak=%s", declared, len(meta), crypto.Keccak256Hash(raw), sha)
	}
	parserHash, moduleHash := crypto.Keccak256Hash(parser.runtime), crypto.Keccak256Hash(module.runtime)
	got := stockS2aVerifyRunEntry(t, e, coord, parserAt, parserHash, id, moduleAt, moduleHash, "loadWide", nil, 64)
	if got.Machine.Lifecycle != stockS2aVerifyReturned || got.Machine.Result != 123456789 || got.TotalSteps != 2 {
		t.Fatalf("loadWide=%+v", got)
	}
	stockS2aVerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, stockS2aVerifyClass{bytes: raw}, "populateIntegerPool", nil, "S2aMethodError(uint256,uint256)", 5, 1)
}

type stockS2aVerifyBytecodeCase struct {
	name     string
	class    stockS2aVerifyClass
	entry    string
	args     []int32
	code, pc uint64
}

func TestStockS2aVerifyNegativeCatalogueBranchesAndOperands(t *testing.T) {
	page := stockS2aVerifyLoadPage(t)
	parser := stockS2aVerifyLoadArtifact(t, "S2aClassParser")
	module := stockS2aVerifyLoadArtifact(t, "S2aStepModule")
	coord := stockS2aVerifyLoadArtifact(t, "S2aCoordinator")
	e := stockS2aVerifyNewEnv(t)
	defer e.close()
	parserAt, _ := e.mustCreate(parser.init, stockS2aVerifyCreateGas)
	moduleAt, _ := e.mustCreate(module.init, stockS2aVerifyCreateGas)
	parserHash, moduleHash := crypto.Keccak256Hash(parser.runtime), crypto.Keccak256Hash(module.runtime)
	b := []stockS2aVerifyBytecodeCase{
		{"B01-branch-no-operands", stockS2aVerifySimpleClass([]byte{0xa7}, 1, 0, "()I"), "entry", nil, 2, 0},
		{"B02-branch-one-operand", stockS2aVerifySimpleClass([]byte{0xa7, 0}, 1, 0, "()I"), "entry", nil, 2, 0},
		{"B03-min-s16-from-nonzero", stockS2aVerifySimpleClass([]byte{0, 0xa7, 0x80, 0}, 1, 0, "()I"), "entry", nil, 15, 1},
		{"B04-negative-one", stockS2aVerifySimpleClass([]byte{0xa7, 0xff, 0xff}, 1, 0, "()I"), "entry", nil, 15, 0},
		{"B06-target-first-operand", stockS2aVerifySimpleClass([]byte{0xa7, 0, 1}, 1, 0, "()I"), "entry", nil, 15, 0},
		{"B07-max-s16", stockS2aVerifySimpleClass([]byte{0xa7, 0x7f, 0xff}, 1, 0, "()I"), "entry", nil, 15, 0},
		{"B08-exact-negative-one", stockS2aVerifySimpleClass([]byte{0, 0, 0, 0xa7, 0xff, 0xfc}, 1, 0, "()I"), "entry", nil, 15, 3},
		{"B09-target-code-length", stockS2aVerifySimpleClass([]byte{0xa7, 0, 3}, 1, 0, "()I"), "entry", nil, 15, 0},
		{"B10-target-after-code", stockS2aVerifySimpleClass([]byte{0xa7, 0, 4}, 1, 0, "()I"), "entry", nil, 15, 0},
		{"B11-target-sipush-middle", stockS2aVerifySimpleClass([]byte{0xa7, 0, 4, 0x11, 0, 1, 0xac}, 1, 0, "()I"), "entry", nil, 15, 0},
		{"B12-target-iinc-operand", stockS2aVerifySimpleClass([]byte{0xa7, 0, 4, 0x84, 0, 1, 3, 0xac}, 1, 1, "()I"), "entry", nil, 15, 0},
		{"B13-unreachable-bad-target", stockS2aVerifySimpleClass([]byte{3, 0xac, 0xa7, 0, 1}, 1, 0, "()I"), "entry", nil, 15, 2},
		{"B14-unreachable-unsupported", stockS2aVerifySimpleClass([]byte{3, 0xac, 0xb1}, 1, 0, "()I"), "entry", nil, 6, 2},
	}
	for _, tc := range b {
		t.Run(tc.name, func(t *testing.T) {
			stockS2aVerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, tc.class, tc.entry, tc.args, "S2aBytecodeError(uint256,uint256)", tc.code, tc.pc)
		})
	}
	// B05: offset zero is valid and identical-PC progress is not rejected. The
	// coordinator emits lifecycle STEP_LIMIT at each committed exact cap.
	self := stockS2aVerifySimpleClass([]byte{0xa7, 0, 0}, 0, 0, "()I")
	for _, cap := range []uint64{1, 128, 4096} {
		t.Run(fmt.Sprintf("B05-zero-offset-cap-%d", cap), func(t *testing.T) {
			_, _, _, id, _, _, _ := stockS2aVerifyDeployRegistered(t, e, page, parser, parserAt, self.bytes)
			at, _ := stockS2aVerifyDeployCoordinator(t, e, coord, parserAt, parserHash, id, moduleAt, moduleHash, "entry", nil, cap)
			before := stockS2aVerifyCheckpointAt(t, e, coord, at)
			for before.Machine.Lifecycle == stockS2aVerifyRunnable {
				r := stockS2aVerifyResume(t, e, coord, at, before.Epoch, 128, 32, stockS2aVerifyCallGas)
				if r.result.Err != nil {
					t.Fatalf("same-PC progress failed: %v", r.result.Err)
				}
				after := stockS2aVerifyCheckpointAt(t, e, coord, at)
				if after.Epoch != before.Epoch+1 || after.TotalSteps <= before.TotalSteps || after.Machine.Pc != 0 {
					t.Fatalf("same-PC transition before=%+v after=%+v", before, after)
				}
				before = after
			}
			if before.TotalSteps != cap || before.Machine.Lifecycle != stockS2aVerifyStepLimit || before.Machine.Result != 0 {
				t.Fatalf("cap checkpoint=%+v", before)
			}
			failed := stockS2aVerifyResume(t, e, coord, at, before.Epoch, 1, 32, stockS2aVerifyCallGas)
			stockS2aVerifyAssertRevert(t, failed, "S2aControlError(uint256)", 1)
		})
	}
	o := []stockS2aVerifyBytecodeCase{
		{"O01-unary-underflow", stockS2aVerifySimpleClass([]byte{0x99, 0, 3, 3, 0xac}, 1, 0, "()I"), "entry", nil, 3, 0},
		{"O02-binary-zero-operands", stockS2aVerifySimpleClass([]byte{0x9f, 0, 3, 3, 0xac}, 2, 0, "()I"), "entry", nil, 3, 0},
		{"O03-binary-one-operand", stockS2aVerifySimpleClass([]byte{3, 0x9f, 0, 3, 3, 0xac}, 2, 0, "()I"), "entry", nil, 3, 1},
		{"O04-branch-path-capacity", stockS2aVerifySimpleClass([]byte{0x1a, 0x99, 0, 7, 3, 4, 0x60, 0xac, 3, 0xac}, 1, 1, "(I)I"), "entry", []int32{1}, 9, 5},
		{"O05-generic-local-range", stockS2aVerifySimpleClass([]byte{0x15, 1, 0xac}, 1, 1, "()I"), "entry", nil, 8, 0},
		{"O06-compact-local-range", stockS2aVerifySimpleClass([]byte{0x1b, 0xac}, 1, 1, "()I"), "entry", nil, 8, 0},
		{"O07-first-extra-local-uninitialized", stockS2aVerifySimpleClass([]byte{0x1b, 0xac}, 1, 2, "(I)I"), "entry", []int32{7}, 11, 0},
		{"O08-one-predecessor-initialized", stockS2aVerifySimpleClass([]byte{0x1a, 0x99, 0, 9, 4, 0x3c, 0xa7, 0, 4, 0, 0x1b, 0xac}, 1, 2, "(I)I"), "entry", []int32{0}, 11, 10},
		{"O09-join-stack-height", stockS2aVerifySimpleClass([]byte{0x1a, 0x99, 0, 8, 4, 0xa7, 0, 4, 0, 3, 0xac}, 2, 1, "(I)I"), "entry", []int32{1}, 5, 9},
		{"O10-fallthrough", stockS2aVerifySimpleClass([]byte{3}, 1, 0, "()I"), "entry", nil, 7, 0},
		{"O11-return-empty", stockS2aVerifySimpleClass([]byte{0xac}, 1, 0, "()I"), "entry", nil, 5, 0},
		{"O12-return-two", stockS2aVerifySimpleClass([]byte{3, 4, 0xac}, 2, 0, "()I"), "entry", nil, 5, 2},
		{"O13-idiv-zero-operands-hard-error", stockS2aVerifySimpleClass([]byte{0x6c, 0xac}, 2, 0, "()I"), "entry", nil, 3, 0},
		{"O14-irem-one-operand-hard-error", stockS2aVerifySimpleClass([]byte{3, 0x70, 0xac}, 2, 0, "()I"), "entry", nil, 3, 1},
		{"O15-i2b-underflow-hard-error", stockS2aVerifySimpleClass([]byte{0x91, 0xac}, 1, 0, "()I"), "entry", nil, 3, 0},
	}
	for _, tc := range o {
		t.Run(tc.name, func(t *testing.T) {
			stockS2aVerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, tc.class, tc.entry, tc.args, "S2aBytecodeError(uint256,uint256)", tc.code, tc.pc)
		})
	}
}

func TestStockS2aVerifySignedBranchesLocalsAndReturnPrecedence(t *testing.T) {
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
		{"signed", "(II)I", 0x0009, []byte{0x1a, 0x1b, 0xa2, 0, 5, 0x02, 0xac, 0x04, 0xac}, 2, 2, 1, 0},
		// Includes the frozen real backward edge 13 + (-11) = 2.
		{"loop", "(I)I", 0x0009, []byte{3, 0x3c, 0x1b, 0x1a, 0xa2, 0, 12, 0x84, 1, 1, 0, 0, 0, 0xa7, 0xff, 0xf5, 0x1b, 0xac}, 2, 2, 1, 0},
		{"locals6", "(IIII)I", 0x0009, []byte{0x1a, 0x1b, 0x60, 0x3b, 0x1c, 0x1d, 0x60, 0x36, 5, 0x1a, 0x15, 5, 0x60, 0xac}, 2, 6, 1, 0},
		{"three", "(III)I", 0x0009, []byte{0x1a, 0x1b, 0x60, 0x1c, 0x60, 0xac}, 2, 3, 1, 0},
		{"exact", "()I", 0x0009, []byte{4, 0xac}, 1, 0, 1, 0},
	}
	class := stockS2aVerifyBuildClass("S2aPositive", methods, 0)
	_, _, _, id, _, _, _ := stockS2aVerifyDeployRegistered(t, e, page, parser, parserAt, class.bytes)
	cases := []struct {
		name, entry string
		args        []int32
		want        int32
		steps, cap  uint64
	}{{"signed-min-max", "signed", []int32{math.MinInt32, math.MaxInt32}, -1, 5, 64}, {"signed-max-min", "signed", []int32{math.MaxInt32, math.MinInt32}, 1, 5, 64}, {"loop-backward", "loop", []int32{3}, 3, 31, 64}, {"locals6-minmax", "locals6", []int32{math.MinInt32, math.MaxInt32, -1, 1}, -1, 12, 64}, {"argc3-minmax", "three", []int32{math.MinInt32, math.MaxInt32, 1}, 0, 6, 64}, {"returned-wins-at-cap", "exact", nil, 1, 2, 2}}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			at, _ := stockS2aVerifyDeployCoordinator(t, e, coord, parserAt, parserHash, id, moduleAt, moduleHash, tc.entry, tc.args, tc.cap)
			var executed uint64
			for {
				c := stockS2aVerifyCheckpointAt(t, e, coord, at)
				if c.Machine.Lifecycle != 0 {
					if c.Machine.Lifecycle != stockS2aVerifyReturned || c.Machine.Result != tc.want || c.TotalSteps != tc.steps || executed != tc.steps {
						t.Fatalf("terminal=%+v executed=%d", c, executed)
					}
					break
				}
				r := stockS2aVerifyResume(t, e, coord, at, c.Epoch, 1, 32, stockS2aVerifyCallGas)
				if r.result.Err != nil {
					t.Fatal(r.result.Err)
				}
				executed++
			}
		})
	}
	// Arguments cover 0..4, MIN/MAX, and exactly local index 5. maxLocals below
	// argc is a recorded MethodError(5), while maxLocals=6 above is accepted.
	tooFew := stockS2aVerifyBuildClass("S2aTooFew", []stockS2aVerifyMethod{{"entry", "(IIII)I", 0x0009, []byte{0x1a, 0xac}, 1, 3, 1, 0}}, 0)
	stockS2aVerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, tooFew, "entry", []int32{1, 2, 3, 4}, "S2aMethodError(uint256,uint256)", 5, 1)
}

func stockS2aVerifyRunEntry(t *testing.T, e *stockS2aVerifyEnv, coord stockS2aVerifyArtifact, parserAt common.Address, parserHash, classID common.Hash, moduleAt common.Address, moduleHash common.Hash, entry string, args []int32, cap uint64) stockS2aVerifyCheckpoint {
	t.Helper()
	at, _ := stockS2aVerifyDeployCoordinator(t, e, coord, parserAt, parserHash, classID, moduleAt, moduleHash, entry, args, cap)
	for {
		before := stockS2aVerifyCheckpointAt(t, e, coord, at)
		if before.Machine.Lifecycle != stockS2aVerifyRunnable {
			return before
		}
		r := stockS2aVerifyResume(t, e, coord, at, before.Epoch, 128, 32, stockS2aVerifyCallGas)
		if r.coreErr != nil || r.result == nil || r.result.Failed() {
			t.Fatalf("%s%v resume: core=%v evm=%v data=%x", entry, args, r.coreErr, stockS2aVerifyResultErr(r.result), stockS2aVerifyResultData(r.result))
		}
	}
}

func TestStockS2aVerifyIntegerCompletionMatrices(t *testing.T) {
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
	class := stockS2aVerifyBuildClass("S2aIntegerCompletion", methods, 0)
	_, _, _, id, _, _, _ := stockS2aVerifyDeployRegistered(t, e, page, parser, parserAt, class.bytes)
	check := func(name string, args []int32, want int32, steps uint64) {
		t.Helper()
		got := stockS2aVerifyRunEntry(t, e, coord, parserAt, parserHash, id, moduleAt, moduleHash, name, args, 64)
		if got.Machine.Lifecycle != stockS2aVerifyReturned || got.Machine.Result != want || got.TotalSteps != steps || got.Machine.Sp != 0 || got.Machine.JavaFaultKind != 0 || got.Machine.FaultPC != 0 {
			t.Fatalf("%s%v=%+v want=%d/%d", name, args, got, want, steps)
		}
	}
	pairs := [][2]int32{{math.MinInt32, -1}, {math.MinInt32, 1}, {math.MinInt32, 3}, {-17, -5}, {-17, 5}, {-1, -1}, {0, -7}, {1, -1}, {17, -5}, {17, 5}, {math.MaxInt32, -1}, {math.MaxInt32, 31}}
	for _, p := range pairs {
		a, b := p[0], p[1]
		var q, r int32
		if a == math.MinInt32 && b == -1 {
			q, r = math.MinInt32, 0
		} else {
			q, r = int32(int64(a)/int64(b)), int32(int64(a)%int64(b))
		}
		check("div", []int32{a, b}, q, 4)
		check("rem", []int32{a, b}, r, 4)
	}
	for _, distance := range []int32{-1, math.MinInt32, math.MaxInt32, 0, 31, 32, 33, 63} {
		s := uint32(distance) & 31
		for _, value := range []int32{math.MinInt32, -1, 0x40000001} {
			check("shl", []int32{value, distance}, int32(uint32(value)<<s), 4)
			check("shr", []int32{value, distance}, value>>s, 4)
			check("ushr", []int32{value, distance}, int32(uint32(value)>>s), 4)
		}
	}
	for _, p := range [][2]int32{{math.MinInt32, -1}, {0x40000001, -1431655766}, {-1, 0}, {0x12345678, 0x0f0f0f0f}} {
		check("and", []int32{p[0], p[1]}, p[0]&p[1], 4)
		check("or", []int32{p[0], p[1]}, p[0]|p[1], 4)
		check("xor", []int32{p[0], p[1]}, p[0]^p[1], 4)
	}
	for _, value := range []int32{math.MinInt32, -32769, -32768, -129, -128, -1, 0, 127, 128, 255, 32767, 32768, math.MaxInt32} {
		check("i2b", []int32{value}, int32(int8(value)), 3)
		check("i2c", []int32{value}, int32(uint16(value)), 3)
		check("i2s", []int32{value}, int32(int16(value)), 3)
	}
}

func TestStockS2aVerifyArithmeticFaultStateAndCapPrecedence(t *testing.T) {
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
		{"prefix", "(II)I", 9, []byte{0x1a, 0x04, 0x60, 0x3d, 0x1a, 0x1b, 0x6c, 0x3d, 0x1c, 0xac}, 2, 3, 1, 0},
	}
	class := stockS2aVerifyBuildClass("S2aFaults", methods, 0)
	_, _, _, id, _, _, _ := stockS2aVerifyDeployRegistered(t, e, page, parser, parserAt, class.bytes)
	for _, tc := range []struct {
		entry string
		pc    uint32
		steps uint64
	}{{"div", 2, 3}, {"rem", 2, 3}, {"prefix", 6, 7}} {
		t.Run(tc.entry, func(t *testing.T) {
			got := stockS2aVerifyRunEntry(t, e, coord, parserAt, parserHash, id, moduleAt, moduleHash, tc.entry, []int32{-17, 0}, 64)
			if got.Machine.Lifecycle != stockS2aVerifyJavaFault || got.Machine.JavaFaultKind != stockS2aVerifyArithmeticFault || got.Machine.FaultPC != tc.pc || got.Machine.Pc != tc.pc || got.Machine.Result != 0 || got.Machine.Sp != 2 || got.TotalSteps != tc.steps || got.Epoch != 1 {
				t.Fatalf("fault checkpoint=%+v", got)
			}
			if got.Machine.Stack[0].Cmp(stockS2aVerifyTagged(0xffffffef)) != 0 || got.Machine.Stack[1].Cmp(stockS2aVerifyTagged(0)) != 0 || got.Machine.Locals[0].Cmp(stockS2aVerifyTagged(0xffffffef)) != 0 || got.Machine.Locals[1].Cmp(stockS2aVerifyTagged(0)) != 0 {
				t.Fatalf("pre-fault operands/locals changed: %+v", got.Machine)
			}
			if tc.entry == "prefix" && got.Machine.Locals[2].Cmp(stockS2aVerifyTagged(0xfffffff0)) != 0 {
				t.Fatal("successful prefix local did not commit, or following istore executed")
			}
		})
	}
	beforeFault := stockS2aVerifyRunEntry(t, e, coord, parserAt, parserHash, id, moduleAt, moduleHash, "div", []int32{7, 0}, 2)
	if beforeFault.Machine.Lifecycle != stockS2aVerifyStepLimit || beforeFault.TotalSteps != 2 || beforeFault.Machine.Pc != 2 || beforeFault.Machine.JavaFaultKind != 0 || beforeFault.Machine.FaultPC != 0 {
		t.Fatalf("cap before fault predicted exception: %+v", beforeFault)
	}
	atFault := stockS2aVerifyRunEntry(t, e, coord, parserAt, parserHash, id, moduleAt, moduleHash, "div", []int32{7, 0}, 3)
	if atFault.Machine.Lifecycle != stockS2aVerifyJavaFault || atFault.TotalSteps != 3 {
		t.Fatalf("fault must win at exact cap: %+v", atFault)
	}
	returned := stockS2aVerifyRunEntry(t, e, coord, parserAt, parserHash, id, moduleAt, moduleHash, "div", []int32{7, 1}, 4)
	if returned.Machine.Lifecycle != stockS2aVerifyReturned || returned.Machine.Result != 7 || returned.TotalSteps != 4 {
		t.Fatalf("return must win at exact cap: %+v", returned)
	}
}

func stockS2aVerifyProgramCall(t *testing.T, e *stockS2aVerifyEnv, module stockS2aVerifyArtifact, moduleAt common.Address, p stockS2aVerifyProgram, m stockS2aVerifyMachine, budget uint16, gas uint64) stockS2aVerifyTx {
	t.Helper()
	return e.apply(&moduleAt, stockS2aVerifyCallData(t, module, "step", p, m, budget), gas)
}
func stockS2aVerifyProgramContext(t *testing.T, e *stockS2aVerifyEnv, coord stockS2aVerifyArtifact, at common.Address) stockS2aVerifyProgram {
	t.Helper()
	r := e.mustCall(at, stockS2aVerifyCallData(t, coord, "programContext"), stockS2aVerifyCallGas)
	return stockS2aVerifyProgramFrom(stockS2aVerifyUnpack(t, coord, "programContext", r.result.ReturnData)[0])
}
func stockS2aVerifyFakeStepRuntime(machine stockS2aVerifyMachine, executed uint16, loopUnlessBudgetOne bool) []byte {
	var out []byte
	if loopUnlessBudgetOne { // beforeState.pc is calldata word 10 after the selector.
		out = append(out, 0x61, 0x01, 0x44, 0x35, 0x15, 0x61, 0, 0, 0x57)
		loop := len(out)
		out = append(out, 0x5b, 0x61, byte(loop>>8), byte(loop), 0x56)
		dest := len(out)
		out[6], out[7] = byte(dest>>8), byte(dest)
		out = append(out, 0x5b)
	}
	words := []*big.Int{new(big.Int).SetUint64(uint64(machine.Pc)), new(big.Int).SetUint64(uint64(machine.Sp)), new(big.Int).SetUint64(uint64(machine.Initialized)), new(big.Int).SetUint64(uint64(machine.Lifecycle))}
	words = append(words, machine.Stack[:]...)
	words = append(words, machine.Locals[:]...)
	if machine.Result < 0 {
		words = append(words, new(big.Int).Add(new(big.Int).Lsh(big.NewInt(1), 256), big.NewInt(int64(machine.Result))))
	} else {
		words = append(words, big.NewInt(int64(machine.Result)))
	}
	words = append(words, new(big.Int).SetUint64(uint64(machine.JavaFaultKind)), new(big.Int).SetUint64(uint64(machine.FaultPC)), new(big.Int).SetUint64(uint64(executed)))
	for i, w := range words {
		var word [32]byte
		w.FillBytes(word[:])
		out = append(out, 0x7f)
		out = append(out, word[:]...)
		offset := i * 32
		if offset <= 255 {
			out = append(out, 0x60, byte(offset))
		} else {
			out = append(out, 0x61, byte(offset>>8), byte(offset))
		}
		out = append(out, 0x52)
	}
	out = append(out, 0x61, byte(len(words)*32>>8), byte(len(words)*32), 0x60, 0, 0xf3)
	return out
}

func stockS2aVerifyOOGAfterCallRuntime(target common.Address, calldata []byte) []byte {
	if len(calldata) > math.MaxUint16 {
		panic("wrapper calldata too large")
	}
	// CODECOPY fixed resume calldata, CALL the coordinator to a successful
	// commit, then loop until the outer signed transaction runs out of gas.
	out := []byte{0x61, byte(len(calldata) >> 8), byte(len(calldata)), 0x61, 0, 0, 0x5f, 0x39,
		0x5f, 0x5f, 0x61, byte(len(calldata) >> 8), byte(len(calldata)), 0x5f, 0x5f, 0x73}
	out = append(out, target[:]...)
	out = append(out, 0x5a, 0xf1, 0x50)
	loop := len(out)
	out = append(out, 0x5b, 0x61, byte(loop>>8), byte(loop), 0x56)
	offset := len(out)
	out[4], out[5] = byte(offset>>8), byte(offset)
	return append(out, calldata...)
}

func TestStockS2aVerifyNegativeCatalogueCommitmentsAtomicityAndGas(t *testing.T) {
	page := stockS2aVerifyLoadPage(t)
	parser := stockS2aVerifyLoadArtifact(t, "S2aClassParser")
	module := stockS2aVerifyLoadArtifact(t, "S2aStepModule")
	coord := stockS2aVerifyLoadArtifact(t, "S2aCoordinator")
	metadata := stockS2aVerifyLoadArtifact(t, "S2aMetadataPage")
	e := stockS2aVerifyNewEnv(t)
	defer e.close()
	parserAt, _ := e.mustCreate(parser.init, stockS2aVerifyCreateGas)
	moduleAt, _ := e.mustCreate(module.init, stockS2aVerifyCreateGas)
	parserHash, moduleHash := crypto.Keccak256Hash(parser.runtime), crypto.Keccak256Hash(module.runtime)
	class := stockS2aVerifySimpleClass([]byte{0x1a, 4, 0x60, 0x3b, 0x1a, 0xac}, 2, 1, "(I)I")
	rawAt, pageHash, payloadHash, id, metadataAt, metadataHash, _ := stockS2aVerifyDeployRegistered(t, e, page, parser, parserAt, class.bytes)
	t.Run("C01-wrong-raw-page-payload-hash", func(t *testing.T) {
		bad := pageHash
		bad[0] ^= 1
		r := e.apply(&parserAt, stockS2aVerifyCallData(t, parser, "registerClass", rawAt, bad, payloadHash), stockS2aVerifyCallGas)
		stockS2aVerifyAssertRevert(t, r, "StockPageError(uint256)", 3)
		bad = payloadHash
		bad[0] ^= 1
		r = e.apply(&parserAt, stockS2aVerifyCallData(t, parser, "registerClass", rawAt, pageHash, bad), stockS2aVerifyCallGas)
		stockS2aVerifyAssertRevert(t, r, "StockPageError(uint256)", 4)
	})
	baseAt, _ := stockS2aVerifyDeployCoordinator(t, e, coord, parserAt, parserHash, id, moduleAt, moduleHash, "entry", []int32{7}, 64)
	program := stockS2aVerifyProgramContext(t, e, coord, baseAt)
	machine := stockS2aVerifyCheckpointAt(t, e, coord, baseAt).Machine
	directControl2 := func(t *testing.T, p stockS2aVerifyProgram) {
		r := stockS2aVerifyProgramCall(t, e, module, moduleAt, p, machine, 1, stockS2aVerifyCallGas)
		stockS2aVerifyAssertRevert(t, r, "S2aControlError(uint256)", 2)
	}
	t.Run("C02-wrong-EVM-metadata-hash-and-fake-page", func(t *testing.T) {
		fakePayload := append([]byte(nil), e.state.StateDB.GetCode(metadataAt)[1:]...)
		fakePayload[0] ^= 1
		fakeAt, _ := e.mustCreate(stockS2aVerifyConstructor(t, metadata, fakePayload), stockS2aVerifyCreateGas)
		p := program
		p.MetadataPage = fakeAt
		p.MetadataHash = [32]byte(crypto.Keccak256Hash(e.state.StateDB.GetCode(fakeAt)))
		directControl2(t, p)
	})
	t.Run("C02b-unregistered-parser-issuer", func(t *testing.T) {
		otherParser, _ := e.mustCreate(parser.init, stockS2aVerifyCreateGas)
		p := program
		p.Parser = otherParser
		// Identical code hash is only a component commitment. The second parser
		// did not issue this class record and must not attest the metadata.
		directControl2(t, p)
	})
	t.Run("C03-wrong-parser-module-hash", func(t *testing.T) {
		for _, which := range []string{"parser", "module"} {
			bad := parserHash
			if which == "module" {
				bad = moduleHash
			}
			bad[0] ^= 1
			nonce := e.state.StateDB.GetNonce(e.sender)
			var init []byte
			if which == "parser" {
				init = stockS2aVerifyConstructor(t, coord, parserAt, bad, id, moduleAt, moduleHash, []byte("entry"), []int32{7}, uint64(64))
			} else {
				init = stockS2aVerifyConstructor(t, coord, parserAt, parserHash, id, moduleAt, bad, []byte("entry"), []int32{7}, uint64(64))
			}
			r := e.apply(nil, init, stockS2aVerifyCreateGas)
			stockS2aVerifyAssertRevert(t, r, "S2aControlError(uint256)", 2)
			if len(e.state.StateDB.GetCode(crypto.CreateAddress(e.sender, nonce))) != 0 {
				t.Fatal("hash mismatch left coordinator")
			}
		}
	})
	t.Run("C04-wrong-declared-class-component", func(t *testing.T) { p := program; p.ClassId[0] ^= 1; directControl2(t, p) })
	t.Run("C05-missing-wrong-ambiguous-method", func(t *testing.T) {
		stockS2aVerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, class, "wrong", []int32{7}, "S2aMethodError(uint256,uint256)", 1, stockS2aVerifyMaxUint256)
		amb := stockS2aVerifyBuildClass("S2aC05", []stockS2aVerifyMethod{{"same", "()I", 9, []byte{3, 0xac}, 1, 0, 1, 0}, {"same", "(I)I", 9, []byte{0x1a, 0xac}, 1, 1, 1, 0}}, 0)
		stockS2aVerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, amb, "same", nil, "S2aMethodError(uint256,uint256)", 2, 2)
	})
	t.Run("C06-descriptor-argc-mismatch", func(t *testing.T) {
		stockS2aVerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, class, "entry", nil, "S2aMethodError(uint256,uint256)", 7, 1)
	})
	t.Run("C07-one-nonzero-argument-bit-changes-root", func(t *testing.T) {
		otherAt, _ := stockS2aVerifyDeployCoordinator(t, e, coord, parserAt, parserHash, id, moduleAt, moduleHash, "entry", []int32{6}, 64)
		other := stockS2aVerifyCheckpointAt(t, e, coord, otherAt)
		base := stockS2aVerifyCheckpointAt(t, e, coord, baseAt)
		if other.ProgramID != base.ProgramID || other.InputRoot == base.InputRoot || stockS2aVerifyProgramContext(t, e, coord, otherAt).ProgramId != program.ProgramId {
			t.Fatal("argument mutation was not isolated to args/input commitment")
		}
		if other.Machine.Locals[0].Cmp(stockS2aVerifyTagged(6)) != 0 || base.Machine.Locals[0].Cmp(stockS2aVerifyTagged(7)) != 0 {
			t.Fatal("committed argument local mismatch")
		}
	})
	t.Run("C08-wrong-schema-program-root", func(t *testing.T) { p := program; p.ProgramId[0] ^= 1; directControl2(t, p) })
	t.Run("C09-stale-epoch-before-first-resume", func(t *testing.T) {
		before := stockS2aVerifyCheckpointAt(t, e, coord, baseAt)
		r := stockS2aVerifyResume(t, e, coord, baseAt, 1, 1, 32, stockS2aVerifyCallGas)
		stockS2aVerifyAssertRevert(t, r, "S2aControlError(uint256)", 3)
		stockS2aVerifyAssertRollback(t, e, coord, baseAt, before, r)
	})
	t.Run("C12-dirty-cap-first-argument-checkpoint", func(t *testing.T) {
		before := stockS2aVerifyCheckpointAt(t, e, coord, baseAt)
		r := stockS2aVerifyResume(t, e, coord, baseAt, 0, 3, 1, stockS2aVerifyCallGas)
		stockS2aVerifyAssertRevert(t, r, "S2aControlError(uint256)", 6)
		stockS2aVerifyAssertRollback(t, e, coord, baseAt, before, r)
	})
	t.Run("C18-reserve-before-progress", func(t *testing.T) {
		before := stockS2aVerifyCheckpointAt(t, e, coord, baseAt)
		r := stockS2aVerifyResume(t, e, coord, baseAt, 0, 3, 32, stockS2aVerifyReserve-50_000)
		stockS2aVerifyAssertRevert(t, r, "S2aControlError(uint256)", 5)
		stockS2aVerifyAssertRollback(t, e, coord, baseAt, before, r)
	})
	first := stockS2aVerifyResume(t, e, coord, baseAt, 0, 3, 32, stockS2aVerifyCallGas)
	if first.result.Err != nil {
		t.Fatal(first.result.Err)
	}
	progress := stockS2aVerifyCheckpointAt(t, e, coord, baseAt)
	if progress.Epoch != 1 || progress.TotalSteps != 3 || progress.Machine.Stack[0].Cmp(stockS2aVerifyTagged(8)) != 0 || progress.Machine.Locals[0].Cmp(stockS2aVerifyTagged(7)) != 0 {
		t.Fatalf("nonzero progress=%+v", progress)
	}
	for _, tc := range []struct {
		name  string
		epoch uint64
		dirty uint8
		gas   uint64
		code  uint64
	}{{"C10-stale-epoch-after-progress", 0, 32, stockS2aVerifyCallGas, 3}, {"C13-dirty-cap-after-progress", 1, 1, stockS2aVerifyCallGas, 6}, {"C18-reserve-after-progress", 1, 32, stockS2aVerifyReserve - 50_000, 5}} {
		t.Run(tc.name, func(t *testing.T) {
			before := stockS2aVerifyCheckpointAt(t, e, coord, baseAt)
			r := stockS2aVerifyResume(t, e, coord, baseAt, tc.epoch, 2, tc.dirty, tc.gas)
			stockS2aVerifyAssertRevert(t, r, "S2aControlError(uint256)", tc.code)
			stockS2aVerifyAssertRollback(t, e, coord, baseAt, before, r)
		})
	}
	// C11 uses a real valid goto 0 checkpoint; stale epoch remains stale even
	// though PC and all machine words are identical.
	t.Run("C11-stale-after-legitimate-same-PC", func(t *testing.T) {
		self := stockS2aVerifySimpleClass([]byte{0xa7, 0, 0}, 0, 0, "()I")
		_, _, _, sid, _, _, _ := stockS2aVerifyDeployRegistered(t, e, page, parser, parserAt, self.bytes)
		at, _ := stockS2aVerifyDeployCoordinator(t, e, coord, parserAt, parserHash, sid, moduleAt, moduleHash, "entry", nil, 128)
		ok := stockS2aVerifyResume(t, e, coord, at, 0, 16, 32, stockS2aVerifyCallGas)
		if ok.result.Err != nil {
			t.Fatal(ok.result.Err)
		}
		before := stockS2aVerifyCheckpointAt(t, e, coord, at)
		r := stockS2aVerifyResume(t, e, coord, at, 0, 16, 32, stockS2aVerifyCallGas)
		stockS2aVerifyAssertRevert(t, r, "S2aControlError(uint256)", 3)
		stockS2aVerifyAssertRollback(t, e, coord, at, before, r)
	})
	t.Run("C14-dirty-cap-terminal-return", func(t *testing.T) {
		terminal := stockS2aVerifySimpleClass([]byte{0x1a, 0xac}, 1, 1, "(I)I")
		_, _, _, tid, _, _, _ := stockS2aVerifyDeployRegistered(t, e, page, parser, parserAt, terminal.bytes)
		at, _ := stockS2aVerifyDeployCoordinator(t, e, coord, parserAt, parserHash, tid, moduleAt, moduleHash, "entry", []int32{9}, 2)
		before := stockS2aVerifyCheckpointAt(t, e, coord, at)
		r := stockS2aVerifyResume(t, e, coord, at, 0, 2, 1, stockS2aVerifyCallGas)
		stockS2aVerifyAssertRevert(t, r, "S2aControlError(uint256)", 6)
		stockS2aVerifyAssertRollback(t, e, coord, at, before, r)
	})
	t.Run("C15-parser-OOG-atomic-registry-and-code", func(t *testing.T) {
		fresh := stockS2aVerifySimpleClass([]byte{3, 0xac}, 1, 0, "()I")
		pa, ph, pvh, _ := stockS2aVerifyDeployPage(t, e, page, fresh.bytes)
		expectedMeta := append([]byte{0}, stockS2aVerifyMetadataExpected(fresh.bytes, pa, ph, pvh)...)
		expectedID := stockS2aVerifyClassID(t, parserHash, pa, ph, pvh, crypto.Keccak256Hash(expectedMeta))
		internal := crypto.CreateAddress(parserAt, e.state.StateDB.GetNonce(parserAt))
		nonce := e.state.StateDB.GetNonce(e.sender)
		balance := e.state.StateDB.GetBalance(e.sender).ToBig()
		r := e.apply(&parserAt, stockS2aVerifyCallData(t, parser, "registerClass", pa, ph, pvh), 150_000)
		if r.coreErr != nil || r.result == nil || !errors.Is(r.result.Err, vm.ErrOutOfGas) || len(r.result.ReturnData) != 0 {
			t.Fatalf("registration OOG identity core=%v evm=%v data=%x", r.coreErr, stockS2aVerifyResultErr(r.result), stockS2aVerifyResultData(r.result))
		}
		if e.state.StateDB.GetNonce(e.sender) != nonce+1 || e.state.StateDB.GetBalance(e.sender).ToBig().Cmp(balance) >= 0 {
			t.Fatal("failed registration sender effects")
		}
		if at, h := stockS2aVerifyClassRecord(t, e, parser, parserAt, expectedID); at != (common.Address{}) || h != (common.Hash{}) {
			t.Fatal("OOG registration left registry")
		}
		if len(e.state.StateDB.GetCode(internal)) != 0 {
			t.Fatal("OOG registration left metadata code")
		}
	})
	// A fake module is a normally deployed configuration commitment, never an
	// attested artifact. It can test response validation and nested OOG safely.
	fakeAfter := stockS2aVerifyZeroMachine()
	fakeAfter.Pc = 1
	fakeAfter.Sp = 1
	fakeAfter.Initialized = 1
	fakeAfter.Stack[0] = stockS2aVerifyTagged(7)
	fakeAfter.Locals[0] = stockS2aVerifyTagged(7)
	fakeCode := stockS2aVerifyFakeStepRuntime(fakeAfter, 1, true)
	fakeAt, _ := stockS2aVerifyDeployRaw(t, e, fakeCode, stockS2aVerifyCreateGas)
	fakeHash := crypto.Keccak256Hash(fakeCode)
	fakeCoord, _ := stockS2aVerifyDeployCoordinator(t, e, coord, parserAt, parserHash, id, fakeAt, fakeHash, "entry", []int32{7}, 64)
	ok := stockS2aVerifyResume(t, e, coord, fakeCoord, 0, 1, 32, stockS2aVerifyCallGas)
	if ok.result.Err != nil {
		t.Fatalf("fake progress setup: %v %x", ok.result.Err, ok.result.ReturnData)
	}
	t.Run("C16-module-OOG-after-progress", func(t *testing.T) {
		before := stockS2aVerifyCheckpointAt(t, e, coord, fakeCoord)
		r := stockS2aVerifyResume(t, e, coord, fakeCoord, 1, 2, 32, stockS2aVerifyCallGas)
		if r.coreErr != nil || r.result == nil || !errors.Is(r.result.Err, vm.ErrExecutionReverted) || len(r.result.ReturnData) != 0 {
			t.Fatalf("nested OOG identity core=%v evm=%v data=%x", r.coreErr, stockS2aVerifyResultErr(r.result), stockS2aVerifyResultData(r.result))
		}
		stockS2aVerifyAssertRollback(t, e, coord, fakeCoord, before, r)
	})
	t.Run("C17-transaction-OOG-during-commit-after-progress", func(t *testing.T) {
		before := stockS2aVerifyCheckpointAt(t, e, coord, baseAt)
		resumeData := stockS2aVerifyCallData(t, coord, "resume", before.Epoch, uint16(3), uint8(32))
		wrapperCode := stockS2aVerifyOOGAfterCallRuntime(baseAt, resumeData)
		wrapper, _ := stockS2aVerifyDeployRaw(t, e, wrapperCode, stockS2aVerifyCreateGas)
		r := e.apply(&wrapper, nil, stockS2aVerifyCallGas)
		if r.coreErr != nil || r.result == nil || !errors.Is(r.result.Err, vm.ErrOutOfGas) || len(r.result.ReturnData) != 0 {
			t.Fatalf("post-commit transaction OOG core=%v evm=%v data=%x", r.coreErr, stockS2aVerifyResultErr(r.result), stockS2aVerifyResultData(r.result))
		}
		stockS2aVerifyAssertRollback(t, e, coord, baseAt, before, r)
	})
	finalTx := stockS2aVerifyResume(t, e, coord, baseAt, progress.Epoch, 128, 32, stockS2aVerifyCallGas)
	if finalTx.result.Err != nil {
		t.Fatal(finalTx.result.Err)
	}
	final := stockS2aVerifyCheckpointAt(t, e, coord, baseAt)
	if final.Machine.Lifecycle != stockS2aVerifyReturned || final.Machine.Result != 8 {
		t.Fatalf("final=%+v", final)
	}
	t.Run("C19-resume-after-terminal", func(t *testing.T) {
		r := stockS2aVerifyResume(t, e, coord, baseAt, final.Epoch, 1, 32, stockS2aVerifyCallGas)
		stockS2aVerifyAssertRevert(t, r, "S2aControlError(uint256)", 1)
		stockS2aVerifyAssertRollback(t, e, coord, baseAt, final, r)
	})
	t.Run("C20-exact-cap-is-success-STEP_LIMIT-not-Java", func(t *testing.T) {
		self := stockS2aVerifySimpleClass([]byte{0xa7, 0, 0}, 0, 0, "()I")
		_, _, _, sid, _, _, _ := stockS2aVerifyDeployRegistered(t, e, page, parser, parserAt, self.bytes)
		at, _ := stockS2aVerifyDeployCoordinator(t, e, coord, parserAt, parserHash, sid, moduleAt, moduleHash, "entry", nil, 1)
		r := stockS2aVerifyResume(t, e, coord, at, 0, 128, 32, stockS2aVerifyCallGas)
		if r.result.Err != nil {
			t.Fatal(r.result.Err)
		}
		c := stockS2aVerifyCheckpointAt(t, e, coord, at)
		if c.Machine.Lifecycle != stockS2aVerifyStepLimit || c.TotalSteps != 1 || c.Machine.Result != 0 {
			t.Fatalf("step-limit checkpoint=%+v", c)
		}
	})
	// Every logical machine word changed in this conservative synthetic bound;
	// on-chain calls accept 32 while exact reports never exceed 26.
	a := stockS2aVerifyZeroMachine()
	b := stockS2aVerifyCloneMachine(a)
	b.Pc = 1
	b.Sp = 8
	b.Initialized = 0xff
	b.Lifecycle = stockS2aVerifyReturned
	b.Result = 1
	b.JavaFaultKind = 1
	b.FaultPC = 1
	for i := range b.Stack {
		b.Stack[i] = stockS2aVerifyTagged(uint32(i + 1))
		b.Locals[i] = stockS2aVerifyTagged(uint32(i + 9))
	}
	if got := stockS2aVerifyDirty(a, b); got != 26 || got > 32 {
		t.Fatalf("all-dirty conservative count=%d", got)
	}
	_ = metadataHash
}

type stockS2aVerifyReplayRecord struct {
	hashes        []common.Hash
	gas           []uint64
	outputs, logs [][]byte
	addresses     []common.Address
	codeHashes    []common.Hash
	checkpoint    stockS2aVerifyCheckpoint
	root          common.Hash
}

func stockS2aVerifyReplay(t *testing.T) stockS2aVerifyReplayRecord {
	t.Helper()
	page := stockS2aVerifyLoadPage(t)
	parser := stockS2aVerifyLoadArtifact(t, "S2aClassParser")
	module := stockS2aVerifyLoadArtifact(t, "S2aStepModule")
	coord := stockS2aVerifyLoadArtifact(t, "S2aCoordinator")
	e := stockS2aVerifyNewEnv(t)
	defer e.close()
	var rec stockS2aVerifyReplayRecord
	capture := func(r stockS2aVerifyTx) {
		rec.hashes = append(rec.hashes, r.tx.Hash())
		rec.gas = append(rec.gas, r.result.UsedGas)
		rec.outputs = append(rec.outputs, append([]byte(nil), r.result.ReturnData...))
		var enc []byte
		for _, l := range r.logs {
			enc = append(enc, l.Address[:]...)
			for _, topic := range l.Topics {
				enc = append(enc, topic[:]...)
			}
			enc = append(enc, l.Data...)
		}
		rec.logs = append(rec.logs, enc)
	}
	parserAt, tx := e.mustCreate(parser.init, stockS2aVerifyCreateGas)
	capture(tx)
	moduleAt, tx := e.mustCreate(module.init, stockS2aVerifyCreateGas)
	capture(tx)
	class := stockS2aVerifySimpleClass([]byte{0x1a, 4, 0x60, 0x3b, 0x1a, 0xac}, 2, 1, "(I)I")
	rawAt, ph, pvh, pageTx := stockS2aVerifyDeployPage(t, e, page, class.bytes)
	capture(pageTx)
	id, metaAt, _, _, reg := stockS2aVerifyRegister(t, e, parser, parserAt, rawAt, ph, pvh)
	capture(reg)
	at, create := stockS2aVerifyDeployCoordinator(t, e, coord, parserAt, crypto.Keccak256Hash(parser.runtime), id, moduleAt, crypto.Keccak256Hash(module.runtime), "entry", []int32{41}, 64)
	capture(create)
	for epoch := uint64(0); epoch < 2; epoch++ {
		r := stockS2aVerifyResume(t, e, coord, at, epoch, 3, 32, stockS2aVerifyCallGas)
		if r.result.Err != nil {
			t.Fatal(r.result.Err)
		}
		capture(r)
	}
	rec.checkpoint = stockS2aVerifyCheckpointAt(t, e, coord, at)
	if rec.checkpoint.Machine.Lifecycle != stockS2aVerifyReturned || rec.checkpoint.Machine.Result != 42 || rec.checkpoint.TotalSteps != 6 {
		t.Fatalf("replay terminal=%+v", rec.checkpoint)
	}
	rec.addresses = []common.Address{parserAt, moduleAt, rawAt, metaAt, at}
	for _, address := range rec.addresses {
		rec.codeHashes = append(rec.codeHashes, crypto.Keccak256Hash(e.state.StateDB.GetCode(address)))
	}
	rec.root = e.state.StateDB.IntermediateRoot(true)
	return rec
}
func TestStockS2aVerifyDeterministicSignedApplyMessageReplay(t *testing.T) {
	a, b := stockS2aVerifyReplay(t), stockS2aVerifyReplay(t)
	if !reflect.DeepEqual(a, b) {
		t.Fatalf("identical explicit-context replay differs\nA=%+v\nB=%+v", a, b)
	}
	var gas uint64
	for _, g := range a.gas {
		gas += g
	}
	if len(a.hashes) != 7 || len(a.addresses) != 5 || gas > 30_000_000 {
		t.Fatalf("replay evidence tx=%d addresses=%d aggregateGas=%d", len(a.hashes), len(a.addresses), gas)
	}
	t.Logf("signed replay txHashes=%v addresses=%v gas=%v aggregate=%d codeHashes=%v checkpointDigest=%s stateRoot=%s", a.hashes, a.addresses, a.gas, gas, a.codeHashes, a.checkpoint.Digest, a.root)
}

func TestStockS2aVerifyMalformedIncomingAndModuleFaultResponses(t *testing.T) {
	page := stockS2aVerifyLoadPage(t)
	parser := stockS2aVerifyLoadArtifact(t, "S2aClassParser")
	module := stockS2aVerifyLoadArtifact(t, "S2aStepModule")
	coord := stockS2aVerifyLoadArtifact(t, "S2aCoordinator")
	e := stockS2aVerifyNewEnv(t)
	defer e.close()
	parserAt, _ := e.mustCreate(parser.init, stockS2aVerifyCreateGas)
	moduleAt, _ := e.mustCreate(module.init, stockS2aVerifyCreateGas)
	class := stockS2aVerifySimpleClass([]byte{0x1a, 0x1b, 0x6c, 0xac}, 2, 2, "(II)I")
	_, _, _, id, _, _, _ := stockS2aVerifyDeployRegistered(t, e, page, parser, parserAt, class.bytes)
	parserHash := crypto.Keccak256Hash(parser.runtime)
	actual, _ := stockS2aVerifyDeployCoordinator(t, e, coord, parserAt, parserHash, id, moduleAt, crypto.Keccak256Hash(module.runtime), "entry", []int32{7, 0}, 64)
	program := stockS2aVerifyProgramContext(t, e, coord, actual)
	initial := stockS2aVerifyCheckpointAt(t, e, coord, actual).Machine
	incoming := []struct {
		name string
		edit func(*stockS2aVerifyMachine)
	}{
		{"fault-kind-outside-fault", func(m *stockS2aVerifyMachine) { m.JavaFaultKind = 1 }},
		{"fault-pc-outside-fault", func(m *stockS2aVerifyMachine) { m.FaultPC = 2 }},
		{"result-outside-return", func(m *stockS2aVerifyMachine) { m.Result = 1 }},
		{"inactive-stack-cell", func(m *stockS2aVerifyMachine) { m.Stack[7] = stockS2aVerifyTagged(1) }},
		{"raw-active-tag", func(m *stockS2aVerifyMachine) { m.Sp = 1; m.Stack[0] = big.NewInt(7) }},
		{"bad-initialization-mask", func(m *stockS2aVerifyMachine) { m.Initialized = 0xff }},
	}
	for _, tc := range incoming {
		t.Run("incoming/"+tc.name, func(t *testing.T) {
			m := stockS2aVerifyCloneMachine(initial)
			tc.edit(&m)
			r := stockS2aVerifyProgramCall(t, e, module, moduleAt, program, m, 1, stockS2aVerifyCallGas)
			stockS2aVerifyAssertRevert(t, r, "S2aBytecodeError(uint256,uint256)", 14, 0)
		})
	}
	preFault := stockS2aVerifyCloneMachine(initial)
	preFault.Pc, preFault.Sp = 2, 2
	preFault.Stack[0], preFault.Stack[1] = stockS2aVerifyTagged(7), stockS2aVerifyTagged(0)
	directFault := stockS2aVerifyProgramCall(t, e, module, moduleAt, program, preFault, 1, stockS2aVerifyCallGas)
	if directFault.result == nil || directFault.result.Failed() {
		t.Fatalf("direct fault step: %v", stockS2aVerifyResultErr(directFault.result))
	}
	directOut := stockS2aVerifyUnpack(t, module, "step", directFault.result.ReturnData)
	directMachine := stockS2aVerifyMachineFrom(directOut[0])
	if directOut[1].(uint16) != 1 || directMachine.Lifecycle != stockS2aVerifyJavaFault || directMachine.Pc != 2 || directMachine.FaultPC != 2 || directMachine.Sp != 2 || directMachine.Stack[0].Cmp(preFault.Stack[0]) != 0 || directMachine.Stack[1].Cmp(preFault.Stack[1]) != 0 {
		t.Fatalf("direct fault did not preserve pre-instruction state: machine=%+v executed=%v", directMachine, directOut[1])
	}
	badOperand := stockS2aVerifyCloneMachine(preFault)
	badOperand.Stack[0] = big.NewInt(7)
	stockS2aVerifyAssertRevert(t, stockS2aVerifyProgramCall(t, e, module, moduleAt, program, badOperand, 1, stockS2aVerifyCallGas), "S2aBytecodeError(uint256,uint256)", 14, 2)

	base := stockS2aVerifyZeroMachine()
	base.Pc, base.Sp, base.Initialized, base.Lifecycle = 2, 2, 3, stockS2aVerifyJavaFault
	base.Stack[0], base.Stack[1] = stockS2aVerifyTagged(7), stockS2aVerifyTagged(0)
	base.Locals[0], base.Locals[1] = stockS2aVerifyTagged(7), stockS2aVerifyTagged(0)
	base.JavaFaultKind, base.FaultPC = stockS2aVerifyArithmeticFault, 2
	deployFake := func(t *testing.T, m stockS2aVerifyMachine, executed uint16) (common.Address, stockS2aVerifyCheckpoint) {
		t.Helper()
		code := stockS2aVerifyFakeStepRuntime(m, executed, false)
		fakeAt, _ := stockS2aVerifyDeployRaw(t, e, code, stockS2aVerifyCreateGas)
		at, _ := stockS2aVerifyDeployCoordinator(t, e, coord, parserAt, parserHash, id, fakeAt, crypto.Keccak256Hash(code), "entry", []int32{7, 0}, 64)
		return at, stockS2aVerifyCheckpointAt(t, e, coord, at)
	}
	validAt, validBefore := deployFake(t, base, 3)
	validTx := stockS2aVerifyResume(t, e, coord, validAt, 0, 3, 32, stockS2aVerifyCallGas)
	if validTx.result == nil || validTx.result.Failed() {
		t.Fatalf("well-formed synthetic fault response rejected: %v", stockS2aVerifyResultErr(validTx.result))
	}
	valid := stockS2aVerifyCheckpointAt(t, e, coord, validAt)
	if valid.Machine.Lifecycle != stockS2aVerifyJavaFault || valid.TotalSteps != 3 || valid.Epoch != validBefore.Epoch+1 {
		t.Fatalf("well-formed fault response=%+v", valid)
	}
	terminal := stockS2aVerifyResume(t, e, coord, validAt, valid.Epoch, 1, 32, stockS2aVerifyCallGas)
	stockS2aVerifyAssertRevert(t, terminal, "S2aControlError(uint256)", 1)

	bad := []struct {
		name     string
		executed uint16
		edit     func(*stockS2aVerifyMachine)
	}{
		{"kind2-not-SOE", 3, func(m *stockS2aVerifyMachine) { m.JavaFaultKind = 2 }},
		{"kind255", 3, func(m *stockS2aVerifyMachine) { m.JavaFaultKind = 255 }},
		{"unknown-lifecycle", 3, func(m *stockS2aVerifyMachine) { m.Lifecycle = 4 }},
		{"fault-pc-not-opcode", 3, func(m *stockS2aVerifyMachine) { m.Pc, m.FaultPC = 1, 1 }},
		{"pc-faultpc-disagree", 3, func(m *stockS2aVerifyMachine) { m.FaultPC = 1 }},
		{"fault-stack-arity", 3, func(m *stockS2aVerifyMachine) { m.Sp = 1; m.Stack[1] = new(big.Int) }},
		{"nonzero-divisor", 3, func(m *stockS2aVerifyMachine) { m.Stack[1] = stockS2aVerifyTagged(1) }},
		{"malformed-divisor-tag", 3, func(m *stockS2aVerifyMachine) { m.Stack[1] = new(big.Int) }},
		{"fault-result", 3, func(m *stockS2aVerifyMachine) { m.Result = 1 }},
		{"fault-fields-runnable", 3, func(m *stockS2aVerifyMachine) { m.Lifecycle = stockS2aVerifyRunnable }},
		{"zero-attempt-count", 0, func(m *stockS2aVerifyMachine) {}},
	}
	for _, tc := range bad {
		t.Run("response/"+tc.name, func(t *testing.T) {
			m := stockS2aVerifyCloneMachine(base)
			tc.edit(&m)
			at, before := deployFake(t, m, tc.executed)
			r := stockS2aVerifyResume(t, e, coord, at, 0, 3, 32, stockS2aVerifyCallGas)
			stockS2aVerifyAssertRevert(t, r, "S2aControlError(uint256)", 7)
			stockS2aVerifyAssertRollback(t, e, coord, at, before, r)
		})
	}
}

func TestStockS2aVerifyFaultRollbackReserveAndRetry(t *testing.T) {
	page := stockS2aVerifyLoadPage(t)
	parser := stockS2aVerifyLoadArtifact(t, "S2aClassParser")
	module := stockS2aVerifyLoadArtifact(t, "S2aStepModule")
	coord := stockS2aVerifyLoadArtifact(t, "S2aCoordinator")
	e := stockS2aVerifyNewEnv(t)
	defer e.close()
	parserAt, _ := e.mustCreate(parser.init, stockS2aVerifyCreateGas)
	moduleAt, _ := e.mustCreate(module.init, stockS2aVerifyCreateGas)
	class := stockS2aVerifySimpleClass([]byte{0x1a, 0x1b, 0x6c, 0xac}, 2, 2, "(II)I")
	_, _, _, id, _, _, _ := stockS2aVerifyDeployRegistered(t, e, page, parser, parserAt, class.bytes)
	ph, mh := crypto.Keccak256Hash(parser.runtime), crypto.Keccak256Hash(module.runtime)
	newFault := func(t *testing.T) common.Address {
		t.Helper()
		at, _ := stockS2aVerifyDeployCoordinator(t, e, coord, parserAt, ph, id, moduleAt, mh, "entry", []int32{-9, 0}, 64)
		return at
	}
	at := newFault(t)
	before := stockS2aVerifyCheckpointAt(t, e, coord, at)
	dirty := stockS2aVerifyResume(t, e, coord, at, 0, 3, 1, stockS2aVerifyCallGas)
	stockS2aVerifyAssertRevert(t, dirty, "S2aControlError(uint256)", 6)
	stockS2aVerifyAssertRollback(t, e, coord, at, before, dirty)
	retry := stockS2aVerifyResume(t, e, coord, at, 0, 3, 32, stockS2aVerifyCallGas)
	if retry.result == nil || retry.result.Failed() {
		t.Fatalf("fault retry failed: %v", stockS2aVerifyResultErr(retry.result))
	}
	after := stockS2aVerifyCheckpointAt(t, e, coord, at)
	if after.Machine.Lifecycle != stockS2aVerifyJavaFault || after.TotalSteps != 3 || after.Epoch != 1 {
		t.Fatalf("fault retry=%+v", after)
	}
	stockS2aVerifyCheckEvent(t, coord, retry, after, 3, stockS2aVerifyDirty(before.Machine, after.Machine))
	stockS2aVerifyAssertRevert(t, stockS2aVerifyResume(t, e, coord, at, 1, 1, 32, stockS2aVerifyCallGas), "S2aControlError(uint256)", 1)

	for _, progressed := range []bool{false, true} {
		t.Run(fmt.Sprintf("reserve/progress-%v", progressed), func(t *testing.T) {
			at := newFault(t)
			if progressed {
				r := stockS2aVerifyResume(t, e, coord, at, 0, 2, 32, stockS2aVerifyCallGas)
				if r.result == nil || r.result.Failed() {
					t.Fatal(stockS2aVerifyResultErr(r.result))
				}
			}
			before := stockS2aVerifyCheckpointAt(t, e, coord, at)
			r := stockS2aVerifyResume(t, e, coord, at, before.Epoch, 3, 32, stockS2aVerifyReserve-50_000)
			stockS2aVerifyAssertRevert(t, r, "S2aControlError(uint256)", 5)
			stockS2aVerifyAssertRollback(t, e, coord, at, before, r)
		})
	}
	// A successful nested fault commit is still reverted if its ordinary outer
	// signed transaction subsequently runs out of gas.
	outerAt := newFault(t)
	outerBefore := stockS2aVerifyCheckpointAt(t, e, coord, outerAt)
	wrapperCode := stockS2aVerifyOOGAfterCallRuntime(outerAt, stockS2aVerifyCallData(t, coord, "resume", uint64(0), uint16(3), uint8(32)))
	wrapper, _ := stockS2aVerifyDeployRaw(t, e, wrapperCode, stockS2aVerifyCreateGas)
	oog := e.apply(&wrapper, nil, stockS2aVerifyCallGas)
	if oog.coreErr != nil || oog.result == nil || !errors.Is(oog.result.Err, vm.ErrOutOfGas) || len(oog.result.ReturnData) != 0 {
		t.Fatalf("fault outer OOG core=%v evm=%v data=%x", oog.coreErr, stockS2aVerifyResultErr(oog.result), stockS2aVerifyResultData(oog.result))
	}
	stockS2aVerifyAssertRollback(t, e, coord, outerAt, outerBefore, oog)
}

func TestStockS2aVerifyStockProtocolLimitLayers(t *testing.T) {
	e := stockS2aVerifyNewEnv(t)
	defer e.close()
	nonce := e.state.StateDB.GetNonce(e.sender)
	balance := e.state.StateDB.GetBalance(e.sender).ToBig()
	runtime := make([]byte, 24577)
	r := e.apply(nil, stockS2aVerifyRawInit(runtime), stockS2aVerifyCreateGas)
	if r.coreErr != nil || r.result == nil || !errors.Is(r.result.Err, vm.ErrMaxCodeSizeExceeded) {
		t.Fatalf("EIP-170 layer core=%v evm=%v", r.coreErr, stockS2aVerifyResultErr(r.result))
	}
	if e.state.StateDB.GetNonce(e.sender) != nonce+1 || e.state.StateDB.GetBalance(e.sender).ToBig().Cmp(balance) >= 0 || len(e.state.StateDB.GetCode(crypto.CreateAddress(e.sender, nonce))) != 0 {
		t.Fatal("EIP-170 sender/code semantics")
	}
	nonce = e.state.StateDB.GetNonce(e.sender)
	balance = e.state.StateDB.GetBalance(e.sender).ToBig()
	snapshot := e.state.StateDB.Snapshot()
	r = e.apply(nil, make([]byte, 49153), stockS2aVerifyCreateGas)
	if !errors.Is(r.coreErr, core.ErrMaxInitCodeSizeExceeded) || r.result != nil {
		t.Fatalf("EIP-3860 layer core=%v result=%v", r.coreErr, r.result)
	}
	debit := new(big.Int).Sub(balance, e.state.StateDB.GetBalance(e.sender).ToBig())
	wantDebit := new(big.Int).Mul(new(big.Int).SetUint64(stockS2aVerifyCreateGas), big.NewInt(2))
	if e.state.StateDB.GetNonce(e.sender) != nonce || debit.Cmp(wantDebit) != 0 {
		t.Fatalf("raw EIP-3860 transition nonce/debit=%d/%s", e.state.StateDB.GetNonce(e.sender), debit)
	}
	e.state.StateDB.RevertToSnapshot(snapshot)
	if e.state.StateDB.GetNonce(e.sender) != nonce || e.state.StateDB.GetBalance(e.sender).ToBig().Cmp(balance) != 0 {
		t.Fatal("discard EIP-3860 state")
	}
	nonce = e.state.StateDB.GetNonce(e.sender)
	balance = e.state.StateDB.GetBalance(e.sender).ToBig()
	to := common.HexToAddress("0x7825")
	r = e.apply(&to, nil, params.MaxTxGas+1)
	if !errors.Is(r.coreErr, core.ErrGasLimitTooHigh) || r.result != nil {
		t.Fatalf("EIP-7825 layer core=%v result=%v", r.coreErr, r.result)
	}
	if e.state.StateDB.GetNonce(e.sender) != nonce || e.state.StateDB.GetBalance(e.sender).ToBig().Cmp(balance) != 0 {
		t.Fatal("EIP-7825 changed sender")
	}
}
