// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.
//
// Parent-owned independent verifier for the frozen LOCAL MC-IOE0 profile.
// No stub, host evaluation, or skipped artifact counts as execution evidence. The
// decoder in this file is test-only: production Go continues to transport the
// checkpoint as opaque bytes and never evaluates Java state.
package ioe0

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
	sc0transport "github.com/ethereum/go-ethereum/jvmevm/localcontinuation/sc0"
)

const (
	ioe0VerifyOrdinaryGas = uint64(100_000_000)
	ioe0VerifyBoundaryGas = uint64(1_000_000_000)
	ioe0VerifyReserveGas  = uint64(25_000_000)
	ioe0VerifyMaxBlob     = 1 << 20
	ioe0VerifyHeaderSize  = 216

	ioe0VerifyRunnable = uint8(1)
	ioe0VerifyReturned = uint8(2)
	ioe0VerifyUncaught = uint8(3)
)

var (
	ioe0VerifyOwner = common.HexToAddress("0x0000000000000000000000000000000000007101")
	ioe0VerifyOther = common.HexToAddress("0x0000000000000000000000000000000000007102")
	ioe0VerifyAt    = common.HexToAddress("0x4a564d45564d494f453052554e54494d45000001")
)

type ioe0VerifySlice struct {
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

type ioe0VerifyHead struct {
	Owner           common.Address
	Epoch           uint64
	CheckpointRoot  common.Hash
	MachineRoot     common.Hash
	ArtifactRoot    common.Hash
	ConfigRoot      common.Hash
	RuntimeCodeHash common.Hash
	Lifecycle       uint8
}

type ioe0VerifyCall struct {
	output []byte
	left   uint64
	err    error
	logs   []*types.Log
}

type ioe0VerifyEnv struct {
	t        *testing.T
	state    *state.StateDB
	code     []byte
	contract abi.ABI
	calls    uint64
}

func ioe0VerifyNewEnv(t *testing.T) *ioe0VerifyEnv {
	t.Helper()
	code, err := Runtime()
	if err != nil {
		t.Fatalf("load IOE0 runtime (runtime integration dependency absent): %v", err)
	}
	contract, err := ABI()
	if err != nil {
		t.Fatalf("load IOE0 ABI: %v", err)
	}
	st, err := state.New(types.EmptyRootHash, state.NewDatabaseForTesting())
	if err != nil {
		t.Fatal(err)
	}
	st.CreateAccount(ioe0VerifyAt)
	st.SetCode(ioe0VerifyAt, code, tracing.CodeChangeUnspecified)
	return &ioe0VerifyEnv{t: t, state: st, code: code, contract: contract}
}

func (e *ioe0VerifyEnv) close() { e.state.Database().TrieDB().Close() }

func (e *ioe0VerifyEnv) callAs(owner common.Address, gas uint64, method string, args ...any) ioe0VerifyCall {
	e.t.Helper()
	input, err := e.contract.Pack(method, args...)
	if err != nil {
		e.t.Fatalf("pack %s: %v", method, err)
	}
	e.calls++
	txHash := crypto.Keccak256Hash([]byte("IOE0 verifier call"), new(big.Int).SetUint64(e.calls).Bytes())
	e.state.SetTxContext(txHash, 0)
	start := time.Now()
	output, left, callErr := runtime.Call(ioe0VerifyAt, input, &runtime.Config{
		State: e.state, Origin: owner, GasLimit: gas,
		BlockNumber: big.NewInt(1), Time: 1,
	})
	limit := 30 * time.Second
	if gas > ioe0VerifyOrdinaryGas {
		limit = 120 * time.Second
	}
	if elapsed := time.Since(start); elapsed > limit {
		e.t.Fatalf("%s call exceeded LOCAL watchdog: %s > %s", method, elapsed, limit)
	}
	logs := append([]*types.Log(nil), e.state.GetLogs(txHash, 1, common.Hash{}, 1)...)
	return ioe0VerifyCall{append([]byte(nil), output...), left, callErr, logs}
}

func (e *ioe0VerifyEnv) start(owner common.Address, instance common.Hash, raw [][]byte, entryClass, entry string, args []int32, jvm uint64, internal uint32, gas uint64) (ioe0VerifySlice, []byte, ioe0VerifyCall) {
	e.t.Helper()
	c := e.callAs(owner, gas, "start", instance, raw, entryClass, entry, args, jvm, internal)
	if c.err != nil {
		return ioe0VerifySlice{}, nil, c
	}
	values, err := e.contract.Methods["start"].Outputs.Unpack(c.output)
	if err != nil || len(values) != 2 {
		e.t.Fatalf("decode start outputs=%d: %v (%x)", len(values), err, c.output)
	}
	s := *abi.ConvertType(values[0], new(ioe0VerifySlice)).(*ioe0VerifySlice)
	return s, append([]byte(nil), values[1].([]byte)...), c
}

func (e *ioe0VerifyEnv) resume(owner common.Address, instance common.Hash, epoch uint64, root common.Hash, raw [][]byte, checkpoint []byte, jvm uint64, internal uint32, gas uint64) (ioe0VerifySlice, []byte, ioe0VerifyCall) {
	e.t.Helper()
	c := e.callAs(owner, gas, "resume", instance, epoch, root, raw, checkpoint, jvm, internal)
	if c.err != nil {
		return ioe0VerifySlice{}, nil, c
	}
	values, err := e.contract.Methods["resume"].Outputs.Unpack(c.output)
	if err != nil || len(values) != 2 {
		e.t.Fatalf("decode resume outputs=%d: %v (%x)", len(values), err, c.output)
	}
	s := *abi.ConvertType(values[0], new(ioe0VerifySlice)).(*ioe0VerifySlice)
	return s, append([]byte(nil), values[1].([]byte)...), c
}

func (e *ioe0VerifyEnv) head(instance common.Hash) ioe0VerifyHead {
	e.t.Helper()
	c := e.callAs(ioe0VerifyOwner, ioe0VerifyOrdinaryGas, "head", instance)
	if c.err != nil {
		e.t.Fatalf("head: %v data=%x", c.err, c.output)
	}
	v, err := e.contract.Methods["head"].Outputs.Unpack(c.output)
	if err != nil || len(v) != 8 {
		e.t.Fatalf("decode head: %v values=%d", err, len(v))
	}
	return ioe0VerifyHead{v[0].(common.Address), v[1].(uint64), common.Hash(v[2].([32]byte)), common.Hash(v[3].([32]byte)), common.Hash(v[4].([32]byte)), common.Hash(v[5].([32]byte)), common.Hash(v[6].([32]byte)), v[7].(uint8)}
}

func ioe0VerifySliceRoot(s ioe0VerifySlice) common.Hash   { return common.Hash(s.CheckpointRoot) }
func ioe0VerifyMachineRoot(s ioe0VerifySlice) common.Hash { return common.Hash(s.MachineStateRoot) }

func ioe0VerifyAssertSuccess(t *testing.T, s ioe0VerifySlice, checkpoint []byte, c ioe0VerifyCall) {
	t.Helper()
	if c.err != nil || len(c.logs) != 1 {
		t.Fatalf("successful slice err=%v data=%x left=%d logs=%d", c.err, c.output, c.left, len(c.logs))
	}
	if s.Schema != 1 || s.Epoch == 0 || s.Lifecycle < ioe0VerifyRunnable || s.Lifecycle > ioe0VerifyUncaught || len(checkpoint) < ioe0VerifyHeaderSize || len(checkpoint) > ioe0VerifyMaxBlob {
		t.Fatalf("noncanonical slice=%+v checkpoint=%d", s, len(checkpoint))
	}
	if crypto.Keccak256Hash(checkpoint) != ioe0VerifySliceRoot(s) {
		t.Fatal("checkpointRoot is not keccak(exact checkpoint)")
	}
	if s.Lifecycle == ioe0VerifyRunnable && (s.Result != 0 || s.JavaKind != 0 || s.JavaRef != 0 || len(s.JavaClass) != 0) {
		t.Fatalf("RUNNABLE leaked terminal output: %+v", s)
	}
	if s.Lifecycle == ioe0VerifyReturned && (s.JavaKind != 0 || s.JavaRef != 0 || len(s.JavaClass) != 0) {
		t.Fatalf("RETURNED has Java exception output: %+v", s)
	}
	if s.Lifecycle == ioe0VerifyUncaught && (s.Result != 0 || s.JavaRef == 0 || (s.JavaKind == 0) == (len(s.JavaClass) == 0)) {
		t.Fatalf("UNCAUGHT outcome shape is not canonical: %+v", s)
	}
}

func ioe0VerifyCustomError(signature string, words ...uint64) []byte {
	out := append([]byte(nil), crypto.Keccak256([]byte(signature))[:4]...)
	for _, value := range words {
		var word [32]byte
		binary.BigEndian.PutUint64(word[24:], value)
		out = append(out, word[:]...)
	}
	return out
}

func ioe0VerifyAssertControl(t *testing.T, c ioe0VerifyCall, code uint64) {
	t.Helper()
	if !errors.Is(c.err, vm.ErrExecutionReverted) || !bytes.Equal(c.output, ioe0VerifyCustomError("LC0ControlError(uint256)", code)) || len(c.logs) != 0 {
		t.Fatalf("want LC0ControlError(%d), err=%v data=%x logs=%d", code, c.err, c.output, len(c.logs))
	}
}

func ioe0VerifyStateError(data []byte) (code, offset uint64, ok bool) {
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

func ioe0VerifyAssertState(t *testing.T, c ioe0VerifyCall, code uint64, offsets ...uint64) {
	t.Helper()
	got, off, ok := ioe0VerifyStateError(c.output)
	if !errors.Is(c.err, vm.ErrExecutionReverted) || !ok || got != code || len(c.logs) != 0 {
		t.Fatalf("want LC0StateError(%d,*), got %d/%d/%v err=%v data=%x logs=%d", code, got, off, ok, c.err, c.output, len(c.logs))
	}
	if len(offsets) != 0 && off != offsets[0] {
		t.Fatalf("LC0StateError offset=%d want=%d", off, offsets[0])
	}
}

func ioe0VerifyAssertHeadEqual(t *testing.T, have, want ioe0VerifyHead) {
	t.Helper()
	if !reflect.DeepEqual(have, want) {
		t.Fatalf("head changed\nhave %+v\nwant %+v", have, want)
	}
}

// ioe0VerifyReader decodes the exact custom 216-byte envelope and flat machine
// stream. It deliberately has no connection to Session.Start/Resume.
type ioe0VerifyReader struct {
	b []byte
	p int
}

func (r *ioe0VerifyReader) take(n int) ([]byte, error) {
	if n < 0 || r.p > len(r.b) || n > len(r.b)-r.p {
		return nil, fmt.Errorf("truncated at %d need %d", r.p, n)
	}
	v := r.b[r.p : r.p+n]
	r.p += n
	return v, nil
}
func (r *ioe0VerifyReader) u8() (uint8, error) {
	b, e := r.take(1)
	if e != nil {
		return 0, e
	}
	return b[0], nil
}
func (r *ioe0VerifyReader) u16() (uint16, error) {
	b, e := r.take(2)
	if e != nil {
		return 0, e
	}
	return binary.BigEndian.Uint16(b), nil
}
func (r *ioe0VerifyReader) u32() (uint32, error) {
	b, e := r.take(4)
	if e != nil {
		return 0, e
	}
	return binary.BigEndian.Uint32(b), nil
}
func (r *ioe0VerifyReader) u64() (uint64, error) {
	b, e := r.take(8)
	if e != nil {
		return 0, e
	}
	return binary.BigEndian.Uint64(b), nil
}

type ioe0VerifyFrame struct {
	Offset, FlagsOffset, SPOffset, BitmapOffset int
	Class, Method                               uint16
	PC                                          uint32
	CallPC                                      *big.Int
	Flags                                       uint8
	This                                        uint32
	SP, Locals                                  uint16
	StackOffsets, LocalOffsets                  []int
}
type ioe0VerifyHeapRecord struct {
	Offset, HandleOffset, MetadataOffset, ClassOffset, RankOffset, CountOffset int
	Handle                                                                     uint32
	Metadata                                                                   *big.Int
	Class                                                                      uint16
	Rank                                                                       uint8
	Count                                                                      uint32
	CellOffsets                                                                []int
	Object                                                                     bool
}
type ioe0VerifyMachine struct {
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
	Frames                                                              []ioe0VerifyFrame
	HeapHeaderOffset                                                    int
	NextHandle                                                          uint32
	OrdinaryObjects, OrdinaryArrays                                     uint16
	OrdinaryElements, OrdinaryFields                                    uint32
	EmergencyRef                                                        uint32
	ExceptionObjects                                                    uint16
	ExceptionFields                                                     uint32
	Heap                                                                []ioe0VerifyHeapRecord
	PendingOffset, PendingKindOffset, PendingRefOffset, PendingPCOffset int
	PendingActive, PendingKind                                          uint8
	PendingRef                                                          uint32
	PendingPC                                                           *big.Int
	InternCountOffset                                                   int
	InternHandleOffsets, InternHashOffsets                              []int
}
type ioe0VerifyCheckpoint struct {
	Bytes                                          []byte
	Schema                                         uint32
	Instance                                       common.Hash
	Epoch                                          uint64
	Parent, Runtime, Artifact, Config, MachineRoot common.Hash
	MachineLength                                  uint32
	Machine                                        ioe0VerifyMachine
}

func ioe0VerifyReadASCII(r *ioe0VerifyReader) (string, error) {
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

func ioe0VerifyDecodeCheckpoint(blob []byte) (ioe0VerifyCheckpoint, error) {
	var c ioe0VerifyCheckpoint
	c.Bytes = append([]byte(nil), blob...)
	if len(blob) < ioe0VerifyHeaderSize {
		return c, fmt.Errorf("short header")
	}
	if string(blob[:8]) != "JVMIOE01" {
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
	if c.Schema != 1 || int(c.MachineLength) != len(blob)-ioe0VerifyHeaderSize || len(blob) > ioe0VerifyMaxBlob {
		return c, fmt.Errorf("header length/schema")
	}
	r := &ioe0VerifyReader{b: blob[ioe0VerifyHeaderSize:]}
	if b, e := r.take(4); e != nil || string(b) != "IES1" {
		return c, fmt.Errorf("machine magic")
	}
	m := ioe0VerifyMachine{}
	m.LifecycleOffset = ioe0VerifyHeaderSize + r.p
	m.Lifecycle, _ = r.u8()
	m.ResultOffset = ioe0VerifyHeaderSize + r.p
	b, e := r.take(4)
	if e != nil {
		return c, e
	}
	m.Result = int32(binary.BigEndian.Uint32(b))
	m.JavaKindOffset = ioe0VerifyHeaderSize + r.p
	m.JavaKind, _ = r.u8()
	m.JavaRefOffset = ioe0VerifyHeaderSize + r.p
	m.JavaRef, _ = r.u32()
	m.TotalJvmOffset = ioe0VerifyHeaderSize + r.p
	m.TotalJvm, _ = r.u64()
	m.TotalInternalOffset = ioe0VerifyHeaderSize + r.p
	m.TotalInternal, _ = r.u64()
	if m.EntryClass, e = ioe0VerifyReadASCII(r); e != nil {
		return c, e
	}
	if m.Entry, e = ioe0VerifyReadASCII(r); e != nil {
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
		m.ClassOffsets = append(m.ClassOffsets, ioe0VerifyHeaderSize+r.p)
		m.InitOffsets = append(m.InitOffsets, ioe0VerifyHeaderSize+r.p)
		if _, e = r.u8(); e != nil {
			return c, e
		}
		m.StartedOffsets = append(m.StartedOffsets, ioe0VerifyHeaderSize+r.p)
		if _, e = r.u8(); e != nil {
			return c, e
		}
		n, e := r.u16()
		if e != nil {
			return c, e
		}
		var indices, vals []int
		for j := 0; j < int(n); j++ {
			indices = append(indices, ioe0VerifyHeaderSize+r.p)
			if _, e = r.u16(); e != nil {
				return c, e
			}
			vals = append(vals, ioe0VerifyHeaderSize+r.p)
			if _, e = r.take(32); e != nil {
				return c, e
			}
		}
		m.StaticIndexOffsets = append(m.StaticIndexOffsets, indices)
		m.StaticValueOffsets = append(m.StaticValueOffsets, vals)
	}
	m.FrameCountOffset = ioe0VerifyHeaderSize + r.p
	frames, e := r.u16()
	if e != nil {
		return c, e
	}
	for i := 0; i < int(frames); i++ {
		f := ioe0VerifyFrame{Offset: ioe0VerifyHeaderSize + r.p}
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
		f.FlagsOffset = ioe0VerifyHeaderSize + r.p
		f.Flags, e = r.u8()
		if e != nil {
			return c, e
		}
		f.This, e = r.u32()
		if e != nil {
			return c, e
		}
		f.SPOffset = ioe0VerifyHeaderSize + r.p
		f.SP, e = r.u16()
		if e != nil {
			return c, e
		}
		for j := 0; j < int(f.SP); j++ {
			f.StackOffsets = append(f.StackOffsets, ioe0VerifyHeaderSize+r.p)
			if _, e = r.take(32); e != nil {
				return c, e
			}
		}
		f.Locals, e = r.u16()
		if e != nil {
			return c, e
		}
		f.BitmapOffset = ioe0VerifyHeaderSize + r.p
		if _, e = r.take((int(f.Locals) + 7) / 8); e != nil {
			return c, e
		}
		for j := 0; j < int(f.Locals); j++ {
			f.LocalOffsets = append(f.LocalOffsets, ioe0VerifyHeaderSize+r.p)
			if _, e = r.take(32); e != nil {
				return c, e
			}
		}
		m.Frames = append(m.Frames, f)
	}
	m.HeapHeaderOffset = ioe0VerifyHeaderSize + r.p
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
		h := ioe0VerifyHeapRecord{Offset: ioe0VerifyHeaderSize + r.p, HandleOffset: ioe0VerifyHeaderSize + r.p}
		h.Handle, e = r.u32()
		if e != nil {
			return c, e
		}
		h.MetadataOffset = ioe0VerifyHeaderSize + r.p
		b, e = r.take(32)
		if e != nil {
			return c, e
		}
		h.Metadata = new(big.Int).SetBytes(b)
		h.Object = len(b) > 0 && b[0]&0x80 != 0
		h.ClassOffset = ioe0VerifyHeaderSize + r.p
		h.Class, e = r.u16()
		if e != nil {
			return c, e
		}
		h.RankOffset = ioe0VerifyHeaderSize + r.p
		h.Rank, e = r.u8()
		if e != nil {
			return c, e
		}
		h.CountOffset = ioe0VerifyHeaderSize + r.p
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
			h.CellOffsets = append(h.CellOffsets, ioe0VerifyHeaderSize+r.p)
			if _, e = r.take(width); e != nil {
				return c, e
			}
		}
		m.Heap = append(m.Heap, h)
	}
	m.PendingOffset = ioe0VerifyHeaderSize + r.p
	m.PendingActive, e = r.u8()
	if e != nil {
		return c, e
	}
	m.PendingKindOffset = ioe0VerifyHeaderSize + r.p
	m.PendingKind, e = r.u8()
	if e != nil {
		return c, e
	}
	m.PendingRefOffset = ioe0VerifyHeaderSize + r.p
	m.PendingRef, e = r.u32()
	if e != nil {
		return c, e
	}
	m.PendingPCOffset = ioe0VerifyHeaderSize + r.p
	b, e = r.take(32)
	if e != nil {
		return c, e
	}
	m.PendingPC = new(big.Int).SetBytes(b)
	m.InternCountOffset = ioe0VerifyHeaderSize + r.p
	interns, e := r.u16()
	if e != nil {
		return c, e
	}
	for i := 0; i < int(interns); i++ {
		m.InternHandleOffsets = append(m.InternHandleOffsets, ioe0VerifyHeaderSize+r.p)
		if _, e = r.u32(); e != nil {
			return c, e
		}
		m.InternHashOffsets = append(m.InternHashOffsets, ioe0VerifyHeaderSize+r.p)
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

func ioe0VerifyABIHash(t *testing.T, typesText []string, values ...any) common.Hash {
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
func ioe0VerifyArtifactRoot(t *testing.T, raw [][]byte) common.Hash {
	return ioe0VerifyABIHash(t, []string{"bytes32", "bytes[]"}, crypto.Keccak256Hash([]byte("JVMEVM:MC:IOE0:ARTIFACT:1")), raw)
}
func ioe0VerifyBootstrapRoot(t *testing.T) common.Hash {
	t.Helper()
	names := []string{"Object", "Cloneable", "Serializable", "Float", "Double", "Throwable", "Error", "VirtualMachineError", "StackOverflowError", "OutOfMemoryError", "LinkageError", "ExceptionInInitializerError", "IncompatibleClassChangeError", "NoClassDefFoundError", "AbstractMethodError", "Exception", "RuntimeException", "ArithmeticException", "NullPointerException", "NegativeArraySizeException", "ClassCastException", "ArrayStoreException", "IndexOutOfBoundsException", "ArrayIndexOutOfBoundsException", "Comparable", "CharSequence", "String", "IOException", "FileNotFoundException", "EOFException"}
	var hashes [30][32]byte
	for i, name := range names {
		path := filepath.Join("..", "..", "runtime", "bootstrap", name+".class.hex")
		switch name {
		case "String":
			path = filepath.Join("..", "..", "runtime", "local", "sc0", "bootstrap", "java", "lang", name+".class.hex")
		case "Throwable", "Exception", "ExceptionInInitializerError":
			path = filepath.Join("..", "..", "runtime", "local", "ioe0", "bootstrap", "java", "lang", name+".class.hex")
		case "IOException", "FileNotFoundException", "EOFException":
			path = filepath.Join("..", "..", "runtime", "local", "ioe0", "bootstrap", "java", "io", name+".class.hex")
		}
		text, err := os.ReadFile(path)
		if err != nil {
			t.Fatal(err)
		}
		raw, err := hex.DecodeString(strings.TrimSpace(string(text)))
		if err != nil {
			t.Fatal(err)
		}
		hashes[i] = crypto.Keccak256Hash(raw)
	}
	return ioe0VerifyABIHash(t, []string{"bytes32", "bytes32[30]"}, crypto.Keccak256Hash([]byte("JVMEVM:MC:IOE0:BOOTSTRAP:1")), hashes)
}
func ioe0VerifyConfigRoot(t *testing.T, runtimeHash, bootstrap, artifact common.Hash, entryClass, entry string, args []int32) common.Hash {
	return ioe0VerifyABIHash(t, []string{"bytes32", "uint32", "bytes32", "bytes32", "bytes32", "string", "string", "int32[]"}, crypto.Keccak256Hash([]byte("JVMEVM:MC:IOE0:CONFIG:1")), uint32(1), runtimeHash, bootstrap, artifact, entryClass, entry, args)
}
func ioe0VerifyMachineStateRoot(t *testing.T, c ioe0VerifyCheckpoint, machine []byte) common.Hash {
	return ioe0VerifyABIHash(t, []string{"bytes32", "uint32", "bytes32", "bytes32", "bytes32"}, crypto.Keccak256Hash([]byte("JVMEVM:MC:IOE0:MACHINE:1")), uint32(1), c.Artifact, c.Config, crypto.Keccak256Hash(machine))
}
func ioe0VerifyRehashMachine(t *testing.T, blob []byte) []byte {
	t.Helper()
	out := append([]byte(nil), blob...)
	c, e := ioe0VerifyDecodeCheckpoint(out)
	if e != nil {
		t.Fatal(e)
	}
	root := ioe0VerifyMachineStateRoot(t, c, out[216:])
	copy(out[180:212], root[:])
	return out
}

func ioe0VerifyValidate(e *ioe0VerifyEnv, raw [][]byte, blob []byte, gas uint64) ioe0VerifyCall {
	return e.callAs(ioe0VerifyOwner, gas, "validateCheckpoint", raw, blob)
}

func ioe0VerifyCheckEvent(t *testing.T, contract abi.ABI, instance common.Hash, s ioe0VerifySlice, c ioe0VerifyCall) {
	t.Helper()
	if len(c.logs) != 1 {
		t.Fatalf("events=%d", len(c.logs))
	}
	ev, ok := contract.Events["CheckpointCommitted"]
	if !ok {
		t.Fatal("event absent")
	}
	l := c.logs[0]
	if l.Address != ioe0VerifyAt || len(l.Topics) != 3 || l.Topics[0] != ev.ID || common.Hash(l.Topics[1]) != instance || new(big.Int).SetBytes(l.Topics[2][:]).Uint64() != s.Epoch {
		t.Fatalf("bad topics=%v", l.Topics)
	}
	v, err := ev.Inputs.NonIndexed().Unpack(l.Data)
	if err != nil {
		t.Fatal(err)
	}
	if common.Hash(v[0].([32]byte)) != ioe0VerifySliceRoot(s) || common.Hash(v[1].([32]byte)) != ioe0VerifyMachineRoot(s) || v[2].(uint8) != s.Lifecycle || v[3].(uint64) != s.TotalJvmSteps || v[4].(uint64) != s.TotalInternalSteps {
		t.Fatalf("bad event data=%v slice=%+v", v, s)
	}
}

// Everything below is an independent verifier corpus. javac only creates trusted
// raw Java 8 inputs; every asserted semantic result is produced by runtime.Call
// into IOException0Interpreter. No host JVM evaluates a root.
func ioe0VerifyCompileTrusted(t *testing.T, sources map[string]string, names []string) map[string][]byte {
	t.Helper()
	base := filepath.Join("..", "..", "..", "build", "java-diff-mc-ioe0-verifier")
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

func ioe0VerifyRaw(classes map[string][]byte, names ...string) [][]byte {
	out := make([][]byte, len(names))
	for i, name := range names {
		out[i] = classes[name]
	}
	return out
}

func ioe0VerifyInstance(label string) common.Hash {
	return crypto.Keccak256Hash([]byte("JVMEVM:MC:IOE0:VERIFY:" + label))
}

type ioe0VerifyRun struct {
	slice ioe0VerifySlice
	blob  []byte
	snaps []ioe0VerifyCheckpoint
}

func ioe0VerifyRunToEnd(t *testing.T, e *ioe0VerifyEnv, label string, raw [][]byte, class, method string, jvm uint64, internal uint32, gas uint64, dispatchCap uint64) ioe0VerifyRun {
	t.Helper()
	id := ioe0VerifyInstance(label)
	s, blob, call := e.start(ioe0VerifyOwner, id, raw, class, method, nil, jvm, internal, gas)
	ioe0VerifyAssertSuccess(t, s, blob, call)
	r := ioe0VerifyRun{slice: s, blob: blob}
	for slices := 0; ; slices++ {
		cp, err := ioe0VerifyDecodeCheckpoint(blob)
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
		if s.Lifecycle != ioe0VerifyRunnable {
			break
		}
		s, blob, call = e.resume(ioe0VerifyOwner, id, s.Epoch, ioe0VerifySliceRoot(s), raw, blob, jvm, internal, gas)
		ioe0VerifyAssertSuccess(t, s, blob, call)
		r.slice, r.blob = s, blob
	}
	return r
}

func ioe0VerifyHeapByRef(cp ioe0VerifyCheckpoint, ref uint32) (ioe0VerifyHeapRecord, bool) {
	for _, h := range cp.Machine.Heap {
		if h.Handle == ref {
			return h, true
		}
	}
	return ioe0VerifyHeapRecord{}, false
}

func ioe0VerifyRequireReturned(t *testing.T, r ioe0VerifyRun, want int32) {
	t.Helper()
	if r.slice.Lifecycle != ioe0VerifyReturned || r.slice.Result != want || r.slice.JavaKind != 0 || r.slice.JavaRef != 0 || len(r.slice.JavaClass) != 0 {
		t.Fatalf("returned shape=%+v want=%d", r.slice, want)
	}
}

func ioe0VerifyRequireUncaught(t *testing.T, r ioe0VerifyRun, kind uint8, class string) {
	t.Helper()
	if r.slice.Lifecycle != ioe0VerifyUncaught || r.slice.Result != 0 || r.slice.JavaKind != kind || r.slice.JavaRef == 0 || string(r.slice.JavaClass) != class {
		t.Fatalf("uncaught shape=%+v want kind=%d class=%q", r.slice, kind, class)
	}
	last := r.snaps[len(r.snaps)-1].Machine
	if len(last.Frames) != 0 || last.PendingActive != 1 || last.PendingRef != r.slice.JavaRef || last.PendingKind != kind {
		t.Fatalf("terminal pending does not retain exact ref: %+v", last)
	}
}

func ioe0VerifyValidateOK(t *testing.T, e *ioe0VerifyEnv, raw [][]byte, blob []byte) common.Hash {
	t.Helper()
	c := ioe0VerifyValidate(e, raw, blob, ioe0VerifyBoundaryGas)
	if c.err != nil {
		t.Fatalf("validate: %v data=%x", c.err, c.output)
	}
	v, err := e.contract.Methods["validateCheckpoint"].Outputs.Unpack(c.output)
	if err != nil || len(v) != 1 {
		t.Fatalf("validate output: %v/%d", err, len(v))
	}
	return common.Hash(v[0].([32]byte))
}

func ioe0VerifyMutateRehash(t *testing.T, blob []byte, at int, mutate func([]byte)) []byte {
	t.Helper()
	cp, err := ioe0VerifyDecodeCheckpoint(blob)
	if err != nil {
		t.Fatal(err)
	}
	out := append([]byte(nil), blob...)
	if at < ioe0VerifyHeaderSize || at >= len(out) {
		t.Fatalf("mutation offset=%d len=%d", at, len(out))
	}
	mutate(out[at:])
	root := ioe0VerifyMachineStateRoot(t, cp, out[ioe0VerifyHeaderSize:])
	copy(out[180:212], root[:])
	return out
}

func ioe0VerifyErrorSelector(data []byte, signature string) bool {
	return len(data) >= 4 && bytes.Equal(data[:4], crypto.Keccak256([]byte(signature))[:4])
}

// ioe0VerifyValue decodes one flat TLS1/IES1 tagged 256-bit value.  The low
// 64 bits are the payload and the next byte is the value tag.
func ioe0VerifyValue(b []byte) (uint8, uint64) {
	v := new(big.Int).SetBytes(b[:32])
	return uint8(new(big.Int).Rsh(new(big.Int).Set(v), 64).Uint64()), v.Uint64()
}

func ioe0VerifyPutValue(b []byte, tag uint8, payload uint64) {
	v := new(big.Int).Lsh(new(big.Int).SetUint64(uint64(tag)), 64)
	v.Or(v, new(big.Int).SetUint64(payload)).FillBytes(b[:32])
}

func ioe0VerifyStringClass(raw [][]byte) uint16 { return uint16(len(raw) + 26) }

func ioe0VerifyObject(cp ioe0VerifyCheckpoint, class uint16) []ioe0VerifyHeapRecord {
	var out []ioe0VerifyHeapRecord
	for _, h := range cp.Machine.Heap {
		if h.Object && h.Class == class {
			out = append(out, h)
		}
	}
	return out
}

func ioe0VerifyHeap(cp ioe0VerifyCheckpoint, handle uint32) (ioe0VerifyHeapRecord, bool) {
	for _, h := range cp.Machine.Heap {
		if h.Handle == handle {
			return h, true
		}
	}
	return ioe0VerifyHeapRecord{}, false
}

func ioe0VerifyInterns(cp ioe0VerifyCheckpoint) ([]uint32, []uint32) {
	handles := make([]uint32, len(cp.Machine.InternHandleOffsets))
	hashes := make([]uint32, len(handles))
	for i := range handles {
		handles[i] = binary.BigEndian.Uint32(cp.Bytes[cp.Machine.InternHandleOffsets[i]:])
		hashes[i] = binary.BigEndian.Uint32(cp.Bytes[cp.Machine.InternHashOffsets[i]:])
	}
	return handles, hashes
}

func ioe0VerifyJavaHash(units ...uint16) uint32 {
	var h uint32
	for _, u := range units {
		h = h*31 + uint32(u)
	}
	return h
}

func ioe0VerifyAssertProfile(t *testing.T, c ioe0VerifyCall, reason, pc uint64) {
	t.Helper()
	want := ioe0VerifyCustomError("StringProfileError(uint256,uint256)", reason, pc)
	if !errors.Is(c.err, vm.ErrExecutionReverted) || !bytes.Equal(c.output, want) || len(c.logs) != 0 {
		t.Fatalf("want StringProfileError(%d,%d), err=%v data=%x logs=%d", reason, pc, c.err, c.output, len(c.logs))
	}
}

func ioe0VerifyAssertHardSelector(t *testing.T, c ioe0VerifyCall, signature string) {
	t.Helper()
	if !errors.Is(c.err, vm.ErrExecutionReverted) || !ioe0VerifyErrorSelector(c.output, signature) || len(c.logs) != 0 {
		t.Fatalf("want %s revert, err=%v data=%x logs=%d", signature, c.err, c.output, len(c.logs))
	}
}

// ioe0VerifyClassCode is a deliberately small classfile reader used only to find
// bytecode PCs and make same-length negative mutations in trusted fixtures.  It
// never participates in the production transport or execution path.
type ioe0VerifyClassCode struct {
	codeOff  int
	code     []byte
	cpUTF    map[uint16]string
	cpUTFOff map[uint16]int
}

func ioe0VerifyFindCode(t *testing.T, class []byte, method, descriptor string) ioe0VerifyClassCode {
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
				return ioe0VerifyClassCode{co, class[co : co+clen], utf, uoff}
			}
			p += z
		}
	}
	t.Fatalf("method %s%s absent", method, descriptor)
	return ioe0VerifyClassCode{}
}
func ioe0VerifyOpcodePC(t *testing.T, class []byte, method, desc string, opcode byte, ordinal int) uint64 {
	c := ioe0VerifyFindCode(t, class, method, desc)
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

func ioe0VerifyNewEnvWithCode(t *testing.T, code []byte) *ioe0VerifyEnv {
	t.Helper()
	contract, err := ABI()
	if err != nil {
		t.Fatal(err)
	}
	st, err := state.New(types.EmptyRootHash, state.NewDatabaseForTesting())
	if err != nil {
		t.Fatal(err)
	}
	st.CreateAccount(ioe0VerifyAt)
	st.SetCode(ioe0VerifyAt, code, tracing.CodeChangeUnspecified)
	return &ioe0VerifyEnv{t: t, state: st, code: append([]byte(nil), code...), contract: contract}
}

// ioe0VerifySyntheticObject emits a small, structurally valid Java 8 Object
// class. It is intentionally EVM-profile-only. "publish" has a real putstatic
// callback and "fail" really throws its receiver; neither is run on a host JVM.
func ioe0VerifySyntheticObject(t *testing.T, inheritedFields int, mode string) []byte {
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

func ioe0VerifyFinal(t *testing.T, source, root, method string, names []string, jvm uint64, gas, cap uint64) (ioe0VerifyRun, [][]byte) {
	t.Helper()
	classes := ioe0VerifyCompileTrusted(t, map[string]string{root + ".java": source}, names)
	raw := ioe0VerifyRaw(classes, names...)
	e := ioe0VerifyNewEnv(t)
	defer e.close()
	return ioe0VerifyRunToEnd(t, e, t.Name(), raw, root, method, jvm, 4096, gas, cap), raw
}

// 01..08 allocation, quota, layout, checkpoint and declared-bound probes.

func TestIOE0Verify01ArtifactAndThirtyImageCommitments(t *testing.T) {
	code, err := Runtime()
	if err != nil {
		t.Fatal(err)
	}
	if len(code) == 0 || len(code) > 256*1024 {
		t.Fatal("runtime size")
	}
	hash, err := RuntimeHash()
	if err != nil {
		t.Fatal(err)
	}
	sum := sha256.Sum256(code)
	if hash != hex.EncodeToString(sum[:]) {
		t.Fatal("runtime hash")
	}
	a, err := ABI()
	if err != nil {
		t.Fatal(err)
	}
	if len(a.Methods) != 4 {
		t.Fatal("unexpected public API")
	}
	if _, ok := a.Errors["ThrowableAPIProfileError"]; !ok {
		t.Fatal("getter profile error absent")
	}
	cs := ioe0VerifyCompileTrusted(t, map[string]string{"IArtifact.java": `public class IArtifact{public static int run(){return 1;}}`}, []string{"IArtifact"})
	raw := ioe0VerifyRaw(cs, "IArtifact")
	e := ioe0VerifyNewEnv(t)
	defer e.close()
	r := ioe0VerifyRunToEnd(t, e, "artifact-root", raw, "IArtifact", "run", 4096, 4096, ioe0VerifyOrdinaryGas, 4096)
	ioe0VerifyRequireReturned(t, r, 1)
	cp := r.snaps[len(r.snaps)-1]
	if cp.Machine.ClassCount != 31 || cp.Config != ioe0VerifyConfigRoot(t, crypto.Keccak256Hash(code), ioe0VerifyBootstrapRoot(t), ioe0VerifyArtifactRoot(t, raw), "IArtifact", "run", nil) {
		t.Fatal("30-image config commitment mismatch")
	}
}

func TestIOE0Verify04GetterOriginNotDynamicClass(t *testing.T) {
	cases := []struct {
		label, body string
		blocked     uint64
	}{
		{"ordinary-ae", `ArithmeticException e=new ArithmeticException();return e.getMessage()==null&&e.getCause()==null?1:0;`, 0},
		{"ordinary-oom", `OutOfMemoryError e=new OutOfMemoryError();return e.getMessage()==null&&e.getCause()==null?1:0;`, 0},
		{"implicit-ae-cause", `try{int z=0;return 1/z;}catch(ArithmeticException e){return e.getCause()==null?1:0;}`, 0},
		{"implicit-ae-message", `try{int z=0;return 1/z;}catch(ArithmeticException e){return e.getMessage()==null?1:0;}`, 1},
		{"implicit-negative-cause", `try{int[] a=new int[-1];return a.length;}catch(NegativeArraySizeException e){return e.getCause()==null?1:0;}`, 4},
		{"implicit-npe", `try{int[] a=null;return a.length;}catch(NullPointerException e){return e.getMessage()==null&&e.getCause()==null?1:0;}`, 0},
	}
	for _, tc := range cases {
		t.Run(tc.label, func(t *testing.T) {
			cs := ioe0VerifyCompileTrusted(t, map[string]string{"IOrigin.java": "public class IOrigin {public static int run(){" + tc.body + "}}"}, []string{"IOrigin"})
			raw := ioe0VerifyRaw(cs, "IOrigin")
			e := ioe0VerifyNewEnv(t)
			defer e.close()
			if tc.blocked != 0 {
				_, _, c := e.start(ioe0VerifyOwner, ioe0VerifyInstance(tc.label), raw, "IOrigin", "run", nil, 4096, 4096, ioe0VerifyOrdinaryGas)
				pc := ioe0VerifyOpcodePC(t, raw[0], "run", "()I", 0xb6, 0)
				if !errors.Is(c.err, vm.ErrExecutionReverted) || !bytes.Equal(c.output, ioe0VerifyCustomError("ThrowableAPIProfileError(uint256,uint256)", tc.blocked, pc)) {
					t.Fatalf("getter profile: %v %x", c.err, c.output)
				}
				return
			}
			var root [32]byte
			for _, q := range []uint64{4096, 1} {
				r := ioe0VerifyRunToEnd(t, e, fmt.Sprintf("%s-%d", tc.label, q), raw, "IOrigin", "run", q, 4096, ioe0VerifyOrdinaryGas, 4096)
				ioe0VerifyRequireReturned(t, r, 1)
				if q == 4096 {
					root = r.slice.MachineStateRoot
				} else if root != r.slice.MachineStateRoot {
					t.Fatal("getter quantum mismatch")
				}
			}
		})
	}
}

func TestIOE0Verify21ExplicitEIIEMayHaveLaterAllocatedCause(t *testing.T) {
	src := `public class ILater {public static int run(){ExceptionInInitializerError e=new ExceptionInInitializerError(new Throwable());return e.getCause()==e.getException()&&e.getException()!=null&&e.getMessage()==null?1:0;}}`
	cs := ioe0VerifyCompileTrusted(t, map[string]string{"ILater.java": src}, []string{"ILater"})
	raw := ioe0VerifyRaw(cs, "ILater")
	e := ioe0VerifyNewEnv(t)
	defer e.close()
	r := ioe0VerifyRunToEnd(t, e, "later-cause", raw, "ILater", "run", 1, 1, ioe0VerifyOrdinaryGas, 4096)
	ioe0VerifyRequireReturned(t, r, 1)
	cp := r.snaps[len(r.snaps)-1]
	found := false
	for _, h := range cp.Machine.Heap {
		if !h.Object || h.Class != uint16(len(raw)+11) {
			continue
		}
		if len(h.CellOffsets) != 3 {
			t.Fatal("EIIE physical fields")
		}
		tag, ref := ioe0VerifyValue(cp.Bytes[h.CellOffsets[2]:])
		if tag != 2 || ref <= uint64(h.Handle) {
			t.Fatal("ordinary later cause lost")
		}
		found = true
	}
	if !found {
		t.Fatal("ordinary EIIE record absent")
	}
	ioe0VerifyValidateOK(t, e, raw, cp.Bytes)
}

func TestIOE0Verify02ReservedImagesRejectReplacement(t *testing.T) {
	cs := ioe0VerifyCompileTrusted(t, map[string]string{"IReserved.java": `public class IReserved{public static int run(){return 1;}}`}, []string{"IReserved"})
	for _, name := range []string{"IOException", "FileNotFoundException", "EOFException"} {
		t.Run(name, func(t *testing.T) {
			text, err := os.ReadFile(filepath.Join("..", "..", "runtime", "local", "ioe0", "bootstrap", "java", "io", name+".class.hex"))
			if err != nil {
				t.Fatal(err)
			}
			image, err := hex.DecodeString(strings.TrimSpace(string(text)))
			if err != nil {
				t.Fatal(err)
			}
			e := ioe0VerifyNewEnv(t)
			defer e.close()
			_, _, c := e.start(ioe0VerifyOwner, ioe0VerifyInstance(name), [][]byte{cs["IReserved"], image}, "IReserved", "run", nil, 4096, 4096, ioe0VerifyOrdinaryGas)
			if c.err == nil || len(c.logs) != 0 {
				t.Fatal("raw reserved replacement accepted")
			}
		})
	}
}

func TestIOE0Verify03MessageIdentityUTF16AndNull(t *testing.T) {
	src := `public class IMessage {public static int run(){String s=new String(new char[]{0,'x','\ud800'});java.io.IOException e=new java.io.IOException(s);return e.getMessage()==s&&e.getMessage().charAt(2)==55296&&e.getCause()==null&&new java.io.EOFException((String)null).getMessage()==null?1:0;}}`
	cs := ioe0VerifyCompileTrusted(t, map[string]string{"IMessage.java": src}, []string{"IMessage"})
	raw := ioe0VerifyRaw(cs, "IMessage")
	e := ioe0VerifyNewEnv(t)
	defer e.close()
	var root [32]byte
	for _, q := range []uint64{4096, 1, 7} {
		r := ioe0VerifyRunToEnd(t, e, fmt.Sprintf("message-%d", q), raw, "IMessage", "run", q, 4096, ioe0VerifyOrdinaryGas, 4096)
		ioe0VerifyRequireReturned(t, r, 1)
		if q == 4096 {
			root = r.slice.MachineStateRoot
		} else if root != r.slice.MachineStateRoot {
			t.Fatal("message state differs")
		}
	}
}

func TestIOE0Verify05VirtualOverrideAndSpecialGetter(t *testing.T) {
	src := `public class IOverride {static class P extends java.io.IOException {String m;P(String s){super(s);m=s;}public String getMessage(){return m;}String base(){return super.getMessage();}}public static int run(){String s=new String(new char[]{'v'});P p=new P(s);Throwable t=p;return t.getMessage()==s&&p.base()==s&&p.getCause()==null?1:0;}}`
	r, _ := ioe0VerifyFinal(t, src, "IOverride", "run", []string{"IOverride", "IOverride$P"}, 1, ioe0VerifyOrdinaryGas, 4096)
	ioe0VerifyRequireReturned(t, r, 1)
}

func TestIOE0Verify06UnmodeledAPIsStayHardUnsupported(t *testing.T) {
	cases := []string{`Throwable t=new Throwable();t.initCause(new Throwable());return 0;`, `Throwable t=new Throwable(new Throwable());return 0;`, `return new ExceptionInInitializerError("message").getMessage().length();`}
	for i, body := range cases {
		t.Run(fmt.Sprint(i), func(t *testing.T) {
			cs := ioe0VerifyCompileTrusted(t, map[string]string{"IAbsent.java": "public class IAbsent {public static int run(){" + body + "}}"}, []string{"IAbsent"})
			e := ioe0VerifyNewEnv(t)
			defer e.close()
			_, _, c := e.start(ioe0VerifyOwner, ioe0VerifyInstance(fmt.Sprint(i)), ioe0VerifyRaw(cs, "IAbsent"), "IAbsent", "run", nil, 4096, 4096, ioe0VerifyOrdinaryGas)
			ioe0VerifyAssertHardSelector(t, c, "CallError(uint256,uint256)")
		})
	}
}

func TestIOE0Verify07NullGetterReceiverStillRaisesNPE(t *testing.T) {
	src := `public class INullGetter {public static int run(){Throwable t=null;try{t.getMessage();return 0;}catch(NullPointerException e){return e.getMessage()==null&&e.getCause()==null?1:0;}}}`
	r, _ := ioe0VerifyFinal(t, src, "INullGetter", "run", []string{"INullGetter"}, 1, ioe0VerifyOrdinaryGas, 4096)
	ioe0VerifyRequireReturned(t, r, 1)
}

func TestIOE0Verify08GetterLookalikesAreOrdinaryCode(t *testing.T) {
	src := `public class ILook {static String getMessage(){return "ordinary";}Throwable getCause(){return null;}public static int run(){return getMessage().length()==8&&new ILook().getCause()==null?1:0;}}`
	r, _ := ioe0VerifyFinal(t, src, "ILook", "run", []string{"ILook"}, 1, ioe0VerifyOrdinaryGas, 4096)
	ioe0VerifyRequireReturned(t, r, 1)
}

func TestIOE0Verify09OrdinaryFieldLimitAndInheritedOffsets(t *testing.T) {
	cs := ioe0VerifyCompileTrusted(t, map[string]string{"IFields.java": `public class IFields{public static int run(){try{java.io.IOException e=new java.io.IOException();return e.getCause()==null&&e.getMessage()==null?1:0;}catch(OutOfMemoryError e){return 7;}}}`}, []string{"IFields"})
	for _, n := range []int{0, 1, 1022, 1023} {
		t.Run(fmt.Sprint(n), func(t *testing.T) {
			raw := [][]byte{cs["IFields"], ioe0VerifySyntheticObject(t, n, "canonical")}
			e := ioe0VerifyNewEnv(t)
			defer e.close()
			r := ioe0VerifyRunToEnd(t, e, fmt.Sprint(n), raw, "IFields", "run", 4096, 4096, ioe0VerifyBoundaryGas, 65536)
			want := int32(1)
			if n == 1023 {
				want = 7
			}
			ioe0VerifyRequireReturned(t, r, want)
			m := r.snaps[len(r.snaps)-1].Machine
			if n <= 1022 && m.OrdinaryFields != uint32(n+2) {
				t.Fatal("inherited field accounting")
			}
			if n == 1023 && m.OrdinaryObjects != 0 {
				t.Fatal("failed allocation charged object")
			}
		})
	}
}

func TestIOE0Verify10ArenaNotOrdinaryPerObjectFieldLimit(t *testing.T) {
	cs := ioe0VerifyCompileTrusted(t, map[string]string{"IArenaFields.java": `public class IArenaFields{public static int run(){try{int[] a=null;return a.length;}catch(NullPointerException e){return e.getCause()==null&&e.getMessage()==null?1:0;}}}`}, []string{"IArenaFields"})
	raw := [][]byte{cs["IArenaFields"], ioe0VerifySyntheticObject(t, 1023, "canonical")}
	e := ioe0VerifyNewEnv(t)
	defer e.close()
	r := ioe0VerifyRunToEnd(t, e, "arena-fields", raw, "IArenaFields", "run", 4096, 4096, ioe0VerifyBoundaryGas, 65536)
	ioe0VerifyRequireReturned(t, r, 1)
	m := r.snaps[len(r.snaps)-1].Machine
	if m.ExceptionObjects != 1 || m.ExceptionFields != 2050 {
		t.Fatalf("arena/emergency field count %+v", m)
	}
}

func TestIOE0Verify11FullOrdinaryHeapStillRaisesAE(t *testing.T) {
	src := `public class IFull {static Object sink;public static int run(){for(int i=0;i<1024;i++)sink=new Object();try{int z=0;return 1/z;}catch(ArithmeticException e){return e.getCause()==null?1:0;}}}`
	r, _ := ioe0VerifyFinal(t, src, "IFull", "run", []string{"IFull"}, 4096, ioe0VerifyBoundaryGas, 65536)
	ioe0VerifyRequireReturned(t, r, 1)
	m := r.snaps[len(r.snaps)-1].Machine
	if m.OrdinaryObjects != 1024 || m.ExceptionObjects != 1 {
		t.Fatal("ordinary versus arena quota")
	}
}

func TestIOE0Verify12ArenaAndEmergencySelfCause(t *testing.T) {
	src := `public class IArena{static int div(){int z=0;return 1/z;}public static int run(){for(int i=0;i<256;i++)try{div();}catch(ArithmeticException e){}try{return div();}catch(OutOfMemoryError e){return 1;}}}`
	r, _ := ioe0VerifyFinal(t, src, "IArena", "run", []string{"IArena"}, 4096, ioe0VerifyBoundaryGas, 65536)
	ioe0VerifyRequireReturned(t, r, 1)
	cp := r.snaps[len(r.snaps)-1]
	if cp.Machine.ExceptionObjects != 256 {
		t.Fatal("arena count")
	}
	for _, h := range cp.Machine.Heap {
		if !h.Object || h.Metadata.Uint64()&255 == 0 {
			continue
		}
		tag, cause := ioe0VerifyValue(cp.Bytes[h.CellOffsets[1]:])
		if tag != 2 || cause != uint64(h.Handle) {
			t.Fatal("VM self cause")
		}
	}
}

func TestIOE0Verify13WrapperOOMHasNoPhantomEIIE(t *testing.T) {
	src := `public class IWrapOOM{static class B{static int x=fail();static int fail(){throw new RuntimeException();}}static int div(){int z=0;return 1/z;}public static int run(){for(int i=0;i<256;i++)try{div();}catch(ArithmeticException e){}try{return B.x;}catch(OutOfMemoryError e){return 1;}}}`
	r, _ := ioe0VerifyFinal(t, src, "IWrapOOM", "run", []string{"IWrapOOM", "IWrapOOM$B"}, 4096, ioe0VerifyBoundaryGas, 65536)
	ioe0VerifyRequireReturned(t, r, 1)
	cp := r.snaps[len(r.snaps)-1]
	for _, h := range cp.Machine.Heap {
		if h.Object && h.Metadata.Uint64()&255 == 3 {
			t.Fatal("phantom wrapper")
		}
	}
}

func TestIOE0Verify14ExactCheckpointLimit(t *testing.T) {
	for _, method := range []string{"abcdef", "abcdefg"} {
		t.Run(method, func(t *testing.T) {
			src := fmt.Sprintf("public class ICap{public static int %s(){long[] a=new long[65536];long[] b=new long[65455];return a.length+b.length;}}", method)
			cs := ioe0VerifyCompileTrusted(t, map[string]string{"ICap.java": src}, []string{"ICap"})
			raw := ioe0VerifyRaw(cs, "ICap")
			e := ioe0VerifyNewEnv(t)
			defer e.close()
			id := ioe0VerifyInstance(method)
			s, b, c := e.start(ioe0VerifyOwner, id, raw, "ICap", method, nil, 4096, 4096, ioe0VerifyBoundaryGas)
			if method == "abcdefg" {
				ioe0VerifyAssertState(t, c, 1, 0)
				if e.head(id) != (ioe0VerifyHead{}) {
					t.Fatal("oversize published")
				}
				return
			}
			ioe0VerifyAssertSuccess(t, s, b, c)
			if len(b) != 1<<20 {
				t.Fatalf("exact cap got%d", len(b))
			}
			ioe0VerifyValidateOK(t, e, raw, b)
		})
	}
}

func ioe0VerifyStateFixture(t *testing.T, method string) (*ioe0VerifyEnv, [][]byte, ioe0VerifyRun) {
	t.Helper()
	src := `public class IState {static String m="message";static Object o=new Object();static Throwable other=new Throwable();public static int ordinary()throws Throwable{throw new java.io.IOException(m);}public static int vm(){try{int[] a=null;return a.length;}catch(NullPointerException e){return 1;}}}`
	cs := ioe0VerifyCompileTrusted(t, map[string]string{"IState.java": src}, []string{"IState"})
	raw := ioe0VerifyRaw(cs, "IState")
	e := ioe0VerifyNewEnv(t)
	r := ioe0VerifyRunToEnd(t, e, method, raw, "IState", method, 4096, 4096, ioe0VerifyOrdinaryGas, 4096)
	return e, raw, r
}

func TestIOE0Verify15CounterAndSharedHandleBounds(t *testing.T) {
	e, raw, r := ioe0VerifyStateFixture(t, "ordinary")
	defer e.close()
	cp := r.snaps[len(r.snaps)-1]
	for _, mut := range []struct {
		off   int
		width int
		value uint64
	}{{cp.Machine.HeapHeaderOffset, 4, 65535}, {cp.Machine.HeapHeaderOffset + 4, 2, 1025}, {cp.Machine.HeapHeaderOffset + 12, 4, 65537}, {cp.Machine.HeapHeaderOffset + 8, 4, 262145}} {
		bad := ioe0VerifyMutateRehash(t, cp.Bytes, mut.off, func(b []byte) {
			if mut.width == 4 {
				binary.BigEndian.PutUint32(b, uint32(mut.value))
			} else {
				binary.BigEndian.PutUint16(b, uint16(mut.value))
			}
		})
		c := ioe0VerifyValidate(e, raw, bad, ioe0VerifyBoundaryGas)
		if c.err == nil || !ioe0VerifyErrorSelector(c.output, "LC0StateError(uint256,uint256)") {
			t.Fatalf("counter accepted/misclassified %v %x", c.err, c.output)
		}
	}
}

func TestIOE0Verify16ImplicitAEDoesNotAllocateMessageStrings(t *testing.T) {
	r, _ := ioe0VerifyFinal(t, `public class INoMessage{public static int run(){int z=0;return 1/z;}}`, "INoMessage", "run", []string{"INoMessage"}, 4096, ioe0VerifyOrdinaryGas, 4096)
	ioe0VerifyRequireUncaught(t, r, 1, "")
	m := r.snaps[len(r.snaps)-1].Machine
	if m.ExceptionObjects != 1 || m.OrdinaryObjects != 0 || m.OrdinaryArrays != 0 || len(m.InternHandleOffsets) != 0 || m.NextHandle != 2 {
		t.Fatal("unrequested VM message allocation")
	}
}

func TestIOE0Verify17OrdinaryCauseIsNullOrSelfNotOther(t *testing.T) {
	e, raw, r := ioe0VerifyStateFixture(t, "ordinary")
	defer e.close()
	cp := r.snaps[len(r.snaps)-1]
	h, ok := ioe0VerifyHeapByRef(cp, r.slice.JavaRef)
	if !ok {
		t.Fatal("missing thrown I/O object")
	}
	var other uint32
	for _, x := range cp.Machine.Heap {
		if x.Class == uint16(len(raw)+5) {
			other = x.Handle
		}
	}
	if other == 0 {
		t.Fatal("missing ordinary Throwable")
	}
	bad := ioe0VerifyMutateRehash(t, cp.Bytes, h.CellOffsets[1], func(b []byte) { ioe0VerifyPutValue(b, 2, uint64(other)) })
	ioe0VerifyAssertState(t, ioe0VerifyValidate(e, raw, bad, ioe0VerifyOrdinaryGas), 7)
}

func TestIOE0Verify18VMRequiresSelfCause(t *testing.T) {
	e, raw, r := ioe0VerifyStateFixture(t, "vm")
	defer e.close()
	cp := r.snaps[len(r.snaps)-1]
	for _, h := range cp.Machine.Heap {
		if !h.Object || h.Metadata.Uint64()&255 != 6 {
			continue
		}
		for _, ref := range []uint64{0, 1} {
			bad := ioe0VerifyMutateRehash(t, cp.Bytes, h.CellOffsets[1], func(b []byte) { ioe0VerifyPutValue(b, 2, ref) })
			ioe0VerifyAssertState(t, ioe0VerifyValidate(e, raw, bad, ioe0VerifyOrdinaryGas), 7)
		}
		return
	}
	t.Fatal("missing VM NPE")
}

func TestIOE0Verify19VMMessageMustRemainNull(t *testing.T) {
	e, raw, r := ioe0VerifyStateFixture(t, "vm")
	defer e.close()
	cp := r.snaps[len(r.snaps)-1]
	strings := ioe0VerifyObject(cp, ioe0VerifyStringClass(raw))
	if len(strings) != 1 {
		t.Fatal("literal")
	}
	for _, h := range cp.Machine.Heap {
		if h.Object && h.Metadata.Uint64()&255 == 6 {
			bad := ioe0VerifyMutateRehash(t, cp.Bytes, h.CellOffsets[0], func(b []byte) { ioe0VerifyPutValue(b, 2, uint64(strings[0].Handle)) })
			ioe0VerifyAssertState(t, ioe0VerifyValidate(e, raw, bad, ioe0VerifyOrdinaryGas), 7)
			return
		}
	}
	t.Fatal("missing NPE")
}

func TestIOE0Verify20MessageTypeCannotBeOrdinaryObject(t *testing.T) {
	e, raw, r := ioe0VerifyStateFixture(t, "ordinary")
	defer e.close()
	cp := r.snaps[len(r.snaps)-1]
	h, _ := ioe0VerifyHeapByRef(cp, r.slice.JavaRef)
	objects := ioe0VerifyObject(cp, uint16(len(raw)))
	if len(objects) != 1 {
		t.Fatal("Object")
	}
	bad := ioe0VerifyMutateRehash(t, cp.Bytes, h.CellOffsets[0], func(b []byte) { ioe0VerifyPutValue(b, 2, uint64(objects[0].Handle)) })
	ioe0VerifyAssertState(t, ioe0VerifyValidate(e, raw, bad, ioe0VerifyOrdinaryGas), 6)
}

func TestIOE0Verify22OrdinaryEIIEAllowsErrorCause(t *testing.T) {
	src := `public class IErrorCause{public static int run(){Error cause=new Error();ExceptionInInitializerError e=new ExceptionInInitializerError(cause);return e.getCause()==cause&&e.getException()==cause&&e.getMessage()==null?1:0;}}`
	r, _ := ioe0VerifyFinal(t, src, "IErrorCause", "run", []string{"IErrorCause"}, 1, ioe0VerifyOrdinaryGas, 4096)
	ioe0VerifyRequireReturned(t, r, 1)
}

func TestIOE0Verify23VMWrapperCauseRestrictions(t *testing.T) {
	src := `public class IWrap{static Error err=new Error();static class B{static int x=fail();static int fail(){throw new RuntimeException();}}public static int run(){return B.x;}}`
	cs := ioe0VerifyCompileTrusted(t, map[string]string{"IWrap.java": src}, []string{"IWrap", "IWrap$B"})
	raw := ioe0VerifyRaw(cs, "IWrap", "IWrap$B")
	e := ioe0VerifyNewEnv(t)
	defer e.close()
	r := ioe0VerifyRunToEnd(t, e, "VMwrap", raw, "IWrap", "run", 1, 1, ioe0VerifyOrdinaryGas, 4096)
	ioe0VerifyRequireUncaught(t, r, 3, "")
	cp := r.snaps[len(r.snaps)-1]
	h, _ := ioe0VerifyHeapByRef(cp, r.slice.JavaRef)
	var errorRef uint32
	for _, x := range cp.Machine.Heap {
		if x.Class == uint16(len(raw)+6) && x.Metadata.Uint64()&255 == 0 {
			errorRef = x.Handle
		}
	}
	if errorRef == 0 {
		t.Fatal("ordinary Error")
	}
	for _, ref := range []uint64{0, uint64(h.Handle), uint64(errorRef)} {
		bad := ioe0VerifyMutateRehash(t, cp.Bytes, h.CellOffsets[2], func(b []byte) { ioe0VerifyPutValue(b, 2, ref) })
		ioe0VerifyAssertState(t, ioe0VerifyValidate(e, raw, bad, ioe0VerifyOrdinaryGas), 7)
	}
}

func TestIOE0Verify24ShadowFieldsDoNotReplaceCanonicalFields(t *testing.T) {
	src := `public class IShadow{static class P extends java.io.IOException{public String detailMessage;public Throwable cause;P(String s){super(s);detailMessage="shadow";cause=new Error();}}public static int run(){String s="base";P p=new P(s);return p.getMessage()==s&&p.getCause()==null&&p.detailMessage.length()==6&&p.cause!=null?1:0;}}`
	r, _ := ioe0VerifyFinal(t, src, "IShadow", "run", []string{"IShadow", "IShadow$P"}, 1, ioe0VerifyOrdinaryGas, 4096)
	ioe0VerifyRequireReturned(t, r, 1)
}

func TestIOE0Verify25CauseCyclesAndConstructorPhases(t *testing.T) {
	src := `public class IPhases{public static int run(){java.io.IOException e=new java.io.IOException("x");return e.getMessage().length()==1&&e.getCause()==null?1:0;}}`
	cs := ioe0VerifyCompileTrusted(t, map[string]string{"IPhases.java": src}, []string{"IPhases"})
	raw := ioe0VerifyRaw(cs, "IPhases")
	e := ioe0VerifyNewEnv(t)
	defer e.close()
	r := ioe0VerifyRunToEnd(t, e, "phases", raw, "IPhases", "run", 1, 1, ioe0VerifyOrdinaryGas, 4096)
	ioe0VerifyRequireReturned(t, r, 1)
	sawNull, sawSelf := false, false
	for _, cp := range r.snaps {
		for _, h := range cp.Machine.Heap {
			if h.Class != uint16(len(raw)+27) {
				continue
			}
			_, ref := ioe0VerifyValue(cp.Bytes[h.CellOffsets[1]:])
			if ref == 0 {
				sawNull = true
			}
			if ref == uint64(h.Handle) {
				sawSelf = true
			}
		}
		ioe0VerifyValidateOK(t, e, raw, cp.Bytes)
	}
	if !sawNull || !sawSelf {
		t.Fatal("constructor phase not observed")
	}
}

func TestIOE0Verify26ObjectMayThrowPublishedThisBeforeCauseStore(t *testing.T) {
	src := `public class IEscape{static void make()throws java.io.IOException{new java.io.IOException();}public static int run(){try{make();return 0;}catch(java.io.IOException e){return e.getMessage()==null&&e.getCause()==null?1:0;}}}`
	cs := ioe0VerifyCompileTrusted(t, map[string]string{"IEscape.java": src}, []string{"IEscape"})
	raw := [][]byte{cs["IEscape"], ioe0VerifySyntheticObject(t, 0, "fail")}
	e := ioe0VerifyNewEnv(t)
	defer e.close()
	r := ioe0VerifyRunToEnd(t, e, "synthetic-escape", raw, "IEscape", "run", 1, 1, ioe0VerifyOrdinaryGas, 4096)
	ioe0VerifyRequireReturned(t, r, 1)
	cp := r.snaps[len(r.snaps)-1]
	ioe0VerifyValidateOK(t, e, raw, cp.Bytes)
}

func ioe0VerifyControlRaw(t *testing.T) [][]byte {
	return ioe0VerifyRaw(ioe0VerifyCompileTrusted(t, map[string]string{"ICtl.java": `public class ICtl{public static int run(){java.io.IOException e=new java.io.IOException("ctl");return e.getMessage().length();}}`}, []string{"ICtl"}), "ICtl")
}

func TestIOE0Verify27OwnerEpochAndHeadBinding(t *testing.T) {
	raw := ioe0VerifyControlRaw(t)
	e := ioe0VerifyNewEnv(t)
	defer e.close()
	id := ioe0VerifyInstance("binding")
	s, b, c := e.start(ioe0VerifyOwner, id, raw, "ICtl", "run", nil, 1, 1, ioe0VerifyOrdinaryGas)
	ioe0VerifyAssertSuccess(t, s, b, c)
	before := e.head(id)
	_, _, wrongOwner := e.resume(ioe0VerifyOther, id, s.Epoch, ioe0VerifySliceRoot(s), raw, b, 1, 4096, ioe0VerifyOrdinaryGas)
	ioe0VerifyAssertControl(t, wrongOwner, 2)
	_, _, wrongEpoch := e.resume(ioe0VerifyOwner, id, s.Epoch+1, ioe0VerifySliceRoot(s), raw, b, 1, 4096, ioe0VerifyOrdinaryGas)
	ioe0VerifyAssertControl(t, wrongEpoch, 3)
	bad := append([]byte(nil), b...)
	bad[len(bad)-1] ^= 1
	_, _, wrongBlob := e.resume(ioe0VerifyOwner, id, s.Epoch, ioe0VerifySliceRoot(s), raw, bad, 1, 4096, ioe0VerifyOrdinaryGas)
	ioe0VerifyAssertControl(t, wrongBlob, 4)
	ioe0VerifyAssertHeadEqual(t, e.head(id), before)
}

func TestIOE0Verify28OOGAndReserveRollbackRetry(t *testing.T) {
	raw := ioe0VerifyControlRaw(t)
	e := ioe0VerifyNewEnv(t)
	defer e.close()
	id := ioe0VerifyInstance("oog")
	s, b, c := e.start(ioe0VerifyOwner, id, raw, "ICtl", "run", nil, 1, 1, ioe0VerifyOrdinaryGas)
	ioe0VerifyAssertSuccess(t, s, b, c)
	before := e.head(id)
	_, _, failed := e.resume(ioe0VerifyOwner, id, s.Epoch, ioe0VerifySliceRoot(s), raw, b, 4096, 4096, 10000)
	if !errors.Is(failed.err, vm.ErrOutOfGas) || len(failed.logs) != 0 {
		t.Fatalf("lowgas %v %x", failed.err, failed.output)
	}
	ioe0VerifyAssertHeadEqual(t, e.head(id), before)
	_, _, reserve := e.resume(ioe0VerifyOwner, id, s.Epoch, ioe0VerifySliceRoot(s), raw, b, 1, 4096, ioe0VerifyReserveGas+500000)
	ioe0VerifyAssertControl(t, reserve, 7)
	ioe0VerifyAssertHeadEqual(t, e.head(id), before)
	snap := e.state.Snapshot()
	control, cb, cc := e.resume(ioe0VerifyOwner, id, s.Epoch, ioe0VerifySliceRoot(s), raw, b, 1, 4096, ioe0VerifyOrdinaryGas)
	ioe0VerifyAssertSuccess(t, control, cb, cc)
	e.state.RevertToSnapshot(snap)
	retry, rb, rc := e.resume(ioe0VerifyOwner, id, s.Epoch, ioe0VerifySliceRoot(s), raw, b, 1, 4096, ioe0VerifyOrdinaryGas)
	ioe0VerifyAssertSuccess(t, retry, rb, rc)
	if !reflect.DeepEqual(control, retry) || !bytes.Equal(cb, rb) {
		t.Fatal("retry differs from successful control")
	}
}

func TestIOE0Verify29NamespaceBlobAndStoreRefusal(t *testing.T) {
	raw := ioe0VerifyControlRaw(t)
	// Use a root that requires no new IOE0 capability for the old-profile blob.
	simple := ioe0VerifyRaw(ioe0VerifyCompileTrusted(t, map[string]string{"ISimple.java": `public class ISimple{public static int run(){return 1;}}`}, []string{"ISimple"}), "ISimple")
	old, err := sc0transport.NewMemory(ioe0VerifyOwner)
	if err != nil {
		t.Fatal(err)
	}
	defer old.Close()
	r, err := old.Start(ioe0VerifyInstance("old"), simple, "ISimple", "run", nil, 4096, 4096, ioe0VerifyOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	e := ioe0VerifyNewEnv(t)
	defer e.close()
	ioe0VerifyAssertState(t, ioe0VerifyValidate(e, raw, r.Checkpoint, ioe0VerifyOrdinaryGas), 3, 0)
	for _, oldFirst := range []bool{false, true} {
		dir := t.TempDir()
		if oldFirst {
			s, err := sc0transport.Open(dir, ioe0VerifyOwner)
			if err != nil {
				t.Fatal(err)
			}
			s.Close()
			bad, err := Open(dir, ioe0VerifyOwner)
			if bad != nil {
				bad.Close()
			}
			if err == nil {
				t.Fatal("SC0 store accepted as IOE0")
			}
		} else {
			s, err := Open(dir, ioe0VerifyOwner)
			if err != nil {
				t.Fatal(err)
			}
			s.Close()
			bad, err := sc0transport.Open(dir, ioe0VerifyOwner)
			if bad != nil {
				bad.Close()
			}
			if err == nil {
				t.Fatal("IOE0 store accepted as SC0")
			}
		}
	}
}

func TestIOE0Verify30DiskFailureDoesNotExposeChild(t *testing.T) {
	raw := ioe0VerifyControlRaw(t)
	dir := t.TempDir()
	s, err := Open(dir, ioe0VerifyOwner)
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()
	id := ioe0VerifyInstance("publication")
	parent, err := s.Start(id, raw, "ICtl", "run", nil, 1, 1, ioe0VerifyOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	s.testFault = func(p ioe0HarnessFaultPoint) error {
		if p == ioe0HarnessFaultBeforeManifest {
			return errors.New("parent publication seam")
		}
		return nil
	}
	failed, err := s.Resume(id, parent.Slice.Epoch, parent.Slice.CheckpointRoot, raw, parent.Checkpoint, 7, 4096, ioe0VerifyOrdinaryGas)
	if err == nil || !reflect.DeepEqual(failed.Slice, SliceResult{}) || len(failed.Checkpoint) != 0 || len(failed.Logs) != 0 {
		t.Fatal("speculative child exposed")
	}
	h, err := s.Head(id)
	if err != nil || h.CheckpointRoot != parent.Slice.CheckpointRoot {
		t.Fatal("failed publication advanced head", err)
	}
	s.testFault = nil
	retry, err := s.Resume(id, parent.Slice.Epoch, parent.Slice.CheckpointRoot, raw, parent.Checkpoint, 7, 4096, ioe0VerifyOrdinaryGas)
	if err != nil || retry.Slice.Epoch != parent.Slice.Epoch+1 {
		t.Fatal("publication retry failed", err)
	}
}

type ioe0VerifyProcessInput struct {
	Directory, Class string
	Raw              [][]byte
	ID               common.Hash
}
type ioe0VerifyProcessOutput struct {
	Result        int32
	Root          [32]byte
	Jvm, Internal uint64
}

func ioe0VerifyProcessCase(t *testing.T, wrapper bool) {
	t.Helper()
	name, source, names := "IProcess", `public class IProcess{public static int run(){java.io.IOException e=new java.io.IOException("persist");return e.getMessage().length()==7&&e.getCause()==null?1:0;}}`, []string{"IProcess"}
	if wrapper {
		source = `public class IProcess{static class B{static int x=fail();static int fail(){throw new RuntimeException();}}public static int run(){try{return B.x;}catch(ExceptionInInitializerError e){return e.getException()!=null&&e.getCause()==e.getException()?1:0;}}}`
		names = append(names, "IProcess$B")
	}
	raw := ioe0VerifyRaw(ioe0VerifyCompileTrusted(t, map[string]string{name + ".java": source}, names), names...)
	e := ioe0VerifyNewEnv(t)
	defer e.close()
	control := ioe0VerifyRunToEnd(t, e, "process-control", raw, name, "run", 4096, 4096, ioe0VerifyOrdinaryGas, 4096)
	ioe0VerifyRequireReturned(t, control, 1)
	dir := filepath.Join(t.TempDir(), "store")
	s, err := Open(dir, ioe0VerifyOwner)
	if err != nil {
		t.Fatal(err)
	}
	id := ioe0VerifyInstance("process")
	r, err := s.Start(id, raw, name, "run", nil, 1, 1, ioe0VerifyOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	stopped := false
	for n := 0; n < 256; n++ {
		cp, err := ioe0VerifyDecodeCheckpoint(r.Checkpoint)
		if err != nil {
			t.Fatal(err)
		}
		if wrapper {
			for _, h := range cp.Machine.Heap {
				if h.Object && h.Metadata.Uint64()&255 == 3 {
					stopped = true
				}
			}
		} else {
			for _, f := range cp.Machine.Frames {
				if f.Class == uint16(len(raw)+5) && f.PC == 9 && len(f.LocalOffsets) == 2 {
					stopped = true
				}
			}
		}
		if stopped {
			break
		}
		if r.Slice.Lifecycle != 1 {
			t.Fatal("target process snapshot not reached")
		}
		r, err = s.Resume(id, r.Slice.Epoch, r.Slice.CheckpointRoot, raw, r.Checkpoint, 1, 1, ioe0VerifyOrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
	}
	if !stopped || r.Slice.Lifecycle != 1 {
		t.Fatal("missing runnable process stop")
	}
	if err := s.Close(); err != nil {
		t.Fatal(err)
	}
	input := ioe0VerifyProcessInput{dir, name, raw, id}
	b, err := json.Marshal(input)
	if err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(t.TempDir(), "transport.json")
	if err := os.WriteFile(path, b, 0600); err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, os.Args[0], "-test.run=^TestIOE0VerifyProcessHelper$", "-test.v")
	cmd.Env = append(os.Environ(), "JVMEVM_IOE0_PARENT_PROCESS="+path)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("new process %v %s", err, out)
	}
	var got ioe0VerifyProcessOutput
	parsed := false
	for _, line := range bytes.Split(out, []byte{'\n'}) {
		if bytes.HasPrefix(line, []byte{'{'}) {
			if err := json.Unmarshal(line, &got); err != nil {
				t.Fatal(err)
			}
			parsed = true
		}
	}
	if !parsed || got.Result != 1 || got.Root != control.slice.MachineStateRoot || got.Jvm != control.slice.TotalJvmSteps || got.Internal != control.slice.TotalInternalSteps {
		t.Fatalf("new process/control mismatch %+v", got)
	}
}
func TestIOE0Verify31NewProcessMidMessageConstructor(t *testing.T) { ioe0VerifyProcessCase(t, false) }
func TestIOE0Verify32NewProcessWrapperField(t *testing.T)          { ioe0VerifyProcessCase(t, true) }
func TestIOE0VerifyProcessHelper(t *testing.T) {
	path := os.Getenv("JVMEVM_IOE0_PARENT_PROCESS")
	if path == "" {
		return
	}
	b, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	var in ioe0VerifyProcessInput
	if err := json.Unmarshal(b, &in); err != nil {
		t.Fatal(err)
	}
	s, err := Open(in.Directory, ioe0VerifyOwner)
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()
	if s.testCodeInstalls != 0 {
		t.Fatal("code reinstalled")
	}
	for n := 0; n < 256; n++ {
		h, err := s.Head(in.ID)
		if err != nil {
			t.Fatal(err)
		}
		b, err := s.ReadCheckpoint(h.CheckpointRoot)
		if err != nil {
			t.Fatal(err)
		}
		r, err := s.Resume(in.ID, h.Epoch, h.CheckpointRoot, in.Raw, b, 7, 4096, ioe0VerifyOrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
		if r.Slice.Lifecycle != 1 {
			if r.Slice.Lifecycle != 2 {
				t.Fatal("uncaught child")
			}
			out, _ := json.Marshal(ioe0VerifyProcessOutput{r.Slice.Result, r.Slice.MachineStateRoot, r.Slice.TotalJvmSteps, r.Slice.TotalInternalSteps})
			fmt.Println(string(out))
			return
		}
	}
	t.Fatal("process cap")
}
