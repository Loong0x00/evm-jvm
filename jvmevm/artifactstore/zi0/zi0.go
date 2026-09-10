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
	"fmt"
	"strings"
	"sync"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
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
	ContractName     string          `json:"contractName"`
	ABI              json.RawMessage `json:"abi"`
	Bytecode         string          `json:"bytecode"`
	DeployedBytecode string          `json:"deployedBytecode"`
	Runtime          string          `json:"runtime"`
}

var (
	loadOnce                   sync.Once
	loadErr                    error
	loadABI                    abi.ABI
	loadRaw, loadInit, loadRun []byte
)

func loadArtifact() {
	loadOnce.Do(func() {
		var doc artifactJSON
		if err := json.Unmarshal(zi0runtime.Artifact(), &doc); err != nil {
			loadErr = fmt.Errorf("zi0: decode embedded artifact: %w", err)
			return
		}
		if doc.ContractName != "ZI0ZipIndex" {
			loadErr = fmt.Errorf("zi0: unexpected embedded contract %q", doc.ContractName)
			return
		}
		if len(bytes.TrimSpace(doc.ABI)) == 0 || bytes.Equal(bytes.TrimSpace(doc.ABI), []byte("null")) {
			loadErr = fmt.Errorf("zi0: embedded ABI is empty")
			return
		}
		a, err := abi.JSON(bytes.NewReader(doc.ABI))
		if err != nil {
			loadErr = fmt.Errorf("zi0: parse embedded ABI: %w", err)
			return
		}
		if err = validateABI(a); err != nil {
			loadErr = err
			return
		}
		init, err := decodeCode("init", doc.Bytecode)
		if err != nil {
			loadErr = err
			return
		}
		runText := doc.DeployedBytecode
		if runText == "" {
			runText = doc.Runtime
		}
		run, err := decodeCode("runtime", runText)
		if err != nil {
			loadErr = err
			return
		}
		if len(init) > 49152 || len(run) > 24576 {
			loadErr = fmt.Errorf("zi0: embedded code exceeds frozen constructor/runtime bounds (%d/%d)", len(init), len(run))
			return
		}
		loadABI, loadRaw, loadInit, loadRun = a, append([]byte(nil), doc.ABI...), init, run
	})
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
	if a.HasFallback() || a.HasReceive() {
		return fmt.Errorf("zi0: frozen ABI has no fallback or receive")
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
