// Generated-fixture-only EVM integration driver for BindingMethodInspector.
// It never opens an original archive, host classpath, checkpoint, or world.
package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"math/big"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"sync/atomic"
	"time"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/rawdb"
	"github.com/ethereum/go-ethereum/core/state"
	"github.com/ethereum/go-ethereum/core/tracing"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/core/vm"
	evmrun "github.com/ethereum/go-ethereum/core/vm/runtime"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/as0"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/di0"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/zi0"
	"github.com/ethereum/go-ethereum/params"
	"github.com/ethereum/go-ethereum/triedb"
	"github.com/holiman/uint256"
)

const callGas uint64 = 1_000_000_000
const callTimeout = 60 * time.Second
const engineAddressHex = "0x4d432d52414e444f4d2d434c4153532d5031006c"
const ownerAddressHex = "0x4d432d52414e444f4d2d434c4153532d5031006d"
const engineCodeHashHex = "0x339b2ea289856952e2236e4ca2311ab10a57939f72ca9f59dd5a6cdc74bcf81f"
const coordinatorCodeHashHex = "0x3ea16a99b237255584b709aeac06f484d4cf8ca52ecfae138e718ed4320f58f7"
const as0CodeHashHex = "0xc8cec283e80fd82b15254bd50a9f2aea3a91305ba71f756f834439280600f896"
const zi0CodeHashHex = "0x0c22eca78e00865ce03e8e298708bfe51ce9856cff138d1046905fc285ad5a77"
const di0CodeHashHex = "0x946686a0a4f09ec9a03e3eb63e9bbeac008212061d6f316586034cf800380c37"
const coordinatorName = "MCEntryCoordinator"

var owner = common.HexToAddress(ownerAddressHex)
var engine = common.HexToAddress(engineAddressHex)
var zero = uint256.NewInt(0)
var readSelector = crypto.Keccak256([]byte("read(uint32,uint32)"))[:4]

// All requested resources are explicit generated-fixture bindings from fixture.json.
type fixtureConfig struct {
	ZIPPath          string        `json:"zipPath"`
	CoordinatorJSON  string        `json:"coordinatorArtifact"`
	EngineJSON       string        `json:"engineArtifact"`
	InspectorJSON    string        `json:"inspectorArtifact"`
	Bindings         []string      `json:"bindings"`
	Requests         []scanRequest `json:"requests"`
	Negative         []scanRequest `json:"negativeRequests"`
	TamperBinding    uint8         `json:"tamperBinding"`
	InvalidBinding   uint8         `json:"invalidBinding"`
	WrongPackageSalt bool          `json:"runWrongPackageConstructor"`
	WrongCodeSalt    bool          `json:"runWrongCodeConstructor"`
}

type scanRequest struct {
	Label      string `json:"label"`
	Binding    uint8  `json:"binding"`
	Method     uint16 `json:"methodIndex"`
	PCStart    uint32 `json:"pcStart"`
	PCEnd      uint32 `json:"pcEnd"`
	MaxResults uint16 `json:"maxResults"`
	Expected   bool   `json:"expectSuccess"`
}

type artifact struct {
	ABI              json.RawMessage `json:"abi"`
	Bytecode         string          `json:"bytecode"`
	DeployedBytecode string          `json:"deployedBytecode"`
}

type scanResult struct {
	BindingIndex        uint8
	ResourceName        []byte
	DeclaringClass      []byte
	MethodIndex         uint16
	MethodName          []byte
	MethodDescriptor    []byte
	PcStart             uint32
	PcEnd               uint32
	CodeLength          uint32
	DecodedInstructions uint32
	SwitchInstructions  uint16
	WideInstructions    uint16
	Coordinator         common.Address
	CoordinatorCodeHash [32]byte
	PackageRoot         [32]byte
	IndexRoot           [32]byte
	ResourceRoot        [32]byte
	ClassBytesKeccak    [32]byte
	References          []scanReference
}

type scanReference struct {
	MethodIndex       uint16
	Pc                uint32
	Opcode            uint8
	Kind              uint8
	ConstantPoolTag   uint8
	ConstantPoolIndex uint16
	OpcodeName        []byte
	Provenance        []byte
	Owner             []byte
	Name              []byte
	Descriptor        []byte
	TypeName          []byte
}

type callStats struct {
	GasUsed       uint64   `json:"gasUsed"`
	ReadSizes     []uint32 `json:"di0ReadSizes,omitempty"`
	ElapsedMillis int64    `json:"elapsedMillis"`
}

type resultJSON struct {
	Label               string          `json:"label,omitempty"`
	Success             bool            `json:"success"`
	Error               string          `json:"error,omitempty"`
	Stats               callStats       `json:"stats,omitempty"`
	BindingIndex        uint8           `json:"bindingIndex,omitempty"`
	ResourceName        string          `json:"resourceName,omitempty"`
	ResourceNameHex     string          `json:"resourceNameHex,omitempty"`
	DeclaringClass      string          `json:"declaringClass,omitempty"`
	MethodIndex         uint16          `json:"methodIndex,omitempty"`
	MethodName          string          `json:"methodName,omitempty"`
	MethodDescriptor    string          `json:"methodDescriptor,omitempty"`
	PCStart             uint32          `json:"pcStart,omitempty"`
	PCEnd               uint32          `json:"pcEnd,omitempty"`
	CodeLength          uint32          `json:"codeLength,omitempty"`
	DecodedInstructions uint32          `json:"decodedInstructions,omitempty"`
	SwitchInstructions  uint16          `json:"switchInstructions,omitempty"`
	WideInstructions    uint16          `json:"wideInstructions,omitempty"`
	Coordinator         string          `json:"coordinator,omitempty"`
	CoordinatorCodeHash string          `json:"coordinatorCodeHash,omitempty"`
	PackageRoot         string          `json:"packageRoot,omitempty"`
	IndexRoot           string          `json:"indexRoot,omitempty"`
	ResourceRoot        string          `json:"resourceRoot,omitempty"`
	ClassBytesKeccak    string          `json:"classBytesKeccak,omitempty"`
	References          []referenceJSON `json:"references,omitempty"`
}

type referenceJSON struct {
	MethodIndex       uint16 `json:"methodIndex"`
	PC                uint32 `json:"pc"`
	Opcode            uint8  `json:"opcodeByte"`
	OpcodeName        string `json:"opcode"`
	Provenance        string `json:"provenance"`
	Kind              uint8  `json:"kind"`
	ConstantPoolTag   uint8  `json:"constantPoolTag"`
	ConstantPoolIndex uint16 `json:"constantPoolIndex"`
	Owner             string `json:"owner,omitempty"`
	OwnerHex          string `json:"ownerHex,omitempty"`
	Name              string `json:"name,omitempty"`
	NameHex           string `json:"nameHex,omitempty"`
	Descriptor        string `json:"descriptor,omitempty"`
	DescriptorHex     string `json:"descriptorHex,omitempty"`
	TypeName          string `json:"typeName,omitempty"`
	TypeNameHex       string `json:"typeNameHex,omitempty"`
}

type evmState struct {
	st        *state.StateDB
	pid       common.Address
	totalGas  uint64
	maxGas    uint64
	callCount uint64
}

type traceReads struct {
	targets map[common.Address]bool
	sizes   []uint32
}

type callOutput struct {
	bytes []byte
	gas   uint64
	err   error
	reads []uint32
	ms    int64
}

func must(err error) {
	if err != nil {
		panic(err)
	}
}

func readArtifact(path string) (artifact, abi.ABI, []byte, []byte) {
	b, err := os.ReadFile(path)
	must(err)
	var a artifact
	must(json.Unmarshal(b, &a))
	parsed, err := abi.JSON(bytes.NewReader(a.ABI))
	must(err)
	init, err := hex.DecodeString(strings.TrimPrefix(a.Bytecode, "0x"))
	must(err)
	run, err := hex.DecodeString(strings.TrimPrefix(a.DeployedBytecode, "0x"))
	must(err)
	return a, parsed, init, run
}

func shaHex(b []byte) string {
	h := sha256.Sum256(b)
	return hex.EncodeToString(h[:])
}

func mustHashCode(label string, code []byte, expected string) common.Hash {
	got := crypto.Keccak256Hash(code)
	if got != common.HexToHash(expected) {
		panic(fmt.Sprintf("%s runtime codehash %s, want %s", label, got, expected))
	}
	return got
}

func abiPack(types []string, values ...interface{}) []byte {
	var args abi.Arguments
	for _, name := range types {
		t, err := abi.NewType(name, "", nil)
		must(err)
		args = append(args, abi.Argument{Type: t})
	}
	b, err := args.Pack(values...)
	must(err)
	return b
}

func newState(engineCode []byte) *evmState {
	db := rawdb.NewMemoryDatabase()
	trie := triedb.NewDatabase(db, triedb.HashDefaults)
	st, err := state.New(types.EmptyRootHash, state.NewDatabase(trie, nil))
	must(err)
	st.CreateAccount(owner)
	st.CreateAccount(engine)
	st.SetCode(engine, engineCode, tracing.CodeChangeUnspecified)
	if crypto.Keccak256Hash(st.GetCode(engine)) != common.HexToHash(engineCodeHashHex) {
		panic("installed engine codehash")
	}
	return &evmState{st: st, pid: owner}
}

func config(st *state.StateDB, hooks *tracing.Hooks) *evmrun.Config {
	z := common.Hash{}
	return &evmrun.Config{
		ChainConfig: params.AllDevChainProtocolChanges,
		Difficulty:  new(big.Int),
		Origin:      owner,
		Coinbase:    common.Address{},
		BlockNumber: big.NewInt(1),
		Time:        1,
		GasLimit:    callGas,
		GasPrice:    new(big.Int),
		Value:       new(big.Int),
		BaseFee:     new(big.Int).SetUint64(params.InitialBaseFee),
		BlobBaseFee: new(big.Int).SetUint64(params.BlobTxMinBlobGasprice),
		Random:      &z,
		State:       st,
		GetHashFn:   func(uint64) common.Hash { return common.Hash{} },
		EVMConfig:   vm.Config{Tracer: hooks},
	}
}

func activeRules(cfg *evmrun.Config) params.Rules {
	return cfg.ChainConfig.Rules(cfg.BlockNumber, cfg.Random != nil, cfg.Time)
}

func (w *evmState) prepare(to *common.Address, hooks *tracing.Hooks) *vm.EVM {
	c := config(w.st, hooks)
	rules := activeRules(c)
	w.st.Prepare(rules, owner, common.Address{}, to, vm.ActivePrecompiles(rules), nil)
	return evmrun.NewEnv(c)
}

func (w *evmState) create(code []byte, label string) (common.Address, []byte, callStats, error) {
	started := time.Now()
	e := w.prepare(nil, nil)
	var cancelled atomic.Bool
	done := make(chan struct{})
	timer := time.AfterFunc(callTimeout, func() { cancelled.Store(true); e.Cancel(); close(done) })
	out, addr, left, err := e.Create(owner, code, callGas, zero)
	if !timer.Stop() {
		<-done
	}
	stats := callStats{GasUsed: callGas - left, ElapsedMillis: time.Since(started).Milliseconds()}
	if cancelled.Load() {
		err = fmt.Errorf("%s cancelled by 60-second local EVM watchdog", label)
		return common.Address{}, nil, stats, err
	}
	if stats.GasUsed > callGas {
		return common.Address{}, nil, stats, errors.New("EVM gas accounting exceeds per-call cap")
	}
	w.recordGas(stats.GasUsed)
	return addr, append([]byte(nil), out...), stats, err
}

func (w *evmState) invoke(to common.Address, data []byte, readOnly bool, traceTargets map[common.Address]bool, label string) callOutput {
	started := time.Now()
	trace := &traceReads{targets: traceTargets}
	hooks := &tracing.Hooks{OnEnter: func(_ int, _ byte, _ common.Address, target common.Address, input []byte, _ uint64, _ *big.Int) {
		if !trace.targets[target] || len(input) != 68 || !bytes.Equal(input[:4], readSelector) {
			return
		}
		if new(big.Int).SetBytes(input[4:36]).BitLen() > 32 || new(big.Int).SetBytes(input[36:68]).BitLen() > 32 {
			trace.sizes = append(trace.sizes, ^uint32(0))
			return
		}
		trace.sizes = append(trace.sizes, binary.BigEndian.Uint32(input[64:68]))
	}}
	e := w.prepare(&to, hooks)
	var cancelled atomic.Bool
	done := make(chan struct{})
	timer := time.AfterFunc(callTimeout, func() { cancelled.Store(true); e.Cancel(); close(done) })
	var out []byte
	var left uint64
	var err error
	if readOnly {
		out, left, err = e.StaticCall(owner, to, data, callGas)
	} else {
		out, left, err = e.Call(owner, to, data, callGas, zero)
	}
	if !timer.Stop() {
		<-done
	}
	statsGas := callGas - left
	if cancelled.Load() {
		err = fmt.Errorf("%s cancelled by 60-second local EVM watchdog", label)
		out = nil
	}
	if statsGas > callGas {
		err = errors.New("EVM gas accounting exceeds per-call cap")
	}
	w.recordGas(statsGas)
	return callOutput{bytes: append([]byte(nil), out...), gas: statsGas, err: err, reads: append([]uint32(nil), trace.sizes...), ms: time.Since(started).Milliseconds()}
}

func (w *evmState) recordGas(gas uint64) {
	w.totalGas += gas
	w.callCount++
	if gas > w.maxGas {
		w.maxGas = gas
	}
}

func (w *evmState) deploy(init []byte, a abi.ABI, args ...interface{}) (common.Address, []byte, callStats) {
	constructor, err := a.Pack("", args...)
	must(err)
	code := append(append([]byte(nil), init...), constructor...)
	addr, out, stats, err := w.create(code, "CREATE")
	must(err)
	if len(w.st.GetCode(addr)) == 0 {
		panic("CREATE did not install runtime")
	}
	return addr, out, stats
}

func (w *evmState) packCall(a abi.ABI, method string, args ...interface{}) []byte {
	data, err := a.Pack(method, args...)
	must(err)
	return data
}

func (w *evmState) call(a abi.ABI, to common.Address, method string, args ...interface{}) (callOutput, []interface{}) {
	result := w.invoke(to, w.packCall(a, method, args...), false, nil, method)
	if result.err != nil {
		return result, nil
	}
	values, err := a.Unpack(method, result.bytes)
	if err != nil {
		result.err = fmt.Errorf("ABI decode %s: %w", method, err)
		return result, nil
	}
	return result, values
}

func (w *evmState) view(a abi.ABI, to common.Address, method string, args ...interface{}) []interface{} {
	result := w.invoke(to, w.packCall(a, method, args...), true, nil, method)
	if result.err != nil {
		panic(fmt.Sprintf("view %s: %v revert=0x%x", method, result.err, result.bytes))
	}
	values, err := a.Unpack(method, result.bytes)
	must(err)
	return values
}

func (w *evmState) mutate(a abi.ABI, to common.Address, method string, args ...interface{}) callStats {
	result := w.invoke(to, w.packCall(a, method, args...), false, nil, method)
	if result.err != nil {
		panic(fmt.Sprintf("mutate %s: %v revert=0x%x", method, result.err, result.bytes))
	}
	return callStats{GasUsed: result.gas, ElapsedMillis: result.ms}
}

func pageCommit(at common.Address, page uint32, raw []byte) common.Hash {
	return crypto.Keccak256Hash(abiPack(
		[]string{"bytes32", "address", "uint32", "uint32", "bytes32"},
		crypto.Keccak256Hash([]byte("MC-AS0/page/v1")), at, page, uint32(len(raw)), crypto.Keccak256Hash(raw),
	))
}

func deployArchive(w *evmState, raw []byte) (common.Address, abi.ABI, common.Hash, []byte) {
	a, err := as0.ABI()
	must(err)
	init, err := as0.InitCode()
	must(err)
	run, err := as0.Runtime()
	must(err)
	mustHashCode("AS0", run, as0CodeHashHex)
	addr, out, _ := w.deploy(init, a, uint32(len(raw)))
	if !bytes.Equal(out, run) || !bytes.Equal(w.st.GetCode(addr), run) {
		panic("AS0 deployment runtime mismatch")
	}
	for offset, page := 0, uint32(0); offset < len(raw); page++ {
		n := 8192
		if len(raw)-offset < n {
			n = len(raw) - offset
		}
		chunk := raw[offset : offset+n]
		w.mutate(a, addr, "append", uint32(offset), chunk, pageCommit(addr, page, chunk))
		offset += n
	}
	chain := w.view(a, addr, "chainCommitment")[0].([32]byte)
	w.mutate(a, addr, "seal", uint32(len(raw)), common.Hash(chain))
	content := common.Hash(w.view(a, addr, "contentCommitment")[0].([32]byte))
	return addr, a, content, run
}

func deployIndex(w *evmState, store common.Address, content common.Hash) (common.Address, abi.ABI, common.Hash) {
	a, err := zi0.ABI()
	must(err)
	init, err := zi0.InitCode()
	must(err)
	run, err := zi0.Runtime()
	must(err)
	mustHashCode("ZI0", run, zi0CodeHashHex)
	addr, out, _ := w.deploy(init, a, store, [32]byte(content))
	if !bytes.Equal(out, run) || !bytes.Equal(w.st.GetCode(addr), run) {
		panic("ZI0 deployment runtime mismatch")
	}
	w.mutate(a, addr, "discover")
	for {
		next := w.view(a, addr, "nextEntry")[0].(uint32)
		count := w.view(a, addr, "count")[0].(uint32)
		if next == count {
			break
		}
		cursor := w.view(a, addr, "cdCursor")[0].(uint32)
		rolling := w.view(a, addr, "rolling")[0].([32]byte)
		units := uint16(64)
		if count-next < uint32(units) {
			units = uint16(count - next)
		}
		w.mutate(a, addr, "scan", next, cursor, rolling, units)
	}
	count := w.view(a, addr, "count")[0].(uint32)
	cursor := w.view(a, addr, "cdCursor")[0].(uint32)
	rolling := w.view(a, addr, "rolling")[0].([32]byte)
	w.mutate(a, addr, "finish", count, cursor, rolling)
	return addr, a, common.Hash(w.view(a, addr, "finalRoot")[0].([32]byte))
}

func createDecoder(w *evmState, index common.Address, indexRoot common.Hash, name []byte) (common.Address, common.Hash, uint32) {
	a, err := di0.ABI()
	must(err)
	init, err := di0.InitCode()
	must(err)
	run, err := di0.Runtime()
	must(err)
	mustHashCode("DI0", run, di0CodeHashHex)
	addr, out, _ := w.deploy(init, a, index, [32]byte(indexRoot), name)
	if !bytes.Equal(out, run) || !bytes.Equal(w.st.GetCode(addr), run) {
		panic("DI0 deployment runtime mismatch")
	}
	size := w.view(a, addr, "plainSize")[0].(uint32)
	for w.view(a, addr, "phase")[0].(uint8) == 1 {
		cursor := w.view(a, addr, "work")[0].(uint32)
		w.mutate(a, addr, "step", cursor, uint16(128))
	}
	for w.view(a, addr, "phase")[0].(uint8) != 4 {
		page := w.view(a, addr, "publishedPages")[0].(uint8)
		rolling := w.view(a, addr, "publicationRolling")[0].([32]byte)
		w.mutate(a, addr, "publish", page, rolling, uint8(1))
	}
	return addr, common.Hash(w.view(a, addr, "finalRoot")[0].([32]byte)), size
}

func computePackageRoot(coord common.Address, decoders []common.Address, names [][]byte, index common.Address, indexRoot common.Hash, roots []common.Hash, sizes []uint32) common.Hash {
	packageDomain := crypto.Keccak256Hash([]byte("MC-CHECKPOINT-2M-P34/package/v1"))
	classDomain := crypto.Keccak256Hash([]byte("MC-CHECKPOINT-2M-P34/class/v1"))
	diHash := common.HexToHash(di0CodeHashHex)
	ziHash := common.HexToHash(zi0CodeHashHex)
	rolling := crypto.Keccak256Hash(abiPack(
		[]string{"bytes32", "address", "address", "address", "bytes32", "bytes32", "bytes32", "uint8"},
		packageDomain, coord, owner, engine, common.HexToHash(engineCodeHashHex), diHash, ziHash, uint8(len(decoders)),
	))
	var total uint32
	for i := range decoders {
		total += sizes[i]
		rolling = crypto.Keccak256Hash(abiPack(
			[]string{"bytes32", "bytes32", "uint8", "address", "bytes32", "bytes32", "bytes32", "uint32"},
			classDomain, rolling, uint8(i), decoders[i], crypto.Keccak256Hash(names[i]), indexRoot, roots[i], sizes[i],
		))
	}
	return crypto.Keccak256Hash(abiPack(
		[]string{"bytes32", "bytes32", "uint32", "address", "bytes32", "uint8"},
		packageDomain, rolling, total, index, indexRoot, uint8(0),
	))
}

func repeatRoot(root common.Hash, n int) [][32]byte {
	out := make([][32]byte, n)
	for i := range out {
		out[i] = [32]byte(root)
	}
	return out
}

func setupCoordinator(w *evmState, raw []byte, names [][]byte, coordArtifact artifact, coordABI abi.ABI, coordInit, coordRun []byte) (common.Address, common.Hash, common.Hash, []common.Address, []uint32) {
	store, archiveABI, content, _ := deployArchive(w, raw)
	index, _, indexRoot := deployIndex(w, store, content)
	decoders := make([]common.Address, len(names))
	roots := make([]common.Hash, len(names))
	sizes := make([]uint32, len(names))
	for i, name := range names {
		decoders[i], roots[i], sizes[i] = createDecoder(w, index, indexRoot, name)
	}
	_ = archiveABI
	predicted := crypto.CreateAddress(owner, w.st.GetNonce(owner))
	packageRoot := computePackageRoot(predicted, decoders, names, index, indexRoot, roots, sizes)
	indexRoots := repeatRoot(indexRoot, len(names))
	instanceSalt := crypto.Keccak256Hash([]byte("MC-CHECKPOINT-2M-P34/generated-inspector-fixture/v1"))
	args, err := coordABI.Pack("", owner, [32]byte(instanceSalt), decoders, names, indexRoots, roots,
		common.Address{}, []byte{}, [32]byte{}, [32]byte{}, [32]byte(packageRoot))
	must(err)
	addr, out, _, err := w.create(append(append([]byte(nil), coordInit...), args...), coordinatorName)
	must(err)
	if addr != predicted || !bytes.Equal(out, coordRun) || !bytes.Equal(w.st.GetCode(addr), coordRun) {
		panic("coordinator deployment identity/runtime mismatch")
	}
	if crypto.Keccak256Hash(w.st.GetCode(addr)) != common.HexToHash(coordinatorCodeHashHex) {
		panic("coordinator runtime codehash mismatch")
	}
	gotPackage := common.Hash(w.view(coordABI, addr, "packageRoot")[0].([32]byte))
	gotIndex := common.Hash(w.view(coordABI, addr, "finalIndexRoot")[0].([32]byte))
	if gotPackage != packageRoot || gotIndex != indexRoot {
		panic("coordinator immutable package/index anchor mismatch")
	}
	_ = coordArtifact
	return addr, packageRoot, indexRoot, decoders, sizes
}

func stateRoot(st *state.StateDB) common.Hash {
	return st.Copy().IntermediateRoot(true)
}

func jsonBytes(b []byte) (string, string) {
	return string(b), hex.EncodeToString(b)
}

func toJSON(r scanResult, label string, stats callStats) resultJSON {
	name, nameHex := jsonBytes(r.ResourceName)
	declaring, _ := jsonBytes(r.DeclaringClass)
	method, _ := jsonBytes(r.MethodName)
	descriptor, _ := jsonBytes(r.MethodDescriptor)
	out := resultJSON{
		Label: label, Success: true, Stats: stats,
		BindingIndex: r.BindingIndex, ResourceName: name, ResourceNameHex: nameHex,
		DeclaringClass: declaring, MethodIndex: r.MethodIndex, MethodName: method,
		MethodDescriptor: descriptor, PCStart: r.PcStart, PCEnd: r.PcEnd,
		CodeLength: r.CodeLength, DecodedInstructions: r.DecodedInstructions,
		SwitchInstructions: r.SwitchInstructions, WideInstructions: r.WideInstructions,
		Coordinator: r.Coordinator.Hex(), CoordinatorCodeHash: common.Hash(r.CoordinatorCodeHash).Hex(),
		PackageRoot: common.Hash(r.PackageRoot).Hex(), IndexRoot: common.Hash(r.IndexRoot).Hex(),
		ResourceRoot: common.Hash(r.ResourceRoot).Hex(), ClassBytesKeccak: common.Hash(r.ClassBytesKeccak).Hex(),
		References: make([]referenceJSON, 0, len(r.References)),
	}
	for _, ref := range r.References {
		ownerText, ownerHex := jsonBytes(ref.Owner)
		nameText, nameHex := jsonBytes(ref.Name)
		descText, descHex := jsonBytes(ref.Descriptor)
		typeText, typeHex := jsonBytes(ref.TypeName)
		out.References = append(out.References, referenceJSON{
			MethodIndex: ref.MethodIndex, PC: ref.Pc, Opcode: ref.Opcode, OpcodeName: string(ref.OpcodeName),
			Provenance: string(ref.Provenance), Kind: ref.Kind, ConstantPoolTag: ref.ConstantPoolTag, ConstantPoolIndex: ref.ConstantPoolIndex,
			Owner: ownerText, OwnerHex: ownerHex, Name: nameText, NameHex: nameHex,
			Descriptor: descText, DescriptorHex: descHex, TypeName: typeText, TypeNameHex: typeHex,
		})
	}
	return out
}

func callInspector(w *evmState, inspector common.Address, inspectorABI abi.ABI, request scanRequest, readTargets map[common.Address]bool) resultJSON {
	data, err := inspectorABI.Pack("inspect", request.Binding, request.Method, request.PCStart, request.PCEnd, request.MaxResults)
	must(err)
	before := stateRoot(w.st)
	called := w.invoke(inspector, data, true, readTargets, request.Label)
	after := stateRoot(w.st)
	if before != after {
		panic(fmt.Sprintf("static diagnostic changed state root for %s: %s => %s", request.Label, before, after))
	}
	stats := callStats{GasUsed: called.gas, ReadSizes: called.reads, ElapsedMillis: called.ms}
	if called.err != nil {
		return resultJSON{Label: request.Label, Success: false, Error: fmt.Sprintf("%v revert=0x%x", called.err, called.bytes), Stats: stats}
	}
	var decoded struct {
		Result scanResult
	}
	if err := inspectorABI.UnpackIntoInterface(&decoded, "inspect", called.bytes); err != nil {
		return resultJSON{Label: request.Label, Success: false, Error: "ABI decode: " + err.Error(), Stats: stats}
	}
	return toJSON(decoded.Result, request.Label, stats)
}

func expectOutcome(label string, got resultJSON, success bool) {
	if got.Success != success {
		panic(fmt.Sprintf("%s outcome=%v expected=%v error=%s", label, got.Success, success, got.Error))
	}
	for _, n := range got.Stats.ReadSizes {
		if n == ^uint32(0) || n > 4096 {
			panic(fmt.Sprintf("%s DI0 chunk bound %d", label, n))
		}
	}
}

func constructorRefusal(w *evmState, inspectorABI abi.ABI, init []byte, coord common.Address, coordHash, packageRoot common.Hash, wrongHash bool) (bool, uint64) {
	copyWorld := &evmState{st: w.st.Copy(), pid: w.pid}
	assertHash := coordHash
	assertRoot := packageRoot
	if wrongHash {
		assertHash[0] ^= 0x01
	} else {
		assertRoot[0] ^= 0x01
	}
	args, err := inspectorABI.Pack("", coord, [32]byte(assertHash), [32]byte(assertRoot))
	must(err)
	_, _, _, err = copyWorld.create(append(append([]byte(nil), init...), args...), "negative inspector constructor")
	return err != nil, copyWorld.totalGas
}

func tryView(w *evmState, a abi.ABI, to common.Address, method string) ([]interface{}, bool) {
	data, err := a.Pack(method)
	if err != nil {
		return nil, false
	}
	called := w.invoke(to, data, true, nil, "guard getter "+method)
	if called.err != nil {
		return nil, false
	}
	values, err := a.Unpack(method, called.bytes)
	return values, err == nil && len(values) == 1
}

type getterGuardSpec struct {
	field  string
	abi    abi.ABI
	method string
}

func probeStorageGuard(w *evmState, inspector common.Address, inspectorABI abi.ABI,
	readTargets map[common.Address]bool, target common.Address, field string, binding uint8,
	guards []getterGuardSpec) (uint64, resultJSON, uint64, error) {
	var spent uint64
	baselines := make(map[string]interface{}, len(guards))
	for _, guard := range guards {
		values, ok := tryView(w, guard.abi, target, guard.method)
		if !ok {
			return 0, resultJSON{}, spent, fmt.Errorf("baseline getter %s failed", guard.field)
		}
		baselines[guard.field] = values[0]
	}
	patterns := []byte{0x01, 0x42, 0x7f, 0xff}
	for slot := uint64(0); slot < 48; slot++ {
		key := common.BigToHash(new(big.Int).SetUint64(slot))
		oldValue := w.st.GetState(target, key)
		for byteAt := 0; byteAt < 32; byteAt++ {
			for _, pattern := range patterns {
				newValue := oldValue
				newValue[31-byteAt] = pattern
				if newValue == oldValue {
					continue
				}
				copyWorld := &evmState{st: w.st.Copy(), pid: w.pid}
				copyWorld.st.SetState(target, key, newValue)
				changedTarget, changedSibling := false, false
				beforeGas := copyWorld.totalGas
				for _, guard := range guards {
					values, ok := tryView(copyWorld, guard.abi, target, guard.method)
					if !ok {
						if guard.field == field {
							changedTarget = true
						} else {
							changedSibling = true
						}
						continue
					}
					changed := !reflect.DeepEqual(baselines[guard.field], values[0])
					if guard.field == field {
						changedTarget = changed
					} else if changed {
						changedSibling = true
					}
				}
				spent += copyWorld.totalGas - beforeGas
				if !changedTarget || changedSibling {
					continue
				}
				request := scanRequest{Label: "tamper-" + field, Binding: binding, Method: 0, PCStart: 0, PCEnd: 1, MaxResults: 8}
				beforeGas = copyWorld.totalGas
				bad := callInspector(copyWorld, inspector, inspectorABI, request, readTargets)
				spent += copyWorld.totalGas - beforeGas
				if bad.Success {
					return slot, bad, spent, fmt.Errorf("diagnostic accepted forged %s getter state", field)
				}
				return slot, bad, spent, nil
			}
		}
	}
	return 0, resultJSON{}, spent, fmt.Errorf("could not find an isolated generated storage mutation for %s", field)
}

func decodeFixtureNames(names []string) [][]byte {
	out := make([][]byte, len(names))
	for i, name := range names {
		if name == "" || len(name) > 256 || !strings.HasSuffix(name, ".class") || strings.Contains(name, ",") {
			panic("invalid explicit generated class binding " + name)
		}
		out[i] = []byte(name)
	}
	return out
}

func getBindingMetadata(w *evmState, coord common.Address, coordABI abi.ABI, diABI abi.ABI, binding uint8) (common.Address, common.Hash, uint32) {
	vals := w.view(coordABI, coord, "classBinding", binding)
	decoder := vals[0].(common.Address)
	name := vals[1].([]byte)
	root := common.Hash(vals[2].([32]byte))
	size := vals[3].(uint32)
	if len(name) == 0 || size == 0 || decoder == (common.Address{}) {
		panic("empty coordinator classBinding metadata")
	}
	if w.view(diABI, decoder, "owner")[0].(common.Address) != w.view(coordABI, coord, "owner")[0].(common.Address) {
		panic("DI0 owner differs from coordinator owner")
	}
	if w.view(diABI, decoder, "phase")[0].(uint8) != 4 {
		panic("DI0 is not phase 4")
	}
	if common.Hash(w.view(diABI, decoder, "indexRoot")[0].([32]byte)) != common.Hash(w.view(coordABI, coord, "finalIndexRoot")[0].([32]byte)) {
		panic("DI0 indexRoot differs from coordinator")
	}
	if w.view(diABI, decoder, "plainSize")[0].(uint32) != size {
		panic("DI0 plainSize differs from coordinator binding")
	}
	if common.Hash(w.view(diABI, decoder, "finalRoot")[0].([32]byte)) != root {
		panic("DI0 finalRoot differs from coordinator binding")
	}
	return decoder, root, size
}

func run() error {
	if len(os.Args) != 2 {
		return errors.New("usage: generated_evm.go fixture-config.json")
	}
	configBytes, err := os.ReadFile(os.Args[1])
	if err != nil {
		return err
	}
	var cfg fixtureConfig
	if err := json.Unmarshal(configBytes, &cfg); err != nil {
		return err
	}
	if len(cfg.Bindings) == 0 || len(cfg.Bindings) > 16 || len(cfg.Requests) == 0 {
		return errors.New("fixture harness requires 1..16 explicit bindings and explicit methods")
	}
	root, err := os.Getwd()
	if err != nil {
		return err
	}
	resolve := func(path string) string {
		if filepath.IsAbs(path) {
			return path
		}
		return filepath.Join(root, path)
	}
	cfg.ZIPPath = resolve(cfg.ZIPPath)
	cfg.CoordinatorJSON = resolve(cfg.CoordinatorJSON)
	cfg.EngineJSON = resolve(cfg.EngineJSON)
	cfg.InspectorJSON = resolve(cfg.InspectorJSON)
	expectedBindings := []string{"scan/Base.class", "scan/Bad.class", "scan/Helper.class", "scan/Marker.class", "scan/Probe.class", "scan/WrongName.class"}
	if !reflect.DeepEqual(cfg.Bindings, expectedBindings) {
		return errors.New("generated helper accepts only its literal generated fixture bindings")
	}
	expectedRoot := filepath.Join(root, "evidence/java-evm/minecraft-entry")
	if cfg.ZIPPath != filepath.Join(expectedRoot, "perf-evm-dependency-preflight/fixtures/generated/fixture.zip") ||
		cfg.EngineJSON != filepath.Join(expectedRoot, "performance-base-p34/engine/MCEntryInterpreter.json") ||
		cfg.CoordinatorJSON != filepath.Join(expectedRoot, "performance-base-p34/coordinator/MCEntryCoordinator.json") ||
		cfg.InspectorJSON != filepath.Join(expectedRoot, "perf-evm-dependency-preflight/BindingMethodInspector.json") {
		return errors.New("generated helper path confinement failed")
	}

	_, _, engineInit, engineRun := readArtifact(cfg.EngineJSON)
	_ = engineInit
	if shaHex(engineRun) != "1c67cdc85ae7eb73620b69241158b052d5ab28de1b9ece97e36372f9be508e44" {
		return errors.New("frozen P34 engine SHA-256 mismatch")
	}
	mustHashCode("P34 engine", engineRun, engineCodeHashHex)
	coordArtifact, coordABI, coordInit, coordRun := readArtifact(cfg.CoordinatorJSON)
	if len(coordRun) != 5411 || shaHex(coordRun) != "f30ef4d058ef37aed6ee25a1131434b0079c8d4c91c84d014784de2f0e27b475" {
		return errors.New("frozen P34 coordinator runtime pin mismatch")
	}
	mustHashCode("P34 coordinator", coordRun, coordinatorCodeHashHex)
	inspectorArtifact, inspectorABI, inspectorInit, inspectorRun := readArtifact(cfg.InspectorJSON)
	if len(inspectorRun) == 0 || len(inspectorRun) > 24576 {
		return errors.New("diagnostic runtime is empty or exceeds the ordinary EIP-170 limit")
	}
	if len(inspectorInit) > 49152 {
		return errors.New("diagnostic init code exceeds EIP-3860")
	}
	_ = inspectorArtifact

	zipBytes, err := os.ReadFile(cfg.ZIPPath)
	if err != nil {
		return err
	}
	w := newState(engineRun)
	start := time.Now()
	coord, packageRoot, indexRoot, decoders, sizes := setupCoordinator(w, zipBytes, decodeFixtureNames(cfg.Bindings), coordArtifact, coordABI, coordInit, coordRun)
	coordHash := crypto.Keccak256Hash(w.st.GetCode(coord))
	ctorArgs, err := inspectorABI.Pack("", coord, [32]byte(coordHash), [32]byte(packageRoot))
	if err != nil {
		return err
	}
	inspector, inspectorOut, _, err := w.create(append(append([]byte(nil), inspectorInit...), ctorArgs...), "BindingMethodInspector CREATE")
	if err != nil {
		return fmt.Errorf("inspector CREATE revert: %w (0x%x)", err, inspectorOut)
	}
	if len(w.st.GetCode(inspector)) != len(inspectorRun) {
		return errors.New("deployed inspector runtime size mismatch")
	}
	if w.view(coordABI, coord, "owner")[0].(common.Address) != owner {
		return errors.New("coordinator owner anchor mismatch")
	}
	if common.Hash(w.view(coordABI, coord, "packageRoot")[0].([32]byte)) != packageRoot {
		return errors.New("coordinator package root mismatch")
	}
	if common.Hash(w.view(coordABI, coord, "finalIndexRoot")[0].([32]byte)) != indexRoot {
		return errors.New("coordinator final index root mismatch")
	}
	diABI, err := di0.ABI()
	if err != nil {
		return err
	}
	bindingDecoders := make([]common.Address, len(decoders))
	bindingRoots := make([]common.Hash, len(decoders))
	bindingSizes := make([]uint32, len(decoders))
	for i := range decoders {
		bindingDecoders[i], bindingRoots[i], bindingSizes[i] = getBindingMetadata(w, coord, coordABI, diABI, uint8(i))
		if bindingDecoders[i] != decoders[i] || bindingRoots[i] == (common.Hash{}) || bindingSizes[i] != sizes[i] {
			return fmt.Errorf("binding metadata mismatch at %d", i)
		}
	}
	readTargets := make(map[common.Address]bool, len(decoders))
	for _, decoder := range decoders {
		readTargets[decoder] = true
	}

	results := make([]resultJSON, 0, len(cfg.Requests)+len(cfg.Negative)+6)
	for _, request := range cfg.Requests {
		got := callInspector(w, inspector, inspectorABI, request, readTargets)
		expectOutcome(request.Label, got, request.Expected)
		results = append(results, got)
	}
	for _, request := range cfg.Negative {
		got := callInspector(w, inspector, inspectorABI, request, readTargets)
		expectOutcome(request.Label, got, request.Expected)
		results = append(results, got)
	}
	if cfg.InvalidBinding < uint8(len(cfg.Bindings)) {
		return errors.New("invalidBinding must be outside the explicit binding list")
	}
	invalid := scanRequest{Label: "invalid-binding", Binding: cfg.InvalidBinding, Method: 0, PCStart: 0, PCEnd: 1, MaxResults: 8}
	gotInvalid := callInspector(w, inspector, inspectorABI, invalid, readTargets)
	expectOutcome(invalid.Label, gotInvalid, false)
	results = append(results, gotInvalid)
	wrongPackageRefused := false
	wrongCodeHashRefused := false
	extraProbeGas := uint64(0)
	if cfg.WrongPackageSalt {
		var gas uint64
		wrongPackageRefused, gas = constructorRefusal(w, inspectorABI, inspectorInit, coord, coordHash, packageRoot, false)
		extraProbeGas += gas
		if !wrongPackageRefused {
			return errors.New("wrong package-root constructor unexpectedly succeeded")
		}
	}
	if cfg.WrongCodeSalt {
		var gas uint64
		wrongCodeHashRefused, gas = constructorRefusal(w, inspectorABI, inspectorInit, coord, coordHash, packageRoot, true)
		extraProbeGas += gas
		if !wrongCodeHashRefused {
			return errors.New("wrong coordinator-codehash constructor unexpectedly succeeded")
		}
	}
	if cfg.TamperBinding >= uint8(len(decoders)) {
		return errors.New("tamperBinding outside explicit binding list")
	}
	for _, mode := range []string{"coordinator-code", "di0-code"} {
		copyWorld := &evmState{st: w.st.Copy(), pid: w.pid}
		if mode == "coordinator-code" {
			copyWorld.st.SetCode(coord, []byte{0xfe}, tracing.CodeChangeUnspecified)
		} else {
			copyWorld.st.SetCode(decoders[cfg.TamperBinding], []byte{0xfe}, tracing.CodeChangeUnspecified)
		}
		probe := scanRequest{Label: "tamper-" + mode, Binding: cfg.TamperBinding, Method: 0, PCStart: 0, PCEnd: 1, MaxResults: 8}
		bad := callInspector(copyWorld, inspector, inspectorABI, probe, readTargets)
		extraProbeGas += copyWorld.totalGas
		expectOutcome(probe.Label, bad, false)
		results = append(results, bad)
	}

	guardSlots := make(map[string]uint64)
	guardGas := uint64(0)
	coordinatorGuards := []getterGuardSpec{
		{field: "coordinator-owner", abi: coordABI, method: "owner"},
		{field: "coordinator-packageRoot", abi: coordABI, method: "packageRoot"},
		{field: "coordinator-finalIndexRoot", abi: coordABI, method: "finalIndexRoot"},
	}
	di0Guards := []getterGuardSpec{
		{field: "di0-owner", abi: diABI, method: "owner"},
		{field: "di0-phase", abi: diABI, method: "phase"},
		{field: "di0-indexRoot", abi: diABI, method: "indexRoot"},
		{field: "di0-plainSize", abi: diABI, method: "plainSize"},
		{field: "di0-finalRoot", abi: diABI, method: "finalRoot"},
	}
	guardCases := []struct {
		field   string
		target  common.Address
		binding uint8
		guards  []getterGuardSpec
	}{
		{field: "coordinator-owner", target: coord, binding: cfg.TamperBinding, guards: coordinatorGuards},
		{field: "coordinator-packageRoot", target: coord, binding: cfg.TamperBinding, guards: coordinatorGuards},
		{field: "coordinator-finalIndexRoot", target: coord, binding: cfg.TamperBinding, guards: coordinatorGuards},
		{field: "di0-owner", target: decoders[cfg.TamperBinding], binding: cfg.TamperBinding, guards: di0Guards},
		{field: "di0-phase", target: decoders[cfg.TamperBinding], binding: cfg.TamperBinding, guards: di0Guards},
		{field: "di0-indexRoot", target: decoders[cfg.TamperBinding], binding: cfg.TamperBinding, guards: di0Guards},
		{field: "di0-plainSize", target: decoders[cfg.TamperBinding], binding: cfg.TamperBinding, guards: di0Guards},
		{field: "di0-finalRoot", target: decoders[cfg.TamperBinding], binding: cfg.TamperBinding, guards: di0Guards},
	}
	for _, guard := range guardCases {
		slot, bad, probeGas, err := probeStorageGuard(w, inspector, inspectorABI, readTargets,
			guard.target, guard.field, guard.binding, guard.guards)
		if err != nil {
			return err
		}
		guardSlots[guard.field] = slot
		guardGas += probeGas
		expectOutcome("tamper-"+guard.field, bad, false)
		results = append(results, bad)
	}
	if w.totalGas+guardGas+extraProbeGas > callGas {
		return fmt.Errorf("generated EVM suite gas %d exceeded initial 1B test budget", w.totalGas+guardGas+extraProbeGas)
	}
	classRoots := make([]string, len(bindingRoots))
	for i, root := range bindingRoots {
		classRoots[i] = root.Hex()
	}
	summary := map[string]interface{}{
		"diagnosticOnly":                             true,
		"inputProvenance":                            "generated Java 8 fixture ZIP only",
		"guestExecution":                             false,
		"checkpointOrContinuation":                   false,
		"worldOrPackageMutationByInspector":          false,
		"packageRoot":                                packageRoot.Hex(),
		"indexRoot":                                  indexRoot.Hex(),
		"coordinator":                                coord.Hex(),
		"coordinatorCodeHash":                        coordHash.Hex(),
		"inspector":                                  inspector.Hex(),
		"inspectorRuntimeBytes":                      len(w.st.GetCode(inspector)),
		"inspectorRuntimeKeccak":                     crypto.Keccak256Hash(w.st.GetCode(inspector)).Hex(),
		"fixtureZIPBytes":                            len(zipBytes),
		"explicitBindings":                           cfg.Bindings,
		"bindingRoots":                               classRoots,
		"bindingSizes":                               bindingSizes,
		"forgedStateGuardSlots":                      guardSlots,
		"forgedStateGuardProbeGas":                   guardGas,
		"otherNegativeProbeGas":                      extraProbeGas,
		"wrongPackageRootConstructorRefused":         wrongPackageRefused,
		"wrongCoordinatorCodeHashConstructorRefused": wrongCodeHashRefused,
		"results":                                    results,
		"elapsedMillis":                              time.Since(start).Milliseconds(),
		"readChunkLimit":                             4096,
		"ordinaryGasLimitPerEVMCall":                 callGas,
		"totalObservedEVMGas":                        w.totalGas,
		"maximumObservedEVMCallGas":                  w.maxGas,
		"observedEVMCallCount":                       w.callCount,
	}
	out, err := json.MarshalIndent(summary, "", "  ")
	if err != nil {
		return err
	}
	fmt.Println(string(out))
	return nil
}

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
