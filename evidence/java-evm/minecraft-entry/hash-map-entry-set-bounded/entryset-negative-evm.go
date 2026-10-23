package main

import (
	"bytes"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math/big"
	"os"

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
	Path, Data []byte
	ReadOnly   bool
}
type observation struct {
	Case          string `json:"case"`
	ErrorSelector string `json:"errorSelector"`
	ErrorData     string `json:"errorData"`
	RefusalAtomic bool   `json:"refusalAtomic"`
}

func must(err error) {
	if err != nil {
		panic(err)
	}
}
func main() {
	if len(os.Args) != 4 {
		panic("engine.json fixture-class-dir report.json")
	}
	b, err := os.ReadFile(os.Args[1])
	must(err)
	var a artifact
	must(json.Unmarshal(b, &a))
	engineABI, err := abi.JSON(bytes.NewReader(a.ABI))
	must(err)
	packError := func(name string, args ...interface{}) []byte {
		definition := engineABI.Errors[name]
		payload, e := definition.Inputs.Pack(args...)
		must(e)
		return append(append([]byte(nil), definition.ID[:4]...), payload...)
	}
	code, err := hex.DecodeString(a.DeployedBytecode)
	must(err)
	origin := common.HexToAddress("0x0000000000000000000000000000000000000001")
	contract := common.BytesToAddress([]byte("contract"))
	invoke := func(st *state.StateDB, data []byte) ([]byte, error) {
		out, _, e := evmrun.Call(contract, data, &evmrun.Config{State: st, Origin: origin, GasLimit: 1_000_000_000})
		return out, e
	}
	mkState := func() *state.StateDB {
		st, e := state.New(types.EmptyRootHash, state.NewDatabaseForTesting())
		must(e)
		st.CreateAccount(contract)
		st.SetCode(contract, code, tracing.CodeChangeUnspecified)
		return st
	}
	load := func(name string) []byte { x, e := os.ReadFile(os.Args[2] + "/" + name); must(e); return x }
	rawProbe := [][]byte{load("EntrySetUnsupportedProbe.class")}
	rawReplacement := [][]byte{load("EntrySetUnsupportedProbe.class"), load("HashMap.class")}
	check := func(name string, raw [][]byte, want []byte) observation {
		st := mkState()
		id := common.BytesToHash([]byte("negative-" + name))
		data, e := engineABI.Pack("startMain", id, raw, "EntrySetUnsupportedProbe", []seedFile{}, uint64(65536), uint32(4096))
		must(e)
		out, callErr := invoke(st, data)
		if callErr == nil {
			panic(name + ": expected raw refusal")
		}
		if len(out) < 4 {
			panic(fmt.Sprintf("%s: no custom refusal bytes: %x (%v)", name, out, callErr))
		}
		selector := hex.EncodeToString(out[:4])
		if !bytes.Equal(out, want) {
			panic(fmt.Sprintf("%s: error %x wanted %x", name, out, want))
		}
		headData, e := engineABI.Pack("head", id)
		must(e)
		headOut, e := invoke(st, headData)
		if e != nil {
			panic(e)
		}
		headVals, e := engineABI.Unpack("head", headOut)
		must(e)
		epoch := headVals[1].(uint64)
		if epoch != 0 {
			panic(name + ": refusal published state")
		}
		return observation{Case: name, ErrorSelector: "0x" + selector, ErrorData: "0x" + hex.EncodeToString(out), RefusalAtomic: true}
	}
	// Existing HashMap byte image is also pinned; supplying it raw must be refused.
	replacement := check("raw-HashMap-replacement", rawReplacement, packError("BootstrapProfileError", big.NewInt(1), big.NewInt(1)))
	unsupported := check("entrySet-equals", rawProbe, packError("CallError", big.NewInt(4), big.NewInt(15)))
	out := []observation{replacement, unsupported}
	report, err := json.MarshalIndent(map[string]interface{}{"profile": "generated raw replacement and unsupported EntrySet API EVM refusals", "cases": out}, "", "  ")
	must(err)
	must(os.WriteFile(os.Args[3], append(report, '\n'), 0600))
	fmt.Printf("PASS atomic EVM refusals: %s %s\n", replacement.ErrorSelector, unsupported.ErrorSelector)
}
