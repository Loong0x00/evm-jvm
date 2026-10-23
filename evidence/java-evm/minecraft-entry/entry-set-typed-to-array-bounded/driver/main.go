package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math/big"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"time"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/state"
	"github.com/ethereum/go-ethereum/core/tracing"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/core/vm/runtime"
	"github.com/ethereum/go-ethereum/crypto"
)

const callGas uint64 = 1_000_000_000
const internalBudget uint32 = 4096

var engineAddress = common.HexToAddress("0x4d432d52414e444f4d2d434c4153532d50310070")
var callerAddress = common.HexToAddress("0x4d435459504544544f4152524159000000000002")

type artifact struct {
	ABI []abi.Method `json:"-"`
}

type rawArtifact struct {
	ABI              json.RawMessage `json:"abi"`
	DeployedBytecode string          `json:"deployedBytecode"`
}

type seedFile struct {
	Path     []byte
	Data     []byte
	ReadOnly bool
}

type receipt struct {
	Label            string   `json:"label"`
	Quantum          uint64   `json:"quantum"`
	Entry            string   `json:"entry"`
	Calls            int      `json:"calls"`
	GasUsed          uint64   `json:"gasUsed"`
	Lifecycle        uint64   `json:"lifecycle"`
	Outcome          uint64   `json:"outcome"`
	TotalJava        uint64   `json:"totalJava"`
	TotalInternal    uint64   `json:"totalInternal"`
	ExecutedJava     uint64   `json:"executedJava"`
	ExecutedInternal uint64   `json:"executedInternal"`
	JavaKind         uint64   `json:"javaKind"`
	JavaClass        string   `json:"javaClass"`
	CheckpointBytes  int      `json:"checkpointBytes"`
	CheckpointKeccak string   `json:"checkpointKeccak"`
	MachineRoot      string   `json:"machineRoot"`
	VFSRoot          string   `json:"vfsRoot"`
	StateRoot        string   `json:"stateRoot"`
	CallErrors       []string `json:"callErrors,omitempty"`
}

func must(err error) {
	if err != nil {
		panic(err)
	}
}

func field(v interface{}, name string) reflect.Value {
	r := reflect.ValueOf(v)
	for r.IsValid() && (r.Kind() == reflect.Interface || r.Kind() == reflect.Pointer) {
		r = r.Elem()
	}
	if !r.IsValid() || r.Kind() != reflect.Struct {
		panic(fmt.Sprintf("tuple is %T, not struct", v))
	}
	f := r.FieldByName(name)
	if !f.IsValid() {
		panic(fmt.Sprintf("tuple %T missing field %s", v, name))
	}
	return f
}

func uintField(v interface{}, name string) uint64 {
	f := field(v, name)
	switch f.Kind() {
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
		return f.Uint()
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		return uint64(f.Int())
	case reflect.Ptr:
		if n, ok := f.Interface().(*big.Int); ok {
			return n.Uint64()
		}
	}
	panic(fmt.Sprintf("field %s kind %s", name, f.Kind()))
}

func bytesField(v interface{}, name string) []byte {
	f := field(v, name)
	if b, ok := f.Interface().([]byte); ok {
		return b
	}
	panic(fmt.Sprintf("field %s is %s", name, f.Kind()))
}

func uintValue(v interface{}) uint64 {
	r := reflect.ValueOf(v)
	for r.IsValid() && (r.Kind() == reflect.Interface || r.Kind() == reflect.Pointer) {
		if r.Kind() == reflect.Pointer && r.Type().Elem().String() == "big.Int" {
			return r.Interface().(*big.Int).Uint64()
		}
		r = r.Elem()
	}
	if !r.IsValid() {
		panic("nil uint")
	}
	switch r.Kind() {
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
		return r.Uint()
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		return uint64(r.Int())
	}
	panic(fmt.Sprintf("not uint: %T", v))
}

func bytes32Field(v interface{}, name string) common.Hash {
	f := field(v, name)
	if h, ok := f.Interface().([32]byte); ok {
		return common.Hash(h)
	}
	panic(fmt.Sprintf("field %s is %s", name, f.Type()))
}

func stateRoot(st *state.StateDB) common.Hash { return st.Copy().IntermediateRoot(false) }

func call(cfg *runtime.Config, method string, input []byte) ([]byte, uint64, error) {
	cfg.GasLimit = callGas
	ret, left, err := runtime.Call(engineAddress, input, cfg)
	return ret, callGas - left, err
}

func unpackResult(parsed abi.ABI, method string, ret []byte) (interface{}, []byte) {
	values, err := parsed.Unpack(method, ret)
	must(err)
	if len(values) != 2 {
		panic(fmt.Sprintf("%s outputs=%d", method, len(values)))
	}
	return values[0], values[1].([]byte)
}

func runMain(parsed abi.ABI, code []byte, classFiles [][]byte, entry string, quantum uint64, label string) receipt {
	outCheckpoint = nil
	st, err := state.New(types.EmptyRootHash, state.NewDatabaseForTesting())
	must(err)
	st.SetCode(engineAddress, code, tracing.CodeChangeUnspecified)
	before := stateRoot(st)
	cfg := &runtime.Config{State: st, Origin: callerAddress}
	instance := crypto.Keccak256Hash([]byte("entry-set-typed-to-array/" + label))
	seeds := []seedFile{}
	input, err := parsed.Pack("startMain", [32]byte(instance), classFiles, entry, seeds, quantum, internalBudget)
	must(err)
	var out receipt
	out.Label, out.Quantum, out.Entry = label, quantum, entry
	for {
		method := "startMain"
		if out.Calls > 0 {
			method = "resumeMain"
			headInput, e := parsed.Pack("head", [32]byte(instance))
			must(e)
			headRaw, _, e := call(cfg, "head", headInput)
			must(e)
			headValues, e := parsed.Unpack("head", headRaw)
			must(e)
			if len(headValues) != 10 {
				panic("bad head arity")
			}
			head := uintValue(headValues[1])
			checkpointRoot := headValues[2].([32]byte)
			input, err = parsed.Pack("resumeMain", [32]byte(instance), head, checkpointRoot, classFiles, outCheckpoint, quantum, internalBudget)
			must(err)
		}
		ret, used, callErr := call(cfg, method, input)
		out.Calls++
		out.GasUsed += used
		if callErr != nil {
			out.CallErrors = append(out.CallErrors, callErr.Error()+" revert="+hex.EncodeToString(ret))
			break
		}
		result, cp := unpackResult(parsed, method, ret)
		out.Lifecycle = uintField(result, "Lifecycle")
		out.Outcome = uintField(result, "Outcome")
		out.TotalJava = uintField(result, "TotalJvmSteps")
		out.TotalInternal = uintField(result, "TotalInternalSteps")
		out.ExecutedJava = uintField(result, "ExecutedJvmSteps")
		out.ExecutedInternal = uintField(result, "ExecutedInternalSteps")
		out.JavaKind = uintField(result, "JavaKind")
		out.JavaClass = string(bytesField(result, "JavaClass"))
		out.MachineRoot = common.Hash(bytes32Field(result, "MachineStateRoot")).Hex()
		out.VFSRoot = common.Hash(bytes32Field(result, "VfsStateRoot")).Hex()
		outCheckpoint = cp
		if out.Lifecycle != 1 {
			break
		}
		if out.Calls > 10000 {
			panic("bounded quantum-call watchdog exceeded 10000 calls")
		}
	}
	out.CheckpointBytes = len(outCheckpoint)
	if len(outCheckpoint) != 0 {
		out.CheckpointKeccak = crypto.Keccak256Hash(outCheckpoint).Hex()
	}
	out.StateRoot = stateRoot(st).Hex()
	if out.Calls == 0 {
		out.StateRoot = before.Hex()
	}
	return out
}

var outCheckpoint []byte

func runRefusal(parsed abi.ABI, code []byte, classFiles [][]byte, entry, label string) map[string]interface{} {
	st, err := state.New(types.EmptyRootHash, state.NewDatabaseForTesting())
	must(err)
	st.SetCode(engineAddress, code, tracing.CodeChangeUnspecified)
	before := stateRoot(st)
	cfg := &runtime.Config{State: st, Origin: callerAddress}
	instance := crypto.Keccak256Hash([]byte("entry-set-typed-to-array/refusal/" + label))
	input, err := parsed.Pack("startMain", [32]byte(instance), classFiles, entry, []seedFile{}, uint64(65536), internalBudget)
	must(err)
	started := time.Now()
	ret, used, callErr := call(cfg, "startMain", input)
	after := stateRoot(st)
	return map[string]interface{}{"label": label, "entry": entry, "gasUsed": used, "durationMs": time.Since(started).Milliseconds(), "error": fmt.Sprint(callErr), "revertData": hex.EncodeToString(ret), "rootBefore": before.Hex(), "rootAfter": after.Hex(), "rootUnchanged": before == after}
}

func main() {
	if len(os.Args) != 5 {
		panic("usage: driver ARTIFACT.json CLASSES_DIR MODE REPORT.json")
	}
	artifactPath, classDir, mode, reportPath := os.Args[1], os.Args[2], os.Args[3], os.Args[4]
	var raw rawArtifact
	data, err := os.ReadFile(artifactPath)
	must(err)
	must(json.Unmarshal(data, &raw))
	parsed, err := abi.JSON(strings.NewReader(string(raw.ABI)))
	must(err)
	code, err := hex.DecodeString(strings.TrimPrefix(raw.DeployedBytecode, "0x"))
	must(err)
	classFiles := make([][]byte, 0, 8)
	for _, n := range []string{"TypedToArrayPositive", "TypedToArrayShortArray", "TypedToArrayUnsupportedAdd", "TypedToArrayUnsupportedEquals", "TypedToArrayUnsupportedNoArg"} {
		p := filepath.Join(classDir, n+".class")
		b, e := os.ReadFile(p)
		must(e)
		classFiles = append(classFiles, b)
	}
	receipts := make([]receipt, 0, 3)
	for _, q := range []uint64{1, 7, 65536} {
		receipts = append(receipts, runMain(parsed, code, classFiles[:1], "TypedToArrayPositive", q, fmt.Sprintf("positive-q%d", q)))
	}
	for i := 1; i < len(receipts); i++ {
		a, b := receipts[0], receipts[i]
		if a.Lifecycle != b.Lifecycle || a.Outcome != b.Outcome || a.TotalJava != b.TotalJava ||
			a.TotalInternal != b.TotalInternal || a.MachineRoot != b.MachineRoot || a.VFSRoot != b.VFSRoot {
			panic(fmt.Sprintf("quantum inequivalence q1 vs q%d: %#v %#v", b.Quantum, a, b))
		}
	}
	refusals := []map[string]interface{}{
		runRefusal(parsed, code, classFiles, "TypedToArrayShortArray", "short-array-raw-refusal"),
		runRefusal(parsed, code, classFiles, "TypedToArrayUnsupportedAdd", "entryset-add-remains-unbound"),
		runRefusal(parsed, code, classFiles, "TypedToArrayUnsupportedEquals", "entryset-equals-remains-unbound"),
		runRefusal(parsed, code, classFiles, "TypedToArrayUnsupportedNoArg", "noarg-toArray-remains-unbound"),
	}
	for _, r := range refusals {
		if r["error"] == "<nil>" || r["rootUnchanged"] != true || !strings.HasPrefix(r["revertData"].(string), "d631c3a4") {
			panic(fmt.Sprintf("refusal did not remain atomic CallError: %#v", r))
		}
	}
	result := map[string]interface{}{"engineRuntimeSHA256": fmt.Sprintf("%x", sha256.Sum256(code)), "engineRuntimeKeccak256": crypto.Keccak256Hash(code).Hex(), "mode": mode, "positive": receipts, "refusals": refusals}
	encoded, err := json.MarshalIndent(result, "", "  ")
	must(err)
	must(os.MkdirAll(filepath.Dir(reportPath), 0755))
	must(os.WriteFile(reportPath, append(encoded, '\n'), 0644))
	fmt.Printf("report=%s positive=%d refusals=%d\n", reportPath, len(receipts), len(refusals))
}
