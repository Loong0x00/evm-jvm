package vfs0a

// Parent-only wire reader and root-mutator for adversarial VIEW tests. This is
// not production Java/filesystem evaluation, a guest-state authority or a way
// to issue/resume a checkpoint. Live resume must still reject any rehashed blob
// that differs from the exact EVM-issued live head.
import (
	"bytes"
	"encoding/binary"
	"fmt"
	"strings"
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

// TEST-only Java8 Object emitter; never installed in a host JVM. It lets the
// guest VM exercise its explicitly supported noncanonical Object profile.
func vfsParentObjectImage(fields int, nop bool) []byte {
	var b bytes.Buffer
	put := func(v any) {
		if e := binary.Write(&b, binary.BigEndian, v); e != nil {
			panic(e)
		}
	}
	utf := func(s string) { put(uint8(1)); put(uint16(len(s))); b.WriteString(s) }
	put(uint32(0xcafebabe))
	put(uint16(0))
	put(uint16(52))
	put(uint16(7 + fields))
	put(uint8(7))
	put(uint16(2))
	utf("java/lang/Object")
	utf("<init>")
	utf("()V")
	utf("Code")
	utf("I")
	for i := 0; i < fields; i++ {
		utf(fmt.Sprintf("f%d", i))
	}
	put(uint16(0x21))
	put(uint16(1))
	put(uint16(0))
	put(uint16(0))
	put(uint16(fields))
	for i := 0; i < fields; i++ {
		put(uint16(1))
		put(uint16(7 + i))
		put(uint16(6))
		put(uint16(0))
	}
	code := []byte{0xb1}
	if nop {
		code = []byte{0, 0xb1}
	}
	put(uint16(1))
	put(uint16(1))
	put(uint16(3))
	put(uint16(4))
	put(uint16(1))
	put(uint16(5))
	put(uint32(12 + len(code)))
	put(uint16(0))
	put(uint16(1))
	put(uint32(len(code)))
	b.Write(code)
	put(uint16(0))
	put(uint16(0))
	put(uint16(0))
	return b.Bytes()
}

func TestVFS0aParent05AllocationProfileAndInheritedFields(t *testing.T) {
	plain := `public class PPlain {public static int run(){Object o=new Object();java.io.IOException e=new java.io.IOException("m");return o!=null&&e.getMessage().equals("m")&&e.getCause()==null?1:0;}}`
	raw := [][]byte{vfsParentCompileOracle(t, "PPlain", plain, 1), vfsParentObjectImage(0, true)}
	vfsParentNativeRun(t, "PPlain", raw, nil, 1, 4096, 4096, nil)
	for _, tc := range []struct{ name, source string }{
		{"PGFile", `public class PGFile{public static int run(){new java.io.File("f");return 1;}}`},
		{"PGInput", `public class PGInput extends java.io.InputStream{public int read(){return -1;}public static int run(){new PGInput();return 1;}}`},
		{"PGOutput", `public class PGOutput extends java.io.OutputStream{public void write(int x){}public static int run(){new PGOutput();return 1;}}`},
	} {
		t.Run(tc.name, func(t *testing.T) {
			s, e := NewMemory(common.HexToAddress("0x7d03"))
			if e != nil {
				t.Fatal(e)
			}
			defer s.Close()
			raw := [][]byte{vfsParentCompileOracle(t, tc.name, tc.source, 1), vfsParentObjectImage(0, true)}
			r, e := s.Start(crypto.Keccak256Hash([]byte(tc.name)), raw, tc.name, "run", nil, nil, 4096, 4096, 100_000_000)
			if e == nil {
				t.Fatal("noncanonical Object family allocation accepted")
			}
			vfsBoundaryWantError(t, s, r.RevertData, e, "VFS0aProfileError", 5, 0)
		})
	}
	src := `import java.io.*;public class PInherited {public static int run()throws IOException{File f=new File("f");FileOutputStream o=new FileOutputStream(f);o.write(23);o.close();FileInputStream i=new FileInputStream(f);int v=i.read();i.close();return v==23?1:0;}}`
	raw = [][]byte{vfsParentCompileOracle(t, "PInherited", src, 1), vfsParentObjectImage(3, false)}
	tr := vfsParentNativeRun(t, "PInherited", raw, nil, 1, 4096, 4096, nil)
	c := tr.Snapshots[len(tr.Snapshots)-1]
	for _, d := range c.Descriptors {
		h := c.Heap[d.Owner-1]
		if len(h.Cells) != 4 {
			t.Fatal("inherited handle field layout")
		}
		v := tr.Final.Checkpoint[h.Cells[3] : h.Cells[3]+32]
		if v[23] != 1 || binary.BigEndian.Uint32(v[28:]) != d.ID {
			t.Fatal("wrong canonical INT handle offset")
		}
	}
}

func vfsParentCheckPendingCorridor(t *testing.T, input bool) {
	src := `import java.io.*;public class PCorridor{public static int run()throws IOException{FileOutputStream o=new FileOutputStream(new File("f"));o.write(1);o.close();return 1;}}`
	invokePC, returnPC, localSlot, wrongMethod := uint32(19), uint32(22), 3, uint16(0)
	var seeds []SeedFile
	var setup []string
	if input {
		src = `import java.io.*;public class PCorridor{public static int run()throws IOException{FileInputStream i=new FileInputStream(new File("f"));int v=i.read();i.close();return v;}}`
		invokePC, returnPC, localSlot, wrongMethod = 18, 21, 2, 1
		seeds = []SeedFile{{Path: []byte("f"), Data: []byte{1}}}
		setup = []string{`try(java.io.FileOutputStream o=new java.io.FileOutputStream("f")){o.write(1);}`}
	}
	raw := [][]byte{vfsParentCompileOracle(t, "PCorridor", src, 1, setup...)}
	tr := vfsParentNativeRun(t, "PCorridor", raw, seeds, 1, 1, 4096, nil)
	s, e := NewMemory(common.HexToAddress("0x7d04"))
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	pcs := map[uint32]bool{}
	for _, c := range tr.Snapshots {
		if len(c.Descriptors) != 1 || c.Descriptors[0].Phase != 1 {
			continue
		}
		d := c.Descriptors[0]
		f := c.Frames[len(c.Frames)-1]
		if pcs[f.PC] {
			continue
		}
		pcs[f.PC] = true
		t.Run(fmt.Sprintf("pc%d", f.PC), func(t *testing.T) {
			if _, _, e := vfsParentValidateCall(t, s, raw, c.Bytes); e != nil {
				t.Fatal("issued corridor rejected", e)
			}
			mutate := func(name string, fn func([]byte)) {
				t.Run(name, func(t *testing.T) {
					bad := append([]byte(nil), c.Bytes...)
					fn(bad)
					bad = vfsParentRehashForView(t, bad)
					out, _, e := vfsParentValidateCall(t, s, raw, bad)
					if e == nil {
						t.Fatal("invalid pending corridor accepted")
					}
					if len(out) < 4 {
						t.Fatalf("unbounded rejection %v", e)
					}
				})
			}
			mutate("bind-invoke-not-putfield", func(b []byte) { binary.BigEndian.PutUint32(b[d.PCOffset:], invokePC) })
			mutate("wrong-depth", func(b []byte) { binary.BigEndian.PutUint16(b[d.DepthOffset:], 0) })
			mutate("wrong-owner", func(b []byte) { binary.BigEndian.PutUint32(b[d.OwnerOffset:], d.Owner+1) })
			mutate("wrong-method", func(b []byte) { binary.BigEndian.PutUint16(b[f.Offset+2:], wrongMethod) }) // FOS(File), not FOS(File,Z)
			mutate("local0-uninitialized-tag", func(b []byte) { b[f.Locals[0]+23] = 3 })
			mutate("local0-other-ref", func(b []byte) { binary.BigEndian.PutUint32(b[f.Locals[0]+28:], d.Owner+1) })
			mutate("already-written-handle", func(b []byte) { binary.BigEndian.PutUint32(b[c.Heap[d.Owner-1].Cells[0]+28:], d.ID) })
			for j, at := range f.Stack {
				j, at := j, at
				mutate(fmt.Sprintf("stack%d", j), func(b []byte) { binary.BigEndian.PutUint32(b[at+28:], 0) })
			}
			if f.PC != returnPC {
				mutate("wrong-local-id", func(b []byte) { binary.BigEndian.PutUint32(b[f.Locals[localSlot]+28:], d.ID+1) })
			}
			// Insert an otherwise valid INT into the stack while preserving every
			// subsequent frame/heap/VFS byte and repairing lengths and roots.
			at := f.SPOffset + 2 + 32*len(f.Stack)
			bad := append([]byte(nil), c.Bytes[:at]...)
			word := make([]byte, 32)
			word[23] = 1
			word[31] = 1
			bad = append(bad, word...)
			bad = append(bad, c.Bytes[at:]...)
			binary.BigEndian.PutUint16(bad[f.SPOffset:], uint16(len(f.Stack)+1))
			binary.BigEndian.PutUint32(bad[276:280], uint32(len(bad)-280))
			bad = vfsParentRehashForView(t, bad)
			out, _, e := vfsParentValidateCall(t, s, raw, bad)
			if e == nil {
				t.Fatal("extra pending operand accepted")
			}
			if len(out) < 4 {
				t.Fatal("extra operand unbounded rejection")
			}
		})
	}
	if len(pcs) != 6 {
		t.Fatalf("observed pending PCs%v", pcs)
	}
}

func TestVFS0aParent070809PendingCorridorViews(t *testing.T) {
	t.Run("output", func(t *testing.T) { vfsParentCheckPendingCorridor(t, false) })
	t.Run("input", func(t *testing.T) { vfsParentCheckPendingCorridor(t, true) })
}

func TestVFS0aParent12EscapedFailedStreamSubclass(t *testing.T) {
	src := `import java.io.*;public class PEscaped extends FileOutputStream {
 static PEscaped escaped;PEscaped()throws IOException{super(new File("f"));escaped=this;throw new IOException("boom");}
 public static int run()throws IOException{try{new PEscaped();}catch(IOException e){if(!e.getMessage().equals("boom"))return 0;}escaped.write(19);escaped.close();return 1;}}`
	raw := [][]byte{vfsParentCompileOracle(t, "PEscaped", src, 1)}
	a := vfsParentNativeRun(t, "PEscaped", raw, nil, 1, 4096, 4096, nil)
	b := vfsParentNativeRun(t, "PEscaped", raw, nil, 1, 7, 1, nil)
	if a.Final.Slice.MachineStateRoot != b.Final.Slice.MachineStateRoot || a.Final.Slice.VFSStateRoot != b.Final.Slice.VFSStateRoot {
		t.Fatal("escaped subclass quantum mismatch")
	}
	c := b.Snapshots[len(b.Snapshots)-1]
	if len(c.Descriptors) != 1 || c.Descriptors[0].Phase != 3 || !bytes.Equal(c.Inodes[c.Descriptors[0].Inode-1].Data, []byte{19}) {
		t.Fatal("escaped initialized stream lost")
	}
}

func TestVFS0aParent02ReservedAndLookalikeNatives(t *testing.T) {
	base := vfsParentCompileOracle(t, "PReserved", "public class PReserved{public static int run(){return 1;}}", 1)
	for name := range vfsParentImagePins {
		t.Run(name, func(t *testing.T) {
			s, e := NewMemory(common.HexToAddress("0x7d05"))
			if e != nil {
				t.Fatal(e)
			}
			defer s.Close()
			r, e := s.Start(crypto.Keccak256Hash([]byte(name)), [][]byte{base, vfsParentImage(t, name)}, "PReserved", "run", nil, nil, 4096, 4096, 100_000_000)
			if e == nil {
				t.Fatal("raw reserved replacement accepted")
			}
			vfsBoundaryWantError(t, s, r.RevertData, e, "LinkError", 6, 1)
		})
	}
	src := `public class PLookalike{private native int open0(java.io.File f);public static int run(){return new PLookalike().open0(null);}}`
	setup := `try{PLookalike.run();}catch(UnsatisfiedLinkError e){System.out.println(1);return;}`
	raw := vfsParentCompileOracle(t, "PLookalike", src, 1, setup)
	s, e := NewMemory(common.HexToAddress("0x7d06"))
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	r, e := s.Start(crypto.Keccak256Hash([]byte("lookalike")), [][]byte{raw}, "PLookalike", "run", nil, nil, 4096, 4096, 100_000_000)
	sel := s.contractABI.Errors["CallError"].ID
	if e == nil || len(r.RevertData) < 36 || !bytes.Equal(r.RevertData[:4], sel[:4]) || binary.BigEndian.Uint64(r.RevertData[28:36]) != 4 {
		t.Fatalf("lookalike did not hard-fail ordinary native call: %v %x", e, r.RevertData)
	}
}

func TestVFS0aParent06FailedDefaultObjects(t *testing.T) {
	for _, tc := range []struct {
		name, source string
		class        uint16
		kind         byte
	}{
		{"PNullFile", `import java.io.*;public class PNullFile{public static int run(){try{new File((String)null);}catch(NullPointerException e){return e.getMessage()==null?1:0;}return 0;}}`, 34, 2},
		{"PNullStream", `import java.io.*;public class PNullStream{public static int run()throws IOException{try{new FileInputStream((File)null);}catch(NullPointerException e){return e.getMessage()==null?1:0;}return 0;}}`, 37, 1},
	} {
		t.Run(tc.name, func(t *testing.T) {
			raw := [][]byte{vfsParentCompileOracle(t, tc.name, tc.source, 1)}
			a := vfsParentNativeRun(t, tc.name, raw, nil, 1, 4096, 4096, nil)
			b := vfsParentNativeRun(t, tc.name, raw, nil, 1, 1, 1, nil)
			if a.Final.Slice.MachineStateRoot != b.Final.Slice.MachineStateRoot {
				t.Fatal("failed constructor quantum mismatch")
			}
			c := a.Snapshots[len(a.Snapshots)-1]
			found := false
			for _, h := range c.Heap {
				if h.Object && h.Class == tc.class {
					found = true
					if len(h.Cells) != 1 {
						t.Fatal("default layout")
					}
					v := a.Final.Checkpoint[h.Cells[0] : h.Cells[0]+32]
					if v[23] != tc.kind || binary.BigEndian.Uint64(v[24:]) != 0 {
						t.Fatal("default field lost after failed constructor")
					}
				}
			}
			if !found || len(c.Descriptors) != 0 || c.LogicalBytes != 0 {
				t.Fatal("failed ctor resource side effect")
			}
		})
	}
}

func TestVFS0aParent15RepeatedMessageCode(t *testing.T) {
	src := `import java.io.*;public class PMessages{public static int run()throws IOException{File f=new File("m");FileNotFoundException a=null,b=null;try{new FileInputStream(f);}catch(FileNotFoundException e){a=e;}try{new FileInputStream(f);}catch(FileNotFoundException e){b=e;}return a!=null&&b!=null&&a!=b&&a.getMessage()!=b.getMessage()&&a.getMessage().equals("m (No such file or directory)")&&a.getMessage().equals(b.getMessage())&&a.getCause()==null&&b.getCause()==null?1:0;}}`
	raw := [][]byte{vfsParentCompileOracle(t, "PMessages", src, 1)}
	a := vfsParentNativeRun(t, "PMessages", raw, nil, 1, 4096, 4096, nil)
	b := vfsParentNativeRun(t, "PMessages", raw, nil, 1, 7, 1, nil)
	if a.Final.Slice.MachineStateRoot != b.Final.Slice.MachineStateRoot || a.Final.Slice.DescriptorCount != 0 {
		t.Fatal("message construction state mismatch")
	}
}

func TestVFS0aParent2528ValidationIsNotLiveAuthority(t *testing.T) {
	raw := [][]byte{vfsParentCompileOracle(t, "PStay", "public class PStay{public static int run(){int x=0;for(int i=0;i<5;i++)x+=i;return x;}}", 10)}
	s, e := NewMemory(common.HexToAddress("0x7d07"))
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	id := crypto.Keccak256Hash([]byte(t.Name()))
	r, e := s.Start(id, raw, "PStay", "run", nil, []SeedFile{{Path: []byte("f"), Data: []byte{1}}}, 1, 4096, 100_000_000)
	if e != nil || r.Slice.Lifecycle != 1 {
		t.Fatalf("live control %v %+v", e, r.Slice)
	}
	c, e := vfsParentDecodeWire(r.Checkpoint)
	if e != nil {
		t.Fatal(e)
	}
	changed := append([]byte(nil), r.Checkpoint...)
	changed[c.Inodes[3].DataOffset] = 2
	changed = vfsParentRehashForView(t, changed)
	if _, _, e := vfsParentValidateCall(t, s, raw, changed); e != nil {
		t.Fatal("well-formed view control rejected", e)
	}
	forged, e := s.Resume(id, r.Slice.Epoch, r.Slice.CheckpointRoot, raw, changed, 1, 4096, 100_000_000)
	if e == nil {
		t.Fatal("view incorrectly granted live authority")
	}
	vfsBoundaryWantError(t, s, forged.RevertData, e, "LC0ControlError", 4)
	for _, tc := range []struct {
		name  string
		owner common.Address
		epoch uint64
		root  common.Hash
		raw   [][]byte
		q     uint64
		code  uint64
	}{
		{"owner", common.HexToAddress("0x7d08"), r.Slice.Epoch, r.Slice.CheckpointRoot, raw, 1, 2},
		{"epoch", s.owner, r.Slice.Epoch + 1, r.Slice.CheckpointRoot, raw, 1, 3},
		{"root", s.owner, r.Slice.Epoch, common.Hash{}, raw, 1, 4},
		{"artifact", s.owner, r.Slice.Epoch, r.Slice.CheckpointRoot, [][]byte{append(append([]byte(nil), raw[0]...), 0)}, 1, 5},
		{"budget", s.owner, r.Slice.Epoch, r.Slice.CheckpointRoot, raw, 0, 6},
	} {
		t.Run(tc.name, func(t *testing.T) {
			data, e := s.contractABI.Pack("resume", id, tc.epoch, tc.root, tc.raw, r.Checkpoint, tc.q, uint32(4096))
			if e != nil {
				t.Fatal(e)
			}
			cfg := s.vfs0aHarnessRuntimeConfig(s.stateDB.Copy(), 100_000_000)
			cfg.Origin = tc.owner
			out, _, e := evmruntime.Call(s.contract, data, cfg)
			if e == nil {
				t.Fatal("invalid control accepted")
			}
			vfsBoundaryWantError(t, s, out, e, "LC0ControlError", tc.code)
		})
	}
	next, e := s.Resume(id, r.Slice.Epoch, r.Slice.CheckpointRoot, raw, r.Checkpoint, 1, 4096, 100_000_000)
	if e != nil || next.Slice.Epoch != r.Slice.Epoch+1 {
		t.Fatal("exact old head retry failed", e)
	}
	stale, e := s.Resume(id, r.Slice.Epoch, r.Slice.CheckpointRoot, raw, r.Checkpoint, 1, 4096, 100_000_000)
	if e == nil {
		t.Fatal("stale committed parent accepted")
	}
	vfsBoundaryWantError(t, s, stale.RevertData, e, "LC0ControlError", 3)
}

func TestVFS0aParent16MessageAllocationOOM(t *testing.T) {
	src := `import java.io.*;public class PMessageOOM{public static int run(){File f=new File("m");for(int i=0;i<1019;i++)new Object();try{new FileInputStream(f);}catch(OutOfMemoryError e){return 1;}catch(FileNotFoundException e){return 2;}return 0;}}`
	// Unbounded stock JVMs return FNFE (2); EVM's explicit ordinary-object quota
	// must produce its genuine OOM (1), not a fabricated null-message exception.
	raw := [][]byte{vfsParentCompileOracle(t, "PMessageOOM", src, 2)}
	s, e := NewMemory(common.HexToAddress("0x7d09"))
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	id := crypto.Keccak256Hash([]byte(t.Name()))
	r, e := s.Start(id, raw, "PMessageOOM", "run", nil, nil, 4096, 4096, 1_000_000_000)
	seenMessageFrame := false
	calls := 0
	for {
		calls++
		if e != nil {
			t.Fatalf("OOM chain call%d: %v %x", calls, e, r.RevertData)
		}
		c, er := vfsParentDecodeWire(r.Checkpoint)
		if er != nil {
			t.Fatal(er)
		}
		if r.Slice.TotalJvmSteps+r.Slice.TotalInternalSteps > 65536 || calls > 4096 {
			t.Fatal("dedicated quota-test budget")
		}
		if len(c.Descriptors) != 0 || len(c.Inodes) != 3 || c.LogicalBytes != 0 {
			t.Fatal("failed open/message OOM leaked filesystem effect")
		}
		objects := binary.BigEndian.Uint16(c.Bytes[c.HeapHeaderOffset+4:])
		for _, f := range c.Frames {
			if f.Class == 37 && f.Method == 5 {
				seenMessageFrame = true
				if objects != 1024 {
					t.Fatalf("unexpected pre-OOM ordinary objects%d", objects)
				}
			}
		}
		if r.Slice.Lifecycle != 1 {
			if r.Slice.Lifecycle != 2 || r.Slice.Result != 1 || !seenMessageFrame {
				t.Fatalf("OOM after real Java message-frame execution not demonstrated: %+v seen=%t objects%d", r.Slice, seenMessageFrame, objects)
			}
			t.Logf("genuine message-allocation OOM: calls%d JVM%d internal%d checkpoint%d", calls, r.Slice.TotalJvmSteps, r.Slice.TotalInternalSteps, len(r.Checkpoint))
			break
		}
		q := uint64(4096)
		if objects >= 1000 {
			q = 1
		} else if objects >= 700 {
			q = 64
		}
		r, e = s.Resume(id, r.Slice.Epoch, r.Slice.CheckpointRoot, raw, r.Checkpoint, q, 4096, 1_000_000_000)
	}
}

func TestVFS0aParent04PathProfileBounds(t *testing.T) {
	cases := []struct {
		name, path string
		reject     bool
	}{
		{"empty", "", true}, {"root-escape", "/../escape", true}, {"non-ascii", "\u0080", true}, {"control", "\t", true},
		{"component64", strings.Repeat("x", 64), false}, {"component65", strings.Repeat("x", 65), true},
		{"depth16", "/" + strings.TrimSuffix(strings.Repeat("x/", 16), "/"), false}, {"depth17", "/" + strings.TrimSuffix(strings.Repeat("x/", 17), "/"), true},
		{"path256", "/" + strings.Repeat("x", 64) + "/" + strings.Repeat("y", 64) + "/" + strings.Repeat("z", 64) + "/" + strings.Repeat("w", 60), false},
		{"path257", "/" + strings.Repeat("x", 64) + "/" + strings.Repeat("y", 64) + "/" + strings.Repeat("z", 64) + "/" + strings.Repeat("w", 61), true},
	}
	for i, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			class := fmt.Sprintf("PPathLimit%d", i)
			src := fmt.Sprintf(`public class %s{public static int run(){new java.io.File(%q).exists();return 1;}}`, class, tc.path)
			raw := [][]byte{vfsParentCompileOracle(t, class, src, 1)}
			s, e := NewMemory(common.HexToAddress("0x7d10"))
			if e != nil {
				t.Fatal(e)
			}
			defer s.Close()
			id := crypto.Keccak256Hash([]byte(t.Name()))
			r, e := s.Start(id, raw, class, "run", nil, nil, 4096, 4096, 1_000_000_000)
			for n := 0; e == nil && r.Slice.Lifecycle == 1; n++ {
				if n > 4096 || r.Slice.TotalJvmSteps+r.Slice.TotalInternalSteps > 65536 {
					t.Fatal("path-copy budget")
				}
				r, e = s.Resume(id, r.Slice.Epoch, r.Slice.CheckpointRoot, raw, r.Checkpoint, 4096, 4096, 1_000_000_000)
			}
			if tc.reject {
				if e == nil {
					t.Fatal("unsupported path accepted")
				}
				vfsBoundaryWantError(t, s, r.RevertData, e, "VFS0aProfileError", 1, 1)
			} else if e != nil || r.Slice.Lifecycle != 2 || r.Slice.Result != 1 {
				t.Fatalf("valid path rejected %v %+v", e, r.Slice)
			}
		})
	}
}

// TEST-only constant-pool editing of a trusted compiler output, to check Java
// access/invocation rules. No class parser is added to production transport.
func vfsParentReplaceUTF(t *testing.T, raw []byte, from, to string) []byte {
	t.Helper()
	out := append([]byte(nil), raw[:10]...)
	n := int(binary.BigEndian.Uint16(raw[8:10]))
	at := 10
	hits := 0
	for i := 1; i < n; i++ {
		tag := raw[at]
		at++
		out = append(out, tag)
		width := 0
		switch tag {
		case 1:
			l := int(binary.BigEndian.Uint16(raw[at:]))
			at += 2
			text := string(raw[at : at+l])
			at += l
			if text == from {
				text = to
				hits++
			}
			out = append(out, byte(len(text)>>8), byte(len(text)))
			out = append(out, []byte(text)...)
			continue
		case 3, 4, 9, 10, 11, 12, 18:
			width = 4
		case 5, 6:
			width = 8
			i++
		case 7, 8, 16:
			width = 2
		case 15:
			width = 3
		default:
			t.Fatalf("unexpected trusted CP tag%d", tag)
		}
		out = append(out, raw[at:at+width]...)
		at += width
	}
	if hits != 1 {
		t.Fatalf("trusted UTF replacement%s hits%d", from, hits)
	}
	return append(out, raw[at:]...)
}

func TestVFS0aParent02PrivateNativeAccessModes(t *testing.T) {
	src := `public class PPrivate{public static int run(){java.io.File f=new java.io.File("f");return f.exists()?1:0;}}`
	raw := vfsParentCompileOracle(t, "PPrivate", src, 0)
	raw = vfsParentReplaceUTF(t, raw, "exists", "stat0")
	raw = vfsParentReplaceUTF(t, raw, "()Z", "()I")
	// This tiny trusted fixture has exactly one invokevirtual byte. The name and
	// descriptor edits preserve its operands; test each forbidden dispatch mode.
	at := -1
	for i, b := range raw {
		if b == 0xb6 {
			if at != -1 {
				t.Fatal("ambiguous fixture invokevirtual byte")
			}
			at = i
		}
	}
	if at < 0 {
		t.Fatal("missing fixture invokevirtual")
	}
	for _, op := range []byte{0xb6, 0xb7, 0xb8} {
		t.Run(fmt.Sprintf("opcode%x", op), func(t *testing.T) {
			bad := append([]byte(nil), raw...)
			bad[at] = op
			s, e := NewMemory(common.HexToAddress("0x7d11"))
			if e != nil {
				t.Fatal(e)
			}
			defer s.Close()
			r, e := s.Start(crypto.Keccak256Hash([]byte(t.Name())), [][]byte{bad}, "PPrivate", "run", nil, nil, 4096, 4096, 100_000_000)
			sel := s.contractABI.Errors["CallError"].ID
			if e == nil || len(r.RevertData) < 4 || !bytes.Equal(r.RevertData[:4], sel[:4]) {
				t.Fatalf("foreign private native dispatch did not hard-fail: %v %x", e, r.RevertData)
			}
			if len(r.Checkpoint) != 0 || len(r.Logs) != 0 {
				t.Fatal("private native failure published state")
			}
			t.Logf("CallError data%x", r.RevertData)
		})
	}
}
