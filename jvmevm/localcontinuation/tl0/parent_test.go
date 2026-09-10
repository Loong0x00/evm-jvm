package tl0

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"testing"

	"github.com/ethereum/go-ethereum/crypto"
)

func TestTL0ParentNullAthrowConsumesOperand(t *testing.T) {
	classes := tl0VerifyCompileTrusted(t, map[string]string{"TPNull.java": `public class TPNull {public static int run(){throw null;}}`}, []string{"TPNull"})
	e := tl0VerifyNewEnv(t)
	defer e.close()
	r := tl0VerifyRunToEnd(t, e, "parent-null-consume", tl0VerifyRaw(classes, "TPNull"), "TPNull", "run", 1, 1, tl0VerifyOrdinaryGas, 4096)
	seen := false
	for _, cp := range r.snaps {
		if cp.Machine.PendingActive == 1 && len(cp.Machine.Frames) > 0 {
			seen = true
			f := cp.Machine.Frames[len(cp.Machine.Frames)-1]
			if len(f.StackOffsets) != 0 {
				t.Fatalf("athrow null left %d operands in pending frame", len(f.StackOffsets))
			}
		}
	}
	if !seen {
		t.Fatal("no pending null-athrow checkpoint")
	}
	tl0VerifyRequireUncaught(t, r, 6, "")
}

func TestTL0ParentInvalidAthrowErrorIndependentOfQuantum(t *testing.T) {
	classes := tl0VerifyCompileTrusted(t, map[string]string{"TPBad.java": `public class TPBad {public static int run(){throw null;}}`}, []string{"TPBad"})
	raw := classes["TPBad"]
	if bytes.Count(raw, []byte{1, 0xbf}) != 1 {
		t.Fatal("expected unique aconst_null/athrow Code")
	}
	raw = bytes.Replace(raw, []byte{1, 0xbf}, []byte{3, 0xbf}, 1) // raw unsupported int operand, not a JVM-valid fixture
	for _, q := range []uint64{4096, 1} {
		e := tl0VerifyNewEnv(t)
		_, _, c := e.start(tl0VerifyOwner, tl0VerifyInstance("parent-bad-throw"), [][]byte{raw}, "TPBad", "run", nil, q, 4096, tl0VerifyOrdinaryGas)
		e.close()
		if c.err == nil || len(c.output) != 68 || !bytes.Equal(c.output[:4], crypto.Keccak256([]byte("BytecodeError(uint256,uint256)"))[:4]) || binary.BigEndian.Uint64(c.output[28:36]) != 14 || binary.BigEndian.Uint64(c.output[60:68]) != 1 {
			t.Fatalf("q=%d want BytecodeError(14,1), got %v %x", q, c.err, c.output)
		}
	}
}

func TestTL0ParentEveryCanonicalThrowableOriginAndOutcome(t *testing.T) {
	names := []string{"ArithmeticException", "StackOverflowError", "ExceptionInInitializerError", "NegativeArraySizeException", "ArrayIndexOutOfBoundsException", "NullPointerException", "OutOfMemoryError", "ClassCastException", "ArrayStoreException", "IncompatibleClassChangeError", "AbstractMethodError", "NoClassDefFoundError", "Throwable", "Exception", "RuntimeException", "Error", "LinkageError", "IndexOutOfBoundsException"}
	src := "public class TPKinds {"
	for i, n := range names {
		src += fmt.Sprintf("public static int k%d() throws Throwable {throw new %s();}", i, n)
	}
	src += "}"
	cs := tl0VerifyCompileTrusted(t, map[string]string{"TPKinds.java": src}, []string{"TPKinds"})
	raw := tl0VerifyRaw(cs, "TPKinds")
	e := tl0VerifyNewEnv(t)
	defer e.close()
	for i, n := range names {
		t.Run(n, func(t *testing.T) {
			var control tl0VerifyRun
			for _, q := range []uint64{4096, 1} {
				internal := uint32(4096)
				if q == 1 {
					internal = 1
				}
				r := tl0VerifyRunToEnd(t, e, fmt.Sprintf("all-kinds-%d-%d", i, q), raw, "TPKinds", fmt.Sprintf("k%d", i), q, internal, tl0VerifyOrdinaryGas, 4096)
				kind := uint8(0)
				name := "java/lang/" + n
				if i < 12 {
					kind = uint8(i + 1)
					name = ""
				}
				tl0VerifyRequireUncaught(t, r, kind, name)
				cp := r.snaps[len(r.snaps)-1]
				if cp.Machine.OrdinaryObjects != 1 || cp.Machine.ExceptionObjects != 0 || len(cp.Machine.CauseWrapperOffsets) != 0 {
					t.Fatal("ordinary explicit Throwable changed origin/cause")
				}
				if q == 4096 {
					control = r
				} else if control.slice.MachineStateRoot != r.slice.MachineStateRoot {
					t.Fatal("canonical outcome differs across quanta")
				}
			}
		})
	}
}

func TestTL0ParentSupplementaryClassNameRemainsOpaque(t *testing.T) {
	src := `public class TPNames {static class 𐐀 extends RuntimeException{} public static int run(){throw new 𐐀();}}`
	cs := tl0VerifyCompileTrusted(t, map[string]string{"TPNames.java": src}, []string{"TPNames", "TPNames$𐐀"})
	raw := tl0VerifyRaw(cs, "TPNames", "TPNames$𐐀")
	// CONSTANT_Utf8 uses the two UTF-16 surrogate encodings, not host UTF-8.
	want := append([]byte("TPNames$"), 0xed, 0xa0, 0x81, 0xed, 0xb0, 0x80)
	e := tl0VerifyNewEnv(t)
	defer e.close()
	r := tl0VerifyRunToEnd(t, e, "opaque-name", raw, "TPNames", "run", 1, 1, tl0VerifyOrdinaryGas, 4096)
	tl0VerifyRequireUncaught(t, r, 0, string(want))
	s, err := NewMemory(tl0VerifyOwner)
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()
	result, err := s.Start(tl0VerifyInstance("opaque-transport"), raw, "TPNames", "run", nil, 4096, 4096, tl0VerifyOrdinaryGas)
	if err != nil || !bytes.Equal(result.Slice.JavaClass, want) {
		t.Fatalf("opaque EVM class changed in Go: %+v %v", result.Slice, err)
	}
}

func TestTL0ParentLargeCheckpointValidateRollbackRetry(t *testing.T) {
	cs := tl0VerifyCompileTrusted(t, map[string]string{"TLCap.java": `public final class TLCap {public static int abcdefg(){long[] a=new long[65536];long[] b=new long[65464];return a.length+b.length;}}`}, []string{"TLCap"})
	raw := tl0VerifyRaw(cs, "TLCap")
	e := tl0VerifyNewEnv(t)
	defer e.close()
	id := tl0VerifyInstance("large-retry")
	s, b, c := e.start(tl0VerifyOwner, id, raw, "TLCap", "abcdefg", nil, 3, 4096, tl0VerifyBoundaryGas)
	tl0VerifyAssertSuccess(t, s, b, c)
	before := e.head(id)
	_, _, failed := e.resume(tl0VerifyOwner, id, s.Epoch, tl0VerifySliceRoot(s), raw, b, 3, 4096, tl0VerifyBoundaryGas)
	tl0VerifyAssertState(t, failed, 1, 0)
	tl0VerifyAssertHeadEqual(t, e.head(id), before)
	done, out, retry := e.resume(tl0VerifyOwner, id, s.Epoch, tl0VerifySliceRoot(s), raw, b, 4096, 4096, tl0VerifyBoundaryGas)
	tl0VerifyAssertSuccess(t, done, out, retry)
	if done.Result != 131000 || len(out) != 1<<20 {
		t.Fatal("large retry mismatch")
	}
	validation := tl0VerifyValidate(e, raw, out, tl0VerifyBoundaryGas)
	if validation.err != nil {
		t.Fatalf("exact limit validation: %v %x", validation.err, validation.output)
	}
	t.Logf("parentBytes=%d finalBytes=%d retryGas=%d validationGas=%d", len(b), len(out), tl0VerifyBoundaryGas-retry.left, tl0VerifyBoundaryGas-validation.left)
}

func TestTL0ParentSharedCauseAcrossInitializers(t *testing.T) {
	src := `public class TPShared {static final class P extends RuntimeException{} static P p=new P();static class A{static int x=fail();}static class B{static int x=fail();}static int fail(){throw p;}public static int run(){int n=0;try{n=A.x;}catch(ExceptionInInitializerError e){n++;}try{n=B.x;}catch(ExceptionInInitializerError e){n++;}return n;}}`
	cs := tl0VerifyCompileTrusted(t, map[string]string{"TPShared.java": src}, []string{"TPShared", "TPShared$P", "TPShared$A", "TPShared$B"})
	raw := tl0VerifyRaw(cs, "TPShared", "TPShared$P", "TPShared$A", "TPShared$B")
	e := tl0VerifyNewEnv(t)
	defer e.close()
	var root [32]byte
	for _, q := range []uint64{4096, 1, 7} {
		r := tl0VerifyRunToEnd(t, e, fmt.Sprintf("shared-cause-%d", q), raw, "TPShared", "run", q, 4096, tl0VerifyOrdinaryGas, 4096)
		tl0VerifyRequireReturned(t, r, 2)
		cp := r.snaps[len(r.snaps)-1]
		causes := tl0VerifyCauseMap(cp)
		if len(causes) != 2 {
			t.Fatal("expected two wrappers")
		}
		var shared uint32
		for wrapper, cause := range causes {
			if cause == 0 || cause >= wrapper {
				t.Fatal("cause order")
			}
			if shared == 0 {
				shared = cause
			} else if cause != shared {
				t.Fatal("shared cause identity duplicated")
			}
		}
		if q == 4096 {
			root = r.slice.MachineStateRoot
		} else if root != r.slice.MachineStateRoot {
			t.Fatal("shared cause quantum mismatch")
		}
	}
}

func TestTL0ParentAbstractBootstrapStillRejectsNew(t *testing.T) {
	cs := tl0VerifyCompileTrusted(t, map[string]string{"TPAbstract.java": `public class TPAbstract{public static int run(){throw new RuntimeException();}}`}, []string{"TPAbstract"})
	cpUTF := func(s string) []byte { b := []byte{1, byte(len(s) >> 8), byte(len(s))}; return append(b, []byte(s)...) }
	raw := cs["TPAbstract"]
	old := cpUTF("java/lang/RuntimeException")
	if bytes.Count(raw, old) != 1 {
		t.Fatal("constant-pool target not unique")
	}
	raw = bytes.Replace(raw, old, cpUTF("java/lang/VirtualMachineError"), 1)
	e := tl0VerifyNewEnv(t)
	defer e.close()
	_, _, c := e.start(tl0VerifyOwner, tl0VerifyInstance("abstract-bootstrap"), [][]byte{raw}, "TPAbstract", "run", nil, 4096, 4096, tl0VerifyOrdinaryGas)
	if c.err == nil || len(c.output) != 68 || !bytes.Equal(c.output[:4], crypto.Keccak256([]byte("ObjectError(uint256,uint256)"))[:4]) || binary.BigEndian.Uint64(c.output[28:36]) != 2 {
		t.Fatalf("abstract allocation result %v %x", c.err, c.output)
	}
}

func TestTL0ParentEnvelopeMachineRootErrorOffset(t *testing.T) {
	cs := tl0VerifyCompileTrusted(t, map[string]string{"TPOffset.java": `public class TPOffset {public static int run(){return 7;}}`}, []string{"TPOffset"})
	raw := tl0VerifyRaw(cs, "TPOffset")
	e := tl0VerifyNewEnv(t)
	defer e.close()
	s, b, c := e.start(tl0VerifyOwner, tl0VerifyInstance("header-offset"), raw, "TPOffset", "run", nil, 4096, 4096, tl0VerifyOrdinaryGas)
	tl0VerifyAssertSuccess(t, s, b, c)
	bad := append([]byte(nil), b...)
	bad[180] ^= 1
	tl0VerifyAssertState(t, tl0VerifyValidate(e, raw, bad, tl0VerifyOrdinaryGas), 3, 180)
}

func TestTL0ParentAbstractDynamicHeapClassRejected(t *testing.T) {
	src := `public class TPAbstractState {static abstract class A extends RuntimeException{}static class P extends A{}public static int run(){throw new P();}}`
	cs := tl0VerifyCompileTrusted(t, map[string]string{"TPAbstractState.java": src}, []string{"TPAbstractState", "TPAbstractState$A", "TPAbstractState$P"})
	raw := tl0VerifyRaw(cs, "TPAbstractState", "TPAbstractState$A", "TPAbstractState$P")
	e := tl0VerifyNewEnv(t)
	defer e.close()
	r := tl0VerifyRunToEnd(t, e, "abstract-dynamic", raw, "TPAbstractState", "run", 4096, 4096, tl0VerifyOrdinaryGas, 4096)
	cp := r.snaps[len(r.snaps)-1]
	h, ok := tl0VerifyHeapByRef(cp, r.slice.JavaRef)
	if !ok || h.Class != 2 {
		t.Fatal("expected concrete P instance")
	}
	// Both layouts are empty and both classes have completed initialization, but
	// abstract A cannot be an object's dynamic allocation class.
	bad := tl0VerifyMutateRehash(t, cp.Bytes, h.ClassOffset, func(b []byte) { binary.BigEndian.PutUint16(b, 1) })
	tl0VerifyAssertState(t, tl0VerifyValidate(e, raw, bad, tl0VerifyOrdinaryGas), 6)
}
