// Package main is a generated-fixture-only canonical geth EVM transport for the
// frozen LOCAL1M ArrayList(int) candidate. Engine code is locally preinstalled at
// its pinned address; it is not deployed with CREATE and no interpreter logic is
// run by this Go harness.
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
	"strconv"
	"strings"
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
	"github.com/ethereum/go-ethereum/ethdb"
	"github.com/ethereum/go-ethereum/ethdb/leveldb"
	"github.com/ethereum/go-ethereum/params"
	"github.com/ethereum/go-ethereum/triedb"
)

const (
	ordinaryGas = uint64(1_000_000_000)
	maxInternal = uint32(4096)
	maxJvm      = uint64(65536)
	engineHex   = "0x4d432d52414e444f4d2d434c4153532d50310060"
	callerHex   = "0x4d432d41525241594c4953544c4f43414c310001"
	coordHex    = "0x4d432d41525241594c4953544c4f43414c310002"
	rootKind    = uint8(1)
)

var engineAddress = common.HexToAddress(engineHex)
var callerAddress = common.HexToAddress(callerHex)
var coordinatorAddress = common.HexToAddress(coordHex)

type artifact struct {
	ABI              json.RawMessage   `json:"abi"`
	Bytecode         string            `json:"bytecode"`
	DeployedBytecode string            `json:"deployedBytecode"`
	SourceHashes     map[string]string `json:"sourceHashes"`
	CodeHashes       struct {
		RuntimeSHA256    string `json:"runtimeSHA256"`
		RuntimeKeccak256 string `json:"runtimeKeccak256"`
	} `json:"codeHashes"`
}

type classFile struct {
	Index      int    `json:"index"`
	BinaryName string `json:"binaryName"`
	File       string `json:"file"`
	Bytes      int    `json:"bytes"`
	SHA256     string `json:"sha256"`
}

type fixtureCase struct {
	Name       string      `json:"name"`
	RawCount   int         `json:"rawCount"`
	RawBytes   int         `json:"rawBytes"`
	RawClasses []classFile `json:"rawClasses"`
	EntryClass string      `json:"entryClass"`
}

type fixtureManifest struct {
	Cases                         map[string]fixtureCase `json:"cases"`
	IdentityHashMapCapacityOracle struct {
		Rows map[string]struct {
			TableLength uint32 `json:"tableLength"`
			Size        int    `json:"size"`
			IsEmpty     bool   `json:"isEmpty"`
		} `json:"rows"`
	} `json:"identityHashMapCapacityOracle"`
}

type mr0Result struct {
	Schema                uint32
	Lifecycle             uint8
	Outcome               uint8
	Epoch                 uint64
	CheckpointRoot        common.Hash
	MachineStateRoot      common.Hash
	TotalJvmSteps         uint64
	TotalInternalSteps    uint64
	ExecutedJvmSteps      uint64
	ExecutedInternalSteps uint32
	Result                int32
	JavaKind              uint8
	JavaRef               uint32
	JavaClass             []byte
	VfsStateRoot          common.Hash
	InodeCount            uint32
	DescriptorCount       uint32
	LogicalFileBytes      uint64
}

type startOutput struct {
	Result     mr0Result
	Checkpoint []byte
}

type sliceSummary struct {
	Schema                uint32      `json:"schema"`
	Lifecycle             uint8       `json:"lifecycle"`
	Outcome               uint8       `json:"outcome"`
	Epoch                 uint64      `json:"epoch"`
	CheckpointRoot        common.Hash `json:"checkpointRoot"`
	MachineStateRoot      common.Hash `json:"machineStateRoot"`
	TotalJvmSteps         uint64      `json:"totalJvmSteps"`
	TotalInternalSteps    uint64      `json:"totalInternalSteps"`
	ExecutedJvmSteps      uint64      `json:"executedJvmSteps"`
	ExecutedInternalSteps uint32      `json:"executedInternalSteps"`
	JavaKind              uint8       `json:"javaKind"`
	JavaRef               uint32      `json:"javaRef"`
	JavaClass             string      `json:"javaClass,omitempty"`
	VfsStateRoot          common.Hash `json:"vfsStateRoot"`
	GasUsed               uint64      `json:"gasUsed"`
	WallMS                int64       `json:"wallMs"`
}

type report struct {
	Status              string           `json:"status"`
	Mode                string           `json:"mode"`
	EngineSHA256        string           `json:"engineRuntimeSHA256"`
	EngineCodeHash      common.Hash      `json:"engineRuntimeKeccak256"`
	CoordinatorSHA256   string           `json:"coordinatorRuntimeSHA256"`
	CoordinatorCodeHash common.Hash      `json:"coordinatorRuntimeKeccak256"`
	GasBudget           uint64           `json:"localGasBudget"`
	Caller              common.Address   `json:"caller"`
	Engine              common.Address   `json:"engineAddress"`
	Coordinator         common.Address   `json:"coordinatorAddress"`
	Schedules           []scheduleReport `json:"schedules,omitempty"`
	Cases               []caseReport     `json:"cases,omitempty"`
	Controls            []controlReport  `json:"controls,omitempty"`
	Failure             *failureReport   `json:"failure,omitempty"`
	ProcessID           int              `json:"processId"`
	ElapsedMS           int64            `json:"elapsedMs"`
}

type scheduleReport struct {
	Name                 string       `json:"name"`
	Quantum              uint64       `json:"quantum"`
	Transport            string       `json:"transport"`
	RawCount             int          `json:"rawCount"`
	RawBytes             int          `json:"rawBytes"`
	BootstrapCount       int          `json:"bootstrapCount"`
	DiagnosticClassCount int          `json:"diagnosticClassCount"`
	CallCount            int          `json:"callCount"`
	TotalGas             uint64       `json:"totalGas"`
	MaxCallGas           uint64       `json:"maxCallGas"`
	WallMS               int64        `json:"wallMs"`
	StateRoot            common.Hash  `json:"stateRoot"`
	InstanceID           common.Hash  `json:"instanceId"`
	Final                sliceSummary `json:"final"`
	CheckpointBytes      int          `json:"checkpointBytes"`
	CheckpointSHA256     string       `json:"checkpointSHA256"`
	HeapAudit            *heapAudit   `json:"readOnlyCheckpointHeapAudit,omitempty"`
	ReopenRequest        string       `json:"reopenRequest,omitempty"`
}

type caseReport struct {
	Name             string       `json:"name"`
	Expectation      string       `json:"expectation"`
	RawCount         int          `json:"rawCount"`
	RawBytes         int          `json:"rawBytes"`
	BootstrapCount   int          `json:"bootstrapCount"`
	ClassCount       int          `json:"classCount"`
	CallCount        int          `json:"callCount"`
	TotalGas         uint64       `json:"totalGas"`
	StateRoot        common.Hash  `json:"stateRoot"`
	Final            sliceSummary `json:"final"`
	CheckpointBytes  int          `json:"checkpointBytes"`
	CheckpointSHA256 string       `json:"checkpointSHA256"`
	HeapAudit        *heapAudit   `json:"readOnlyCheckpointHeapAudit,omitempty"`
}

type controlReport struct {
	Name        string      `json:"name"`
	Expectation string      `json:"expectation"`
	ErrorName   string      `json:"errorName,omitempty"`
	ErrorArgs   []string    `json:"errorArgs,omitempty"`
	Selector    string      `json:"selector,omitempty"`
	JavaClass   string      `json:"javaClass,omitempty"`
	RootBefore  common.Hash `json:"rootBefore"`
	RootAfter   common.Hash `json:"rootAfter"`
	Atomic      bool        `json:"atomic"`
	GasUsed     uint64      `json:"gasUsed"`
	WallMS      int64       `json:"wallMs"`
}

type failureReport struct {
	Classification string `json:"classification"`
	Case           string `json:"case"`
	GasBudget      uint64 `json:"gasBudget"`
	Error          string `json:"error"`
}

type heapAudit struct {
	MachineBytes                        int               `json:"machineBytes"`
	ClassCount                          int               `json:"classCount"`
	RawCount                            int               `json:"rawCount"`
	BootstrapCount                      int               `json:"bootstrapCount"`
	NextHandle                          uint32            `json:"nextHandle"`
	ArrayListClassIndex                 uint32            `json:"arrayListClassIndex"`
	IdentityHashMapClassIndex           uint32            `json:"identityHashMapClassIndex"`
	ObjectClassIndex                    uint32            `json:"objectClassIndex"`
	ArrayListObjects                    int               `json:"arrayListObjectCount"`
	IdentityHashMapObjects              int               `json:"identityHashMapObjectCount"`
	BackingLengths                      []uint32          `json:"arrayListBackingLengths"`
	BackingHandles                      []uint32          `json:"arrayListBackingHandles"`
	IdentityHashMapBackingLengths       []uint32          `json:"identityHashMapTableLengths"`
	IdentityHashMapBackingHandles       []uint32          `json:"identityHashMapTableHandles"`
	AllBackingsObjectArray              bool              `json:"allBackingsAreObjectArrays"`
	AllBackingElementsZero              bool              `json:"allBackingElementsZero"`
	AllIdentityHashMapTablesObjectArray bool              `json:"allIdentityHashMapTablesAreObjectArrays"`
	AllIdentityHashMapTableElementsZero bool              `json:"allIdentityHashMapTableElementsAreZero"`
	PackedFloatLengths                  []uint32          `json:"packedFloatLengths,omitempty"`
	SparseFloatLengths                  []uint32          `json:"sparseFloatLengths,omitempty"`
	FloatNonzeroCounts                  map[string]uint32 `json:"floatNonzeroCounts,omitempty"`
}

type errorDetail struct {
	Name     string   `json:"name"`
	Selector string   `json:"selector"`
	Args     []string `json:"args"`
}

func (r *runner) validateIdentityHashMapMatrix(a heapAudit) error {
	capacities := []int{0, 1, 2, 3, 10, 21, 512, 1024, 21845}
	if a.IdentityHashMapObjects != len(capacities) || len(a.IdentityHashMapBackingLengths) != len(capacities) ||
		len(a.IdentityHashMapBackingHandles) != len(capacities) {
		return fmt.Errorf("IdentityHashMap matrix object/table count mismatch: objects=%d lengths=%d handles=%d",
			a.IdentityHashMapObjects, len(a.IdentityHashMapBackingLengths), len(a.IdentityHashMapBackingHandles))
	}
	if !a.AllIdentityHashMapTablesObjectArray || !a.AllIdentityHashMapTableElementsZero {
		return errors.New("IdentityHashMap matrix does not own only zero-filled Object[] tables")
	}
	seen := make(map[uint32]bool, len(capacities))
	for i, capacity := range capacities {
		oracle, ok := r.fixtures.IdentityHashMapCapacityOracle.Rows[strconv.Itoa(capacity)]
		if !ok || oracle.Size != 0 || !oracle.IsEmpty {
			return fmt.Errorf("missing/invalid independent Java 8 reflection oracle for capacity %d", capacity)
		}
		if a.IdentityHashMapBackingLengths[i] != oracle.TableLength {
			return fmt.Errorf("IdentityHashMap table[%d] for expected size %d has %d slots; independent Java 8 reflection oracle says %d",
				i, capacity, a.IdentityHashMapBackingLengths[i], oracle.TableLength)
		}
		handle := a.IdentityHashMapBackingHandles[i]
		if handle == 0 || seen[handle] {
			return fmt.Errorf("IdentityHashMap table handle %d is null or aliased", handle)
		}
		seen[handle] = true
	}
	return nil
}

type durableDB interface {
	ethdb.Database
	SyncKeyValue() error
}

type world struct {
	path string
	disk durableDB
	trie *triedb.Database
	st   *state.StateDB
	root common.Hash
}

type runner struct {
	root         string
	fixtureDir   string
	reportDir    string
	gas          uint64
	engineABI    abi.ABI
	coordABI     abi.ABI
	engineCode   []byte
	coordCode    []byte
	coordInit    []byte
	engineArt    artifact
	coordArt     artifact
	fixtures     fixtureManifest
	report       report
	evmGasTotal  uint64
	evmMaxGas    uint64
	evmCallCount uint64
}

type failure struct{ classification, caseName, message string }

func must(err error) {
	if err != nil {
		panic(err)
	}
}

func sha256Hex(data []byte) string {
	digest := sha256.Sum256(data)
	return hex.EncodeToString(digest[:])
}

func readJSON(path string, out any) {
	b, err := os.ReadFile(path)
	must(err)
	must(json.Unmarshal(b, out))
}

func hexCode(s string) []byte {
	s = strings.TrimPrefix(s, "0x")
	b, err := hex.DecodeString(s)
	must(err)
	return b
}

func loadABI(raw json.RawMessage) abi.ABI {
	a, err := abi.JSON(bytes.NewReader(raw))
	must(err)
	return a
}

func loadArtifact(path string) (artifact, abi.ABI, []byte) {
	var a artifact
	readJSON(path, &a)
	code := hexCode(a.DeployedBytecode)
	got := crypto.Keccak256Hash(code)
	if strings.TrimPrefix(strings.ToLower(a.CodeHashes.RuntimeKeccak256), "0x") != hex.EncodeToString(got[:]) {
		panic("artifact runtime Keccak does not match deployed bytecode: " + path)
	}
	return a, loadABI(a.ABI), code
}

func openWorld(path string, root common.Hash) (*world, error) {
	if err := os.MkdirAll(filepath.Join(path, "state"), 0700); err != nil {
		return nil, err
	}
	kv, err := leveldb.New(filepath.Join(path, "state"), 16, 16, "array-list-local1m-generated", false)
	if err != nil {
		return nil, err
	}
	disk := rawdb.NewDatabase(kv)
	trie := triedb.NewDatabase(disk, triedb.HashDefaults)
	st, err := state.New(root, state.NewDatabase(trie, nil))
	if err != nil {
		trie.Close()
		disk.Close()
		return nil, err
	}
	return &world{path: path, disk: disk, trie: trie, st: st, root: root}, nil
}

func (w *world) close() {
	if w == nil {
		return
	}
	_ = w.trie.Close()
	_ = w.disk.Close()
}

func (w *world) persistAndReload() error {
	root, err := w.st.Commit(1, false, false)
	if err != nil {
		return err
	}
	if err = w.trie.Commit(root, false); err != nil {
		return err
	}
	if err = w.disk.SyncKeyValue(); err != nil {
		return err
	}
	st, err := state.New(root, state.NewDatabase(w.trie, nil))
	if err != nil {
		return err
	}
	w.st, w.root = st, root
	return nil
}

func (w *world) installCode(engineCode, coordCode []byte) error {
	w.st.CreateAccount(engineAddress)
	w.st.SetCode(engineAddress, engineCode, tracing.CodeChangeUnspecified)
	w.st.CreateAccount(coordinatorAddress)
	w.st.SetCode(coordinatorAddress, coordCode, tracing.CodeChangeUnspecified)
	return w.persistAndReload()
}

func (r *runner) runtimeConfig(st *state.StateDB) *evmrun.Config {
	z := common.Hash{}
	return &evmrun.Config{
		ChainConfig: params.AllDevChainProtocolChanges,
		Difficulty:  new(big.Int),
		Origin:      callerAddress,
		Coinbase:    common.Address{},
		BlockNumber: big.NewInt(1),
		Time:        1,
		GasLimit:    r.gas,
		GasPrice:    new(big.Int),
		Value:       new(big.Int),
		BaseFee:     new(big.Int).SetUint64(params.InitialBaseFee),
		BlobBaseFee: new(big.Int).SetUint64(params.BlobTxMinBlobGasprice),
		Random:      &z,
		State:       st,
		GetHashFn:   func(uint64) common.Hash { return common.Hash{} },
		EVMConfig:   vm.Config{},
	}
}

func (r *runner) call(to common.Address, data []byte) ([]byte, uint64, error, int64) {
	started := time.Now()
	out, left, err := evmrun.Call(to, data, r.runtimeConfig(current.st))
	lastCallOutput = out
	used := r.gas - left
	r.evmGasTotal += used
	r.evmCallCount++
	if used > r.evmMaxGas {
		r.evmMaxGas = used
	}
	return out, used, err, time.Since(started).Milliseconds()
}

func (r *runner) create(data []byte) ([]byte, common.Address, uint64, error, int64) {
	started := time.Now()
	out, address, left, err := evmrun.Create(data, r.runtimeConfig(current.st))
	lastCallOutput = out
	used := r.gas - left
	r.evmGasTotal += used
	r.evmCallCount++
	if used > r.evmMaxGas {
		r.evmMaxGas = used
	}
	return out, address, used, err, time.Since(started).Milliseconds()
}

// current is temporarily set while running a schedule or reopen check.
var current *world

func (r *runner) setCurrent(w *world) { current = w }

// runtime.Call is not a StaticCall API and can touch ephemeral transaction
// state even for Solidity view functions. Run observer views against a copied
// StateDB and discard that copy; no diagnostic call is allowed to publish state.
func (r *runner) callReadOnly(to common.Address, data []byte) ([]byte, uint64, error, int64) {
	original := current
	copyWorld := *original
	copyWorld.st = original.st.Copy()
	current = &copyWorld
	defer func() { current = original }()
	return r.call(to, data)
}

func (r *runner) loadCase(name string) (fixtureCase, [][]byte) {
	c, ok := r.fixtures.Cases[name]
	if !ok {
		panic("missing fixture case: " + name)
	}
	bundle := filepath.Join(r.fixtureDir, "bundles", name)
	classes := make([][]byte, len(c.RawClasses))
	for i, f := range c.RawClasses {
		b, err := os.ReadFile(filepath.Join(bundle, f.File))
		must(err)
		digest := sha256.Sum256(b)
		if len(b) != f.Bytes || hex.EncodeToString(digest[:]) != f.SHA256 {
			panic("fixture bytes/hash mismatch: " + f.File)
		}
		classes[i] = b
	}
	return c, classes
}

func (r *runner) packStart(instance common.Hash, classes [][]byte, entry string, q uint64, internal uint32) []byte {
	type seedFile struct {
		Path     []byte
		Data     []byte
		ReadOnly bool
	}
	data, err := r.engineABI.Pack("startMain", instance, classes, entry, []seedFile{}, q, internal)
	must(err)
	return data
}

func (r *runner) packResume(instance common.Hash, epoch uint64, cpRoot common.Hash, classes [][]byte, cp []byte, q uint64, internal uint32) []byte {
	data, err := r.engineABI.Pack("resumeMain", instance, epoch, cpRoot, classes, cp, q, internal)
	must(err)
	return data
}

func unpackOutput(a abi.ABI, method string, raw []byte) startOutput {
	var out startOutput
	values, err := a.Unpack(method, raw)
	if err != nil {
		panic(fmt.Sprintf("unpack %s: %v", method, err))
	}
	if len(values) != 2 {
		panic("unexpected engine return arity")
	}
	src := reflect.ValueOf(values[0])
	if src.Kind() == reflect.Pointer {
		src = src.Elem()
	}
	dst := reflect.ValueOf(&out.Result).Elem()
	if src.Kind() != reflect.Struct {
		panic("unexpected MR0 tuple type")
	}
	for i := 0; i < src.NumField(); i++ {
		name := src.Type().Field(i).Name
		target := dst.FieldByName(name)
		if !target.IsValid() || !target.CanSet() {
			panic("unmapped MR0 ABI field: " + name)
		}
		if !src.Field(i).Type().AssignableTo(target.Type()) {
			panic("incompatible MR0 ABI field: " + name)
		}
		target.Set(src.Field(i))
	}
	checkpoint, ok := values[1].([]byte)
	if !ok {
		panic(fmt.Sprintf("unexpected checkpoint ABI value type %T", values[1]))
	}
	out.Checkpoint = checkpoint
	return out
}

func sliceSummaryOf(x mr0Result, gas uint64, wall int64) sliceSummary {
	return sliceSummary{
		Schema: x.Schema, Lifecycle: x.Lifecycle, Outcome: x.Outcome, Epoch: x.Epoch,
		CheckpointRoot: x.CheckpointRoot, MachineStateRoot: x.MachineStateRoot,
		TotalJvmSteps: x.TotalJvmSteps, TotalInternalSteps: x.TotalInternalSteps,
		ExecutedJvmSteps: x.ExecutedJvmSteps, ExecutedInternalSteps: x.ExecutedInternalSteps,
		JavaKind: x.JavaKind, JavaRef: x.JavaRef, JavaClass: string(x.JavaClass), VfsStateRoot: x.VfsStateRoot,
		GasUsed: gas, WallMS: wall,
	}
}

func (r *runner) decodeError(out []byte) errorDetail {
	if len(out) < 4 {
		return errorDetail{Selector: "0x" + hex.EncodeToString(out)}
	}
	for _, e := range r.engineABI.Errors {
		if bytes.Equal(out[:4], e.ID[:4]) {
			values, err := e.Inputs.Unpack(out[4:])
			if err != nil {
				return errorDetail{Name: e.Name, Selector: "0x" + hex.EncodeToString(out[:4]), Args: []string{"<decode-error:" + err.Error() + ">"}}
			}
			args := make([]string, len(values))
			for i, v := range values {
				args[i] = fmt.Sprint(v)
			}
			return errorDetail{Name: e.Name, Selector: "0x" + hex.EncodeToString(out[:4]), Args: args}
		}
	}
	return errorDetail{Selector: "0x" + hex.EncodeToString(out[:4])}
}

func asHash(v any) common.Hash {
	switch x := v.(type) {
	case common.Hash:
		return x
	case [32]byte:
		return common.Hash(x)
	default:
		panic(fmt.Sprintf("unexpected bytes32 ABI type %T", v))
	}
}

func errorCode(d errorDetail) string {
	if len(d.Args) == 0 {
		return ""
	}
	return strings.Trim(d.Args[0], "<>")
}

func (r *runner) getHead(instance common.Hash) (common.Address, uint64, common.Hash, uint8, error) {
	input, err := r.engineABI.Pack("head", instance)
	if err != nil {
		return common.Address{}, 0, common.Hash{}, 0, err
	}
	out, used, callErr, _ := r.callReadOnly(engineAddress, input)
	if callErr != nil {
		classification := "EVM-positive-call-failure"
		if errors.Is(callErr, vm.ErrOutOfGas) {
			classification = "test-only-gas-budget"
		}
		return common.Address{}, 0, common.Hash{}, 0, &positiveCallError{classification: classification,
			name: "engine-head-view", gas: r.gas, err: fmt.Errorf("%w after %d gas; output=0x%x", callErr, used, out)}
	}
	v, err := r.engineABI.Unpack("head", out)
	if err != nil {
		return common.Address{}, 0, common.Hash{}, 0, err
	}
	return v[0].(common.Address), v[1].(uint64), asHash(v[2]), v[9].(uint8), nil
}

func (r *runner) verifyInstalledCode(w *world) error {
	if !bytes.Equal(w.st.GetCode(engineAddress), r.engineCode) {
		return errors.New("fresh engine bytecode not present at pinned local address")
	}
	if !bytes.Equal(w.st.GetCode(coordinatorAddress), r.coordCode) {
		return errors.New("paired coordinator bytecode not present at pinned local address")
	}
	if crypto.Keccak256Hash(w.st.GetCode(engineAddress)) != common.HexToHash(r.engineArt.CodeHashes.RuntimeKeccak256) {
		return errors.New("installed engine codehash mismatch")
	}
	if crypto.Keccak256Hash(w.st.GetCode(coordinatorAddress)) != common.HexToHash(r.coordArt.CodeHashes.RuntimeKeccak256) {
		return errors.New("installed coordinator codehash mismatch")
	}
	return nil
}

func (r *runner) checkCP(cp []byte, root common.Hash, classes [][]byte) (heapAudit, error) {
	if len(cp) < 280 || len(cp) > 1048576 {
		return heapAudit{}, errors.New("checkpoint envelope length outside pinned bounds")
	}
	if string(cp[:8]) != "JVMVF0A1" || binary.BigEndian.Uint32(cp[8:12]) != 1 {
		return heapAudit{}, errors.New("checkpoint magic/schema mismatch")
	}
	if crypto.Keccak256Hash(cp) != root {
		return heapAudit{}, errors.New("checkpoint root mismatch")
	}
	if binary.BigEndian.Uint32(cp[276:280]) != uint32(len(cp)-280) {
		return heapAudit{}, errors.New("checkpoint machine length mismatch")
	}
	machine := cp[280:]
	parsed, err := auditMachine(machine, len(classes))
	if err != nil {
		return heapAudit{}, err
	}
	return parsed, nil
}

func (r *runner) validateCheckpoint(classes [][]byte, cp []byte, expected common.Hash) error {
	input, err := r.engineABI.Pack("validateCheckpoint", classes, cp)
	if err != nil {
		return err
	}
	out, used, callErr, _ := r.callReadOnly(engineAddress, input)
	if callErr != nil {
		classification := "EVM-positive-call-failure"
		if errors.Is(callErr, vm.ErrOutOfGas) {
			classification = "test-only-gas-budget"
		}
		return &positiveCallError{classification: classification, name: "validateCheckpoint",
			gas: r.gas, err: fmt.Errorf("%w after %d gas; output=0x%x", callErr, used, out)}
	}
	v, err := r.engineABI.Unpack("validateCheckpoint", out)
	if err != nil {
		return err
	}
	if asHash(v[0]) != expected {
		return errors.New("read-only validateCheckpoint machine root mismatch")
	}
	if asHash(v[1]) != common.BytesToHash(cp[244:276]) {
		return errors.New("read-only validateCheckpoint VFS root mismatch")
	}
	return nil
}

func (r *runner) runSchedule(name string, q uint64, caseName string, auditArrayList bool, wantVoid bool) (scheduleReport, *world, error) {
	fc, classes := r.loadCase(caseName)
	w, err := openWorld(filepath.Join(r.reportDir, "worlds", name), types.EmptyRootHash)
	if err != nil {
		return scheduleReport{}, nil, err
	}
	r.setCurrent(w)
	if err = w.installCode(r.engineCode, r.coordCode); err != nil {
		w.close()
		return scheduleReport{}, nil, err
	}
	if err = r.verifyInstalledCode(w); err != nil {
		w.close()
		return scheduleReport{}, nil, err
	}
	instance := crypto.Keccak256Hash([]byte("MC-ARRAY-LIST-LOCAL1M/" + name + "/" + caseName))
	start := time.Now()
	callCount := 0
	var totalGas uint64
	var maxCallGas uint64
	var last startOutput
	var lastGas uint64
	var lastWall int64
	method := "startMain"
	input := r.packStart(instance, classes, fc.EntryClass, q, maxInternal)
	for callCount < 10000 {
		out, gasUsed, callErr, wall := r.call(engineAddress, input)
		callCount++
		totalGas += gasUsed
		if gasUsed > maxCallGas {
			maxCallGas = gasUsed
		}
		if callErr != nil {
			classification := "EVM-positive-call-failure"
			if errors.Is(callErr, vm.ErrOutOfGas) {
				classification = "test-only-gas-budget"
			}
			detail := r.decodeError(out)
			return scheduleReport{}, w, &positiveCallError{classification: classification, name: name, gas: r.gas, err: fmt.Errorf("%w; typed=%s args=%v selector=%s", callErr, detail.Name, detail.Args, detail.Selector)}
		}
		last = unpackOutput(r.engineABI, method, out)
		lastGas, lastWall = gasUsed, wall
		if last.Result.Schema != 1 || last.Result.Epoch == 0 || last.Result.Outcome != last.Result.Lifecycle {
			return scheduleReport{}, w, fmt.Errorf("%s invalid MR0 result: schema=%d lifecycle=%d outcome=%d", name, last.Result.Schema, last.Result.Lifecycle, last.Result.Outcome)
		}
		if last.Result.CheckpointRoot != crypto.Keccak256Hash(last.Checkpoint) {
			return scheduleReport{}, w, errors.New("engine result/checkpoint root mismatch")
		}
		if err = w.persistAndReload(); err != nil {
			return scheduleReport{}, w, fmt.Errorf("persist/reopen after %s call: %w", name, err)
		}
		if last.Result.Lifecycle != 1 {
			break
		}
		method = "resumeMain"
		input = r.packResume(instance, last.Result.Epoch, last.Result.CheckpointRoot, classes, last.Checkpoint, q, maxInternal)
	}
	if last.Result.Lifecycle == 1 {
		return scheduleReport{}, w, fmt.Errorf("%s exceeded 10000 continuation calls", name)
	}
	if wantVoid && (last.Result.Lifecycle != 2 || last.Result.Outcome != 2 || last.Result.JavaKind != 0 || len(last.Result.JavaClass) != 0) {
		return scheduleReport{}, w, fmt.Errorf("%s expected genuine void terminal, got lifecycle=%d outcome=%d kind=%d class=%q", name, last.Result.Lifecycle, last.Result.Outcome, last.Result.JavaKind, last.Result.JavaClass)
	}
	if err = r.validateCheckpoint(classes, last.Checkpoint, last.Result.MachineStateRoot); err != nil {
		return scheduleReport{}, w, err
	}
	var audit *heapAudit
	if auditArrayList {
		a, e := r.checkCP(last.Checkpoint, last.Result.CheckpointRoot, classes)
		if e != nil {
			return scheduleReport{}, w, e
		}
		if a.ClassCount != fc.RawCount+100 {
			return scheduleReport{}, w, fmt.Errorf("diagnostic class count %d != raw+100=%d", a.ClassCount, fc.RawCount+100)
		}
		if caseName == "ArrayListMatrix" || caseName == "raw150-envelope" || caseName == "raw-bytes-exact" {
			want := []uint32{0, 1, 3, 10, 1024}
			if a.ArrayListObjects != len(want) || len(a.BackingLengths) != len(want) {
				return scheduleReport{}, w, fmt.Errorf("expected five real ArrayList heap objects/backings, got %d/%d", a.ArrayListObjects, len(a.BackingLengths))
			}
			if !a.AllBackingsObjectArray || !a.AllBackingElementsZero {
				return scheduleReport{}, w, errors.New("matrix backing arrays were not all zero-filled Object[] instances")
			}
			for i := range want {
				if a.BackingLengths[i] != want[i] {
					return scheduleReport{}, w, fmt.Errorf("ArrayList backing length[%d]=%d expected=%d", i, a.BackingLengths[i], want[i])
				}
			}
		}
		if caseName == "IdentityHashMapMatrix" {
			if err := r.validateIdentityHashMapMatrix(a); err != nil {
				return scheduleReport{}, w, err
			}
		}
		audit = &a
	}
	owner, epoch, headRoot, lifecycle, err := r.getHead(instance)
	if err != nil {
		return scheduleReport{}, w, err
	}
	if owner != callerAddress || epoch != last.Result.Epoch || headRoot != last.Result.CheckpointRoot || lifecycle != last.Result.Lifecycle {
		return scheduleReport{}, w, fmt.Errorf("engine head disagrees with committed result: owner=%s epoch=%d lifecycle=%d", owner, epoch, lifecycle)
	}
	cpName := name + ".checkpoint.bin"
	cpPath := filepath.Join(r.reportDir, "checkpoints", cpName)
	if err = os.MkdirAll(filepath.Dir(cpPath), 0700); err != nil {
		return scheduleReport{}, w, err
	}
	if err = os.WriteFile(cpPath, last.Checkpoint, 0600); err != nil {
		return scheduleReport{}, w, err
	}
	row := scheduleReport{
		Name: name, Quantum: q, Transport: "geth core/vm/runtime.Call; preinstalled local bytecode; state trie committed/reloaded after every successful slice",
		RawCount: fc.RawCount, RawBytes: fc.RawBytes, BootstrapCount: 100,
		DiagnosticClassCount: fc.RawCount + 100, CallCount: callCount, TotalGas: totalGas, MaxCallGas: maxCallGas,
		WallMS: time.Since(start).Milliseconds(), StateRoot: w.root, InstanceID: instance,
		Final: sliceSummaryOf(last.Result, lastGas, lastWall), CheckpointBytes: len(last.Checkpoint),
		CheckpointSHA256: sha256Hex(last.Checkpoint), HeapAudit: audit,
	}
	if name == "q1-identity-hash-map-matrix" || name == "q1-raw150" {
		requestName := name + ".json"
		row.ReopenRequest = filepath.ToSlash(filepath.Join("reopen-requests", requestName))
		req := map[string]any{"stateDir": w.path, "stateRoot": w.root, "instanceId": instance,
			"case": caseName, "checkpoint": cpName, "checkpointRoot": last.Result.CheckpointRoot,
			"machineStateRoot": last.Result.MachineStateRoot, "epoch": last.Result.Epoch,
			"lifecycle": last.Result.Lifecycle, "preReopenPID": os.Getpid(), "gas": r.gas}
		b, _ := json.MarshalIndent(req, "", "  ")
		requestPath := filepath.Join(r.reportDir, "reopen-requests", requestName)
		if err = os.MkdirAll(filepath.Dir(requestPath), 0700); err != nil {
			return scheduleReport{}, w, err
		}
		if err = os.WriteFile(requestPath, append(b, '\n'), 0600); err != nil {
			return scheduleReport{}, w, err
		}
	}
	return row, w, nil
}

type positiveCallError struct {
	classification, name string
	gas                  uint64
	err                  error
}

func (e *positiveCallError) Error() string {
	return fmt.Sprintf("%s: %s failed at gas=%d: %v", e.classification, e.name, e.gas, e.err)
}

func (r *runner) runTerminal(name, expectation, caseName string, wantOutcome uint8, javaClass string, javaKind uint8, auditArrayList bool) (caseReport, error) {
	fc, classes := r.loadCase(caseName)
	w, err := openWorld(filepath.Join(r.reportDir, "worlds", name), types.EmptyRootHash)
	if err != nil {
		return caseReport{}, err
	}
	r.setCurrent(w)
	defer w.close()
	if err = w.installCode(r.engineCode, r.coordCode); err != nil {
		return caseReport{}, err
	}
	if err = r.verifyInstalledCode(w); err != nil {
		return caseReport{}, err
	}
	instance := crypto.Keccak256Hash([]byte("MC-ARRAY-LIST-LOCAL1M/" + name))
	input := r.packStart(instance, classes, fc.EntryClass, maxJvm, maxInternal)
	out, gasUsed, callErr, wall := r.call(engineAddress, input)
	if callErr != nil {
		classification := "EVM-positive-call-failure"
		if errors.Is(callErr, vm.ErrOutOfGas) {
			classification = "test-only-gas-budget"
		}
		detail := r.decodeError(out)
		return caseReport{}, &positiveCallError{classification: classification, name: name, gas: r.gas, err: fmt.Errorf("%w; typed=%s args=%v selector=%s", callErr, detail.Name, detail.Args, detail.Selector)}
	}
	decoded := unpackOutput(r.engineABI, "startMain", out)
	if decoded.Result.Lifecycle == 1 {
		return caseReport{}, fmt.Errorf("%s expected a one-call terminal outcome but remained RUNNING", name)
	}
	if decoded.Result.Outcome != wantOutcome {
		return caseReport{}, fmt.Errorf("%s outcome=%d expected=%d", name, decoded.Result.Outcome, wantOutcome)
	}
	if string(decoded.Result.JavaClass) != javaClass || decoded.Result.JavaKind != javaKind {
		return caseReport{}, fmt.Errorf("%s Java exception mismatch class=%q kind=%d expected class=%q kind=%d", name, decoded.Result.JavaClass, decoded.Result.JavaKind, javaClass, javaKind)
	}
	if decoded.Result.CheckpointRoot != crypto.Keccak256Hash(decoded.Checkpoint) {
		return caseReport{}, errors.New("terminal checkpoint root mismatch")
	}
	if err = r.validateCheckpoint(classes, decoded.Checkpoint, decoded.Result.MachineStateRoot); err != nil {
		return caseReport{}, err
	}
	parsedAudit, err := r.checkCP(decoded.Checkpoint, decoded.Result.CheckpointRoot, classes)
	if err != nil {
		return caseReport{}, err
	}
	if parsedAudit.ClassCount != fc.RawCount+100 {
		return caseReport{}, fmt.Errorf("%s checkpoint class count=%d expected raw+100=%d", name, parsedAudit.ClassCount, fc.RawCount+100)
	}
	if err = w.persistAndReload(); err != nil {
		return caseReport{}, err
	}
	owner, epoch, checkpointRoot, lifecycle, err := r.getHead(instance)
	if err != nil {
		return caseReport{}, err
	}
	if owner != callerAddress || epoch != decoded.Result.Epoch || checkpointRoot != decoded.Result.CheckpointRoot || lifecycle != decoded.Result.Lifecycle {
		return caseReport{}, fmt.Errorf("%s terminal engine head mismatch after persistence", name)
	}
	var audit *heapAudit
	if auditArrayList {
		audit = &parsedAudit
	}
	cpPath := filepath.Join(r.reportDir, "checkpoints", name+".checkpoint.bin")
	if err = os.MkdirAll(filepath.Dir(cpPath), 0700); err != nil {
		return caseReport{}, err
	}
	if err = os.WriteFile(cpPath, decoded.Checkpoint, 0600); err != nil {
		return caseReport{}, err
	}
	return caseReport{Name: name, Expectation: expectation, RawCount: fc.RawCount, RawBytes: fc.RawBytes,
		BootstrapCount: 100, ClassCount: fc.RawCount + 100, CallCount: 1, TotalGas: gasUsed, StateRoot: w.root,
		Final: sliceSummaryOf(decoded.Result, gasUsed, wall), CheckpointBytes: len(decoded.Checkpoint),
		CheckpointSHA256: sha256Hex(decoded.Checkpoint), HeapAudit: audit}, nil
}

func (r *runner) runRejection(name, caseName, expectedError string, expectedCode string, q uint64, internal uint32) (controlReport, error) {
	fc, classes := r.loadCase(caseName)
	w, err := openWorld(filepath.Join(r.reportDir, "worlds", "refusal-"+name), types.EmptyRootHash)
	if err != nil {
		return controlReport{}, err
	}
	r.setCurrent(w)
	defer w.close()
	if err = w.installCode(r.engineCode, r.coordCode); err != nil {
		return controlReport{}, err
	}
	instance := crypto.Keccak256Hash([]byte("MC-ARRAY-LIST-LOCAL1M/refusal/" + name))
	before := w.root
	input := r.packStart(instance, classes, fc.EntryClass, q, internal)
	_, gasUsed, callErr, wall := r.call(engineAddress, input)
	if callErr == nil {
		return controlReport{}, fmt.Errorf("%s unexpectedly returned; refusal was required", name)
	}
	detail := r.decodeError(lastCallOutput)
	if expectedError != "" && detail.Name != expectedError {
		return controlReport{}, fmt.Errorf("%s revert type=%s expected=%s selector=%s", name, detail.Name, expectedError, detail.Selector)
	}
	if expectedCode != "" && errorCode(detail) != expectedCode {
		return controlReport{}, fmt.Errorf("%s error code=%s expected=%s args=%v", name, errorCode(detail), expectedCode, detail.Args)
	}
	if detail.Name == "" {
		return controlReport{}, fmt.Errorf("%s refusal has unrecognized revert data %x", name, lastCallOutput)
	}
	after := w.st.IntermediateRoot(false)
	if before != after {
		return controlReport{}, fmt.Errorf("%s refusal mutated state root: before=%s after=%s", name, before, after)
	}
	owner, epoch, _, lifecycle, headErr := r.getHead(instance)
	if headErr != nil {
		return controlReport{}, headErr
	}
	if owner != (common.Address{}) || epoch != 0 || lifecycle != 0 {
		return controlReport{}, fmt.Errorf("%s refusal leaked an engine head", name)
	}
	if detail.Name == "AbstractMethodError" {
		return controlReport{}, fmt.Errorf("%s synthesized AME instead of refusing the unbound method", name)
	}
	return controlReport{Name: name, Expectation: "typed EVM refusal; root/head unchanged", ErrorName: detail.Name,
		ErrorArgs: detail.Args, Selector: detail.Selector, RootBefore: before, RootAfter: after,
		Atomic: true, GasUsed: gasUsed, WallMS: wall}, nil
}

var lastCallOutput []byte

func (r *runner) runOldCodeHashGuard() (controlReport, error) {
	fc, classes := r.loadCase("raw150-envelope")
	w, err := openWorld(filepath.Join(r.reportDir, "worlds", "old-codehash-guard"), types.EmptyRootHash)
	if err != nil {
		return controlReport{}, err
	}
	r.setCurrent(w)
	defer w.close()
	if err = w.installCode(r.engineCode, r.coordCode); err != nil {
		return controlReport{}, err
	}
	instance := crypto.Keccak256Hash([]byte("MC-RAW150/old-codehash-guard"))
	startOut, _, callErr, _ := r.call(engineAddress, r.packStart(instance, classes, fc.EntryClass, 1, maxInternal))
	if callErr != nil {
		return controlReport{}, fmt.Errorf("old-codehash setup start failed: %w", callErr)
	}
	start := unpackOutput(r.engineABI, "startMain", startOut)
	if start.Result.Lifecycle != 1 || start.Result.Epoch != 1 || start.Result.CheckpointRoot != crypto.Keccak256Hash(start.Checkpoint) {
		return controlReport{}, errors.New("old-codehash setup did not commit a valid q1 checkpoint")
	}
	if err = w.persistAndReload(); err != nil {
		return controlReport{}, err
	}
	altered := append(bytes.Clone(r.engineCode), 0x00) // preserve executable prefix, change only runtime codehash
	if crypto.Keccak256Hash(altered) == crypto.Keccak256Hash(r.engineCode) {
		return controlReport{}, errors.New("old-codehash tamper did not change the runtime codehash")
	}
	w.st.SetCode(engineAddress, altered, tracing.CodeChangeUnspecified)
	if err = w.persistAndReload(); err != nil {
		return controlReport{}, err
	}
	before := w.root
	resume := r.packResume(instance, start.Result.Epoch, start.Result.CheckpointRoot, classes,
		start.Checkpoint, 1, maxInternal)
	_, gasUsed, callErr, wall := r.call(engineAddress, resume)
	if callErr == nil {
		return controlReport{}, errors.New("resume accepted an old-codehash checkpoint under modified runtime")
	}
	detail := r.decodeError(lastCallOutput)
	if detail.Name != "LC0ControlError" || errorCode(detail) != "5" {
		return controlReport{}, fmt.Errorf("old-codehash resume refusal was %s args=%v selector=%s", detail.Name, detail.Args, detail.Selector)
	}
	after := w.st.IntermediateRoot(false)
	if before != after {
		return controlReport{}, errors.New("old-codehash refusal changed committed state root")
	}
	owner, epoch, root, lifecycle, err := r.getHead(instance)
	if err != nil {
		return controlReport{}, err
	}
	if owner != callerAddress || epoch != start.Result.Epoch || root != start.Result.CheckpointRoot || lifecycle != 1 {
		return controlReport{}, errors.New("old-codehash refusal changed or lost the prior head")
	}
	return controlReport{Name: "old-engine-codehash-resume-refusal",
		Expectation: "typed LC0ControlError(5); prior successful q1 head and state preserved",
		ErrorName:   detail.Name, ErrorArgs: detail.Args, Selector: detail.Selector,
		RootBefore: before, RootAfter: after, Atomic: true, GasUsed: gasUsed, WallMS: wall}, nil
}

func (r *runner) runBudgetRefusal(name string, q uint64, internal uint32, expectedArgs ...string) (controlReport, error) {
	fc, classes := r.loadCase("ArrayListMatrix")
	w, err := openWorld(filepath.Join(r.reportDir, "worlds", "budget-"+name), types.EmptyRootHash)
	if err != nil {
		return controlReport{}, err
	}
	r.setCurrent(w)
	defer w.close()
	if err = w.installCode(r.engineCode, r.coordCode); err != nil {
		return controlReport{}, err
	}
	instance := crypto.Keccak256Hash([]byte("MC-ARRAY-LIST-LOCAL1M/budget/" + name))
	before := w.root
	_, gasUsed, callErr, wall := r.call(engineAddress, r.packStart(instance, classes, fc.EntryClass, q, internal))
	if callErr == nil {
		return controlReport{}, fmt.Errorf("budget control %s unexpectedly accepted", name)
	}
	detail := r.decodeError(lastCallOutput)
	if detail.Name != "LC0ControlError" || errorCode(detail) != "6" {
		return controlReport{}, fmt.Errorf("budget control %s got %s %v", name, detail.Name, detail.Args)
	}
	for i, expected := range expectedArgs {
		if i >= len(detail.Args) || detail.Args[i] != expected {
			return controlReport{}, fmt.Errorf("budget control %s args %v expected %v", name, detail.Args, expectedArgs)
		}
	}
	after := w.st.IntermediateRoot(false)
	if before != after {
		return controlReport{}, errors.New("budget refusal changed state root")
	}
	return controlReport{Name: name, Expectation: "expected guest execution-budget rejection; not an expansion trigger",
		ErrorName: detail.Name, ErrorArgs: detail.Args, Selector: detail.Selector, RootBefore: before,
		RootAfter: after, Atomic: true, GasUsed: gasUsed, WallMS: wall}, nil
}

func writeJSON(path string, value any) error {
	if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
		return err
	}
	b, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, append(b, '\n'), 0600)
}

func (r *runner) gate() error {
	started := time.Now()
	q1, w1, err := r.runSchedule("q1-matrix", 1, "ArrayListMatrix", true, true)
	if err != nil {
		if w1 != nil {
			w1.close()
		}
		return err
	}
	w1.close()
	r.report.Schedules = append(r.report.Schedules, q1)
	q7, w7, err := r.runSchedule("q7-matrix", 7, "ArrayListMatrix", true, true)
	if err != nil {
		if w7 != nil {
			w7.close()
		}
		return err
	}
	w7.close()
	r.report.Schedules = append(r.report.Schedules, q7)
	direct, wd, err := r.runSchedule("q65536-direct-matrix", maxJvm, "ArrayListMatrix", true, true)
	if err != nil {
		if wd != nil {
			wd.close()
		}
		return err
	}
	wd.close()
	r.report.Schedules = append(r.report.Schedules, direct)
	if q1.Final.MachineStateRoot != q7.Final.MachineStateRoot || q7.Final.MachineStateRoot != direct.Final.MachineStateRoot {
		return errors.New("matrix machine roots differ across q1/q7/direct-q65536")
	}
	if q1.Final.VfsStateRoot != q7.Final.VfsStateRoot || q7.Final.VfsStateRoot != direct.Final.VfsStateRoot {
		return errors.New("matrix VFS roots differ across q1/q7/direct-q65536")
	}
	if q1.Final.TotalJvmSteps != q7.Final.TotalJvmSteps || q7.Final.TotalJvmSteps != direct.Final.TotalJvmSteps {
		return errors.New("matrix Java step totals differ across quanta")
	}
	if q1.Final.TotalInternalSteps != q7.Final.TotalInternalSteps || q7.Final.TotalInternalSteps != direct.Final.TotalInternalSteps {
		return errors.New("matrix internal step totals differ across quanta")
	}
	var identityMapRows []scheduleReport
	for _, spec := range []struct {
		name string
		q    uint64
	}{
		{"q1-identity-hash-map-matrix", 1},
		{"q7-identity-hash-map-matrix", 7},
		{"q65536-identity-hash-map-matrix", maxJvm},
		{"q4096-identity-hash-map-matrix", 4096},
	} {
		row, world, runErr := r.runSchedule(spec.name, spec.q, "IdentityHashMapMatrix", true, true)
		if runErr != nil {
			if world != nil {
				world.close()
			}
			return runErr
		}
		world.close()
		r.report.Schedules = append(r.report.Schedules, row)
		identityMapRows = append(identityMapRows, row)
	}
	for i := 1; i < len(identityMapRows); i++ {
		if identityMapRows[0].Final.MachineStateRoot != identityMapRows[i].Final.MachineStateRoot ||
			identityMapRows[0].Final.VfsStateRoot != identityMapRows[i].Final.VfsStateRoot ||
			identityMapRows[0].Final.TotalJvmSteps != identityMapRows[i].Final.TotalJvmSteps ||
			identityMapRows[0].Final.TotalInternalSteps != identityMapRows[i].Final.TotalInternalSteps {
			return errors.New("IdentityHashMap terminal state differs across q1/q7/q65536/q4096")
		}
	}
	// Separate child-process reopen requests validate both the IdentityHashMap
	// matrix and exact raw150 envelope after the gate exits.
	// A separate child-process reopen validates the durable q1 world after the
	// gate exits; the request pins the q1 state root and opaque terminal blob.
	for _, spec := range []struct {
		name, expectation, fixture string
		outcome                    uint8
		javaClass                  string
		kind                       uint8
		audit                      bool
	}{
		{"negative-minus-one", "guest java/lang/IllegalArgumentException", "ArrayListNegativeMinusOne", 3, "java/lang/IllegalArgumentException", 0, false},
		{"negative-int-min", "guest java/lang/IllegalArgumentException", "ArrayListNegativeMin", 3, "java/lang/IllegalArgumentException", 0, false},
		{"identity-map-negative-minus-one", "guest java/lang/IllegalArgumentException", "IdentityHashMapNegativeMinusOne", 3, "java/lang/IllegalArgumentException", 0, false},
		{"identity-map-negative-int-min", "guest java/lang/IllegalArgumentException without overflow", "IdentityHashMapNegativeMin", 3, "java/lang/IllegalArgumentException", 0, false},
		{"identity-map-max-int-capacity-oom", "Java 8 max-int capacity calculation reaches guest array-quota OutOfMemoryError", "IdentityHashMapMaximumControl", 2, "", 0, false},
		{"identity-map-array-quota-oom", "table beyond unchanged 65536-slot VM array bound throws guest OutOfMemoryError", "IdentityHashMapArrayQuotaControl", 2, "", 0, false},
		{"math-object-integer-control", "Math.max/min; Integer.parseInt bounds; Object.equals identity; empty ArrayList", "ArrayListMathObjectInteger", 2, "", 0, false},
		{"arraylist-maximum-legal-capacity", "ArrayList constructor accepts max legal 65536-element Object[] and leaves it zero-filled", "ArrayListQuotaBoundary", 2, "", 0, true},
		{"packed-sparse-control", "genuine void terminal plus canonical packed/sparse arrays", "ArrayListPackedSparse", 2, "", 0, false},
		{"arraylist-quota-oom", "guest known OutOfMemoryError kind at unchanged array quota", "ArrayListQuotaOOM", 3, "", 7, false},
	} {
		row, runErr := r.runTerminal(spec.name, spec.expectation, spec.fixture, spec.outcome, spec.javaClass, spec.kind, spec.audit)
		if runErr != nil {
			return runErr
		}
		if spec.name == "arraylist-maximum-legal-capacity" {
			if row.HeapAudit == nil || row.HeapAudit.ArrayListObjects != 1 || len(row.HeapAudit.BackingLengths) != 1 ||
				row.HeapAudit.BackingLengths[0] != 65536 || !row.HeapAudit.AllBackingsObjectArray || !row.HeapAudit.AllBackingElementsZero {
				return fmt.Errorf("maximum-capacity heap audit mismatch: %#v", row.HeapAudit)
			}
		}
		if spec.name == "packed-sparse-control" {
			fc, classes := r.loadCase(spec.fixture)
			cp, readErr := os.ReadFile(filepath.Join(r.reportDir, "checkpoints", spec.name+".checkpoint.bin"))
			if readErr != nil {
				return readErr
			}
			a, auditErr := r.checkCP(cp, row.Final.CheckpointRoot, classes)
			if auditErr != nil {
				return auditErr
			}
			if len(a.PackedFloatLengths) != 1 || a.PackedFloatLengths[0] != 1024 || len(a.SparseFloatLengths) != 1 || a.SparseFloatLengths[0] != 1024 {
				return fmt.Errorf("packed/sparse checkpoint controls missing: packed=%v sparse=%v", a.PackedFloatLengths, a.SparseFloatLengths)
			}
			row.HeapAudit = &a
			_ = fc
		}
		r.report.Cases = append(r.report.Cases, row)
	}
	// Exercise the exact 150-class maximum through q1/q7/direct/q4096 and keep
	// the q1 state for a distinct-process terminal MR01 reopen below.
	var raw150Rows []scheduleReport
	for _, spec := range []struct {
		name string
		q    uint64
	}{
		{"q1-raw150", 1}, {"q7-raw150", 7}, {"q65536-raw150", maxJvm}, {"q4096-raw150", 4096},
	} {
		row, world, runErr := r.runSchedule(spec.name, spec.q, "raw150-envelope", true, true)
		if runErr != nil {
			if world != nil {
				world.close()
			}
			return runErr
		}
		world.close()
		r.report.Schedules = append(r.report.Schedules, row)
		raw150Rows = append(raw150Rows, row)
	}
	for i := 1; i < len(raw150Rows); i++ {
		if raw150Rows[0].Final.MachineStateRoot != raw150Rows[i].Final.MachineStateRoot ||
			raw150Rows[0].Final.VfsStateRoot != raw150Rows[i].Final.VfsStateRoot ||
			raw150Rows[0].Final.TotalJvmSteps != raw150Rows[i].Final.TotalJvmSteps ||
			raw150Rows[0].Final.TotalInternalSteps != raw150Rows[i].Final.TotalInternalSteps {
			return errors.New("raw150 MR01 terminal state differs across q1/q7/q65536/q4096")
		}
	}
	if raw150Rows[0].RawCount != 150 || raw150Rows[0].DiagnosticClassCount != 250 {
		return errors.New("raw150 diagnostic count did not reach the enforced 250-class frontier")
	}
	oldCodeHash, guardErr := r.runOldCodeHashGuard()
	if guardErr != nil {
		return guardErr
	}
	r.report.Controls = append(r.report.Controls, oldCodeHash)
	// Count and byte refusals run before the maximum-byte positive. If the
	// legacy checkpoint ceiling rejects that positive, its structured failure
	// remains a measured independent quota event rather than a Java blocker.
	for _, spec := range []struct{ name, fixture, errName, code string }{
		{"raw151-envelope", "raw151-refusal", "LinkError", "1"},
		{"raw-bytes-over", "raw-bytes-over", "LinkError", "1"},
	} {
		control, refusalErr := r.runRejection(spec.name, spec.fixture, spec.errName, spec.code, maxJvm, maxInternal)
		if refusalErr != nil {
			return refusalErr
		}
		if spec.name == "raw151-envelope" && (len(control.ErrorArgs) < 2 || control.ErrorArgs[1] != "151") {
			return errors.New("raw151 refusal did not report count 151")
		}
		if spec.name == "raw-bytes-over" && (len(control.ErrorArgs) < 2 || control.ErrorArgs[1] != "1063931") {
			return errors.New("raw byte over-limit error did not report 1063931")
		}
		r.report.Controls = append(r.report.Controls, control)
	}
	rowBytes, err := r.runTerminal("raw-bytes-exact", "exact 1,063,930-byte positive aggregate raw envelope", "raw-bytes-exact", 2, "", 0, true)
	if err != nil {
		return err
	}
	if rowBytes.RawCount != 150 || rowBytes.RawBytes != 1063930 || rowBytes.ClassCount != 250 {
		return fmt.Errorf("exact raw-byte positive envelope count/size/diagnostic mismatch: %d/%d/%d", rowBytes.RawCount, rowBytes.RawBytes, rowBytes.ClassCount)
	}
	r.report.Cases = append(r.report.Cases, rowBytes)
	for _, spec := range []struct{ name, fixture, errName, code string }{
		{"unbound-add-concrete", "ArrayListUnboundAddConcrete", "CallError", "4"},
		{"unbound-add-interface", "ArrayListUnboundAddInterface", "CallError", "4"},
		{"unbound-iterator-concrete", "ArrayListUnboundIteratorConcrete", "CallError", "4"},
		{"unbound-iterator-interface", "ArrayListUnboundIteratorInterface", "CallError", "4"},
		{"missing-default-constructor", "ArrayListMissingDefaultConstructor", "", ""},
		{"identity-map-unbound-put-concrete", "IdentityHashMapUnboundPutConcrete", "CallError", "4"},
		{"identity-map-unbound-put-interface", "IdentityHashMapUnboundPutInterface", "CallError", "4"},
		{"identity-map-unbound-get-interface", "IdentityHashMapUnboundGetInterface", "CallError", "4"},
		{"identity-map-object-equals-refusal", "IdentityHashMapUnboundEqualsObject", "CallError", "4"},
		{"identity-map-object-hash-refusal", "IdentityHashMapUnboundHashCodeObject", "CallError", "4"},
		{"identity-map-default-method-refusal", "IdentityHashMapUnboundDefaultMethod", "CallError", "4"},
		{"identity-map-view-refusal", "IdentityHashMapUnboundViews", "CallError", "4"},
		{"identity-map-missing-default-constructor", "IdentityHashMapMissingDefaultConstructor", "", ""},
		{"raw-platform-arraylist-replacement", "raw-platform-replacement", "BootstrapProfileError", "1"},
		{"raw-platform-identity-map-replacement", "identity-map-raw-platform-replacement", "BootstrapProfileError", "1"},
		{"malformed-classfile", "malformed-classfile", "ClassError", "1"},
	} {
		control, refusalErr := r.runRejection(spec.name, spec.fixture, spec.errName, spec.code, maxJvm, maxInternal)
		if refusalErr != nil {
			return refusalErr
		}
		r.report.Controls = append(r.report.Controls, control)
	}
	for _, spec := range []struct {
		name     string
		q        uint64
		internal uint32
	}{
		{"q-zero", 0, maxInternal}, {"q-over", maxJvm + 1, maxInternal},
		{"internal-zero", maxJvm, 0}, {"internal-over", maxJvm, maxInternal + 1},
	} {
		control, budgetErr := r.runBudgetRefusal(spec.name, spec.q, spec.internal, "6")
		if budgetErr != nil {
			return budgetErr
		}
		r.report.Controls = append(r.report.Controls, control)
	}
	// The last q1 request names the raw150 terminal checkpoint for a separate
	// process; this verifies MR01 bytes, roots, head and LevelDB reopen.
	r.report.Status = "generated EVM gates passed; original replay/Done not part of this worker"
	r.report.Mode = "gate"
	r.report.ProcessID = os.Getpid()
	r.report.ElapsedMS = time.Since(started).Milliseconds()
	return writeJSON(filepath.Join(r.reportDir, "gate-summary.json"), r.report)
}

func (r *runner) reopen() error {
	type reopenRequest struct {
		StateDir         string      `json:"stateDir"`
		StateRoot        common.Hash `json:"stateRoot"`
		InstanceID       common.Hash `json:"instanceId"`
		Case             string      `json:"case"`
		Checkpoint       string      `json:"checkpoint"`
		CheckpointRoot   common.Hash `json:"checkpointRoot"`
		MachineStateRoot common.Hash `json:"machineStateRoot"`
		Epoch            uint64      `json:"epoch"`
		Lifecycle        uint8       `json:"lifecycle"`
		PreReopenPID     int         `json:"preReopenPID"`
		Gas              uint64      `json:"gas"`
	}
	requestDir := filepath.Join(r.reportDir, "reopen-requests")
	entries, err := os.ReadDir(requestDir)
	if err != nil {
		return err
	}
	if len(entries) != 2 {
		return fmt.Errorf("fresh-process gate expected two pinned reopen requests, got %d", len(entries))
	}
	rows := make([]map[string]any, 0, len(entries))
	var raw150 map[string]any
	var identityMap map[string]any
	for _, entry := range entries {
		if entry.IsDir() || filepath.Ext(entry.Name()) != ".json" {
			return fmt.Errorf("unexpected reopen request entry %q", entry.Name())
		}
		var req reopenRequest
		readJSON(filepath.Join(requestDir, entry.Name()), &req)
		fc, classes := r.loadCase(req.Case)
		cp, readErr := os.ReadFile(filepath.Join(r.reportDir, "checkpoints", req.Checkpoint))
		if readErr != nil {
			return readErr
		}
		w, openErr := openWorld(req.StateDir, req.StateRoot)
		if openErr != nil {
			return openErr
		}
		r.setCurrent(w)
		if err = r.verifyInstalledCode(w); err == nil {
			var owner common.Address
			var epoch uint64
			var root common.Hash
			var lifecycle uint8
			owner, epoch, root, lifecycle, err = r.getHead(req.InstanceID)
			if err == nil && (owner != callerAddress || epoch != req.Epoch || root != req.CheckpointRoot || lifecycle != req.Lifecycle) {
				err = fmt.Errorf("new-process head mismatch: owner=%s epoch=%d root=%s lifecycle=%d", owner, epoch, root, lifecycle)
			}
			if err == nil && crypto.Keccak256Hash(cp) != req.CheckpointRoot {
				err = errors.New("new-process checkpoint digest mismatch")
			}
			if err == nil {
				err = r.validateCheckpoint(classes, cp, req.MachineStateRoot)
			}
		}
		var audit heapAudit
		if err == nil {
			audit, err = r.checkCP(cp, req.CheckpointRoot, classes)
		}
		if err == nil && req.Case == "IdentityHashMapMatrix" {
			err = r.validateIdentityHashMapMatrix(audit)
		}
		stateRoot := w.root
		w.close()
		if err != nil {
			return err
		}
		if os.Getpid() == req.PreReopenPID {
			return errors.New("reopen verifier did not run in a distinct OS process")
		}
		row := map[string]any{
			"request": entry.Name(), "case": req.Case, "processId": os.Getpid(),
			"priorProcessId": req.PreReopenPID, "distinctProcess": true,
			"stateRoot": stateRoot, "instanceId": req.InstanceID, "epoch": req.Epoch,
			"lifecycle": req.Lifecycle, "checkpointRoot": req.CheckpointRoot,
			"machineStateRoot": req.MachineStateRoot, "rawCount": fc.RawCount,
			"bootstrapCount": 100, "diagnosticClassCount": fc.RawCount + 100,
			"checkpointBytes": len(cp), "heapAudit": audit,
		}
		rows = append(rows, row)
		if req.Case == "raw150-envelope" {
			raw150 = row
		}
		if req.Case == "IdentityHashMapMatrix" {
			identityMap = row
		}
	}
	if raw150 == nil || identityMap == nil {
		return errors.New("fresh-process gate omitted raw150 or IdentityHashMap matrix reopen")
	}
	out := map[string]any{
		"status":    "fresh-process LevelDB/StateDB reopen and read-only EVM checkpoint validation passed",
		"processId": os.Getpid(), "distinctProcess": true, "reopenCount": len(rows),
		"reopens": rows, "rawCount": raw150["rawCount"],
		"bootstrapCount": raw150["bootstrapCount"], "diagnosticClassCount": raw150["diagnosticClassCount"],
		"identityHashMapRawCount":             identityMap["rawCount"],
		"identityHashMapDiagnosticClassCount": identityMap["diagnosticClassCount"],
	}
	return writeJSON(filepath.Join(r.reportDir, "reopen-summary.json"), out)
}

func jsonInt(v any) int64 {
	switch x := v.(type) {
	case *big.Int:
		return x.Int64()
	case uint64:
		return int64(x)
	case uint32:
		return int64(x)
	default:
		return -1
	}
}

func readArtifactPaths(args []string) (*runner, string, error) {
	if len(args) < 6 {
		return nil, "", errors.New("usage: driver <gate|reopen|coordinator> ENGINE.json COORD.json FIXTURE-MANIFEST.json FIXTURE-DIR REPORT-DIR [GAS]")
	}
	mode := args[0]
	gas := ordinaryGas
	if len(args) >= 7 {
		parsed, ok := new(big.Int).SetString(args[6], 10)
		if !ok {
			return nil, "", errors.New("invalid gas budget")
		}
		if !parsed.IsUint64() {
			return nil, "", errors.New("gas budget not uint64")
		}
		gas = parsed.Uint64()
	}
	r := &runner{fixtureDir: args[4], reportDir: args[5], gas: gas}
	var err error
	r.engineArt, r.engineABI, r.engineCode = loadArtifact(args[1])
	r.coordArt, r.coordABI, r.coordCode = loadArtifact(args[2])
	r.coordInit = hexCode(r.coordArt.Bytecode)
	readJSON(args[3], &r.fixtures)
	if err = os.MkdirAll(r.reportDir, 0700); err != nil {
		return nil, "", err
	}
	r.report = report{Status: "running", Mode: mode, EngineSHA256: r.engineArt.CodeHashes.RuntimeSHA256,
		EngineCodeHash: crypto.Keccak256Hash(r.engineCode), CoordinatorSHA256: r.coordArt.CodeHashes.RuntimeSHA256,
		CoordinatorCodeHash: crypto.Keccak256Hash(r.coordCode), GasBudget: gas, Caller: callerAddress,
		Engine: engineAddress, Coordinator: coordinatorAddress, ProcessID: os.Getpid()}
	return r, mode, nil
}

func writeFailure(r *runner, err error) int {
	classification, name := "semantic-or-harness-failure", "unknown"
	var p *positiveCallError
	if errors.As(err, &p) {
		classification, name = p.classification, p.name
	}
	r.report.Status = "failed"
	r.report.Failure = &failureReport{Classification: classification, Case: name, GasBudget: r.gas, Error: err.Error()}
	r.report.ProcessID = os.Getpid()
	_ = writeJSON(filepath.Join(r.reportDir, "gate-failure.json"), r.report)
	fmt.Fprintln(os.Stderr, err)
	if classification == "test-only-gas-budget" {
		return 42
	}
	return 1
}

func main() {
	r, mode, err := readArtifactPaths(os.Args[1:])
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	if mode == "gate" {
		if err = r.gate(); err != nil {
			os.Exit(writeFailure(r, err))
		}
		return
	}
	if mode == "reopen" {
		r.report.Mode = "reopen"
		if err = r.reopen(); err != nil {
			os.Exit(writeFailure(r, err))
		}
		return
	}
	if mode == "coordinator" {
		r.report.Mode = "coordinator"
		if err = r.coordinatorRoute(); err != nil {
			os.Exit(writeFailure(r, err))
		}
		return
	}
	fmt.Fprintln(os.Stderr, "unknown mode", mode)
	os.Exit(2)
}

func auditMachine(machine []byte, rawCount int) (heapAudit, error) {
	var out heapAudit
	p := 0
	need := func(n int) error {
		if n < 0 || p > len(machine) || len(machine)-p < n {
			return fmt.Errorf("machine checkpoint truncated at %d need %d", p, n)
		}
		return nil
	}
	u := func(n int) (uint64, error) {
		if err := need(n); err != nil {
			return 0, err
		}
		var v uint64
		for i := 0; i < n; i++ {
			v = (v << 8) | uint64(machine[p+i])
		}
		p += n
		return v, nil
	}
	skip := func(n int) error {
		if err := need(n); err != nil {
			return err
		}
		p += n
		return nil
	}
	if len(machine) < 4 || string(machine[:4]) != "MR01" {
		return out, errors.New("machine checkpoint magic mismatch")
	}
	p = 4
	if err := skip(1 + 4 + 1 + 4 + 8 + 8 + 1 + 32); err != nil {
		return out, err
	}
	for i := 0; i < 2; i++ {
		n, e := u(2)
		if e != nil {
			return out, e
		}
		if e = skip(int(n)); e != nil {
			return out, e
		}
	}
	argc, e := u(1)
	if e != nil {
		return out, e
	}
	if e = skip(int(argc) * 4); e != nil {
		return out, e
	}
	classCount, e := u(2)
	if e != nil {
		return out, e
	}
	if rawCount < 0 || rawCount > 150 {
		return out, fmt.Errorf("diagnostic raw class count %d outside 0..150", rawCount)
	}
	out.ClassCount = int(classCount)
	out.RawCount = rawCount
	out.BootstrapCount = out.ClassCount - rawCount
	if out.BootstrapCount != 100 {
		return out, fmt.Errorf("checkpoint has %d bootstrap classes, expected100", out.BootstrapCount)
	}
	if out.ClassCount > 250 {
		return out, fmt.Errorf("MR01 diagnostic class count %d exceeds enforced 250", out.ClassCount)
	}
	for i := 0; i < int(classCount); i++ {
		if e = skip(1 + 1); e != nil {
			return out, e
		}
		n, err := u(2)
		if err != nil {
			return out, err
		}
		if err = skip(int(n) * 34); err != nil {
			return out, err
		}
	}
	depth, e := u(2)
	if e != nil {
		return out, e
	}
	for i := 0; i < int(depth); i++ {
		if e = skip(2 + 2 + 4 + 32 + 1 + 4); e != nil {
			return out, e
		}
		sp, err := u(2)
		if err != nil {
			return out, err
		}
		if err = skip(int(sp) * 32); err != nil {
			return out, err
		}
		locals, err := u(2)
		if err != nil {
			return out, err
		}
		if err = skip((int(locals)+7)/8 + int(locals)*32); err != nil {
			return out, err
		}
	}
	next, e := u(4)
	if e != nil {
		return out, e
	}
	out.NextHandle = uint32(next)
	if e = skip(2 + 2 + 4 + 4 + 4 + 2 + 4); e != nil {
		return out, e
	}
	arrays := make(map[uint32]arrayRecord)
	objects := make([]objectRecord, 0)
	for h := uint32(1); h <= out.NextHandle; h++ {
		ordinal, err := u(4)
		if err != nil {
			return out, err
		}
		if ordinal != uint64(h) {
			return out, errors.New("noncanonical heap ordinal")
		}
		if err = need(32); err != nil {
			return out, err
		}
		meta := append([]byte(nil), machine[p:p+32]...)
		p += 32
		ci, err := u(2)
		if err != nil {
			return out, err
		}
		rank, err := u(1)
		if err != nil {
			return out, err
		}
		wire, err := u(4)
		if err != nil {
			return out, err
		}
		isObject := meta[0]&0x80 != 0
		if isObject {
			fields := make([][32]byte, int(wire))
			for i := range fields {
				if err = need(32); err != nil {
					return out, err
				}
				copy(fields[i][:], machine[p:p+32])
				p += 32
			}
			objects = append(objects, objectRecord{handle: h, classIndex: uint32(ci), fields: fields})
			continue
		}
		flags := uint32(wire) & 0xc0000000
		length := uint32(wire) & 0x3fffffff
		rec := arrayRecord{handle: h, meta: new(big.Int).SetBytes(meta), classIndex: uint32(ci), rank: uint8(rank), length: length}
		switch flags {
		case 0:
			rec.wireKind = 0
			if err = need(int(length) * 8); err != nil {
				return out, err
			}
			if rec.meta.Cmp(big.NewInt(0x46)) == 0 && rec.rank == 1 {
				for i := uint32(0); i < length; i++ {
					v := binary.BigEndian.Uint64(machine[p+int(i)*8 : p+int(i+1)*8])
					if v != 0 {
						rec.nonzero++
					}
				}
			}
			if rec.meta.IsUint64() && rec.meta.Uint64() >= 0x100 {
				rec.valuesZero = true
				for i := uint32(0); i < length; i++ {
					if binary.BigEndian.Uint64(machine[p+int(i)*8:p+int(i+1)*8]) != 0 {
						rec.valuesZero = false
					}
				}
			}
			p += int(length) * 8
		case 0x40000000:
			rec.wireKind = flags
			if rec.meta.Cmp(big.NewInt(0x46)) != 0 || rec.rank != 1 {
				return out, errors.New("invalid packed-float record in CP")
			}
			if err = need(int(length) * 4); err != nil {
				return out, err
			}
			for i := uint32(0); i < length; i++ {
				if binary.BigEndian.Uint32(machine[p+int(i)*4:p+int(i+1)*4]) != 0 {
					rec.nonzero++
				}
			}
			p += int(length) * 4
		case 0x80000000:
			rec.wireKind = flags
			if err = need(4); err != nil {
				return out, err
			}
			n := binary.BigEndian.Uint32(machine[p : p+4])
			p += 4
			if err = need(int(n) * 12); err != nil {
				return out, err
			}
			rec.nonzero = n
			p += int(n) * 12
		default:
			return out, errors.New("invalid array wire flags")
		}
		arrays[h] = rec
	}
	out.ArrayListClassIndex = uint32(rawCount + 98)
	out.IdentityHashMapClassIndex = uint32(rawCount + 99)
	out.ObjectClassIndex = uint32(rawCount)
	out.AllBackingsObjectArray = true
	out.AllBackingElementsZero = true
	out.AllIdentityHashMapTablesObjectArray = true
	out.AllIdentityHashMapTableElementsZero = true
	for _, o := range objects {
		if o.classIndex != out.ArrayListClassIndex {
			continue
		}
		out.ArrayListObjects++
		if len(o.fields) != 2 {
			return out, fmt.Errorf("ArrayList object handle %d has %d fields expected2", o.handle, len(o.fields))
		}
		ref := o.fields[0]
		refIsNull := bytes.Equal(ref[:], make([]byte, 32)) ||
			(bytes.Equal(ref[0:23], make([]byte, 23)) && ref[23] == 2 && binary.BigEndian.Uint64(ref[24:32]) == 0)
		if refIsNull {
			// A constructor that throws before assigning elementData leaves a real,
			// partially initialized ArrayList object with its Java default null.
			out.AllBackingsObjectArray = false
			out.AllBackingElementsZero = false
			value := o.fields[1]
			if !bytes.Equal(value[0:23], make([]byte, 23)) || value[23] != 1 || binary.BigEndian.Uint64(value[24:32]) != 0 {
				return out, fmt.Errorf("ArrayList handle %d size field was not Java int zero", o.handle)
			}
			continue
		}
		if !bytes.Equal(ref[0:23], make([]byte, 23)) || ref[23] != 2 || ref[24] != 0 || ref[25] != 0 || ref[26] != 0 || ref[27] != 0 {
			return out, fmt.Errorf("ArrayList handle %d elementData is not a reference", o.handle)
		}
		backing := binary.BigEndian.Uint32(ref[28:32])
		rec, ok := arrays[backing]
		if !ok {
			return out, fmt.Errorf("ArrayList handle %d points to non-array backing %d", o.handle, backing)
		}
		if rec.rank != 1 || rec.classIndex != 0 || !rec.meta.IsUint64() || rec.meta.Uint64() != 0x100+uint64(out.ObjectClassIndex) {
			out.AllBackingsObjectArray = false
		}
		if !rec.valuesZero {
			out.AllBackingElementsZero = false
		}
		// The actual field descriptor and source declaration are pinned separately;
		// the CP record proves its non-null Object[] handle and actual allocation length.
		out.BackingLengths = append(out.BackingLengths, rec.length)
		out.BackingHandles = append(out.BackingHandles, backing)
		value := o.fields[1]
		if !bytes.Equal(value[0:23], make([]byte, 23)) || value[23] != 1 || binary.BigEndian.Uint64(value[24:32]) != 0 {
			return out, fmt.Errorf("ArrayList handle %d size field was not Java int zero", o.handle)
		}
	}
	for _, o := range objects {
		if o.classIndex != out.IdentityHashMapClassIndex {
			continue
		}
		out.IdentityHashMapObjects++
		if len(o.fields) != 2 {
			return out, fmt.Errorf("IdentityHashMap object handle %d has %d fields expected2", o.handle, len(o.fields))
		}
		ref := o.fields[0]
		refIsNull := bytes.Equal(ref[:], make([]byte, 32)) ||
			(bytes.Equal(ref[0:23], make([]byte, 23)) && ref[23] == 2 && binary.BigEndian.Uint64(ref[24:32]) == 0)
		if refIsNull {
			// An OOM constructor can leave its receiver table field at Java's null default.
			out.AllIdentityHashMapTablesObjectArray = false
			out.AllIdentityHashMapTableElementsZero = false
		} else {
			if !bytes.Equal(ref[0:23], make([]byte, 23)) || ref[23] != 2 ||
				ref[24] != 0 || ref[25] != 0 || ref[26] != 0 || ref[27] != 0 {
				return out, fmt.Errorf("IdentityHashMap handle %d table field is not a reference", o.handle)
			}
			backing := binary.BigEndian.Uint32(ref[28:32])
			rec, ok := arrays[backing]
			if !ok {
				return out, fmt.Errorf("IdentityHashMap handle %d points to non-array table %d", o.handle, backing)
			}
			if rec.rank != 1 || rec.classIndex != 0 || !rec.meta.IsUint64() ||
				rec.meta.Uint64() != 0x100+uint64(out.ObjectClassIndex) {
				out.AllIdentityHashMapTablesObjectArray = false
			}
			if !rec.valuesZero {
				out.AllIdentityHashMapTableElementsZero = false
			}
			out.IdentityHashMapBackingLengths = append(out.IdentityHashMapBackingLengths, rec.length)
			out.IdentityHashMapBackingHandles = append(out.IdentityHashMapBackingHandles, backing)
		}
		value := o.fields[1]
		if !bytes.Equal(value[0:23], make([]byte, 23)) || value[23] != 1 || binary.BigEndian.Uint64(value[24:32]) != 0 {
			return out, fmt.Errorf("IdentityHashMap handle %d size field was not Java int zero", o.handle)
		}
	}
	out.FloatNonzeroCounts = map[string]uint32{}
	for _, rec := range arrays {
		if rec.meta.Cmp(big.NewInt(0x46)) != 0 || rec.rank != 1 {
			continue
		}
		if rec.length == 1024 && rec.nonzero > 0 {
			// The wire discriminator is retained by reading the four-byte word from
			// its record offset in the parser below; arrayRecord stores that kind.
			if rec.wireKind == 0x40000000 {
				out.PackedFloatLengths = append(out.PackedFloatLengths, rec.length)
			}
			if rec.wireKind == 0x80000000 {
				out.SparseFloatLengths = append(out.SparseFloatLengths, rec.length)
			}
			out.FloatNonzeroCounts[fmt.Sprintf("%d/%d", rec.wireKind, rec.length)] = rec.nonzero
		}
	}
	if e = skip(1 + 1 + 4 + 32); e != nil {
		return out, e
	}
	intern, e := u(2)
	if e != nil {
		return out, e
	}
	if e = skip(int(intern) * 8); e != nil {
		return out, e
	}
	if len(machine)-p < 24 {
		return out, fmt.Errorf("VFS checkpoint tail truncated at %d", p)
	}
	out.MachineBytes = len(machine)
	return out, nil
}

type objectRecord struct {
	handle, classIndex uint32
	fields             [][32]byte
}
type arrayRecord struct {
	handle     uint32
	meta       *big.Int
	classIndex uint32
	rank       uint8
	length     uint32
	nonzero    uint32
	valuesZero bool
	wireKind   uint32
}
