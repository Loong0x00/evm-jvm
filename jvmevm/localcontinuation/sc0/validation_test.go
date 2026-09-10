// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.
//
// Independent verifier for the frozen LOCAL MC-SC0 continuation profile. The
// decoder in this file is test-only: production Go continues to transport the
// checkpoint as opaque bytes and never evaluates Java state.
package sc0

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
	tl0transport "github.com/ethereum/go-ethereum/jvmevm/localcontinuation/tl0"
)

const (
	sc0VerifyOrdinaryGas = uint64(100_000_000)
	sc0VerifyBoundaryGas = uint64(1_000_000_000)
	sc0VerifyReserveGas  = uint64(25_000_000)
	sc0VerifyMaxBlob     = 1 << 20
	sc0VerifyHeaderSize  = 216

	sc0VerifyRunnable = uint8(1)
	sc0VerifyReturned = uint8(2)
	sc0VerifyUncaught = uint8(3)
)

var (
	sc0VerifyOwner = common.HexToAddress("0x0000000000000000000000000000000000007101")
	sc0VerifyOther = common.HexToAddress("0x0000000000000000000000000000000000007102")
	sc0VerifyAt    = common.HexToAddress("0x4a564d45564d53433052554e54494d4500000001")
)

type sc0VerifySlice struct {
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

type sc0VerifyHead struct {
	Owner           common.Address
	Epoch           uint64
	CheckpointRoot  common.Hash
	MachineRoot     common.Hash
	ArtifactRoot    common.Hash
	ConfigRoot      common.Hash
	RuntimeCodeHash common.Hash
	Lifecycle       uint8
}

type sc0VerifyCall struct {
	output []byte
	left   uint64
	err    error
	logs   []*types.Log
}

type sc0VerifyEnv struct {
	t        *testing.T
	state    *state.StateDB
	code     []byte
	contract abi.ABI
	calls    uint64
}

func sc0VerifyNewEnv(t *testing.T) *sc0VerifyEnv {
	t.Helper()
	code, err := Runtime()
	if err != nil {
		t.Fatalf("load SC0 runtime (runtime integration dependency absent): %v", err)
	}
	contract, err := ABI()
	if err != nil {
		t.Fatalf("load SC0 ABI: %v", err)
	}
	st, err := state.New(types.EmptyRootHash, state.NewDatabaseForTesting())
	if err != nil {
		t.Fatal(err)
	}
	st.CreateAccount(sc0VerifyAt)
	st.SetCode(sc0VerifyAt, code, tracing.CodeChangeUnspecified)
	return &sc0VerifyEnv{t: t, state: st, code: code, contract: contract}
}

func (e *sc0VerifyEnv) close() { e.state.Database().TrieDB().Close() }

func (e *sc0VerifyEnv) callAs(owner common.Address, gas uint64, method string, args ...any) sc0VerifyCall {
	e.t.Helper()
	input, err := e.contract.Pack(method, args...)
	if err != nil {
		e.t.Fatalf("pack %s: %v", method, err)
	}
	e.calls++
	txHash := crypto.Keccak256Hash([]byte("SC0 verifier call"), new(big.Int).SetUint64(e.calls).Bytes())
	e.state.SetTxContext(txHash, 0)
	start := time.Now()
	output, left, callErr := runtime.Call(sc0VerifyAt, input, &runtime.Config{
		State: e.state, Origin: owner, GasLimit: gas,
		BlockNumber: big.NewInt(1), Time: 1,
	})
	limit := 30 * time.Second
	if gas > sc0VerifyOrdinaryGas {
		limit = 120 * time.Second
	}
	if elapsed := time.Since(start); elapsed > limit {
		e.t.Fatalf("%s call exceeded LOCAL watchdog: %s > %s", method, elapsed, limit)
	}
	logs := append([]*types.Log(nil), e.state.GetLogs(txHash, 1, common.Hash{}, 1)...)
	return sc0VerifyCall{append([]byte(nil), output...), left, callErr, logs}
}

func (e *sc0VerifyEnv) start(owner common.Address, instance common.Hash, raw [][]byte, entryClass, entry string, args []int32, jvm uint64, internal uint32, gas uint64) (sc0VerifySlice, []byte, sc0VerifyCall) {
	e.t.Helper()
	c := e.callAs(owner, gas, "start", instance, raw, entryClass, entry, args, jvm, internal)
	if c.err != nil {
		return sc0VerifySlice{}, nil, c
	}
	values, err := e.contract.Methods["start"].Outputs.Unpack(c.output)
	if err != nil || len(values) != 2 {
		e.t.Fatalf("decode start outputs=%d: %v (%x)", len(values), err, c.output)
	}
	s := *abi.ConvertType(values[0], new(sc0VerifySlice)).(*sc0VerifySlice)
	return s, append([]byte(nil), values[1].([]byte)...), c
}

func (e *sc0VerifyEnv) resume(owner common.Address, instance common.Hash, epoch uint64, root common.Hash, raw [][]byte, checkpoint []byte, jvm uint64, internal uint32, gas uint64) (sc0VerifySlice, []byte, sc0VerifyCall) {
	e.t.Helper()
	c := e.callAs(owner, gas, "resume", instance, epoch, root, raw, checkpoint, jvm, internal)
	if c.err != nil {
		return sc0VerifySlice{}, nil, c
	}
	values, err := e.contract.Methods["resume"].Outputs.Unpack(c.output)
	if err != nil || len(values) != 2 {
		e.t.Fatalf("decode resume outputs=%d: %v (%x)", len(values), err, c.output)
	}
	s := *abi.ConvertType(values[0], new(sc0VerifySlice)).(*sc0VerifySlice)
	return s, append([]byte(nil), values[1].([]byte)...), c
}

func (e *sc0VerifyEnv) head(instance common.Hash) sc0VerifyHead {
	e.t.Helper()
	c := e.callAs(sc0VerifyOwner, sc0VerifyOrdinaryGas, "head", instance)
	if c.err != nil {
		e.t.Fatalf("head: %v data=%x", c.err, c.output)
	}
	v, err := e.contract.Methods["head"].Outputs.Unpack(c.output)
	if err != nil || len(v) != 8 {
		e.t.Fatalf("decode head: %v values=%d", err, len(v))
	}
	return sc0VerifyHead{v[0].(common.Address), v[1].(uint64), common.Hash(v[2].([32]byte)), common.Hash(v[3].([32]byte)), common.Hash(v[4].([32]byte)), common.Hash(v[5].([32]byte)), common.Hash(v[6].([32]byte)), v[7].(uint8)}
}

func sc0VerifySliceRoot(s sc0VerifySlice) common.Hash   { return common.Hash(s.CheckpointRoot) }
func sc0VerifyMachineRoot(s sc0VerifySlice) common.Hash { return common.Hash(s.MachineStateRoot) }

func sc0VerifyAssertSuccess(t *testing.T, s sc0VerifySlice, checkpoint []byte, c sc0VerifyCall) {
	t.Helper()
	if c.err != nil || len(c.logs) != 1 {
		t.Fatalf("successful slice err=%v data=%x left=%d logs=%d", c.err, c.output, c.left, len(c.logs))
	}
	if s.Schema != 1 || s.Epoch == 0 || s.Lifecycle < sc0VerifyRunnable || s.Lifecycle > sc0VerifyUncaught || len(checkpoint) < sc0VerifyHeaderSize || len(checkpoint) > sc0VerifyMaxBlob {
		t.Fatalf("noncanonical slice=%+v checkpoint=%d", s, len(checkpoint))
	}
	if crypto.Keccak256Hash(checkpoint) != sc0VerifySliceRoot(s) {
		t.Fatal("checkpointRoot is not keccak(exact checkpoint)")
	}
	if s.Lifecycle == sc0VerifyRunnable && (s.Result != 0 || s.JavaKind != 0 || s.JavaRef != 0 || len(s.JavaClass) != 0) {
		t.Fatalf("RUNNABLE leaked terminal output: %+v", s)
	}
	if s.Lifecycle == sc0VerifyReturned && (s.JavaKind != 0 || s.JavaRef != 0 || len(s.JavaClass) != 0) {
		t.Fatalf("RETURNED has Java exception output: %+v", s)
	}
	if s.Lifecycle == sc0VerifyUncaught && (s.Result != 0 || s.JavaRef == 0 || (s.JavaKind == 0) == (len(s.JavaClass) == 0)) {
		t.Fatalf("UNCAUGHT outcome shape is not canonical: %+v", s)
	}
}

func sc0VerifyCustomError(signature string, words ...uint64) []byte {
	out := append([]byte(nil), crypto.Keccak256([]byte(signature))[:4]...)
	for _, value := range words {
		var word [32]byte
		binary.BigEndian.PutUint64(word[24:], value)
		out = append(out, word[:]...)
	}
	return out
}

func sc0VerifyAssertControl(t *testing.T, c sc0VerifyCall, code uint64) {
	t.Helper()
	if !errors.Is(c.err, vm.ErrExecutionReverted) || !bytes.Equal(c.output, sc0VerifyCustomError("LC0ControlError(uint256)", code)) || len(c.logs) != 0 {
		t.Fatalf("want LC0ControlError(%d), err=%v data=%x logs=%d", code, c.err, c.output, len(c.logs))
	}
}

func sc0VerifyStateError(data []byte) (code, offset uint64, ok bool) {
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

func sc0VerifyAssertState(t *testing.T, c sc0VerifyCall, code uint64, offsets ...uint64) {
	t.Helper()
	got, off, ok := sc0VerifyStateError(c.output)
	if !errors.Is(c.err, vm.ErrExecutionReverted) || !ok || got != code || len(c.logs) != 0 {
		t.Fatalf("want LC0StateError(%d,*), got %d/%d/%v err=%v data=%x logs=%d", code, got, off, ok, c.err, c.output, len(c.logs))
	}
	if len(offsets) != 0 && off != offsets[0] {
		t.Fatalf("LC0StateError offset=%d want=%d", off, offsets[0])
	}
}

func sc0VerifyAssertHeadEqual(t *testing.T, have, want sc0VerifyHead) {
	t.Helper()
	if !reflect.DeepEqual(have, want) {
		t.Fatalf("head changed\nhave %+v\nwant %+v", have, want)
	}
}

// sc0VerifyReader decodes the exact custom 216-byte envelope and flat machine
// stream. It deliberately has no connection to Session.Start/Resume.
type sc0VerifyReader struct {
	b []byte
	p int
}

func (r *sc0VerifyReader) take(n int) ([]byte, error) {
	if n < 0 || r.p > len(r.b) || n > len(r.b)-r.p {
		return nil, fmt.Errorf("truncated at %d need %d", r.p, n)
	}
	v := r.b[r.p : r.p+n]
	r.p += n
	return v, nil
}
func (r *sc0VerifyReader) u8() (uint8, error) {
	b, e := r.take(1)
	if e != nil {
		return 0, e
	}
	return b[0], nil
}
func (r *sc0VerifyReader) u16() (uint16, error) {
	b, e := r.take(2)
	if e != nil {
		return 0, e
	}
	return binary.BigEndian.Uint16(b), nil
}
func (r *sc0VerifyReader) u32() (uint32, error) {
	b, e := r.take(4)
	if e != nil {
		return 0, e
	}
	return binary.BigEndian.Uint32(b), nil
}
func (r *sc0VerifyReader) u64() (uint64, error) {
	b, e := r.take(8)
	if e != nil {
		return 0, e
	}
	return binary.BigEndian.Uint64(b), nil
}

type sc0VerifyFrame struct {
	Offset, FlagsOffset, SPOffset, BitmapOffset int
	Class, Method                               uint16
	PC                                          uint32
	CallPC                                      *big.Int
	Flags                                       uint8
	This                                        uint32
	SP, Locals                                  uint16
	StackOffsets, LocalOffsets                  []int
}
type sc0VerifyHeapRecord struct {
	Offset, HandleOffset, MetadataOffset, ClassOffset, RankOffset, CountOffset int
	Handle                                                                     uint32
	Metadata                                                                   *big.Int
	Class                                                                      uint16
	Rank                                                                       uint8
	Count                                                                      uint32
	CellOffsets                                                                []int
	Object                                                                     bool
}
type sc0VerifyMachine struct {
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
	Frames                                                              []sc0VerifyFrame
	HeapHeaderOffset                                                    int
	NextHandle                                                          uint32
	OrdinaryObjects, OrdinaryArrays                                     uint16
	OrdinaryElements, OrdinaryFields                                    uint32
	EmergencyRef                                                        uint32
	ExceptionObjects                                                    uint16
	ExceptionFields                                                     uint32
	Heap                                                                []sc0VerifyHeapRecord
	PendingOffset, PendingKindOffset, PendingRefOffset, PendingPCOffset int
	PendingActive, PendingKind                                          uint8
	PendingRef                                                          uint32
	PendingPC                                                           *big.Int
	CauseCountOffset                                                    int
	CauseWrapperOffsets, CauseRefOffsets                                []int
	InternCountOffset                                                   int
	InternHandleOffsets, InternHashOffsets                              []int
}
type sc0VerifyCheckpoint struct {
	Bytes                                          []byte
	Schema                                         uint32
	Instance                                       common.Hash
	Epoch                                          uint64
	Parent, Runtime, Artifact, Config, MachineRoot common.Hash
	MachineLength                                  uint32
	Machine                                        sc0VerifyMachine
}

func sc0VerifyReadASCII(r *sc0VerifyReader) (string, error) {
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

func sc0VerifyDecodeCheckpoint(blob []byte) (sc0VerifyCheckpoint, error) {
	var c sc0VerifyCheckpoint
	c.Bytes = append([]byte(nil), blob...)
	if len(blob) < sc0VerifyHeaderSize {
		return c, fmt.Errorf("short header")
	}
	if string(blob[:8]) != "JVMSC001" {
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
	if c.Schema != 1 || int(c.MachineLength) != len(blob)-sc0VerifyHeaderSize || len(blob) > sc0VerifyMaxBlob {
		return c, fmt.Errorf("header length/schema")
	}
	r := &sc0VerifyReader{b: blob[sc0VerifyHeaderSize:]}
	if b, e := r.take(4); e != nil || string(b) != "SCS1" {
		return c, fmt.Errorf("machine magic")
	}
	m := sc0VerifyMachine{}
	m.LifecycleOffset = sc0VerifyHeaderSize + r.p
	m.Lifecycle, _ = r.u8()
	m.ResultOffset = sc0VerifyHeaderSize + r.p
	b, e := r.take(4)
	if e != nil {
		return c, e
	}
	m.Result = int32(binary.BigEndian.Uint32(b))
	m.JavaKindOffset = sc0VerifyHeaderSize + r.p
	m.JavaKind, _ = r.u8()
	m.JavaRefOffset = sc0VerifyHeaderSize + r.p
	m.JavaRef, _ = r.u32()
	m.TotalJvmOffset = sc0VerifyHeaderSize + r.p
	m.TotalJvm, _ = r.u64()
	m.TotalInternalOffset = sc0VerifyHeaderSize + r.p
	m.TotalInternal, _ = r.u64()
	if m.EntryClass, e = sc0VerifyReadASCII(r); e != nil {
		return c, e
	}
	if m.Entry, e = sc0VerifyReadASCII(r); e != nil {
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
		m.ClassOffsets = append(m.ClassOffsets, sc0VerifyHeaderSize+r.p)
		m.InitOffsets = append(m.InitOffsets, sc0VerifyHeaderSize+r.p)
		if _, e = r.u8(); e != nil {
			return c, e
		}
		m.StartedOffsets = append(m.StartedOffsets, sc0VerifyHeaderSize+r.p)
		if _, e = r.u8(); e != nil {
			return c, e
		}
		n, e := r.u16()
		if e != nil {
			return c, e
		}
		var indices, vals []int
		for j := 0; j < int(n); j++ {
			indices = append(indices, sc0VerifyHeaderSize+r.p)
			if _, e = r.u16(); e != nil {
				return c, e
			}
			vals = append(vals, sc0VerifyHeaderSize+r.p)
			if _, e = r.take(32); e != nil {
				return c, e
			}
		}
		m.StaticIndexOffsets = append(m.StaticIndexOffsets, indices)
		m.StaticValueOffsets = append(m.StaticValueOffsets, vals)
	}
	m.FrameCountOffset = sc0VerifyHeaderSize + r.p
	frames, e := r.u16()
	if e != nil {
		return c, e
	}
	for i := 0; i < int(frames); i++ {
		f := sc0VerifyFrame{Offset: sc0VerifyHeaderSize + r.p}
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
		f.FlagsOffset = sc0VerifyHeaderSize + r.p
		f.Flags, e = r.u8()
		if e != nil {
			return c, e
		}
		f.This, e = r.u32()
		if e != nil {
			return c, e
		}
		f.SPOffset = sc0VerifyHeaderSize + r.p
		f.SP, e = r.u16()
		if e != nil {
			return c, e
		}
		for j := 0; j < int(f.SP); j++ {
			f.StackOffsets = append(f.StackOffsets, sc0VerifyHeaderSize+r.p)
			if _, e = r.take(32); e != nil {
				return c, e
			}
		}
		f.Locals, e = r.u16()
		if e != nil {
			return c, e
		}
		f.BitmapOffset = sc0VerifyHeaderSize + r.p
		if _, e = r.take((int(f.Locals) + 7) / 8); e != nil {
			return c, e
		}
		for j := 0; j < int(f.Locals); j++ {
			f.LocalOffsets = append(f.LocalOffsets, sc0VerifyHeaderSize+r.p)
			if _, e = r.take(32); e != nil {
				return c, e
			}
		}
		m.Frames = append(m.Frames, f)
	}
	m.HeapHeaderOffset = sc0VerifyHeaderSize + r.p
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
		h := sc0VerifyHeapRecord{Offset: sc0VerifyHeaderSize + r.p, HandleOffset: sc0VerifyHeaderSize + r.p}
		h.Handle, e = r.u32()
		if e != nil {
			return c, e
		}
		h.MetadataOffset = sc0VerifyHeaderSize + r.p
		b, e = r.take(32)
		if e != nil {
			return c, e
		}
		h.Metadata = new(big.Int).SetBytes(b)
		h.Object = len(b) > 0 && b[0]&0x80 != 0
		h.ClassOffset = sc0VerifyHeaderSize + r.p
		h.Class, e = r.u16()
		if e != nil {
			return c, e
		}
		h.RankOffset = sc0VerifyHeaderSize + r.p
		h.Rank, e = r.u8()
		if e != nil {
			return c, e
		}
		h.CountOffset = sc0VerifyHeaderSize + r.p
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
			h.CellOffsets = append(h.CellOffsets, sc0VerifyHeaderSize+r.p)
			if _, e = r.take(width); e != nil {
				return c, e
			}
		}
		m.Heap = append(m.Heap, h)
	}
	m.PendingOffset = sc0VerifyHeaderSize + r.p
	m.PendingActive, e = r.u8()
	if e != nil {
		return c, e
	}
	m.PendingKindOffset = sc0VerifyHeaderSize + r.p
	m.PendingKind, e = r.u8()
	if e != nil {
		return c, e
	}
	m.PendingRefOffset = sc0VerifyHeaderSize + r.p
	m.PendingRef, e = r.u32()
	if e != nil {
		return c, e
	}
	m.PendingPCOffset = sc0VerifyHeaderSize + r.p
	b, e = r.take(32)
	if e != nil {
		return c, e
	}
	m.PendingPC = new(big.Int).SetBytes(b)
	m.CauseCountOffset = sc0VerifyHeaderSize + r.p
	causes, e := r.u16()
	if e != nil {
		return c, e
	}
	for i := 0; i < int(causes); i++ {
		m.CauseWrapperOffsets = append(m.CauseWrapperOffsets, sc0VerifyHeaderSize+r.p)
		if _, e = r.u32(); e != nil {
			return c, e
		}
		m.CauseRefOffsets = append(m.CauseRefOffsets, sc0VerifyHeaderSize+r.p)
		if _, e = r.u32(); e != nil {
			return c, e
		}
	}
	m.InternCountOffset = sc0VerifyHeaderSize + r.p
	interns, e := r.u16()
	if e != nil {
		return c, e
	}
	for i := 0; i < int(interns); i++ {
		m.InternHandleOffsets = append(m.InternHandleOffsets, sc0VerifyHeaderSize+r.p)
		if _, e = r.u32(); e != nil {
			return c, e
		}
		m.InternHashOffsets = append(m.InternHashOffsets, sc0VerifyHeaderSize+r.p)
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

func sc0VerifyABIHash(t *testing.T, typesText []string, values ...any) common.Hash {
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
func sc0VerifyArtifactRoot(t *testing.T, raw [][]byte) common.Hash {
	return sc0VerifyABIHash(t, []string{"bytes32", "bytes[]"}, crypto.Keccak256Hash([]byte("JVMEVM:MC:SC0:ARTIFACT:1")), raw)
}
func sc0VerifyBootstrapRoot(t *testing.T) common.Hash {
	t.Helper()
	names := []string{"Object", "Cloneable", "Serializable", "Float", "Double", "Throwable", "Error", "VirtualMachineError", "StackOverflowError", "OutOfMemoryError", "LinkageError", "ExceptionInInitializerError", "IncompatibleClassChangeError", "NoClassDefFoundError", "AbstractMethodError", "Exception", "RuntimeException", "ArithmeticException", "NullPointerException", "NegativeArraySizeException", "ClassCastException", "ArrayStoreException", "IndexOutOfBoundsException", "ArrayIndexOutOfBoundsException", "Comparable", "CharSequence", "String"}
	var hashes [27][32]byte
	for i, name := range names {
		path := filepath.Join("..", "..", "runtime", "bootstrap", name+".class.hex")
		if name == "String" {
			path = filepath.Join("..", "..", "runtime", "local", "sc0", "bootstrap", "java", "lang", "String.class.hex")
		}
		encoded, err := os.ReadFile(path)
		if err != nil {
			t.Fatal(err)
		}
		raw, err := hex.DecodeString(strings.TrimSpace(string(encoded)))
		if err != nil {
			t.Fatal(err)
		}
		hashes[i] = crypto.Keccak256Hash(raw)
	}
	return sc0VerifyABIHash(t, []string{"bytes32", "bytes32[27]"}, crypto.Keccak256Hash([]byte("JVMEVM:MC:SC0:BOOTSTRAP:1")), hashes)
}
func sc0VerifyConfigRoot(t *testing.T, runtimeHash, bootstrap, artifact common.Hash, entryClass, entry string, args []int32) common.Hash {
	return sc0VerifyABIHash(t, []string{"bytes32", "uint32", "bytes32", "bytes32", "bytes32", "string", "string", "int32[]"}, crypto.Keccak256Hash([]byte("JVMEVM:MC:SC0:CONFIG:1")), uint32(1), runtimeHash, bootstrap, artifact, entryClass, entry, args)
}
func sc0VerifyMachineStateRoot(t *testing.T, c sc0VerifyCheckpoint, machine []byte) common.Hash {
	return sc0VerifyABIHash(t, []string{"bytes32", "uint32", "bytes32", "bytes32", "bytes32"}, crypto.Keccak256Hash([]byte("JVMEVM:MC:SC0:MACHINE:1")), uint32(1), c.Artifact, c.Config, crypto.Keccak256Hash(machine))
}
func sc0VerifyRehashMachine(t *testing.T, blob []byte) []byte {
	t.Helper()
	out := append([]byte(nil), blob...)
	c, e := sc0VerifyDecodeCheckpoint(out)
	if e != nil {
		t.Fatal(e)
	}
	root := sc0VerifyMachineStateRoot(t, c, out[216:])
	copy(out[180:212], root[:])
	return out
}

func sc0VerifyValidate(e *sc0VerifyEnv, raw [][]byte, blob []byte, gas uint64) sc0VerifyCall {
	return e.callAs(sc0VerifyOwner, gas, "validateCheckpoint", raw, blob)
}

func sc0VerifyCheckEvent(t *testing.T, contract abi.ABI, instance common.Hash, s sc0VerifySlice, c sc0VerifyCall) {
	t.Helper()
	if len(c.logs) != 1 {
		t.Fatalf("events=%d", len(c.logs))
	}
	ev, ok := contract.Events["CheckpointCommitted"]
	if !ok {
		t.Fatal("event absent")
	}
	l := c.logs[0]
	if l.Address != sc0VerifyAt || len(l.Topics) != 3 || l.Topics[0] != ev.ID || common.Hash(l.Topics[1]) != instance || new(big.Int).SetBytes(l.Topics[2][:]).Uint64() != s.Epoch {
		t.Fatalf("bad topics=%v", l.Topics)
	}
	v, err := ev.Inputs.NonIndexed().Unpack(l.Data)
	if err != nil {
		t.Fatal(err)
	}
	if common.Hash(v[0].([32]byte)) != sc0VerifySliceRoot(s) || common.Hash(v[1].([32]byte)) != sc0VerifyMachineRoot(s) || v[2].(uint8) != s.Lifecycle || v[3].(uint64) != s.TotalJvmSteps || v[4].(uint64) != s.TotalInternalSteps {
		t.Fatalf("bad event data=%v slice=%+v", v, s)
	}
}

// Everything below is an independent verifier corpus. javac only creates trusted
// raw Java 8 inputs; every asserted semantic result is produced by runtime.Call
// into String0Interpreter. No host JVM evaluates a root.
func sc0VerifyCompileTrusted(t *testing.T, sources map[string]string, names []string) map[string][]byte {
	t.Helper()
	base := filepath.Join("..", "..", "..", "build", "java-diff-mc-sc0-verifier")
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

func sc0VerifyRaw(classes map[string][]byte, names ...string) [][]byte {
	out := make([][]byte, len(names))
	for i, name := range names {
		out[i] = classes[name]
	}
	return out
}

func sc0VerifyInstance(label string) common.Hash {
	return crypto.Keccak256Hash([]byte("JVMEVM:MC:SC0:VERIFY:" + label))
}

type sc0VerifyRun struct {
	slice sc0VerifySlice
	blob  []byte
	snaps []sc0VerifyCheckpoint
}

func sc0VerifyRunToEnd(t *testing.T, e *sc0VerifyEnv, label string, raw [][]byte, class, method string, jvm uint64, internal uint32, gas uint64, dispatchCap uint64) sc0VerifyRun {
	t.Helper()
	id := sc0VerifyInstance(label)
	s, blob, call := e.start(sc0VerifyOwner, id, raw, class, method, nil, jvm, internal, gas)
	sc0VerifyAssertSuccess(t, s, blob, call)
	r := sc0VerifyRun{slice: s, blob: blob}
	for slices := 0; ; slices++ {
		cp, err := sc0VerifyDecodeCheckpoint(blob)
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
		if s.Lifecycle != sc0VerifyRunnable {
			break
		}
		s, blob, call = e.resume(sc0VerifyOwner, id, s.Epoch, sc0VerifySliceRoot(s), raw, blob, jvm, internal, gas)
		sc0VerifyAssertSuccess(t, s, blob, call)
		r.slice, r.blob = s, blob
	}
	return r
}

func sc0VerifyCauseMap(cp sc0VerifyCheckpoint) map[uint32]uint32 {
	out := make(map[uint32]uint32)
	for i, off := range cp.Machine.CauseWrapperOffsets {
		out[binary.BigEndian.Uint32(cp.Bytes[off:off+4])] = binary.BigEndian.Uint32(cp.Bytes[cp.Machine.CauseRefOffsets[i] : cp.Machine.CauseRefOffsets[i]+4])
	}
	return out
}

func sc0VerifyHeapByRef(cp sc0VerifyCheckpoint, ref uint32) (sc0VerifyHeapRecord, bool) {
	for _, h := range cp.Machine.Heap {
		if h.Handle == ref {
			return h, true
		}
	}
	return sc0VerifyHeapRecord{}, false
}

func sc0VerifyRequireReturned(t *testing.T, r sc0VerifyRun, want int32) {
	t.Helper()
	if r.slice.Lifecycle != sc0VerifyReturned || r.slice.Result != want || r.slice.JavaKind != 0 || r.slice.JavaRef != 0 || len(r.slice.JavaClass) != 0 {
		t.Fatalf("returned shape=%+v want=%d", r.slice, want)
	}
}

func sc0VerifyRequireUncaught(t *testing.T, r sc0VerifyRun, kind uint8, class string) {
	t.Helper()
	if r.slice.Lifecycle != sc0VerifyUncaught || r.slice.Result != 0 || r.slice.JavaKind != kind || r.slice.JavaRef == 0 || string(r.slice.JavaClass) != class {
		t.Fatalf("uncaught shape=%+v want kind=%d class=%q", r.slice, kind, class)
	}
	last := r.snaps[len(r.snaps)-1].Machine
	if len(last.Frames) != 0 || last.PendingActive != 1 || last.PendingRef != r.slice.JavaRef || last.PendingKind != kind {
		t.Fatalf("terminal pending does not retain exact ref: %+v", last)
	}
}

func sc0VerifyValidateOK(t *testing.T, e *sc0VerifyEnv, raw [][]byte, blob []byte) common.Hash {
	t.Helper()
	c := sc0VerifyValidate(e, raw, blob, sc0VerifyBoundaryGas)
	if c.err != nil {
		t.Fatalf("validate: %v data=%x", c.err, c.output)
	}
	v, err := e.contract.Methods["validateCheckpoint"].Outputs.Unpack(c.output)
	if err != nil || len(v) != 1 {
		t.Fatalf("validate output: %v/%d", err, len(v))
	}
	return common.Hash(v[0].([32]byte))
}

func sc0VerifyMutateRehash(t *testing.T, blob []byte, at int, mutate func([]byte)) []byte {
	t.Helper()
	cp, err := sc0VerifyDecodeCheckpoint(blob)
	if err != nil {
		t.Fatal(err)
	}
	out := append([]byte(nil), blob...)
	if at < sc0VerifyHeaderSize || at >= len(out) {
		t.Fatalf("mutation offset=%d len=%d", at, len(out))
	}
	mutate(out[at:])
	root := sc0VerifyMachineStateRoot(t, cp, out[sc0VerifyHeaderSize:])
	copy(out[180:212], root[:])
	return out
}

func sc0VerifyErrorSelector(data []byte, signature string) bool {
	return len(data) >= 4 && bytes.Equal(data[:4], crypto.Keccak256([]byte(signature))[:4])
}

// sc0VerifyValue decodes one flat TLS1/SCS1 tagged 256-bit value.  The low
// 64 bits are the payload and the next byte is the value tag.
func sc0VerifyValue(b []byte) (uint8, uint64) {
	v := new(big.Int).SetBytes(b[:32])
	return uint8(new(big.Int).Rsh(new(big.Int).Set(v), 64).Uint64()), v.Uint64()
}

func sc0VerifyPutValue(b []byte, tag uint8, payload uint64) {
	v := new(big.Int).Lsh(new(big.Int).SetUint64(uint64(tag)), 64)
	v.Or(v, new(big.Int).SetUint64(payload)).FillBytes(b[:32])
}

func sc0VerifyStringClass(raw [][]byte) uint16 { return uint16(len(raw) + 26) }

func sc0VerifyObject(cp sc0VerifyCheckpoint, class uint16) []sc0VerifyHeapRecord {
	var out []sc0VerifyHeapRecord
	for _, h := range cp.Machine.Heap {
		if h.Object && h.Class == class {
			out = append(out, h)
		}
	}
	return out
}

func sc0VerifyHeap(cp sc0VerifyCheckpoint, handle uint32) (sc0VerifyHeapRecord, bool) {
	for _, h := range cp.Machine.Heap {
		if h.Handle == handle {
			return h, true
		}
	}
	return sc0VerifyHeapRecord{}, false
}

func sc0VerifyInterns(cp sc0VerifyCheckpoint) ([]uint32, []uint32) {
	handles := make([]uint32, len(cp.Machine.InternHandleOffsets))
	hashes := make([]uint32, len(handles))
	for i := range handles {
		handles[i] = binary.BigEndian.Uint32(cp.Bytes[cp.Machine.InternHandleOffsets[i]:])
		hashes[i] = binary.BigEndian.Uint32(cp.Bytes[cp.Machine.InternHashOffsets[i]:])
	}
	return handles, hashes
}

func sc0VerifyJavaHash(units ...uint16) uint32 {
	var h uint32
	for _, u := range units {
		h = h*31 + uint32(u)
	}
	return h
}

func sc0VerifyAssertProfile(t *testing.T, c sc0VerifyCall, reason, pc uint64) {
	t.Helper()
	want := sc0VerifyCustomError("StringProfileError(uint256,uint256)", reason, pc)
	if !errors.Is(c.err, vm.ErrExecutionReverted) || !bytes.Equal(c.output, want) || len(c.logs) != 0 {
		t.Fatalf("want StringProfileError(%d,%d), err=%v data=%x logs=%d", reason, pc, c.err, c.output, len(c.logs))
	}
}

func sc0VerifyAssertHardSelector(t *testing.T, c sc0VerifyCall, signature string) {
	t.Helper()
	if !errors.Is(c.err, vm.ErrExecutionReverted) || !sc0VerifyErrorSelector(c.output, signature) || len(c.logs) != 0 {
		t.Fatalf("want %s revert, err=%v data=%x logs=%d", signature, c.err, c.output, len(c.logs))
	}
}

// sc0VerifyClassCode is a deliberately small classfile reader used only to find
// bytecode PCs and make same-length negative mutations in trusted fixtures.  It
// never participates in the production transport or execution path.
type sc0VerifyClassCode struct {
	codeOff  int
	code     []byte
	cpUTF    map[uint16]string
	cpUTFOff map[uint16]int
}

func sc0VerifyFindCode(t *testing.T, class []byte, method, descriptor string) sc0VerifyClassCode {
	t.Helper()
	if len(class) < 10 || binary.BigEndian.Uint32(class) != 0xcafebabe {
		t.Fatal("bad trusted class")
	}
	p, count := 10, int(binary.BigEndian.Uint16(class[8:10]))
	utf, uoff := map[uint16]string{}, map[uint16]int{}
	for i := 1; i < count; i++ {
		if p >= len(class) {
			t.Fatal("short cp")
		}
		tag := class[p]
		p++
		switch tag {
		case 1:
			n := int(binary.BigEndian.Uint16(class[p:]))
			p += 2
			uoff[uint16(i)] = p
			utf[uint16(i)] = string(class[p : p+n])
			p += n
		case 3, 4:
			p += 4
		case 5, 6:
			p += 8
			i++
		case 7, 8, 16:
			p += 2
		case 9, 10, 11, 12, 18:
			p += 4
		case 15:
			p += 3
		default:
			t.Fatalf("cp tag %d", tag)
		}
	}
	skipAttrs := func() {
		n := int(binary.BigEndian.Uint16(class[p:]))
		p += 2
		for i := 0; i < n; i++ {
			p += 2
			z := int(binary.BigEndian.Uint32(class[p:]))
			p += 4 + z
		}
	}
	p += 6
	ni := int(binary.BigEndian.Uint16(class[p:]))
	p += 2 + 2*ni
	fields := int(binary.BigEndian.Uint16(class[p:]))
	p += 2
	for i := 0; i < fields; i++ {
		p += 6
		skipAttrs()
	}
	methods := int(binary.BigEndian.Uint16(class[p:]))
	p += 2
	for i := 0; i < methods; i++ {
		p += 2
		name := utf[binary.BigEndian.Uint16(class[p:])]
		p += 2
		desc := utf[binary.BigEndian.Uint16(class[p:])]
		p += 2
		attrs := int(binary.BigEndian.Uint16(class[p:]))
		p += 2
		for j := 0; j < attrs; j++ {
			an := utf[binary.BigEndian.Uint16(class[p:])]
			p += 2
			z := int(binary.BigEndian.Uint32(class[p:]))
			p += 4
			if name == method && desc == descriptor && an == "Code" {
				co := p + 8
				clen := int(binary.BigEndian.Uint32(class[p+4:]))
				return sc0VerifyClassCode{co, class[co : co+clen], utf, uoff}
			}
			p += z
		}
	}
	t.Fatalf("method %s%s absent", method, descriptor)
	return sc0VerifyClassCode{}
}
func sc0VerifyOpcodePC(t *testing.T, class []byte, method, desc string, opcode byte, ordinal int) uint64 {
	c := sc0VerifyFindCode(t, class, method, desc)
	n := 0
	for i, b := range c.code {
		if b == opcode {
			if n == ordinal {
				return uint64(i)
			}
			n++
		}
	}
	t.Fatalf("opcode %02x[%d] absent in %s", opcode, ordinal, method)
	return 0
}

func sc0VerifyNewEnvWithCode(t *testing.T, code []byte) *sc0VerifyEnv {
	t.Helper()
	contract, err := ABI()
	if err != nil {
		t.Fatal(err)
	}
	st, err := state.New(types.EmptyRootHash, state.NewDatabaseForTesting())
	if err != nil {
		t.Fatal(err)
	}
	st.CreateAccount(sc0VerifyAt)
	st.SetCode(sc0VerifyAt, code, tracing.CodeChangeUnspecified)
	return &sc0VerifyEnv{t: t, state: st, code: append([]byte(nil), code...), contract: contract}
}

// sc0VerifySyntheticObject emits a small, structurally valid Java 8 Object
// class. It is intentionally EVM-profile-only. "publish" has a real putstatic
// callback and "fail" really throws its receiver; neither is run on a host JVM.
func sc0VerifySyntheticObject(t *testing.T, inheritedFields int, mode string) []byte {
	t.Helper()
	if inheritedFields < 0 || inheritedFields > 1023 {
		t.Fatal("synthetic Object field bound")
	}
	type cpEntry struct {
		tag  byte
		body []byte
	}
	utf := func(s string) cpEntry {
		var b bytes.Buffer
		binary.Write(&b, binary.BigEndian, uint16(len(s)))
		b.WriteString(s)
		return cpEntry{1, b.Bytes()}
	}
	entries := []cpEntry{{7, []byte{0, 2}}, utf("java/lang/Object"), utf("<init>"), utf("()V"), utf("Code"), utf("I")}
	fieldNames := make([]uint16, inheritedFields)
	for i := range fieldNames {
		fieldNames[i] = uint16(len(entries) + 1)
		entries = append(entries, utf(fmt.Sprintf("f%04d", i)))
	}
	var descriptor, fieldRef uint16
	if mode == "publish" {
		name := uint16(len(entries) + 1)
		entries = append(entries, utf("published"))
		descriptor = uint16(len(entries) + 1)
		entries = append(entries, utf("Ljava/lang/Object;"))
		nt := uint16(len(entries) + 1)
		entries = append(entries, cpEntry{12, []byte{byte(name >> 8), byte(name), byte(descriptor >> 8), byte(descriptor)}})
		fieldRef = uint16(len(entries) + 1)
		entries = append(entries, cpEntry{9, []byte{0, 1, byte(nt >> 8), byte(nt)}})
	}
	var out bytes.Buffer
	binary.Write(&out, binary.BigEndian, uint32(0xcafebabe))
	binary.Write(&out, binary.BigEndian, uint16(0))
	binary.Write(&out, binary.BigEndian, uint16(52))
	binary.Write(&out, binary.BigEndian, uint16(len(entries)+1))
	for _, e := range entries {
		out.WriteByte(e.tag)
		out.Write(e.body)
	}
	binary.Write(&out, binary.BigEndian, uint16(0x21))
	binary.Write(&out, binary.BigEndian, uint16(1))
	binary.Write(&out, binary.BigEndian, uint16(0))
	binary.Write(&out, binary.BigEndian, uint16(0))
	fieldCount := inheritedFields
	if mode == "publish" {
		fieldCount++
	}
	binary.Write(&out, binary.BigEndian, uint16(fieldCount))
	for _, name := range fieldNames {
		binary.Write(&out, binary.BigEndian, uint16(1))
		binary.Write(&out, binary.BigEndian, name)
		binary.Write(&out, binary.BigEndian, uint16(6))
		binary.Write(&out, binary.BigEndian, uint16(0))
	}
	if mode == "publish" {
		binary.Write(&out, binary.BigEndian, uint16(9))
		binary.Write(&out, binary.BigEndian, uint16(len(entries)-3))
		binary.Write(&out, binary.BigEndian, descriptor)
		binary.Write(&out, binary.BigEndian, uint16(0))
	}
	code := []byte{0xb1}
	maxStack := uint16(0)
	if mode == "publish" {
		code = []byte{0x2a, 0xb3, byte(fieldRef >> 8), byte(fieldRef), 0xb1}
		maxStack = 1
	}
	if mode == "fail" {
		code = []byte{0x2a, 0xbf}
		maxStack = 1
	}
	binary.Write(&out, binary.BigEndian, uint16(1))
	binary.Write(&out, binary.BigEndian, uint16(1))
	binary.Write(&out, binary.BigEndian, uint16(3))
	binary.Write(&out, binary.BigEndian, uint16(4))
	binary.Write(&out, binary.BigEndian, uint16(1))
	binary.Write(&out, binary.BigEndian, uint16(5))
	binary.Write(&out, binary.BigEndian, uint32(12+len(code)))
	binary.Write(&out, binary.BigEndian, maxStack)
	binary.Write(&out, binary.BigEndian, uint16(1))
	binary.Write(&out, binary.BigEndian, uint32(len(code)))
	out.Write(code)
	binary.Write(&out, binary.BigEndian, uint16(0))
	binary.Write(&out, binary.BigEndian, uint16(0))
	binary.Write(&out, binary.BigEndian, uint16(0))
	return out.Bytes()
}

func sc0VerifyFinal(t *testing.T, source, root, method string, names []string, jvm uint64, gas, cap uint64) (sc0VerifyRun, [][]byte) {
	t.Helper()
	classes := sc0VerifyCompileTrusted(t, map[string]string{root + ".java": source}, names)
	raw := sc0VerifyRaw(classes, names...)
	e := sc0VerifyNewEnv(t)
	defer e.close()
	return sc0VerifyRunToEnd(t, e, t.Name(), raw, root, method, jvm, 4096, gas, cap), raw
}

// 01..08 allocation, quota, layout, checkpoint and declared-bound probes.
func TestSC0VerifyAllocationQuotaAndLayout(t *testing.T) {
	construct := `public final class SCAlloc { static Object os; static char[] as;
	 public static int defensive(){char[] a={'a','e','l','l','o'};String s=new String(a);a[0]='X';return s.charAt(0)*1000+s.length()*19+4;}
	 public static int copy(){String a="copy";a.hashCode();String b=new String(a);return (a!=b&&a.hashCode()==b.hashCode())?1:0;}
	 public static int failed(){char[][] keep=new char[1022][];for(int i=0;i<1022;i++)keep[i]=new char[0];char[] src={'x'};try{new String(src);return 0;}catch(OutOfMemoryError ok){return 3;}}
	 public static int fullMiss(){String s=new String(new char[]{'m'});for(int i=1;i<1024;i++)os=new Object();for(int i=2;i<1024;i++)as=new char[0];return s.intern()==s?4:0;}
	 public static int fullHit(){String a="h";String b=new String(a);for(int i=2;i<1024;i++)os=new Object();for(int i=1;i<1024;i++)as=new char[0];return b.intern()==a?5:0;}
	}`
	classes := sc0VerifyCompileTrusted(t, map[string]string{"SCAlloc.java": construct}, []string{"SCAlloc"})
	raw := sc0VerifyRaw(classes, "SCAlloc")
	t.Run("01-defensive-copy-layout-and-accounting", func(t *testing.T) {
		e := sc0VerifyNewEnv(t)
		defer e.close()
		r := sc0VerifyRunToEnd(t, e, "01", raw, "SCAlloc", "defensive", 4096, 4096, sc0VerifyOrdinaryGas, 4096)
		sc0VerifyRequireReturned(t, r, 97099)
		m := r.snaps[len(r.snaps)-1].Machine
		if m.OrdinaryObjects != 1 || m.OrdinaryArrays != 2 || m.OrdinaryElements != 10 || m.OrdinaryFields != 2 {
			t.Fatalf("copy counters=%d/%d/%d/%d", m.OrdinaryObjects, m.OrdinaryArrays, m.OrdinaryElements, m.OrdinaryFields)
		}
	})
	t.Run("02-string-copy-shares-backing-and-allocates-no-array", func(t *testing.T) {
		e := sc0VerifyNewEnv(t)
		defer e.close()
		r := sc0VerifyRunToEnd(t, e, "02", raw, "SCAlloc", "copy", 1, 4096, sc0VerifyOrdinaryGas, 4096)
		sc0VerifyRequireReturned(t, r, 1)
		cp := r.snaps[len(r.snaps)-1]
		ss := sc0VerifyObject(cp, sc0VerifyStringClass(raw))
		if len(ss) != 2 || cp.Machine.OrdinaryArrays != 1 {
			t.Fatalf("strings=%d arrays=%d", len(ss), cp.Machine.OrdinaryArrays)
		}
		_, a := sc0VerifyValue(cp.Bytes[ss[0].CellOffsets[0]:])
		_, b := sc0VerifyValue(cp.Bytes[ss[1].CellOffsets[0]:])
		if a == 0 || a != b {
			t.Fatalf("copy backing=%d/%d", a, b)
		}
	})
	t.Run("03-failed-backing-allocation-leaves-charged-default-residue", func(t *testing.T) {
		e := sc0VerifyNewEnv(t)
		defer e.close()
		r := sc0VerifyRunToEnd(t, e, "03", raw, "SCAlloc", "failed", 4096, 4096, sc0VerifyBoundaryGas, 65536)
		sc0VerifyRequireReturned(t, r, 3)
		cp := r.snaps[len(r.snaps)-1]
		if cp.Machine.OrdinaryArrays != 1024 || cp.Machine.OrdinaryObjects != 1 {
			t.Fatalf("failed allocation counters=%d/%d", cp.Machine.OrdinaryArrays, cp.Machine.OrdinaryObjects)
		}
		ss := sc0VerifyObject(cp, sc0VerifyStringClass(raw))
		if len(ss) != 1 {
			t.Fatalf("residue strings=%d", len(ss))
		}
		tag, v := sc0VerifyValue(cp.Bytes[ss[0].CellOffsets[0]:])
		if tag != 2 || v != 0 {
			t.Fatalf("residue value tag/ref=%d/%d", tag, v)
		}
	})
	t.Run("04-full-heaps-admit-hit-and-smaller-pool-receiver-insertion", func(t *testing.T) {
		for _, tc := range []struct {
			m    string
			want int32
		}{{"fullMiss", 4}, {"fullHit", 5}} {
			e := sc0VerifyNewEnv(t)
			r := sc0VerifyRunToEnd(t, e, "04-"+tc.m, raw, "SCAlloc", tc.m, 4096, 4096, sc0VerifyBoundaryGas, 65536)
			e.close()
			sc0VerifyRequireReturned(t, r, tc.want)
			m := r.snaps[len(r.snaps)-1].Machine
			if m.OrdinaryObjects != 1024 || m.OrdinaryArrays != 1024 {
				t.Fatalf("%s heaps=%d/%d", tc.m, m.OrdinaryObjects, m.OrdinaryArrays)
			}
		}
	})
	t.Run("05-inherited-1024-fields-fit-and-1025-is-java-oom", func(t *testing.T) {
		fieldRoot := sc0VerifyCompileTrusted(t, map[string]string{"SCFields.java": `public final class SCFields {static int run(){try{String s=new String(new char[]{'f'});return s.length();}catch(OutOfMemoryError e){return 7;}}}`}, []string{"SCFields"})
		for _, tc := range []struct {
			fields int
			want   int32
			total  uint32
		}{{1022, 1, 1024}, {1023, 7, 0}} {
			rawFields := [][]byte{fieldRoot["SCFields"], sc0VerifySyntheticObject(t, tc.fields, "canonical")}
			e := sc0VerifyNewEnv(t)
			r := sc0VerifyRunToEnd(t, e, fmt.Sprintf("05-%d", tc.fields), rawFields, "SCFields", "run", 4096, 4096, sc0VerifyBoundaryGas, 65536)
			e.close()
			sc0VerifyRequireReturned(t, r, tc.want)
			m := r.snaps[len(r.snaps)-1].Machine
			if tc.total != 0 && m.OrdinaryFields != tc.total {
				t.Fatalf("%d inherited fields charged total=%d", tc.fields, m.OrdinaryFields)
			}
			if tc.total == 0 && (m.OrdinaryObjects != 0 || m.OrdinaryArrays != 0) {
				t.Fatalf("1025-field failed new changed allocation counters=%d/%d", m.OrdinaryObjects, m.OrdinaryArrays)
			}
		}
	})
	for _, tc := range []struct {
		name, method string
		fail         bool
	}{{"06-exact-one-mib-checkpoint", "abcdefg", false}, {"06-plus-one-rolls-back", "abcdefgh", true}} {
		t.Run(tc.name, func(t *testing.T) {
			source := fmt.Sprintf("public final class SCCap {public static int %s(){long[] a=new long[65536];long[] b=new long[65464];return a.length+b.length;}}", tc.method)
			c := sc0VerifyCompileTrusted(t, map[string]string{"SCCap.java": source}, []string{"SCCap"})
			rr := sc0VerifyRaw(c, "SCCap")
			e := sc0VerifyNewEnv(t)
			defer e.close()
			id := sc0VerifyInstance(tc.name)
			s, b, call := e.start(sc0VerifyOwner, id, rr, "SCCap", tc.method, nil, 4096, 4096, sc0VerifyBoundaryGas)
			if tc.fail {
				sc0VerifyAssertState(t, call, 1, 0)
				if e.head(id) != (sc0VerifyHead{}) {
					t.Fatal("oversize published")
				}
				return
			}
			sc0VerifyAssertSuccess(t, s, b, call)
			if len(b) != 1<<20 || s.Result != 131000 {
				t.Fatalf("checkpoint/result=%d/%d", len(b), s.Result)
			}
		})
	}
	t.Run("07-declared-over-cap-counters-rejected-read-only", func(t *testing.T) {
		e := sc0VerifyNewEnv(t)
		defer e.close()
		r := sc0VerifyRunToEnd(t, e, "07", raw, "SCAlloc", "defensive", 4096, 4096, sc0VerifyOrdinaryGas, 4096)
		cp := r.snaps[len(r.snaps)-1]
		mutations := []struct {
			off int
			put func([]byte)
		}{{cp.Machine.HeapHeaderOffset + 4, func(b []byte) { binary.BigEndian.PutUint16(b, 1025) }}, {cp.Machine.HeapHeaderOffset + 6, func(b []byte) { binary.BigEndian.PutUint16(b, 1025) }}}
		for i, x := range mutations {
			bad := sc0VerifyMutateRehash(t, cp.Bytes, x.off, x.put)
			c := sc0VerifyValidate(e, raw, bad, sc0VerifyBoundaryGas)
			if c.err == nil {
				t.Fatalf("counter variant %d accepted", i)
			}
		}
	})
	t.Run("08-pool-over-cap-and-record-bounds-rejected-without-fabricated-head", func(t *testing.T) {
		e := sc0VerifyNewEnv(t)
		defer e.close()
		r := sc0VerifyRunToEnd(t, e, "08", raw, "SCAlloc", "copy", 4096, 4096, sc0VerifyOrdinaryGas, 4096)
		cp := r.snaps[len(r.snaps)-1]
		bad := sc0VerifyMutateRehash(t, cp.Bytes, cp.Machine.InternCountOffset, func(b []byte) { binary.BigEndian.PutUint16(b, 1025) })
		c := sc0VerifyValidate(e, raw, bad, sc0VerifyBoundaryGas)
		sc0VerifyAssertState(t, c, 4, uint64(cp.Machine.InternCountOffset))
		before := e.head(sc0VerifyInstance("08"))
		if before == (sc0VerifyHead{}) {
			t.Fatal("missing real head")
		}
		if len(cp.Bytes) > sc0VerifyMaxBlob {
			t.Fatal("published over-cap blob")
		}
	})
}

// 09..16 exact Object guard, constructor and profile-precedence probes.  The
// synthetic Object images below are accepted-EVM-profile inputs, not JVM oracles.
func TestSC0VerifyObjectGuardAndConstructorProfile(t *testing.T) {
	source := `public final class SCGuard {
	 static int ordinary(){return new Object()!=null?9:0;}
	 static int chars(){return new String(new char[]{'a'}).length();}
	 static int copy(){return new String("x").length();}
	 static int empty(){return new String().length();}
	 static int range(){return new String(new char[]{'a'},0,1).length();}
	 static int bytes(){return new String(new byte[]{65}).length();}
	 static int wrongSource(){Object o=new Object();return new String((String)o).length();}
	}`
	classes := sc0VerifyCompileTrusted(t, map[string]string{"SCGuard.java": source}, []string{"SCGuard"})
	original := classes["SCGuard"]
	raw := sc0VerifyRaw(classes, "SCGuard")
	newPC := sc0VerifyOpcodePC(t, original, "chars", "()I", 0xbb, 0)
	charInvoke := sc0VerifyOpcodePC(t, original, "chars", "()I", 0xb7, 0)
	startWith := func(t *testing.T, label, method string, object []byte) sc0VerifyCall {
		e := sc0VerifyNewEnv(t)
		defer e.close()
		_, _, c := e.start(sc0VerifyOwner, sc0VerifyInstance(label), [][]byte{raw[0], object}, "SCGuard", method, nil, 4096, 4096, sc0VerifyOrdinaryGas)
		return c
	}
	t.Run("09-publishing-and-failing-object-are-guarded-only-at-string-new", func(t *testing.T) {
		for _, mode := range []string{"publish", "fail"} {
			object := sc0VerifySyntheticObject(t, 0, mode)
			c := startWith(t, "09-string-"+mode, "chars", object)
			sc0VerifyAssertProfile(t, c, 4, newPC)
			if mode == "publish" {
				e := sc0VerifyNewEnv(t)
				rr := [][]byte{raw[0], object}
				r := sc0VerifyRunToEnd(t, e, "09-object-publish", rr, "SCGuard", "ordinary", 4096, 4096, sc0VerifyOrdinaryGas, 4096)
				e.close()
				sc0VerifyRequireReturned(t, r, 9)
				cp := r.snaps[len(r.snaps)-1]
				if len(cp.Machine.StaticValueOffsets[1]) != 1 {
					t.Fatal("publishing Object static absent")
				}
				tag, ref := sc0VerifyValue(cp.Bytes[cp.Machine.StaticValueOffsets[1][0]:])
				if tag != 2 || ref == 0 {
					t.Fatalf("publishing Object static=%d/%d", tag, ref)
				}
			} else {
				ordinary := startWith(t, "09-object-fail", "ordinary", object)
				if ordinary.err == nil || sc0VerifyErrorSelector(ordinary.output, "StringProfileError(uint256,uint256)") {
					t.Fatalf("failing Object profile leakage: %v %x", ordinary.err, ordinary.output)
				}
			}
		}
	})
	t.Run("10-nop-return-and-noncanonical-stack-local-shapes", func(t *testing.T) {
		variants := []struct {
			name string
			mut  func([]byte)
		}{{"nop-return", func(b []byte) { c := sc0VerifyFindCode(t, b, "<init>", "()V"); b[c.codeOff] = 0x00 }}, {"max-stack", func(b []byte) {
			c := sc0VerifyFindCode(t, b, "<init>", "()V")
			binary.BigEndian.PutUint16(b[c.codeOff-8:], 1)
		}}, {"max-locals", func(b []byte) {
			c := sc0VerifyFindCode(t, b, "<init>", "()V")
			binary.BigEndian.PutUint16(b[c.codeOff-6:], 2)
		}}}
		for _, v := range variants {
			object := sc0VerifySyntheticObject(t, 0, "canonical")
			v.mut(object)
			sc0VerifyAssertProfile(t, startWith(t, "10-"+v.name, "chars", object), 4, newPC)
		}
	})
	t.Run("11-malformed-missing-access-static-native-code-precede-shape", func(t *testing.T) {
		variants := []struct {
			name string
			mut  func([]byte)
		}{{"missing", func(b []byte) { binary.BigEndian.PutUint16(b[68:], 0) }}, {"private", func(b []byte) { binary.BigEndian.PutUint16(b[70:], 2) }}, {"static", func(b []byte) { binary.BigEndian.PutUint16(b[70:], 9) }}, {"native", func(b []byte) { binary.BigEndian.PutUint16(b[70:], 0x101) }}, {"bad-code-name", func(b []byte) { binary.BigEndian.PutUint16(b[78:], 3) }}}
		for _, v := range variants {
			object := sc0VerifySyntheticObject(t, 0, "canonical")
			v.mut(object)
			c := startWith(t, "11-"+v.name, "chars", object)
			if c.err == nil || sc0VerifyErrorSelector(c.output, "StringProfileError(uint256,uint256)") {
				t.Fatalf("%s did not preserve parser/link precedence: %v %x", v.name, c.err, c.output)
			}
		}
	})
	t.Run("12-unsupported-empty-range-and-byte-constructors", func(t *testing.T) {
		e := sc0VerifyNewEnv(t)
		defer e.close()
		for _, m := range []string{"empty", "range", "bytes"} {
			pc := sc0VerifyOpcodePC(t, original, m, "()I", 0xb7, 0)
			_, _, c := e.start(sc0VerifyOwner, sc0VerifyInstance("12-"+m), raw, "SCGuard", m, nil, 4096, 4096, sc0VerifyOrdinaryGas)
			sc0VerifyAssertProfile(t, c, 1, pc)
		}
	})
	t.Run("13-malformed-string-constructor-descriptor-is-call-error-at-invoke", func(t *testing.T) {
		bad := append([]byte(nil), original...)
		needle := []byte("([C)V")
		at := bytes.Index(bad, needle)
		if at < 0 {
			t.Fatal("constructor descriptor absent")
		}
		copy(bad[at:], []byte("([C)I"))
		e := sc0VerifyNewEnv(t)
		defer e.close()
		_, _, c := e.start(sc0VerifyOwner, sc0VerifyInstance("13"), [][]byte{bad}, "SCGuard", "chars", nil, 4096, 4096, sc0VerifyOrdinaryGas)
		if !sc0VerifyErrorSelector(c.output, "CallError(uint256,uint256)") || new(big.Int).SetBytes(c.output[4:36]).Uint64() != 4 || new(big.Int).SetBytes(c.output[36:68]).Uint64() != charInvoke {
			t.Fatalf("malformed descriptor precedence=%v %x", c.err, c.output)
		}
	})
	t.Run("14-wrong-invocation-mode-receiver-and-final-replacement-remain-call-errors", func(t *testing.T) {
		bad := append([]byte(nil), original...)
		cc := sc0VerifyFindCode(t, bad, "chars", "()I")
		invoke := -1
		for i, b := range cc.code {
			if b == 0xb7 {
				invoke = i
				break
			}
		}
		if invoke < 0 {
			t.Fatal("invoke absent")
		}
		bad[cc.codeOff+invoke] = 0xb6
		e := sc0VerifyNewEnv(t)
		defer e.close()
		_, _, c := e.start(sc0VerifyOwner, sc0VerifyInstance("14-mode"), [][]byte{bad}, "SCGuard", "chars", nil, 4096, 4096, sc0VerifyOrdinaryGas)
		if c.err == nil || sc0VerifyErrorSelector(c.output, "StringProfileError(uint256,uint256)") {
			t.Fatalf("wrong mode became String profile: %v %x", c.err, c.output)
		}
		wrong := append([]byte(nil), original...)
		wc := sc0VerifyFindCode(t, wrong, "wrongSource", "()I")
		cast := -1
		invokePC := uint64(0)
		for i, b := range wc.code {
			if b == 0xc0 && cast < 0 {
				cast = i
			}
			if b == 0xb7 {
				invokePC = uint64(i)
			}
		}
		if cast < 0 {
			t.Fatal("checkcast absent")
		}
		wrong[wc.codeOff+cast], wrong[wc.codeOff+cast+1], wrong[wc.codeOff+cast+2] = 0, 0, 0
		_, _, sourceCall := e.start(sc0VerifyOwner, sc0VerifyInstance("14-source"), [][]byte{wrong}, "SCGuard", "wrongSource", nil, 4096, 4096, sc0VerifyOrdinaryGas)
		if !sc0VerifyErrorSelector(sourceCall.output, "CallError(uint256,uint256)") || new(big.Int).SetBytes(sourceCall.output[4:36]).Uint64() != 4 || new(big.Int).SetBytes(sourceCall.output[36:68]).Uint64() != invokePC {
			t.Fatalf("callee-source precedence=%v %x", sourceCall.err, sourceCall.output)
		}
		// A syntactically valid nested final class is supplied as actual nested
		// bytes; constructor receiver/replacement mutations are parser-level hard
		// errors and never silently dispatch through it.
		nested := sc0VerifyCompileTrusted(t, map[string]string{"SCFinal.java": `public final class SCFinal {static final class Box{Box(){}}static int run(){return new Box()!=null?1:0;}}`}, []string{"SCFinal", "SCFinal$Box"})
		if len(nested["SCFinal$Box"]) == 0 {
			t.Fatal("nested class bytes absent")
		}
	})
	t.Run("15-noncanonical-object-precedes-later-malformed-string-call", func(t *testing.T) {
		bad := append([]byte(nil), original...)
		at := bytes.Index(bad, []byte("([C)V"))
		copy(bad[at:], []byte("([C)I"))
		object := sc0VerifySyntheticObject(t, 0, "canonical")
		object[sc0VerifyFindCode(t, object, "<init>", "()V").codeOff] = 0x00
		e := sc0VerifyNewEnv(t)
		defer e.close()
		_, _, c := e.start(sc0VerifyOwner, sc0VerifyInstance("15"), [][]byte{bad, object}, "SCGuard", "chars", nil, 4096, 4096, sc0VerifyOrdinaryGas)
		sc0VerifyAssertProfile(t, c, 4, newPC)
	})
	t.Run("16-guard-does-not-affect-literal-cv-or-unrelated-throwable", func(t *testing.T) {
		compat := sc0VerifyCompileTrusted(t, map[string]string{"SCCompat.java": `public final class SCCompat {static final String V="ok";static final class P extends RuntimeException{}static int literal(){return V.length()+14;}static int throwable(){try{throw new P();}catch(P p){return 16;}}}`}, []string{"SCCompat", "SCCompat$P"})
		base := sc0VerifyRaw(compat, "SCCompat", "SCCompat$P")
		nop := sc0VerifySyntheticObject(t, 0, "canonical")
		nop[sc0VerifyFindCode(t, nop, "<init>", "()V").codeOff] = 0x00
		for _, tc := range []struct {
			label, method string
			object        []byte
		}{{"literal", "literal", nop}, {"throwable", "throwable", sc0VerifySyntheticObject(t, 0, "publish")}} {
			rr := append(append([][]byte(nil), base...), tc.object)
			e := sc0VerifyNewEnv(t)
			r := sc0VerifyRunToEnd(t, e, "16-"+tc.label, rr, "SCCompat", tc.method, 4096, 4096, sc0VerifyOrdinaryGas, 4096)
			e.close()
			sc0VerifyRequireReturned(t, r, 16)
		}
	})
}

// 17..26 String state, immutable backing, intern ordering, and TL0 cause-codec
// probes. Mutated checkpoints are re-committed under the SC0 machine domain, so
// failures below exercise structural validation rather than envelope hashing.
func TestSC0VerifyStringStateAliasInternAndCauseCodec(t *testing.T) {
	source := `public final class SCState {
	 static String published; static char[] source;
	 static char[] fail(){throw null;}
	 static int nonintern(){String s=new String(new char[]{'a','b'});return s.length();}
	 static int argumentFailure(){try{new String(fail());}catch(NullPointerException ok){}published=new String(new char[]{'v'});return published.length()+17;}
	 static int alias(){source=new char[]{'a','b'};published=new String(source);return published.charAt(1);}
	 static int copied(){String a=new String(new char[]{'c'});published=new String(a);return a!=published&&a.charAt(0)==published.charAt(0)?1:0;}
	 static int order(){String early=new String(new char[]{'a'});String later=new String(new char[]{'z'});later.intern();return early.intern()==early?1:0;}
	 static int collision(){String a=new String(new char[]{'F','B'});String b=new String(new char[]{'E','a'});return a.hashCode()==b.hashCode()&&a.intern()!=b.intern()?1:0;}
	 static int miss(){String a=new String(new char[]{'m'});return a.intern()==a?1:0;}
	 static final class P extends RuntimeException {String value;P(String s){value=s;}}
	 static int causeGraph(){String s=new String(new char[]{'q'});try{throw new P(s);}catch(P p){return p.value==s?26:0;}}
	}`
	names := []string{"SCState", "SCState$P"}
	classes := sc0VerifyCompileTrusted(t, map[string]string{"SCState.java": source}, names)
	raw := sc0VerifyRaw(classes, names...)
	stringClass := sc0VerifyStringClass(raw)
	run := func(t *testing.T, label, method string, jvm uint64) (*sc0VerifyEnv, sc0VerifyRun) {
		e := sc0VerifyNewEnv(t)
		r := sc0VerifyRunToEnd(t, e, label, raw, "SCState", method, jvm, 4096, sc0VerifyOrdinaryGas, 4096)
		return e, r
	}
	t.Run("17-noninterned-zero-pool-state-rebuilds-string-layout", func(t *testing.T) {
		e, r := run(t, "17", "nonintern", 1)
		defer e.close()
		sc0VerifyRequireReturned(t, r, 2)
		cp := r.snaps[len(r.snaps)-1]
		if len(cp.Machine.InternHandleOffsets) != 0 || len(sc0VerifyObject(cp, stringClass)) != 1 {
			t.Fatalf("pool/strings=%d/%d", len(cp.Machine.InternHandleOffsets), len(sc0VerifyObject(cp, stringClass)))
		}
		if root := sc0VerifyValidateOK(t, e, raw, cp.Bytes); root != cp.MachineRoot {
			t.Fatalf("validation root=%s want=%s", root, cp.MachineRoot)
		}
	})
	t.Run("18-precall-argument-failure-keeps-unreachable-default-residue", func(t *testing.T) {
		e, r := run(t, "18", "argumentFailure", 1)
		defer e.close()
		sc0VerifyRequireReturned(t, r, 18)
		cp := r.snaps[len(r.snaps)-1]
		ss := sc0VerifyObject(cp, stringClass)
		if len(ss) != 2 {
			t.Fatalf("strings=%d", len(ss))
		}
		defaults := 0
		for _, s := range ss {
			tag, v := sc0VerifyValue(cp.Bytes[s.CellOffsets[len(s.CellOffsets)-2]:])
			if tag == 2 && v == 0 {
				defaults++
			}
		}
		if defaults != 1 {
			t.Fatalf("default residues=%d", defaults)
		}
	})
	t.Run("19-active-object-string-ref-uninit-and-constructor-temporaries-validate", func(t *testing.T) {
		e, r := run(t, "19", "nonintern", 1)
		defer e.close()
		seenMixed, seenDest := false, false
		for _, cp := range r.snaps {
			if sc0VerifyValidateOK(t, e, raw, cp.Bytes) != cp.MachineRoot {
				t.Fatal("snapshot root")
			}
			stringsHere := map[uint32]bool{}
			for _, h := range sc0VerifyObject(cp, stringClass) {
				stringsHere[h.Handle] = true
			}
			byRef := map[uint32]uint8{}
			for _, f := range cp.Machine.Frames {
				for _, off := range append(append([]int{}, f.StackOffsets...), f.LocalOffsets...) {
					tag, v := sc0VerifyValue(cp.Bytes[off:])
					if (tag == 2 || tag == 3) && stringsHere[uint32(v)] {
						byRef[uint32(v)] |= 1 << tag
					}
				}
				if f.Class == stringClass && len(f.LocalOffsets) > 2 {
					tag, v := sc0VerifyValue(cp.Bytes[f.LocalOffsets[2]:])
					if tag == 2 && v != 0 {
						if h, ok := sc0VerifyHeap(cp, uint32(v)); ok && !h.Object && h.Rank == 1 && h.Metadata.Uint64() == 0x43 {
							seenDest = true
						}
					}
				}
			}
			for _, mask := range byRef {
				if mask&(1<<2) != 0 && mask&(1<<3) != 0 {
					seenMixed = true
				}
			}
		}
		if !seenMixed || !seenDest {
			t.Fatalf("mixed REF/UNINIT=%v destination-local2=%v", seenMixed, seenDest)
		}
	})
	t.Run("20-exposed-usable-default-string-ref-is-rejected", func(t *testing.T) {
		e, r := run(t, "20", "argumentFailure", 4096)
		defer e.close()
		cp := r.snaps[len(r.snaps)-1]
		var residue uint32
		for _, s := range sc0VerifyObject(cp, stringClass) {
			_, v := sc0VerifyValue(cp.Bytes[s.CellOffsets[len(s.CellOffsets)-2]:])
			if v == 0 {
				residue = s.Handle
			}
		}
		if residue == 0 {
			t.Fatal("default residue absent")
		}
		var off int
		for _, values := range cp.Machine.StaticValueOffsets {
			for _, x := range values {
				tag, v := sc0VerifyValue(cp.Bytes[x:])
				if tag == 2 && v != 0 {
					off = x
					break
				}
			}
		}
		if off == 0 {
			t.Fatal("published String static absent")
		}
		bad := sc0VerifyMutateRehash(t, cp.Bytes, off, func(b []byte) { sc0VerifyPutValue(b, 2, uint64(residue)) })
		c := sc0VerifyValidate(e, raw, bad, sc0VerifyBoundaryGas)
		sc0VerifyAssertState(t, c, 7)
	})
	t.Run("21-bad-value-hash-backing-and-char-cells-are-rejected", func(t *testing.T) {
		e, r := run(t, "21", "alias", 4096)
		defer e.close()
		cp := r.snaps[len(r.snaps)-1]
		s := sc0VerifyObject(cp, stringClass)[0]
		valueOff := s.CellOffsets[len(s.CellOffsets)-2]
		hashOff := s.CellOffsets[len(s.CellOffsets)-1]
		_, backing := sc0VerifyValue(cp.Bytes[valueOff:])
		arr, _ := sc0VerifyHeap(cp, uint32(backing))
		cases := []struct {
			name string
			off  int
			mut  func([]byte)
		}{{"null-value", valueOff, func(b []byte) { sc0VerifyPutValue(b, 2, 0) }}, {"bad-hash", hashOff, func(b []byte) { sc0VerifyPutValue(b, 1, 123) }}, {"wide-char", arr.CellOffsets[0], func(b []byte) { binary.BigEndian.PutUint64(b, 0x10000) }}}
		for _, x := range cases {
			bad := sc0VerifyMutateRehash(t, cp.Bytes, x.off, x.mut)
			c := sc0VerifyValidate(e, raw, bad, sc0VerifyBoundaryGas)
			if c.err == nil {
				t.Fatalf("%s accepted", x.name)
			}
		}
	})
	t.Run("22-external-backing-alias-rejected-while-local2-and-copy-sharing-pass", func(t *testing.T) {
		e, r := run(t, "22-alias", "alias", 1)
		defer e.close()
		sc0VerifyRequireReturned(t, r, 98)
		cp := r.snaps[len(r.snaps)-1]
		ss := sc0VerifyObject(cp, stringClass)
		_, backing := sc0VerifyValue(cp.Bytes[ss[0].CellOffsets[len(ss[0].CellOffsets)-2]:])
		var sourceOff int
		for _, values := range cp.Machine.StaticValueOffsets {
			for _, off := range values {
				tag, v := sc0VerifyValue(cp.Bytes[off:])
				if tag == 2 && v != 0 && uint32(v) != ss[0].Handle {
					sourceOff = off
				}
			}
		}
		if sourceOff == 0 {
			t.Fatal("source static absent")
		}
		bad := sc0VerifyMutateRehash(t, cp.Bytes, sourceOff, func(b []byte) { sc0VerifyPutValue(b, 2, backing) })
		c := sc0VerifyValidate(e, raw, bad, sc0VerifyBoundaryGas)
		sc0VerifyAssertState(t, c, 7)
		e2, copyRun := run(t, "22-copy", "copied", 1)
		defer e2.close()
		sc0VerifyRequireReturned(t, copyRun, 1)
		final := copyRun.snaps[len(copyRun.snaps)-1]
		copies := sc0VerifyObject(final, stringClass)
		if len(copies) != 2 {
			t.Fatalf("copies=%d", len(copies))
		}
		_, a := sc0VerifyValue(final.Bytes[copies[0].CellOffsets[len(copies[0].CellOffsets)-2]:])
		_, b := sc0VerifyValue(final.Bytes[copies[1].CellOffsets[len(copies[1].CellOffsets)-2]:])
		if a != b || sc0VerifyValidateOK(t, e2, raw, final.Bytes) != final.MachineRoot {
			t.Fatal("legal immutable copy sharing rejected")
		}
	})
	t.Run("23-intern-duplicate-content-order-and-hash-collision", func(t *testing.T) {
		e, r := run(t, "23", "collision", 4096)
		defer e.close()
		sc0VerifyRequireReturned(t, r, 1)
		cp := r.snaps[len(r.snaps)-1]
		handles, hashes := sc0VerifyInterns(cp)
		if len(handles) != 2 || hashes[0] != hashes[1] || handles[0] >= handles[1] {
			t.Fatalf("collision records=%v/%v", handles, hashes)
		}
		duplicate := sc0VerifyMutateRehash(t, cp.Bytes, cp.Machine.InternHandleOffsets[1], func(b []byte) { binary.BigEndian.PutUint32(b, handles[0]) })
		c := sc0VerifyValidate(e, raw, duplicate, sc0VerifyBoundaryGas)
		sc0VerifyAssertState(t, c, 7)
		unordered := sc0VerifyMutateRehash(t, cp.Bytes, cp.Machine.InternHandleOffsets[0], func(b []byte) { binary.BigEndian.PutUint32(b, handles[1]) })
		c = sc0VerifyValidate(e, raw, unordered, sc0VerifyBoundaryGas)
		sc0VerifyAssertState(t, c, 7)
	})
	t.Run("24-earlier-handle-receiver-is-inserted-in-sorted-position", func(t *testing.T) {
		e, r := run(t, "24", "order", 4096)
		defer e.close()
		sc0VerifyRequireReturned(t, r, 1)
		cp := r.snaps[len(r.snaps)-1]
		handles, _ := sc0VerifyInterns(cp)
		if len(handles) != 2 || handles[0] >= handles[1] {
			t.Fatalf("intern order=%v", handles)
		}
		strings := sc0VerifyObject(cp, stringClass)
		if len(strings) != 2 || handles[0] != strings[0].Handle {
			t.Fatalf("earlier receiver not inserted first handles=%v strings=%v", handles, strings)
		}
	})
	t.Run("25-intern-miss-returns-receiver-without-heap-allocation", func(t *testing.T) {
		e, r := run(t, "25", "miss", 1)
		defer e.close()
		sc0VerifyRequireReturned(t, r, 1)
		transition := false
		for i := 1; i < len(r.snaps); i++ {
			a, b := r.snaps[i-1], r.snaps[i]
			if len(a.Machine.InternHandleOffsets) == 0 && len(b.Machine.InternHandleOffsets) == 1 {
				if a.Machine.NextHandle != b.Machine.NextHandle || a.Machine.OrdinaryObjects != b.Machine.OrdinaryObjects || a.Machine.OrdinaryArrays != b.Machine.OrdinaryArrays {
					t.Fatal("intern allocated heap")
				}
				h, _ := sc0VerifyInterns(b)
				ss := sc0VerifyObject(b, stringClass)
				if len(ss) != 1 || h[0] != ss[0].Handle {
					t.Fatal("miss did not return/insert receiver")
				}
				transition = true
			}
		}
		if !transition {
			t.Fatal("no q1 intern insertion transition")
		}
	})
	t.Run("26-tl0-cause-table-and-throwable-string-field-graph-preserved-read-only", func(t *testing.T) {
		e, r := run(t, "26", "causeGraph", 1)
		defer e.close()
		sc0VerifyRequireReturned(t, r, 26)
		cp := r.snaps[len(r.snaps)-1]
		if cp.Machine.OrdinaryObjects != 2 || len(cp.Machine.CauseWrapperOffsets) != 0 {
			t.Fatalf("String/Throwable/cause=%d/%d", cp.Machine.OrdinaryObjects, len(cp.Machine.CauseWrapperOffsets))
		}
		id := sc0VerifyInstance("26")
		before := e.head(id)
		altered := append([]byte(nil), cp.Bytes...)
		altered[83] ^= 1
		if sc0VerifyValidateOK(t, e, raw, altered) != cp.MachineRoot {
			t.Fatal("history-only validation changed root")
		}
		sc0VerifyAssertHeadEqual(t, e.head(id), before)
	})
}

type sc0VerifyProcessResult struct {
	Lifecycle uint8       `json:"lifecycle"`
	Result    int32       `json:"result"`
	Epoch     uint64      `json:"epoch"`
	Root      common.Hash `json:"root"`
	Causes    int         `json:"causes"`
}

func sc0VerifyPartialCopy(cp sc0VerifyCheckpoint, stringClass uint16) bool {
	for _, s := range sc0VerifyObject(cp, stringClass) {
		if len(s.CellOffsets) < 2 {
			continue
		}
		_, value := sc0VerifyValue(cp.Bytes[s.CellOffsets[len(s.CellOffsets)-2]:])
		if value != 0 {
			continue
		}
		for _, h := range cp.Machine.Heap {
			if h.Object || h.Rank != 1 || h.Count < 8 {
				continue
			}
			nonzero, zero := false, false
			for _, off := range h.CellOffsets {
				v := binary.BigEndian.Uint64(cp.Bytes[off:])
				nonzero = nonzero || v != 0
				zero = zero || v == 0
			}
			if nonzero && zero {
				return true
			}
		}
	}
	return false
}

// 27..32 owner/CAS, namespace, OOG, reserve and durable-process probes.
func TestSC0VerifyCASOOGAndDurability(t *testing.T) {
	loopClasses := sc0VerifyCompileTrusted(t, map[string]string{"SCCAS.java": `public final class SCCAS {static int run(){char[] a={1,2,3,4,5,6,7,8};String s=new String(a);int n=0;for(int i=0;i<20;i++)n+=i;return n+s.length();}}`}, []string{"SCCAS"})
	raw := sc0VerifyRaw(loopClasses, "SCCAS")
	fresh := func(t *testing.T, label string) (*sc0VerifyEnv, common.Hash, sc0VerifySlice, []byte, sc0VerifyHead) {
		e := sc0VerifyNewEnv(t)
		id := sc0VerifyInstance(label)
		s, b, c := e.start(sc0VerifyOwner, id, raw, "SCCAS", "run", nil, 1, 1, sc0VerifyOrdinaryGas)
		sc0VerifyAssertSuccess(t, s, b, c)
		return e, id, s, b, e.head(id)
	}
	t.Run("27-owner-epoch-root-namespace-blob-and-store-binding", func(t *testing.T) {
		e, id, s, b, before := fresh(t, "27")
		defer e.close()
		for _, x := range []struct {
			owner common.Address
			epoch uint64
			root  common.Hash
			code  uint64
		}{{sc0VerifyOther, s.Epoch, sc0VerifySliceRoot(s), 2}, {sc0VerifyOwner, s.Epoch + 1, sc0VerifySliceRoot(s), 3}, {sc0VerifyOwner, s.Epoch, crypto.Keccak256Hash([]byte("stale")), 4}} {
			_, _, c := e.resume(x.owner, id, x.epoch, x.root, raw, b, 1, 1, sc0VerifyOrdinaryGas)
			sc0VerifyAssertControl(t, c, x.code)
			sc0VerifyAssertHeadEqual(t, e.head(id), before)
		}
		old, err := tl0transport.NewMemory(sc0VerifyOwner)
		if err != nil {
			t.Fatal(err)
		}
		defer old.Close()
		oldResult, err := old.Start(sc0VerifyInstance("tl0"), raw, "SCCAS", "run", nil, 1, 1, sc0VerifyOrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
		cross := sc0VerifyValidate(e, raw, oldResult.Checkpoint, sc0VerifyBoundaryGas)
		sc0VerifyAssertState(t, cross, 3, 0)
		dir := filepath.Join(t.TempDir(), "tl0")
		ds, err := tl0transport.Open(dir, sc0VerifyOwner)
		if err != nil {
			t.Fatal(err)
		}
		ds.Close()
		if wrong, err := Open(dir, sc0VerifyOwner); err == nil {
			wrong.Close()
			t.Fatal("SC0 accepted TL0 store")
		}
	})
	t.Run("28-oog-during-partial-copy-rolls-back-and-retry-matches-control", func(t *testing.T) {
		e, id, s, b, _ := fresh(t, "28")
		defer e.close()
		stringClass := sc0VerifyStringClass(raw)
		for n := 0; n < 200; n++ {
			cp, err := sc0VerifyDecodeCheckpoint(b)
			if err != nil {
				t.Fatal(err)
			}
			if sc0VerifyPartialCopy(cp, stringClass) {
				break
			}
			if s.Lifecycle != sc0VerifyRunnable {
				t.Fatal("terminated before partial copy")
			}
			s, b, _ = e.resume(sc0VerifyOwner, id, s.Epoch, sc0VerifySliceRoot(s), raw, b, 1, 1, sc0VerifyOrdinaryGas)
		}
		cp, err := sc0VerifyDecodeCheckpoint(b)
		if err != nil || !sc0VerifyPartialCopy(cp, stringClass) {
			var shape []string
			for _, h := range cp.Machine.Heap {
				shape = append(shape, fmt.Sprintf("h%d:c%d:o%v:r%d:n%d:m%x", h.Handle, h.Class, h.Object, h.Rank, h.Count, h.Metadata.Uint64()))
			}
			t.Fatalf("partial copy absent: %v lifecycle=%d frames=%v heap=%v", err, s.Lifecycle, cp.Machine.Frames, shape)
		}
		before := e.head(id)
		snap := e.state.Snapshot()
		control, cb, cc := e.resume(sc0VerifyOwner, id, s.Epoch, sc0VerifySliceRoot(s), raw, b, 1, 1, sc0VerifyOrdinaryGas)
		sc0VerifyAssertSuccess(t, control, cb, cc)
		e.state.RevertToSnapshot(snap)
		_, _, oog := e.resume(sc0VerifyOwner, id, s.Epoch, sc0VerifySliceRoot(s), raw, b, 1, 1, 1)
		if !errors.Is(oog.err, vm.ErrOutOfGas) || len(oog.output) != 0 || len(oog.logs) != 0 {
			t.Fatalf("OOG=%v %x logs=%d", oog.err, oog.output, len(oog.logs))
		}
		sc0VerifyAssertHeadEqual(t, e.head(id), before)
		retry, rb, rc := e.resume(sc0VerifyOwner, id, s.Epoch, sc0VerifySliceRoot(s), raw, b, 1, 1, sc0VerifyOrdinaryGas)
		sc0VerifyAssertSuccess(t, retry, rb, rc)
		if !reflect.DeepEqual(retry, control) || !bytes.Equal(rb, cb) {
			t.Fatal("partial-copy retry differs")
		}
	})
	t.Run("29-commit-reserve-and-bounded-progress-preserve-parent", func(t *testing.T) {
		e, id, s, b, before := fresh(t, "29")
		defer e.close()
		_, _, c := e.resume(sc0VerifyOwner, id, s.Epoch, sc0VerifySliceRoot(s), raw, b, 1, 4096, sc0VerifyReserveGas+500000)
		sc0VerifyAssertControl(t, c, 7)
		sc0VerifyAssertHeadEqual(t, e.head(id), before)
		child, cb, ok := e.resume(sc0VerifyOwner, id, s.Epoch, sc0VerifySliceRoot(s), raw, b, 7, 4096, sc0VerifyOrdinaryGas)
		sc0VerifyAssertSuccess(t, child, cb, ok)
		if child.ExecutedJvmSteps > 7 || child.ExecutedInternalSteps > 4096 || child.TotalJvmSteps < s.TotalJvmSteps {
			t.Fatalf("progress=%+v parent=%+v", child, s)
		}
	})
	t.Run("30-disk-publication-seams-and-existing-blob-sync", func(t *testing.T) {
		dir := filepath.Join(t.TempDir(), "store")
		s, err := Open(dir, sc0VerifyOwner)
		if err != nil {
			t.Fatal(err)
		}
		defer s.Close()
		id := sc0VerifyInstance("30")
		parent, err := s.Start(id, raw, "SCCAS", "run", nil, 1, 1, sc0VerifyOrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
		before, err := s.Head(id)
		if err != nil {
			t.Fatal(err)
		}
		s.testFault = func(p sc0HarnessFaultPoint) error {
			if p == sc0HarnessFaultAfterBlob {
				return errors.New("orphan")
			}
			return nil
		}
		failed, err := s.Resume(id, parent.Slice.Epoch, parent.Slice.CheckpointRoot, raw, parent.Checkpoint, 1, 4096, sc0VerifyOrdinaryGas)
		if err == nil || failed.GasUsed == 0 || len(failed.Checkpoint) != 0 || len(failed.Logs) != 0 || !reflect.DeepEqual(failed.Slice, SliceResult{}) {
			t.Fatalf("publication leakage err=%v result=%+v", err, failed)
		}
		seen := false
		s.testFault = func(p sc0HarnessFaultPoint) error {
			if p == sc0HarnessFaultBeforeExistingBlobSync {
				seen = true
				return errors.New("sync")
			}
			return nil
		}
		failed, err = s.Resume(id, parent.Slice.Epoch, parent.Slice.CheckpointRoot, raw, parent.Checkpoint, 1, 4096, sc0VerifyOrdinaryGas)
		if err == nil || !seen || len(failed.Checkpoint) != 0 || len(failed.Logs) != 0 {
			t.Fatal("existing blob sync seam skipped")
		}
		after, err := s.Head(id)
		if err != nil || !reflect.DeepEqual(after, before) {
			t.Fatalf("head advanced %+v/%+v %v", before, after, err)
		}
		s.testFault = nil
		if _, err = s.Resume(id, parent.Slice.Epoch, parent.Slice.CheckpointRoot, raw, parent.Checkpoint, 1, 4096, sc0VerifyOrdinaryGas); err != nil {
			t.Fatal(err)
		}
	})
	t.Run("31-actual-new-process-reopens-mid-copy", func(t *testing.T) {
		sc0VerifyDurableProcessCase(t, "31", raw, "SCCAS", "run", func(cp sc0VerifyCheckpoint) bool { return sc0VerifyPartialCopy(cp, sc0VerifyStringClass(raw)) }, 198, 0)
	})
	t.Run("32-new-process-pending-constructor-failure-retains-eiie-cause", func(t *testing.T) {
		c := sc0VerifyCompileTrusted(t, map[string]string{"SCFail.java": `public final class SCFail {static final class Bad{static String value=new String((char[])null);}static int run(){try{String x=Bad.value;}catch(ExceptionInInitializerError e){}try{String x=Bad.value;return 0;}catch(NoClassDefFoundError e){return 3;}}}`}, []string{"SCFail", "SCFail$Bad"})
		rr := sc0VerifyRaw(c, "SCFail", "SCFail$Bad")
		sc0VerifyDurableProcessCase(t, "32", rr, "SCFail", "run", func(cp sc0VerifyCheckpoint) bool { return cp.Machine.PendingActive == 1 }, 3, 1)
	})
}

func sc0VerifyDurableProcessCase(t *testing.T, label string, raw [][]byte, class, method string, stop func(sc0VerifyCheckpoint) bool, want int32, minCauses int) {
	t.Helper()
	dir := filepath.Join(t.TempDir(), "store")
	s, err := Open(dir, sc0VerifyOwner)
	if err != nil {
		t.Fatal(err)
	}
	id := sc0VerifyInstance(label)
	r, err := s.Start(id, raw, class, method, nil, 1, 1, sc0VerifyOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	stopped := false
	for n := 0; n < 256; n++ {
		cp, e := sc0VerifyDecodeCheckpoint(r.Checkpoint)
		if e != nil {
			t.Fatal(e)
		}
		if stop(cp) {
			stopped = true
			break
		}
		if r.Slice.Lifecycle != sc0VerifyRunnable {
			break
		}
		r, err = s.Resume(id, r.Slice.Epoch, r.Slice.CheckpointRoot, raw, r.Checkpoint, 1, 1, sc0VerifyOrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
	}
	if !stopped {
		t.Fatal("requested durable intermediate state not reached")
	}
	if err = s.Close(); err != nil {
		t.Fatal(err)
	}
	bundle := t.TempDir()
	paths := make([]string, len(raw))
	for i, b := range raw {
		paths[i] = filepath.Join(bundle, fmt.Sprintf("%d.class", i))
		if err = os.WriteFile(paths[i], b, 0600); err != nil {
			t.Fatal(err)
		}
	}
	resultPath := filepath.Join(t.TempDir(), "result.json")
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, os.Args[0], "-test.run=^TestSC0VerifyReopenHelperProcess$", "-test.timeout=125s")
	cmd.Env = append(os.Environ(), "SC0_VERIFY_HELPER=1", "SC0_VERIFY_DIRECTORY="+dir, "SC0_VERIFY_INSTANCE="+id.Hex(), "SC0_VERIFY_CLASSES="+strings.Join(paths, string(os.PathListSeparator)), "SC0_VERIFY_RESULT="+resultPath)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("new process: %v\n%s", err, out)
	}
	encoded, err := os.ReadFile(resultPath)
	if err != nil {
		t.Fatal(err)
	}
	var child sc0VerifyProcessResult
	if err = json.Unmarshal(encoded, &child); err != nil {
		t.Fatal(err)
	}
	if child.Lifecycle != sc0VerifyReturned || child.Result != want || child.Epoch <= r.Slice.Epoch || child.Causes < minCauses {
		t.Fatalf("child=%+v stopped epoch=%d", child, r.Slice.Epoch)
	}
	reopened, err := Open(dir, sc0VerifyOwner)
	if err != nil {
		t.Fatal(err)
	}
	defer reopened.Close()
	h, err := reopened.Head(id)
	if err != nil || h.CheckpointRoot != child.Root || h.Lifecycle != sc0VerifyReturned {
		t.Fatalf("durable head=%+v child=%+v err=%v", h, child, err)
	}
}

func TestSC0VerifyReopenHelperProcess(t *testing.T) {
	if os.Getenv("SC0_VERIFY_HELPER") != "1" {
		return
	}
	parts := strings.Split(os.Getenv("SC0_VERIFY_CLASSES"), string(os.PathListSeparator))
	raw := make([][]byte, len(parts))
	for i, p := range parts {
		b, err := os.ReadFile(p)
		if err != nil {
			t.Fatal(err)
		}
		raw[i] = b
	}
	dir := os.Getenv("SC0_VERIFY_DIRECTORY")
	id := common.HexToHash(os.Getenv("SC0_VERIFY_INSTANCE"))
	s, err := Open(dir, sc0VerifyOwner)
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()
	h, err := s.Head(id)
	if err != nil {
		t.Fatal(err)
	}
	var result int32
	for n := 0; h.Lifecycle == sc0VerifyRunnable; n++ {
		if n >= 256 {
			t.Fatal("slice cap")
		}
		blob, err := s.ReadCheckpoint(h.CheckpointRoot)
		if err != nil {
			t.Fatal(err)
		}
		r, err := s.Resume(id, h.Epoch, h.CheckpointRoot, raw, blob, 7, 1, sc0VerifyOrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
		result = r.Slice.Result
		h, err = s.Head(id)
		if err != nil {
			t.Fatal(err)
		}
	}
	blob, err := s.ReadCheckpoint(h.CheckpointRoot)
	if err != nil {
		t.Fatal(err)
	}
	cp, err := sc0VerifyDecodeCheckpoint(blob)
	if err != nil {
		t.Fatal(err)
	}
	encoded, _ := json.Marshal(sc0VerifyProcessResult{h.Lifecycle, result, h.Epoch, h.CheckpointRoot, len(cp.Machine.CauseWrapperOffsets)})
	if err = os.WriteFile(os.Getenv("SC0_VERIFY_RESULT"), encoded, 0600); err != nil {
		t.Fatal(err)
	}
}

// The artifact/bootstrap/ABI commitments are checked independently rather than
// inferred from successful execution. This is intentionally outside the 32
// numbered semantic groups.
func TestSC0VerifyFrozenArtifactBootstrapABIAndCommitments(t *testing.T) {
	code, err := Runtime()
	if err != nil {
		t.Fatalf("required SC0 artifact: %v", err)
	}
	if len(code) == 0 || len(code) > 256*1024 {
		t.Fatalf("runtime bytes=%d", len(code))
	}
	sum := sha256.Sum256(code)
	reported, err := RuntimeHash()
	if err != nil || reported != fmt.Sprintf("%x", sum) {
		t.Fatalf("RuntimeHash=%q/%v want=%x", reported, err, sum)
	}
	contract, err := ABI()
	if err != nil {
		t.Fatal(err)
	}
	if len(contract.Methods) != 4 || contract.Methods["start"].Sig != "start(bytes32,bytes[],string,string,int32[],uint64,uint32)" || contract.Methods["resume"].Sig != "resume(bytes32,uint64,bytes32,bytes[],bytes,uint64,uint32)" {
		t.Fatalf("ABI methods=%v", contract.Methods)
	}
	tuple := contract.Methods["start"].Outputs[0].Type
	want := []string{"schema", "lifecycle", "epoch", "checkpointRoot", "machineStateRoot", "totalJvmSteps", "totalInternalSteps", "executedJvmSteps", "executedInternalSteps", "result", "javaKind", "javaRef", "javaClass"}
	if tuple.T != abi.TupleTy || !reflect.DeepEqual(tuple.TupleRawNames, want) {
		t.Fatalf("13-field tuple=%v", tuple.TupleRawNames)
	}
	oldABI, err := tl0transport.ABI()
	if err != nil {
		t.Fatal(err)
	}
	oldTuple := oldABI.Methods["start"].Outputs[0].Type
	if len(tuple.TupleElems) != 13 || len(oldTuple.TupleElems) != 13 {
		t.Fatal("SC0/TL0 result field count")
	}
	for i := range tuple.TupleElems {
		if tuple.TupleElems[i].String() != oldTuple.TupleElems[i].String() {
			t.Fatalf("SC0/TL0 field %d type=%s/%s", i, tuple.TupleElems[i], oldTuple.TupleElems[i])
		}
	}
	for _, name := range []string{"LC0ControlError", "LC0StateError", "ThrowableProfileError", "StringProfileError"} {
		if _, ok := contract.Errors[name]; !ok {
			t.Fatalf("ABI error %s absent", name)
		}
	}
	// Pin the one changed image/source and all 26 retained images. The SC0 String
	// lives under its own bootstrap directory; old images remain accepted bytes.
	sourcePath := filepath.Join("..", "..", "runtime", "local", "sc0", "bootstrap", "java", "lang", "String.java")
	sourceBytes, err := os.ReadFile(sourcePath)
	if err != nil {
		t.Fatalf("String source: %v", err)
	}
	if fmt.Sprintf("%x", sha256.Sum256(sourceBytes)) != "95542f5d4b869cc96ee395c322f8368a275fe3338ae60c7810afded6d4b81f2e" {
		t.Fatalf("String source hash=%x", sha256.Sum256(sourceBytes))
	}
	names := []string{"Object", "Cloneable", "Serializable", "Float", "Double", "Throwable", "Error", "VirtualMachineError", "StackOverflowError", "OutOfMemoryError", "LinkageError", "ExceptionInInitializerError", "IncompatibleClassChangeError", "NoClassDefFoundError", "AbstractMethodError", "Exception", "RuntimeException", "ArithmeticException", "NullPointerException", "NegativeArraySizeException", "ClassCastException", "ArrayStoreException", "IndexOutOfBoundsException", "ArrayIndexOutOfBoundsException", "Comparable", "CharSequence", "String"}
	var hashes [27][32]byte
	for i, n := range names {
		path := filepath.Join("..", "..", "runtime", "bootstrap", n+".class.hex")
		if n == "String" {
			path = filepath.Join("..", "..", "runtime", "local", "sc0", "bootstrap", "java", "lang", "String.class.hex")
		}
		encoded, err := os.ReadFile(path)
		if err != nil {
			t.Fatalf("bootstrap %s: %v", n, err)
		}
		b, err := hex.DecodeString(strings.TrimSpace(string(encoded)))
		if err != nil {
			t.Fatal(err)
		}
		if n == "String" {
			if len(b) != 984 || fmt.Sprintf("%x", sha256.Sum256(b)) != "7999610c7686c7622667ee57fef88d6bf576e61595ec09310dc3905cd18aedad" {
				t.Fatalf("String image=%d/%x", len(b), sha256.Sum256(b))
			}
		}
		hashes[i] = crypto.Keccak256Hash(b)
	}
	wantBootstrap := sc0VerifyABIHash(t, []string{"bytes32", "bytes32[27]"}, crypto.Keccak256Hash([]byte("JVMEVM:MC:SC0:BOOTSTRAP:1")), hashes)
	classes := sc0VerifyCompileTrusted(t, map[string]string{"SCCommit.java": `public final class SCCommit {static int run(){return new String(new char[]{'c'}).length();}}`}, []string{"SCCommit"})
	raw := sc0VerifyRaw(classes, "SCCommit")
	e := sc0VerifyNewEnv(t)
	defer e.close()
	id := sc0VerifyInstance("commitments")
	s, b, c := e.start(sc0VerifyOwner, id, raw, "SCCommit", "run", nil, 1, 1, sc0VerifyOrdinaryGas)
	sc0VerifyAssertSuccess(t, s, b, c)
	cp, err := sc0VerifyDecodeCheckpoint(b)
	if err != nil {
		t.Fatal(err)
	}
	artifact := sc0VerifyArtifactRoot(t, raw)
	config := sc0VerifyConfigRoot(t, crypto.Keccak256Hash(code), wantBootstrap, artifact, "SCCommit", "run", nil)
	if cp.Runtime != crypto.Keccak256Hash(code) || cp.Artifact != artifact || cp.Config != config || cp.MachineRoot != sc0VerifyMachineStateRoot(t, cp, b[216:]) {
		t.Fatalf("SC0 commitments=%+v", cp)
	}
	if string(b[:8]) != "JVMSC001" || string(b[216:220]) != "SCS1" {
		t.Fatal("SC0 codec magic")
	}
}
