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
	"strings"
	"testing"
	"time"

	"github.com/ethereum/go-ethereum/core/vm"
	"github.com/ethereum/go-ethereum/crypto"
)

const (
	verifyM4fbGasLimit      = uint64(100_000_000)
	verifyM4fbInvokespecial = byte(0xb7)
	verifyM4fbInvokestatic  = byte(0xb8)
	verifyM4fbGetstatic     = byte(0xb2)
	verifyM4fbAbstract      = uint16(0x0400)
	verifyM4fbSynthetic     = uint16(0x1000)
	verifyM4fbBridge        = uint16(0x0040)
	verifyM4fbSynchronized  = uint16(0x0020)
)

// Every source below is a bounded, trusted Java 8 probe. Binary-evolution tests
// compile old and new source trees separately, then pass selected classfiles
// unchanged to both the Java 8 oracle and RunClasses.

func TestVerifyM4fbDefaultMaximaClassWinsBridgesAndOpcodeCaches(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"defaults/Box.java": `package defaults; public final class Box { public int value; }`,
		"defaults/P.java": `package defaults; public interface P {
			default int f(int x){return x+1;} default void put(Box b,int x){b.value=b.value+x;}
			default P self(){return this;}
		}`,
		"defaults/Q.java":         `package defaults; public interface Q extends P { default int f(int x){return x+10;} }`,
		"defaults/Base.java":      `package defaults; public class Base implements P { }`,
		"defaults/Sub.java":       `package defaults; public final class Sub extends Base implements Q { }`,
		"defaults/Winner.java":    `package defaults; public final class Winner extends Base implements Q { public int f(int x){return x+100;} }`,
		"defaults/Covariant.java": `package defaults; public interface Covariant extends P { default Covariant self(){return this;} }`,
		"defaults/CovImpl.java":   `package defaults; public final class CovImpl implements Covariant { }`,
		"defaults/Root.java": `package defaults; public final class Root {
			static int viaP(P p,int x){return p.f(x);} static int viaBase(Base p,int x){return p.f(x);}
			public static int run(int x){P a=new Base(),b=new Sub(),c=new Winner();Box box=new Box();
				a.put(box,3);b.put(box,4);Covariant cv=new CovImpl();
				return viaP(a,x)*100000+viaP(b,x)*1000+viaP(c,x)*10+viaBase(new Base(),x)
					+viaBase(new Sub(),x)*10000000+(a.self()==a?1:0)+(cv.self()==cv?2:0)+box.value;}
		}`,
	}, "defaults/Box", "defaults/P", "defaults/Q", "defaults/Base", "defaults/Sub", "defaults/Winner", "defaults/Covariant", "defaults/CovImpl", "defaults/Root")

	bridge := parseStaticsClass(t, classes["defaults/Covariant"])
	found := false
	for _, method := range bridge.methods {
		if method.name == "self" && method.descriptor == "()Ldefaults/P;" {
			found = method.access&(verifyM4fbSynthetic|verifyM4fbBridge) == verifyM4fbSynthetic|verifyM4fbBridge && len(method.code) != 0
		}
	}
	if !found {
		t.Fatal("javac did not emit the expected concrete synthetic interface bridge")
	}
	verifyM4fbAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4faBundle(classes), "defaults/Root", "run", []int32{2}, verifyM4fbGasLimit)
	}, 120313033)
}

func TestVerifyM4fbInterfaceSuperDirectCallsAndReturnShapes(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"supercall/Box.java": `package supercall; public final class Box { int value; }`,
		"supercall/P.java": `package supercall; public interface P {
			default int f(int x){return x+1;} default void put(Box b,int x){b.value=b.value+x;}
			default Box pass(Box b){return b;}
		}`,
		"supercall/Q.java": `package supercall; public interface Q extends P {
			default int f(int x){return P.super.f(x)+10;}
		}`,
		"supercall/C.java": `package supercall; public final class C implements Q {
			int direct(int x){Box b=new Box();Q.super.put(b,3);return Q.super.f(x)*100+b.value+(Q.super.pass(b)==b?1:0);}
		}`,
		"supercall/Root.java": `package supercall; public final class Root { public static int run(int x){return new C().direct(x);} }`,
	}, "supercall/Box", "supercall/P", "supercall/Q", "supercall/C", "supercall/Root")
	c := parseStaticsClass(t, classes["supercall/C"])
	for _, shape := range []struct{ name, descriptor string }{{"f", "(I)I"}, {"put", "(Lsupercall/Box;I)V"}, {"pass", "(Lsupercall/Box;)Lsupercall/Box;"}} {
		verifyM4fbMemberInstruction(t, c, c.method(t, "direct", "(I)I"), verifyM4fbInvokespecial, 11, shape.name, shape.descriptor)
	}
	q := parseStaticsClass(t, classes["supercall/Q"])
	verifyM4fbMemberInstruction(t, q, q.method(t, "f", "(I)I"), verifyM4fbInvokespecial, 11, "f", "(I)I")
	verifyM4fbAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4faBundle(classes), "supercall/Root", "run", []int32{2}, verifyM4fbGasLimit)
	}, 1304)
}

func TestVerifyM4fbMandatoryInterfaceInitializationPostorderDedupAndOmission(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"initorder/Tracker.java": `package initorder; public final class Tracker { public static int value; public static int mark(int x){value=value*10+x;return x;} }`,
		"initorder/A.java":       `package initorder; public interface A { int XA=Tracker.mark(1); default int a(){return 1;} }`,
		"initorder/N.java":       `package initorder; public interface N { int XN=Tracker.mark(2); int n(); }`,
		"initorder/B.java":       `package initorder; public interface B extends A,N { int XB=Tracker.mark(3); default int b(){return 3;} }`,
		"initorder/D.java":       `package initorder; public interface D extends A { int XD=Tracker.mark(4); default int d(){return 4;} }`,
		"initorder/E.java":       `package initorder; public interface E extends B,D { int XE=Tracker.mark(6); }`,
		"initorder/C.java":       `package initorder; public final class C implements E { static int XC=Tracker.mark(5); public int n(){return 2;} }`,
		"initorder/Root.java":    `package initorder; public final class Root { public static int run(){new C();return Tracker.value;} }`,
	}, "initorder/Tracker", "initorder/A", "initorder/N", "initorder/B", "initorder/D", "initorder/E", "initorder/C", "initorder/Root")
	verifyM4fbAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4faBundle(classes), "initorder/Root", "run", nil, verifyM4fbGasLimit)
	}, 1345)
}

func TestVerifyM4fbParentDefaultInitializesDespiteDescendantReabstractionAndClassWin(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"reabstractinit/Tracker.java": `package reabstractinit; public final class Tracker { public static int value; public static int mark(int x){value=value*10+x;return x;} }`,
		"reabstractinit/P.java":       `package reabstractinit; public interface P { int X=Tracker.mark(1); default int f(){return 1;} }`,
		"reabstractinit/Q.java":       `package reabstractinit; public interface Q extends P { int X=Tracker.mark(2); int f(); }`,
		"reabstractinit/C.java":       `package reabstractinit; public final class C implements Q { static int X=Tracker.mark(3); public int f(){return 7;} }`,
		"reabstractinit/Root.java":    `package reabstractinit; public final class Root { public static int run(){new C();return Tracker.value;} }`,
	}, "reabstractinit/Tracker", "reabstractinit/P", "reabstractinit/Q", "reabstractinit/C", "reabstractinit/Root")
	verifyM4fbAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4faBundle(classes), "reabstractinit/Root", "run", nil, verifyM4fbGasLimit)
	}, 13)
}

func TestVerifyM4fbSyntheticBridgeAloneMakesInterfaceInitializationMandatory(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"bridgeinit/Tracker.java": `package bridgeinit; public final class Tracker { public static int value; public static int mark(int x){value=value*10+x;return x;} }`,
		"bridgeinit/Box.java":     `package bridgeinit; public final class Box { }`,
		"bridgeinit/P.java":       `package bridgeinit; public interface P { default Object make(){return null;} }`,
		"bridgeinit/Q.java":       `package bridgeinit; public interface Q extends P { int X=Tracker.mark(9); Box make(); }`,
		"bridgeinit/C.java":       `package bridgeinit; public final class C implements Q { static int X=Tracker.mark(8); public Box make(){return new Box();} }`,
		"bridgeinit/Root.java":    `package bridgeinit; public final class Root { public static int run(){new C();return Tracker.value;} }`,
	}, "bridgeinit/Tracker", "bridgeinit/Box", "bridgeinit/P", "bridgeinit/Q", "bridgeinit/C", "bridgeinit/Root")
	q := parseStaticsClass(t, classes["bridgeinit/Q"])
	concrete := 0
	for _, method := range q.methods {
		if method.name == "make" && len(method.code) != 0 {
			concrete++
			if method.access&(verifyM4fbSynthetic|verifyM4fbBridge) != verifyM4fbSynthetic|verifyM4fbBridge {
				t.Fatalf("concrete Q.make flags=%x, want synthetic bridge", method.access)
			}
		}
	}
	if concrete != 1 {
		t.Fatalf("concrete Q.make count=%d, want only bridge", concrete)
	}
	verifyM4fbAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4faBundle(classes), "bridgeinit/Root", "run", nil, verifyM4fbGasLimit)
	}, 98)
}

func TestVerifyM4fbSuperclassFirstReentrantInitializationAndOwnInterfaceFields(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"initdeep/Tracker.java": `package initdeep; public final class Tracker { public static int value; public static int mark(int x){value=value*10+x;return x;} }`,
		"initdeep/Helper.java": `package initdeep; public final class Helper {
			public static int first(int x){Tracker.mark(x);C.touch();return x;}
			public static int next(int x){Tracker.mark(x);return x;}
		}`,
		"initdeep/SI.java":    `package initdeep; public interface SI { int X=Tracker.mark(6); default int s(){return 6;} }`,
		"initdeep/Super.java": `package initdeep; public class Super implements SI { static int X=Tracker.mark(7); }`,
		"initdeep/I.java": `package initdeep; public interface I {
			int A=Helper.first(1); int B=Helper.next(A+1); default int f(){return 1;}
		}`,
		"initdeep/C.java": `package initdeep; public final class C extends Super implements I {
			static int value=Helper.next(8); static int touch(){return value;}
		}`,
		"initdeep/Root.java": `package initdeep; public final class Root { public static int run(){new C();return Tracker.value;} }`,
	}, "initdeep/Tracker", "initdeep/Helper", "initdeep/SI", "initdeep/Super", "initdeep/I", "initdeep/C", "initdeep/Root")
	verifyM4fbAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4faBundle(classes), "initdeep/Root", "run", nil, verifyM4fbGasLimit)
	}, 67128)
}

func TestVerifyM4fbNonErrorInitializerFailureWrapsButErrorsAndOOGDoNot(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"initfail/Helper.java": `package initfail; public final class Helper { public static int zero(){return 0;} }`,
		"initfail/I.java":      `package initfail; public interface I { int X=1/Helper.zero(); default int f(){return 1;} }`,
		"initfail/C.java":      `package initfail; public final class C implements I { }`,
		"initfail/Root.java":   `package initfail; public final class Root { public static int run(){new C();return 1;} }`,
	}, "initfail/Helper", "initfail/I", "initfail/C", "initfail/Root")
	verifyM4fbAssertException(t, func() (Result, error) {
		return RunClasses(verifyM4faBundle(classes), "initfail/Root", "run", nil, verifyM4fbGasLimit)
	}, "java.lang.ExceptionInInitializerError", 3)
	result, err := RunClasses(verifyM4faBundle(classes), "initfail/Root", "run", nil, 1)
	if err == nil || !errors.Is(err, vm.ErrOutOfGas) || result.ExceptionClass != "" || len(result.RevertData) != 0 {
		t.Fatalf("result/error=%+v/%v, want unlabeled EVM OOG", result, err)
	}
}

func TestVerifyM4fbDefaultMethodShapeFlagsRemainExact(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"shape/I.java":    `package shape; public interface I { default int f(){return 1;} }`,
		"shape/C.java":    `package shape; public final class C implements I { }`,
		"shape/Root.java": `package shape; public final class Root { public static int run(){return new C().f();} }`,
	}, "shape/I", "shape/C", "shape/Root")
	iface := classes["shape/I"]
	for _, tc := range []struct {
		name string
		edit func(uint16) uint16
	}{
		{"private", func(f uint16) uint16 { return (f &^ accessMask) | accPrivate }},
		{"native", func(f uint16) uint16 { return f | accNative }},
		{"synchronized", func(f uint16) uint16 { return f | verifyM4fbSynchronized }},
		{"abstract-with-code", func(f uint16) uint16 { return f | verifyM4fbAbstract }},
	} {
		t.Run(tc.name, func(t *testing.T) {
			bad := verifyM4fbMutateMethod(t, iface, "f", "()I", func(raw []byte, method staticsMethod) {
				binary.BigEndian.PutUint16(raw[method.accessOffset:], tc.edit(method.access))
			})
			verifyM4fbAssertError(t, func() (Result, error) {
				return RunClasses([][]byte{bad, classes["shape/C"], classes["shape/Root"]}, "shape/Root", "run", nil, verifyM4fbGasLimit)
			}, "InterfaceError(uint256,uint256)", 4, 0)
		})
	}
	noCode := verifyM4fbMutateMethod(t, iface, "f", "()I", func(raw []byte, method staticsMethod) {
		binary.BigEndian.PutUint16(raw[method.codeNameOffset:], parseStaticsClass(t, raw).utfIndex(t, "SourceFile"))
	})
	verifyM4fbAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{noCode, classes["shape/C"], classes["shape/Root"]}, "shape/Root", "run", nil, verifyM4fbGasLimit)
	}, "InterfaceError(uint256,uint256)", 4, 0)
}

func TestVerifyM4fbInvokeinterfaceDefaultCPCountAndTrailingByteValidation(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"b9shape/I.java":    `package b9shape; public interface I { default int f(int x){return x+1;} }`,
		"b9shape/C.java":    `package b9shape; public final class C implements I { }`,
		"b9shape/Root.java": `package b9shape; public final class Root { static int call(I x,int n){return x.f(n);} public static int run(){return call(new C(),3);} }`,
	}, "b9shape/I", "b9shape/C", "b9shape/Root")
	root := classes["b9shape/Root"]
	parsed := parseStaticsClass(t, root)
	ref, pc := verifyM4fbMemberInstruction(t, parsed, parsed.method(t, "call", "(Lb9shape/I;I)I"), 0xb9, 11, "f", "(I)I")
	if got := parsed.method(t, "call", "(Lb9shape/I;I)I").code[pc+3 : pc+5]; !bytes.Equal(got, []byte{2, 0}) {
		t.Fatalf("invokeinterface suffix=%x want 0200", got)
	}
	for _, tc := range []struct {
		name string
		edit func([]byte, staticsClass)
	}{
		{"cp-zero", func(_ []byte, c staticsClass) {
			binary.BigEndian.PutUint16(c.method(t, "call", "(Lb9shape/I;I)I").code[pc+1:], 0)
		}},
		{"cp-range", func(_ []byte, c staticsClass) {
			binary.BigEndian.PutUint16(c.method(t, "call", "(Lb9shape/I;I)I").code[pc+1:], uint16(c.cpCount))
		}},
		{"cp-tag10", func(raw []byte, c staticsClass) { raw[c.entry(t, ref).offset] = 10 }},
		{"count-low", func(_ []byte, c staticsClass) { c.method(t, "call", "(Lb9shape/I;I)I").code[pc+3] = 1 }},
		{"count-high", func(_ []byte, c staticsClass) { c.method(t, "call", "(Lb9shape/I;I)I").code[pc+3] = 3 }},
		{"trailing", func(_ []byte, c staticsClass) { c.method(t, "call", "(Lb9shape/I;I)I").code[pc+4] = 1 }},
	} {
		t.Run(tc.name, func(t *testing.T) {
			bad := verifyM4faMutate(t, root, tc.edit)
			verifyM4fbAssertError(t, func() (Result, error) {
				return RunClasses([][]byte{classes["b9shape/I"], classes["b9shape/C"], bad}, "b9shape/Root", "run", nil, verifyM4fbGasLimit)
			}, "CallError(uint256,uint256)", 1, uint64(pc))
		})
	}
}

func TestVerifyM4fbInterfaceSuperCPDirectnessCallerReceiverAndBranchShape(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"special/I.java": `package special; public interface I { default int f(int x){return x+1;} }`,
		"special/J.java": `package special; public interface J extends I { default int f(int x){return x+2;} default void ping(){} }`,
		"special/C.java": `package special; public final class C implements J {
			int direct(int x){return J.super.f(x);} void directPing(){J.super.ping();} int other(C x){return x.f(3);}
			public static int run(){return new C().direct(3);} public static int runOther(){C a=new C(),b=new C();return a.other(b);}
			public static int padding(){int x=0;` + strings.Repeat("x++;", 30) + `return x;}
		}`,
	}, "special/I", "special/J", "special/C")
	original := classes["special/C"]
	parsed := parseStaticsClass(t, original)
	ref, pc := verifyM4fbMemberInstruction(t, parsed, parsed.method(t, "direct", "(I)I"), verifyM4fbInvokespecial, 11, "f", "(I)I")
	verifyM4fbAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4faBundle(classes), "special/C", "run", nil, verifyM4fbGasLimit)
	}, 5)

	for _, tc := range []struct {
		name     string
		make     func([]byte, staticsClass)
		wantSig  string
		wantCode uint64
	}{
		{"cp-zero", func(_ []byte, c staticsClass) {
			binary.BigEndian.PutUint16(c.method(t, "direct", "(I)I").code[pc+1:], 0)
		}, "CallError(uint256,uint256)", 1},
		{"cp-range", func(_ []byte, c staticsClass) {
			binary.BigEndian.PutUint16(c.method(t, "direct", "(I)I").code[pc+1:], uint16(c.cpCount))
		}, "CallError(uint256,uint256)", 1},
		// CP tag 10 is a structurally valid Methodref. Its interface owner makes
		// this a supported-tag but unsupported invokespecial form, not malformed CP.
		{"cp-tag10", func(raw []byte, c staticsClass) { raw[c.entry(t, ref).offset] = 10 }, "CallError(uint256,uint256)", 4},
	} {
		t.Run(tc.name, func(t *testing.T) {
			bad := verifyM4faMutate(t, original, tc.make)
			verifyM4fbAssertError(t, func() (Result, error) {
				return RunClasses([][]byte{classes["special/I"], classes["special/J"], bad}, "special/C", "run", nil, verifyM4fbGasLimit)
			}, tc.wantSig, tc.wantCode, uint64(pc))
		})
	}

	// javac does not otherwise need a Class entry for indirect parent I in C.
	// Append an exact Class/Utf8 pair so this mutation isolates directness rather
	// than failing in the test helper before the runtime is invoked.
	indirectBase, indirectOwner := verifyM4faAppendNameAndClass(t, original, "special/I")
	indirect := verifyM4faMutate(t, indirectBase, func(raw []byte, c staticsClass) {
		e := c.entry(t, ref)
		binary.BigEndian.PutUint16(raw[e.offset+1:], indirectOwner)
	})
	verifyM4fbAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["special/I"], classes["special/J"], indirect}, "special/C", "run", nil, verifyM4fbGasLimit)
	}, "CallError(uint256,uint256)", 4, uint64(pc))

	nonInterface := verifyM4faMutate(t, original, func(raw []byte, c staticsClass) {
		e := c.entry(t, ref)
		binary.BigEndian.PutUint16(raw[e.offset+1:], verifyM4faClassIndex(t, c, "special/C"))
	})
	verifyM4fbAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["special/I"], classes["special/J"], nonInterface}, "special/C", "run", nil, verifyM4fbGasLimit)
	}, "InterfaceError(uint256,uint256)", 1, uint64(pc))

	otherParsed := parseStaticsClass(t, original)
	_, otherPC := verifyM4fbMemberInstruction(t, otherParsed, otherParsed.method(t, "other", "(Lspecial/C;)I"), 0xb6, 10, "f", "(I)I")
	nonCurrent := verifyM4faMutate(t, original, func(_ []byte, c staticsClass) {
		m := c.method(t, "other", "(Lspecial/C;)I")
		m.code[otherPC] = verifyM4fbInvokespecial
		binary.BigEndian.PutUint16(m.code[otherPC+1:], ref)
	})
	verifyM4fbAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["special/I"], classes["special/J"], nonCurrent}, "special/C", "runOther", nil, verifyM4fbGasLimit)
	}, "CallError(uint256,uint256)", 4, uint64(otherPC))

	pingRef, _ := verifyM4fbMemberInstruction(t, parsed, parsed.method(t, "directPing", "()V"), verifyM4fbInvokespecial, 11, "ping", "()V")
	constructor := parsed.method(t, "<init>", "()V")
	_, constructorPC := verifyM4fbMemberInstruction(t, parsed, constructor, verifyM4fbInvokespecial, 10, "<init>", "()V")
	uninitializedThis := verifyM4faMutate(t, original, func(_ []byte, c staticsClass) {
		binary.BigEndian.PutUint16(c.method(t, "<init>", "()V").code[constructorPC+1:], pingRef)
	})
	verifyM4fbAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["special/I"], classes["special/J"], uninitializedThis}, "special/C", "run", nil, verifyM4fbGasLimit)
	}, "BytecodeError(uint256,uint256)", 14, uint64(constructorPC))

	staticCallerCode := []byte{0x01, 0x06, verifyM4fbInvokespecial, byte(ref >> 8), byte(ref), 0xac}
	staticCaller := verifyM4faRewriteCode(t, original, "padding", "()I", staticCallerCode, 8, 1)
	verifyM4fbAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["special/I"], classes["special/J"], staticCaller}, "special/C", "padding", nil, verifyM4fbGasLimit)
	}, "CallError(uint256,uint256)", 4, 2)

	for operands := 0; operands <= 1; operands++ {
		t.Run(fmt.Sprintf("truncated-%d", operands), func(t *testing.T) {
			ending := append([]byte{verifyM4fbInvokespecial}, make([]byte, operands)...)
			bad := verifyM4faRewriteAtEnd(t, original, "padding", "()I", ending)
			truncatedPC := len(parseStaticsClass(t, bad).method(t, "padding", "()I").code) - len(ending)
			verifyM4fbAssertError(t, func() (Result, error) {
				return RunClasses([][]byte{classes["special/I"], classes["special/J"], bad}, "special/C", "padding", nil, verifyM4fbGasLimit)
			}, "BytecodeError(uint256,uint256)", 2, uint64(truncatedPC))
		})
	}
	for operand := 1; operand <= 2; operand++ {
		t.Run(fmt.Sprintf("branch-operand-%d", operand), func(t *testing.T) {
			invokePC := 5
			target := invokePC + operand
			offset := target - 1
			code := []byte{0x03, 0x99, byte(offset >> 8), byte(offset), 0x01, verifyM4fbInvokespecial, byte(ref >> 8), byte(ref), 0x03, 0xac}
			bad := verifyM4faRewriteCode(t, original, "padding", "()I", code, 8, 1)
			verifyM4fbAssertError(t, func() (Result, error) {
				return RunClasses([][]byte{classes["special/I"], classes["special/J"], bad}, "special/C", "padding", nil, verifyM4fbGasLimit)
			}, "BytecodeError(uint256,uint256)", 12, 1)
		})
	}
}

func TestVerifyM4fcInterfaceStaticsAndFieldsReplaceOnlyObsoleteGuards(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"retained/I.java":    `package retained; public interface I { int X=init(); static int init(){return 7;} static int call(){return X;} default int f(){return 1;} }`,
		"retained/C.java":    `package retained; public final class C implements I { }`,
		"retained/Root.java": `package retained; public final class Root { public static int call(){return I.call();} public static int field(){return I.X;} public static int run(){return new C().f();} }`,
	}, "retained/I", "retained/C", "retained/Root")
	root := classes["retained/Root"]
	parsed := parseStaticsClass(t, root)
	staticRef, staticPC := verifyM4fbMemberInstruction(t, parsed, parsed.namedMethod(t, "call"), verifyM4fbInvokestatic, 11, "call", "()I")
	verifyM4fbAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4faBundle(classes), "retained/Root", "call", nil, verifyM4fbGasLimit)
	}, 7)
	forged := verifyM4faMutate(t, root, func(raw []byte, c staticsClass) { raw[c.entry(t, staticRef).offset] = 10 })
	verifyM4fbAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["retained/I"], forged}, "retained/Root", "call", nil, verifyM4fbGasLimit)
	}, "CallError(uint256,uint256)", 4, uint64(staticPC))
	verifyM4faFieldInstruction(t, parsed, parsed.namedMethod(t, "field"), verifyM4fbGetstatic, "X", "I")
	verifyM4fbAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4faBundle(classes), "retained/Root", "field", nil, verifyM4fbGasLimit)
	}, 7)
	verifyM4fbAssertCodeError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["retained/I"]}, "retained/I", "f", nil, verifyM4fbGasLimit)
	}, "MethodError(uint256)", 6)
	verifyM4fbAssertCodeError(t, func() (Result, error) {
		return Run(classes["retained/I"], "f", nil, verifyM4fbGasLimit)
	}, "MethodError(uint256)", 6)
}

func TestVerifyM4fbJava8BinaryEvolutionConflictAndAllocationTiming(t *testing.T) {
	old := verifyM4fbCompileVersion(t, map[string]string{
		"evo/A.java":    `package evo; public interface A { default int f(){return 1;} }`,
		"evo/B.java":    `package evo; public interface B extends A { }`,
		"evo/C.java":    `package evo; public final class C implements A,B { }`,
		"evo/Root.java": `package evo; public final class Root { static int call(A x){return x.f();} public static int run(){return call(new C());} public static int allocate(){new C();return 7;} }`,
	}, "evo/A", "evo/B", "evo/C", "evo/Root")
	newVersion := verifyM4fbCompileVersion(t, map[string]string{
		"evo/B.java": `package evo; public interface B { default int f(){return 2;} }`,
	}, "evo/B")
	bundle := [][]byte{old["evo/A"], newVersion["evo/B"], old["evo/C"], old["evo/Root"]}
	verifyM4fbJava8Outcome(t, bundle, "evo.Root", "run", "java.lang.IncompatibleClassChangeError")
	verifyM4fbAssertException(t, func() (Result, error) { return RunClasses(bundle, "evo/Root", "run", nil, verifyM4fbGasLimit) }, "java.lang.IncompatibleClassChangeError", 10)
	verifyM4fbJava8Outcome(t, bundle, "evo.Root", "allocate", "value=7")
	verifyM4fbAssertValue(t, func() (Result, error) { return RunClasses(bundle, "evo/Root", "allocate", nil, verifyM4fbGasLimit) }, 7)
}

func TestVerifyM4fbJava8UniqueConcreteMaximumWithUnrelatedAbstractMaximum(t *testing.T) {
	old := verifyM4fbCompileVersion(t, map[string]string{
		"unique/A.java":    `package unique; public interface A { default int f(){return 7;} }`,
		"unique/B.java":    `package unique; public interface B { }`,
		"unique/C.java":    `package unique; public final class C implements A,B { }`,
		"unique/Root.java": `package unique; public final class Root { static int call(A x){return x.f();} public static int run(){return call(new C());} }`,
	}, "unique/A", "unique/B", "unique/C", "unique/Root")
	newVersion := verifyM4fbCompileVersion(t, map[string]string{
		"unique/B.java": `package unique; public interface B { int f(); }`,
	}, "unique/B")
	bundle := [][]byte{old["unique/A"], newVersion["unique/B"], old["unique/C"], old["unique/Root"]}
	verifyM4fbJava8Outcome(t, bundle, "unique.Root", "run", "value=7")
	verifyM4fbAssertValue(t, func() (Result, error) { return RunClasses(bundle, "unique/Root", "run", nil, verifyM4fbGasLimit) }, 7)
}

func TestVerifyM4fbJava8AbstractClassDeclarationSuppressesDefault(t *testing.T) {
	old := verifyM4fbCompileVersion(t, map[string]string{
		"classabstract/I.java":    `package classabstract; public interface I { default int f(){return 1;} }`,
		"classabstract/Base.java": `package classabstract; public class Base implements I { public int f(){return 2;} }`,
		"classabstract/C.java":    `package classabstract; public final class C extends Base { }`,
		"classabstract/Root.java": `package classabstract; public final class Root { static int call(I x){return x.f();} public static int run(){return call(new C());} }`,
	}, "classabstract/I", "classabstract/Base", "classabstract/C", "classabstract/Root")
	newVersion := verifyM4fbCompileVersion(t, map[string]string{
		"classabstract/I.java":    `package classabstract; public interface I { default int f(){return 1;} }`,
		"classabstract/Base.java": `package classabstract; public abstract class Base implements I { public abstract int f(); }`,
	}, "classabstract/Base")
	bundle := [][]byte{old["classabstract/I"], newVersion["classabstract/Base"], old["classabstract/C"], old["classabstract/Root"]}
	verifyM4fbJava8Outcome(t, bundle, "classabstract.Root", "run", "java.lang.AbstractMethodError")
	verifyM4fbAssertException(t, func() (Result, error) {
		return RunClasses(bundle, "classabstract/Root", "run", nil, verifyM4fbGasLimit)
	}, "java.lang.AbstractMethodError", 11)
}

func TestVerifyM4fbJava8BinaryEvolutionRemovedImplementationAndAbstractSuppression(t *testing.T) {
	old := verifyM4fbCompileVersion(t, map[string]string{
		"removed/P.java":    `package removed; public interface P { default int f(){return 1;} }`,
		"removed/I.java":    `package removed; public interface I extends P { }`,
		"removed/C.java":    `package removed; public final class C implements I { }`,
		"removed/Root.java": `package removed; public final class Root { static int call(P x){return x.f();} public static int run(){return call(new C());} }`,
	}, "removed/P", "removed/I", "removed/C", "removed/Root")
	newVersion := verifyM4fbCompileVersion(t, map[string]string{
		"removed/P.java": `package removed; public interface P { default int f(){return 1;} }`,
		"removed/I.java": `package removed; public interface I extends P { int f(); }`,
	}, "removed/I")
	bundle := [][]byte{old["removed/P"], newVersion["removed/I"], old["removed/C"], old["removed/Root"]}
	verifyM4fbJava8Outcome(t, bundle, "removed.Root", "run", "java.lang.AbstractMethodError")
	verifyM4fbAssertException(t, func() (Result, error) { return RunClasses(bundle, "removed/Root", "run", nil, verifyM4fbGasLimit) }, "java.lang.AbstractMethodError", 11)
}

func TestVerifyM4fbJava8InitializerLinkageErrorsStayUnwrapped(t *testing.T) {
	for _, tc := range []struct {
		name, replacement, want string
		kind                    byte
	}{
		{"icce", `package initerror; public interface B { default int f(){return 2;} }`, "java.lang.IncompatibleClassChangeError", 10},
		{"ame", `package initerror; public interface B extends A { int f(); }`, "java.lang.AbstractMethodError", 11},
	} {
		t.Run(tc.name, func(t *testing.T) {
			old := verifyM4fbCompileVersion(t, map[string]string{
				"initerror/A.java":        `package initerror; public interface A { default int f(){return 1;} }`,
				"initerror/B.java":        `package initerror; public interface B extends A { }`,
				"initerror/Conflict.java": `package initerror; public final class Conflict implements A,B { }`,
				"initerror/Helper.java":   `package initerror; public final class Helper { static int call(A x){return x.f();} public static int trigger(){return call(new Conflict());} }`,
				"initerror/Trigger.java":  `package initerror; public interface Trigger { int X=Helper.trigger(); default int value(){return 1;} }`,
				"initerror/Target.java":   `package initerror; public final class Target implements Trigger { }`,
				"initerror/Root.java":     `package initerror; public final class Root { public static int run(){new Target();return 1;} }`,
			}, "initerror/A", "initerror/B", "initerror/Conflict", "initerror/Helper", "initerror/Trigger", "initerror/Target", "initerror/Root")
			newVersion := verifyM4fbCompileVersion(t, map[string]string{
				"initerror/A.java": `package initerror; public interface A { default int f(){return 1;} }`,
				"initerror/B.java": tc.replacement,
			}, "initerror/B")
			bundle := [][]byte{old["initerror/A"], newVersion["initerror/B"], old["initerror/Conflict"], old["initerror/Helper"], old["initerror/Trigger"], old["initerror/Target"], old["initerror/Root"]}
			verifyM4fbJava8Outcome(t, bundle, "initerror.Root", "run", tc.want)
			verifyM4fbAssertException(t, func() (Result, error) { return RunClasses(bundle, "initerror/Root", "run", nil, verifyM4fbGasLimit) }, tc.want, tc.kind)
		})
	}
}

func TestVerifyM4fcAncestorInitializerCanReadExternalInterfaceField(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"fieldguard/Tracker.java": `package fieldguard; public final class Tracker { public static int mark(){return 7;} }`,
		"fieldguard/Helper.java":  `package fieldguard; public final class Helper { public static int read(){return Child.Y;} }`,
		"fieldguard/Parent.java":  `package fieldguard; public interface Parent { int X=Helper.read(); default int f(){return 1;} }`,
		"fieldguard/Child.java":   `package fieldguard; public interface Child extends Parent { int Y=Tracker.mark(); default int g(){return 2;} }`,
		"fieldguard/C.java":       `package fieldguard; public final class C implements Child { }`,
		"fieldguard/Root.java":    `package fieldguard; public final class Root { public static int run(){new C();return 1;} }`,
	}, "fieldguard/Tracker", "fieldguard/Helper", "fieldguard/Parent", "fieldguard/Child", "fieldguard/C", "fieldguard/Root")
	helper := parseStaticsClass(t, classes["fieldguard/Helper"])
	verifyM4faFieldInstruction(t, helper, helper.namedMethod(t, "read"), verifyM4fbGetstatic, "Y", "I")
	verifyM4fbAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4faBundle(classes), "fieldguard/Root", "run", nil, verifyM4fbGasLimit)
	}, 1)
}

func TestVerifyM4fbExactDecoderRejectsUnknownAndOOG(t *testing.T) {
	known := []string{
		"java.lang.ArithmeticException", "java.lang.StackOverflowError",
		"java.lang.ExceptionInInitializerError", "java.lang.NegativeArraySizeException",
		"java.lang.ArrayIndexOutOfBoundsException", "java.lang.NullPointerException",
		"java.lang.OutOfMemoryError", "java.lang.ClassCastException",
		"java.lang.ArrayStoreException", "java.lang.IncompatibleClassChangeError",
		"java.lang.AbstractMethodError",
	}
	for index, want := range known {
		payload := append(append([]byte(nil), javaExceptionSelector...), make([]byte, 32)...)
		payload[len(payload)-1] = byte(index + 1)
		if got, ok := decodeJavaException(payload); !ok || got != want {
			t.Fatalf("kind %d decoded as %q/%v, want %q/true", index+1, got, ok, want)
		}
	}
	for name, payload := range map[string][]byte{
		"unknown-12": append(append([]byte(nil), javaExceptionSelector...), append(make([]byte, 31), 12)...),
		"short":      append(append([]byte(nil), javaExceptionSelector...), make([]byte, 31)...),
		"noncanonical": func() []byte {
			p := append(append([]byte(nil), javaExceptionSelector...), make([]byte, 32)...)
			p[4], p[len(p)-1] = 1, 10
			return p
		}(),
	} {
		if got, ok := decodeJavaException(payload); ok || got != "" {
			t.Fatalf("%s decoded as %q/%v, want rejection", name, got, ok)
		}
	}
	classfile := compileJava(t, "M4fbOOG", `public final class M4fbOOG { public static int run(){return 1;} }`)
	result, err := Run(classfile, "run", nil, 1)
	if err == nil || !errors.Is(err, vm.ErrOutOfGas) || result.ExceptionClass != "" || len(result.RevertData) != 0 {
		t.Fatalf("result/error=%+v/%v, want unlabeled OOG", result, err)
	}
}

// --- verifier-only helpers ---

func verifyM4fbMutateMethod(t *testing.T, original []byte, name, descriptor string, edit func([]byte, staticsMethod)) []byte {
	t.Helper()
	out := append([]byte(nil), original...)
	edit(out, parseStaticsClass(t, out).method(t, name, descriptor))
	return out
}

func verifyM4fbMemberInstruction(t *testing.T, c staticsClass, method staticsMethod, opcode, tag byte, name, descriptor string) (uint16, int) {
	t.Helper()
	return verifyM4faMemberInstruction(t, c, method, opcode, tag, name, descriptor)
}

func verifyM4fbAssertValue(t *testing.T, run func() (Result, error), want int32) {
	t.Helper()
	result, err := run()
	if err != nil || result.ExceptionClass != "" || result.Value != want || result.GasUsed == 0 || len(result.RevertData) != 0 {
		t.Fatalf("result/error=%+v/%v, want value %d", result, err, want)
	}
}

func verifyM4fbAssertException(t *testing.T, run func() (Result, error), want string, kind byte) {
	t.Helper()
	result, err := run()
	selector := crypto.Keccak256([]byte("JavaException(uint256)"))[:4]
	if err != nil || result.ExceptionClass != want || result.GasUsed == 0 || len(result.RevertData) != 36 || !bytes.Equal(result.RevertData[:4], selector) || !bytes.Equal(result.RevertData[4:35], make([]byte, 31)) || result.RevertData[35] != kind {
		t.Fatalf("result/error=%+v/%v data=%x, want %s kind %d", result, err, result.RevertData, want, kind)
	}
}

func verifyM4fbAssertError(t *testing.T, run func() (Result, error), signature string, code, location uint64) {
	t.Helper()
	result, err := run()
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error=%+v/%v, want %s(%d,%d)", result, err, signature, code, location)
	}
	selector := crypto.Keccak256([]byte(signature))[:4]
	if result.ExceptionClass != "" || result.GasUsed == 0 || len(result.RevertData) != 68 || !bytes.Equal(result.RevertData[:4], selector) {
		t.Fatalf("result=%+v data=%x, want exact %s", result, result.RevertData, signature)
	}
	if got := binary.BigEndian.Uint64(result.RevertData[28:36]); got != code {
		t.Fatalf("%s code=%d want %d", signature, got, code)
	}
	if got := binary.BigEndian.Uint64(result.RevertData[60:68]); got != location {
		t.Fatalf("%s location=%d want %d", signature, got, location)
	}
}

func verifyM4fbAssertCodeError(t *testing.T, run func() (Result, error), signature string, code uint64) {
	t.Helper()
	result, err := run()
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error=%+v/%v, want %s(%d)", result, err, signature, code)
	}
	selector := crypto.Keccak256([]byte(signature))[:4]
	if result.ExceptionClass != "" || result.GasUsed == 0 || len(result.RevertData) != 36 || !bytes.Equal(result.RevertData[:4], selector) {
		t.Fatalf("result=%+v data=%x, want exact %s", result, result.RevertData, signature)
	}
	if got := binary.BigEndian.Uint64(result.RevertData[28:36]); got != code {
		t.Fatalf("%s code=%d want %d", signature, got, code)
	}
}

func verifyM4fbCompileVersion(t *testing.T, sources map[string]string, internalNames ...string) map[string][]byte {
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

func verifyM4fbJava8(t *testing.T) string {
	t.Helper()
	path := os.Getenv("JAVA_EVM_JAVA8")
	if path == "" {
		path = "/usr/lib/jvm/java-8-openjdk/bin/java"
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	output, err := exec.CommandContext(ctx, path, "-version").CombinedOutput()
	if err != nil {
		t.Fatalf("M4f-b binary-evolution oracle requires Java 8; JAVA_EVM_JAVA8=%q: %v\n%s", path, err, output)
	}
	if !regexp.MustCompile(`(?m)version "1\.8\.`).Match(output) {
		t.Fatalf("M4f-b binary-evolution oracle requires Java major 8; JAVA_EVM_JAVA8=%q reported:\n%s", path, output)
	}
	t.Logf("binary-evolution oracle: %s: %s", path, strings.Split(strings.TrimSpace(string(output)), "\n")[0])
	return path
}

func verifyM4fbJava8Outcome(t *testing.T, bundle [][]byte, mainClass, method, want string) {
	t.Helper()
	java8 := verifyM4fbJava8(t)
	dir := t.TempDir()
	oracle := `public final class M4fbOracle {
		public static void main(String[] args) throws Exception {
			try { Class<?> c=Class.forName(args[0]); java.lang.reflect.Method m=c.getMethod(args[1]);
				Object v=m.invoke(null); System.out.print("value="+v);
			} catch (java.lang.reflect.InvocationTargetException x) {
				System.out.print(x.getCause().getClass().getName());
			} catch (Throwable x) { System.out.print(x.getClass().getName()); }
		}
	}`
	oraclePath := filepath.Join(dir, "M4fbOracle.java")
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
	ctxRun, cancelRun := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancelRun()
	output, err := exec.CommandContext(ctxRun, java8, "-Xmx64m", "-cp", dir, "M4fbOracle", mainClass, method).CombinedOutput()
	if err != nil {
		t.Fatalf("bounded Java8 binary-evolution oracle failed: %v\n%s", err, output)
	}
	if got := strings.TrimSpace(string(output)); got != want {
		t.Fatalf("Java8 %s.%s outcome=%q want %q", mainClass, method, got, want)
	}
}

func verifyM4fbClassName(t *testing.T, classfile []byte) string {
	t.Helper()
	c := parseStaticsClass(t, classfile)
	e := c.entry(t, c.thisClass)
	if e.tag != 7 {
		t.Fatalf("this_class tag=%d", e.tag)
	}
	return c.utf8[c.u2(t, e.offset+1)]
}
