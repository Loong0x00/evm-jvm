// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"context"
	"encoding/binary"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"testing"
	"time"

	"github.com/ethereum/go-ethereum/core/vm"
	"github.com/ethereum/go-ethereum/crypto"
)

const (
	verifyM5aGasLimit         = uint64(100_000_000)
	verifyM5aCapacityGasLimit = uint64(250_000_000)
	verifyM5aNewarray         = byte(0xbc)
	verifyM5aBaload           = byte(0x33)
	verifyM5aCaload           = byte(0x34)
	verifyM5aSaload           = byte(0x35)
	verifyM5aBastore          = byte(0x54)
	verifyM5aCastore          = byte(0x55)
	verifyM5aSastore          = byte(0x56)
)

// All inputs below are bounded trusted Java 8 fixtures. Controlled mutations
// preserve raw classfile execution: neither these tests nor production host code
// parse or translate a guest on the execution path.

func TestVerifyM5aRootABIRejectsEveryNarrowDeclaredType(t *testing.T) {
	classes := verifyM5aCompile(t, map[string]string{
		"roots/NarrowRoots.java": `package roots; public final class NarrowRoots {
			public static boolean argZ(boolean x){return x;} public static byte argB(byte x){return x;}
			public static char argC(char x){return x;} public static short argS(short x){return x;}
			public static boolean retZ(){return true;} public static byte retB(){return 1;}
			public static char retC(){return 1;} public static short retS(){return 1;}
			public static int exactI(int x){return x;}
		}`,
		"roots/NarrowIface.java": `package roots; public interface NarrowIface {
			static boolean argZ(boolean x){return x;} static byte argB(byte x){return x;}
			static char argC(char x){return x;} static short argS(short x){return x;}
			static boolean retZ(){return true;} static byte retB(){return 1;}
			static char retC(){return 1;} static short retS(){return 1;}
		}`,
	}, "roots/NarrowRoots", "roots/NarrowIface")
	for _, owner := range []string{"roots/NarrowRoots", "roots/NarrowIface"} {
		for _, method := range []string{"argZ", "argB", "argC", "argS", "retZ", "retB", "retC", "retS"} {
			t.Run(owner+"/"+method, func(t *testing.T) {
				args := []int32(nil)
				if strings.HasPrefix(method, "arg") {
					args = []int32{1}
				}
				verifyM5aAssertMethodError(t, func() (Result, error) {
					return RunClasses(verifyM5aBundle(classes), owner, method, args, verifyM5aGasLimit)
				}, 11)
			})
		}
	}
	verifyM5aAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM5aBundle(classes), "roots/NarrowRoots", "exactI", []int32{-7}, verifyM5aGasLimit)
	}, -7)
}

func TestVerifyM5aRawInvocationArgumentsAreNotImplicitlyNarrowedAcrossCallModes(t *testing.T) {
	classes := verifyM5aCompile(t, map[string]string{
		"rawcall/I.java": `package rawcall; public interface I {
			int iface(short x); default int defaultCall(byte x){return x;}
			static int staticCall(char x){return x;} static int booleanCall(boolean x){return x?100:2;}
		}`,
		"rawcall/C.java": `package rawcall; public class C implements I {
			public int seen; public C(byte x){seen=x;} public int virtualCall(byte x){return x;}
			public int iface(short x){return x;}
		}`,
		"rawcall/Helper.java": `package rawcall; public final class Helper { static int staticCall(byte x){return x;} }`,
		"rawcall/Root.java": `package rawcall; public final class Root {
			private int specialCall(byte x){return x;}
			public static int staticArg(int x){return Helper.staticCall((byte)x);}
			public static int cachedArg(int x){return Helper.staticCall((byte)x)+Helper.staticCall((byte)x);}
			public static int ifaceStaticArg(int x){return I.staticCall((char)x);}
			public static int specialArg(int x){return new Root().specialCall((byte)x);}
			public static int virtualArg(int x){return new C((byte)0).virtualCall((byte)x);}
			public static int interfaceArg(int x){I v=new C((byte)0);return v.iface((short)x);}
			public static int defaultArg(int x){I v=new C((byte)0);return v.defaultCall((byte)x);}
			public static int constructorArg(int x){return new C((byte)x).seen;}
			public static int booleanArg(){return I.booleanCall(false);}
		}`,
	}, "rawcall/I", "rawcall/C", "rawcall/Helper", "rawcall/Root")
	root := classes["rawcall/Root"]
	conversions := map[string]byte{
		"staticArg": 0x91, "cachedArg": 0x91, "ifaceStaticArg": 0x92, "specialArg": 0x91,
		"virtualArg": 0x91, "interfaceArg": 0x93, "defaultArg": 0x91, "constructorArg": 0x91,
	}
	for method, opcode := range conversions {
		root = verifyM5aReplaceInstructions(t, root, method, opcode, 0x00, -1)
	}
	// A boolean argument cannot be written from an int in Java source. Its
	// iconst_0 is changed to iconst_2; Java 8 proves that (Z)I receives raw 2.
	root = verifyM5aMutate(t, root, func(_ []byte, c staticsClass) {
		m := c.method(t, "booleanArg", "()I")
		callPC := verifyM5aMemberPC(t, c, m, 0xb8, 11, "booleanCall", "(Z)I")
		producer := verifyM5aPreviousInstruction(t, m.code, callPC)
		if m.code[producer] != 0x03 {
			t.Fatalf("boolean argument producer=0x%02x at pc %d, want iconst_0", m.code[producer], producer)
		}
		m.code[producer] = 0x05
	})
	classes["rawcall/Root"] = root
	bundle := verifyM5aBundle(classes)
	cases := []struct {
		method string
		args   []int32
		want   int32
	}{
		{"staticArg", []int32{255}, 255},
		{"cachedArg", []int32{255}, 510},
		{"ifaceStaticArg", []int32{-1}, -1},
		{"specialArg", []int32{255}, 255},
		{"virtualArg", []int32{255}, 255},
		{"interfaceArg", []int32{65535}, 65535},
		{"defaultArg", []int32{255}, 255},
		{"constructorArg", []int32{255}, 255},
		// No call-boundary narrowing: the callee's ordinary integer branch sees
		// raw 2 as nonzero. This is intentionally distinct from Z return/field/CV lowbit rules.
		{"booleanArg", nil, 100},
	}
	for _, tc := range cases {
		t.Run(tc.method, func(t *testing.T) {
			verifyM5aJava8Outcome(t, bundle, "rawcall.Root", tc.method, tc.args, "value="+strconv.Itoa(int(tc.want)))
			verifyM5aAssertValue(t, func() (Result, error) {
				return RunClasses(bundle, "rawcall/Root", tc.method, tc.args, verifyM5aGasLimit)
			}, tc.want)
		})
	}
}

func TestVerifyM5aIreturnNarrowsByActualDeclaredSubtype(t *testing.T) {
	classes := verifyM5aCompile(t, map[string]string{
		"rawreturn/I.java": `package rawreturn; public interface I {
			static int raw255(){return 255;} static int raw65535(){return 65535;}
			default byte defaultB(){return (byte)raw255();} char ifaceC();
			static short staticS(){return (short)raw65535();} static boolean staticZ(){return false;}
		}`,
		"rawreturn/C.java": `package rawreturn; public final class C implements I {
			static int raw255(){return 255;} static int rawMinus1(){return -1;}
			private byte specialB(){return (byte)raw255();} public byte virtualB(){return (byte)raw255();}
			public char ifaceC(){return (char)rawMinus1();} public int specialRoot(){return specialB();}
		}`,
		"rawreturn/Root.java": `package rawreturn; public final class Root {
			public static int staticS(){return I.staticS();} public static int staticZ(){return I.staticZ()?1:0;}
			public static int specialB(){return new C().specialRoot();}
			public static int virtualB(){return new C().virtualB();}
			public static int interfaceC(){I x=new C();return x.ifaceC();}
			public static int defaultB(){I x=new C();return x.defaultB();}
		}`,
	}, "rawreturn/I", "rawreturn/C", "rawreturn/Root")
	classes["rawreturn/I"] = verifyM5aReplaceInstructions(t, classes["rawreturn/I"], "defaultB", 0x91, 0x00, 1)
	classes["rawreturn/I"] = verifyM5aReplaceInstructions(t, classes["rawreturn/I"], "staticS", 0x93, 0x00, 1)
	classes["rawreturn/C"] = verifyM5aReplaceInstructions(t, classes["rawreturn/C"], "specialB", 0x91, 0x00, 1)
	classes["rawreturn/C"] = verifyM5aReplaceInstructions(t, classes["rawreturn/C"], "virtualB", 0x91, 0x00, 1)
	classes["rawreturn/C"] = verifyM5aReplaceInstructions(t, classes["rawreturn/C"], "ifaceC", 0x92, 0x00, 1)
	classes["rawreturn/I"] = verifyM5aRewriteMethodPrefix(t, classes["rawreturn/I"], "staticZ", "()Z", []byte{0x05, 0xac}, 1, 0)
	bundle := verifyM5aBundle(classes)
	cases := []struct {
		method string
		want   int32
	}{
		{"staticS", -1}, {"staticZ", 0}, {"specialB", -1}, {"virtualB", -1},
		{"interfaceC", 65535}, {"defaultB", -1},
	}
	for _, tc := range cases {
		t.Run(tc.method, func(t *testing.T) {
			verifyM5aJava8Outcome(t, bundle, "rawreturn.Root", tc.method, nil, "value="+strconv.Itoa(int(tc.want)))
			verifyM5aAssertValue(t, func() (Result, error) {
				return RunClasses(bundle, "rawreturn/Root", tc.method, nil, verifyM5aGasLimit)
			}, tc.want)
		})
	}
}

func TestVerifyM5aFieldsNormalizeOnPutAndPreserveOwnerCachesFinalsAndDefaults(t *testing.T) {
	classes := verifyM5aCompile(t, map[string]string{
		"nfields/Parent.java": `package nfields; public class Parent { public static byte hidden=(byte)255; }`,
		"nfields/Child.java":  `package nfields; public final class Child extends Parent { public static short hidden=(short)65535; }`,
		"nfields/Flags.java":  `package nfields; public interface Flags { char C=(char)-1; boolean Z=true; }`,
		"nfields/Box.java":    `package nfields; public final class Box { byte b; short s; char c; boolean z; }`,
		"nfields/Root.java": `package nfields; public final class Root {
			static byte b; static short s; static char c; static boolean z;
			public static int instance(int x){Box v=new Box();v.b=(byte)x;v.s=(short)x;v.c=(char)x;v.z=true;
				return v.b*1000000+v.s*1000+v.c+(v.z?1:0);}
			public static int statics(int x){b=(byte)x;s=(short)x;c=(char)x;z=true;
				return b*1000000+s*1000+c+(z?1:0);}
			public static int cached(int x){b=(byte)x;return b*1000+b;}
			public static int owners(){return Parent.hidden*1000000+Child.hidden*1000+Flags.C+(Flags.Z?1:0);}
		}`,
	}, "nfields/Parent", "nfields/Child", "nfields/Flags", "nfields/Box", "nfields/Root")
	root := classes["nfields/Root"]
	for _, method := range []string{"instance", "statics"} {
		for _, opcode := range []byte{0x91, 0x92, 0x93} {
			root = verifyM5aReplaceInstructions(t, root, method, opcode, 0x00, 1)
		}
	}
	root = verifyM5aReplaceInstructions(t, root, "cached", 0x91, 0x00, 1)
	// Change the immediate boolean values written by putfield and putstatic from
	// canonical true (1) to noncanonical 2. The fields must store lowbit zero.
	for _, tc := range []struct {
		method string
		put    byte
		field  string
	}{
		{"instance", 0xb5, "z"}, {"statics", 0xb3, "z"},
	} {
		root = verifyM5aMutate(t, root, func(_ []byte, c staticsClass) {
			m := c.namedMethod(t, tc.method)
			pc := verifyM5aFieldPC(t, c, m, tc.put, tc.field, "Z")
			producer := verifyM5aPreviousInstruction(t, m.code, pc)
			if m.code[producer] != 0x04 {
				t.Fatalf("%s boolean producer=0x%02x at pc %d, want iconst_1", tc.method, m.code[producer], producer)
			}
			m.code[producer] = 0x05
		})
	}
	classes["nfields/Root"] = root
	bundle := verifyM5aBundle(classes)
	for _, tc := range []struct {
		arg, want int32
	}{{255, -1_000_000 + 255_000 + 255}, {65535, -1_000_000 - 1_000 + 65535}} {
		for _, method := range []string{"instance", "statics"} {
			t.Run(method+"/"+strconv.Itoa(int(tc.arg)), func(t *testing.T) {
				// Z receives a raw 2 and therefore stores lowbit zero in both methods.
				verifyM5aJava8Outcome(t, bundle, "nfields.Root", method, []int32{tc.arg}, "value="+strconv.Itoa(int(tc.want)))
				verifyM5aAssertValue(t, func() (Result, error) {
					return RunClasses(bundle, "nfields/Root", method, []int32{tc.arg}, verifyM5aGasLimit)
				}, tc.want)
			})
		}
	}
	verifyM5aJava8Outcome(t, bundle, "nfields.Root", "cached", []int32{255}, "value=-1001")
	verifyM5aAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "nfields/Root", "cached", []int32{255}, verifyM5aGasLimit)
	}, -1001)
	verifyM5aAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "nfields/Root", "owners", nil, verifyM5aGasLimit)
	}, -1_000_000-1_000+65535+1)
	// Re-running proves all narrow static storage and resolution caches are VM-local.
	verifyM5aAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "nfields/Root", "statics", []int32{255}, verifyM5aGasLimit)
	}, -1_000_000+255_000+255)
}

func TestVerifyM5aConstantValueUsesDeclaredSubtypeAndIntegerPayload(t *testing.T) {
	old := verifyM5aCompile(t, map[string]string{
		"cv/Z.java": `package cv; public final class Z { public static boolean V; }`,
		"cv/B.java": `package cv; public final class B { public static byte V; }`,
		"cv/C.java": `package cv; public final class C { public static char V; }`,
		"cv/S.java": `package cv; public final class S { public static short V; }`,
		"cv/Root.java": `package cv; public final class Root {
			public static int z(){return Z.V?1:0;} public static int b(){return B.V;}
			public static int c(){return C.V;} public static int s(){return S.V;}
		}`,
	}, "cv/Root")
	fresh := verifyM5aCompile(t, map[string]string{
		"cv/Z.java": `package cv; public final class Z { public static final boolean V=false; }`,
		"cv/B.java": `package cv; public final class B { public static final byte V=0; }`,
		"cv/C.java": `package cv; public final class C { public static final char V=0; }`,
		"cv/S.java": `package cv; public final class S { public static final short V=0; }`,
	}, "cv/Z", "cv/B", "cv/C", "cv/S")
	cases := []struct {
		payload int32
		want    map[string]int32
	}{
		{2, map[string]int32{"z": 0, "b": 2, "c": 2, "s": 2}},
		{255, map[string]int32{"z": 1, "b": -1, "c": 255, "s": 255}},
		{-1, map[string]int32{"z": 1, "b": -1, "c": 65535, "s": -1}},
		{65535, map[string]int32{"z": 1, "b": -1, "c": 65535, "s": -1}},
	}
	for _, tc := range cases {
		t.Run(fmt.Sprint(tc.payload), func(t *testing.T) {
			classes := map[string][]byte{"cv/Root": old["cv/Root"]}
			for _, kind := range []string{"Z", "B", "C", "S"} {
				classes["cv/"+kind] = verifyM5aMutateConstantValue(t, fresh["cv/"+kind], "V", kind, tc.payload)
			}
			bundle := verifyM5aBundle(classes)
			for method, want := range tc.want {
				t.Run(method, func(t *testing.T) {
					verifyM5aJava8Outcome(t, bundle, "cv.Root", method, nil, "value="+strconv.Itoa(int(want)))
					verifyM5aAssertValue(t, func() (Result, error) {
						return RunClasses(bundle, "cv/Root", method, nil, verifyM5aGasLimit)
					}, want)
				})
			}
		})
	}
}

func TestVerifyM5aComputationalIntsIincAndExistingConversionsStay32Bit(t *testing.T) {
	classfile := compileJava(t, "NarrowComputational", `public final class NarrowComputational {
		static int byteLocal(byte x){x++;return x;} static int shortLocal(short x){x++;return x;}
		static int charLocal(char x){x++;return x;} static int boolLocal(boolean x){int y=x?2:3;y++;return y;}
		public static int run(int x){int y=2147483647;y++;return ((byte)x)*1000000+((short)x)*1000+((char)x)+(y==(-2147483647-1)?1:0);}
	}`)
	parsed := parseStaticsClass(t, classfile)
	// Narrow parameters are computational ints; javac emits explicit conversions
	// when source assignment requires narrowing. The unrelated int local's iinc
	// must retain full int32 wraparound.
	verifyM5aInstructionPC(t, parsed.namedMethod(t, "run").code, 0x84, 0)
	for _, op := range []byte{0x91, 0x92, 0x93} {
		if verifyM5aInstructionPC(t, parsed.namedMethod(t, "run").code, op, 0) < 0 {
			t.Fatalf("run lacks existing conversion 0x%02x", op)
		}
	}
	verifyM5aAssertValue(t, func() (Result, error) {
		return Run(classfile, "run", []int32{255}, verifyM5aGasLimit)
	}, -1_000_000+255_000+255+1)
}

func TestVerifyM5aPrimitiveArrayAtypesLoadsStoresDefaultsAndIdentity(t *testing.T) {
	classfile := compileJava(t, "NarrowArrays", `public final class NarrowArrays {
		public static int bytes(int x){byte[] a=new byte[2];a[0]=(byte)x;return a[0]*100+a[1];}
		public static int booleans(int x){boolean[] a=new boolean[2];a[0]=(x&1)!=0;return (a[0]?10:0)+(a[1]?1:0);}
		public static int chars(int x){char[] a=new char[2];a[0]=(char)x;return a[0]+a[1];}
		public static int shorts(int x){short[] a=new short[2];a[0]=(short)x;return a[0]+a[1];}
		public static int ints(int x){int[] a=new int[2];a[0]=x;return a[0]+a[1];}
		public static int identity(){byte[] b=new byte[0],ba=b;boolean[] z=new boolean[0];char[] c=new char[0];short[] s=new short[0];int[] i=new int[0];
			return (b==ba?1:0)+(b!=(Object)z?2:0)+(b!=(Object)c?4:0)+(b!=(Object)s?8:0)+(b!=(Object)i?16:0);}
	}`)
	c := parseStaticsClass(t, classfile)
	wantOps := map[string][]byte{
		"bytes": {verifyM5aBaload, verifyM5aBastore}, "booleans": {verifyM5aBaload, verifyM5aBastore},
		"chars": {verifyM5aCaload, verifyM5aCastore}, "shorts": {verifyM5aSaload, verifyM5aSastore},
		"ints": {0x2e, 0x4f},
	}
	wantAtypes := map[string]byte{"bytes": 8, "booleans": 4, "chars": 5, "shorts": 9, "ints": 10}
	for method, ops := range wantOps {
		code := c.namedMethod(t, method).code
		pc := verifyM5aInstructionPC(t, code, verifyM5aNewarray, 0)
		if code[pc+1] != wantAtypes[method] {
			t.Fatalf("%s newarray atype=%d want %d", method, code[pc+1], wantAtypes[method])
		}
		for _, op := range ops {
			verifyM5aInstructionPC(t, code, op, 0)
		}
	}
	for _, tc := range []struct {
		method    string
		arg, want int32
	}{
		{"bytes", 255, -100}, {"booleans", 255, 10}, {"booleans", 2, 0},
		{"chars", -1, 65535}, {"shorts", 65535, -1}, {"ints", -1, -1},
		{"identity", 0, 31},
	} {
		args := []int32(nil)
		if tc.method != "identity" {
			args = []int32{tc.arg}
		}
		verifyM5aAssertValue(t, func() (Result, error) { return Run(classfile, tc.method, args, verifyM5aGasLimit) }, tc.want)
	}
}

func TestVerifyM5aRawByteAndBooleanArrayStoresNormalizeByActualLeaf(t *testing.T) {
	classfile := compileJava(t, "RawNarrowArrayStores", `public final class RawNarrowArrayStores {
		public static int bytes(int x){byte[] a=new byte[1];a[0]=(byte)x;return a[0];}
		public static int booleans(){boolean[] a=new boolean[1];a[0]=true;return a[0]?1:0;}
	}`)
	classfile = verifyM5aReplaceInstructions(t, classfile, "bytes", 0x91, 0x00, 1)
	classfile = verifyM5aMutate(t, classfile, func(_ []byte, c staticsClass) {
		m := c.namedMethod(t, "booleans")
		pc := verifyM5aInstructionPC(t, m.code, verifyM5aBastore, 0)
		producer := verifyM5aPreviousInstruction(t, m.code, pc)
		if m.code[producer] != 0x04 {
			t.Fatalf("boolean[] producer=0x%02x at pc %d, want iconst_1", m.code[producer], producer)
		}
		m.code[producer] = 0x05
	})
	for _, tc := range []struct {
		method string
		args   []int32
		want   int32
	}{{"bytes", []int32{255}, -1}, {"booleans", nil, 0}} {
		t.Run(tc.method, func(t *testing.T) {
			verifyM5aJava8Outcome(t, [][]byte{classfile}, "RawNarrowArrayStores", tc.method, tc.args, "value="+strconv.Itoa(int(tc.want)))
			verifyM5aAssertValue(t, func() (Result, error) { return Run(classfile, tc.method, tc.args, verifyM5aGasLimit) }, tc.want)
		})
	}
}

func TestVerifyM5aBaloadBastoreDiscriminateByteBooleanAndWrongArrayKinds(t *testing.T) {
	original := compileJava(t, "NarrowArrayKinds", `public final class NarrowArrayKinds {
		public static int byteLoad(){byte[] a=new byte[1];a[0]=(byte)255;return a[0];}
		public static int boolLoad(){boolean[] a=new boolean[1];a[0]=true;return a[0]?1:0;}
		public static int charLoad(){char[] a=new char[1];return a[0];}
		public static int shortLoad(){short[] a=new short[1];return a[0];}
		public static int intLoad(){int[] a=new int[1];return a[0];}
		public static int nested(){byte[][] a=new byte[1][];return a[0]==null?1:0;}
		public static int padding(){int x=0;`+strings.Repeat("x=x+1;", 30)+`return x;}
	}`)
	cases := []struct {
		method   string
		from, to byte
	}{
		{"byteLoad", verifyM5aBaload, 0x2e}, {"charLoad", verifyM5aCaload, verifyM5aSaload},
		{"shortLoad", verifyM5aSaload, verifyM5aCaload}, {"intLoad", 0x2e, verifyM5aBaload},
		{"nested", 0x32, verifyM5aBaload},
	}
	for _, tc := range cases {
		t.Run(tc.method, func(t *testing.T) {
			bad := verifyM5aReplaceInstructions(t, original, tc.method, tc.from, tc.to, 1)
			pc := verifyM5aInstructionPC(t, parseStaticsClass(t, bad).namedMethod(t, tc.method).code, tc.to, 0)
			verifyM5aAssertError(t, func() (Result, error) { return Run(bad, tc.method, nil, verifyM5aGasLimit) }, "ReferenceError(uint256,uint256)", 1, uint64(pc))
		})
	}
	stackCases := []struct {
		name string
		code []byte
		op   byte
	}{
		{"int-as-array", []byte{0x03, 0x03, verifyM5aBaload, 0xac}, verifyM5aBaload},
		{"null-as-byte-value", []byte{0x04, verifyM5aNewarray, 8, 0x03, 0x01, verifyM5aBastore, 0x03, 0xac}, verifyM5aBastore},
		{"ref-as-index", []byte{0x04, verifyM5aNewarray, 8, 0x01, verifyM5aBaload, 0xac}, verifyM5aBaload},
	}
	for _, tc := range stackCases {
		bad := verifyM5aRewriteMethodPrefix(t, original, "padding", "()I", tc.code, 4, 1)
		pc := verifyM5aInstructionPC(t, tc.code, tc.op, 0)
		verifyM5aAssertError(t, func() (Result, error) { return Run(bad, "padding", nil, verifyM5aGasLimit) }, "BytecodeError(uint256,uint256)", 14, uint64(pc))
	}
}

func TestVerifyM5aPrimitiveArrayTypeIdentityCastsMarkersASEAndNestedMultianewarray(t *testing.T) {
	classfile := compileJava(t, "NarrowArrayTypes", `public final class NarrowArrayTypes {
		public static int markers(){Object[] a={new boolean[0],new byte[0],new char[0],new short[0],new int[0]};int n=0;
			for(int i=0;i<a.length;i++)if(a[i] instanceof Object && a[i] instanceof Cloneable && a[i] instanceof java.io.Serializable)n++;return n;}
		public static int matrix(){Object b=new byte[1],z=new boolean[1],i=new int[1],bb=new byte[1][];
			return (b instanceof byte[]?1:0)+(b instanceof boolean[]?2:0)+(z instanceof byte[]?4:0)
				+(i instanceof byte[]?8:0)+(bb instanceof Object[]?16:0)+(b instanceof Object[]?32:0);}
		public static int multi(){byte[][] b=new byte[2][3];boolean[][] z=new boolean[1][2];char[][] c=new char[1][4];short[][] s=new short[1][5];
			b[1][2]=(byte)255;z[0][1]=true;c[0][3]=(char)-1;s[0][4]=(short)65535;
			return b.length*10000000+b[0].length*100000+(z[0][1]?10000:0)+c[0][3]+s[0][4];}
		public static int ase(){Object[] a=new boolean[1][];a[0]=new byte[1];return 1;}
		public static int castBZ(){Object a=new byte[1];return ((boolean[])a).length;}
		public static int castZI(){Object a=new boolean[1];return ((int[])a).length;}
	}`)
	verifyM5aAssertValue(t, func() (Result, error) { return Run(classfile, "markers", nil, verifyM5aGasLimit) }, 5)
	verifyM5aAssertValue(t, func() (Result, error) { return Run(classfile, "matrix", nil, verifyM5aGasLimit) }, 17)
	verifyM5aAssertValue(t, func() (Result, error) { return Run(classfile, "multi", nil, verifyM5aGasLimit) }, 20375534)
	verifyM5aAssertException(t, func() (Result, error) { return Run(classfile, "ase", nil, verifyM5aGasLimit) }, "java.lang.ArrayStoreException", 9)
	for _, method := range []string{"castBZ", "castZI"} {
		verifyM5aAssertException(t, func() (Result, error) { return Run(classfile, method, nil, verifyM5aGasLimit) }, "java.lang.ClassCastException", 8)
	}
	for _, method := range []string{"multi"} {
		code := parseStaticsClass(t, classfile).namedMethod(t, method).code
		if verifyM5aInstructionPC(t, code, 0xc5, 0) < 0 {
			t.Fatalf("%s lacks multianewarray", method)
		}
	}
}

func TestVerifyM5aArrayDescriptorChecksAtCallsFieldsAndReturnsUseReference2(t *testing.T) {
	original := compileJava(t, "NarrowArrayDescriptors", `public final class NarrowArrayDescriptors {
		static byte[] field; static int accept(byte[] x){return x.length;} static byte[] give(){return new byte[1];}
		public static int argument(){return accept(new byte[1]);}
		public static int staticField(){field=new byte[1];return field.length;}
		public static int returned(){return give().length;}
	}`)
	for _, tc := range []struct {
		method   string
		boundary byte
		entry    string
	}{
		{"argument", 0xb8, "argument"}, {"staticField", 0xb3, "staticField"}, {"give", 0xb0, "returned"},
	} {
		t.Run(tc.method, func(t *testing.T) {
			bad := verifyM5aMutate(t, original, func(_ []byte, c staticsClass) {
				m := c.namedMethod(t, tc.method)
				pc := verifyM5aInstructionPC(t, m.code, verifyM5aNewarray, 0)
				if m.code[pc+1] != 8 {
					t.Fatalf("%s atype=%d want byte", tc.method, m.code[pc+1])
				}
				m.code[pc+1] = 4
			})
			pc := verifyM5aInstructionPC(t, parseStaticsClass(t, bad).namedMethod(t, tc.method).code, tc.boundary, 0)
			verifyM5aAssertError(t, func() (Result, error) { return Run(bad, tc.entry, nil, verifyM5aGasLimit) }, "ReferenceError(uint256,uint256)", 2, uint64(pc))
		})
	}
}

func TestVerifyM5aAtypesUnsupportedTargetsRank255AndExactBranchBoundaries(t *testing.T) {
	original := compileJava(t, "NarrowArrayShape", `public final class NarrowArrayShape {
		public static int run(){return new byte[1].length;}
		public static int typeLong(){Object x=new int[1];return x instanceof long[]?1:0;}
		public static int typeFloat(){Object x=new int[1];return x instanceof float[]?1:0;}
		public static int typeDouble(){Object x=new int[1];return x instanceof double[]?1:0;}
		public static int padding(){int x=0;`+strings.Repeat("x=x+1;", 420)+`return x;}
	}`)
	for _, atype := range []byte{0, 3, 12, 255} {
		t.Run(fmt.Sprintf("invalid-atype-%d", atype), func(t *testing.T) {
			bad := verifyM5aRewriteMethodPrefix(t, original, "padding", "()I", []byte{0x04, verifyM5aNewarray, atype, 0xbe, 0xac}, 2, 0)
			verifyM5aAssertError(t, func() (Result, error) { return Run(bad, "padding", nil, verifyM5aGasLimit) }, "ArrayError(uint256,uint256)", 1, 1)
		})
	}
	for _, atype := range []byte{6, 7} {
		t.Run(fmt.Sprintf("ieee-atype-%d", atype), func(t *testing.T) {
			classfile := verifyM5aRewriteMethodPrefix(t, original, "padding", "()I", []byte{0x04, verifyM5aNewarray, atype, 0xbe, 0xac}, 2, 0)
			verifyM5aAssertValue(t, func() (Result, error) { return Run(classfile, "padding", nil, verifyM5aGasLimit) }, 1)
		})
	}
	longArray := verifyM5aRewriteMethodPrefix(t, original, "padding", "()I", []byte{0x04, verifyM5aNewarray, 11, 0xbe, 0xac}, 2, 0)
	longOracle := compileJava(t, "M5aLongArrayOracle", `public final class M5aLongArrayOracle { public static int run(){return new long[1].length;} }`)
	oracleCode := parseStaticsClass(t, longOracle).namedMethod(t, "run").code
	oraclePC := verifyM5aInstructionPC(t, oracleCode, verifyM5aNewarray, 0)
	if oracleCode[oraclePC+1] != 11 {
		t.Fatalf("javac long[] atype=%d want 11", oracleCode[oraclePC+1])
	}
	verifyM5aJava8Outcome(t, [][]byte{longOracle}, "M5aLongArrayOracle", "run", nil, "value=1")
	verifyM5aAssertValue(t, func() (Result, error) { return Run(longArray, "padding", nil, verifyM5aGasLimit) }, 1)

	verifyM5aJava8Outcome(t, [][]byte{original}, "NarrowArrayShape", "typeLong", nil, "value=0")
	verifyM5aAssertValue(t, func() (Result, error) { return Run(original, "typeLong", nil, verifyM5aGasLimit) }, 0)
	for _, method := range []string{"typeFloat", "typeDouble"} {
		verifyM5aJava8Outcome(t, [][]byte{original}, "NarrowArrayShape", method, nil, "value=0")
		verifyM5aAssertValue(t, func() (Result, error) { return Run(original, method, nil, verifyM5aGasLimit) }, 0)
	}

	truncated := verifyM5aRewriteAtEnd(t, original, "padding", "()I", []byte{verifyM5aNewarray})
	truncatedPC := len(parseStaticsClass(t, truncated).namedMethod(t, "padding").code) - 1
	verifyM5aAssertError(t, func() (Result, error) { return Run(truncated, "padding", nil, verifyM5aGasLimit) }, "BytecodeError(uint256,uint256)", 2, uint64(truncatedPC))
	branch := []byte{0x03, 0x99, 0, 5, 0x04, verifyM5aNewarray, 8, 0x57, 0x03, 0xac}
	branchClass := verifyM5aRewriteMethodPrefix(t, original, "padding", "()I", branch, 2, 0)
	if pc := verifyM5aInstructionPC(t, branch, verifyM5aNewarray, 0); pc != 5 {
		t.Fatalf("newarray pc=%d want 5", pc)
	}
	verifyM5aAssertError(t, func() (Result, error) { return Run(branchClass, "padding", nil, verifyM5aGasLimit) }, "BytecodeError(uint256,uint256)", 12, 1)

	// anewarray rank 254 -> rank 255 is legal for a primitive byte leaf; rank
	// 255 -> 256 is not. Zero lengths keep both EVM and host memory bounded.
	for _, tc := range []struct {
		rank     int
		overflow bool
	}{{254, false}, {255, true}} {
		descriptor := strings.Repeat("[", tc.rank) + "B"
		classfile := verifyM5aRetargetAnewarray(t, original, "padding", descriptor)
		pc := verifyM5aInstructionPC(t, parseStaticsClass(t, classfile).namedMethod(t, "padding").code, 0xbd, 0)
		if tc.overflow {
			verifyM5aAssertError(t, func() (Result, error) { return Run(classfile, "padding", nil, verifyM5aGasLimit) }, "ArrayError(uint256,uint256)", 2, uint64(pc))
		} else {
			verifyM5aAssertValue(t, func() (Result, error) { return Run(classfile, "padding", nil, verifyM5aGasLimit) }, 1)
		}
	}
	multi := verifyM5aRetargetMultianewarray(t, original, "padding", strings.Repeat("[", 255)+"B")
	verifyM5aAssertValue(t, func() (Result, error) { return Run(multi, "padding", nil, verifyM5aGasLimit) }, 1)
}

func TestVerifyM5aSharedPrimitiveArrayCapsNoGCResetAndOOGRemainExact(t *testing.T) {
	classfile := compileJava(t, "NarrowArrayCaps", `public final class NarrowArrayCaps {
		public static int mixed(int n){Object x=null;for(int i=0;i<n;i++){int k=i%5;
			if(k==0)x=new boolean[0];else if(k==1)x=new byte[0];else if(k==2)x=new char[0];
			else if(k==3)x=new short[0];else x=new int[0];}return n+(x==null?0:0);}
	}`)
	verifyM5aAssertValue(t, func() (Result, error) { return Run(classfile, "mixed", []int32{1024}, verifyM5aCapacityGasLimit) }, 1024)
	verifyM5aAssertException(t, func() (Result, error) { return Run(classfile, "mixed", []int32{1025}, verifyM5aCapacityGasLimit) }, "java.lang.OutOfMemoryError", 7)
	verifyM5aAssertValue(t, func() (Result, error) { return Run(classfile, "mixed", []int32{1024}, verifyM5aCapacityGasLimit) }, 1024)
	result, err := Run(classfile, "mixed", []int32{1}, 1)
	if err == nil || !errors.Is(err, vm.ErrOutOfGas) || result.ExceptionClass != "" || len(result.RevertData) != 0 {
		t.Fatalf("result/error=%+v/%v, want unlabeled EVM out of gas", result, err)
	}
}

// --- M5a verifier-only helpers ---

func verifyM5aCompile(t *testing.T, sources map[string]string, internalNames ...string) map[string][]byte {
	t.Helper()
	dir := t.TempDir()
	rels := make([]string, 0, len(sources))
	for rel := range sources {
		rels = append(rels, rel)
	}
	sort.Strings(rels)
	args := []string{"-J-Xmx64m", "--release", "8", "-d", dir}
	for _, rel := range rels {
		path := filepath.Join(dir, filepath.FromSlash(rel))
		if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(sources[rel]), 0600); err != nil {
			t.Fatal(err)
		}
		args = append(args, path)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	if output, err := exec.CommandContext(ctx, "javac", args...).CombinedOutput(); err != nil {
		t.Fatalf("bounded trusted javac --release 8 failed: %v\n%s", err, output)
	}
	out := make(map[string][]byte, len(internalNames))
	for _, name := range internalNames {
		data, err := os.ReadFile(filepath.Join(dir, filepath.FromSlash(name+".class")))
		if err != nil {
			t.Fatalf("read %s: %v", name, err)
		}
		out[name] = data
	}
	return out
}

func verifyM5aBundle(classes map[string][]byte) [][]byte {
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

func verifyM5aJava8(t *testing.T) string {
	t.Helper()
	path := os.Getenv("JAVA_EVM_JAVA8")
	if path == "" {
		path = "/usr/lib/jvm/java-8-openjdk/bin/java"
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	output, err := exec.CommandContext(ctx, path, "-version").CombinedOutput()
	if err != nil {
		t.Fatalf("M5a exact classfile oracle requires Java 8; JAVA_EVM_JAVA8=%q: %v\n%s", path, err, output)
	}
	if !regexp.MustCompile(`(?m)version "1\.8\.`).Match(output) {
		t.Fatalf("M5a oracle requires Java major 8; JAVA_EVM_JAVA8=%q reported:\n%s", path, output)
	}
	return path
}

func verifyM5aJava8Outcome(t *testing.T, bundle [][]byte, mainClass, method string, args []int32, want string) {
	t.Helper()
	dir := t.TempDir()
	oracle := `public final class VerifyM5aOracle {
		public static void main(String[] a) throws Exception { try {
			Class<?> c=Class.forName(a[0]);Class<?>[] p=new Class<?>[a.length-2];Object[] v=new Object[a.length-2];
			for(int i=0;i<p.length;i++){p[i]=Integer.TYPE;v[i]=Integer.valueOf(a[i+2]);}
			Object x=c.getMethod(a[1],p).invoke(null,v);System.out.print("value="+x);
		} catch(java.lang.reflect.InvocationTargetException x){System.out.print(x.getCause().getClass().getName());}
		catch(Throwable x){System.out.print(x.getClass().getName());}}
	}`
	path := filepath.Join(dir, "VerifyM5aOracle.java")
	if err := os.WriteFile(path, []byte(oracle), 0600); err != nil {
		t.Fatal(err)
	}
	ctxCompile, cancelCompile := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancelCompile()
	if output, err := exec.CommandContext(ctxCompile, "javac", "-J-Xmx64m", "--release", "8", "-d", dir, path).CombinedOutput(); err != nil {
		t.Fatalf("compile trusted M5a oracle: %v\n%s", err, output)
	}
	for _, classfile := range bundle {
		name := verifyM5aClassName(t, classfile)
		classPath := filepath.Join(dir, filepath.FromSlash(name+".class"))
		if err := os.MkdirAll(filepath.Dir(classPath), 0700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(classPath, classfile, 0600); err != nil {
			t.Fatal(err)
		}
	}
	argv := []string{"-Xmx64m", "-cp", dir, "VerifyM5aOracle", mainClass, method}
	for _, arg := range args {
		argv = append(argv, strconv.FormatInt(int64(arg), 10))
	}
	ctxRun, cancelRun := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancelRun()
	output, err := exec.CommandContext(ctxRun, verifyM5aJava8(t), argv...).CombinedOutput()
	if err != nil {
		t.Fatalf("bounded Java8 M5a oracle failed: %v\n%s", err, output)
	}
	if got := strings.TrimSpace(string(output)); got != want {
		t.Fatalf("Java8 %s.%s outcome=%q want %q", mainClass, method, got, want)
	}
}

func verifyM5aClassName(t *testing.T, classfile []byte) string {
	t.Helper()
	c := parseStaticsClass(t, classfile)
	e := c.entry(t, c.thisClass)
	if e.tag != 7 {
		t.Fatalf("this_class tag=%d want Class", e.tag)
	}
	return c.utf8[c.u2(t, e.offset+1)]
}

func verifyM5aMutate(t *testing.T, original []byte, edit func([]byte, staticsClass)) []byte {
	t.Helper()
	out := append([]byte(nil), original...)
	edit(out, parseStaticsClass(t, out))
	return out
}

func verifyM5aReplaceInstructions(t *testing.T, original []byte, method string, from, to byte, want int) []byte {
	t.Helper()
	return verifyM5aMutate(t, original, func(_ []byte, c staticsClass) {
		m := c.namedMethod(t, method)
		count := 0
		for pc := 0; pc < len(m.code); pc += verifyM5aInstructionWidth(t, m.code, pc) {
			if m.code[pc] == from {
				m.code[pc] = to
				count++
			}
		}
		if want >= 0 && count != want {
			t.Fatalf("%s replaced %d boundary-aligned 0x%02x, want %d (code=%x)", method, count, from, want, m.code)
		}
		if want < 0 && count == 0 {
			t.Fatalf("%s has no boundary-aligned 0x%02x (code=%x)", method, from, m.code)
		}
	})
}

func verifyM5aMutateConstantValue(t *testing.T, original []byte, name, descriptor string, payload int32) []byte {
	t.Helper()
	return verifyM5aMutate(t, original, func(raw []byte, c staticsClass) {
		field := c.field(t, name, descriptor)
		attr := field.attribute(t, "ConstantValue")
		if attr == nil || attr.length != 2 {
			t.Fatalf("%s:%s lacks canonical ConstantValue", name, descriptor)
		}
		index := binary.BigEndian.Uint16(raw[attr.dataOffset:])
		e := c.entry(t, index)
		if e.tag != 3 {
			t.Fatalf("%s:%s ConstantValue tag=%d want Integer", name, descriptor, e.tag)
		}
		binary.BigEndian.PutUint32(raw[e.offset+1:], uint32(payload))
	})
}

func verifyM5aFieldPC(t *testing.T, c staticsClass, m staticsMethod, opcode byte, name, descriptor string) int {
	t.Helper()
	for pc := 0; pc < len(m.code); pc += verifyM5aInstructionWidth(t, m.code, pc) {
		if m.code[pc] != opcode || pc+2 >= len(m.code) {
			continue
		}
		ref := binary.BigEndian.Uint16(m.code[pc+1:])
		if ref == 0 || int(ref) >= len(c.entries) || c.entries[ref].tag != 9 {
			continue
		}
		e := c.entry(t, ref)
		nat := c.entry(t, c.u2(t, e.offset+3))
		if nat.tag == 12 && c.utf8[c.u2(t, nat.offset+1)] == name && c.utf8[c.u2(t, nat.offset+3)] == descriptor {
			return pc
		}
	}
	t.Fatalf("%s%s lacks field opcode 0x%02x %s:%s at an instruction boundary", m.name, m.descriptor, opcode, name, descriptor)
	return -1
}

func verifyM5aMemberPC(t *testing.T, c staticsClass, m staticsMethod, opcode, tag byte, name, descriptor string) int {
	t.Helper()
	for pc := 0; pc < len(m.code); pc += verifyM5aInstructionWidth(t, m.code, pc) {
		if m.code[pc] != opcode || pc+2 >= len(m.code) {
			continue
		}
		ref := binary.BigEndian.Uint16(m.code[pc+1:])
		if ref == 0 || int(ref) >= len(c.entries) || c.entries[ref].tag != tag {
			continue
		}
		e := c.entry(t, ref)
		nat := c.entry(t, c.u2(t, e.offset+3))
		if nat.tag == 12 && c.utf8[c.u2(t, nat.offset+1)] == name && c.utf8[c.u2(t, nat.offset+3)] == descriptor {
			return pc
		}
	}
	t.Fatalf("%s%s lacks call opcode 0x%02x %s%s", m.name, m.descriptor, opcode, name, descriptor)
	return -1
}

func verifyM5aPreviousInstruction(t *testing.T, code []byte, target int) int {
	t.Helper()
	previous := -1
	for pc := 0; pc < len(code); pc += verifyM5aInstructionWidth(t, code, pc) {
		if pc == target {
			if previous < 0 {
				t.Fatalf("instruction at pc %d has no predecessor", target)
			}
			return previous
		}
		if pc > target {
			break
		}
		previous = pc
	}
	t.Fatalf("pc %d is not an instruction boundary in %x", target, code)
	return -1
}

func verifyM5aInstructionPC(t *testing.T, code []byte, opcode byte, occurrence int) int {
	t.Helper()
	seen := 0
	for pc := 0; pc < len(code); pc += verifyM5aInstructionWidth(t, code, pc) {
		if code[pc] == opcode {
			if seen == occurrence {
				return pc
			}
			seen++
		}
	}
	t.Fatalf("opcode 0x%02x occurrence %d missing at instruction boundaries in %x", opcode, occurrence, code)
	return -1
}

func verifyM5aInstructionWidth(t *testing.T, code []byte, pc int) int {
	t.Helper()
	if pc < 0 || pc >= len(code) {
		t.Fatalf("invalid instruction pc %d", pc)
	}
	op := code[pc]
	width := 1
	switch op {
	case 0x10, 0x12, 0x15, 0x16, 0x17, 0x18, 0x19, 0x36, 0x37, 0x38, 0x39, 0x3a, 0xa9, verifyM5aNewarray:
		width = 2
	case 0x11, 0x13, 0x14, 0x84,
		0x99, 0x9a, 0x9b, 0x9c, 0x9d, 0x9e, 0x9f, 0xa0, 0xa1, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6, 0xa7, 0xa8,
		0xb2, 0xb3, 0xb4, 0xb5, 0xb6, 0xb7, 0xb8, 0xbb, 0xbd, 0xc0, 0xc1, 0xc6, 0xc7:
		width = 3
	case 0xb9, 0xba, 0xc8, 0xc9:
		width = 5
	case 0xc5:
		width = 4
	case 0xc4:
		if pc+1 >= len(code) {
			t.Fatalf("truncated wide at pc %d", pc)
		}
		if code[pc+1] == 0x84 {
			width = 6
		} else {
			width = 4
		}
	case 0xaa, 0xab:
		t.Fatalf("test boundary walker deliberately does not accept switch at pc %d", pc)
	}
	if pc+width > len(code) {
		t.Fatalf("truncated opcode 0x%02x at pc %d in %x", op, pc, code)
	}
	return width
}

func verifyM5aRewriteMethodPrefix(t *testing.T, original []byte, name, descriptor string, code []byte, maxStack, maxLocals uint16) []byte {
	t.Helper()
	out := append([]byte(nil), original...)
	m := parseStaticsClass(t, out).method(t, name, descriptor)
	if len(code) > len(m.code) {
		t.Fatalf("replacement %s%s has %d bytes, Code has %d", name, descriptor, len(code), len(m.code))
	}
	start := -1
	for i := range out {
		if len(m.code) > 0 && &out[i] == &m.code[0] {
			start = i
			break
		}
	}
	if start < 8 {
		t.Fatalf("cannot locate Code for %s%s", name, descriptor)
	}
	binary.BigEndian.PutUint16(out[start-8:], maxStack)
	binary.BigEndian.PutUint16(out[start-6:], maxLocals)
	for i := range m.code {
		m.code[i] = 0
	}
	copy(m.code, code)
	return out
}

func verifyM5aRewriteAtEnd(t *testing.T, original []byte, name, descriptor string, ending []byte) []byte {
	t.Helper()
	out := verifyM5aRewriteMethodPrefix(t, original, name, descriptor, nil, 16, 16)
	m := parseStaticsClass(t, out).method(t, name, descriptor)
	copy(m.code[len(m.code)-len(ending):], ending)
	return out
}

func verifyM5aAppendNameAndClass(t *testing.T, original []byte, name string) ([]byte, uint16) {
	t.Helper()
	c := parseStaticsClass(t, original)
	if c.cpCount+2 > 65535 || len(name) > 65535 {
		t.Fatal("test CP/name too large")
	}
	utf := make([]byte, 3+len(name))
	utf[0] = 1
	binary.BigEndian.PutUint16(utf[1:], uint16(len(name)))
	copy(utf[3:], name)
	class := []byte{7, byte(c.cpCount >> 8), byte(c.cpCount)}
	insert := append(utf, class...)
	out := make([]byte, len(original)+len(insert))
	copy(out, original[:c.cpEnd])
	copy(out[c.cpEnd:], insert)
	copy(out[c.cpEnd+len(insert):], original[c.cpEnd:])
	binary.BigEndian.PutUint16(out[8:10], uint16(c.cpCount+2))
	return out, uint16(c.cpCount + 1)
}

func verifyM5aRetargetAnewarray(t *testing.T, original []byte, method, descriptor string) []byte {
	t.Helper()
	out, index := verifyM5aAppendNameAndClass(t, original, descriptor)
	out = verifyM5aRewriteMethodPrefix(t, out, method, "()I", []byte{0x04, 0xbd, byte(index >> 8), byte(index), 0xbe, 0xac}, 2, 0)
	return out
}

func verifyM5aRetargetMultianewarray(t *testing.T, original []byte, method, descriptor string) []byte {
	t.Helper()
	out, index := verifyM5aAppendNameAndClass(t, original, descriptor)
	out = verifyM5aRewriteMethodPrefix(t, out, method, "()I", []byte{0x04, 0xc5, byte(index >> 8), byte(index), 1, 0xbe, 0xac}, 2, 0)
	return out
}

func verifyM5aAssertValue(t *testing.T, run func() (Result, error), want int32) {
	t.Helper()
	result, err := run()
	if err != nil || result.ExceptionClass != "" || result.Value != want || result.GasUsed == 0 || len(result.RevertData) != 0 {
		t.Fatalf("result/error=%+v/%v want value %d", result, err, want)
	}
}

func verifyM5aAssertException(t *testing.T, run func() (Result, error), want string, kind byte) {
	t.Helper()
	result, err := run()
	selector := crypto.Keccak256([]byte("JavaException(uint256)"))[:4]
	if err != nil || result.ExceptionClass != want || result.GasUsed == 0 || len(result.RevertData) != 36 ||
		!bytes.Equal(result.RevertData[:4], selector) || !bytes.Equal(result.RevertData[4:35], make([]byte, 31)) || result.RevertData[35] != kind {
		t.Fatalf("result/error=%+v/%v data=%x want %s kind %d", result, err, result.RevertData, want, kind)
	}
}

func verifyM5aAssertError(t *testing.T, run func() (Result, error), signature string, code, pc uint64) {
	t.Helper()
	result, err := run()
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error=%+v/%v want %s(%d,%d)", result, err, signature, code, pc)
	}
	selector := crypto.Keccak256([]byte(signature))[:4]
	if result.ExceptionClass != "" || result.GasUsed == 0 || len(result.RevertData) != 68 || !bytes.Equal(result.RevertData[:4], selector) {
		t.Fatalf("result=%+v data=%x want exact %s", result, result.RevertData, signature)
	}
	if got := verifyM5aUint256(t, result.RevertData[4:36]); got != code {
		t.Fatalf("%s code=%d want %d", signature, got, code)
	}
	if got := verifyM5aUint256(t, result.RevertData[36:]); got != pc {
		t.Fatalf("%s pc=%d want %d", signature, got, pc)
	}
}

func verifyM5aAssertMethodError(t *testing.T, run func() (Result, error), code uint64) {
	t.Helper()
	result, err := run()
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error=%+v/%v want MethodError(%d)", result, err, code)
	}
	selector := crypto.Keccak256([]byte("MethodError(uint256)"))[:4]
	if result.ExceptionClass != "" || result.GasUsed == 0 || len(result.RevertData) != 36 || !bytes.Equal(result.RevertData[:4], selector) || verifyM5aUint256(t, result.RevertData[4:]) != code {
		t.Fatalf("result=%+v data=%x want exact MethodError(%d)", result, result.RevertData, code)
	}
}

func verifyM5aUint256(t *testing.T, word []byte) uint64 {
	t.Helper()
	if len(word) != 32 || !bytes.Equal(word[:24], make([]byte, 24)) {
		t.Fatalf("noncanonical uint256 %x", word)
	}
	return binary.BigEndian.Uint64(word[24:])
}
