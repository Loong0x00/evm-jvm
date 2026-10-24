package main

import (
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
	"time"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	evmrun "github.com/ethereum/go-ethereum/core/vm/runtime"
)

type artifact struct { DeployedBytecode string `json:"deployedBytecode"`; ABI json.RawMessage `json:"abi"` }
type seed struct { Path []byte; Data []byte; ReadOnly bool }

func main() {
	if len(os.Args) != 4 { panic("usage: runner <engine-json> <fixture-dir> <quantum>") }
	quantum, err := strconv.ParseUint(os.Args[3], 10, 64); must(err)
	if quantum == 0 || quantum > 65536 { panic("quantum outside accepted bound") }
	ab, err := os.ReadFile(os.Args[1]); must(err)
	var art artifact; must(json.Unmarshal(ab, &art))
	parsed, err := abi.JSON(strings.NewReader(string(art.ABI))); must(err)
	code, err := hex.DecodeString(art.DeployedBytecode); must(err)
	dir := os.Args[2]
	entries, err := os.ReadDir(dir); must(err)
	var names []string
	for _, entry := range entries { if !entry.IsDir() && strings.HasSuffix(entry.Name(), ".class") { names = append(names, entry.Name()) } }
	// Stable fixture order: entry first, fillers in lexical order, Component last.
	if len(names) == 150 {
		ordered := []string{"Probe.class"}
		for _, name := range names { if name != "Probe.class" && name != "Component.class" { ordered = append(ordered, name) } }
		ordered = append(ordered, "Component.class")
		names = ordered
	}
	var classes [][]byte
	for _, name := range names { b, e := os.ReadFile(filepath.Join(dir, name)); must(e); classes = append(classes, b) }
	if len(classes) == 0 { panic("fixture has no classfiles") }
	var id [32]byte; copy(id[:], []byte("reflect-array-newinstance"))
	cfg := &evmrun.Config{GasLimit: 1_000_000_000, Origin: common.HexToAddress("0x1001")}
	var out []byte
	start := time.Now()
	input, err := parsed.Pack("startMain", id, classes, "Probe", []seed{}, quantum, uint32(4096)); must(err)
	out, cfg.State, err = evmrun.Execute(code, input, cfg)
	if err != nil { fmt.Printf("start revert=%x\n", out); panic(err) }
	values, err := parsed.Unpack("startMain", out); must(err)
	if len(values) != 2 { panic(fmt.Sprintf("start output values %d", len(values))) }
	resumeCount := uint64(0)
	for {
		v := reflect.ValueOf(values[0]); for v.Kind() == reflect.Pointer { v = v.Elem() }
		lifecycle := v.FieldByName("Lifecycle").Uint()
		if lifecycle != 1 { break }
		fmt.Printf("continuing epoch=%d lifecycle=%d\n", v.FieldByName("Epoch").Uint(), lifecycle)
		checkpoint := values[1].([]byte)
		cfg.State.Finalise(true)
		headdata, e := parsed.Pack("head", id); must(e)
		hout, _, e := evmrun.Call(common.BytesToAddress([]byte("contract")), headdata, cfg); must(e)
		hv, e := parsed.Unpack("head", hout); must(e)
		fmt.Printf("anchor=%v epoch=%v lifecycle=%v\n", hv[0], hv[1], hv[9])
		epoch := v.FieldByName("Epoch").Uint()
		root := v.FieldByName("CheckpointRoot").Interface().([32]byte)
		input, err = parsed.Pack("resumeMain", id, epoch, root, classes, checkpoint, quantum, uint32(4096)); must(err)
		out, _, err = evmrun.Call(common.BytesToAddress([]byte("contract")), input, cfg)
		if err != nil { fmt.Printf("resume revert=%x\n", out); panic(err) }
		values, err = parsed.Unpack("resumeMain", out); must(err)
		if len(values) != 2 { panic(fmt.Sprintf("resume output values %d", len(values))) }
		resumeCount++
	}
	elapsed := time.Since(start)
	v := reflect.ValueOf(values[0]); for v.Kind() == reflect.Pointer { v = v.Elem() }
	fmt.Printf("elapsed=%s quantum=%d resumes=%d outputBytes=%d\n", elapsed, quantum, resumeCount, len(out))
	for _, n := range []string{"Lifecycle", "Outcome", "JavaKind", "JavaRef", "JavaClass", "ExecutedJvmSteps", "TotalJvmSteps", "Epoch", "CheckpointRoot", "MachineStateRoot", "VfsStateRoot"} {
		fmt.Printf("%s=%v\n", n, v.FieldByName(n).Interface())
	}
	checkpoint := values[1].([]byte)
	fmt.Printf("checkpointBytes=%d\n", len(checkpoint))
}
func must(err error) { if err != nil { panic(err) } }
