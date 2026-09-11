// Copyright 2026 The go-ethereum Authors
// SPDX-License-Identifier: LGPL-3.0-or-later

// Package di0 provides the opaque Go transport for the frozen MC-DI0 EVM
// resource decoder. Go transports archive bytes, ABI calls, and committed EVM
// state; the EVM is the only ZIP metadata, DEFLATE, CRC, and page authority.
package di0

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
	runtimeassets "github.com/ethereum/go-ethereum/jvmevm/artifactstore/di0/runtime"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/zi0"
)

const (
	MaxEntries     = zi0.MaxEntries
	MaxCD          = zi0.MaxCD
	MaxName        = zi0.MaxName
	MaxOutput      = uint32(262144)
	MaxHistory     = uint32(32768)
	MaxCopy        = uint32(32)
	OutputPageSize = uint32(8192)
	MaxOutputPages = uint8(32)
	MaxRead        = uint32(4096)
	MaxStepUnits   = uint16(128)
	PublishUnits   = uint8(1)
	StepReserveGas = uint64(25_000_000)
	MaxGas         = uint64(1_000_000_000)
	OrdinaryGas    = uint64(100_000_000)
	BoundaryGas    = uint64(1_000_000_000)

	storeMarker     = "JVMEVM-MC-DI0-DISK-STORE-1\n"
	storeFormat     = uint32(1)
	markerName      = "STORE-FORMAT"
	manifestName    = "durable-head.json"
	stateDirectory  = "state"
	contextID       = "all-dev-chain:block=1,time=1,coinbase=0000000000000000000000000000000000000000,value=0"
	manifestMaxSize = int64(32768)
)

var (
	as0CodeHash = common.HexToHash("0xc8cec283e80fd82b15254bd50a9f2aea3a91305ba71f756f834439280600f896")
	zi0CodeHash = common.HexToHash("0x0c22eca78e00865ce03e8e298708bfe51ce9856cff138d1046905fc285ad5a77")
)

// Operation describes one EVM mutation. CreatedAddress is populated only by a
// successfully published CreateIndex or CreateDecoder. EVM failures expose only
// GasUsed and RevertData; publication failures expose only GasUsed.
type Operation struct {
	GasUsed        uint64
	StateRoot      common.Hash
	Logs           []*types.Log
	RevertData     []byte
	CreatedAddress common.Address
}

// Read is an opaque byte result returned by an EVM read call.
type Read struct {
	Bytes   []byte
	GasUsed uint64
}

// Page is immutable output-page metadata returned by the decoder.
type Page struct {
	Address    common.Address
	CodeHash   common.Hash
	Commitment common.Hash
	Length     uint32
	GasUsed    uint64
}

// DI0Head is the fixed controller identity plus all 29 typed diagnostic getter
// values. It contains no host-derived DEFLATE state.
type Entry = zi0.Entry
type IndexHead = zi0.IndexHead
type EntryResult = zi0.EntryResult
type LookupResult = zi0.LookupResult
type Lookup = zi0.Lookup

// Head combines copied-state AS0, ZI0, and DI0 getter results. StateRoot is the
// transport trie root; Decoder.FinalRoot is the decoded resource commitment.
type Head struct {
	StateRoot common.Hash
	AS0       as0.Head
	Index     zi0.IndexHead
	Decoder   DI0Head
	GasUsed   uint64
}

type DI0Head struct {
	Address            common.Address
	RuntimeCodeHash    common.Hash
	Owner              common.Address
	Index              common.Address
	Store              common.Address
	IndexRoot          common.Hash
	Content            common.Hash
	PackedRecord       common.Hash
	NameHash           common.Hash
	Binding            common.Hash
	OutputRolling      common.Hash
	PublicationRolling common.Hash
	FinalRoot          common.Hash
	EntryIndex         uint32
	DataStart          uint32
	CompressedSize     uint32
	PlainSize          uint32
	ExpectedCRC        uint32
	OutputCount        uint32
	InputByte          uint32
	Work               uint32
	CRC                uint32
	PendingLength      uint16
	PendingDistance    uint16
	InputBit           uint8
	Method             uint8
	Phase              uint8
	BlockMode          uint8
	BlockFinal         bool
	FixedBlock         bool
	PublishedPages     uint8
	GasUsed            uint64
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
	ZI0RuntimeCodeKeccak256 string `json:"ZI0RuntimeCodeKeccak256"`
}
type artifactLimits struct {
	ArchiveBytes      uint32 `json:"archiveBytes"`
	AS0PageBytes      uint32 `json:"as0PageBytes"`
	AS0ReadBytes      uint32 `json:"as0ReadBytes"`
	RawNameBytes      uint32 `json:"rawNameBytes"`
	OutputBytes       uint32 `json:"outputBytes"`
	HistoryBytes      uint32 `json:"historyBytes"`
	CopyBytes         uint32 `json:"copyBytes"`
	OutputPageBytes   uint32 `json:"outputPageBytes"`
	OutputPages       uint32 `json:"outputPages"`
	ReadBytes         uint32 `json:"readBytes"`
	StepUnits         uint32 `json:"stepUnits"`
	PublishUnits      uint32 `json:"publishUnits"`
	StepReserveGas    uint32 `json:"stepReserveGas"`
	RuntimeBytes      uint32 `json:"runtimeBytes"`
	CompleteInitBytes uint32 `json:"completeInitBytes"`
}

// These independent pins are filled from the sole runtime-writer's reproducible
// final artifact before this package can load it. Keeping them constants rather
// than reading asserted values from JSON is part of the transport boundary.
const (
	artifactSHA256   = "72773d5c53533969a6b0d0a1391513330affb11b4cdf300fa4c115bab23613ca"
	sourceSHA256     = "682d8243a6a0671f151316c8bce0a220ec1934205ca5bb4144a4d635463b4470"
	initSHA256       = "604d6a515fcb5efb539f998987ddba94c7f1e1d1fe3e712a5b95606bc1dab576"
	runtimeSHA256    = "8c309455d3b0817725cd775f909abc2477b39fed6e18235114737480b05e17b0"
	runtimeKeccak256 = "946686a0a4f09ec9a03e3eb63e9bbeac008212061d6f316586034cf800380c37"
	abiSchemaSHA256  = "d44a67c73dd94c463dcb25ce00a8b6814967f3a1f37ed0c60770ce818f63f7ee"
	layoutSHA256     = "5c07eef01462da0f9685e37dff3bd65c1e10769b82375963973ff41743ecaffc"
	compilerVersion  = "0.8.30+commit.73712a01.Emscripten.clang"
)

var (
	loadOnce                   sync.Once
	loadErr                    error
	loadABI                    abi.ABI
	loadRaw, loadInit, loadRun []byte
)

func loadArtifact() {
	loadOnce.Do(func() { loadABI, loadRaw, loadInit, loadRun, loadErr = validateArtifact(runtimeassets.Artifact()) })
}

func validateArtifact(raw []byte) (abi.ABI, []byte, []byte, []byte, error) {
	var doc artifactJSON
	dec := json.NewDecoder(bytes.NewReader(raw))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&doc); err != nil {
		return abi.ABI{}, nil, nil, nil, fmt.Errorf("di0: decode embedded artifact: %w", err)
	}
	var trailing interface{}
	if err := dec.Decode(&trailing); err == nil {
		return abi.ABI{}, nil, nil, nil, errors.New("di0: trailing embedded artifact data")
	} else if !errors.Is(err, io.EOF) {
		return abi.ABI{}, nil, nil, nil, fmt.Errorf("di0: decode trailing artifact: %w", err)
	}
	if digest(raw) != artifactSHA256 {
		return abi.ABI{}, nil, nil, nil, errors.New("di0: embedded combined artifact hash differs from production pin")
	}
	if doc.ContractName != "DI0Resource" {
		return abi.ABI{}, nil, nil, nil, fmt.Errorf("di0: unexpected embedded contract %q", doc.ContractName)
	}
	canonicalABI, err := canonicalJSON(doc.ABI)
	if err != nil || digest(canonicalABI) != abiSchemaSHA256 {
		return abi.ABI{}, nil, nil, nil, errors.New("di0: embedded ABI schema hash differs from production pin")
	}
	a, err := abi.JSON(bytes.NewReader(doc.ABI))
	if err != nil {
		return abi.ABI{}, nil, nil, nil, fmt.Errorf("di0: parse embedded ABI: %w", err)
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
	// A 256-byte name contributes 384 bytes of ABI constructor encoding.
	if len(init)+384 > 49152 || len(run) > 24576 {
		return abi.ABI{}, nil, nil, nil, fmt.Errorf("di0: embedded code exceeds frozen sizes (complete=%d runtime=%d)", len(init)+384, len(run))
	}
	if digest(init) != initSHA256 || digest(run) != runtimeSHA256 || strings.TrimPrefix(crypto.Keccak256Hash(run).Hex(), "0x") != runtimeKeccak256 {
		return abi.ABI{}, nil, nil, nil, errors.New("di0: embedded code differs from production pins")
	}
	if doc.CodeHashes.BytecodeSHA256 != initSHA256 || doc.CodeHashes.DeployedSHA256 != runtimeSHA256 || doc.CodeHashes.DeployedKeccak256 != runtimeKeccak256 {
		return abi.ABI{}, nil, nil, nil, errors.New("di0: generated code hash fields differ from production pins")
	}
	if len(doc.ImmutableReferences) != 0 {
		return abi.ABI{}, nil, nil, nil, errors.New("di0: deployed runtime contains immutable substitutions")
	}
	if doc.Compiler.Version != compilerVersion || !doc.Compiler.Optimizer.Enabled || doc.Compiler.Optimizer.Runs != 200 || !doc.Compiler.ViaIR || doc.Compiler.EVMVersion != "cancun" || doc.Compiler.Metadata.AppendCBOR || doc.Compiler.Metadata.BytecodeHash != "none" {
		return abi.ABI{}, nil, nil, nil, errors.New("di0: compiler/settings differ from frozen build")
	}
	if len(doc.SourceHashes) != 1 || doc.SourceHashes["DI0Resource.sol"] != sourceSHA256 {
		return abi.ABI{}, nil, nil, nil, errors.New("di0: source hash differs from production pin")
	}
	if doc.DependencyPins.AS0RuntimeCodeKeccak256 != strings.TrimPrefix(as0CodeHash.Hex(), "0x") || doc.DependencyPins.ZI0RuntimeCodeKeccak256 != strings.TrimPrefix(zi0CodeHash.Hex(), "0x") {
		return abi.ABI{}, nil, nil, nil, errors.New("di0: dependency pins differ from accepted runtimes")
	}
	want := artifactLimits{33554432, 8192, 4096, 256, 262144, 32768, 32, 8192, 32, 4096, 128, 1, 25000000, 24576, 49152}
	if doc.Limits != want {
		return abi.ABI{}, nil, nil, nil, errors.New("di0: artifact limits differ from frozen profile")
	}
	layout, err := canonicalJSON(doc.StorageLayout)
	if err != nil || digest(layout) != layoutSHA256 {
		return abi.ABI{}, nil, nil, nil, errors.New("di0: storage layout differs from production schema")
	}
	return a, append([]byte(nil), doc.ABI...), init, run, nil
}

func canonicalJSON(raw []byte) ([]byte, error) {
	var v interface{}
	d := json.NewDecoder(bytes.NewReader(raw))
	d.UseNumber()
	if err := d.Decode(&v); err != nil {
		return nil, err
	}
	return json.Marshal(v)
}
func digest(raw []byte) string { h := sha256.Sum256(raw); return hex.EncodeToString(h[:]) }
func decodeCode(label, s string) ([]byte, error) {
	s = strings.TrimSpace(s)
	if strings.HasPrefix(s, "0x") || s == "" || len(s)%2 != 0 {
		return nil, fmt.Errorf("di0: embedded %s code must be nonempty lowercase hex without 0x", label)
	}
	if s != strings.ToLower(s) {
		return nil, fmt.Errorf("di0: embedded %s code is not lowercase", label)
	}
	b, e := hex.DecodeString(s)
	if e != nil {
		return nil, fmt.Errorf("di0: decode embedded %s code: %w", label, e)
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
	return abi.JSON(bytes.NewReader(loadRaw))
}
func RuntimeHash() (string, error) {
	b, e := Runtime()
	if e != nil {
		return "", e
	}
	return digest(b), nil
}

func validateABI(a abi.ABI) error {
	if a.HasFallback() || a.HasReceive() || len(a.Events) != 0 {
		return errors.New("di0: frozen ABI has no events, fallback, or receive")
	}
	type shape struct {
		sig, mut           string
		in, inn, out, outn []string
	}
	want := map[string]shape{
		"step":    {"step(uint32,uint16)", "nonpayable", []string{"uint32", "uint16"}, []string{"expectedWork", "units"}, nil, nil},
		"publish": {"publish(uint8,bytes32,uint8)", "nonpayable", []string{"uint8", "bytes32", "uint8"}, []string{"expectedPage", "expectedRolling", "units"}, nil, nil},
		"read":    {"read(uint32,uint32)", "view", []string{"uint32", "uint32"}, []string{"offset", "length"}, []string{"bytes"}, []string{"out"}},
		"page":    {"page(uint8)", "view", []string{"uint8"}, []string{"at"}, []string{"address", "bytes32", "bytes32", "uint32"}, []string{"pageAddress", "codeHash", "pageCommitment", "length"}},
	}
	getters := map[string]string{"owner": "address", "index": "address", "store": "address", "indexRoot": "bytes32", "content": "bytes32", "packedRecord": "bytes32", "nameHash": "bytes32", "binding": "bytes32", "outputRolling": "bytes32", "publicationRolling": "bytes32", "finalRoot": "bytes32", "entryIndex": "uint32", "dataStart": "uint32", "compressedSize": "uint32", "plainSize": "uint32", "expectedCRC": "uint32", "outputCount": "uint32", "inputByte": "uint32", "work": "uint32", "crc": "uint32", "pendingLength": "uint16", "pendingDistance": "uint16", "inputBit": "uint8", "method": "uint8", "phase": "uint8", "blockMode": "uint8", "blockFinal": "bool", "fixedBlock": "bool", "publishedPages": "uint8"}
	for n, t := range getters {
		want[n] = shape{n + "()", "view", nil, nil, []string{t}, []string{""}}
	}
	if len(a.Methods) != len(want) {
		return fmt.Errorf("di0: embedded ABI has %d methods, want exactly %d", len(a.Methods), len(want))
	}
	for n, w := range want {
		m, ok := a.Methods[n]
		if !ok || m.RawName != n || m.Sig != w.sig || m.StateMutability != w.mut || len(m.Inputs) != len(w.in) || len(m.Outputs) != len(w.out) {
			return fmt.Errorf("di0: embedded ABI method %s differs from frozen shape", n)
		}
		for i, x := range m.Inputs {
			if x.Type.String() != w.in[i] || x.Name != w.inn[i] {
				return fmt.Errorf("di0: embedded ABI %s input %d differs", n, i)
			}
		}
		for i, x := range m.Outputs {
			if x.Type.String() != w.out[i] || x.Name != w.outn[i] {
				return fmt.Errorf("di0: embedded ABI %s output %d differs", n, i)
			}
		}
	}
	if len(a.Constructor.Inputs) != 3 || a.Constructor.StateMutability != "nonpayable" {
		return errors.New("di0: embedded constructor differs from frozen shape")
	}
	cn := []string{"finalIndex", "assertedIndexRoot", "rawName"}
	ct := []string{"address", "bytes32", "bytes"}
	for i, x := range a.Constructor.Inputs {
		if x.Name != cn[i] || x.Type.String() != ct[i] {
			return errors.New("di0: embedded constructor differs from frozen shape")
		}
	}
	e, ok := a.Errors["DI0Error"]
	if !ok || len(a.Errors) != 1 || e.Sig != "DI0Error(uint256)" || len(e.Inputs) != 1 || e.Inputs[0].Name != "code" || e.Inputs[0].Type.String() != "uint256" {
		return errors.New("di0: embedded ABI must contain exactly DI0Error(uint256 code)")
	}
	return nil
}
