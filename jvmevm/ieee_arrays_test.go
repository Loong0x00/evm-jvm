// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"strings"
	"testing"
)

const (
	runtimeM5cdSingleGas = uint64(20_000_000)
	runtimeM5cdFlowGas   = uint64(120_000_000)
	runtimeM5cdQuotaGas  = uint64(250_000_000)
)

func runtimeM5cdRun(t *testing.T, classfile []byte, method string, args []int32, want int32, gas uint64) Result {
	t.Helper()
	result, err := Run(classfile, method, args, gas)
	if err != nil || result.ExceptionClass != "" || result.Value != want || result.GasUsed == 0 || result.GasUsed > gas || len(result.RevertData) != 0 {
		t.Fatalf("%s%v = %+v/%v, want value %d within gas %d", method, args, result, err, want, gas)
	}
	return result
}

func runtimeM5cdRunClasses(t *testing.T, classes map[string][]byte, entry, method string, args []int32, want int32) Result {
	t.Helper()
	result, err := RunClasses(runtimeM5bbBundle(classes), entry, method, args, runtimeM5cdFlowGas)
	if err != nil || result.ExceptionClass != "" || result.Value != want || result.GasUsed == 0 || result.GasUsed > runtimeM5cdFlowGas || len(result.RevertData) != 0 {
		t.Fatalf("%s.%s%v = %+v/%v, want value %d", entry, method, args, result, err, want)
	}
	return result
}

func runtimeM5cdException(t *testing.T, classfile []byte, method string, args []int32, want string, gas uint64) {
	t.Helper()
	result, err := Run(classfile, method, args, gas)
	if err != nil || result.ExceptionClass != want || result.GasUsed == 0 || len(result.RevertData) != 36 {
		t.Fatalf("%s%v = %+v/%v, want %s", method, args, result, err, want)
	}
}

func runtimeM5cdBitsClass(t *testing.T) []byte {
	t.Helper()
	return compileJava(t, "RuntimeM5cdBits", `
public class RuntimeM5cdBits {
    static long bits(int hi,int lo){return ((long)hi<<32)|(lo&0xffffffffL);}
    public static int f(int raw){float[] a=new float[3];a[1]=Float.intBitsToFloat(raw);a[2]=a[1];return Float.floatToRawIntBits(a[2]);}
    public static int fDefault(){return Float.floatToRawIntBits((new float[1])[0]);}
    static long d(int hi,int lo){double[] a=new double[3];a[1]=Double.longBitsToDouble(bits(hi,lo));a[2]=a[1];return Double.doubleToRawLongBits(a[2]);}
    public static int dHi(int hi,int lo){return (int)(d(hi,lo)>>>32);}
    public static int dLo(int hi,int lo){return (int)d(hi,lo);}
    public static int dDefaultHi(){return (int)(Double.doubleToRawLongBits((new double[1])[0])>>>32);}
    public static int dDefaultLo(){return (int)Double.doubleToRawLongBits((new double[1])[0]);}
    public static int fPost(int raw){float[] a={Float.intBitsToFloat(raw)};float old=a[0]++;return Float.floatToRawIntBits(old)^Float.floatToRawIntBits(a[0]);}
    public static int dCompound(int hi,int lo){double[] a={Double.longBitsToDouble(bits(hi,lo))};a[0]+=1.0d;long x=Double.doubleToRawLongBits(a[0]);return (int)(x^(x>>>32));}
}`)
}

func TestRuntimeM5cdExactRawCellsDefaultsAndQuietJavaOracles(t *testing.T) {
	classfile := runtimeM5cdBitsClass(t)
	code := parseTestClass(t, classfile).methodCode(t, "f")
	for _, op := range []byte{0xbc, 0x30, 0x51} {
		if !bytes.Contains(code, []byte{op}) {
			t.Fatalf("f bytecode %x does not contain opcode 0x%02x", code, op)
		}
	}
	if !bytes.Contains(code, []byte{0xbc, 6}) {
		t.Fatalf("f bytecode %x has no newarray atype 6", code)
	}
	dcode := parseTestClass(t, classfile).methodCode(t, "d")
	for _, op := range []byte{0xbc, 0x31, 0x52} {
		if !bytes.Contains(dcode, []byte{op}) {
			t.Fatalf("d bytecode %x does not contain opcode 0x%02x", dcode, op)
		}
	}
	if !bytes.Contains(dcode, []byte{0xbc, 7}) {
		t.Fatalf("d bytecode %x has no newarray atype 7", dcode)
	}

	oracle := verifyM5ccNewOracle(t, classfile)
	for _, raw := range []uint32{
		0, 0x80000000, 0x3f800000, 1, 0x007fffff, 0x7f800000, 0xff800000,
		0x7fc12345, 0xffc54321,
	} {
		args := []int32{int32(raw)}
		want := oracle.int(t, "f", args)
		if uint32(want) != raw {
			t.Fatalf("Java 8/21 quiet float transport %08x returned %08x", raw, uint32(want))
		}
		runtimeM5cdRun(t, classfile, "f", args, int32(raw), runtimeM5cdSingleGas)
	}
	for _, raw := range []uint64{
		0, 0x8000000000000000, 0x3ff0000000000000, 1, 0x000fffffffffffff,
		0x7ff0000000000000, 0xfff0000000000000, 0x7ff8123456789abc, 0xfff8abcdef012345,
	} {
		args := []int32{int32(raw >> 32), int32(raw)}
		wantHi, wantLo := oracle.int(t, "dHi", args), oracle.int(t, "dLo", args)
		if got := uint64(uint32(wantHi))<<32 | uint64(uint32(wantLo)); got != raw {
			t.Fatalf("Java 8/21 quiet double transport %016x returned %016x", raw, got)
		}
		runtimeM5cdRun(t, classfile, "dHi", args, int32(raw>>32), runtimeM5cdSingleGas)
		runtimeM5cdRun(t, classfile, "dLo", args, int32(raw), runtimeM5cdSingleGas)
	}
	// Signaling-NaN transport is an EVM-only raw-cell guarantee: host JVM paths may quiet it.
	for _, raw := range []uint32{0x7f800001, 0xff812345} {
		runtimeM5cdRun(t, classfile, "f", []int32{int32(raw)}, int32(raw), runtimeM5cdSingleGas)
	}
	for _, raw := range []uint64{0x7ff0000000000001, 0xfff0123456789abc} {
		args := []int32{int32(raw >> 32), int32(raw)}
		runtimeM5cdRun(t, classfile, "dHi", args, int32(raw>>32), runtimeM5cdSingleGas)
		runtimeM5cdRun(t, classfile, "dLo", args, int32(raw), runtimeM5cdSingleGas)
	}
	runtimeM5cdRun(t, classfile, "fDefault", nil, 0, runtimeM5cdSingleGas)
	runtimeM5cdRun(t, classfile, "dDefaultHi", nil, 0, runtimeM5cdSingleGas)
	runtimeM5cdRun(t, classfile, "dDefaultLo", nil, 0, runtimeM5cdSingleGas)

	for _, tc := range []struct {
		method string
		args   []int32
	}{
		{"fPost", []int32{0x3f800000}},
		{"fPost", []int32{runtimeM5cbI32(0x80000000)}},
		{"dCompound", []int32{0x3ff00000, 0}},
		{"dCompound", []int32{runtimeM5cbI32(0x80000000), 0}},
	} {
		want := oracle.int(t, tc.method, tc.args)
		runtimeM5cdRun(t, classfile, tc.method, tc.args, want, runtimeM5cdSingleGas)
	}
}

func TestRuntimeM5cdFieldsConstructorsCallsNestedTypesAndCovariance(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"m5cd/I.java": `package m5cd; public interface I {
            float[] apply(float[] a,float x); default double[] pass(double[] a){return a;}
        }`,
		"m5cd/Base.java": `package m5cd; public class Base {
            protected final double[] values; Base(double seed){values=new double[2];values[0]=seed;}
            double[] virtual(double[] a){a[1]=values[0];return a;}
        }`,
		"m5cd/Impl.java": `package m5cd; public class Impl extends Base implements I {
            Impl(double seed){super(seed);} private float[] special(float[] a){a[0]+=2.0f;return a;}
            public float[] apply(float[] a,float x){a[0]+=x;return special(a);}
        }`,
		"m5cd/Root.java": `package m5cd; public class Root {
            static final float[] STATIC=init(); static float[] init(){float[] a=new float[2];a[0]=1.5f;return a;}
            static int fold(double x){long b=Double.doubleToRawLongBits(x);return (int)(b^(b>>>32));}
            public static int calls(int n){Impl x=new Impl((double)n);I i=x;float[] f=new float[1];double[] d=new double[2];
                i.apply(f,(float)n);x.virtual(d);i.pass(d);STATIC[1]=f[0];return Float.floatToRawIntBits(STATIC[0])
                    ^Float.floatToRawIntBits(STATIC[1])^fold(d[1]);}
            public static int types(int n){float[][] a=new float[2][3];float[][][] p=new float[1][2][];
                Object[] objects=a;Cloneable[] clones=a;java.io.Serializable serial=a;
                objects[0]=new float[]{Float.intBitsToFloat(n)};a[1][2]=2.0f;Object leaf=a[0];
                Object ints=new int[0], doubles=new double[0][0];
                return a.length*100+a[0].length*10+p[0].length+(leaf instanceof float[]?4:0)
                    +(leaf instanceof Object[]?8:0)+(a instanceof Object[]?16:0)+(a instanceof Cloneable[]?32:0)
                    +(serial!=null?64:0)+(clones==a?128:0)+(ints instanceof float[]?256:0)
                    +(doubles instanceof float[][]?512:0)+Float.floatToRawIntBits(a[0][0]);}
            public static int badStore(){Object[] x=new float[1][];x[0]=new double[1];return 0;}
            public static int badCast(){Object x=new double[1];return ((float[])x).length;}
        }`,
	})
	bundle := runtimeM5bbBundle(classes)
	oracle := verifyM5ccNewOracle(t, bundle...)
	for _, tc := range []struct {
		method string
		args   []int32
	}{
		{"calls", []int32{0}}, {"calls", []int32{7}}, {"calls", []int32{-3}},
		{"types", []int32{0x3f000000}}, {"types", []int32{runtimeM5cbI32(0x80000000)}},
	} {
		want := oracle.intClass(t, "m5cd.Root", tc.method, tc.args)
		runtimeM5cdRunClasses(t, classes, "m5cd/Root", tc.method, tc.args, want)
	}

	root := classes["m5cd/Root"]
	runtimeM5cdException(t, root, "badStore", nil, "java.lang.ArrayStoreException", runtimeM5cdFlowGas)
	runtimeM5cdException(t, root, "badCast", nil, "java.lang.ClassCastException", runtimeM5cdFlowGas)

	code := parseTestClass(t, root).methodCode(t, "calls")
	var interfaceCounts []byte
	for pc := 0; pc < len(code); pc += verifyM5baInstructionWidth(t, code, pc) {
		if code[pc] == 0xb9 {
			interfaceCounts = append(interfaceCounts, code[pc+3])
		}
	}
	// apply consumes receiver + float[] + scalar float; pass consumes receiver + double[].
	// Both FP array references remain category-one values despite their leaf type.
	if !bytes.Equal(interfaceCounts, []byte{3, 2}) {
		t.Fatalf("invokeinterface counts in %x = %v, want [3 2]", code, interfaceCounts)
	}
}

func TestRuntimeM5cdNullBoundsEvaluationAndInitialization(t *testing.T) {
	classfile := compileJava(t, "RuntimeM5cdErrors", `
public class RuntimeM5cdErrors {
    static int zero(){return 0;}
    public static int negative(int n){return new double[n].length;}
    public static int nullF(int i){float[] a=null;return (int)a[i];}
    public static int nullDStore(int i){double[] a=null;a[i]=1.0d;return 0;}
    public static int boundsF(int i){return (int)(new float[2])[i];}
    public static int boundsDStore(int i){double[] a=new double[2];a[i]=1.0d;return 0;}
    public static int integerValueFirst(int ignored){float[] a=null;a[99]=(float)(1/zero());return 0;}
    public static int fpValueFirst(int ignored){double[] a=null;a[99]=1.0d/0.0d;return 0;}
}`)
	for _, tc := range []struct {
		method string
		arg    int32
		want   string
	}{
		{"negative", -1, "java.lang.NegativeArraySizeException"},
		{"nullF", -1, "java.lang.NullPointerException"},
		{"nullDStore", 99, "java.lang.NullPointerException"},
		{"boundsF", -1, "java.lang.ArrayIndexOutOfBoundsException"},
		{"boundsF", 2, "java.lang.ArrayIndexOutOfBoundsException"},
		{"boundsDStore", -1, "java.lang.ArrayIndexOutOfBoundsException"},
		{"boundsDStore", 2, "java.lang.ArrayIndexOutOfBoundsException"},
		{"integerValueFirst", 0, "java.lang.ArithmeticException"},
		{"fpValueFirst", 0, "java.lang.NullPointerException"},
	} {
		t.Run(tc.method, func(t *testing.T) {
			runtimeM5cdException(t, classfile, tc.method, []int32{tc.arg}, tc.want, runtimeM5cdSingleGas)
		})
	}

	for name, source := range map[string]string{
		"RuntimeM5cdInit": `public class RuntimeM5cdInit {static final double[] A=make();static int count;
            static double[] make(){count++;double[] a=new double[1];a[0]=1.5d;return a;}
            public static int run(){return (int)A[0]+count;}}`,
		"RuntimeM5cdInitFailure": `public class RuntimeM5cdInitFailure {static int z(){return 0;}static float[] A=make();
            static float[] make(){float[] a=new float[1];a[0]=1/z();return a;}public static int run(){return 0;}}`,
	} {
		t.Run(name, func(t *testing.T) {
			cf := compileJava(t, name, source)
			if strings.HasSuffix(name, "Failure") {
				runtimeM5cdException(t, cf, "run", nil, "java.lang.ExceptionInInitializerError", runtimeM5cdFlowGas)
			} else {
				runtimeM5cdRun(t, cf, "run", nil, 2, runtimeM5cdFlowGas)
			}
		})
	}
}

func TestRuntimeM5cdExactOpcodeKindsRanksAndMalformedAtypes(t *testing.T) {
	template := compileJava(t, "RuntimeM5cdRaw", `public class RuntimeM5cdRaw {
        public static int run(){float[] f=new float[1];double[] d=new double[1];f[0]=1.25f;d[0]=1.25d;return (int)(f[0]+d[0]);}
        public static int room(){int x=0;x++;x++;x++;x++;x++;x++;x++;x++;x++;x++;return x;}
        public static int nested(){return new double[1][].length;}
    }`)
	parsed := parseTestClass(t, template)
	floatIndex, doubleIndex := 0, 0
	for i, tag := range parsed.tags {
		if tag == 4 && floatIndex == 0 {
			floatIndex = i
		}
		if tag == 6 && doubleIndex == 0 {
			doubleIndex = i
		}
	}
	if floatIndex == 0 || floatIndex > 255 || doubleIndex == 0 {
		t.Fatalf("missing usable float/double constants: float=%d double=%d", floatIndex, doubleIndex)
	}
	ldcF := []byte{0x12, byte(floatIndex)}
	ldcD := []byte{0x14, byte(doubleIndex >> 8), byte(doubleIndex)}
	doubleArrayClass := runtimeM4eClassIndex(t, template, "[D")
	cases := []struct {
		name           string
		code           []byte
		maxStack       uint16
		signature      string
		codeNumber, pc uint64
	}{
		{"faload-int-array", []byte{0x04, 0xbc, 10, 0x03, 0x30, 0x8b, 0xac}, 2, "ReferenceError(uint256,uint256)", 1, 4},
		{"iaload-float-array", []byte{0x04, 0xbc, 6, 0x03, 0x2e, 0xac}, 2, "ReferenceError(uint256,uint256)", 1, 4},
		{"daload-double-rank-two", []byte{0x04, 0xbd, byte(doubleArrayClass >> 8), byte(doubleArrayClass), 0x03, 0x31, 0x8e, 0xac}, 2, "ReferenceError(uint256,uint256)", 1, 5},
		{"aastore-float-leaf", []byte{0x04, 0xbc, 6, 0x03, 0x01, 0x53, 0x03, 0xac}, 3, "ReferenceError(uint256,uint256)", 1, 5},
		{"fastore-int-value", []byte{0x04, 0xbc, 6, 0x03, 0x04, 0x51, 0x03, 0xac}, 3, "BytecodeError(uint256,uint256)", 14, 5},
		{"dastore-float-value", append([]byte{0x04, 0xbc, 7, 0x03}, append(ldcF, 0x52, 0x03, 0xac)...), 4, "BytecodeError(uint256,uint256)", 14, 6},
		{"faload-wrong-ref-kind", []byte{0x03, 0x03, 0x30, 0x8b, 0xac}, 2, "BytecodeError(uint256,uint256)", 14, 2},
		{"faload-underflow", []byte{0x01, 0x30, 0x8b, 0xac}, 2, "BytecodeError(uint256,uint256)", 3, 1},
		{"dastore-underflow", []byte{0x01, 0x03, 0x52, 0x03, 0xac}, 4, "BytecodeError(uint256,uint256)", 3, 2},
		{"dastore-word-capacity", append([]byte{0x04, 0xbc, 7, 0x03}, append(ldcD, 0x52, 0x03, 0xac)...), 3, "BytecodeError(uint256,uint256)", 9, 4},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			cf := runtimeM5bbReplaceCode(t, template, "room", tc.code, tc.maxStack, 2)
			result, err := Run(cf, "room", nil, 30_000_000)
			assertSolidityError(t, result, err, tc.signature, tc.codeNumber, tc.pc)
		})
	}
	for _, atype := range []byte{0, 3, 12, 255} {
		t.Run("atype", func(t *testing.T) {
			cf := runtimeM5bbReplaceCode(t, template, "room", []byte{0x03, 0xbc, atype, 0xbe, 0xac}, 1, 1)
			result, err := Run(cf, "room", nil, runtimeM5cdSingleGas)
			assertSolidityError(t, result, err, "ArrayError(uint256,uint256)", 1, 1)
		})
	}
}

func TestRuntimeM5cdInterleavedHeapQuotasResetAndRank255(t *testing.T) {
	classfile := compileJava(t, "RuntimeM5cdHeap", `public class RuntimeM5cdHeap {
        static int fold(double x){long b=Double.doubleToRawLongBits(x);return (int)(b^(b>>>32));}
        public static int floatFirst(){float[] f=new float[1];double[] d=new double[1];long[] j=new long[1];int[] i=new int[1];Object[] r=new Object[1];Object o=new Object();
            f[0]=1.5f;d[0]=2.5d;j[0]=3;i[0]=4;r[0]=o;return Float.floatToRawIntBits(f[0])^fold(d[0])^(int)j[0]^i[0]^(r[0]==o?1:0);}
        public static int doubleFirst(){double[] d=new double[1];Object o=new Object();float[] f=new float[1];Object[] r=new Object[1];long[] j=new long[1];int[] i=new int[1];
            d[0]=-0.0d;f[0]=-0.0f;r[0]=o;j[0]=7;i[0]=9;return fold(d[0])^Float.floatToRawIntBits(f[0])^(int)j[0]^i[0]^(r[0]==o?1:0);}
        public static int maxArrays(){for(int i=0;i<1024;i++){if((i&1)==0){float[] a=new float[0];}else{double[] a=new double[0];}}return 1024;}
        public static int tooManyArrays(){for(int i=0;i<1025;i++){double[] a=new double[0];}return 0;}
        public static int maxElements(){int n=0;for(int i=0;i<4;i++)n+=new double[65536].length;return n;}
        public static int mixedElements(){int n=0;for(int i=0;i<4;i++){if((i&1)==0)n+=new float[65536].length;else n+=new long[65536].length;}return n;}
        public static int tooManyElements(){for(int i=0;i<4;i++){double[] a=new double[65536];}return new float[1].length;}
        public static int objectsIndependent(){Object o=new Object();for(int i=0;i<1024;i++){float[] a=new float[0];}return o!=null?1:0;}
    }`)
	oracle := verifyM5ccNewOracle(t, classfile)
	for _, method := range []string{"floatFirst", "doubleFirst"} {
		runtimeM5cdRun(t, classfile, method, nil, oracle.int(t, method, nil), runtimeM5cdFlowGas)
	}
	for invocation := 0; invocation < 2; invocation++ {
		runtimeM5cdRun(t, classfile, "maxArrays", nil, 1024, runtimeM5cdQuotaGas)
	}
	for _, method := range []string{"maxElements", "mixedElements"} {
		result := runtimeM5cdRun(t, classfile, method, nil, 262144, runtimeM5cdQuotaGas)
		t.Logf("M5c-d %s gas=%d limit=%d", method, result.GasUsed, runtimeM5cdQuotaGas)
	}
	runtimeM5cdRun(t, classfile, "objectsIndependent", nil, 1, runtimeM5cdQuotaGas)
	for _, method := range []string{"tooManyArrays", "tooManyElements"} {
		runtimeM5cdException(t, classfile, method, nil, "java.lang.OutOfMemoryError", runtimeM5cdQuotaGas)
	}
	result, err := Run(classfile, "maxElements", nil, 300_000)
	if err == nil || !strings.Contains(err.Error(), "out of gas") || result.ExceptionClass != "" {
		t.Fatalf("double-array OOG = %+v/%v, want unwrapped EVM OOG", result, err)
	}

	rank255 := compileJava(t, "RuntimeM5cdRank255", `public class RuntimeM5cdRank255 {
        public static int run(){return new float`+strings.Repeat("[1]", 255)+`.length;}}`)
	pc := runtimeM5bbOpcodePC(t, rank255, "run", 0xc5)
	code := parseTestClass(t, rank255).methodCode(t, "run")
	if code[pc+3] != 255 {
		t.Fatalf("multianewarray dimensions=%d, want 255", code[pc+3])
	}
	runtimeM5cdRun(t, rank255, "run", nil, 1, runtimeM5cdQuotaGas)
}
