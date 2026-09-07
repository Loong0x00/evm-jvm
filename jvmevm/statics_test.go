// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"encoding/binary"
	"strings"
	"testing"
)

func TestM3cSingleClassStaticsInitializationDupOnceAndFreshRun(t *testing.T) {
	classfile := compileJava(t, "State", `
public class State {
    static int zero;
    static int value;
    static int initialized;
    static { initialized++; value = 40; }
    static int next() { return value++; }
    public static int run(int x) { return zero + initialized * 100 + next() + next() + x; }
}`)
	parsed := parseCallTestClass(t, classfile)
	if !bytes.Contains(parsed.code(t, "next"), []byte{0x59}) {
		t.Fatalf("next bytecode = %x, want genuine dup", parsed.code(t, "next"))
	}
	for invocation := 0; invocation < 2; invocation++ {
		result, err := Run(classfile, "run", []int32{1}, 15_000_000)
		if err != nil || result.Value != 182 || result.ExceptionClass != "" {
			t.Fatalf("invocation %d = %+v/%v, want fresh value 182", invocation, result, err)
		}
		t.Logf("single invocation %d gas=%d", invocation, result.GasUsed)
	}
}

func TestM3cCrossClassInitializationOrderCyclesAndOperandPreservation(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"Root.java": `public class Root {
    public static int put(int v) { return 1000 + (Target.value = v) + Target.inits * 10; }
    public static int call(int v) { return 2000 + Target.add(v); }
    public static int cycleA() { return A.a * 10 + B.b; }
    public static int cycleB() { return B.b * 10 + A.a; }
}`,
		"Target.java": `public class Target {
    static int value = 7; static int inits; static { inits++; }
    static int add(int v) { return value + v + inits * 100; }
}`,
		"A.java": `public class A { static int a = B.b + 1; }`,
		"B.java": `public class B { static int b = A.a + 2; }`,
	})
	bundle := [][]byte{classes["B"], classes["Target"], classes["Root"], classes["A"]}
	for _, tc := range []struct {
		method string
		arg    []int32
		want   int32
	}{
		{"put", []int32{9}, 1019},  // prefix and putstatic value survive Target.<clinit>
		{"call", []int32{5}, 2112}, // argument and prefix survive target initialization
		{"cycleA", nil, 32},        // A.a=3, B.b=2
		{"cycleB", nil, 31},        // B.b=3, A.a=1
	} {
		result, err := RunClasses(bundle, "Root", tc.method, tc.arg, 50_000_000)
		if err != nil || result.Value != tc.want {
			t.Fatalf("%s = %+v/%v, want %d", tc.method, result, err, tc.want)
		}
		t.Logf("%s gas=%d", tc.method, result.GasUsed)
	}
}

func TestM3cInitializationIsLazyAndTypedOutcomesAreExact(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"Root.java": `public class Root {
    public static int plain() { return 9; }
    public static int enter() { return Broken.value; }
    public static int overflow() { return Overflow.value; }
}`,
		"Broken.java": `public class Broken {
    static int value; static { helper(); }
    static void helper() { value = 1 / value; }
}`,
		"Overflow.java": `public class Overflow {
    static int value; static { recurse(); }
    static void recurse() { recurse(); }
}`,
	})
	bundle := [][]byte{classes["Broken"], classes["Root"], classes["Overflow"]}
	plain, err := RunClasses(bundle, "Root", "plain", nil, 50_000_000)
	if err != nil || plain.Value != 9 {
		t.Fatalf("unused initializer affected result: %+v/%v", plain, err)
	}
	broken, err := RunClasses(bundle, "Root", "enter", nil, 50_000_000)
	if err != nil || broken.ExceptionClass != "java.lang.ExceptionInInitializerError" {
		t.Fatalf("nested initializer arithmetic = %+v/%v, want EIIE", broken, err)
	}
	overflow, err := RunClasses(bundle, "Root", "overflow", nil, 100_000_000)
	if err != nil || overflow.ExceptionClass != "java.lang.StackOverflowError" {
		t.Fatalf("initializer recursion = %+v/%v, want StackOverflowError", overflow, err)
	}
	outside := compileJava(t, "Outside", `public class Outside { public static int run(int x) { return 1 / x; } }`)
	arithmetic, err := Run(outside, "run", []int32{0}, 10_000_000)
	if err != nil || arithmetic.ExceptionClass != "java.lang.ArithmeticException" {
		t.Fatalf("outside arithmetic = %+v/%v", arithmetic, err)
	}
}

func TestM3cInitializerOutOfGasRemainsEVMFailure(t *testing.T) {
	classfile := compileJava(t, "InitOOG", `public class InitOOG {
    static int value; static { for (int i = 0; i < 1000; i++) value += i; }
    public static int run() { return value; }
}`)
	result, err := Run(classfile, "run", nil, 200_000)
	if err == nil || !strings.Contains(err.Error(), "out of gas") || result.ExceptionClass != "" {
		t.Fatalf("initializer OOG = %+v/%v, want unwrapped EVM out of gas", result, err)
	}
}

func TestM3cConstantValueNonFinalAndActualFinalInitializerWrite(t *testing.T) {
	classfile := compileJava(t, "Constants", `
public class Constants {
    static final int constant = 17;
    static int ordinary;
    static final int assigned;
    static { assigned = 9; }
    public static int readOrdinary() { return ordinary; }
    public static int readAssigned() { return assigned; }
}`)
	mutated := append([]byte(nil), classfile...)
	parsed := parseCallTestClass(t, mutated)
	code := parsed.code(t, "readOrdinary")
	if len(code) < 3 || code[0] != 0xb2 {
		t.Fatalf("readOrdinary bytecode = %x, want getstatic", code)
	}
	ref := binary.BigEndian.Uint16(code[1:3])
	nat := parsed.second[ref]
	binary.BigEndian.PutUint16(mutated[parsed.cpOffsets[nat]+1:], parsed.utfIndex("constant"))
	constantAccess := staticsFieldAccessOffset(t, mutated, "constant")
	flags := binary.BigEndian.Uint16(mutated[constantAccess:])
	binary.BigEndian.PutUint16(mutated[constantAccess:], flags&^uint16(0x0010))
	result, err := Run(mutated, "readOrdinary", nil, 15_000_000)
	if err != nil || result.Value != 17 {
		t.Fatalf("raw getstatic of non-final ConstantValue = %+v/%v, want 17", result, err)
	}
	assigned, err := Run(classfile, "readAssigned", nil, 15_000_000)
	if err != nil || assigned.Value != 9 {
		t.Fatalf("actual declaring <clinit> final write = %+v/%v, want 9", assigned, err)
	}
}

func TestM3cFinalWriteChecksActualInitializerFrameAfterCachedRead(t *testing.T) {
	classfile := compileJava(t, "FinalRules", `
public class FinalRules {
    static int value;
    static { int ignored = value; helper(); }
    static void helper() { value = 7; }
    public static int run() { return value; }
}`)
	mutated := append([]byte(nil), classfile...)
	fieldAccess := staticsFieldAccessOffset(t, mutated, "value")
	flags := binary.BigEndian.Uint16(mutated[fieldAccess:])
	binary.BigEndian.PutUint16(mutated[fieldAccess:], flags|0x0010)
	result, err := Run(mutated, "run", nil, 20_000_000)
	assertSolidityError(t, result, err, "FieldError(uint256,uint256)", 4, uint64(bytes.IndexByte(parseCallTestClass(t, mutated).code(t, "helper"), 0xb3)))
}

func TestM3cFrozenFieldErrorsAndInstanceConstantValueIgnored(t *testing.T) {
	base := compileJava(t, "FieldFailures", `
public class FieldFailures {
    static int value;
    public static int run() { return value; }
}`)
	baseParsed := parseCallTestClass(t, base)
	code := baseParsed.code(t, "run")
	pc := bytes.IndexByte(code, 0xb2)
	ref := binary.BigEndian.Uint16(code[pc+1 : pc+3])

	t.Run("bad-fieldref", func(t *testing.T) {
		bad := append([]byte(nil), base...)
		bad[baseParsed.cpOffsets[ref]] = 10
		result, err := Run(bad, "run", nil, 15_000_000)
		assertSolidityError(t, result, err, "FieldError(uint256,uint256)", 1, uint64(pc))
	})
	t.Run("missing-declaration", func(t *testing.T) {
		bad := append([]byte(nil), base...)
		nat := baseParsed.second[ref]
		binary.BigEndian.PutUint16(bad[baseParsed.cpOffsets[nat]+1:], baseParsed.utfIndex("run"))
		result, err := Run(bad, "run", nil, 15_000_000)
		assertSolidityError(t, result, err, "FieldError(uint256,uint256)", 2, uint64(pc))
	})
	t.Run("nonstatic", func(t *testing.T) {
		bad := append([]byte(nil), base...)
		off := staticsFieldAccessOffset(t, bad, "value")
		binary.BigEndian.PutUint16(bad[off:], binary.BigEndian.Uint16(bad[off:])&^uint16(0x0008))
		result, err := Run(bad, "run", nil, 15_000_000)
		assertSolidityError(t, result, err, "FieldError(uint256,uint256)", 3, uint64(pc))
	})
	t.Run("unsupported-descriptor", func(t *testing.T) {
		bad := append([]byte(nil), base...)
		i := baseParsed.utfIndex("I")
		bad[baseParsed.cpOffsets[i]+3] = 'J'
		result, err := Run(bad, "run", nil, 15_000_000)
		assertSolidityError(t, result, err, "FieldError(uint256,uint256)", 3, uint64(pc))
	})

	cross := compileJavaSources(t, map[string]string{
		"a/Root.java":  `package a; public class Root { public static int run() { return b.Owner.value; } }`,
		"b/Owner.java": `package b; public class Owner { public static int value = 3; }`,
	})
	owner := append([]byte(nil), cross["b/Owner"]...)
	off := staticsFieldAccessOffset(t, owner, "value")
	binary.BigEndian.PutUint16(owner[off:], (binary.BigEndian.Uint16(owner[off:])&^uint16(0x0001))|0x0002)
	rootPC := bytes.IndexByte(parseCallTestClass(t, cross["a/Root"]).code(t, "run"), 0xb2)
	result, err := RunClasses([][]byte{owner, cross["a/Root"]}, "a/Root", "run", nil, 30_000_000)
	assertSolidityError(t, result, err, "FieldError(uint256,uint256)", 4, uint64(rootPC))

	constant := compileJava(t, "BadConstant", `public class BadConstant {
    static final int constant = 7; public static int run() { return 3; }
}`)
	field := staticsFieldMetadata(t, constant, "constant")
	badConstant := append([]byte(nil), constant...)
	binary.BigEndian.PutUint16(badConstant[field.constantPayload:], 0)
	result, err = Run(badConstant, "run", nil, 15_000_000)
	assertSolidityError(t, result, err, "FieldError(uint256,uint256)", 5, uint64(field.index))

	ignored := append([]byte(nil), badConstant...)
	flags := binary.BigEndian.Uint16(ignored[field.accessOffset:])
	binary.BigEndian.PutUint16(ignored[field.accessOffset:], flags&^uint16(0x0008))
	ok, err := Run(ignored, "run", nil, 15_000_000)
	if err != nil || ok.Value != 3 {
		t.Fatalf("instance ConstantValue was not ignored: %+v/%v", ok, err)
	}
}

func TestM3cInitErrorAndDirectInitInvocationError(t *testing.T) {
	invalid := compileJava(t, "InvalidInitializer", `public class InvalidInitializer {
    static int value = 3; public static int run() { return value; }
}`)
	badFlags := append([]byte(nil), invalid...)
	parsed := parseCallTestClass(t, badFlags)
	off := parsed.methodAccess["<clinit>"]
	binary.BigEndian.PutUint16(badFlags[off:], binary.BigEndian.Uint16(badFlags[off:])|0x0020)
	result, err := Run(badFlags, "run", nil, 15_000_000)
	assertSolidityError(t, result, err, "InitError(uint256,uint256)", 1, 0)

	direct := compileJava(t, "DirectInit", `public class DirectInit {
    static int helper() { return 4; }
    public static int run() { return helper(); }
}`)
	mutated := append([]byte(nil), direct...)
	p := parseCallTestClass(t, mutated)
	helperUTF := p.utfIndex("helper")
	copy(mutated[p.cpOffsets[helperUTF]+3:], []byte("<init>"))
	callPC := bytes.IndexByte(p.code(t, "run"), 0xb8)
	result, err = Run(mutated, "run", nil, 15_000_000)
	assertSolidityError(t, result, err, "CallError(uint256,uint256)", 4, uint64(callPC))
}

type staticsFieldMeta struct {
	index           int
	accessOffset    int
	constantPayload int
}

func staticsFieldMetadata(t *testing.T, data []byte, wanted string) staticsFieldMeta {
	t.Helper()
	parsed := parseCallTestClass(t, data)
	p := &testClassParser{t: t, data: data}
	if p.u4() != 0xcafebabe {
		t.Fatal("bad class magic")
	}
	p.skip(4)
	cpCount := int(p.u2())
	for i := 1; i < cpCount; i++ {
		switch p.u1() {
		case 1:
			p.skip(int(p.u2()))
		case 3, 4:
			p.skip(4)
		case 5, 6:
			p.skip(8)
			i++
		case 7, 8, 16, 19, 20:
			p.skip(2)
		case 9, 10, 11, 12, 17, 18:
			p.skip(4)
		case 15:
			p.skip(3)
		default:
			t.Fatal("bad constant pool")
		}
	}
	p.skip(6)
	p.skip(2 * int(p.u2()))
	fields := int(p.u2())
	for i := 0; i < fields; i++ {
		meta := staticsFieldMeta{index: i, accessOffset: p.pos, constantPayload: -1}
		p.skip(2)
		name := parsed.utf8[p.u2()]
		p.skip(2)
		attrs := int(p.u2())
		for a := 0; a < attrs; a++ {
			attributeName := parsed.utf8[p.u2()]
			n := int(p.u4())
			if attributeName == "ConstantValue" {
				meta.constantPayload = p.pos
			}
			p.skip(n)
		}
		if name == wanted {
			return meta
		}
	}
	t.Fatalf("field %q not found", wanted)
	return staticsFieldMeta{}
}

func staticsFieldAccessOffset(t *testing.T, data []byte, wanted string) int {
	t.Helper()
	parsed := parseCallTestClass(t, data)
	p := &testClassParser{t: t, data: data}
	if p.u4() != 0xcafebabe {
		t.Fatal("bad class magic")
	}
	p.skip(4)
	cpCount := int(p.u2())
	for i := 1; i < cpCount; i++ {
		switch p.u1() {
		case 1:
			p.skip(int(p.u2()))
		case 3, 4:
			p.skip(4)
		case 5, 6:
			p.skip(8)
			i++
		case 7, 8, 16, 19, 20:
			p.skip(2)
		case 9, 10, 11, 12, 17, 18:
			p.skip(4)
		case 15:
			p.skip(3)
		default:
			t.Fatal("bad constant pool")
		}
	}
	p.skip(6)
	p.skip(2 * int(p.u2()))
	fields := int(p.u2())
	for i := 0; i < fields; i++ {
		off := p.pos
		p.skip(2)
		name := parsed.utf8[p.u2()]
		p.skip(2)
		attrs := int(p.u2())
		for a := 0; a < attrs; a++ {
			p.skip(2)
			p.skip(int(p.u4()))
		}
		if name == wanted {
			return off
		}
	}
	t.Fatalf("field %q not found", wanted)
	return 0
}
