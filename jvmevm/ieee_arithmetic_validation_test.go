// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"context"
	"encoding/binary"
	"fmt"
	"math/rand"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"testing"
	"time"

	"github.com/ethereum/go-ethereum/crypto"
)

const (
	verifyM5ccGasLimit       = uint64(220_000_000)
	verifyM5ccSingleGasLimit = uint64(20_000_000)
	verifyM5ccRepeatGasLimit = uint64(100_000_000)
)

// M5c-c oracle use is deliberately confined to these bounded trusted tests.
// Java 8 and the current Java 21 VM independently execute the unchanged class.
// Only the result of an arithmetic opcode is canonicalized when it is a NaN;
// finite values, infinities, and both zero signs remain exact raw bits. No
// signaling-NaN transport portability is claimed here (M5c-b covers EVM-only
// raw transport separately).

func TestVerifyM5ccArithmeticBytecodesAreDynamicAndUncoalesced(t *testing.T) {
	classfile := verifyM5ccArithmeticClass(t)
	parsed := parseStaticsClass(t, classfile)
	for method, opcode := range map[string]byte{
		"fadd": 0x62, "fsub": 0x66, "fmul": 0x6a, "fdiv": 0x6e, "frem": 0x72,
		"dadd0": 0x63, "dsub0": 0x67, "dmul0": 0x6b, "ddiv0": 0x6f, "drem0": 0x73,
	} {
		if got := verifyM5ccOpcodeCount(t, parsed.namedMethod(t, method).code, opcode); got != 1 {
			t.Fatalf("%s contains %d opcode 0x%02x, want exactly one dynamic operation", method, got, opcode)
		}
	}
	if got := verifyM5ccOpcodeCount(t, parsed.method(t, "repeatDrem16", "(IIII)I").code, 0x73); got != 16 {
		t.Fatalf("repeatDrem16 contains %d drem opcodes, want 16", got)
	}
}

func TestVerifyM5ccCriticalExactBitPatterns(t *testing.T) {
	classfile := verifyM5ccArithmeticClass(t)
	oracle := verifyM5ccNewOracle(t, classfile)
	floats := []struct {
		name, method string
		a, b         uint32
		want         uint32
	}{
		{"add-half-even", "fadd", 0x3f800000, 0x33800000, 0x3f800000},
		{"add-half-odd-rounds-up", "fadd", 0x3f800001, 0x33800000, 0x3f800002},
		{"add-exact-cancel-positive-zero", "fadd", 0x3f800000, 0xbf800000, 0x00000000},
		{"add-two-negative-zeros", "fadd", 0x80000000, 0x80000000, 0x80000000},
		{"add-subnormal-to-min-normal", "fadd", 0x007fffff, 0x00000001, 0x00800000},
		{"add-max-exponent-absorption", "fadd", 0x7f7fffff, 0x00000001, 0x7f7fffff},
		{"add-overflow", "fadd", 0x7f7fffff, 0x7f7fffff, 0x7f800000},
		{"add-opposite-infinities", "fadd", 0x7f800000, 0xff800000, 0x7fc00000},
		{"sub-negative-zero-positive-zero", "fsub", 0x80000000, 0x00000000, 0x80000000},
		{"sub-negative-zero-negative-zero", "fsub", 0x80000000, 0x80000000, 0x00000000},
		{"sub-near-cancellation", "fsub", 0x3f800001, 0x3f800000, 0x34000000},
		{"sub-qnan-canonical", "fsub", 0xffc12345, 0x3f800000, 0x7fc00000},
		{"mul-min-normal-half", "fmul", 0x00800000, 0x3f000000, 0x00400000},
		{"mul-min-subnormal-half-tie", "fmul", 0x00000001, 0x3f000000, 0x00000000},
		{"mul-min-subnormal-one-point-five", "fmul", 0x00000001, 0x3fc00000, 0x00000002},
		{"mul-negative-zero", "fmul", 0x80000000, 0x40400000, 0x80000000},
		{"mul-zero-infinity", "fmul", 0x00000000, 0x7f800000, 0x7fc00000},
		{"div-min-normal-two", "fdiv", 0x00800000, 0x40000000, 0x00400000},
		{"div-three-minsub-two", "fdiv", 0x00000003, 0x40000000, 0x00000002},
		{"div-finite-positive-zero", "fdiv", 0x3f800000, 0x00000000, 0x7f800000},
		{"div-finite-negative-zero", "fdiv", 0x3f800000, 0x80000000, 0xff800000},
		{"div-zero-zero-is-value", "fdiv", 0x00000000, 0x00000000, 0x7fc00000},
		{"rem-java-seven-four", "frem", 0x40e00000, 0x40800000, 0x40400000},
		{"rem-negative-seven-four", "frem", 0xc0e00000, 0x40800000, 0xc0400000},
		{"rem-max-exp-gap-subnormal", "frem", 0x7f7fffff, 0x00800001, 0x00000003},
		// The rounded fdiv quotient is 27529318 although the exact quotient
		// truncates to 27529317. Implementing x-y*(int)(x/y) incorrectly gives 0.
		{"rem-must-not-use-rounded-div", "frem", 0x49656fa9, 0x3d0bd353, 0x3ce8e082},
		{"rem-negative-exact-zero", "frem", 0xc0800000, 0x40000000, 0x80000000},
		{"rem-finite-infinity-unchanged", "frem", 0x80000001, 0x7f800000, 0x80000001},
		{"rem-zero-divisor-nan", "frem", 0x3f800000, 0x80000000, 0x7fc00000},
	}
	for _, tc := range floats {
		t.Run(tc.name, func(t *testing.T) {
			args := []int32{int32(tc.a), int32(tc.b)}
			if got := oracle.floatBits(t, tc.method, args); got != tc.want {
				t.Fatalf("independent JVM bits=%08x want hard-coded %08x", got, tc.want)
			}
			verifyM5ccAssertValue(t, classfile, tc.method, args, int32(tc.want), verifyM5ccGasLimit)
		})
	}

	doubles := []struct {
		name, method string
		a, b, want   uint64
	}{
		{"add-half-even", "dadd", 0x3ff0000000000000, 0x3ca0000000000000, 0x3ff0000000000000},
		{"add-half-odd-rounds-up", "dadd", 0x3ff0000000000001, 0x3ca0000000000000, 0x3ff0000000000002},
		{"add-exact-cancel-positive-zero", "dadd", 0x3ff0000000000000, 0xbff0000000000000, 0x0000000000000000},
		{"add-two-negative-zeros", "dadd", 0x8000000000000000, 0x8000000000000000, 0x8000000000000000},
		{"add-subnormal-to-min-normal", "dadd", 0x000fffffffffffff, 1, 0x0010000000000000},
		{"add-max-exponent-absorption", "dadd", 0x7fefffffffffffff, 1, 0x7fefffffffffffff},
		{"add-overflow", "dadd", 0x7fefffffffffffff, 0x7fefffffffffffff, 0x7ff0000000000000},
		{"add-opposite-infinities", "dadd", 0x7ff0000000000000, 0xfff0000000000000, 0x7ff8000000000000},
		{"sub-negative-zero-positive-zero", "dsub", 0x8000000000000000, 0, 0x8000000000000000},
		{"sub-negative-zero-negative-zero", "dsub", 0x8000000000000000, 0x8000000000000000, 0},
		{"sub-near-cancellation", "dsub", 0x3ff0000000000001, 0x3ff0000000000000, 0x3cb0000000000000},
		{"sub-qnan-canonical", "dsub", 0xfff8123456789abc, 0x3ff0000000000000, 0x7ff8000000000000},
		{"mul-min-normal-half", "dmul", 0x0010000000000000, 0x3fe0000000000000, 0x0008000000000000},
		{"mul-min-subnormal-half-tie", "dmul", 1, 0x3fe0000000000000, 0},
		{"mul-min-subnormal-one-point-five", "dmul", 1, 0x3ff8000000000000, 2},
		{"mul-zero-infinity", "dmul", 0, 0x7ff0000000000000, 0x7ff8000000000000},
		{"div-min-normal-two", "ddiv", 0x0010000000000000, 0x4000000000000000, 0x0008000000000000},
		{"div-three-minsub-two", "ddiv", 3, 0x4000000000000000, 2},
		{"div-finite-negative-zero", "ddiv", 0x3ff0000000000000, 0x8000000000000000, 0xfff0000000000000},
		{"div-zero-zero-is-value", "ddiv", 0, 0, 0x7ff8000000000000},
		{"rem-java-seven-four", "drem", 0x401c000000000000, 0x4010000000000000, 0x4008000000000000},
		{"rem-max-exp-gap-subnormal", "drem", 0x7fefffffffffffff, 0x0010000000000001, 0x0000000000060000},
		// The rounded ddiv quotient is one larger than trunc(exact x/y).
		{"rem-must-not-use-rounded-div", "drem", 0x432e403526d7059e, 0x3fedf5c47dd7ba69, 0x3fe25483ca54c155},
		{"rem-negative-exact-zero", "drem", 0xc010000000000000, 0x4000000000000000, 0x8000000000000000},
		{"rem-finite-infinity-unchanged", "drem", 0x8000000000000001, 0x7ff0000000000000, 0x8000000000000001},
		{"rem-zero-divisor-nan", "drem", 0x3ff0000000000000, 0, 0x7ff8000000000000},
	}
	for _, tc := range doubles {
		t.Run(tc.name, func(t *testing.T) {
			args := verifyM5ccDoubleArgs(tc.a, tc.b)
			if got := oracle.long(t, tc.method, args); got != tc.want {
				t.Fatalf("independent JVM bits=%016x want hard-coded %016x", got, tc.want)
			}
			verifyM5ccAssertDouble(t, classfile, tc.method, args, tc.want, verifyM5ccGasLimit)
		})
	}
}

func TestVerifyM5ccAllSpecialClassSignMatrices(t *testing.T) {
	classfile := verifyM5ccArithmeticClass(t)
	oracle := verifyM5ccNewOracle(t, classfile)
	for op, name := range []string{"add", "sub", "mul", "div", "rem"} {
		t.Run("float-"+name, func(t *testing.T) {
			args := []int32{int32(op)}
			want := oracle.int(t, "fmatrix", args)
			verifyM5ccAssertValue(t, classfile, "fmatrix", args, want, verifyM5ccGasLimit)
		})
		t.Run("double-"+name, func(t *testing.T) {
			args := []int32{int32(op)}
			want := oracle.int(t, "dmatrix", args)
			verifyM5ccAssertValue(t, classfile, "dmatrix", args, want, verifyM5ccGasLimit)
		})
	}
}

func TestVerifyM5ccSeededFiniteVectorsMatchJava8And21Exactly(t *testing.T) {
	classfile := verifyM5ccArithmeticClass(t)
	oracle := verifyM5ccNewOracle(t, classfile)
	rng := rand.New(rand.NewSource(0x5cc2026))
	for _, method := range []string{"fadd", "fsub", "fmul", "fdiv", "frem"} {
		for i := 0; i < 4; i++ {
			a, b := verifyM5ccRandomFinite32(rng), verifyM5ccRandomFinite32(rng)
			if b&0x7fffffff == 0 {
				b = 1
			}
			args := []int32{int32(a), int32(b)}
			want := int32(oracle.floatBits(t, method, args))
			t.Run(fmt.Sprintf("%s-%d-%08x-%08x", method, i, a, b), func(t *testing.T) {
				verifyM5ccAssertValue(t, classfile, method, args, want, verifyM5ccGasLimit)
			})
		}
	}
	for _, method := range []string{"dadd", "dsub", "dmul", "ddiv", "drem"} {
		for i := 0; i < 4; i++ {
			a, b := verifyM5ccRandomFinite64(rng), verifyM5ccRandomFinite64(rng)
			if b&0x7fffffffffffffff == 0 {
				b = 1
			}
			args := verifyM5ccDoubleArgs(a, b)
			want := oracle.long(t, method, args)
			t.Run(fmt.Sprintf("%s-%d-%016x-%016x", method, i, a, b), func(t *testing.T) {
				verifyM5ccAssertDouble(t, classfile, method, args, want, verifyM5ccGasLimit)
			})
		}
	}
}

func TestVerifyM5ccTypedOperandsPrefixesAndReturns(t *testing.T) {
	base := verifyM5ccTypedClass(t)
	parsed := parseStaticsClass(t, base)
	newPC := verifyM5cbInstructionPC(t, parsed.method(t, "allocate", "()I").code, 0xbb, 0)
	newIndex := binary.BigEndian.Uint16(parsed.method(t, "allocate", "()I").code[newPC+1:])
	valid := []struct {
		name string
		code []byte
		maxS uint16
		want int32
	}{
		{"int-prefix-fadd", []byte{0x08, 0x0c, 0x0d, 0x62, 0x57, 0xac}, 3, 5},
		{"reference-prefix-fmul", []byte{0x01, 0x0c, 0x0d, 0x6a, 0x57, 0x57, 0x10, 7, 0xac}, 3, 7},
		{"long-prefix-dadd", []byte{0x0a, 0x0f, 0x0e, 0x63, 0x58, 0x88, 0xac}, 6, 1},
		{"double-prefix-frem", []byte{0x0f, 0x0d, 0x0c, 0x72, 0x57, 0x8e, 0xac}, 4, 1},
	}
	for _, tc := range valid {
		t.Run(tc.name, func(t *testing.T) {
			classfile := verifyM5cbRewriteCode(t, base, "padding", "()I", tc.code, tc.maxS, 0)
			verifyM5ccAssertValue(t, classfile, "padding", nil, tc.want, verifyM5ccGasLimit)
		})
	}
	invalid := []struct {
		name     string
		code     []byte
		maxS     uint16
		kind, pc uint64
	}{
		{"fadd-missing", []byte{0x0c, 0x62, 0x57, 0x03, 0xac}, 1, 3, 1},
		{"dadd-missing-whole-value", []byte{0x0f, 0x63, 0x58, 0x03, 0xac}, 2, 3, 1},
		{"int-is-not-float", []byte{0x03, 0x0c, 0x62, 0x57, 0x03, 0xac}, 2, 14, 2},
		{"long-is-not-double", []byte{0x09, 0x0f, 0x63, 0x58, 0x03, 0xac}, 4, 14, 2},
		{"float-is-not-double", []byte{0x0c, 0x0f, 0x63, 0x58, 0x03, 0xac}, 3, 14, 2},
		{"double-is-not-float", []byte{0x0f, 0x0c, 0x62, 0x57, 0x03, 0xac}, 3, 14, 2},
		{"reference-is-not-float", []byte{0x01, 0x0c, 0x62, 0x57, 0x03, 0xac}, 2, 14, 2},
		{"uninitialized-is-not-float", []byte{0xbb, byte(newIndex >> 8), byte(newIndex), 0x0c, 0x62, 0x57, 0x03, 0xac}, 2, 14, 4},
	}
	for _, tc := range invalid {
		t.Run(tc.name, func(t *testing.T) {
			classfile := verifyM5cbRewriteCode(t, base, "padding", "()I", tc.code, tc.maxS, 0)
			verifyM5cbAssertError(t, func() (Result, error) { return Run(classfile, "padding", nil, verifyM5ccGasLimit) },
				"BytecodeError(uint256,uint256)", tc.kind, tc.pc)
		})
	}
	floatIndex := verifyM5cbCPIndices(parsed, 4)[0]
	doubleIndex := verifyM5cbCPIndices(parsed, 6)[0]
	for _, tc := range []struct {
		name       string
		index      uint16
		retag      byte
		code       []byte
		maxS       uint16
		arithmetic uint64
	}{
		{"cp-float-retagged-int", floatIndex, 3, []byte{0x13, byte(floatIndex >> 8), byte(floatIndex), 0x0c, 0x62, 0x57, 0x03, 0xac}, 2, 4},
		{"cp-double-retagged-long", doubleIndex, 5, []byte{0x14, byte(doubleIndex >> 8), byte(doubleIndex), 0x0f, 0x63, 0x58, 0x03, 0xac}, 4, 4},
	} {
		t.Run(tc.name, func(t *testing.T) {
			bad := verifyM5cbMutate(t, base, func(raw []byte, c staticsClass) { raw[c.entry(t, tc.index).offset] = tc.retag })
			bad = verifyM5cbRewriteCode(t, bad, "padding", "()I", tc.code, tc.maxS, 0)
			verifyM5cbAssertError(t, func() (Result, error) { return Run(bad, "padding", nil, verifyM5ccGasLimit) },
				"BytecodeError(uint256,uint256)", 14, tc.arithmetic)
		})
	}

	for _, tc := range []struct {
		name string
		code []byte
		maxS uint16
		opPC uint64
	}{
		{"freturn-from-int-method", []byte{0x0c, 0x0d, 0x62, 0xae}, 2, 3},
		{"dreturn-from-int-method", []byte{0x0f, 0x0e, 0x63, 0xaf}, 4, 3},
	} {
		t.Run(tc.name, func(t *testing.T) {
			classfile := verifyM5cbRewriteCode(t, base, "padding", "()I", tc.code, tc.maxS, 0)
			verifyM5cbAssertError(t, func() (Result, error) { return Run(classfile, "padding", nil, verifyM5ccGasLimit) },
				"CallError(uint256,uint256)", 5, tc.opPC)
		})
	}
}

func TestVerifyM5ccFieldsPostIncrementCallsDefaultsAndInitialization(t *testing.T) {
	classes := verifyM5ccCompile(t, map[string]string{
		"m5ccflow/I.java": `package m5ccflow; public interface I {
			default double value(double x,float y){return x+y;} float scale(float x,float y);
		}`,
		"m5ccflow/Box.java": `package m5ccflow; public final class Box implements I {
			float f; double d; static double sd;
			public float scale(float x,float y){return x*y;} public double direct(double x,double y){return x/y;}
			int postF(int bits){f=Float.intBitsToFloat(bits);float old=f++;int a=Float.floatToRawIntBits(old),b=Float.floatToRawIntBits(f);return a^((b<<1)|(b>>>31));}
			static int postD(int h,int l){sd=Double.longBitsToDouble(((long)h<<32)|(l&0xffffffffL));double old=sd--;long a=Double.doubleToRawLongBits(old),b=Double.doubleToRawLongBits(sd);return (int)(a^(a>>>32)^b^(b>>>32));}
		}`,
		"m5ccflow/InitValues.java": `package m5ccflow; public final class InitValues {
			static float zeroF(){return Float.intBitsToFloat(0);} static double zeroD(){return Double.longBitsToDouble(0);}
			static int fi=Float.floatToRawIntBits(1.0f/zeroF()); static long di=Double.doubleToRawLongBits(-1.0d/zeroD());
			public static int run(){return fi^(int)(di>>>32);}
		}`,
		"m5ccflow/InitFailure.java": `package m5ccflow; public final class InitFailure { static int zero(){return 0;} static int x=1/zero(); public static int run(){return x;} }`,
		"m5ccflow/Root.java": `package m5ccflow; public final class Root {
			static float f(int x){return Float.intBitsToFloat(x);} static double d(int h,int l){return Double.longBitsToDouble(((long)h<<32)|(l&0xffffffffL));}
			public static int fields(int x){return new Box().postF(x);} public static int staticField(int h,int l){return Box.postD(h,l);}
			public static int virtualF(int a,int b){Box x=new Box();return Float.floatToRawIntBits(x.scale(f(a),f(b)));}
			public static int virtualD(int ah,int al,int bh,int bl){Box x=new Box();return (int)(Double.doubleToRawLongBits(x.direct(d(ah,al),d(bh,bl)))>>>32);}
			public static int defaultD(int ah,int al,int b){I x=new Box();return (int)Double.doubleToRawLongBits(x.value(d(ah,al),f(b)));}
		}`,
	}, "m5ccflow/I", "m5ccflow/Box", "m5ccflow/InitValues", "m5ccflow/InitFailure", "m5ccflow/Root")
	bundle := verifyM5cbBundle(classes)
	oracle := verifyM5ccNewOracle(t, bundle...)
	cases := []struct {
		root, method string
		args         []int32
	}{
		{"m5ccflow/Root", "fields", []int32{int32(0x3f800000)}},
		{"m5ccflow/Root", "staticField", []int32{int32(0x40000000), 0}},
		{"m5ccflow/Root", "virtualF", []int32{int32(0x00800000), int32(0x3f000000)}},
		{"m5ccflow/Root", "virtualD", []int32{int32(0x3ff00000), 0, 0, 0}},
		{"m5ccflow/Root", "defaultD", []int32{int32(0x3ff00000), 0, int32(0x3f000000)}},
		{"m5ccflow/InitValues", "run", nil},
	}
	for _, tc := range cases {
		t.Run(tc.root+"-"+tc.method, func(t *testing.T) {
			want := oracle.intClass(t, strings.ReplaceAll(tc.root, "/", "."), tc.method, tc.args)
			verifyM5ccAssertClassesValue(t, bundle, tc.root, tc.method, tc.args, want, verifyM5ccGasLimit)
		})
	}
	verifyM5cbAssertException(t, func() (Result, error) {
		return RunClasses(bundle, "m5ccflow/InitFailure", "run", nil, verifyM5ccGasLimit)
	}, "java.lang.ExceptionInInitializerError", 3)
}

func TestVerifyM5ccRegistryAndDeferredBoundariesRemainExact(t *testing.T) {
	names := []string{
		"java.lang.ArithmeticException", "java.lang.StackOverflowError", "java.lang.ExceptionInInitializerError",
		"java.lang.NegativeArraySizeException", "java.lang.ArrayIndexOutOfBoundsException", "java.lang.NullPointerException",
		"java.lang.OutOfMemoryError", "java.lang.ClassCastException", "java.lang.ArrayStoreException",
		"java.lang.IncompatibleClassChangeError", "java.lang.AbstractMethodError",
	}
	selector := crypto.Keccak256([]byte("JavaException(uint256)"))[:4]
	for i, want := range names {
		data := make([]byte, 36)
		copy(data, selector)
		data[35] = byte(i + 1)
		if got, ok := decodeJavaException(data); !ok || got != want {
			t.Fatalf("kind %d decoded as %q/%v want %q", i+1, got, ok, want)
		}
	}
	unknown := make([]byte, 36)
	copy(unknown, selector)
	unknown[35] = 12
	if got, ok := decodeJavaException(unknown); ok || got != "" {
		t.Fatalf("new exception kind silently accepted: %q/%v", got, ok)
	}

	classes := verifyM5ccCompile(t, map[string]string{
		"DeferredM5cc.java": `public final class DeferredM5cc {
			public static int fa(){float[] x=new float[1];return x.length;} public static int da(){double[] x=new double[1];return x.length;}
			public static int other(int x){return Float.floatToIntBits(Float.intBitsToFloat(x));}
		}`,
	}, "DeferredM5cc")
	classfile := classes["DeferredM5cc"]
	parsed := parseStaticsClass(t, classfile)
	for _, method := range []string{"fa", "da"} {
		pc := verifyM5cbInstructionPC(t, parsed.method(t, method, "()I").code, 0xbc, 0)
		verifyM5cbAssertError(t, func() (Result, error) { return Run(classfile, method, nil, verifyM5ccGasLimit) },
			"ArrayError(uint256,uint256)", 1, uint64(pc))
	}
	otherPC := verifyM5cbMemberPC(t, parsed, parsed.method(t, "other", "(I)I"), 0xb8, 10, "floatToIntBits", "(F)I")
	verifyM5cbAssertError(t, func() (Result, error) { return Run(classfile, "other", []int32{1}, verifyM5ccGasLimit) },
		"CallError(uint256,uint256)", 3, uint64(otherPC))
}

func TestVerifyM5ccFixedMinimalWrapperGasGates(t *testing.T) {
	classfile := verifyM5ccArithmeticClass(t)
	oracle := verifyM5ccNewOracle(t, classfile)
	floats := []struct {
		method string
		a, b   uint32
	}{
		{"fadd", 0x3f800001, 0xbf800000}, {"fsub", 0x3f800001, 0x3f800000},
		{"fmul", 0x00800000, 0x3f000000}, {"fdiv", 0x00000003, 0x40000000},
		{"frem", 0x7f7fffff, 0x00800001},
	}
	for _, tc := range floats {
		t.Run(tc.method, func(t *testing.T) {
			args := []int32{int32(tc.a), int32(tc.b)}
			want := int32(oracle.floatBits(t, tc.method, args))
			result := verifyM5ccRunValue(t, classfile, tc.method, args, want, verifyM5ccSingleGasLimit)
			t.Logf("M5c-c single %s gas=%d limit=%d", tc.method, result.GasUsed, verifyM5ccSingleGasLimit)
		})
	}
	doubles := []struct {
		method string
		a, b   uint64
	}{
		{"dadd", 0x3ff0000000000001, 0xbff0000000000000}, {"dsub", 0x3ff0000000000001, 0x3ff0000000000000},
		{"dmul", 0x0010000000000000, 0x3fe0000000000000}, {"ddiv", 3, 0x4000000000000000},
		{"drem", 0x7fefffffffffffff, 0x0010000000000001},
	}
	for _, tc := range doubles {
		t.Run(tc.method, func(t *testing.T) {
			args := verifyM5ccDoubleArgs(tc.a, tc.b)
			want := oracle.long(t, tc.method, args)
			result := verifyM5ccRunDouble(t, classfile, tc.method, args, want, verifyM5ccSingleGasLimit)
			t.Logf("M5c-c single %s gas=%d limit=%d", tc.method, result.GasUsed, verifyM5ccSingleGasLimit)
		})
	}
	t.Run("repeat-drem-16", func(t *testing.T) {
		if got := verifyM5ccOpcodeCount(t, parseStaticsClass(t, classfile).method(t, "repeatDrem16", "(IIII)I").code, 0x73); got != 16 {
			t.Fatalf("repeat wrapper has %d drem opcodes, want exactly 16", got)
		}
		args := verifyM5ccDoubleArgs(0x7fefffffffffffff, 0x0010000000000001)
		want := oracle.int(t, "repeatDrem16", args)
		result := verifyM5ccRunValue(t, classfile, "repeatDrem16", args, want, verifyM5ccRepeatGasLimit)
		t.Logf("M5c-c sixteen repeated drem gas=%d limit=%d", result.GasUsed, verifyM5ccRepeatGasLimit)
	})
}

// --- M5c-c verifier-only helpers ---

func verifyM5ccArithmeticClass(t *testing.T) []byte {
	t.Helper()
	return verifyM5ccCompile(t, map[string]string{
		"VerifyM5ccArithmetic.java": `public strictfp final class VerifyM5ccArithmetic {
			static float f(int x){return Float.intBitsToFloat(x);} static int fb(float x){return Float.floatToRawIntBits(x);} static int cnf(int b){return ((b&0x7f800000)==0x7f800000&&(b&0x007fffff)!=0)?0x7fc00000:b;}
			static double d(int h,int l){return Double.longBitsToDouble(((long)h<<32)|(l&0xffffffffL));} static long db(double x){return Double.doubleToRawLongBits(x);} static long cd(double x){long b=db(x);return ((b&0x7ff0000000000000L)==0x7ff0000000000000L&&(b&0x000fffffffffffffL)!=0)?0x7ff8000000000000L:b;}
			public static int fadd(int a,int b){return fb(f(a)+f(b));} public static int fsub(int a,int b){return fb(f(a)-f(b));} public static int fmul(int a,int b){return fb(f(a)*f(b));} public static int fdiv(int a,int b){return fb(f(a)/f(b));} public static int frem(int a,int b){return fb(f(a)%f(b));}
			static double dadd0(int ah,int al,int bh,int bl){return d(ah,al)+d(bh,bl);} static double dsub0(int ah,int al,int bh,int bl){return d(ah,al)-d(bh,bl);} static double dmul0(int ah,int al,int bh,int bl){return d(ah,al)*d(bh,bl);} static double ddiv0(int ah,int al,int bh,int bl){return d(ah,al)/d(bh,bl);} static double drem0(int ah,int al,int bh,int bl){return d(ah,al)%d(bh,bl);}
			public static int daddHi(int a,int b,int c,int e){return (int)(db(dadd0(a,b,c,e))>>>32);} public static int daddLo(int a,int b,int c,int e){return (int)db(dadd0(a,b,c,e));}
			public static int dsubHi(int a,int b,int c,int e){return (int)(db(dsub0(a,b,c,e))>>>32);} public static int dsubLo(int a,int b,int c,int e){return (int)db(dsub0(a,b,c,e));}
			public static int dmulHi(int a,int b,int c,int e){return (int)(db(dmul0(a,b,c,e))>>>32);} public static int dmulLo(int a,int b,int c,int e){return (int)db(dmul0(a,b,c,e));}
			public static int ddivHi(int a,int b,int c,int e){return (int)(db(ddiv0(a,b,c,e))>>>32);} public static int ddivLo(int a,int b,int c,int e){return (int)db(ddiv0(a,b,c,e));}
			public static int dremHi(int a,int b,int c,int e){return (int)(db(drem0(a,b,c,e))>>>32);} public static int dremLo(int a,int b,int c,int e){return (int)db(drem0(a,b,c,e));}
			static int fs(int i){switch(i){case 0:return 0x7fc12345;case 1:return 0xffc12345;case 2:return 0x7f800000;case 3:return 0xff800000;case 4:return 0;case 5:return 0x80000000;case 6:return 0x3f800000;default:return 0xbf800000;}}
			static long ds(int i){switch(i){case 0:return 0x7ff8123456789abcL;case 1:return 0xfff8123456789abcL;case 2:return 0x7ff0000000000000L;case 3:return 0xfff0000000000000L;case 4:return 0;case 5:return 0x8000000000000000L;case 6:return 0x3ff0000000000000L;default:return 0xbff0000000000000L;}}
			static int fo(int a,int b,int op){int z;switch(op){case 0:z=fadd(a,b);break;case 1:z=fsub(a,b);break;case 2:z=fmul(a,b);break;case 3:z=fdiv(a,b);break;default:z=frem(a,b);}return cnf(z);}
			static long dd(long a,long b,int op){double x=Double.longBitsToDouble(a),y=Double.longBitsToDouble(b);switch(op){case 0:return cd(x+y);case 1:return cd(x-y);case 2:return cd(x*y);case 3:return cd(x/y);default:return cd(x%y);}}
			public static int fmatrix(int op){int h=1;for(int i=0;i<8;i++)for(int j=0;j<8;j++)h=31*h+fo(fs(i),fs(j),op);return h;}
			public static int dmatrix(int op){int h=1;for(int i=0;i<8;i++)for(int j=0;j<8;j++){long x=dd(ds(i),ds(j),op);h=31*h+(int)(x^(x>>>32));}return h;}
			static long rot(long x,int n){return (x<<n)|(x>>>(64-n));}
			public static int repeatDrem16(int ah,int al,int bh,int bl){double x=d(ah,al),y=d(bh,bl);long h=0;
				h^=cd(x%y);h^=rot(cd(x%y),1);h^=rot(cd(x%y),2);h^=rot(cd(x%y),3);
				h^=rot(cd(x%y),4);h^=rot(cd(x%y),5);h^=rot(cd(x%y),6);h^=rot(cd(x%y),7);
				h^=rot(cd(x%y),8);h^=rot(cd(x%y),9);h^=rot(cd(x%y),10);h^=rot(cd(x%y),11);
				h^=rot(cd(x%y),12);h^=rot(cd(x%y),13);h^=rot(cd(x%y),14);h^=rot(cd(x%y),15);return (int)(h^(h>>>32));}
		}`,
	}, "VerifyM5ccArithmetic")["VerifyM5ccArithmetic"]
}

func verifyM5ccTypedClass(t *testing.T) []byte {
	t.Helper()
	return verifyM5ccCompile(t, map[string]string{
		"VerifyM5ccTyped.java": `public final class VerifyM5ccTyped { public VerifyM5ccTyped(){} static float fc(){return 1.25f;} static double dc(){return 1.25d;} public static int allocate(){return new VerifyM5ccTyped()==null?0:1;} public static int padding(){int x=0;` + strings.Repeat("x=x+1;", 80) + `return x;} }`,
	}, "VerifyM5ccTyped")["VerifyM5ccTyped"]
}

func verifyM5ccCompile(t *testing.T, sources map[string]string, internalNames ...string) map[string][]byte {
	t.Helper()
	return verifyM5cbCompile(t, sources, internalNames...)
}

type verifyM5ccOracle struct {
	classPath string
	root      string
	java8     string
	java21    string
}

func verifyM5ccNewOracle(t *testing.T, classfiles ...[]byte) verifyM5ccOracle {
	t.Helper()
	dir := t.TempDir()
	source := `public final class VerifyM5ccOracle { public static void main(String[] a)throws Exception{Class<?> c=Class.forName(a[0]);Class<?>[] p=new Class<?>[a.length-2];Object[] v=new Object[p.length];for(int i=0;i<p.length;i++){p[i]=Integer.TYPE;v[i]=Integer.valueOf(a[i+2]);}System.out.print(c.getMethod(a[1],p).invoke(null,v));}}`
	path := filepath.Join(dir, "VerifyM5ccOracle.java")
	if err := os.WriteFile(path, []byte(source), 0o600); err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	if output, err := exec.CommandContext(ctx, "javac", "-J-Xmx64m", "--release", "8", "-d", dir, path).CombinedOutput(); err != nil {
		t.Fatalf("compile bounded M5c-c oracle: %v\n%s", err, output)
	}
	root := ""
	for _, classfile := range classfiles {
		name := verifyM5baClassName(t, classfile)
		if root == "" || name == "VerifyM5ccArithmetic" {
			root = strings.ReplaceAll(name, "/", ".")
		}
		classPath := filepath.Join(dir, filepath.FromSlash(name+".class"))
		if err := os.MkdirAll(filepath.Dir(classPath), 0o700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(classPath, classfile, 0o600); err != nil {
			t.Fatal(err)
		}
	}
	java8 := verifyM5baJava8(t)
	verifyM5ccRequireJavaVersion(t, java8, regexp.MustCompile(`(?m)version "1\.8\.`), "Java 8")
	verifyM5ccRequireJavaVersion(t, "java", regexp.MustCompile(`(?m)version "21\.`), "current Java 21")
	return verifyM5ccOracle{classPath: dir, root: root, java8: java8, java21: "java"}
}

func verifyM5ccRequireJavaVersion(t *testing.T, path string, pattern *regexp.Regexp, label string) {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	output, err := exec.CommandContext(ctx, path, "-version").CombinedOutput()
	if err != nil || !pattern.Match(output) {
		t.Fatalf("%s oracle unavailable at %q: %v\n%s", label, path, err, output)
	}
}

func (o verifyM5ccOracle) int(t *testing.T, method string, args []int32) int32 {
	t.Helper()
	return o.intClass(t, o.root, method, args)
}

func (o verifyM5ccOracle) intClass(t *testing.T, class, method string, args []int32) int32 {
	t.Helper()
	values := o.ints(t, class, method, args)
	if values[0] != values[1] {
		t.Fatalf("Java 8/21 disagreement for %s.%s%v: %d != %d", class, method, args, values[0], values[1])
	}
	return values[0]
}

func (o verifyM5ccOracle) ints(t *testing.T, class, method string, args []int32) [2]int32 {
	t.Helper()
	var values [2]int32
	for i, java := range []string{o.java8, o.java21} {
		argv := []string{"-Xmx64m", "-cp", o.classPath, "VerifyM5ccOracle", class, method}
		for _, arg := range args {
			argv = append(argv, strconv.FormatInt(int64(arg), 10))
		}
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		output, err := exec.CommandContext(ctx, java, argv...).CombinedOutput()
		cancel()
		if err != nil {
			t.Fatalf("bounded %s oracle %s.%s failed: %v\n%s", java, class, method, err, output)
		}
		value, err := strconv.ParseInt(strings.TrimSpace(string(output)), 10, 32)
		if err != nil {
			t.Fatalf("%s oracle returned non-int32 %q: %v", java, output, err)
		}
		values[i] = int32(value)
	}
	return values
}

func (o verifyM5ccOracle) floatBits(t *testing.T, method string, args []int32) uint32 {
	t.Helper()
	values := o.ints(t, o.root, method, args)
	var normalized [2]uint32
	for i, value := range values {
		normalized[i] = uint32(value)
		if normalized[i]&0x7f800000 == 0x7f800000 && normalized[i]&0x007fffff != 0 {
			normalized[i] = 0x7fc00000
		}
	}
	if normalized[0] != normalized[1] {
		t.Fatalf("Java 8/21 float-bit disagreement for %s%v: %08x != %08x", method, args, normalized[0], normalized[1])
	}
	return normalized[0]
}

func (o verifyM5ccOracle) long(t *testing.T, method string, args []int32) uint64 {
	t.Helper()
	his := o.ints(t, o.root, method+"Hi", args)
	los := o.ints(t, o.root, method+"Lo", args)
	var normalized [2]uint64
	for i := range normalized {
		normalized[i] = uint64(uint32(his[i]))<<32 | uint64(uint32(los[i]))
		if normalized[i]&0x7ff0000000000000 == 0x7ff0000000000000 && normalized[i]&0x000fffffffffffff != 0 {
			normalized[i] = 0x7ff8000000000000
		}
	}
	if normalized[0] != normalized[1] {
		t.Fatalf("Java 8/21 double-bit disagreement for %s%v: %016x != %016x", method, args, normalized[0], normalized[1])
	}
	return normalized[0]
}

func verifyM5ccDoubleArgs(a, b uint64) []int32 {
	return []int32{int32(a >> 32), int32(a), int32(b >> 32), int32(b)}
}

func verifyM5ccRandomFinite32(rng *rand.Rand) uint32 {
	exponent := uint32(rng.Intn(255))
	return uint32(rng.Intn(2))<<31 | exponent<<23 | uint32(rng.Intn(1<<23))
}

func verifyM5ccRandomFinite64(rng *rand.Rand) uint64 {
	exponent := uint64(rng.Intn(2047))
	return uint64(rng.Intn(2))<<63 | exponent<<52 | rng.Uint64()&0x000fffffffffffff
}

func verifyM5ccAssertValue(t *testing.T, classfile []byte, method string, args []int32, want int32, gas uint64) {
	t.Helper()
	verifyM5ccRunValue(t, classfile, method, args, want, gas)
}

func verifyM5ccRunValue(t *testing.T, classfile []byte, method string, args []int32, want int32, gas uint64) Result {
	t.Helper()
	result, err := Run(classfile, method, args, gas)
	if err != nil || result.ExceptionClass != "" || result.Value != want || result.GasUsed == 0 || result.GasUsed > gas || len(result.RevertData) != 0 {
		t.Fatalf("%s%v result/error=%+v/%v want value=%d within gas=%d", method, args, result, err, want, gas)
	}
	return result
}

func verifyM5ccAssertDouble(t *testing.T, classfile []byte, method string, args []int32, want uint64, gas uint64) {
	t.Helper()
	verifyM5ccRunDouble(t, classfile, method, args, want, gas)
}

func verifyM5ccRunDouble(t *testing.T, classfile []byte, method string, args []int32, want uint64, gas uint64) Result {
	t.Helper()
	hi, err := Run(classfile, method+"Hi", args, gas)
	if err != nil || hi.ExceptionClass != "" || hi.GasUsed == 0 || hi.GasUsed > gas || len(hi.RevertData) != 0 {
		t.Fatalf("%sHi result/error=%+v/%v", method, hi, err)
	}
	lo, err := Run(classfile, method+"Lo", args, gas)
	if err != nil || lo.ExceptionClass != "" || lo.GasUsed == 0 || lo.GasUsed > gas || len(lo.RevertData) != 0 {
		t.Fatalf("%sLo result/error=%+v/%v", method, lo, err)
	}
	got := uint64(uint32(hi.Value))<<32 | uint64(uint32(lo.Value))
	if got != want {
		t.Fatalf("%s%v bits=%016x want %016x", method, args, got, want)
	}
	if lo.GasUsed > hi.GasUsed {
		return lo
	}
	return hi
}

func verifyM5ccAssertClassesValue(t *testing.T, bundle [][]byte, root, method string, args []int32, want int32, gas uint64) {
	t.Helper()
	result, err := RunClasses(bundle, root, method, args, gas)
	if err != nil || result.ExceptionClass != "" || result.Value != want || result.GasUsed == 0 || result.GasUsed > gas || len(result.RevertData) != 0 {
		t.Fatalf("%s.%s result/error=%+v/%v want %d", root, method, result, err, want)
	}
}

func verifyM5ccOpcodeCount(t *testing.T, code []byte, opcode byte) int {
	t.Helper()
	count := 0
	for pc := 0; pc < len(code); pc += verifyM5baInstructionWidth(t, code, pc) {
		if code[pc] == opcode {
			count++
		}
	}
	return count
}
