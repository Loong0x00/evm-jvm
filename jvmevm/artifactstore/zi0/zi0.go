// Copyright 2026 The go-ethereum Authors
// SPDX-License-Identifier: LGPL-3.0-or-later

// Package zi0 provides the opaque Go transport for the frozen MC-ZI0 EVM ZIP
// directory index. The EVM contract is the only ZIP authority: this package
// transports bytes, ABI calls, and committed state, but never parses an archive.
package zi0

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"strings"
	"sync"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/as0"
	zi0runtime "github.com/ethereum/go-ethereum/jvmevm/artifactstore/zi0/runtime"
)

const (
	MaxEntries  = uint32(32768)
	MaxCD       = uint32(4 * 1024 * 1024)
	MaxName     = uint16(256)
	MaxExtra    = uint16(1024)
	MaxComment  = uint16(1024)
	MaxTail     = uint32(65557)
	MaxGas      = uint64(1_000_000_000)
	OrdinaryGas = uint64(100_000_000)
	BoundaryGas = uint64(1_000_000_000)

	storeMarker     = "JVMEVM-MC-ZI0-DISK-STORE-1\n"
	storeFormat     = uint32(1)
	markerName      = "STORE-FORMAT"
	manifestName    = "durable-head.json"
	stateDirectory  = "state"
	contextID       = "all-dev-chain:block=1,time=1,coinbase=0000000000000000000000000000000000000000,value=0"
	manifestMaxSize = int64(16384)
)

var as0CodeHash = common.HexToHash("0xc8cec283e80fd82b15254bd50a9f2aea3a91305ba71f756f834439280600f896")

// Operation describes one EVM mutation. CreatedAddress is nonzero only after
// a successfully published ZI0 CREATE. Publication failures deliberately do
// not expose a success root or address.
type Operation struct {
	GasUsed        uint64
	StateRoot      commonHash
	Logs           []*typesLog
	RevertData     []byte
	CreatedAddress commonAddress
}

// The aliases keep the public declaration above readable while retaining the
// go-ethereum types in one place in the transport implementation.
type commonHash = common.Hash
type commonAddress = common.Address
type typesLog = types.Log

// Entry is an opaque EVM entry result. PackedRecord must not be interpreted by
// Go as a class/resource catalogue.
type Entry struct {
	Name         []byte
	PackedRecord common.Hash
	GasUsed      uint64
}
type LookupResult struct {
	Found        bool
	Index        uint32
	PackedRecord common.Hash
	GasUsed      uint64
}

// Lookup is retained as a descriptive alias for callers that name view results.
type Lookup = LookupResult

// EntryResult is an alias for the opaque Entry view result.
type EntryResult = Entry

// IndexHead contains the thirteen scalar diagnostic getters of ZI0.
type IndexHead struct {
	Address         common.Address
	RuntimeCodeHash common.Hash
	Owner           common.Address
	Store           common.Address
	Content         common.Hash
	Length          uint32
	Phase           uint8
	EOCD            uint32
	CDOffset        uint32
	CDSize          uint32
	Count           uint32
	NextEntry       uint32
	CDCursor        uint32
	Rolling         common.Hash
	FinalRoot       common.Hash
	GasUsed         uint64
}

// Head combines copied-state AS0 and ZI0 getter results.
type Head struct {
	StateRoot common.Hash
	AS0       as0.Head
	Index     IndexHead
	GasUsed   uint64
}

type artifactJSON struct {
	ContractName        string                     `json:"contractName"`
	ABI                 json.RawMessage            `json:"abi"`
	Bytecode            string                     `json:"bytecode"`
	DeployedBytecode    string                     `json:"deployedBytecode"`
	ImmutableReferences map[string]json.RawMessage `json:"immutableReferences"`
	Compiler            artifactCompiler           `json:"compiler"`
	SourceHashes        map[string]string          `json:"sourceHashes"`
	CodeHashes          artifactCodeHashes         `json:"codeHashes"`
	DependencyPins      artifactDependencyPins     `json:"dependencyPins"`
	Limits              artifactLimits             `json:"limits"`
	StorageLayout       json.RawMessage            `json:"storageLayout"`
}

type artifactCompiler struct {
	Version   string `json:"version"`
	Optimizer struct {
		Enabled bool   `json:"enabled"`
		Runs    uint32 `json:"runs"`
	} `json:"optimizer"`
	ViaIR      bool   `json:"viaIR"`
	EVMVersion string `json:"evmVersion"`
	Metadata   struct {
		AppendCBOR   bool   `json:"appendCBOR"`
		BytecodeHash string `json:"bytecodeHash"`
	} `json:"metadata"`
}
type artifactCodeHashes struct {
	BytecodeSHA256    string `json:"bytecodeSHA256"`
	DeployedSHA256    string `json:"deployedBytecodeSHA256"`
	DeployedKeccak256 string `json:"deployedBytecodeKeccak256"`
}
type artifactDependencyPins struct {
	AS0RuntimeCodeKeccak256 string `json:"AS0RuntimeCodeKeccak256"`
}
type artifactLimits struct {
	ArchiveBytes          uint32 `json:"archiveBytes"`
	AS0PageBytes          uint32 `json:"as0PageBytes"`
	AS0ReadBytes          uint32 `json:"as0ReadBytes"`
	Entries               uint32 `json:"entries"`
	CentralDirectoryBytes uint32 `json:"centralDirectoryBytes"`
	RawNameBytes          uint32 `json:"rawNameBytes"`
	ExtraBytes            uint32 `json:"extraBytes"`
	CommentBytes          uint32 `json:"commentBytes"`
	ScanUnits             uint32 `json:"scanUnits"`
	EOCDTailBytes         uint32 `json:"eocdTailBytes"`
	RuntimeBytes          uint32 `json:"runtimeBytes"`
	CompleteInitBytes     uint32 `json:"completeInitBytes"`
}

const (
	artifactSHA256   = "424246923fd5a022ec7dabda19f6847ad36896d5fd34ca8598e7c3f32719443e"
	sourceSHA256     = "78329d1610c0ba180c7e267989bf36190a9d9eb536020acce42234066a94a2ae"
	initSHA256       = "f3d6d4614cf916cc4be4cd1ef58212642d829d63b710cea9d140181bafd00870"
	runtimeSHA256    = "74ea23889368b3381843e39bb2caf53a66de8dbfdb3dc58dc4a066c97a33d7a3"
	runtimeKeccak256 = "0c22eca78e00865ce03e8e298708bfe51ce9856cff138d1046905fc285ad5a77"
	abiSchemaSHA256  = "d4cbb83eb725e27c6d16d32d333a6b576af47fde093a7d071bc01ff69980b9b6"
	layoutSHA256     = "b572f7b901cbf78e87b4ba05369361bf10c76c1113640d3b026f6662c114b58b"
	compilerVersion  = "0.8.30+commit.73712a01.Emscripten.clang"
)

var (
	loadOnce                   sync.Once
	loadErr                    error
	loadABI                    abi.ABI
	loadRaw, loadInit, loadRun []byte
)

func loadArtifact() {
	loadOnce.Do(func() {
		loadABI, loadRaw, loadInit, loadRun, loadErr = validateArtifact(zi0runtime.Artifact())
	})
}

// validateArtifact verifies the generated combined-artifact schema against
// independent production pins. Values carried inside the JSON are never treated
// as self-authenticating hashes or compiler settings.
func validateArtifact(raw []byte) (abi.ABI, []byte, []byte, []byte, error) {
	var doc artifactJSON
	dec := json.NewDecoder(bytes.NewReader(raw))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&doc); err != nil {
		return abi.ABI{}, nil, nil, nil, fmt.Errorf("zi0: decode embedded artifact: %w", err)
	}
	var trailing interface{}
	if err := dec.Decode(&trailing); err == nil {
		return abi.ABI{}, nil, nil, nil, fmt.Errorf("zi0: trailing embedded artifact data")
	} else if !errors.Is(err, io.EOF) {
		return abi.ABI{}, nil, nil, nil, fmt.Errorf("zi0: decode trailing embedded artifact data: %w", err)
	}
	if digest(raw) != artifactSHA256 {
		return abi.ABI{}, nil, nil, nil, fmt.Errorf("zi0: embedded combined artifact hash differs from production pin")
	}
	if doc.ContractName != "ZI0ZipIndex" {
		return abi.ABI{}, nil, nil, nil, fmt.Errorf("zi0: unexpected embedded contract %q", doc.ContractName)
	}
	if len(bytes.TrimSpace(doc.ABI)) == 0 || bytes.Equal(bytes.TrimSpace(doc.ABI), []byte("null")) {
		return abi.ABI{}, nil, nil, nil, fmt.Errorf("zi0: embedded ABI is empty")
	}
	canonicalABI, err := canonicalJSON(doc.ABI)
	if err != nil || digest(canonicalABI) != abiSchemaSHA256 {
		return abi.ABI{}, nil, nil, nil, fmt.Errorf("zi0: embedded ABI schema hash differs from production pin")
	}
	a, err := abi.JSON(bytes.NewReader(doc.ABI))
	if err != nil {
		return abi.ABI{}, nil, nil, nil, fmt.Errorf("zi0: parse embedded ABI: %w", err)
	}
	if err = validateABI(a); err != nil {
		return abi.ABI{}, nil, nil, nil, err
	}
	init, err := decodeCode("init", doc.Bytecode)
	if err != nil {
		return abi.ABI{}, nil, nil, nil, err
	}
	run, err := decodeCode("runtime", doc.DeployedBytecode)
	if err != nil {
		return abi.ABI{}, nil, nil, nil, err
	}
	if len(init) != 9873 || len(init)+64 != 9937 || len(init)+64 > 49152 || len(run) != 9177 || len(run) > 24576 {
		return abi.ABI{}, nil, nil, nil, fmt.Errorf("zi0: embedded code differs from frozen sizes (init=%d complete=%d runtime=%d)", len(init), len(init)+64, len(run))
	}
	if digest(init) != initSHA256 || digest(run) != runtimeSHA256 {
		return abi.ABI{}, nil, nil, nil, fmt.Errorf("zi0: embedded bytecode hash differs from production pin")
	}
	// The Keccak identity is the EVM code binding; SHA-256 pins transport bytes.
	if strings.TrimPrefix(crypto.Keccak256Hash(run).Hex(), "0x") != runtimeKeccak256 {
		return abi.ABI{}, nil, nil, nil, fmt.Errorf("zi0: embedded runtime Keccak differs from production pin")
	}
	if doc.CodeHashes.BytecodeSHA256 != initSHA256 || doc.CodeHashes.DeployedSHA256 != runtimeSHA256 || doc.CodeHashes.DeployedKeccak256 != runtimeKeccak256 {
		return abi.ABI{}, nil, nil, nil, fmt.Errorf("zi0: generated code-hash fields differ from production pins")
	}
	if len(doc.ImmutableReferences) != 0 {
		return abi.ABI{}, nil, nil, nil, fmt.Errorf("zi0: deployed runtime contains immutable substitutions")
	}
	if doc.Compiler.Version != compilerVersion || !doc.Compiler.Optimizer.Enabled || doc.Compiler.Optimizer.Runs != 200 || !doc.Compiler.ViaIR || doc.Compiler.EVMVersion != "cancun" || doc.Compiler.Metadata.AppendCBOR || doc.Compiler.Metadata.BytecodeHash != "none" {
		return abi.ABI{}, nil, nil, nil, fmt.Errorf("zi0: compiler/settings differ from frozen build")
	}
	if len(doc.SourceHashes) != 1 || doc.SourceHashes["ZI0ZipIndex.sol"] != sourceSHA256 {
		return abi.ABI{}, nil, nil, nil, fmt.Errorf("zi0: source hash differs from production pin")
	}
	if doc.DependencyPins.AS0RuntimeCodeKeccak256 != strings.TrimPrefix(as0CodeHash.Hex(), "0x") {
		return abi.ABI{}, nil, nil, nil, fmt.Errorf("zi0: AS0 dependency pin differs from accepted runtime")
	}
	wantLimits := artifactLimits{
		ArchiveBytes: 33554432, AS0PageBytes: 8192, AS0ReadBytes: 4096,
		Entries: 32768, CentralDirectoryBytes: 4194304, RawNameBytes: 256,
		ExtraBytes: 1024, CommentBytes: 1024, ScanUnits: 64,
		EOCDTailBytes: 65557, RuntimeBytes: 24576, CompleteInitBytes: 49152,
	}
	if doc.Limits != wantLimits {
		return abi.ABI{}, nil, nil, nil, fmt.Errorf("zi0: artifact limits differ from frozen profile")
	}
	layout, err := canonicalJSON(doc.StorageLayout)
	if err != nil || digest(layout) != layoutSHA256 {
		return abi.ABI{}, nil, nil, nil, fmt.Errorf("zi0: storage layout differs from production schema")
	}
	return a, append([]byte(nil), doc.ABI...), init, run, nil
}

func canonicalJSON(raw []byte) ([]byte, error) {
	var value interface{}
	dec := json.NewDecoder(bytes.NewReader(raw))
	dec.UseNumber()
	if err := dec.Decode(&value); err != nil {
		return nil, err
	}
	return json.Marshal(value)
}
func digest(raw []byte) string {
	h := sha256.Sum256(raw)
	return hex.EncodeToString(h[:])
}
func decodeCode(label, s string) ([]byte, error) {
	s = strings.TrimPrefix(strings.TrimSpace(s), "0x")
	if s == "" || len(s)%2 != 0 {
		return nil, fmt.Errorf("zi0: embedded %s code is empty or odd-length", label)
	}
	b, e := hex.DecodeString(s)
	if e != nil {
		return nil, fmt.Errorf("zi0: decode embedded %s code: %w", label, e)
	}
	return b, nil
}

func Runtime() ([]byte, error) {
	loadArtifact()
	if loadErr != nil {
		return nil, loadErr
	}
	return append([]byte(nil), loadRun...), nil
}
func InitCode() ([]byte, error) {
	loadArtifact()
	if loadErr != nil {
		return nil, loadErr
	}
	return append([]byte(nil), loadInit...), nil
}
func ABI() (abi.ABI, error) {
	loadArtifact()
	if loadErr != nil {
		return abi.ABI{}, loadErr
	}
	a, e := abi.JSON(bytes.NewReader(loadRaw))
	if e != nil {
		return abi.ABI{}, fmt.Errorf("zi0: copy embedded ABI: %w", e)
	}
	return a, nil
}

// RuntimeHash is a host transport pin for reporting. EVM identity uses the
// deployed bytecode hash; this helper does not grant authority to host code.
func RuntimeHash() (string, error) {
	code, err := Runtime()
	if err != nil {
		return "", err
	}
	h := sha256.Sum256(code)
	return hex.EncodeToString(h[:]), nil
}

func validateABI(a abi.ABI) error {
	if a.HasFallback() || a.HasReceive() || len(a.Events) != 0 {
		return fmt.Errorf("zi0: frozen ABI has no events, fallback, or receive")
	}
	type shape struct {
		sig, mut           string
		in, inn, out, outn []string
	}
	want := map[string]shape{
		"discover":  {"discover()", "nonpayable", nil, nil, nil, nil},
		"scan":      {"scan(uint32,uint32,bytes32,uint16)", "nonpayable", []string{"uint32", "uint32", "bytes32", "uint16"}, []string{"expectedEntry", "expectedCursor", "expectedRolling", "units"}, nil, nil},
		"finish":    {"finish(uint32,uint32,bytes32)", "nonpayable", []string{"uint32", "uint32", "bytes32"}, []string{"expectedCount", "expectedCursor", "expectedRolling"}, nil, nil},
		"entry":     {"entry(uint32)", "view", []string{"uint32"}, []string{"index"}, []string{"bytes", "bytes32"}, []string{"rawName", "packedRecord"}},
		"lookup":    {"lookup(bytes)", "view", []string{"bytes"}, []string{"rawName"}, []string{"bool", "uint32", "bytes32"}, []string{"found", "index", "packedRecord"}},
		"owner":     {"owner()", "view", nil, nil, []string{"address"}, []string{""}},
		"store":     {"store()", "view", nil, nil, []string{"address"}, []string{""}},
		"content":   {"content()", "view", nil, nil, []string{"bytes32"}, []string{""}},
		"length":    {"length()", "view", nil, nil, []string{"uint32"}, []string{""}},
		"phase":     {"phase()", "view", nil, nil, []string{"uint8"}, []string{""}},
		"eocd":      {"eocd()", "view", nil, nil, []string{"uint32"}, []string{""}},
		"cdOffset":  {"cdOffset()", "view", nil, nil, []string{"uint32"}, []string{""}},
		"cdSize":    {"cdSize()", "view", nil, nil, []string{"uint32"}, []string{""}},
		"count":     {"count()", "view", nil, nil, []string{"uint32"}, []string{""}},
		"nextEntry": {"nextEntry()", "view", nil, nil, []string{"uint32"}, []string{""}},
		"cdCursor":  {"cdCursor()", "view", nil, nil, []string{"uint32"}, []string{""}},
		"rolling":   {"rolling()", "view", nil, nil, []string{"bytes32"}, []string{""}},
		"finalRoot": {"finalRoot()", "view", nil, nil, []string{"bytes32"}, []string{""}},
	}
	if len(a.Methods) != len(want) {
		return fmt.Errorf("zi0: embedded ABI has %d methods, want exactly %d", len(a.Methods), len(want))
	}
	for name, w := range want {
		m, ok := a.Methods[name]
		if !ok || m.RawName != name || m.Sig != w.sig || m.StateMutability != w.mut || len(m.Inputs) != len(w.in) || len(m.Outputs) != len(w.out) {
			return fmt.Errorf("zi0: embedded ABI method %s differs from frozen shape", name)
		}
		for i, x := range m.Inputs {
			if x.Type.String() != w.in[i] || x.Name != w.inn[i] {
				return fmt.Errorf("zi0: embedded ABI %s input %d differs", name, i)
			}
		}
		for i, x := range m.Outputs {
			if x.Type.String() != w.out[i] || x.Name != w.outn[i] {
				return fmt.Errorf("zi0: embedded ABI %s output %d differs", name, i)
			}
		}
	}
	if len(a.Constructor.Inputs) != 2 || a.Constructor.StateMutability != "nonpayable" || a.Constructor.Inputs[0].Name != "sealedAS0" || a.Constructor.Inputs[0].Type.String() != "address" || a.Constructor.Inputs[1].Name != "assertedContent" || a.Constructor.Inputs[1].Type.String() != "bytes32" {
		return fmt.Errorf("zi0: embedded ABI constructor differs from frozen shape")
	}
	e, ok := a.Errors["ZI0Error"]
	if !ok || len(a.Errors) != 1 || e.Sig != "ZI0Error(uint256)" || len(e.Inputs) != 1 || e.Inputs[0].Name != "code" {
		return fmt.Errorf("zi0: embedded ABI must contain exactly ZI0Error(uint256 code)")
	}
	return nil
}
