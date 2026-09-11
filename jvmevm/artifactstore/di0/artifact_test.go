package di0

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/accounts/abi"
	runtimeassets "github.com/ethereum/go-ethereum/jvmevm/artifactstore/di0/runtime"
)

func TestDI0HarnessRejectsAlteredArtifactAndExtraABISurface(t *testing.T) {
	raw := runtimeassets.Artifact()
	mutations := []func([]byte) []byte{
		func(b []byte) []byte { return append(b, ' ') },
		func(b []byte) []byte { b[len(b)/2] ^= 1; return b },
		func(b []byte) []byte {
			return bytes.Replace(b, []byte(compilerVersion), []byte(strings.Repeat("x", len(compilerVersion))), 1)
		},
		func(b []byte) []byte {
			return bytes.Replace(b, []byte(runtimeKeccak256), []byte(strings.Repeat("0", 64)), 1)
		},
	}
	for _, mutate := range mutations {
		if _, _, _, _, err := validateArtifact(mutate(append([]byte(nil), raw...))); err == nil {
			t.Fatal("altered combined artifact accepted")
		}
	}
	var doc struct {
		ABI []map[string]interface{} `json:"abi"`
	}
	if err := json.Unmarshal(raw, &doc); err != nil {
		t.Fatal(err)
	}
	extras := []map[string]interface{}{{"type": "event", "name": "Extra", "anonymous": false, "inputs": []interface{}{}}, {"type": "fallback", "stateMutability": "nonpayable"}, {"type": "receive", "stateMutability": "payable"}, {"type": "function", "name": "debug", "stateMutability": "view", "inputs": []interface{}{}, "outputs": []interface{}{}}}
	for _, extra := range extras {
		entries := append(append([]map[string]interface{}(nil), doc.ABI...), extra)
		encoded, _ := json.Marshal(entries)
		changed, err := abi.JSON(bytes.NewReader(encoded))
		if err != nil {
			t.Fatal(err)
		}
		if err = validateABI(changed); err == nil {
			t.Fatalf("extra ABI %v accepted", extra["type"])
		}
	}
}
