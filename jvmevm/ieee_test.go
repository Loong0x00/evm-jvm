// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"strconv"
	"strings"
	"testing"
)

func TestRuntimeM5cbRawBindingsAndScalarConversions(t *testing.T) {
	classfile := compileJava(t, "IEEE", `
public class IEEE {
  static long bits(int hi, int lo) { return ((long)hi << 32) | (lo & 0xffffffffL); }
  public static int rawF(int x) { return Float.floatToRawIntBits(Float.intBitsToFloat(x)); }
  public static int rawDHi(int hi, int lo) { return (int)(Double.doubleToRawLongBits(Double.longBitsToDouble(bits(hi, lo))) >>> 32); }
  public static int rawDLo(int hi, int lo) { return (int)Double.doubleToRawLongBits(Double.longBitsToDouble(bits(hi, lo))); }
  public static int i2f(int x) { return Float.floatToRawIntBits((float)x); }
  public static int i2dHi(int x) { return (int)(Double.doubleToRawLongBits((double)x) >>> 32); }
  public static int i2dLo(int x) { return (int)Double.doubleToRawLongBits((double)x); }
  public static int l2f(int hi, int lo) { return Float.floatToRawIntBits((float)bits(hi, lo)); }
  public static int l2dHi(int hi, int lo) { return (int)(Double.doubleToRawLongBits((double)bits(hi, lo)) >>> 32); }
  public static int l2dLo(int hi, int lo) { return (int)Double.doubleToRawLongBits((double)bits(hi, lo)); }
  public static int f2i(int x) { return (int)Float.intBitsToFloat(x); }
  public static int f2lHi(int x) { return (int)(((long)Float.intBitsToFloat(x)) >>> 32); }
  public static int f2lLo(int x) { return (int)(long)Float.intBitsToFloat(x); }
  public static int d2i(int hi, int lo) { return (int)Double.longBitsToDouble(bits(hi, lo)); }
  public static int d2lHi(int hi, int lo) { return (int)(((long)Double.longBitsToDouble(bits(hi, lo))) >>> 32); }
  public static int d2lLo(int hi, int lo) { return (int)(long)Double.longBitsToDouble(bits(hi, lo)); }
  public static int f2dHi(int x) { return (int)(Double.doubleToRawLongBits((double)Float.intBitsToFloat(x)) >>> 32); }
  public static int f2dLo(int x) { return (int)Double.doubleToRawLongBits((double)Float.intBitsToFloat(x)); }
  public static int d2f(int hi, int lo) { return Float.floatToRawIntBits((float)Double.longBitsToDouble(bits(hi, lo))); }
}`)
	cases := []struct {
		method string
		args   []int32
		want   int32
	}{
		{"rawF", []int32{runtimeM5cbI32(0x80000000)}, runtimeM5cbI32(0x80000000)},
		{"rawF", []int32{runtimeM5cbI32(0x7fc12345)}, runtimeM5cbI32(0x7fc12345)},
		{"rawF", []int32{runtimeM5cbI32(0x7fa12345)}, runtimeM5cbI32(0x7fa12345)}, // EVM transport also preserves signaling payloads
		{"rawDHi", []int32{runtimeM5cbI32(0xfff80000), 0x12345678}, runtimeM5cbI32(0xfff80000)},
		{"rawDLo", []int32{runtimeM5cbI32(0xfff80000), 0x12345678}, 0x12345678},
		{"i2f", []int32{16777217}, runtimeM5cbI32(0x4b800000)},
		{"i2f", []int32{2147483647}, runtimeM5cbI32(0x4f000000)},
		{"i2f", []int32{-2147483648}, runtimeM5cbI32(0xcf000000)},
		{"i2dHi", []int32{2147483647}, runtimeM5cbI32(0x41dfffff)},
		{"i2dLo", []int32{2147483647}, runtimeM5cbI32(0xffc00000)},
		{"l2f", []int32{0x7fffffff, -1}, runtimeM5cbI32(0x5f000000)},
		{"l2f", []int32{-2147483648, 0}, runtimeM5cbI32(0xdf000000)},
		{"l2dHi", []int32{0x00200000, 1}, 0x43400000},
		{"l2dLo", []int32{0x00200000, 1}, 0}, // 2^53+1 is a tie to even
		{"l2dLo", []int32{0x00200000, 3}, 2}, // 2^53+3 ties upward to the even neighbor
		{"l2dHi", []int32{0x7fffffff, -1}, 0x43e00000},
		{"l2dHi", []int32{-2147483648, 0}, runtimeM5cbI32(0xc3e00000)},
		{"f2i", []int32{runtimeM5cbI32(0x7fc00001)}, 0},
		{"f2i", []int32{runtimeM5cbI32(0x7f800000)}, 2147483647},
		{"f2i", []int32{runtimeM5cbI32(0xff800000)}, -2147483648},
		{"f2i", []int32{runtimeM5cbI32(0xc0700000)}, -3},
		{"f2lHi", []int32{runtimeM5cbI32(0x5f000000)}, runtimeM5cbI32(0x7fffffff)},
		{"f2lLo", []int32{runtimeM5cbI32(0x5f000000)}, -1},
		{"d2i", []int32{0x400c0000, 0}, 3},
		{"d2i", []int32{runtimeM5cbI32(0xc00c0000), 0}, -3},
		{"d2lHi", []int32{0x43e00000, 0}, runtimeM5cbI32(0x7fffffff)},
		{"d2lLo", []int32{0x43e00000, 0}, -1},
		{"f2dHi", []int32{1}, 0x36a00000},
		{"f2dLo", []int32{1}, 0},
		{"f2dHi", []int32{runtimeM5cbI32(0x7fc12345)}, 0x7ff80000},
		{"f2dLo", []int32{runtimeM5cbI32(0x7fc12345)}, 0},
		{"d2f", []int32{0x36a00000, 0}, 1},
		{"d2f", []int32{0x36900000, 0}, 0}, // exactly half of the least float subnormal, ties even
		{"d2f", []int32{0x36900000, 1}, 1},
		{"d2f", []int32{0x7ff00000, 1}, runtimeM5cbI32(0x7fc00000)},
		{"d2f", []int32{runtimeM5cbI32(0x80000000), 0}, runtimeM5cbI32(0x80000000)},
		{"d2f", []int32{0x47efffff, runtimeM5cbI32(0xefffffff)}, runtimeM5cbI32(0x7f7fffff)},
		{"d2f", []int32{0x47efffff, runtimeM5cbI32(0xf0000000)}, runtimeM5cbI32(0x7f800000)},
	}
	for _, tc := range cases {
		t.Run(tc.method, func(t *testing.T) {
			result, err := Run(classfile, tc.method, tc.args, 60_000_000)
			if err != nil || result.Value != tc.want || result.ExceptionClass != "" {
				t.Fatalf("result/error = %+v/%v, want %d", result, err, tc.want)
			}
		})
	}
}

func TestRuntimeM5cbNegCompareFieldsCallsAndDeferredOperations(t *testing.T) {
	classfile := compileJava(t, "IEEEFlow", `
public class IEEEFlow {
  static float sf; static double sd; float f; double d;
  static final float CF = -0.0f; static final double CD = -0.0d;
  static float passF(float x) { return x; }
  static double passD(double x) { return x; }
  public static int fneg(int x) { return Float.floatToRawIntBits(-passF(Float.intBitsToFloat(x))); }
  public static int dnegHi(int hi, int lo) { long x=((long)hi<<32)|(lo&0xffffffffL); return (int)(Double.doubleToRawLongBits(-passD(Double.longBitsToDouble(x)))>>>32); }
  public static int fcmpL(int a,int b) { float x=Float.intBitsToFloat(a),y=Float.intBitsToFloat(b); return x<y?-1:(x==y?0:1); }
  public static int fcmpG(int a,int b) { float x=Float.intBitsToFloat(a),y=Float.intBitsToFloat(b); return x>y?1:(x==y?0:-1); }
  public static int fields(int x) { IEEEFlow o=new IEEEFlow(); sf=Float.intBitsToFloat(x); o.f=sf; return Float.floatToRawIntBits(o.f); }
  public static int doubleFields(int hi,int lo) { IEEEFlow o=new IEEEFlow(); sd=Double.longBitsToDouble(((long)hi<<32)|(lo&0xffffffffL)); o.d=sd; return (int)Double.doubleToRawLongBits(o.d); }
  public static int constantF() { return Float.floatToRawIntBits(CF); }
  public static int constantDHi() { return (int)(Double.doubleToRawLongBits(CD)>>>32); }
}`)
	cases := []struct {
		method string
		args   []int32
		want   int32
	}{
		{"fneg", []int32{runtimeM5cbI32(0x7fc12345)}, runtimeM5cbI32(0xffc12345)},
		{"fneg", []int32{0}, runtimeM5cbI32(0x80000000)},
		{"dnegHi", []int32{0x7ff81234, 1}, runtimeM5cbI32(0xfff81234)},
		{"fcmpL", []int32{runtimeM5cbI32(0x80000000), 0}, 0},
		{"fcmpL", []int32{runtimeM5cbI32(0x7fc00000), 0}, 1},
		{"fcmpG", []int32{runtimeM5cbI32(0x7fc00000), 0}, -1},
		{"fcmpL", []int32{runtimeM5cbI32(0xbf800000), runtimeM5cbI32(0x800000)}, -1},
		{"fields", []int32{runtimeM5cbI32(0x80000000)}, runtimeM5cbI32(0x80000000)},
		{"doubleFields", []int32{0x7ff81234, 0x56789abc}, runtimeM5cbI32(0x56789abc)},
		{"constantF", nil, runtimeM5cbI32(0x80000000)},
		{"constantDHi", nil, runtimeM5cbI32(0x80000000)},
	}
	for _, tc := range cases {
		t.Run(tc.method, func(t *testing.T) {
			result, err := Run(classfile, tc.method, tc.args, 80_000_000)
			if err != nil || result.Value != tc.want {
				t.Fatalf("result/error = %+v/%v, want %d", result, err, tc.want)
			}
		})
	}

	deferred := compileJava(t, "DeferredFP", `public class DeferredFP {
 public static int add(int x){ return Float.floatToRawIntBits(Float.intBitsToFloat(x)+1.0f); }
 public static int array(int x){ float[] a=new float[1]; a[0]=Float.intBitsToFloat(x); return Float.floatToRawIntBits(a[0]); }
}`)
	verifyM5baJava8Outcome(t, [][]byte{deferred}, "DeferredFP", "add", []int32{1}, "value=1065353216")
	result, err := Run(deferred, "add", []int32{1}, 20_000_000)
	if err != nil || result.Value != 1065353216 || result.ExceptionClass != "" || len(result.RevertData) != 0 {
		t.Fatalf("scalar IEEE add result/error = %+v/%v, want exact Java bits 1065353216", result, err)
	}
	if _, err := Run(deferred, "array", []int32{1}, 20_000_000); err == nil {
		t.Fatal("float array unexpectedly accepted")
	}
}

func TestRuntimeM5cbFloatDoubleAcrossInterfaceAndVirtualFrames(t *testing.T) {
	classes := runtimeM4cCompileClasses(t, map[string]string{
		"IEEEIface": `public interface IEEEIface { float f(float x); double d(double x); }`,
		"IEEEImpl": `public class IEEEImpl implements IEEEIface {
 public float f(float x){return x;} public double d(double x){return x;} }`,
		"IEEECalls": `public class IEEECalls {
 public static int ifaceF(int x){IEEEIface v=new IEEEImpl();return Float.floatToRawIntBits(v.f(Float.intBitsToFloat(x)));}
 public static int ifaceD(int hi,int lo){IEEEIface v=new IEEEImpl();long x=((long)hi<<32)|(lo&0xffffffffL);return (int)Double.doubleToRawLongBits(v.d(Double.longBitsToDouble(x)));}
 public static int virtualD(int hi,int lo){IEEEImpl v=new IEEEImpl();long x=((long)hi<<32)|(lo&0xffffffffL);return (int)(Double.doubleToRawLongBits(v.d(Double.longBitsToDouble(x)))>>>32);}
}`,
	})
	for _, tc := range []struct {
		method string
		args   []int32
		want   int32
	}{
		{"ifaceF", []int32{runtimeM5cbI32(0xffc12345)}, runtimeM5cbI32(0xffc12345)},
		{"ifaceD", []int32{0x7ff81234, runtimeM5cbI32(0x89abcdef)}, runtimeM5cbI32(0x89abcdef)},
		{"virtualD", []int32{runtimeM5cbI32(0xfff81234), 1}, runtimeM5cbI32(0xfff81234)},
	} {
		result, err := RunClasses(runtimeM4cBundle(classes), "IEEECalls", tc.method, tc.args, 100_000_000)
		if err != nil || result.Value != tc.want {
			t.Fatalf("%s result/error = %+v/%v, want %d", tc.method, result, err, tc.want)
		}
	}
}

func TestRuntimeM5cbWideFloatAndDoubleLocals(t *testing.T) {
	var source strings.Builder
	source.WriteString("public class IEEEWide {")
	for _, method := range []struct {
		name, declaration, result string
	}{
		{"wideF", "float x=Float.intBitsToFloat(bits);", "Float.floatToRawIntBits(x)"},
		{"wideD", "double x=Double.longBitsToDouble(((long)bits)<<32);", "(int)(Double.doubleToRawLongBits(x)>>>32)"},
	} {
		source.WriteString("public static int " + method.name + "(int bits){")
		for i := 0; i < 260; i++ {
			source.WriteString("int v" + strconv.Itoa(i) + "=0;")
		}
		source.WriteString(method.declaration + "return " + method.result)
		for i := 0; i < 260; i++ {
			source.WriteString("+v" + strconv.Itoa(i))
		}
		source.WriteString(";}")
	}
	source.WriteString("}")
	classfile := compileJava(t, "IEEEWide", source.String())
	parsed := parseStaticsClass(t, classfile)
	for _, tc := range []struct {
		method      string
		load, store byte
	}{
		{"wideF", 0x17, 0x38}, {"wideD", 0x18, 0x39},
	} {
		code := parsed.namedMethod(t, tc.method).code
		if !bytes.Contains(code, []byte{0xc4, tc.store}) || !bytes.Contains(code, []byte{0xc4, tc.load}) {
			t.Fatalf("%s does not exercise wide IEEE load/store: %x", tc.method, code)
		}
	}
	for _, method := range []string{"wideF", "wideD"} {
		result, err := Run(classfile, method, []int32{runtimeM5cbI32(0x80000000)}, 100_000_000)
		if err != nil || result.Value != runtimeM5cbI32(0x80000000) {
			t.Fatalf("%s result/error = %+v/%v", method, result, err)
		}
	}
}

func TestRuntimeM5cbNativeRegistryIsExactAndOrdinaryCodeWins(t *testing.T) {
	ordinary := runtimeM4cCompileClasses(t, map[string]string{
		"java/lang/Float": `package java.lang; public final class Float {
 private Float() {} public static float intBitsToFloat(int x) { return 2.0f; }
 public static int floatToRawIntBits(float x) { return 77; }
}`,
		"NativeOverrideRoot": `public class NativeOverrideRoot { public static int run(int x) {
 return Float.floatToRawIntBits(Float.intBitsToFloat(x)); } }`,
	})
	result, err := RunClasses(runtimeM4cBundle(ordinary), "NativeOverrideRoot", "run", []int32{123}, 80_000_000)
	if err != nil || result.Value != 77 {
		t.Fatalf("ordinary canonical-name Code result/error = %+v/%v, want 77", result, err)
	}

	unknown := runtimeM4cCompileClasses(t, map[string]string{
		"OtherNative":     `public class OtherNative { public static native int raw(int x); }`,
		"OtherNativeRoot": `public class OtherNativeRoot { public static int run(int x) { return OtherNative.raw(x); } }`,
	})
	if _, err := RunClasses(runtimeM4cBundle(unknown), "OtherNativeRoot", "run", []int32{1}, 20_000_000); err == nil {
		t.Fatal("unknown native method unexpectedly accepted")
	}

	initialization := runtimeM4cCompileClasses(t, map[string]string{
		"java/lang/Float": `package java.lang; public final class Float {
 private Float() {} static int fail=1/0;
 public static native float intBitsToFloat(int x);
 public static native int floatToRawIntBits(float x);
}`,
		"NativeInitRoot": `public class NativeInitRoot { public static int run(int x) {
 return Float.floatToRawIntBits(Float.intBitsToFloat(x)); } }`,
	})
	result, err = RunClasses(runtimeM4cBundle(initialization), "NativeInitRoot", "run", []int32{1}, 80_000_000)
	if err != nil || result.ExceptionClass != "java.lang.ExceptionInInitializerError" {
		t.Fatalf("native declaring-class initialization result/error = %+v/%v", result, err)
	}
}

func runtimeM5cbI32(value uint32) int32 { return int32(value) }
