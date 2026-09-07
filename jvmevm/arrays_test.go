// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"encoding/binary"
	"strings"
	"testing"
)

func TestRuntimeM4aArrayBasicsAliasingIdentityAndHelpers(t *testing.T) {
	classfile := compileJava(t, "Arrays", `
public class Arrays {
    static int[] saved;
    static int[] make(int n) { return new int[n]; }
    static int sum(int[] a) { int s = 0; for (int i = 0; i < a.length; i++) s += a[i]; return s; }
    static void fill(int[] a, int seed) { for (int i = 0; i < a.length; i++) a[i] = seed + i; }
    static int same(int[] a, int[] b) { return a == b ? 1 : 0; }
    static int nullness(int[] a) { return a == null ? 1 : (a != null ? 2 : 3); }
    public static int run(int n) {
        int[] a = make(n); int[] alias = a; int[] other = make(n);
        fill(a, 10); saved = alias; saved[0] = saved[0] + 7;
        return sum(a) * 100 + same(a, alias) * 10 + same(a, other)
            + nullness(null) + nullness(a) + other.length;
    }
}`)
	for _, tc := range []struct {
		n, want int32
	}{{1, 1714}, {4, 5317}} {
		result, err := Run(classfile, "run", []int32{tc.n}, 40_000_000)
		if err != nil || result.ExceptionClass != "" || result.Value != tc.want {
			t.Fatalf("run(%d) = %+v/%v, want %d", tc.n, result, err, tc.want)
		}
		t.Logf("run(%d) gas=%d", tc.n, result.GasUsed)
	}
}

func TestRuntimeM4aArrayExpressionsAndInt32Values(t *testing.T) {
	classfile := compileJava(t, "Expressions", `
public class Expressions {
    public static int run(int x) {
        int[] a = new int[3];
        a[0] = x; a[1] = a[0]++; a[2] = ++a[0];
        int y = (a[1] = (a[2] = a[2] + 5));
        return a[0] ^ a[1] ^ a[2] ^ y;
    }
}`)
	code := parseTestClass(t, classfile).methodCode(t, "run")
	for _, op := range []byte{0x5b, 0x5c} { // genuine dup_x2 and dup2 array expression forms
		if !bytes.Contains(code, []byte{op}) {
			t.Fatalf("run bytecode %x does not exercise opcode 0x%02x", code, op)
		}
	}
	for _, x := range []int32{7, 2147483647, -2147483648} {
		want := (x + 2) ^ (x + 7)
		result, err := Run(classfile, "run", []int32{x}, 30_000_000)
		if err != nil || result.Value != want {
			t.Fatalf("run(%d) = %+v/%v, want %d", x, result, err, want)
		}
	}
}

func TestRuntimeM4aStaticHierarchyInitializationAndFreshHeap(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"Root.java": `public class Root {
    public static int run(int x) { int[] local = Child.echo(Base.values); Child.set(local, x); return Base.values[0] + Child.values[1] + Child.inits(); }
}`,
		"Base.java": `public class Base {
    protected static final int[] values = new int[2];
    static { values[0] = 40; }
}`,
		"Child.java": `public class Child extends Base {
    static int count; static { count++; values[1] = 2; }
    static int[] echo(int[] a) { return a; }
    static void set(int[] a, int x) { a[0] += x; }
    static int inits() { return count; }
}`,
	})
	bundle := [][]byte{classes["Child"], classes["Root"], classes["Base"]}
	for invocation := 0; invocation < 2; invocation++ {
		result, err := RunClasses(bundle, "Root", "run", []int32{3}, 60_000_000)
		if err != nil || result.Value != 46 {
			t.Fatalf("invocation %d = %+v/%v, want fresh initialized value 46", invocation, result, err)
		}
	}
}

func TestRuntimeM4aArrayJavaOutcomesAndInitializerWrapping(t *testing.T) {
	classfile := compileJava(t, "Failures", `
public class Failures {
    public static int negative(int n) { return new int[n].length; }
    public static int nullLength(int x) { int[] a = null; return a.length; }
    public static int nullRead(int i) { int[] a = null; return a[i]; }
    public static int nullWrite(int i) { int[] a = null; a[i] = 1; return 0; }
    public static int read(int i) { return (new int[2])[i]; }
    public static int write(int i) { int[] a = new int[2]; a[i] = 1; return 0; }
}`)
	for _, tc := range []struct {
		method string
		arg    int32
		class  string
	}{{"negative", -1, "java.lang.NegativeArraySizeException"},
		{"nullLength", 0, "java.lang.NullPointerException"},
		{"nullRead", -1, "java.lang.NullPointerException"},
		{"nullWrite", 99, "java.lang.NullPointerException"},
		{"read", -1, "java.lang.ArrayIndexOutOfBoundsException"},
		{"read", 2, "java.lang.ArrayIndexOutOfBoundsException"},
		{"write", -1, "java.lang.ArrayIndexOutOfBoundsException"},
		{"write", 2, "java.lang.ArrayIndexOutOfBoundsException"}} {
		t.Run(tc.method, func(t *testing.T) {
			result, err := Run(classfile, tc.method, []int32{tc.arg}, 20_000_000)
			if err != nil || result.ExceptionClass != tc.class {
				t.Fatalf("%s(%d) = %+v/%v, want %s", tc.method, tc.arg, result, err, tc.class)
			}
		})
	}

	for name, source := range map[string]string{
		"InitNegative": `public class InitNegative { static int[] a = new int[-1]; public static int run(){ return 0; } }`,
		"InitBounds":   `public class InitBounds { static int x = (new int[1])[2]; public static int run(){ return 0; } }`,
		"InitNull":     `public class InitNull { static int[] a; static int x = a.length; public static int run(){ return 0; } }`,
	} {
		t.Run(name, func(t *testing.T) {
			cf := compileJava(t, name, source)
			result, err := Run(cf, "run", nil, 20_000_000)
			if err != nil || result.ExceptionClass != "java.lang.ExceptionInInitializerError" {
				t.Fatalf("initializer = %+v/%v, want wrapped EIIE", result, err)
			}
		})
	}
}

func TestRuntimeM4aHeapCapsOOMAndReset(t *testing.T) {
	classfile := compileJava(t, "Caps", `
public class Caps {
    public static int maxArrays() { int[] a = null; for (int i=0; i<1024; i++) a = new int[0]; return a.length; }
    public static int tooManyArrays() { for (int i=0; i<1025; i++) { int[] a = new int[0]; } return 0; }
    public static int maxElements() { int s=0; for (int i=0; i<4; i++) s += new int[65536].length; return s; }
    public static int tooManyElements() { for (int i=0; i<4; i++) { int[] a = new int[65536]; } return new int[1].length; }
    public static int tooLong() { return new int[65537].length; }
    public static int negativeAfterArrayCap() { for (int i=0; i<1024; i++) { int[] a = new int[0]; } return new int[-1].length; }
}`)
	for invocation := 0; invocation < 2; invocation++ {
		result, err := Run(classfile, "maxArrays", nil, 200_000_000)
		if err != nil || result.Value != 0 {
			t.Fatalf("maxArrays invocation %d = %+v/%v", invocation, result, err)
		}
	}
	max, err := Run(classfile, "maxElements", nil, 200_000_000)
	if err != nil || max.Value != 262144 {
		t.Fatalf("maxElements = %+v/%v", max, err)
	}
	negative, err := Run(classfile, "negativeAfterArrayCap", nil, 250_000_000)
	if err != nil || negative.ExceptionClass != "java.lang.NegativeArraySizeException" {
		t.Fatalf("negative-after-cap = %+v/%v, want NASE precedence", negative, err)
	}
	for _, method := range []string{"tooManyArrays", "tooManyElements", "tooLong"} {
		result, err := Run(classfile, method, nil, 250_000_000)
		if err != nil || result.ExceptionClass != "java.lang.OutOfMemoryError" {
			t.Fatalf("%s = %+v/%v, want OOM", method, result, err)
		}
	}
	initOOM := compileJava(t, "InitOOM", `public class InitOOM {
    static { for (int i=0; i<1025; i++) { int[] a = new int[0]; } }
    public static int run(){ return 0; }
}`)
	oom, err := Run(initOOM, "run", nil, 250_000_000)
	if err != nil || oom.ExceptionClass != "java.lang.OutOfMemoryError" {
		t.Fatalf("initializer OOM = %+v/%v, want unwrapped OOM", oom, err)
	}
}

func TestRuntimeM4aCategory1PermutationOrderAndKinds(t *testing.T) {
	base := compileJava(t, "Permutation", `public class Permutation { public static int run(int x) {
        x=x+1;x=x+2;x=x+3;x=x+4;x=x+5;x=x+6;x=x+7;x=x+8;x=x+9;x=x+10;
        x=x+11;x=x+12;x=x+13;x=x+14;x=x+15;x=x+16;x=x+17;x=x+18;x=x+19;x=x+20; return x; } }`)
	orders := []struct {
		name   string
		op     byte
		inputs int
		want   int32
	}{
		{"dup", 0x59, 1, 11}, {"dup_x1", 0x5a, 2, 212}, {"dup_x2", 0x5b, 3, 3123},
		{"dup2", 0x5c, 2, 1212}, {"dup2_x1", 0x5d, 3, 23123}, {"dup2_x2", 0x5e, 4, 341234}, {"swap", 0x5f, 2, 21},
	}
	for _, tc := range orders {
		t.Run(tc.name+"-order", func(t *testing.T) {
			var seq []byte
			for i := 1; i <= tc.inputs; i++ {
				seq = append(seq, byte(0x03+i))
			}
			seq = append(seq, tc.op)
			outputs := tc.inputs
			if tc.op >= 0x59 && tc.op <= 0x5b {
				outputs++
			} else if tc.op >= 0x5c && tc.op <= 0x5e {
				outputs += 2
			}
			for i := 1; i <= outputs; i++ {
				seq = append(seq, 0x36, byte(i))
			}
			seq = append(seq, 0x15, byte(outputs))
			for i := outputs - 1; i >= 1; i-- {
				seq = append(seq, 0x10, 10, 0x68, 0x15, byte(i), 0x60)
			}
			seq = append(seq, 0xac)
			result, err := Run(runtimeM4aReplaceMethodCode(t, base, "run", seq), "run", []int32{0}, 20_000_000)
			if err != nil || result.Value != tc.want {
				t.Fatalf("result = %+v/%v, want %d", result, err, tc.want)
			}
		})
	}
	mixed := []struct {
		name            string
		op              byte
		initial, output []byte
	}{
		{"dup", 0x59, []byte{2}, []byte{2, 2}},
		{"dup_x1", 0x5a, []byte{2, 1}, []byte{1, 2, 1}},
		{"dup_x2", 0x5b, []byte{2, 1, 2}, []byte{2, 2, 1, 2}},
		{"dup2", 0x5c, []byte{2, 1}, []byte{2, 1, 2, 1}},
		{"dup2_x1", 0x5d, []byte{1, 2, 1}, []byte{2, 1, 1, 2, 1}},
		{"dup2_x2", 0x5e, []byte{2, 1, 2, 1}, []byte{2, 1, 2, 1, 2, 1}},
		{"swap", 0x5f, []byte{2, 1}, []byte{1, 2}},
	}
	for _, tc := range mixed {
		t.Run(tc.name+"-mixed-kinds", func(t *testing.T) {
			var seq []byte
			for _, kind := range tc.initial {
				if kind == 1 {
					seq = append(seq, 0x04)
				} else {
					seq = append(seq, 0x01)
				}
			}
			seq = append(seq, tc.op)
			for i := len(tc.output) - 1; i >= 0; i-- {
				if tc.output[i] == 1 {
					seq = append(seq, 0x36, 1)
				} else {
					seq = append(seq, 0x3a, 1)
				}
			}
			seq = append(seq, 0x10, 7, 0xac)
			result, err := Run(runtimeM4aReplaceMethodCode(t, base, "run", seq), "run", []int32{0}, 20_000_000)
			if err != nil || result.Value != 7 {
				t.Fatalf("mixed result = %+v/%v", result, err)
			}
		})
	}
	pop2 := runtimeM4aReplaceMethodCode(t, base, "run", []byte{0x01, 0x04, 0x58, 0x10, 7, 0xac})
	result, err := Run(pop2, "run", []int32{0}, 20_000_000)
	if err != nil || result.Value != 7 {
		t.Fatalf("mixed pop2 = %+v/%v", result, err)
	}
}

func TestRuntimeM4aExactArrayAndKindValidationErrors(t *testing.T) {
	base := compileJava(t, "InvalidKinds", `public class InvalidKinds { public static int run(int x) { x=x+1;x=x+2;x=x+3;x=x+4;x=x+5;return x; } }`)
	cases := []struct {
		name string
		code []byte
		pc   uint64
	}{
		{"int-as-array", []byte{0x03, 0xbe, 0xac}, 1}, {"ref-as-int", []byte{0x01, 0x04, 0x60, 0xac}, 2},
		{"int-ifnull", []byte{0x03, 0xc6, 0x00, 0x03, 0x03, 0xac}, 1}, {"int-aload", []byte{0x2a, 0xac}, 0},
		{"ref-istore", []byte{0x01, 0x3b, 0x03, 0xac}, 1}, {"int-astore", []byte{0x03, 0x4b, 0x03, 0xac}, 1},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			result, err := Run(runtimeM4aReplaceMethodCode(t, base, "run", tc.code), "run", []int32{0}, 20_000_000)
			assertSolidityError(t, result, err, "BytecodeError(uint256,uint256)", 14, tc.pc)
		})
	}
	array := compileJava(t, "ArrayType", `public class ArrayType { public static int run(int n){return new int[n].length;} }`)
	parsed := parseTestClass(t, array)
	pc := bytes.IndexByte(parsed.methodCode(t, "run"), 0xbc)
	badType := append([]byte(nil), array...)
	badType[parsed.codeOffsets["run"]+pc+1] = 11
	result, err := Run(badType, "run", []int32{1}, 20_000_000)
	assertSolidityError(t, result, err, "ArrayError(uint256,uint256)", 1, uint64(pc))
	truncated := runtimeM4aReplaceMethodCode(t, base, "run", nil)
	truncatedParsed := parseTestClass(t, truncated)
	truncatedPC := truncatedParsed.codeLengths["run"] - 1
	truncated[truncatedParsed.codeOffsets["run"]+truncatedPC] = 0xbc
	result, err = Run(truncated, "run", []int32{0}, 20_000_000)
	assertSolidityError(t, result, err, "BytecodeError(uint256,uint256)", 2, uint64(truncatedPC))
}

func TestRuntimeM4aFinalArrayReferenceAndMutableElements(t *testing.T) {
	classfile := compileJava(t, "FinalArray", `public class FinalArray { static final int[] a=new int[1]; public static int run(int x){a[0]=x;return a[0];} }`)
	result, err := Run(classfile, "run", []int32{99}, 20_000_000)
	if err != nil || result.Value != 99 {
		t.Fatalf("final array element write = %+v/%v", result, err)
	}
	nonfinal := compileJava(t, "Reassign", `public class Reassign { static int[] a; public static int run(int x){a=new int[x];return a.length;} }`)
	mutated := append([]byte(nil), nonfinal...)
	field := parseStaticsClass(t, mutated).field(t, "a", "[I")
	binary.BigEndian.PutUint16(mutated[field.accessOffset:], field.access|accFinal)
	_, putPC := parseStaticsClass(t, mutated).fieldInstruction(t, "run", opPutstatic, 0)
	result, err = Run(mutated, "run", []int32{1}, 20_000_000)
	assertSolidityError(t, result, err, "FieldError(uint256,uint256)", 4, uint64(putPC))
}

func TestRuntimeM4aCallAndReturnKindsAreChecked(t *testing.T) {
	caller := compileJava(t, "TypedCall", `public class TypedCall { static int helper(int x){return x;} public static int run(int x){return helper(x);} }`)
	parsed := parseTestClass(t, caller)
	runCode := parsed.methodCode(t, "run")
	callPC := bytes.IndexByte(runCode, 0xb8)
	if callPC < 1 {
		t.Fatalf("unexpected caller bytecode %x", runCode)
	}
	badCall := append([]byte(nil), caller...)
	badCall[parsed.codeOffsets["run"]] = 0x01
	result, err := Run(badCall, "run", []int32{7}, 20_000_000)
	assertSolidityError(t, result, err, "BytecodeError(uint256,uint256)", 14, uint64(callPC))

	returns := compileJava(t, "TypedReturn", `public class TypedReturn { static int[] helper(){return null;} public static int run(int x){return helper()==null?1:0;} }`)
	retParsed := parseTestClass(t, returns)
	helperCode := retParsed.methodCode(t, "helper")
	if len(helperCode) < 2 || helperCode[0] != 0x01 || helperCode[1] != 0xb0 {
		t.Fatalf("unexpected helper bytecode %x", helperCode)
	}
	badReturn := append([]byte(nil), returns...)
	badReturn[retParsed.codeOffsets["helper"]] = 0x03
	result, err = Run(badReturn, "run", []int32{0}, 20_000_000)
	assertSolidityError(t, result, err, "BytecodeError(uint256,uint256)", 14, 1)
}

func TestRuntimeM4aArrayOutOfGasIsNotJavaOOM(t *testing.T) {
	classfile := compileJava(t, "ArrayOOG", `public class ArrayOOG { public static int run(int x){ return new int[65536].length; } }`)
	result, err := Run(classfile, "run", []int32{0}, 300_000)
	if err == nil || !strings.Contains(err.Error(), "out of gas") || result.ExceptionClass != "" {
		t.Fatalf("array OOG = %+v/%v, want unwrapped EVM OOG", result, err)
	}
}

func TestRuntimeM4aRootReferenceSignaturesRemainRejected(t *testing.T) {
	classfile := compileJava(t, "RootRefs", `
public class RootRefs {
    public static int takes(int[] a) { return a == null ? 1 : 2; }
    public static int[] gives(int x) { return new int[x]; }
}`)
	for _, tc := range []struct {
		method string
		args   []int32
	}{{"takes", []int32{0}}, {"gives", []int32{1}}} {
		result, err := Run(classfile, tc.method, tc.args, 10_000_000)
		assertHeaderProfileMethodError(t, result, err, 11)
	}
}

func runtimeM4aReplaceMethodCode(t *testing.T, classfile []byte, method string, code []byte) []byte {
	t.Helper()
	out := append([]byte(nil), classfile...)
	parsed := parseTestClass(t, out)
	off, length := parsed.codeOffsets[method], parsed.codeLengths[method]
	if len(code) > length {
		t.Fatalf("replacement code length %d exceeds available %d", len(code), length)
	}
	for i := 0; i < length; i++ {
		out[off+i] = 0x00
	}
	copy(out[off:], code)
	binary.BigEndian.PutUint16(out[off-8:], 16)
	binary.BigEndian.PutUint16(out[off-6:], 16)
	return out
}
