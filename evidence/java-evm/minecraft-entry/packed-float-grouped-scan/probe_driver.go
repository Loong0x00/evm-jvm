// Test-only direct EVM caller for groupedScanProbe(uint64[]).
package main

import (
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"strings"

	"github.com/ethereum/go-ethereum/core/vm"
	evmrun "github.com/ethereum/go-ethereum/core/vm/runtime"
	"github.com/ethereum/go-ethereum/crypto"
)

const ordinaryGas = uint64(1_000_000_000)
const handle = uint64(37)

type result struct {
	Name           string `json:"name"`
	Length         int    `json:"length"`
	Expected       uint64 `json:"expectedCount"`
	Actual         uint64 `json:"actualCount"`
	ExpectedPacked bool   `json:"expectedPacked"`
	Packed         bool   `json:"packed"`
	ExpectedSparse bool   `json:"expectedSparse"`
	Sparse         bool   `json:"sparse"`
	Error          string `json:"error,omitempty"`
	ErrorCode      uint64 `json:"errorCode,omitempty"`
	ErrorRef       uint64 `json:"errorRef,omitempty"`
	GasCeiling     uint64 `json:"suppliedGas"`
}

type report struct {
	Result          string   `json:"result"`
	GeneratedOnly   bool     `json:"generatedOnly"`
	OrdinaryGas     uint64   `json:"ordinaryExternalGas"`
	Handle          uint64   `json:"handle"`
	RuntimeBytes    int      `json:"runtimeBytes"`
	SuccessfulCases int      `json:"successfulCases"`
	RefusalCases    int      `json:"typedRefusalCases"`
	Cases           []result `json:"cases"`
}

func word(n uint64) []byte {
	b := make([]byte, 32)
	binary.BigEndian.PutUint64(b[24:], n)
	return b
}

func calldata(selector []byte, values []uint64) []byte {
	data := append([]byte{}, selector...)
	data = append(data, word(32)...)
	data = append(data, word(uint64(len(values)))...)
	for _, value := range values {
		data = append(data, word(value)...)
	}
	return data
}

func run(code, selector []byte, tc result, values []uint64, wantError bool) result {
	input := calldata(selector, values)
	ret, _, err := evmrun.Execute(code, input, &evmrun.Config{GasLimit: ordinaryGas})
	tc.Length = len(values)
	tc.GasCeiling = ordinaryGas
	if wantError {
		wantSelector := crypto.Keccak256([]byte("LC0StateError(uint256,uint256)"))[:4]
		if err == nil || !errors.Is(err, vm.ErrExecutionReverted) || len(ret) != 68 || string(ret[:4]) != string(wantSelector) {
			panic(fmt.Sprintf("%s: expected LC0StateError revert, err=%v returndata=%x", tc.Name, err, ret))
		}
		tc.Error = "LC0StateError"
		tc.ErrorCode = binary.BigEndian.Uint64(ret[28:36])
		tc.ErrorRef = binary.BigEndian.Uint64(ret[60:68])
		if tc.ErrorCode != 6 || tc.ErrorRef != handle {
			panic(fmt.Sprintf("%s: wrong typed error args code=%d ref=%d returndata=%x", tc.Name, tc.ErrorCode, tc.ErrorRef, ret))
		}
		return tc
	}
	if err != nil || len(ret) != 32 {
		panic(fmt.Sprintf("%s: expected packed uint256 result, err=%v returndata=%x", tc.Name, err, ret))
	}
	tc.Actual = binary.BigEndian.Uint64(ret[24:32])
	tc.Packed = ret[0]&0x80 != 0
	tc.Sparse = ret[0]&0x40 != 0
	if tc.Actual != tc.Expected || tc.Packed != tc.ExpectedPacked || tc.Sparse != tc.ExpectedSparse {
		panic(fmt.Sprintf("%s: count/selection=(%d,%t,%t) want=(%d,%t,%t)",
			tc.Name, tc.Actual, tc.Packed, tc.Sparse,
			tc.Expected, tc.ExpectedPacked, tc.ExpectedSparse))
	}
	return tc
}

func main() {
	if len(os.Args) != 3 {
		panic("usage: probe_driver RUNTIME_HEX OUTPUT_JSON")
	}
	hexText, err := os.ReadFile(os.Args[1])
	if err != nil {
		panic(err)
	}
	code, err := hex.DecodeString(strings.TrimSpace(string(hexText)))
	if err != nil {
		panic(err)
	}
	selector := crypto.Keccak256([]byte("groupedScanProbe(uint64[])"))[:4]
	out := report{Result: "PASS", GeneratedOnly: true, OrdinaryGas: ordinaryGas,
		Handle: handle, RuntimeBytes: len(code)}
	check := func(name string, values []uint64, want uint64, packed, sparse bool) {
		out.Cases = append(out.Cases, run(code, selector,
			result{Name: name, Expected: want, ExpectedPacked: packed, ExpectedSparse: sparse}, values, false))
		out.SuccessfulCases++
	}
	refuse := func(name string, values []uint64) {
		out.Cases = append(out.Cases, run(code, selector, result{Name: name}, values, true))
		out.RefusalCases++
	}

	for _, n := range []int{0, 1, 7, 8, 9} {
		values := make([]uint64, n)
		for i := range values {
			if i%2 == 0 {
				values[i] = 1
			}
		}
		var count uint64
		for _, value := range values {
			if value != 0 {
				count++
			}
		}
		check(fmt.Sprintf("boundary-%d", n), values, count, false, false)
	}
	for _, n := range []int{1024, 1025, 1031} {
		check(fmt.Sprintf("zero-%d", n), make([]uint64, n), 0, false, true)
		mixed := make([]uint64, n)
		var mixedCount uint64
		for i := range mixed {
			if i%3 == 0 {
				mixed[i] = 0x80000000
				mixedCount++
			}
		}
		check(fmt.Sprintf("mixed-%d", n), mixed, mixedCount, true, true)
		full := make([]uint64, n)
		for i := range full {
			full[i] = 0xffffffff
		}
		check(fmt.Sprintf("full-%d", n), full, uint64(n), true, false)
	}
	for lane := 0; lane < 8; lane++ {
		values := make([]uint64, 16)
		values[lane] = uint64(1) << 32
		refuse(fmt.Sprintf("high-bit-group-lane-%d", lane), values)
	}
	for _, n := range []int{1025, 1031} {
		grouped := n &^ 7
		for i := grouped; i < n; i++ {
			values := make([]uint64, n)
			values[i] = uint64(1) << 32
			refuse(fmt.Sprintf("high-bit-tail-%d-index-%d", n, i), values)
		}
	}
	encoded, err := json.MarshalIndent(out, "", "  ")
	if err != nil {
		panic(err)
	}
	if err := os.WriteFile(os.Args[2], append(encoded, '\n'), 0o644); err != nil {
		panic(err)
	}
	fmt.Printf("%s cases=%d typedRefusals=%d runtimeBytes=%d gasLimit=%d\n",
		out.Result, out.SuccessfulCases, out.RefusalCases, out.RuntimeBytes, ordinaryGas)
}
