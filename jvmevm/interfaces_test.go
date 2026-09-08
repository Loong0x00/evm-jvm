// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"encoding/binary"
	"testing"
)

const runtimeM4faGasLimit = 180_000_000

func runtimeM4faBundle(classes map[string][]byte, names ...string) [][]byte {
	out := make([][]byte, len(names))
	for i, name := range names {
		out[i] = classes[name]
	}
	return out
}

func TestRuntimeM4faAbstractInterfaceDAGAndVirtualFallback(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"m4fa/I.java":     `package m4fa; public interface I { int f(); }`,
		"m4fa/J.java":     `package m4fa; public interface J extends I { }`,
		"m4fa/K.java":     `package m4fa; public interface K extends I { }`,
		"m4fa/D.java":     `package m4fa; public interface D extends J, K { }`,
		"m4fa/Base.java":  `package m4fa; public class Base { public int f(){ return 7; } }`,
		"m4fa/Child.java": `package m4fa; public class Child extends Base implements D { public Child(){} }`,
		"m4fa/A.java":     `package m4fa; public abstract class A implements I { public A(){} }`,
		"m4fa/B.java":     `package m4fa; public final class B extends A { public B(){} public int f(){ return 11; } }`,
		"m4fa/Root.java": `package m4fa; public final class Root {
            static int throughInterface(I x){ return x.f(); }
            static int throughAbstract(A x){ return x.f(); }
            public static int run(){ return throughInterface(new Child()) * 10 + throughAbstract(new B()); }
        }`,
	})
	bundle := runtimeM4faBundle(classes, "m4fa/D", "m4fa/K", "m4fa/Root", "m4fa/Base", "m4fa/I", "m4fa/B", "m4fa/J", "m4fa/A", "m4fa/Child")
	got, err := RunClasses(bundle, "m4fa/Root", "run", nil, runtimeM4faGasLimit)
	if err != nil || got.ExceptionClass != "" || got.Value != 81 {
		t.Fatalf("interface DAG / abstract invokevirtual result = %+v/%v, want 81", got, err)
	}
}

func TestRuntimeM4faInterfaceArraysAndBootstrapMarkers(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"m4array/I.java": `package m4array; public interface I { int f(); }`,
		"m4array/C.java": `package m4array; public final class C implements I { public C(){} public int f(){return 3;} }`,
		"m4array/Root.java": `package m4array; public final class Root {
            public static int run(){
                I[] values = new C[1]; values[0] = new C();
                Object ints = new int[1]; int[][] matrix = new int[1][1];
                Object[] ordinary = new Object[1];
                int score = values[0].f();
                if (ints instanceof Cloneable) score += 10;
                if (ints instanceof java.io.Serializable) score += 20;
                if (matrix instanceof Cloneable[]) score += 40;
                if (!(ordinary instanceof Cloneable[])) score += 80;
                I[][] empty = new I[0][0];
                return score + empty.length;
            }
        }`,
	})
	got, err := RunClasses(runtimeM4faBundle(classes, "m4array/Root", "m4array/I", "m4array/C"), "m4array/Root", "run", nil, runtimeM4faGasLimit)
	if err != nil || got.ExceptionClass != "" || got.Value != 153 {
		t.Fatalf("interface/marker array result = %+v/%v, want 153", got, err)
	}
}

func TestRuntimeM4faAbstractInterfacesDoNotInitialize(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"m4init/Helper.java": `package m4init; public final class Helper { static int touched; public static int mark(){touched=9;return 9;} }`,
		"m4init/I.java":      `package m4init; public interface I { int X = Helper.mark(); int f(); }`,
		"m4init/Root.java":   `package m4init; public final class Root implements I { public int f(){return 1;} public static int run(){return Helper.touched;} }`,
	})
	got, err := RunClasses(runtimeM4faBundle(classes, "m4init/I", "m4init/Root", "m4init/Helper"), "m4init/Root", "run", nil, runtimeM4faGasLimit)
	if err != nil || got.ExceptionClass != "" || got.Value != 0 {
		t.Fatalf("abstract interface initialization result = %+v/%v, want 0", got, err)
	}
}

func TestRuntimeM4fbReachableDefaultAllowsClassInitialization(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"m4default/I.java":    `package m4default; public interface I { default int f(){return 1;} }`,
		"m4default/Root.java": `package m4default; public final class Root implements I { static int x=7; public static int run(){return x;} }`,
	})
	result, err := RunClasses(runtimeM4faBundle(classes, "m4default/Root", "m4default/I"), "m4default/Root", "run", nil, runtimeM4faGasLimit)
	if err != nil || result.ExceptionClass != "" || result.Value != 7 {
		t.Fatalf("default-bearing class initialization result = %+v/%v, want 7", result, err)
	}
}

func TestRuntimeM4faGraphDuplicateMissingKindAndCycle(t *testing.T) {
	duplicateClasses := compileJavaSources(t, map[string]string{
		"m4graph/I.java":    `package m4graph; public interface I { }`,
		"m4graph/J.java":    `package m4graph; public interface J { }`,
		"m4graph/Root.java": `package m4graph; public final class Root implements I,J { public static int run(){return 1;} }`,
	})
	duplicate := append([]byte(nil), duplicateClasses["m4graph/Root"]...)
	parsed := parseStaticsClass(t, duplicate)
	interfacesAt := parsed.cpEnd + 6
	if binary.BigEndian.Uint16(duplicate[interfacesAt:]) != 2 {
		t.Fatal("duplicate fixture does not have two direct interfaces")
	}
	copy(duplicate[interfacesAt+4:interfacesAt+6], duplicate[interfacesAt+2:interfacesAt+4])
	result, err := RunClasses([][]byte{duplicate, duplicateClasses["m4graph/I"], duplicateClasses["m4graph/J"]}, "m4graph/Root", "run", nil, runtimeM4faGasLimit)
	assertSolidityError(t, result, err, "InterfaceError(uint256,uint256)", 1, 0)

	result, err = RunClasses([][]byte{duplicateClasses["m4graph/Root"], duplicateClasses["m4graph/J"]}, "m4graph/Root", "run", nil, runtimeM4faGasLimit)
	assertSolidityError(t, result, err, "LinkError(uint256,uint256)", 4, 0)

	wrongKind := append([]byte(nil), duplicateClasses["m4graph/I"]...)
	wrongParsed := parseStaticsClass(t, wrongKind)
	flags := binary.BigEndian.Uint16(wrongKind[wrongParsed.cpEnd:])
	binary.BigEndian.PutUint16(wrongKind[wrongParsed.cpEnd:], flags&^uint16(0x0200|0x0400))
	result, err = RunClasses([][]byte{duplicateClasses["m4graph/Root"], wrongKind, duplicateClasses["m4graph/J"]}, "m4graph/Root", "run", nil, runtimeM4faGasLimit)
	assertSolidityError(t, result, err, "InterfaceError(uint256,uint256)", 1, 0)

	cycleClasses := compileJavaSources(t, map[string]string{
		"m4cycle/I.java":    `package m4cycle; public interface I extends J { }`,
		"m4cycle/J.java":    `package m4cycle; public interface J extends K { }`,
		"m4cycle/K.java":    `package m4cycle; public interface K extends L { }`,
		"m4cycle/L.java":    `package m4cycle; public interface L { }`,
		"m4cycle/Root.java": `package m4cycle; public final class Root implements I { public static int run(){return 1;} }`,
	})
	cycleK := append([]byte(nil), cycleClasses["m4cycle/K"]...)
	if at := bytes.Index(cycleK, []byte("m4cycle/L")); at < 0 {
		t.Fatal("cycle fixture lacks parent name")
	} else {
		copy(cycleK[at:], []byte("m4cycle/I"))
	}
	result, err = RunClasses([][]byte{cycleClasses["m4cycle/Root"], cycleClasses["m4cycle/I"], cycleClasses["m4cycle/J"], cycleK}, "m4cycle/Root", "run", nil, runtimeM4faGasLimit)
	assertSolidityError(t, result, err, "InterfaceError(uint256,uint256)", 2, 1)
}

func TestRuntimeM4faInvokeinterfaceCountAndTrailingByte(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"m4operand/I.java":    `package m4operand; public interface I { int f(int x); }`,
		"m4operand/C.java":    `package m4operand; public final class C implements I { public C(){} public int f(int x){return x+1;} }`,
		"m4operand/Root.java": `package m4operand; public final class Root { public static int run(){I x=new C();return x.f(4);} }`,
	})
	for name, delta := range map[string]int{"count": 3, "trailing": 4} {
		t.Run(name, func(t *testing.T) {
			root := append([]byte(nil), classes["m4operand/Root"]...)
			method := parseStaticsClass(t, root).method(t, "run", "()I")
			pc := bytes.IndexByte(method.code, 0xb9)
			if pc < 0 {
				t.Fatal("fixture lacks invokeinterface")
			}
			method.code[pc+delta]++
			result, err := RunClasses([][]byte{root, classes["m4operand/I"], classes["m4operand/C"]}, "m4operand/Root", "run", nil, runtimeM4faGasLimit)
			assertSolidityError(t, result, err, "CallError(uint256,uint256)", 1, uint64(pc))
		})
	}
}
