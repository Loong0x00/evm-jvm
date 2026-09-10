package vfs0a

// Parent-only wire reader and root-mutator for adversarial VIEW tests. This is
// not production Java/filesystem evaluation, a guest-state authority or a way
// to issue/resume a checkpoint. Live resume must still reject any rehashed blob
// that differs from the exact EVM-issued live head.
import (
	"bytes"
	"encoding/binary"
	"fmt"
	"testing"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	evmruntime "github.com/ethereum/go-ethereum/core/vm/runtime"
	"github.com/ethereum/go-ethereum/crypto"
)

const vfsParentHeader = 280

type vfsParentWire struct {
	b   []byte
	p   int
	err error
}

func (r *vfsParentWire) take(n int) []byte {
	if r.err != nil {
		return nil
	}
	if n < 0 || r.p > len(r.b) || n > len(r.b)-r.p {
		r.err = fmt.Errorf("wire truncated at%d need%d", r.p, n)
		return nil
	}
	b := r.b[r.p : r.p+n]
	r.p += n
	return b
}
func (r *vfsParentWire) u8() uint8 {
	b := r.take(1)
	if b == nil {
		return 0
	}
	return b[0]
}
func (r *vfsParentWire) u16() uint16 {
	b := r.take(2)
	if b == nil {
		return 0
	}
	return binary.BigEndian.Uint16(b)
}
func (r *vfsParentWire) u32() uint32 {
	b := r.take(4)
	if b == nil {
		return 0
	}
	return binary.BigEndian.Uint32(b)
}
func (r *vfsParentWire) u64() uint64 {
	b := r.take(8)
	if b == nil {
		return 0
	}
	return binary.BigEndian.Uint64(b)
}
func (r *vfsParentWire) sized16() []byte { return r.take(int(r.u16())) }
func (r *vfsParentWire) cells(n uint32, width int) []int {
	if r.err != nil {
		return nil
	}
	if uint64(n)*uint64(width) > uint64(len(r.b)-r.p) {
		r.err = fmt.Errorf("wire cells at%d n%d width%d", r.p, n, width)
		return nil
	}
	out := make([]int, int(n))
	for i := range out {
		out[i] = r.p
		r.take(width)
	}
	return out
}

type vfsParentFrameWire struct {
	Offset, PCOffset, FlagsOffset, ThisOffset, SPOffset, BitmapOffset int
	Class, Method                                                     uint16
	PC                                                                uint32
	Flags                                                             uint8
	This                                                              uint32
	Stack, Locals                                                     []int
}
type vfsParentHeapWire struct {
	Offset, MetadataOffset, ClassOffset, RankOffset, CountOffset int
	Handle                                                       uint32
	Class                                                        uint16
	Rank                                                         uint8
	Object                                                       bool
	Cells                                                        []int
}
type vfsParentInodeWire struct {
	Offset, KindOffset, ReadOnlyOffset, ParentOffset, NameLengthOffset, DataLengthOffset, NameOffset, DataOffset int
	ID, Parent                                                                                                   uint32
	Kind, ReadOnly                                                                                               uint8
	Name, Data                                                                                                   []byte
}
type vfsParentDescriptorWire struct {
	Offset, InodeOffset, OwnerOffset, FlagsOffset, CursorOffset, PhaseOffset, DepthOffset, PCOffset int
	ID, Inode, Owner, PC                                                                            uint32
	Flags, Phase                                                                                    uint8
	Cursor                                                                                          uint64
	Depth                                                                                           uint16
}
type vfsParentCheckpointWire struct {
	Bytes                                                                                   []byte
	MachineRoot, VFSRoot, SeedRoot, ArtifactRoot, ConfigRoot                                common.Hash
	LifecycleOffset, ResultOffset, JavaKindOffset, JavaRefOffset, JvmOffset, InternalOffset int
	EntryClass, Entry                                                                       []byte
	InitOffsets, StartedOffsets, StaticValues                                               []int
	FrameCountOffset                                                                        int
	Frames                                                                                  []vfsParentFrameWire
	HeapHeaderOffset                                                                        int
	NextHandle                                                                              uint32
	Heap                                                                                    []vfsParentHeapWire
	PendingOffset, InternCountOffset                                                        int
	InternHandles, InternHashes                                                             []int
	VFSOffset, LogicalBytesOffset                                                           int
	NextInode, NextDescriptor                                                               uint32
	LogicalBytes                                                                            uint64
	Inodes                                                                                  []vfsParentInodeWire
	Descriptors                                                                             []vfsParentDescriptorWire
}

func vfsParentDecodeWire(blob []byte) (c vfsParentCheckpointWire, err error) {
	if len(blob) < vfsParentHeader || len(blob) > 1<<20 {
		return c, fmt.Errorf("wire envelope size%d", len(blob))
	}
	if string(blob[:8]) != "JVMVF0A1" || binary.BigEndian.Uint32(blob[8:12]) != 1 {
		return c, fmt.Errorf("wire envelope magic/schema")
	}
	if int(binary.BigEndian.Uint32(blob[276:280])) != len(blob)-vfsParentHeader {
		return c, fmt.Errorf("wire machine length")
	}
	c.Bytes = append([]byte(nil), blob...)
	copy(c.ArtifactRoot[:], blob[116:148])
	copy(c.ConfigRoot[:], blob[148:180])
	copy(c.MachineRoot[:], blob[180:212])
	copy(c.SeedRoot[:], blob[212:244])
	copy(c.VFSRoot[:], blob[244:276])
	r := &vfsParentWire{b: blob, p: vfsParentHeader}
	if string(r.take(4)) != "VFA1" {
		return c, fmt.Errorf("wire machine magic")
	}
	c.LifecycleOffset = r.p
	r.u8()
	c.ResultOffset = r.p
	r.u32()
	c.JavaKindOffset = r.p
	r.u8()
	c.JavaRefOffset = r.p
	r.u32()
	c.JvmOffset = r.p
	r.u64()
	c.InternalOffset = r.p
	r.u64()
	c.EntryClass = r.sized16()
	c.Entry = r.sized16()
	r.cells(uint32(r.u8()), 4)
	classes := r.u16()
	for i := 0; i < int(classes) && r.err == nil; i++ {
		c.InitOffsets = append(c.InitOffsets, r.p)
		r.u8()
		c.StartedOffsets = append(c.StartedOffsets, r.p)
		r.u8()
		fields := r.u16()
		for j := 0; j < int(fields) && r.err == nil; j++ {
			r.u16()
			c.StaticValues = append(c.StaticValues, r.p)
			r.take(32)
		}
	}
	c.FrameCountOffset = r.p
	frames := r.u16()
	for i := 0; i < int(frames) && r.err == nil; i++ {
		f := vfsParentFrameWire{Offset: r.p}
		f.Class = r.u16()
		f.Method = r.u16()
		f.PCOffset = r.p
		f.PC = r.u32()
		r.take(32)
		f.FlagsOffset = r.p
		f.Flags = r.u8()
		f.ThisOffset = r.p
		f.This = r.u32()
		f.SPOffset = r.p
		sp := r.u16()
		f.Stack = r.cells(uint32(sp), 32)
		locals := r.u16()
		f.BitmapOffset = r.p
		r.take((int(locals) + 7) / 8)
		f.Locals = r.cells(uint32(locals), 32)
		c.Frames = append(c.Frames, f)
	}
	c.HeapHeaderOffset = r.p
	c.NextHandle = r.u32()
	r.u16()
	r.u16()
	r.u32()
	r.u32()
	r.u32()
	r.u16()
	r.u32()
	for i := uint32(0); i < c.NextHandle && r.err == nil; i++ {
		h := vfsParentHeapWire{Offset: r.p}
		h.Handle = r.u32()
		h.MetadataOffset = r.p
		meta := r.take(32)
		h.Object = len(meta) == 32 && meta[0]&0x80 != 0
		h.ClassOffset = r.p
		h.Class = r.u16()
		h.RankOffset = r.p
		h.Rank = r.u8()
		h.CountOffset = r.p
		n := r.u32()
		width := 8
		if h.Object {
			width = 32
		}
		h.Cells = r.cells(n, width)
		c.Heap = append(c.Heap, h)
	}
	c.PendingOffset = r.p
	r.take(38) // implicit Java pending exception, no cause side table
	c.InternCountOffset = r.p
	interns := r.u16()
	for i := 0; i < int(interns) && r.err == nil; i++ {
		c.InternHandles = append(c.InternHandles, r.p)
		r.u32()
		c.InternHashes = append(c.InternHashes, r.p)
		r.u32()
	}
	c.VFSOffset = r.p
	c.NextInode = r.u32()
	c.NextDescriptor = r.u32()
	inodes := r.u32()
	descriptors := r.u32()
	c.LogicalBytesOffset = r.p
	c.LogicalBytes = r.u64()
	if inodes > 64 || descriptors > 32 {
		return c, fmt.Errorf("wire VFS count %d/%d", inodes, descriptors)
	}
	for i := uint32(0); i < inodes && r.err == nil; i++ {
		n := vfsParentInodeWire{Offset: r.p}
		n.ID = r.u32()
		n.KindOffset = r.p
		n.Kind = r.u8()
		n.ReadOnlyOffset = r.p
		n.ReadOnly = r.u8()
		n.ParentOffset = r.p
		n.Parent = r.u32()
		n.NameLengthOffset = r.p
		nl := r.u8()
		n.DataLengthOffset = r.p
		dl := r.u32()
		if nl > 64 || dl > 65536 {
			return c, fmt.Errorf("wire inode length %d/%d", nl, dl)
		}
		n.NameOffset = r.p
		n.Name = r.take(int(nl))
		n.DataOffset = r.p
		n.Data = r.take(int(dl))
		c.Inodes = append(c.Inodes, n)
	}
	for i := uint32(0); i < descriptors && r.err == nil; i++ {
		d := vfsParentDescriptorWire{Offset: r.p}
		d.ID = r.u32()
		d.InodeOffset = r.p
		d.Inode = r.u32()
		d.OwnerOffset = r.p
		d.Owner = r.u32()
		d.FlagsOffset = r.p
		d.Flags = r.u8()
		d.CursorOffset = r.p
		d.Cursor = r.u64()
		d.PhaseOffset = r.p
		d.Phase = r.u8()
		d.DepthOffset = r.p
		d.Depth = r.u16()
		d.PCOffset = r.p
		d.PC = r.u32()
		c.Descriptors = append(c.Descriptors, d)
	}
	if r.err != nil {
		return c, r.err
	}
	if r.p != len(blob) {
		return c, fmt.Errorf("wire trailing%d", len(blob)-r.p)
	}
	return c, nil
}

func vfsParentHashABI(t *testing.T, types []string, values ...any) common.Hash {
	t.Helper()
	args := make(abi.Arguments, len(types))
	for i, text := range types {
		typ, e := abi.NewType(text, "", nil)
		if e != nil {
			t.Fatal(e)
		}
		args[i] = abi.Argument{Type: typ}
	}
	b, e := args.Pack(values...)
	if e != nil {
		t.Fatal(e)
	}
	return crypto.Keccak256Hash(b)
}
func vfsParentWireRoots(t *testing.T, c vfsParentCheckpointWire) (machine, vfs common.Hash) {
	t.Helper()
	vfs = vfsParentHashABI(t, []string{"bytes32", "uint32", "bytes32", "bytes32"}, crypto.Keccak256Hash([]byte("JVMEVM:MC:VFS0A:VFS:1")), uint32(1), c.SeedRoot, crypto.Keccak256Hash(c.Bytes[c.VFSOffset:]))
	machine = vfsParentHashABI(t, []string{"bytes32", "uint32", "bytes32", "bytes32", "bytes32", "bytes32"}, crypto.Keccak256Hash([]byte("JVMEVM:MC:VFS0A:MACHINE:1")), uint32(1), c.ArtifactRoot, c.ConfigRoot, crypto.Keccak256Hash(c.Bytes[vfsParentHeader:]), vfs)
	return
}
func vfsParentRehashForView(t *testing.T, blob []byte) []byte {
	t.Helper()
	c, e := vfsParentDecodeWire(blob)
	if e != nil {
		t.Fatal(e)
	}
	m, v := vfsParentWireRoots(t, c)
	out := append([]byte(nil), blob...)
	copy(out[180:212], m[:])
	copy(out[244:276], v[:])
	return out
}

// Pure parser self-test. This synthetic layout intentionally has no valid Java
// program/heap and is NEVER supplied to a live EVM resume or called EVM-issued.
func TestVFS0aParentWireReaderLayout(t *testing.T) {
	var m bytes.Buffer
	put := func(v any) {
		if e := binary.Write(&m, binary.BigEndian, v); e != nil {
			t.Fatal(e)
		}
	}
	m.WriteString("VFA1")
	put(uint8(2))
	put(int32(0))
	put(uint8(0))
	put(uint32(0))
	put(uint64(0))
	put(uint64(0))
	put(uint16(1))
	m.WriteString("P")
	put(uint16(3))
	m.WriteString("run")
	put(uint8(0))
	put(uint16(0))
	put(uint16(0))
	m.Write(make([]byte, 26+38))
	put(uint16(0))
	vfsOffset := vfsParentHeader + m.Len()
	put(uint32(4))
	put(uint32(1))
	put(uint32(3))
	put(uint32(0))
	put(uint64(0))
	for i, name := range []string{"", "work", "ro"} {
		put(uint32(i + 1))
		put(uint8(1))
		ro := uint8(0)
		if i == 2 {
			ro = 1
		}
		put(ro)
		parent := uint32(1)
		if i == 0 {
			parent = 0
		}
		put(parent)
		put(uint8(len(name)))
		put(uint32(0))
		m.WriteString(name)
	}
	b := make([]byte, vfsParentHeader)
	copy(b, "JVMVF0A1")
	binary.BigEndian.PutUint32(b[8:12], 1)
	binary.BigEndian.PutUint32(b[276:280], uint32(m.Len()))
	b = append(b, m.Bytes()...)
	c, e := vfsParentDecodeWire(b)
	if e != nil {
		t.Fatal(e)
	}
	if c.VFSOffset != vfsOffset || len(b)-vfsOffset != 75 || len(c.Inodes) != 3 || c.Inodes[2].ReadOnly != 1 || string(c.Inodes[1].Name) != "work" {
		t.Fatalf("layout mismatch: %+v", c)
	}
	h := vfsParentRehashForView(t, b)
	cc, e := vfsParentDecodeWire(h)
	if e != nil {
		t.Fatal(e)
	}
	mr, vr := vfsParentWireRoots(t, cc)
	if cc.MachineRoot != mr || cc.VFSRoot != vr {
		t.Fatal("root roundtrip")
	}
	for cut := 0; cut < len(b); cut++ {
		truncated := append([]byte(nil), b[:cut]...)
		if cut >= vfsParentHeader {
			// Fix the outer length so this also exercises inner bounds, not
			// merely a header-length mismatch on every truncated sample.
			binary.BigEndian.PutUint32(truncated[276:280], uint32(cut-vfsParentHeader))
		}
		if _, e := vfsParentDecodeWire(truncated); e == nil {
			t.Fatalf("truncation accepted at%d", cut)
		}
	}
	bad := append(append([]byte(nil), b...), 0)
	binary.BigEndian.PutUint32(bad[276:280], uint32(len(bad)-vfsParentHeader))
	if _, e := vfsParentDecodeWire(bad); e == nil {
		t.Fatal("trailing byte accepted")
	}
	bad = append([]byte(nil), b...)
	binary.BigEndian.PutUint32(bad[c.VFSOffset+8:], 65)
	if _, e := vfsParentDecodeWire(bad); e == nil {
		t.Fatal("unbounded inode count")
	}
}

func vfsParentValidateCall(t *testing.T, s *Session, raw [][]byte, blob []byte) ([]byte, uint64, error) {
	t.Helper()
	input, e := s.contractABI.Pack("validateCheckpoint", raw, blob)
	if e != nil {
		t.Fatal(e)
	}
	const gas = uint64(100_000_000)
	out, left, e := evmruntime.Call(s.contract, input, s.vfs0aHarnessRuntimeConfig(s.stateDB.Copy(), gas))
	return out, gas - left, e
}

func vfsParentReviewSeedCheckpoint(t *testing.T) (*Session, [][]byte, Result, vfsParentCheckpointWire) {
	t.Helper()
	raw := [][]byte{vfsParentCompileOracle(t, "PWire", "public class PWire {public static int run(){return 1;}}", 1)}
	s, e := NewMemory(common.HexToAddress("0x7d01"))
	if e != nil {
		t.Fatal(e)
	}
	t.Cleanup(func() { s.Close() })
	id := crypto.Keccak256Hash([]byte(t.Name()))
	r, e := s.Start(id, raw, "PWire", "run", nil, []SeedFile{{Path: []byte("a"), Data: []byte("x")}, {Path: []byte("b"), Data: []byte("y")}}, 4096, 4096, 100_000_000)
	if e != nil || r.Slice.Lifecycle != 2 || r.Slice.Result != 1 {
		t.Fatalf("issued control: %+v %v", r, e)
	}
	c, e := vfsParentDecodeWire(r.Checkpoint)
	if e != nil {
		t.Fatal(e)
	}
	if _, _, e := vfsParentValidateCall(t, s, raw, r.Checkpoint); e != nil {
		t.Fatalf("valid issued checkpoint rejected: %v", e)
	}
	return s, raw, r, c
}

func TestVFS0aParent24DirectoryWireRules(t *testing.T) {
	s, raw, r, c := vfsParentReviewSeedCheckpoint(t)
	cases := []struct {
		name   string
		change func([]byte)
	}{
		{"regular-file-parent", func(b []byte) { binary.BigEndian.PutUint32(b[c.Inodes[4].ParentOffset:], c.Inodes[3].ID) }},
		{"slash-component", func(b []byte) { b[c.Inodes[3].NameOffset] = '/' }},
		{"dot-component", func(b []byte) { b[c.Inodes[3].NameOffset] = '.' }},
		{"non-ascii-component", func(b []byte) { b[c.Inodes[3].NameOffset] = 0x80 }},
		{"control-component", func(b []byte) { b[c.Inodes[3].NameOffset] = 0 }},
		{"duplicate-sibling", func(b []byte) { b[c.Inodes[4].NameOffset] = 'a' }},
		{"self-parent", func(b []byte) { binary.BigEndian.PutUint32(b[c.Inodes[3].ParentOffset:], c.Inodes[3].ID) }},
		{"readonly-boolean-two", func(b []byte) { b[c.Inodes[3].ReadOnlyOffset] = 2 }},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			bad := append([]byte(nil), r.Checkpoint...)
			tc.change(bad)
			bad = vfsParentRehashForView(t, bad)
			out, gas, e := vfsParentValidateCall(t, s, raw, bad)
			if e == nil {
				t.Fatalf("EVM view accepted invalid VFS directory structure; gas%d output%x", gas, out)
			}
			if len(out) < 4 {
				t.Fatalf("expected bounded profile rejection, got %v gas%d", e, gas)
			}
			t.Logf("rejected gas%d data%x", gas, out)
		})
	}
}

func TestVFS0aParent23ReadonlyWriterState(t *testing.T) {
	src := `import java.io.*;public class PReadOnlyState {public static int run()throws IOException{FileOutputStream o=new FileOutputStream(new File("f"));o.write(1);o.close();return 1;}}`
	raw := [][]byte{vfsParentCompileOracle(t, "PReadOnlyState", src, 1)}
	tr := vfsParentNativeRun(t, "PReadOnlyState", raw, nil, 1, 4096, 4096, nil)
	c := tr.Snapshots[len(tr.Snapshots)-1]
	s, e := NewMemory(common.HexToAddress("0x7d02"))
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	if _, _, e := vfsParentValidateCall(t, s, raw, tr.Final.Checkpoint); e != nil {
		t.Fatal(e)
	}
	bad := append([]byte(nil), tr.Final.Checkpoint...)
	target := c.Descriptors[0].Inode
	bad[c.Inodes[target-1].ReadOnlyOffset] = 1
	bad = vfsParentRehashForView(t, bad)
	out, gas, e := vfsParentValidateCall(t, s, raw, bad)
	if e == nil {
		t.Fatalf("EVM view accepted WRITE descriptor on effective-readonly inode; gas%d out%x", gas, out)
	}
	if len(out) < 4 {
		t.Fatalf("unbounded rejection: %v gas%d", e, gas)
	}
}
