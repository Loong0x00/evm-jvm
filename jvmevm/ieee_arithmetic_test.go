// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.

package jvmevm

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
)

const (
	runtimeM5ccSingleGas = uint64(20_000_000)
	runtimeM5ccRepeatGas = uint64(100_000_000)
)

type runtimeM5ccVector struct {
	name, method string
	args         []int32
	want         uint64
	double       bool
}

func TestRuntimeM5ccCriticalIEEEArithmetic(t *testing.T) {
	classfile := runtimeM5ccClass(t)
	vectors := []runtimeM5ccVector{
		{"f-add-basic", "fadd", runtimeM5ccFArgs(0x3f800000, 0x40000000), 0x40400000, false},
		{"f-add-tie-even", "fadd", runtimeM5ccFArgs(0x3f800000, 0x33800000), 0x3f800000, false},
		{"f-add-tie-odd", "fadd", runtimeM5ccFArgs(0x3f800001, 0x33800000), 0x3f800002, false},
		{"f-add-cancel", "fadd", runtimeM5ccFArgs(0x3f800000, 0xbf800000), 0, false},
		{"f-add-negative-zeros", "fadd", runtimeM5ccFArgs(0x80000000, 0x80000000), 0x80000000, false},
		{"f-sub-negative-zero", "fsub", runtimeM5ccFArgs(0x80000000, 0), 0x80000000, false},
		{"f-add-overflow", "fadd", runtimeM5ccFArgs(0x7f7fffff, 0x7f7fffff), 0x7f800000, false},
		{"f-mul-gradual", "fmul", runtimeM5ccFArgs(0x00800000, 0x3f000000), 0x00400000, false},
		{"f-div-third", "fdiv", runtimeM5ccFArgs(0x3f800000, 0x40400000), 0x3eaaaaab, false},
		{"f-div-half-minsub", "fdiv", runtimeM5ccFArgs(1, 0x40000000), 0, false},
		{"f-div-tie-to-even-minsub", "fdiv", runtimeM5ccFArgs(3, 0x40000000), 2, false},
		{"f-div-zero-no-exception", "fdiv", runtimeM5ccFArgs(0xbf800000, 0), 0xff800000, false},
		{"f-rem-java-not-nearest", "frem", runtimeM5ccFArgs(0x40e00000, 0x40800000), 0x40400000, false},
		{"f-rem-negative-zero", "frem", runtimeM5ccFArgs(0xc0800000, 0x40000000), 0x80000000, false},
		{"f-rem-extreme-gap", "frem", runtimeM5ccFArgs(0x7f7fffff, 1), 0, false},
		{"f-invalid-canonical", "fmul", runtimeM5ccFArgs(0, 0x7f800000), 0x7fc00000, false},
		{"f-snan-input-canonical", "fadd", runtimeM5ccFArgs(0x7f800001, 0x3f800000), 0x7fc00000, false},

		{"d-add-basic", "dadd", runtimeM5ccDArgs(0x3ff0000000000000, 0x4000000000000000), 0x4008000000000000, true},
		{"d-add-tie-even", "dadd", runtimeM5ccDArgs(0x3ff0000000000000, 0x3ca0000000000000), 0x3ff0000000000000, true},
		{"d-add-tie-odd", "dadd", runtimeM5ccDArgs(0x3ff0000000000001, 0x3ca0000000000000), 0x3ff0000000000002, true},
		{"d-add-cancel", "dadd", runtimeM5ccDArgs(0x3ff0000000000000, 0xbff0000000000000), 0, true},
		{"d-add-negative-zeros", "dadd", runtimeM5ccDArgs(0x8000000000000000, 0x8000000000000000), 0x8000000000000000, true},
		{"d-sub-negative-zero", "dsub", runtimeM5ccDArgs(0x8000000000000000, 0), 0x8000000000000000, true},
		{"d-add-overflow", "dadd", runtimeM5ccDArgs(0x7fefffffffffffff, 0x7fefffffffffffff), 0x7ff0000000000000, true},
		{"d-mul-gradual", "dmul", runtimeM5ccDArgs(0x0010000000000000, 0x3fe0000000000000), 0x0008000000000000, true},
		{"d-div-third", "ddiv", runtimeM5ccDArgs(0x3ff0000000000000, 0x4008000000000000), 0x3fd5555555555555, true},
		{"d-div-half-minsub", "ddiv", runtimeM5ccDArgs(1, 0x4000000000000000), 0, true},
		{"d-div-tie-to-even-minsub", "ddiv", runtimeM5ccDArgs(3, 0x4000000000000000), 2, true},
		{"d-div-zero-no-exception", "ddiv", runtimeM5ccDArgs(0xbff0000000000000, 0), 0xfff0000000000000, true},
		{"d-rem-java-not-nearest", "drem", runtimeM5ccDArgs(0x401c000000000000, 0x4010000000000000), 0x4008000000000000, true},
		{"d-rem-negative-zero", "drem", runtimeM5ccDArgs(0xc010000000000000, 0x4000000000000000), 0x8000000000000000, true},
		{"d-rem-extreme-gap", "drem", runtimeM5ccDArgs(0x7fefffffffffffff, 1), 0, true},
		{"d-invalid-canonical", "dmul", runtimeM5ccDArgs(0, 0x7ff0000000000000), 0x7ff8000000000000, true},
		{"d-snan-input-canonical", "dadd", runtimeM5ccDArgs(0x7ff0000000000001, 0x3ff0000000000000), 0x7ff8000000000000, true},
	}
	oracleDir := runtimeM5ccOracle(t)
	for _, tc := range vectors {
		t.Run(tc.name, func(t *testing.T) {
			got, gas := runtimeM5ccRunBits(t, classfile, tc.method, tc.args, tc.double, runtimeM5ccSingleGas)
			if got != tc.want {
				t.Fatalf("bits=%016x want=%016x gas=%d", got, tc.want, gas)
			}
			// Generated NaN payloads are intentionally canonicalized by the EVM.
			// Every finite/infinite/zero critical result must agree with both JVM 8 and 21.
			if !runtimeM5ccIsNaN(tc.want, tc.double) {
				for _, java := range runtimeM5ccJavaExecutables(t) {
					if oracle := runtimeM5ccOracleBits(t, java, oracleDir, tc); oracle != tc.want {
						t.Fatalf("%s oracle bits=%016x want=%016x", java, oracle, tc.want)
					}
				}
			}
		})
	}
}

func TestRuntimeM5ccSeededFiniteVectorsMatchJava(t *testing.T) {
	classfile := runtimeM5ccClass(t)
	oracleDir := runtimeM5ccOracle(t)
	java := runtimeM5ccJavaExecutables(t)[1]
	state := uint64(0x5cc70a2eba)
	methods := []string{"fadd", "fsub", "fmul", "fdiv", "frem", "dadd", "dsub", "dmul", "ddiv", "drem"}
	for i := 0; i < 200; i++ {
		state = state*6364136223846793005 + 1442695040888963407
		a := state
		state = state*6364136223846793005 + 1442695040888963407
		b := state
		method := methods[i%len(methods)]
		doubles := method[0] == 'd'
		if doubles {
			a &^= uint64(0x7ff) << 52 // force finite while retaining sign/fraction diversity
			b &^= uint64(0x7ff) << 52
			// Reinsert a bounded exponent selected independently from the fraction.
			a |= ((state >> 17) % 0x7ff) << 52
			b |= ((state >> 36) % 0x7ff) << 52
		} else {
			a = uint64(uint32(a))
			b = uint64(uint32(b))
			a &^= uint64(0xff) << 23
			b &^= uint64(0xff) << 23
			a |= ((state >> 11) % 0xff) << 23
			b |= ((state >> 29) % 0xff) << 23
		}
		if (method == "fdiv" || method == "frem" || method == "ddiv" || method == "drem") && runtimeM5ccMagnitude(b, doubles) == 0 {
			b = 1
		}
		var args []int32
		if doubles {
			args = runtimeM5ccDArgs(a, b)
		} else {
			args = runtimeM5ccFArgs(uint32(a), uint32(b))
		}
		tc := runtimeM5ccVector{fmt.Sprintf("seed-%02d", i), method, args, 0, doubles}
		want := runtimeM5ccOracleBits(t, java, oracleDir, tc)
		got, _ := runtimeM5ccRunBits(t, classfile, method, args, doubles, runtimeM5ccSingleGas)
		if runtimeM5ccNormalizeNaN(got, doubles) != runtimeM5ccNormalizeNaN(want, doubles) {
			t.Fatalf("%s a=%016x b=%016x got=%016x oracle=%016x", method, a, b, got, want)
		}
	}
}

func TestRuntimeM5ccFloatingDivideByZeroInClassInitIsAValue(t *testing.T) {
	classfile := compileJava(t, "RuntimeM5ccInit", `public class RuntimeM5ccInit {
		static float zero; static float infinity=1.0f/zero;
		public static int run(){return Float.floatToRawIntBits(infinity);}
	}`)
	result, err := Run(classfile, "run", nil, runtimeM5ccSingleGas)
	if err != nil || result.ExceptionClass != "" || uint32(result.Value) != 0x7f800000 {
		t.Fatalf("floating divide-by-zero initializer result=%+v err=%v, want +infinity value", result, err)
	}
}

func TestRuntimeM5ccKindsMissingOperandsAndGasBounds(t *testing.T) {
	classfile := runtimeM5ccClass(t)
	parsed := parseStaticsClass(t, classfile)
	fadd := parsed.method(t, "fadd", "(II)I")
	faddPC := verifyM5cbInstructionPC(t, fadd.code, 0x62, 0)

	codeOffset := fadd.codeNameOffset + 14
	wrong := append([]byte(nil), classfile...)
	wrong[codeOffset+faddPC] = 0x63 // dadd must reject two category-1 floats
	verifyM5cbAssertError(t, func() (Result, error) {
		return Run(wrong, "fadd", runtimeM5ccFArgs(0x3f800000, 0x40000000), runtimeM5ccSingleGas)
	}, "BytecodeError(uint256,uint256)", 14, uint64(faddPC))

	missing := append([]byte(nil), classfile...)
	secondLoad := verifyM5cbInstructionPC(t, fadd.code, 0x1b, 0)
	missing[codeOffset+secondLoad] = 0x62 // only the first converted float is present
	verifyM5cbAssertError(t, func() (Result, error) {
		return Run(missing, "fadd", runtimeM5ccFArgs(0x3f800000, 0x40000000), runtimeM5ccSingleGas)
	}, "BytecodeError(uint256,uint256)", 3, uint64(secondLoad))

	singles := []runtimeM5ccVector{
		{"fadd-gap", "fadd", runtimeM5ccFArgs(0x7f7fffff, 1), 0, false},
		{"fsub-cancel", "fsub", runtimeM5ccFArgs(0x00800001, 0x00800000), 0, false},
		{"fmul-underflow", "fmul", runtimeM5ccFArgs(1, 0x3f000000), 0, false},
		{"fdiv-underflow", "fdiv", runtimeM5ccFArgs(1, 0x7f7fffff), 0, false},
		{"frem-gap", "frem", runtimeM5ccFArgs(0x7f7fffff, 3), 0, false},
		{"dadd-gap", "dadd", runtimeM5ccDArgs(0x7fefffffffffffff, 1), 0, true},
		{"dsub-cancel", "dsub", runtimeM5ccDArgs(0x0010000000000001, 0x0010000000000000), 0, true},
		{"dmul-underflow", "dmul", runtimeM5ccDArgs(1, 0x3fe0000000000000), 0, true},
		{"ddiv-underflow", "ddiv", runtimeM5ccDArgs(1, 0x7fefffffffffffff), 0, true},
		{"drem-gap", "drem", runtimeM5ccDArgs(0x7fefffffffffffff, 3), 0, true},
	}
	for _, tc := range singles {
		_, gas := runtimeM5ccRunBits(t, classfile, tc.method, tc.args, tc.double, runtimeM5ccSingleGas)
		t.Logf("single worst-case %s gas=%d", tc.method, gas)
	}

	repeat := runtimeM5ccRepeatClass(t)
	for _, tc := range []runtimeM5ccVector{
		{"frem16", "frem16", runtimeM5ccFArgs(0x7f7fffff, 3), 0, false},
		{"drem16", "drem16", runtimeM5ccDArgs(0x7fefffffffffffff, 3), 0, false},
	} {
		result, err := Run(repeat, tc.method, tc.args, runtimeM5ccRepeatGas)
		if err != nil {
			t.Fatalf("%s: %v", tc.method, err)
		}
		if result.ExceptionClass != "" {
			t.Fatalf("%s exception=%s", tc.method, result.ExceptionClass)
		}
		t.Logf("16 repeated same-operand %s gas=%d", tc.method, result.GasUsed)
	}
}

func runtimeM5ccClass(t *testing.T) []byte {
	t.Helper()
	return compileJava(t, "RuntimeM5ccOps", `public strictfp class RuntimeM5ccOps {
		static long j(int h,int l){return ((long)h<<32)|(l&0xffffffffL);}
		static double d(int h,int l){return Double.longBitsToDouble(j(h,l));}
		static int part(double x,int p){long z=Double.doubleToRawLongBits(x);return p==0?(int)(z>>>32):(int)z;}
		public static int fadd(int a,int b){return Float.floatToRawIntBits(Float.intBitsToFloat(a)+Float.intBitsToFloat(b));}
		public static int fsub(int a,int b){return Float.floatToRawIntBits(Float.intBitsToFloat(a)-Float.intBitsToFloat(b));}
		public static int fmul(int a,int b){return Float.floatToRawIntBits(Float.intBitsToFloat(a)*Float.intBitsToFloat(b));}
		public static int fdiv(int a,int b){return Float.floatToRawIntBits(Float.intBitsToFloat(a)/Float.intBitsToFloat(b));}
		public static int frem(int a,int b){return Float.floatToRawIntBits(Float.intBitsToFloat(a)%Float.intBitsToFloat(b));}
		public static int dadd(int ah,int al,int bh,int bl,int p){return part(d(ah,al)+d(bh,bl),p);}
		public static int dsub(int ah,int al,int bh,int bl,int p){return part(d(ah,al)-d(bh,bl),p);}
		public static int dmul(int ah,int al,int bh,int bl,int p){return part(d(ah,al)*d(bh,bl),p);}
		public static int ddiv(int ah,int al,int bh,int bl,int p){return part(d(ah,al)/d(bh,bl),p);}
		public static int drem(int ah,int al,int bh,int bl,int p){return part(d(ah,al)%d(bh,bl),p);}
	}`)
}

func runtimeM5ccRepeatClass(t *testing.T) []byte {
	t.Helper()
	return compileJava(t, "RuntimeM5ccRepeat", `public strictfp class RuntimeM5ccRepeat {
		static long j(int h,int l){return ((long)h<<32)|(l&0xffffffffL);}
		public static int frem16(int a,int b){float x=Float.intBitsToFloat(a),y=Float.intBitsToFloat(b);int z=0;for(int i=0;i<16;i++)z^=Float.floatToRawIntBits(x%y);return z;}
		public static int drem16(int ah,int al,int bh,int bl){double x=Double.longBitsToDouble(j(ah,al)),y=Double.longBitsToDouble(j(bh,bl));int z=0;for(int i=0;i<16;i++){long r=Double.doubleToRawLongBits(x%y);z^=(int)(r^(r>>>32));}return z;}
	}`)
}

func runtimeM5ccFArgs(a, b uint32) []int32 { return []int32{int32(a), int32(b)} }

func runtimeM5ccDArgs(a, b uint64) []int32 {
	return []int32{int32(a >> 32), int32(a), int32(b >> 32), int32(b)}
}

func runtimeM5ccRunBits(t *testing.T, classfile []byte, method string, args []int32, doubles bool, gas uint64) (uint64, uint64) {
	t.Helper()
	if !doubles {
		result, err := Run(classfile, method, args, gas)
		if err != nil || result.ExceptionClass != "" {
			t.Fatalf("%s: result=%+v err=%v", method, result, err)
		}
		return uint64(uint32(result.Value)), result.GasUsed
	}
	hiArgs := append(append([]int32(nil), args...), 0)
	loArgs := append(append([]int32(nil), args...), 1)
	hi, err := Run(classfile, method, hiArgs, gas)
	if err != nil || hi.ExceptionClass != "" {
		t.Fatalf("%s high: result=%+v err=%v", method, hi, err)
	}
	lo, err := Run(classfile, method, loArgs, gas)
	if err != nil || lo.ExceptionClass != "" {
		t.Fatalf("%s low: result=%+v err=%v", method, lo, err)
	}
	return uint64(uint32(hi.Value))<<32 | uint64(uint32(lo.Value)), max(hi.GasUsed, lo.GasUsed)
}

func runtimeM5ccOracle(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	source := `public strictfp class RuntimeM5ccOracle {
		static long u(String s){return Long.parseUnsignedLong(s,16);} static float f(String s){return Float.intBitsToFloat((int)u(s));} static double d(String s){return Double.longBitsToDouble(u(s));}
		public static void main(String[] a){String o=a[0];long r=0;if(o.equals("fadd"))r=Float.floatToRawIntBits(f(a[1])+f(a[2]))&0xffffffffL;else if(o.equals("fsub"))r=Float.floatToRawIntBits(f(a[1])-f(a[2]))&0xffffffffL;else if(o.equals("fmul"))r=Float.floatToRawIntBits(f(a[1])*f(a[2]))&0xffffffffL;else if(o.equals("fdiv"))r=Float.floatToRawIntBits(f(a[1])/f(a[2]))&0xffffffffL;else if(o.equals("frem"))r=Float.floatToRawIntBits(f(a[1])%f(a[2]))&0xffffffffL;else if(o.equals("dadd"))r=Double.doubleToRawLongBits(d(a[1])+d(a[2]));else if(o.equals("dsub"))r=Double.doubleToRawLongBits(d(a[1])-d(a[2]));else if(o.equals("dmul"))r=Double.doubleToRawLongBits(d(a[1])*d(a[2]));else if(o.equals("ddiv"))r=Double.doubleToRawLongBits(d(a[1])/d(a[2]));else if(o.equals("drem"))r=Double.doubleToRawLongBits(d(a[1])%d(a[2]));System.out.printf("%016x%n",r);}
	}`
	path := filepath.Join(dir, "RuntimeM5ccOracle.java")
	if err := os.WriteFile(path, []byte(source), 0600); err != nil {
		t.Fatal(err)
	}
	cmd := exec.Command("javac", "--release", "8", "-d", dir, path)
	if out, err := cmd.CombinedOutput(); err != nil {
		t.Fatalf("compile oracle: %v\n%s", err, out)
	}
	return dir
}

func runtimeM5ccJavaExecutables(t *testing.T) []string {
	t.Helper()
	java8 := "/usr/lib/jvm/java-8-openjdk/bin/java"
	if _, err := os.Stat(java8); err != nil {
		t.Fatalf("required Java 8 oracle %s: %v", java8, err)
	}
	current, err := exec.LookPath("java")
	if err != nil {
		t.Fatalf("required current Java oracle: %v", err)
	}
	return []string{java8, current}
}

func runtimeM5ccOracleBits(t *testing.T, java, dir string, tc runtimeM5ccVector) uint64 {
	t.Helper()
	var a, b uint64
	if tc.double {
		a = uint64(uint32(tc.args[0]))<<32 | uint64(uint32(tc.args[1]))
		b = uint64(uint32(tc.args[2]))<<32 | uint64(uint32(tc.args[3]))
	} else {
		a, b = uint64(uint32(tc.args[0])), uint64(uint32(tc.args[1]))
	}
	cmd := exec.Command(java, "-cp", dir, "RuntimeM5ccOracle", tc.method, fmt.Sprintf("%x", a), fmt.Sprintf("%x", b))
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("oracle %s %s: %v\n%s", java, tc.method, err, out)
	}
	value, err := strconv.ParseUint(strings.TrimSpace(string(out)), 16, 64)
	if err != nil {
		t.Fatalf("oracle output %q: %v", out, err)
	}
	return value
}

func runtimeM5ccMagnitude(raw uint64, doubles bool) uint64 {
	if doubles {
		return raw & 0x7fffffffffffffff
	}
	return raw & 0x7fffffff
}

func runtimeM5ccIsNaN(raw uint64, doubles bool) bool {
	if doubles {
		return raw&0x7ff0000000000000 == 0x7ff0000000000000 && raw&0xfffffffffffff != 0
	}
	return raw&0x7f800000 == 0x7f800000 && raw&0x7fffff != 0
}

func runtimeM5ccNormalizeNaN(raw uint64, doubles bool) uint64 {
	if runtimeM5ccIsNaN(raw, doubles) {
		if doubles {
			return 0x7ff8000000000000
		}
		return 0x7fc00000
	}
	return raw
}
