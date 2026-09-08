// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"encoding/binary"
	"errors"
	"fmt"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/core/vm"
	"github.com/ethereum/go-ethereum/crypto"
)

const (
	verifyM4cGasLimit      = uint64(100_000_000)
	verifyM4cInvokevirtual = byte(0xb6)
	verifyM4cCheckcast     = byte(0xc0)
	verifyM4cInstanceof    = byte(0xc1)
	verifyM4cAbstract      = uint16(0x0400)
	verifyM4cSynchronized  = uint16(0x0020)
)

// These tests use only trusted javac --release 8 inputs. Mutations alter one
// named flag, CP edge, or instruction in a locally generated class. Helpers are
// verifier-only and deliberately expose no production parser or host fallback.

func TestVerifyM4cVirtualDispatchSelectionPolymorphismAndOpcodeSeparation(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"dispatch/Base.java": `package dispatch; public class Base {
            public Base(){} public int pick(int x){return x+1;} public int inherited(){return 7;}
            public void add(Box b,int x){b.value=b.value+x;} public Base self(){return this;}
        }`,
		"dispatch/Left.java": `package dispatch; public class Left extends Base {
            public Left(){} public int pick(int x){return x+10;} public Base self(){return this;}
        }`,
		"dispatch/Right.java": `package dispatch; public final class Right extends Base {
            public Right(){} public int pick(int x){return x+100;}
        }`,
		"dispatch/Box.java": `package dispatch; public final class Box { public int value; }`,
		"dispatch/Root.java": `package dispatch; public final class Root {
            static int atOneSite(Base b,int x){return b.pick(x);}
            static int same(Base b){return b.self()==b?1:0;}
            public static int run(int x){Base a=new Left();Base b=new Right();Box box=new Box();
                a.add(box,3);b.add(box,4);return atOneSite(a,x)*10000+atOneSite(b,x)*10
                    +a.inherited()+same(a)+box.value;}
        }`,
	}, "dispatch/Base", "dispatch/Left", "dispatch/Right", "dispatch/Box", "dispatch/Root")
	verifyM4cAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4bBundle(classes), "dispatch/Root", "run", []int32{2}, verifyM4cGasLimit)
	}, 121035)

	separation := compileBundleValidationJava(t, map[string]string{
		"separate/Base.java": `package separate; public class Base { public Base(){} public int f(){return 1;} }`,
		"separate/Child.java": `package separate; public final class Child extends Base {
            public Child(){} public int f(){return 2;} public int run(){int a=f();return a+super.f();}
        }`,
		"separate/Root.java": `package separate; public final class Root {
            public static int run(){return new Child().run();}
        }`,
	}, "separate/Base", "separate/Child", "separate/Root")
	// Force Child.run's virtual and special sites to share Base.f's Methodref.
	// Selection/cache state must remain opcode-specific: virtual selects Child.f,
	// invokespecial selects Base.f.
	child := verifyM4bMutate(t, separation["separate/Child"], func(out []byte, c staticsClass) {
		m := c.method(t, "run", "()I")
		_, virtualPC := verifyM4bMemberInstruction(t, c, m, verifyM4cInvokevirtual, "f", "()I")
		specialRef, _ := verifyM4bMemberInstruction(t, c, m, verifyM4bInvokespecial, "f", "()I")
		binary.BigEndian.PutUint16(m.code[virtualPC+1:], specialRef)
	})
	separation["separate/Child"] = child
	verifyM4cAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4bBundle(separation), "separate/Root", "run", nil, verifyM4cGasLimit)
	}, 3)
}

func TestVerifyM4cResolvedUnsupportedMethodMaySelectOrdinaryOverride(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"resolved/AbstractBase.java": `package resolved; public abstract class AbstractBase {
            public AbstractBase(){} public abstract int f();
        }`,
		"resolved/AbstractChild.java": `package resolved; public final class AbstractChild extends AbstractBase {
            public AbstractChild(){} public int f(){return 11;}
        }`,
		"resolved/NativeBase.java": `package resolved; public class NativeBase {
            public NativeBase(){} public native int f();
        }`,
		"resolved/NativeChild.java": `package resolved; public final class NativeChild extends NativeBase {
            public NativeChild(){} public int f(){return 13;}
        }`,
		"resolved/SyncBase.java": `package resolved; public class SyncBase {
            public SyncBase(){} public synchronized int f(){return 1;}
        }`,
		"resolved/SyncChild.java": `package resolved; public final class SyncChild extends SyncBase {
            public SyncChild(){} public int f(){return 17;}
        }`,
		"resolved/Root.java": `package resolved; public final class Root {
            static int a(AbstractBase x){return x.f();} static int n(NativeBase x){return x.f();}
            static int s(SyncBase x){return x.f();}
            public static int run(){return a(new AbstractChild())*10000+n(new NativeChild())*100+s(new SyncChild());}
        }`,
	}, "resolved/AbstractBase", "resolved/AbstractChild", "resolved/NativeBase", "resolved/NativeChild", "resolved/SyncBase", "resolved/SyncChild", "resolved/Root")
	verifyM4cAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4bBundle(classes), "resolved/Root", "run", nil, verifyM4cGasLimit)
	}, 111317)
}

func TestVerifyM4cSelectedOverrideUnsupportedAndPrivateDeclarationsDoNotHijack(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"selected/Base.java":  `package selected; public class Base { public Base(){} public int f(){return 1;} }`,
		"selected/Child.java": `package selected; public final class Child extends Base { public Child(){} public int f(){return 2;} }`,
		"selected/Root.java": `package selected; public final class Root {
            static int call(Base b){return b.f();} public static int run(){return call(new Child());}
        }`,
	}, "selected/Base", "selected/Child", "selected/Root")
	pc := verifyM4bOpcodePC(t, parseStaticsClass(t, classes["selected/Root"]).method(t, "call", "(Lselected/Base;)I").code, verifyM4cInvokevirtual, 0)
	for _, tc := range []struct {
		name   string
		mutate func([]byte, staticsClass, staticsMethod)
	}{
		{"native", func(out []byte, c staticsClass, m staticsMethod) {
			binary.BigEndian.PutUint16(out[m.accessOffset:], m.access|accNative)
		}},
		{"abstract", func(out []byte, c staticsClass, m staticsMethod) {
			binary.BigEndian.PutUint16(out[m.accessOffset:], m.access|verifyM4cAbstract)
		}},
		{"synchronized", func(out []byte, c staticsClass, m staticsMethod) {
			binary.BigEndian.PutUint16(out[m.accessOffset:], m.access|verifyM4cSynchronized)
		}},
		{"no-code", func(out []byte, c staticsClass, m staticsMethod) {
			binary.BigEndian.PutUint16(out[m.codeNameOffset:], c.utfIndex(t, "SourceFile"))
		}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			child := verifyM4bMutate(t, classes["selected/Child"], func(out []byte, c staticsClass) {
				tc.mutate(out, c, c.method(t, "f", "()I"))
			})
			verifyM4cAssertError(t, func() (Result, error) {
				return RunClasses([][]byte{classes["selected/Base"], child, classes["selected/Root"]}, "selected/Root", "run", nil, verifyM4cGasLimit)
			}, "CallError(uint256,uint256)", 4, uint64(pc))
		})
	}
	privateChild := verifyM4bMutate(t, classes["selected/Child"], func(out []byte, c staticsClass) {
		m := c.method(t, "f", "()I")
		binary.BigEndian.PutUint16(out[m.accessOffset:], (m.access&^accessMask)|accPrivate)
	})
	verifyM4cAssertValue(t, func() (Result, error) {
		return RunClasses([][]byte{classes["selected/Base"], privateChild, classes["selected/Root"]}, "selected/Root", "run", nil, verifyM4cGasLimit)
	}, 1)
}

func TestVerifyM4cPackagePrivateOverrideChainsAndFinalSlots(t *testing.T) {
	good := compileBundleValidationJava(t, map[string]string{
		"chainp/A.java": `package chainp; public class A { public A(){} int f(){return 1;} }`,
		"chainp/B.java": `package chainp; public class B extends A { public B(){} public int f(){return 2;} }`,
		"chainq/C.java": `package chainq; public final class C extends chainp.B { public C(){} public int f(){return 3;} }`,
		"chainp/Root.java": `package chainp; public final class Root {
            static int call(A a){return a.f();} public static int run(){return call(new chainq.C());}
        }`,
	}, "chainp/A", "chainp/B", "chainq/C", "chainp/Root")
	verifyM4cAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4bBundle(good), "chainp/Root", "run", nil, verifyM4cGasLimit)
	}, 3)

	gap := compileBundleValidationJava(t, map[string]string{
		"gapp/A.java": `package gapp; public class A { public A(){} int f(){return 4;} }`,
		"gapq/B.java": `package gapq; public class B extends gapp.A { public B(){} public int f(){return 5;} }`,
		"gapq/C.java": `package gapq; public final class C extends B { public C(){} public int f(){return 6;} }`,
		"gapp/Root.java": `package gapp; public final class Root {
            static int call(A a){return a.f();} public static int run(){return call(new gapq.C());}
        }`,
	}, "gapp/A", "gapq/B", "gapq/C", "gapp/Root")
	// B.f cannot override inaccessible A.f across the package gap, and C.f only
	// overrides B.f. Neither declaration may hijack the A slot.
	verifyM4cAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4bBundle(gap), "gapp/Root", "run", nil, verifyM4cGasLimit)
	}, 4)

	finalGap := verifyM4bMutate(t, gap["gapp/A"], func(out []byte, c staticsClass) {
		m := c.method(t, "f", "()I")
		binary.BigEndian.PutUint16(out[m.accessOffset:], m.access|accFinal)
	})
	gap["gapp/A"] = finalGap
	verifyM4cAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4bBundle(gap), "gapp/Root", "run", nil, verifyM4cGasLimit)
	}, 4)
}

func TestVerifyM4cConstructorVirtualCallbackUsesAllocationClassAndDefaults(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"callback/Base.java": `package callback; public class Base {
            public int observed; public Base(){observed=value();} public int value(){return 1;}
        }`,
		"callback/Child.java": `package callback; public final class Child extends Base {
            public int derived; public Child(int x){super();derived=x;} public int value(){return derived+7;}
        }`,
		"callback/Root.java": `package callback; public final class Root {
            public static int run(int x){Child c=new Child(x);return c.observed*100+c.value();}
        }`,
	}, "callback/Base", "callback/Child", "callback/Root")
	// Base.<init> dispatches to Child.value before Child initializes derived: 7.
	verifyM4cAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4bBundle(classes), "callback/Root", "run", []int32{5}, verifyM4cGasLimit)
	}, 712)
}

func TestVerifyM4cVirtualResolutionAccessAndSelectedBodyErrorsExact(t *testing.T) {
	original := compileJava(t, "VirtualErrors", `public class VirtualErrors {
        public VirtualErrors(){} public int f(int x){return x+1;} public int absent(){return 0;}
        public static int run(int x){return new VirtualErrors().f(x);}
    }`)
	parsed := parseStaticsClass(t, original)
	run := parsed.method(t, "run", "(I)I")
	ref, pc := verifyM4bMemberInstruction(t, parsed, run, verifyM4cInvokevirtual, "f", "(I)I")
	cases := []struct {
		name string
		make func([]byte, staticsClass)
		code uint64
	}{
		{"operand-zero", func(out []byte, c staticsClass) {
			binary.BigEndian.PutUint16(c.method(t, "run", "(I)I").code[pc+1:], 0)
		}, 1},
		{"operand-range", func(out []byte, c staticsClass) {
			binary.BigEndian.PutUint16(c.method(t, "run", "(I)I").code[pc+1:], uint16(c.cpCount))
		}, 1},
		{"wrong-tag", func(out []byte, c staticsClass) { out[c.entry(t, ref).offset] = 11 }, 1},
		{"zero-owner", func(out []byte, c staticsClass) { binary.BigEndian.PutUint16(out[c.entry(t, ref).offset+1:], 0) }, 1},
		{"zero-name-type", func(out []byte, c staticsClass) { binary.BigEndian.PutUint16(out[c.entry(t, ref).offset+3:], 0) }, 1},
		{"missing", func(out []byte, c staticsClass) {
			// Rewrite only f's NameAndType name. The class declares absent()I,
			// so the resulting exact lookup absent(I)I is genuinely missing.
			nat := c.entry(t, c.u2(t, c.entry(t, ref).offset+3))
			binary.BigEndian.PutUint16(out[nat.offset+1:], c.utfIndex(t, "absent"))
		}, 3},
		{"resolved-static", func(out []byte, c staticsClass) {
			m := c.method(t, "f", "(I)I")
			binary.BigEndian.PutUint16(out[m.accessOffset:], m.access|accStatic)
		}, 4},
		{"resolved-private", func(out []byte, c staticsClass) {
			m := c.method(t, "f", "(I)I")
			binary.BigEndian.PutUint16(out[m.accessOffset:], (m.access&^accessMask)|accPrivate)
		}, 4},
		{"resolved-synchronized-selected", func(out []byte, c staticsClass) {
			m := c.method(t, "f", "(I)I")
			binary.BigEndian.PutUint16(out[m.accessOffset:], m.access|verifyM4cSynchronized)
		}, 4},
		{"resolved-native-selected", func(out []byte, c staticsClass) {
			m := c.method(t, "f", "(I)I")
			binary.BigEndian.PutUint16(out[m.accessOffset:], m.access|accNative)
		}, 4},
		{"resolved-abstract-selected", func(out []byte, c staticsClass) {
			m := c.method(t, "f", "(I)I")
			binary.BigEndian.PutUint16(out[m.accessOffset:], m.access|verifyM4cAbstract)
		}, 4},
		{"selected-no-code", func(out []byte, c staticsClass) {
			m := c.method(t, "f", "(I)I")
			binary.BigEndian.PutUint16(out[m.codeNameOffset:], c.utfIndex(t, "SourceFile"))
		}, 4},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			bad := verifyM4bMutate(t, original, tc.make)
			verifyM4cAssertError(t, func() (Result, error) { return Run(bad, "run", []int32{2}, verifyM4cGasLimit) },
				"CallError(uint256,uint256)", tc.code, uint64(pc))
		})
	}
	truncated := verifyM4bRewriteAtEnd(t, original, "run", "(I)I", verifyM4cInvokevirtual)
	truncatedPC := len(parseStaticsClass(t, truncated).method(t, "run", "(I)I").code) - 1
	verifyM4cAssertError(t, func() (Result, error) { return Run(truncated, "run", []int32{2}, verifyM4cGasLimit) },
		"BytecodeError(uint256,uint256)", 2, uint64(truncatedPC))
	branchCode := []byte{0x03, 0x99, 0, 5, verifyM4cInvokevirtual, byte(ref >> 8), byte(ref), 0x03, 0xac}
	branch := verifyM4bRewriteCode(t, original, "run", "(I)I", branchCode)
	verifyM4cAssertError(t, func() (Result, error) { return Run(branch, "run", []int32{2}, verifyM4cGasLimit) },
		"BytecodeError(uint256,uint256)", 12, 1)

	// Constructor names are forbidden even when a real constructor with the
	// descriptor exists. This mutation is isolated to the call's NameAndType.
	ctorSource := compileJava(t, "VirtualCtor", `public class VirtualCtor {
        public VirtualCtor(int x){} public int f(int x){return x;} public static int run(int x){return new VirtualCtor(0).f(x);}
    }`)
	ctorParsed := parseStaticsClass(t, ctorSource)
	ctorRef, ctorPC := verifyM4bMemberInstruction(t, ctorParsed, ctorParsed.method(t, "run", "(I)I"), verifyM4cInvokevirtual, "f", "(I)I")
	badCtor := verifyM4bMutate(t, ctorSource, func(out []byte, c staticsClass) {
		nat := c.entry(t, c.u2(t, c.entry(t, ctorRef).offset+3))
		binary.BigEndian.PutUint16(out[nat.offset+1:], c.utfIndex(t, "<init>"))
	})
	verifyM4cAssertError(t, func() (Result, error) { return Run(badCtor, "run", []int32{2}, verifyM4cGasLimit) },
		"CallError(uint256,uint256)", 4, uint64(ctorPC))
}

func TestVerifyM4cNullVirtualChecksResolutionBeforeReceiver(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"nullvirtual/AbstractBase.java": `package nullvirtual; public abstract class AbstractBase { public abstract int f(); }`,
		"nullvirtual/NativeBase.java":   `package nullvirtual; public class NativeBase { public native int f(); }`,
		"nullvirtual/Missing.java":      `package nullvirtual; public class Missing { public int f(){return 1;} }`,
		"nullvirtual/Root.java": `package nullvirtual; public final class Root {
            public static int ordinary(){Root x=null;return x.f();} public int f(){return 1;}
            public static int abstractCall(){AbstractBase x=null;return x.f();}
            public static int nativeCall(){NativeBase x=null;return x.f();}
            public static int missingCall(){Missing x=null;return x.f();}
        }`,
	}, "nullvirtual/AbstractBase", "nullvirtual/NativeBase", "nullvirtual/Missing", "nullvirtual/Root")
	for _, method := range []string{"ordinary", "abstractCall", "nativeCall"} {
		t.Run(method, func(t *testing.T) {
			verifyM4cAssertException(t, func() (Result, error) {
				return RunClasses(verifyM4bBundle(classes), "nullvirtual/Root", method, nil, verifyM4cGasLimit)
			}, "java.lang.NullPointerException", 6)
		})
	}
	pc := verifyM4bOpcodePC(t, parseStaticsClass(t, classes["nullvirtual/Root"]).method(t, "missingCall", "()I").code, verifyM4cInvokevirtual, 0)
	verifyM4cAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["nullvirtual/Root"]}, "nullvirtual/Root", "missingCall", nil, verifyM4cGasLimit)
	}, "LinkError(uint256,uint256)", 4, uint64(pc))
}

func TestVerifyM4cVirtualReceiverArgumentReturnAndFinalChecksExact(t *testing.T) {
	original := compileJava(t, "VirtualKinds", `public class VirtualKinds {
        public VirtualKinds(){} public int f(int x){return x;} public VirtualKinds pass(VirtualKinds x){return x;}
        public static int call(){return new VirtualKinds().f(3);}
        public static int ref(){VirtualKinds x=new VirtualKinds();return x.pass(x)==x?1:0;}
    }`)
	c := parseStaticsClass(t, original)
	fRef, _ := verifyM4bMemberInstruction(t, c, c.method(t, "call", "()I"), verifyM4cInvokevirtual, "f", "(I)I")
	badReceiver := verifyM4bRewriteCode(t, original, "call", "()I", []byte{0x04, 0x06, verifyM4cInvokevirtual, byte(fRef >> 8), byte(fRef), 0xac})
	verifyM4cAssertError(t, func() (Result, error) { return Run(badReceiver, "call", nil, verifyM4cGasLimit) },
		"BytecodeError(uint256,uint256)", 14, 2)
	badArg := verifyM4bRewriteCode(t, original, "call", "()I", []byte{0x01, 0x01, verifyM4cInvokevirtual, byte(fRef >> 8), byte(fRef), 0xac})
	verifyM4cAssertError(t, func() (Result, error) { return Run(badArg, "call", nil, verifyM4cGasLimit) },
		"BytecodeError(uint256,uint256)", 14, 2)
	uninit := verifyM4bRewriteCode(t, original, "call", "()I", []byte{verifyM4bNew, byte(c.thisClass >> 8), byte(c.thisClass), 0x06, verifyM4cInvokevirtual, byte(fRef >> 8), byte(fRef), 0xac})
	verifyM4cAssertError(t, func() (Result, error) { return Run(uninit, "call", nil, verifyM4cGasLimit) },
		"BytecodeError(uint256,uint256)", 14, 4)

	mismatch := verifyM4bMutate(t, original, func(out []byte, c staticsClass) {
		m := c.method(t, "f", "(I)I")
		m.code[verifyM4bOpcodePC(t, m.code, 0xac, 0)] = 0xb0
	})
	verifyM4cAssertError(t, func() (Result, error) { return Run(mismatch, "call", nil, verifyM4cGasLimit) },
		"CallError(uint256,uint256)", 5, uint64(verifyM4bOpcodePC(t, parseStaticsClass(t, mismatch).method(t, "f", "(I)I").code, 0xb0, 0)))

	classes := compileBundleValidationJava(t, map[string]string{
		"finalslot/Base.java":  `package finalslot; public class Base { public Base(){} public int f(){return 1;} }`,
		"finalslot/Child.java": `package finalslot; public final class Child extends Base { public Child(){} public int f(){return 2;} }`,
		"finalslot/Root.java":  `package finalslot; public final class Root { static int call(Base b){return b.f();} public static int run(){return call(new Child());} }`,
	}, "finalslot/Base", "finalslot/Child", "finalslot/Root")
	rootPC := verifyM4bOpcodePC(t, parseStaticsClass(t, classes["finalslot/Root"]).method(t, "call", "(Lfinalslot/Base;)I").code, verifyM4cInvokevirtual, 0)
	classes["finalslot/Base"] = verifyM4bMutate(t, classes["finalslot/Base"], func(out []byte, c staticsClass) {
		m := c.method(t, "f", "()I")
		binary.BigEndian.PutUint16(out[m.accessOffset:], m.access|accFinal)
	})
	verifyM4cAssertError(t, func() (Result, error) {
		return RunClasses(verifyM4bBundle(classes), "finalslot/Root", "run", nil, verifyM4cGasLimit)
	}, "CallError(uint256,uint256)", 4, uint64(rootPC))
}

func TestVerifyM4cVirtualReferenceArgumentsAndReturnsAreAssignable(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"virtualrefs/A.java": `package virtualrefs; public class A { public A(){} }`,
		"virtualrefs/B.java": `package virtualrefs; public class B { public B(){} }`,
		"virtualrefs/Receiver.java": `package virtualrefs; public class Receiver {
            public Receiver(){} public A pass(A x){return x;} public A give(){return new A();}
            static int mention(){new B();return 0;}
        }`,
		"virtualrefs/Root.java": `package virtualrefs; public final class Root {
            public static int argument(){Receiver r=new Receiver();return r.pass(new A())==null?0:1;}
            public static int returns(){return new Receiver().give()==null?0:1;}
            static int mention(){new B();return 0;}
        }`,
	}, "virtualrefs/A", "virtualrefs/B", "virtualrefs/Receiver", "virtualrefs/Root")
	t.Run("incompatible-argument", func(t *testing.T) {
		root := verifyM4cRetargetAllocation(t, classes["virtualrefs/Root"], "argument", "virtualrefs/A", "virtualrefs/B")
		pc := verifyM4bOpcodePC(t, parseStaticsClass(t, root).method(t, "argument", "()I").code, verifyM4cInvokevirtual, 0)
		verifyM4cAssertError(t, func() (Result, error) {
			return RunClasses([][]byte{classes["virtualrefs/A"], classes["virtualrefs/B"], classes["virtualrefs/Receiver"], root}, "virtualrefs/Root", "argument", nil, verifyM4cGasLimit)
		}, "ReferenceError(uint256,uint256)", 2, uint64(pc))
	})
	t.Run("incompatible-return", func(t *testing.T) {
		receiver := verifyM4cRetargetAllocation(t, classes["virtualrefs/Receiver"], "give", "virtualrefs/A", "virtualrefs/B")
		returnPC := verifyM4bOpcodePC(t, parseStaticsClass(t, receiver).method(t, "give", "()Lvirtualrefs/A;").code, 0xb0, 0)
		verifyM4cAssertError(t, func() (Result, error) {
			return RunClasses([][]byte{classes["virtualrefs/A"], classes["virtualrefs/B"], receiver, classes["virtualrefs/Root"]}, "virtualrefs/Root", "returns", nil, verifyM4cGasLimit)
		}, "ReferenceError(uint256,uint256)", 2, uint64(returnPC))
	})
	// Invalid nonzero handles remain unforgeable through supported roots and
	// bytecode; this verifier never bypasses allocation/kind checks to fabricate one.
}

func TestVerifyM4cProtectedReceiverAndArrayReceiverOrderingExact(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"protectbase/Base.java": `package protectbase; public class Base { public Base(){} protected int f(){return 1;} }`,
		"protectsub/Child.java": `package protectsub; public class Child extends protectbase.Base {
            public Child(){} public static int call(){Child x=new Child();return x.f();}
        }`,
	}, "protectbase/Base", "protectsub/Child")
	child := classes["protectsub/Child"]
	child = verifyM4bRetargetAllocation(t, child, "call", "protectsub/Child", "protectbase/Base")
	// javac is permitted to use Child as the qualifying Methodref owner for its
	// inherited f. Retarget that edge explicitly to Base so receiver assignability
	// succeeds and the intended declaring-class protected check is isolated.
	child = verifyM4bMutate(t, child, func(out []byte, c staticsClass) {
		m := c.method(t, "call", "()I")
		ref, _ := verifyM4bMemberInstruction(t, c, m, verifyM4cInvokevirtual, "f", "()I")
		binary.BigEndian.PutUint16(out[c.entry(t, ref).offset+1:], verifyM4bClassIndex(t, c, "protectbase/Base"))
	})
	pc := verifyM4bOpcodePC(t, parseStaticsClass(t, child).method(t, "call", "()I").code, verifyM4cInvokevirtual, 0)
	verifyM4cAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["protectbase/Base"], child}, "protectsub/Child", "call", nil, verifyM4cGasLimit)
	}, "CallError(uint256,uint256)", 4, uint64(pc))

	arrayCall := compileJava(t, "ArrayVirtual", `public class ArrayVirtual {
        public ArrayVirtual(){} public int f(){return 9;} public static int run(){return new ArrayVirtual().f();}
    }`)
	ac := parseStaticsClass(t, arrayCall)
	callRef, _ := verifyM4bMemberInstruction(t, ac, ac.method(t, "run", "()I"), verifyM4cInvokevirtual, "f", "()I")
	arrayCall = verifyM4bRewriteCode(t, arrayCall, "run", "()I", []byte{0x04, 0xbc, 10, verifyM4cInvokevirtual, byte(callRef >> 8), byte(callRef), 0xac})
	// The symbolic ArrayVirtual.f()I resolves successfully, and the array is a
	// valid reference. Frozen M4c array deferral then wins over ordinary-object
	// receiver assignability, which is tested separately as ReferenceError(2).
	verifyM4cAssertError(t, func() (Result, error) { return Run(arrayCall, "run", nil, verifyM4cGasLimit) },
		"CallError(uint256,uint256)", 4, 3)

	// A missing bootstrap Object method fails symbolic resolution before the
	// ARRAY RECEIVER deferral; arrays do not gain fake Object APIs.
	objectAPI := compileJava(t, "ArrayObjectAPI", `public final class ArrayObjectAPI {
        public static int run(){Object x=new int[1];return x.hashCode();}
    }`)
	apiPC := verifyM4bOpcodePC(t, parseStaticsClass(t, objectAPI).method(t, "run", "()I").code, verifyM4cInvokevirtual, 0)
	verifyM4cAssertError(t, func() (Result, error) { return Run(objectAPI, "run", nil, verifyM4cGasLimit) },
		"CallError(uint256,uint256)", 3, uint64(apiPC))
}

func TestVerifyM4cCastTypeTestClassesArraysObjectIdentityAndNoClinit(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"types/Base.java":  `package types; public class Base { public Base(){} }`,
		"types/Child.java": `package types; public final class Child extends Base { public Child(){} }`,
		"types/Other.java": `package types; public final class Other { static int starts=1/0; public Other(){} }`,
		"types/Root.java": `package types; public final class Root {
            static int object(Object x){return x instanceof Object?1:0;}
            public static int run(){Child c=new Child();Base b=c;Object a=new int[2];
                Base same=(Base)b;int[] ints=(int[])a;
                return (same==c?10000:0)+(b instanceof Child?1000:0)+(b instanceof Base?100:0)
                    +(b instanceof Object?10:0)+(ints==a?1:0)+object(a);}
            public static int nulls(){Object x=null;return ((Base)x)==null && !(x instanceof Base)?1:0;}
            public static int noInit(){Object x=new Child();return x instanceof Other?0:1;}
            public static int arrayVsClass(){Object x=new int[1];return x instanceof Base?1:0;}
            public static int objectVsArray(){Object x=new Child();return x instanceof int[]?1:0;}
            public static int castArrayToClass(){Object x=new int[1];return ((Base)x)==null?0:1;}
            public static int castObjectToArray(){Object x=new Child();return ((int[])x).length;}
        }`,
	}, "types/Base", "types/Child", "types/Other", "types/Root")
	verifyM4cAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4bBundle(classes), "types/Root", "run", nil, verifyM4cGasLimit)
	}, 11112)
	verifyM4cAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4bBundle(classes), "types/Root", "nulls", nil, verifyM4cGasLimit)
	}, 1)
	// Resolving Other for instanceof must not execute its failing <clinit>.
	verifyM4cAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4bBundle(classes), "types/Root", "noInit", nil, verifyM4cGasLimit)
	}, 1)
	for _, method := range []string{"arrayVsClass", "objectVsArray"} {
		verifyM4cAssertValue(t, func() (Result, error) {
			return RunClasses(verifyM4bBundle(classes), "types/Root", method, nil, verifyM4cGasLimit)
		}, 0)
	}
	for _, method := range []string{"castArrayToClass", "castObjectToArray"} {
		verifyM4cAssertException(t, func() (Result, error) {
			return RunClasses(verifyM4bBundle(classes), "types/Root", method, nil, verifyM4cGasLimit)
		}, "java.lang.ClassCastException", 8)
	}
}

func TestVerifyM4cCastFailureInitializerWrappingAndOOGRemainExact(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"castfail/A.java": `package castfail; public final class A { public A(){} }`,
		"castfail/B.java": `package castfail; public final class B { public B(){} }`,
		"castfail/Root.java": `package castfail; public final class Root {
            public static int fail(){Object x=new A();B b=(B)x;return b==null?0:1;}
        }`,
		"castfail/Init.java": `package castfail; public final class Init {
            static int value=bad(); static int bad(){Object x=new A();B b=(B)x;return b==null?0:1;}
            public static int run(){return value;}
        }`,
	}, "castfail/A", "castfail/B", "castfail/Root", "castfail/Init")
	verifyM4cAssertException(t, func() (Result, error) {
		return RunClasses(verifyM4bBundle(classes), "castfail/Root", "fail", nil, verifyM4cGasLimit)
	}, "java.lang.ClassCastException", 8)
	verifyM4cAssertException(t, func() (Result, error) {
		return RunClasses(verifyM4bBundle(classes), "castfail/Init", "run", nil, verifyM4cGasLimit)
	}, "java.lang.ExceptionInInitializerError", 3)
	result, err := RunClasses(verifyM4bBundle(classes), "castfail/Root", "fail", nil, 1)
	if err == nil || !errors.Is(err, vm.ErrOutOfGas) || result.ExceptionClass != "" || len(result.RevertData) != 0 {
		t.Fatalf("result/error=%+v/%v, want unlabeled EVM out of gas", result, err)
	}
}

func TestVerifyM4cNullMissingTargetShortcutAndNonNullResolutionExact(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"missing/Missing.java": `package missing; public class Missing { }`,
		"missing/Root.java": `package missing; public final class Root {
            public static int nullCast(){Object x=null;return ((Missing)x)==null?1:0;}
            public static int nullTest(){Object x=null;return x instanceof Missing?1:0;}
            public static int objectCast(){Object x=new Object();return ((Missing)x)==null?1:0;}
            public static int objectTest(){Object x=new Object();return x instanceof Missing?1:0;}
        }`,
	}, "missing/Missing", "missing/Root")
	bundle := [][]byte{classes["missing/Root"]} // Deliberately omit well-formed Missing.
	verifyM4cAssertValue(t, func() (Result, error) { return RunClasses(bundle, "missing/Root", "nullCast", nil, verifyM4cGasLimit) }, 1)
	verifyM4cAssertValue(t, func() (Result, error) { return RunClasses(bundle, "missing/Root", "nullTest", nil, verifyM4cGasLimit) }, 0)
	for _, method := range []string{"objectCast", "objectTest"} {
		t.Run(method, func(t *testing.T) {
			m := parseStaticsClass(t, classes["missing/Root"]).namedMethod(t, method)
			pc := verifyM4cFirstTypeOpcode(t, m.code)
			verifyM4cAssertError(t, func() (Result, error) { return RunClasses(bundle, "missing/Root", method, nil, verifyM4cGasLimit) },
				"LinkError(uint256,uint256)", 4, uint64(pc))
		})
	}
}

func TestVerifyM4cInaccessibleCastTargetSkippedForNullRejectedForObject(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"castaccess/Target.java": `package castaccess; public class Target { public Target(){} }`,
		"castuser/Root.java": `package castuser; public final class Root {
            public static int nullTarget(){Object x=null;return ((castaccess.Target)x)==null?1:0;}
            public static int objectTarget(){Object x=new Object();return x instanceof castaccess.Target?1:0;}
        }`,
	}, "castaccess/Target", "castuser/Root")
	target := verifyM4bMutate(t, classes["castaccess/Target"], func(out []byte, c staticsClass) {
		flags := binary.BigEndian.Uint16(out[c.cpEnd:])
		binary.BigEndian.PutUint16(out[c.cpEnd:], flags&^accPublic)
	})
	bundle := [][]byte{target, classes["castuser/Root"]}
	verifyM4cAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "castuser/Root", "nullTarget", nil, verifyM4cGasLimit)
	}, 1)
	m := parseStaticsClass(t, classes["castuser/Root"]).method(t, "objectTarget", "()I")
	pc := verifyM4cFirstTypeOpcode(t, m.code)
	verifyM4cAssertError(t, func() (Result, error) {
		return RunClasses(bundle, "castuser/Root", "objectTarget", nil, verifyM4cGasLimit)
	}, "TypeError(uint256,uint256)", 2, uint64(pc))
}

func TestVerifyM4cDeferredInterfaceAndArrayTargetsRejectOnlyNonNull(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"deferred/I.java": `package deferred; public interface I { }`,
		"deferred/Root.java": `package deferred; public final class Root {
            public static int nullInterface(){Object x=null;return ((I)x)==null && !(x instanceof I)?1:0;}
            public static int objectInterface(){Object x=new Object();return x instanceof I?1:0;}
            public static int nullLongs(){Object x=null;return ((long[])x)==null && !(x instanceof long[])?1:0;}
            public static int objectLongs(){Object x=new Object();return x instanceof long[]?1:0;}
        }`,
	}, "deferred/I", "deferred/Root")
	verifyM4cAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4bBundle(classes), "deferred/Root", "nullInterface", nil, verifyM4cGasLimit)
	}, 1)
	verifyM4cAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4bBundle(classes), "deferred/Root", "nullLongs", nil, verifyM4cGasLimit)
	}, 1)
	// M4f-a supports interface targets; Object does not implement this empty I.
	verifyM4cAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4bBundle(classes), "deferred/Root", "objectInterface", nil, verifyM4cGasLimit)
	}, 0)
	// [J is supported from M5b-b; an ordinary Object is simply not a long[].
	verifyM5baJava8Outcome(t, verifyM4bBundle(classes), "deferred.Root", "objectLongs", nil, "value=0")
	verifyM4cAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4bBundle(classes), "deferred/Root", "objectLongs", nil, verifyM4cGasLimit)
	}, 0)
}

func TestVerifyM4cCastOperandsMalformedNamesKindsTruncationAndBranchesExact(t *testing.T) {
	original := compileJava(t, "TypeShapes", `public final class TypeShapes {
        static class Bad {} public static int cast(){Object x=null;return ((Bad)x)==null?1:0;}
        public static int test(){Object x=null;return x instanceof Bad?1:0;}
        public static int scalar(){int x=1;x=x+2;x=x+3;return x;}
    }`)
	for _, method := range []string{"cast", "test"} {
		t.Run(method, func(t *testing.T) {
			parsed := parseStaticsClass(t, original)
			m := parsed.method(t, method, "()I")
			pc := verifyM4cFirstTypeOpcode(t, m.code)
			ref := binary.BigEndian.Uint16(m.code[pc+1:])
			cases := []struct {
				name string
				make func([]byte, staticsClass)
			}{
				{"zero", func(out []byte, c staticsClass) {
					binary.BigEndian.PutUint16(c.method(t, method, "()I").code[pc+1:], 0)
				}},
				{"range", func(out []byte, c staticsClass) {
					binary.BigEndian.PutUint16(c.method(t, method, "()I").code[pc+1:], uint16(c.cpCount))
				}},
				{"wrong-tag", func(out []byte, c staticsClass) { out[c.entry(t, ref).offset] = 8 }},
				{"zero-name", func(out []byte, c staticsClass) { binary.BigEndian.PutUint16(out[c.entry(t, ref).offset+1:], 0) }},
			}
			for _, tc := range cases {
				t.Run(tc.name, func(t *testing.T) {
					bad := verifyM4bMutate(t, original, tc.make)
					verifyM4cAssertError(t, func() (Result, error) { return Run(bad, method, nil, verifyM4cGasLimit) },
						"TypeError(uint256,uint256)", 1, uint64(pc))
				})
			}
			badName := verifyM4cRetargetTypeToAppendedName(t, original, method, "[Qbad")
			verifyM4cAssertError(t, func() (Result, error) { return Run(badName, method, nil, verifyM4cGasLimit) },
				"TypeError(uint256,uint256)", 1, uint64(pc))
		})
	}

	// JVMS 4.9.1/4.11 limit an array type to 255 dimensions. Even with a null
	// operand, a 256-dimensional CONSTANT_Class name is structurally malformed.
	tooManyDimensions := verifyM4cRetargetTypeToAppendedName(t, original, "cast", strings.Repeat("[", 256)+"I")
	tooManyPC := verifyM4cFirstTypeOpcode(t, parseStaticsClass(t, tooManyDimensions).method(t, "cast", "()I").code)
	verifyM4cAssertError(t, func() (Result, error) {
		return Run(tooManyDimensions, "cast", nil, verifyM4cGasLimit)
	}, "TypeError(uint256,uint256)", 1, uint64(tooManyPC))

	parsed := parseStaticsClass(t, original)
	classIndex := verifyM4bClassIndex(t, parsed, "TypeShapes$Bad")
	for _, opcode := range []byte{verifyM4cCheckcast, verifyM4cInstanceof} {
		t.Run(fmt.Sprintf("opcode-%02x-int", opcode), func(t *testing.T) {
			intOperand := verifyM4bRewriteCode(t, original, "scalar", "()I", []byte{0x04, opcode, byte(classIndex >> 8), byte(classIndex), 0x03, 0xac})
			verifyM4cAssertError(t, func() (Result, error) { return Run(intOperand, "scalar", nil, verifyM4cGasLimit) },
				"BytecodeError(uint256,uint256)", 14, 1)
		})
		t.Run(fmt.Sprintf("opcode-%02x-truncated", opcode), func(t *testing.T) {
			truncated := verifyM4bRewriteAtEnd(t, original, "scalar", "()I", opcode)
			truncatedPC := len(parseStaticsClass(t, truncated).method(t, "scalar", "()I").code) - 1
			verifyM4cAssertError(t, func() (Result, error) { return Run(truncated, "scalar", nil, verifyM4cGasLimit) },
				"BytecodeError(uint256,uint256)", 2, uint64(truncatedPC))
		})
		t.Run(fmt.Sprintf("opcode-%02x-branch", opcode), func(t *testing.T) {
			branch := verifyM4bRewriteCode(t, original, "scalar", "()I", []byte{0x03, 0x99, 0, 5, opcode, byte(classIndex >> 8), byte(classIndex), 0x03, 0xac})
			verifyM4cAssertError(t, func() (Result, error) { return Run(branch, "scalar", nil, verifyM4cGasLimit) },
				"BytecodeError(uint256,uint256)", 12, 1)
		})
	}
}

func TestVerifyM4cJavaExceptionDecoderKind8CanonicalAndUnknownStrict(t *testing.T) {
	selector := crypto.Keccak256([]byte("JavaException(uint256)"))[:4]
	payload := append(append([]byte(nil), selector...), make([]byte, 32)...)
	payload[35] = 8
	if got, ok := decodeJavaException(payload); !ok || got != "java.lang.ClassCastException" {
		t.Fatalf("decode kind8=(%q,%v), want exact ClassCastException", got, ok)
	}
	for _, bad := range [][]byte{
		append([]byte(nil), payload[:35]...),
		append(append([]byte(nil), payload...), 0),
		func() []byte { out := append([]byte(nil), payload...); out[4] = 1; return out }(),
		func() []byte { out := append([]byte(nil), payload...); out[35] = 255; return out }(),
		func() []byte { out := append([]byte(nil), payload...); out[0] ^= 1; return out }(),
	} {
		if got, ok := decodeJavaException(bad); ok || got != "" {
			t.Fatalf("noncanonical/unknown payload %x decoded as (%q,%v)", bad, got, ok)
		}
	}
	// Previously known initializer outcome remains exact while adding kind 8.
	payload[35] = 3
	if got, ok := decodeJavaException(payload); !ok || got != "java.lang.ExceptionInInitializerError" {
		t.Fatalf("decode kind3=(%q,%v)", got, ok)
	}
}

func verifyM4cRetargetAllocation(t *testing.T, original []byte, method, from, to string) []byte {
	t.Helper()
	return verifyM4bMutate(t, original, func(out []byte, c staticsClass) {
		m := c.namedMethod(t, method)
		_, newPC := verifyM4bMemberInstruction(t, c, m, verifyM4bNew, from, "")
		toIndex := verifyM4bClassIndex(t, c, to)
		binary.BigEndian.PutUint16(m.code[newPC+1:], toIndex)
		constructorPC := -1
		for pc := newPC + 3; pc+2 < len(m.code); pc++ {
			if m.code[pc] != verifyM4bInvokespecial {
				continue
			}
			ref := binary.BigEndian.Uint16(m.code[pc+1:])
			if ref == 0 || int(ref) >= len(c.entries) || c.entries[ref].tag != 10 {
				continue
			}
			e := c.entry(t, ref)
			owner := c.entry(t, c.u2(t, e.offset+1))
			nat := c.entry(t, c.u2(t, e.offset+3))
			if owner.tag == 7 && nat.tag == 12 && c.utf8[c.u2(t, owner.offset+1)] == from &&
				c.utf8[c.u2(t, nat.offset+1)] == "<init>" {
				binary.BigEndian.PutUint16(out[e.offset+1:], toIndex)
				constructorPC = pc
				break
			}
		}
		if constructorPC < 0 {
			t.Fatalf("%s has no %s constructor after new at pc %d", method, from, newPC)
		}
	})
}

func verifyM4cFirstTypeOpcode(t *testing.T, code []byte) int {
	t.Helper()
	for pc, op := range code {
		if op == verifyM4cCheckcast || op == verifyM4cInstanceof {
			return pc
		}
	}
	t.Fatalf("no checkcast/instanceof in %x", code)
	return -1
}

func verifyM4cRetargetTypeToAppendedName(t *testing.T, original []byte, method, name string) []byte {
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
	parsed := parseStaticsClass(t, out)
	m := parsed.namedMethod(t, method)
	pc := verifyM4cFirstTypeOpcode(t, m.code)
	binary.BigEndian.PutUint16(m.code[pc+1:], uint16(c.cpCount+1))
	return out
}

func verifyM4cAssertValue(t *testing.T, run func() (Result, error), want int32) {
	t.Helper()
	result, err := run()
	if err != nil || result.ExceptionClass != "" || result.Value != want || result.GasUsed == 0 || len(result.RevertData) != 0 {
		t.Fatalf("result/error=%+v/%v, want value %d", result, err, want)
	}
}

func verifyM4cAssertException(t *testing.T, run func() (Result, error), want string, kind byte) {
	t.Helper()
	result, err := run()
	selector := crypto.Keccak256([]byte("JavaException(uint256)"))[:4]
	if err != nil || result.ExceptionClass != want || result.GasUsed == 0 || len(result.RevertData) != 36 ||
		!bytes.Equal(result.RevertData[:4], selector) || !bytes.Equal(result.RevertData[4:35], make([]byte, 31)) || result.RevertData[35] != kind {
		t.Fatalf("result/error=%+v/%v data=%x, want exact %s kind %d", result, err, result.RevertData, want, kind)
	}
}

func verifyM4cAssertError(t *testing.T, run func() (Result, error), signature string, code, pc uint64) {
	t.Helper()
	result, err := run()
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error=%+v/%v, want %s(%d,%d)", result, err, signature, code, pc)
	}
	selector := crypto.Keccak256([]byte(signature))[:4]
	if result.ExceptionClass != "" || result.GasUsed == 0 || len(result.RevertData) != 68 || !bytes.Equal(result.RevertData[:4], selector) {
		t.Fatalf("result=%+v data=%x, want exact %s payload", result, result.RevertData, signature)
	}
	if got := verifyM4cUint256(t, result.RevertData[4:36]); got != code {
		t.Fatalf("%s code=%d want %d data=%x", signature, got, code, result.RevertData)
	}
	if got := verifyM4cUint256(t, result.RevertData[36:]); got != pc {
		t.Fatalf("%s pc=%d want %d data=%x", signature, got, pc, result.RevertData)
	}
}

func verifyM4cUint256(t *testing.T, word []byte) uint64 {
	t.Helper()
	if len(word) != 32 || !bytes.Equal(word[:24], make([]byte, 24)) {
		t.Fatalf("noncanonical uint256 %x", word)
	}
	return binary.BigEndian.Uint64(word[24:])
}
