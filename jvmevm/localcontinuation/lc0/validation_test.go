// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.
//
// Independent verifier for the frozen LOCAL MC-LC0 continuation profile. The
// decoder in this file is test-only: production Go continues to transport the
// checkpoint as opaque bytes and never evaluates Java state.
package lc0

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"math/big"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
	"testing"
	"time"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/state"
	"github.com/ethereum/go-ethereum/core/tracing"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/core/vm"
	"github.com/ethereum/go-ethereum/core/vm/runtime"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/jvmevm"
)

const (
	lc0VerifyOrdinaryGas = uint64(100_000_000)
	lc0VerifyBoundaryGas = uint64(1_000_000_000)
	lc0VerifyReserveGas  = uint64(25_000_000)
	lc0VerifyMaxBlob     = 1 << 20
	lc0VerifyHeaderSize  = 216

	lc0VerifyRunnable = uint8(1)
	lc0VerifyReturned = uint8(2)
	lc0VerifyUncaught = uint8(3)
)

var (
	lc0VerifyOwner = common.HexToAddress("0x0000000000000000000000000000000000001c01")
	lc0VerifyOther = common.HexToAddress("0x0000000000000000000000000000000000001c02")
	lc0VerifyAt    = common.HexToAddress("0x0000000000000000000000000000000000001c00")
)

type lc0VerifySlice struct {
	Schema                uint32
	Lifecycle             uint8
	Epoch                 uint64
	CheckpointRoot        [32]byte
	MachineStateRoot      [32]byte
	TotalJvmSteps         uint64
	TotalInternalSteps    uint64
	ExecutedJvmSteps      uint64
	ExecutedInternalSteps uint32
	Result                int32
	JavaKind              uint8
	JavaRef               uint32
}

type lc0VerifyHead struct {
	Owner           common.Address
	Epoch           uint64
	CheckpointRoot  common.Hash
	MachineRoot     common.Hash
	ArtifactRoot    common.Hash
	ConfigRoot      common.Hash
	RuntimeCodeHash common.Hash
	Lifecycle       uint8
}

type lc0VerifyCall struct {
	output []byte
	left   uint64
	err    error
	logs   []*types.Log
}

type lc0VerifyEnv struct {
	t        *testing.T
	state    *state.StateDB
	code     []byte
	contract abi.ABI
	calls    uint64
}

func lc0VerifyNewEnv(t *testing.T) *lc0VerifyEnv {
	t.Helper()
	code, err := Runtime()
	if err != nil {
		t.Fatalf("load LC0 runtime (runtime integration dependency absent): %v", err)
	}
	contract, err := ABI()
	if err != nil {
		t.Fatalf("load LC0 ABI: %v", err)
	}
	st, err := state.New(types.EmptyRootHash, state.NewDatabaseForTesting())
	if err != nil {
		t.Fatal(err)
	}
	st.CreateAccount(lc0VerifyAt)
	st.SetCode(lc0VerifyAt, code, tracing.CodeChangeUnspecified)
	return &lc0VerifyEnv{t: t, state: st, code: code, contract: contract}
}

func (e *lc0VerifyEnv) close() { e.state.Database().TrieDB().Close() }

func (e *lc0VerifyEnv) callAs(owner common.Address, gas uint64, method string, args ...any) lc0VerifyCall {
	e.t.Helper()
	input, err := e.contract.Pack(method, args...)
	if err != nil {
		e.t.Fatalf("pack %s: %v", method, err)
	}
	e.calls++
	txHash := crypto.Keccak256Hash([]byte("LC0 verifier call"), new(big.Int).SetUint64(e.calls).Bytes())
	e.state.SetTxContext(txHash, 0)
	start := time.Now()
	output, left, callErr := runtime.Call(lc0VerifyAt, input, &runtime.Config{
		State: e.state, Origin: owner, GasLimit: gas,
		BlockNumber: big.NewInt(1), Time: 1,
	})
	limit := 30 * time.Second
	if gas > lc0VerifyOrdinaryGas {
		limit = 120 * time.Second
	}
	if elapsed := time.Since(start); elapsed > limit {
		e.t.Fatalf("%s call exceeded LOCAL watchdog: %s > %s", method, elapsed, limit)
	}
	logs := append([]*types.Log(nil), e.state.GetLogs(txHash, 1, common.Hash{}, 1)...)
	return lc0VerifyCall{append([]byte(nil), output...), left, callErr, logs}
}

func (e *lc0VerifyEnv) start(owner common.Address, instance common.Hash, raw [][]byte, entryClass, entry string, args []int32, jvm uint64, internal uint32, gas uint64) (lc0VerifySlice, []byte, lc0VerifyCall) {
	e.t.Helper()
	c := e.callAs(owner, gas, "start", instance, raw, entryClass, entry, args, jvm, internal)
	if c.err != nil {
		return lc0VerifySlice{}, nil, c
	}
	values, err := e.contract.Methods["start"].Outputs.Unpack(c.output)
	if err != nil || len(values) != 2 {
		e.t.Fatalf("decode start outputs=%d: %v (%x)", len(values), err, c.output)
	}
	s := *abi.ConvertType(values[0], new(lc0VerifySlice)).(*lc0VerifySlice)
	return s, append([]byte(nil), values[1].([]byte)...), c
}

func (e *lc0VerifyEnv) resume(owner common.Address, instance common.Hash, epoch uint64, root common.Hash, raw [][]byte, checkpoint []byte, jvm uint64, internal uint32, gas uint64) (lc0VerifySlice, []byte, lc0VerifyCall) {
	e.t.Helper()
	c := e.callAs(owner, gas, "resume", instance, epoch, root, raw, checkpoint, jvm, internal)
	if c.err != nil {
		return lc0VerifySlice{}, nil, c
	}
	values, err := e.contract.Methods["resume"].Outputs.Unpack(c.output)
	if err != nil || len(values) != 2 {
		e.t.Fatalf("decode resume outputs=%d: %v (%x)", len(values), err, c.output)
	}
	s := *abi.ConvertType(values[0], new(lc0VerifySlice)).(*lc0VerifySlice)
	return s, append([]byte(nil), values[1].([]byte)...), c
}

func (e *lc0VerifyEnv) head(instance common.Hash) lc0VerifyHead {
	e.t.Helper()
	c := e.callAs(lc0VerifyOwner, lc0VerifyOrdinaryGas, "head", instance)
	if c.err != nil {
		e.t.Fatalf("head: %v data=%x", c.err, c.output)
	}
	v, err := e.contract.Methods["head"].Outputs.Unpack(c.output)
	if err != nil || len(v) != 8 {
		e.t.Fatalf("decode head: %v values=%d", err, len(v))
	}
	return lc0VerifyHead{v[0].(common.Address), v[1].(uint64), common.Hash(v[2].([32]byte)), common.Hash(v[3].([32]byte)), common.Hash(v[4].([32]byte)), common.Hash(v[5].([32]byte)), common.Hash(v[6].([32]byte)), v[7].(uint8)}
}

func lc0VerifySliceRoot(s lc0VerifySlice) common.Hash   { return common.Hash(s.CheckpointRoot) }
func lc0VerifyMachineRoot(s lc0VerifySlice) common.Hash { return common.Hash(s.MachineStateRoot) }

func lc0VerifyAssertSuccess(t *testing.T, s lc0VerifySlice, checkpoint []byte, c lc0VerifyCall) {
	t.Helper()
	if c.err != nil || len(c.logs) != 1 {
		t.Fatalf("successful slice err=%v data=%x left=%d logs=%d", c.err, c.output, c.left, len(c.logs))
	}
	if s.Schema != 1 || s.Epoch == 0 || s.Lifecycle < lc0VerifyRunnable || s.Lifecycle > lc0VerifyUncaught || len(checkpoint) < lc0VerifyHeaderSize || len(checkpoint) > lc0VerifyMaxBlob {
		t.Fatalf("noncanonical slice=%+v checkpoint=%d", s, len(checkpoint))
	}
	if crypto.Keccak256Hash(checkpoint) != lc0VerifySliceRoot(s) {
		t.Fatal("checkpointRoot is not keccak(exact checkpoint)")
	}
}

func lc0VerifyCustomError(signature string, words ...uint64) []byte {
	out := append([]byte(nil), crypto.Keccak256([]byte(signature))[:4]...)
	for _, value := range words {
		var word [32]byte
		binary.BigEndian.PutUint64(word[24:], value)
		out = append(out, word[:]...)
	}
	return out
}

func lc0VerifyAssertControl(t *testing.T, c lc0VerifyCall, code uint64) {
	t.Helper()
	if !errors.Is(c.err, vm.ErrExecutionReverted) || !bytes.Equal(c.output, lc0VerifyCustomError("LC0ControlError(uint256)", code)) || len(c.logs) != 0 {
		t.Fatalf("want LC0ControlError(%d), err=%v data=%x logs=%d", code, c.err, c.output, len(c.logs))
	}
}

func lc0VerifyStateError(data []byte) (code, offset uint64, ok bool) {
	if len(data) != 68 || !bytes.Equal(data[:4], crypto.Keccak256([]byte("LC0StateError(uint256,uint256)"))[:4]) {
		return 0, 0, false
	}
	for _, b := range append(append([]byte(nil), data[4:28]...), data[36:60]...) {
		if b != 0 {
			return 0, 0, false
		}
	}
	return binary.BigEndian.Uint64(data[28:36]), binary.BigEndian.Uint64(data[60:68]), true
}

func lc0VerifyAssertState(t *testing.T, c lc0VerifyCall, code uint64, offsets ...uint64) {
	t.Helper()
	got, off, ok := lc0VerifyStateError(c.output)
	if !errors.Is(c.err, vm.ErrExecutionReverted) || !ok || got != code || len(c.logs) != 0 {
		t.Fatalf("want LC0StateError(%d,*), got %d/%d/%v err=%v data=%x logs=%d", code, got, off, ok, c.err, c.output, len(c.logs))
	}
	if len(offsets) != 0 && off != offsets[0] {
		t.Fatalf("LC0StateError offset=%d want=%d", off, offsets[0])
	}
}

func lc0VerifyAssertHeadEqual(t *testing.T, have, want lc0VerifyHead) {
	t.Helper()
	if !reflect.DeepEqual(have, want) {
		t.Fatalf("head changed\nhave %+v\nwant %+v", have, want)
	}
}

// lc0VerifyReader decodes the exact custom 216-byte envelope and flat machine
// stream. It deliberately has no connection to Session.Start/Resume.
type lc0VerifyReader struct {
	b []byte
	p int
}

func (r *lc0VerifyReader) take(n int) ([]byte, error) {
	if n < 0 || r.p > len(r.b) || n > len(r.b)-r.p {
		return nil, fmt.Errorf("truncated at %d need %d", r.p, n)
	}
	v := r.b[r.p : r.p+n]
	r.p += n
	return v, nil
}
func (r *lc0VerifyReader) u8() (uint8, error) {
	b, e := r.take(1)
	if e != nil {
		return 0, e
	}
	return b[0], nil
}
func (r *lc0VerifyReader) u16() (uint16, error) {
	b, e := r.take(2)
	if e != nil {
		return 0, e
	}
	return binary.BigEndian.Uint16(b), nil
}
func (r *lc0VerifyReader) u32() (uint32, error) {
	b, e := r.take(4)
	if e != nil {
		return 0, e
	}
	return binary.BigEndian.Uint32(b), nil
}
func (r *lc0VerifyReader) u64() (uint64, error) {
	b, e := r.take(8)
	if e != nil {
		return 0, e
	}
	return binary.BigEndian.Uint64(b), nil
}

type lc0VerifyFrame struct {
	Offset, FlagsOffset, SPOffset, BitmapOffset int
	Class, Method                               uint16
	PC                                          uint32
	CallPC                                      *big.Int
	Flags                                       uint8
	This                                        uint32
	SP, Locals                                  uint16
	StackOffsets, LocalOffsets                  []int
}
type lc0VerifyHeapRecord struct {
	Offset, HandleOffset, MetadataOffset, ClassOffset, RankOffset, CountOffset int
	Handle                                                                     uint32
	Metadata                                                                   *big.Int
	Class                                                                      uint16
	Rank                                                                       uint8
	Count                                                                      uint32
	CellOffsets                                                                []int
	Object                                                                     bool
}
type lc0VerifyMachine struct {
	LifecycleOffset, ResultOffset, JavaKindOffset, JavaRefOffset        int
	TotalJvmOffset, TotalInternalOffset                                 int
	Lifecycle, JavaKind                                                 uint8
	Result                                                              int32
	JavaRef                                                             uint32
	TotalJvm, TotalInternal                                             uint64
	EntryClass, Entry                                                   string
	Args                                                                []int32
	ClassCount                                                          uint16
	ClassOffsets, InitOffsets, StartedOffsets                           []int
	StaticIndexOffsets, StaticValueOffsets                              [][]int
	FrameCountOffset                                                    int
	Frames                                                              []lc0VerifyFrame
	HeapHeaderOffset                                                    int
	NextHandle                                                          uint32
	OrdinaryObjects, OrdinaryArrays                                     uint16
	OrdinaryElements, OrdinaryFields                                    uint32
	EmergencyRef                                                        uint32
	ExceptionObjects                                                    uint16
	ExceptionFields                                                     uint32
	Heap                                                                []lc0VerifyHeapRecord
	PendingOffset, PendingKindOffset, PendingRefOffset, PendingPCOffset int
	PendingActive, PendingKind                                          uint8
	PendingRef                                                          uint32
	PendingPC                                                           *big.Int
	InternCountOffset                                                   int
	InternHandleOffsets, InternHashOffsets                              []int
}
type lc0VerifyCheckpoint struct {
	Bytes                                          []byte
	Schema                                         uint32
	Instance                                       common.Hash
	Epoch                                          uint64
	Parent, Runtime, Artifact, Config, MachineRoot common.Hash
	MachineLength                                  uint32
	Machine                                        lc0VerifyMachine
}

func lc0VerifyReadASCII(r *lc0VerifyReader) (string, error) {
	n, e := r.u16()
	if e != nil {
		return "", e
	}
	b, e := r.take(int(n))
	if e != nil {
		return "", e
	}
	for _, c := range b {
		if c < 0x20 || c > 0x7e {
			return "", fmt.Errorf("non-ASCII at %d", r.p-int(n))
		}
	}
	return string(b), nil
}

func lc0VerifyDecodeCheckpoint(blob []byte) (lc0VerifyCheckpoint, error) {
	var c lc0VerifyCheckpoint
	c.Bytes = append([]byte(nil), blob...)
	if len(blob) < lc0VerifyHeaderSize {
		return c, fmt.Errorf("short header")
	}
	if string(blob[:8]) != "JVMELC01" {
		return c, fmt.Errorf("header magic")
	}
	c.Schema = binary.BigEndian.Uint32(blob[8:12])
	copy(c.Instance[:], blob[12:44])
	c.Epoch = binary.BigEndian.Uint64(blob[44:52])
	copy(c.Parent[:], blob[52:84])
	copy(c.Runtime[:], blob[84:116])
	copy(c.Artifact[:], blob[116:148])
	copy(c.Config[:], blob[148:180])
	copy(c.MachineRoot[:], blob[180:212])
	c.MachineLength = binary.BigEndian.Uint32(blob[212:216])
	if c.Schema != 1 || int(c.MachineLength) != len(blob)-lc0VerifyHeaderSize || len(blob) > lc0VerifyMaxBlob {
		return c, fmt.Errorf("header length/schema")
	}
	r := &lc0VerifyReader{b: blob[lc0VerifyHeaderSize:]}
	if b, e := r.take(4); e != nil || string(b) != "LCS1" {
		return c, fmt.Errorf("machine magic")
	}
	m := lc0VerifyMachine{}
	m.LifecycleOffset = lc0VerifyHeaderSize + r.p
	m.Lifecycle, _ = r.u8()
	m.ResultOffset = lc0VerifyHeaderSize + r.p
	b, e := r.take(4)
	if e != nil {
		return c, e
	}
	m.Result = int32(binary.BigEndian.Uint32(b))
	m.JavaKindOffset = lc0VerifyHeaderSize + r.p
	m.JavaKind, _ = r.u8()
	m.JavaRefOffset = lc0VerifyHeaderSize + r.p
	m.JavaRef, _ = r.u32()
	m.TotalJvmOffset = lc0VerifyHeaderSize + r.p
	m.TotalJvm, _ = r.u64()
	m.TotalInternalOffset = lc0VerifyHeaderSize + r.p
	m.TotalInternal, _ = r.u64()
	if m.EntryClass, e = lc0VerifyReadASCII(r); e != nil {
		return c, e
	}
	if m.Entry, e = lc0VerifyReadASCII(r); e != nil {
		return c, e
	}
	argc, e := r.u8()
	if e != nil {
		return c, e
	}
	for i := 0; i < int(argc); i++ {
		b, e := r.take(4)
		if e != nil {
			return c, e
		}
		m.Args = append(m.Args, int32(binary.BigEndian.Uint32(b)))
	}
	m.ClassCount, e = r.u16()
	if e != nil {
		return c, e
	}
	for i := 0; i < int(m.ClassCount); i++ {
		m.ClassOffsets = append(m.ClassOffsets, lc0VerifyHeaderSize+r.p)
		m.InitOffsets = append(m.InitOffsets, lc0VerifyHeaderSize+r.p)
		if _, e = r.u8(); e != nil {
			return c, e
		}
		m.StartedOffsets = append(m.StartedOffsets, lc0VerifyHeaderSize+r.p)
		if _, e = r.u8(); e != nil {
			return c, e
		}
		n, e := r.u16()
		if e != nil {
			return c, e
		}
		var indices, vals []int
		for j := 0; j < int(n); j++ {
			indices = append(indices, lc0VerifyHeaderSize+r.p)
			if _, e = r.u16(); e != nil {
				return c, e
			}
			vals = append(vals, lc0VerifyHeaderSize+r.p)
			if _, e = r.take(32); e != nil {
				return c, e
			}
		}
		m.StaticIndexOffsets = append(m.StaticIndexOffsets, indices)
		m.StaticValueOffsets = append(m.StaticValueOffsets, vals)
	}
	m.FrameCountOffset = lc0VerifyHeaderSize + r.p
	frames, e := r.u16()
	if e != nil {
		return c, e
	}
	for i := 0; i < int(frames); i++ {
		f := lc0VerifyFrame{Offset: lc0VerifyHeaderSize + r.p}
		f.Class, e = r.u16()
		if e != nil {
			return c, e
		}
		f.Method, e = r.u16()
		if e != nil {
			return c, e
		}
		f.PC, e = r.u32()
		if e != nil {
			return c, e
		}
		b, e = r.take(32)
		if e != nil {
			return c, e
		}
		f.CallPC = new(big.Int).SetBytes(b)
		f.FlagsOffset = lc0VerifyHeaderSize + r.p
		f.Flags, e = r.u8()
		if e != nil {
			return c, e
		}
		f.This, e = r.u32()
		if e != nil {
			return c, e
		}
		f.SPOffset = lc0VerifyHeaderSize + r.p
		f.SP, e = r.u16()
		if e != nil {
			return c, e
		}
		for j := 0; j < int(f.SP); j++ {
			f.StackOffsets = append(f.StackOffsets, lc0VerifyHeaderSize+r.p)
			if _, e = r.take(32); e != nil {
				return c, e
			}
		}
		f.Locals, e = r.u16()
		if e != nil {
			return c, e
		}
		f.BitmapOffset = lc0VerifyHeaderSize + r.p
		if _, e = r.take((int(f.Locals) + 7) / 8); e != nil {
			return c, e
		}
		for j := 0; j < int(f.Locals); j++ {
			f.LocalOffsets = append(f.LocalOffsets, lc0VerifyHeaderSize+r.p)
			if _, e = r.take(32); e != nil {
				return c, e
			}
		}
		m.Frames = append(m.Frames, f)
	}
	m.HeapHeaderOffset = lc0VerifyHeaderSize + r.p
	m.NextHandle, e = r.u32()
	if e != nil {
		return c, e
	}
	m.OrdinaryObjects, e = r.u16()
	if e != nil {
		return c, e
	}
	m.OrdinaryArrays, e = r.u16()
	if e != nil {
		return c, e
	}
	m.OrdinaryElements, e = r.u32()
	if e != nil {
		return c, e
	}
	m.OrdinaryFields, e = r.u32()
	if e != nil {
		return c, e
	}
	m.EmergencyRef, e = r.u32()
	if e != nil {
		return c, e
	}
	m.ExceptionObjects, e = r.u16()
	if e != nil {
		return c, e
	}
	m.ExceptionFields, e = r.u32()
	if e != nil {
		return c, e
	}
	for i := uint32(0); i < m.NextHandle; i++ {
		h := lc0VerifyHeapRecord{Offset: lc0VerifyHeaderSize + r.p, HandleOffset: lc0VerifyHeaderSize + r.p}
		h.Handle, e = r.u32()
		if e != nil {
			return c, e
		}
		h.MetadataOffset = lc0VerifyHeaderSize + r.p
		b, e = r.take(32)
		if e != nil {
			return c, e
		}
		h.Metadata = new(big.Int).SetBytes(b)
		h.Object = len(b) > 0 && b[0]&0x80 != 0
		h.ClassOffset = lc0VerifyHeaderSize + r.p
		h.Class, e = r.u16()
		if e != nil {
			return c, e
		}
		h.RankOffset = lc0VerifyHeaderSize + r.p
		h.Rank, e = r.u8()
		if e != nil {
			return c, e
		}
		h.CountOffset = lc0VerifyHeaderSize + r.p
		h.Count, e = r.u32()
		if e != nil {
			return c, e
		}
		width := 8
		if h.Object {
			width = 32
		}
		if uint64(h.Count)*uint64(width) > uint64(len(r.b)-r.p) {
			return c, fmt.Errorf("heap cells overflow")
		}
		for j := uint32(0); j < h.Count; j++ {
			h.CellOffsets = append(h.CellOffsets, lc0VerifyHeaderSize+r.p)
			if _, e = r.take(width); e != nil {
				return c, e
			}
		}
		m.Heap = append(m.Heap, h)
	}
	m.PendingOffset = lc0VerifyHeaderSize + r.p
	m.PendingActive, e = r.u8()
	if e != nil {
		return c, e
	}
	m.PendingKindOffset = lc0VerifyHeaderSize + r.p
	m.PendingKind, e = r.u8()
	if e != nil {
		return c, e
	}
	m.PendingRefOffset = lc0VerifyHeaderSize + r.p
	m.PendingRef, e = r.u32()
	if e != nil {
		return c, e
	}
	m.PendingPCOffset = lc0VerifyHeaderSize + r.p
	b, e = r.take(32)
	if e != nil {
		return c, e
	}
	m.PendingPC = new(big.Int).SetBytes(b)
	m.InternCountOffset = lc0VerifyHeaderSize + r.p
	interns, e := r.u16()
	if e != nil {
		return c, e
	}
	for i := 0; i < int(interns); i++ {
		m.InternHandleOffsets = append(m.InternHandleOffsets, lc0VerifyHeaderSize+r.p)
		if _, e = r.u32(); e != nil {
			return c, e
		}
		m.InternHashOffsets = append(m.InternHashOffsets, lc0VerifyHeaderSize+r.p)
		if _, e = r.u32(); e != nil {
			return c, e
		}
	}
	if r.p != len(r.b) {
		return c, fmt.Errorf("machine trailing %d", len(r.b)-r.p)
	}
	c.Machine = m
	return c, nil
}

func lc0VerifyABIHash(t *testing.T, typesText []string, values ...any) common.Hash {
	t.Helper()
	args := make(abi.Arguments, len(typesText))
	for i, s := range typesText {
		typ, e := abi.NewType(s, "", nil)
		if e != nil {
			t.Fatal(e)
		}
		args[i] = abi.Argument{Type: typ}
	}
	packed, e := args.Pack(values...)
	if e != nil {
		t.Fatal(e)
	}
	return crypto.Keccak256Hash(packed)
}
func lc0VerifyArtifactRoot(t *testing.T, raw [][]byte) common.Hash {
	return lc0VerifyABIHash(t, []string{"bytes32", "bytes[]"}, crypto.Keccak256Hash([]byte("JVMEVM:MC:LC0:ARTIFACT:1")), raw)
}
func lc0VerifyBootstrapRoot(t *testing.T) common.Hash {
	t.Helper()
	names := []string{"Object", "Cloneable", "Serializable", "Float", "Double", "Throwable", "Error", "VirtualMachineError", "StackOverflowError", "OutOfMemoryError", "LinkageError", "ExceptionInInitializerError", "IncompatibleClassChangeError", "NoClassDefFoundError", "AbstractMethodError", "Exception", "RuntimeException", "ArithmeticException", "NullPointerException", "NegativeArraySizeException", "ClassCastException", "ArrayStoreException", "IndexOutOfBoundsException", "ArrayIndexOutOfBoundsException", "Comparable", "CharSequence", "String"}
	var hashes [27][32]byte
	for i, name := range names {
		encoded, err := os.ReadFile(filepath.Join("..", "..", "runtime", "bootstrap", name+".class.hex"))
		if err != nil {
			t.Fatal(err)
		}
		raw, err := hex.DecodeString(strings.TrimSpace(string(encoded)))
		if err != nil {
			t.Fatal(err)
		}
		hashes[i] = crypto.Keccak256Hash(raw)
	}
	return lc0VerifyABIHash(t, []string{"bytes32", "bytes32[27]"}, crypto.Keccak256Hash([]byte("JVMEVM:MC:LC0:BOOTSTRAP:1")), hashes)
}
func lc0VerifyConfigRoot(t *testing.T, runtimeHash, bootstrap, artifact common.Hash, entryClass, entry string, args []int32) common.Hash {
	return lc0VerifyABIHash(t, []string{"bytes32", "uint32", "bytes32", "bytes32", "bytes32", "string", "string", "int32[]"}, crypto.Keccak256Hash([]byte("JVMEVM:MC:LC0:CONFIG:1")), uint32(1), runtimeHash, bootstrap, artifact, entryClass, entry, args)
}
func lc0VerifyMachineStateRoot(t *testing.T, c lc0VerifyCheckpoint, machine []byte) common.Hash {
	return lc0VerifyABIHash(t, []string{"bytes32", "uint32", "bytes32", "bytes32", "bytes32"}, crypto.Keccak256Hash([]byte("JVMEVM:MC:LC0:MACHINE:1")), uint32(1), c.Artifact, c.Config, crypto.Keccak256Hash(machine))
}
func lc0VerifyRehashMachine(t *testing.T, blob []byte) []byte {
	t.Helper()
	out := append([]byte(nil), blob...)
	c, e := lc0VerifyDecodeCheckpoint(out)
	if e != nil {
		t.Fatal(e)
	}
	root := lc0VerifyMachineStateRoot(t, c, out[216:])
	copy(out[180:212], root[:])
	return out
}

func lc0VerifyValidate(e *lc0VerifyEnv, raw [][]byte, blob []byte, gas uint64) lc0VerifyCall {
	return e.callAs(lc0VerifyOwner, gas, "validateCheckpoint", raw, blob)
}

func lc0VerifyCheckEvent(t *testing.T, contract abi.ABI, instance common.Hash, s lc0VerifySlice, c lc0VerifyCall) {
	t.Helper()
	if len(c.logs) != 1 {
		t.Fatalf("events=%d", len(c.logs))
	}
	ev, ok := contract.Events["CheckpointCommitted"]
	if !ok {
		t.Fatal("event absent")
	}
	l := c.logs[0]
	if l.Address != lc0VerifyAt || len(l.Topics) != 3 || l.Topics[0] != ev.ID || common.Hash(l.Topics[1]) != instance || new(big.Int).SetBytes(l.Topics[2][:]).Uint64() != s.Epoch {
		t.Fatalf("bad topics=%v", l.Topics)
	}
	v, err := ev.Inputs.NonIndexed().Unpack(l.Data)
	if err != nil {
		t.Fatal(err)
	}
	if common.Hash(v[0].([32]byte)) != lc0VerifySliceRoot(s) || common.Hash(v[1].([32]byte)) != lc0VerifyMachineRoot(s) || v[2].(uint8) != s.Lifecycle || v[3].(uint64) != s.TotalJvmSteps || v[4].(uint64) != s.TotalInternalSteps {
		t.Fatalf("bad event data=%v slice=%+v", v, s)
	}
}

type lc0VerifyFixture struct {
	name, entry string
	classes     []string
	args        []int32
	want        int32
}

var lc0VerifyFixtures = []lc0VerifyFixture{
	{"call-loop", "LC0CallLoop", []string{"LC0CallLoop"}, []int32{5}, 15},
	{"alias-string", "LC0AliasString", []string{"LC0AliasBox", "LC0AliasString"}, nil, 36},
	{"init-exception", "LC0InitException", []string{"LC0InitDep", "LC0InitException"}, nil, 10},
}

var lc0VerifySources = map[string]string{
	"LC0CallLoop":      "public final class LC0CallLoop {\n  static int add(int a, int b) { return a + b; }\n  public static int run(int n) {\n    int sum = 0;\n    for (int i = 1; i <= n; i++) sum = add(sum, i);\n    return sum;\n  }\n}\n",
	"LC0AliasBox":      "public final class LC0AliasBox {\n  int value;\n  LC0AliasBox(int value) { this.value = value; }\n}\n",
	"LC0AliasString":   "public final class LC0AliasString {\n  static LC0AliasBox saved;\n  static String text = \"same\";\n  public static int run() {\n    LC0AliasBox box = new LC0AliasBox(3);\n    saved = box;\n    Object[] aliases = new Object[] { box, text, box, \"same\" };\n    for (int i = 0; i < 3; i++) box.value++;\n    return box.value + saved.value + ((LC0AliasBox) aliases[0]).value\n        + (text == aliases[1] ? 10 : 0) + (text == aliases[3] ? 4 : 0) + text.length();\n  }\n}\n",
	"LC0InitDep":       "public final class LC0InitDep {\n  static int count;\n  static int value;\n  static {\n    count++;\n    try { value = 10 / (count - 1); }\n    catch (ArithmeticException expected) { value = 9; }\n  }\n}\n",
	"LC0InitException": "public final class LC0InitException {\n  public static int run() { return LC0InitDep.value + LC0InitDep.count; }\n}\n",
}
var lc0VerifyClassSHA = map[string]string{
	"LC0CallLoop":      "4970ae2e395e96b91231b5d19439ba4fdfd6b91ef61429904c9fa758058c8302",
	"LC0AliasBox":      "43cb95765ad4f1568a12cc04ce2493aea08ad29916b60b7827231e40bae863c6",
	"LC0AliasString":   "e7ec98bfb70650c23dfe2d1d63b86964d0aa35969b84c85db66945def6c0ec2f",
	"LC0InitDep":       "ac7aaf7e9d7d6ae457d55d52f1300060718e177fb8cc294f1fa80261b89e52c0",
	"LC0InitException": "0c8005f33deac53eba1afda833ee71df28de99e1451c8f074c6e720e75b5fa9d",
}

func lc0VerifyFixtureRoot() string { return filepath.Join("..", "..", "testdata", "local", "lc0") }
func lc0VerifyReadClass(t *testing.T, name string) []byte {
	t.Helper()
	b, e := os.ReadFile(filepath.Join(lc0VerifyFixtureRoot(), "classes", name+".class"))
	if e != nil {
		t.Fatalf("read frozen %s.class (fixture integration dependency absent): %v", name, e)
	}
	return b
}
func lc0VerifyBundle(t *testing.T, f lc0VerifyFixture) [][]byte {
	t.Helper()
	out := make([][]byte, len(f.classes))
	for i, n := range f.classes {
		out[i] = lc0VerifyReadClass(t, n)
	}
	return out
}

func lc0VerifyInstance(label string) common.Hash {
	return crypto.Keccak256Hash([]byte("JVMEVM:MC:LC0:VERIFY:" + label))
}

func lc0VerifyAssertFlatCanonical(t *testing.T, cp lc0VerifyCheckpoint, rawCount int) {
	t.Helper()
	m := cp.Machine
	if int(m.ClassCount) != rawCount+27 || len(m.Heap) != int(m.NextHandle) {
		t.Fatalf("class/heap dimensions=%d/%d want classes=%d handles=%d", m.ClassCount, len(m.Heap), rawCount+27, m.NextHandle)
	}
	var ordinaryObjects, arrays, exceptionObjects uint16
	var ordinaryFields, elements, exceptionFields uint32
	for i, h := range m.Heap {
		if h.Handle != uint32(i+1) {
			t.Fatalf("heap record %d handle=%d", i, h.Handle)
		}
		if h.Object {
			kind := uint8(h.Metadata.Uint64())
			if kind == 0 {
				ordinaryObjects++
				ordinaryFields += h.Count
			} else {
				if kind > 12 {
					t.Fatalf("exception metadata kind=%d", kind)
				}
				exceptionFields += h.Count
				if h.Handle != m.EmergencyRef {
					exceptionObjects++
				}
			}
		} else {
			arrays++
			elements += h.Count
			if h.Rank == 0 {
				t.Fatalf("array handle %d has rank zero", h.Handle)
			}
		}
	}
	if ordinaryObjects != m.OrdinaryObjects || arrays != m.OrdinaryArrays || ordinaryFields != m.OrdinaryFields || elements != m.OrdinaryElements || exceptionObjects != m.ExceptionObjects || exceptionFields != m.ExceptionFields {
		t.Fatalf("heap counters decoded=%d/%d/%d/%d/%d/%d header=%d/%d/%d/%d/%d/%d", ordinaryObjects, arrays, elements, ordinaryFields, exceptionObjects, exceptionFields, m.OrdinaryObjects, m.OrdinaryArrays, m.OrdinaryElements, m.OrdinaryFields, m.ExceptionObjects, m.ExceptionFields)
	}
	if m.NextHandle != 0 && m.EmergencyRef != 1 {
		t.Fatalf("registry emergencyRef=%d want1", m.EmergencyRef)
	}
	for i, offsets := range m.StaticIndexOffsets {
		var prior uint16
		for j, off := range offsets {
			index := binary.BigEndian.Uint16(cp.Bytes[off : off+2])
			if j > 0 && index <= prior {
				t.Fatalf("class%d static order %d <= %d", i, index, prior)
			}
			prior = index
		}
	}
}

func lc0VerifyJavaHash(units []uint16) uint32 {
	var h uint32
	for _, unit := range units {
		h = h*31 + uint32(unit)
	}
	return h
}

func lc0VerifyAssertInternedSame(t *testing.T, cp lc0VerifyCheckpoint, rawCount int, text string) {
	t.Helper()
	m := cp.Machine
	wantUnits := []uint16{}
	for _, r := range text {
		wantUnits = append(wantUnits, uint16(r))
	}
	wantHash := lc0VerifyJavaHash(wantUnits)
	stringClass := uint16(rawCount + 26)
	byHandle := make(map[uint32]lc0VerifyHeapRecord)
	for _, h := range m.Heap {
		byHandle[h.Handle] = h
	}
	seenContent := make(map[string]uint32)
	for i, off := range m.InternHandleOffsets {
		handle := binary.BigEndian.Uint32(cp.Bytes[off : off+4])
		javaHash := binary.BigEndian.Uint32(cp.Bytes[m.InternHashOffsets[i] : m.InternHashOffsets[i]+4])
		obj, ok := byHandle[handle]
		if !ok || !obj.Object || obj.Class != stringClass || obj.Count != 2 {
			t.Fatalf("intern%d does not name canonical String: handle=%d record=%+v", i, handle, obj)
		}
		value := new(big.Int).SetBytes(cp.Bytes[obj.CellOffsets[0] : obj.CellOffsets[0]+32])
		if new(big.Int).Rsh(new(big.Int).Set(value), 64).Uint64() != 2 {
			t.Fatal("String.value is not a reference")
		}
		backing := byHandle[uint32(value.Uint64())]
		if backing.Object || backing.Metadata.Uint64() != 0x43 || backing.Rank != 1 {
			t.Fatalf("String backing is not char[]: %+v", backing)
		}
		units := make([]uint16, len(backing.CellOffsets))
		for j, cell := range backing.CellOffsets {
			units[j] = uint16(binary.BigEndian.Uint64(cp.Bytes[cell : cell+8]))
		}
		key := fmt.Sprint(units)
		if prior, duplicate := seenContent[key]; duplicate && prior != handle {
			t.Fatalf("duplicate canonical String content handles=%d/%d", prior, handle)
		}
		seenContent[key] = handle
		fieldHash := new(big.Int).SetBytes(cp.Bytes[obj.CellOffsets[1] : obj.CellOffsets[1]+32])
		if new(big.Int).Rsh(new(big.Int).Set(fieldHash), 64).Uint64() != 1 || (uint32(fieldHash.Uint64()) != 0 && uint32(fieldHash.Uint64()) != lc0VerifyJavaHash(units)) {
			t.Fatalf("String.hash tagged/cache=%x", fieldHash)
		}
		if javaHash != lc0VerifyJavaHash(units) {
			t.Fatalf("intern hash=%d computed=%d", javaHash, lc0VerifyJavaHash(units))
		}
		if reflect.DeepEqual(units, wantUnits) && javaHash == wantHash {
			return
		}
	}
	t.Fatalf("interned %q not found", text)
}

type lc0VerifyRun struct {
	slice      lc0VerifySlice
	checkpoint []byte
	snapshots  []lc0VerifyCheckpoint
	gas        uint64
}

func lc0VerifyRunChain(t *testing.T, e *lc0VerifyEnv, f lc0VerifyFixture, label string, jvm uint64, internal uint32) lc0VerifyRun {
	t.Helper()
	id := lc0VerifyInstance(label)
	raw := lc0VerifyBundle(t, f)
	s, blob, c := e.start(lc0VerifyOwner, id, raw, f.entry, "run", f.args, jvm, internal, lc0VerifyOrdinaryGas)
	lc0VerifyAssertSuccess(t, s, blob, c)
	lc0VerifyCheckEvent(t, e.contract, id, s, c)
	out := lc0VerifyRun{slice: s, checkpoint: blob, gas: lc0VerifyOrdinaryGas - c.left}
	cp, err := lc0VerifyDecodeCheckpoint(blob)
	if err != nil {
		t.Fatal(err)
	}
	lc0VerifyAssertFlatCanonical(t, cp, len(raw))
	out.snapshots = append(out.snapshots, cp)
	for slices := 1; s.Lifecycle == lc0VerifyRunnable; slices++ {
		if slices >= 256 {
			t.Fatal("continuation exceeded 256 slices")
		}
		s, blob, c = e.resume(lc0VerifyOwner, id, s.Epoch, lc0VerifySliceRoot(s), raw, blob, jvm, internal, lc0VerifyOrdinaryGas)
		lc0VerifyAssertSuccess(t, s, blob, c)
		lc0VerifyCheckEvent(t, e.contract, id, s, c)
		out.gas += lc0VerifyOrdinaryGas - c.left
		cp, err = lc0VerifyDecodeCheckpoint(blob)
		if err != nil {
			t.Fatal(err)
		}
		lc0VerifyAssertFlatCanonical(t, cp, len(raw))
		out.snapshots = append(out.snapshots, cp)
		out.slice = s
		out.checkpoint = blob
		if s.TotalJvmSteps > 4096 {
			t.Fatal("continuation exceeded 4096 dispatch units")
		}
	}
	if s.Lifecycle != lc0VerifyReturned || s.Result != f.want || s.JavaKind != 0 || s.JavaRef != 0 || len(cp.Machine.Frames) != 0 || cp.Machine.PendingActive != 0 {
		t.Fatalf("%s terminal=%+v machine=%+v", f.name, s, cp.Machine)
	}
	return out
}

func TestLC0VerifyFrozenSourcesRuntimeABIAndCommitments(t *testing.T) {
	root := lc0VerifyFixtureRoot()
	transportSource, err := os.ReadFile("session.go")
	if err != nil {
		t.Fatal(err)
	}
	loaderSource, err := os.ReadFile("lc0.go")
	if err != nil {
		t.Fatal(err)
	}
	joined := string(append(append([]byte(nil), loaderSource...), transportSource...))
	for _, forbidden := range []string{"runtime.Execute(", ".SetState(", "java_diff", "ClassFile", "recoverTrace", "net.Listen", "http.Listen"} {
		if strings.Contains(joined, forbidden) {
			t.Fatalf("production LOCAL transport contains forbidden host path %q", forbidden)
		}
	}
	if strings.Count(string(transportSource), ".SetCode(") != 1 {
		t.Fatalf("production code-install sites=%d want1", strings.Count(string(transportSource), ".SetCode("))
	}
	if !strings.Contains(string(transportSource), "evmruntime.Call(") {
		t.Fatal("Session does not use persistent runtime.Call")
	}
	if len(lc0VerifySources) != 5 || len(lc0VerifyClassSHA) != 5 {
		t.Fatal("frozen fixture dimensions changed")
	}
	var aggregate int
	for name, wantSource := range lc0VerifySources {
		source, err := os.ReadFile(filepath.Join(root, "src", name+".java"))
		if err != nil {
			t.Fatalf("read %s source: %v", name, err)
		}
		if string(source) != wantSource {
			t.Fatalf("%s source bytes changed: sha256=%x", name, sha256.Sum256(source))
		}
		raw := lc0VerifyReadClass(t, name)
		aggregate += len(raw)
		if got := fmt.Sprintf("%x", sha256.Sum256(raw)); got != lc0VerifyClassSHA[name] {
			t.Fatalf("%s class sha256=%s want=%s", name, got, lc0VerifyClassSHA[name])
		}
	}
	if aggregate > 65536 {
		t.Fatalf("fixture aggregate=%d exceeds 64KiB", aggregate)
	}
	code, err := Runtime()
	if err != nil {
		t.Fatal(err)
	}
	if len(code) == 0 || len(code) > 256*1024 {
		t.Fatalf("LOCAL runtime size=%d, want 1..256KiB", len(code))
	}
	sha := fmt.Sprintf("%x", sha256.Sum256(code))
	reported, err := RuntimeHash()
	if err != nil || reported != sha {
		t.Fatalf("RuntimeHash=%q/%v want=%s", reported, err, sha)
	}
	contract, err := ABI()
	if err != nil {
		t.Fatal(err)
	}
	wantMethods := map[string]struct {
		sig, mut string
		in, out  int
	}{
		"start":              {"start(bytes32,bytes[],string,string,int32[],uint64,uint32)", "nonpayable", 7, 2},
		"resume":             {"resume(bytes32,uint64,bytes32,bytes[],bytes,uint64,uint32)", "nonpayable", 7, 2},
		"head":               {"head(bytes32)", "view", 1, 8},
		"validateCheckpoint": {"validateCheckpoint(bytes[],bytes)", "view", 2, 1},
	}
	if len(contract.Methods) != len(wantMethods) {
		t.Fatalf("public method count=%d want4: %v", len(contract.Methods), contract.Methods)
	}
	for name, w := range wantMethods {
		m, ok := contract.Methods[name]
		if !ok || m.Sig != w.sig || m.StateMutability != w.mut || len(m.Inputs) != w.in || len(m.Outputs) != w.out {
			t.Fatalf("%s ABI=%+v present=%v", name, m, ok)
		}
	}
	tuple := contract.Methods["start"].Outputs[0].Type
	wantNames := []string{"schema", "lifecycle", "epoch", "checkpointRoot", "machineStateRoot", "totalJvmSteps", "totalInternalSteps", "executedJvmSteps", "executedInternalSteps", "result", "javaKind", "javaRef"}
	wantTypes := []string{"uint32", "uint8", "uint64", "bytes32", "bytes32", "uint64", "uint64", "uint64", "uint32", "int32", "uint8", "uint32"}
	if tuple.T != abi.TupleTy || !reflect.DeepEqual(tuple.TupleRawNames, wantNames) || len(tuple.TupleElems) != len(wantTypes) {
		t.Fatalf("SliceResult tuple names=%v", tuple.TupleRawNames)
	}
	for i, w := range wantTypes {
		if tuple.TupleElems[i].String() != w {
			t.Fatalf("SliceResult.%s=%s want=%s", wantNames[i], tuple.TupleElems[i], w)
		}
	}
	for _, x := range []struct{ name, sig string }{{"LC0ControlError", "LC0ControlError(uint256)"}, {"LC0StateError", "LC0StateError(uint256,uint256)"}} {
		a, ok := contract.Errors[x.name]
		if !ok || a.Sig != x.sig {
			t.Fatalf("error %s=%+v", x.name, a)
		}
	}
	ev, ok := contract.Events["CheckpointCommitted"]
	if !ok || ev.Sig != "CheckpointCommitted(bytes32,uint64,bytes32,bytes32,uint8,uint64,uint64)" || len(ev.Inputs) != 7 || !ev.Inputs[0].Indexed || !ev.Inputs[1].Indexed {
		t.Fatalf("CheckpointCommitted=%+v", ev)
	}

	artifactPath := filepath.Join("..", "..", "runtime", "local", "lc0", "artifacts", "LC0Interpreter.json")
	artifactBytes, err := os.ReadFile(artifactPath)
	if err != nil {
		t.Fatalf("read pinned artifact: %v", err)
	}
	var doc struct {
		ContractName     string
		ABI              json.RawMessage
		DeployedBytecode string
		Compiler         struct {
			Version, EVMVersion string
			ViaIR               bool `json:"viaIR"`
			Optimizer           struct {
				Enabled bool
				Runs    int
			}
			Metadata struct {
				AppendCBOR   bool
				BytecodeHash string
			}
		}
		SourceHashes map[string]string
	}
	if err = json.Unmarshal(artifactBytes, &doc); err != nil {
		t.Fatal(err)
	}
	artifactCode, err := hex.DecodeString(strings.TrimPrefix(doc.DeployedBytecode, "0x"))
	if err != nil {
		t.Fatal(err)
	}
	if doc.ContractName != "LC0Interpreter" || !bytes.Equal(artifactCode, code) || !strings.HasPrefix(doc.Compiler.Version, "0.8.30+commit.73712a01") || !doc.Compiler.ViaIR || !doc.Compiler.Optimizer.Enabled || doc.Compiler.Optimizer.Runs != 200 || doc.Compiler.EVMVersion != "cancun" || doc.Compiler.Metadata.AppendCBOR || doc.Compiler.Metadata.BytecodeHash != "none" {
		t.Fatalf("artifact/config not frozen: contract=%s bytes=%d/%d compiler=%+v", doc.ContractName, len(artifactCode), len(code), doc.Compiler)
	}
	if len(doc.SourceHashes) == 0 {
		t.Fatal("artifact has no source hashes")
	}
	for rel, want := range doc.SourceHashes {
		source, err := os.ReadFile(filepath.Join("..", "..", "runtime", "local", "lc0", filepath.FromSlash(rel)))
		if err != nil {
			t.Fatalf("artifact source %s: %v", rel, err)
		}
		if got := fmt.Sprintf("%x", sha256.Sum256(source)); got != want {
			t.Fatalf("source %s hash=%s want=%s", rel, got, want)
		}
	}

	e := lc0VerifyNewEnv(t)
	defer e.close()
	if !bytes.Equal(e.state.GetCode(lc0VerifyAt), code) || e.state.GetCodeHash(lc0VerifyAt) != crypto.Keccak256Hash(code) {
		t.Fatal("LOCAL code installation bytes/hash mismatch")
	}
	unknown := e.head(lc0VerifyInstance("unknown"))
	if !reflect.DeepEqual(unknown, lc0VerifyHead{}) {
		t.Fatalf("unknown head nonzero: %+v", unknown)
	}
	f := lc0VerifyFixtures[0]
	raw := lc0VerifyBundle(t, f)
	id := lc0VerifyInstance("commitments")
	s, blob, call := e.start(lc0VerifyOwner, id, raw, f.entry, "run", f.args, 1, 4096, lc0VerifyOrdinaryGas)
	lc0VerifyAssertSuccess(t, s, blob, call)
	cp, err := lc0VerifyDecodeCheckpoint(blob)
	if err != nil {
		t.Fatal(err)
	}
	wantConfig := lc0VerifyConfigRoot(t, crypto.Keccak256Hash(code), lc0VerifyBootstrapRoot(t), lc0VerifyArtifactRoot(t, raw), f.entry, "run", f.args)
	if cp.Instance != id || cp.Epoch != 1 || cp.Parent != (common.Hash{}) || cp.Runtime != crypto.Keccak256Hash(code) || cp.Artifact != lc0VerifyArtifactRoot(t, raw) || cp.Config != wantConfig || cp.MachineRoot != lc0VerifyMachineStateRoot(t, cp, blob[216:]) {
		t.Fatalf("checkpoint commitments=%+v", cp)
	}
	head := e.head(id)
	if head.Owner != lc0VerifyOwner || head.Epoch != 1 || head.CheckpointRoot != crypto.Keccak256Hash(blob) || head.MachineRoot != cp.MachineRoot || head.ArtifactRoot != cp.Artifact || head.ConfigRoot != cp.Config || head.RuntimeCodeHash != cp.Runtime || head.Lifecycle != s.Lifecycle {
		t.Fatalf("head/checkpoint mismatch head=%+v slice=%+v", head, s)
	}
	t.Logf("LC0 LOCAL runtime=%dB sha256=%s codehash=%s sourceFiles=%d fixtureBytes=%d checkpoint=%d gas=%d", len(code), sha, crypto.Keccak256Hash(code), len(doc.SourceHashes), aggregate, len(blob), lc0VerifyOrdinaryGas-call.left)
}

func TestLC0VerifyActualQ1Q7InternalOneAndOneCallChains(t *testing.T) {
	e := lc0VerifyNewEnv(t)
	defer e.close()
	for _, f := range lc0VerifyFixtures {
		t.Run(f.name, func(t *testing.T) {
			one := lc0VerifyRunChain(t, e, f, f.name+"-onecall", 4096, 4096)
			q7 := lc0VerifyRunChain(t, e, f, f.name+"-q7", 7, 4096)
			q1 := lc0VerifyRunChain(t, e, f, f.name+"-q1", 1, 4096)
			internal := lc0VerifyRunChain(t, e, f, f.name+"-internal1", 4096, 1)
			for name, r := range map[string]lc0VerifyRun{"q7": q7, "q1": q1, "internal1": internal} {
				if lc0VerifyMachineRoot(r.slice) != lc0VerifyMachineRoot(one.slice) || r.slice.TotalJvmSteps != one.slice.TotalJvmSteps || r.slice.TotalInternalSteps != one.slice.TotalInternalSteps || r.slice.Result != one.slice.Result {
					t.Fatalf("%s final differs: have=%+v root=%s control=%+v root=%s", name, r.slice, lc0VerifyMachineRoot(r.slice), one.slice, lc0VerifyMachineRoot(one.slice))
				}
			}
			if len(q1.snapshots) <= 1 || len(q7.snapshots) <= 1 {
				t.Fatalf("not actual resume chains q1=%d q7=%d", len(q1.snapshots), len(q7.snapshots))
			}
			for _, r := range []lc0VerifyRun{one, q7, q1, internal} {
				for i, cp := range r.snapshots {
					if cp.Machine.TotalJvm > 4096 || len(cp.Machine.Frames) > 128 || len(cp.Bytes) > lc0VerifyMaxBlob {
						t.Fatalf("snapshot %d bounds", i)
					}
					if cp.Machine.Lifecycle == lc0VerifyRunnable && len(cp.Machine.Frames) == 0 {
						t.Fatalf("runnable empty frames at epoch %d", cp.Epoch)
					}
					if cp.Machine.PendingActive == 0 && (cp.Machine.PendingKind != 0 || cp.Machine.PendingRef != 0 || cp.Machine.PendingPC.Sign() != 0) {
						t.Fatalf("inactive pending nonzero epoch %d", cp.Epoch)
					}
				}
			}
			t.Logf("%s result=%d units=%d/%d slices one/q7/q1/internal1=%d/%d/%d/%d roots=%s gas=%d/%d/%d/%d", f.name, one.slice.Result, one.slice.TotalJvmSteps, one.slice.TotalInternalSteps, len(one.snapshots), len(q7.snapshots), len(q1.snapshots), len(internal.snapshots), lc0VerifyMachineRoot(one.slice), one.gas, q7.gas, q1.gas, internal.gas)
		})
	}
}

func TestLC0VerifyLiveFramesHeapAliasesStringsConstructorsAndInitialization(t *testing.T) {
	e := lc0VerifyNewEnv(t)
	defer e.close()
	t.Run("call-frames", func(t *testing.T) {
		call := lc0VerifyRunChain(t, e, lc0VerifyFixtures[0], "inspect-call", 1, 4096)
		depth2, rootSentinel := false, false
		maxWord := new(big.Int).Sub(new(big.Int).Lsh(big.NewInt(1), 256), big.NewInt(1))
		for _, cp := range call.snapshots {
			if len(cp.Machine.Frames) > 0 && cp.Machine.Frames[0].CallPC.Cmp(maxWord) == 0 {
				rootSentinel = true
			}
			if len(cp.Machine.Frames) > 1 {
				depth2 = true
				top := cp.Machine.Frames[len(cp.Machine.Frames)-1]
				if top.PC == 0 && top.Flags&0x10 == 0 {
					t.Fatalf("entered call frame lost at epoch %d", cp.Epoch)
				}
			}
		}
		if !depth2 || !rootSentinel {
			t.Fatalf("q1 call chain depth/root-sentinel evidence=%v/%v", depth2, rootSentinel)
		}
	})

	t.Run("heap-alias-string-constructor", func(t *testing.T) {
		alias := lc0VerifyRunChain(t, e, lc0VerifyFixtures[1], "inspect-alias", 1, 4096)
		seenCtor, seenLinked, seenUninit, seenString, seenCycleOrAlias := false, false, false, false, false
		for _, cp := range alias.snapshots {
			for _, f := range cp.Machine.Frames {
				if f.Flags&0x04 != 0 {
					seenCtor = true
					if f.Flags&0x08 != 0 {
						seenLinked = true
					}
				}
				for _, off := range append(append([]int{}, f.StackOffsets...), f.LocalOffsets...) {
					v := new(big.Int).SetBytes(cp.Bytes[off : off+32])
					kind := new(big.Int).Rsh(new(big.Int).Set(v), 64).Uint64()
					if kind == 3 {
						seenUninit = true
					}
					if kind > 8 {
						t.Fatalf("unknown value kind %d at %d", kind, off)
					}
				}
			}
			refs := map[uint32]int{}
			for _, h := range cp.Machine.Heap {
				if h.Handle == 0 || h.Handle > cp.Machine.NextHandle {
					t.Fatal("heap ordinal")
				}
				for _, off := range h.CellOffsets {
					if h.Object {
						v := new(big.Int).SetBytes(cp.Bytes[off : off+32])
						if new(big.Int).Rsh(new(big.Int).Set(v), 64).Uint64() == 2 {
							refs[uint32(v.Uint64())]++
						}
					} else if h.Metadata.Uint64() >= 0x100 {
						ref := binary.BigEndian.Uint64(cp.Bytes[off : off+8])
						if ref > 0 {
							refs[uint32(ref)]++
						}
					}
				}
			}
			for _, n := range refs {
				if n > 1 {
					seenCycleOrAlias = true
				}
			}
			if len(cp.Machine.InternHandleOffsets) > 0 {
				seenString = true
				lc0VerifyAssertInternedSame(t, cp, len(lc0VerifyFixtures[1].classes), "same")
				stringClass := len(lc0VerifyFixtures[1].classes) + 26
				if stringClass >= len(cp.Machine.InitOffsets) || cp.Bytes[cp.Machine.InitOffsets[stringClass]] != 0 {
					t.Fatalf("canonical String objects must be valid while String class initState is zero")
				}
				for i, off := range cp.Machine.InternHandleOffsets {
					h := binary.BigEndian.Uint32(cp.Bytes[off : off+4])
					if h == 0 || h > cp.Machine.NextHandle {
						t.Fatalf("intern%d handle=%d", i, h)
					}
				}
			}
		}
		if !seenCtor || !seenLinked || !seenUninit || !seenString || !seenCycleOrAlias {
			t.Fatalf("missing constructor/linked/uninit/string/alias evidence=%v/%v/%v/%v/%v", seenCtor, seenLinked, seenUninit, seenString, seenCycleOrAlias)
		}
	})

	t.Run("pending-fault-and-initialization", func(t *testing.T) {
		f := lc0VerifyFixtures[2]
		raw := lc0VerifyBundle(t, f)
		id := lc0VerifyInstance("pending-q10")
		s, blob, c := e.start(lc0VerifyOwner, id, raw, f.entry, "run", nil, 1, 1, lc0VerifyOrdinaryGas)
		lc0VerifyAssertSuccess(t, s, blob, c)
		var pending lc0VerifyCheckpoint
		seenInitContinuation, seenState2Continuation := false, false
		for n := 0; n < 128; n++ {
			cp, err := lc0VerifyDecodeCheckpoint(blob)
			if err != nil {
				t.Fatal(err)
			}
			for _, frame := range cp.Machine.Frames {
				if frame.Flags&0x02 != 0 {
					seenInitContinuation = true
					for _, initOff := range cp.Machine.InitOffsets {
						if cp.Bytes[initOff] == 2 {
							seenState2Continuation = true
							break
						}
					}
				}
			}
			if cp.Machine.PendingActive == 1 {
				pending = cp
				break
			}
			if s.Lifecycle != lc0VerifyRunnable {
				t.Fatal("terminated before pending idiv boundary")
			}
			s, blob, c = e.resume(lc0VerifyOwner, id, s.Epoch, lc0VerifySliceRoot(s), raw, blob, 1, 1, lc0VerifyOrdinaryGas)
			lc0VerifyAssertSuccess(t, s, blob, c)
		}
		if pending.Bytes == nil || pending.Machine.PendingKind != 1 || pending.Machine.PendingRef == 0 || pending.Machine.PendingPC.Uint64() != 15 || !seenInitContinuation {
			t.Fatalf("missing init continuation or exact q10-equivalent pending ref/PC: continuation=%v pending=%+v", seenInitContinuation, pending.Machine)
		}
		top := pending.Machine.Frames[len(pending.Machine.Frames)-1]
		if top.PC != 16 {
			t.Fatalf("faulting idiv was not already advanced: nextPC=%d", top.PC)
		}
		beforeJvm, beforeRef, beforeHandle := pending.Machine.TotalJvm, pending.Machine.PendingRef, pending.Machine.NextHandle
		s, blob, c = e.resume(lc0VerifyOwner, id, pending.Epoch, crypto.Keccak256Hash(pending.Bytes), raw, pending.Bytes, 1, 1, lc0VerifyOrdinaryGas)
		lc0VerifyAssertSuccess(t, s, blob, c)
		after, err := lc0VerifyDecodeCheckpoint(blob)
		if err != nil {
			t.Fatal(err)
		}
		if after.Machine.TotalJvm != beforeJvm || after.Machine.TotalInternal != pending.Machine.TotalInternal+1 || after.Machine.NextHandle != beforeHandle {
			t.Fatalf("resume repeated opcode/allocation: before=%d/%d/%d after=%d/%d/%d", beforeJvm, pending.Machine.TotalInternal, beforeHandle, after.Machine.TotalJvm, after.Machine.TotalInternal, after.Machine.NextHandle)
		}
		if after.Machine.PendingActive != 0 && after.Machine.PendingRef != beforeRef {
			t.Fatal("pending unwind changed exception identity")
		}
		handlerSameRef := after.Machine.PendingActive != 0
		for _, frame := range after.Machine.Frames {
			for _, off := range frame.StackOffsets {
				v := new(big.Int).SetBytes(after.Bytes[off : off+32])
				if new(big.Int).Rsh(new(big.Int).Set(v), 64).Uint64() == 2 && uint32(v.Uint64()) == beforeRef {
					handlerSameRef = true
				}
			}
		}
		if !handlerSameRef {
			t.Fatal("handler entry did not retain the pending exception reference")
		}
		for s.Lifecycle == lc0VerifyRunnable {
			current, decodeErr := lc0VerifyDecodeCheckpoint(blob)
			if decodeErr != nil {
				t.Fatal(decodeErr)
			}
			for _, frame := range current.Machine.Frames {
				if frame.Flags&0x02 != 0 {
					for _, initOff := range current.Machine.InitOffsets {
						if current.Bytes[initOff] == 2 {
							seenState2Continuation = true
							break
						}
					}
				}
			}
			s, blob, c = e.resume(lc0VerifyOwner, id, s.Epoch, lc0VerifySliceRoot(s), raw, blob, 1, 1, lc0VerifyOrdinaryGas)
			lc0VerifyAssertSuccess(t, s, blob, c)
		}
		terminal, err := lc0VerifyDecodeCheckpoint(blob)
		if err != nil {
			t.Fatal(err)
		}
		staticInts := make([]int32, 0, len(terminal.Machine.StaticValueOffsets[0]))
		for _, off := range terminal.Machine.StaticValueOffsets[0] {
			v := new(big.Int).SetBytes(terminal.Bytes[off : off+32])
			if new(big.Int).Rsh(new(big.Int).Set(v), 64).Uint64() != 1 {
				t.Fatalf("init static is not int: %x", v)
			}
			staticInts = append(staticInts, int32(uint32(v.Uint64())))
		}
		if s.Lifecycle != lc0VerifyReturned || s.Result != 10 || !seenState2Continuation || terminal.Bytes[terminal.Machine.InitOffsets[0]] != 2 || !reflect.DeepEqual(staticInts, []int32{1, 9}) || terminal.Machine.NextHandle != beforeHandle || terminal.Machine.ExceptionObjects != 1 {
			t.Fatalf("fault/init repeated or wrong terminal: slice=%+v state2Continuation=%v init=%d statics=%v next=%d/%d exceptions=%d", s, seenState2Continuation, terminal.Bytes[terminal.Machine.InitOffsets[0]], staticInts, terminal.Machine.NextHandle, beforeHandle, terminal.Machine.ExceptionObjects)
		}
	})
}

func lc0VerifyValidateOK(t *testing.T, e *lc0VerifyEnv, raw [][]byte, blob []byte) common.Hash {
	t.Helper()
	c := lc0VerifyValidate(e, raw, blob, lc0VerifyBoundaryGas)
	if c.err != nil {
		t.Fatalf("validate valid checkpoint: %v data=%x", c.err, c.output)
	}
	v, err := e.contract.Methods["validateCheckpoint"].Outputs.Unpack(c.output)
	if err != nil || len(v) != 1 {
		t.Fatalf("validate decode: %v/%d", err, len(v))
	}
	return common.Hash(v[0].([32]byte))
}
func lc0VerifyMutateRehash(t *testing.T, blob []byte, at int, set func([]byte)) []byte {
	t.Helper()
	original, err := lc0VerifyDecodeCheckpoint(blob)
	if err != nil {
		t.Fatal(err)
	}
	out := append([]byte(nil), blob...)
	if at < 216 || at >= len(out) {
		t.Fatalf("mutation offset=%d size=%d", at, len(out))
	}
	set(out[at:])
	root := lc0VerifyMachineStateRoot(t, original, out[216:])
	copy(out[180:212], root[:])
	return out
}

func TestLC0VerifyStandaloneCanonicalValidationAndAnchoredProvenance(t *testing.T) {
	e := lc0VerifyNewEnv(t)
	defer e.close()
	f := lc0VerifyFixtures[1]
	raw := lc0VerifyBundle(t, f)
	id := lc0VerifyInstance("validation")
	s, blob, call := e.start(lc0VerifyOwner, id, raw, f.entry, "run", nil, 7, 4096, lc0VerifyOrdinaryGas)
	lc0VerifyAssertSuccess(t, s, blob, call)
	cp, err := lc0VerifyDecodeCheckpoint(blob)
	if err != nil {
		t.Fatal(err)
	}
	if got := lc0VerifyValidateOK(t, e, raw, blob); got != cp.MachineRoot {
		t.Fatalf("validate root=%s want=%s", got, cp.MachineRoot)
	}
	before := e.head(id)
	// validateCheckpoint checks well-formedness, not EVM provenance. Parent links
	// are history-only and are intentionally outside machineStateRoot.
	altered := append([]byte(nil), blob...)
	altered[83] ^= 1
	if got := lc0VerifyValidateOK(t, e, raw, altered); got != cp.MachineRoot {
		t.Fatal("history-only alteration changed machine root")
	}
	_, _, badResume := e.resume(lc0VerifyOwner, id, s.Epoch, lc0VerifySliceRoot(s), raw, altered, 1, 1, lc0VerifyOrdinaryGas)
	lc0VerifyAssertControl(t, badResume, 4)
	lc0VerifyAssertHeadEqual(t, e.head(id), before)
	alteredInstance := append([]byte(nil), blob...)
	alteredInstance[43] ^= 1
	lc0VerifyValidateOK(t, e, raw, alteredInstance) // well formed, but not this anchored instance
	_, _, badResume = e.resume(lc0VerifyOwner, id, s.Epoch, lc0VerifySliceRoot(s), raw, alteredInstance, 1, 1, lc0VerifyOrdinaryGas)
	lc0VerifyAssertControl(t, badResume, 4)
	lc0VerifyAssertHeadEqual(t, e.head(id), before)

	tests := []struct {
		name   string
		blob   []byte
		code   uint64
		offset *uint64
	}{
		{"empty", nil, 1, nil},
		{"short-header", blob[:100], 1, nil},
		{"truncated", blob[:len(blob)-1], 2, nil},
		{"trailing", append(append([]byte(nil), blob...), 0), 2, nil},
	}
	magic := append([]byte(nil), blob...)
	magic[0] ^= 1
	tests = append(tests, struct {
		name   string
		blob   []byte
		code   uint64
		offset *uint64
	}{"header-magic", magic, 3, nil})
	badSchema := append([]byte(nil), blob...)
	binary.BigEndian.PutUint32(badSchema[8:12], 2)
	tests = append(tests, struct {
		name   string
		blob   []byte
		code   uint64
		offset *uint64
	}{"schema", badSchema, 3, nil})
	badMachineMagic := lc0VerifyMutateRehash(t, blob, 216, func(b []byte) { b[0] ^= 1 })
	tests = append(tests, struct {
		name   string
		blob   []byte
		code   uint64
		offset *uint64
	}{"machine-magic", badMachineMagic, 3, nil})
	badResult := lc0VerifyMutateRehash(t, blob, cp.Machine.ResultOffset, func(b []byte) { binary.BigEndian.PutUint32(b, 1) })
	tests = append(tests, struct {
		name   string
		blob   []byte
		code   uint64
		offset *uint64
	}{"runnable-result", badResult, 7, nil})
	if len(cp.Machine.InitOffsets) > 0 {
		off := uint64(cp.Machine.InitOffsets[0])
		badInit := lc0VerifyMutateRehash(t, blob, int(off), func(b []byte) { b[0] = 4 })
		tests = append(tests, struct {
			name   string
			blob   []byte
			code   uint64
			offset *uint64
		}{"init-enum", badInit, 4, &off})
		started := uint64(cp.Machine.StartedOffsets[0])
		badStarted := lc0VerifyMutateRehash(t, blob, int(started), func(b []byte) { b[0] = 2 })
		tests = append(tests, struct {
			name   string
			blob   []byte
			code   uint64
			offset *uint64
		}{"initializer-started-enum", badStarted, 4, &started})
	}
	for _, indices := range cp.Machine.StaticIndexOffsets {
		if len(indices) > 1 {
			off := uint64(indices[1])
			badOrder := lc0VerifyMutateRehash(t, blob, int(off), func(b []byte) { copy(b[:2], blob[indices[0]:indices[0]+2]) })
			tests = append(tests, struct {
				name   string
				blob   []byte
				code   uint64
				offset *uint64
			}{"static-order", badOrder, 4, &off})
			break
		}
	}
	lifecycle := uint64(cp.Machine.LifecycleOffset)
	badLifecycle := lc0VerifyMutateRehash(t, blob, cp.Machine.LifecycleOffset, func(b []byte) { b[0] = 4 })
	tests = append(tests, struct {
		name   string
		blob   []byte
		code   uint64
		offset *uint64
	}{"lifecycle-enum", badLifecycle, 4, &lifecycle})
	if len(cp.Machine.Frames) > 0 {
		terminalFrameOff := uint64(cp.Machine.FrameCountOffset)
		badTerminalFrames := lc0VerifyMutateRehash(t, blob, cp.Machine.LifecycleOffset, func(b []byte) { b[0] = lc0VerifyReturned })
		tests = append(tests, struct {
			name   string
			blob   []byte
			code   uint64
			offset *uint64
		}{"terminal-active-frames", badTerminalFrames, 4, &terminalFrameOff})
		flagOff := uint64(cp.Machine.Frames[0].FlagsOffset)
		frameOff := uint64(cp.Machine.Frames[0].Offset)
		badFlags := lc0VerifyMutateRehash(t, blob, int(flagOff), func(b []byte) { b[0] |= 0x80 })
		tests = append(tests, struct {
			name   string
			blob   []byte
			code   uint64
			offset *uint64
		}{"frame-reserved", badFlags, 5, &frameOff})
		pcOff := uint64(cp.Machine.Frames[0].Offset + 4)
		badPC := lc0VerifyMutateRehash(t, blob, int(pcOff), func(b []byte) { binary.BigEndian.PutUint32(b, 0xffffffff) })
		tests = append(tests, struct {
			name   string
			blob   []byte
			code   uint64
			offset *uint64
		}{"frame-pc", badPC, 5, &pcOff})
		var valueOff int
		if len(cp.Machine.Frames[len(cp.Machine.Frames)-1].StackOffsets) > 0 {
			valueOff = cp.Machine.Frames[len(cp.Machine.Frames)-1].StackOffsets[0]
		} else if len(cp.Machine.Frames[0].LocalOffsets) > 0 {
			valueOff = cp.Machine.Frames[0].LocalOffsets[0]
		}
		if fr := cp.Machine.Frames[0]; fr.Locals%8 != 0 && fr.Locals != 0 {
			off := uint64(fr.BitmapOffset + int(fr.Locals/8))
			badBitmap := lc0VerifyMutateRehash(t, blob, int(off), func(b []byte) { b[0] |= 0x80 })
			tests = append(tests, struct {
				name   string
				blob   []byte
				code   uint64
				offset *uint64
			}{"locals-unused-bitmap", badBitmap, 5, &off})
		}
		if valueOff > 0 {
			off := uint64(valueOff)
			badTag := lc0VerifyMutateRehash(t, blob, valueOff, func(b []byte) {
				for i := range b[:32] {
					b[i] = 0
				}
				b[23] = 9
			})
			tests = append(tests, struct {
				name   string
				blob   []byte
				code   uint64
				offset *uint64
			}{"value-tag", badTag, 5, &off})
		}
	}
	if len(cp.Machine.Heap) > 0 {
		h := cp.Machine.Heap[0]
		off := uint64(h.HandleOffset)
		badOrdinal := lc0VerifyMutateRehash(t, blob, h.HandleOffset, func(b []byte) { binary.BigEndian.PutUint32(b, 2) })
		tests = append(tests, struct {
			name   string
			blob   []byte
			code   uint64
			offset *uint64
		}{"heap-ordinal", badOrdinal, 6, &off})
		rankOff := uint64(h.RankOffset)
		heapRecordOff := uint64(h.Offset)
		badRank := lc0VerifyMutateRehash(t, blob, int(rankOff), func(b []byte) { b[0] = 0xff })
		tests = append(tests, struct {
			name   string
			blob   []byte
			code   uint64
			offset *uint64
		}{"heap-rank", badRank, 6, &heapRecordOff})
		counterOff := uint64(cp.Machine.HeapHeaderOffset + 4)
		badCounter := lc0VerifyMutateRehash(t, blob, int(counterOff), func(b []byte) { binary.BigEndian.PutUint16(b, 0xffff) })
		heapHeaderOff := uint64(cp.Machine.HeapHeaderOffset)
		tests = append(tests, struct {
			name   string
			blob   []byte
			code   uint64
			offset *uint64
		}{"heap-counter", badCounter, 6, &heapHeaderOff})
	}
	pendingOff := uint64(cp.Machine.PendingOffset)
	badPendingEnum := lc0VerifyMutateRehash(t, blob, int(pendingOff), func(b []byte) { b[0] = 2 })
	tests = append(tests, struct {
		name   string
		blob   []byte
		code   uint64
		offset *uint64
	}{"pending-enum", badPendingEnum, 4, &pendingOff})
	if cp.Machine.PendingActive == 0 {
		kindOff := uint64(cp.Machine.PendingKindOffset)
		pendingStart := uint64(cp.Machine.PendingOffset)
		badInactive := lc0VerifyMutateRehash(t, blob, int(kindOff), func(b []byte) { b[0] = 1 })
		tests = append(tests, struct {
			name   string
			blob   []byte
			code   uint64
			offset *uint64
		}{"inactive-pending", badInactive, 7, &pendingStart})
	}
	if len(cp.Machine.InternHandleOffsets) > 0 {
		off := uint64(cp.Machine.InternHashOffsets[0])
		badHash := lc0VerifyMutateRehash(t, blob, int(off), func(b []byte) { b[3] ^= 1 })
		zero := uint64(0)
		tests = append(tests, struct {
			name   string
			blob   []byte
			code   uint64
			offset *uint64
		}{"intern-hash", badHash, 7, &zero})
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			c := lc0VerifyValidate(e, raw, tc.blob, lc0VerifyBoundaryGas)
			if tc.offset == nil {
				lc0VerifyAssertState(t, c, tc.code)
			} else {
				lc0VerifyAssertState(t, c, tc.code, *tc.offset)
			}
			lc0VerifyAssertHeadEqual(t, e.head(id), before)
		})
	}

	// Every TEST-rehashed malformed state is a different byte hash and cannot be
	// resumed even if a future validator diagnostic is made more permissive.
	for _, tc := range tests {
		if len(tc.blob) == len(blob) && !bytes.Equal(tc.blob, blob) {
			_, _, c := e.resume(lc0VerifyOwner, id, s.Epoch, lc0VerifySliceRoot(s), raw, tc.blob, 1, 1, lc0VerifyOrdinaryGas)
			lc0VerifyAssertControl(t, c, 4)
			lc0VerifyAssertHeadEqual(t, e.head(id), before)
		}
	}
}

func TestLC0VerifyOwnerEpochHeadCASRawBindingFailuresAndRetry(t *testing.T) {
	e := lc0VerifyNewEnv(t)
	defer e.close()
	f := lc0VerifyFixtures[0]
	raw := lc0VerifyBundle(t, f)
	zero := common.Hash{}
	_, _, c := e.start(lc0VerifyOwner, zero, raw, f.entry, "run", f.args, 1, 1, lc0VerifyOrdinaryGas)
	lc0VerifyAssertControl(t, c, 1)
	id := lc0VerifyInstance("cas")
	_, _, c = e.start(common.Address{}, id, raw, f.entry, "run", f.args, 1, 1, lc0VerifyOrdinaryGas)
	lc0VerifyAssertControl(t, c, 2)
	if e.head(id) != (lc0VerifyHead{}) {
		t.Fatal("failed starts registered a head")
	}
	_, _, c = e.start(lc0VerifyOwner, id, raw, f.entry, "run", f.args, 0, 1, lc0VerifyOrdinaryGas)
	lc0VerifyAssertControl(t, c, 6)
	s, blob, c := e.start(lc0VerifyOwner, id, raw, f.entry, "run", f.args, 1, 4096, lc0VerifyOrdinaryGas)
	lc0VerifyAssertSuccess(t, s, blob, c)
	before := e.head(id)
	_, _, c = e.start(lc0VerifyOwner, id, raw, f.entry, "run", f.args, 1, 1, lc0VerifyOrdinaryGas)
	lc0VerifyAssertControl(t, c, 1)
	unknown := lc0VerifyInstance("cas-unknown")
	_, _, c = e.resume(lc0VerifyOwner, unknown, 1, lc0VerifySliceRoot(s), raw, blob, 1, 1, lc0VerifyOrdinaryGas)
	lc0VerifyAssertControl(t, c, 1)
	// EXTCODEHASH is checked against the committed anchor before checkpoint
	// execution. Appending unreachable STOP is sufficient to change code identity.
	e.state.SetCode(lc0VerifyAt, append(append([]byte(nil), e.code...), 0), tracing.CodeChangeUnspecified)
	_, _, changedCode := e.resume(lc0VerifyOwner, id, s.Epoch, lc0VerifySliceRoot(s), raw, blob, 1, 1, lc0VerifyOrdinaryGas)
	lc0VerifyAssertControl(t, changedCode, 5)
	e.state.SetCode(lc0VerifyAt, e.code, tracing.CodeChangeUnspecified)
	lc0VerifyAssertHeadEqual(t, e.head(id), before)
	for _, tc := range []struct {
		name       string
		owner      common.Address
		epoch      uint64
		root       common.Hash
		classes    [][]byte
		checkpoint []byte
		code       uint64
	}{
		{"owner", lc0VerifyOther, s.Epoch, lc0VerifySliceRoot(s), raw, blob, 2},
		{"epoch", lc0VerifyOwner, s.Epoch + 1, lc0VerifySliceRoot(s), raw, blob, 3},
		{"expected-root", lc0VerifyOwner, s.Epoch, crypto.Keccak256Hash([]byte("wrong")), raw, blob, 4},
		{"bad-blob", lc0VerifyOwner, s.Epoch, lc0VerifySliceRoot(s), raw, append(append([]byte(nil), blob...), 0), 4},
		{"raw-byte", lc0VerifyOwner, s.Epoch, lc0VerifySliceRoot(s), [][]byte{append(append([]byte(nil), raw[0]...), 0)}, blob, 5},
	} {
		t.Run(tc.name, func(t *testing.T) {
			_, _, got := e.resume(tc.owner, id, tc.epoch, tc.root, tc.classes, tc.checkpoint, 1, 1, lc0VerifyOrdinaryGas)
			lc0VerifyAssertControl(t, got, tc.code)
			lc0VerifyAssertHeadEqual(t, e.head(id), before)
		})
	}

	// Snapshot a normal child, rewind it, force reserve and genuine OOG failures,
	// then prove an ordinary retry yields the byte-identical control child.
	snap := e.state.Snapshot()
	control, controlBlob, controlCall := e.resume(lc0VerifyOwner, id, s.Epoch, lc0VerifySliceRoot(s), raw, blob, 1, 4096, lc0VerifyOrdinaryGas)
	lc0VerifyAssertSuccess(t, control, controlBlob, controlCall)
	e.state.RevertToSnapshot(snap)
	lc0VerifyAssertHeadEqual(t, e.head(id), before)
	_, _, reserve := e.resume(lc0VerifyOwner, id, s.Epoch, lc0VerifySliceRoot(s), raw, blob, 1, 4096, lc0VerifyReserveGas+500_000)
	lc0VerifyAssertControl(t, reserve, 7)
	lc0VerifyAssertHeadEqual(t, e.head(id), before)
	_, _, oog := e.resume(lc0VerifyOwner, id, s.Epoch, lc0VerifySliceRoot(s), raw, blob, 1, 4096, 1)
	if !errors.Is(oog.err, vm.ErrOutOfGas) || len(oog.output) != 0 || len(oog.logs) != 0 {
		t.Fatalf("genuine OOG mislabeled: err=%v data=%x logs=%d", oog.err, oog.output, len(oog.logs))
	}
	lc0VerifyAssertHeadEqual(t, e.head(id), before)
	retry, retryBlob, retryCall := e.resume(lc0VerifyOwner, id, s.Epoch, lc0VerifySliceRoot(s), raw, blob, 1, 4096, lc0VerifyOrdinaryGas)
	lc0VerifyAssertSuccess(t, retry, retryBlob, retryCall)
	if !reflect.DeepEqual(retry, control) || !bytes.Equal(retryBlob, controlBlob) {
		t.Fatalf("normal retry differs from control\nretry=%+v %x\ncontrol=%+v %x", retry, crypto.Keccak256Hash(retryBlob), control, crypto.Keccak256Hash(controlBlob))
	}
	for retry.Lifecycle == lc0VerifyRunnable {
		retry, retryBlob, retryCall = e.resume(lc0VerifyOwner, id, retry.Epoch, lc0VerifySliceRoot(retry), raw, retryBlob, 4096, 4096, lc0VerifyOrdinaryGas)
		lc0VerifyAssertSuccess(t, retry, retryBlob, retryCall)
	}
	terminal := e.head(id)
	_, _, terminalCall := e.resume(lc0VerifyOwner, id, retry.Epoch, lc0VerifySliceRoot(retry), raw, retryBlob, 1, 1, lc0VerifyOrdinaryGas)
	lc0VerifyAssertControl(t, terminalCall, 1)
	lc0VerifyAssertHeadEqual(t, e.head(id), terminal)

	// Ordered raw bytes are part of artifactRoot. Reversal is not a classpath set.
	af := lc0VerifyFixtures[1]
	araw := lc0VerifyBundle(t, af)
	aid := lc0VerifyInstance("raw-order")
	as, ablob, ac := e.start(lc0VerifyOwner, aid, araw, af.entry, "run", nil, 1, 4096, lc0VerifyOrdinaryGas)
	lc0VerifyAssertSuccess(t, as, ablob, ac)
	reversed := [][]byte{araw[1], araw[0]}
	_, _, ac = e.resume(lc0VerifyOwner, aid, as.Epoch, lc0VerifySliceRoot(as), reversed, ablob, 1, 1, lc0VerifyOrdinaryGas)
	lc0VerifyAssertControl(t, ac, 5)
}

func TestLC0VerifyPrivateSpecialCategory2NegativeAndKnownUncaught(t *testing.T) {
	source := `public final class LC0Supplement {
 private long twice(long x){ return x+x; }
 private int special(int x){ return (int)twice(x); }
 public static int run(int x){ return new LC0Supplement().special(x)-7; }
 public static int fault(int x){ return 1/x; }
}`
	raw := lc0VerifyCompileTrusted(t, map[string]string{"LC0Supplement.java": source}, []string{"LC0Supplement"})["LC0Supplement"]
	e := lc0VerifyNewEnv(t)
	defer e.close()
	f := lc0VerifyFixture{"supplement", "LC0Supplement", []string{"LC0Supplement"}, []int32{-4}, -15}
	// Use the generated bytes directly rather than the frozen fixture loader.
	id := lc0VerifyInstance("supplement")
	s, blob, c := e.start(lc0VerifyOwner, id, [][]byte{raw}, f.entry, "run", f.args, 1, 4096, lc0VerifyOrdinaryGas)
	lc0VerifyAssertSuccess(t, s, blob, c)
	seenPrivate, seenLong := false, false
	for s.Lifecycle == lc0VerifyRunnable {
		cp, err := lc0VerifyDecodeCheckpoint(blob)
		if err != nil {
			t.Fatal(err)
		}
		for _, fr := range cp.Machine.Frames {
			if len(cp.Machine.Frames) > 1 && fr.Flags&0x04 == 0 {
				seenPrivate = true
			}
			for _, off := range fr.LocalOffsets {
				v := new(big.Int).SetBytes(cp.Bytes[off : off+32])
				kind := new(big.Int).Rsh(v, 64).Uint64()
				if kind == 4 || kind == 5 {
					seenLong = true
				}
			}
		}
		s, blob, c = e.resume(lc0VerifyOwner, id, s.Epoch, lc0VerifySliceRoot(s), [][]byte{raw}, blob, 1, 4096, lc0VerifyOrdinaryGas)
		lc0VerifyAssertSuccess(t, s, blob, c)
	}
	if s.Lifecycle != lc0VerifyReturned || s.Result != -15 || !seenPrivate || !seenLong {
		t.Fatalf("private/category2/negative result=%+v evidence=%v/%v", s, seenPrivate, seenLong)
	}
	faultID := lc0VerifyInstance("known-uncaught")
	fs, fb, fc := e.start(lc0VerifyOwner, faultID, [][]byte{raw}, "LC0Supplement", "fault", []int32{0}, 1, 1, lc0VerifyOrdinaryGas)
	lc0VerifyAssertSuccess(t, fs, fb, fc)
	for fs.Lifecycle == lc0VerifyRunnable {
		fs, fb, fc = e.resume(lc0VerifyOwner, faultID, fs.Epoch, lc0VerifySliceRoot(fs), [][]byte{raw}, fb, 1, 1, lc0VerifyOrdinaryGas)
		lc0VerifyAssertSuccess(t, fs, fb, fc)
	}
	cp, err := lc0VerifyDecodeCheckpoint(fb)
	if err != nil {
		t.Fatal(err)
	}
	if fs.Lifecycle != lc0VerifyUncaught || fs.Result != 0 || fs.JavaKind != 1 || fs.JavaRef == 0 || len(cp.Machine.Frames) != 0 || cp.Machine.PendingActive != 1 || cp.Machine.PendingKind != 1 || cp.Machine.PendingRef != fs.JavaRef {
		t.Fatalf("uncaught arithmetic not structured/canonical: slice=%+v machine=%+v", fs, cp.Machine)
	}
}

func lc0VerifyCompileTrusted(t *testing.T, sources map[string]string, names []string) map[string][]byte {
	t.Helper()
	dir := t.TempDir()
	rels := make([]string, 0, len(sources))
	for rel := range sources {
		rels = append(rels, rel)
	}
	sort.Strings(rels)
	args := []string{"-J-Xmx96m", "--release", "8", "-g:none", "-d", dir}
	for _, rel := range rels {
		path := filepath.Join(dir, filepath.FromSlash(rel))
		if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(sources[rel]), 0600); err != nil {
			t.Fatal(err)
		}
		args = append(args, path)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	output, err := exec.CommandContext(ctx, "javac", args...).CombinedOutput()
	if err != nil {
		t.Fatalf("trusted javac --release 8: %v\n%s", err, output)
	}
	out := make(map[string][]byte)
	for _, name := range names {
		b, err := os.ReadFile(filepath.Join(dir, filepath.FromSlash(name+".class")))
		if err != nil {
			t.Fatal(err)
		}
		out[name] = b
	}
	return out
}

func TestLC0VerifyFrozenJava8Java21AndAcceptedMonolithOracles(t *testing.T) {
	dir := t.TempDir()
	for name := range lc0VerifySources {
		raw := lc0VerifyReadClass(t, name)
		if err := os.WriteFile(filepath.Join(dir, name+".class"), raw, 0600); err != nil {
			t.Fatal(err)
		}
	}
	oracle := `public final class LC0VerifierOracle { public static void main(String[] a) throws Exception { Class<?> c=Class.forName(a[0]); if(a[0].equals("LC0CallLoop")) System.out.print(c.getMethod("run",int.class).invoke(null,Integer.valueOf(5))); else System.out.print(c.getMethod("run").invoke(null)); } }`
	if err := os.WriteFile(filepath.Join(dir, "LC0VerifierOracle.java"), []byte(oracle), 0600); err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	output, err := exec.CommandContext(ctx, "javac", "-J-Xmx64m", "--release", "8", "-g:none", "-cp", dir, "-d", dir, filepath.Join(dir, "LC0VerifierOracle.java")).CombinedOutput()
	cancel()
	if err != nil {
		t.Fatalf("compile host-only oracle: %v\n%s", err, output)
	}
	java8 := "/usr/lib/jvm/java-8-openjdk/bin/java"
	if home := os.Getenv("JAVA8_HOME"); home != "" {
		java8 = filepath.Join(home, "bin", "java")
	}
	java21 := "/usr/lib/jvm/jdk-21.0.9/bin/java"
	if home := os.Getenv("JAVA21_HOME"); home != "" {
		java21 = filepath.Join(home, "bin", "java")
	}
	for _, f := range lc0VerifyFixtures {
		for _, j := range []struct{ name, path string }{{"java8", java8}, {"java21", java21}} {
			t.Run(f.name+"/"+j.name, func(t *testing.T) {
				if _, err := os.Stat(j.path); err != nil {
					t.Fatalf("required oracle %s: %v", j.path, err)
				}
				ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
				defer cancel()
				out, err := exec.CommandContext(ctx, j.path, "-Xmx64m", "-Xss512k", "-Xverify:all", "-cp", dir, "LC0VerifierOracle", f.entry).CombinedOutput()
				if err != nil || strings.TrimSpace(string(out)) != fmt.Sprint(f.want) {
					t.Fatalf("oracle=%q err=%v want=%d", out, err, f.want)
				}
			})
		}
		r, err := jvmevm.RunClasses(lc0VerifyBundle(t, f), f.entry, "run", f.args, lc0VerifyOrdinaryGas)
		if err != nil || r.ExceptionClass != "" || r.Value != f.want {
			t.Fatalf("accepted monolith %s=%+v/%v", f.name, r, err)
		}
	}
}

// The subprocess path is intentionally narrow: it can only reopen an already
// created LC0 directory and continue an opaque checkpoint through Session APIs.
type lc0VerifyProcessResult struct {
	Slice            SliceResult
	CheckpointRoot   common.Hash
	CheckpointSHA256 string
	Installs         uint64
}

func TestLC0VerifyReopenHelperProcess(t *testing.T) {
	if os.Getenv("LC0_VERIFY_REOPEN_HELPER") != "1" {
		return
	}
	dir := os.Getenv("LC0_VERIFY_DIRECTORY")
	id := common.HexToHash(os.Getenv("LC0_VERIFY_INSTANCE"))
	root := common.HexToHash(os.Getenv("LC0_VERIFY_ROOT"))
	fixtureName := os.Getenv("LC0_VERIFY_FIXTURE")
	var f *lc0VerifyFixture
	for i := range lc0VerifyFixtures {
		if lc0VerifyFixtures[i].name == fixtureName {
			f = &lc0VerifyFixtures[i]
		}
	}
	if f == nil {
		t.Fatal("unknown helper fixture")
	}
	s, err := Open(dir, lc0VerifyOwner)
	if err != nil {
		t.Fatal(err)
	}
	if s.testCodeInstalls != 0 {
		t.Fatalf("reopen installed code %d times", s.testCodeInstalls)
	}
	blob, err := s.ReadCheckpoint(root)
	if err != nil {
		t.Fatal(err)
	}
	head, err := s.Head(id)
	if err != nil {
		t.Fatal(err)
	}
	raw := lc0VerifyBundle(t, *f)
	var result Result
	for n := 0; head.Lifecycle == lc0VerifyRunnable; n++ {
		if n >= 256 {
			t.Fatal("helper slices")
		}
		result, err = s.Resume(id, head.Epoch, head.CheckpointRoot, raw, blob, 7, 1, lc0VerifyOrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
		blob = result.Checkpoint
		head, err = s.Head(id)
		if err != nil {
			t.Fatal(err)
		}
	}
	if err := s.Close(); err != nil {
		t.Fatal(err)
	}
	sum := sha256.Sum256(blob)
	out := lc0VerifyProcessResult{result.Slice, crypto.Keccak256Hash(blob), fmt.Sprintf("%x", sum), s.testCodeInstalls}
	encoded, _ := json.Marshal(out)
	if err := os.WriteFile(os.Getenv("LC0_VERIFY_RESULT"), encoded, 0600); err != nil {
		t.Fatal(err)
	}
}

func TestLC0VerifyDurableStateDBOpaqueBlobAndNewProcessReopen(t *testing.T) {
	for _, fixtureName := range []string{"alias-string", "init-exception"} {
		t.Run(fixtureName, func(t *testing.T) {
			var f lc0VerifyFixture
			for _, x := range lc0VerifyFixtures {
				if x.name == fixtureName {
					f = x
				}
			}
			dir := filepath.Join(t.TempDir(), "store")
			session, err := Open(dir, lc0VerifyOwner)
			if err != nil {
				t.Fatal(err)
			}
			if session.testCodeInstalls != 1 {
				t.Fatalf("fresh install count=%d", session.testCodeInstalls)
			}
			id := lc0VerifyInstance("disk-" + fixtureName)
			raw := lc0VerifyBundle(t, f)
			result, err := session.Start(id, raw, f.entry, "run", f.args, 1, 1, lc0VerifyOrdinaryGas)
			if err != nil {
				t.Fatal(err)
			}
			// Advance alias to a heap-bearing point and init-exception to the exact
			// pending idiv point before crossing the process boundary.
			for n := 0; n < 128; n++ {
				cp, err := lc0VerifyDecodeCheckpoint(result.Checkpoint)
				if err != nil {
					t.Fatal(err)
				}
				ready := fixtureName == "alias-string" && len(cp.Machine.InternHandleOffsets) > 0 && len(cp.Machine.Heap) >= 4 || fixtureName == "init-exception" && cp.Machine.PendingActive == 1
				if ready {
					break
				}
				if result.Slice.Lifecycle != lc0VerifyRunnable {
					t.Fatal("terminal before restart boundary")
				}
				result, err = session.Resume(id, result.Slice.Epoch, result.Slice.CheckpointRoot, raw, result.Checkpoint, 1, 1, lc0VerifyOrdinaryGas)
				if err != nil {
					t.Fatal(err)
				}
			}
			root := result.Slice.CheckpointRoot
			onDisk, err := session.ReadCheckpoint(root)
			if err != nil || !bytes.Equal(onDisk, result.Checkpoint) || crypto.Keccak256Hash(onDisk) != root {
				t.Fatalf("opaque blob persistence: %v", err)
			}
			before, err := session.Head(id)
			if err != nil {
				t.Fatal(err)
			}
			if err = session.Close(); err != nil {
				t.Fatal(err)
			}
			resultPath := filepath.Join(t.TempDir(), "result.json")
			ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
			defer cancel()
			cmd := exec.CommandContext(ctx, os.Args[0], "-test.run=^TestLC0VerifyReopenHelperProcess$", "-test.timeout=125s")
			cmd.Env = append(os.Environ(), "LC0_VERIFY_REOPEN_HELPER=1", "LC0_VERIFY_DIRECTORY="+dir, "LC0_VERIFY_INSTANCE="+id.Hex(), "LC0_VERIFY_ROOT="+root.Hex(), "LC0_VERIFY_FIXTURE="+fixtureName, "LC0_VERIFY_RESULT="+resultPath)
			output, err := cmd.CombinedOutput()
			if err != nil {
				t.Fatalf("new-process reopen: %v\n%s", err, output)
			}
			var child lc0VerifyProcessResult
			encoded, err := os.ReadFile(resultPath)
			if err != nil {
				t.Fatal(err)
			}
			if err = json.Unmarshal(encoded, &child); err != nil {
				t.Fatal(err)
			}
			if child.Slice.Lifecycle != lc0VerifyReturned || child.Slice.Result != f.want || child.Installs != 0 {
				t.Fatalf("child result=%+v", child)
			}
			reopened, err := Open(dir, lc0VerifyOwner)
			if err != nil {
				t.Fatal(err)
			}
			defer reopened.Close()
			if reopened.testCodeInstalls != 0 {
				t.Fatal("parent reopen reinstalled runtime")
			}
			code, err := Runtime()
			if err != nil || !bytes.Equal(reopened.stateDB.GetCode(reopened.contract), code) || reopened.stateDB.GetCodeHash(reopened.contract) != crypto.Keccak256Hash(code) || reopened.stateRoot == types.EmptyRootHash {
				t.Fatalf("reopened trie/code/root invalid: root=%s code=%d err=%v", reopened.stateRoot, len(reopened.stateDB.GetCode(reopened.contract)), err)
			}
			after, err := reopened.Head(id)
			if err != nil {
				t.Fatal(err)
			}
			if after.Epoch <= before.Epoch || after.Lifecycle != lc0VerifyReturned || after.CheckpointRoot != child.CheckpointRoot {
				t.Fatalf("durable head before=%+v after=%+v child=%+v", before, after, child)
			}
			blob, err := reopened.ReadCheckpoint(after.CheckpointRoot)
			if err != nil {
				t.Fatal(err)
			}
			if got := fmt.Sprintf("%x", sha256.Sum256(blob)); got != child.CheckpointSHA256 {
				t.Fatalf("reopened blob sha=%s want=%s", got, child.CheckpointSHA256)
			}
		})
	}
	unrelated := t.TempDir()
	if err := os.WriteFile(filepath.Join(unrelated, "mine.txt"), []byte("preserve"), 0600); err != nil {
		t.Fatal(err)
	}
	if s, err := Open(unrelated, lc0VerifyOwner); err == nil {
		s.Close()
		t.Fatal("Open accepted unrelated nonempty directory")
	}
	if b, err := os.ReadFile(filepath.Join(unrelated, "mine.txt")); err != nil || string(b) != "preserve" {
		t.Fatal("Open damaged unrelated directory")
	}
	if s, err := Open(filepath.Join(t.TempDir(), "zero-owner"), common.Address{}); err == nil {
		s.Close()
		t.Fatal("Open accepted zero origin")
	}
}

func TestLC0VerifyDurableFailureBoundariesReloadOldRoot(t *testing.T) {
	for _, point := range []lc0HarnessFaultPoint{lc0HarnessFaultAfterBlob, lc0HarnessFaultAfterTrie, lc0HarnessFaultBeforeManifest} {
		t.Run(fmt.Sprint(point), func(t *testing.T) {
			dir := filepath.Join(t.TempDir(), "store")
			s, err := Open(dir, lc0VerifyOwner)
			if err != nil {
				t.Fatal(err)
			}
			defer s.Close()
			f := lc0VerifyFixtures[0]
			raw := lc0VerifyBundle(t, f)
			id := lc0VerifyInstance(fmt.Sprintf("fault-%d", point))
			r, err := s.Start(id, raw, f.entry, "run", f.args, 1, 4096, lc0VerifyOrdinaryGas)
			if err != nil {
				t.Fatal(err)
			}
			before, err := s.Head(id)
			if err != nil {
				t.Fatal(err)
			}
			s.testFault = func(got lc0HarnessFaultPoint) error {
				if got == point {
					return errors.New("verifier injected persistence failure")
				}
				return nil
			}
			failed, err := s.Resume(id, r.Slice.Epoch, r.Slice.CheckpointRoot, raw, r.Checkpoint, 1, 4096, lc0VerifyOrdinaryGas)
			if err == nil || len(failed.Logs) != 0 || len(failed.Checkpoint) != 0 || failed.Slice.CheckpointRoot != (common.Hash{}) {
				t.Fatalf("persistence failure exposed child/log: epoch=%d root=%s checkpoint=%d logs=%d err=%v", failed.Slice.Epoch, failed.Slice.CheckpointRoot, len(failed.Checkpoint), len(failed.Logs), err)
			}
			s.testFault = nil
			after, err := s.Head(id)
			if err != nil {
				t.Fatal(err)
			}
			if !reflect.DeepEqual(after, before) {
				t.Fatalf("failure changed in-memory old head before=%+v after=%+v", before, after)
			}
			if err = s.Close(); err != nil {
				t.Fatal(err)
			}
			reopened, err := Open(dir, lc0VerifyOwner)
			if err != nil {
				t.Fatal(err)
			}
			defer reopened.Close()
			durable, err := reopened.Head(id)
			if err != nil {
				t.Fatal(err)
			}
			if !reflect.DeepEqual(durable, before) {
				t.Fatalf("failure changed durable head before=%+v after=%+v", before, durable)
			}
			old, err := reopened.ReadCheckpoint(before.CheckpointRoot)
			if err != nil {
				t.Fatal(err)
			}
			retry, err := reopened.Resume(id, before.Epoch, before.CheckpointRoot, raw, old, 1, 4096, lc0VerifyOrdinaryGas)
			if err != nil {
				t.Fatal(err)
			}
			if retry.Slice.Epoch != before.Epoch+1 {
				t.Fatal("retry did not create one child")
			}
		})
	}
}

func TestLC0VerifyProfileAndCheckpointSizeFailuresAreHardAndAtomic(t *testing.T) {
	e := lc0VerifyNewEnv(t)
	defer e.close()
	base := lc0VerifyReadClass(t, "LC0CallLoop")
	cases := []struct {
		name              string
		raw               [][]byte
		entryClass, entry string
		args              []int32
	}{
		{"zero-classes", nil, "LC0CallLoop", "run", []int32{5}},
		{"five-classes", [][]byte{base, base, base, base, base}, "LC0CallLoop", "run", []int32{5}},
		{"aggregate-over-64KiB", [][]byte{bytes.Repeat([]byte{1}, 65537)}, "X", "run", nil},
		{"entry-class-257", [][]byte{base}, strings.Repeat("x", 257), "run", []int32{5}},
		{"entry-257", [][]byte{base}, "LC0CallLoop", strings.Repeat("x", 257), []int32{5}},
		{"nine-args", [][]byte{base}, "LC0CallLoop", "run", make([]int32, 9)},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			id := lc0VerifyInstance("profile-" + tc.name)
			_, _, c := e.start(lc0VerifyOwner, id, tc.raw, tc.entryClass, tc.entry, tc.args, 1, 1, lc0VerifyBoundaryGas)
			if c.err == nil || len(c.logs) != 0 {
				t.Fatalf("profile failure succeeded/logged: err=%v logs=%d", c.err, len(c.logs))
			}
			if _, _, ok := lc0VerifyStateError(c.output); ok {
				t.Fatalf("raw/profile failure incorrectly became checkpoint State error: %x", c.output)
			}
			if e.head(id) != (lc0VerifyHead{}) {
				t.Fatal("profile failure registered head")
			}
		})
	}
	oversized := make([]byte, lc0VerifyMaxBlob+1)
	copy(oversized, []byte("JVMELC01"))
	c := lc0VerifyValidate(e, [][]byte{base}, oversized, lc0VerifyBoundaryGas)
	lc0VerifyAssertState(t, c, 1, 0)
}

func TestLC0VerifyForwardCycleAliasesAndObjectEscapingFailedInitialization(t *testing.T) {
	sources := map[string]string{
		"Cycle.java":      `public final class Cycle { Cycle next; static Cycle saved; public static int run(){Cycle a=new Cycle();Cycle b=new Cycle();a.next=b;b.next=a;saved=a;return saved.next.next==a?11:0;} }`,
		"Escaped.java":    `public final class Escaped { static Escaped object; static int zero(){return 0;} static {object=new Escaped();int x=1/zero();} static int value(){return 1;} }`,
		"EscapeRoot.java": `public final class EscapeRoot { public static int run(){try{return Escaped.value();}catch(ExceptionInInitializerError expected){return 7;}} }`,
	}
	classes := lc0VerifyCompileTrusted(t, sources, []string{"Cycle", "Escaped", "EscapeRoot"})
	e := lc0VerifyNewEnv(t)
	defer e.close()
	id := lc0VerifyInstance("cycle")
	raw := [][]byte{classes["Cycle"]}
	s, blob, c := e.start(lc0VerifyOwner, id, raw, "Cycle", "run", nil, 1, 4096, lc0VerifyOrdinaryGas)
	lc0VerifyAssertSuccess(t, s, blob, c)
	seenForward, seenCycle := false, false
	for s.Lifecycle == lc0VerifyRunnable {
		cp, err := lc0VerifyDecodeCheckpoint(blob)
		if err != nil {
			t.Fatal(err)
		}
		byHandle := map[uint32]lc0VerifyHeapRecord{}
		for _, h := range cp.Machine.Heap {
			byHandle[h.Handle] = h
		}
		for _, h := range cp.Machine.Heap {
			if !h.Object {
				continue
			}
			for _, off := range h.CellOffsets {
				v := new(big.Int).SetBytes(cp.Bytes[off : off+32])
				if new(big.Int).Rsh(new(big.Int).Set(v), 64).Uint64() != 2 {
					continue
				}
				ref := uint32(v.Uint64())
				if ref > h.Handle {
					seenForward = true
				}
				target, ok := byHandle[ref]
				if ok {
					for _, to := range target.CellOffsets {
						back := new(big.Int).SetBytes(cp.Bytes[to : to+32])
						if new(big.Int).Rsh(new(big.Int).Set(back), 64).Uint64() == 2 && uint32(back.Uint64()) == h.Handle {
							seenCycle = true
						}
					}
				}
			}
		}
		s, blob, c = e.resume(lc0VerifyOwner, id, s.Epoch, lc0VerifySliceRoot(s), raw, blob, 1, 4096, lc0VerifyOrdinaryGas)
		lc0VerifyAssertSuccess(t, s, blob, c)
	}
	if s.Result != 11 || !seenForward || !seenCycle {
		t.Fatalf("cycle result/evidence=%d/%v/%v", s.Result, seenForward, seenCycle)
	}

	eraw := [][]byte{classes["Escaped"], classes["EscapeRoot"]}
	eid := lc0VerifyInstance("escaped-failed-init")
	es, eblob, ec := e.start(lc0VerifyOwner, eid, eraw, "EscapeRoot", "run", nil, 1, 1, lc0VerifyOrdinaryGas)
	lc0VerifyAssertSuccess(t, es, eblob, ec)
	escapedHandle := uint32(0)
	seenErroneous := false
	for n := 0; es.Lifecycle == lc0VerifyRunnable; n++ {
		if n > 128 {
			t.Fatal("failed-init chain")
		}
		cp, err := lc0VerifyDecodeCheckpoint(eblob)
		if err != nil {
			t.Fatal(err)
		}
		if cp.Bytes[cp.Machine.InitOffsets[0]] == 3 {
			seenErroneous = true
		}
		for _, h := range cp.Machine.Heap {
			if h.Object && h.Class == 0 && uint8(h.Metadata.Uint64()) == 0 {
				escapedHandle = h.Handle
			}
		}
		es, eblob, ec = e.resume(lc0VerifyOwner, eid, es.Epoch, lc0VerifySliceRoot(es), eraw, eblob, 1, 1, lc0VerifyOrdinaryGas)
		lc0VerifyAssertSuccess(t, es, eblob, ec)
	}
	terminal, err := lc0VerifyDecodeCheckpoint(eblob)
	if err != nil {
		t.Fatal(err)
	}
	for _, h := range terminal.Machine.Heap {
		if h.Handle == escapedHandle && h.Class == 0 {
			goto escapedRetained
		}
	}
	t.Fatalf("object %d allocated during failed init was discarded", escapedHandle)
escapedRetained:
	if es.Lifecycle != lc0VerifyReturned || es.Result != 7 || !seenErroneous || escapedHandle == 0 {
		t.Fatalf("failed init outcome/evidence slice=%+v erroneous=%v escaped=%d", es, seenErroneous, escapedHandle)
	}
}
