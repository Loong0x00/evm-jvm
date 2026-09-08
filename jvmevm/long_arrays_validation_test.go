// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"errors"
	"fmt"
	"sort"
	"strconv"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/core/vm"
)

const (
	verifyM5bbGasLimit         = uint64(180_000_000)
	verifyM5bbCapacityGasLimit = uint64(250_000_000)
	verifyM5bbNewarray         = byte(0xbc)
	verifyM5bbLaload           = byte(0x2f)
	verifyM5bbLastore          = byte(0x50)
)

// These verifier-only probes use bounded trusted Java 8 inputs for valid
// programs. Hand-mutated classfiles isolate EVM validation and exact-PC rules;
// they are not claims that this subset implements the complete JVM verifier.
// Production still receives only opaque, unchanged classfile bytes.

func TestVerifyM5bbFullWidthCellsDefaultsAliasesIdentityAndExpressions(t *testing.T) {
	classfile := verifyM5bbCompile(t, map[string]string{
		"LongArrayCells.java": `public final class LongArrayCells {
			static int fold(long x){return (int)(x^(x>>>32));}
			public static int values(){long[] a=new long[64];
				a[0]=0L;a[1]=Long.MIN_VALUE;a[2]=Long.MAX_VALUE;a[3]=0x1122334455667788L;
				a[63]=-0x102030405060708L;return fold(a[0])+fold(a[1])+fold(a[2])+fold(a[3])+fold(a[63]);}
			public static int defaults(){long[] a=new long[64];long x=0;for(int i=0;i<a.length;i++)x|=a[i];return fold(x)+a.length;}
			public static int aliases(){long[] a=new long[0],alias=a,b=new long[0];long[] c=new long[1];c[0]=0x7fffffff80000000L;
				return (a==alias?1:0)+(a!=b?2:0)+(a!=(Object)c?4:0)+fold(c[0]);}
			public static int expressions(){long[] a=new long[2];a[0]=0x100000002L;a[1]=7;
				long x=a[0]++;long y=++a[0];a[1]+=0x200000003L;a[1]^=a[0];return fold(x)+fold(y)+fold(a[0])+fold(a[1]);}
		}`,
	}, "LongArrayCells")["LongArrayCells"]
	parsed := parseStaticsClass(t, classfile)
	for _, method := range []string{"values", "defaults", "aliases", "expressions"} {
		code := parsed.namedMethod(t, method).code
		verifyM5bbInstructionPC(t, code, verifyM5bbNewarray, 0)
		verifyM5bbInstructionPC(t, code, verifyM5bbLaload, 0)
		if method != "defaults" {
			verifyM5bbInstructionPC(t, code, verifyM5bbLastore, 0)
		}
		want := verifyM5bbJava8Int(t, [][]byte{classfile}, "LongArrayCells", method, nil)
		verifyM5bbAssertValue(t, func() (Result, error) {
			return Run(classfile, method, nil, verifyM5bbGasLimit)
		}, want)
	}
}

func TestVerifyM5bbHigherDimensionsPartialDefaultsAndPrimitiveLeafIdentity(t *testing.T) {
	classfile := verifyM5bbCompile(t, map[string]string{
		"LongArrayTypes.java": `public final class LongArrayTypes {
			public static int shapes(){long[][] full=new long[2][3];long[][] partial=new long[2][];long[][][] high=new long[1][2][3];
				full[1][2]=0x100000002L;high[0][1][2]=7L;
				return full.length*10000+full[0].length*1000+(partial[0]==null?100:0)+high[0].length*10+(int)(full[1][2]+high[0][1][2]);}
			public static int markers(){Object j=new long[0],jj=new long[0][],i=new int[0],b=new byte[0],z=new boolean[0];
				return (j instanceof Object?1:0)+(j instanceof Cloneable?2:0)+(j instanceof java.io.Serializable?4:0)
				+(j instanceof Object[]?8:0)+(jj instanceof Object[]?16:0)+(jj instanceof Cloneable[]?32:0)
				+(j instanceof int[]?64:0)+(j instanceof byte[]?128:0)+(j instanceof boolean[]?256:0)
				+(jj instanceof int[][]?512:0)+(i instanceof long[]?1024:0)+(b instanceof long[]?2048:0)+(z instanceof long[]?4096:0);}
			public static int goodStore(){Object[] x=new long[1][];long[] value=new long[2];x[0]=value;return ((long[])x[0]).length;}
			public static int ase(){Object[] x=new long[1][];x[0]=new int[1];return 1;}
			public static int cce(){Object x=new int[1];return ((long[])x).length;}
		}`,
	}, "LongArrayTypes")["LongArrayTypes"]
	for _, method := range []string{"shapes", "markers", "goodStore"} {
		want := verifyM5bbJava8Int(t, [][]byte{classfile}, "LongArrayTypes", method, nil)
		verifyM5bbAssertValue(t, func() (Result, error) { return Run(classfile, method, nil, verifyM5bbGasLimit) }, want)
	}
	for _, tc := range []struct {
		method, class string
		kind          byte
	}{{"ase", "java.lang.ArrayStoreException", 9}, {"cce", "java.lang.ClassCastException", 8}} {
		verifyM5bbJava8Outcome(t, [][]byte{classfile}, "LongArrayTypes", tc.method, nil, "exception="+tc.class)
		verifyM5bbAssertException(t, func() (Result, error) { return Run(classfile, tc.method, nil, verifyM5bbGasLimit) }, tc.class, tc.kind)
	}
}

func TestVerifyM5bbArrayReferencesAcrossFieldsReturnsAndEveryCallMode(t *testing.T) {
	classes := verifyM5bbCompile(t, map[string]string{
		"callsarray/I.java": `package callsarray; public interface I {
			long[] iface(long[] x); long scalar(long x);
			default long[] def(long[] x){x[0]+=5L;return x;}
			static long[] stat(long[] x){x[0]+=1L;return x;}
		}`,
		"callsarray/Base.java": `package callsarray; public class Base {
			long[] value; Base(long[] x){value=x;} long[] virtual(long[] x){x[0]+=2L;return x;}
		}`,
		"callsarray/C.java": `package callsarray; public final class C extends Base implements I {
			C(long[] x){super(x);} public long[] iface(long[] x){x[0]+=3L;return x;}
			public long scalar(long x){return x+4L;} public long[] virtual(long[] x){return super.virtual(x);}
		}`,
		"callsarray/Root.java": `package callsarray; public final class Root {
			static long[] shared; final long[] fin; Root(long[] x){fin=x;}
			private long[] special(long[] x){x[0]+=6L;return x;} static long[] direct(long[] x){x[0]+=7L;return x;}
			static long mixed(long x,long[] a,int y){return x+a[0]+y;} static long[] viaInterface(I i,long[] a){return i.iface(a);}
			static int fold(long x){return (int)(x^(x>>>32));}
			public static int run(int seed){long[] a=new long[1];a[0]=((long)seed<<40)+9;shared=a;Root r=new Root(a);C c=new C(a);I i=c;
				I.stat(a);r.special(a);c.virtual(a);viaInterface(i,a);i.def(a);direct(a);long q=i.scalar(a[0]);r.fin[0]++;
				return fold(mixed(q,shared,seed))+(r.fin==shared?1:0);}
			public static int takes(long[] x){return x.length;} public static long[] returns(){return new long[1];}
			public static int takesLong(long x){return (int)x;} public static long returnsLong(){return 1L;}
		}`,
	}, "callsarray/I", "callsarray/Base", "callsarray/C", "callsarray/Root")
	bundle := verifyM5bbBundle(classes)
	for _, seed := range []int32{-19, 0, 23, 2147483647} {
		want := verifyM5bbJava8Int(t, bundle, "callsarray.Root", "run", []int32{seed})
		verifyM5bbAssertValue(t, func() (Result, error) {
			return RunClasses(bundle, "callsarray/Root", "run", []int32{seed}, verifyM5bbGasLimit)
		}, want)
	}

	root := parseStaticsClass(t, classes["callsarray/Root"])
	method := root.method(t, "viaInterface", "(Lcallsarray/I;[J)[J")
	pc := verifyM5bbMemberPC(t, root, method, 0xb9, 11, "iface", "([J)[J")
	if got := method.code[pc+3 : pc+5]; !bytes.Equal(got, []byte{2, 0}) {
		t.Fatalf("invokeinterface ([J)[J suffix=%x want one-word array argument count 2, zero", got)
	}
	runMethod := root.method(t, "run", "(I)I")
	scalarPC := verifyM5bbMemberPC(t, root, runMethod, 0xb9, 11, "scalar", "(J)J")
	if got := runMethod.code[scalarPC+3 : scalarPC+5]; !bytes.Equal(got, []byte{3, 0}) {
		t.Fatalf("invokeinterface (J)J suffix=%x want two-word long argument count 3, zero", got)
	}
	for _, count := range []byte{1, 3} {
		badRoot := verifyM5bbMutate(t, classes["callsarray/Root"], func(_ []byte, c staticsClass) {
			m := c.method(t, "viaInterface", "(Lcallsarray/I;[J)[J")
			p := verifyM5bbMemberPC(t, c, m, 0xb9, 11, "iface", "([J)[J")
			m.code[p+3] = count
		})
		bad := verifyM5bbReplaceClass(classes, "callsarray/Root", badRoot)
		verifyM5bbAssertError(t, func() (Result, error) {
			return RunClasses(verifyM5bbBundle(bad), "callsarray/Root", "run", []int32{1}, verifyM5bbGasLimit)
		}, "CallError(uint256,uint256)", 1, uint64(pc))
	}
	for _, tc := range []struct {
		method string
		args   []int32
	}{{"takes", nil}, {"takes", []int32{0}}, {"returns", nil}, {"takesLong", []int32{1}}, {"returnsLong", nil}} {
		verifyM5bbAssertMethodError(t, func() (Result, error) {
			return RunClasses(bundle, "callsarray/Root", tc.method, tc.args, verifyM5bbGasLimit)
		}, 11)
	}
}

func TestVerifyM5bbDescriptorMismatchesAtCallsFieldsAndReturnsAreReferenceTwo(t *testing.T) {
	original := verifyM5bbCompile(t, map[string]string{
		"TypedLongArrays.java": `public final class TypedLongArrays {
			static long[] field; static int accept(long[] x){return x.length;} static long[] give(){return new long[1];}
			public static int argument(){return accept(new long[1]);}
			public static int staticField(){field=new long[1];return field.length;}
			public static int returned(){return give().length;}
		}`,
	}, "TypedLongArrays")["TypedLongArrays"]
	for _, tc := range []struct {
		method   string
		boundary byte
		entry    string
	}{{"argument", 0xb8, "argument"}, {"staticField", 0xb3, "staticField"}, {"give", 0xb0, "returned"}} {
		t.Run(tc.method, func(t *testing.T) {
			bad := verifyM5bbMutate(t, original, func(_ []byte, c staticsClass) {
				m := c.namedMethod(t, tc.method)
				newPC := verifyM5bbInstructionPC(t, m.code, verifyM5bbNewarray, 0)
				if m.code[newPC+1] != 11 {
					t.Fatalf("%s newarray atype=%d want long", tc.method, m.code[newPC+1])
				}
				m.code[newPC+1] = 10
			})
			boundaryPC := verifyM5bbInstructionPC(t, parseStaticsClass(t, bad).namedMethod(t, tc.method).code, tc.boundary, 0)
			verifyM5bbAssertError(t, func() (Result, error) { return Run(bad, tc.entry, nil, verifyM5bbGasLimit) },
				"ReferenceError(uint256,uint256)", 2, uint64(boundaryPC))
		})
	}
}

func TestVerifyM5bbLogicalOperandsPrefixWordDepthAndWrongArrayOpcodes(t *testing.T) {
	base := verifyM5bbCompile(t, map[string]string{
		"M5bbRaw.java": `public final class M5bbRaw {
			static final long V=0x1122334455667788L;
			public static int longLoad(){long[] a=new long[1];return (int)a[0];}
			public static int intLoad(){int[] a=new int[1];return a[0];}
			public static int nestedLoad(){long[][] a=new long[1][];return a[0]==null?1:0;}
			public static int padding(){int x=0;` + strings.Repeat("x=x+1;", 500) + `return x;}
		}`,
	}, "M5bbRaw")["M5bbRaw"]
	parsedBase := parseStaticsClass(t, base)
	longIndex := verifyM5bbCPIndices(parsedBase, 5)[0]
	classIndex := parsedBase.thisClass
	valid := []byte{0x10, 40, 0x04, verifyM5bbNewarray, 11, 0x59, 0x03, 0x14, byte(longIndex >> 8), byte(longIndex), verifyM5bbLastore, 0x03, verifyM5bbLaload, 0x88, 0x60, 0xac}
	validClass := verifyM5bbRewriteCode(t, base, "padding", "()I", valid, 6, 1)
	want := int32(40 + int32(0x55667788))
	verifyM5bbJava8Outcome(t, [][]byte{verifyM5bbMajor49(validClass)}, "M5bbRaw", "padding", nil, "value="+strconv.Itoa(int(want)))
	verifyM5bbAssertValue(t, func() (Result, error) { return Run(validClass, "padding", nil, verifyM5bbGasLimit) }, want)

	for _, tc := range []struct {
		method   string
		from, to byte
	}{{"longLoad", verifyM5bbLaload, 0x2e}, {"intLoad", 0x2e, verifyM5bbLaload}, {"nestedLoad", 0x32, verifyM5bbLaload}} {
		bad := verifyM5bbReplaceOpcode(t, base, tc.method, "()I", tc.from, tc.to, 1)
		pc := verifyM5bbInstructionPC(t, parseStaticsClass(t, bad).namedMethod(t, tc.method).code, tc.to, 0)
		verifyM5bbAssertError(t, func() (Result, error) { return Run(bad, tc.method, nil, verifyM5bbGasLimit) },
			"ReferenceError(uint256,uint256)", 1, uint64(pc))
	}

	withNested, nestedIndex := verifyM5bbAppendNameAndClass(t, base, "[J")
	wrongHeap := []struct {
		name      string
		classfile []byte
		code      []byte
		op        byte
	}{
		{"iastore-long", base, []byte{0x04, verifyM5bbNewarray, 11, 0x03, 0x04, 0x4f, 0x03, 0xac}, 0x4f},
		{"lastore-int", base, []byte{0x04, verifyM5bbNewarray, 10, 0x03, 0x0a, verifyM5bbLastore, 0x03, 0xac}, verifyM5bbLastore},
		{"aastore-long", base, []byte{0x04, verifyM5bbNewarray, 11, 0x03, 0x01, 0x53, 0x03, 0xac}, 0x53},
		{"lastore-long-rank2", withNested, []byte{0x04, 0xbd, byte(nestedIndex >> 8), byte(nestedIndex), 0x03, 0x0a, verifyM5bbLastore, 0x03, 0xac}, verifyM5bbLastore},
	}
	for _, tc := range wrongHeap {
		t.Run(tc.name, func(t *testing.T) {
			bad := verifyM5bbRewriteCode(t, tc.classfile, "padding", "()I", tc.code, 6, 1)
			pc := verifyM5bbInstructionPC(t, tc.code, tc.op, 0)
			verifyM5bbAssertError(t, func() (Result, error) { return Run(bad, "padding", nil, verifyM5bbGasLimit) },
				"ReferenceError(uint256,uint256)", 1, uint64(pc))
		})
	}

	cases := []struct {
		name string
		code []byte
		op   byte
		kind uint64
	}{
		{"laload-empty", []byte{verifyM5bbLaload, 0x88, 0xac}, verifyM5bbLaload, 3},
		{"lastore-empty", []byte{verifyM5bbLastore, 0x03, 0xac}, verifyM5bbLastore, 3},
		{"int-as-array", []byte{0x03, 0x03, verifyM5bbLaload, 0x88, 0xac}, verifyM5bbLaload, 14},
		{"ref-as-index", []byte{0x04, verifyM5bbNewarray, 11, 0x01, verifyM5bbLaload, 0x88, 0xac}, verifyM5bbLaload, 14},
		{"uninitialized-as-array", []byte{0xbb, byte(classIndex >> 8), byte(classIndex), 0x03, verifyM5bbLaload, 0x88, 0xac}, verifyM5bbLaload, 14},
		{"two-ints-not-long", []byte{0x04, verifyM5bbNewarray, 11, 0x03, 0x04, 0x05, verifyM5bbLastore, 0x03, 0xac}, verifyM5bbLastore, 14},
		{"null-count", []byte{0x01, verifyM5bbNewarray, 11, 0xbe, 0xac}, verifyM5bbNewarray, 14},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			bad := verifyM5bbRewriteCode(t, base, "padding", "()I", tc.code, 8, 1)
			pc := verifyM5bbInstructionPC(t, tc.code, tc.op, 0)
			verifyM5bbAssertError(t, func() (Result, error) { return Run(bad, "padding", nil, verifyM5bbGasLimit) },
				"BytecodeError(uint256,uint256)", tc.kind, uint64(pc))
		})
	}

	// arrayref/index/long is four words even though lastore consumes only three
	// logical values. The whole long reaches the capacity check indivisibly.
	capacity := []byte{0x04, verifyM5bbNewarray, 11, 0x03, 0x14, byte(longIndex >> 8), byte(longIndex), verifyM5bbLastore, 0x03, 0xac}
	badCapacity := verifyM5bbRewriteCode(t, base, "padding", "()I", capacity, 3, 1)
	ldcPC := verifyM5bbInstructionPC(t, capacity, 0x14, 0)
	verifyM5bbAssertError(t, func() (Result, error) { return Run(badCapacity, "padding", nil, verifyM5bbGasLimit) },
		"BytecodeError(uint256,uint256)", 9, uint64(ldcPC))
}

func TestVerifyM5bbNullBoundsSourceEvaluationAndInitializerOutcomes(t *testing.T) {
	classes := verifyM5bbCompile(t, map[string]string{
		"LongArrayFaults.java": `public final class LongArrayFaults {
			static int zero(){return 0;} public static int negative(int n){return new long[n].length;}
			public static int loadNull(int i){long[] a=null;return (int)a[i];}
			public static int storeNull(int i){long[] a=null;a[i]=7L;return 1;}
			public static int loadBounds(int i){return (int)(new long[2])[i];}
			public static int storeBounds(int i){long[] a=new long[2];a[i]=7L;return 1;}
			public static int valueBeforeNull(){long[] a=null;a[99]=7L/zero();return 1;}
		}`,
		"InitLongArrayArithmetic.java": `public final class InitLongArrayArithmetic {
			static int zero(){return 0;} static long[] value=fail();static long[] fail(){long[] a=null;a[0]=7L/zero();return a;}
			public static int run(){return value.length;}
		}`,
		"InitLongArrayReentrant.java": `public final class InitLongArrayReentrant {
			static int calls;static long[] value=make();static long[] make(){calls++;long[] x=new long[1];x[0]=read()+0x100000002L;return x;}
			static long read(){return value==null?3L:value[0];}public static int run(){return calls*10+(int)value[0];}
		}`,
		"InitLongArrayOOM.java": `public final class InitLongArrayOOM {
			static long[] value=new long[65537];public static int run(){return value.length;}
		}`,
	}, "LongArrayFaults", "InitLongArrayArithmetic", "InitLongArrayReentrant", "InitLongArrayOOM")
	faults := classes["LongArrayFaults"]
	verifyM5bbAssertException(t, func() (Result, error) { return Run(faults, "negative", []int32{-1}, verifyM5bbGasLimit) }, "java.lang.NegativeArraySizeException", 4)
	for _, method := range []string{"loadNull", "storeNull"} {
		for _, index := range []int32{-1, 65537} {
			verifyM5bbAssertException(t, func() (Result, error) { return Run(faults, method, []int32{index}, verifyM5bbGasLimit) }, "java.lang.NullPointerException", 6)
		}
	}
	for _, method := range []string{"loadBounds", "storeBounds"} {
		for _, index := range []int32{-1, 2} {
			verifyM5bbAssertException(t, func() (Result, error) { return Run(faults, method, []int32{index}, verifyM5bbGasLimit) }, "java.lang.ArrayIndexOutOfBoundsException", 5)
		}
	}
	verifyM5bbJava8Outcome(t, [][]byte{faults}, "LongArrayFaults", "valueBeforeNull", nil, "exception=java.lang.ArithmeticException")
	verifyM5bbAssertException(t, func() (Result, error) { return Run(faults, "valueBeforeNull", nil, verifyM5bbGasLimit) }, "java.lang.ArithmeticException", 1)
	init := classes["InitLongArrayArithmetic"]
	verifyM5bbJava8Outcome(t, [][]byte{init}, "InitLongArrayArithmetic", "run", nil, "exception=java.lang.ExceptionInInitializerError")
	verifyM5bbAssertException(t, func() (Result, error) { return Run(init, "run", nil, verifyM5bbGasLimit) }, "java.lang.ExceptionInInitializerError", 3)
	reentrant := classes["InitLongArrayReentrant"]
	want := verifyM5bbJava8Int(t, [][]byte{reentrant}, "InitLongArrayReentrant", "run", nil)
	verifyM5bbAssertValue(t, func() (Result, error) { return Run(reentrant, "run", nil, verifyM5bbGasLimit) }, want)
	// The fixed interpreter element limit is tested only in EVM; deliberately do
	// not turn host-JVM memory policy into an oracle. Error kind 7 stays unwrapped.
	oom := classes["InitLongArrayOOM"]
	verifyM5bbAssertException(t, func() (Result, error) { return Run(oom, "run", nil, verifyM5bbGasLimit) }, "java.lang.OutOfMemoryError", 7)
}

func TestVerifyM5bbFirstAllocationKindsSharedCapsOneElementNoGCResetAndOOG(t *testing.T) {
	classfile := verifyM5bbCompile(t, map[string]string{
		"LongArrayCaps.java": `public final class LongArrayCaps {
			int value; LongArrayCaps(){value=1;}
			public static int objectFirst(){LongArrayCaps o=new LongArrayCaps();int[] i=new int[1];Object[] r=new Object[1];long[] j=new long[1];
				j[0]=0x100000002L;i[0]=3;r[0]=o;return o.value+i[0]+r.length+(int)j[0];}
			public static int longFirst(){long[] j=new long[1];LongArrayCaps o=new LongArrayCaps();Object[] r=new Object[1];int[] i=new int[1];
				j[0]=0x200000003L;r[0]=o;i[0]=4;return (int)j[0]+i[0]+r.length+o.value;}
			public static int intFirst(){int[] i=new int[1];long[] j=new long[1];LongArrayCaps o=new LongArrayCaps();Object[] r=new Object[1];
				j[0]=0x300000004L;i[0]=5;r[0]=o;return (int)j[0]+i[0]+r.length+o.value;}
			public static int refFirst(){Object[] r=new Object[1];long[] j=new long[1];int[] i=new int[1];LongArrayCaps o=new LongArrayCaps();
				j[0]=0x400000005L;i[0]=6;r[0]=o;return (int)j[0]+i[0]+r.length+o.value;}
			public static int mixedArrays(int n){Object x=null;for(int k=0;k<n;k++){int m=k%3;if(m==0)x=new long[0];else if(m==1)x=new int[0];else x=new Object[0];}return n+(x==null?0:0);}
			public static int perArray(int n){return new long[n].length;}
			public static int exactElements(){Object x=null;for(int k=0;k<4;k++)x=new long[65536];return 262144+(x==null?0:0);}
			public static int overElements(){Object x=null;for(int k=0;k<4;k++)x=new long[65536];x=new int[1];return x==null?0:1;}
			public static int arraysAndObjects(){Object a=null,o=null;for(int k=0;k<1024;k++)a=(k&1)==0?(Object)new long[0]:(Object)new int[0];
				for(int k=0;k<1024;k++)o=new Object();return (a==null?0:1)+(o==null?0:1);}
		}`,
	}, "LongArrayCaps")["LongArrayCaps"]
	for _, method := range []string{"objectFirst", "longFirst", "intFirst", "refFirst"} {
		want := verifyM5bbJava8Int(t, [][]byte{classfile}, "LongArrayCaps", method, nil)
		verifyM5bbAssertValue(t, func() (Result, error) { return Run(classfile, method, nil, verifyM5bbGasLimit) }, want)
	}
	verifyM5bbAssertValue(t, func() (Result, error) {
		return Run(classfile, "mixedArrays", []int32{1024}, verifyM5bbCapacityGasLimit)
	}, 1024)
	verifyM5bbAssertException(t, func() (Result, error) {
		return Run(classfile, "mixedArrays", []int32{1025}, verifyM5bbCapacityGasLimit)
	}, "java.lang.OutOfMemoryError", 7)
	verifyM5bbAssertValue(t, func() (Result, error) { return Run(classfile, "perArray", []int32{65536}, verifyM5bbCapacityGasLimit) }, 65536)
	verifyM5bbAssertException(t, func() (Result, error) { return Run(classfile, "perArray", []int32{65537}, verifyM5bbGasLimit) }, "java.lang.OutOfMemoryError", 7)
	// Four 65,536-cell long arrays prove that one long is one aggregate array
	// element, not two category words or eight byte-counted elements.
	verifyM5bbAssertValue(t, func() (Result, error) { return Run(classfile, "exactElements", nil, verifyM5bbCapacityGasLimit) }, 262144)
	verifyM5bbAssertException(t, func() (Result, error) { return Run(classfile, "overElements", nil, verifyM5bbCapacityGasLimit) }, "java.lang.OutOfMemoryError", 7)
	// Use zero-field bootstrap Object instances so this shared-quota probe spends
	// its finite budget on 1024 arrays plus 1024 objects, not guest constructor
	// field initialization already covered by the first-allocation probes above.
	verifyM5bbAssertValue(t, func() (Result, error) {
		return Run(classfile, "arraysAndObjects", nil, verifyM5bbCapacityGasLimit)
	}, 2)
	// Unreachable allocations count in one invocation, while a fresh invocation resets.
	verifyM5bbAssertValue(t, func() (Result, error) {
		return Run(classfile, "mixedArrays", []int32{1024}, verifyM5bbCapacityGasLimit)
	}, 1024)
	result, err := Run(classfile, "perArray", []int32{1}, 1)
	if err == nil || !errors.Is(err, vm.ErrOutOfGas) || result.ExceptionClass != "" || len(result.RevertData) != 0 {
		t.Fatalf("result/error=%+v/%v want unlabeled EVM out of gas", result, err)
	}
}

func TestVerifyM5bbLongArrayFieldIsOneObjectSlot(t *testing.T) {
	for _, count := range []int{1024, 1025} {
		t.Run(strconv.Itoa(count), func(t *testing.T) {
			var source strings.Builder
			source.WriteString("public final class LongArrayFieldQuota {")
			for i := 0; i < count; i++ {
				fmt.Fprintf(&source, "long[] f%d;", i)
			}
			source.WriteString("public static int run(){return new LongArrayFieldQuota()==null?0:1;}}")
			classfile := verifyM5bbCompile(t, map[string]string{"LongArrayFieldQuota.java": source.String()}, "LongArrayFieldQuota")["LongArrayFieldQuota"]
			if count == 1024 {
				verifyM5bbAssertValue(t, func() (Result, error) { return Run(classfile, "run", nil, verifyM5bbCapacityGasLimit) }, 1)
			} else {
				verifyM5bbAssertException(t, func() (Result, error) { return Run(classfile, "run", nil, verifyM5bbCapacityGasLimit) }, "java.lang.OutOfMemoryError", 7)
			}
		})
	}
}

func TestVerifyM5bbRank255MultianewarrayPredecodeTruncationAndDeferredFD(t *testing.T) {
	base := verifyM5bbCompile(t, map[string]string{
		"LongArrayStructure.java": `public final class LongArrayStructure {
			public static int typeLong(){Object x=new int[1];return x instanceof long[]?1:0;}
			public static int typeFloat(){Object x=new int[1];return x instanceof float[]?1:0;}
			public static int typeDouble(){Object x=new int[1];return x instanceof double[]?1:0;}
			public static int padding(){int x=0;` + strings.Repeat("x=x+1;", 700) + `return x;}
		}`,
	}, "LongArrayStructure")["LongArrayStructure"]

	descriptor := strings.Repeat("[", 255) + "J"
	withRank, arrayIndex := verifyM5bbAppendNameAndClass(t, base, descriptor)
	full := make([]byte, 0, 800)
	for i := 0; i < 255; i++ {
		full = append(full, 0x04)
	}
	full = append(full, 0xc5, byte(arrayIndex>>8), byte(arrayIndex), 255)
	for i := 0; i < 254; i++ {
		full = append(full, 0x03, 0x32)
	}
	full = append(full, 0xbe, 0xac)
	fullClass := verifyM5bbRewriteCode(t, withRank, "padding", "()I", full, 300, 1)
	verifyM5bbAssertValue(t, func() (Result, error) { return Run(fullClass, "padding", nil, verifyM5bbCapacityGasLimit) }, 1)
	partial := []byte{0x04, 0xc5, byte(arrayIndex >> 8), byte(arrayIndex), 1, 0xbe, 0xac}
	partialClass := verifyM5bbRewriteCode(t, withRank, "padding", "()I", partial, 4, 1)
	verifyM5bbAssertValue(t, func() (Result, error) { return Run(partialClass, "padding", nil, verifyM5bbGasLimit) }, 1)

	for _, tc := range []struct {
		rank     int
		overflow bool
	}{{254, false}, {255, true}} {
		withComponent, componentIndex := verifyM5bbAppendNameAndClass(t, base, strings.Repeat("[", tc.rank)+"J")
		code := []byte{0x04, 0xbd, byte(componentIndex >> 8), byte(componentIndex), 0xbe, 0xac}
		classfile := verifyM5bbRewriteCode(t, withComponent, "padding", "()I", code, 2, 1)
		if tc.overflow {
			verifyM5bbAssertError(t, func() (Result, error) { return Run(classfile, "padding", nil, verifyM5bbGasLimit) }, "ArrayError(uint256,uint256)", 2, 1)
		} else {
			verifyM5bbAssertValue(t, func() (Result, error) { return Run(classfile, "padding", nil, verifyM5bbGasLimit) }, 1)
		}
	}

	for _, atype := range []byte{6, 7} {
		code := []byte{0x04, verifyM5bbNewarray, atype, 0xbe, 0xac}
		classfile := verifyM5bbRewriteCode(t, base, "padding", "()I", code, 2, 1)
		verifyM5bbAssertValue(t, func() (Result, error) { return Run(classfile, "padding", nil, verifyM5bbGasLimit) }, 1)
	}
	for _, method := range []string{"typeFloat", "typeDouble"} {
		verifyM5bbJava8Outcome(t, [][]byte{base}, "LongArrayStructure", method, nil, "value=0")
		verifyM5bbAssertValue(t, func() (Result, error) { return Run(base, method, nil, verifyM5bbGasLimit) }, 0)
	}
	// [J is no longer deferred: a non-null unlike primitive must simply test false.
	verifyM5bbJava8Outcome(t, [][]byte{base}, "LongArrayStructure", "typeLong", nil, "value=0")
	verifyM5bbAssertValue(t, func() (Result, error) { return Run(base, "typeLong", nil, verifyM5bbGasLimit) }, 0)

	truncated := verifyM5bbRewriteAtEnd(t, base, "padding", "()I", []byte{verifyM5bbNewarray})
	truncatedPC := len(parseStaticsClass(t, truncated).namedMethod(t, "padding").code) - 1
	verifyM5bbAssertError(t, func() (Result, error) { return Run(truncated, "padding", nil, verifyM5bbGasLimit) }, "BytecodeError(uint256,uint256)", 2, uint64(truncatedPC))
	for operands := 0; operands <= 2; operands++ {
		ending := append([]byte{0xc5}, make([]byte, operands)...)
		bad := verifyM5bbRewriteAtEnd(t, withRank, "padding", "()I", ending)
		pc := len(parseStaticsClass(t, bad).namedMethod(t, "padding").code) - len(ending)
		verifyM5bbAssertError(t, func() (Result, error) { return Run(bad, "padding", nil, verifyM5bbGasLimit) }, "BytecodeError(uint256,uint256)", 2, uint64(pc))
	}

	// The first 0xbc is an ldc_w operand, not an instruction. The actual
	// newarray starts at PC 5; a branch into its atype byte must be rejected.
	boundary := []byte{0x13, 0x00, 0xbc, 0x99, 0, 3, 0x04, verifyM5bbNewarray, 11, 0x57, 0x03, 0xac}
	if pc := verifyM5bbInstructionPC(t, boundary, verifyM5bbNewarray, 0); pc != 7 {
		t.Fatalf("boundary-aware newarray pc=%d want 7", pc)
	}
	// Replace ldc_w with iconst_0/nops while preserving the branch at PC 3,
	// whose +5 target is PC 8 (the atype operand).
	branch := []byte{0x03, 0x00, 0x00, 0x99, 0, 5, 0x04, verifyM5bbNewarray, 11, 0x57, 0x03, 0xac}
	branchClass := verifyM5bbRewriteCode(t, base, "padding", "()I", branch, 2, 1)
	verifyM5bbAssertError(t, func() (Result, error) { return Run(branchClass, "padding", nil, verifyM5bbGasLimit) }, "BytecodeError(uint256,uint256)", 12, 3)
}

// --- M5b-b verifier-only helpers ---

func verifyM5bbCompile(t *testing.T, sources map[string]string, internalNames ...string) map[string][]byte {
	t.Helper()
	return verifyM5baCompile(t, sources, internalNames...)
}

func verifyM5bbBundle(classes map[string][]byte) [][]byte {
	names := make([]string, 0, len(classes))
	for name := range classes {
		names = append(names, name)
	}
	sort.Strings(names)
	out := make([][]byte, len(names))
	for i, name := range names {
		out[i] = classes[name]
	}
	return out
}

func verifyM5bbReplaceClass(classes map[string][]byte, name string, replacement []byte) map[string][]byte {
	out := make(map[string][]byte, len(classes))
	for key, value := range classes {
		out[key] = value
	}
	out[name] = replacement
	return out
}

func verifyM5bbMutate(t *testing.T, original []byte, edit func([]byte, staticsClass)) []byte {
	t.Helper()
	return verifyM5baMutate(t, original, edit)
}

func verifyM5bbRewriteCode(t *testing.T, original []byte, name, descriptor string, code []byte, maxStack, maxLocals uint16) []byte {
	t.Helper()
	return verifyM5baRewriteCode(t, original, name, descriptor, code, maxStack, maxLocals)
}

func verifyM5bbRewriteAtEnd(t *testing.T, original []byte, name, descriptor string, ending []byte) []byte {
	t.Helper()
	return verifyM5baRewriteAtEnd(t, original, name, descriptor, ending)
}

func verifyM5bbReplaceOpcode(t *testing.T, original []byte, name, descriptor string, from, to byte, want int) []byte {
	t.Helper()
	return verifyM5baReplaceOpcode(t, original, name, descriptor, from, to, want)
}

func verifyM5bbInstructionPC(t *testing.T, code []byte, opcode byte, occurrence int) int {
	t.Helper()
	return verifyM5baInstructionPC(t, code, opcode, occurrence)
}

func verifyM5bbMemberPC(t *testing.T, c staticsClass, m staticsMethod, opcode, tag byte, name, descriptor string) int {
	t.Helper()
	return verifyM5baMemberPC(t, c, m, opcode, tag, name, descriptor)
}

func verifyM5bbCPIndices(c staticsClass, tag byte) []uint16 {
	return verifyM5baCPIndices(c, tag)
}

func verifyM5bbAppendNameAndClass(t *testing.T, original []byte, name string) ([]byte, uint16) {
	t.Helper()
	return verifyM5aAppendNameAndClass(t, original, name)
}

func verifyM5bbMajor49(classfile []byte) []byte {
	return verifyM5baMajor49(classfile)
}

func verifyM5bbJava8Outcome(t *testing.T, bundle [][]byte, mainClass, method string, args []int32, want string) {
	t.Helper()
	verifyM5baJava8Outcome(t, bundle, mainClass, method, args, want)
}

func verifyM5bbJava8Int(t *testing.T, bundle [][]byte, mainClass, method string, args []int32) int32 {
	t.Helper()
	return verifyM5baJava8Int(t, bundle, mainClass, method, args)
}

func verifyM5bbAssertValue(t *testing.T, run func() (Result, error), want int32) {
	t.Helper()
	verifyM5baAssertValue(t, run, want)
}

func verifyM5bbAssertException(t *testing.T, run func() (Result, error), want string, kind byte) {
	t.Helper()
	verifyM5baAssertException(t, run, want, kind)
}

func verifyM5bbAssertError(t *testing.T, run func() (Result, error), signature string, code, location uint64) {
	t.Helper()
	verifyM5baAssertError(t, run, signature, code, location)
}

func verifyM5bbAssertMethodError(t *testing.T, run func() (Result, error), code uint64) {
	t.Helper()
	verifyM5baAssertMethodError(t, run, code)
}
