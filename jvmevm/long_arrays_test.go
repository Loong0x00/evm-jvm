// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"sort"
	"strings"
	"testing"
)

const runtimeM5bbGasLimit = uint64(250_000_000)

func runtimeM5bbBundle(classes map[string][]byte) [][]byte {
	names := make([]string, 0, len(classes))
	for name := range classes {
		names = append(names, name)
	}
	sort.Strings(names)
	bundle := make([][]byte, 0, len(names))
	for _, name := range names {
		bundle = append(bundle, classes[name])
	}
	return bundle
}

func runtimeM5bbWantValue(t *testing.T, classes map[string][]byte, entry, method string, args ...int32) {
	t.Helper()
	bundle := runtimeM5bbBundle(classes)
	want := verifyM5baJava8Int(t, bundle, strings.ReplaceAll(entry, "/", "."), method, args)
	result, err := RunClasses(bundle, entry, method, args, runtimeM5bbGasLimit)
	if err != nil || result.ExceptionClass != "" || result.Value != want || result.GasUsed == 0 || len(result.RevertData) != 0 {
		t.Fatalf("%s.%s%v = %+v/%v, want Java 8 value %d", entry, method, args, result, err, want)
	}
}

func runtimeM5bbWantException(t *testing.T, classfile []byte, method, want string, args ...int32) {
	t.Helper()
	verifyM5baJava8Outcome(t, [][]byte{classfile}, verifyM5baClassName(t, classfile), method, args, "exception="+want)
	result, err := Run(classfile, method, args, runtimeM5bbGasLimit)
	if err != nil || result.ExceptionClass != want || result.GasUsed == 0 || len(result.RevertData) != 36 {
		t.Fatalf("%s%v = %+v/%v, want Java 8 exception %s", method, args, result, err, want)
	}
}

func runtimeM5bbOpcodePC(t *testing.T, classfile []byte, method string, opcode byte) int {
	t.Helper()
	code := parseTestClass(t, classfile).methodCode(t, method)
	pc := bytes.IndexByte(code, opcode)
	if pc < 0 {
		t.Fatalf("%s bytecode %x has no opcode 0x%02x", method, code, opcode)
	}
	return pc
}

func runtimeM5bbReplaceCode(t *testing.T, classfile []byte, method string, code []byte, maxStack, maxLocals uint16) []byte {
	t.Helper()
	return runtimeM5baReplaceMethodCode(t, classfile, method, code, maxStack, maxLocals)
}

func TestRuntimeM5bbFullWidthLoadsStoresDefaultsAndCategory2Expressions(t *testing.T) {
	classfile := compileJava(t, "RuntimeM5bbBits", `
public class RuntimeM5bbBits {
    static int fold(long x) { return (int)(x ^ (x >>> 32)); }
    public static int run(int n) {
        long[] a = new long[5]; long[] alias = a; long[] other = new long[0];
        a[0] = 0xfedcba9876543210L;
        a[1] = Long.MIN_VALUE;
        a[2] = Long.MAX_VALUE;
        a[3] = ((long)n << 40) | 0x89abcdefL;
        long before = a[0]++;
        a[1] += 0x123456789L;
        long after = ++a[2];
        return fold(before) ^ fold(a[0]) ^ fold(a[1]) ^ fold(after) ^ fold(a[3])
            ^ fold(a[4]) ^ (alias == a ? 0x100 : 0) ^ (other == a ? 0x200 : 0);
    }
}`)
	code := parseTestClass(t, classfile).methodCode(t, "run")
	for _, opcode := range []byte{0xbc, 0x2f, 0x50, 0x5e} {
		if !bytes.Contains(code, []byte{opcode}) {
			t.Fatalf("run bytecode %x does not exercise opcode 0x%02x", code, opcode)
		}
	}
	if pc := bytes.Index(code, []byte{0xbc, 11}); pc < 0 {
		t.Fatalf("run bytecode %x has no newarray atype 11", code)
	}
	classes := map[string][]byte{"RuntimeM5bbBits": classfile}
	for _, n := range []int32{0, 1, -1, 0x123456, -2147483648, 2147483647} {
		runtimeM5bbWantValue(t, classes, "RuntimeM5bbBits", "run", n)
	}
}

func TestRuntimeM5bbArrayReferencesAcrossFieldsAndAllCallModes(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"m5bb/I.java": `package m5bb; public interface I {
            long[] apply(long[] a,long x);
            default long[] pass(long[] a){return a;}
        }`,
		"m5bb/Base.java": `package m5bb; public class Base {
            protected final long[] values;
            Base(long seed){values=new long[2];values[0]=seed;}
            long[] virtual(long[] a){a[1]=values[0];return a;}
        }`,
		"m5bb/Impl.java": `package m5bb; public class Impl extends Base implements I {
            Impl(long seed){super(seed);}
            private long[] special(long[] a){a[0]^=0x1122334455667788L;return a;}
            public long[] apply(long[] a,long x){a[0]+=x;return special(a);}
            static long[] direct(long[] a,long x){a[1]=x;return a;}
        }`,
		"m5bb/Root.java": `package m5bb; public class Root {
            static final long[] STATIC=init();
            static long[] init(){long[] a=new long[2];a[0]=0x1020304050607080L;return a;}
            static int fold(long x){return (int)(x^(x>>>32));}
            public static int run(int n){long seed=((long)n<<36)|7L;Impl x=new Impl(seed);I i=x;
                long[] a=new long[2];Impl.direct(a,0xfedcba9876543210L);x.virtual(a);i.apply(a,seed);i.pass(a);
                STATIC[1]=a[0]+a[1];return fold(a[0])+fold(a[1])+fold(STATIC[0])+fold(STATIC[1]);}
        }`,
	})
	rootCode := parseTestClass(t, classes["m5bb/Root"]).methodCode(t, "run")
	interfacePC := bytes.IndexByte(rootCode, 0xb9)
	if interfacePC < 0 {
		t.Fatalf("run bytecode %x has no invokeinterface", rootCode)
	}
	// apply([JJ)[J consumes receiver(1) + array ref(1) + scalar long(2).
	if rootCode[interfacePC+3] != 4 {
		t.Fatalf("invokeinterface count=%d, want four JVM words", rootCode[interfacePC+3])
	}
	for _, n := range []int32{0, 7, -3, 2147483647} {
		runtimeM5bbWantValue(t, classes, "m5bb/Root", "run", n)
	}
}

func TestRuntimeM5bbNestedTypesCovarianceMarkersAndArrayStore(t *testing.T) {
	classfile := compileJava(t, "RuntimeM5bbTypes", `
public class RuntimeM5bbTypes {
    public static int types(int n) {
        long[][] a=new long[2][3]; long[][][] partial=new long[1][2][];
        Object[] objects=a; Cloneable[] clones=a; java.io.Serializable serial=a;
        objects[0]=new long[]{0x100000002L}; a[1][2]=((long)n<<35)|9L;
        Object leaf=a[0]; Object ints=new int[0]; Object unlike=new int[0][0];
        return a.length*100+a[0].length*10+partial[0].length
            +(leaf instanceof long[]?4:0)+(leaf instanceof Object[]?8:0)
            +(a instanceof Object[]?16:0)+(a instanceof Cloneable[]?32:0)
            +(serial!=null?64:0)+(clones==a?128:0)+(ints instanceof long[]?256:0)
            +(unlike instanceof long[][]?512:0)+(int)(a[0][0]+a[1][2]);
    }
    public static int badStore(){Object[] x=new long[1][];x[0]=new int[1];return 0;}
    public static int badCast(){Object x=new int[1];return ((long[])x).length;}
}`)
	classes := map[string][]byte{"RuntimeM5bbTypes": classfile}
	for _, n := range []int32{0, 5, -7} {
		runtimeM5bbWantValue(t, classes, "RuntimeM5bbTypes", "types", n)
	}
	runtimeM5bbWantException(t, classfile, "badStore", "java.lang.ArrayStoreException")
	runtimeM5bbWantException(t, classfile, "badCast", "java.lang.ClassCastException")
}

func TestRuntimeM5bbJavaErrorsEvaluationOrderAndInitialization(t *testing.T) {
	classfile := compileJava(t, "RuntimeM5bbErrors", `
public class RuntimeM5bbErrors {
    static int zero(){return 0;}
    public static int negative(int n){return new long[n].length;}
    public static int nullRead(int i){long[] a=null;return (int)a[i];}
    public static int nullStore(int i){long[] a=null;a[i]=1L;return 0;}
    public static int boundsRead(int i){return (int)(new long[2])[i];}
    public static int boundsStore(int i){long[] a=new long[2];a[i]=1L;return 0;}
    public static int valueFirst(){long[] a=null;a[99]=1L/(long)zero();return 0;}
}`)
	for _, tc := range []struct {
		method string
		arg    int32
		want   string
	}{
		{"negative", -1, "java.lang.NegativeArraySizeException"},
		{"nullRead", -1, "java.lang.NullPointerException"},
		{"nullStore", 99, "java.lang.NullPointerException"},
		{"boundsRead", -1, "java.lang.ArrayIndexOutOfBoundsException"},
		{"boundsRead", 2, "java.lang.ArrayIndexOutOfBoundsException"},
		{"boundsStore", -1, "java.lang.ArrayIndexOutOfBoundsException"},
		{"boundsStore", 2, "java.lang.ArrayIndexOutOfBoundsException"},
	} {
		t.Run(tc.method, func(t *testing.T) { runtimeM5bbWantException(t, classfile, tc.method, tc.want, tc.arg) })
	}
	runtimeM5bbWantException(t, classfile, "valueFirst", "java.lang.ArithmeticException")

	for name, source := range map[string]string{
		"RuntimeM5bbInitValue": `public class RuntimeM5bbInitValue {
            static final long[] A=make();static int count;
            static long[] make(){count++;int seen=peek();long[] a=new long[1];a[0]=0x123456789abcdef0L+seen;return a;}
            static int peek(){return A==null?4:8;}
            public static int run(){long x=A[0];return (int)(x^(x>>>32))+count;}}`,
		"RuntimeM5bbInitFailure": `public class RuntimeM5bbInitFailure {
            static int z(){return 0;}static long[] A=make();static long[] make(){long[] a=new long[1];a[0]=1L/z();return a;}
            public static int run(){return 0;}}`,
	} {
		t.Run(name, func(t *testing.T) {
			cf := compileJava(t, name, source)
			if strings.HasSuffix(name, "Failure") {
				runtimeM5bbWantException(t, cf, "run", "java.lang.ExceptionInInitializerError")
			} else {
				runtimeM5bbWantValue(t, map[string][]byte{name: cf}, name, "run")
			}
		})
	}
}

func TestRuntimeM5bbInterleavedFirstAllocationsIdentityQuotasAndReset(t *testing.T) {
	classfile := compileJava(t, "RuntimeM5bbHeap", `
public class RuntimeM5bbHeap {
    static int fold(long x){return (int)(x^(x>>>32));}
    public static int objectFirst(){Object o=new Object();long[] l=new long[1];int[] i=new int[1];Object[] r=new Object[1];
        l[0]=0xfedcba9876543210L;i[0]=7;r[0]=o;return fold(l[0])+i[0]+(r[0]==o?1:0);}
    public static int longFirst(){long[] l=new long[1];Object o=new Object();Object[] r=new Object[1];int[] i=new int[1];
        l[0]=0x8123456789abcdefL;r[0]=o;i[0]=9;return fold(l[0])+i[0]+(r[0]==o?1:0);}
    public static int intFirst(){int[] i=new int[1];long[] l=new long[1];Object[] r=new Object[1];Object o=new Object();
        i[0]=13;l[0]=0x7fffffff00000001L;r[0]=o;return i[0]+fold(l[0])+(r[0]==o?1:0);}
    public static int refFirst(){Object[] r=new Object[1];long[] l=new long[1];Object o=new Object();int[] i=new int[1];
        r[0]=o;l[0]=Long.MIN_VALUE;i[0]=11;return fold(l[0])+i[0]+(r[0]==o?1:0);}
    public static int identities(){long[] a=new long[0],b=new long[0];return a!=b?1:0;}
    public static int maxArrays(){for(int i=0;i<1024;i++){if((i&1)==0){long[] a=new long[0];}else{int[] a=new int[0];}}return 1024;}
    public static int tooManyArrays(){for(int i=0;i<1025;i++){long[] a=new long[0];}return 0;}
    public static int maxElements(){int n=0;for(int i=0;i<4;i++)n+=new long[65536].length;return n;}
    public static int mixedElements(){int n=0;for(int i=0;i<4;i++){if((i&1)==0)n+=new long[65536].length;else n+=new int[65536].length;}return n;}
    public static int tooManyElements(){for(int i=0;i<4;i++){long[] a=new long[65536];}return new long[1].length;}
    public static int tooManyMixedElements(){for(int i=0;i<4;i++){if((i&1)==0){long[] a=new long[65536];}else{int[] a=new int[65536];}}return new long[1].length;}
    public static int tooLong(){return new long[65537].length;}
    public static int objectsIndependent(){Object o=new Object();for(int i=0;i<1024;i++){long[] a=new long[0];}return o!=null?1:0;}
}`)
	classes := map[string][]byte{"RuntimeM5bbHeap": classfile}
	for _, method := range []string{"objectFirst", "longFirst", "intFirst", "refFirst", "identities"} {
		runtimeM5bbWantValue(t, classes, "RuntimeM5bbHeap", method)
	}
	for invocation := 0; invocation < 2; invocation++ {
		runtimeM5bbWantValue(t, classes, "RuntimeM5bbHeap", "maxArrays")
	}
	for _, method := range []string{"maxElements", "mixedElements", "objectsIndependent"} {
		runtimeM5bbWantValue(t, classes, "RuntimeM5bbHeap", method)
	}
	for _, method := range []string{"tooManyArrays", "tooManyElements", "tooManyMixedElements", "tooLong"} {
		result, err := Run(classfile, method, nil, runtimeM5bbGasLimit)
		if err != nil || result.ExceptionClass != "java.lang.OutOfMemoryError" {
			t.Fatalf("%s = %+v/%v, want logical Java OOM", method, result, err)
		}
	}
	oog, err := Run(classfile, "maxElements", nil, 300_000)
	if err == nil || !strings.Contains(err.Error(), "out of gas") || oog.ExceptionClass != "" {
		t.Fatalf("long-array OOG = %+v/%v, want unwrapped EVM OOG", oog, err)
	}
}

func TestRuntimeM5bbExactOpcodeKindsPrefixAndRootProfile(t *testing.T) {
	template := compileJava(t, "RuntimeM5bbRaw", `public class RuntimeM5bbRaw {
        public static int run(){long[] a=new long[2];a[0]=0x1122334455667788L;return (int)a[0];}
        public static int room(){int x=0;x++;x++;x++;x++;x++;x++;x++;x++;x++;x++;
            x++;x++;x++;x++;x++;x++;x++;x++;x++;x++;return x;}
        public static int nested(){return new long[1][].length;}
        public static int takes(long[] a){return a==null?1:0;}
    }`)
	longIndex := 0
	for i, tag := range parseTestClass(t, template).tags {
		if tag == 5 {
			longIndex = i
			break
		}
	}
	if longIndex == 0 {
		t.Fatal("template has no CONSTANT_Long")
	}
	ldc := []byte{0x14, byte(longIndex >> 8), byte(longIndex)}
	longArrayClass := runtimeM4eClassIndex(t, template, "[J")
	cases := []struct {
		name           string
		code           []byte
		maxStack       uint16
		signature      string
		codeNumber, pc uint64
	}{
		{"laload-int-array", []byte{0x04, 0xbc, 10, 0x03, 0x2f, 0x88, 0xac}, 2, "ReferenceError(uint256,uint256)", 1, 4},
		{"iaload-long-array", []byte{0x04, 0xbc, 11, 0x03, 0x2e, 0xac}, 2, "ReferenceError(uint256,uint256)", 1, 4},
		{"lastore-int-array", append([]byte{0x04, 0xbc, 10, 0x03}, append(ldc, 0x50, 0x03, 0xac)...), 4, "ReferenceError(uint256,uint256)", 1, 7},
		{"laload-long-rank-two", []byte{0x04, 0xbd, byte(longArrayClass >> 8), byte(longArrayClass), 0x03, 0x2f, 0x88, 0xac}, 2, "ReferenceError(uint256,uint256)", 1, 5},
		{"aastore-long-leaf", []byte{0x04, 0xbc, 11, 0x03, 0x01, 0x53, 0x03, 0xac}, 3, "ReferenceError(uint256,uint256)", 1, 5},
		{"lastore-int-value", []byte{0x04, 0xbc, 11, 0x03, 0x04, 0x50, 0x03, 0xac}, 4, "BytecodeError(uint256,uint256)", 14, 5},
		{"lastore-word-capacity", append([]byte{0x04, 0xbc, 11, 0x03}, append(ldc, 0x50, 0x03, 0xac)...), 3, "BytecodeError(uint256,uint256)", 9, 4},
		{"laload-underflow", []byte{0x01, 0x2f, 0x88, 0xac}, 2, "BytecodeError(uint256,uint256)", 3, 1},
		{"lastore-underflow", []byte{0x01, 0x03, 0x50, 0x03, 0xac}, 4, "BytecodeError(uint256,uint256)", 3, 2},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			cf := runtimeM5bbReplaceCode(t, template, "room", tc.code, tc.maxStack, 2)
			result, err := Run(cf, "room", nil, 30_000_000)
			assertSolidityError(t, result, err, tc.signature, tc.codeNumber, tc.pc)
		})
	}

	prefixCode := append([]byte{0x08, 0x04, 0xbc, 11, 0x03}, ldc...)
	prefixCode = append(prefixCode, 0x50, 0x04, 0xbc, 11, 0x03)
	prefixCode = append(prefixCode, ldc...)
	prefixCode = append(prefixCode, 0x50) // leave the original int prefix below the loaded long
	prefixCode = append(prefixCode, 0x04, 0xbc, 11, 0x03, 0x2f, 0x88, 0x60, 0xac)
	// The first two throwaway arrays also exercise whole-long consumption by lastore.
	prefix := runtimeM5bbReplaceCode(t, template, "room", prefixCode, 8, 2)
	result, err := Run(prefix, "room", nil, 40_000_000)
	if err != nil || result.ExceptionClass != "" || result.Value != 5 {
		t.Fatalf("prefix result = %+v/%v, want preserved value 5", result, err)
	}

	result, err = Run(template, "takes", []int32{0}, 20_000_000)
	runtimeM5baAssertMethodError(t, result, err, 11)
}

func TestRuntimeM5bbRank255LongArrayIsIterative(t *testing.T) {
	classfile := compileJava(t, "RuntimeM5bbRank255", `public class RuntimeM5bbRank255 {
        public static int run(){return new long`+strings.Repeat("[1]", 255)+`.length;}
    }`)
	pc := runtimeM5bbOpcodePC(t, classfile, "run", 0xc5)
	parsed := parseTestClass(t, classfile)
	if parsed.methodCode(t, "run")[pc+3] != 255 {
		t.Fatalf("multianewarray dimensions=%d, want 255", parsed.methodCode(t, "run")[pc+3])
	}
	result, err := Run(classfile, "run", nil, runtimeM5bbGasLimit)
	if err != nil || result.ExceptionClass != "" || result.Value != 1 {
		t.Fatalf("rank255 result = %+v/%v, want 1", result, err)
	}
}
