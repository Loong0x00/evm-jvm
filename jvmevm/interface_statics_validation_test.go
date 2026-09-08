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
	verifyM4fcGasLimit     = uint64(100_000_000)
	verifyM4fcGetstatic    = byte(0xb2)
	verifyM4fcPutstatic    = byte(0xb3)
	verifyM4fcGetfield     = byte(0xb4)
	verifyM4fcPutfield     = byte(0xb5)
	verifyM4fcInvokestatic = byte(0xb8)
	verifyM4fcAbstract     = uint16(0x0400)
	verifyM4fcSynchronized = uint16(0x0020)
)

// Every source compiled here is a bounded, trusted Java 8 probe. Mutations are
// narrow test-only classfile edits. The production API still receives raw class
// bytes and performs parsing, resolution, initialization, and execution in EVM.

func TestVerifyM4fcInterfaceStaticRootsCallsTypedArgumentsAndNullSemantics(t *testing.T) {
	classes := verifyM4fcCompile(t, map[string]string{
		"api/Box.java": `package api; public final class Box { public int value; }`,
		"api/I.java": `package api; public interface I {
			static int add(int x){return x+7;} static Box id(Box x){return x;}
			static int length(int[] x){return x.length;} static int classCall(int x){return Helper.twice(x);}
			static int nullInside(){Box x=null;return x.value;}
			default int fromDefault(int x){return I.add(x);}
		}`,
		"api/J.java":      `package api; public interface J { static int cross(int x){return I.add(x);} }`,
		"api/Helper.java": `package api; public final class Helper { public static int twice(int x){return x*2;} }`,
		"api/Impl.java":   `package api; public final class Impl implements I { }`,
		"api/Root.java": `package api; public final class Root {
			public static int run(int x){Box b=new Box();b.value=3;int[] a=new int[2];
				return I.add(x)*100+I.id(b).value*10+I.length(a)+I.classCall(x)+J.cross(x);}
			public static int viaDefault(int x){return new Impl().fromDefault(x);}
			public static int padding(int x){int y=0;` + strings.Repeat("y=y+1;", 30) + `return y+x;}
		}`,
	}, "api/Box", "api/I", "api/J", "api/Helper", "api/Impl", "api/Root")
	bundle := verifyM4fcBundle(classes)
	verifyM4fcJava8Outcome(t, bundle, "api.Root", "run", []int32{2}, "value=945")
	verifyM4fcAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "api/Root", "run", []int32{2}, verifyM4fcGasLimit)
	}, 945)
	verifyM4fcAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "api/Root", "viaDefault", []int32{4}, verifyM4fcGasLimit)
	}, 11)
	verifyM4fcAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "api/I", "add", []int32{4}, verifyM4fcGasLimit)
	}, 11)
	verifyM4fcAssertValue(t, func() (Result, error) {
		return Run(classes["api/I"], "add", []int32{4}, verifyM4fcGasLimit)
	}, 11)
	verifyM4fcAssertException(t, func() (Result, error) {
		return RunClasses(bundle, "api/I", "nullInside", nil, verifyM4fcGasLimit)
	}, "java.lang.NullPointerException", 6)

	root := classes["api/Root"]
	parsed := parseStaticsClass(t, root)
	ref, _ := verifyM4fcMemberInstruction(t, parsed, parsed.method(t, "run", "(I)I"), verifyM4fcInvokestatic, 11, "add", "(I)I")
	// Keep an unrelated null below the explicit int argument. invokestatic has
	// no receiver and must consume only its descriptor arguments.
	code := []byte{0x01, 0x1a, verifyM4fcInvokestatic, byte(ref >> 8), byte(ref), 0x3c, 0x57, 0x1b, 0xac}
	prefix := verifyM4faRewriteCode(t, root, "padding", "(I)I", code, 4, 2)
	verifyM4fcAssertValue(t, func() (Result, error) {
		return RunClasses([][]byte{classes["api/I"], prefix}, "api/Root", "padding", []int32{5}, verifyM4fcGasLimit)
	}, 12)
}

func TestVerifyM4fcInterfaceStaticCallCPKindsExactLookupShapesAndBoundaries(t *testing.T) {
	classes := verifyM4fcCompile(t, map[string]string{
		"calls/Parent.java": `package calls; public interface Parent { static int s(int x){return x+1;} }`,
		"calls/Child.java":  `package calls; public interface Child extends Parent { static int s(int x){return x+2;} }`,
		"calls/Root.java": `package calls; public final class Root {
			public static int run(int x){return Child.s(x);} public static int absent(int x){return x;}
			public static int padding(){int x=0;` + strings.Repeat("x=x+1;", 40) + `return x;}
		}`,
	}, "calls/Parent", "calls/Child", "calls/Root")
	root := classes["calls/Root"]
	parsed := parseStaticsClass(t, root)
	ref, pc := verifyM4fcMemberInstruction(t, parsed, parsed.method(t, "run", "(I)I"), verifyM4fcInvokestatic, 11, "s", "(I)I")
	verifyM4fcAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4fcBundle(classes), "calls/Root", "run", []int32{3}, verifyM4fcGasLimit)
	}, 5)

	missing := verifyM4faRenameMethod(t, classes["calls/Child"], "s", "(I)I", 'g')
	verifyM4fcAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["calls/Parent"], missing, root}, "calls/Root", "run", []int32{3}, verifyM4fcGasLimit)
	}, "CallError(uint256,uint256)", 3, uint64(pc))

	for _, tc := range []struct {
		name string
		make func([]byte, staticsClass)
		sig  string
		code uint64
	}{
		{"cp-zero", func(_ []byte, c staticsClass) { binary.BigEndian.PutUint16(c.method(t, "run", "(I)I").code[pc+1:], 0) }, "CallError(uint256,uint256)", 1},
		{"cp-range", func(_ []byte, c staticsClass) {
			binary.BigEndian.PutUint16(c.method(t, "run", "(I)I").code[pc+1:], uint16(c.cpCount))
		}, "CallError(uint256,uint256)", 1},
		// CP10 is structurally valid but cannot name an interface invokestatic.
		{"cp10-interface", func(raw []byte, c staticsClass) { raw[c.entry(t, ref).offset] = 10 }, "CallError(uint256,uint256)", 4},
		// Conversely CP11 naming an ordinary class is an exact owner-kind fault.
		{"cp11-class", func(raw []byte, c staticsClass) {
			binary.BigEndian.PutUint16(raw[c.entry(t, ref).offset+1:], verifyM4faClassIndex(t, c, "calls/Root"))
		}, "InterfaceError(uint256,uint256)", 1},
	} {
		t.Run(tc.name, func(t *testing.T) {
			bad := verifyM4faMutate(t, root, tc.make)
			verifyM4fcAssertError(t, func() (Result, error) {
				return RunClasses([][]byte{classes["calls/Parent"], classes["calls/Child"], bad}, "calls/Root", "run", []int32{3}, verifyM4fcGasLimit)
			}, tc.sig, tc.code, uint64(pc))
		})
	}

	for _, tc := range []struct {
		name string
		edit func(uint16) uint16
	}{
		{"nonstatic", func(f uint16) uint16 { return f &^ accStatic }},
		{"private", func(f uint16) uint16 { return (f &^ accessMask) | accPrivate | accStatic }},
		{"native", func(f uint16) uint16 { return f | accNative }},
		{"synchronized", func(f uint16) uint16 { return f | verifyM4fcSynchronized }},
		{"abstract-with-code", func(f uint16) uint16 { return f | verifyM4fcAbstract }},
	} {
		t.Run("shape-"+tc.name, func(t *testing.T) {
			child := verifyM4fcMutateMethod(t, classes["calls/Child"], "s", "(I)I", func(raw []byte, m staticsMethod) {
				binary.BigEndian.PutUint16(raw[m.accessOffset:], tc.edit(m.access))
			})
			verifyM4fcAssertError(t, func() (Result, error) {
				return RunClasses([][]byte{classes["calls/Parent"], child, root}, "calls/Root", "run", []int32{3}, verifyM4fcGasLimit)
			}, "CallError(uint256,uint256)", 4, uint64(pc))
		})
	}
	noCode := verifyM4fcMutateMethod(t, classes["calls/Child"], "s", "(I)I", func(raw []byte, m staticsMethod) {
		binary.BigEndian.PutUint16(raw[m.codeNameOffset:], parseStaticsClass(t, raw).utfIndex(t, "SourceFile"))
	})
	verifyM4fcAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["calls/Parent"], noCode, root}, "calls/Root", "run", []int32{3}, verifyM4fcGasLimit)
	}, "CallError(uint256,uint256)", 4, uint64(pc))

	for operands := 0; operands <= 1; operands++ {
		t.Run(fmt.Sprintf("truncated-%d", operands), func(t *testing.T) {
			ending := append([]byte{verifyM4fcInvokestatic}, make([]byte, operands)...)
			bad := verifyM4faRewriteAtEnd(t, root, "padding", "()I", ending)
			boundary := len(parseStaticsClass(t, bad).method(t, "padding", "()I").code) - len(ending)
			verifyM4fcAssertError(t, func() (Result, error) { return Run(bad, "padding", nil, verifyM4fcGasLimit) }, "BytecodeError(uint256,uint256)", 2, uint64(boundary))
		})
	}
	for operand := 1; operand <= 2; operand++ {
		t.Run(fmt.Sprintf("branch-operand-%d", operand), func(t *testing.T) {
			invokePC := 5
			target := invokePC + operand
			offset := target - 1
			code := []byte{0x03, 0x99, byte(offset >> 8), byte(offset), 0x03, verifyM4fcInvokestatic, byte(ref >> 8), byte(ref), 0xac}
			bad := verifyM4faRewriteCode(t, root, "padding", "()I", code, 4, 1)
			verifyM4fcAssertError(t, func() (Result, error) {
				return RunClasses([][]byte{classes["calls/Child"], bad}, "calls/Root", "padding", nil, verifyM4fcGasLimit)
			}, "BytecodeError(uint256,uint256)", 12, 1)
		})
	}
}

func TestVerifyM4fcStaticResolutionPrecedesInitializationAndBodyInspection(t *testing.T) {
	classes := verifyM4fcCompile(t, map[string]string{
		"resolve/I.java": `package resolve; public interface I {
			int BAD=9/zero(); static int zero(){return 0;} static int present(){return BAD;}
		}`,
		"resolve/Root.java": `package resolve; public final class Root {
			public static int run(){return I.present();} public static int absent(){return 1;}
		}`,
	}, "resolve/I", "resolve/Root")
	root := classes["resolve/Root"]
	c := parseStaticsClass(t, root)
	ref, pc := verifyM4fcMemberInstruction(t, c, c.namedMethod(t, "run"), verifyM4fcInvokestatic, 11, "present", "()I")
	missing := verifyM4faMutate(t, root, func(raw []byte, p staticsClass) {
		nat := p.entry(t, p.u2(t, p.entry(t, ref).offset+3))
		binary.BigEndian.PutUint16(raw[nat.offset+1:], p.utfIndex(t, "absent"))
	})
	verifyM4fcAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["resolve/I"], missing}, "resolve/Root", "run", nil, verifyM4fcGasLimit)
	}, "CallError(uint256,uint256)", 3, uint64(pc))

	// A selected native/body inconsistency is rejected as Call4 before Code is
	// entered; the unsupported byte at PC 0 must not become BytecodeError.
	badBody := verifyM4fcMutateMethod(t, classes["resolve/I"], "present", "()I", func(raw []byte, m staticsMethod) {
		binary.BigEndian.PutUint16(raw[m.accessOffset:], m.access|accNative)
		m.code[0] = 0xff
	})
	verifyM4fcAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{badBody, root}, "resolve/Root", "run", nil, verifyM4fcGasLimit)
	}, "CallError(uint256,uint256)", 4, uint64(pc))
}

func TestVerifyM4fcDeclaringInterfaceInitializationNotQualifierOrParents(t *testing.T) {
	classes := verifyM4fcCompile(t, map[string]string{
		"owner/Tracker.java":       `package owner; public final class Tracker { public static int value; public static int mark(int x){value=value*10+x;return x;} }`,
		"owner/Parent.java":        `package owner; public interface Parent { int X=Tracker.mark(1); }`,
		"owner/DefaultParent.java": `package owner; public interface DefaultParent { int D=Tracker.mark(6); default int f(){return 6;} }`,
		"owner/Child.java": `package owner; public interface Child extends Parent,DefaultParent {
			int Y=Tracker.mark(2); static int active(){return Tracker.mark(7)+Tracker.value*10;}
		}`,
		"owner/C.java": `package owner; public final class C implements Child {
			static int OWN=Tracker.mark(8);
		}`,
		"owner/Root.java": `package owner; public final class Root {
			public static int inherited(){return Child.X*100+Parent.X*10+Tracker.value;}
			public static int throughClass(){return C.X*100+Parent.X*10+Tracker.value;}
			public static int active(){return Child.active();}
			public static int classDefault(){new C();return Tracker.value;}
		}`,
	}, "owner/Tracker", "owner/Parent", "owner/DefaultParent", "owner/Child", "owner/C", "owner/Root")
	root := parseStaticsClass(t, classes["owner/Root"])
	for _, method := range []string{"inherited", "throughClass"} {
		ref, _ := verifyM4faFieldInstruction(t, root, root.namedMethod(t, method), verifyM4fcGetstatic, "X", "I")
		owner := verifyM4fcRefOwner(t, root, ref)
		want := map[string]string{"inherited": "owner/Child", "throughClass": "owner/C"}[method]
		if owner != want {
			t.Fatalf("%s symbolic field owner=%q want %q", method, owner, want)
		}
	}
	bundle := verifyM4fcBundle(classes)
	for _, tc := range []struct {
		method string
		want   int32
	}{
		{"inherited", 111},    // Both qualifiers share Parent.X; Parent initializes once.
		{"throughClass", 111}, // C and Parent qualifiers share storage; C/Child stay idle.
		{"active", 277},       // Child only: mark(2), then active mark(7); parents stay untouched.
		{"classDefault", 68},  // ordinary class still initializes default-declaring Parent then C.
	} {
		t.Run(tc.method, func(t *testing.T) {
			verifyM4fcJava8Outcome(t, bundle, "owner.Root", tc.method, nil, "value="+strconv.Itoa(int(tc.want)))
			verifyM4fcAssertValue(t, func() (Result, error) {
				return RunClasses(bundle, "owner/Root", tc.method, nil, verifyM4fcGasLimit)
			}, tc.want)
		})
	}
}

func TestVerifyM4fcFieldResolutionDFSBeforeSuperclassUsesJava8Evolution(t *testing.T) {
	old := verifyM4fcCompile(t, map[string]string{
		"evofield/Tracker.java": `package evofield; public final class Tracker { public static int value; public static int mark(int x){value=value*10+x;return x;} }`,
		"evofield/Top.java":     `package evofield; public interface Top { }`,
		"evofield/Left.java":    `package evofield; public interface Left extends Top { }`,
		"evofield/Right.java":   `package evofield; public interface Right { }`,
		"evofield/Parent.java":  `package evofield; public class Parent { public static int X=Tracker.mark(3); }`,
		"evofield/C.java":       `package evofield; public final class C extends Parent implements Left,Right { }`,
		"evofield/Root.java":    `package evofield; public final class Root { public static int run(){return C.X*100+Tracker.value;} }`,
	}, "evofield/Tracker", "evofield/Top", "evofield/Left", "evofield/Right", "evofield/Parent", "evofield/C", "evofield/Root")
	newTop := verifyM4fcCompile(t, map[string]string{
		"evofield/Tracker.java": `package evofield; public final class Tracker { public static int value; public static int mark(int x){value=value*10+x;return x;} }`,
		"evofield/Top.java":     `package evofield; public interface Top { int X=Tracker.mark(1); }`,
	}, "evofield/Top")
	bundle := [][]byte{old["evofield/Tracker"], newTop["evofield/Top"], old["evofield/Left"], old["evofield/Right"], old["evofield/Parent"], old["evofield/C"], old["evofield/Root"]}
	root := parseStaticsClass(t, old["evofield/Root"])
	ref, _ := verifyM4faFieldInstruction(t, root, root.namedMethod(t, "run"), verifyM4fcGetstatic, "X", "I")
	if owner := verifyM4fcRefOwner(t, root, ref); owner != "evofield/C" {
		t.Fatalf("binary-evolution Fieldref owner=%q want evofield/C", owner)
	}
	verifyM4fcJava8Outcome(t, bundle, "evofield.Root", "run", nil, "value=101")
	verifyM4fcAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "evofield/Root", "run", nil, verifyM4fcGasLimit)
	}, 101)
}

func TestVerifyM4fcFieldDeclarationWinsBeforeInterfacesAndSuperclass(t *testing.T) {
	classes := verifyM4fcCompile(t, map[string]string{
		"ownfield/Tracker.java": `package ownfield; public final class Tracker { public static int value; public static int mark(int x){value=value*10+x;return x;} }`,
		"ownfield/Face.java":    `package ownfield; public interface Face { int X=Tracker.mark(1); }`,
		"ownfield/Base.java":    `package ownfield; public class Base { public static int X=Tracker.mark(2); }`,
		"ownfield/C.java":       `package ownfield; public final class C extends Base implements Face { public static int X=Tracker.mark(3); }`,
		"ownfield/Root.java":    `package ownfield; public final class Root { public static int run(){return C.X*100+Face.X*10+Base.X;} }`,
	}, "ownfield/Tracker", "ownfield/Face", "ownfield/Base", "ownfield/C", "ownfield/Root")
	root := parseStaticsClass(t, classes["ownfield/Root"])
	ref, _ := verifyM4faFieldInstruction(t, root, root.namedMethod(t, "run"), verifyM4fcGetstatic, "X", "I")
	if owner := verifyM4fcRefOwner(t, root, ref); owner != "ownfield/C" {
		t.Fatalf("declaration-first Fieldref owner=%q want ownfield/C", owner)
	}
	bundle := verifyM4fcBundle(classes)
	verifyM4fcJava8Outcome(t, bundle, "ownfield.Root", "run", nil, "value=312")
	verifyM4fcAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "ownfield/Root", "run", nil, verifyM4fcGasLimit)
	}, 312)
}

func TestVerifyM4fcFieldResolutionDoesNotSkipInstanceOrPrivateDeclaration(t *testing.T) {
	old := verifyM4fcCompile(t, map[string]string{
		"fieldkind/Parent.java": `package fieldkind; public class Parent { public static int X=7; }`,
		"fieldkind/Child.java":  `package fieldkind; public final class Child extends Parent { }`,
		"fieldkind/Root.java":   `package fieldkind; public final class Root { public static int run(){return Child.X;} }`,
	}, "fieldkind/Parent", "fieldkind/Child", "fieldkind/Root")
	newChild := verifyM4fcCompile(t, map[string]string{
		"fieldkind/Parent.java": `package fieldkind; public class Parent { public static int X=7; }`,
		"fieldkind/Child.java":  `package fieldkind; public final class Child extends Parent { public int X; }`,
	}, "fieldkind/Child")
	bundle := [][]byte{old["fieldkind/Parent"], newChild["fieldkind/Child"], old["fieldkind/Root"]}
	verifyM4fcJava8Outcome(t, bundle, "fieldkind.Root", "run", nil, "java.lang.IncompatibleClassChangeError")
	_, pc := verifyM4faFieldInstruction(t, parseStaticsClass(t, old["fieldkind/Root"]), parseStaticsClass(t, old["fieldkind/Root"]).namedMethod(t, "run"), verifyM4fcGetstatic, "X", "I")
	verifyM4fcAssertError(t, func() (Result, error) {
		return RunClasses(bundle, "fieldkind/Root", "run", nil, verifyM4fcGasLimit)
	}, "FieldError(uint256,uint256)", 3, uint64(pc))

	privateChild := verifyM4faMutate(t, newChild["fieldkind/Child"], func(raw []byte, c staticsClass) {
		f := c.field(t, "X", "I")
		binary.BigEndian.PutUint16(raw[f.accessOffset:], (f.access&^accessMask)|accPrivate)
	})
	verifyM4fcAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{old["fieldkind/Parent"], privateChild, old["fieldkind/Root"]}, "fieldkind/Root", "run", nil, verifyM4fcGasLimit)
	}, "FieldError(uint256,uint256)", 3, uint64(pc))
}

func TestVerifyM4fcFieldStorageAliasesHiddenDeclarationAndOpcodeStaticness(t *testing.T) {
	classes := verifyM4fcCompile(t, map[string]string{
		"hiddenfield/P.java":     `package hiddenfield; interface P { int X=init(); static int init(){return 9;} }`,
		"hiddenfield/C.java":     `package hiddenfield; public interface C extends P { }`,
		"outsidefield/Root.java": `package outsidefield; public final class Root { public static int hidden(){return hiddenfield.C.X;} }`,
		"mismatch/I.java":        `package mismatch; public interface I { int X=init(); static int init(){return 7;} }`,
		"mismatch/Box.java":      `package mismatch; public final class Box { public int x; }`,
		"mismatch/Root.java": `package mismatch; public final class Root {
			static int read(Box b){return b.x;} static int write(Box b,int x){b.x=x;return x;}
			public static int get(){return read(new Box());} public static int put(){return write(new Box(),3);}
			public static int mention(){return I.X;}
		}`,
	}, "hiddenfield/P", "hiddenfield/C", "outsidefield/Root", "mismatch/I", "mismatch/Box", "mismatch/Root")
	hiddenRoot := parseStaticsClass(t, classes["outsidefield/Root"])
	hiddenRef, _ := verifyM4faFieldInstruction(t, hiddenRoot, hiddenRoot.namedMethod(t, "hidden"), verifyM4fcGetstatic, "X", "I")
	if owner := verifyM4fcRefOwner(t, hiddenRoot, hiddenRef); owner != "hiddenfield/C" {
		t.Fatalf("public symbolic qualifier=%q want hiddenfield/C", owner)
	}
	verifyM4fcAssertValue(t, func() (Result, error) {
		return RunClasses([][]byte{classes["hiddenfield/P"], classes["hiddenfield/C"], classes["outsidefield/Root"]}, "outsidefield/Root", "hidden", nil, verifyM4fcGasLimit)
	}, 9)

	root := classes["mismatch/Root"]
	c := parseStaticsClass(t, root)
	staticRef, _ := verifyM4faFieldInstruction(t, c, c.namedMethod(t, "mention"), verifyM4fcGetstatic, "X", "I")
	for _, tc := range []struct {
		method string
		opcode byte
	}{
		{"read", verifyM4fcGetfield}, {"write", verifyM4fcPutfield},
	} {
		t.Run(tc.method, func(t *testing.T) {
			_, pc := verifyM4faFieldInstruction(t, c, c.namedMethod(t, tc.method), tc.opcode, "x", "I")
			bad := verifyM4faMutate(t, root, func(_ []byte, p staticsClass) {
				_, at := verifyM4faFieldInstruction(t, p, p.namedMethod(t, tc.method), tc.opcode, "x", "I")
				binary.BigEndian.PutUint16(p.namedMethod(t, tc.method).code[at+1:], staticRef)
			})
			entry := map[string]string{"read": "get", "write": "put"}[tc.method]
			verifyM4fcAssertError(t, func() (Result, error) {
				return RunClasses([][]byte{classes["mismatch/I"], classes["mismatch/Box"], bad}, "mismatch/Root", entry, nil, verifyM4fcGasLimit)
			}, "FieldError(uint256,uint256)", 3, uint64(pc))
		})
	}
}

func TestVerifyM4fcInvalidInterfaceFieldFlagsRemainGraphShapeErrors(t *testing.T) {
	classes := verifyM4fcCompile(t, map[string]string{
		"fieldshape/I.java":    `package fieldshape; public interface I { int X=init(); static int init(){return 7;} }`,
		"fieldshape/Root.java": `package fieldshape; public final class Root { public static int run(){return I.X;} }`,
	}, "fieldshape/I", "fieldshape/Root")
	for _, tc := range []struct {
		name string
		bit  uint16
	}{
		{"public", accPublic}, {"static", accStatic}, {"final", accFinal},
	} {
		t.Run(tc.name, func(t *testing.T) {
			bad := verifyM4faMutate(t, classes["fieldshape/I"], func(raw []byte, c staticsClass) {
				f := c.field(t, "X", "I")
				binary.BigEndian.PutUint16(raw[f.accessOffset:], f.access&^tc.bit)
			})
			// Interface is deliberately bundle index 0. This is not a private-field
			// FieldError4 probe; malformed Java 8 interface field shape is graph error 1.
			verifyM4fcAssertError(t, func() (Result, error) {
				return RunClasses([][]byte{bad, classes["fieldshape/Root"]}, "fieldshape/Root", "run", nil, verifyM4fcGasLimit)
			}, "InterfaceError(uint256,uint256)", 1, 0)
		})
	}
}

func TestVerifyM4fcInterfaceFinalFieldsCacheCrossOwnerAndTypedReferences(t *testing.T) {
	classes := verifyM4fcCompile(t, map[string]string{
		"finals/Box.java": `package finals; public final class Box { public int value; }`,
		"finals/I.java": `package finals; public interface I {
			int A=readB(); int B=makeB(); Box BOX=makeBox(); int[] ARRAY=makeArray(); Object OBJECT=BOX;
			static int readB(){return B;} static int makeB(){return 9;}
			static Box makeBox(){Box b=new Box();b.value=4;return b;}
			static int[] makeArray(){return new int[2];}
		}`,
		"finals/Parent.java": `package finals; public interface Parent { int X=init(); static int init(){return 7;} }`,
		"finals/Child.java":  `package finals; public interface Child extends Parent { int Y=initY(); static int initY(){return 3;} static int parent(){return Parent.X;} }`,
		"finals/Root.java": `package finals; public final class Root {
			public static int valid(){I.ARRAY[0]=5;I.BOX.value=6;return I.A*1000+I.B*100+I.ARRAY[0]*10+I.BOX.value+(I.OBJECT==I.BOX?1:0);}
			public static int child(){return Child.Y;} public static int cachedWrite(){int x=Parent.X;` + strings.Repeat("x=x+1;", 12) + `return x;}
		}`,
	}, "finals/Box", "finals/I", "finals/Parent", "finals/Child", "finals/Root")
	bundle := verifyM4fcBundle(classes)
	verifyM4fcJava8Outcome(t, bundle, "finals.Root", "valid", nil, "value=957")
	verifyM4fcAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "finals/Root", "valid", nil, verifyM4fcGasLimit)
	}, 957)

	// Child.<clinit>'s putstatic normally initializes Child.Y. Retarget only the
	// fieldref to Parent.X: a child initializer cannot write its parent's final.
	child := classes["finals/Child"]
	childParsed := parseStaticsClass(t, child)
	_, childPutPC := verifyM4faFieldInstruction(t, childParsed, childParsed.method(t, "<clinit>", "()V"), verifyM4fcPutstatic, "Y", "I")
	childWithParent, parentClass := verifyM4faAppendNameAndClass(t, child, "finals/Parent")
	childWithParent = verifyM4faMutate(t, childWithParent, func(raw []byte, c staticsClass) {
		ref, _ := verifyM4faFieldInstruction(t, c, c.method(t, "<clinit>", "()V"), verifyM4fcPutstatic, "Y", "I")
		e := c.entry(t, ref)
		binary.BigEndian.PutUint16(raw[e.offset+1:], parentClass)
		nat := c.entry(t, c.u2(t, e.offset+3))
		binary.BigEndian.PutUint16(raw[nat.offset+1:], c.utfIndex(t, "X"))
	})
	verifyM4fcAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["finals/Parent"], childWithParent, classes["finals/Root"]}, "finals/Root", "child", nil, verifyM4fcGasLimit)
	}, "FieldError(uint256,uint256)", 4, uint64(childPutPC))

	// Rewrite one roomy method to use one Parent.X Fieldref for a successful
	// cached read and then an unauthorized final write at a distinct PC.
	root := classes["finals/Root"]
	p := parseStaticsClass(t, root)
	parentRef, _ := verifyM4faFieldInstruction(t, p, p.namedMethod(t, "cachedWrite"), verifyM4fcGetstatic, "X", "I")
	code := []byte{verifyM4fcGetstatic, byte(parentRef >> 8), byte(parentRef), 0x57, 0x04, verifyM4fcPutstatic, byte(parentRef >> 8), byte(parentRef), 0x04, 0xac}
	unauthorized := verifyM4faRewriteCode(t, root, "cachedWrite", "()I", code, 2, 0)
	verifyM4fcAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["finals/Parent"], unauthorized}, "finals/Root", "cachedWrite", nil, verifyM4fcGasLimit)
	}, "FieldError(uint256,uint256)", 4, 5)
}

func TestVerifyM4fcCrossInterfaceClassReentrancyAndInstructionReplay(t *testing.T) {
	classes := verifyM4fcCompile(t, map[string]string{
		"cyclefc/Tracker.java": `package cyclefc; public final class Tracker { public static int value; public static int mark(int x){value=value*10+x;return x;} }`,
		"cyclefc/Helper.java":  `package cyclefc; public final class Helper { public static int start(){Tracker.mark(1);return C.touch()+3;} }`,
		"cyclefc/I.java": `package cyclefc; public interface I {
			int X=Helper.start(); static int peek(){return X;} default int d(){return 1;}
		}`,
		"cyclefc/C.java": `package cyclefc; public final class C implements I {
			static int Y=Tracker.mark(2); public static int touch(){return I.peek()+Y;}
		}`,
		"cyclefc/Root.java": `package cyclefc; public final class Root { public static int run(){return I.X*100+Tracker.value;} }`,
	}, "cyclefc/Tracker", "cyclefc/Helper", "cyclefc/I", "cyclefc/C", "cyclefc/Root")
	bundle := verifyM4fcBundle(classes)
	verifyM4fcJava8Outcome(t, bundle, "cyclefc.Root", "run", nil, "value=512")
	verifyM4fcAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "cyclefc/Root", "run", nil, verifyM4fcGasLimit)
	}, 512)
}

func TestVerifyM4fcStaticMethodBinaryEvolutionIsNeverInherited(t *testing.T) {
	t.Run("cp11-interface-owner", func(t *testing.T) {
		old := verifyM4fcCompile(t, map[string]string{
			"evocall/Parent.java": `package evocall; public interface Parent { static int s(){return 1;} }`,
			"evocall/Child.java":  `package evocall; public interface Child extends Parent { static int s(){return 2;} }`,
			"evocall/Root.java":   `package evocall; public final class Root { public static int run(){return Child.s();} }`,
		}, "evocall/Parent", "evocall/Child", "evocall/Root")
		newChild := verifyM4fcCompile(t, map[string]string{
			"evocall/Parent.java": `package evocall; public interface Parent { static int s(){return 1;} }`,
			"evocall/Child.java":  `package evocall; public interface Child extends Parent { }`,
		}, "evocall/Child")
		bundle := [][]byte{old["evocall/Parent"], newChild["evocall/Child"], old["evocall/Root"]}
		verifyM4fcJava8Outcome(t, bundle, "evocall.Root", "run", nil, "java.lang.NoSuchMethodError")
		root := parseStaticsClass(t, old["evocall/Root"])
		_, pc := verifyM4fcMemberInstruction(t, root, root.namedMethod(t, "run"), verifyM4fcInvokestatic, 11, "s", "()I")
		verifyM4fcAssertError(t, func() (Result, error) {
			return RunClasses(bundle, "evocall/Root", "run", nil, verifyM4fcGasLimit)
		}, "CallError(uint256,uint256)", 3, uint64(pc))
	})

	t.Run("cp10-class-owner", func(t *testing.T) {
		// CP10 lookup stays on the ordinary superclass chain. Implementing an
		// interface that declares a same-signature static does not make it inherited.
		old := verifyM4fcCompile(t, map[string]string{
			"evoclass/I.java":    `package evoclass; public interface I { static int s(){return 1;} }`,
			"evoclass/Impl.java": `package evoclass; public final class Impl implements I { public static int s(){return 2;} }`,
			"evoclass/Root.java": `package evoclass; public final class Root { public static int run(){return Impl.s();} }`,
		}, "evoclass/I", "evoclass/Impl", "evoclass/Root")
		newImpl := verifyM4fcCompile(t, map[string]string{
			"evoclass/I.java":    `package evoclass; public interface I { static int s(){return 1;} }`,
			"evoclass/Impl.java": `package evoclass; public final class Impl implements I { }`,
		}, "evoclass/Impl")
		bundle := [][]byte{old["evoclass/I"], newImpl["evoclass/Impl"], old["evoclass/Root"]}
		verifyM4fcJava8Outcome(t, bundle, "evoclass.Root", "run", nil, "java.lang.NoSuchMethodError")
		root := parseStaticsClass(t, old["evoclass/Root"])
		_, pc := verifyM4fcMemberInstruction(t, root, root.namedMethod(t, "run"), verifyM4fcInvokestatic, 10, "s", "()I")
		verifyM4fcAssertError(t, func() (Result, error) {
			return RunClasses(bundle, "evoclass/Root", "run", nil, verifyM4fcGasLimit)
		}, "CallError(uint256,uint256)", 3, uint64(pc))
	})
}

func TestVerifyM4fcInterfaceInitializerOutcomesFramesDecoderAndOOG(t *testing.T) {
	classes := verifyM4fcCompile(t, map[string]string{
		"outfc/Arithmetic.java": `package outfc; public interface Arithmetic { int X=9/zero(); static int zero(){return 0;} static int get(){return X;} }`,
		"outfc/Recurse.java":    `package outfc; public interface Recurse { static int call(){return call();} }`,
	}, "outfc/Arithmetic", "outfc/Recurse")
	verifyM4fcAssertException(t, func() (Result, error) {
		return RunClasses([][]byte{classes["outfc/Arithmetic"]}, "outfc/Arithmetic", "get", nil, verifyM4fcGasLimit)
	}, "java.lang.ExceptionInInitializerError", 3)
	verifyM4fcAssertException(t, func() (Result, error) {
		return RunClasses([][]byte{classes["outfc/Recurse"]}, "outfc/Recurse", "call", nil, verifyM4fcGasLimit)
	}, "java.lang.StackOverflowError", 2)
	result, err := RunClasses([][]byte{classes["outfc/Arithmetic"]}, "outfc/Arithmetic", "get", nil, 1)
	if err == nil || !errors.Is(err, vm.ErrOutOfGas) || result.ExceptionClass != "" || len(result.RevertData) != 0 {
		t.Fatalf("result/error=%+v/%v, want unlabeled EVM OOG", result, err)
	}

	known := []string{
		"java.lang.ArithmeticException", "java.lang.StackOverflowError",
		"java.lang.ExceptionInInitializerError", "java.lang.NegativeArraySizeException",
		"java.lang.ArrayIndexOutOfBoundsException", "java.lang.NullPointerException",
		"java.lang.OutOfMemoryError", "java.lang.ClassCastException",
		"java.lang.ArrayStoreException", "java.lang.IncompatibleClassChangeError",
		"java.lang.AbstractMethodError", "java.lang.NoClassDefFoundError",
	}
	for index, want := range known {
		payload := append(append([]byte(nil), javaExceptionSelector...), make([]byte, 32)...)
		payload[len(payload)-1] = byte(index + 1)
		if got, ok := decodeJavaException(payload); !ok || got != want {
			t.Fatalf("kind %d decoded as %q/%v want %q/true", index+1, got, ok, want)
		}
	}
	for _, kind := range []byte{0, 13, 255} {
		payload := append(append([]byte(nil), javaExceptionSelector...), make([]byte, 32)...)
		payload[len(payload)-1] = kind
		if got, ok := decodeJavaException(payload); ok || got != "" {
			t.Fatalf("unknown kind %d decoded as %q/%v", kind, got, ok)
		}
	}
}

func TestVerifyM4fcInterfaceInitializerLinkageErrorsStayUnwrapped(t *testing.T) {
	for _, tc := range []struct {
		name, replacement, want string
		kind                    byte
	}{
		{"icce", `package initlinkfc; public interface B { default int f(){return 2;} }`, "java.lang.IncompatibleClassChangeError", 10},
		{"ame", `package initlinkfc; public interface B extends A { int f(); }`, "java.lang.AbstractMethodError", 11},
	} {
		t.Run(tc.name, func(t *testing.T) {
			old := verifyM4fcCompile(t, map[string]string{
				"initlinkfc/A.java":       `package initlinkfc; public interface A { default int f(){return 1;} }`,
				"initlinkfc/B.java":       `package initlinkfc; public interface B extends A { }`,
				"initlinkfc/C.java":       `package initlinkfc; public final class C implements A,B { }`,
				"initlinkfc/Helper.java":  `package initlinkfc; public final class Helper { static int call(A x){return x.f();} public static int trigger(){return call(new C());} }`,
				"initlinkfc/Trigger.java": `package initlinkfc; public interface Trigger { int X=Helper.trigger(); static int get(){return X;} }`,
			}, "initlinkfc/A", "initlinkfc/B", "initlinkfc/C", "initlinkfc/Helper", "initlinkfc/Trigger")
			newVersion := verifyM4fcCompile(t, map[string]string{
				"initlinkfc/A.java": `package initlinkfc; public interface A { default int f(){return 1;} }`,
				"initlinkfc/B.java": tc.replacement,
			}, "initlinkfc/B")
			bundle := [][]byte{old["initlinkfc/A"], newVersion["initlinkfc/B"], old["initlinkfc/C"], old["initlinkfc/Helper"], old["initlinkfc/Trigger"]}
			verifyM4fcJava8Outcome(t, bundle, "initlinkfc.Trigger", "get", nil, tc.want)
			verifyM4fcAssertException(t, func() (Result, error) {
				return RunClasses(bundle, "initlinkfc/Trigger", "get", nil, verifyM4fcGasLimit)
			}, tc.want, tc.kind)
		})
	}
}

func TestVerifyM4fcInterfaceRootRejectedShapesRemainExact(t *testing.T) {
	iface := verifyM4fcCompile(t, map[string]string{
		"rootshape/I.java": `package rootshape; public interface I { static int run(int x){return x;} }`,
	}, "rootshape/I")["rootshape/I"]
	for _, tc := range []struct {
		name string
		edit func(uint16) uint16
		code uint64
	}{
		{"nonstatic", func(f uint16) uint16 { return f &^ accStatic }, 6},
		{"native", func(f uint16) uint16 { return f | accNative }, 7},
		{"synchronized", func(f uint16) uint16 { return f | verifyM4fcSynchronized }, 7},
		{"abstract", func(f uint16) uint16 { return f | verifyM4fcAbstract }, 7},
	} {
		t.Run(tc.name, func(t *testing.T) {
			bad := verifyM4fcMutateMethod(t, iface, "run", "(I)I", func(raw []byte, m staticsMethod) {
				binary.BigEndian.PutUint16(raw[m.accessOffset:], tc.edit(m.access))
			})
			verifyM4fcAssertCodeError(t, func() (Result, error) {
				return RunClasses([][]byte{bad}, "rootshape/I", "run", []int32{1}, verifyM4fcGasLimit)
			}, "MethodError(uint256)", tc.code)
		})
	}
}

// --- verifier-only helpers ---

func verifyM4fcCompile(t *testing.T, sources map[string]string, internalNames ...string) map[string][]byte {
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
		t.Fatalf("bounded javac --release 8 failed: %v\n%s", err, output)
	}
	classes := make(map[string][]byte, len(internalNames))
	for _, name := range internalNames {
		data, err := os.ReadFile(filepath.Join(dir, filepath.FromSlash(name+".class")))
		if err != nil {
			t.Fatalf("read %s: %v", name, err)
		}
		classes[name] = data
	}
	return classes
}

func verifyM4fcBundle(classes map[string][]byte) [][]byte {
	names := make([]string, 0, len(classes))
	for name := range classes {
		names = append(names, name)
	}
	sort.Strings(names)
	bundle := make([][]byte, len(names))
	for i, name := range names {
		bundle[i] = classes[name]
	}
	return bundle
}

func verifyM4fcJava8(t *testing.T) string {
	t.Helper()
	path := os.Getenv("JAVA_EVM_JAVA8")
	if path == "" {
		path = "/usr/lib/jvm/java-8-openjdk/bin/java"
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	output, err := exec.CommandContext(ctx, path, "-version").CombinedOutput()
	if err != nil {
		t.Fatalf("M4f-c binary-evolution oracle requires Java 8; JAVA_EVM_JAVA8=%q: %v\n%s", path, err, output)
	}
	if !regexp.MustCompile(`(?m)version "1\.8\.`).Match(output) {
		t.Fatalf("M4f-c oracle requires Java major 8; JAVA_EVM_JAVA8=%q reported:\n%s", path, output)
	}
	return path
}

func verifyM4fcJava8Outcome(t *testing.T, bundle [][]byte, mainClass, method string, args []int32, want string) {
	t.Helper()
	dir := t.TempDir()
	oracle := `public final class M4fcOracle {
		public static void main(String[] a) throws Exception {
			try {
				Class<?> c=Class.forName(a[0]); Class<?>[] p=new Class<?>[a.length-2]; Object[] v=new Object[a.length-2];
				for(int i=0;i<p.length;i++){p[i]=Integer.TYPE;v[i]=Integer.valueOf(a[i+2]);}
				Object x=c.getMethod(a[1],p).invoke(null,v); System.out.print("value="+x);
			} catch (java.lang.reflect.InvocationTargetException x) {
				System.out.print(x.getCause().getClass().getName());
			} catch (Throwable x) { System.out.print(x.getClass().getName()); }
		}
	}`
	oraclePath := filepath.Join(dir, "M4fcOracle.java")
	if err := os.WriteFile(oraclePath, []byte(oracle), 0600); err != nil {
		t.Fatal(err)
	}
	ctxCompile, cancelCompile := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancelCompile()
	if output, err := exec.CommandContext(ctxCompile, "javac", "-J-Xmx64m", "--release", "8", "-d", dir, oraclePath).CombinedOutput(); err != nil {
		t.Fatalf("compile trusted Java8 oracle: %v\n%s", err, output)
	}
	for _, classfile := range bundle {
		name := verifyM4fbClassName(t, classfile)
		path := filepath.Join(dir, filepath.FromSlash(name+".class"))
		if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, classfile, 0600); err != nil {
			t.Fatal(err)
		}
	}
	argv := []string{"-Xmx64m", "-cp", dir, "M4fcOracle", mainClass, method}
	for _, arg := range args {
		argv = append(argv, strconv.FormatInt(int64(arg), 10))
	}
	ctxRun, cancelRun := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancelRun()
	output, err := exec.CommandContext(ctxRun, verifyM4fcJava8(t), argv...).CombinedOutput()
	if err != nil {
		t.Fatalf("bounded Java8 oracle failed: %v\n%s", err, output)
	}
	if got := strings.TrimSpace(string(output)); got != want {
		t.Fatalf("Java8 %s.%s outcome=%q want %q", mainClass, method, got, want)
	}
	t.Logf("Java8 proved %s.%s => %s", mainClass, method, want)
}

func verifyM4fcMutateMethod(t *testing.T, original []byte, name, descriptor string, edit func([]byte, staticsMethod)) []byte {
	t.Helper()
	out := append([]byte(nil), original...)
	edit(out, parseStaticsClass(t, out).method(t, name, descriptor))
	return out
}

func verifyM4fcMemberInstruction(t *testing.T, c staticsClass, method staticsMethod, opcode, tag byte, name, descriptor string) (uint16, int) {
	t.Helper()
	return verifyM4faMemberInstruction(t, c, method, opcode, tag, name, descriptor)
}

func verifyM4fcRefOwner(t *testing.T, c staticsClass, ref uint16) string {
	t.Helper()
	e := c.entry(t, ref)
	owner := c.entry(t, c.u2(t, e.offset+1))
	if owner.tag != 7 {
		t.Fatalf("member ref CP%d owner tag=%d want Class", ref, owner.tag)
	}
	return c.utf8[c.u2(t, owner.offset+1)]
}

func verifyM4fcAssertValue(t *testing.T, run func() (Result, error), want int32) {
	t.Helper()
	result, err := run()
	if err != nil || result.ExceptionClass != "" || result.Value != want || result.GasUsed == 0 || len(result.RevertData) != 0 {
		t.Fatalf("result/error=%+v/%v want value %d", result, err, want)
	}
}

func verifyM4fcAssertException(t *testing.T, run func() (Result, error), want string, kind byte) {
	t.Helper()
	result, err := run()
	selector := crypto.Keccak256([]byte("JavaException(uint256)"))[:4]
	if err != nil || result.ExceptionClass != want || result.GasUsed == 0 || len(result.RevertData) != 36 || !bytes.Equal(result.RevertData[:4], selector) || !bytes.Equal(result.RevertData[4:35], make([]byte, 31)) || result.RevertData[35] != kind {
		t.Fatalf("result/error=%+v/%v data=%x want %s kind %d", result, err, result.RevertData, want, kind)
	}
}

func verifyM4fcAssertError(t *testing.T, run func() (Result, error), signature string, code, location uint64) {
	t.Helper()
	result, err := run()
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error=%+v/%v want %s(%d,%d)", result, err, signature, code, location)
	}
	selector := crypto.Keccak256([]byte(signature))[:4]
	if result.ExceptionClass != "" || result.GasUsed == 0 || len(result.RevertData) != 68 || !bytes.Equal(result.RevertData[:4], selector) {
		t.Fatalf("result=%+v data=%x want exact %s", result, result.RevertData, signature)
	}
	if got := verifyM4fcUint256(t, result.RevertData[4:36]); got != code {
		t.Fatalf("%s code=%d want %d", signature, got, code)
	}
	if got := verifyM4fcUint256(t, result.RevertData[36:68]); got != location {
		t.Fatalf("%s location=%d want %d", signature, got, location)
	}
}

func verifyM4fcAssertCodeError(t *testing.T, run func() (Result, error), signature string, code uint64) {
	t.Helper()
	result, err := run()
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error=%+v/%v want %s(%d)", result, err, signature, code)
	}
	selector := crypto.Keccak256([]byte(signature))[:4]
	if result.ExceptionClass != "" || result.GasUsed == 0 || len(result.RevertData) != 36 || !bytes.Equal(result.RevertData[:4], selector) || verifyM4fcUint256(t, result.RevertData[4:]) != code {
		t.Fatalf("result=%+v data=%x want exact %s(%d)", result, result.RevertData, signature, code)
	}
}

func verifyM4fcUint256(t *testing.T, word []byte) uint64 {
	t.Helper()
	if len(word) != 32 || !bytes.Equal(word[:24], make([]byte, 24)) {
		t.Fatalf("noncanonical uint256 %x", word)
	}
	return binary.BigEndian.Uint64(word[24:])
}
