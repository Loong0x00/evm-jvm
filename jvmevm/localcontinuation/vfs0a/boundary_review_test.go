package vfs0a

// Independent FINAL-VFS0a boundary/rollback review. Production Go remains opaque:
// Java sources below are trusted test fixtures and wire decoding is assertion-only.
import (
	"bytes"
	"context"
	"encoding/binary"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strconv"
	"testing"
	"time"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
)

const vfsBoundarySource = `import java.io.*;
public final class VFSBoundaryProbe {
 public static int noop(){return 1;}
 public static int failedOpenNoEffects(int which) throws Exception {
  if(which==1)try{new FileInputStream(new File("missing"));}catch(FileNotFoundException e){return "missing (No such file or directory)".equals(e.getMessage())?1:0;}
  if(which==2)try{new FileOutputStream(new File("missing/child"));}catch(FileNotFoundException e){return "missing/child (No such file or directory)".equals(e.getMessage())?1:0;}
  if(which==3)try{new FileInputStream(new File("dir"));}catch(FileNotFoundException e){return "dir (Is a directory)".equals(e.getMessage())?1:0;}
  if(which==4)try{new FileOutputStream(new File("/ro/r"));}catch(FileNotFoundException e){return "/ro/r (Permission denied)".equals(e.getMessage())?1:0;}
  if(which==5)try{new FileInputStream(new File("plain/child"));}catch(FileNotFoundException e){return "plain/child (Not a directory)".equals(e.getMessage())?1:0;}
  return 0;
 }
 public static int precedenceAndLow8() throws Exception {
  FileOutputStream o=new FileOutputStream(new File("bytes")); o.write(-1);o.write(0x123);o.close();
  byte[] b=new byte[3]; FileInputStream i=new FileInputStream(new File("bytes"));int n=i.read(b);i.close();int v=0;
  if(n==2 && b[0]==-1 && b[1]==35)v|=1;
  try{i.read(null,-1,-1);}catch(NullPointerException e){v|=2;}
  try{i.read(b,4,0);}catch(IndexOutOfBoundsException e){v|=4;}
  if(i.read(b,3,0)==0)v|=8;
  try{o.write((byte[])null,-1,-1);}catch(NullPointerException e){v|=16;}
  try{o.write(b,4,0);}catch(IndexOutOfBoundsException e){v|=32;}
  o.write(b,3,0); return v;
 }
 public static int gapAppendStale() throws Exception {
  File f=new File("gap"); FileOutputStream first=new FileOutputStream(f);first.write(new byte[]{65,66,67});
  FileInputStream stale=new FileInputStream(f);byte[] old=new byte[2];if(stale.read(old)!=2)return 0;
  FileOutputStream trunc=new FileOutputStream(f);trunc.write(88);first.write(89);
  if(stale.read()!=0 || stale.read()!=89)return 0;
  FileOutputStream app=new FileOutputStream(f,true);FileOutputStream again=new FileOutputStream(f);again.write(81);app.write(82);
  first.close();trunc.close();app.close();again.close();stale.close();
  byte[] z=new byte[3];FileInputStream in=new FileInputStream(f);int n=in.read(z);in.close();
  return n==2&&z[0]==81&&z[1]==82?1:0;
 }
 public static int mkdirBoundary(int excess){return new File(excess==0?"last":"last/child").mkdirs()?1:0;}
 public static int descriptors(int n) throws Exception {for(int i=0;i<n;i++){FileOutputStream o=new FileOutputStream(new File("descs"),true);o.close();}return 1;}
 public static int transfer(int n) throws Exception {FileOutputStream o=new FileOutputStream(new File("transfer"));o.write(new byte[n]);o.close();return 1;}
 public static int readTransfer(int n) throws Exception {FileInputStream i=new FileInputStream(new File("/ro/input"));byte[] b=new byte[n];int got=i.read(b);i.close();return got==n?1:0;}
 public static int fileQuota(int extra) throws Exception {FileOutputStream o=new FileOutputStream(new File("large"));byte[] b=new byte[4096];for(int i=0;i<16;i++)o.write(b);if(extra!=0)o.write(extra);o.close();return 1;}
 public static int aggregateQuota(int extra) throws Exception {FileOutputStream o=new FileOutputStream(new File("aggregate"));byte[] b=new byte[4096];for(int i=0;i<15;i++)o.write(b);o.write(new byte[4095]);if(extra!=0)o.write(extra);o.close();return 1;}
 public static int allocate(int a,int b){byte[] x=new byte[a];byte[] y=new byte[b];x[0]=1;y[0]=2;return x[0]+y[0]-2;}
 public static int nativeWritePending() throws Exception {FileOutputStream o=new FileOutputStream(new File("native"));o.write(new byte[]{11,12,13,14});o.close();return 1;}
}
final class VFSBoundaryAux1{} final class VFSBoundaryAux2{} final class VFSBoundaryAux3{}`

func vfsBoundaryCompileBundle(t *testing.T) [][]byte {
	t.Helper()
	d := t.TempDir()
	p := filepath.Join(d, "VFSBoundaryProbe.java")
	if err := os.WriteFile(p, []byte(vfsBoundarySource), 0o600); err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, "/usr/lib/jvm/java-8-openjdk/bin/javac", "-source", "8", "-target", "8", "-g:none", "-d", d, p)
	if out, err := cmd.CombinedOutput(); err != nil {
		t.Fatalf("trusted Java8 fixture compile: %v\n%s", err, out)
	}
	names := []string{"VFSBoundaryProbe", "VFSBoundaryAux1", "VFSBoundaryAux2", "VFSBoundaryAux3"}
	out := make([][]byte, len(names))
	for i, n := range names {
		raw, err := os.ReadFile(filepath.Join(d, n+".class"))
		if err != nil {
			t.Fatal(err)
		}
		out[i] = raw
	}
	return out
}

func vfsBoundaryCompile(t *testing.T) []byte { t.Helper(); return vfsBoundaryCompileBundle(t)[0] }

type vfsBoundaryRun struct {
	Result Result
	Calls  int
	MaxGas uint64
}

func vfsBoundaryChain(t *testing.T, s *Session, raw []byte, entry string, args []int32, seeds []SeedFile, q uint64, internal uint32, gas, totalLimit uint64, label string) vfsBoundaryRun {
	t.Helper()
	id := crypto.Keccak256Hash([]byte(t.Name() + ":" + label))
	r, err := s.Start(id, [][]byte{raw}, "VFSBoundaryProbe", entry, args, seeds, q, internal, gas)
	out := vfsBoundaryRun{}
	for calls := 1; ; calls++ {
		if err != nil {
			t.Fatalf("%s call%d: %v revert=%x", label, calls, err, r.RevertData)
		}
		out.Calls = calls
		if r.GasUsed > out.MaxGas {
			out.MaxGas = r.GasUsed
		}
		if r.Slice.TotalJvmSteps+r.Slice.TotalInternalSteps > totalLimit {
			t.Fatalf("%s exceeded total units: %d+%d", label, r.Slice.TotalJvmSteps, r.Slice.TotalInternalSteps)
		}
		if r.Slice.Lifecycle != 1 {
			out.Result = r
			return out
		}
		if calls >= 4096 {
			t.Fatalf("%s exceeded VFS slice allowance", label)
		}
		r, err = s.Resume(id, r.Slice.Epoch, r.Slice.CheckpointRoot, [][]byte{raw}, r.Checkpoint, q, internal, gas)
	}
}

func vfsBoundarySession(t *testing.T, suffix byte) *Session {
	t.Helper()
	a := common.Address{}
	a[0] = 0xb0
	a[19] = suffix
	s, err := NewMemory(a)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { s.Close() })
	return s
}

func vfsBoundaryWantReturned(t *testing.T, run vfsBoundaryRun, value int32) vfsParentCheckpointWire {
	t.Helper()
	r := run.Result
	if r.Slice.Lifecycle != 2 || r.Slice.Result != value || r.Slice.JavaKind != 0 || r.Slice.JavaRef != 0 || len(r.Slice.JavaClass) != 0 {
		t.Fatalf("terminal=%+v want RETURNED/%d", r.Slice, value)
	}
	wire, err := vfsParentDecodeWire(r.Checkpoint)
	if err != nil {
		t.Fatal(err)
	}
	if uint32(len(wire.Inodes)) != r.Slice.InodeCount || uint32(len(wire.Descriptors)) != r.Slice.DescriptorCount || wire.LogicalBytes != r.Slice.LogicalFileBytes {
		t.Fatalf("typed wire/result counts differ: inodes=%d/%d descriptors=%d/%d bytes=%d/%d", len(wire.Inodes), r.Slice.InodeCount, len(wire.Descriptors), r.Slice.DescriptorCount, wire.LogicalBytes, r.Slice.LogicalFileBytes)
	}
	return wire
}

func vfsBoundaryWantError(t *testing.T, s *Session, got []byte, err error, errorName string, words ...uint64) {
	t.Helper()
	e := s.contractABI.Errors[errorName]
	want := make([]byte, 4+32*len(words))
	copy(want, e.ID[:4])
	for i, w := range words {
		binary.BigEndian.PutUint64(want[4+i*32+24:4+(i+1)*32], w)
	}
	if !bytes.Equal(got, want) {
		t.Fatalf("%s revert=%x want=%x err=%v", errorName, got, want, err)
	}
}

func vfsBoundaryRevert(t *testing.T, s *Session, raw []byte, entry string, args []int32, seeds []SeedFile, gas uint64, errorName string, words ...uint64) Result {
	t.Helper()
	id := crypto.Keccak256Hash([]byte(t.Name() + ":" + entry + ":" + fmt.Sprint(args) + ":" + fmt.Sprint(len(seeds))))
	r, err := s.Start(id, [][]byte{raw}, "VFSBoundaryProbe", entry, args, seeds, 4096, 4096, gas)
	if err == nil {
		t.Fatalf("%s unexpectedly succeeded: %+v", errorName, r.Slice)
	}
	vfsBoundaryWantError(t, s, r.RevertData, err, errorName, words...)
	if r.GasUsed == 0 || !reflect.DeepEqual(r.Slice, SliceResult{}) || len(r.Checkpoint) != 0 || len(r.Logs) != 0 {
		t.Fatalf("failed call leaked success output: %+v", r)
	}
	h, he := s.Head(id)
	if he != nil || !reflect.DeepEqual(h, Head{}) {
		t.Fatalf("failed start published head: %+v %v", h, he)
	}
	return r
}

func TestVFS0aBoundaryFinalArtifactAndSemantics(t *testing.T) {
	code, err := Runtime()
	if err != nil {
		t.Fatal(err)
	}
	hash, err := RuntimeHash()
	if err != nil {
		t.Fatal(err)
	}
	if len(code) != 293010 || hash != "78d57a051311538c13ed6b60a59ceab5800722bf49ec9e9f3683bb23521739c9" {
		t.Fatalf("reviewed artifact=%d/%s", len(code), hash)
	}
	raw := vfsBoundaryCompile(t)
	cases := []struct {
		name, entry   string
		want          int32
		inodes, descs uint32
		dataPath      string
		data          []byte
	}{
		{"byte-null-bounds-zero-low8", "precedenceAndLow8", 63, 4, 2, "bytes", []byte{255, 35}},
		{"gap-append-current-eof-stale", "gapAppendStale", 1, 4, 6, "gap", []byte{81, 82}},
	}
	for i, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			s := vfsBoundarySession(t, byte(10+i))
			run := vfsBoundaryChain(t, s, raw, tc.entry, nil, nil, 4096, 4096, vfs0aHarnessOrdinaryGas, 4096, tc.name)
			w := vfsBoundaryWantReturned(t, run, tc.want)
			if uint32(len(w.Inodes)) != tc.inodes || uint32(len(w.Descriptors)) != tc.descs {
				t.Fatalf("wire counts=%d/%d want=%d/%d", len(w.Inodes), len(w.Descriptors), tc.inodes, tc.descs)
			}
			v, err := s.InspectFile([][]byte{raw}, run.Result.Checkpoint, []byte(tc.dataPath), 0, 4096)
			if err != nil || !bytes.Equal(v.Data, tc.data) {
				t.Fatalf("inspection=%+v err=%v", v, err)
			}
		})
	}
	seeds := []SeedFile{{Path: []byte("dir/seed"), Data: []byte{1}}, {Path: []byte("/ro/r"), Data: []byte{2}, ReadOnly: true}, {Path: []byte("plain"), Data: []byte{3}}}
	for which := int32(1); which <= 5; which++ {
		t.Run(fmt.Sprintf("failed-open-no-effects-%d", which), func(t *testing.T) {
			s := vfsBoundarySession(t, byte(15+which))
			run := vfsBoundaryChain(t, s, raw, "failedOpenNoEffects", []int32{which}, seeds, 4096, 4096, vfs0aHarnessOrdinaryGas, 4096, fmt.Sprintf("failed-%d", which))
			w := vfsBoundaryWantReturned(t, run, 1)
			if len(w.Inodes) != 7 || len(w.Descriptors) != 0 || w.LogicalBytes != 3 {
				t.Fatalf("failed open mutated VFS: %d/%d/%d", len(w.Inodes), len(w.Descriptors), w.LogicalBytes)
			}
		})
	}
}

func vfsBoundaryInodeSeeds(excess bool) []SeedFile {
	seeds := make([]SeedFile, 0, 16)
	for i := 0; i < 15; i++ {
		seeds = append(seeds, SeedFile{Path: []byte(fmt.Sprintf("a%02d/b/c/d", i))})
	}
	last := "a00/e"
	if excess {
		last = "extra/f"
	}
	seeds = append(seeds, SeedFile{Path: []byte(last)})
	return seeds
}

func TestVFS0aBoundaryRawBundleLimits(t *testing.T) {
	bundle := vfsBoundaryCompileBundle(t)
	s := vfsBoundarySession(t, 29)
	id := crypto.Keccak256Hash([]byte(t.Name() + ":four"))
	r, err := s.Start(id, bundle, "VFSBoundaryProbe", "noop", nil, nil, 4096, 4096, vfs0aHarnessOrdinaryGas)
	if err != nil {
		t.Fatalf("four valid raw classes: %v", err)
	}
	vfsBoundaryWantReturned(t, vfsBoundaryRun{Result: r, Calls: 1}, 1)
	id = crypto.Keccak256Hash([]byte(t.Name() + ":five"))
	five := append(append([][]byte(nil), bundle...), bundle[3])
	failed, err := s.Start(id, five, "VFSBoundaryProbe", "noop", nil, nil, 4096, 4096, vfs0aHarnessOrdinaryGas)
	if err == nil {
		t.Fatal("five raw classes accepted")
	}
	vfsBoundaryWantError(t, s, failed.RevertData, err, "LinkError", 1, 5)
	id = crypto.Keccak256Hash([]byte(t.Name() + ":bytes65536"))
	exact := bytes.Repeat([]byte{0}, 65536)
	failed, err = s.Start(id, [][]byte{exact}, "VFSBoundaryProbe", "noop", nil, nil, 4096, 4096, vfs0aHarnessOrdinaryGas)
	if err == nil {
		t.Fatal("malformed exact-64KiB class accepted")
	}
	vfsBoundaryWantError(t, s, failed.RevertData, err, "ClassError", 1, 0)
	id = crypto.Keccak256Hash([]byte(t.Name() + ":bytes65537"))
	failed, err = s.Start(id, [][]byte{append(exact, 0)}, "VFSBoundaryProbe", "noop", nil, nil, 4096, 4096, vfs0aHarnessOrdinaryGas)
	if err == nil {
		t.Fatal("raw 64KiB+1 accepted")
	}
	vfsBoundaryWantError(t, s, failed.RevertData, err, "LinkError", 1, 65537)
}

func TestVFS0aBoundarySeedInodeDescriptorLimits(t *testing.T) {
	raw := vfsBoundaryCompile(t)
	t.Run("seed-order-count-bytes-ro", func(t *testing.T) {
		s := vfsBoundarySession(t, 30)
		seeds := make([]SeedFile, 16)
		for i := range seeds {
			seeds[i] = SeedFile{Path: []byte(fmt.Sprintf("s%02d", i)), ReadOnly: i == 0}
		}
		seeds[0].Data = bytes.Repeat([]byte{0xa5}, 65536)
		a := vfsBoundaryChain(t, s, raw, "noop", nil, seeds, 4096, 4096, vfs0aHarnessBoundaryGas, 65536, "seed16-64k")
		w := vfsBoundaryWantReturned(t, a, 1)
		if len(w.Inodes) != 19 || w.LogicalBytes != 65536 || w.Inodes[3].ReadOnly != 1 || len(w.Inodes[3].Data) != 65536 {
			t.Fatalf("seed wire boundary wrong: inodes=%d bytes=%d ro=%d data=%d", len(w.Inodes), w.LogicalBytes, w.Inodes[3].ReadOnly, len(w.Inodes[3].Data))
		}
		rev := append([]SeedFile(nil), seeds...)
		rev[0], rev[1] = rev[1], rev[0]
		b := vfsBoundaryChain(t, s, raw, "noop", nil, rev, 4096, 4096, vfs0aHarnessBoundaryGas, 65536, "seed-reordered")
		wb := vfsBoundaryWantReturned(t, b, 1)
		if wb.SeedRoot == w.SeedRoot || wb.VFSRoot == w.VFSRoot {
			t.Fatal("ordered seed commitment collision")
		}
	})
	t.Run("seed-plus-one-and-collision", func(t *testing.T) {
		s := vfsBoundarySession(t, 31)
		vfsBoundaryRevert(t, s, raw, "noop", nil, []SeedFile{{Path: []byte("big"), Data: bytes.Repeat([]byte{1}, 65537)}}, vfs0aHarnessBoundaryGas, "VFS0aQuotaError", 1, 65537, 65536)
		vfsBoundaryRevert(t, s, raw, "noop", nil, []SeedFile{{Path: []byte("a//b"), Data: nil}, {Path: []byte("a/b"), Data: nil}}, vfs0aHarnessOrdinaryGas, "VFS0aProfileError", 1, 0)
	})
	t.Run("inode64-65", func(t *testing.T) {
		s := vfsBoundarySession(t, 32)
		ok := vfsBoundaryChain(t, s, raw, "noop", nil, vfsBoundaryInodeSeeds(false), 4096, 4096, vfs0aHarnessOrdinaryGas, 4096, "inode64")
		w := vfsBoundaryWantReturned(t, ok, 1)
		if len(w.Inodes) != 64 {
			t.Fatalf("inodes=%d", len(w.Inodes))
		}
		vfsBoundaryRevert(t, s, raw, "noop", nil, vfsBoundaryInodeSeeds(true), vfs0aHarnessOrdinaryGas, "VFS0aQuotaError", 2, 65, 64)
		base := vfsBoundaryInodeSeeds(false)[:15] // 3 builtins + 60 seeded nodes = 63.
		made := vfsBoundaryChain(t, s, raw, "mkdirBoundary", []int32{0}, base, 4096, 4096, vfs0aHarnessOrdinaryGas, 4096, "mkdir-to-64")
		mw := vfsBoundaryWantReturned(t, made, 1)
		if len(mw.Inodes) != 64 {
			t.Fatalf("mkdir boundary inodes=%d", len(mw.Inodes))
		}
		vfsBoundaryRevert(t, s, raw, "mkdirBoundary", []int32{1}, base, vfs0aHarnessOrdinaryGas, "VFS0aQuotaError", 2, 65, 64)
	})
	t.Run("descriptor32-33-closed", func(t *testing.T) {
		s := vfsBoundarySession(t, 33)
		ok := vfsBoundaryChain(t, s, raw, "descriptors", []int32{32}, nil, 4096, 4096, vfs0aHarnessBoundaryGas, 65536, "descriptor32")
		w := vfsBoundaryWantReturned(t, ok, 1)
		if len(w.Descriptors) != 32 {
			t.Fatalf("descriptors=%d", len(w.Descriptors))
		}
		for _, d := range w.Descriptors {
			if d.Phase != 3 || d.Depth != 0 || d.PC != 0 {
				t.Fatalf("noncanonical closed descriptor: %+v", d)
			}
		}
		id := crypto.Keccak256Hash([]byte(t.Name() + ":descriptor33"))
		r, err := s.Start(id, [][]byte{raw}, "VFSBoundaryProbe", "descriptors", []int32{33}, nil, 4096, 4096, vfs0aHarnessBoundaryGas)
		for calls := 1; ; calls++ {
			if err != nil {
				t.Fatalf("descriptor33 initial/early failure call%d: %v", calls, err)
			}
			if r.Slice.Lifecycle != 1 {
				t.Fatal("descriptor33 returned instead of quota failure")
			}
			before, headErr := s.Head(id)
			if headErr != nil {
				t.Fatal(headErr)
			}
			failed, resumeErr := s.Resume(id, r.Slice.Epoch, r.Slice.CheckpointRoot, [][]byte{raw}, r.Checkpoint, 4096, 4096, vfs0aHarnessBoundaryGas)
			if resumeErr != nil {
				vfsBoundaryWantError(t, s, failed.RevertData, resumeErr, "VFS0aQuotaError", 3, 33, 32)
				if failed.GasUsed == 0 || !reflect.DeepEqual(failed.Slice, SliceResult{}) || len(failed.Checkpoint) != 0 || len(failed.Logs) != 0 {
					t.Fatalf("descriptor quota leaked: %+v", failed)
				}
				after, _ := s.Head(id)
				if after != before {
					t.Fatal("descriptor quota changed prior head")
				}
				break
			}
			r = failed
			if calls >= 16 {
				t.Fatal("descriptor quota not reached")
			}
		}
	})
}

func TestVFS0aBoundaryTransferAndFileQuotas(t *testing.T) {
	raw := vfsBoundaryCompile(t)
	t.Run("transfer4096-4097", func(t *testing.T) {
		s := vfsBoundarySession(t, 40)
		ok := vfsBoundaryChain(t, s, raw, "transfer", []int32{4096}, nil, 4096, 4096, vfs0aHarnessBoundaryGas, 65536, "transfer4096")
		w := vfsBoundaryWantReturned(t, ok, 1)
		if w.LogicalBytes != 4096 {
			t.Fatalf("bytes=%d", w.LogicalBytes)
		}
		vfsBoundaryRevert(t, s, raw, "transfer", []int32{4097}, nil, vfs0aHarnessBoundaryGas, "VFS0aProfileError", 3, 37)
		readSeed := []SeedFile{{Path: []byte("/ro/input"), Data: bytes.Repeat([]byte{9}, 4096), ReadOnly: true}}
		readOK := vfsBoundaryChain(t, s, raw, "readTransfer", []int32{4096}, readSeed, 4096, 4096, vfs0aHarnessBoundaryGas, 65536, "read4096-ro")
		rw := vfsBoundaryWantReturned(t, readOK, 1)
		if rw.LogicalBytes != 4096 || rw.Inodes[3].ReadOnly != 1 {
			t.Fatalf("read-only input wire=%d/%d", rw.LogicalBytes, rw.Inodes[3].ReadOnly)
		}
		readPlus := []SeedFile{{Path: []byte("/ro/input"), Data: bytes.Repeat([]byte{9}, 4097), ReadOnly: true}}
		vfsBoundaryRevert(t, s, raw, "readTransfer", []int32{4097}, readPlus, vfs0aHarnessBoundaryGas, "VFS0aProfileError", 3, 38)
	})
	t.Run("per-file65536-plus-one", func(t *testing.T) {
		s := vfsBoundarySession(t, 41)
		ok := vfsBoundaryChain(t, s, raw, "fileQuota", []int32{0}, nil, 4096, 4096, vfs0aHarnessBoundaryGas, 65536, "file65536")
		w := vfsBoundaryWantReturned(t, ok, 1)
		if w.LogicalBytes != 65536 {
			t.Fatalf("bytes=%d", w.LogicalBytes)
		}
		vfsBoundaryRevert(t, s, raw, "fileQuota", []int32{1}, nil, vfs0aHarnessBoundaryGas, "VFS0aQuotaError", 4, 65537, 65536)
	})
	t.Run("aggregate-includes-ro-seed", func(t *testing.T) {
		s := vfsBoundarySession(t, 42)
		seed := []SeedFile{{Path: []byte("ro/seed"), Data: []byte{7}, ReadOnly: true}}
		ok := vfsBoundaryChain(t, s, raw, "aggregateQuota", []int32{0}, seed, 4096, 4096, vfs0aHarnessBoundaryGas, 65536, "aggregate65536")
		w := vfsBoundaryWantReturned(t, ok, 1)
		if w.LogicalBytes != 65536 {
			t.Fatalf("bytes=%d", w.LogicalBytes)
		}
		vfsBoundaryRevert(t, s, raw, "aggregateQuota", []int32{1}, seed, vfs0aHarnessBoundaryGas, "VFS0aQuotaError", 5, 65537, 65536)
	})
}

func TestVFS0aBoundaryQuantumOOGRollbackAndNativeReopen(t *testing.T) {
	raw := vfsBoundaryCompile(t)
	t.Run("quantum-internal1", func(t *testing.T) {
		a := vfsBoundaryChain(t, vfsBoundarySession(t, 50), raw, "gapAppendStale", nil, nil, 4096, 4096, vfs0aHarnessOrdinaryGas, 4096, "control")
		b := vfsBoundaryChain(t, vfsBoundarySession(t, 51), raw, "gapAppendStale", nil, nil, 1, 1, vfs0aHarnessOrdinaryGas, 4096, "q1i1")
		vfsBoundaryWantReturned(t, a, 1)
		vfsBoundaryWantReturned(t, b, 1)
		if a.Result.Slice.MachineStateRoot != b.Result.Slice.MachineStateRoot || a.Result.Slice.VFSStateRoot != b.Result.Slice.VFSStateRoot || a.Result.Slice.TotalJvmSteps != b.Result.Slice.TotalJvmSteps || a.Result.Slice.TotalInternalSteps != b.Result.Slice.TotalInternalSteps {
			t.Fatalf("quantum mismatch: control=%+v q1=%+v", a.Result.Slice, b.Result.Slice)
		}
		t.Logf("q1/internal1 calls=%d counters=%d/%d", b.Calls, b.Result.Slice.TotalJvmSteps, b.Result.Slice.TotalInternalSteps)
	})
	t.Run("oog-reserve-old-root-retry", func(t *testing.T) {
		s := vfsBoundarySession(t, 52)
		id := crypto.Keccak256Hash([]byte(t.Name()))
		parent, err := s.Start(id, [][]byte{raw}, "VFSBoundaryProbe", "nativeWritePending", nil, nil, 1, 1, vfs0aHarnessOrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
		before, err := s.Head(id)
		if err != nil {
			t.Fatal(err)
		}
		failed, err := s.Resume(id, parent.Slice.Epoch, parent.Slice.CheckpointRoot, [][]byte{raw}, parent.Checkpoint, 4096, 4096, 1)
		if err == nil || failed.GasUsed == 0 || !reflect.DeepEqual(failed.Slice, SliceResult{}) || len(failed.Checkpoint) != 0 || len(failed.Logs) != 0 {
			t.Fatalf("unsafe OOG output=%+v err=%v", failed, err)
		}
		after, _ := s.Head(id)
		if after != before {
			t.Fatal("OOG changed head")
		}
		retry, err := s.Resume(id, parent.Slice.Epoch, parent.Slice.CheckpointRoot, [][]byte{raw}, parent.Checkpoint, 4096, 4096, vfs0aHarnessOrdinaryGas)
		if err != nil {
			t.Fatalf("old-root retry: %v", err)
		}
		if retry.Slice.Epoch != parent.Slice.Epoch+1 {
			t.Fatal("retry did not advance exact old root")
		}
		s2 := vfsBoundarySession(t, 53)
		vfsBoundaryRevert(t, s2, raw, "noop", nil, nil, 25_000_000, "LC0ControlError", 7)
	})
	t.Run("disk-native-write-reopen", func(t *testing.T) {
		dir := t.TempDir()
		owner := common.HexToAddress("0xb400000000000000000000000000000000000054")
		s, err := Open(dir, owner)
		if err != nil {
			t.Fatal(err)
		}
		id := crypto.Keccak256Hash([]byte(t.Name()))
		r, err := s.Start(id, [][]byte{raw}, "VFSBoundaryProbe", "nativeWritePending", nil, nil, 1, 1, vfs0aHarnessOrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
		for i := 0; i < 4096; i++ {
			view, ve := s.InspectFile([][]byte{raw}, r.Checkpoint, []byte("native"), 0, 16)
			if ve == nil && bytes.Equal(view.Data, []byte{11, 12, 13, 14}) && r.Slice.Lifecycle == 1 {
				break
			}
			if r.Slice.Lifecycle != 1 {
				t.Fatal("no runnable native-write checkpoint")
			}
			r, err = s.Resume(id, r.Slice.Epoch, r.Slice.CheckpointRoot, [][]byte{raw}, r.Checkpoint, 1, 1, vfs0aHarnessOrdinaryGas)
			if err != nil {
				t.Fatal(err)
			}
		}
		epoch, root := r.Slice.Epoch, r.Slice.CheckpointRoot
		s.Close()
		s, err = Open(dir, owner)
		if err != nil {
			t.Fatal(err)
		}
		defer s.Close()
		cp, err := s.ReadCheckpoint(root)
		if err != nil {
			t.Fatal(err)
		}
		for i := 0; i < 4096 && r.Slice.Lifecycle == 1; i++ {
			r, err = s.Resume(id, epoch, root, [][]byte{raw}, cp, 7, 1, vfs0aHarnessOrdinaryGas)
			if err != nil {
				t.Fatal(err)
			}
			epoch, root, cp = r.Slice.Epoch, r.Slice.CheckpointRoot, r.Checkpoint
		}
		vfsBoundaryWantReturned(t, vfsBoundaryRun{Result: r}, 1)
		v, err := s.InspectFile([][]byte{raw}, r.Checkpoint, []byte("native"), 0, 16)
		if err != nil || !bytes.Equal(v.Data, []byte{11, 12, 13, 14}) {
			t.Fatalf("reopened native data=%v err=%v", v.Data, err)
		}
	})
}

func TestVFS0aBoundaryDurabilityAndStoreNamespace(t *testing.T) {
	raw := vfsBoundaryCompile(t)
	owner := common.HexToAddress("0xb600000000000000000000000000000000000062")
	dir := t.TempDir()
	s, err := Open(dir, owner)
	if err != nil {
		t.Fatal(err)
	}
	id := crypto.Keccak256Hash([]byte(t.Name()))
	parent, err := s.Start(id, [][]byte{raw}, "VFSBoundaryProbe", "nativeWritePending", nil, nil, 1, 1, vfs0aHarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	before, err := s.Head(id)
	if err != nil {
		t.Fatal(err)
	}
	fired := false
	s.testFault = func(p vfs0aHarnessFaultPoint) error {
		if p == vfs0aHarnessFaultAfterBlob && !fired {
			fired = true
			return fmt.Errorf("boundary durable fault")
		}
		return nil
	}
	failed, err := s.Resume(id, parent.Slice.Epoch, parent.Slice.CheckpointRoot, [][]byte{raw}, parent.Checkpoint, 1, 1, vfs0aHarnessOrdinaryGas)
	if err == nil || !fired || failed.GasUsed == 0 || !reflect.DeepEqual(failed.Slice, SliceResult{}) || len(failed.Checkpoint) != 0 || len(failed.Logs) != 0 || len(failed.RevertData) != 0 {
		t.Fatalf("durability failure leaked output: %+v %v", failed, err)
	}
	after, _ := s.Head(id)
	if after != before {
		t.Fatal("durability failure changed in-process head")
	}
	s.Close()
	if wrong, e := Open(dir, common.HexToAddress("0x9999")); e == nil {
		wrong.Close()
		t.Fatal("different-owner store opened")
	}
	s, err = Open(dir, owner)
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()
	after, err = s.Head(id)
	if err != nil || after != before {
		t.Fatalf("reopen head=%+v want=%+v err=%v", after, before, err)
	}
	cp, err := s.ReadCheckpoint(parent.Slice.CheckpointRoot)
	if err != nil {
		t.Fatal(err)
	}
	retry, err := s.Resume(id, parent.Slice.Epoch, parent.Slice.CheckpointRoot, [][]byte{raw}, cp, 1, 1, vfs0aHarnessOrdinaryGas)
	if err != nil || retry.Slice.Epoch != parent.Slice.Epoch+1 {
		t.Fatalf("durable old-root retry=%+v err=%v", retry.Slice, err)
	}
	old := t.TempDir()
	if err := os.WriteFile(filepath.Join(old, vfs0aHarnessStoreMarkerName), []byte("JVMEVM-MC-IOE0-DISK-STORE-1\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if oldSession, e := Open(old, owner); e == nil {
		oldSession.Close()
		t.Fatal("old profile marker accepted")
	}
	marker, _ := os.ReadFile(filepath.Join(old, vfs0aHarnessStoreMarkerName))
	if string(marker) != "JVMEVM-MC-IOE0-DISK-STORE-1\n" {
		t.Fatal("old profile store modified")
	}
}

func TestVFS0aBoundaryCheckpointExactMiB(t *testing.T) {
	if testing.Short() {
		t.Skip("explicit 1B-gas checkpoint boundary")
	}
	raw := vfsBoundaryCompile(t)
	s := vfsBoundarySession(t, 60)
	// Two primitive arrays make checkpoint size affine in 8-byte cells. A bounded
	// search finds the largest successful cell count, then seed bytes tune the
	// exact byte remainder. Every accepted candidate is EVM-issued and decoded.
	best := -1
	var bestRun vfsBoundaryRun
	lo, hi := 100000, 131070
	for lo <= hi {
		n := (lo + hi) / 2
		a := n / 2
		b := n - a
		runID := fmt.Sprintf("search-%d", n)
		id := crypto.Keccak256Hash([]byte(t.Name() + ":" + runID))
		r, err := s.Start(id, [][]byte{raw}, "VFSBoundaryProbe", "allocate", []int32{int32(a), int32(b)}, nil, 4096, 4096, vfs0aHarnessBoundaryGas)
		if err == nil {
			if len(r.Checkpoint) <= 1<<20 {
				best = n
				bestRun = vfsBoundaryRun{Result: r, Calls: 1}
				lo = n + 1
			} else {
				t.Fatal("host accepted oversized checkpoint")
			}
		} else {
			hi = n - 1
		}
	}
	if best < 0 {
		t.Fatal("no successful checkpoint sizing control")
	}
	_ = bestRun        // only issuance success, not blob rehashing, determines the search edge.
	cells := best - 16 // leave bounded room for the seed inode's fixed record.
	base := vfsBoundaryChain(t, s, raw, "allocate", []int32{int32(cells / 2), int32(cells - cells/2)}, nil, 4096, 4096, vfs0aHarnessBoundaryGas, 65536, "tuning-base")
	baseLen := len(base.Result.Checkpoint)
	gap := (1 << 20) - baseLen
	if gap < 0 || gap > 65536 {
		t.Fatalf("checkpoint tuning gap=%d base=%d cells=%d", gap, baseLen, cells)
	}
	// A seed adds its data bytes and a fixed inode/path record. Measure that fixed
	// delta with empty data, then choose exact payload without inferring guest state.
	measure := vfsBoundaryChain(t, s, raw, "allocate", []int32{int32(cells / 2), int32(cells - cells/2)}, []SeedFile{{Path: []byte("p")}}, 4096, 4096, vfs0aHarnessBoundaryGas, 65536, "measure-seed")
	fixed := len(measure.Result.Checkpoint) - baseLen
	payload := gap - fixed
	if payload < 0 || payload > 65536 {
		t.Fatalf("seed tuning payload=%d fixed=%d gap=%d", payload, fixed, gap)
	}
	exact := vfsBoundaryChain(t, s, raw, "allocate", []int32{int32(cells / 2), int32(cells - cells/2)}, []SeedFile{{Path: []byte("p"), Data: bytes.Repeat([]byte{3}, payload)}}, 4096, 4096, vfs0aHarnessBoundaryGas, 65536, "exact-mib")
	vfsBoundaryWantReturned(t, exact, 1)
	if len(exact.Result.Checkpoint) != 1<<20 {
		t.Fatalf("exact checkpoint=%d payload=%d cells=%d", len(exact.Result.Checkpoint), payload, best)
	}
	// +1 uses the same genuine Java state shape and one additional VFS byte. It
	// must fail atomically with the checkpoint-size error, with no success tuple.
	vfsBoundaryRevert(t, s, raw, "allocate", []int32{int32(cells / 2), int32(cells - cells/2)}, []SeedFile{{Path: []byte("p"), Data: bytes.Repeat([]byte{3}, payload+1)}}, vfs0aHarnessBoundaryGas, "LC0StateError", 1, 0)
	t.Logf("exact1MiB cells=%d searchEdge=%d seedPayload=%d gas=%d", cells, best, payload, exact.MaxGas)
}

func TestVFS0aBoundaryNativeWriteChild(t *testing.T) {
	if os.Getenv("JVMEVM_VFS0A_BOUNDARY_CHILD") != "" {
		dir := os.Getenv("JVMEVM_VFS0A_BOUNDARY_DIR")
		owner := common.HexToAddress(os.Getenv("JVMEVM_VFS0A_BOUNDARY_OWNER"))
		id := common.HexToHash(os.Getenv("JVMEVM_VFS0A_BOUNDARY_ID"))
		epoch, _ := strconv.ParseUint(os.Getenv("JVMEVM_VFS0A_BOUNDARY_EPOCH"), 10, 64)
		root := common.HexToHash(os.Getenv("JVMEVM_VFS0A_BOUNDARY_ROOT"))
		raw := vfsBoundaryCompile(t)
		s, err := Open(dir, owner)
		if err != nil {
			t.Fatal(err)
		}
		defer s.Close()
		cp, err := s.ReadCheckpoint(root)
		if err != nil {
			t.Fatal(err)
		}
		var r Result
		for i := 0; i < 4096; i++ {
			r, err = s.Resume(id, epoch, root, [][]byte{raw}, cp, 7, 1, vfs0aHarnessOrdinaryGas)
			if err != nil {
				t.Fatal(err)
			}
			if r.Slice.Lifecycle != 1 {
				if r.Slice.Lifecycle != 2 || r.Slice.Result != 1 {
					t.Fatalf("child terminal=%+v", r.Slice)
				}
				fmt.Printf("BOUNDARY_CHILD_OK %s %s\n", r.Slice.MachineStateRoot, r.Slice.VFSStateRoot)
				return
			}
			epoch, root, cp = r.Slice.Epoch, r.Slice.CheckpointRoot, r.Checkpoint
		}
		t.Fatal("child slices")
		return
	}
	raw := vfsBoundaryCompile(t)
	dir := t.TempDir()
	owner := common.HexToAddress("0xb500000000000000000000000000000000000061")
	s, err := Open(dir, owner)
	if err != nil {
		t.Fatal(err)
	}
	id := crypto.Keccak256Hash([]byte(t.Name()))
	r, err := s.Start(id, [][]byte{raw}, "VFSBoundaryProbe", "nativeWritePending", nil, nil, 1, 1, vfs0aHarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	for i := 0; i < 4096; i++ {
		v, ve := s.InspectFile([][]byte{raw}, r.Checkpoint, []byte("native"), 0, 16)
		if ve == nil && bytes.Equal(v.Data, []byte{11, 12, 13, 14}) && r.Slice.Lifecycle == 1 {
			break
		}
		r, err = s.Resume(id, r.Slice.Epoch, r.Slice.CheckpointRoot, [][]byte{raw}, r.Checkpoint, 1, 1, vfs0aHarnessOrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
	}
	epoch, root := r.Slice.Epoch, r.Slice.CheckpointRoot
	s.Close()
	cmd := exec.Command(os.Args[0], "-test.run=^TestVFS0aBoundaryNativeWriteChild$")
	cmd.Env = append(os.Environ(), "JVMEVM_VFS0A_BOUNDARY_CHILD=1", "JVMEVM_VFS0A_BOUNDARY_DIR="+dir, "JVMEVM_VFS0A_BOUNDARY_OWNER="+owner.Hex(), "JVMEVM_VFS0A_BOUNDARY_ID="+id.Hex(), "JVMEVM_VFS0A_BOUNDARY_EPOCH="+strconv.FormatUint(epoch, 10), "JVMEVM_VFS0A_BOUNDARY_ROOT="+root.Hex())
	out, err := cmd.CombinedOutput()
	if err != nil || !bytes.Contains(out, []byte("BOUNDARY_CHILD_OK")) {
		t.Fatalf("real child resume: %v\n%s", err, out)
	}
}
