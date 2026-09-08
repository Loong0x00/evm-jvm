// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.

package jvmevm

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"testing"
)

const runtimeM5aGasLimit = uint64(260_000_000)

func runtimeM5aRunValue(t *testing.T, classfile []byte, method string, args []int32, want int32) {
	t.Helper()
	result, err := Run(classfile, method, args, runtimeM5aGasLimit)
	if err != nil || result.ExceptionClass != "" || result.Value != want {
		t.Fatalf("%s%v = %+v/%v, want %d", method, args, result, err, want)
	}
}

func runtimeM5aReplaceUTF8(t *testing.T, classfile []byte, from, to string) []byte {
	t.Helper()
	if len(from) != len(to) {
		t.Fatalf("UTF8 replacement length %d != %d", len(from), len(to))
	}
	out := append([]byte(nil), classfile...)
	parsed := parseStaticsClass(t, out)
	matches := 0
	for index := 1; index < parsed.cpCount; index++ {
		cpIndex := uint16(index)
		if parsed.utf8[cpIndex] == from {
			copy(out[parsed.entries[cpIndex].offset+3:], to)
			matches++
		}
	}
	if matches != 1 {
		t.Fatalf("UTF8 %q matches=%d, want exactly one", from, matches)
	}
	return out
}

func runtimeM5aConstantClass(t *testing.T, name, primitive, literal string, payload int32) []byte {
	t.Helper()
	returnExpression := "x"
	if primitive == "boolean" {
		returnExpression = "x ? 1 : 0"
	}
	source := fmt.Sprintf(`public class %s {
    static final %s K = %s;
    static %s x;
    public static int run() { return %s; }
}`, name, primitive, literal, primitive, returnExpression)
	out := compileJava(t, name, source)
	parsed := parseCallTestClass(t, out)
	code := parsed.code(t, "run")
	pc := bytes.IndexByte(code, 0xb2)
	if pc < 0 {
		t.Fatalf("run bytecode %x has no getstatic", code)
	}
	ref := binary.BigEndian.Uint16(code[pc+1:])
	nat := parsed.second[ref]
	binary.BigEndian.PutUint16(out[parsed.cpOffsets[nat]+1:], parsed.utfIndex("K"))
	meta := staticsFieldMetadata(t, out, "K")
	if meta.constantPayload < 0 {
		t.Fatal("K has no ConstantValue")
	}
	constantIndex := binary.BigEndian.Uint16(out[meta.constantPayload:])
	if parsed.tags[constantIndex] != 3 {
		t.Fatalf("ConstantValue tag=%d, want Integer", parsed.tags[constantIndex])
	}
	binary.BigEndian.PutUint32(out[parsed.cpOffsets[constantIndex]+1:], uint32(payload))
	return out
}

func TestRuntimeM5aRootRemainsExactlyIntDescriptor(t *testing.T) {
	classfile := compileJava(t, "NarrowRoots", `public class NarrowRoots {
    public static boolean z(boolean x) { return x; }
    public static byte b(byte x) { return x; }
    public static char c(char x) { return x; }
    public static short s(short x) { return x; }
    public static boolean rz(int x) { return x != 0; }
    public static byte rb(int x) { return (byte)x; }
    public static char rc(int x) { return (char)x; }
    public static short rs(int x) { return (short)x; }
}`)
	for _, tc := range []struct {
		method string
		args   []int32
	}{{"z", []int32{1}}, {"b", []int32{1}}, {"c", []int32{1}}, {"s", []int32{1}},
		{"rz", []int32{1}}, {"rb", []int32{1}}, {"rc", []int32{1}}, {"rs", []int32{1}}} {
		t.Run(tc.method, func(t *testing.T) {
			result, err := Run(classfile, tc.method, tc.args, runtimeM5aGasLimit)
			assertHeaderProfileMethodError(t, result, err, 11)
		})
	}
}

func TestRuntimeM5aArgumentsStayComputationalIntAndReturnsNarrow(t *testing.T) {
	for _, tc := range []struct {
		name, descriptor string
		value, want      int32
	}{
		{"byte", "(B)I", 255, 7},
		{"boolean", "(Z)I", 2, 7},
	} {
		t.Run("argument-"+tc.name, func(t *testing.T) {
			source := fmt.Sprintf(`public class RawArgument {
    static int check(int x) { return x == 255 || x == 2 ? 7 : 9; }
    public static int run() { return check(%d); }
}`, tc.value)
			base := compileJava(t, "RawArgument", source)
			mutated := runtimeM5aReplaceUTF8(t, base, "(I)I", tc.descriptor)
			runtimeM5aRunValue(t, mutated, "run", nil, tc.want)
		})
	}
	for _, tc := range []struct {
		name, descriptor string
		value, want      int32
	}{
		{"int", "(I)I", 65535, 65535},
		{"byte", "(I)B", 255, -1},
		{"char", "(I)C", -1, 65535},
		{"short", "(I)S", 65535, -1},
		{"boolean-even", "(I)Z", 2, 0},
		{"boolean-odd", "(I)Z", 255, 1},
	} {
		t.Run("return-"+tc.name, func(t *testing.T) {
			source := fmt.Sprintf(`public class RawReturn {
    static int identity(int x) { return x; }
    public static int run() { return identity(%d); }
}`, tc.value)
			base := compileJava(t, "RawReturn", source)
			mutated := base
			if tc.descriptor != "(I)I" {
				mutated = runtimeM5aReplaceUTF8(t, base, "(I)I", tc.descriptor)
			}
			runtimeM5aRunValue(t, mutated, "run", nil, tc.want)
		})
	}
}

func TestRuntimeM5aJava8RawClassArgumentAndReturnOracle(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"rawm5a/Probe.java": `package rawm5a; public class Probe {
    static int helper(int b, int z) { return b == 255 && z == 2 ? 255 : 3; }
    public static int run() { return helper(255, 2); }
}`,
		"rawm5a/Main.java": `package rawm5a; public class Main {
    public static void main(String[] args) { System.out.print(Probe.run()); }
}`,
	})
	classes["rawm5a/Probe"] = runtimeM5aReplaceUTF8(
		t, classes["rawm5a/Probe"], "(II)I", "(BZ)B",
	)
	// Java 8 sees both raw computational-int arguments (255 and 2), then applies
	// the declared byte return narrowing. This is a bounded trusted oracle run.
	runtimeM4fbJava8Value(t, classes, "rawm5a.Main", "-1")
	result, err := RunClasses(
		[][]byte{classes["rawm5a/Probe"]}, "rawm5a/Probe", "run", nil, runtimeM5aGasLimit,
	)
	if err != nil || result.ExceptionClass != "" || result.Value != -1 {
		t.Fatalf("raw Java 8 parity = %+v/%v, want -1", result, err)
	}
}

func TestRuntimeM5aSelectedReturnSubtypeSurvivesEveryDispatch(t *testing.T) {
	t.Run("virtual", func(t *testing.T) {
		classes := compileJavaSources(t, map[string]string{
			"retv/Box.java":  `package retv; public class Box { public int id(int x){return x;} }`,
			"retv/Root.java": `package retv; public class Root { public static int run(){return new Box().id(255);} }`,
		})
		classes["retv/Box"] = runtimeM5aReplaceUTF8(t, classes["retv/Box"], "(I)I", "(I)B")
		classes["retv/Root"] = runtimeM5aReplaceUTF8(t, classes["retv/Root"], "(I)I", "(I)B")
		result, err := RunClasses(runtimeM4dBundle(classes), "retv/Root", "run", nil, runtimeM5aGasLimit)
		if err != nil || result.Value != -1 {
			t.Fatalf("virtual return = %+v/%v, want -1", result, err)
		}
	})
	t.Run("interface-implementation", func(t *testing.T) {
		classes := compileJavaSources(t, map[string]string{
			"reti/N.java":    `package reti; public interface N { int id(int x); }`,
			"reti/Box.java":  `package reti; public class Box implements N { public int id(int x){return x;} }`,
			"reti/Root.java": `package reti; public class Root { public static int run(){N n=new Box();return n.id(65535);} }`,
		})
		for _, name := range []string{"reti/N", "reti/Box", "reti/Root"} {
			classes[name] = runtimeM5aReplaceUTF8(t, classes[name], "(I)I", "(I)S")
		}
		result, err := RunClasses(runtimeM4dBundle(classes), "reti/Root", "run", nil, runtimeM5aGasLimit)
		if err != nil || result.Value != -1 {
			t.Fatalf("interface return = %+v/%v, want -1", result, err)
		}
	})
	t.Run("default", func(t *testing.T) {
		classes := compileJavaSources(t, map[string]string{
			"retd/N.java":    `package retd; public interface N { default int id(int x){return x;} }`,
			"retd/Box.java":  `package retd; public class Box implements N { }`,
			"retd/Root.java": `package retd; public class Root { public static int run(){N n=new Box();return n.id(65535);} }`,
		})
		for _, name := range []string{"retd/N", "retd/Root"} {
			classes[name] = runtimeM5aReplaceUTF8(t, classes[name], "(I)I", "(I)S")
		}
		result, err := RunClasses(runtimeM4dBundle(classes), "retd/Root", "run", nil, runtimeM5aGasLimit)
		if err != nil || result.Value != -1 {
			t.Fatalf("default return = %+v/%v, want -1", result, err)
		}
	})
	t.Run("special-and-constructor-argument", func(t *testing.T) {
		classfile := compileJava(t, "SpecialNarrow", `public class SpecialNarrow {
    int seen; SpecialNarrow(int x){seen=x;}
    private int id(int x){return x;}
    public static int run(){SpecialNarrow x=new SpecialNarrow(255);return x.seen+x.id(255);}
}`)
		classfile = runtimeM5aReplaceUTF8(t, classfile, "(I)V", "(B)V")
		classfile = runtimeM5aReplaceUTF8(t, classfile, "(I)I", "(I)B")
		runtimeM5aRunValue(t, classfile, "run", nil, 254)
	})
	t.Run("interface-static", func(t *testing.T) {
		classes := compileJavaSources(t, map[string]string{
			"rets/N.java":    `package rets; public interface N { static int id(int x){return x;} }`,
			"rets/Root.java": `package rets; public class Root { public static int run(){return N.id(-1);} }`,
		})
		for _, name := range []string{"rets/N", "rets/Root"} {
			classes[name] = runtimeM5aReplaceUTF8(t, classes[name], "(I)I", "(I)C")
		}
		result, err := RunClasses(runtimeM4dBundle(classes), "rets/Root", "run", nil, runtimeM5aGasLimit)
		if err != nil || result.Value != 65535 {
			t.Fatalf("interface static return = %+v/%v, want 65535", result, err)
		}
	})
}

func TestRuntimeM5aFieldStoresAndConstantValuesNormalizeByDeclaration(t *testing.T) {
	for _, tc := range []struct {
		name        string
		desc        byte
		value, want int32
	}{
		{"byte", 'B', 255, -1}, {"char", 'C', -1, 65535},
		{"short", 'S', 65535, -1}, {"boolean-even", 'Z', 2, 0},
		{"boolean-odd", 'Z', 255, 1},
	} {
		t.Run("static-"+tc.name, func(t *testing.T) {
			base := compileJava(t, "RawStaticField", `public class RawStaticField {
    static int value; public static int run(int x) { value=x; return value; }
}`)
			mutated := runtimeM5aReplaceUTF8(t, base, "I", string(tc.desc))
			runtimeM5aRunValue(t, mutated, "run", []int32{tc.value}, tc.want)
		})
		t.Run("instance-"+tc.name, func(t *testing.T) {
			base := compileJava(t, "RawInstanceField", `public class RawInstanceField {
    int value; RawInstanceField() {} public static int run(int x) {
        RawInstanceField box=new RawInstanceField(); box.value=x; return box.value;
    }
}`)
			mutated := runtimeM5aReplaceUTF8(t, base, "I", string(tc.desc))
			runtimeM5aRunValue(t, mutated, "run", []int32{tc.value}, tc.want)
		})
	}

	for _, payload := range []int32{2, 255, -1, 65535} {
		for _, tc := range []struct {
			primitive, literal string
			want               int32
		}{
			{"boolean", "false", payload & 1},
			{"byte", "(byte)0", int32(int8(payload))},
			{"char", "(char)0", int32(uint16(payload))},
			{"short", "(short)0", int32(int16(payload))},
		} {
			name := fmt.Sprintf("CV_%s_%d", tc.primitive, uint32(payload))
			t.Run(name, func(t *testing.T) {
				classfile := runtimeM5aConstantClass(t, name, tc.primitive, tc.literal, payload)
				runtimeM5aRunValue(t, classfile, "run", nil, tc.want)
			})
		}
	}
}

func TestRuntimeM5aAllInvocationKindsAndNarrowFields(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"m5a/N.java": `package m5a; public interface N {
    default byte d(byte x) { return x; }
    static char c(char x) { return x; }
}`,
		"m5a/Box.java": `package m5a; public class Box implements N {
    byte field; Box(byte x) { field=x; }
    short virtual(short x) { return x; }
    boolean flag(boolean x) { return x; }
}`,
		"m5a/Root.java": `package m5a; public class Root {
    static byte direct(byte x) { return x; }
    public static int run() {
        Box b=new Box((byte)255); N n=b;
        return b.field + b.virtual((short)65535) + n.d((byte)128)
            + N.c((char)-1) + (b.flag(true)?1:0) + direct((byte)2);
    }
}`,
	})
	result, err := RunClasses(runtimeM4dBundle(classes), "m5a/Root", "run", nil, runtimeM5aGasLimit)
	if err != nil || result.ExceptionClass != "" || result.Value != 65408 {
		t.Fatalf("all invocation kinds = %+v/%v, want 65408", result, err)
	}
}

func TestRuntimeM5aPrimitiveArrayOpcodesAndNormalization(t *testing.T) {
	base := compileJava(t, "RawPrimitiveArray", `public class RawPrimitiveArray {
    public static int run(int x) { int[] a=new int[1]; a[0]=x; return a[0]; }
}`)
	for _, tc := range []struct {
		name        string
		atype       byte
		load, store byte
		value, want int32
	}{
		{"int", 10, 0x2e, 0x4f, -1, -1},
		{"byte", 8, 0x33, 0x54, 255, -1},
		{"boolean-even", 4, 0x33, 0x54, 2, 0},
		{"boolean-odd", 4, 0x33, 0x54, 255, 1},
		{"char", 5, 0x34, 0x55, -1, 65535},
		{"short", 9, 0x35, 0x56, 65535, -1},
	} {
		t.Run(tc.name, func(t *testing.T) {
			out := append([]byte(nil), base...)
			parsed := parseTestClass(t, out)
			code := parsed.methodCode(t, "run")
			newPC := bytes.IndexByte(code, 0xbc)
			storePC := bytes.IndexByte(code, 0x4f)
			loadPC := bytes.IndexByte(code, 0x2e)
			if newPC < 0 || storePC < 0 || loadPC < 0 {
				t.Fatalf("unexpected run bytecode %x", code)
			}
			off := parsed.codeOffsets["run"]
			out[off+newPC+1] = tc.atype
			out[off+storePC] = tc.store
			out[off+loadPC] = tc.load
			runtimeM5aRunValue(t, out, "run", []int32{tc.value}, tc.want)
		})
	}
}

func TestRuntimeM5aPrimitiveArrayIdentityNestedCastsAndStores(t *testing.T) {
	classfile := compileJava(t, "PrimitiveArrayTypes", `public class PrimitiveArrayTypes {
    static byte[][] saved;
    static byte[][] pass(byte[][] x) { return x; }
    public static int valid() {
        byte[][] b=new byte[1][2]; b[0][1]=(byte)255; saved=pass(b); Object[] o=b;
        Object leaf=o[0]; boolean[] z=new boolean[1]; char[] c=new char[1]; short[] s=new short[1];
        return saved[0][1] + (b instanceof Object[]?2:0) + (leaf instanceof byte[]?4:0)
            + (z instanceof Object?8:0) + (c instanceof Cloneable?16:0)
            + (s instanceof java.io.Serializable?32:0);
    }
    public static int badStore() { Object[] o=new byte[1][]; o[0]=new boolean[1]; return 0; }
    public static int badCast() { Object x=new boolean[1]; return ((byte[])x).length; }
    public static int badObjectArrayCast() { Object x=new byte[1]; return ((Object[])x).length; }
    public static int distinct() {
        Object b=new byte[0], z=new boolean[0], i=new int[0];
        Object bb=new byte[0][], ii=new int[0][];
        return (b instanceof boolean[]?1:0)+(z instanceof byte[]?2:0)+(b instanceof int[]?4:0)
            +(i instanceof byte[]?8:0)+(bb instanceof int[][]?16:0)+(ii instanceof byte[][]?32:0);
    }
}`)
	runtimeM5aRunValue(t, classfile, "valid", nil, 61)
	runtimeM5aRunValue(t, classfile, "distinct", nil, 0)
	for method, want := range map[string]string{
		"badStore":           "java.lang.ArrayStoreException",
		"badCast":            "java.lang.ClassCastException",
		"badObjectArrayCast": "java.lang.ClassCastException",
	} {
		result, err := Run(classfile, method, nil, runtimeM5aGasLimit)
		if err != nil || result.ExceptionClass != want {
			t.Fatalf("%s = %+v/%v, want %s", method, result, err, want)
		}
	}
}

func TestRuntimeM5aWrongPrimitiveArrayOpcodeRankAndKinds(t *testing.T) {
	base := compileJava(t, "WrongPrimitiveArray", `public class WrongPrimitiveArray {
    public static int run(int x) { int[] a=new int[1]; a[0]=x; return a[0]; }
}`)
	parsed := parseTestClass(t, base)
	loadPC := bytes.IndexByte(parsed.methodCode(t, "run"), 0x2e)
	wrong := append([]byte(nil), base...)
	wrong[parsed.codeOffsets["run"]+loadPC] = 0x33
	result, err := Run(wrong, "run", []int32{1}, runtimeM5aGasLimit)
	runtimeM4dWantSolidityError(t, result, err, "ReferenceError(uint256,uint256)", 1, uint64(loadPC))

	rank := compileJava(t, "WrongPrimitiveRank", `public class WrongPrimitiveRank {
    public static int run(int x) { byte[][] a=new byte[1][]; return a[0]==null?1:0; }
}`)
	rankParsed := parseTestClass(t, rank)
	aaPC := bytes.IndexByte(rankParsed.methodCode(t, "run"), 0x32)
	if aaPC < 0 {
		t.Fatalf("unexpected rank bytecode %x", rankParsed.methodCode(t, "run"))
	}
	wrongRank := append([]byte(nil), rank...)
	wrongRank[rankParsed.codeOffsets["run"]+aaPC] = 0x33
	result, err = Run(wrongRank, "run", []int32{0}, runtimeM5aGasLimit)
	runtimeM4dWantSolidityError(t, result, err, "ReferenceError(uint256,uint256)", 1, uint64(aaPC))

	wrongKind := runtimeM4aReplaceMethodCode(t, base, "run", []byte{0x03, 0x03, 0x33, 0xac})
	result, err = Run(wrongKind, "run", []int32{0}, runtimeM5aGasLimit)
	runtimeM4dWantSolidityError(t, result, err, "BytecodeError(uint256,uint256)", 14, 2)

	refValue := runtimeM4aReplaceMethodCode(
		t, base, "run", []byte{0x04, 0xbc, 8, 0x03, 0x01, 0x54, 0x03, 0xac},
	)
	result, err = Run(refValue, "run", []int32{0}, runtimeM5aGasLimit)
	runtimeM4dWantSolidityError(t, result, err, "BytecodeError(uint256,uint256)", 14, 5)

	classIndex := runtimeM4dClassIndex(t, base, "WrongPrimitiveArray")
	uninitialized := runtimeM4aReplaceMethodCode(t, base, "run", []byte{
		0x04, 0xbc, 8, 0xbb, byte(classIndex >> 8), byte(classIndex), 0x33, 0xac,
	})
	result, err = Run(uninitialized, "run", []int32{0}, runtimeM5aGasLimit)
	runtimeM4dWantSolidityError(t, result, err, "BytecodeError(uint256,uint256)", 14, 6)

	badAtype := append([]byte(nil), base...)
	newPC := bytes.IndexByte(parsed.methodCode(t, "run"), 0xbc)
	storePC := bytes.IndexByte(parsed.methodCode(t, "run"), 0x4f)
	badAtype[parsed.codeOffsets["run"]+newPC+1] = 11
	result, err = Run(badAtype, "run", []int32{0}, runtimeM5aGasLimit)
	// Allocation succeeds, but iastore must not reinterpret a long[] cell.
	runtimeM4dWantSolidityError(t, result, err, "ReferenceError(uint256,uint256)", 1, uint64(storePC))
}
