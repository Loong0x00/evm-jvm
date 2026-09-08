// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"encoding/binary"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/crypto"
)

func TestRuntimeM5baScalarLongArithmeticLocalsAndStatics(t *testing.T) {
	classfile := compileJava(t, "RuntimeM5baScalar", `
public class RuntimeM5baScalar {
    static final long CV = 0xfedcba9876543210L;
    static long state;
    static long mix(long a, int distance, long b) {
        long x = (a + b) ^ (a - b) ^ (a * 3L);
        x = ((x << distance) | (x >>> (64 - distance))) & CV;
        state = x;
        return -state;
    }
    static long divide(long a, long b) { return a / b; }
    static long remainder(long a, long b) { return a % b; }
    public static int run(int n) {
        long signed = (long)n;
        long x = mix((signed << 40) | 0x12345678L, n & 63, -1234567890123456789L);
        long q = divide(Long.MIN_VALUE, -1L);
        long r = remainder(Long.MIN_VALUE, -1L);
        if (q != Long.MIN_VALUE || r != 0L) return 1;
        long d = divide(-987654321012345678L, 123456789L);
        long m = remainder(-987654321012345678L, 123456789L);
        if (d * 123456789L + m != -987654321012345678L) return 2;
        long negative = -8L;
        if ((negative >> (n & 3)) >= 0L) return 3;
        return (int)(x ^ (x >>> 32) ^ state ^ (state >>> 32));
    }
}`)
	for _, tc := range []struct {
		arg  int32
		want int32
	}{{0, 8388607}, {1, 1023}, {-1, 524287}, {31, 31}, {63, 524287}} {
		result, err := Run(classfile, "run", []int32{tc.arg}, 60_000_000)
		if err != nil || result.ExceptionClass != "" || result.Value != tc.want {
			t.Fatalf("run(%d) = %+v, %v; want %d", tc.arg, result, err, tc.want)
		}
	}
}

func TestRuntimeM5baLongCallsObjectsFieldsAndInterfaceCount(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"RuntimeM5baIface.java": `
public interface RuntimeM5baIface {
    long MAGIC = 0x1122334455667788L;
    long apply(long x, int n);
    default long twice(long x) { return x + x; }
}`,
		"RuntimeM5baBase.java": `
public class RuntimeM5baBase {
    protected long value;
    RuntimeM5baBase(long value) { this.value = value; }
    long adjust(long x) { return value + x; }
}`,
		"RuntimeM5baImpl.java": `
public class RuntimeM5baImpl extends RuntimeM5baBase implements RuntimeM5baIface {
    RuntimeM5baImpl(long value) { super(value); }
    public long apply(long x, int n) { value += x; return adjust(value) + twice((long)n); }
}`,
		"RuntimeM5baEntry.java": `
public class RuntimeM5baEntry {
    static long direct(long x) { return x ^ RuntimeM5baIface.MAGIC; }
    public static int run(int n) {
        RuntimeM5baIface x = new RuntimeM5baImpl(direct((long)n << 33));
        long out = x.apply(0xfedcba9876543210L, n);
        return (int)(out ^ (out >>> 32));
    }
}`,
	})
	bundle := [][]byte{classes["RuntimeM5baEntry"], classes["RuntimeM5baIface"], classes["RuntimeM5baBase"], classes["RuntimeM5baImpl"]}
	for _, tc := range []struct {
		arg, want int32
	}{{0, -2004318071}, {7, -2004317957}, {-3, 1275092359}} {
		result, err := RunClasses(bundle, "RuntimeM5baEntry", "run", []int32{tc.arg}, 100_000_000)
		if err != nil || result.ExceptionClass != "" || result.Value != tc.want {
			t.Fatalf("run(%d) = %+v, %v; want %d", tc.arg, result, err, tc.want)
		}
	}

	badCountEntry := append([]byte(nil), classes["RuntimeM5baEntry"]...)
	parsed := parseTestClass(t, badCountEntry)
	invokePC := bytes.IndexByte(parsed.methodCode(t, "run"), 0xb9)
	if invokePC < 0 {
		t.Fatal("javac did not emit invokeinterface")
	}
	badCountEntry[parsed.codeOffsets["run"]+invokePC+3] = 3 // receiver + J + I is four words
	badBundle := [][]byte{badCountEntry, classes["RuntimeM5baIface"], classes["RuntimeM5baBase"], classes["RuntimeM5baImpl"]}
	result, err := RunClasses(badBundle, "RuntimeM5baEntry", "run", []int32{1}, 100_000_000)
	assertSolidityError(t, result, err, "CallError(uint256,uint256)", 1, uint64(invokePC))
}

func TestRuntimeM5baAllCategory2StackForms(t *testing.T) {
	template := compileJava(t, "RuntimeM5baStack", `
public class RuntimeM5baStack {
    public static int run() {
        int x = 0;
        for (int i = 0; i < 20; i++) x += i;
        return x;
    }
}`)
	cases := map[string]struct {
		code []byte
		want int32
	}{
		"pop2-category2":            {[]byte{0x0a, 0x58, 0x10, 42, 0xac}, 42},
		"dup2-category2":            {[]byte{0x0a, 0x5c, 0x61, 0x88, 0xac}, 2},
		"dup-x2-long-below":         {[]byte{0x0a, 0x05, 0x5b, 0x57, 0x58, 0xac}, 2},
		"dup2-x1-long-top":          {[]byte{0x05, 0x0a, 0x5d, 0x58, 0x57, 0x88, 0xac}, 1},
		"dup2-x2-two-longs":         {[]byte{0x0a, 0x0a, 0x5e, 0x61, 0x61, 0x88, 0xac}, 3},
		"dup2-x2-cat1-cat1-long":    {[]byte{0x05, 0x06, 0x0a, 0x5e, 0x58, 0x60, 0x57, 0x88, 0xac}, 1},
		"dup2-x2-long-cat1-cat1":    {[]byte{0x0a, 0x05, 0x06, 0x5e, 0x60, 0x57, 0x58, 0x60, 0xac}, 5},
		"dup2-x2-four-category-one": {[]byte{0x04, 0x05, 0x06, 0x07, 0x5e, 0x60, 0x60, 0x60, 0x60, 0x60, 0xac}, 17},
	}
	for name, tc := range cases {
		t.Run(name, func(t *testing.T) {
			classfile := runtimeM5baReplaceMethodCode(t, template, "run", tc.code, 16, 16)
			result, err := Run(classfile, "run", nil, 15_000_000)
			if err != nil || result.ExceptionClass != "" || result.Value != tc.want {
				t.Fatalf("result/error = %+v/%v, want %d", result, err, tc.want)
			}
		})
	}
}

func TestRuntimeM5baCategoryAndLocalValidationCodes(t *testing.T) {
	template := compileJava(t, "RuntimeM5baInvalid", `
public class RuntimeM5baInvalid {
    public static int run() {
        int x = 0;
        for (int i = 0; i < 20; i++) x += i;
        return x;
    }
}`)
	cases := map[string]struct {
		code       []byte
		maxStack   uint16
		maxLocals  uint16
		codeNumber uint64
		pc         uint64
	}{
		"pop-long":                {[]byte{0x0a, 0x57, 0x03, 0xac}, 2, 1, 14, 1},
		"pop2-cat1-over-long":     {[]byte{0x0a, 0x04, 0x58, 0x03, 0xac}, 3, 1, 14, 2},
		"dup-long":                {[]byte{0x0a, 0x59, 0x58, 0x03, 0xac}, 4, 1, 14, 1},
		"swap-long":               {[]byte{0x0a, 0x04, 0x5f, 0x58, 0x03, 0xac}, 3, 1, 14, 2},
		"dup-x1-underflow":        {[]byte{0x04, 0x5a, 0xac}, 2, 1, 3, 1},
		"dup2-x1-long-below":      {[]byte{0x0a, 0x04, 0x5d, 0x03, 0xac}, 5, 1, 14, 2},
		"dup2-x2-long-in-pair":    {[]byte{0x0a, 0x04, 0x5e, 0x03, 0xac}, 5, 1, 14, 2},
		"dup2-x2-underflow":       {[]byte{0x04, 0x5e, 0xac}, 3, 1, 3, 1},
		"i2l-capacity":            {[]byte{0x03, 0x85, 0x88, 0xac}, 1, 1, 9, 1},
		"dup2-capacity":           {[]byte{0x0a, 0x5c, 0x61, 0x88, 0xac}, 2, 1, 9, 1},
		"long-local-out-of-range": {[]byte{0x0a, 0x40, 0x03, 0xac}, 2, 2, 8, 1},
		"tail-is-not-long-head":   {[]byte{0x0a, 0x40, 0x20, 0x88, 0xac}, 2, 4, 14, 2},
		"store-over-former-tail":  {[]byte{0x0a, 0x40, 0x05, 0x3d, 0x1f, 0x88, 0xac}, 2, 3, 11, 4},
		"store-over-former-head":  {[]byte{0x0a, 0x40, 0x05, 0x3c, 0x1f, 0x88, 0xac}, 2, 3, 14, 4},
	}
	for name, tc := range cases {
		t.Run(name, func(t *testing.T) {
			classfile := runtimeM5baReplaceMethodCode(
				t, template, "run", tc.code, tc.maxStack, tc.maxLocals,
			)
			result, err := Run(classfile, "run", nil, 15_000_000)
			assertSolidityError(
				t, result, err, "BytecodeError(uint256,uint256)", tc.codeNumber, tc.pc,
			)
		})
	}
}

func TestRuntimeM5baConstantPoolKindsRootAndArithmeticException(t *testing.T) {
	template := compileJava(t, "RuntimeM5baConstants", `
public class RuntimeM5baConstants {
    static final long L = 0x1020304050607080L;
    static final double D = 1.25d;
    public static int run() {
        int x = 0;
        for (int i = 0; i < 20; i++) x += i;
        return x;
    }
}`)
	parsed := parseTestClass(t, template)
	var longIndex, doubleIndex int
	for i, tag := range parsed.tags {
		if tag == 5 && longIndex == 0 {
			longIndex = i
		}
		if tag == 6 && doubleIndex == 0 {
			doubleIndex = i
		}
	}
	if longIndex == 0 || doubleIndex == 0 || longIndex+1 >= len(parsed.tags) || parsed.tags[longIndex+1] != 0 {
		t.Fatalf("unexpected CP tags: long=%d double=%d tags=%v", longIndex, doubleIndex, parsed.tags)
	}
	cases := map[string]struct {
		code     []byte
		kind, pc uint64
	}{
		// CONSTANT_Double is now a valid ldc2_w operand, but l2i must reject
		// consuming its distinct double value kind.
		"ldc2-double-then-l2i": {[]byte{0x14, byte(doubleIndex >> 8), byte(doubleIndex), 0x88, 0xac}, 14, 3},
		"ldc2-hole":            {[]byte{0x14, byte((longIndex + 1) >> 8), byte(longIndex + 1), 0x88, 0xac}, 13, 0},
		"ldc-long":             {[]byte{0x12, byte(longIndex), 0xac}, 13, 0},
	}
	for name, tc := range cases {
		t.Run(name, func(t *testing.T) {
			classfile := runtimeM5baReplaceMethodCode(t, template, "run", tc.code, 4, 1)
			result, err := Run(classfile, "run", nil, 15_000_000)
			assertSolidityError(t, result, err, "BytecodeError(uint256,uint256)", tc.kind, tc.pc)
		})
	}

	longRoot := compileJava(t, "RuntimeM5baLongRoot", `
public class RuntimeM5baLongRoot { public static long run(int x) { return (long)x; } }
`)
	result, err := Run(longRoot, "run", []int32{1}, 15_000_000)
	runtimeM5baAssertMethodError(t, result, err, 11)

	divide := compileJava(t, "RuntimeM5baDivide", `
public class RuntimeM5baDivide {
    static long divide(long x) { return Long.MIN_VALUE / x; }
    public static int run(int x) { return (int)divide((long)x); }
}`)
	result, err = Run(divide, "run", []int32{0}, 20_000_000)
	if err != nil || result.ExceptionClass != "java.lang.ArithmeticException" {
		t.Fatalf("divide by zero = %+v/%v, want ArithmeticException", result, err)
	}
}

func TestRuntimeM5baInitializerReplayPreservesLongPrefix(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"RuntimeM5baInitValue.java": `
public class RuntimeM5baInitValue {
    static long x = init();
    static long init() { return 0x1020304050607080L; }
}`,
		"RuntimeM5baInitEntry.java": `
public class RuntimeM5baInitEntry {
    public static int run() {
        long x = 0xfedcba9876543210L + RuntimeM5baInitValue.x;
        return (int)(x ^ (x >>> 32));
    }
}`,
	})
	result, err := RunClasses(
		[][]byte{classes["RuntimeM5baInitEntry"], classes["RuntimeM5baInitValue"]},
		"RuntimeM5baInitEntry", "run", nil, 50_000_000,
	)
	if err != nil || result.ExceptionClass != "" || result.Value != -934787000 {
		t.Fatalf("initializer replay result/error = %+v/%v", result, err)
	}

	failing := compileJava(t, "RuntimeM5baFailingInit", `
public class RuntimeM5baFailingInit {
    static int zero() { return 0; }
    static long value = 1L / (long)zero();
    public static int run() { return (int)value; }
}`)
	result, err = Run(failing, "run", nil, 30_000_000)
	if err != nil || result.ExceptionClass != "java.lang.ExceptionInInitializerError" {
		t.Fatalf("failing long initializer = %+v/%v, want EIIE", result, err)
	}
}

func runtimeM5baAssertMethodError(t *testing.T, result Result, err error, code uint64) {
	t.Helper()
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error = %+v/%v, want MethodError revert", result, err)
	}
	selector := crypto.Keccak256([]byte("MethodError(uint256)"))[:4]
	if len(result.RevertData) != 36 || !bytes.Equal(result.RevertData[:4], selector) {
		t.Fatalf("revert data = 0x%x, want exact MethodError payload", result.RevertData)
	}
	if got := binary.BigEndian.Uint64(result.RevertData[28:36]); got != code {
		t.Fatalf("MethodError code = %d, want %d", got, code)
	}
}

func runtimeM5baReplaceMethodCode(
	t *testing.T, classfile []byte, method string, code []byte, maxStack, maxLocals uint16,
) []byte {
	t.Helper()
	parsed := parseTestClass(t, classfile)
	off, ok := parsed.codeOffsets[method]
	if !ok {
		t.Fatalf("method %q has no Code", method)
	}
	length := parsed.codeLengths[method]
	if len(code) > length {
		t.Fatalf("replacement code length %d exceeds available %d", len(code), length)
	}
	out := append([]byte(nil), classfile...)
	for i := 0; i < length; i++ {
		out[off+i] = 0x00
	}
	copy(out[off:], code)
	binary.BigEndian.PutUint16(out[off-8:], maxStack)
	binary.BigEndian.PutUint16(out[off-6:], maxLocals)
	return out
}
