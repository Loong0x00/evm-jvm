// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.
//
// Independent verifier for the frozen LOCAL MC-TL0 continuation profile. The
// decoder in this file is test-only: production Go continues to transport the
// checkpoint as opaque bytes and never evaluates Java state.
package tl0

import (
	"bytes"
	"context"
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
	lc0transport "github.com/ethereum/go-ethereum/jvmevm/localcontinuation/lc0"
)

const (
	tl0VerifyOrdinaryGas = uint64(100_000_000)
	tl0VerifyBoundaryGas = uint64(1_000_000_000)
	tl0VerifyReserveGas  = uint64(25_000_000)
	tl0VerifyMaxBlob     = 1 << 20
	tl0VerifyHeaderSize  = 216

	tl0VerifyRunnable = uint8(1)
	tl0VerifyReturned = uint8(2)
	tl0VerifyUncaught = uint8(3)
)

var (
	tl0VerifyOwner = common.HexToAddress("0x0000000000000000000000000000000000007101")
	tl0VerifyOther = common.HexToAddress("0x0000000000000000000000000000000000007102")
	tl0VerifyAt    = common.HexToAddress("0x004a564d45564d544c3052554e54494d4500000001")
)

type tl0VerifySlice struct {
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
	JavaClass             []byte
}

type tl0VerifyHead struct {
	Owner           common.Address
	Epoch           uint64
	CheckpointRoot  common.Hash
	MachineRoot     common.Hash
	ArtifactRoot    common.Hash
	ConfigRoot      common.Hash
	RuntimeCodeHash common.Hash
	Lifecycle       uint8
}

type tl0VerifyCall struct {
	output []byte
	left   uint64
	err    error
	logs   []*types.Log
}

type tl0VerifyEnv struct {
	t        *testing.T
	state    *state.StateDB
	code     []byte
	contract abi.ABI
	calls    uint64
}

func tl0VerifyNewEnv(t *testing.T) *tl0VerifyEnv {
	t.Helper()
	code, err := Runtime()
	if err != nil {
		t.Fatalf("load TL0 runtime (runtime integration dependency absent): %v", err)
	}
	contract, err := ABI()
	if err != nil {
		t.Fatalf("load TL0 ABI: %v", err)
	}
	st, err := state.New(types.EmptyRootHash, state.NewDatabaseForTesting())
	if err != nil {
		t.Fatal(err)
	}
	st.CreateAccount(tl0VerifyAt)
	st.SetCode(tl0VerifyAt, code, tracing.CodeChangeUnspecified)
	return &tl0VerifyEnv{t: t, state: st, code: code, contract: contract}
}

func (e *tl0VerifyEnv) close() { e.state.Database().TrieDB().Close() }

func (e *tl0VerifyEnv) callAs(owner common.Address, gas uint64, method string, args ...any) tl0VerifyCall {
	e.t.Helper()
	input, err := e.contract.Pack(method, args...)
	if err != nil {
		e.t.Fatalf("pack %s: %v", method, err)
	}
	e.calls++
	txHash := crypto.Keccak256Hash([]byte("TL0 verifier call"), new(big.Int).SetUint64(e.calls).Bytes())
	e.state.SetTxContext(txHash, 0)
	start := time.Now()
	output, left, callErr := runtime.Call(tl0VerifyAt, input, &runtime.Config{
		State: e.state, Origin: owner, GasLimit: gas,
		BlockNumber: big.NewInt(1), Time: 1,
	})
	limit := 30 * time.Second
	if gas > tl0VerifyOrdinaryGas {
		limit = 120 * time.Second
	}
	if elapsed := time.Since(start); elapsed > limit {
		e.t.Fatalf("%s call exceeded LOCAL watchdog: %s > %s", method, elapsed, limit)
	}
	logs := append([]*types.Log(nil), e.state.GetLogs(txHash, 1, common.Hash{}, 1)...)
	return tl0VerifyCall{append([]byte(nil), output...), left, callErr, logs}
}

func (e *tl0VerifyEnv) start(owner common.Address, instance common.Hash, raw [][]byte, entryClass, entry string, args []int32, jvm uint64, internal uint32, gas uint64) (tl0VerifySlice, []byte, tl0VerifyCall) {
	e.t.Helper()
	c := e.callAs(owner, gas, "start", instance, raw, entryClass, entry, args, jvm, internal)
	if c.err != nil {
		return tl0VerifySlice{}, nil, c
	}
	values, err := e.contract.Methods["start"].Outputs.Unpack(c.output)
	if err != nil || len(values) != 2 {
		e.t.Fatalf("decode start outputs=%d: %v (%x)", len(values), err, c.output)
	}
	s := *abi.ConvertType(values[0], new(tl0VerifySlice)).(*tl0VerifySlice)
	return s, append([]byte(nil), values[1].([]byte)...), c
}

func (e *tl0VerifyEnv) resume(owner common.Address, instance common.Hash, epoch uint64, root common.Hash, raw [][]byte, checkpoint []byte, jvm uint64, internal uint32, gas uint64) (tl0VerifySlice, []byte, tl0VerifyCall) {
	e.t.Helper()
	c := e.callAs(owner, gas, "resume", instance, epoch, root, raw, checkpoint, jvm, internal)
	if c.err != nil {
		return tl0VerifySlice{}, nil, c
	}
	values, err := e.contract.Methods["resume"].Outputs.Unpack(c.output)
	if err != nil || len(values) != 2 {
		e.t.Fatalf("decode resume outputs=%d: %v (%x)", len(values), err, c.output)
	}
	s := *abi.ConvertType(values[0], new(tl0VerifySlice)).(*tl0VerifySlice)
	return s, append([]byte(nil), values[1].([]byte)...), c
}

func (e *tl0VerifyEnv) head(instance common.Hash) tl0VerifyHead {
	e.t.Helper()
	c := e.callAs(tl0VerifyOwner, tl0VerifyOrdinaryGas, "head", instance)
	if c.err != nil {
		e.t.Fatalf("head: %v data=%x", c.err, c.output)
	}
	v, err := e.contract.Methods["head"].Outputs.Unpack(c.output)
	if err != nil || len(v) != 8 {
		e.t.Fatalf("decode head: %v values=%d", err, len(v))
	}
	return tl0VerifyHead{v[0].(common.Address), v[1].(uint64), common.Hash(v[2].([32]byte)), common.Hash(v[3].([32]byte)), common.Hash(v[4].([32]byte)), common.Hash(v[5].([32]byte)), common.Hash(v[6].([32]byte)), v[7].(uint8)}
}

func tl0VerifySliceRoot(s tl0VerifySlice) common.Hash   { return common.Hash(s.CheckpointRoot) }
func tl0VerifyMachineRoot(s tl0VerifySlice) common.Hash { return common.Hash(s.MachineStateRoot) }

func tl0VerifyAssertSuccess(t *testing.T, s tl0VerifySlice, checkpoint []byte, c tl0VerifyCall) {
	t.Helper()
	if c.err != nil || len(c.logs) != 1 {
		t.Fatalf("successful slice err=%v data=%x left=%d logs=%d", c.err, c.output, c.left, len(c.logs))
	}
	if s.Schema != 1 || s.Epoch == 0 || s.Lifecycle < tl0VerifyRunnable || s.Lifecycle > tl0VerifyUncaught || len(checkpoint) < tl0VerifyHeaderSize || len(checkpoint) > tl0VerifyMaxBlob {
		t.Fatalf("noncanonical slice=%+v checkpoint=%d", s, len(checkpoint))
	}
	if crypto.Keccak256Hash(checkpoint) != tl0VerifySliceRoot(s) {
		t.Fatal("checkpointRoot is not keccak(exact checkpoint)")
	}
	if s.Lifecycle == tl0VerifyRunnable && (s.Result != 0 || s.JavaKind != 0 || s.JavaRef != 0 || len(s.JavaClass) != 0) {
		t.Fatalf("RUNNABLE leaked terminal output: %+v", s)
	}
	if s.Lifecycle == tl0VerifyReturned && (s.JavaKind != 0 || s.JavaRef != 0 || len(s.JavaClass) != 0) {
		t.Fatalf("RETURNED has Java exception output: %+v", s)
	}
	if s.Lifecycle == tl0VerifyUncaught && (s.Result != 0 || s.JavaRef == 0 || (s.JavaKind == 0) == (len(s.JavaClass) == 0)) {
		t.Fatalf("UNCAUGHT outcome shape is not canonical: %+v", s)
	}
}

func tl0VerifyCustomError(signature string, words ...uint64) []byte {
	out := append([]byte(nil), crypto.Keccak256([]byte(signature))[:4]...)
	for _, value := range words {
		var word [32]byte
		binary.BigEndian.PutUint64(word[24:], value)
		out = append(out, word[:]...)
	}
	return out
}

func tl0VerifyAssertControl(t *testing.T, c tl0VerifyCall, code uint64) {
	t.Helper()
	if !errors.Is(c.err, vm.ErrExecutionReverted) || !bytes.Equal(c.output, tl0VerifyCustomError("LC0ControlError(uint256)", code)) || len(c.logs) != 0 {
		t.Fatalf("want LC0ControlError(%d), err=%v data=%x logs=%d", code, c.err, c.output, len(c.logs))
	}
}

func tl0VerifyStateError(data []byte) (code, offset uint64, ok bool) {
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

func tl0VerifyAssertState(t *testing.T, c tl0VerifyCall, code uint64, offsets ...uint64) {
	t.Helper()
	got, off, ok := tl0VerifyStateError(c.output)
	if !errors.Is(c.err, vm.ErrExecutionReverted) || !ok || got != code || len(c.logs) != 0 {
		t.Fatalf("want LC0StateError(%d,*), got %d/%d/%v err=%v data=%x logs=%d", code, got, off, ok, c.err, c.output, len(c.logs))
	}
	if len(offsets) != 0 && off != offsets[0] {
		t.Fatalf("LC0StateError offset=%d want=%d", off, offsets[0])
	}
}

func tl0VerifyAssertHeadEqual(t *testing.T, have, want tl0VerifyHead) {
	t.Helper()
	if !reflect.DeepEqual(have, want) {
		t.Fatalf("head changed\nhave %+v\nwant %+v", have, want)
	}
}

// tl0VerifyReader decodes the exact custom 216-byte envelope and flat machine
// stream. It deliberately has no connection to Session.Start/Resume.
type tl0VerifyReader struct {
	b []byte
	p int
}

func (r *tl0VerifyReader) take(n int) ([]byte, error) {
	if n < 0 || r.p > len(r.b) || n > len(r.b)-r.p {
		return nil, fmt.Errorf("truncated at %d need %d", r.p, n)
	}
	v := r.b[r.p : r.p+n]
	r.p += n
	return v, nil
}
func (r *tl0VerifyReader) u8() (uint8, error) {
	b, e := r.take(1)
	if e != nil {
		return 0, e
	}
	return b[0], nil
}
func (r *tl0VerifyReader) u16() (uint16, error) {
	b, e := r.take(2)
	if e != nil {
		return 0, e
	}
	return binary.BigEndian.Uint16(b), nil
}
func (r *tl0VerifyReader) u32() (uint32, error) {
	b, e := r.take(4)
	if e != nil {
		return 0, e
	}
	return binary.BigEndian.Uint32(b), nil
}
func (r *tl0VerifyReader) u64() (uint64, error) {
	b, e := r.take(8)
	if e != nil {
		return 0, e
	}
	return binary.BigEndian.Uint64(b), nil
}

type tl0VerifyFrame struct {
	Offset, FlagsOffset, SPOffset, BitmapOffset int
	Class, Method                               uint16
	PC                                          uint32
	CallPC                                      *big.Int
	Flags                                       uint8
	This                                        uint32
	SP, Locals                                  uint16
	StackOffsets, LocalOffsets                  []int
}
type tl0VerifyHeapRecord struct {
	Offset, HandleOffset, MetadataOffset, ClassOffset, RankOffset, CountOffset int
	Handle                                                                     uint32
	Metadata                                                                   *big.Int
	Class                                                                      uint16
	Rank                                                                       uint8
	Count                                                                      uint32
	CellOffsets                                                                []int
	Object                                                                     bool
}
type tl0VerifyMachine struct {
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
	Frames                                                              []tl0VerifyFrame
	HeapHeaderOffset                                                    int
	NextHandle                                                          uint32
	OrdinaryObjects, OrdinaryArrays                                     uint16
	OrdinaryElements, OrdinaryFields                                    uint32
	EmergencyRef                                                        uint32
	ExceptionObjects                                                    uint16
	ExceptionFields                                                     uint32
	Heap                                                                []tl0VerifyHeapRecord
	PendingOffset, PendingKindOffset, PendingRefOffset, PendingPCOffset int
	PendingActive, PendingKind                                          uint8
	PendingRef                                                          uint32
	PendingPC                                                           *big.Int
	CauseCountOffset                                                    int
	CauseWrapperOffsets, CauseRefOffsets                                []int
	InternCountOffset                                                   int
	InternHandleOffsets, InternHashOffsets                              []int
}
type tl0VerifyCheckpoint struct {
	Bytes                                          []byte
	Schema                                         uint32
	Instance                                       common.Hash
	Epoch                                          uint64
	Parent, Runtime, Artifact, Config, MachineRoot common.Hash
	MachineLength                                  uint32
	Machine                                        tl0VerifyMachine
}

func tl0VerifyReadASCII(r *tl0VerifyReader) (string, error) {
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

func tl0VerifyDecodeCheckpoint(blob []byte) (tl0VerifyCheckpoint, error) {
	var c tl0VerifyCheckpoint
	c.Bytes = append([]byte(nil), blob...)
	if len(blob) < tl0VerifyHeaderSize {
		return c, fmt.Errorf("short header")
	}
	if string(blob[:8]) != "JVMTL001" {
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
	if c.Schema != 1 || int(c.MachineLength) != len(blob)-tl0VerifyHeaderSize || len(blob) > tl0VerifyMaxBlob {
		return c, fmt.Errorf("header length/schema")
	}
	r := &tl0VerifyReader{b: blob[tl0VerifyHeaderSize:]}
	if b, e := r.take(4); e != nil || string(b) != "TLS1" {
		return c, fmt.Errorf("machine magic")
	}
	m := tl0VerifyMachine{}
	m.LifecycleOffset = tl0VerifyHeaderSize + r.p
	m.Lifecycle, _ = r.u8()
	m.ResultOffset = tl0VerifyHeaderSize + r.p
	b, e := r.take(4)
	if e != nil {
		return c, e
	}
	m.Result = int32(binary.BigEndian.Uint32(b))
	m.JavaKindOffset = tl0VerifyHeaderSize + r.p
	m.JavaKind, _ = r.u8()
	m.JavaRefOffset = tl0VerifyHeaderSize + r.p
	m.JavaRef, _ = r.u32()
	m.TotalJvmOffset = tl0VerifyHeaderSize + r.p
	m.TotalJvm, _ = r.u64()
	m.TotalInternalOffset = tl0VerifyHeaderSize + r.p
	m.TotalInternal, _ = r.u64()
	if m.EntryClass, e = tl0VerifyReadASCII(r); e != nil {
		return c, e
	}
	if m.Entry, e = tl0VerifyReadASCII(r); e != nil {
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
		m.ClassOffsets = append(m.ClassOffsets, tl0VerifyHeaderSize+r.p)
		m.InitOffsets = append(m.InitOffsets, tl0VerifyHeaderSize+r.p)
		if _, e = r.u8(); e != nil {
			return c, e
		}
		m.StartedOffsets = append(m.StartedOffsets, tl0VerifyHeaderSize+r.p)
		if _, e = r.u8(); e != nil {
			return c, e
		}
		n, e := r.u16()
		if e != nil {
			return c, e
		}
		var indices, vals []int
		for j := 0; j < int(n); j++ {
			indices = append(indices, tl0VerifyHeaderSize+r.p)
			if _, e = r.u16(); e != nil {
				return c, e
			}
			vals = append(vals, tl0VerifyHeaderSize+r.p)
			if _, e = r.take(32); e != nil {
				return c, e
			}
		}
		m.StaticIndexOffsets = append(m.StaticIndexOffsets, indices)
		m.StaticValueOffsets = append(m.StaticValueOffsets, vals)
	}
	m.FrameCountOffset = tl0VerifyHeaderSize + r.p
	frames, e := r.u16()
	if e != nil {
		return c, e
	}
	for i := 0; i < int(frames); i++ {
		f := tl0VerifyFrame{Offset: tl0VerifyHeaderSize + r.p}
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
		f.FlagsOffset = tl0VerifyHeaderSize + r.p
		f.Flags, e = r.u8()
		if e != nil {
			return c, e
		}
		f.This, e = r.u32()
		if e != nil {
			return c, e
		}
		f.SPOffset = tl0VerifyHeaderSize + r.p
		f.SP, e = r.u16()
		if e != nil {
			return c, e
		}
		for j := 0; j < int(f.SP); j++ {
			f.StackOffsets = append(f.StackOffsets, tl0VerifyHeaderSize+r.p)
			if _, e = r.take(32); e != nil {
				return c, e
			}
		}
		f.Locals, e = r.u16()
		if e != nil {
			return c, e
		}
		f.BitmapOffset = tl0VerifyHeaderSize + r.p
		if _, e = r.take((int(f.Locals) + 7) / 8); e != nil {
			return c, e
		}
		for j := 0; j < int(f.Locals); j++ {
			f.LocalOffsets = append(f.LocalOffsets, tl0VerifyHeaderSize+r.p)
			if _, e = r.take(32); e != nil {
				return c, e
			}
		}
		m.Frames = append(m.Frames, f)
	}
	m.HeapHeaderOffset = tl0VerifyHeaderSize + r.p
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
		h := tl0VerifyHeapRecord{Offset: tl0VerifyHeaderSize + r.p, HandleOffset: tl0VerifyHeaderSize + r.p}
		h.Handle, e = r.u32()
		if e != nil {
			return c, e
		}
		h.MetadataOffset = tl0VerifyHeaderSize + r.p
		b, e = r.take(32)
		if e != nil {
			return c, e
		}
		h.Metadata = new(big.Int).SetBytes(b)
		h.Object = len(b) > 0 && b[0]&0x80 != 0
		h.ClassOffset = tl0VerifyHeaderSize + r.p
		h.Class, e = r.u16()
		if e != nil {
			return c, e
		}
		h.RankOffset = tl0VerifyHeaderSize + r.p
		h.Rank, e = r.u8()
		if e != nil {
			return c, e
		}
		h.CountOffset = tl0VerifyHeaderSize + r.p
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
			h.CellOffsets = append(h.CellOffsets, tl0VerifyHeaderSize+r.p)
			if _, e = r.take(width); e != nil {
				return c, e
			}
		}
		m.Heap = append(m.Heap, h)
	}
	m.PendingOffset = tl0VerifyHeaderSize + r.p
	m.PendingActive, e = r.u8()
	if e != nil {
		return c, e
	}
	m.PendingKindOffset = tl0VerifyHeaderSize + r.p
	m.PendingKind, e = r.u8()
	if e != nil {
		return c, e
	}
	m.PendingRefOffset = tl0VerifyHeaderSize + r.p
	m.PendingRef, e = r.u32()
	if e != nil {
		return c, e
	}
	m.PendingPCOffset = tl0VerifyHeaderSize + r.p
	b, e = r.take(32)
	if e != nil {
		return c, e
	}
	m.PendingPC = new(big.Int).SetBytes(b)
	m.CauseCountOffset = tl0VerifyHeaderSize + r.p
	causes, e := r.u16()
	if e != nil {
		return c, e
	}
	for i := 0; i < int(causes); i++ {
		m.CauseWrapperOffsets = append(m.CauseWrapperOffsets, tl0VerifyHeaderSize+r.p)
		if _, e = r.u32(); e != nil {
			return c, e
		}
		m.CauseRefOffsets = append(m.CauseRefOffsets, tl0VerifyHeaderSize+r.p)
		if _, e = r.u32(); e != nil {
			return c, e
		}
	}
	m.InternCountOffset = tl0VerifyHeaderSize + r.p
	interns, e := r.u16()
	if e != nil {
		return c, e
	}
	for i := 0; i < int(interns); i++ {
		m.InternHandleOffsets = append(m.InternHandleOffsets, tl0VerifyHeaderSize+r.p)
		if _, e = r.u32(); e != nil {
			return c, e
		}
		m.InternHashOffsets = append(m.InternHashOffsets, tl0VerifyHeaderSize+r.p)
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

func tl0VerifyABIHash(t *testing.T, typesText []string, values ...any) common.Hash {
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
func tl0VerifyArtifactRoot(t *testing.T, raw [][]byte) common.Hash {
	return tl0VerifyABIHash(t, []string{"bytes32", "bytes[]"}, crypto.Keccak256Hash([]byte("JVMEVM:MC:TL0:ARTIFACT:1")), raw)
}
func tl0VerifyBootstrapRoot(t *testing.T) common.Hash {
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
	return tl0VerifyABIHash(t, []string{"bytes32", "bytes32[27]"}, crypto.Keccak256Hash([]byte("JVMEVM:MC:TL0:BOOTSTRAP:1")), hashes)
}
func tl0VerifyConfigRoot(t *testing.T, runtimeHash, bootstrap, artifact common.Hash, entryClass, entry string, args []int32) common.Hash {
	return tl0VerifyABIHash(t, []string{"bytes32", "uint32", "bytes32", "bytes32", "bytes32", "string", "string", "int32[]"}, crypto.Keccak256Hash([]byte("JVMEVM:MC:TL0:CONFIG:1")), uint32(1), runtimeHash, bootstrap, artifact, entryClass, entry, args)
}
func tl0VerifyMachineStateRoot(t *testing.T, c tl0VerifyCheckpoint, machine []byte) common.Hash {
	return tl0VerifyABIHash(t, []string{"bytes32", "uint32", "bytes32", "bytes32", "bytes32"}, crypto.Keccak256Hash([]byte("JVMEVM:MC:TL0:MACHINE:1")), uint32(1), c.Artifact, c.Config, crypto.Keccak256Hash(machine))
}
func tl0VerifyRehashMachine(t *testing.T, blob []byte) []byte {
	t.Helper()
	out := append([]byte(nil), blob...)
	c, e := tl0VerifyDecodeCheckpoint(out)
	if e != nil {
		t.Fatal(e)
	}
	root := tl0VerifyMachineStateRoot(t, c, out[216:])
	copy(out[180:212], root[:])
	return out
}

func tl0VerifyValidate(e *tl0VerifyEnv, raw [][]byte, blob []byte, gas uint64) tl0VerifyCall {
	return e.callAs(tl0VerifyOwner, gas, "validateCheckpoint", raw, blob)
}

func tl0VerifyCheckEvent(t *testing.T, contract abi.ABI, instance common.Hash, s tl0VerifySlice, c tl0VerifyCall) {
	t.Helper()
	if len(c.logs) != 1 {
		t.Fatalf("events=%d", len(c.logs))
	}
	ev, ok := contract.Events["CheckpointCommitted"]
	if !ok {
		t.Fatal("event absent")
	}
	l := c.logs[0]
	if l.Address != tl0VerifyAt || len(l.Topics) != 3 || l.Topics[0] != ev.ID || common.Hash(l.Topics[1]) != instance || new(big.Int).SetBytes(l.Topics[2][:]).Uint64() != s.Epoch {
		t.Fatalf("bad topics=%v", l.Topics)
	}
	v, err := ev.Inputs.NonIndexed().Unpack(l.Data)
	if err != nil {
		t.Fatal(err)
	}
	if common.Hash(v[0].([32]byte)) != tl0VerifySliceRoot(s) || common.Hash(v[1].([32]byte)) != tl0VerifyMachineRoot(s) || v[2].(uint8) != s.Lifecycle || v[3].(uint64) != s.TotalJvmSteps || v[4].(uint64) != s.TotalInternalSteps {
		t.Fatalf("bad event data=%v slice=%+v", v, s)
	}
}

// Everything below is an independent verifier corpus. javac only creates trusted
// raw Java 8 inputs; every asserted semantic result is produced by runtime.Call
// into Throwable0Interpreter. No host JVM evaluates a root.
func tl0VerifyCompileTrusted(t *testing.T, sources map[string]string, names []string) map[string][]byte {
	t.Helper()
	base := filepath.Join("..", "..", "..", "build", "java-diff-mc-tl0-verifier")
	if err := os.MkdirAll(base, 0700); err != nil {
		t.Fatal(err)
	}
	dir, err := os.MkdirTemp(base, "classes-")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { os.RemoveAll(dir) })
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
	out, err := exec.CommandContext(ctx, "javac", args...).CombinedOutput()
	if err != nil {
		t.Fatalf("trusted javac --release 8: %v\n%s", err, out)
	}
	classes := make(map[string][]byte)
	for _, name := range names {
		b, err := os.ReadFile(filepath.Join(dir, filepath.FromSlash(name+".class")))
		if err != nil {
			t.Fatal(err)
		}
		classes[name] = b
	}
	return classes
}

func tl0VerifyRaw(classes map[string][]byte, names ...string) [][]byte {
	out := make([][]byte, len(names))
	for i, name := range names {
		out[i] = classes[name]
	}
	return out
}

func tl0VerifyInstance(label string) common.Hash {
	return crypto.Keccak256Hash([]byte("JVMEVM:MC:TL0:VERIFY:" + label))
}

type tl0VerifyRun struct {
	slice tl0VerifySlice
	blob  []byte
	snaps []tl0VerifyCheckpoint
}

func tl0VerifyRunToEnd(t *testing.T, e *tl0VerifyEnv, label string, raw [][]byte, class, method string, jvm uint64, internal uint32, gas uint64, dispatchCap uint64) tl0VerifyRun {
	t.Helper()
	id := tl0VerifyInstance(label)
	s, blob, call := e.start(tl0VerifyOwner, id, raw, class, method, nil, jvm, internal, gas)
	tl0VerifyAssertSuccess(t, s, blob, call)
	r := tl0VerifyRun{slice: s, blob: blob}
	for slices := 0; ; slices++ {
		cp, err := tl0VerifyDecodeCheckpoint(blob)
		if err != nil {
			t.Fatalf("decode epoch %d: %v", s.Epoch, err)
		}
		r.snaps = append(r.snaps, cp)
		if cp.Machine.TotalJvm != s.TotalJvmSteps || cp.Machine.TotalInternal != s.TotalInternalSteps {
			t.Fatal("outer/stream counters differ")
		}
		if s.TotalJvmSteps > dispatchCap || slices >= 256 {
			t.Fatalf("continuation cap steps=%d slices=%d", s.TotalJvmSteps, slices+1)
		}
		if s.Lifecycle != tl0VerifyRunnable {
			break
		}
		s, blob, call = e.resume(tl0VerifyOwner, id, s.Epoch, tl0VerifySliceRoot(s), raw, blob, jvm, internal, gas)
		tl0VerifyAssertSuccess(t, s, blob, call)
		r.slice, r.blob = s, blob
	}
	return r
}

func tl0VerifyCauseMap(cp tl0VerifyCheckpoint) map[uint32]uint32 {
	out := make(map[uint32]uint32)
	for i, off := range cp.Machine.CauseWrapperOffsets {
		out[binary.BigEndian.Uint32(cp.Bytes[off:off+4])] = binary.BigEndian.Uint32(cp.Bytes[cp.Machine.CauseRefOffsets[i] : cp.Machine.CauseRefOffsets[i]+4])
	}
	return out
}

func tl0VerifyHeapByRef(cp tl0VerifyCheckpoint, ref uint32) (tl0VerifyHeapRecord, bool) {
	for _, h := range cp.Machine.Heap {
		if h.Handle == ref {
			return h, true
		}
	}
	return tl0VerifyHeapRecord{}, false
}

func tl0VerifyRequireReturned(t *testing.T, r tl0VerifyRun, want int32) {
	t.Helper()
	if r.slice.Lifecycle != tl0VerifyReturned || r.slice.Result != want || r.slice.JavaKind != 0 || r.slice.JavaRef != 0 || len(r.slice.JavaClass) != 0 {
		t.Fatalf("returned shape=%+v want=%d", r.slice, want)
	}
}

func tl0VerifyRequireUncaught(t *testing.T, r tl0VerifyRun, kind uint8, class string) {
	t.Helper()
	if r.slice.Lifecycle != tl0VerifyUncaught || r.slice.Result != 0 || r.slice.JavaKind != kind || r.slice.JavaRef == 0 || string(r.slice.JavaClass) != class {
		t.Fatalf("uncaught shape=%+v want kind=%d class=%q", r.slice, kind, class)
	}
	last := r.snaps[len(r.snaps)-1].Machine
	if len(last.Frames) != 0 || last.PendingActive != 1 || last.PendingRef != r.slice.JavaRef || last.PendingKind != kind {
		t.Fatalf("terminal pending does not retain exact ref: %+v", last)
	}
}

func tl0VerifyValidateOK(t *testing.T, e *tl0VerifyEnv, raw [][]byte, blob []byte) common.Hash {
	t.Helper()
	c := tl0VerifyValidate(e, raw, blob, tl0VerifyBoundaryGas)
	if c.err != nil {
		t.Fatalf("validate: %v data=%x", c.err, c.output)
	}
	v, err := e.contract.Methods["validateCheckpoint"].Outputs.Unpack(c.output)
	if err != nil || len(v) != 1 {
		t.Fatalf("validate output: %v/%d", err, len(v))
	}
	return common.Hash(v[0].([32]byte))
}

func tl0VerifyMutateRehash(t *testing.T, blob []byte, at int, mutate func([]byte)) []byte {
	t.Helper()
	cp, err := tl0VerifyDecodeCheckpoint(blob)
	if err != nil {
		t.Fatal(err)
	}
	out := append([]byte(nil), blob...)
	if at < tl0VerifyHeaderSize || at >= len(out) {
		t.Fatalf("mutation offset=%d len=%d", at, len(out))
	}
	mutate(out[at:])
	root := tl0VerifyMachineStateRoot(t, cp, out[tl0VerifyHeaderSize:])
	copy(out[180:212], root[:])
	return out
}

func tl0VerifyErrorSelector(data []byte, signature string) bool {
	return len(data) >= 4 && bytes.Equal(data[:4], crypto.Keccak256([]byte(signature))[:4])
}

// Eight independently named allocation/arena/field/checkpoint probes.
func TestTL0VerifyAllocationArenaFieldAndCheckpointBoundaries(t *testing.T) {
	code, err := Runtime()
	if err != nil {
		t.Fatalf("required TL0 artifact: %v", err)
	}
	if len(code) == 0 || len(code) > 256*1024 {
		t.Fatalf("TL0 runtime size=%d", len(code))
	}
	contract, err := ABI()
	if err != nil {
		t.Fatal(err)
	}
	if len(contract.Methods) != 4 || contract.Methods["start"].Sig != "start(bytes32,bytes[],string,string,int32[],uint64,uint32)" || contract.Methods["resume"].Sig != "resume(bytes32,uint64,bytes32,bytes[],bytes,uint64,uint32)" {
		t.Fatalf("unexpected TL0 public ABI: %v", contract.Methods)
	}
	tuple := contract.Methods["start"].Outputs[0].Type
	wantNames := []string{"schema", "lifecycle", "epoch", "checkpointRoot", "machineStateRoot", "totalJvmSteps", "totalInternalSteps", "executedJvmSteps", "executedInternalSteps", "result", "javaKind", "javaRef", "javaClass"}
	if tuple.T != abi.TupleTy || !reflect.DeepEqual(tuple.TupleRawNames, wantNames) || tuple.TupleElems[len(tuple.TupleElems)-1].String() != "bytes" {
		t.Fatalf("ThrowableSliceResult ABI=%v", tuple.TupleRawNames)
	}
	if _, ok := contract.Errors["ThrowableProfileError"]; !ok {
		t.Fatal("ThrowableProfileError absent from TL0 ABI")
	}

	basic := tl0VerifyCompileTrusted(t, map[string]string{
		"TLAlloc.java": `public final class TLAlloc {
		 static final class P extends RuntimeException { int a,b,c; P(int x){a=x;b=x+1;c=x+2;} }
		 public static int ordinaryKnown(){throw new ArithmeticException();}
		 public static int implicitKnown(){int z=0;return 1/z;}
		 public static int fields(){try{throw new P(4);}catch(P p){return p.a+p.b+p.c;}}
		}`,
	}, []string{"TLAlloc", "TLAlloc$P"})
	rawBasic := tl0VerifyRaw(basic, "TLAlloc", "TLAlloc$P")

	t.Run("01-ordinary-known-kind-keeps-ordinary-origin", func(t *testing.T) {
		e := tl0VerifyNewEnv(t)
		defer e.close()
		r := tl0VerifyRunToEnd(t, e, "alloc-ordinary-known", rawBasic, "TLAlloc", "ordinaryKnown", 4096, 4096, tl0VerifyOrdinaryGas, 4096)
		tl0VerifyRequireUncaught(t, r, 1, "")
		cp := r.snaps[len(r.snaps)-1]
		m := cp.Machine
		wantArtifact := tl0VerifyArtifactRoot(t, rawBasic)
		wantConfig := tl0VerifyConfigRoot(t, crypto.Keccak256Hash(code), tl0VerifyBootstrapRoot(t), wantArtifact, "TLAlloc", "ordinaryKnown", nil)
		if cp.Runtime != crypto.Keccak256Hash(code) || cp.Artifact != wantArtifact || cp.Config != wantConfig || cp.MachineRoot != tl0VerifyMachineStateRoot(t, cp, cp.Bytes[tl0VerifyHeaderSize:]) {
			t.Fatalf("TL0 namespace commitments mismatch: %+v", cp)
		}
		if m.OrdinaryObjects != 1 || m.ExceptionObjects != 0 {
			t.Fatalf("origin counters ordinary=%d arena=%d", m.OrdinaryObjects, m.ExceptionObjects)
		}
	})
	t.Run("02-implicit-known-kind-keeps-arena-origin", func(t *testing.T) {
		e := tl0VerifyNewEnv(t)
		defer e.close()
		r := tl0VerifyRunToEnd(t, e, "alloc-implicit-known", rawBasic, "TLAlloc", "implicitKnown", 4096, 4096, tl0VerifyOrdinaryGas, 4096)
		tl0VerifyRequireUncaught(t, r, 1, "")
		m := r.snaps[len(r.snaps)-1].Machine
		if m.OrdinaryObjects != 0 || m.ExceptionObjects != 1 {
			t.Fatalf("origin counters ordinary=%d arena=%d", m.OrdinaryObjects, m.ExceptionObjects)
		}
	})
	t.Run("03-throwable-fields-use-ordinary-field-quota", func(t *testing.T) {
		e := tl0VerifyNewEnv(t)
		defer e.close()
		r := tl0VerifyRunToEnd(t, e, "alloc-fields", rawBasic, "TLAlloc", "fields", 4096, 4096, tl0VerifyOrdinaryGas, 4096)
		tl0VerifyRequireReturned(t, r, 15)
		m := r.snaps[len(r.snaps)-1].Machine
		if m.OrdinaryObjects != 1 || m.OrdinaryFields != 3 || m.ExceptionObjects != 0 {
			t.Fatalf("ordinary object/fields=%d/%d arena=%d", m.OrdinaryObjects, m.OrdinaryFields, m.ExceptionObjects)
		}
	})

	quota := tl0VerifyCompileTrusted(t, map[string]string{
		"TLQuota.java": `public final class TLQuota { static Q sink; static final class Q extends RuntimeException { Q(){} }
		 static void fill(){for(int i=0;i<1024;i++)sink=new Q();}
		 public static int run(){fill();try{int z=0;return 1/z;}catch(ArithmeticException ok){return 41;}}
		}`,
	}, []string{"TLQuota", "TLQuota$Q"})
	t.Run("04-full-ordinary-pool-still-allows-implicit-fault", func(t *testing.T) {
		e := tl0VerifyNewEnv(t)
		defer e.close()
		r := tl0VerifyRunToEnd(t, e, "alloc-full-ordinary", tl0VerifyRaw(quota, "TLQuota", "TLQuota$Q"), "TLQuota", "run", 4096, 4096, tl0VerifyBoundaryGas, 65536)
		tl0VerifyRequireReturned(t, r, 41)
		m := r.snaps[len(r.snaps)-1].Machine
		if m.OrdinaryObjects != 1024 || m.ExceptionObjects != 1 {
			t.Fatalf("full ordinary/implicit arena=%d/%d", m.OrdinaryObjects, m.ExceptionObjects)
		}
	})

	arena := tl0VerifyCompileTrusted(t, map[string]string{
		"TLArena.java": `public final class TLArena { static int div(){int z=0;return 1/z;}
		 public static int run(){for(int i=0;i<256;i++){try{div();}catch(ArithmeticException x){}}try{div();return 0;}catch(OutOfMemoryError x){return 256;}}
		}`,
	}, []string{"TLArena"})
	t.Run("05-full-implicit-arena-uses-emergency-oom", func(t *testing.T) {
		e := tl0VerifyNewEnv(t)
		defer e.close()
		r := tl0VerifyRunToEnd(t, e, "alloc-full-arena", tl0VerifyRaw(arena, "TLArena"), "TLArena", "run", 4096, 4096, tl0VerifyBoundaryGas, 4096)
		tl0VerifyRequireReturned(t, r, 256)
		m := r.snaps[len(r.snaps)-1].Machine
		if m.ExceptionObjects != 256 || m.EmergencyRef == 0 {
			t.Fatalf("arena/emergency=%d/%d", m.ExceptionObjects, m.EmergencyRef)
		}
	})

	wrapperOOM := tl0VerifyCompileTrusted(t, map[string]string{
		"TLWrapOOM.java": `public final class TLWrapOOM { static final class P extends RuntimeException{} static final class Bad {static int fail(){throw new P();}static int x=fail();}
		 static int div(){int z=0;return 1/z;} public static int run(){new P();for(int i=0;i<256;i++)try{div();}catch(ArithmeticException x){}try{return Bad.x;}catch(OutOfMemoryError x){return 77;}}
		}`,
	}, []string{"TLWrapOOM", "TLWrapOOM$P", "TLWrapOOM$Bad"})
	t.Run("06-wrapper-allocation-failure-is-emergency-oom-without-cause", func(t *testing.T) {
		e := tl0VerifyNewEnv(t)
		defer e.close()
		r := tl0VerifyRunToEnd(t, e, "alloc-wrapper-oom", tl0VerifyRaw(wrapperOOM, "TLWrapOOM", "TLWrapOOM$P", "TLWrapOOM$Bad"), "TLWrapOOM", "run", 4096, 4096, tl0VerifyBoundaryGas, 4096)
		tl0VerifyRequireReturned(t, r, 77)
		cp := r.snaps[len(r.snaps)-1]
		if len(cp.Machine.CauseWrapperOffsets) != 0 || cp.Machine.ExceptionObjects != 256 {
			t.Fatalf("fictitious cause or arena count: causes=%d arena=%d", len(cp.Machine.CauseWrapperOffsets), cp.Machine.ExceptionObjects)
		}
	})

	for _, tc := range []struct {
		name, method string
		wantLen      int
		fail         bool
	}{
		{"07-exact-one-mib-checkpoint", "abcdefg", 1 << 20, false},
		{"08-plus-one-checkpoint-rolls-back", "abcdefgh", (1 << 20) + 1, true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			source := fmt.Sprintf("public final class TLCap {public static int %s(){long[] a=new long[65536];long[] b=new long[65464];return a.length+b.length;}}", tc.method)
			classes := tl0VerifyCompileTrusted(t, map[string]string{"TLCap.java": source}, []string{"TLCap"})
			e := tl0VerifyNewEnv(t)
			defer e.close()
			id := tl0VerifyInstance(tc.name)
			s, blob, call := e.start(tl0VerifyOwner, id, tl0VerifyRaw(classes, "TLCap"), "TLCap", tc.method, nil, 4096, 4096, tl0VerifyBoundaryGas)
			if tc.fail {
				tl0VerifyAssertState(t, call, 1, 0)
				if e.head(id) != (tl0VerifyHead{}) || len(call.logs) != 0 {
					t.Fatal("oversize checkpoint published")
				}
				return
			}
			tl0VerifyAssertSuccess(t, s, blob, call)
			if len(blob) != tc.wantLen || s.Result != 131000 {
				t.Fatalf("checkpoint=%d result=%d want=%d/131000", len(blob), s.Result, tc.wantLen)
			}
		})
	}
}

// Eight tag/constructor/fill-profile probes, including every corrected legal
// constructor state from the frozen contract.
func TestTL0VerifyTagsConstructorsAndFillProfile(t *testing.T) {
	nullClass := tl0VerifyCompileTrusted(t, map[string]string{
		"TLNull.java": `public final class TLNull {public static int run(){throw null;}}`,
	}, []string{"TLNull"})
	t.Run("09-null-athrow-is-npe", func(t *testing.T) {
		e := tl0VerifyNewEnv(t)
		defer e.close()
		r := tl0VerifyRunToEnd(t, e, "tag-null", tl0VerifyRaw(nullClass, "TLNull"), "TLNull", "run", 4096, 4096, tl0VerifyOrdinaryGas, 4096)
		tl0VerifyRequireUncaught(t, r, 6, "")
	})

	mutSrc := tl0VerifyCompileTrusted(t, map[string]string{
		"TLTag.java": `public final class TLTag {static Object other=new Object();static final class P extends RuntimeException{} public static int run(){throw new P();}}`,
	}, []string{"TLTag", "TLTag$P"})
	rawMut := tl0VerifyRaw(mutSrc, "TLTag", "TLTag$P")
	makeThrowSnapshot := func(t *testing.T) (*tl0VerifyEnv, tl0VerifyCheckpoint, [][]byte) {
		t.Helper()
		e := tl0VerifyNewEnv(t)
		r := tl0VerifyRunToEnd(t, e, "tag-snapshot-"+t.Name(), rawMut, "TLTag", "run", 1, 1, tl0VerifyOrdinaryGas, 4096)
		for _, cp := range r.snaps {
			throwables := make(map[uint32]bool)
			for _, h := range cp.Machine.Heap {
				if h.Object && h.Class == 1 {
					throwables[h.Handle] = true
				}
			}
			for _, f := range cp.Machine.Frames {
				for _, off := range f.StackOffsets {
					v := new(big.Int).SetBytes(cp.Bytes[off : off+32])
					if new(big.Int).Rsh(new(big.Int).Set(v), 64).Uint64() == 2 && throwables[uint32(v.Uint64())] {
						return e, cp, rawMut
					}
				}
			}
		}
		e.close()
		t.Fatal("no actual REF operand snapshot")
		return nil, tl0VerifyCheckpoint{}, nil
	}
	findRefOffset := func(cp tl0VerifyCheckpoint) int {
		throwables := make(map[uint32]bool)
		for _, h := range cp.Machine.Heap {
			if h.Object && h.Class == 1 {
				throwables[h.Handle] = true
			}
		}
		for _, f := range cp.Machine.Frames {
			for _, off := range f.StackOffsets {
				v := new(big.Int).SetBytes(cp.Bytes[off : off+32])
				if new(big.Int).Rsh(new(big.Int).Set(v), 64).Uint64() == 2 && throwables[uint32(v.Uint64())] {
					return off
				}
			}
		}
		return 0
	}
	putTagged := func(b []byte, kind, ref uint64) {
		v := new(big.Int).Lsh(new(big.Int).SetUint64(kind), 64)
		v.Or(v, new(big.Int).SetUint64(ref))
		v.FillBytes(b[:32])
	}
	for _, tc := range []struct {
		name string
		kind uint64
	}{
		{"10-illegal-int-tag-at-throw-boundary", 1},
		{"11-uninitialized-tag-at-throw-boundary", 3},
	} {
		t.Run(tc.name, func(t *testing.T) {
			e, cp, raw := makeThrowSnapshot(t)
			defer e.close()
			off := findRefOffset(cp)
			bad := tl0VerifyMutateRehash(t, cp.Bytes, off, func(b []byte) { putTagged(b, tc.kind, 1) })
			c := tl0VerifyValidate(e, raw, bad, tl0VerifyBoundaryGas)
			code, _, ok := tl0VerifyStateError(c.output)
			if c.err == nil || !ok || code != 5 {
				t.Fatalf("illegal tag accepted/misclassified err=%v data=%x", c.err, c.output)
			}
		})
	}
	t.Run("12-nonthrowable-ref-rejected-at-typed-frame-boundary", func(t *testing.T) {
		e, cp, raw := makeThrowSnapshot(t)
		defer e.close()
		off := findRefOffset(cp)
		var objectRef uint32
		for _, h := range cp.Machine.Heap {
			if h.Object && h.Class == uint16(len(raw)) {
				objectRef = h.Handle
				break
			}
		}
		if objectRef == 0 {
			t.Fatal("actual non-Throwable Object not found")
		}
		bad := tl0VerifyMutateRehash(t, cp.Bytes, off, func(b []byte) { putTagged(b, 2, uint64(objectRef)) })
		c := tl0VerifyValidate(e, raw, bad, tl0VerifyBoundaryGas)
		if c.err == nil {
			t.Fatal("non-Throwable REF accepted")
		}
		if code, _, ok := tl0VerifyStateError(c.output); !ok || (code != 5 && code != 7) {
			t.Fatalf("wrong validator error %x", c.output)
		}
	})

	legalCases := []struct {
		name, source, root string
		names              []string
		want               int32
	}{
		{"13-post-super-constructor-throw-this", `public final class TLDirect {static final class P extends RuntimeException {P(){super();throw this;}}public static int run(){try{new P();return 0;}catch(P p){return 101;}}}`, "TLDirect", []string{"TLDirect", "TLDirect$P"}, 101},
		{"14-method-throws-active-constructor-receiver", `public final class TLThrough {static void boom(P p){throw p;}static final class P extends RuntimeException {P(){super();boom(this);}}public static int run(){try{new P();return 0;}catch(P p){return 102;}}}`, "TLThrough", []string{"TLThrough", "TLThrough$P"}, 102},
		{"15-saved-initialized-ref-survives-constructor-failure", `public final class TLSaved {static P saved;static final class P extends RuntimeException {P(){super();saved=this;throw this;}}public static int run(){P first=null;try{new P();}catch(P p){first=p;}try{throw saved;}catch(P p){return p==first?103:0;}}}`, "TLSaved", []string{"TLSaved", "TLSaved$P"}, 103},
	}
	for _, tc := range legalCases {
		t.Run(tc.name, func(t *testing.T) {
			classes := tl0VerifyCompileTrusted(t, map[string]string{tc.root + ".java": tc.source}, tc.names)
			e := tl0VerifyNewEnv(t)
			defer e.close()
			r := tl0VerifyRunToEnd(t, e, tc.name, tl0VerifyRaw(classes, tc.names...), tc.root, "run", 1, 1, tl0VerifyOrdinaryGas, 4096)
			tl0VerifyRequireReturned(t, r, tc.want)
			seenCoexist := false
			for _, cp := range r.snaps {
				refs := map[uint32]uint8{}
				for _, f := range cp.Machine.Frames {
					for _, off := range append(append([]int{}, f.StackOffsets...), f.LocalOffsets...) {
						v := new(big.Int).SetBytes(cp.Bytes[off : off+32])
						k := uint8(new(big.Int).Rsh(new(big.Int).Set(v), 64).Uint64())
						if k == 2 || k == 3 {
							refs[uint32(v.Uint64())] |= 1 << k
						}
					}
				}
				for _, values := range cp.Machine.StaticValueOffsets {
					for _, off := range values {
						v := new(big.Int).SetBytes(cp.Bytes[off : off+32])
						if new(big.Int).Rsh(new(big.Int).Set(v), 64).Uint64() == 2 {
							refs[uint32(v.Uint64())] |= 1 << 2
						}
					}
				}
				if cp.Machine.PendingActive == 1 && cp.Machine.PendingRef != 0 {
					refs[cp.Machine.PendingRef] |= 1 << 2
				}
				for _, mask := range refs {
					if mask&(1<<2) != 0 && mask&(1<<3) != 0 {
						seenCoexist = true
					}
				}
			}
			if !seenCoexist {
				t.Fatal("legal initialized REF did not coexist with caller UNINIT duplicate at any q1 checkpoint")
			}
		})
	}

	t.Run("16-fill-override-rejected-but-overload-accepted", func(t *testing.T) {
		e := tl0VerifyNewEnv(t)
		defer e.close()
		assertProfile := func(label string, raw [][]byte, class string, declaration uint64) {
			id := tl0VerifyInstance("fill-" + label)
			_, _, c := e.start(tl0VerifyOwner, id, raw, class, "run", nil, 4096, 4096, tl0VerifyOrdinaryGas)
			if !errors.Is(c.err, vm.ErrExecutionReverted) || len(c.output) != 100 || !tl0VerifyErrorSelector(c.output, "ThrowableProfileError(uint256,uint256,uint256)") || new(big.Int).SetBytes(c.output[4:36]).Uint64() != 1 || new(big.Int).SetBytes(c.output[36:68]).Uint64() != declaration || new(big.Int).SetBytes(c.output[68:100]).Sign() == 0 || len(c.logs) != 0 || e.head(id) != (tl0VerifyHead{}) {
				t.Fatalf("%s override not exact hard profile error: %v %x", label, c.err, c.output)
			}
		}
		bad := tl0VerifyCompileTrusted(t, map[string]string{"TLFillBad.java": `public final class TLFillBad extends RuntimeException {public synchronized Throwable fillInStackTrace(){return this;}public static int run(){throw new TLFillBad();}}`}, []string{"TLFillBad"})
		assertProfile("direct", tl0VerifyRaw(bad, "TLFillBad"), "TLFillBad", 0)
		inherited := tl0VerifyCompileTrusted(t, map[string]string{"TLFillInherited.java": `public final class TLFillInherited {static class Base extends RuntimeException {public Throwable fillInStackTrace(){return this;}}static final class Child extends Base{}public static int run(){throw new Child();}}`}, []string{"TLFillInherited", "TLFillInherited$Base", "TLFillInherited$Child"})
		assertProfile("inherited", tl0VerifyRaw(inherited, "TLFillInherited", "TLFillInherited$Base", "TLFillInherited$Child"), "TLFillInherited", 1)
		covariant := tl0VerifyCompileTrusted(t, map[string]string{"TLFillCovariant.java": `public final class TLFillCovariant extends RuntimeException {public TLFillCovariant fillInStackTrace(){return this;}public static int run(){throw new TLFillCovariant();}}`}, []string{"TLFillCovariant"})
		assertProfile("covariant-bridge", tl0VerifyRaw(covariant, "TLFillCovariant"), "TLFillCovariant", 0)
		good := tl0VerifyCompileTrusted(t, map[string]string{"TLFillGood.java": `public final class TLFillGood extends RuntimeException {public Throwable fillInStackTrace(int ignored){return this;}public static int run(){try{throw new TLFillGood();}catch(TLFillGood x){return 16;}}}`}, []string{"TLFillGood"})
		r := tl0VerifyRunToEnd(t, e, "fill-overload", tl0VerifyRaw(good, "TLFillGood"), "TLFillGood", "run", 4096, 4096, tl0VerifyOrdinaryGas, 4096)
		tl0VerifyRequireReturned(t, r, 16)
	})
}

// Ten pending/outcome/cause-codec probes. Dynamic class bytes and cause refs are
// read from EVM output/checkpoints, never reconstructed from host class metadata.
func TestTL0VerifyPendingOutcomeAndCauseCodec(t *testing.T) {
	outcomes := tl0VerifyCompileTrusted(t, map[string]string{
		"TLOut.java": `public final class TLOut {static final class Problem extends RuntimeException{}static final class KnownChild extends ArithmeticException{}
		 public static int exact(){throw new ArithmeticException();}public static int custom(){throw new Problem();}public static int child(){throw new KnownChild();}
		 public static int local(){Problem p=new Problem();try{throw p;}catch(Problem q){return p==q?1:0;}}
		 public static int rethrow(){Problem p=new Problem();try{try{throw p;}catch(Problem q){throw q;}}catch(Problem q){return p==q?2:0;}}
		}`,
	}, []string{"TLOut", "TLOut$Problem", "TLOut$KnownChild"})
	rawOut := tl0VerifyRaw(outcomes, "TLOut", "TLOut$Problem", "TLOut$KnownChild")
	for _, tc := range []struct {
		name, method string
		kind         uint8
		class        string
	}{
		{"17-exact-known-outcome-empty-class", "exact", 1, ""},
		{"18-custom-outcome-kind-zero-dynamic-class", "custom", 0, "TLOut$Problem"},
		{"19-known-subclass-is-kind-zero-dynamic-class", "child", 0, "TLOut$KnownChild"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			e := tl0VerifyNewEnv(t)
			defer e.close()
			r := tl0VerifyRunToEnd(t, e, tc.name, rawOut, "TLOut", tc.method, 4096, 4096, tl0VerifyOrdinaryGas, 4096)
			tl0VerifyRequireUncaught(t, r, tc.kind, tc.class)
		})
	}
	t.Run("20-local-catch-preserves-identity", func(t *testing.T) {
		e := tl0VerifyNewEnv(t)
		defer e.close()
		r := tl0VerifyRunToEnd(t, e, "identity-local", rawOut, "TLOut", "local", 1, 1, tl0VerifyOrdinaryGas, 4096)
		tl0VerifyRequireReturned(t, r, 1)
	})
	t.Run("21-pending-rethrow-preserves-one-ref-and-allocates-nothing", func(t *testing.T) {
		e := tl0VerifyNewEnv(t)
		defer e.close()
		r := tl0VerifyRunToEnd(t, e, "identity-rethrow", rawOut, "TLOut", "rethrow", 1, 1, tl0VerifyOrdinaryGas, 4096)
		tl0VerifyRequireReturned(t, r, 2)
		refs := map[uint32]bool{}
		var ordinary uint16
		for _, cp := range r.snaps {
			if cp.Machine.PendingActive == 1 && cp.Machine.PendingKind == 0 {
				refs[cp.Machine.PendingRef] = true
			}
			if cp.Machine.OrdinaryObjects > ordinary {
				ordinary = cp.Machine.OrdinaryObjects
			}
		}
		if len(refs) != 1 || ordinary != 1 {
			t.Fatalf("rethrow refs=%v ordinary allocations=%d", refs, ordinary)
		}
	})

	wrap := tl0VerifyCompileTrusted(t, map[string]string{
		"TLWrap.java": `public final class TLWrap {static final class Problem extends RuntimeException{Problem(){super();throw this;}}static final class Bad{static Problem value=new Problem();}public static int run(){try{Problem x=Bad.value;return 0;}catch(ExceptionInInitializerError x){return 201;}}}`,
	}, []string{"TLWrap", "TLWrap$Problem", "TLWrap$Bad"})
	t.Run("22-constructor-self-throw-escaping-clinit-is-exact-eiie-cause", func(t *testing.T) {
		e := tl0VerifyNewEnv(t)
		defer e.close()
		r := tl0VerifyRunToEnd(t, e, "cause-wrap", tl0VerifyRaw(wrap, "TLWrap", "TLWrap$Problem", "TLWrap$Bad"), "TLWrap", "run", 1, 1, tl0VerifyOrdinaryGas, 4096)
		tl0VerifyRequireReturned(t, r, 201)
		cp := r.snaps[len(r.snaps)-1]
		causes := tl0VerifyCauseMap(cp)
		if len(causes) != 1 {
			t.Fatalf("cause records=%v", causes)
		}
		for wrapper, cause := range causes {
			w, wok := tl0VerifyHeapByRef(cp, wrapper)
			c, cok := tl0VerifyHeapByRef(cp, cause)
			if !wok || !cok || wrapper <= cause || w.Class != uint16(len(wrap)+11) || c.Class != 1 || uint8(w.Metadata.Uint64()) != 3 || uint8(c.Metadata.Uint64()) != 0 {
				t.Fatalf("wrapper/cause relation %d:%d w=%+v c=%+v", wrapper, cause, w, c)
			}
		}
	})

	explicit := tl0VerifyCompileTrusted(t, map[string]string{"TLExplicit.java": `public final class TLExplicit {public static int run(){throw new ExceptionInInitializerError();}}`}, []string{"TLExplicit"})
	t.Run("23-explicit-eiie-is-ordinary-and-has-no-cause-record", func(t *testing.T) {
		e := tl0VerifyNewEnv(t)
		defer e.close()
		r := tl0VerifyRunToEnd(t, e, "cause-explicit", tl0VerifyRaw(explicit, "TLExplicit"), "TLExplicit", "run", 4096, 4096, tl0VerifyOrdinaryGas, 4096)
		tl0VerifyRequireUncaught(t, r, 3, "")
		cp := r.snaps[len(r.snaps)-1]
		if len(cp.Machine.CauseWrapperOffsets) != 0 || cp.Machine.OrdinaryObjects != 1 {
			t.Fatalf("explicit EIIE cause/origin=%d/%d", len(cp.Machine.CauseWrapperOffsets), cp.Machine.OrdinaryObjects)
		}
	})

	errClasses := tl0VerifyCompileTrusted(t, map[string]string{"TLErrorInit.java": `public final class TLErrorInit {static final class Boom extends Error{}static final class Bad{static int fail(){throw new Boom();}static int x=fail();}public static int run(){return Bad.x;}}`}, []string{"TLErrorInit", "TLErrorInit$Boom", "TLErrorInit$Bad"})
	t.Run("24-error-subclass-escapes-clinit-unwrapped", func(t *testing.T) {
		e := tl0VerifyNewEnv(t)
		defer e.close()
		r := tl0VerifyRunToEnd(t, e, "cause-error", tl0VerifyRaw(errClasses, "TLErrorInit", "TLErrorInit$Boom", "TLErrorInit$Bad"), "TLErrorInit", "run", 4096, 4096, tl0VerifyOrdinaryGas, 4096)
		tl0VerifyRequireUncaught(t, r, 0, "TLErrorInit$Boom")
		if len(r.snaps[len(r.snaps)-1].Machine.CauseWrapperOffsets) != 0 {
			t.Fatal("Error was wrapped")
		}
	})

	codec := tl0VerifyCompileTrusted(t, map[string]string{
		"TLCauseCodec.java": `public final class TLCauseCodec {static Object object=new Object();static final class P extends RuntimeException{}static final class A{static int f(){throw new P();}static int x=f();}static final class B{static int f(){throw new P();}static int x=f();}public static int run(){try{int x=A.x;}catch(ExceptionInInitializerError x){}try{int x=B.x;}catch(ExceptionInInitializerError x){}return 9;}}`,
	}, []string{"TLCauseCodec", "TLCauseCodec$P", "TLCauseCodec$A", "TLCauseCodec$B"})
	rawCodec := tl0VerifyRaw(codec, "TLCauseCodec", "TLCauseCodec$P", "TLCauseCodec$A", "TLCauseCodec$B")
	t.Run("25-cause-stream-rejects-missing-duplicate-order-and-wrong-type", func(t *testing.T) {
		e := tl0VerifyNewEnv(t)
		defer e.close()
		r := tl0VerifyRunToEnd(t, e, "cause-codec", rawCodec, "TLCauseCodec", "run", 4096, 4096, tl0VerifyOrdinaryGas, 4096)
		tl0VerifyRequireReturned(t, r, 9)
		cp := r.snaps[len(r.snaps)-1]
		if len(cp.Machine.CauseWrapperOffsets) != 2 {
			t.Fatalf("need two actual wrappers, got %d", len(cp.Machine.CauseWrapperOffsets))
		}
		w0 := binary.BigEndian.Uint32(cp.Bytes[cp.Machine.CauseWrapperOffsets[0]:])
		w1 := binary.BigEndian.Uint32(cp.Bytes[cp.Machine.CauseWrapperOffsets[1]:])
		var ordinaryObject uint32
		for _, h := range cp.Machine.Heap {
			if h.Object && h.Class == uint16(len(rawCodec)) {
				ordinaryObject = h.Handle
				break
			}
		}
		if ordinaryObject == 0 {
			t.Fatal("ordinary Object absent")
		}
		cases := []struct {
			name string
			off  int
			set  uint32
		}{
			{"missing-arena-wrapper", cp.Machine.CauseWrapperOffsets[0], w1},
			{"duplicate-wrapper", cp.Machine.CauseWrapperOffsets[1], w0},
			{"unordered-wrapper", cp.Machine.CauseWrapperOffsets[0], w1 + 1},
			{"wrong-type-cause", cp.Machine.CauseRefOffsets[0], ordinaryObject},
		}
		for _, tc := range cases {
			bad := tl0VerifyMutateRehash(t, cp.Bytes, tc.off, func(b []byte) { binary.BigEndian.PutUint32(b, tc.set) })
			c := tl0VerifyValidate(e, rawCodec, bad, tl0VerifyBoundaryGas)
			code, _, ok := tl0VerifyStateError(c.output)
			if c.err == nil || !ok || code != 7 {
				t.Fatalf("%s accepted/misclassified: %v %x", tc.name, c.err, c.output)
			}
		}
	})
	t.Run("26-readonly-validation-does-not-create-live-provenance", func(t *testing.T) {
		e := tl0VerifyNewEnv(t)
		defer e.close()
		id := tl0VerifyInstance("readonly-provenance")
		raw := rawOut
		s, blob, c := e.start(tl0VerifyOwner, id, raw, "TLOut", "rethrow", nil, 1, 1, tl0VerifyOrdinaryGas)
		tl0VerifyAssertSuccess(t, s, blob, c)
		before := e.head(id)
		altered := append([]byte(nil), blob...)
		altered[83] ^= 1
		if tl0VerifyValidateOK(t, e, raw, altered) != (common.Hash(s.MachineStateRoot)) {
			t.Fatal("history-only validation changed machine root")
		}
		tl0VerifyAssertHeadEqual(t, e.head(id), before)
		_, _, bad := e.resume(tl0VerifyOwner, id, s.Epoch, tl0VerifySliceRoot(s), raw, altered, 1, 1, tl0VerifyOrdinaryGas)
		tl0VerifyAssertControl(t, bad, 4)
		tl0VerifyAssertHeadEqual(t, e.head(id), before)
	})
}

type tl0VerifyProcessResult struct {
	Lifecycle uint8       `json:"lifecycle"`
	Result    int32       `json:"result"`
	Epoch     uint64      `json:"epoch"`
	Root      common.Hash `json:"root"`
}

// Six CAS/OOG/rollback/retry/new-process probes. All failed calls assert the old
// live head and zero child event; validator success is never treated as authority.
func TestTL0VerifyCASOOGRetryAndNewProcess(t *testing.T) {
	classes := tl0VerifyCompileTrusted(t, map[string]string{"TLCAS.java": `public final class TLCAS {public static int run(){int s=0;for(int i=0;i<20;i++)s+=i;return s;}}`}, []string{"TLCAS"})
	raw := tl0VerifyRaw(classes, "TLCAS")
	fresh := func(t *testing.T, label string) (*tl0VerifyEnv, common.Hash, tl0VerifySlice, []byte, tl0VerifyHead) {
		t.Helper()
		e := tl0VerifyNewEnv(t)
		id := tl0VerifyInstance(label)
		s, b, c := e.start(tl0VerifyOwner, id, raw, "TLCAS", "run", nil, 1, 1, tl0VerifyOrdinaryGas)
		tl0VerifyAssertSuccess(t, s, b, c)
		return e, id, s, b, e.head(id)
	}
	t.Run("27-owner-cas-preserves-live-head", func(t *testing.T) {
		e, id, s, b, before := fresh(t, "cas-owner")
		defer e.close()
		_, _, c := e.resume(tl0VerifyOther, id, s.Epoch, tl0VerifySliceRoot(s), raw, b, 1, 1, tl0VerifyOrdinaryGas)
		tl0VerifyAssertControl(t, c, 2)
		tl0VerifyAssertHeadEqual(t, e.head(id), before)
	})
	t.Run("28-epoch-and-stale-root-cas-preserve-live-head", func(t *testing.T) {
		e, id, s, b, before := fresh(t, "cas-epoch")
		defer e.close()
		_, _, c := e.resume(tl0VerifyOwner, id, s.Epoch+1, tl0VerifySliceRoot(s), raw, b, 1, 1, tl0VerifyOrdinaryGas)
		tl0VerifyAssertControl(t, c, 3)
		_, _, c = e.resume(tl0VerifyOwner, id, s.Epoch, crypto.Keccak256Hash([]byte("stale")), raw, b, 1, 1, tl0VerifyOrdinaryGas)
		tl0VerifyAssertControl(t, c, 4)
		tl0VerifyAssertHeadEqual(t, e.head(id), before)
	})
	t.Run("29-exact-live-bytes-and-profile-namespace-bind", func(t *testing.T) {
		e, id, s, b, before := fresh(t, "cas-bytes")
		defer e.close()
		changed := append([]byte(nil), b...)
		changed[52] ^= 1
		tl0VerifyValidateOK(t, e, raw, changed)
		_, _, c := e.resume(tl0VerifyOwner, id, s.Epoch, tl0VerifySliceRoot(s), raw, changed, 1, 1, tl0VerifyOrdinaryGas)
		tl0VerifyAssertControl(t, c, 4)
		tl0VerifyAssertHeadEqual(t, e.head(id), before)
		old, err := lc0transport.NewMemory(tl0VerifyOwner)
		if err != nil {
			t.Fatal(err)
		}
		defer old.Close()
		oldResult, err := old.Start(tl0VerifyInstance("lc0-blob"), raw, "TLCAS", "run", nil, 1, 1, tl0VerifyOrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
		cross := tl0VerifyValidate(e, raw, oldResult.Checkpoint, tl0VerifyBoundaryGas)
		if code, _, ok := tl0VerifyStateError(cross.output); cross.err == nil || !ok || code != 3 {
			t.Fatalf("TL0 accepted/misclassified LC0 blob: %v %x", cross.err, cross.output)
		}
	})
	t.Run("30-genuine-oog-has-no-java-result-log-or-publication", func(t *testing.T) {
		e, id, s, b, before := fresh(t, "cas-oog")
		defer e.close()
		_, _, c := e.resume(tl0VerifyOwner, id, s.Epoch, tl0VerifySliceRoot(s), raw, b, 1, 1, 1)
		if !errors.Is(c.err, vm.ErrOutOfGas) || len(c.output) != 0 || len(c.logs) != 0 {
			t.Fatalf("OOG shape err=%v data=%x logs=%d", c.err, c.output, len(c.logs))
		}
		tl0VerifyAssertHeadEqual(t, e.head(id), before)
		memory, err := NewMemory(tl0VerifyOwner)
		if err != nil {
			t.Fatal(err)
		}
		defer memory.Close()
		failed, err := memory.Start(tl0VerifyInstance("session-oog"), raw, "TLCAS", "run", nil, 1, 1, 1)
		if err == nil || len(failed.Checkpoint) != 0 || len(failed.Logs) != 0 || failed.Slice.CheckpointRoot != (common.Hash{}) {
			t.Fatalf("speculative Session output err=%v result=%+v", err, failed)
		}
	})
	t.Run("31-rollback-then-retry-matches-control-child-byte-for-byte", func(t *testing.T) {
		e, id, s, b, before := fresh(t, "cas-retry")
		defer e.close()
		snap := e.state.Snapshot()
		control, controlBlob, cc := e.resume(tl0VerifyOwner, id, s.Epoch, tl0VerifySliceRoot(s), raw, b, 1, 4096, tl0VerifyOrdinaryGas)
		tl0VerifyAssertSuccess(t, control, controlBlob, cc)
		e.state.RevertToSnapshot(snap)
		tl0VerifyAssertHeadEqual(t, e.head(id), before)
		_, _, reserve := e.resume(tl0VerifyOwner, id, s.Epoch, tl0VerifySliceRoot(s), raw, b, 1, 4096, tl0VerifyReserveGas+500000)
		tl0VerifyAssertControl(t, reserve, 7)
		tl0VerifyAssertHeadEqual(t, e.head(id), before)
		retry, retryBlob, rc := e.resume(tl0VerifyOwner, id, s.Epoch, tl0VerifySliceRoot(s), raw, b, 1, 4096, tl0VerifyOrdinaryGas)
		tl0VerifyAssertSuccess(t, retry, retryBlob, rc)
		if !reflect.DeepEqual(retry, control) || !bytes.Equal(retryBlob, controlBlob) {
			t.Fatal("retry child differs from control")
		}
	})
	t.Run("32-real-new-process-reopen-and-cross-namespace-store-refusal", func(t *testing.T) {
		restart := tl0VerifyCompileTrusted(t, map[string]string{"TLRestart.java": `public final class TLRestart {static final class P extends RuntimeException{}public static int run(){P p=new P();try{throw p;}catch(P q){return p==q?32:0;}}}`}, []string{"TLRestart", "TLRestart$P"})
		rawRestart := tl0VerifyRaw(restart, "TLRestart") // Root's only dependency is emitted as a nested class and is loaded as a supplied class below.
		// Include the nested class while starting, but persist both raw bytes in one
		// compact helper bundle file with an explicit length prefix.
		rawRestart = append(rawRestart, restart["TLRestart$P"])
		dir := filepath.Join(t.TempDir(), "store")
		session, err := Open(dir, tl0VerifyOwner)
		if err != nil {
			t.Fatal(err)
		}
		id := tl0VerifyInstance("new-process")
		r, err := session.Start(id, rawRestart, "TLRestart", "run", nil, 1, 1, tl0VerifyOrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
		for n := 0; n < 128; n++ {
			cp, err := tl0VerifyDecodeCheckpoint(r.Checkpoint)
			if err != nil {
				t.Fatal(err)
			}
			if cp.Machine.PendingActive == 1 {
				break
			}
			if r.Slice.Lifecycle != tl0VerifyRunnable {
				t.Fatal("terminal before pending restart point")
			}
			r, err = session.Resume(id, r.Slice.Epoch, r.Slice.CheckpointRoot, rawRestart, r.Checkpoint, 1, 1, tl0VerifyOrdinaryGas)
			if err != nil {
				t.Fatal(err)
			}
		}
		if err := session.Close(); err != nil {
			t.Fatal(err)
		}
		// The subprocess reads an exact length-prefixed bundle; generate a tiny
		// helper Go test input by placing classes in a directory and passing both.
		bundleDir := t.TempDir()
		paths := make([]string, len(rawRestart))
		for i, b := range rawRestart {
			paths[i] = filepath.Join(bundleDir, fmt.Sprintf("%d.class", i))
			if err := os.WriteFile(paths[i], b, 0600); err != nil {
				t.Fatal(err)
			}
		}
		resultPath := filepath.Join(t.TempDir(), "result.json")
		ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
		defer cancel()
		cmd := exec.CommandContext(ctx, os.Args[0], "-test.run=^TestTL0VerifyReopenBundleHelperProcess$", "-test.timeout=125s")
		cmd.Env = append(os.Environ(), "TL0_VERIFY_BUNDLE_HELPER=1", "TL0_VERIFY_DIRECTORY="+dir, "TL0_VERIFY_INSTANCE="+id.Hex(), "TL0_VERIFY_CLASSES="+strings.Join(paths, string(os.PathListSeparator)), "TL0_VERIFY_RESULT="+resultPath)
		out, err := cmd.CombinedOutput()
		if err != nil {
			t.Fatalf("new process: %v\n%s", err, out)
		}
		var child tl0VerifyProcessResult
		encoded, err := os.ReadFile(resultPath)
		if err != nil {
			t.Fatal(err)
		}
		if err = json.Unmarshal(encoded, &child); err != nil {
			t.Fatal(err)
		}
		if child.Lifecycle != tl0VerifyReturned || child.Result != 32 || child.Epoch <= r.Slice.Epoch {
			t.Fatalf("child=%+v", child)
		}
		reopened, err := Open(dir, tl0VerifyOwner)
		if err != nil {
			t.Fatal(err)
		}
		h, err := reopened.Head(id)
		reopened.Close()
		if err != nil || h.CheckpointRoot != child.Root || h.Lifecycle != tl0VerifyReturned {
			t.Fatalf("durable head=%+v err=%v", h, err)
		}
		lcdir := filepath.Join(t.TempDir(), "lc0-store")
		old, err := lc0transport.Open(lcdir, tl0VerifyOwner)
		if err != nil {
			t.Fatal(err)
		}
		old.Close()
		if wrong, err := Open(lcdir, tl0VerifyOwner); err == nil {
			wrong.Close()
			t.Fatal("TL0 accepted LC0 disk namespace")
		}
		if old, err := lc0transport.Open(dir, tl0VerifyOwner); err == nil {
			old.Close()
			t.Fatal("LC0 accepted TL0 disk namespace")
		}
	})
}

func TestTL0VerifyReopenBundleHelperProcess(t *testing.T) {
	if os.Getenv("TL0_VERIFY_BUNDLE_HELPER") != "1" {
		return
	}
	parts := strings.Split(os.Getenv("TL0_VERIFY_CLASSES"), string(os.PathListSeparator))
	raw := make([][]byte, len(parts))
	for i, p := range parts {
		b, err := os.ReadFile(p)
		if err != nil {
			t.Fatal(err)
		}
		raw[i] = b
	}
	dir := os.Getenv("TL0_VERIFY_DIRECTORY")
	id := common.HexToHash(os.Getenv("TL0_VERIFY_INSTANCE"))
	s, err := Open(dir, tl0VerifyOwner)
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()
	h, err := s.Head(id)
	if err != nil {
		t.Fatal(err)
	}
	var result int32
	for n := 0; h.Lifecycle == tl0VerifyRunnable; n++ {
		if n >= 256 {
			t.Fatal("slice cap")
		}
		blob, err := s.ReadCheckpoint(h.CheckpointRoot)
		if err != nil {
			t.Fatal(err)
		}
		r, err := s.Resume(id, h.Epoch, h.CheckpointRoot, raw, blob, 7, 1, tl0VerifyOrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
		result = r.Slice.Result
		h, err = s.Head(id)
		if err != nil {
			t.Fatal(err)
		}
	}
	encoded, _ := json.Marshal(tl0VerifyProcessResult{h.Lifecycle, result, h.Epoch, h.CheckpointRoot})
	if err := os.WriteFile(os.Getenv("TL0_VERIFY_RESULT"), encoded, 0600); err != nil {
		t.Fatal(err)
	}
}
