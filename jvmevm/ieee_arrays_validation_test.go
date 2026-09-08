// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"errors"
	"fmt"
	"strconv"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/core/vm"
	"github.com/ethereum/go-ethereum/crypto"
)

const (
	verifyM5cdGasLimit         = uint64(220_000_000)
	verifyM5cdSimpleGasLimit   = uint64(20_000_000)
	verifyM5cdCapacityGasLimit = uint64(250_000_000)
	verifyM5cdNewarray         = byte(0xbc)
	verifyM5cdFaload           = byte(0x30)
	verifyM5cdDaload           = byte(0x31)
	verifyM5cdFastore          = byte(0x51)
	verifyM5cdDastore          = byte(0x52)
)

// These verifier-only probes compile bounded, trusted Java 8 inputs. Java 8
// and Java 21 are test oracles only; unchanged classfiles are executed by the
// EVM interpreter. Quiet NaNs, finite values, infinities, and signed zeros are
// compared as raw cells. Signaling-NaN transport is deliberately EVM-only.

func TestVerifyM5cdRawCellsDefaultsCopiesAndArithmeticNaNBoundary(t *testing.T) {
	classfile := verifyM5cdCompile(t, map[string]string{
		"VerifyM5cdCells.java": `public strictfp final class VerifyM5cdCells {
			static float f(int x){return Float.intBitsToFloat(x);} static int fb(float x){return Float.floatToRawIntBits(x);}
			static long join(int h,int l){return ((long)h<<32)|(l&0xffffffffL);} static double d(int h,int l){return Double.longBitsToDouble(join(h,l));}
			static long db(double x){return Double.doubleToRawLongBits(x);}
			public static int fdefault(){float[] a=new float[3];return fb(a[2]);}
			public static int fcopy(int x){float[] a=new float[3];a[0]=f(x);a[2]=a[0];return fb(a[2]);}
			static long dcopy0(int h,int l){double[] a=new double[3];a[0]=d(h,l);a[2]=a[0];return db(a[2]);}
			public static int dcopyHi(int h,int l){return (int)(dcopy0(h,l)>>>32);} public static int dcopyLo(int h,int l){return (int)dcopy0(h,l);}
			public static int ddefaultHi(){return (int)(db((new double[2])[1])>>>32);} public static int ddefaultLo(){return (int)db((new double[2])[1]);}
			public static int farithmeticNaN(){float[] a=new float[1];a[0]=f(0)/f(0);int b=fb(a[0]);return ((b&0x7f800000)==0x7f800000&&(b&0x007fffff)!=0)?0x7fc00000:b;}
			public static int darithmeticNaNHi(){double[] a=new double[1];a[0]=d(0,0)/d(0,0);long b=db(a[0]);b=((b&0x7ff0000000000000L)==0x7ff0000000000000L&&(b&0xfffffffffffffL)!=0)?0x7ff8000000000000L:b;return (int)(b>>>32);}
			public static int darithmeticNaNLo(){double[] a=new double[1];a[0]=d(0,0)/d(0,0);long b=db(a[0]);b=((b&0x7ff0000000000000L)==0x7ff0000000000000L&&(b&0xfffffffffffffL)!=0)?0x7ff8000000000000L:b;return (int)b;}
		}`,
	}, "VerifyM5cdCells")["VerifyM5cdCells"]
	parsed := parseStaticsClass(t, classfile)
	for _, tc := range []struct {
		method      string
		load, store byte
	}{
		{"fcopy", verifyM5cdFaload, verifyM5cdFastore},
		{"dcopy0", verifyM5cdDaload, verifyM5cdDastore},
	} {
		code := parsed.namedMethod(t, tc.method).code
		verifyM5cdInstructionPC(t, code, tc.load, 0)
		verifyM5cdInstructionPC(t, code, tc.store, 0)
	}
	oracle := verifyM5cdNewOracle(t, classfile)
	for _, bits := range []uint32{0, 0x80000000, 1, 0x007fffff, 0x7f800000, 0xff800000, 0x7fc12345, 0xffc54321} {
		args := []int32{int32(bits)}
		want := oracle.intClass(t, "VerifyM5cdCells", "fcopy", args)
		if uint32(want) != bits {
			t.Fatalf("Java array float transport changed %08x to %08x", bits, uint32(want))
		}
		result := verifyM5cdRunValue(t, classfile, "fcopy", args, want, verifyM5cdSimpleGasLimit)
		t.Logf("M5c-d simple float raw transport bits=%08x gas=%d limit=%d", bits, result.GasUsed, verifyM5cdSimpleGasLimit)
	}
	for _, bits := range []uint64{0, 0x8000000000000000, 1, 0x000fffffffffffff, 0x7ff0000000000000, 0xfff0000000000000, 0x7ff8123456789abc, 0xfff8abcdeffedcba} {
		args := []int32{int32(bits >> 32), int32(bits)}
		hi := oracle.intClass(t, "VerifyM5cdCells", "dcopyHi", args)
		lo := oracle.intClass(t, "VerifyM5cdCells", "dcopyLo", args)
		want := uint64(uint32(hi))<<32 | uint64(uint32(lo))
		if want != bits {
			t.Fatalf("Java array double transport changed %016x to %016x", bits, want)
		}
		rh := verifyM5cdRunValue(t, classfile, "dcopyHi", args, hi, verifyM5cdSimpleGasLimit)
		rl := verifyM5cdRunValue(t, classfile, "dcopyLo", args, lo, verifyM5cdSimpleGasLimit)
		t.Logf("M5c-d simple double raw transport bits=%016x gas=%d/%d limit=%d", bits, rh.GasUsed, rl.GasUsed, verifyM5cdSimpleGasLimit)
	}
	for _, tc := range []struct {
		method string
		want   int32
	}{
		{"fdefault", 0}, {"ddefaultHi", 0}, {"ddefaultLo", 0},
		{"farithmeticNaN", int32(0x7fc00000)}, {"darithmeticNaNHi", int32(0x7ff80000)}, {"darithmeticNaNLo", 0},
	} {
		if got := oracle.intClass(t, "VerifyM5cdCells", tc.method, nil); got != tc.want {
			t.Fatalf("Java 8/21 %s=%08x want hard-coded %08x", tc.method, uint32(got), uint32(tc.want))
		}
		verifyM5cdRunValue(t, classfile, tc.method, nil, tc.want, verifyM5cdSimpleGasLimit)
	}

	// Some host JVM paths quiet signaling NaNs. The EVM contract is stronger:
	// array transport itself is a pure cell copy and must preserve every bit.
	for _, bits := range []uint32{0x7f800001, 0xff812345} {
		verifyM5cdRunValue(t, classfile, "fcopy", []int32{int32(bits)}, int32(bits), verifyM5cdSimpleGasLimit)
	}
	for _, bits := range []uint64{0x7ff0000000000001, 0xfff0123456789abc} {
		args := []int32{int32(bits >> 32), int32(bits)}
		verifyM5cdRunValue(t, classfile, "dcopyHi", args, int32(bits>>32), verifyM5cdSimpleGasLimit)
		verifyM5cdRunValue(t, classfile, "dcopyLo", args, int32(bits), verifyM5cdSimpleGasLimit)
	}
}

func TestVerifyM5cdFieldsFinalAliasesCallsAndInvokeinterfaceWordCounts(t *testing.T) {
	classes := verifyM5cdCompile(t, map[string]string{
		"m5cdcalls/I.java": `package m5cdcalls; public interface I {
			float[] iface(float[] x); double scalar(double x);
			default double[] def(double[] x){x[0]+=2.0d;return x;}
			static float[] stat(float[] x){x[0]+=1.0f;return x;}
		}`,
		"m5cdcalls/Base.java": `package m5cdcalls; public class Base {
			final float[] f; double[] d; Base(float[] x,double[] y){f=x;d=y;}
			float[] virtual(float[] x){x[0]+=4.0f;return x;}
		}`,
		"m5cdcalls/Box.java": `package m5cdcalls; public final class Box extends Base implements I {
			Box(float[] x,double[] y){super(x,y);} public float[] iface(float[] x){x[0]+=8.0f;return x;}
			public double scalar(double x){return x+16.0d;} public float[] virtual(float[] x){return super.virtual(x);}
		}`,
		"m5cdcalls/Root.java": `package m5cdcalls; public final class Root {
			static float[] sf; static double[] sd; final double[] fin; Root(double[] x){fin=x;}
			private double[] special(double[] x){x[0]+=32.0d;return x;} static float[] direct(float[] x){x[0]+=64.0f;return x;}
			static int fold(long x){return (int)(x^(x>>>32));} static float[] via(I i,float[] x){return i.iface(x);} static double viaScalar(I i,double x){return i.scalar(x);}
			public static int run(){float[] f=new float[1];double[] d=new double[1];f[0]=1.0f;d[0]=1.0d;sf=f;sd=d;
				Root r=new Root(d);Box b=new Box(f,d);I i=b;I.stat(f);b.virtual(f);via(i,f);i.def(d);r.special(d);direct(f);d[0]=viaScalar(i,d[0]);r.fin[0]++;
				return Float.floatToRawIntBits(sf[0])^fold(Double.doubleToRawLongBits(sd[0]))^(b.f==sf?1:0)^(r.fin==sd?2:0);}
		}`,
	}, "m5cdcalls/I", "m5cdcalls/Base", "m5cdcalls/Box", "m5cdcalls/Root")
	bundle := verifyM5cdBundle(classes)
	oracle := verifyM5cdNewOracle(t, bundle...)
	want := oracle.intClass(t, "m5cdcalls.Root", "run", nil)
	verifyM5cdRunClassesValue(t, bundle, "m5cdcalls/Root", "run", nil, want, verifyM5cdGasLimit)
	// Repetition proves static array references/caches and cells are invocation-local.
	verifyM5cdRunClassesValue(t, bundle, "m5cdcalls/Root", "run", nil, want, verifyM5cdGasLimit)

	root := parseStaticsClass(t, classes["m5cdcalls/Root"])
	ifacePC := verifyM5cdMemberPC(t, root, root.method(t, "via", "(Lm5cdcalls/I;[F)[F"), 0xb9, 11, "iface", "([F)[F")
	if got := root.method(t, "via", "(Lm5cdcalls/I;[F)[F").code[ifacePC+3 : ifacePC+5]; !bytes.Equal(got, []byte{2, 0}) {
		t.Fatalf("invokeinterface array count=%x want receiver plus one-word [F = 2,0", got)
	}
	scalarPC := verifyM5cdMemberPC(t, root, root.method(t, "viaScalar", "(Lm5cdcalls/I;D)D"), 0xb9, 11, "scalar", "(D)D")
	if got := root.method(t, "viaScalar", "(Lm5cdcalls/I;D)D").code[scalarPC+3 : scalarPC+5]; !bytes.Equal(got, []byte{3, 0}) {
		t.Fatalf("invokeinterface scalar D count=%x want receiver plus two-word D = 3,0", got)
	}
	defaultPC := verifyM5cdMemberPC(t, root, root.method(t, "run", "()I"), 0xb9, 11, "def", "([D)[D")
	if got := root.method(t, "run", "()I").code[defaultPC+3 : defaultPC+5]; !bytes.Equal(got, []byte{2, 0}) {
		t.Fatalf("invokeinterface array count=%x want receiver plus one-word [D = 2,0", got)
	}
	for _, count := range []byte{1, 3} {
		badRoot := verifyM5cdMutate(t, classes["m5cdcalls/Root"], func(_ []byte, c staticsClass) {
			m := c.method(t, "via", "(Lm5cdcalls/I;[F)[F")
			pc := verifyM5cdMemberPC(t, c, m, 0xb9, 11, "iface", "([F)[F")
			m.code[pc+3] = count
		})
		bad := verifyM5cdReplaceClass(classes, "m5cdcalls/Root", badRoot)
		verifyM5cdAssertError(t, func() (Result, error) {
			return RunClasses(verifyM5cdBundle(bad), "m5cdcalls/Root", "run", nil, verifyM5cdGasLimit)
		}, "CallError(uint256,uint256)", 1, uint64(ifacePC))
	}
}

func TestVerifyM5cdEveryFirstAllocationKindHasIndependentBacking(t *testing.T) {
	classfile := verifyM5cdCompile(t, map[string]string{
		"VerifyM5cdFirst.java": `public final class VerifyM5cdFirst {
			int x=1; static int use(float[] f,double[] d,int[] i,long[] j,Object[] r,VerifyM5cdFirst o){f[0]=2f;d[0]=3d;i[0]=4;j[0]=5;r[0]=o;return (int)(f[0]+d[0]+i[0]+j[0])+((VerifyM5cdFirst)r[0]).x;}
			public static int fFirst(){float[] f=new float[1];double[] d=new double[1];int[] i=new int[1];long[] j=new long[1];Object[] r=new Object[1];VerifyM5cdFirst o=new VerifyM5cdFirst();return use(f,d,i,j,r,o);}
			public static int dFirst(){double[] d=new double[1];long[] j=new long[1];Object[] r=new Object[1];VerifyM5cdFirst o=new VerifyM5cdFirst();int[] i=new int[1];float[] f=new float[1];return use(f,d,i,j,r,o);}
			public static int iFirst(){int[] i=new int[1];float[] f=new float[1];VerifyM5cdFirst o=new VerifyM5cdFirst();double[] d=new double[1];Object[] r=new Object[1];long[] j=new long[1];return use(f,d,i,j,r,o);}
			public static int jFirst(){long[] j=new long[1];double[] d=new double[1];float[] f=new float[1];int[] i=new int[1];VerifyM5cdFirst o=new VerifyM5cdFirst();Object[] r=new Object[1];return use(f,d,i,j,r,o);}
			public static int refFirst(){Object[] r=new Object[1];float[] f=new float[1];long[] j=new long[1];int[] i=new int[1];double[] d=new double[1];VerifyM5cdFirst o=new VerifyM5cdFirst();return use(f,d,i,j,r,o);}
			public static int objectFirst(){VerifyM5cdFirst o=new VerifyM5cdFirst();double[] d=new double[1];int[] i=new int[1];Object[] r=new Object[1];float[] f=new float[1];long[] j=new long[1];return use(f,d,i,j,r,o);}
		}`,
	}, "VerifyM5cdFirst")["VerifyM5cdFirst"]
	oracle := verifyM5cdNewOracle(t, classfile)
	for _, method := range []string{"fFirst", "dFirst", "iFirst", "jFirst", "refFirst", "objectFirst"} {
		want := oracle.intClass(t, "VerifyM5cdFirst", method, nil)
		if want != 15 {
			t.Fatalf("%s Java result=%d want hard-coded 15", method, want)
		}
		verifyM5cdRunValue(t, classfile, method, nil, want, verifyM5cdGasLimit)
	}
}

func TestVerifyM5cdPrimitiveIdentityNestedCovarianceMarkersAndShapes(t *testing.T) {
	classfile := verifyM5cdCompile(t, map[string]string{
		"VerifyM5cdTypes.java": `public final class VerifyM5cdTypes {
			public static int identity(){Object f=new float[0],d=new double[0],i=new int[0],j=new long[0],ff=new float[0][];
				return (f instanceof float[]?1:0)+(f instanceof int[]?2:0)+(d instanceof double[]?4:0)+(d instanceof long[]?8:0)+(d instanceof float[]?16:0)+(ff instanceof Object[]?32:0)+(ff instanceof double[][]?64:0);}
			public static int markers(){Object f=new float[0],d=new double[0],ff=new float[0][];
				return (f instanceof Object?1:0)+(f instanceof Cloneable?2:0)+(f instanceof java.io.Serializable?4:0)+(f instanceof Object[]?8:0)
				+(d instanceof Cloneable?16:0)+(d instanceof java.io.Serializable?32:0)+(ff instanceof Object[]?64:0)+(ff instanceof Cloneable[]?128:0);}
			public static int goodStore(){Object[] x=new float[1][];float[] y=new float[3];x[0]=y;x[0]=null;x[0]=y;return ((float[])x[0]).length;}
			public static int ase(){Object[] x=new float[1][];x[0]=new double[1];return 1;}
			public static int cce(){Object x=new double[1];return ((float[])x).length;}
			public static int multi(){float[][] f=new float[2][3];double[][][] d=new double[1][2][3];f[1][2]=7f;d[0][1][2]=9d;return f.length*1000+f[0].length*100+d[0].length*10+(int)(f[1][2]+d[0][1][2]);}
			public static int partial(){float[][][] f=new float[2][][];double[][] d=new double[2][];return (f[0]==null?1:0)+(d[1]==null?2:0);}
			public static int zeroStops(){double[][][] d=new double[2][0][65536];return d.length*10+d[0].length;}
			public static int distinctEmpty(){float[][] f=new float[2][0];return f[0]!=f[1]?1:0;}
			public static int negativeBeforeCap(){return new float[65536][-1].length;}
			public static int padding(){int x=0;` + strings.Repeat("x=x+1;", 700) + `return x;}
		}`,
	}, "VerifyM5cdTypes")["VerifyM5cdTypes"]
	oracle := verifyM5cdNewOracle(t, classfile)
	for _, tc := range []struct {
		method string
		want   int32
	}{
		{"identity", 37}, {"markers", 247}, {"goodStore", 3}, {"multi", 2336},
		{"partial", 3}, {"zeroStops", 20}, {"distinctEmpty", 1},
	} {
		if got := oracle.intClass(t, "VerifyM5cdTypes", tc.method, nil); got != tc.want {
			t.Fatalf("Java 8/21 %s=%d want hard-coded %d", tc.method, got, tc.want)
		}
		verifyM5cdRunValue(t, classfile, tc.method, nil, tc.want, verifyM5cdGasLimit)
	}
	for _, tc := range []struct {
		method, class string
		kind          byte
	}{{"ase", "java.lang.ArrayStoreException", 9}, {"cce", "java.lang.ClassCastException", 8}, {"negativeBeforeCap", "java.lang.NegativeArraySizeException", 4}} {
		verifyM5cdJava8Outcome(t, [][]byte{classfile}, "VerifyM5cdTypes", tc.method, nil, "exception="+tc.class)
		verifyM5cdAssertException(t, func() (Result, error) { return Run(classfile, tc.method, nil, verifyM5cdGasLimit) }, tc.class, tc.kind)
	}

	for _, leaf := range []string{"F", "D"} {
		descriptor := strings.Repeat("[", 255) + leaf
		withRank, index := verifyM5cdAppendNameAndClass(t, classfile, descriptor)
		full := make([]byte, 0, 800)
		for i := 0; i < 255; i++ {
			full = append(full, 0x04)
		}
		full = append(full, 0xc5, byte(index>>8), byte(index), 255)
		for i := 0; i < 254; i++ {
			full = append(full, 0x03, 0x32)
		}
		full = append(full, 0xbe, 0xac)
		fullClass := verifyM5cdRewriteCode(t, withRank, "padding", "()I", full, 300, 1)
		verifyM5cdRunValue(t, fullClass, "padding", nil, 1, verifyM5cdCapacityGasLimit)

		for _, rank := range []int{254, 255} {
			withComponent, component := verifyM5cdAppendNameAndClass(t, classfile, strings.Repeat("[", rank)+leaf)
			code := []byte{0x04, 0xbd, byte(component >> 8), byte(component), 0xbe, 0xac}
			candidate := verifyM5cdRewriteCode(t, withComponent, "padding", "()I", code, 2, 1)
			if rank == 254 {
				verifyM5cdRunValue(t, candidate, "padding", nil, 1, verifyM5cdGasLimit)
			} else {
				verifyM5cdAssertError(t, func() (Result, error) { return Run(candidate, "padding", nil, verifyM5cdGasLimit) }, "ArrayError(uint256,uint256)", 2, 1)
			}
		}
	}
	withVoid, voidIndex := verifyM5cdAppendNameAndClass(t, classfile, "[V")
	voidCode := []byte{0x04, 0xbd, byte(voidIndex >> 8), byte(voidIndex), 0xbe, 0xac}
	voidClass := verifyM5cdRewriteCode(t, withVoid, "padding", "()I", voidCode, 2, 1)
	verifyM5cdAssertError(t, func() (Result, error) { return Run(voidClass, "padding", nil, verifyM5cdGasLimit) }, "TypeError(uint256,uint256)", 1, 1)

	for _, descriptor := range []string{"[[F", "[[D"} {
		withMulti, index := verifyM5cdAppendNameAndClass(t, classfile, descriptor)
		valid := []byte{0x04, 0x04, 0xc5, byte(index >> 8), byte(index), 2, 0xbe, 0xac}
		candidate := verifyM5cdRewriteCode(t, withMulti, "padding", "()I", valid, 2, 1)
		verifyM5cdRunValue(t, candidate, "padding", nil, 1, verifyM5cdGasLimit)
		for _, dimensions := range []byte{0, 3} {
			badCode := append([]byte(nil), valid...)
			badCode[5] = dimensions
			bad := verifyM5cdRewriteCode(t, withMulti, "padding", "()I", badCode, 2, 1)
			verifyM5cdAssertError(t, func() (Result, error) { return Run(bad, "padding", nil, verifyM5cdGasLimit) }, "ArrayError(uint256,uint256)", 3, 2)
		}
	}
	for _, descriptor := range []string{"[Qbad", strings.Repeat("[", 256) + "F"} {
		withBad, index := verifyM5cdAppendNameAndClass(t, classfile, descriptor)
		code := []byte{0x04, 0xc5, byte(index >> 8), byte(index), 1, 0xbe, 0xac}
		bad := verifyM5cdRewriteCode(t, withBad, "padding", "()I", code, 2, 1)
		verifyM5cdAssertError(t, func() (Result, error) { return Run(bad, "padding", nil, verifyM5cdGasLimit) }, "TypeError(uint256,uint256)", 1, 1)
	}
}

func TestVerifyM5cdOpcodeKindsCategoryTwoPrefixesLocalsAtypesAndPCs(t *testing.T) {
	base := verifyM5cdCompile(t, map[string]string{
		"VerifyM5cdRaw.java": `public final class VerifyM5cdRaw {
			public static int fload(){float[] a=new float[1];return (int)a[0];} public static int dload(){double[] a=new double[1];return (int)a[0];}
			public static int iload(){int[] a=new int[1];return a[0];} public static int jload(){long[] a=new long[1];return (int)a[0];}
			public static int nested(){float[][] a=new float[1][];return a[0]==null?1:0;} public static int nestedD(){double[][] a=new double[1][];return a[0]==null?1:0;}
			public static int padding(){int x=0;` + strings.Repeat("x=x+1;", 500) + `return x;}
		}`,
	}, "VerifyM5cdRaw")["VerifyM5cdRaw"]
	for _, tc := range []struct {
		method   string
		from, to byte
	}{
		{"fload", verifyM5cdFaload, 0x2e}, {"fload", verifyM5cdFaload, verifyM5cdDaload},
		{"dload", verifyM5cdDaload, 0x2f}, {"dload", verifyM5cdDaload, verifyM5cdFaload},
		{"iload", 0x2e, verifyM5cdFaload}, {"jload", 0x2f, verifyM5cdDaload},
		{"nested", 0x32, verifyM5cdFaload}, {"nestedD", 0x32, verifyM5cdDaload},
	} {
		t.Run(tc.method+fmt.Sprintf("-%02x", tc.to), func(t *testing.T) {
			bad := verifyM5cdReplaceOpcode(t, base, tc.method, "()I", tc.from, tc.to, 1)
			pc := verifyM5cdInstructionPC(t, parseStaticsClass(t, bad).namedMethod(t, tc.method).code, tc.to, 0)
			verifyM5cdAssertError(t, func() (Result, error) { return Run(bad, tc.method, nil, verifyM5cdGasLimit) }, "ReferenceError(uint256,uint256)", 1, uint64(pc))
		})
	}

	valid := []struct {
		name       string
		code       []byte
		maxS, maxL uint16
		want       int32
	}{
		{"float-prefix-local", []byte{0x10, 40, 0x04, verifyM5cdNewarray, 6, 0x59, 0x03, 0x0d, verifyM5cdFastore, 0x03, verifyM5cdFaload, 0x45, 0x24, 0x8b, 0x60, 0xac}, 5, 3, 42},
		{"double-prefix-local", []byte{0x10, 40, 0x04, verifyM5cdNewarray, 7, 0x59, 0x03, 0x0f, verifyM5cdDastore, 0x03, verifyM5cdDaload, 0x48, 0x27, 0x8e, 0x60, 0xac}, 6, 3, 41},
	}
	for _, tc := range valid {
		classfile := verifyM5cdRewriteCode(t, base, "padding", "()I", tc.code, tc.maxS, tc.maxL)
		verifyM5cdJava8Outcome(t, [][]byte{verifyM5cdMajor49(classfile)}, "VerifyM5cdRaw", "padding", nil, "value="+strconv.Itoa(int(tc.want)))
		verifyM5cdRunValue(t, classfile, "padding", nil, tc.want, verifyM5cdSimpleGasLimit)
	}

	wrongHeap := []struct {
		name string
		code []byte
		op   byte
	}{
		{"fastore-double", []byte{0x04, verifyM5cdNewarray, 7, 0x03, 0x0c, verifyM5cdFastore, 0x03, 0xac}, verifyM5cdFastore},
		{"dastore-float", []byte{0x04, verifyM5cdNewarray, 6, 0x03, 0x0e, verifyM5cdDastore, 0x03, 0xac}, verifyM5cdDastore},
		{"iastore-float", []byte{0x04, verifyM5cdNewarray, 6, 0x03, 0x03, 0x4f, 0x03, 0xac}, 0x4f},
		{"lastore-double", []byte{0x04, verifyM5cdNewarray, 7, 0x03, 0x09, 0x50, 0x03, 0xac}, 0x50},
		{"aastore-float", []byte{0x04, verifyM5cdNewarray, 6, 0x03, 0x01, 0x53, 0x03, 0xac}, 0x53},
	}
	for _, tc := range wrongHeap {
		bad := verifyM5cdRewriteCode(t, base, "padding", "()I", tc.code, 8, 1)
		pc := verifyM5cdInstructionPC(t, tc.code, tc.op, 0)
		verifyM5cdAssertError(t, func() (Result, error) { return Run(bad, "padding", nil, verifyM5cdGasLimit) }, "ReferenceError(uint256,uint256)", 1, uint64(pc))
	}

	classIndex := parseStaticsClass(t, base).thisClass
	badOperands := []struct {
		name string
		code []byte
		op   byte
		kind uint64
	}{
		{"faload-empty", []byte{verifyM5cdFaload, 0x57, 0x03, 0xac}, verifyM5cdFaload, 3},
		{"dastore-empty", []byte{verifyM5cdDastore, 0x03, 0xac}, verifyM5cdDastore, 3},
		{"int-as-array", []byte{0x03, 0x03, verifyM5cdFaload, 0x57, 0x03, 0xac}, verifyM5cdFaload, 14},
		{"ref-as-index", []byte{0x04, verifyM5cdNewarray, 6, 0x01, verifyM5cdFaload, 0x57, 0x03, 0xac}, verifyM5cdFaload, 14},
		{"int-as-float", []byte{0x04, verifyM5cdNewarray, 6, 0x03, 0x04, verifyM5cdFastore, 0x03, 0xac}, verifyM5cdFastore, 14},
		{"long-as-double", []byte{0x04, verifyM5cdNewarray, 7, 0x03, 0x09, verifyM5cdDastore, 0x03, 0xac}, verifyM5cdDastore, 14},
		{"two-floats-not-double", []byte{0x04, verifyM5cdNewarray, 7, 0x03, 0x0c, 0x0d, verifyM5cdDastore, 0x03, 0xac}, verifyM5cdDastore, 14},
		{"uninitialized-as-array", []byte{0xbb, byte(classIndex >> 8), byte(classIndex), 0x03, verifyM5cdFaload, 0x57, 0x03, 0xac}, verifyM5cdFaload, 14},
		{"null-count", []byte{0x01, verifyM5cdNewarray, 6, 0xbe, 0xac}, verifyM5cdNewarray, 14},
	}
	for _, tc := range badOperands {
		bad := verifyM5cdRewriteCode(t, base, "padding", "()I", tc.code, 8, 1)
		pc := verifyM5cdInstructionPC(t, tc.code, tc.op, 0)
		verifyM5cdAssertError(t, func() (Result, error) { return Run(bad, "padding", nil, verifyM5cdGasLimit) }, "BytecodeError(uint256,uint256)", tc.kind, uint64(pc))
	}
	// A double is indivisible and needs two max_stack words before dastore.
	capacityCode := []byte{0x04, verifyM5cdNewarray, 7, 0x03, 0x0f, verifyM5cdDastore, 0x03, 0xac}
	capacity := verifyM5cdRewriteCode(t, base, "padding", "()I", capacityCode, 3, 1)
	dconstPC := verifyM5cdInstructionPC(t, capacityCode, 0x0f, 0)
	verifyM5cdAssertError(t, func() (Result, error) { return Run(capacity, "padding", nil, verifyM5cdGasLimit) }, "BytecodeError(uint256,uint256)", 9, uint64(dconstPC))

	// dstore into an overlapping local pair invalidates both pre-existing
	// category-two values. This independently protects D's head/tail identity.
	for _, tc := range []struct {
		name string
		code []byte
		kind uint64
	}{
		{"dstore-overlaps-left", []byte{0x0f, 0x47, 0x0f, 0x49, 0x0f, 0x48, 0x26, 0x8e, 0xac}, 11},
		{"dstore-overlaps-right-head", []byte{0x0f, 0x47, 0x0f, 0x49, 0x0f, 0x48, 0x28, 0x8e, 0xac}, 14},
	} {
		bad := verifyM5cdRewriteCode(t, base, "padding", "()I", tc.code, 6, 4)
		verifyM5cdAssertError(t, func() (Result, error) { return Run(bad, "padding", nil, verifyM5cdGasLimit) }, "BytecodeError(uint256,uint256)", tc.kind, 6)
	}

	// Every JVM newarray atype is now valid; no accidental 6/7-only whitelist.
	for atype := byte(4); atype <= 11; atype++ {
		code := []byte{0x04, verifyM5cdNewarray, atype, 0xbe, 0xac}
		classfile := verifyM5cdRewriteCode(t, base, "padding", "()I", code, 2, 1)
		verifyM5cdRunValue(t, classfile, "padding", nil, 1, verifyM5cdSimpleGasLimit)
	}
	for _, atype := range []byte{0, 3, 12} {
		code := []byte{0x04, verifyM5cdNewarray, atype, 0xbe, 0xac}
		classfile := verifyM5cdRewriteCode(t, base, "padding", "()I", code, 2, 1)
		verifyM5cdAssertError(t, func() (Result, error) { return Run(classfile, "padding", nil, verifyM5cdGasLimit) }, "ArrayError(uint256,uint256)", 1, 1)
	}
	truncated := verifyM5cdRewriteAtEnd(t, base, "padding", "()I", []byte{verifyM5cdNewarray})
	truncatedPC := len(parseStaticsClass(t, truncated).namedMethod(t, "padding").code) - 1
	verifyM5cdAssertError(t, func() (Result, error) { return Run(truncated, "padding", nil, verifyM5cdGasLimit) }, "BytecodeError(uint256,uint256)", 2, uint64(truncatedPC))
	// The branch target is PC 6, the atype operand, not an instruction. This is
	// an actual classfile PC check, not a byte-pattern search through operands.
	branchCode := []byte{0x03, 0x99, 0, 5, 0x04, verifyM5cdNewarray, 6, 0x57, 0x03, 0xac}
	if pc := verifyM5cdInstructionPC(t, branchCode, verifyM5cdNewarray, 0); pc != 5 {
		t.Fatalf("boundary-aware newarray pc=%d want 5", pc)
	}
	branch := verifyM5cdRewriteCode(t, base, "padding", "()I", branchCode, 2, 1)
	verifyM5cdAssertError(t, func() (Result, error) { return Run(branch, "padding", nil, verifyM5cdGasLimit) }, "BytecodeError(uint256,uint256)", 12, 1)
}

func TestVerifyM5cdNullBoundsEvaluationInitializationRegistryAndDeferredFeatures(t *testing.T) {
	classes := verifyM5cdCompile(t, map[string]string{
		"VerifyM5cdFaults.java": `public final class VerifyM5cdFaults {
			static int trace; static int zero(){return 0;} static float fzero(){return 0f;} static double dzero(){return 0d;}
			static float[] fa(){trace=trace*10+1;return new float[1];} static double[] da(){trace=trace*10+1;return new double[1];} static long[] ja(){trace=trace*10+1;return new long[1];}
			static int ix(){trace=trace*10+2;return 0;} static float fv(){trace=trace*10+3;return -0.0f;} static double dv(){trace=trace*10+3;return -0.0d;} static long jv(){trace=trace*10+3;return 7L;}
			public static int storeOrderF(){trace=0;fa()[ix()]=fv();return trace;} public static int storeOrderD(){trace=0;da()[ix()]=dv();return trace;} public static int storeOrderJ(){trace=0;ja()[ix()]=jv();return trace;}
			public static int negativeF(int n){return new float[n].length;} public static int negativeD(int n){return new double[n].length;}
			public static int loadNullF(int i){float[] a=null;return (int)a[i];} public static int loadNullD(int i){double[] a=null;return (int)a[i];}
			public static int storeNullF(int i){float[] a=null;a[i]=1f;return 1;} public static int storeNullD(int i){double[] a=null;a[i]=1d;return 1;}
			public static int loadBoundsF(int i){return (int)(new float[2])[i];} public static int loadBoundsD(int i){return (int)(new double[2])[i];}
			public static int storeBoundsF(int i){float[] a=new float[2];a[i]=1f;return 1;} public static int storeBoundsD(int i){double[] a=new double[2];a[i]=1d;return 1;}
			public static int intBeforeNullF(){float[] a=null;a[99]=(float)(1/zero());return 1;} public static int intBeforeNullD(){double[] a=null;a[99]=(double)(1/zero());return 1;}
			public static int fpBeforeNullF(){float[] a=null;a[99]=1f/fzero();return 1;} public static int fpBeforeNullD(){double[] a=null;a[99]=1d/dzero();return 1;}
			public static int handled(){try{return loadBoundsF(9);}catch(ArrayIndexOutOfBoundsException x){return 7;}}
		}`,
		"VerifyM5cdInitArithmetic.java": `public final class VerifyM5cdInitArithmetic {static int z(){return 0;}static float[] a=fail();static float[] fail(){float[] x=null;x[0]=(float)(1/z());return x;}public static int run(){return a.length;}}`,
		"UnknownM5cdNative.java":        `public final class UnknownM5cdNative {public static native int arrayBits(float[] x);}`,
		"UnknownM5cdRoot.java":          `public final class UnknownM5cdRoot {public static int run(){return UnknownM5cdNative.arrayBits(new float[1]);}}`,
	}, "VerifyM5cdFaults", "VerifyM5cdInitArithmetic", "UnknownM5cdNative", "UnknownM5cdRoot")
	faults := classes["VerifyM5cdFaults"]
	for _, method := range []string{"storeOrderF", "storeOrderD", "storeOrderJ"} {
		verifyM5cdJava8Outcome(t, [][]byte{faults}, "VerifyM5cdFaults", method, nil, "value=123")
		verifyM5cdRunValue(t, faults, method, nil, 123, verifyM5cdSimpleGasLimit)
	}
	for _, method := range []string{"negativeF", "negativeD"} {
		verifyM5cdAssertException(t, func() (Result, error) { return Run(faults, method, []int32{-1}, verifyM5cdGasLimit) }, "java.lang.NegativeArraySizeException", 4)
	}
	for _, method := range []string{"loadNullF", "loadNullD", "storeNullF", "storeNullD"} {
		for _, index := range []int32{-1, 65537} {
			verifyM5cdAssertException(t, func() (Result, error) { return Run(faults, method, []int32{index}, verifyM5cdGasLimit) }, "java.lang.NullPointerException", 6)
		}
	}
	for _, method := range []string{"loadBoundsF", "loadBoundsD", "storeBoundsF", "storeBoundsD"} {
		for _, index := range []int32{-1, 2} {
			verifyM5cdAssertException(t, func() (Result, error) { return Run(faults, method, []int32{index}, verifyM5cdGasLimit) }, "java.lang.ArrayIndexOutOfBoundsException", 5)
		}
	}
	for _, method := range []string{"intBeforeNullF", "intBeforeNullD"} {
		verifyM5cdJava8Outcome(t, [][]byte{faults}, "VerifyM5cdFaults", method, nil, "exception=java.lang.ArithmeticException")
		verifyM5cdAssertException(t, func() (Result, error) { return Run(faults, method, nil, verifyM5cdGasLimit) }, "java.lang.ArithmeticException", 1)
	}
	for _, method := range []string{"fpBeforeNullF", "fpBeforeNullD"} {
		verifyM5cdJava8Outcome(t, [][]byte{faults}, "VerifyM5cdFaults", method, nil, "exception=java.lang.NullPointerException")
		verifyM5cdAssertException(t, func() (Result, error) { return Run(faults, method, nil, verifyM5cdGasLimit) }, "java.lang.NullPointerException", 6)
	}
	init := classes["VerifyM5cdInitArithmetic"]
	verifyM5cdJava8Outcome(t, [][]byte{init}, "VerifyM5cdInitArithmetic", "run", nil, "exception=java.lang.ExceptionInInitializerError")
	verifyM5cdAssertException(t, func() (Result, error) { return Run(init, "run", nil, verifyM5cdGasLimit) }, "java.lang.ExceptionInInitializerError", 3)

	// M5d-a supersedes the old handler rejection: verify real catch behavior
	// against Java8, retaining the original guest source and gas ceiling.
	// Unknown native array helpers still fail; only four raw-bit bindings exist.
	verifyM5cdJava8Outcome(t, [][]byte{faults}, "VerifyM5cdFaults", "handled", nil, "value=7")
	verifyM5cdRunValue(t, faults, "handled", nil, 7, verifyM5cdGasLimit)
	unknownBundle := verifyM5cdBundle(map[string][]byte{"UnknownM5cdNative": classes["UnknownM5cdNative"], "UnknownM5cdRoot": classes["UnknownM5cdRoot"]})
	root := parseStaticsClass(t, classes["UnknownM5cdRoot"])
	pc := verifyM5cdMemberPC(t, root, root.method(t, "run", "()I"), 0xb8, 10, "arrayBits", "([F)I")
	verifyM5cdAssertError(t, func() (Result, error) {
		return RunClasses(unknownBundle, "UnknownM5cdRoot", "run", nil, verifyM5cdGasLimit)
	}, "CallError(uint256,uint256)", 4, uint64(pc))

	names := []string{
		"java.lang.ArithmeticException", "java.lang.StackOverflowError", "java.lang.ExceptionInInitializerError",
		"java.lang.NegativeArraySizeException", "java.lang.ArrayIndexOutOfBoundsException", "java.lang.NullPointerException",
		"java.lang.OutOfMemoryError", "java.lang.ClassCastException", "java.lang.ArrayStoreException",
		"java.lang.IncompatibleClassChangeError", "java.lang.AbstractMethodError",
		"java.lang.NoClassDefFoundError",
	}
	selector := crypto.Keccak256([]byte("JavaException(uint256)"))[:4]
	for i, want := range names {
		data := make([]byte, 36)
		copy(data, selector)
		data[35] = byte(i + 1)
		if got, ok := decodeJavaException(data); !ok || got != want {
			t.Fatalf("kind %d decoded %q/%v want %q", i+1, got, ok, want)
		}
	}
	unknown := make([]byte, 36)
	copy(unknown, selector)
	unknown[35] = 13
	if got, ok := decodeJavaException(unknown); ok || got != "" {
		t.Fatalf("new exception kind accepted: %q/%v", got, ok)
	}
	result, err := Run(faults, "negativeF", []int32{1}, 1)
	if err == nil || !errors.Is(err, vm.ErrOutOfGas) || result.ExceptionClass != "" || len(result.RevertData) != 0 {
		t.Fatalf("result/error=%+v/%v want unlabeled EVM out of gas", result, err)
	}
}

func TestVerifyM5cdSharedArrayQuotasOneDoubleElementNoGCResetAndObjectIndependence(t *testing.T) {
	classfile := verifyM5cdCompile(t, map[string]string{
		"VerifyM5cdCaps.java": `public final class VerifyM5cdCaps {
			public static int mixed(int n){Object x=null;for(int k=0;k<n;k++){switch(k%5){case 0:x=new float[0];break;case 1:x=new double[0];break;case 2:x=new int[0];break;case 3:x=new long[0];break;default:x=new Object[0];}}return n+(x==null?0:0);}
			public static int perArray(int n){return new double[n].length;}
			public static int exactDoubleElements(){Object x=null;for(int k=0;k<4;k++)x=new double[65536];return 262144+(x==null?0:0);}
			public static int overElements(){Object x=null;for(int k=0;k<4;k++)x=new double[65536];x=new float[1];return 1;}
			public static int arraysAndObjects(){Object a=null,o=null;for(int k=0;k<1024;k++)a=(k&1)==0?(Object)new float[0]:(Object)new double[0];for(int k=0;k<1024;k++)o=new Object();return (a==null?0:1)+(o==null?0:1);}
		}`,
	}, "VerifyM5cdCaps")["VerifyM5cdCaps"]
	for _, tc := range []struct {
		method string
		args   []int32
		want   int32
	}{
		{"mixed", []int32{1024}, 1024}, {"perArray", []int32{65536}, 65536},
		{"exactDoubleElements", nil, 262144}, {"arraysAndObjects", nil, 2},
	} {
		result := verifyM5cdRunValue(t, classfile, tc.method, tc.args, tc.want, verifyM5cdCapacityGasLimit)
		t.Logf("M5c-d quota %s gas=%d limit=%d", tc.method, result.GasUsed, verifyM5cdCapacityGasLimit)
	}
	for _, tc := range []struct {
		method string
		args   []int32
	}{
		{"mixed", []int32{1025}}, {"perArray", []int32{65537}}, {"overElements", nil},
	} {
		verifyM5cdAssertException(t, func() (Result, error) { return Run(classfile, tc.method, tc.args, verifyM5cdCapacityGasLimit) }, "java.lang.OutOfMemoryError", 7)
	}
	// Unreachable arrays count within one invocation. A fresh invocation resets
	// all allocation/cell state, so the exact-cap run succeeds again.
	verifyM5cdRunValue(t, classfile, "mixed", []int32{1024}, 1024, verifyM5cdCapacityGasLimit)
}

func TestVerifyM5cdArrayReferencesUseOneFieldSlotAndDescriptorBoundaries(t *testing.T) {
	for _, count := range []int{1024, 1025} {
		var source strings.Builder
		source.WriteString("public final class VerifyM5cdFieldQuota {")
		for i := 0; i < count; i++ {
			if i&1 == 0 {
				fmt.Fprintf(&source, "float[] f%d;", i)
			} else {
				fmt.Fprintf(&source, "double[] d%d;", i)
			}
		}
		source.WriteString("public static int run(){return new VerifyM5cdFieldQuota()==null?0:1;}}")
		classfile := verifyM5cdCompile(t, map[string]string{"VerifyM5cdFieldQuota.java": source.String()}, "VerifyM5cdFieldQuota")["VerifyM5cdFieldQuota"]
		if count == 1024 {
			verifyM5cdRunValue(t, classfile, "run", nil, 1, verifyM5cdCapacityGasLimit)
		} else {
			verifyM5cdAssertException(t, func() (Result, error) { return Run(classfile, "run", nil, verifyM5cdCapacityGasLimit) }, "java.lang.OutOfMemoryError", 7)
		}
	}

	original := verifyM5cdCompile(t, map[string]string{
		"VerifyM5cdDescriptors.java": `public final class VerifyM5cdDescriptors {
			static float[] field; static final float[] FIN=new float[1]; static int accept(float[] x){return x.length;} static float[] give(){return new float[1];}
			public static int argument(){return accept(new float[1]);} public static int staticField(){field=new float[1];return field.length;} public static int returned(){return give().length;}
			public static int mutateFinal(){FIN[0]=3f;return (int)FIN[0];}
		}`,
	}, "VerifyM5cdDescriptors")["VerifyM5cdDescriptors"]
	verifyM5cdRunValue(t, original, "mutateFinal", nil, 3, verifyM5cdSimpleGasLimit)
	for _, tc := range []struct {
		method   string
		boundary byte
		entry    string
	}{
		{"argument", 0xb8, "argument"}, {"staticField", 0xb3, "staticField"}, {"give", 0xb0, "returned"},
	} {
		bad := verifyM5cdMutate(t, original, func(_ []byte, c staticsClass) {
			m := c.namedMethod(t, tc.method)
			newPC := verifyM5cdInstructionPC(t, m.code, verifyM5cdNewarray, 0)
			if m.code[newPC+1] != 6 {
				t.Fatalf("%s atype=%d want float", tc.method, m.code[newPC+1])
			}
			m.code[newPC+1] = 7
		})
		pc := verifyM5cdInstructionPC(t, parseStaticsClass(t, bad).namedMethod(t, tc.method).code, tc.boundary, 0)
		verifyM5cdAssertError(t, func() (Result, error) { return Run(bad, tc.entry, nil, verifyM5cdGasLimit) }, "ReferenceError(uint256,uint256)", 2, uint64(pc))
	}
	badFinal := verifyM5cdMutate(t, original, func(raw []byte, c staticsClass) {
		field := c.field(t, "field", "[F")
		raw[field.accessOffset] = byte((field.access | accFinal) >> 8)
		raw[field.accessOffset+1] = byte(field.access | accFinal)
	})
	parsedFinal := parseStaticsClass(t, badFinal)
	finalPC := verifyM5cdFieldPC(t, parsedFinal, parsedFinal.method(t, "staticField", "()I"), 0xb3, "field", "[F")
	verifyM5cdAssertError(t, func() (Result, error) { return Run(badFinal, "staticField", nil, verifyM5cdGasLimit) }, "FieldError(uint256,uint256)", 4, uint64(finalPC))

	for _, tc := range []struct {
		method string
		args   []int32
	}{
		{"accept", nil}, {"accept", []int32{0}}, {"give", nil},
	} {
		verifyM5cdAssertMethodError(t, func() (Result, error) { return Run(original, tc.method, tc.args, verifyM5cdGasLimit) }, 11)
	}
}

// --- M5c-d verifier-only helpers ---

func verifyM5cdCompile(t *testing.T, sources map[string]string, internalNames ...string) map[string][]byte {
	t.Helper()
	return verifyM5ccCompile(t, sources, internalNames...)
}

func verifyM5cdBundle(classes map[string][]byte) [][]byte { return verifyM5bbBundle(classes) }

func verifyM5cdReplaceClass(classes map[string][]byte, name string, replacement []byte) map[string][]byte {
	return verifyM5bbReplaceClass(classes, name, replacement)
}

func verifyM5cdMutate(t *testing.T, original []byte, edit func([]byte, staticsClass)) []byte {
	t.Helper()
	return verifyM5bbMutate(t, original, edit)
}

func verifyM5cdRewriteCode(t *testing.T, original []byte, name, descriptor string, code []byte, maxStack, maxLocals uint16) []byte {
	t.Helper()
	return verifyM5bbRewriteCode(t, original, name, descriptor, code, maxStack, maxLocals)
}

func verifyM5cdRewriteAtEnd(t *testing.T, original []byte, name, descriptor string, ending []byte) []byte {
	t.Helper()
	return verifyM5bbRewriteAtEnd(t, original, name, descriptor, ending)
}

func verifyM5cdReplaceOpcode(t *testing.T, original []byte, name, descriptor string, from, to byte, want int) []byte {
	t.Helper()
	return verifyM5bbReplaceOpcode(t, original, name, descriptor, from, to, want)
}

func verifyM5cdInstructionPC(t *testing.T, code []byte, opcode byte, occurrence int) int {
	t.Helper()
	return verifyM5bbInstructionPC(t, code, opcode, occurrence)
}

func verifyM5cdMemberPC(t *testing.T, c staticsClass, m staticsMethod, opcode, tag byte, name, descriptor string) int {
	t.Helper()
	return verifyM5bbMemberPC(t, c, m, opcode, tag, name, descriptor)
}

func verifyM5cdAppendNameAndClass(t *testing.T, original []byte, name string) ([]byte, uint16) {
	t.Helper()
	return verifyM5bbAppendNameAndClass(t, original, name)
}

func verifyM5cdMajor49(classfile []byte) []byte { return verifyM5bbMajor49(classfile) }

func verifyM5cdFieldPC(t *testing.T, c staticsClass, m staticsMethod, opcode byte, name, descriptor string) int {
	t.Helper()
	return verifyM5cbFieldPC(t, c, m, opcode, name, descriptor)
}

type verifyM5cdOracle = verifyM5ccOracle

func verifyM5cdNewOracle(t *testing.T, classfiles ...[]byte) verifyM5cdOracle {
	t.Helper()
	return verifyM5ccNewOracle(t, classfiles...)
}

func verifyM5cdJava8Outcome(t *testing.T, bundle [][]byte, mainClass, method string, args []int32, want string) {
	t.Helper()
	verifyM5bbJava8Outcome(t, bundle, mainClass, method, args, want)
}

func verifyM5cdRunValue(t *testing.T, classfile []byte, method string, args []int32, want int32, gas uint64) Result {
	t.Helper()
	result, err := Run(classfile, method, args, gas)
	if err != nil || result.ExceptionClass != "" || result.Value != want || result.GasUsed == 0 || result.GasUsed > gas || len(result.RevertData) != 0 {
		t.Fatalf("%s%v result/error=%+v/%v want value=%d within gas=%d", method, args, result, err, want, gas)
	}
	return result
}

func verifyM5cdRunClassesValue(t *testing.T, bundle [][]byte, root, method string, args []int32, want int32, gas uint64) Result {
	t.Helper()
	result, err := RunClasses(bundle, root, method, args, gas)
	if err != nil || result.ExceptionClass != "" || result.Value != want || result.GasUsed == 0 || result.GasUsed > gas || len(result.RevertData) != 0 {
		t.Fatalf("%s.%s%v result/error=%+v/%v want value=%d within gas=%d", root, method, args, result, err, want, gas)
	}
	return result
}

func verifyM5cdAssertException(t *testing.T, run func() (Result, error), want string, kind byte) {
	t.Helper()
	verifyM5bbAssertException(t, run, want, kind)
}

func verifyM5cdAssertError(t *testing.T, run func() (Result, error), signature string, code, location uint64) {
	t.Helper()
	verifyM5bbAssertError(t, run, signature, code, location)
}

func verifyM5cdAssertMethodError(t *testing.T, run func() (Result, error), code uint64) {
	t.Helper()
	verifyM5bbAssertMethodError(t, run, code)
}
