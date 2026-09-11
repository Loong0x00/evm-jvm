package runtimeassets

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"reflect"
	"sort"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/crypto"
)

type di0TestArtifact struct {
	ContractName     string          `json:"contractName"`
	ABI              json.RawMessage `json:"abi"`
	Bytecode         string          `json:"bytecode"`
	DeployedBytecode string          `json:"deployedBytecode"`
	Immutable        map[string]any  `json:"immutableReferences"`
	Compiler         struct {
		Version    string `json:"version"`
		ViaIR      bool   `json:"viaIR"`
		EVMVersion string `json:"evmVersion"`
		Optimizer  struct {
			Enabled bool `json:"enabled"`
			Runs    int  `json:"runs"`
		} `json:"optimizer"`
		Metadata struct {
			AppendCBOR   bool   `json:"appendCBOR"`
			BytecodeHash string `json:"bytecodeHash"`
		} `json:"metadata"`
	} `json:"compiler"`
	SourceHashes map[string]string `json:"sourceHashes"`
	CodeHashes   struct {
		BytecodeSHA256 string `json:"bytecodeSHA256"`
		RuntimeSHA256  string `json:"deployedBytecodeSHA256"`
		RuntimeKeccak  string `json:"deployedBytecodeKeccak256"`
	} `json:"codeHashes"`
	DependencyPins map[string]string `json:"dependencyPins"`
	Limits         map[string]uint64 `json:"limits"`
	StorageLayout  json.RawMessage   `json:"storageLayout"`
}

func TestDI0EmbeddedArtifactPinsCapsABIAndDefensiveCopy(t *testing.T) {
	first, second := Artifact(), Artifact()
	if len(first) == 0 || len(second) == 0 {
		t.Fatal("empty embedded artifact")
	}
	first[0] ^= 0xff
	if bytes.Equal(first, second) || !bytes.Equal(second, Artifact()) {
		t.Fatal("Artifact is not defensive")
	}

	var top map[string]json.RawMessage
	if err := json.Unmarshal(second, &top); err != nil {
		t.Fatal(err)
	}
	gotKeys := make([]string, 0, len(top))
	for key := range top {
		gotKeys = append(gotKeys, key)
	}
	sort.Strings(gotKeys)
	wantKeys := []string{"abi", "bytecode", "codeHashes", "compiler", "contractName", "dependencyPins", "deployedBytecode", "immutableReferences", "limits", "sourceHashes", "storageLayout"}
	if !reflect.DeepEqual(gotKeys, wantKeys) {
		t.Fatalf("artifact keys=%v want %v", gotKeys, wantKeys)
	}

	var doc di0TestArtifact
	if err := json.Unmarshal(second, &doc); err != nil {
		t.Fatal(err)
	}
	if doc.ContractName != "DI0Resource" || len(doc.Immutable) != 0 || len(doc.StorageLayout) == 0 {
		t.Fatal("identity/immutable/layout pin differs")
	}
	contractABI, err := abi.JSON(bytes.NewReader(doc.ABI))
	if err != nil {
		t.Fatal(err)
	}
	if len(contractABI.Methods) != 33 || len(contractABI.Errors) != 1 || len(contractABI.Events) != 0 || contractABI.HasFallback() || contractABI.HasReceive() {
		t.Fatalf("ABI surface methods=%d errors=%d events=%d", len(contractABI.Methods), len(contractABI.Errors), len(contractABI.Events))
	}
	if _, ok := contractABI.Errors["DI0Error"]; !ok {
		t.Fatal("missing DI0Error")
	}

	decode := func(label, value string) []byte {
		out, err := hex.DecodeString(value)
		if err != nil || len(out) == 0 {
			t.Fatalf("%s hex: %v", label, err)
		}
		return out
	}
	initCode, runtimeCode := decode("init", doc.Bytecode), decode("runtime", doc.DeployedBytecode)
	if len(runtimeCode) > 24576 || len(initCode)+384 > 49152 {
		t.Fatalf("caps init+maxargs=%d runtime=%d", len(initCode)+384, len(runtimeCode))
	}
	initSHA, runtimeSHA := sha256.Sum256(initCode), sha256.Sum256(runtimeCode)
	if hex.EncodeToString(initSHA[:]) != doc.CodeHashes.BytecodeSHA256 || hex.EncodeToString(runtimeSHA[:]) != doc.CodeHashes.RuntimeSHA256 || strings.TrimPrefix(crypto.Keccak256Hash(runtimeCode).Hex(), "0x") != doc.CodeHashes.RuntimeKeccak {
		t.Fatal("code hash pins differ")
	}
	if doc.Compiler.Version != "0.8.30+commit.73712a01.Emscripten.clang" || !doc.Compiler.ViaIR || doc.Compiler.EVMVersion != "cancun" || !doc.Compiler.Optimizer.Enabled || doc.Compiler.Optimizer.Runs != 200 || doc.Compiler.Metadata.AppendCBOR || doc.Compiler.Metadata.BytecodeHash != "none" {
		t.Fatalf("compiler pin differs: %+v", doc.Compiler)
	}
	if doc.DependencyPins["AS0RuntimeCodeKeccak256"] != "c8cec283e80fd82b15254bd50a9f2aea3a91305ba71f756f834439280600f896" || doc.DependencyPins["ZI0RuntimeCodeKeccak256"] != "0c22eca78e00865ce03e8e298708bfe51ce9856cff138d1046905fc285ad5a77" {
		t.Fatal("dependency pins differ")
	}
	wantLimits := map[string]uint64{"archiveBytes": 33554432, "as0PageBytes": 8192, "as0ReadBytes": 4096, "rawNameBytes": 256, "outputBytes": 262144, "historyBytes": 32768, "copyBytes": 32, "outputPageBytes": 8192, "outputPages": 32, "readBytes": 4096, "stepUnits": 128, "publishUnits": 1, "stepReserveGas": 25000000, "runtimeBytes": 24576, "completeInitBytes": 49152}
	if !reflect.DeepEqual(doc.Limits, wantLimits) {
		t.Fatalf("limits=%v want %v", doc.Limits, wantLimits)
	}

	source, err := os.ReadFile("DI0Resource.sol")
	if err != nil {
		t.Fatal(err)
	}
	sourceSHA := sha256.Sum256(source)
	if len(doc.SourceHashes) != 1 || doc.SourceHashes["DI0Resource.sol"] != hex.EncodeToString(sourceSHA[:]) {
		t.Fatal("source hash pin differs")
	}
	initHex, err := os.ReadFile("DI0Resource.init.hex")
	if err != nil {
		t.Fatal(err)
	}
	runtimeHex, err := os.ReadFile("DI0Resource.runtime.hex")
	if err != nil {
		t.Fatal(err)
	}
	abiJSON, err := os.ReadFile("DI0Resource.abi.json")
	if err != nil {
		t.Fatal(err)
	}
	var splitABI, combinedABI any
	if err := json.Unmarshal(abiJSON, &splitABI); err != nil {
		t.Fatal(err)
	}
	if err := json.Unmarshal(doc.ABI, &combinedABI); err != nil {
		t.Fatal(err)
	}
	if string(initHex) != doc.Bytecode+"\n" || string(runtimeHex) != doc.DeployedBytecode+"\n" || !reflect.DeepEqual(splitABI, combinedABI) {
		t.Fatal("split generated artifacts differ from combined artifact")
	}
}
