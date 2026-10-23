package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"math/big"
	"os"
	"path/filepath"
	"reflect"
	"sort"
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
	"github.com/ethereum/go-ethereum/params"
	"github.com/ethereum/go-ethereum/triedb"
	"github.com/holiman/uint256"
)

const gasCeiling = uint64(1_000_000_000)
const callTimeout = 30 * time.Second

var engineAddress = common.HexToAddress("0x4d432d52414e444f4d2d434c4153532d50310070")
var sender = common.HexToAddress("0x4d432d52414e444f4d2d434c4153532d50310071")

type seed struct {
	Path     []byte
	Data     []byte
	ReadOnly bool
}
type result struct {
	Name          string `json:"name"`
	Passed        bool   `json:"passed"`
	Calls         int    `json:"calls"`
	Gas           uint64 `json:"gas"`
	MaxCallGas    uint64 `json:"maxCallGas,omitempty"`
	Lifecycle     uint64 `json:"lifecycle,omitempty"`
	JavaSteps     uint64 `json:"javaSteps,omitempty"`
	InternalSteps uint64 `json:"internalSteps,omitempty"`
	MachineRoot   string `json:"machineRoot,omitempty"`
	VFSRoot       string `json:"vfsRoot,omitempty"`
	Detail        string `json:"detail,omitempty"`
}
type report struct {
	Profile          string   `json:"profile"`
	RuntimeSHA256    string   `json:"runtimeSHA256"`
	RuntimeKeccak256 string   `json:"runtimeKeccak256"`
	RawClassCount    int      `json:"rawClassCount"`
	RawBytes         int      `json:"rawBytes"`
	Results          []result `json:"results"`
}
type output struct {
	Raw       []byte
	GasUsed   uint64
	Err       error
	Cancelled bool
}

func must(err error) {
	if err != nil {
		panic(err)
	}
}
func sha(b []byte) string { h := sha256.Sum256(b); return hex.EncodeToString(h[:]) }
func loadABI(p string) abi.ABI {
	b, e := os.ReadFile(p)
	must(e)
	a, e := abi.JSON(strings.NewReader(string(b)))
	must(e)
	return a
}
func readClasses(dir string) [][]byte {
	names, e := filepath.Glob(filepath.Join(dir, "*.class"))
	must(e)
	sort.Strings(names)
	out := make([][]byte, 0, len(names))
	for _, n := range names {
		b, e := os.ReadFile(n)
		must(e)
		out = append(out, b)
	}
	return out
}
func makeState(runtime []byte) *state.StateDB {
	db := rawdb.NewMemoryDatabase()
	tdb := triedb.NewDatabase(db, triedb.HashDefaults)
	st, e := state.New(types.EmptyRootHash, state.NewDatabase(tdb, nil))
	must(e)
	st.CreateAccount(engineAddress)
	st.SetCode(engineAddress, runtime, tracing.CodeChangeUnspecified)
	return st
}
func call(st *state.StateDB, input []byte) output {
	z := common.Hash{}
	cfg := &evmrun.Config{ChainConfig: params.AllDevChainProtocolChanges, Difficulty: new(big.Int), Origin: sender, Coinbase: common.Address{}, BlockNumber: big.NewInt(1), Time: 1, GasLimit: gasCeiling, GasPrice: new(big.Int), Value: new(big.Int), BaseFee: new(big.Int).SetUint64(params.InitialBaseFee), BlobBaseFee: new(big.Int).SetUint64(params.BlobTxMinBlobGasprice), Random: &z, State: st, GetHashFn: func(uint64) common.Hash { return common.Hash{} }}
	v := evmrun.NewEnv(cfg)
	rules := cfg.ChainConfig.Rules(v.Context.BlockNumber, v.Context.Random != nil, v.Context.Time)
	st.Prepare(rules, cfg.Origin, cfg.Coinbase, &engineAddress, vm.ActivePrecompiles(rules), nil)
	var cancelled atomic.Bool
	fired := make(chan struct{})
	timer := time.AfterFunc(callTimeout, func() { cancelled.Store(true); v.Cancel(); close(fired) })
	raw, left, err := v.Call(sender, engineAddress, input, gasCeiling, uint256.MustFromBig(cfg.Value))
	if !timer.Stop() {
		<-fired
	}
	return output{Raw: raw, GasUsed: gasCeiling - left, Err: err, Cancelled: cancelled.Load()}
}
func rootsEqual(a, b []byte) bool { return string(a) == string(b) }
func tupleField(v interface{}, name string) reflect.Value {
	x := reflect.ValueOf(v)
	if x.Kind() == reflect.Pointer {
		x = x.Elem()
	}
	return x.FieldByName(name)
}
func decodeSlice(a abi.ABI, method string, out []byte) ([]interface{}, error) {
	return a.Unpack(method, out)
}
func mainResult(a abi.ABI, method string, raw []byte) (uint64, uint64, uint64, uint64, []byte, []byte, error) {
	v, e := decodeSlice(a, method, raw)
	if e != nil {
		return 0, 0, 0, 0, nil, nil, e
	}
	if len(v) != 2 {
		return 0, 0, 0, 0, nil, nil, fmt.Errorf("expected result+checkpoint")
	}
	r := v[0]
	epoch := tupleField(r, "Epoch").Uint()
	life := tupleField(r, "Lifecycle").Uint()
	jvm := tupleField(r, "TotalJvmSteps").Uint()
	internal := tupleField(r, "TotalInternalSteps").Uint()
	mach := tupleField(r, "MachineStateRoot").Interface().([32]byte)
	vfs := tupleField(r, "VfsStateRoot").Interface().([32]byte)
	_ = vfs
	cp := v[1].([]byte)
	return epoch, life, jvm, internal, mach[:], append([]byte(nil), cp...), nil
}
func execute(a abi.ABI, runtime []byte, classes [][]byte, entry string, q uint64) (result, []byte, error) {
	st := makeState(runtime)
	instance := crypto.Keccak256Hash([]byte("list-iterator-link/equivalence"))
	callCount := 0
	var totalGas, maxGas uint64
	input, e := a.Pack("startMain", [32]byte(instance), classes, entry, []seed{}, q, uint32(4096))
	if e != nil {
		return result{}, nil, e
	}
	var out output
	out = call(st, input)
	callCount++
	totalGas += out.GasUsed
	if out.GasUsed > maxGas {
		maxGas = out.GasUsed
	}
	if out.Err != nil {
		return result{Name: "inherited-interface/main", Calls: callCount, Gas: totalGas, Detail: fmt.Sprintf("startMain: %v reverted=0x%x", out.Err, out.Raw)}, nil, out.Err
	}
	var lastMachine, lastVFS []byte
	var totalSteps, totalInternal uint64
	var lifecycle uint64
	for n := 0; n < 2000; n++ {
		epoch, life, steps, internal, mach, cp, e := mainResult(a, "startMain", out.Raw)
		if e != nil {
			return result{}, nil, e
		}
		lifecycle = life
		totalSteps = steps
		totalInternal = internal
		lastMachine = mach
		// VFS root is decoded independently from the return tuple to retain the exact oracle.
		vals, _ := a.Unpack("startMain", out.Raw)
		vfsRoot := tupleField(vals[0], "VfsStateRoot").Interface().([32]byte)
		lastVFS = vfsRoot[:]
		if life != 1 {
			if life != 2 {
				return result{Name: "inherited-interface/main", Calls: callCount, Gas: totalGas, Lifecycle: life, Detail: "main ended in non-VOID lifecycle"}, nil, fmt.Errorf("unexpected lifecycle %d", life)
			}
			break
		}
		root := tupleFieldMust(a, "startMain", out.Raw, "CheckpointRoot")
		resume, e := a.Pack("resumeMain", [32]byte(instance), epoch, root, classes, cp, q, uint32(4096))
		if e != nil {
			return result{}, nil, e
		}
		out = call(st, resume)
		callCount++
		totalGas += out.GasUsed
		if out.GasUsed > maxGas {
			maxGas = out.GasUsed
		}
		if out.Err != nil {
			return result{Name: "inherited-interface/main", Calls: callCount, Gas: totalGas, Lifecycle: life, Detail: fmt.Sprintf("resume: %v reverted=0x%x", out.Err, out.Raw)}, nil, out.Err
		}
		if n == 1999 {
			return result{}, nil, errors.New("resume iteration bound")
		}
	}
	_ = lastVFS
	r := result{Name: "inherited-interface/main", Passed: true, Calls: callCount, Gas: totalGas, MaxCallGas: maxGas, Lifecycle: lifecycle, JavaSteps: totalSteps, InternalSteps: totalInternal, MachineRoot: hex.EncodeToString(lastMachine)}
	vals, _ := a.Unpack("startMain", out.Raw)
	r.VFSRoot = fmt.Sprintf("%x", tupleField(vals[0], "VfsStateRoot").Interface().([32]byte))
	return r, st.IntermediateRoot(true).Bytes(), nil
}
func refusal(a abi.ABI, code []byte, classes [][]byte, entry string) result {
	st := makeState(code)
	instance := crypto.Keccak256Hash([]byte("list-iterator-link/refusal/" + entry))
	input, err := a.Pack("startMain", [32]byte(instance), classes, entry, []seed{}, uint64(128), uint32(4096))
	must(err)
	before := st.IntermediateRoot(true)
	out := call(st, input)
	after := st.IntermediateRoot(true)
	name := ""
	if len(out.Raw) >= 4 {
		for candidate, kind := range a.Errors {
			if bytes.Equal(out.Raw[:4], kind.ID[:4]) {
				name = candidate
				break
			}
		}
	}
	allowed := name == "BootstrapProfileError" || name == "CallError" || name == "LinkError" || name == "HierarchyError" || name == "MethodError"
	ok := out.Err != nil && allowed && before == after && !out.Cancelled
	return result{Name: entry, Passed: ok, Calls: 1, Gas: out.GasUsed, Detail: fmt.Sprintf("revert=%s selector=0x%x atomic=%t canceled=%t", name, out.Raw[:minInt(4, len(out.Raw))], before == after, out.Cancelled)}
}
func minInt(a, b int) int {
	if a < b {
		return a
	}
	return b
}
func tupleFieldMust(a abi.ABI, method string, raw []byte, name string) [32]byte {
	vals, e := a.Unpack(method, raw)
	must(e)
	return tupleField(vals[0], name).Interface().([32]byte)
}
func main() {
	root := os.Getenv("MC_LINK_ROOT")
	if root == "" {
		root = "evidence/java-evm/minecraft-entry/list-iterator-link-bounded"
	}
	runtimePath := os.Getenv("MC_LINK_RUNTIME")
	if runtimePath == "" {
		runtimePath = filepath.Join(root, "engine/MCEntryInterpreter.runtime.hex")
	}
	b, e := os.ReadFile(runtimePath)
	must(e)
	code, e := hex.DecodeString(strings.TrimSpace(string(b)))
	must(e)
	a := loadABI(filepath.Join(root, "engine/MCEntryInterpreter.abi.json"))
	classes := readClasses(filepath.Join(root, "tests/raw150-classes"))
	if len(classes) != 150 {
		panic(fmt.Sprintf("raw classes %d", len(classes)))
	}
	rawBytes := 0
	for _, c := range classes {
		rawBytes += len(c)
	}
	rpt := report{Profile: "MC-LIST-ITERATOR-LINK-BOUNDED-1", RuntimeSHA256: sha(code), RuntimeKeccak256: crypto.Keccak256Hash(code).Hex(), RawClassCount: len(classes), RawBytes: rawBytes}
	r, _, e := execute(a, code, classes, "LinkCheck", 128)
	if e != nil {
		r.Passed = false
		r.Detail = fmt.Sprintf("%v", e)
	}
	r.Name = "raw150/high-index-typed-array-clone"
	rpt.Results = append(rpt.Results, r)
	small := readClasses(filepath.Join(root, "tests/classes"))
	var eq []result
	for _, q := range []uint64{1, 7, 128} {
		x, _, err := execute(a, code, small, "LinkCheck", q)
		if err != nil {
			x.Passed = false
			x.Detail = fmt.Sprintf("%v", err)
		}
		x.Name = fmt.Sprintf("interface-dispatch-q%d", q)
		rpt.Results = append(rpt.Results, x)
		eq = append(eq, x)
	}
	if len(eq) == 3 {
		identical := eq[0].Lifecycle == eq[1].Lifecycle && eq[1].Lifecycle == eq[2].Lifecycle && eq[0].JavaSteps == eq[1].JavaSteps && eq[1].JavaSteps == eq[2].JavaSteps && eq[0].MachineRoot == eq[1].MachineRoot && eq[1].MachineRoot == eq[2].MachineRoot && eq[0].VFSRoot == eq[1].VFSRoot && eq[1].VFSRoot == eq[2].VFSRoot
		rpt.Results = append(rpt.Results, result{Name: "q1-q7-coarse-final-roots", Passed: identical, Detail: fmt.Sprintf("identical=%t", identical)})
	}
	apiClasses := readClasses(filepath.Join(root, "tests/api-classes"))
	for _, entry := range []string{"ApiPrevious", "ApiAdd", "ApiSet", "ApiRemove"} {
		rpt.Results = append(rpt.Results, refusal(a, code, apiClasses, entry))
	}
	canonical, err := os.ReadFile(filepath.Join(root, "ListIterator.class"))
	must(err)
	rpt.Results = append(rpt.Results, refusal(a, code, [][]byte{canonical}, "RawListIteratorReserved"))
	out, e := json.MarshalIndent(rpt, "", "  ")
	must(e)
	fmt.Println(string(out))
	if e != nil {
		os.Exit(1)
	}
	for _, x := range rpt.Results {
		if !x.Passed {
			os.Exit(1)
		}
	}
}
