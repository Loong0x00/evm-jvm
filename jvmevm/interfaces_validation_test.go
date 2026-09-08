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
	"sort"
	"strings"
	"testing"
	"time"

	"github.com/ethereum/go-ethereum/core/vm"
	"github.com/ethereum/go-ethereum/crypto"
)

const (
	verifyM4faGasLimit        = uint64(100_000_000)
	verifyM4faInvokevirtual   = byte(0xb6)
	verifyM4faInvokestatic    = byte(0xb8)
	verifyM4faInvokeinterface = byte(0xb9)
	verifyM4faAnewarray       = byte(0xbd)
	verifyM4faCheckcast       = byte(0xc0)
	verifyM4faMultianewarray  = byte(0xc5)
	verifyM4faAbstract        = uint16(0x0400)
	verifyM4faInterface       = uint16(0x0200)
	verifyM4faSynchronized    = uint16(0x0020)
)

// All sources in this file are bounded, trusted Java 8 test programs. Narrow
// mutations isolate classfile graph and instruction faults which javac cannot
// emit. Production execution still receives only raw bytes and entry metadata.

func TestVerifyM4faInterfaceGraphDispatchAndActualJVMArithmetic(t *testing.T) {
	classes := verifyM4faCompileWithOracle(t, map[string]string{
		"graph/I.java":   `package graph; public interface I { int f(int x); void put(Box b,int x); I self(); }`,
		"graph/J.java":   `package graph; public interface J extends I { int f(int x); }`,
		"graph/K.java":   `package graph; public interface K extends I { int f(int x); }`,
		"graph/D.java":   `package graph; public interface D extends J,K { }`,
		"graph/Box.java": `package graph; public final class Box { public int value; }`,
		"graph/Base.java": `package graph; public class Base {
			public int f(int x){return x+1;} public void put(Box b,int x){b.value=b.value+x;} public I self(){return (I)this;}
		}`,
		"graph/Left.java": `package graph; public class Left extends Base implements D { }`,
		"graph/Sub.java":  `package graph; public final class Sub extends Left { }`,
		"graph/Right.java": `package graph; public final class Right implements D {
			public int f(int x){return x+10;} public void put(Box b,int x){b.value=b.value+x*2;} public I self(){return this;}
		}`,
		"graph/Root.java": `package graph; public final class Root {
			static int atOneSite(D v,int x){return v.f(x);} static int recurse(I v,int n){return n==0?0:v.f(n)+recurse(v,n-1);}
			public static int run(int x){D a=new Sub();D b=new Right();Box box=new Box();a.put(box,2);b.put(box,3);
				return atOneSite(a,x)*10000+atOneSite(b,x)*100+recurse(a,2)*10+box.value+(a.self()==a?1:0);}
			public static void main(String[] x){System.out.print(run(2));}
		}`,
	}, "graph.Root", "31259", "graph/I", "graph/J", "graph/K", "graph/D", "graph/Box", "graph/Base", "graph/Left", "graph/Sub", "graph/Right", "graph/Root")
	root := parseStaticsClass(t, classes["graph/Root"])
	ref, _ := verifyM4faMemberInstruction(t, root, root.namedMethod(t, "atOneSite"), verifyM4faInvokeinterface, 11, "f", "(I)I")
	owner := root.entry(t, root.u2(t, root.entry(t, ref).offset+1))
	if got := root.utf8[root.u2(t, owner.offset+1)]; got != "graph/D" {
		t.Fatalf("maximally-specific probe symbolic owner=%q, want graph/D", got)
	}
	verifyM4faAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4faBundle(classes), "graph/Root", "run", []int32{2}, verifyM4faGasLimit)
	}, 31259)
}

func TestVerifyM4faInterfaceReferenceArraysMarkersCastsAndStores(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"types/I.java":      `package types; public interface I { int value(); }`,
		"types/J.java":      `package types; public interface J extends I { }`,
		"types/Child.java":  `package types; public final class Child implements J { public int value(){return 7;} }`,
		"types/Other.java":  `package types; public final class Other { }`,
		"types/Holder.java": `package types; public final class Holder { I field; static I pass(I x){return x;} int call(){return field.value();} }`,
		"types/Root.java": `package types; public final class Root {
			public static int run(){Child c=new Child();I i=c;I[] a=new Child[2];a[0]=c;I[][] m=new Child[1][2];
				Holder h=new Holder();h.field=Holder.pass(i);Object ints=new int[1];Cloneable[] rows=new int[1][];
				return h.call()*1000+(a instanceof I[]?100:0)+(m instanceof I[][]?40:0)
					+(ints instanceof Cloneable?10:0)+(ints instanceof java.io.Serializable?5:0)
					+(rows instanceof Cloneable[]?2:0)+(new Object[1] instanceof Cloneable[]?0:1);}
			public static int arbitrary(){return ((Object)new int[1]) instanceof I?1:0;}
			public static int castBad(){Object x=new Other();return ((I)x).value();}
			public static int storeBad(){Object[] x=new I[1];x[0]=new Other();return 1;}
			public static int nulls(){Object x=null;return ((I)x)==null && !(x instanceof I)?1:0;}
		}`,
	}, "types/I", "types/J", "types/Child", "types/Other", "types/Holder", "types/Root")
	bundle := verifyM4faBundle(classes)
	verifyM4faAssertValue(t, func() (Result, error) { return RunClasses(bundle, "types/Root", "run", nil, verifyM4faGasLimit) }, 7158)
	verifyM4faAssertValue(t, func() (Result, error) { return RunClasses(bundle, "types/Root", "arbitrary", nil, verifyM4faGasLimit) }, 0)
	verifyM4faAssertValue(t, func() (Result, error) { return RunClasses(bundle, "types/Root", "nulls", nil, verifyM4faGasLimit) }, 1)
	verifyM4faAssertException(t, func() (Result, error) { return RunClasses(bundle, "types/Root", "castBad", nil, verifyM4faGasLimit) }, "java.lang.ClassCastException", 8)
	verifyM4faAssertException(t, func() (Result, error) { return RunClasses(bundle, "types/Root", "storeBad", nil, verifyM4faGasLimit) }, "java.lang.ArrayStoreException", 9)

	// Retarget an ordinary allocation to the well-formed interface CP class.
	root := classes["types/Root"]
	c := parseStaticsClass(t, root)
	m := c.namedMethod(t, "castBad")
	_, newPC := verifyM4faMemberInstruction(t, c, m, 0xbb, 7, "", "")
	ifaceIndex := verifyM4faClassIndex(t, c, "types/I")
	newIface := verifyM4faMutate(t, root, func(_ []byte, parsed staticsClass) {
		binary.BigEndian.PutUint16(parsed.namedMethod(t, "castBad").code[newPC+1:], ifaceIndex)
	})
	verifyM4faAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["types/I"], newIface}, "types/Root", "castBad", nil, verifyM4faGasLimit)
	}, "ObjectError(uint256,uint256)", 2, uint64(newPC))
}

func TestVerifyM4faGraphKindDuplicateCycleMissingAccessAndHeaderErrors(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"bad/A.java":     `package bad; public interface A { int f(); }`,
		"bad/B.java":     `package bad; public interface B { int f(); }`,
		"user/Root.java": `package user; public final class Root implements bad.A,bad.B { public int f(){return 1;} public static int run(){return new Root().f();} }`,
	}, "bad/A", "bad/B", "user/Root")

	// Omission is a real missing direct edge, and its location is the owner class index.
	verifyM4faAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["user/Root"]}, "user/Root", "run", nil, verifyM4faGasLimit)
	}, "LinkError(uint256,uint256)", 4, 0)

	rootHeader := verifyM4faHeaderOf(t, classes["user/Root"])
	if len(rootHeader.interfaces) != 2 {
		t.Fatalf("trusted Root interfaces=%v, want two", rootHeader.interfaces)
	}
	duplicate, alias := verifyM4faAppendNameAndClass(t, classes["user/Root"], "bad/A")
	duplicate = verifyM4faMutate(t, duplicate, func(_ []byte, c staticsClass) {
		h := verifyM4faHeaderOf(t, c.data)
		binary.BigEndian.PutUint16(c.data[h.interfaceOffsets[1]:], alias)
	})
	verifyM4faAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["bad/A"], classes["bad/B"], duplicate}, "user/Root", "run", nil, verifyM4faGasLimit)
	}, "InterfaceError(uint256,uint256)", 1, 2)

	wrongKindSource := compileJava(t, "A", `public class A { public A(){} }`)
	wrongKind := verifyM4faRenameClass(t, wrongKindSource, "A", "bad/A")
	verifyM4faAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{wrongKind, classes["bad/B"], classes["user/Root"]}, "user/Root", "run", nil, verifyM4faGasLimit)
	}, "InterfaceError(uint256,uint256)", 1, 2)

	inaccessible := verifyM4faMutate(t, classes["bad/A"], func(raw []byte, c staticsClass) {
		h := verifyM4faHeaderOf(t, raw)
		binary.BigEndian.PutUint16(raw[h.accessOffset:], h.access&^accPublic)
	})
	verifyM4faAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{inaccessible, classes["bad/B"], classes["user/Root"]}, "user/Root", "run", nil, verifyM4faGasLimit)
	}, "InterfaceError(uint256,uint256)", 3, 2)

	zeroSuper := verifyM4faMutate(t, classes["bad/A"], func(raw []byte, _ staticsClass) {
		h := verifyM4faHeaderOf(t, raw)
		binary.BigEndian.PutUint16(raw[h.superOffset:], 0)
	})
	verifyM4faAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{zeroSuper, classes["bad/B"], classes["user/Root"]}, "user/Root", "run", nil, verifyM4faGasLimit)
	}, "InterfaceError(uint256,uint256)", 1, 0)

	badSuper := verifyM4faMutate(t, classes["user/Root"], func(raw []byte, c staticsClass) {
		h := verifyM4faHeaderOf(t, raw)
		binary.BigEndian.PutUint16(raw[h.superOffset:], verifyM4faClassIndex(t, c, "bad/A"))
	})
	verifyM4faAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["bad/A"], classes["bad/B"], badSuper}, "user/Root", "run", nil, verifyM4faGasLimit)
	}, "HierarchyError(uint256,uint256)", 4, 2)

	verifyM4faAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["bad/A"]}, "bad/A", "f", nil, verifyM4faGasLimit)
	}, "LinkError(uint256,uint256)", 5, 0)

	cycleSources := compileBundleValidationJava(t, map[string]string{
		"cycle/Anchor.java": `package cycle; public interface Anchor { }`,
		"cycle/I.java":      `package cycle; public interface I extends Anchor { }`,
		"cycle/J.java":      `package cycle; public interface J extends Anchor { }`,
		"cycle/Root.java":   `package cycle; public final class Root implements I { public static int run(){return 1;} }`,
	}, "cycle/Anchor", "cycle/I", "cycle/J", "cycle/Root")
	i := verifyM4faRetargetFirstInterface(t, cycleSources["cycle/I"], "cycle/J")
	j := verifyM4faRetargetFirstInterface(t, cycleSources["cycle/J"], "cycle/I")
	verifyM4faAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{i, j, cycleSources["cycle/Root"]}, "cycle/Root", "run", nil, verifyM4faGasLimit)
	}, "InterfaceError(uint256,uint256)", 2, 0)
}

func TestVerifyM4faDefaultGuardPrecedesClassInitializationAndStaticMetadataStaysUnentered(t *testing.T) {
	guard := compileBundleValidationJava(t, map[string]string{
		"guard/I.java":    `package guard; public interface I { default int f(){return 1;} }`,
		"guard/Root.java": `package guard; public final class Root implements I { static int bad=1/zero(); static int zero(){return 0;} public static int run(){return bad;} }`,
	}, "guard/I", "guard/Root")
	verifyM4faAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{guard["guard/I"], guard["guard/Root"]}, "guard/Root", "run", nil, verifyM4faGasLimit)
	}, "InterfaceError(uint256,uint256)", 4, 0)

	lazy := compileBundleValidationJava(t, map[string]string{
		"lazy/Tracker.java": `package lazy; public final class Tracker { static int count; static int start(){count++;return 7;} }`,
		"lazy/I.java":       `package lazy; public interface I { int X=Tracker.start(); static int staticBody(){return X;} int f(); }`,
		"lazy/Impl.java":    `package lazy; public final class Impl implements I { public int f(){return 3;} }`,
		"lazy/Root.java": `package lazy; public final class Root {
			static int call(I x){return x.f();} public static int run(){I x=new Impl();I[] a=new I[1];I[][] b=new I[1][1];a[0]=x;
				return call(a[0])*100+Tracker.count*10+b.length;}
		}`,
	}, "lazy/Tracker", "lazy/I", "lazy/Impl", "lazy/Root")
	verifyM4faAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4faBundle(lazy), "lazy/Root", "run", nil, verifyM4faGasLimit)
	}, 301)
}

func TestVerifyM4faInvokeinterfaceFiveByteStructureCountCPAndBranchBoundaries(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"shape/Box.java":  `package shape; public final class Box { }`,
		"shape/I.java":    `package shape; public interface I { int f(int x,Box b,int[] a); }`,
		"shape/Impl.java": `package shape; public final class Impl implements I { public int f(int x,Box b,int[] a){return x+a.length;} }`,
		"shape/Root.java": `package shape; public final class Root {
			static int seed=one(); static int one(){return 1;}
			static int call(I x,int n){return x.f(n,new Box(),new int[2]);}
			public static int run(int n){return call(new Impl(),n);}
			public static int padding(){int x=0;` + strings.Repeat("x=x+1;", 50) + `return x;}
		}`,
	}, "shape/Box", "shape/I", "shape/Impl", "shape/Root")
	root := classes["shape/Root"]
	c := parseStaticsClass(t, root)
	call := c.method(t, "call", "(Lshape/I;I)I")
	ref, pc := verifyM4faMemberInstruction(t, c, call, verifyM4faInvokeinterface, 11, "f", "(ILshape/Box;[I)I")
	if call.code[pc+3] != 4 || call.code[pc+4] != 0 || verifyM4eInstructionWidth(t, call.code, pc) != 5 {
		t.Fatalf("invokeinterface bytes=%x, want CP11 count=argSlots+1=4 trailing zero", call.code[pc:pc+5])
	}
	verifyM4faAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4faBundle(classes), "shape/Root", "run", []int32{5}, verifyM4faGasLimit)
	}, 7)
	for _, tc := range []struct {
		name   string
		mutate func([]byte, staticsClass)
	}{
		{"cp-zero", func(_ []byte, p staticsClass) {
			binary.BigEndian.PutUint16(p.method(t, "call", "(Lshape/I;I)I").code[pc+1:], 0)
		}},
		{"cp-range", func(_ []byte, p staticsClass) {
			binary.BigEndian.PutUint16(p.method(t, "call", "(Lshape/I;I)I").code[pc+1:], uint16(p.cpCount))
		}},
		{"cp-tag10", func(raw []byte, p staticsClass) { raw[p.entry(t, ref).offset] = 10 }},
		{"count-zero", func(_ []byte, p staticsClass) { p.method(t, "call", "(Lshape/I;I)I").code[pc+3] = 0 }},
		{"count-low", func(_ []byte, p staticsClass) { p.method(t, "call", "(Lshape/I;I)I").code[pc+3] = 3 }},
		{"count-high", func(_ []byte, p staticsClass) { p.method(t, "call", "(Lshape/I;I)I").code[pc+3] = 5 }},
		{"trailing-nonzero", func(_ []byte, p staticsClass) { p.method(t, "call", "(Lshape/I;I)I").code[pc+4] = 1 }},
	} {
		t.Run(tc.name, func(t *testing.T) {
			bad := verifyM4faMutate(t, root, tc.mutate)
			verifyM4faAssertError(t, func() (Result, error) {
				return RunClasses([][]byte{classes["shape/Box"], classes["shape/I"], classes["shape/Impl"], bad}, "shape/Root", "run", []int32{5}, verifyM4faGasLimit)
			}, "CallError(uint256,uint256)", 1, uint64(pc))
		})
	}

	wrongOwner := verifyM4faMutate(t, root, func(raw []byte, p staticsClass) {
		binary.BigEndian.PutUint16(raw[p.entry(t, ref).offset+1:], verifyM4faClassIndex(t, p, "shape/Impl"))
	})
	verifyM4faAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["shape/Box"], classes["shape/I"], classes["shape/Impl"], wrongOwner}, "shape/Root", "run", []int32{5}, verifyM4faGasLimit)
	}, "InterfaceError(uint256,uint256)", 1, uint64(pc))

	for _, forbidden := range []string{"<init>", "<clinit>"} {
		t.Run("forbidden-name-"+forbidden, func(t *testing.T) {
			bad := verifyM4faMutate(t, root, func(raw []byte, p staticsClass) {
				nat := p.entry(t, p.u2(t, p.entry(t, ref).offset+3))
				binary.BigEndian.PutUint16(raw[nat.offset+1:], p.utfIndex(t, forbidden))
			})
			verifyM4faAssertError(t, func() (Result, error) {
				return RunClasses([][]byte{classes["shape/Box"], classes["shape/I"], classes["shape/Impl"], bad}, "shape/Root", "run", []int32{5}, verifyM4faGasLimit)
			}, "CallError(uint256,uint256)", 4, uint64(pc))
		})
	}

	for operands := 0; operands <= 3; operands++ {
		t.Run(fmt.Sprintf("truncated-%d", operands), func(t *testing.T) {
			ending := append([]byte{verifyM4faInvokeinterface}, make([]byte, operands)...)
			bad := verifyM4faRewriteAtEnd(t, root, "padding", "()I", ending)
			truncatedPC := len(parseStaticsClass(t, bad).method(t, "padding", "()I").code) - len(ending)
			verifyM4faAssertError(t, func() (Result, error) { return Run(bad, "padding", nil, verifyM4faGasLimit) }, "BytecodeError(uint256,uint256)", 2, uint64(truncatedPC))
		})
	}
	for operand := 1; operand <= 4; operand++ {
		t.Run(fmt.Sprintf("branch-operand-%d", operand), func(t *testing.T) {
			invokePC := 5
			target := invokePC + operand
			offset := target - 1
			code := []byte{0x03, 0x99, byte(offset >> 8), byte(offset), 0x01, verifyM4faInvokeinterface, byte(ref >> 8), byte(ref), 4, 0, 0x03, 0xac}
			bad := verifyM4faRewriteCode(t, root, "padding", "()I", code, 16, 16)
			verifyM4faAssertError(t, func() (Result, error) { return Run(bad, "padding", nil, verifyM4faGasLimit) }, "BytecodeError(uint256,uint256)", 12, 1)
		})
	}
}

func TestVerifyM4faStaticInterfaceCallsAndFieldsRemainPreciselyDeferred(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"defer/I.java":    `package defer; public interface I { int X=init(); static int init(){return 7;} static int s(){return X;} int f(); }`,
		"defer/Root.java": `package defer; public final class Root { public static int call(){return I.s();} public static int field(){return I.X;} }`,
	}, "defer/I", "defer/Root")
	root := classes["defer/Root"]
	c := parseStaticsClass(t, root)
	staticRef, staticPC := verifyM4faMemberInstruction(t, c, c.namedMethod(t, "call"), verifyM4faInvokestatic, 11, "s", "()I")
	verifyM4faAssertError(t, func() (Result, error) {
		return RunClasses(verifyM4faBundle(classes), "defer/Root", "call", nil, verifyM4faGasLimit)
	}, "CallError(uint256,uint256)", 1, uint64(staticPC))
	forged := verifyM4faMutate(t, root, func(raw []byte, p staticsClass) { raw[p.entry(t, staticRef).offset] = 10 })
	verifyM4faAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["defer/I"], forged}, "defer/Root", "call", nil, verifyM4faGasLimit)
	}, "CallError(uint256,uint256)", 4, uint64(staticPC))
	_, fieldPC := verifyM4faFieldInstruction(t, c, c.namedMethod(t, "field"), 0xb2, "X", "I")
	verifyM4faAssertError(t, func() (Result, error) {
		return RunClasses(verifyM4faBundle(classes), "defer/Root", "field", nil, verifyM4faGasLimit)
	}, "FieldError(uint256,uint256)", 3, uint64(fieldPC))
}

func TestVerifyM4faReceiverChecksSelectedImplementationsAndNullOrdering(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"recv/I.java":     `package recv; public interface I { int f(int x); int absent(); }`,
		"recv/Good.java":  `package recv; public class Good implements I { public int f(int x){return x+1;} public int absent(){return 2;} }`,
		"recv/Other.java": `package recv; public class Other { public int f(int x){return x+9;} }`,
		"recv/Root.java": `package recv; public final class Root {
			static int call(I x){return x.f(3);} public static int run(){return call(new Good());}
			public static int mention(I x){return x.absent();}
			public static int nullCall(){I x=null;return x.f(3);} public static int other(){I x=(I)(Object)new Other();return x.f(3);}
		}`,
	}, "recv/I", "recv/Good", "recv/Other", "recv/Root")
	root := classes["recv/Root"]
	parsed := parseStaticsClass(t, root)
	_, callPC := verifyM4faMemberInstruction(t, parsed, parsed.method(t, "call", "(Lrecv/I;)I"), verifyM4faInvokeinterface, 11, "f", "(I)I")
	verifyM4faAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4faBundle(classes), "recv/Root", "run", nil, verifyM4faGasLimit)
	}, 4)
	verifyM4faAssertException(t, func() (Result, error) {
		return RunClasses(verifyM4faBundle(classes), "recv/Root", "nullCall", nil, verifyM4faGasLimit)
	}, "java.lang.NullPointerException", 6)

	// Remove only checkcast's three-byte instruction. The initialized Other
	// reaches b9 and is a valid reference, but does not implement I.
	other := verifyM4faMutate(t, root, func(_ []byte, p staticsClass) {
		m := p.namedMethod(t, "other")
		castPC := verifyM4eInstructionPC(t, m.code, verifyM4faCheckcast, 0)
		m.code[castPC] = 0
		m.code[castPC+1] = 0
		m.code[castPC+2] = 0
	})
	otherPC := verifyM4eInstructionPC(t, parseStaticsClass(t, other).namedMethod(t, "other").code, verifyM4faInvokeinterface, 0)
	verifyM4faAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["recv/I"], classes["recv/Other"], other}, "recv/Root", "other", nil, verifyM4faGasLimit)
	}, "ReferenceError(uint256,uint256)", 2, uint64(otherPC))

	for _, tc := range []struct {
		name  string
		flags func(uint16) uint16
	}{
		{"native", func(f uint16) uint16 { return f | accNative }},
		{"abstract", func(f uint16) uint16 { return f | verifyM4faAbstract }},
		{"synchronized", func(f uint16) uint16 { return f | verifyM4faSynchronized }},
		{"static", func(f uint16) uint16 { return f | accStatic }},
		{"private", func(f uint16) uint16 { return (f &^ accessMask) | accPrivate }},
	} {
		t.Run(tc.name, func(t *testing.T) {
			good := verifyM4faMutate(t, classes["recv/Good"], func(raw []byte, p staticsClass) {
				m := p.method(t, "f", "(I)I")
				binary.BigEndian.PutUint16(raw[m.accessOffset:], tc.flags(m.access))
			})
			verifyM4faAssertError(t, func() (Result, error) {
				return RunClasses([][]byte{classes["recv/I"], good, root}, "recv/Root", "run", nil, verifyM4faGasLimit)
			}, "CallError(uint256,uint256)", 4, uint64(callPC))
		})
	}
	missingImpl := verifyM4faRenameMethod(t, classes["recv/Good"], "f", "(I)I", 'g')
	verifyM4faAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["recv/I"], missingImpl, root}, "recv/Root", "run", nil, verifyM4faGasLimit)
	}, "CallError(uint256,uint256)", 4, uint64(callPC))

	// Well-formed symbolic resolution still precedes receiver checks.
	nullRoot := root
	nullParsed := parseStaticsClass(t, nullRoot)
	nullMethod := nullParsed.namedMethod(t, "nullCall")
	nullRef, nullPC := verifyM4faMemberInstruction(t, nullParsed, nullMethod, verifyM4faInvokeinterface, 11, "f", "(I)I")
	missing := verifyM4faMutate(t, nullRoot, func(raw []byte, p staticsClass) {
		nat := p.entry(t, p.u2(t, p.entry(t, nullRef).offset+3))
		binary.BigEndian.PutUint16(raw[nat.offset+1:], p.utfIndex(t, "absent"))
	})
	// absent()I and f(I)I differ, so exact symbolic lookup is genuinely missing.
	verifyM4faAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["recv/I"], missing}, "recv/Root", "nullCall", nil, verifyM4faGasLimit)
	}, "CallError(uint256,uint256)", 3, uint64(nullPC))

	badKindsBase := root
	ref := nullRef
	numeric := verifyM4faRewriteCode(t, badKindsBase, "nullCall", "()I", []byte{0x04, 0x06, verifyM4faInvokeinterface, byte(ref >> 8), byte(ref), 2, 0, 0xac}, 16, 8)
	verifyM4faAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["recv/I"], numeric}, "recv/Root", "nullCall", nil, verifyM4faGasLimit)
	}, "BytecodeError(uint256,uint256)", 14, 2)
	goodIndex := verifyM4faClassIndex(t, parsed, "recv/Good")
	uninit := verifyM4faRewriteCode(t, badKindsBase, "nullCall", "()I", []byte{0xbb, byte(goodIndex >> 8), byte(goodIndex), 0x06, verifyM4faInvokeinterface, byte(ref >> 8), byte(ref), 2, 0, 0xac}, 16, 8)
	verifyM4faAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["recv/I"], classes["recv/Good"], uninit}, "recv/Root", "nullCall", nil, verifyM4faGasLimit)
	}, "BytecodeError(uint256,uint256)", 14, 4)
}

func TestVerifyM4faAbstractVirtualFallbackClassBridgeAndOpcodeCaches(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"fallback/I.java":     `package fallback; public interface I { int f(); }`,
		"fallback/A.java":     `package fallback; public abstract class A implements I { }`,
		"fallback/B.java":     `package fallback; public final class B extends A { public int f(){return 7;} }`,
		"fallback/Base.java":  `package fallback; public class Base { }`,
		"fallback/Child.java": `package fallback; public final class Child extends Base { }`,
		"fallback/P.java":     `package fallback; public interface P { Base make(); }`,
		"fallback/Maker.java": `package fallback; public final class Maker implements P { public Child make(){return new Child();} }`,
		"fallback/Root.java": `package fallback; public final class Root {
			static int viaClass(A x){return x.f();} static int viaIface(I x){return x.f();}
			public static int run(){B b=new B();P p=new Maker();return viaClass(b)*100+viaIface(b)*10+(p.make() instanceof Child?1:0);}
		}`,
	}, "fallback/I", "fallback/A", "fallback/B", "fallback/Base", "fallback/Child", "fallback/P", "fallback/Maker", "fallback/Root")
	root := classes["fallback/Root"]
	c := parseStaticsClass(t, root)
	if _, pc := verifyM4faMemberInstruction(t, c, c.namedMethod(t, "viaClass"), verifyM4faInvokevirtual, 10, "f", "()I"); pc < 0 {
		t.Fatal("missing b6 fallback site")
	}
	if _, pc := verifyM4faMemberInstruction(t, c, c.namedMethod(t, "viaIface"), verifyM4faInvokeinterface, 11, "f", "()I"); pc < 0 {
		t.Fatal("missing b9 site")
	}
	bridge := parseStaticsClass(t, classes["fallback/Maker"])
	bridgeMethod := bridge.method(t, "make", "()Lfallback/Base;")
	if bridgeMethod.access&accPublic == 0 || bridgeMethod.access&verifyM4faAbstract != 0 || len(bridgeMethod.code) == 0 {
		t.Fatalf("class bridge flags/code=%x/%x", bridgeMethod.access, bridgeMethod.code)
	}
	verifyM4faAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4faBundle(classes), "fallback/Root", "run", nil, verifyM4faGasLimit)
	}, 771)
}

func TestVerifyM4faObjectFallbackUsesSuppliedCodeAndInventsNoBootstrapAPI(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"java/lang/Object.java": `package java.lang; public class Object { public Object(){} public int f(){return 23;} }`,
		"objectfb/I.java":       `package objectfb; public interface I { int f(); }`,
		"objectfb/Impl.java":    `package objectfb; public final class Impl implements I { public int f(){return 9;} }`,
		"objectfb/Root.java":    `package objectfb; public final class Root { static int call(I x){return x.f();} public static int run(){return call(new Impl());} }`,
	}, "java/lang/Object", "objectfb/I", "objectfb/Impl", "objectfb/Root")
	i := verifyM4faRenameMethod(t, classes["objectfb/I"], "f", "()I", 'g')
	impl := verifyM4faRenameMethod(t, classes["objectfb/Impl"], "f", "()I", 'g')
	withObject := [][]byte{classes["java/lang/Object"], i, impl, classes["objectfb/Root"]}
	verifyM4faAssertValue(t, func() (Result, error) { return RunClasses(withObject, "objectfb/Root", "run", nil, verifyM4faGasLimit) }, 23)
	_, pc := verifyM4faMemberInstruction(t, parseStaticsClass(t, classes["objectfb/Root"]), parseStaticsClass(t, classes["objectfb/Root"]).namedMethod(t, "call"), verifyM4faInvokeinterface, 11, "f", "()I")
	verifyM4faAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{i, impl, classes["objectfb/Root"]}, "objectfb/Root", "run", nil, verifyM4faGasLimit)
	}, "CallError(uint256,uint256)", 3, uint64(pc))
}

func TestVerifyM4faEveryArrayReceiverDefersOnlyAfterResolution(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"java/lang/Cloneable.java": `package java.lang; public interface Cloneable { int f(); }`,
		"arraycall/I.java":         `package arraycall; public interface I { int f(); }`,
		"arraycall/Impl.java":      `package arraycall; public final class Impl implements I { public int f(){return 1;} }`,
		"arraycall/Root.java":      `package arraycall; public final class Root { static int call(I x){return x.f();} public static int run(){return call(new Impl());} public static int padding(){int x=0;` + strings.Repeat("x++;", 30) + `return x;} }`,
	}, "java/lang/Cloneable", "arraycall/I", "arraycall/Impl", "arraycall/Root")
	root := classes["arraycall/Root"]
	c := parseStaticsClass(t, root)
	ref, _ := verifyM4faMemberInstruction(t, c, c.namedMethod(t, "call"), verifyM4faInvokeinterface, 11, "f", "()I")
	markerIndex := verifyM4faAppendClassTarget(t, &root, "java/lang/Cloneable")
	root = verifyM4faMutate(t, root, func(raw []byte, p staticsClass) {
		binary.BigEndian.PutUint16(raw[p.entry(t, ref).offset+1:], markerIndex)
	})
	rootParsed := parseStaticsClass(t, root)
	ifaceIndex := verifyM4faClassIndex(t, rootParsed, "arraycall/I")
	objectIndex := verifyM4faAppendClassTarget(t, &root, "java/lang/Object")
	multiIndex := verifyM4faAppendClassTarget(t, &root, "[[I")
	programs := map[string][]byte{
		"int":   {0x04, 0xbc, 10, verifyM4faInvokeinterface, byte(ref >> 8), byte(ref), 1, 0, 0xac},
		"ref":   {0x04, verifyM4faAnewarray, byte(objectIndex >> 8), byte(objectIndex), verifyM4faInvokeinterface, byte(ref >> 8), byte(ref), 1, 0, 0xac},
		"iface": {0x04, verifyM4faAnewarray, byte(ifaceIndex >> 8), byte(ifaceIndex), verifyM4faInvokeinterface, byte(ref >> 8), byte(ref), 1, 0, 0xac},
		"multi": {0x04, 0x04, verifyM4faMultianewarray, byte(multiIndex >> 8), byte(multiIndex), 2, verifyM4faInvokeinterface, byte(ref >> 8), byte(ref), 1, 0, 0xac},
	}
	for name, code := range programs {
		t.Run(name, func(t *testing.T) {
			bad := verifyM4faRewriteCode(t, root, "padding", "()I", code, 16, 8)
			callPC := verifyM4eInstructionPC(t, code, verifyM4faInvokeinterface, 0)
			verifyM4faAssertError(t, func() (Result, error) {
				return RunClasses([][]byte{classes["java/lang/Cloneable"], classes["arraycall/I"], bad}, "arraycall/Root", "padding", nil, verifyM4faGasLimit)
			}, "CallError(uint256,uint256)", 4, uint64(callPC))
		})
	}
}

func TestVerifyM4faSuppliedMarkerMustParseAsAnInterface(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"java/lang/Cloneable.java": `package java.lang; public class Cloneable { public Cloneable(){} }`,
		"marker/Root.java": `package marker; public final class Root {
			public static int run(){Object x=new int[0];return x instanceof java.lang.Cloneable?1:0;}
		}`,
	}, "java/lang/Cloneable", "marker/Root")
	verifyM4faAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["java/lang/Cloneable"], classes["marker/Root"]}, "marker/Root", "run", nil, verifyM4faGasLimit)
	}, "InterfaceError(uint256,uint256)", 1, 0)
}

func TestVerifyM4faSixtyFourUserInputsStillAppendThreeBootClasses(t *testing.T) {
	sources := map[string]string{"cap/Root.java": `package cap; public final class Root { public static int run(){Object x=new int[0];return x instanceof Cloneable && x instanceof java.io.Serializable?1:0;} }`}
	names := []string{"cap/Root"}
	for i := 0; i < 63; i++ {
		name := fmt.Sprintf("cap/C%02d", i)
		sources[name+".java"] = fmt.Sprintf("package cap; public final class C%02d { }", i)
		names = append(names, name)
	}
	classes := compileBundleValidationJava(t, sources, names...)
	bundle := make([][]byte, 0, 64)
	for _, name := range names {
		bundle = append(bundle, classes[name])
	}
	verifyM4faAssertValue(t, func() (Result, error) { return RunClasses(bundle, "cap/Root", "run", nil, verifyM4faGasLimit) }, 1)
	tooMany := append(append([][]byte(nil), bundle...), classes["cap/C00"])
	verifyM4faAssertError(t, func() (Result, error) { return RunClasses(tooMany, "cap/Root", "run", nil, verifyM4faGasLimit) }, "LinkError(uint256,uint256)", 1, 65)
}

// --- verifier-only classfile and assertion helpers ---

type verifyM4faHeader struct {
	accessOffset         int
	access               uint16
	superOffset          int
	interfaceCountOffset int
	interfaces           []uint16
	interfaceOffsets     []int
}

func verifyM4faHeaderOf(t *testing.T, data []byte) verifyM4faHeader {
	t.Helper()
	c := parseStaticsClass(t, data)
	pos := c.cpEnd
	if pos+8 > len(data) {
		t.Fatal("truncated header")
	}
	h := verifyM4faHeader{accessOffset: pos, access: binary.BigEndian.Uint16(data[pos:]), superOffset: pos + 4, interfaceCountOffset: pos + 6}
	n := int(binary.BigEndian.Uint16(data[pos+6:]))
	pos += 8
	if pos+2*n > len(data) {
		t.Fatal("truncated interfaces")
	}
	for i := 0; i < n; i++ {
		h.interfaceOffsets = append(h.interfaceOffsets, pos)
		h.interfaces = append(h.interfaces, binary.BigEndian.Uint16(data[pos:]))
		pos += 2
	}
	return h
}

func verifyM4faBundle(classes map[string][]byte) [][]byte {
	names := make([]string, 0, len(classes))
	for n := range classes {
		names = append(names, n)
	}
	sort.Strings(names)
	out := make([][]byte, len(names))
	for i, n := range names {
		out[i] = classes[n]
	}
	return out
}

func verifyM4faMutate(t *testing.T, original []byte, change func([]byte, staticsClass)) []byte {
	t.Helper()
	out := append([]byte(nil), original...)
	change(out, parseStaticsClass(t, out))
	return out
}

func verifyM4faClassIndex(t *testing.T, c staticsClass, name string) uint16 {
	t.Helper()
	for i := 1; i < len(c.entries); i++ {
		e := c.entries[i]
		if e.tag == 7 && c.utf8[c.u2(t, e.offset+1)] == name {
			return uint16(i)
		}
	}
	t.Fatalf("Class %q missing", name)
	return 0
}

func verifyM4faMemberInstruction(t *testing.T, c staticsClass, m staticsMethod, opcode, tag byte, name, descriptor string) (uint16, int) {
	t.Helper()
	for pc := 0; pc < len(m.code); pc += verifyM4eInstructionWidth(t, m.code, pc) {
		if m.code[pc] != opcode || pc+2 >= len(m.code) {
			continue
		}
		ref := binary.BigEndian.Uint16(m.code[pc+1:])
		if ref == 0 || int(ref) >= len(c.entries) || c.entries[ref].tag != tag {
			continue
		}
		if name == "" {
			return ref, pc
		}
		e := c.entry(t, ref)
		nat := c.entry(t, c.u2(t, e.offset+3))
		if nat.tag == 12 && c.utf8[c.u2(t, nat.offset+1)] == name && c.utf8[c.u2(t, nat.offset+3)] == descriptor {
			return ref, pc
		}
	}
	t.Fatalf("%s%s lacks opcode %02x CP tag %d %s%s: %x", m.name, m.descriptor, opcode, tag, name, descriptor, m.code)
	return 0, -1
}

func verifyM4faFieldInstruction(t *testing.T, c staticsClass, m staticsMethod, opcode byte, name, descriptor string) (uint16, int) {
	t.Helper()
	return verifyM4faMemberInstruction(t, c, m, opcode, 9, name, descriptor)
}

func verifyM4faAppendNameAndClass(t *testing.T, original []byte, name string) ([]byte, uint16) {
	t.Helper()
	c := parseStaticsClass(t, original)
	if c.cpCount+2 > 65535 || len(name) > 65535 {
		t.Fatal("constant pool overflow")
	}
	insert := make([]byte, 6+len(name))
	insert[0] = 1
	binary.BigEndian.PutUint16(insert[1:], uint16(len(name)))
	copy(insert[3:], name)
	p := 3 + len(name)
	insert[p] = 7
	binary.BigEndian.PutUint16(insert[p+1:], uint16(c.cpCount))
	out := make([]byte, len(original)+len(insert))
	copy(out, original[:c.cpEnd])
	copy(out[c.cpEnd:], insert)
	copy(out[c.cpEnd+len(insert):], original[c.cpEnd:])
	binary.BigEndian.PutUint16(out[8:], uint16(c.cpCount+2))
	return out, uint16(c.cpCount + 1)
}

func verifyM4faAppendClassTarget(t *testing.T, classfile *[]byte, name string) uint16 {
	t.Helper()
	out, index := verifyM4faAppendNameAndClass(t, *classfile, name)
	*classfile = out
	return index
}

func verifyM4faRetargetFirstInterface(t *testing.T, original []byte, target string) []byte {
	t.Helper()
	out, index := verifyM4faAppendNameAndClass(t, original, target)
	h := verifyM4faHeaderOf(t, out)
	if len(h.interfaces) != 1 {
		t.Fatalf("interfaces=%v, want one", h.interfaces)
	}
	binary.BigEndian.PutUint16(out[h.interfaceOffsets[0]:], index)
	return out
}

func verifyM4faRenameClass(t *testing.T, original []byte, from, to string) []byte {
	t.Helper()
	if len(from) != len(to) { // append a new UTF/Class and retarget this_class for unequal names
		out, index := verifyM4faAppendNameAndClass(t, original, to)
		h := verifyM4faHeaderOf(t, out)
		binary.BigEndian.PutUint16(out[h.accessOffset+2:], index)
		return out
	}
	out := append([]byte(nil), original...)
	c := parseStaticsClass(t, out)
	e := c.entry(t, c.utfIndex(t, from))
	copy(out[e.offset+3:], to)
	return out
}

func verifyM4faRenameMethod(t *testing.T, original []byte, name, descriptor string, replacement byte) []byte {
	t.Helper()
	return verifyM4faMutate(t, original, func(raw []byte, c staticsClass) {
		m := c.method(t, name, descriptor)
		index := binary.BigEndian.Uint16(raw[m.nameIndexOffset:])
		e := c.entry(t, index)
		if e.tag != 1 || binary.BigEndian.Uint16(raw[e.offset+1:]) != 1 {
			t.Fatalf("method name %q is not isolated one-byte UTF", name)
		}
		raw[e.offset+3] = replacement
	})
}

func verifyM4faRewriteCode(t *testing.T, original []byte, name, descriptor string, code []byte, maxStack, maxLocals uint16) []byte {
	t.Helper()
	out := append([]byte(nil), original...)
	m := parseStaticsClass(t, out).method(t, name, descriptor)
	if len(code) > len(m.code) {
		t.Fatalf("replacement code %d > %d", len(code), len(m.code))
	}
	start := -1
	for i := range out {
		if len(m.code) > 0 && &out[i] == &m.code[0] {
			start = i
			break
		}
	}
	if start < 8 {
		t.Fatal("Code location missing")
	}
	binary.BigEndian.PutUint16(out[start-8:], maxStack)
	binary.BigEndian.PutUint16(out[start-6:], maxLocals)
	for i := range m.code {
		m.code[i] = 0
	}
	copy(m.code, code)
	return out
}

func verifyM4faRewriteAtEnd(t *testing.T, original []byte, name, descriptor string, ending []byte) []byte {
	t.Helper()
	out := verifyM4faRewriteCode(t, original, name, descriptor, nil, 16, 16)
	m := parseStaticsClass(t, out).method(t, name, descriptor)
	copy(m.code[len(m.code)-len(ending):], ending)
	return out
}

func verifyM4faCompileWithOracle(t *testing.T, sources map[string]string, main, want string, names ...string) map[string][]byte {
	t.Helper()
	dir := t.TempDir()
	rels := make([]string, 0, len(sources))
	for rel := range sources {
		rels = append(rels, rel)
	}
	sort.Strings(rels)
	args := []string{"--release", "8", "-d", dir}
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
		t.Fatalf("bounded javac: %v\n%s", err, output)
	}
	ctxRun, cancelRun := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancelRun()
	output, err := exec.CommandContext(ctxRun, "java", "-cp", dir, main).CombinedOutput()
	if err != nil {
		t.Fatalf("bounded trusted JVM oracle: %v\n%s", err, output)
	}
	if strings.TrimSpace(string(output)) != want {
		t.Fatalf("trusted JVM=%q want %q", output, want)
	}
	classes := make(map[string][]byte, len(names))
	for _, name := range names {
		data, err := os.ReadFile(filepath.Join(dir, filepath.FromSlash(name+".class")))
		if err != nil {
			t.Fatal(err)
		}
		classes[name] = data
	}
	return classes
}

func verifyM4faAssertValue(t *testing.T, run func() (Result, error), want int32) {
	t.Helper()
	result, err := run()
	if err != nil || result.ExceptionClass != "" || result.Value != want || result.GasUsed == 0 || len(result.RevertData) != 0 {
		t.Fatalf("result/error=%+v/%v, want value %d", result, err, want)
	}
}

func verifyM4faAssertException(t *testing.T, run func() (Result, error), want string, kind byte) {
	t.Helper()
	result, err := run()
	selector := crypto.Keccak256([]byte("JavaException(uint256)"))[:4]
	if err != nil || result.ExceptionClass != want || result.GasUsed == 0 || len(result.RevertData) != 36 || !bytes.Equal(result.RevertData[:4], selector) || !bytes.Equal(result.RevertData[4:35], make([]byte, 31)) || result.RevertData[35] != kind {
		t.Fatalf("result/error=%+v/%v data=%x, want %s kind %d", result, err, result.RevertData, want, kind)
	}
}

func verifyM4faAssertError(t *testing.T, run func() (Result, error), signature string, code, location uint64) {
	t.Helper()
	result, err := run()
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error=%+v/%v, want %s(%d,%d)", result, err, signature, code, location)
	}
	selector := crypto.Keccak256([]byte(signature))[:4]
	if result.ExceptionClass != "" || result.GasUsed == 0 || len(result.RevertData) != 68 || !bytes.Equal(result.RevertData[:4], selector) {
		t.Fatalf("result=%+v data=%x, want exact %s", result, result.RevertData, signature)
	}
	if got := verifyM4faUint256(t, result.RevertData[4:36]); got != code {
		t.Fatalf("%s code=%d want %d", signature, got, code)
	}
	if got := verifyM4faUint256(t, result.RevertData[36:]); got != location {
		t.Fatalf("%s location=%d want %d", signature, got, location)
	}
}

func verifyM4faUint256(t *testing.T, word []byte) uint64 {
	t.Helper()
	if len(word) != 32 || !bytes.Equal(word[:24], make([]byte, 24)) {
		t.Fatalf("noncanonical uint256 %x", word)
	}
	return binary.BigEndian.Uint64(word[24:])
}

func TestVerifyM4faOOGRemainsUnlabeledEngineFailure(t *testing.T) {
	classfile := compileJava(t, "M4faOOG", `public final class M4faOOG { public static int run(){return 1;} }`)
	result, err := Run(classfile, "run", nil, 1)
	if err == nil || !errors.Is(err, vm.ErrOutOfGas) || result.ExceptionClass != "" || len(result.RevertData) != 0 {
		t.Fatalf("result/error=%+v/%v, want unlabeled EVM OOG", result, err)
	}
}
