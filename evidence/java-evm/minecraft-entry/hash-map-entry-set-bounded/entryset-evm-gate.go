package main

import (
	"bytes"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"reflect"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/state"
	"github.com/ethereum/go-ethereum/core/tracing"
	"github.com/ethereum/go-ethereum/core/types"
	evmrun "github.com/ethereum/go-ethereum/core/vm/runtime"
)

type artifact struct {
	ABI              json.RawMessage `json:"abi"`
	DeployedBytecode string          `json:"deployedBytecode"`
}
type seedFile struct {
	Path     []byte
	Data     []byte
	ReadOnly bool
}

type summary struct {
	Lifecycle          uint8  `json:"lifecycle"`
	Outcome            uint8  `json:"outcome"`
	Epoch              uint64 `json:"epoch"`
	CheckpointRoot     string `json:"checkpointRoot"`
	MachineStateRoot   string `json:"machineStateRoot"`
	VFSStateRoot       string `json:"vfsStateRoot"`
	TotalJvmSteps      uint64 `json:"totalJvmSteps"`
	TotalInternalSteps uint64 `json:"totalInternalSteps"`
	Result             int32  `json:"result"`
	JavaKind           uint8  `json:"javaKind"`
	JavaClass          string `json:"javaClass"`
}

func readArtifact(path string) (abi.ABI, []byte) {
	b, err := os.ReadFile(path)
	must(err)
	var a artifact
	must(json.Unmarshal(b, &a))
	contractABI, err := abi.JSON(bytes.NewReader(a.ABI))
	must(err)
	code, err := hex.DecodeString(a.DeployedBytecode)
	must(err)
	return contractABI, code
}
func must(err error) {
	if err != nil {
		panic(err)
	}
}
func getField(v reflect.Value, name string) reflect.Value { return v.FieldByName(name) }
func summaryOf(v interface{}) summary {
	x := reflect.ValueOf(v)
	get := func(n string) reflect.Value { return getField(x, n) }
	bytes32 := func(n string) string {
		f := get(n)
		b := make([]byte, f.Len())
		for i := range b {
			b[i] = byte(f.Index(i).Uint())
		}
		return "0x" + hex.EncodeToString(b)
	}
	return summary{
		Lifecycle: uint8(get("Lifecycle").Uint()), Outcome: uint8(get("Outcome").Uint()), Epoch: get("Epoch").Uint(),
		CheckpointRoot: bytes32("CheckpointRoot"), MachineStateRoot: bytes32("MachineStateRoot"), VFSStateRoot: bytes32("VfsStateRoot"),
		TotalJvmSteps: get("TotalJvmSteps").Uint(), TotalInternalSteps: get("TotalInternalSteps").Uint(),
		Result: int32(get("Result").Int()), JavaKind: uint8(get("JavaKind").Uint()), JavaClass: string(get("JavaClass").Bytes()),
	}
}
func invoke(contract common.Address, st *state.StateDB, origin common.Address, data []byte) []byte {
	out, _, err := evmrun.Call(contract, data, &evmrun.Config{State: st, Origin: origin, GasLimit: 1_000_000_000})
	if err != nil {
		panic(fmt.Errorf("EVM call failed: %w revertData=0x%x", err, out))
	}
	return out
}
func run(q uint64, engineABI abi.ABI, code []byte, raw [][]byte, origin common.Address) summary {
	st, err := state.New(types.EmptyRootHash, state.NewDatabaseForTesting())
	must(err)
	contract := common.BytesToAddress([]byte("contract"))
	st.CreateAccount(contract)
	st.SetCode(contract, code, tracing.CodeChangeUnspecified)
	id := common.BytesToHash([]byte(fmt.Sprintf("entryset-q-%d", q)))
	data, err := engineABI.Pack("startMain", id, raw, "EntrySetProbe", []seedFile{}, q, uint32(4096))
	must(err)
	ret := invoke(contract, st, origin, data)
	vals, err := engineABI.Unpack("startMain", ret)
	must(err)
	cur := summaryOf(vals[0])
	checkpoint := vals[1].([]byte)
	for calls := 0; cur.Lifecycle == 1; calls++ {
		if calls > 16384 {
			panic("resume call bound exceeded")
		}
		data, err = engineABI.Pack("resumeMain", id, cur.Epoch, [32]byte(common.HexToHash(cur.CheckpointRoot)), raw, checkpoint, q, uint32(4096))
		must(err)
		ret = invoke(contract, st, origin, data)
		vals, err = engineABI.Unpack("resumeMain", ret)
		must(err)
		cur = summaryOf(vals[0])
		checkpoint = vals[1].([]byte)
	}
	if cur.Lifecycle != 2 || cur.Outcome != 2 || cur.JavaKind != 0 {
		panic(fmt.Sprintf("guest did not complete normally: %+v", cur))
	}
	return cur
}
func main() {
	if len(os.Args) != 4 {
		panic("engine.json fixture-class-dir report.json")
	}
	engineABI, code := readArtifact(os.Args[1])
	raw := make([][]byte, 0, 2)
	for _, name := range []string{"EntrySetProbe.class", "EntrySetProbe$Key.class"} {
		b, err := os.ReadFile(os.Args[2] + "/" + name)
		must(err)
		raw = append(raw, b)
	}
	origin := common.HexToAddress("0x0000000000000000000000000000000000000001")
	q1 := run(1, engineABI, code, raw, origin)
	q7 := run(7, engineABI, code, raw, origin)
	if q1.MachineStateRoot != q7.MachineStateRoot || q1.VFSStateRoot != q7.VFSStateRoot || q1.TotalJvmSteps != q7.TotalJvmSteps || q1.TotalInternalSteps != q7.TotalInternalSteps {
		panic("q1/q7 terminal state/counter mismatch")
	}
	b, err := json.MarshalIndent(map[string]interface{}{"profile": "generated HashMap.entrySet direct-engine q1/q7", "engineRuntimeKeccak": "8a68539b311dc63c0e274092fb7e30a7d319f5f8ff88768a28b98bbb5521d9ed", "rawClasses": 2, "q1": q1, "q7": q7}, "", "  ")
	must(err)
	must(os.WriteFile(os.Args[3], append(b, '\n'), 0600))
	fmt.Printf("PASS q1/q7 genuine EVM guest completion: Java=%d internal=%d root=%s\n", q1.TotalJvmSteps, q1.TotalInternalSteps, q1.MachineStateRoot)
}
