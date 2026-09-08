// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"encoding/binary"
	"sort"
	"strings"
	"testing"
)

const runtimeM4fcGasLimit = uint64(260_000_000)

func runtimeM4fcBundle(classes map[string][]byte) [][]byte {
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

func runtimeM4fcAssertValue(t *testing.T, classes map[string][]byte, root, method string, args []int32, want int32) {
	t.Helper()
	result, err := RunClasses(runtimeM4fcBundle(classes), root, method, args, runtimeM4fcGasLimit)
	if err != nil || result.ExceptionClass != "" || result.Value != want || result.GasUsed == 0 || len(result.RevertData) != 0 {
		t.Fatalf("%s.%s = %+v/%v, want %d", root, method, result, err, want)
	}
}

func runtimeM4fcAssertException(t *testing.T, classes map[string][]byte, root, method, want string) {
	t.Helper()
	result, err := RunClasses(runtimeM4fcBundle(classes), root, method, nil, runtimeM4fcGasLimit)
	if err != nil || result.ExceptionClass != want || result.GasUsed == 0 || len(result.RevertData) != 36 {
		t.Fatalf("%s.%s = %+v/%v, want %s", root, method, result, err, want)
	}
}

func runtimeM4fcAssertSolidityError(t *testing.T, classes map[string][]byte, root, method, signature string, code, pc uint64) {
	t.Helper()
	result, err := RunClasses(runtimeM4fcBundle(classes), root, method, nil, runtimeM4fcGasLimit)
	assertSolidityError(t, result, err, signature, code, pc)
}

func runtimeM4fcAssertJava8(t *testing.T, classes map[string][]byte, mainClass, want string, wantError bool) {
	t.Helper()
	output, err := runtimeM4fbRunJava8(t, classes, mainClass)
	if wantError {
		if err == nil || !strings.Contains(string(output), want) {
			t.Fatalf("Java 8 %s = %q/%v, want error containing %q", mainClass, output, err, want)
		}
		return
	}
	if err != nil || strings.TrimSpace(string(output)) != want {
		t.Fatalf("Java 8 %s = %q/%v, want %q", mainClass, output, err, want)
	}
}

func TestRuntimeM4fcInterfaceStaticCallsRootsAndReferenceShapes(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"staticapi/Box.java": `package staticapi; public final class Box { int value; Box(int x){value=x;} }`,
		"staticapi/API.java": `package staticapi; public interface API {
			int SEED=seed(); static int seed(){return 7;} static int add(int a,int b){return a+b+SEED;}
			static Box pass(Box b){return b;} static int[] passArray(int[] a){return a;}
			static void put(Box b,int x){b.value=x;} static int root(int x){return add(x,1);}
		}`,
		"staticapi/Impl.java": `package staticapi; public final class Impl implements API { }`,
		"staticapi/Root.java": `package staticapi; public final class Root {
			public static int run(){Box b=new Box(1);API.put(API.pass(b),9);int[] a=API.passArray(new int[3]);
				return API.add(2,3)*100+b.value*10+a.length;}
			public static void main(String[] x){System.out.print(run());}
		}`,
	})
	api := parseStaticsClass(t, classes["staticapi/API"])
	root := parseStaticsClass(t, classes["staticapi/Root"])
	verifyM4faMemberInstruction(t, api, api.method(t, "root", "(I)I"), 0xb8, 11, "add", "(II)I")
	verifyM4faMemberInstruction(t, root, root.namedMethod(t, "run"), 0xb8, 11, "pass", "(Lstaticapi/Box;)Lstaticapi/Box;")
	runtimeM4fcAssertValue(t, classes, "staticapi/Root", "run", nil, 1293)
	runtimeM4fcAssertValue(t, classes, "staticapi/API", "root", []int32{4}, 12)
	runtimeM4fcAssertJava8(t, classes, "staticapi.Root", "1293", false)

	legacy, err := Run(classes["staticapi/API"], "root", []int32{4}, runtimeM4fcGasLimit)
	if err != nil || legacy.ExceptionClass != "" || legacy.Value != 12 || legacy.GasUsed == 0 {
		t.Fatalf("legacy interface root = %+v/%v, want 12", legacy, err)
	}
}

func TestRuntimeM4fcActiveInterfaceInitializesOnlyItself(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"owninit/Tracker.java":        `package owninit; public final class Tracker { static int n; static int mark(int x){n=n*10+x;return x;} }`,
		"owninit/DefaultParent.java":  `package owninit; public interface DefaultParent { int X=Tracker.mark(1); default int f(){return 1;} }`,
		"owninit/AbstractParent.java": `package owninit; public interface AbstractParent { int X=Tracker.mark(2); int g(); }`,
		"owninit/Child.java": `package owninit; public interface Child extends DefaultParent,AbstractParent {
			int X=Tracker.mark(3); static int value(){return X;} default int g(){return 2;}
		}`,
		"owninit/Root.java": `package owninit; public final class Root { public static int run(){return Child.value()*10+Tracker.n;} }`,
	})
	// Active use of Child runs Child.<clinit>, but neither its ordinary parent nor
	// its default-declaring parent is an initialization prerequisite.
	runtimeM4fcAssertValue(t, classes, "owninit/Root", "run", nil, 33)
}

func TestRuntimeM4fcInterfaceFieldResolutionStorageAndFinalReferenceMutation(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"ifacefield/Tracker.java": `package ifacefield; public final class Tracker {
			static int n; static int mark(int x){n=n*10+x;return x;} static Box box(){mark(2);return new Box();}
		}`,
		"ifacefield/Box.java": `package ifacefield; public final class Box { int value; }`,
		"ifacefield/Parent.java": `package ifacefield; public interface Parent {
			int X=Tracker.mark(1); int[] A=new int[2]; Box B=Tracker.box();
		}`,
		"ifacefield/Child.java": `package ifacefield; public interface Child extends Parent { }`,
		"ifacefield/Impl.java":  `package ifacefield; public final class Impl implements Child { static int UNUSED=Tracker.mark(9); }`,
		"ifacefield/Root.java": `package ifacefield; public final class Root {
			public static int run(){Child.A[0]=4;Impl.B.value=5;return Impl.X*10000+Child.X*1000+Parent.X*100
				+Parent.A[0]*10+Child.B.value+Tracker.n;}
		}`,
	})
	root := parseStaticsClass(t, classes["ifacefield/Root"])
	for _, qualifier := range []string{"ifacefield/Impl", "ifacefield/Child", "ifacefield/Parent"} {
		found := false
		for _, entry := range root.entries {
			if entry.tag != 9 {
				continue
			}
			ownerEntry := root.entry(t, root.u2(t, entry.offset+1))
			if root.utf8[root.u2(t, ownerEntry.offset+1)] == qualifier {
				found = true
			}
		}
		if !found {
			t.Fatalf("javac emitted no Fieldref with symbolic qualifier %s", qualifier)
		}
	}
	// Parent owns every slot. Its initializer runs once and Impl remains untouched.
	runtimeM4fcAssertValue(t, classes, "ifacefield/Root", "run", nil, 11157)
}

func TestRuntimeM4fcFieldResolutionInterfacesBeforeSuperclassAndHiddenDeclaringOwner(t *testing.T) {
	old := compileJavaSources(t, map[string]string{
		"precedence/Tracker.java": `package precedence; public final class Tracker { static int n; static int mark(int x){n=n*10+x;return x;} }`,
		"precedence/I.java":       `package precedence; public interface I { }`,
		"precedence/Super.java":   `package precedence; public class Super { public static int X=Tracker.mark(9); }`,
		"precedence/C.java":       `package precedence; public final class C extends Super implements I { }`,
		"precedence/Root.java":    `package precedence; public final class Root { public static int run(){return C.X*10+Tracker.n;} public static void main(String[] x){System.out.print(run());} }`,
	})
	newInterface := compileJavaSources(t, map[string]string{
		"precedence/Tracker.java": `package precedence; public final class Tracker { static int n; static int mark(int x){n=n*10+x;return x;} }`,
		"precedence/I.java":       `package precedence; public interface I { int X=Tracker.mark(1); }`,
	})
	old["precedence/I"] = newInterface["precedence/I"]
	// Root's existing Fieldref names C. Binary evolution adds I.X; JVMS field
	// resolution finds C's direct interface before C's superclass.
	runtimeM4fcAssertValue(t, old, "precedence/Root", "run", nil, 11)
	runtimeM4fcAssertJava8(t, old, "precedence.Root", "11", false)

	hidden := compileJavaSources(t, map[string]string{
		"hidden/Tracker.java": `package hidden; public final class Tracker { public static int n; public static int mark(int x){n=n*10+x;return x;} }`,
		"hidden/Hidden.java":  `package hidden; class Hidden { public static int X=Tracker.mark(4); }`,
		"hidden/Public.java":  `package hidden; public final class Public extends Hidden { static int UNUSED=Tracker.mark(8); }`,
		"outside/Root.java":   `package outside; public final class Root { public static int run(){return hidden.Public.X*10+hidden.Tracker.n;} }`,
	})
	// Access is checked against the public symbolic qualifier and public member;
	// the actual package-private declaring class is not an extra access barrier.
	runtimeM4fcAssertValue(t, hidden, "outside/Root", "run", nil, 44)
}

func TestRuntimeM4fcStaticMethodsAreNotInherited(t *testing.T) {
	old := compileJavaSources(t, map[string]string{
		"noninherit/P.java":    `package noninherit; public interface P { static int f(){return 1;} }`,
		"noninherit/C.java":    `package noninherit; public interface C extends P { static int f(){return 2;} }`,
		"noninherit/Root.java": `package noninherit; public final class Root { public static int run(){return C.f();} public static void main(String[] x){System.out.print(run());} }`,
	})
	newChild := compileJavaSources(t, map[string]string{
		"noninherit/P.java": `package noninherit; public interface P { static int f(){return 1;} }`,
		"noninherit/C.java": `package noninherit; public interface C extends P { }`,
	})
	old["noninherit/C"] = newChild["noninherit/C"]
	root := parseStaticsClass(t, old["noninherit/Root"])
	_, pc := verifyM4faMemberInstruction(t, root, root.namedMethod(t, "run"), 0xb8, 11, "f", "()I")
	runtimeM4fcAssertSolidityError(t, old, "noninherit/Root", "run", "CallError(uint256,uint256)", 3, uint64(pc))
	runtimeM4fcAssertJava8(t, old, "noninherit.Root", "java.lang.NoSuchMethodError", true)

	classOld := compileJavaSources(t, map[string]string{
		"classnoninherit/I.java":    `package classnoninherit; public interface I { static int f(){return 3;} }`,
		"classnoninherit/C.java":    `package classnoninherit; public final class C implements I { public static int f(){return 4;} }`,
		"classnoninherit/Root.java": `package classnoninherit; public final class Root { public static int run(){return C.f();} public static void main(String[] x){System.out.print(run());} }`,
	})
	classNew := compileJavaSources(t, map[string]string{
		"classnoninherit/I.java": `package classnoninherit; public interface I { static int f(){return 3;} }`,
		"classnoninherit/C.java": `package classnoninherit; public final class C implements I { }`,
	})
	classOld["classnoninherit/C"] = classNew["classnoninherit/C"]
	classRoot := parseStaticsClass(t, classOld["classnoninherit/Root"])
	_, classPC := verifyM4faMemberInstruction(t, classRoot, classRoot.namedMethod(t, "run"), 0xb8, 10, "f", "()I")
	runtimeM4fcAssertSolidityError(t, classOld, "classnoninherit/Root", "run", "CallError(uint256,uint256)", 3, uint64(classPC))
	runtimeM4fcAssertJava8(t, classOld, "classnoninherit.Root", "java.lang.NoSuchMethodError", true)
}

func TestRuntimeM4fcCrossInterfaceClassReentrantInitializationRunsOnce(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"crossinit/Tracker.java": `package crossinit; public final class Tracker { static int n; static int mark(int x){n=n*10+x;return x;} }`,
		"crossinit/A.java": `package crossinit; public interface A {
			int X=Helper.start(); static int peek(){return X;} static int value(){return X;}
		}`,
		"crossinit/Helper.java": `package crossinit; public final class Helper {
			static int start(){Tracker.mark(1);return C.touch()+1;}
		}`,
		"crossinit/B.java": `package crossinit; public interface B {
			int Y=init(); static int init(){Tracker.mark(3);return A.peek()+4;} static int value(){return Y;}
		}`,
		"crossinit/C.java": `package crossinit; public final class C {
			static int V=B.value(); static int touch(){Tracker.mark(2);return V;}
		}`,
		"crossinit/Root.java": `package crossinit; public final class Root {
			public static int run(){int a=A.value();return Tracker.n*100+a*10+B.value()+A.value()-a;}
		}`,
	})
	// A(active)->Helper->C(active)->B(active)->A observes A's prepared zero.
	// Each initializer and the replayed C.touch invocation executes exactly once.
	runtimeM4fcAssertValue(t, classes, "crossinit/Root", "run", nil, 13254)
}

func TestRuntimeM4fcInterfaceInitializerFailureWrappingAndReceiverFreeCall(t *testing.T) {
	failure := compileJavaSources(t, map[string]string{
		"ifail/I.java":    `package ifail; public interface I { int X=1/zero(); static int zero(){return 0;} static int run(){return X;} }`,
		"ifail/Root.java": `package ifail; public final class Root { public static int run(){return I.run();} }`,
	})
	runtimeM4fcAssertException(t, failure, "ifail/Root", "run", "java.lang.ExceptionInInitializerError")

	classes := compileJavaSources(t, map[string]string{
		"nostaticreceiver/I.java": `package nostaticreceiver; public interface I { static int f(){return 7;} }`,
		"nostaticreceiver/Root.java": `package nostaticreceiver; public final class Root {
			public static int call(){return I.f();} public static int padding(){int x=0;x++;x++;return x;}
		}`,
	})
	root := parseStaticsClass(t, classes["nostaticreceiver/Root"])
	ref, _ := verifyM4faMemberInstruction(t, root, root.namedMethod(t, "call"), 0xb8, 11, "f", "()I")
	// An unrelated null below the explicit argument list is neither a receiver nor
	// consumed by invokestatic. swap/pop removes it after the call.
	code := []byte{0x01, 0xb8, byte(ref >> 8), byte(ref), 0x5f, 0x57, 0xac}
	mutated := verifyM4faRewriteCode(t, classes["nostaticreceiver/Root"], "padding", "()I", code, 3, 0)
	classes["nostaticreceiver/Root"] = mutated
	runtimeM4fcAssertValue(t, classes, "nostaticreceiver/Root", "padding", nil, 7)
}

func runtimeM4fcMutateMethod(t *testing.T, original []byte, name, descriptor string, edit func([]byte, staticsMethod)) []byte {
	t.Helper()
	out := append([]byte(nil), original...)
	edit(out, parseStaticsClass(t, out).method(t, name, descriptor))
	return out
}

func TestRuntimeM4fcInterfaceStaticMethodShapesAreCallErrors(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"staticshape/I.java":    `package staticshape; public interface I { static int f(){return 7;} }`,
		"staticshape/Root.java": `package staticshape; public final class Root { public static int run(){return I.f();} }`,
	})
	root := parseStaticsClass(t, classes["staticshape/Root"])
	_, pc := verifyM4faMemberInstruction(t, root, root.namedMethod(t, "run"), 0xb8, 11, "f", "()I")
	for _, tc := range []struct {
		name string
		edit func(uint16) uint16
	}{
		{"instance", func(flags uint16) uint16 { return flags &^ 0x0008 }},
		{"private", func(flags uint16) uint16 { return (flags &^ 0x0001) | 0x0002 }},
		{"native", func(flags uint16) uint16 { return flags | 0x0100 }},
		{"synchronized", func(flags uint16) uint16 { return flags | 0x0020 }},
		{"abstract-with-code", func(flags uint16) uint16 { return flags | 0x0400 }},
	} {
		t.Run(tc.name, func(t *testing.T) {
			mutated := runtimeM4fcMutateMethod(t, classes["staticshape/I"], "f", "()I", func(raw []byte, method staticsMethod) {
				binary.BigEndian.PutUint16(raw[method.accessOffset:], tc.edit(method.access))
			})
			bundle := map[string][]byte{"staticshape/I": mutated, "staticshape/Root": classes["staticshape/Root"]}
			runtimeM4fcAssertSolidityError(t, bundle, "staticshape/Root", "run", "CallError(uint256,uint256)", 4, uint64(pc))
		})
	}
}

func TestRuntimeM4fcResolveBeforeStaticnessAndWrongOwnerKinds(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"resolvefirst/I.java":    `package resolvefirst; public interface I { int X=3; static int f(){return 3;} }`,
		"resolvefirst/C.java":    `package resolvefirst; public final class C { public static int X=4; public static int f(){return 4;} }`,
		"resolvefirst/Root.java": `package resolvefirst; public final class Root { public static int field(){return C.X;} public static int call(){return C.f();} }`,
	})
	classFile := append([]byte(nil), classes["resolvefirst/C"]...)
	parsedClass := parseStaticsClass(t, classFile)
	field := parsedClass.field(t, "X", "I")
	binary.BigEndian.PutUint16(classFile[field.accessOffset:], (field.access&^uint16(0x0008))|uint16(0x0002))
	classes["resolvefirst/C"] = classFile
	root := parseStaticsClass(t, classes["resolvefirst/Root"])
	_, fieldPC := verifyM4faFieldInstruction(t, root, root.namedMethod(t, "field"), 0xb2, "X", "I")
	runtimeM4fcAssertSolidityError(t, classes, "resolvefirst/Root", "field", "FieldError(uint256,uint256)", 3, uint64(fieldPC))

	callRef, callPC := verifyM4faMemberInstruction(t, root, root.namedMethod(t, "call"), 0xb8, 10, "f", "()I")
	cp11Class := append([]byte(nil), classes["resolvefirst/Root"]...)
	cp11Parsed := parseStaticsClass(t, cp11Class)
	cp11Class[cp11Parsed.entry(t, callRef).offset] = 11
	classes["resolvefirst/Root"] = cp11Class
	runtimeM4fcAssertSolidityError(t, classes, "resolvefirst/Root", "call", "InterfaceError(uint256,uint256)", 1, uint64(callPC))

	ifaceCall := compileJavaSources(t, map[string]string{
		"wrongkind/I.java":    `package wrongkind; public interface I { static int f(){return 1;} }`,
		"wrongkind/Root.java": `package wrongkind; public final class Root { public static int run(){return I.f();} }`,
	})
	wrongRoot := append([]byte(nil), ifaceCall["wrongkind/Root"]...)
	wrongParsed := parseStaticsClass(t, wrongRoot)
	ifaceRef, ifacePC := verifyM4faMemberInstruction(t, wrongParsed, wrongParsed.namedMethod(t, "run"), 0xb8, 11, "f", "()I")
	wrongRoot[wrongParsed.entry(t, ifaceRef).offset] = 10
	ifaceCall["wrongkind/Root"] = wrongRoot
	runtimeM4fcAssertSolidityError(t, ifaceCall, "wrongkind/Root", "run", "CallError(uint256,uint256)", 4, uint64(ifacePC))
}
