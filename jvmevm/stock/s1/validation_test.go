// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.
//
// This is the independent Stock S1 verifier. It intentionally does not use the
// S1 harness: artifacts are decoded again, all transactions are signed, and the
// only class analysis below is an assertion oracle for small trusted inputs.
package s1

import (
	"bytes"
	"crypto/ecdsa"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"math/big"
	"os"
	"reflect"
	"strings"
	"testing"

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
	stockS1VerifyCreateGas = uint64(8_000_000)
	stockS1VerifyCallGas   = uint64(2_000_000)
	stockS1VerifyBlockGas  = uint64(30_000_000)
	stockS1VerifyReserve   = uint64(800_000)
)

const (
	stockS1VerifyRunnable  = uint8(0)
	stockS1VerifyReturned  = uint8(1)
	stockS1VerifyStepLimit = uint8(2)
)

var (
	stockS1VerifyOne        = big.NewInt(1)
	stockS1VerifyMaxUint256 = new(big.Int).Sub(new(big.Int).Lsh(big.NewInt(1), 256), big.NewInt(1))
)

type stockS1VerifyCompiler struct {
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

type stockS1VerifyImmutable struct {
	Start, Length int
}

func (r *stockS1VerifyImmutable) UnmarshalJSON(blob []byte) error {
	var v struct{ Start, Length int }
	if err := json.Unmarshal(blob, &v); err != nil {
		return err
	}
	r.Start, r.Length = v.Start, v.Length
	return nil
}

type stockS1VerifyArtifactJSON struct {
	ContractName        string                              `json:"contractName"`
	ABI                 json.RawMessage                     `json:"abi"`
	Bytecode            string                              `json:"bytecode"`
	DeployedBytecode    string                              `json:"deployedBytecode"`
	ImmutableReferences map[string][]stockS1VerifyImmutable `json:"immutableReferences"`
	Compiler            stockS1VerifyCompiler               `json:"compiler"`
	SourceHashes        map[string]string                   `json:"sourceHashes"`
}

type stockS1VerifyArtifact struct {
	name       string
	abi        abi.ABI
	init       []byte
	runtime    []byte
	immutables map[string][]stockS1VerifyImmutable
}

func stockS1VerifyLoadArtifact(t *testing.T, name string) stockS1VerifyArtifact {
	t.Helper()
	path := "runtime/artifacts/" + name + ".json"
	blob, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read frozen %s artifact (S1 runtime integration dependency is absent): %v", name, err)
	}
	var raw stockS1VerifyArtifactJSON
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
	return stockS1VerifyArtifact{name, contractABI, decode("bytecode", raw.Bytecode), decode("deployedBytecode", raw.DeployedBytecode), raw.ImmutableReferences}
}

func stockS1VerifyLoadPage(t *testing.T) stockS1VerifyArtifact {
	t.Helper()
	a, err := stock.LoadArtifact(stock.ArtifactPage)
	if err != nil {
		t.Fatalf("load accepted S0 ArtifactPage: %v", err)
	}
	return stockS1VerifyArtifact{stock.ArtifactPage, a.ABI, a.InitCode, a.RuntimeCode, nil}
}

type stockS1VerifyMachine struct {
	Pc          uint32
	Sp          uint8
	Initialized uint8
	Lifecycle   uint8
	Stack       [8]*big.Int
	Locals      [8]*big.Int
	Result      int32
}

type stockS1VerifyProgram struct {
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

type stockS1VerifyCheckpoint struct {
	Schema     uint32
	ClassID    common.Hash
	ProgramID  common.Hash
	InputRoot  common.Hash
	Epoch      uint64
	TotalSteps uint64
	Digest     common.Hash
	Machine    stockS1VerifyMachine
}

func stockS1VerifyZeroMachine() stockS1VerifyMachine {
	m := stockS1VerifyMachine{}
	for i := range m.Stack {
		m.Stack[i] = new(big.Int)
	}
	for i := range m.Locals {
		m.Locals[i] = new(big.Int)
	}
	return m
}

func stockS1VerifyCloneMachine(m stockS1VerifyMachine) stockS1VerifyMachine {
	out := m
	for i := range out.Stack {
		out.Stack[i] = new(big.Int).Set(m.Stack[i])
	}
	for i := range out.Locals {
		out.Locals[i] = new(big.Int).Set(m.Locals[i])
	}
	return out
}

func stockS1VerifyTagged(v uint32) *big.Int {
	return new(big.Int).Or(new(big.Int).Lsh(big.NewInt(1), 64), new(big.Int).SetUint64(uint64(v)))
}

func stockS1VerifyMachineFrom(v any) stockS1VerifyMachine {
	return *abi.ConvertType(v, new(stockS1VerifyMachine)).(*stockS1VerifyMachine)
}
func stockS1VerifyProgramFrom(v any) stockS1VerifyProgram {
	return *abi.ConvertType(v, new(stockS1VerifyProgram)).(*stockS1VerifyProgram)
}

func stockS1VerifyMachineEqual(a, b stockS1VerifyMachine) bool {
	if a.Pc != b.Pc || a.Sp != b.Sp || a.Initialized != b.Initialized || a.Lifecycle != b.Lifecycle || a.Result != b.Result {
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

func stockS1VerifyDirty(a, b stockS1VerifyMachine) uint8 {
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
	if n > 24 {
		panic("S1 dirty accounting exceeded frozen maximum")
	}
	return uint8(n)
}

type stockS1VerifyEnv struct {
	t       *testing.T
	state   gethtests.StateTestState
	key     *ecdsa.PrivateKey
	sender  common.Address
	signer  types.Signer
	block   vm.BlockContext
	gasUsed uint64
}

type stockS1VerifyTx struct {
	tx      *types.Transaction
	result  *core.ExecutionResult
	coreErr error
	address common.Address
	logs    []*types.Log
	receipt *types.Receipt
}

func stockS1VerifyNewEnv(t *testing.T) *stockS1VerifyEnv {
	t.Helper()
	key, err := crypto.HexToECDSA("51a151a151a151a151a151a151a151a151a151a151a151a151a151a151a151a1")
	if err != nil {
		t.Fatal(err)
	}
	sender := crypto.PubkeyToAddress(key.PublicKey)
	pre := gethtests.MakePreState(rawdb.NewMemoryDatabase(), types.GenesisAlloc{
		sender: {Balance: new(big.Int).Exp(big.NewInt(10), big.NewInt(30), nil)},
	}, false, rawdb.HashScheme)
	random := crypto.Keccak256Hash([]byte("JVMEVM:STOCK:S1:VERIFY"))
	block := vm.BlockContext{
		CanTransfer: core.CanTransfer, Transfer: core.Transfer,
		GetHash:     func(n uint64) common.Hash { return crypto.Keccak256Hash(new(big.Int).SetUint64(n).Bytes()) },
		Coinbase:    common.HexToAddress("0x0000000000000000000000000000000000001337"),
		BlockNumber: big.NewInt(1), Time: 1, Difficulty: new(big.Int), BaseFee: new(big.Int).Set(stockS1VerifyOne),
		GasLimit: stockS1VerifyBlockGas, Random: &random,
	}
	return &stockS1VerifyEnv{t: t, state: pre, key: key, sender: sender,
		signer: types.MakeSigner(params.AllDevChainProtocolChanges, block.BlockNumber, block.Time), block: block}
}
func (e *stockS1VerifyEnv) close() { e.state.Close() }

func (e *stockS1VerifyEnv) apply(to *common.Address, input []byte, gas uint64) stockS1VerifyTx {
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
	result, coreErr := core.ApplyMessage(evm, msg, new(core.GasPool).AddGas(stockS1VerifyBlockGas))
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
	return stockS1VerifyTx{signed, result, coreErr, address, logs, receipt}
}

func stockS1VerifyResultErr(r *core.ExecutionResult) error {
	if r == nil {
		return nil
	}
	return r.Err
}
func stockS1VerifyResultData(r *core.ExecutionResult) []byte {
	if r == nil {
		return nil
	}
	return r.ReturnData
}

func (e *stockS1VerifyEnv) mustCreate(init []byte, gas uint64) (common.Address, stockS1VerifyTx) {
	e.t.Helper()
	r := e.apply(nil, init, gas)
	if r.coreErr != nil || r.result == nil || r.result.Err != nil {
		e.t.Fatalf("CREATE: core=%v evm=%v data=%x", r.coreErr, stockS1VerifyResultErr(r.result), stockS1VerifyResultData(r.result))
	}
	if len(e.state.StateDB.GetCode(r.address)) == 0 || r.receipt == nil || r.receipt.Status != types.ReceiptStatusSuccessful {
		e.t.Fatalf("CREATE %s has no successful receipt/code", r.address)
	}
	return r.address, r
}
func (e *stockS1VerifyEnv) mustCall(to common.Address, input []byte, gas uint64) stockS1VerifyTx {
	e.t.Helper()
	r := e.apply(&to, input, gas)
	if r.coreErr != nil || r.result == nil || r.result.Err != nil || r.receipt == nil || r.receipt.Status != types.ReceiptStatusSuccessful {
		e.t.Fatalf("CALL %s: core=%v evm=%v data=%x", to, r.coreErr, stockS1VerifyResultErr(r.result), stockS1VerifyResultData(r.result))
	}
	return r
}

func stockS1VerifyConstructor(t *testing.T, a stockS1VerifyArtifact, args ...any) []byte {
	t.Helper()
	tail, err := a.abi.Pack("", args...)
	if err != nil {
		t.Fatalf("pack %s constructor: %v", a.name, err)
	}
	return append(append([]byte(nil), a.init...), tail...)
}
func stockS1VerifyCallData(t *testing.T, a stockS1VerifyArtifact, method string, args ...any) []byte {
	t.Helper()
	out, err := a.abi.Pack(method, args...)
	if err != nil {
		t.Fatalf("pack %s.%s: %v", a.name, method, err)
	}
	return out
}
func stockS1VerifyUnpack(t *testing.T, a stockS1VerifyArtifact, method string, data []byte) []any {
	t.Helper()
	out, err := a.abi.Unpack(method, data)
	if err != nil {
		t.Fatalf("unpack %s.%s %x: %v", a.name, method, data, err)
	}
	return out
}

func stockS1VerifyCustomError(signature string, values ...any) []byte {
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
func stockS1VerifyAssertRevert(t *testing.T, r stockS1VerifyTx, signature string, words ...any) {
	t.Helper()
	if r.coreErr != nil || r.result == nil || !errors.Is(r.result.Err, vm.ErrExecutionReverted) {
		t.Fatalf("want %s%v: core=%v evm=%v data=%x", signature, words, r.coreErr, stockS1VerifyResultErr(r.result), stockS1VerifyResultData(r.result))
	}
	want := stockS1VerifyCustomError(signature, words...)
	if !bytes.Equal(r.result.ReturnData, want) {
		t.Fatalf("wrong revert\nhave %x\nwant %x", r.result.ReturnData, want)
	}
	if len(r.logs) != 0 || r.receipt == nil || r.receipt.Status != types.ReceiptStatusFailed {
		t.Fatalf("failed transaction logs/receipt: logs=%d receipt=%+v", len(r.logs), r.receipt)
	}
}

func stockS1VerifyRawInit(runtime []byte) []byte {
	if len(runtime) > math.MaxUint16 {
		panic("raw runtime too large")
	}
	out := []byte{0x61, byte(len(runtime) >> 8), byte(len(runtime)), 0x61, 0, 15, 0x60, 0, 0x39, 0x61, byte(len(runtime) >> 8), byte(len(runtime)), 0x60, 0, 0xf3}
	return append(out, runtime...)
}
func stockS1VerifyDeployRaw(t *testing.T, e *stockS1VerifyEnv, runtime []byte, gas uint64) (common.Address, stockS1VerifyTx) {
	t.Helper()
	at, tx := e.mustCreate(stockS1VerifyRawInit(runtime), gas)
	if !bytes.Equal(e.state.StateDB.GetCode(at), runtime) {
		t.Fatal("ordinary raw CREATE bytes differ")
	}
	return at, tx
}
func stockS1VerifyDeployPage(t *testing.T, e *stockS1VerifyEnv, page stockS1VerifyArtifact, payload []byte) (common.Address, common.Hash, common.Hash, stockS1VerifyTx) {
	t.Helper()
	at, tx := e.mustCreate(stockS1VerifyConstructor(t, page, payload), stockS1VerifyCreateGas)
	code := append([]byte{0}, payload...)
	pageHash, payloadHash := crypto.Keccak256Hash(code), crypto.Keccak256Hash(payload)
	if !bytes.Equal(e.state.StateDB.GetCode(at), code) {
		t.Fatal("ArtifactPage is not exact STOP||raw payload")
	}
	return at, pageHash, payloadHash, tx
}

func stockS1VerifyRequireMethod(t *testing.T, a stockS1VerifyArtifact, name, signature, mutability string, in, out int) {
	t.Helper()
	m, ok := a.abi.Methods[name]
	if !ok || m.Sig != signature || m.StateMutability != mutability || len(m.Inputs) != in || len(m.Outputs) != out {
		t.Fatalf("%s.%s ABI mismatch: present=%v sig=%q mut=%q in=%d out=%d", a.name, name, ok, m.Sig, m.StateMutability, len(m.Inputs), len(m.Outputs))
	}
}
func stockS1VerifyRequireError(t *testing.T, a stockS1VerifyArtifact, name, signature string) {
	t.Helper()
	e, ok := a.abi.Errors[name]
	if !ok || e.Sig != signature {
		t.Fatalf("%s error %s: present=%v sig=%q", a.name, name, ok, e.Sig)
	}
}
func stockS1VerifyTuple(t *testing.T, typ abi.Type, names, typesWant []string) {
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

// stockS1VerifyClass is a bounded trusted classfile generator. Its output is
// passed unchanged to ArtifactPage. No offsets, starts, literals, or results are
// supplied to any production contract.
type stockS1VerifyMethod struct {
	name, descriptor    string
	access              uint16
	code                []byte
	maxStack, maxLocals uint16
	codeCopies          int
	handlers            uint16
}
type stockS1VerifyClass struct {
	bytes []byte
	marks map[string]int
}
type stockS1VerifyCP struct {
	tag   byte
	body  []byte
	slots uint16
}

func stockS1VerifyU2(v uint16) []byte { return []byte{byte(v >> 8), byte(v)} }
func stockS1VerifyU4(v uint32) []byte {
	return []byte{byte(v >> 24), byte(v >> 16), byte(v >> 8), byte(v)}
}
func stockS1VerifyUtf8(s string) stockS1VerifyCP {
	return stockS1VerifyCP{1, append(stockS1VerifyU2(uint16(len(s))), []byte(s)...), 1}
}
func stockS1VerifyBuildClass(className string, methods []stockS1VerifyMethod, cpPad int) stockS1VerifyClass {
	if className == "" {
		className = "S1Trusted"
	}
	all := append([]stockS1VerifyMethod{{"<init>", "()V", 0x0001, []byte{0x2a, 0xb7, 0, 9, 0xb1}, 1, 1, 1, 0}}, methods...)
	cp := []stockS1VerifyCP{
		stockS1VerifyUtf8(className), {7, stockS1VerifyU2(1), 1},
		stockS1VerifyUtf8("java/lang/Object"), {7, stockS1VerifyU2(3), 1},
		stockS1VerifyUtf8("<init>"), stockS1VerifyUtf8("()V"), stockS1VerifyUtf8("Code"),
		{12, append(stockS1VerifyU2(5), stockS1VerifyU2(6)...), 1},
		{10, append(stockS1VerifyU2(4), stockS1VerifyU2(8)...), 1},
		{3, []byte{0x12, 0x34, 0x56, 0x78}, 1},
	}
	utf := map[string]uint16{className: 1, "<init>": 5, "()V": 6, "Code": 7}
	next := uint16(11)
	for _, m := range methods {
		for _, s := range []string{m.name, m.descriptor} {
			if _, ok := utf[s]; !ok {
				utf[s] = next
				cp = append(cp, stockS1VerifyUtf8(s))
				next++
			}
		}
	}
	for len(cp)+1 < cpPad {
		cp = append(cp, stockS1VerifyCP{3, []byte{0, 0, 0, byte(len(cp))}, 1})
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
	put(stockS1VerifyU2(uint16(len(cp) + 1)))
	for _, c := range cp {
		put([]byte{c.tag})
		put(c.body)
	}
	mark("classAccess")
	put(stockS1VerifyU2(0x0021))
	put(stockS1VerifyU2(2))
	put(stockS1VerifyU2(4))
	put(stockS1VerifyU2(0))
	put(stockS1VerifyU2(0))
	mark("methodCount")
	put(stockS1VerifyU2(uint16(len(all))))
	for i, m := range all {
		prefix := fmt.Sprintf("method%d", i)
		if m.codeCopies == 0 {
			m.codeCopies = 1
		}
		mark(prefix + ".access")
		put(stockS1VerifyU2(m.access))
		put(stockS1VerifyU2(utf[m.name]))
		put(stockS1VerifyU2(utf[m.descriptor]))
		mark(prefix + ".attrs")
		put(stockS1VerifyU2(uint16(m.codeCopies)))
		for copyNo := 0; copyNo < m.codeCopies; copyNo++ {
			p := fmt.Sprintf("%s.code%d", prefix, copyNo)
			put(stockS1VerifyU2(7))
			put(stockS1VerifyU4(uint32(12 + len(m.code) + int(m.handlers)*8)))
			mark(p + ".maxStack")
			put(stockS1VerifyU2(m.maxStack))
			mark(p + ".maxLocals")
			put(stockS1VerifyU2(m.maxLocals))
			mark(p + ".codeLen")
			put(stockS1VerifyU4(uint32(len(m.code))))
			mark(p + ".bytes")
			put(m.code)
			mark(p + ".handlers")
			put(stockS1VerifyU2(m.handlers))
			put(make([]byte, int(m.handlers)*8))
			put(stockS1VerifyU2(0))
		}
	}
	put(stockS1VerifyU2(0))
	return stockS1VerifyClass{out, marks}
}
func stockS1VerifySimpleClass(code []byte, stack, locals uint16, descriptor string) stockS1VerifyClass {
	if descriptor == "" {
		descriptor = "()I"
	}
	return stockS1VerifyBuildClass("S1Trusted", []stockS1VerifyMethod{{"entry", descriptor, 0x0009, code, stack, locals, 1, 0}}, 0)
}
func stockS1VerifyPatchU2(c stockS1VerifyClass, mark string, v uint16) stockS1VerifyClass {
	out := stockS1VerifyClass{append([]byte(nil), c.bytes...), c.marks}
	binary.BigEndian.PutUint16(out.bytes[out.marks[mark]:], v)
	return out
}
func stockS1VerifyPatchU4(c stockS1VerifyClass, mark string, v uint32) stockS1VerifyClass {
	out := stockS1VerifyClass{append([]byte(nil), c.bytes...), c.marks}
	binary.BigEndian.PutUint32(out.bytes[out.marks[mark]:], v)
	return out
}

// Independent decoder for valid generated inputs. It computes the complete
// schema-2 metadata expectation from raw bytes, rather than from generator marks.
type stockS1VerifyParsedMethod struct {
	index, access             uint16
	name, descriptor          []byte
	codeOffset                uint32
	code                      []byte
	maxStack, maxLocals, argc uint8
	starts                    *big.Int
	literals                  []stockS1VerifyLiteral
}
type stockS1VerifyLiteral struct {
	method, pc uint16
	bits       uint32
}
type stockS1VerifyParsed struct {
	className       []byte
	access, cpCount uint16
	methods         []stockS1VerifyParsedMethod
	literals        []stockS1VerifyLiteral
}
type stockS1VerifyReader struct {
	b []byte
	p int
}

func (r *stockS1VerifyReader) take(n int) []byte {
	if n < 0 || r.p+n > len(r.b) {
		panic("trusted class parser boundary")
	}
	v := r.b[r.p : r.p+n]
	r.p += n
	return v
}
func (r *stockS1VerifyReader) u1() byte   { return r.take(1)[0] }
func (r *stockS1VerifyReader) u2() uint16 { return binary.BigEndian.Uint16(r.take(2)) }
func (r *stockS1VerifyReader) u4() uint32 { return binary.BigEndian.Uint32(r.take(4)) }
func stockS1VerifyArgc(desc string) (uint8, bool) {
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
func stockS1VerifyOpcodeWidth(op byte) int {
	switch op {
	case 0x10, 0x12, 0x15, 0x36:
		return 2
	case 0x11, 0x13, 0x84, 0x99, 0x9a, 0x9b, 0x9c, 0x9d, 0x9e, 0x9f, 0xa0, 0xa1, 0xa2, 0xa3, 0xa4, 0xa7:
		return 3
	default:
		return 1
	}
}
func stockS1VerifyParseTrusted(raw []byte) stockS1VerifyParsed {
	r := &stockS1VerifyReader{b: raw}
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
	parsed := stockS1VerifyParsed{className: className, access: access, cpCount: cpCount}
	for i := uint16(0); i < methodCount; i++ {
		m := stockS1VerifyParsedMethod{index: i, access: r.u2()}
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
		argc, eligible := stockS1VerifyArgc(string(m.descriptor))
		eligible = eligible && m.access == 0x0009 && len(m.code) > 0 && len(m.code) <= 256 && m.maxStack <= 8 && m.maxLocals <= 8 && m.maxLocals >= argc
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
					lit := stockS1VerifyLiteral{i, uint16(pc), ints[ix]}
					m.literals = append(m.literals, lit)
					parsed.literals = append(parsed.literals, lit)
				}
				pc += stockS1VerifyOpcodeWidth(op)
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

func stockS1VerifyMetadataExpected(raw []byte, rawPage common.Address, pageHash, payloadHash common.Hash) []byte {
	p := stockS1VerifyParseTrusted(raw)
	words := make([][32]byte, 0, 6+4*len(p.methods))
	putHash := func(h common.Hash) { words = append(words, [32]byte(h)) }
	putHash(crypto.Keccak256Hash([]byte("JVMEVM:S1:METADATA:2")))
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
			v.Or(v, new(big.Int).Lsh(big.NewInt(1), 104))
			v.Or(v, new(big.Int).Lsh(big.NewInt(6), 112))
			v.Or(v, new(big.Int).Lsh(new(big.Int).SetUint64(uint64(m.index)), 120))
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

func stockS1VerifyRegister(t *testing.T, e *stockS1VerifyEnv, parser stockS1VerifyArtifact, parserAt, rawAt common.Address, pageHash, payloadHash common.Hash) (common.Hash, common.Address, common.Hash, uint16, stockS1VerifyTx) {
	t.Helper()
	tx := e.mustCall(parserAt, stockS1VerifyCallData(t, parser, "registerClass", rawAt, pageHash, payloadHash), stockS1VerifyCreateGas)
	out := stockS1VerifyUnpack(t, parser, "registerClass", tx.result.ReturnData)
	if len(out) != 4 {
		t.Fatalf("registerClass outputs=%d", len(out))
	}
	return common.Hash(out[0].([32]byte)), out[1].(common.Address), common.Hash(out[2].([32]byte)), out[3].(uint16), tx
}
func stockS1VerifyClassRecord(t *testing.T, e *stockS1VerifyEnv, parser stockS1VerifyArtifact, at common.Address, id common.Hash) (common.Address, common.Hash) {
	t.Helper()
	tx := e.mustCall(at, stockS1VerifyCallData(t, parser, "classRecord", id), stockS1VerifyCallGas)
	out := stockS1VerifyUnpack(t, parser, "classRecord", tx.result.ReturnData)
	return out[0].(common.Address), common.Hash(out[1].([32]byte))
}
func stockS1VerifyDeployRegistered(t *testing.T, e *stockS1VerifyEnv, page, parser stockS1VerifyArtifact, parserAt common.Address, raw []byte) (common.Address, common.Hash, common.Hash, common.Hash, common.Address, common.Hash, stockS1VerifyTx) {
	t.Helper()
	rawAt, pageHash, payloadHash, _ := stockS1VerifyDeployPage(t, e, page, raw)
	id, metaAt, metaHash, _, tx := stockS1VerifyRegister(t, e, parser, parserAt, rawAt, pageHash, payloadHash)
	return rawAt, pageHash, payloadHash, id, metaAt, metaHash, tx
}
func stockS1VerifyDeployCoordinator(t *testing.T, e *stockS1VerifyEnv, coord stockS1VerifyArtifact, parserAt common.Address, parserHash, classID common.Hash, moduleAt common.Address, moduleHash common.Hash, entry string, args []int32, cap uint64) (common.Address, stockS1VerifyTx) {
	t.Helper()
	return e.mustCreate(stockS1VerifyConstructor(t, coord, parserAt, parserHash, classID, moduleAt, moduleHash, []byte(entry), args, cap), stockS1VerifyCreateGas)
}
func stockS1VerifyCheckpointAt(t *testing.T, e *stockS1VerifyEnv, coord stockS1VerifyArtifact, at common.Address) stockS1VerifyCheckpoint {
	t.Helper()
	tx := e.mustCall(at, stockS1VerifyCallData(t, coord, "checkpoint"), stockS1VerifyCallGas)
	out := stockS1VerifyUnpack(t, coord, "checkpoint", tx.result.ReturnData)
	return stockS1VerifyCheckpoint{out[0].(uint32), common.Hash(out[1].([32]byte)), common.Hash(out[2].([32]byte)), common.Hash(out[3].([32]byte)), out[4].(uint64), out[5].(uint64), common.Hash(out[6].([32]byte)), stockS1VerifyMachineFrom(out[7])}
}
func stockS1VerifyResume(t *testing.T, e *stockS1VerifyEnv, coord stockS1VerifyArtifact, at common.Address, epoch uint64, budget uint16, dirty uint8, gas uint64) stockS1VerifyTx {
	t.Helper()
	return e.apply(&at, stockS1VerifyCallData(t, coord, "resume", epoch, budget, dirty), gas)
}
func stockS1VerifyAssertRollback(t *testing.T, e *stockS1VerifyEnv, coord stockS1VerifyArtifact, at common.Address, before stockS1VerifyCheckpoint, tx stockS1VerifyTx) {
	t.Helper()
	if len(tx.logs) != 0 {
		t.Fatalf("failed transaction retained %d logs", len(tx.logs))
	}
	after := stockS1VerifyCheckpointAt(t, e, coord, at)
	if before.Schema != after.Schema || before.ClassID != after.ClassID || before.ProgramID != after.ProgramID || before.InputRoot != after.InputRoot || before.Epoch != after.Epoch || before.TotalSteps != after.TotalSteps || before.Digest != after.Digest || !stockS1VerifyMachineEqual(before.Machine, after.Machine) {
		t.Fatalf("failed resume changed checkpoint\nbefore=%+v\nafter=%+v", before, after)
	}
}
func stockS1VerifyABIHash(t *testing.T, typesText []string, values ...any) common.Hash {
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
func stockS1VerifyClassID(t *testing.T, parserHash common.Hash, rawAt common.Address, pageHash, payloadHash, metadataHash common.Hash) common.Hash {
	return stockS1VerifyABIHash(t, []string{"bytes32", "uint32", "bytes32", "address", "bytes32", "bytes32", "bytes32"}, crypto.Keccak256Hash([]byte("JVMEVM:S1:CLASS")), uint32(2), parserHash, rawAt, pageHash, payloadHash, metadataHash)
}
func stockS1VerifyProgramID(t *testing.T, classID common.Hash, index uint16, entry, desc []byte, moduleHash common.Hash) common.Hash {
	return stockS1VerifyABIHash(t, []string{"bytes32", "uint32", "bytes32", "uint16", "bytes32", "bytes32", "bytes32"}, crypto.Keccak256Hash([]byte("JVMEVM:S1:PROGRAM")), uint32(2), classID, index, crypto.Keccak256Hash(entry), crypto.Keccak256Hash(desc), moduleHash)
}
func stockS1VerifyArgsHash(t *testing.T, args []int32) common.Hash {
	return stockS1VerifyABIHash(t, []string{"int32[]"}, args)
}
func stockS1VerifyInputRoot(t *testing.T, program, argsHash common.Hash, cap uint64) common.Hash {
	return stockS1VerifyABIHash(t, []string{"bytes32", "bytes32", "bytes32", "uint64"}, crypto.Keccak256Hash([]byte("JVMEVM:S1:INPUT")), program, argsHash, cap)
}
func stockS1VerifyDigest(t *testing.T, input, parserHash, moduleHash common.Hash, m stockS1VerifyMachine, epoch, total uint64, machineType abi.Type) common.Hash {
	t.Helper()
	u32, _ := abi.NewType("uint32", "", nil)
	b32, _ := abi.NewType("bytes32", "", nil)
	u64, _ := abi.NewType("uint64", "", nil)
	args := abi.Arguments{{Type: u32}, {Type: b32}, {Type: b32}, {Type: b32}, {Type: machineType}, {Type: u64}, {Type: u64}}
	packed, err := args.Pack(uint32(2), input, parserHash, moduleHash, m, epoch, total)
	if err != nil {
		t.Fatal(err)
	}
	return crypto.Keccak256Hash(packed)
}
func stockS1VerifyCheckEvent(t *testing.T, coord stockS1VerifyArtifact, tx stockS1VerifyTx, c stockS1VerifyCheckpoint, executed uint16, dirty uint8) {
	t.Helper()
	if len(tx.logs) != 1 {
		t.Fatalf("checkpoint logs=%d", len(tx.logs))
	}
	ev := coord.abi.Events["CheckpointV2"]
	log := tx.logs[0]
	if len(log.Topics) != 3 || log.Topics[0] != ev.ID || new(big.Int).SetBytes(log.Topics[1][:]).Uint64() != c.Epoch || common.Hash(log.Topics[2]) != c.ProgramID {
		t.Fatalf("bad event topics %v", log.Topics)
	}
	v, err := ev.Inputs.NonIndexed().Unpack(log.Data)
	if err != nil {
		t.Fatal(err)
	}
	if v[0].(uint64) != c.TotalSteps || v[1].(uint32) != c.Machine.Pc || v[2].(uint8) != c.Machine.Sp || v[3].(uint8) != c.Machine.Lifecycle || v[4].(int32) != c.Machine.Result || v[5].(uint16) != executed || v[6].(uint8) != dirty || common.Hash(v[7].([32]byte)) != c.Digest {
		t.Fatalf("bad CheckpointV2 data %v", v)
	}
}

func TestStockS1VerifyFrozenABIArtifactsMetadataAndDeployment(t *testing.T) {
	page := stockS1VerifyLoadPage(t)
	metadata := stockS1VerifyLoadArtifact(t, "S1MetadataPage")
	parser := stockS1VerifyLoadArtifact(t, "S1ClassParser")
	module := stockS1VerifyLoadArtifact(t, "S1StepModule")
	coord := stockS1VerifyLoadArtifact(t, "S1Coordinator")
	if len(page.runtime) > 12*1024 || len(page.init) > 24*1024 {
		t.Fatal("accepted S0 ArtifactPage limits changed")
	}
	if len(metadata.abi.Constructor.Inputs) != 1 || metadata.abi.Constructor.Inputs[0].Type.String() != "bytes" || len(metadata.abi.Methods) != 0 {
		t.Fatalf("metadata page ABI is not constructor(bytes)-only")
	}
	stockS1VerifyRequireError(t, metadata, "S1ClassError", "S1ClassError(uint256,uint256)")
	if len(parser.abi.Constructor.Inputs) != 0 || len(module.abi.Constructor.Inputs) != 0 {
		t.Fatal("parser/module constructor gained configuration")
	}
	stockS1VerifyRequireMethod(t, parser, "registerClass", "registerClass(address,bytes32,bytes32)", "nonpayable", 3, 4)
	stockS1VerifyRequireMethod(t, parser, "classRecord", "classRecord(bytes32)", "view", 1, 2)
	if len(parser.abi.Methods) != 2 {
		t.Fatalf("parser exposes mutable/non-frozen API: %v", parser.abi.Methods)
	}
	machineNames := []string{"pc", "sp", "initialized", "lifecycle", "stack", "locals", "result"}
	machineTypes := []string{"uint32", "uint8", "uint8", "uint8", "uint256[8]", "uint256[8]", "int32"}
	programNames := []string{"parser", "parserCodeHash", "classId", "rawPage", "rawPageHash", "payloadHash", "metadataPage", "metadataHash", "methodIndex", "programId"}
	programTypes := []string{"address", "bytes32", "bytes32", "address", "bytes32", "bytes32", "address", "bytes32", "uint16", "bytes32"}
	stockS1VerifyRequireMethod(t, module, "step", "step((address,bytes32,bytes32,address,bytes32,bytes32,address,bytes32,uint16,bytes32),(uint32,uint8,uint8,uint8,uint256[8],uint256[8],int32),uint16)", "view", 3, 2)
	if len(module.abi.Methods) != 1 {
		t.Fatalf("module exposes configuration: %v", module.abi.Methods)
	}
	stockS1VerifyTuple(t, module.abi.Methods["step"].Inputs[0].Type, programNames, programTypes)
	stockS1VerifyTuple(t, module.abi.Methods["step"].Inputs[1].Type, machineNames, machineTypes)
	stockS1VerifyTuple(t, module.abi.Methods["step"].Outputs[0].Type, machineNames, machineTypes)
	wantCtor := []string{"address", "bytes32", "bytes32", "address", "bytes32", "bytes", "int32[]", "uint64"}
	if len(coord.abi.Constructor.Inputs) != len(wantCtor) {
		t.Fatalf("coordinator ctor arity=%d", len(coord.abi.Constructor.Inputs))
	}
	for i, w := range wantCtor {
		if coord.abi.Constructor.Inputs[i].Type.String() != w {
			t.Fatalf("coordinator ctor arg%d=%s want=%s", i, coord.abi.Constructor.Inputs[i].Type, w)
		}
	}
	stockS1VerifyRequireMethod(t, coord, "resume", "resume(uint64,uint16,uint8)", "nonpayable", 3, 5)
	stockS1VerifyRequireMethod(t, coord, "checkpoint", "checkpoint()", "view", 0, 8)
	stockS1VerifyRequireMethod(t, coord, "programContext", "programContext()", "view", 0, 1)
	stockS1VerifyTuple(t, coord.abi.Methods["checkpoint"].Outputs[7].Type, machineNames, machineTypes)
	stockS1VerifyTuple(t, coord.abi.Methods["programContext"].Outputs[0].Type, programNames, programTypes)
	for _, g := range []struct{ name, sig, typ string }{{"parser", "parser()", "address"}, {"expectedParserHash", "expectedParserHash()", "bytes32"}, {"classId", "classId()", "bytes32"}, {"module", "module()", "address"}, {"expectedModuleHash", "expectedModuleHash()", "bytes32"}, {"programId", "programId()", "bytes32"}, {"argsHash", "argsHash()", "bytes32"}, {"inputRoot", "inputRoot()", "bytes32"}, {"maxTotalSteps", "maxTotalSteps()", "uint64"}} {
		stockS1VerifyRequireMethod(t, coord, g.name, g.sig, "view", 0, 1)
		if coord.abi.Methods[g.name].Outputs[0].Type.String() != g.typ {
			t.Fatalf("getter %s type=%s", g.name, coord.abi.Methods[g.name].Outputs[0].Type)
		}
	}
	if len(coord.abi.Methods) != 12 {
		t.Fatalf("coordinator API count=%d want12", len(coord.abi.Methods))
	}
	for _, a := range []stockS1VerifyArtifact{parser, module, coord} {
		runtimeCap := 12 * 1024
		if a.name == "S1ClassParser" {
			runtimeCap = 16 * 1024
		}
		if len(a.runtime) > runtimeCap || len(a.init) > 24*1024 {
			t.Fatalf("%s sizes init=%d runtime=%d", a.name, len(a.init), len(a.runtime))
		}
	}
	for _, a := range []stockS1VerifyArtifact{parser, module, coord} {
		for _, x := range []struct{ name, sig string }{{"S1ControlError", "S1ControlError(uint256)"}, {"S1MethodError", "S1MethodError(uint256,uint256)"}, {"S1BytecodeError", "S1BytecodeError(uint256,uint256)"}} {
			if _, ok := a.abi.Errors[x.name]; ok {
				stockS1VerifyRequireError(t, a, x.name, x.sig)
			}
		}
	}
	stockS1VerifyRequireError(t, parser, "StockPageError", "StockPageError(uint256)")
	stockS1VerifyRequireError(t, parser, "S1ClassError", "S1ClassError(uint256,uint256)")
	stockS1VerifyRequireError(t, coord, "S1ControlError", "S1ControlError(uint256)")
	event, ok := parser.abi.Events["ClassRegistered"]
	if !ok || event.Sig != "ClassRegistered(bytes32,address,address,bytes32,uint16)" || len(event.Inputs) != 5 || !event.Inputs[0].Indexed || !event.Inputs[1].Indexed {
		t.Fatalf("ClassRegistered ABI=%v", event)
	}
	checkpointEvent, ok := coord.abi.Events["CheckpointV2"]
	if !ok || checkpointEvent.Sig != "CheckpointV2(uint64,bytes32,uint64,uint32,uint8,uint8,int32,uint16,uint8,bytes32)" || len(checkpointEvent.Inputs) != 10 || !checkpointEvent.Inputs[0].Indexed || !checkpointEvent.Inputs[1].Indexed {
		t.Fatalf("CheckpointV2 ABI=%v", checkpointEvent)
	}

	e := stockS1VerifyNewEnv(t)
	defer e.close()
	// Metadata payload 8,191 is the exact constructor boundary (8,192 bytes
	// including STOP). One more byte fails atomically as a metadata capacity error.
	metadataBoundary, _ := e.mustCreate(stockS1VerifyConstructor(t, metadata, make([]byte, 8191)), stockS1VerifyCreateGas)
	if len(e.state.StateDB.GetCode(metadataBoundary)) != 8192 {
		t.Fatal("metadata 8KiB boundary")
	}
	metadataNonce := e.state.StateDB.GetNonce(e.sender)
	metadataTooLarge := e.apply(nil, stockS1VerifyConstructor(t, metadata, make([]byte, 8192)), stockS1VerifyCreateGas)
	stockS1VerifyAssertRevert(t, metadataTooLarge, "S1ClassError(uint256,uint256)", 5, 0)
	if len(e.state.StateDB.GetCode(crypto.CreateAddress(e.sender, metadataNonce))) != 0 {
		t.Fatal("rejected metadata page left code")
	}
	parserAt, parserTx := e.mustCreate(parser.init, stockS1VerifyCreateGas)
	moduleAt, moduleTx := e.mustCreate(module.init, stockS1VerifyCreateGas)
	parserHash := crypto.Keccak256Hash(e.state.StateDB.GetCode(parserAt))
	moduleHash := crypto.Keccak256Hash(e.state.StateDB.GetCode(moduleAt))
	if !bytes.Equal(e.state.StateDB.GetCode(parserAt), parser.runtime) || !bytes.Equal(e.state.StateDB.GetCode(moduleAt), module.runtime) {
		t.Fatal("deployed component differs from pinned artifact")
	}
	class := stockS1VerifySimpleClass([]byte{0x1a, 0x04, 0x60, 0xac}, 2, 1, "(I)I")
	rawAt, pageHash, payloadHash, _ := stockS1VerifyDeployPage(t, e, page, class.bytes)
	classID, metadataAt, metadataHash, declared, registerTx := stockS1VerifyRegister(t, e, parser, parserAt, rawAt, pageHash, payloadHash)
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
	expectedPayload := stockS1VerifyMetadataExpected(class.bytes, rawAt, pageHash, payloadHash)
	if !bytes.Equal(metadataCode[1:], expectedPayload) {
		t.Fatalf("parser-derived metadata mismatch\nhave=%x\nwant=%x", metadataCode[1:], expectedPayload)
	}
	if len(metadataCode) != 1+6*32+4*32*int(declared) {
		t.Fatalf("metadata exact length=%d", len(metadataCode))
	}
	wantClass := stockS1VerifyClassID(t, parserHash, rawAt, pageHash, payloadHash, metadataHash)
	if classID != wantClass {
		t.Fatalf("classId=%s want=%s", classID, wantClass)
	}
	recordAt, recordHash := stockS1VerifyClassRecord(t, e, parser, parserAt, classID)
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
	id2, at2, hash2, n2, retry := stockS1VerifyRegister(t, e, parser, parserAt, rawAt, pageHash, payloadHash)
	if id2 != classID || at2 != metadataAt || hash2 != metadataHash || n2 != declared || len(retry.logs) != 0 || e.state.StateDB.GetNonce(parserAt) != parserNonce {
		t.Fatal("registration was not idempotent")
	}
	args := []int32{math.MinInt32}
	coordAt, coordTx := stockS1VerifyDeployCoordinator(t, e, coord, parserAt, parserHash, classID, moduleAt, moduleHash, "entry", args, 64)
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
	programTx := e.mustCall(coordAt, stockS1VerifyCallData(t, coord, "programContext"), stockS1VerifyCallGas)
	program := stockS1VerifyProgramFrom(stockS1VerifyUnpack(t, coord, "programContext", programTx.result.ReturnData)[0])
	wantProgram := stockS1VerifyProgramID(t, classID, 1, []byte("entry"), []byte("(I)I"), moduleHash)
	wantArgs := stockS1VerifyArgsHash(t, args)
	wantInput := stockS1VerifyInputRoot(t, wantProgram, wantArgs, 64)
	if program.Parser != parserAt || common.Hash(program.ParserCodeHash) != parserHash || common.Hash(program.ClassId) != classID || program.RawPage != rawAt || common.Hash(program.RawPageHash) != pageHash || common.Hash(program.PayloadHash) != payloadHash || program.MetadataPage != metadataAt || common.Hash(program.MetadataHash) != metadataHash || program.MethodIndex != 1 || common.Hash(program.ProgramId) != wantProgram {
		t.Fatalf("programContext=%+v", program)
	}
	initial := stockS1VerifyCheckpointAt(t, e, coord, coordAt)
	if initial.Schema != 2 || initial.ClassID != classID || initial.ProgramID != wantProgram || initial.InputRoot != wantInput || initial.Epoch != 0 || initial.TotalSteps != 0 || initial.Machine.Pc != 0 || initial.Machine.Sp != 0 || initial.Machine.Initialized != 1 || initial.Machine.Lifecycle != stockS1VerifyRunnable || initial.Machine.Result != 0 || initial.Machine.Locals[0].Cmp(stockS1VerifyTagged(0x80000000)) != 0 {
		t.Fatalf("initial checkpoint=%+v", initial)
	}
	if initial.Digest != stockS1VerifyDigest(t, wantInput, parserHash, moduleHash, initial.Machine, 0, 0, coord.abi.Methods["checkpoint"].Outputs[7].Type) {
		t.Fatal("initial stateDigest mismatch")
	}
	resume := stockS1VerifyResume(t, e, coord, coordAt, 0, 128, 32, stockS1VerifyCallGas)
	if resume.result == nil || resume.result.Err != nil || resume.result.UsedGas > stockS1VerifyCallGas {
		t.Fatalf("resume failed %+v", resume)
	}
	final := stockS1VerifyCheckpointAt(t, e, coord, coordAt)
	if final.Epoch != 1 || final.TotalSteps != 4 || final.Machine.Lifecycle != stockS1VerifyReturned || final.Machine.Result != math.MinInt32+1 || final.Machine.Sp != 0 {
		t.Fatalf("terminal checkpoint=%+v", final)
	}
	dirty := stockS1VerifyDirty(initial.Machine, final.Machine)
	stockS1VerifyCheckEvent(t, coord, resume, final, 4, dirty)
	t.Logf("S1 deployed parser=%dB hash=%s gas=%d module=%dB hash=%s gas=%d raw=%dB metadata=%dB hash=%s registerGas=%d coordinator=%dB hash=%s gas=%d resumeGas=%d", len(parser.runtime), parserHash, parserTx.result.UsedGas, len(module.runtime), moduleHash, moduleTx.result.UsedGas, len(class.bytes), len(metadataCode), metadataHash, registerTx.result.UsedGas, len(e.state.StateDB.GetCode(coordAt)), crypto.Keccak256Hash(e.state.StateDB.GetCode(coordAt)), coordTx.result.UsedGas, resume.result.UsedGas)
}

func stockS1VerifySelectedFailure(t *testing.T, e *stockS1VerifyEnv, page, parser, coord, module stockS1VerifyArtifact, parserAt, moduleAt common.Address, parserHash, moduleHash common.Hash, class stockS1VerifyClass, entry string, args []int32, signature string, words ...any) {
	t.Helper()
	_, _, _, id, _, _, _ := stockS1VerifyDeployRegistered(t, e, page, parser, parserAt, class.bytes)
	nonce := e.state.StateDB.GetNonce(e.sender)
	tx := e.apply(nil, stockS1VerifyConstructor(t, coord, parserAt, parserHash, id, moduleAt, moduleHash, []byte(entry), args, uint64(64)), stockS1VerifyCreateGas)
	stockS1VerifyAssertRevert(t, tx, signature, words...)
	if len(e.state.StateDB.GetCode(crypto.CreateAddress(e.sender, nonce))) != 0 {
		t.Fatal("failed coordinator selection left code")
	}
}

func TestStockS1VerifyParserCapsMetadataCanonicalityAndSelection(t *testing.T) {
	page := stockS1VerifyLoadPage(t)
	parser := stockS1VerifyLoadArtifact(t, "S1ClassParser")
	module := stockS1VerifyLoadArtifact(t, "S1StepModule")
	coord := stockS1VerifyLoadArtifact(t, "S1Coordinator")
	e := stockS1VerifyNewEnv(t)
	defer e.close()
	parserAt, _ := e.mustCreate(parser.init, stockS1VerifyCreateGas)
	moduleAt, _ := e.mustCreate(module.init, stockS1VerifyCreateGas)
	parserHash := crypto.Keccak256Hash(parser.runtime)
	moduleHash := crypto.Keccak256Hash(module.runtime)
	// Retained CP=512 and selected Code=256 boundaries are genuine valid inputs.
	code256 := append(bytes.Repeat([]byte{0x00}, 254), 0x03, 0xac)
	boundary := stockS1VerifyBuildClass("S1Boundary", []stockS1VerifyMethod{{"edge", "()I", 0x0009, code256, 1, 0, 1, 0}}, 512)
	rawAt, pageHash, payloadHash, _ := stockS1VerifyDeployPage(t, e, page, boundary.bytes)
	id, metaAt, metaHash, n, _ := stockS1VerifyRegister(t, e, parser, parserAt, rawAt, pageHash, payloadHash)
	if n != 2 || len(boundary.bytes) > 4096 {
		t.Fatalf("boundary class methods=%d bytes=%d", n, len(boundary.bytes))
	}
	if crypto.Keccak256Hash(e.state.StateDB.GetCode(metaAt)) != metaHash {
		t.Fatal("boundary metadata hash")
	}
	at, _ := stockS1VerifyDeployCoordinator(t, e, coord, parserAt, parserHash, id, moduleAt, moduleHash, "edge", nil, 4096)
	r := stockS1VerifyResume(t, e, coord, at, 0, 128, 32, stockS1VerifyCallGas)
	if r.result.Err != nil {
		t.Fatal(r.result.Err)
	}
	// 32 declared methods and exactly 256 cached literal records produce the
	// maximum frozen aggregate metadata payload, 6,336 bytes, without trailing data.
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
		code = append(code, 0x1a, 0xac)
		methods[i] = stockS1VerifyMethod{fmt.Sprintf("m%02d", i), "()I", 0x0009, code, 1, 1, 1, 0}
	}
	t.Run("declared32-literals256-metadata6336", func(t *testing.T) {
		aggregate := stockS1VerifyBuildClass("S1Aggregate", methods, 0)
		aggregateRawAt, aggregatePageHash, aggregatePayloadHash, _ := stockS1VerifyDeployPage(t, e, page, aggregate.bytes)
		register := e.apply(&parserAt, stockS1VerifyCallData(t, parser, "registerClass", aggregateRawAt, aggregatePageHash, aggregatePayloadHash), stockS1VerifyCreateGas)
		if register.coreErr != nil || register.result == nil || register.result.Err != nil {
			t.Fatalf("exact aggregate registration must fit 8M: core=%v evm=%v data=%x", register.coreErr, stockS1VerifyResultErr(register.result), stockS1VerifyResultData(register.result))
		}
		values := stockS1VerifyUnpack(t, parser, "registerClass", register.result.ReturnData)
		aggregateMetaAt, aggregateMetaHash, aggregateCount := values[1].(common.Address), common.Hash(values[2].([32]byte)), values[3].(uint16)
		metaCode := e.state.StateDB.GetCode(aggregateMetaAt)
		if aggregateCount != 32 || len(metaCode) != 1+6336 || len(metaCode) > 8192 || crypto.Keccak256Hash(metaCode) != aggregateMetaHash {
			t.Fatalf("aggregate methods=%d metadata=%d", aggregateCount, len(metaCode))
		}
		wantMeta := stockS1VerifyMetadataExpected(aggregate.bytes, aggregateRawAt, aggregatePageHash, aggregatePayloadHash)
		if !bytes.Equal(metaCode[1:], wantMeta) {
			t.Fatal("aggregate metadata is not canonical parser-derived schema2")
		}
	})
	// One additional declared method fails at the raw method_count field.
	tooMany := stockS1VerifyBuildClass("S1Methods33", append(methods, stockS1VerifyMethod{"extra", "()I", 0x0009, []byte{3, 0xac}, 1, 0, 1, 0}), 0)
	pa, ph, pvh, _ := stockS1VerifyDeployPage(t, e, page, tooMany.bytes)
	tx := e.apply(&parserAt, stockS1VerifyCallData(t, parser, "registerClass", pa, ph, pvh), stockS1VerifyCreateGas)
	stockS1VerifyAssertRevert(t, tx, "S1ClassError(uint256,uint256)", 5, uint64(tooMany.marks["methodCount"]))
	if at, h := stockS1VerifyClassRecord(t, e, parser, parserAt, common.Hash{}); at != (common.Address{}) || h != (common.Hash{}) {
		t.Fatal("unknown record not zero")
	}
	// One extra literal remains individually valid but violates the aggregate cap.
	methods257 := append([]stockS1VerifyMethod(nil), methods...)
	methods257[3].code = append([]byte{0x12, 10, 0x3b}, methods257[3].code...)
	literal257 := stockS1VerifyBuildClass("S1Literal257", methods257, 0)
	pa, ph, pvh, _ = stockS1VerifyDeployPage(t, e, page, literal257.bytes)
	tx = e.apply(&parserAt, stockS1VerifyCallData(t, parser, "registerClass", pa, ph, pvh), stockS1VerifyCreateGas)
	stockS1VerifyAssertRevert(t, tx, "S1ClassError(uint256,uint256)", 5, 0)
	// cp_count itself is still capped at 512, independently of payload size.
	cp513 := stockS1VerifyBuildClass("S1CP513", []stockS1VerifyMethod{{"entry", "()I", 0x0009, []byte{3, 0xac}, 1, 0, 1, 0}}, 513)
	pa, ph, pvh, _ = stockS1VerifyDeployPage(t, e, page, cp513.bytes)
	tx = e.apply(&parserAt, stockS1VerifyCallData(t, parser, "registerClass", pa, ph, pvh), stockS1VerifyCreateGas)
	stockS1VerifyAssertRevert(t, tx, "S1ClassError(uint256,uint256)", 3, uint64(cp513.marks["cpCount"]))
	// Code=257 and an unsupported opcode in an unused method are records, not
	// class-registration failures. Selecting them returns the recorded error.
	unused := stockS1VerifyBuildClass("S1Unused", []stockS1VerifyMethod{{"good", "()I", 0x0009, []byte{0x08, 0xac}, 1, 0, 1, 0}, {"bad", "()I", 0x0009, []byte{0xb1}, 1, 0, 1, 0}, {"long", "()I", 0x0009, make([]byte, 257), 1, 0, 1, 0}}, 0)
	rawAt, pageHash, payloadHash, id, _, _, _ = stockS1VerifyDeployRegistered(t, e, page, parser, parserAt, unused.bytes)
	good, _ := stockS1VerifyDeployCoordinator(t, e, coord, parserAt, parserHash, id, moduleAt, moduleHash, "good", nil, 64)
	tx = stockS1VerifyResume(t, e, coord, good, 0, 16, 32, stockS1VerifyCallGas)
	if tx.result.Err != nil || stockS1VerifyCheckpointAt(t, e, coord, good).Machine.Result != 5 {
		t.Fatal("unused invalid method poisoned valid selection")
	}
	stockS1VerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, unused, "bad", nil, "S1BytecodeError(uint256,uint256)", 6, 0)
	stockS1VerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, unused, "long", nil, "S1MethodError(uint256,uint256)", 5, 3)
	// Missing, ambiguity, invalid entry bytes and priority access->descriptor->Code->args.
	stockS1VerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, unused, "missing", nil, "S1MethodError(uint256,uint256)", 1, stockS1VerifyMaxUint256)
	ambiguous := stockS1VerifyBuildClass("S1Ambiguous", []stockS1VerifyMethod{{"same", "()I", 0x0009, []byte{3, 0xac}, 1, 0, 1, 0}, {"same", "(I)I", 0x0009, []byte{0x1a, 0xac}, 1, 1, 1, 0}}, 0)
	stockS1VerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, ambiguous, "same", nil, "S1MethodError(uint256,uint256)", 2, 2)
	for _, bad := range [][]byte{nil, {}, []byte("a/b"), []byte{'x', 0}, []byte{0x80}} {
		_, _, _, id, _, _, _ := stockS1VerifyDeployRegistered(t, e, page, parser, parserAt, stockS1VerifySimpleClass([]byte{3, 0xac}, 1, 0, "()I").bytes)
		tx = e.apply(nil, stockS1VerifyConstructor(t, coord, parserAt, parserHash, id, moduleAt, moduleHash, bad, []int32{}, uint64(64)), stockS1VerifyCreateGas)
		stockS1VerifyAssertRevert(t, tx, "S1MethodError(uint256,uint256)", 8, stockS1VerifyMaxUint256)
	}
	priority := stockS1VerifyBuildClass("S1Priority", []stockS1VerifyMethod{{"pick", "()V", 0x0001, nil, 0, 0, 1, 0}}, 0)
	stockS1VerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, priority, "pick", []int32{1}, "S1MethodError(uint256,uint256)", 3, 1)
	descriptor := stockS1VerifyBuildClass("S1Descriptor", []stockS1VerifyMethod{{"pick", "()V", 0x0009, []byte{0xb1}, 0, 0, 1, 0}}, 0)
	stockS1VerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, descriptor, "pick", []int32{1}, "S1MethodError(uint256,uint256)", 4, 1)
	argsMismatch := stockS1VerifySimpleClass([]byte{0x1a, 0xac}, 1, 1, "(I)I")
	stockS1VerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, argsMismatch, "entry", nil, "S1MethodError(uint256,uint256)", 7, 1)
	_ = module
}

type stockS1VerifyBytecodeCase struct {
	name     string
	class    stockS1VerifyClass
	entry    string
	args     []int32
	code, pc uint64
}

func TestStockS1VerifyNegativeCatalogueBranchesAndOperands(t *testing.T) {
	page := stockS1VerifyLoadPage(t)
	parser := stockS1VerifyLoadArtifact(t, "S1ClassParser")
	module := stockS1VerifyLoadArtifact(t, "S1StepModule")
	coord := stockS1VerifyLoadArtifact(t, "S1Coordinator")
	e := stockS1VerifyNewEnv(t)
	defer e.close()
	parserAt, _ := e.mustCreate(parser.init, stockS1VerifyCreateGas)
	moduleAt, _ := e.mustCreate(module.init, stockS1VerifyCreateGas)
	parserHash, moduleHash := crypto.Keccak256Hash(parser.runtime), crypto.Keccak256Hash(module.runtime)
	b := []stockS1VerifyBytecodeCase{
		{"B01-branch-no-operands", stockS1VerifySimpleClass([]byte{0xa7}, 1, 0, "()I"), "entry", nil, 2, 0},
		{"B02-branch-one-operand", stockS1VerifySimpleClass([]byte{0xa7, 0}, 1, 0, "()I"), "entry", nil, 2, 0},
		{"B03-min-s16-from-nonzero", stockS1VerifySimpleClass([]byte{0, 0xa7, 0x80, 0}, 1, 0, "()I"), "entry", nil, 15, 1},
		{"B04-negative-one", stockS1VerifySimpleClass([]byte{0xa7, 0xff, 0xff}, 1, 0, "()I"), "entry", nil, 15, 0},
		{"B06-target-first-operand", stockS1VerifySimpleClass([]byte{0xa7, 0, 1}, 1, 0, "()I"), "entry", nil, 15, 0},
		{"B07-max-s16", stockS1VerifySimpleClass([]byte{0xa7, 0x7f, 0xff}, 1, 0, "()I"), "entry", nil, 15, 0},
		{"B08-exact-negative-one", stockS1VerifySimpleClass([]byte{0, 0, 0, 0xa7, 0xff, 0xfc}, 1, 0, "()I"), "entry", nil, 15, 3},
		{"B09-target-code-length", stockS1VerifySimpleClass([]byte{0xa7, 0, 3}, 1, 0, "()I"), "entry", nil, 15, 0},
		{"B10-target-after-code", stockS1VerifySimpleClass([]byte{0xa7, 0, 4}, 1, 0, "()I"), "entry", nil, 15, 0},
		{"B11-target-sipush-middle", stockS1VerifySimpleClass([]byte{0xa7, 0, 4, 0x11, 0, 1, 0xac}, 1, 0, "()I"), "entry", nil, 15, 0},
		{"B12-target-iinc-operand", stockS1VerifySimpleClass([]byte{0xa7, 0, 4, 0x84, 0, 1, 3, 0xac}, 1, 1, "()I"), "entry", nil, 15, 0},
		{"B13-unreachable-bad-target", stockS1VerifySimpleClass([]byte{3, 0xac, 0xa7, 0, 1}, 1, 0, "()I"), "entry", nil, 15, 2},
		{"B14-unreachable-unsupported", stockS1VerifySimpleClass([]byte{3, 0xac, 0xb1}, 1, 0, "()I"), "entry", nil, 6, 2},
	}
	for _, tc := range b {
		t.Run(tc.name, func(t *testing.T) {
			stockS1VerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, tc.class, tc.entry, tc.args, "S1BytecodeError(uint256,uint256)", tc.code, tc.pc)
		})
	}
	// B05: offset zero is valid and identical-PC progress is not rejected. The
	// coordinator emits lifecycle STEP_LIMIT at each committed exact cap.
	self := stockS1VerifySimpleClass([]byte{0xa7, 0, 0}, 0, 0, "()I")
	for _, cap := range []uint64{1, 128, 4096} {
		t.Run(fmt.Sprintf("B05-zero-offset-cap-%d", cap), func(t *testing.T) {
			_, _, _, id, _, _, _ := stockS1VerifyDeployRegistered(t, e, page, parser, parserAt, self.bytes)
			at, _ := stockS1VerifyDeployCoordinator(t, e, coord, parserAt, parserHash, id, moduleAt, moduleHash, "entry", nil, cap)
			before := stockS1VerifyCheckpointAt(t, e, coord, at)
			for before.Machine.Lifecycle == stockS1VerifyRunnable {
				r := stockS1VerifyResume(t, e, coord, at, before.Epoch, 128, 32, stockS1VerifyCallGas)
				if r.result.Err != nil {
					t.Fatalf("same-PC progress failed: %v", r.result.Err)
				}
				after := stockS1VerifyCheckpointAt(t, e, coord, at)
				if after.Epoch != before.Epoch+1 || after.TotalSteps <= before.TotalSteps || after.Machine.Pc != 0 {
					t.Fatalf("same-PC transition before=%+v after=%+v", before, after)
				}
				before = after
			}
			if before.TotalSteps != cap || before.Machine.Lifecycle != stockS1VerifyStepLimit || before.Machine.Result != 0 {
				t.Fatalf("cap checkpoint=%+v", before)
			}
			failed := stockS1VerifyResume(t, e, coord, at, before.Epoch, 1, 32, stockS1VerifyCallGas)
			stockS1VerifyAssertRevert(t, failed, "S1ControlError(uint256)", 1)
		})
	}
	o := []stockS1VerifyBytecodeCase{
		{"O01-unary-underflow", stockS1VerifySimpleClass([]byte{0x99, 0, 3, 3, 0xac}, 1, 0, "()I"), "entry", nil, 3, 0},
		{"O02-binary-zero-operands", stockS1VerifySimpleClass([]byte{0x9f, 0, 3, 3, 0xac}, 2, 0, "()I"), "entry", nil, 3, 0},
		{"O03-binary-one-operand", stockS1VerifySimpleClass([]byte{3, 0x9f, 0, 3, 3, 0xac}, 2, 0, "()I"), "entry", nil, 3, 1},
		{"O04-branch-path-capacity", stockS1VerifySimpleClass([]byte{0x1a, 0x99, 0, 7, 3, 4, 0x60, 0xac, 3, 0xac}, 1, 1, "(I)I"), "entry", []int32{1}, 9, 5},
		{"O05-generic-local-range", stockS1VerifySimpleClass([]byte{0x15, 1, 0xac}, 1, 1, "()I"), "entry", nil, 8, 0},
		{"O06-compact-local-range", stockS1VerifySimpleClass([]byte{0x1b, 0xac}, 1, 1, "()I"), "entry", nil, 8, 0},
		{"O07-first-extra-local-uninitialized", stockS1VerifySimpleClass([]byte{0x1b, 0xac}, 1, 2, "(I)I"), "entry", []int32{7}, 11, 0},
		{"O08-one-predecessor-initialized", stockS1VerifySimpleClass([]byte{0x1a, 0x99, 0, 9, 4, 0x3c, 0xa7, 0, 4, 0, 0x1b, 0xac}, 1, 2, "(I)I"), "entry", []int32{0}, 11, 10},
		{"O09-join-stack-height", stockS1VerifySimpleClass([]byte{0x1a, 0x99, 0, 8, 4, 0xa7, 0, 4, 0, 3, 0xac}, 2, 1, "(I)I"), "entry", []int32{1}, 5, 9},
		{"O10-fallthrough", stockS1VerifySimpleClass([]byte{3}, 1, 0, "()I"), "entry", nil, 7, 0},
		{"O11-return-empty", stockS1VerifySimpleClass([]byte{0xac}, 1, 0, "()I"), "entry", nil, 5, 0},
		{"O12-return-two", stockS1VerifySimpleClass([]byte{3, 4, 0xac}, 2, 0, "()I"), "entry", nil, 5, 2},
	}
	for _, tc := range o {
		t.Run(tc.name, func(t *testing.T) {
			stockS1VerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, tc.class, tc.entry, tc.args, "S1BytecodeError(uint256,uint256)", tc.code, tc.pc)
		})
	}
}

func TestStockS1VerifySignedBranchesLocalsAndReturnPrecedence(t *testing.T) {
	page := stockS1VerifyLoadPage(t)
	parser := stockS1VerifyLoadArtifact(t, "S1ClassParser")
	module := stockS1VerifyLoadArtifact(t, "S1StepModule")
	coord := stockS1VerifyLoadArtifact(t, "S1Coordinator")
	e := stockS1VerifyNewEnv(t)
	defer e.close()
	parserAt, _ := e.mustCreate(parser.init, stockS1VerifyCreateGas)
	moduleAt, _ := e.mustCreate(module.init, stockS1VerifyCreateGas)
	parserHash, moduleHash := crypto.Keccak256Hash(parser.runtime), crypto.Keccak256Hash(module.runtime)
	methods := []stockS1VerifyMethod{
		{"signed", "(II)I", 0x0009, []byte{0x1a, 0x1b, 0xa2, 0, 5, 0x02, 0xac, 0x04, 0xac}, 2, 2, 1, 0},
		// Includes the frozen real backward edge 13 + (-11) = 2.
		{"loop", "(I)I", 0x0009, []byte{3, 0x3c, 0x1b, 0x1a, 0xa2, 0, 12, 0x84, 1, 1, 0, 0, 0, 0xa7, 0xff, 0xf5, 0x1b, 0xac}, 2, 2, 1, 0},
		{"locals6", "(IIII)I", 0x0009, []byte{0x1a, 0x1b, 0x60, 0x3b, 0x1c, 0x1d, 0x60, 0x36, 5, 0x1a, 0x15, 5, 0x60, 0xac}, 2, 6, 1, 0},
		{"three", "(III)I", 0x0009, []byte{0x1a, 0x1b, 0x60, 0x1c, 0x60, 0xac}, 2, 3, 1, 0},
		{"exact", "()I", 0x0009, []byte{4, 0xac}, 1, 0, 1, 0},
	}
	class := stockS1VerifyBuildClass("S1Positive", methods, 0)
	_, _, _, id, _, _, _ := stockS1VerifyDeployRegistered(t, e, page, parser, parserAt, class.bytes)
	cases := []struct {
		name, entry string
		args        []int32
		want        int32
		steps, cap  uint64
	}{{"signed-min-max", "signed", []int32{math.MinInt32, math.MaxInt32}, -1, 5, 64}, {"signed-max-min", "signed", []int32{math.MaxInt32, math.MinInt32}, 1, 5, 64}, {"loop-backward", "loop", []int32{3}, 3, 31, 64}, {"locals6-minmax", "locals6", []int32{math.MinInt32, math.MaxInt32, -1, 1}, -1, 12, 64}, {"argc3-minmax", "three", []int32{math.MinInt32, math.MaxInt32, 1}, 0, 6, 64}, {"returned-wins-at-cap", "exact", nil, 1, 2, 2}}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			at, _ := stockS1VerifyDeployCoordinator(t, e, coord, parserAt, parserHash, id, moduleAt, moduleHash, tc.entry, tc.args, tc.cap)
			var executed uint64
			for {
				c := stockS1VerifyCheckpointAt(t, e, coord, at)
				if c.Machine.Lifecycle != 0 {
					if c.Machine.Lifecycle != stockS1VerifyReturned || c.Machine.Result != tc.want || c.TotalSteps != tc.steps || executed != tc.steps {
						t.Fatalf("terminal=%+v executed=%d", c, executed)
					}
					break
				}
				r := stockS1VerifyResume(t, e, coord, at, c.Epoch, 1, 32, stockS1VerifyCallGas)
				if r.result.Err != nil {
					t.Fatal(r.result.Err)
				}
				executed++
			}
		})
	}
	// Arguments cover 0..4, MIN/MAX, and exactly local index 5. maxLocals below
	// argc is a recorded MethodError(5), while maxLocals=6 above is accepted.
	tooFew := stockS1VerifyBuildClass("S1TooFew", []stockS1VerifyMethod{{"entry", "(IIII)I", 0x0009, []byte{0x1a, 0xac}, 1, 3, 1, 0}}, 0)
	stockS1VerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, tooFew, "entry", []int32{1, 2, 3, 4}, "S1MethodError(uint256,uint256)", 5, 1)
}

func stockS1VerifyProgramCall(t *testing.T, e *stockS1VerifyEnv, module stockS1VerifyArtifact, moduleAt common.Address, p stockS1VerifyProgram, m stockS1VerifyMachine, budget uint16, gas uint64) stockS1VerifyTx {
	t.Helper()
	return e.apply(&moduleAt, stockS1VerifyCallData(t, module, "step", p, m, budget), gas)
}
func stockS1VerifyProgramContext(t *testing.T, e *stockS1VerifyEnv, coord stockS1VerifyArtifact, at common.Address) stockS1VerifyProgram {
	t.Helper()
	r := e.mustCall(at, stockS1VerifyCallData(t, coord, "programContext"), stockS1VerifyCallGas)
	return stockS1VerifyProgramFrom(stockS1VerifyUnpack(t, coord, "programContext", r.result.ReturnData)[0])
}
func stockS1VerifyFakeStepRuntime(machine stockS1VerifyMachine, executed uint16, loopUnlessBudgetOne bool) []byte {
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
	words = append(words, new(big.Int).SetUint64(uint64(executed)))
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

func stockS1VerifyOOGAfterCallRuntime(target common.Address, calldata []byte) []byte {
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

func TestStockS1VerifyNegativeCatalogueCommitmentsAtomicityAndGas(t *testing.T) {
	page := stockS1VerifyLoadPage(t)
	parser := stockS1VerifyLoadArtifact(t, "S1ClassParser")
	module := stockS1VerifyLoadArtifact(t, "S1StepModule")
	coord := stockS1VerifyLoadArtifact(t, "S1Coordinator")
	metadata := stockS1VerifyLoadArtifact(t, "S1MetadataPage")
	e := stockS1VerifyNewEnv(t)
	defer e.close()
	parserAt, _ := e.mustCreate(parser.init, stockS1VerifyCreateGas)
	moduleAt, _ := e.mustCreate(module.init, stockS1VerifyCreateGas)
	parserHash, moduleHash := crypto.Keccak256Hash(parser.runtime), crypto.Keccak256Hash(module.runtime)
	class := stockS1VerifySimpleClass([]byte{0x1a, 4, 0x60, 0x3b, 0x1a, 0xac}, 2, 1, "(I)I")
	rawAt, pageHash, payloadHash, id, metadataAt, metadataHash, _ := stockS1VerifyDeployRegistered(t, e, page, parser, parserAt, class.bytes)
	t.Run("C01-wrong-raw-page-payload-hash", func(t *testing.T) {
		bad := pageHash
		bad[0] ^= 1
		r := e.apply(&parserAt, stockS1VerifyCallData(t, parser, "registerClass", rawAt, bad, payloadHash), stockS1VerifyCallGas)
		stockS1VerifyAssertRevert(t, r, "StockPageError(uint256)", 3)
		bad = payloadHash
		bad[0] ^= 1
		r = e.apply(&parserAt, stockS1VerifyCallData(t, parser, "registerClass", rawAt, pageHash, bad), stockS1VerifyCallGas)
		stockS1VerifyAssertRevert(t, r, "StockPageError(uint256)", 4)
	})
	baseAt, _ := stockS1VerifyDeployCoordinator(t, e, coord, parserAt, parserHash, id, moduleAt, moduleHash, "entry", []int32{7}, 64)
	program := stockS1VerifyProgramContext(t, e, coord, baseAt)
	machine := stockS1VerifyCheckpointAt(t, e, coord, baseAt).Machine
	directControl2 := func(t *testing.T, p stockS1VerifyProgram) {
		r := stockS1VerifyProgramCall(t, e, module, moduleAt, p, machine, 1, stockS1VerifyCallGas)
		stockS1VerifyAssertRevert(t, r, "S1ControlError(uint256)", 2)
	}
	t.Run("C02-wrong-EVM-metadata-hash-and-fake-page", func(t *testing.T) {
		fakePayload := append([]byte(nil), e.state.StateDB.GetCode(metadataAt)[1:]...)
		fakePayload[0] ^= 1
		fakeAt, _ := e.mustCreate(stockS1VerifyConstructor(t, metadata, fakePayload), stockS1VerifyCreateGas)
		p := program
		p.MetadataPage = fakeAt
		p.MetadataHash = [32]byte(crypto.Keccak256Hash(e.state.StateDB.GetCode(fakeAt)))
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
				init = stockS1VerifyConstructor(t, coord, parserAt, bad, id, moduleAt, moduleHash, []byte("entry"), []int32{7}, uint64(64))
			} else {
				init = stockS1VerifyConstructor(t, coord, parserAt, parserHash, id, moduleAt, bad, []byte("entry"), []int32{7}, uint64(64))
			}
			r := e.apply(nil, init, stockS1VerifyCreateGas)
			stockS1VerifyAssertRevert(t, r, "S1ControlError(uint256)", 2)
			if len(e.state.StateDB.GetCode(crypto.CreateAddress(e.sender, nonce))) != 0 {
				t.Fatal("hash mismatch left coordinator")
			}
		}
	})
	t.Run("C04-wrong-declared-class-component", func(t *testing.T) { p := program; p.ClassId[0] ^= 1; directControl2(t, p) })
	t.Run("C05-missing-wrong-ambiguous-method", func(t *testing.T) {
		stockS1VerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, class, "wrong", []int32{7}, "S1MethodError(uint256,uint256)", 1, stockS1VerifyMaxUint256)
		amb := stockS1VerifyBuildClass("S1C05", []stockS1VerifyMethod{{"same", "()I", 9, []byte{3, 0xac}, 1, 0, 1, 0}, {"same", "(I)I", 9, []byte{0x1a, 0xac}, 1, 1, 1, 0}}, 0)
		stockS1VerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, amb, "same", nil, "S1MethodError(uint256,uint256)", 2, 2)
	})
	t.Run("C06-descriptor-argc-mismatch", func(t *testing.T) {
		stockS1VerifySelectedFailure(t, e, page, parser, coord, module, parserAt, moduleAt, parserHash, moduleHash, class, "entry", nil, "S1MethodError(uint256,uint256)", 7, 1)
	})
	t.Run("C07-one-nonzero-argument-bit-changes-root", func(t *testing.T) {
		otherAt, _ := stockS1VerifyDeployCoordinator(t, e, coord, parserAt, parserHash, id, moduleAt, moduleHash, "entry", []int32{6}, 64)
		other := stockS1VerifyCheckpointAt(t, e, coord, otherAt)
		base := stockS1VerifyCheckpointAt(t, e, coord, baseAt)
		if other.ProgramID != base.ProgramID || other.InputRoot == base.InputRoot || stockS1VerifyProgramContext(t, e, coord, otherAt).ProgramId != program.ProgramId {
			t.Fatal("argument mutation was not isolated to args/input commitment")
		}
		if other.Machine.Locals[0].Cmp(stockS1VerifyTagged(6)) != 0 || base.Machine.Locals[0].Cmp(stockS1VerifyTagged(7)) != 0 {
			t.Fatal("committed argument local mismatch")
		}
	})
	t.Run("C08-wrong-schema-program-root", func(t *testing.T) { p := program; p.ProgramId[0] ^= 1; directControl2(t, p) })
	t.Run("C09-stale-epoch-before-first-resume", func(t *testing.T) {
		before := stockS1VerifyCheckpointAt(t, e, coord, baseAt)
		r := stockS1VerifyResume(t, e, coord, baseAt, 1, 1, 32, stockS1VerifyCallGas)
		stockS1VerifyAssertRevert(t, r, "S1ControlError(uint256)", 3)
		stockS1VerifyAssertRollback(t, e, coord, baseAt, before, r)
	})
	t.Run("C12-dirty-cap-first-argument-checkpoint", func(t *testing.T) {
		before := stockS1VerifyCheckpointAt(t, e, coord, baseAt)
		r := stockS1VerifyResume(t, e, coord, baseAt, 0, 3, 1, stockS1VerifyCallGas)
		stockS1VerifyAssertRevert(t, r, "S1ControlError(uint256)", 6)
		stockS1VerifyAssertRollback(t, e, coord, baseAt, before, r)
	})
	t.Run("C18-reserve-before-progress", func(t *testing.T) {
		before := stockS1VerifyCheckpointAt(t, e, coord, baseAt)
		r := stockS1VerifyResume(t, e, coord, baseAt, 0, 3, 32, stockS1VerifyReserve-50_000)
		stockS1VerifyAssertRevert(t, r, "S1ControlError(uint256)", 5)
		stockS1VerifyAssertRollback(t, e, coord, baseAt, before, r)
	})
	first := stockS1VerifyResume(t, e, coord, baseAt, 0, 3, 32, stockS1VerifyCallGas)
	if first.result.Err != nil {
		t.Fatal(first.result.Err)
	}
	progress := stockS1VerifyCheckpointAt(t, e, coord, baseAt)
	if progress.Epoch != 1 || progress.TotalSteps != 3 || progress.Machine.Stack[0].Cmp(stockS1VerifyTagged(8)) != 0 || progress.Machine.Locals[0].Cmp(stockS1VerifyTagged(7)) != 0 {
		t.Fatalf("nonzero progress=%+v", progress)
	}
	for _, tc := range []struct {
		name  string
		epoch uint64
		dirty uint8
		gas   uint64
		code  uint64
	}{{"C10-stale-epoch-after-progress", 0, 32, stockS1VerifyCallGas, 3}, {"C13-dirty-cap-after-progress", 1, 1, stockS1VerifyCallGas, 6}, {"C18-reserve-after-progress", 1, 32, stockS1VerifyReserve - 50_000, 5}} {
		t.Run(tc.name, func(t *testing.T) {
			before := stockS1VerifyCheckpointAt(t, e, coord, baseAt)
			r := stockS1VerifyResume(t, e, coord, baseAt, tc.epoch, 2, tc.dirty, tc.gas)
			stockS1VerifyAssertRevert(t, r, "S1ControlError(uint256)", tc.code)
			stockS1VerifyAssertRollback(t, e, coord, baseAt, before, r)
		})
	}
	// C11 uses a real valid goto 0 checkpoint; stale epoch remains stale even
	// though PC and all machine words are identical.
	t.Run("C11-stale-after-legitimate-same-PC", func(t *testing.T) {
		self := stockS1VerifySimpleClass([]byte{0xa7, 0, 0}, 0, 0, "()I")
		_, _, _, sid, _, _, _ := stockS1VerifyDeployRegistered(t, e, page, parser, parserAt, self.bytes)
		at, _ := stockS1VerifyDeployCoordinator(t, e, coord, parserAt, parserHash, sid, moduleAt, moduleHash, "entry", nil, 128)
		ok := stockS1VerifyResume(t, e, coord, at, 0, 16, 32, stockS1VerifyCallGas)
		if ok.result.Err != nil {
			t.Fatal(ok.result.Err)
		}
		before := stockS1VerifyCheckpointAt(t, e, coord, at)
		r := stockS1VerifyResume(t, e, coord, at, 0, 16, 32, stockS1VerifyCallGas)
		stockS1VerifyAssertRevert(t, r, "S1ControlError(uint256)", 3)
		stockS1VerifyAssertRollback(t, e, coord, at, before, r)
	})
	t.Run("C14-dirty-cap-terminal-return", func(t *testing.T) {
		terminal := stockS1VerifySimpleClass([]byte{0x1a, 0xac}, 1, 1, "(I)I")
		_, _, _, tid, _, _, _ := stockS1VerifyDeployRegistered(t, e, page, parser, parserAt, terminal.bytes)
		at, _ := stockS1VerifyDeployCoordinator(t, e, coord, parserAt, parserHash, tid, moduleAt, moduleHash, "entry", []int32{9}, 2)
		before := stockS1VerifyCheckpointAt(t, e, coord, at)
		r := stockS1VerifyResume(t, e, coord, at, 0, 2, 1, stockS1VerifyCallGas)
		stockS1VerifyAssertRevert(t, r, "S1ControlError(uint256)", 6)
		stockS1VerifyAssertRollback(t, e, coord, at, before, r)
	})
	t.Run("C15-parser-OOG-atomic-registry-and-code", func(t *testing.T) {
		fresh := stockS1VerifySimpleClass([]byte{3, 0xac}, 1, 0, "()I")
		pa, ph, pvh, _ := stockS1VerifyDeployPage(t, e, page, fresh.bytes)
		expectedMeta := append([]byte{0}, stockS1VerifyMetadataExpected(fresh.bytes, pa, ph, pvh)...)
		expectedID := stockS1VerifyClassID(t, parserHash, pa, ph, pvh, crypto.Keccak256Hash(expectedMeta))
		internal := crypto.CreateAddress(parserAt, e.state.StateDB.GetNonce(parserAt))
		nonce := e.state.StateDB.GetNonce(e.sender)
		balance := e.state.StateDB.GetBalance(e.sender).ToBig()
		r := e.apply(&parserAt, stockS1VerifyCallData(t, parser, "registerClass", pa, ph, pvh), 150_000)
		if r.coreErr != nil || r.result == nil || !errors.Is(r.result.Err, vm.ErrOutOfGas) || len(r.result.ReturnData) != 0 {
			t.Fatalf("registration OOG identity core=%v evm=%v data=%x", r.coreErr, stockS1VerifyResultErr(r.result), stockS1VerifyResultData(r.result))
		}
		if e.state.StateDB.GetNonce(e.sender) != nonce+1 || e.state.StateDB.GetBalance(e.sender).ToBig().Cmp(balance) >= 0 {
			t.Fatal("failed registration sender effects")
		}
		if at, h := stockS1VerifyClassRecord(t, e, parser, parserAt, expectedID); at != (common.Address{}) || h != (common.Hash{}) {
			t.Fatal("OOG registration left registry")
		}
		if len(e.state.StateDB.GetCode(internal)) != 0 {
			t.Fatal("OOG registration left metadata code")
		}
	})
	// A fake module is a normally deployed configuration commitment, never an
	// attested artifact. It can test response validation and nested OOG safely.
	fakeAfter := stockS1VerifyZeroMachine()
	fakeAfter.Pc = 1
	fakeAfter.Sp = 1
	fakeAfter.Initialized = 1
	fakeAfter.Stack[0] = stockS1VerifyTagged(7)
	fakeAfter.Locals[0] = stockS1VerifyTagged(7)
	fakeCode := stockS1VerifyFakeStepRuntime(fakeAfter, 1, true)
	fakeAt, _ := stockS1VerifyDeployRaw(t, e, fakeCode, stockS1VerifyCreateGas)
	fakeHash := crypto.Keccak256Hash(fakeCode)
	fakeCoord, _ := stockS1VerifyDeployCoordinator(t, e, coord, parserAt, parserHash, id, fakeAt, fakeHash, "entry", []int32{7}, 64)
	ok := stockS1VerifyResume(t, e, coord, fakeCoord, 0, 1, 32, stockS1VerifyCallGas)
	if ok.result.Err != nil {
		t.Fatalf("fake progress setup: %v %x", ok.result.Err, ok.result.ReturnData)
	}
	t.Run("C16-module-OOG-after-progress", func(t *testing.T) {
		before := stockS1VerifyCheckpointAt(t, e, coord, fakeCoord)
		r := stockS1VerifyResume(t, e, coord, fakeCoord, 1, 2, 32, stockS1VerifyCallGas)
		if r.coreErr != nil || r.result == nil || !errors.Is(r.result.Err, vm.ErrExecutionReverted) || len(r.result.ReturnData) != 0 {
			t.Fatalf("nested OOG identity core=%v evm=%v data=%x", r.coreErr, stockS1VerifyResultErr(r.result), stockS1VerifyResultData(r.result))
		}
		stockS1VerifyAssertRollback(t, e, coord, fakeCoord, before, r)
	})
	t.Run("C17-transaction-OOG-during-commit-after-progress", func(t *testing.T) {
		before := stockS1VerifyCheckpointAt(t, e, coord, baseAt)
		resumeData := stockS1VerifyCallData(t, coord, "resume", before.Epoch, uint16(3), uint8(32))
		wrapperCode := stockS1VerifyOOGAfterCallRuntime(baseAt, resumeData)
		wrapper, _ := stockS1VerifyDeployRaw(t, e, wrapperCode, stockS1VerifyCreateGas)
		r := e.apply(&wrapper, nil, stockS1VerifyCallGas)
		if r.coreErr != nil || r.result == nil || !errors.Is(r.result.Err, vm.ErrOutOfGas) || len(r.result.ReturnData) != 0 {
			t.Fatalf("post-commit transaction OOG core=%v evm=%v data=%x", r.coreErr, stockS1VerifyResultErr(r.result), stockS1VerifyResultData(r.result))
		}
		stockS1VerifyAssertRollback(t, e, coord, baseAt, before, r)
	})
	finalTx := stockS1VerifyResume(t, e, coord, baseAt, progress.Epoch, 128, 32, stockS1VerifyCallGas)
	if finalTx.result.Err != nil {
		t.Fatal(finalTx.result.Err)
	}
	final := stockS1VerifyCheckpointAt(t, e, coord, baseAt)
	if final.Machine.Lifecycle != stockS1VerifyReturned || final.Machine.Result != 8 {
		t.Fatalf("final=%+v", final)
	}
	t.Run("C19-resume-after-terminal", func(t *testing.T) {
		r := stockS1VerifyResume(t, e, coord, baseAt, final.Epoch, 1, 32, stockS1VerifyCallGas)
		stockS1VerifyAssertRevert(t, r, "S1ControlError(uint256)", 1)
		stockS1VerifyAssertRollback(t, e, coord, baseAt, final, r)
	})
	t.Run("C20-exact-cap-is-success-STEP_LIMIT-not-Java", func(t *testing.T) {
		self := stockS1VerifySimpleClass([]byte{0xa7, 0, 0}, 0, 0, "()I")
		_, _, _, sid, _, _, _ := stockS1VerifyDeployRegistered(t, e, page, parser, parserAt, self.bytes)
		at, _ := stockS1VerifyDeployCoordinator(t, e, coord, parserAt, parserHash, sid, moduleAt, moduleHash, "entry", nil, 1)
		r := stockS1VerifyResume(t, e, coord, at, 0, 128, 32, stockS1VerifyCallGas)
		if r.result.Err != nil {
			t.Fatal(r.result.Err)
		}
		c := stockS1VerifyCheckpointAt(t, e, coord, at)
		if c.Machine.Lifecycle != stockS1VerifyStepLimit || c.TotalSteps != 1 || c.Machine.Result != 0 {
			t.Fatalf("step-limit checkpoint=%+v", c)
		}
	})
	// Every logical machine word changed in this conservative synthetic bound;
	// on-chain calls accept 32 while exact reports never exceed 24.
	a := stockS1VerifyZeroMachine()
	b := stockS1VerifyCloneMachine(a)
	b.Pc = 1
	b.Sp = 8
	b.Initialized = 0xff
	b.Lifecycle = stockS1VerifyReturned
	b.Result = 1
	for i := range b.Stack {
		b.Stack[i] = stockS1VerifyTagged(uint32(i + 1))
		b.Locals[i] = stockS1VerifyTagged(uint32(i + 9))
	}
	if got := stockS1VerifyDirty(a, b); got != 24 || got > 32 {
		t.Fatalf("all-dirty conservative count=%d", got)
	}
	_ = metadataHash
}

type stockS1VerifyReplayRecord struct {
	hashes        []common.Hash
	gas           []uint64
	outputs, logs [][]byte
	addresses     []common.Address
	codeHashes    []common.Hash
	checkpoint    stockS1VerifyCheckpoint
	root          common.Hash
}

func stockS1VerifyReplay(t *testing.T) stockS1VerifyReplayRecord {
	t.Helper()
	page := stockS1VerifyLoadPage(t)
	parser := stockS1VerifyLoadArtifact(t, "S1ClassParser")
	module := stockS1VerifyLoadArtifact(t, "S1StepModule")
	coord := stockS1VerifyLoadArtifact(t, "S1Coordinator")
	e := stockS1VerifyNewEnv(t)
	defer e.close()
	var rec stockS1VerifyReplayRecord
	capture := func(r stockS1VerifyTx) {
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
	parserAt, tx := e.mustCreate(parser.init, stockS1VerifyCreateGas)
	capture(tx)
	moduleAt, tx := e.mustCreate(module.init, stockS1VerifyCreateGas)
	capture(tx)
	class := stockS1VerifySimpleClass([]byte{0x1a, 4, 0x60, 0x3b, 0x1a, 0xac}, 2, 1, "(I)I")
	rawAt, ph, pvh, pageTx := stockS1VerifyDeployPage(t, e, page, class.bytes)
	capture(pageTx)
	id, metaAt, _, _, reg := stockS1VerifyRegister(t, e, parser, parserAt, rawAt, ph, pvh)
	capture(reg)
	at, create := stockS1VerifyDeployCoordinator(t, e, coord, parserAt, crypto.Keccak256Hash(parser.runtime), id, moduleAt, crypto.Keccak256Hash(module.runtime), "entry", []int32{41}, 64)
	capture(create)
	for epoch := uint64(0); epoch < 2; epoch++ {
		r := stockS1VerifyResume(t, e, coord, at, epoch, 3, 32, stockS1VerifyCallGas)
		if r.result.Err != nil {
			t.Fatal(r.result.Err)
		}
		capture(r)
	}
	rec.checkpoint = stockS1VerifyCheckpointAt(t, e, coord, at)
	if rec.checkpoint.Machine.Lifecycle != stockS1VerifyReturned || rec.checkpoint.Machine.Result != 42 || rec.checkpoint.TotalSteps != 6 {
		t.Fatalf("replay terminal=%+v", rec.checkpoint)
	}
	rec.addresses = []common.Address{parserAt, moduleAt, rawAt, metaAt, at}
	for _, address := range rec.addresses {
		rec.codeHashes = append(rec.codeHashes, crypto.Keccak256Hash(e.state.StateDB.GetCode(address)))
	}
	rec.root = e.state.StateDB.IntermediateRoot(true)
	return rec
}
func TestStockS1VerifyDeterministicSignedApplyMessageReplay(t *testing.T) {
	a, b := stockS1VerifyReplay(t), stockS1VerifyReplay(t)
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

func TestStockS1VerifyMalformedModuleResponse(t *testing.T) {
	page := stockS1VerifyLoadPage(t)
	parser := stockS1VerifyLoadArtifact(t, "S1ClassParser")
	module := stockS1VerifyLoadArtifact(t, "S1StepModule")
	coord := stockS1VerifyLoadArtifact(t, "S1Coordinator")
	e := stockS1VerifyNewEnv(t)
	defer e.close()
	parserAt, _ := e.mustCreate(parser.init, stockS1VerifyCreateGas)
	class := stockS1VerifySimpleClass([]byte{3, 0xac}, 1, 0, "()I")
	_, _, _, id, _, _, _ := stockS1VerifyDeployRegistered(t, e, page, parser, parserAt, class.bytes)
	zero := stockS1VerifyZeroMachine()
	badCode := stockS1VerifyFakeStepRuntime(zero, 0, false)
	badAt, _ := stockS1VerifyDeployRaw(t, e, badCode, stockS1VerifyCreateGas)
	at, _ := stockS1VerifyDeployCoordinator(t, e, coord, parserAt, crypto.Keccak256Hash(parser.runtime), id, badAt, crypto.Keccak256Hash(badCode), "entry", nil, 64)
	before := stockS1VerifyCheckpointAt(t, e, coord, at)
	r := stockS1VerifyResume(t, e, coord, at, 0, 1, 32, stockS1VerifyCallGas)
	stockS1VerifyAssertRevert(t, r, "S1ControlError(uint256)", 7)
	stockS1VerifyAssertRollback(t, e, coord, at, before, r)
	_ = module
}

func TestStockS1VerifyStockProtocolLimitLayers(t *testing.T) {
	e := stockS1VerifyNewEnv(t)
	defer e.close()
	nonce := e.state.StateDB.GetNonce(e.sender)
	balance := e.state.StateDB.GetBalance(e.sender).ToBig()
	runtime := make([]byte, 24577)
	r := e.apply(nil, stockS1VerifyRawInit(runtime), stockS1VerifyCreateGas)
	if r.coreErr != nil || r.result == nil || !errors.Is(r.result.Err, vm.ErrMaxCodeSizeExceeded) {
		t.Fatalf("EIP-170 layer core=%v evm=%v", r.coreErr, stockS1VerifyResultErr(r.result))
	}
	if e.state.StateDB.GetNonce(e.sender) != nonce+1 || e.state.StateDB.GetBalance(e.sender).ToBig().Cmp(balance) >= 0 || len(e.state.StateDB.GetCode(crypto.CreateAddress(e.sender, nonce))) != 0 {
		t.Fatal("EIP-170 sender/code semantics")
	}
	nonce = e.state.StateDB.GetNonce(e.sender)
	balance = e.state.StateDB.GetBalance(e.sender).ToBig()
	snapshot := e.state.StateDB.Snapshot()
	r = e.apply(nil, make([]byte, 49153), stockS1VerifyCreateGas)
	if !errors.Is(r.coreErr, core.ErrMaxInitCodeSizeExceeded) || r.result != nil {
		t.Fatalf("EIP-3860 layer core=%v result=%v", r.coreErr, r.result)
	}
	debit := new(big.Int).Sub(balance, e.state.StateDB.GetBalance(e.sender).ToBig())
	wantDebit := new(big.Int).Mul(new(big.Int).SetUint64(stockS1VerifyCreateGas), big.NewInt(2))
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
