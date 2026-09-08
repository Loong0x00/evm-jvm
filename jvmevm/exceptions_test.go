// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"testing"

	"github.com/ethereum/go-ethereum/crypto"
)

func runtimeM5daRun(t *testing.T, class []byte, method string, args []int32, gas uint64) Result {
	t.Helper()
	result, err := Run(class, method, args, gas)
	if err != nil {
		t.Fatalf("Run(%s) failed: %v (result=%+v)", method, err, result)
	}
	return result
}

func TestRuntimeM5daOrderedCatchAndRethrow(t *testing.T) {
	class := compileJava(t, "M5daCatch", `
public class M5daCatch {
    static int divide(int x) { return 100 / x; }
    public static int caught(int x) {
        try { return divide(x); }
        catch (ArithmeticException e) { return e == null ? -1 : 41; }
    }
    public static int rethrow(int x) {
        try {
            try { return divide(x); }
            catch (RuntimeException e) { throw e; }
        } catch (Throwable t) { return t == null ? -1 : 42; }
    }
}`)
	for method, want := range map[string]int32{"caught": 41, "rethrow": 42} {
		result := runtimeM5daRun(t, class, method, []int32{0}, 20_000_000)
		if result.Value != want || result.ExceptionClass != "" {
			t.Fatalf("%s = %+v, want %d", method, result, want)
		}
		t.Logf("%s gas=%d", method, result.GasUsed)
	}
}

func TestRuntimeM5daUserThrowableCatchAllowedButConstructionRejected(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"M5daUserRoot.java": `
public class M5daUserRoot {
    static int fail() { return 1 / 0; }
    public static int run(int x) {
        try { return fail(); }
        catch (M5daUserThrowable notThisSubtype) { return -1; }
        catch (ArithmeticException e) { return 12; }
    }
    public static int allocate(int x) { return new M5daUserThrowable() == null ? 0 : 1; }
}`,
		"M5daUserThrowable.java": `public class M5daUserThrowable extends RuntimeException {}`,
	})
	bundle := [][]byte{classes["M5daUserRoot"], classes["M5daUserThrowable"]}
	result, err := RunClasses(bundle, "M5daUserRoot", "run", []int32{0}, 20_000_000)
	if err != nil || result.Value != 12 || result.ExceptionClass != "" {
		t.Fatalf("catch result/error = %+v/%v, want 12", result, err)
	}
	failed, err := RunClasses(bundle, "M5daUserRoot", "allocate", []int32{0}, 20_000_000)
	selector := crypto.Keccak256([]byte("ObjectError(uint256,uint256)"))[:4]
	if err == nil || len(failed.RevertData) != 68 ||
		!bytes.Equal(failed.RevertData[:4], selector) || failed.RevertData[35] != 2 {
		t.Fatalf("construction result/error = %+v/%v, want ObjectError(2,pc)", failed, err)
	}
}

func TestRuntimeM5daApplicableCatchResolutionIsLazyAndOrdered(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"M5daLazy.java": `
public class M5daLazy {
    public static int run(int x) {
        try { if (x == 0) return 7; return 1 / (x - 1); }
        catch (M5daMissing first) { return -1; }
        catch (ArithmeticException later) { return 8; }
    }
}`,
		"M5daMissing.java": `public class M5daMissing extends RuntimeException {}`,
	})
	ok := runtimeM5daRun(t, classes["M5daLazy"], "run", []int32{0}, 10_000_000)
	if ok.Value != 7 || ok.ExceptionClass != "" {
		t.Fatalf("unreached missing catch result = %+v, want 7", ok)
	}
	failed, err := Run(classes["M5daLazy"], "run", []int32{1}, 10_000_000)
	selector := crypto.Keccak256([]byte("HandlerError(uint256,uint256,uint256,uint256)"))[:4]
	if err == nil || len(failed.RevertData) != 132 || !bytes.Equal(failed.RevertData[:4], selector) {
		t.Fatalf("applicable missing catch result/error = %+v/%v, want HandlerError", failed, err)
	}
	if failed.RevertData[35] != 5 { // first uint256 argument is the frozen HandlerError code
		t.Fatalf("HandlerError payload = 0x%x, want code 5", failed.RevertData)
	}
}

func TestRuntimeM5daInvokeFaultPCStackClearAndWideLocals(t *testing.T) {
	class := compileJava(t, "M5daUnwind", `
public class M5daUnwind {
    static int divide(int x) { return 100 / x; }
    public static int run(int x) {
        long l = 0x1122334455667788L;
        double d = 3.5;
        float f = -2.25f;
        try { return 7 + divide(x); }
        catch (ArithmeticException exact) {
            return l == 0x1122334455667788L && d == 3.5 && f == -2.25f && exact != null ? 55 : -1;
        }
        catch (RuntimeException later) { return -2; }
    }
}`)
	result := runtimeM5daRun(t, class, "run", []int32{0}, 30_000_000)
	if result.Value != 55 || result.ExceptionClass != "" {
		t.Fatalf("result = %+v, want 55", result)
	}
}

func TestRuntimeM5daAllImplicitRuntimeFaultsAreCatchable(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"M5daFaults.java": `
public class M5daFaults {
    int field;
    static int nase() { try { int[] a = new int[-1]; return a.length; }
        catch (NegativeArraySizeException e) { return 1; } }
    static int bounds() { try { int[] a = new int[1]; return a[2]; }
        catch (ArrayIndexOutOfBoundsException e) { return 2; } }
    static int npe() { try { M5daFaults f = null; return f.field; }
        catch (NullPointerException e) { return 4; } }
    static int cast() { try { return ((M5daChild)(Object)new M5daBase()).v; }
        catch (ClassCastException e) { return 8; } }
    static int store() { try { M5daBase[] a = new M5daChild[1]; a[0] = new M5daBase(); return 0; }
        catch (ArrayStoreException e) { return 16; } }
    public static int run(int x) { return nase() + bounds() + npe() + cast() + store(); }
}`,
		"M5daBase.java":  `class M5daBase { int v; }`,
		"M5daChild.java": `class M5daChild extends M5daBase {}`,
	})
	result, err := RunClasses([][]byte{classes["M5daFaults"], classes["M5daBase"], classes["M5daChild"]},
		"M5daFaults", "run", []int32{0}, 40_000_000)
	if err != nil || result.Value != 31 || result.ExceptionClass != "" {
		t.Fatalf("result/error = %+v/%v, want 31", result, err)
	}
}

func TestRuntimeM5daCapturedIdentitySurvivesHeapTransport(t *testing.T) {
	class := compileJava(t, "M5daIdentity", `
public class M5daIdentity {
    static int fail() { return 1 / 0; }
    public static int run(int x) {
        Throwable saved = null;
        Object[] box = new Object[1];
        try { fail(); } catch (ArithmeticException e) { saved = e; box[0] = e; }
        if (saved != box[0] || !(box[0] instanceof ArithmeticException)) return -1;
        try { throw (ArithmeticException)box[0]; }
        catch (RuntimeException same) { return same == saved ? 77 : -2; }
    }
}`)
	result := runtimeM5daRun(t, class, "run", []int32{0}, 30_000_000)
	if result.Value != 77 || result.ExceptionClass != "" {
		t.Fatalf("result = %+v, want 77", result)
	}
}

func TestRuntimeM5daConstructorAbruptExitAndPostSuperCatch(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"M5daCtorRoot.java": `
public class M5daCtorRoot {
    public static int run(int x) {
        int n = new M5daCtorCaught().value;
        try { new M5daCtorFails(); }
        catch (ArithmeticException e) { return e == null ? -1 : n + 2; }
        return -2;
    }
}`,
		"M5daCtorCaught.java": `
class M5daCtorCaught {
    int value;
    static int fail() { return 1 / 0; }
    M5daCtorCaught() { super(); try { value = fail(); } catch (ArithmeticException e) { value = 40; } }
}`,
		"M5daCtorFails.java": `
class M5daCtorFails {
    static int fail() { return 1 / 0; }
    M5daCtorFails() { super(); fail(); }
}`,
	})
	bundle := [][]byte{classes["M5daCtorRoot"], classes["M5daCtorCaught"], classes["M5daCtorFails"]}
	result, err := RunClasses(bundle, "M5daCtorRoot", "run", []int32{0}, 40_000_000)
	if err != nil || result.Value != 42 || result.ExceptionClass != "" {
		t.Fatalf("result/error = %+v/%v, want 42", result, err)
	}
}

func TestRuntimeM5daInitializationFailureThenNCDFE(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"M5daInitRoot.java": `
public class M5daInitRoot {
    public static int run(int x) {
        int seen = 0;
        try { seen += M5daBadInit.value; }
        catch (ExceptionInInitializerError e) { seen = e == null ? -100 : 10; }
        try { seen += M5daBadInit.value; }
        catch (NoClassDefFoundError e) { return e == null ? -200 : seen + 20; }
        return -1;
    }
}`,
		"M5daBadInit.java": `
public class M5daBadInit {
    static int fail() { return 1 / 0; }
    static int value = fail();
}`,
	})
	result, err := RunClasses([][]byte{classes["M5daInitRoot"], classes["M5daBadInit"]},
		"M5daInitRoot", "run", []int32{0}, 40_000_000)
	if err != nil || result.Value != 30 || result.ExceptionClass != "" {
		t.Fatalf("result/error = %+v/%v, want 30", result, err)
	}
	t.Logf("gas=%d", result.GasUsed)
}

func TestRuntimeM5daRootInitializationIsOutsideEntryHandlers(t *testing.T) {
	class := compileJava(t, "M5daRootInit", `
public class M5daRootInit {
    static int fail() { return 1 / 0; }
    static int value = fail();
    public static int run(int x) {
        try { return value; }
        catch (Throwable impossible) { return 99; }
    }
}`)
	result, err := Run(class, "run", []int32{0}, 20_000_000)
	if err != nil || result.ExceptionClass != "java.lang.ExceptionInInitializerError" {
		t.Fatalf("result/error = %+v/%v, want uncaught EIIE", result, err)
	}
}

func TestRuntimeM5daInitializerCanCatchAndComplete(t *testing.T) {
	class := compileJava(t, "M5daCaughtInit", `
public class M5daCaughtInit {
    static int value;
    static int fail() { return 1 / 0; }
    static { try { value = fail(); } catch (ArithmeticException e) { value = 9; } }
    public static int run(int x) { return value; }
}`)
	result := runtimeM5daRun(t, class, "run", []int32{0}, 30_000_000)
	if result.Value != 9 || result.ExceptionClass != "" {
		t.Fatalf("result = %+v, want 9", result)
	}
}

func TestRuntimeM5daFrameCapRaisesCatchableSOE(t *testing.T) {
	class := compileJava(t, "M5daSOE", `
public class M5daSOE {
    static int recurse(int n) {
        try { return recurse(n + 1); }
        catch (StackOverflowError e) { return e == null ? -1 : n; }
    }
    public static int run(int x) { return recurse(1); }
}`)
	result := runtimeM5daRun(t, class, "run", []int32{0}, 100_000_000)
	if result.Value <= 100 || result.Value >= 128 || result.ExceptionClass != "" {
		t.Fatalf("result = %+v, want caller-local depth near the 128-frame cap", result)
	}
	t.Logf("gas=%d depth=%d", result.GasUsed, result.Value)
}

func TestRuntimeM5daArenaExhaustionAndRethrow(t *testing.T) {
	class := compileJava(t, "M5daArena", `
public class M5daArena {
    static int fail() { return 1 / 0; }
    public static int run(int x) {
        ArithmeticException saved = null;
        for (int i = 0; i < 256; i++) {
            try { fail(); }
            catch (ArithmeticException e) { if (i == 255) saved = e; }
        }
        try { fail(); }
        catch (OutOfMemoryError exhausted) {
            try { throw saved; }
            catch (ArithmeticException same) { return same == saved ? 256 : -2; }
        }
        return -1;
    }
}`)
	result := runtimeM5daRun(t, class, "run", []int32{0}, 250_000_000)
	if result.Value != 256 || result.ExceptionClass != "" {
		t.Fatalf("result = %+v, want 256", result)
	}
	t.Logf("gas=%d", result.GasUsed)
}

func TestRuntimeM5daOrdinaryHeapFullOOMIsCatchable(t *testing.T) {
	class := compileJava(t, "M5daHeapOOM", `
public class M5daHeapOOM {
    public static int run(int x) {
        try { Object keep = null; for (int i = 0; i < 1025; i++) keep = new int[0]; }
        catch (OutOfMemoryError e) { return e == null ? -1 : 1024; }
        return -2;
    }
}`)
	result := runtimeM5daRun(t, class, "run", []int32{0}, 250_000_000)
	if result.Value != 1024 || result.ExceptionClass != "" {
		t.Fatalf("result = %+v, want 1024", result)
	}
	t.Logf("gas=%d", result.GasUsed)
}

func TestRuntimeM5daNullAthrowIsCatchable(t *testing.T) {
	class := compileJava(t, "M5daNullThrow", `
public class M5daNullThrow {
    public static int run(int x) {
        try { throw null; }
        catch (NullPointerException e) { return e == null ? -1 : 7; }
    }
}`)
	result := runtimeM5daRun(t, class, "run", []int32{0}, 20_000_000)
	if result.Value != 7 || result.ExceptionClass != "" {
		t.Fatalf("result = %+v, want 7", result)
	}
	t.Logf("gas=%d", result.GasUsed)
}
