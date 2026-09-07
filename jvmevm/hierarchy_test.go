// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"encoding/binary"
	"testing"
)

const hierarchyGasLimit = 100_000_000

func TestHierarchyInheritedMembersStorageAndDeclaringInitialization(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"p/Base.java": `package p;
class Base {
    public static int value = 3;
    public static int get() { return value; }
    public static int add(int x) { return x + value; }
}`,
		"p/Child.java": `package p;
public class Child extends Base {
    static { value = 9; }
}`,
		"p/Sibling.java": `package p;
public class Sibling extends Base {
    public static int set(int x) { value = x; return value; }
}`,
		"p/Hiding.java": `package p;
public class Hiding extends Base {
    public static int value = 40;
    public static int add(int x, int y) { return value + x + y; }
}`,
		"q/Root.java": `package q;
public class Root {
    public static int inheritedOnly() { return p.Child.get(); }
    public static int shared(int x) { return p.Sibling.set(x) + p.Child.value + p.Child.add(1); }
    public static int hiddenAndOverloaded(int x) {
        return p.Hiding.value + p.Hiding.add(x) + p.Hiding.add(x, 1);
    }
}`,
	})
	bundle := [][]byte{
		classes["p/Child"], classes["q/Root"], classes["p/Base"], classes["p/Sibling"],
		classes["p/Hiding"],
	}

	// The Methodref names Child, but get is declared by Base. Active use must
	// initialize Base only; running Child.<clinit> would change this result to 9.
	got, err := RunClasses(bundle, "q/Root", "inheritedOnly", nil, hierarchyGasLimit)
	if err != nil || got.Value != 3 {
		t.Fatalf("inherited declaring-owner call = %+v/%v, want 3", got, err)
	}
	// Both subclasses resolve the one Base slot. add is inherited as well.
	got, err = RunClasses(bundle, "q/Root", "shared", []int32{7}, hierarchyGasLimit)
	if err != nil || got.Value != 22 { // 7 + 7 + (1+7)
		t.Fatalf("shared inherited storage = %+v/%v, want 22", got, err)
	}
	hidden, err := RunClasses(bundle, "q/Root", "hiddenAndOverloaded", []int32{2}, hierarchyGasLimit)
	if err != nil || hidden.Value != 88 { // 40 + inherited Base.add(2)=5 + Hiding.add(2,1)=43
		t.Fatalf("hidden slot/exact overload lookup = %+v/%v, want 88", hidden, err)
	}
	t.Logf("hierarchy declaring-owner gas: shared=%d hidden=%d", got.GasUsed, hidden.GasUsed)
}

func TestHierarchyInitializationOrderAndReentrantChildObservation(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"Parent.java": `class Parent {
    static int observed = Child.readConstantSlot();
}`,
		"Child.java": `public class Child extends Parent {
    static final int constant = 7;
    static int aaaaaaaa;
    static int value = 9;
    static int readConstantSlot() { return aaaaaaaa + value; }
    public static int run() { return observed * 100 + value; }
}`,
		"NoClinit.java": `public class NoClinit extends Parent {
    public static int run() { return observed; }
}`,
	})
	// javac inlines literal constants. Redirect only the read's valid Fieldref
	// NameAndType from the equal-shaped dummy field to the ConstantValue field,
	// forcing an EVM getstatic that observes step-6 preparation before Parent runs.
	child := append([]byte(nil), classes["Child"]...)
	parsed := parseCallTestClass(t, child)
	constantName := parsed.utfIndex("constant")
	var dummyNAT uint16
	for i := 1; i < len(parsed.tags); i++ {
		if parsed.tags[i] == 9 {
			nat := parsed.second[i]
			if parsed.tags[nat] == 12 && parsed.utf8[parsed.first[nat]] == "aaaaaaaa" {
				dummyNAT = nat
				break
			}
		}
	}
	if constantName == 0 || dummyNAT == 0 {
		t.Fatal("fixture lacks constant Utf8 or dummy Fieldref NameAndType")
	}
	binary.BigEndian.PutUint16(child[parsed.cpOffsets[dummyNAT]+1:], constantName)

	bundle := [][]byte{child, classes["Parent"], classes["NoClinit"]}
	got, err := RunClasses(bundle, "Child", "run", nil, hierarchyGasLimit)
	if err != nil || got.Value != 709 {
		t.Fatalf("parent-before-child/reentrant prepared state = %+v/%v, want 709", got, err)
	}
	got, err = RunClasses(bundle, "NoClinit", "run", nil, hierarchyGasLimit)
	if err != nil || got.Value != 16 {
		// NoClinit has no initializer, but Parent still runs. In this independent
		// invocation Parent's active call initializes Child, so the same method sees
		// the prepared constant plus Child's now-initialized ordinary value.
		t.Fatalf("no-clinit child superclass initialization = %+v/%v, want 16", got, err)
	}
}

func TestHierarchyThreeLevelInitializerContinuations(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"Grand.java":  `class Grand { static int order = 1; }`,
		"Middle.java": `class Middle extends Grand { static { order = order * 10 + 2; } }`,
		"Leaf.java": `public class Leaf extends Middle {
    static { order = order * 10 + 3; }
    public static int run(int x) { return x + order; }
}`,
	})
	got, err := RunClasses(
		[][]byte{classes["Middle"], classes["Leaf"], classes["Grand"]},
		"Leaf", "run", []int32{7}, hierarchyGasLimit,
	)
	if err != nil || got.Value != 130 {
		t.Fatalf("three-level initialization continuations = %+v/%v, want 130", got, err)
	}
}

func TestHierarchyParentInitializerFailureStopsChild(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"FailingParent.java": `class FailingParent {
    static int value = divide(0);
    static int divide(int x) { return 1 / x; }
}`,
		"FailingChild.java": `public class FailingChild extends FailingParent {
    static int child = 9;
    public static int run() { return child; }
}`,
	})
	got, err := RunClasses(
		[][]byte{classes["FailingChild"], classes["FailingParent"]},
		"FailingChild", "run", nil, hierarchyGasLimit,
	)
	if err != nil || got.ExceptionClass != "java.lang.ExceptionInInitializerError" {
		t.Fatalf("parent initializer arithmetic failure = %+v/%v, want EIIE", got, err)
	}
}

func TestHierarchyStaticProtectedAndHiddenDeclaringClassAccess(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"p/Hidden.java": `package p;
class Hidden {
    public static int exposed = 5;
    public static int exposed(int x) { return x + exposed; }
    protected static int protectedValue = 11;
}`,
		"p/PublicChild.java": `package p; public class PublicChild extends Hidden {}`,
		"q/Sub.java": `package q;
public class Sub extends p.PublicChild {
    public static int run(int x) { return protectedValue + exposed(x) + p.PublicChild.exposed; }
}`,
	})
	got, err := RunClasses(
		[][]byte{classes["q/Sub"], classes["p/Hidden"], classes["p/PublicChild"]},
		"q/Sub", "run", []int32{2}, hierarchyGasLimit,
	)
	if err != nil || got.Value != 23 { // 11 + (2+5) + 5
		t.Fatalf("protected/public-through-hidden-parent access = %+v/%v, want 23", got, err)
	}
}

func TestHierarchyAccessAndFirstDeclarationFailures(t *testing.T) {
	t.Run("protected-unrelated", func(t *testing.T) {
		classes := compileJavaSources(t, map[string]string{
			"p/Base.java":  `package p; public class Base { public static int secret(int x) { return x + 1; } }`,
			"p/Child.java": `package p; public class Child extends Base {}`,
			"q/Root.java":  `package q; public class Root { public static int run(int x) { return p.Child.secret(x); } }`,
		})
		base := append([]byte(nil), classes["p/Base"]...)
		parsed := parseCallTestClass(t, base)
		off := parsed.methodAccess["secret"]
		flags := binary.BigEndian.Uint16(base[off:])
		binary.BigEndian.PutUint16(base[off:], (flags&^0x0001)|0x0004)
		rootParsed := parseCallTestClass(t, classes["q/Root"])
		pc := bytesIndexOpcode(rootParsed.code(t, "run"), 0xb8)
		assertBundleError(t, [][]byte{classes["q/Root"], classes["p/Child"], base},
			"q/Root", "run", []int32{1}, "CallError(uint256,uint256)", 4, uint64(pc))
	})

	t.Run("nonstatic-child-hides-static-parent", func(t *testing.T) {
		classes := compileJavaSources(t, map[string]string{
			"Base.java":  `public class Base { public static int go(int x) { return x + 1; } }`,
			"Child.java": `public class Child extends Base { public static int go(int x) { return x + 2; } }`,
			"Root.java":  `public class Root { public static int run(int x) { return Child.go(x); } }`,
		})
		child := append([]byte(nil), classes["Child"]...)
		parsed := parseCallTestClass(t, child)
		off := parsed.methodAccess["go"]
		binary.BigEndian.PutUint16(child[off:], binary.BigEndian.Uint16(child[off:])&^0x0008)
		rootParsed := parseCallTestClass(t, classes["Root"])
		pc := bytesIndexOpcode(rootParsed.code(t, "run"), 0xb8)
		assertBundleError(t, [][]byte{classes["Base"], child, classes["Root"]},
			"Root", "run", []int32{1}, "CallError(uint256,uint256)", 4, uint64(pc))
	})
}

func bytesIndexOpcode(code []byte, opcode byte) int {
	for i, b := range code {
		if b == opcode {
			return i
		}
	}
	return -1
}

func TestHierarchyFrozenGraphErrors(t *testing.T) {
	t.Run("unused-missing-parent-is-lazy", func(t *testing.T) {
		classes := compileJavaSources(t, map[string]string{
			"Base.java":   `class Base {}`,
			"Unused.java": `public class Unused extends Base { public static int run() { return 2; } }`,
			"Root.java":   `public class Root { public static int run() { return 1; } }`,
		})
		bundle := [][]byte{classes["Unused"], classes["Root"]} // Base intentionally unsupplied
		got, err := RunClasses(bundle, "Root", "run", nil, hierarchyGasLimit)
		if err != nil || got.Value != 1 {
			t.Fatalf("unused missing-parent class was linked eagerly: %+v/%v", got, err)
		}
		assertBundleError(t, bundle, "Unused", "run", nil,
			"HierarchyError(uint256,uint256)", 1, 0)
	})

	t.Run("extends-final", func(t *testing.T) {
		classes := compileJavaSources(t, map[string]string{
			"Base.java":  `public class Base {}`,
			"Child.java": `public class Child extends Base { public static int run() { return 1; } }`,
		})
		base := append([]byte(nil), classes["Base"]...)
		off := bundleClassAccessOffset(t, base)
		binary.BigEndian.PutUint16(base[off:], binary.BigEndian.Uint16(base[off:])|0x0010)
		assertBundleError(t, [][]byte{base, classes["Child"]}, "Child", "run", nil,
			"HierarchyError(uint256,uint256)", 3, 1)
	})

	t.Run("interface-parent", func(t *testing.T) {
		classes := compileJavaSources(t, map[string]string{
			"Base.java":  `public class Base {}`,
			"Child.java": `public class Child extends Base { public static int run() { return 1; } }`,
		})
		base := append([]byte(nil), classes["Base"]...)
		off := bundleClassAccessOffset(t, base)
		binary.BigEndian.PutUint16(base[off:], binary.BigEndian.Uint16(base[off:])|0x0200)
		assertBundleError(t, [][]byte{classes["Child"], base}, "Child", "run", nil,
			"HierarchyError(uint256,uint256)", 4, 0)
	})

	t.Run("inaccessible-parent", func(t *testing.T) {
		classes := compileJavaSources(t, map[string]string{
			"p/Base.java":  `package p; public class Base {}`,
			"p/Child.java": `package p; public class Child extends Base { public static int run() { return 1; } }`,
		})
		base := append([]byte(nil), classes["p/Base"]...)
		baseOff := bundleClassAccessOffset(t, base)
		binary.BigEndian.PutUint16(base[baseOff:], binary.BigEndian.Uint16(base[baseOff:])&^0x0001)
		child := append([]byte(nil), classes["p/Child"]...)
		parsed := parseCallTestClass(t, child)
		name := parsed.utfIndex("p/Child")
		copy(child[parsed.cpOffsets[name]+3:], []byte("q/Child")) // equal-length internal name
		assertBundleError(t, [][]byte{base, child}, "q/Child", "run", nil,
			"HierarchyError(uint256,uint256)", 5, 1)
	})

	t.Run("cycle-first-repeated", func(t *testing.T) {
		classes := compileJavaSources(t, map[string]string{
			"A.java": `public class A extends B { public static int run() { return 1; } }`,
			"B.java": `class B { static int mention() { return A.run(); } }`,
		})
		b := append([]byte(nil), classes["B"]...)
		parsed := parseCallTestClass(t, b)
		aClass := hierarchyClassIndex(t, parsed, "A")
		off := bundleClassAccessOffset(t, b)
		binary.BigEndian.PutUint16(b[off+4:], aClass)
		assertBundleError(t, [][]byte{classes["A"], b}, "A", "run", nil,
			"HierarchyError(uint256,uint256)", 2, 0)
	})
}

func hierarchyClassIndex(t *testing.T, c callTestClass, name string) uint16 {
	t.Helper()
	for i := 1; i < len(c.tags); i++ {
		if c.tags[i] == 7 && c.utf8[c.first[i]] == name {
			return uint16(i)
		}
	}
	t.Fatalf("class constant %q not found", name)
	return 0
}
