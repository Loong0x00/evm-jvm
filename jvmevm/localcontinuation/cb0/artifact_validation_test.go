package cb0

import (
	"bytes"
	"encoding/json"
	"testing"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	runtimeassets "github.com/ethereum/go-ethereum/jvmevm/localcontinuation/cb0/runtime"
)

func TestCB0ArtifactValidationPinsComputedRuntimeKeccak(t *testing.T) {
	loaded, err := cb0ValidateArtifact(runtimeassets.Artifact())
	if err != nil {
		t.Fatal(err)
	}
	want := common.HexToHash("0x" + cb0RuntimeKeccak)
	if loaded.runtimeHash != want {
		t.Fatalf("runtime hash=%s want %s", loaded.runtimeHash, want)
	}
	if err := cb0ValidateABI(loaded.abi); err != nil {
		t.Fatalf("embedded ABI unexpectedly invalid: %v", err)
	}
}

func TestCB0ArtifactValidationRejectsOutputShapeWithoutSelectorChange(t *testing.T) {
	var artifact struct {
		ABI []map[string]any `json:"abi"`
	}
	if err := json.Unmarshal(runtimeassets.Artifact(), &artifact); err != nil {
		t.Fatal(err)
	}
	for _, tc := range []struct {
		name   string
		mutate func([]map[string]any) bool
	}{
		{
			name: "binding output name",
			mutate: func(entries []map[string]any) bool {
				for _, entry := range entries {
					if entry["type"] == "function" && entry["name"] == "classBinding" {
						entry["outputs"].([]any)[0].(map[string]any)["name"] = "changedDecoder"
						return true
					}
				}
				return false
			},
		},
		{
			name: "start output type",
			mutate: func(entries []map[string]any) bool {
				for _, entry := range entries {
					if entry["type"] == "function" && entry["name"] == "start" {
						entry["outputs"].([]any)[0].(map[string]any)["type"] = "bytes32"
						return true
					}
				}
				return false
			},
		},
	} {
		t.Run(tc.name, func(t *testing.T) {
			var clone []map[string]any
			b, err := json.Marshal(artifact.ABI)
			if err != nil {
				t.Fatal(err)
			}
			if err = json.Unmarshal(b, &clone); err != nil {
				t.Fatal(err)
			}
			if !tc.mutate(clone) {
				t.Fatal("test ABI entry not found")
			}
			mutated, err := json.Marshal(clone)
			if err != nil {
				t.Fatal(err)
			}
			parsed, err := abi.JSON(bytes.NewReader(mutated))
			if err != nil {
				t.Fatal(err)
			}
			if err := cb0ValidateABI(parsed); err == nil {
				t.Fatal("changed output ABI was accepted")
			}
		})
	}
}
