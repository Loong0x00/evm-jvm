package sc0

import (
	"context"
	"fmt"
	"math/rand"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
	"time"
)

func TestSC0ParentForeignConstructorCannotOwnStringBacking(t *testing.T) {
	src := `public class SPForeign {static String s="safe";static class C{C(char[] a){char[] temporary=a;int n=temporary.length;}}public static int run(){new C(new char[]{1});return s.length();}}`
	cs := sc0VerifyCompileTrusted(t, map[string]string{"SPForeign.java": src}, []string{"SPForeign", "SPForeign$C"})
	raw := sc0VerifyRaw(cs, "SPForeign", "SPForeign$C")
	e := sc0VerifyNewEnv(t)
	defer e.close()
	r := sc0VerifyRunToEnd(t, e, "foreign-ctor", raw, "SPForeign", "run", 1, 1, sc0VerifyOrdinaryGas, 4096)
	sc0VerifyRequireReturned(t, r, 4)
	for _, cp := range r.snaps {
		strings := sc0VerifyObject(cp, sc0VerifyStringClass(raw))
		if len(strings) == 0 {
			continue
		}
		_, backing := sc0VerifyValue(cp.Bytes[strings[0].CellOffsets[len(strings[0].CellOffsets)-2]:])
		for _, f := range cp.Machine.Frames {
			if f.Class != 1 || len(f.LocalOffsets) < 3 || f.SP != 0 {
				continue
			}
			tag, ref := sc0VerifyValue(cp.Bytes[f.LocalOffsets[2]:])
			if tag != 2 || ref == 0 {
				continue
			}
			sc0VerifyValidateOK(t, e, raw, cp.Bytes)
			bad := sc0VerifyMutateRehash(t, cp.Bytes, f.LocalOffsets[2], func(b []byte) { sc0VerifyPutValue(b, 2, backing) })
			sc0VerifyAssertState(t, sc0VerifyValidate(e, raw, bad, sc0VerifyOrdinaryGas), 7)
			return
		}
	}
	t.Fatal("no genuine foreign constructor local2 checkpoint")
}

func TestSC0ParentCopyTemporaryMustBeSourceBacking(t *testing.T) {
	cs := sc0VerifyCompileTrusted(t, map[string]string{"SPCopy.java": `public class SPCopy {static String other="other";public static int run(){return new String("source").length();}}`}, []string{"SPCopy"})
	raw := sc0VerifyRaw(cs, "SPCopy")
	e := sc0VerifyNewEnv(t)
	defer e.close()
	r := sc0VerifyRunToEnd(t, e, "copy-temporary", raw, "SPCopy", "run", 1, 1, sc0VerifyOrdinaryGas, 4096)
	sc0VerifyRequireReturned(t, r, 6)
	for _, cp := range r.snaps {
		for _, f := range cp.Machine.Frames {
			if f.Class != sc0VerifyStringClass(raw) || f.PC != 9 || len(f.StackOffsets) < 2 {
				continue
			}
			off := f.StackOffsets[len(f.StackOffsets)-1]
			tag, actual := sc0VerifyValue(cp.Bytes[off:])
			if tag != 2 {
				continue
			}
			for _, s := range sc0VerifyObject(cp, sc0VerifyStringClass(raw)) {
				_, other := sc0VerifyValue(cp.Bytes[s.CellOffsets[len(s.CellOffsets)-2]:])
				if other == 0 || other == actual {
					continue
				}
				sc0VerifyValidateOK(t, e, raw, cp.Bytes)
				bad := sc0VerifyMutateRehash(t, cp.Bytes, off, func(b []byte) { sc0VerifyPutValue(b, 2, other) })
				sc0VerifyAssertState(t, sc0VerifyValidate(e, raw, bad, sc0VerifyOrdinaryGas), 7)
				return
			}
		}
	}
	t.Fatal("no copy constructor source-backing stack snapshot")
}

func TestSC0ParentSeededUTF16ConstructorOracles(t *testing.T) {
	src := `public class SPVectors {public static int run(int a,int b,int c,int d){char[] x={(char)a,(char)b,(char)c,(char)d};String s=new String(x);x[0]++;String copy=new String(s);s.intern();return s.hashCode()+s.charAt(0)+(copy.intern()==s?17:99);}public static void main(String[] a){for(int i=0;i<a.length;i+=4)System.out.println(run(Integer.parseInt(a[i]),Integer.parseInt(a[i+1]),Integer.parseInt(a[i+2]),Integer.parseInt(a[i+3])));}}`
	cs := sc0VerifyCompileTrusted(t, map[string]string{"SPVectors.java": src}, []string{"SPVectors"})
	raw := sc0VerifyRaw(cs, "SPVectors")
	vectors := [][4]int32{{0, 0, 0, 0}, {0xd800, 0, 0xdc00, 65535}, {0xd83d, 0xde00, 1, 0xffff}, {65535, 65535, 65535, 65535}}
	rng := rand.New(rand.NewSource(0x5c032))
	for len(vectors) < 32 {
		vectors = append(vectors, [4]int32{int32(rng.Uint32()), int32(rng.Uint32()), int32(rng.Uint32()), int32(rng.Uint32())})
	}
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "SPVectors.class"), raw[0], 0600); err != nil {
		t.Fatal(err)
	}
	argv := []string{"-Xverify:all", "-cp", dir, "SPVectors"}
	for _, v := range vectors {
		for _, n := range v {
			argv = append(argv, strconv.FormatInt(int64(n), 10))
		}
	}
	var oracle []string
	for _, java := range []string{"/usr/lib/jvm/java-8-openjdk/bin/java", "java"} {
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		out, err := exec.CommandContext(ctx, java, argv...).CombinedOutput()
		cancel()
		if err != nil {
			t.Fatalf("%s: %v %s", java, err, out)
		}
		lines := strings.Fields(string(out))
		if len(lines) != len(vectors) {
			t.Fatal("oracle vector count")
		}
		if oracle == nil {
			oracle = lines
		} else if strings.Join(lines, ",") != strings.Join(oracle, ",") {
			t.Fatal("Java8/21 disagree")
		}
	}
	e := sc0VerifyNewEnv(t)
	defer e.close()
	for i, v := range vectors {
		want, err := strconv.ParseInt(oracle[i], 10, 32)
		if err != nil {
			t.Fatal(err)
		}
		var root [32]byte
		for _, q := range []uint64{4096, 7} {
			id := sc0VerifyInstance(fmt.Sprintf("utf16-%d-%d", i, q))
			s, b, c := e.start(sc0VerifyOwner, id, raw, "SPVectors", "run", v[:], q, 4096, sc0VerifyOrdinaryGas)
			sc0VerifyAssertSuccess(t, s, b, c)
			for slices := 1; s.Lifecycle == 1; slices++ {
				if slices >= 256 {
					t.Fatal("vector slice cap")
				}
				s, b, c = e.resume(sc0VerifyOwner, id, s.Epoch, sc0VerifySliceRoot(s), raw, b, q, 4096, sc0VerifyOrdinaryGas)
				sc0VerifyAssertSuccess(t, s, b, c)
			}
			if s.Lifecycle != 2 || s.Result != int32(want) {
				t.Fatalf("vector%d q%d got %+v want%d", i, q, s, want)
			}
			if q == 4096 {
				root = s.MachineStateRoot
			} else if root != s.MachineStateRoot {
				t.Fatal("quantum changed terminal state")
			}
		}
	}
}

func TestSC0ParentLargeCopyAcrossManySlices(t *testing.T) {
	// Each call is bounded, but the full copy is larger than one4096-unit slice.
	src := `public class SPLarge {public static int run(){char[] a=new char[2048];for(int i=0;i<a.length;i++)a[i]=(char)(i*31);String s=new String(a);a[1023]=0;return s.length()+s.charAt(1023);}}`
	cs := sc0VerifyCompileTrusted(t, map[string]string{"SPLarge.java": src}, []string{"SPLarge"})
	raw := sc0VerifyRaw(cs, "SPLarge")
	e := sc0VerifyNewEnv(t)
	defer e.close()
	var root [32]byte
	for _, q := range []uint64{4096, 1024} {
		r := sc0VerifyRunToEnd(t, e, fmt.Sprintf("large-copy-%d", q), raw, "SPLarge", "run", q, 4096, sc0VerifyBoundaryGas, 65536)
		sc0VerifyRequireReturned(t, r, 33761)
		if q == 4096 {
			root = r.slice.MachineStateRoot
		} else if root != r.slice.MachineStateRoot {
			t.Fatal("large-copy state mismatch")
		}
		t.Logf("q=%d slices=%d jvm=%d checkpoint=%d", q, len(r.snaps), r.slice.TotalJvmSteps, len(r.blob))
	}
}

func TestSC0ParentConstructorFieldWritesKeepOwnReceiver(t *testing.T) {
	for _, tc := range []struct {
		name, expression string
		pc               uint32
		want             int32
	}{{"chars", "new String(new char[]{'x','y'})", 31, 2}, {"copy", "new String(\"source\")", 9, 6}} {
		t.Run(tc.name, func(t *testing.T) {
			src := fmt.Sprintf("public class SPWrite {static String other=\"other\";public static int run(){return %s.length();}}", tc.expression)
			cs := sc0VerifyCompileTrusted(t, map[string]string{"SPWrite.java": src}, []string{"SPWrite"})
			raw := sc0VerifyRaw(cs, "SPWrite")
			e := sc0VerifyNewEnv(t)
			defer e.close()
			r := sc0VerifyRunToEnd(t, e, "field-write-"+tc.name, raw, "SPWrite", "run", 1, 1, sc0VerifyOrdinaryGas, 4096)
			sc0VerifyRequireReturned(t, r, tc.want)
			for _, cp := range r.snaps {
				for _, f := range cp.Machine.Frames {
					if f.Class != sc0VerifyStringClass(raw) || f.PC != tc.pc || len(f.StackOffsets) != 2 {
						continue
					}
					for _, s := range sc0VerifyObject(cp, sc0VerifyStringClass(raw)) {
						if s.Handle == f.This {
							continue
						}
						bad := sc0VerifyMutateRehash(t, cp.Bytes, f.StackOffsets[0], func(b []byte) { sc0VerifyPutValue(b, 2, uint64(s.Handle)) })
						sc0VerifyAssertState(t, sc0VerifyValidate(e, raw, bad, sc0VerifyOrdinaryGas), 7)
						return
					}
				}
			}
			t.Fatal("missing constructor field-write snapshot")
		})
	}
}

func TestSC0ParentNullConstructorCannotLosePendingFault(t *testing.T) {
	for _, typ := range []string{"char[]", "String"} {
		t.Run(typ, func(t *testing.T) {
			src := fmt.Sprintf("public class SPNull {public static int run(){try{return new String((%s)null).length();}catch(NullPointerException e){return 7;}}}", typ)
			cs := sc0VerifyCompileTrusted(t, map[string]string{"SPNull.java": src}, []string{"SPNull"})
			raw := sc0VerifyRaw(cs, "SPNull")
			e := sc0VerifyNewEnv(t)
			defer e.close()
			r := sc0VerifyRunToEnd(t, e, "null-pending-"+typ, raw, "SPNull", "run", 1, 1, sc0VerifyOrdinaryGas, 4096)
			sc0VerifyRequireReturned(t, r, 7)
			for _, cp := range r.snaps {
				if cp.Machine.PendingActive != 1 || cp.Machine.PendingKind != 6 {
					continue
				}
				bad := sc0VerifyMutateRehash(t, cp.Bytes, cp.Machine.PendingOffset, func(b []byte) { clear(b[:38]) })
				sc0VerifyAssertState(t, sc0VerifyValidate(e, raw, bad, sc0VerifyOrdinaryGas), 7)
				return
			}
			t.Fatal("missing pending constructor NPE")
		})
	}
}

func TestSC0ParentNullConstructorArenaOOMRemainsResumable(t *testing.T) {
	for _, typ := range []string{"char[]", "String"} {
		t.Run(typ, func(t *testing.T) {
			src := fmt.Sprintf("public class SPFull {public static int run(){for(int i=0;i<256;i++){try{int z=0;int q=1/z;}catch(ArithmeticException e){}}try{return new String((%s)null).length();}catch(OutOfMemoryError e){return 77;}}}", typ)
			cs := sc0VerifyCompileTrusted(t, map[string]string{"SPFull.java": src}, []string{"SPFull"})
			raw := sc0VerifyRaw(cs, "SPFull")
			e := sc0VerifyNewEnv(t)
			defer e.close()
			control := sc0VerifyRunToEnd(t, e, "full-null-control-"+typ, raw, "SPFull", "run", 4096, 4096, sc0VerifyBoundaryGas, 65536)
			sc0VerifyRequireReturned(t, control, 77)
			id := sc0VerifyInstance("full-null-pauses-" + typ)
			target := control.slice.TotalJvmSteps - 15
			q := target
			if q > 4096 {
				q = 4096
			}
			s, b, c := e.start(sc0VerifyOwner, id, raw, "SPFull", "run", nil, q, 4096, sc0VerifyBoundaryGas)
			sc0VerifyAssertSuccess(t, s, b, c)
			seen := false
			for slices := 1; ; slices++ {
				cp, err := sc0VerifyDecodeCheckpoint(b)
				if err != nil {
					t.Fatal(err)
				}
				if cp.Machine.PendingActive == 1 && cp.Machine.PendingKind == 7 {
					for _, f := range cp.Machine.Frames {
						if f.Class == sc0VerifyStringClass(raw) {
							seen = true
							sc0VerifyValidateOK(t, e, raw, b)
						}
					}
				}
				if s.Lifecycle != 1 {
					break
				}
				if slices >= 256 {
					t.Fatal("slice cap")
				}
				q = 1
				if s.TotalJvmSteps < target {
					q = target - s.TotalJvmSteps
					if q > 4096 {
						q = 4096
					}
				}
				s, b, c = e.resume(sc0VerifyOwner, id, s.Epoch, sc0VerifySliceRoot(s), raw, b, q, 4096, sc0VerifyBoundaryGas)
				sc0VerifyAssertSuccess(t, s, b, c)
			}
			if !seen || s.Lifecycle != 2 || s.Result != 77 || s.MachineStateRoot != control.slice.MachineStateRoot {
				t.Fatal("null constructor emergency OOM did not resume canonically")
			}
		})
	}
}

func TestSC0ParentFullInternPoolHit(t *testing.T) {
	var src strings.Builder
	src.WriteString("public class SPPool {public static int run(){String s=null;")
	for i := 0; i < 1024; i++ {
		fmt.Fprintf(&src, "s=\"p%04d\";", i)
	}
	src.WriteString("return s.intern()==s?1:0;}}")
	cs := sc0VerifyCompileTrusted(t, map[string]string{"SPPool.java": src.String()}, []string{"SPPool"})
	raw := sc0VerifyRaw(cs, "SPPool")
	e := sc0VerifyNewEnv(t)
	defer e.close()
	control, controlBlob, controlCall := e.start(sc0VerifyOwner, sc0VerifyInstance("full-pool-hit-control"), raw, "SPPool", "run", nil, 4096, 4096, sc0VerifyBoundaryGas)
	sc0VerifyAssertSuccess(t, control, controlBlob, controlCall)
	t.Logf("one-call gas%d bytes%d", sc0VerifyBoundaryGas-controlCall.left, len(controlBlob))
	id := sc0VerifyInstance("full-pool-hit-slices")
	s, b, c := e.start(sc0VerifyOwner, id, raw, "SPPool", "run", nil, 128, 4096, sc0VerifyBoundaryGas)
	for n := 1; n <= 256; n++ {
		if c.err != nil {
			t.Fatalf("slice%d failed %v gas%d", n, c.err, sc0VerifyBoundaryGas-c.left)
		}
		sc0VerifyAssertSuccess(t, s, b, c)
		cp, err := sc0VerifyDecodeCheckpoint(b)
		if err != nil {
			t.Fatal(err)
		}
		t.Logf("epoch%d pool%d gas%d bytes%d", n, len(cp.Machine.InternHandleOffsets), sc0VerifyBoundaryGas-c.left, len(b))
		if s.Lifecycle == 2 {
			if s.Result != 1 || len(cp.Machine.InternHandleOffsets) != 1024 || s.MachineStateRoot != control.MachineStateRoot {
				t.Fatal("full pool hit mismatch")
			}
			sc0VerifyValidateOK(t, e, raw, b)
			return
		}
		s, b, c = e.resume(sc0VerifyOwner, id, s.Epoch, sc0VerifySliceRoot(s), raw, b, 128, 4096, sc0VerifyBoundaryGas)
	}
	t.Fatal("slice cap")
}
