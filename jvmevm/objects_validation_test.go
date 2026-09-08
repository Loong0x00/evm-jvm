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
	verifyM4bGasLimit         = uint64(100_000_000)
	verifyM4bCapacityGasLimit = uint64(250_000_000)
	verifyM4bNew              = byte(0xbb)
	verifyM4bGetfield         = byte(0xb4)
	verifyM4bPutfield         = byte(0xb5)
	verifyM4bInvokevirtual    = byte(0xb6)
	verifyM4bInvokespecial    = byte(0xb7)
)

// Every class below is trusted, locally generated test input. Mutations start
// with javac --release 8 output and alter one named CP edge, flag, or bytecode
// site. Production still receives only opaque raw classfiles; these helpers do
// not expose a parser, heap, reference, or Java fallback API.

func TestVerifyM4bOrdinaryObjectsDefaultsIdentityHiddenLayoutAndConstantValue(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"objbasic/Base.java": `package objbasic; public class Base {
            public int inherited; public int hidden; public final int initialized; public final int ignored = 41;
            public Base(int x) { inherited = x; hidden = x + 1; initialized = x + 3; }
            public static int readIgnored(Base b) { return b.inherited; }
        }`,
		"objbasic/Child.java": `package objbasic; public final class Child extends Base {
            public int hidden; public int untouched; public int[] array; public Base ref;
            public Child(int x) { super(x); hidden = x + 2; }
        }`,
		"objbasic/Root.java": `package objbasic; public final class Root {
            static int inspect(Child c) {
                return c.inherited * 100000 + ((Base)c).hidden * 10000 + c.hidden * 1000
                    + c.untouched * 100 + (c.array == null ? 10 : 0)
                    + (c.ref == null ? 1 : 0) + Base.readIgnored(c) + c.initialized;
            }
            public static int run(int x) {
                Child a = new Child(x); Child alias = a; Child b = new Child(x);
                return inspect(a) * 100 + (a == alias ? 10 : 0) + (a != b ? 1 : 0);
            }
        }`,
	}, "objbasic/Base", "objbasic/Child", "objbasic/Root")
	verifyM4bAssertNoVirtual(t, classes)
	// ignored has ConstantValue 41 in the classfile but is an instance field. Remove
	// its complete javac-generated assignment, then retarget the helper's ordinary
	// getfield from inherited to ignored. (A source-level read of a constant variable
	// would be inlined as Objects.requireNonNull plus 41 and would not test the heap.)
	base := verifyM4bMutate(t, classes["objbasic/Base"], func(out []byte, c staticsClass) {
		ctor := c.method(t, "<init>", "(I)V")
		ignoredRef, pc := verifyM4bMemberInstruction(t, c, ctor, verifyM4bPutfield, "ignored", "I")
		if pc < 3 || pc+2 >= len(ctor.code) {
			t.Fatalf("unexpected ignored assignment: %x", ctor.code)
		}
		for i := pc - 3; i <= pc+2; i++ {
			ctor.code[i] = 0
		}
		read := c.method(t, "readIgnored", "(Lobjbasic/Base;)I")
		_, readPC := verifyM4bMemberInstruction(t, c, read, verifyM4bGetfield, "inherited", "I")
		binary.BigEndian.PutUint16(read.code[readPC+1:], ignoredRef)
	})
	bundle := [][]byte{classes["objbasic/Child"], classes["objbasic/Root"], base}
	// inspect(3) = 345017; identity suffix = 11. The initialized final is
	// written legally by its declaring constructor while ignored stays zero.
	verifyM4bAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "objbasic/Root", "run", []int32{3}, verifyM4bGasLimit)
	}, 34_501_711)
}

func TestVerifyM4bBootstrapObjectAndRootObjectConstructorExecuteOrdinaryCode(t *testing.T) {
	// The first run uses the interpreter's bootstrap Object. A successful field
	// initialized after super() requires its one-byte Code{return} to run as an
	// ordinary constructor frame, not a host-side allocation shortcut.
	plain := compileJava(t, "BootstrapChild", `public final class BootstrapChild {
        int x; BootstrapChild(int v) { super(); x = v; }
        static int read(BootstrapChild b) { return b.x; }
        public static int run(int v) { return read(new BootstrapChild(v)); }
    }`)
	verifyM4bAssertValue(t, func() (Result, error) {
		return Run(plain, "run", []int32{17}, verifyM4bGasLimit)
	}, 17)

	// A supplied Object is never replaced. Its root constructor has initialized
	// local0 on entry (there is no superclass), can write its own field, and its
	// nontrivial Code must be interpreted before returning to the caller.
	classes := compileBundleValidationJava(t, map[string]string{
		"java/lang/Object.java": `package java.lang; public class Object {
            public int marker; public Object() { marker = 23; }
            public static int read(Object o) { return o.marker; }
        }`,
		"objectboot/Root.java": `package objectboot; public final class Root {
            public static int run() { return java.lang.Object.read(new java.lang.Object()); }
        }`,
	}, "java/lang/Object", "objectboot/Root")
	verifyM4bAssertNoVirtual(t, classes)
	verifyM4bAssertValue(t, func() (Result, error) {
		return RunClasses([][]byte{classes["objectboot/Root"], classes["java/lang/Object"]},
			"objectboot/Root", "run", nil, verifyM4bGasLimit)
	}, 23)
}

func TestVerifyM4bReferencesCrossStaticsFieldsArgumentsReturnsAndArrays(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"refs/Base.java":  `package refs; public class Base { public int x; Base(int v) { x=v; } }`,
		"refs/Child.java": `package refs; public final class Child extends Base { Child(int v){super(v);} }`,
		"refs/Box.java": `package refs; public final class Box {
            public Base base; public Object any; public int[] ints;
        }`,
		"refs/Root.java": `package refs; public final class Root {
            static Object shared; static Base pass(Base b){return b;} static Object passObject(Object o){return o;}
            static int read(Base b){return b.x;} static int length(int[] a){return a.length;}
            public static int run(int v) {
                Child c=new Child(v); Box b=new Box(); int[] a=new int[2];
                b.base=pass(c); b.any=passObject(a); b.ints=a; shared=c; a[0]=9;
                return read(b.base)*1000 + (b.any==a?100:0) + (shared==c?10:0)
                    + length(b.ints)+a[0];
            }
        }`,
	}, "refs/Base", "refs/Child", "refs/Box", "refs/Root")
	verifyM4bAssertNoVirtual(t, classes)
	verifyM4bAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4bBundle(classes), "refs/Root", "run", []int32{7}, verifyM4bGasLimit)
	}, 7121)
}

func TestVerifyM4bThisSuperChainingPrivateHelpersAndACCSuperSelection(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"direct/Grand.java": `package direct; public class Grand {
            public int x; public Grand(int v){x=v;} public int pick(){return x+1;}
        }`,
		"direct/Parent.java": `package direct; public class Parent extends Grand {
            public Parent(int v){super(v);} public int pick(){return x+2;}
        }`,
		"direct/Child.java": `package direct; public final class Child extends Parent {
            public Child(){this(4);} public Child(int v){super(v); x=secret(v,2);}
            private int secret(int a,int n){return n==0?a:secret(a+1,n-1);}
            private int choose(){return super.pick();}
            static int read(Child c){return c.choose();} static int mention(){new Grand(0);return 0;}
        }`,
		"direct/Root.java": `package direct; public final class Root {
            public static int run(){return Child.read(new Child());}
        }`,
	}, "direct/Grand", "direct/Parent", "direct/Child", "direct/Root")
	verifyM4bAssertNoVirtual(t, classes)
	verifyM4bAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4bBundle(classes), "direct/Root", "run", nil, verifyM4bGasLimit)
	}, 8)

	// Under ACC_SUPER, changing Child.choose's symbolic owner from Parent to
	// Grand must still begin selection at Child's direct superclass and call
	// Parent.pick, rather than bypassing it to Grand.pick.
	child := verifyM4bMutate(t, classes["direct/Child"], func(out []byte, c staticsClass) {
		m := c.method(t, "choose", "()I")
		ref, _ := verifyM4bMemberInstruction(t, c, m, verifyM4bInvokespecial, "pick", "()I")
		binary.BigEndian.PutUint16(out[c.entry(t, ref).offset+1:], verifyM4bClassIndex(t, c, "direct/Grand"))
	})
	mutated := map[string][]byte{}
	for name, data := range classes {
		mutated[name] = data
	}
	mutated["direct/Child"] = child
	verifyM4bAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4bBundle(mutated), "direct/Root", "run", nil, verifyM4bGasLimit)
	}, 8)
}

func TestVerifyM4bConstructorAliasesAndImmediateCallerInitialization(t *testing.T) {
	original := compileJava(t, "AliasLifecycle", `public final class AliasLifecycle {
        int value; AliasLifecycle(int x){super();value=x;}
        static int read(AliasLifecycle a){return a.value;}
        public static int run(int x){int pad=x+1;pad=pad+2;pad=pad+3;return read(new AliasLifecycle(x))+pad-pad;}
    }`)
	parsed := parseStaticsClass(t, original)
	run := parsed.method(t, "run", "(I)I")
	newRef, _ := verifyM4bMemberInstruction(t, parsed, run, verifyM4bNew, "AliasLifecycle", "")
	ctorRef, _ := verifyM4bMemberInstruction(t, parsed, run, verifyM4bInvokespecial, "<init>", "(I)V")
	readRef, _ := verifyM4bMemberInstruction(t, parsed, run, 0xb8, "read", "(LAliasLifecycle;)I")
	// Keep aliases both in a reference local and on the caller stack while the
	// constructor frame runs. Only its immediate caller's aliases become usable
	// when invokespecial returns.
	code := []byte{
		verifyM4bNew, byte(newRef >> 8), byte(newRef), 0x59, 0x4c, 0x59, 0x1a,
		verifyM4bInvokespecial, byte(ctorRef >> 8), byte(ctorRef), 0x2b, 0xa6, 0, 8,
		0x2b, 0xb8, byte(readRef >> 8), byte(readRef), 0xac, 0x02, 0xac,
	}
	classfile := verifyM4bRewriteCode(t, original, "run", "(I)I", code)
	verifyM4bAssertValue(t, func() (Result, error) {
		return Run(classfile, "run", []int32{29}, verifyM4bGasLimit)
	}, 29)
}

func TestVerifyM4bOwnFieldBeforeSuperIsTheOnlyUninitializedThisFieldException(t *testing.T) {
	original := compileJava(t, "PreSuper", `public final class PreSuper {
        int x; PreSuper(int v){super();x=v;} static int read(PreSuper p){return p.x;}
        public static int run(int v){return read(new PreSuper(v));}
    }`)
	parsed := parseStaticsClass(t, original)
	ctor := parsed.method(t, "<init>", "(I)V")
	objectCtor, _ := verifyM4bMemberInstruction(t, parsed, ctor, verifyM4bInvokespecial, "<init>", "()V")
	fieldRef, _ := verifyM4bMemberInstruction(t, parsed, ctor, verifyM4bPutfield, "x", "I")
	code := []byte{0x2a, 0x1b, verifyM4bPutfield, byte(fieldRef >> 8), byte(fieldRef),
		0x2a, verifyM4bInvokespecial, byte(objectCtor >> 8), byte(objectCtor), 0xb1}
	allowed := verifyM4bRewriteCode(t, original, "<init>", "(I)V", code)
	verifyM4bAssertValue(t, func() (Result, error) {
		return Run(allowed, "run", []int32{31}, verifyM4bGasLimit)
	}, 31)

	getBeforeSuper := []byte{0x2a, verifyM4bGetfield, byte(fieldRef >> 8), byte(fieldRef), 0x57,
		0x2a, verifyM4bInvokespecial, byte(objectCtor >> 8), byte(objectCtor), 0xb1}
	bad := verifyM4bRewriteCode(t, original, "<init>", "(I)V", getBeforeSuper)
	verifyM4bAssertError(t, func() (Result, error) {
		return Run(bad, "run", []int32{31}, verifyM4bGasLimit)
	}, "BytecodeError(uint256,uint256)", 14, 1)
}

func TestVerifyM4bUninitializedReferencesCannotEscapeOrBeReused(t *testing.T) {
	original := compileJava(t, "NoEscape", `public final class NoEscape {
        static NoEscape shared; int x; NoEscape(){super();shared=this;x=1;}
        static int read(NoEscape n){return n.x;} public static int run(){int p=1;p=p+2;p=p+3;return read(new NoEscape())+p-p;}
    }`)
	parsed := parseStaticsClass(t, original)
	ctor := parsed.method(t, "<init>", "()V")
	_, superPC := verifyM4bMemberInstruction(t, parsed, ctor, verifyM4bInvokespecial, "<init>", "()V")
	_, putstaticPC := verifyM4bMemberInstruction(t, parsed, ctor, opPutstatic, "shared", "LNoEscape;")
	// Nop only the super call. putstatic is now the first consuming use of
	// uninitialized this and must fail before the later malformed return.
	escape := verifyM4bMutate(t, original, func(out []byte, c staticsClass) {
		m := c.method(t, "<init>", "()V")
		m.code[superPC], m.code[superPC+1], m.code[superPC+2] = 0, 0, 0
	})
	verifyM4bAssertError(t, func() (Result, error) {
		return Run(escape, "run", nil, verifyM4bGasLimit)
	}, "BytecodeError(uint256,uint256)", 14, uint64(putstaticPC))

	// A second constructor invocation on the initialized alias is forbidden.
	run := parsed.method(t, "run", "()I")
	newRef, _ := verifyM4bMemberInstruction(t, parsed, run, verifyM4bNew, "NoEscape", "")
	ctorRef, _ := verifyM4bMemberInstruction(t, parsed, run, verifyM4bInvokespecial, "<init>", "()V")
	repeatedCode := []byte{verifyM4bNew, byte(newRef >> 8), byte(newRef), 0x59,
		verifyM4bInvokespecial, byte(ctorRef >> 8), byte(ctorRef), 0x59}
	secondPC := len(repeatedCode)
	repeatedCode = append(repeatedCode, verifyM4bInvokespecial, byte(ctorRef>>8), byte(ctorRef), 0x57, 0x04, 0xac)
	repeated := verifyM4bRewriteCode(t, original, "run", "()I", repeatedCode)
	verifyM4bAssertError(t, func() (Result, error) {
		return Run(repeated, "run", nil, verifyM4bGasLimit)
	}, "BytecodeError(uint256,uint256)", 14, uint64(secondPC))
}

func TestVerifyM4bConstructorOwnerAndReturnLifecycleErrorsAreExact(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"lifecycle/A.java": `package lifecycle; public class A { public A(){super();} }`,
		"lifecycle/B.java": `package lifecycle; public class B { public B(){super();} }`,
		"lifecycle/Root.java": `package lifecycle; public final class Root {
            public static int run(){new A();return 1;} static int mention(){new B();return 0;}
        }`,
	}, "lifecycle/A", "lifecycle/B", "lifecycle/Root")
	root := classes["lifecycle/Root"]
	rootParsed := parseStaticsClass(t, root)
	run := rootParsed.method(t, "run", "()I")
	ctorRef, ctorPC := verifyM4bMemberInstruction(t, rootParsed, run, verifyM4bInvokespecial, "<init>", "()V")
	wrongOwner := verifyM4bMutate(t, root, func(out []byte, c staticsClass) {
		binary.BigEndian.PutUint16(out[c.entry(t, ctorRef).offset+1:], verifyM4bClassIndex(t, c, "lifecycle/B"))
	})
	verifyM4bAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["lifecycle/A"], classes["lifecycle/B"], wrongOwner},
			"lifecycle/Root", "run", nil, verifyM4bGasLimit)
	}, "ObjectError(uint256,uint256)", 3, uint64(ctorPC))

	a := classes["lifecycle/A"]
	aParsed := parseStaticsClass(t, a)
	aCtor := aParsed.method(t, "<init>", "()V")
	_, superPC := verifyM4bMemberInstruction(t, aParsed, aCtor, verifyM4bInvokespecial, "<init>", "()V")
	noSuper := verifyM4bMutate(t, a, func(out []byte, c staticsClass) {
		m := c.method(t, "<init>", "()V")
		// Consume the transported uninitialized-this value so the intended missing
		// super lifecycle error wins over an unrelated nonempty-return-stack error.
		m.code[superPC], m.code[superPC+1], m.code[superPC+2] = 0x57, 0, 0
	})
	returnPC := verifyM4bOpcodePC(t, parseStaticsClass(t, noSuper).method(t, "<init>", "()V").code, 0xb1, 0)
	verifyM4bAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{root, noSuper}, "lifecycle/Root", "run", nil, verifyM4bGasLimit)
	}, "ObjectError(uint256,uint256)", 3, uint64(returnPC))
}

func TestVerifyM4bNullWrongKindWrongClassAndValueKindsAreExact(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"kinds/A.java": `package kinds; public class A { public int x; public A(){x=3;} }`,
		"kinds/B.java": `package kinds; public class B { public int x; public B(){x=4;} }`,
		"kinds/Root.java": `package kinds; public final class Root {
            static int read(A a){return a.x;} static A pass(A a){return a;}
            public static int nullField(){A a=null;return a.x;}
            public static int good(){return read(pass(new A()));}
            public static int arrayReceiver(){return read(new A());}
            public static int wrongClass(){return read(new A());}
            static A give(){int p=1;p=p+2;p=p+3;return new A();}
            public static int wrongReturn(){return read(give());}
            static int mention(){new B();return 0;}
        }`,
	}, "kinds/A", "kinds/B", "kinds/Root")
	verifyM4bAssertException(t, func() (Result, error) {
		return RunClasses(verifyM4bBundle(classes), "kinds/Root", "nullField", nil, verifyM4bGasLimit)
	}, "java.lang.NullPointerException", 6)

	arrayRoot := verifyM4bMutate(t, classes["kinds/Root"], func(out []byte, c staticsClass) {
		m := c.method(t, "arrayReceiver", "()I")
		_, pc := verifyM4bMemberInstruction(t, c, m, verifyM4bNew, "kinds/A", "")
		m.code[pc], m.code[pc+1], m.code[pc+2] = 0x04, 0xbc, 10
		// Remove dup + A.<init>; otherwise the initialized array is rejected as a
		// constructor receiver before it reaches the intended typed call boundary.
		m.code[pc+3], m.code[pc+4], m.code[pc+5], m.code[pc+6] = 0, 0, 0, 0
	})
	verifyM4bAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["kinds/A"], classes["kinds/B"], arrayRoot},
			"kinds/Root", "arrayReceiver", nil, verifyM4bGasLimit)
	}, "ReferenceError(uint256,uint256)", 1, uint64(verifyM4bOpcodePC(t,
		parseStaticsClass(t, arrayRoot).method(t, "arrayReceiver", "()I").code, 0xb8, 0)))

	wrong := verifyM4bRetargetAllocation(t, classes["kinds/Root"], "wrongClass", "kinds/A", "kinds/B")
	callPC := verifyM4bOpcodePC(t, parseStaticsClass(t, wrong).method(t, "wrongClass", "()I").code, 0xb8, 0)
	verifyM4bAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["kinds/A"], classes["kinds/B"], wrong},
			"kinds/Root", "wrongClass", nil, verifyM4bGasLimit)
	}, "ReferenceError(uint256,uint256)", 2, uint64(callPC))
	wrongReturn := verifyM4bRetargetAllocation(t, classes["kinds/Root"], "give", "kinds/A", "kinds/B")
	returnPC := verifyM4bOpcodePC(t, parseStaticsClass(t, wrongReturn).method(t, "give", "()Lkinds/A;").code, 0xb0, 0)
	verifyM4bAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["kinds/A"], classes["kinds/B"], wrongReturn},
			"kinds/Root", "wrongReturn", nil, verifyM4bGasLimit)
	}, "ReferenceError(uint256,uint256)", 2, uint64(returnPC))

	giveParsed := parseStaticsClass(t, classes["kinds/Root"])
	give := giveParsed.method(t, "give", "()Lkinds/A;")
	giveNew, _ := verifyM4bMemberInstruction(t, giveParsed, give, verifyM4bNew, "kinds/A", "")
	uninitializedReturn := verifyM4bRewriteCode(t, classes["kinds/Root"], "give", "()Lkinds/A;",
		[]byte{verifyM4bNew, byte(giveNew >> 8), byte(giveNew), 0xb0})
	verifyM4bAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["kinds/A"], uninitializedReturn}, "kinds/Root", "wrongReturn", nil, verifyM4bGasLimit)
	}, "BytecodeError(uint256,uint256)", 14, 3)

	// Invalid nonzero handles cannot be forged by legal roots or bytecode: all
	// ref-producing instructions are allocation/null/typed transport. Code1's
	// invalid-handle branch is therefore reviewed defensively rather than exposed
	// through a production test hook.
}

func TestVerifyM4bFieldResolutionMalformedCPAccessFinalAndCacheChecks(t *testing.T) {
	original := compileJava(t, "FieldObject", `public final class FieldObject {
        public int value; public FieldObject(){}
        public static int run(int x){FieldObject o=new FieldObject();int before=o.value;o.value=x;return before+o.value;}
    }`)
	parsed := parseStaticsClass(t, original)
	run := parsed.method(t, "run", "(I)I")
	_, getPC := verifyM4bMemberInstruction(t, parsed, run, verifyM4bGetfield, "value", "I")
	fieldRef, putPC := verifyM4bMemberInstruction(t, parsed, run, verifyM4bPutfield, "value", "I")

	malformed := []struct {
		name string
		make func([]byte, staticsClass)
	}{
		{"operand-zero", func(out []byte, c staticsClass) {
			binary.BigEndian.PutUint16(c.method(t, "run", "(I)I").code[getPC+1:], 0)
		}},
		{"operand-range", func(out []byte, c staticsClass) {
			binary.BigEndian.PutUint16(c.method(t, "run", "(I)I").code[getPC+1:], uint16(c.cpCount))
		}},
		{"wrong-tag", func(out []byte, c staticsClass) { out[c.entry(t, fieldRef).offset] = 10 }},
		{"zero-owner", func(out []byte, c staticsClass) { binary.BigEndian.PutUint16(out[c.entry(t, fieldRef).offset+1:], 0) }},
		{"zero-name-type", func(out []byte, c staticsClass) { binary.BigEndian.PutUint16(out[c.entry(t, fieldRef).offset+3:], 0) }},
	}
	for _, tc := range malformed {
		t.Run(tc.name, func(t *testing.T) {
			bad := verifyM4bMutate(t, original, tc.make)
			verifyM4bAssertError(t, func() (Result, error) {
				return Run(bad, "run", []int32{8}, verifyM4bGasLimit)
			}, "FieldError(uint256,uint256)", 1, uint64(getPC))
		})
	}

	final := verifyM4bMutate(t, original, func(out []byte, c staticsClass) {
		f := c.field(t, "value", "I")
		binary.BigEndian.PutUint16(out[f.accessOffset:], f.access|accFinal)
	})
	// getfield resolves/caches the member first; the later putfield must still
	// recheck the final-write rule at its own PC.
	verifyM4bAssertError(t, func() (Result, error) {
		return Run(final, "run", []int32{8}, verifyM4bGasLimit)
	}, "FieldError(uint256,uint256)", 4, uint64(putPC))
}

func TestVerifyM4bFieldAndSpecialResolutionErrorCodes(t *testing.T) {
	original := compileJava(t, "MemberErrors", `public final class MemberErrors {
        int value; int absent; MemberErrors(){super();}
        private int helper(){return value;} static int anchor(){return 0;}
        public static int field(){return new MemberErrors().value;}
        public static int call(){return new MemberErrors().helper();}
    }`)
	parsed := parseStaticsClass(t, original)
	fieldMethod := parsed.method(t, "field", "()I")
	fieldRef, fieldPC := verifyM4bMemberInstruction(t, parsed, fieldMethod, verifyM4bGetfield, "value", "I")
	callMethod := parsed.method(t, "call", "()I")
	callRef, callPC := verifyM4bMemberInstruction(t, parsed, callMethod, verifyM4bInvokespecial, "helper", "()I")

	missingField := verifyM4bMutate(t, original, func(out []byte, c staticsClass) {
		nat := c.entry(t, c.u2(t, c.entry(t, fieldRef).offset+3))
		binary.BigEndian.PutUint16(out[nat.offset+1:], c.utfIndex(t, "anchor"))
	})
	verifyM4bAssertError(t, func() (Result, error) { return Run(missingField, "field", nil, verifyM4bGasLimit) },
		"FieldError(uint256,uint256)", 2, uint64(fieldPC))
	staticField := verifyM4bMutate(t, original, func(out []byte, c staticsClass) {
		f := c.field(t, "value", "I")
		binary.BigEndian.PutUint16(out[f.accessOffset:], f.access|accStatic)
	})
	verifyM4bAssertError(t, func() (Result, error) { return Run(staticField, "field", nil, verifyM4bGasLimit) },
		"FieldError(uint256,uint256)", 3, uint64(fieldPC))

	missingCall := verifyM4bMutate(t, original, func(out []byte, c staticsClass) {
		nat := c.entry(t, c.u2(t, c.entry(t, callRef).offset+3))
		binary.BigEndian.PutUint16(out[nat.offset+1:], c.utfIndex(t, "absent"))
	})
	verifyM4bAssertError(t, func() (Result, error) { return Run(missingCall, "call", nil, verifyM4bGasLimit) },
		"CallError(uint256,uint256)", 3, uint64(callPC))
	staticCall := verifyM4bMutate(t, original, func(out []byte, c staticsClass) {
		m := c.method(t, "helper", "()I")
		binary.BigEndian.PutUint16(out[m.accessOffset:], m.access|accStatic)
	})
	verifyM4bAssertError(t, func() (Result, error) { return Run(staticCall, "call", nil, verifyM4bGasLimit) },
		"CallError(uint256,uint256)", 4, uint64(callPC))
}

func TestVerifyM4bProtectedReceiverAndPrivateDirectAccessRules(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"accessbase/Base.java": `package accessbase; public class Base {
            protected int value; public Base(){value=4;} protected int method(){return 5;}
        }`,
		"accesssub/Child.java": `package accesssub; public final class Child extends accessbase.Base {
            Child(){super();} private int direct(){return super.method();}
            public static int good(){Child c=new Child();return c.value*10+c.direct();}
            public static int bad(){Child c=new Child();return c.value;}
        }`,
	}, "accessbase/Base", "accesssub/Child")
	verifyM4bAssertNoVirtual(t, classes)
	verifyM4bAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4bBundle(classes), "accesssub/Child", "good", nil, verifyM4bGasLimit)
	}, 45)

	childParsed := parseStaticsClass(t, classes["accesssub/Child"])
	_, specialPC := verifyM4bMemberInstruction(t, childParsed, childParsed.method(t, "direct", "()I"), verifyM4bInvokespecial, "method", "()I")
	privateMethod := verifyM4bMutate(t, classes["accessbase/Base"], func(out []byte, c staticsClass) {
		m := c.method(t, "method", "()I")
		binary.BigEndian.PutUint16(out[m.accessOffset:], (m.access&^accessMask)|accPrivate)
	})
	verifyM4bAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["accesssub/Child"], privateMethod}, "accesssub/Child", "good", nil, verifyM4bGasLimit)
	}, "CallError(uint256,uint256)", 4, uint64(specialPC))

	privateField := verifyM4bMutate(t, classes["accessbase/Base"], func(out []byte, c staticsClass) {
		f := c.field(t, "value", "I")
		binary.BigEndian.PutUint16(out[f.accessOffset:], (f.access&^accessMask)|accPrivate)
	})
	privateFieldPC := verifyM4bOpcodePC(t, childParsed.method(t, "bad", "()I").code, verifyM4bGetfield, 0)
	verifyM4bAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["accesssub/Child"], privateField}, "accesssub/Child", "bad", nil, verifyM4bGasLimit)
	}, "FieldError(uint256,uint256)", 4, uint64(privateFieldPC))

	// Retarget bad's allocation/constructor and the fieldref's symbolic owner to
	// Base. A Base receiver satisfies field resolution but is not Child-or-subclass,
	// so the intended cross-package protected receiver check is the first failure.
	badChild := verifyM4bRetargetAllocation(t, classes["accesssub/Child"], "bad", "accesssub/Child", "accessbase/Base")
	badChild = verifyM4bMutate(t, badChild, func(out []byte, c staticsClass) {
		m := c.method(t, "bad", "()I")
		fieldRef, _ := verifyM4bMemberInstruction(t, c, m, verifyM4bGetfield, "value", "I")
		binary.BigEndian.PutUint16(out[c.entry(t, fieldRef).offset+1:], verifyM4bClassIndex(t, c, "accessbase/Base"))
	})
	badPC := verifyM4bOpcodePC(t, parseStaticsClass(t, badChild).method(t, "bad", "()I").code, verifyM4bGetfield, 0)
	verifyM4bAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["accessbase/Base"], badChild}, "accesssub/Child", "bad", nil, verifyM4bGasLimit)
	}, "FieldError(uint256,uint256)", 4, uint64(badPC))
}

func TestVerifyM4bFinalWriteUsesDeclaringConstructorNotReceiverIdentity(t *testing.T) {
	original := compileJava(t, "FinalOther", `public final class FinalOther {
        int value; static int seen; FinalOther(){super();}
        FinalOther(int x){super();FinalOther other=new FinalOther();other.value=x;seen=other.value;}
        public static int run(int x){new FinalOther(x);return seen;}
    }`)
	final := verifyM4bMutate(t, original, func(out []byte, c staticsClass) {
		f := c.field(t, "value", "I")
		binary.BigEndian.PutUint16(out[f.accessOffset:], f.access|accFinal)
	})
	verifyM4bAssertValue(t, func() (Result, error) { return Run(final, "run", []int32{27}, verifyM4bGasLimit) }, 27)
}

func TestVerifyM4bSubclassCannotWriteAncestorFinalEvenAfterCachedRead(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"finalobj/Parent.java": `package finalobj; public class Parent { public int value; public Parent(){value=2;} }`,
		"finalobj/Child.java": `package finalobj; public final class Child extends Parent {
            Child(int x){super();int old=value;value=x;} static int read(Child c){return c.value;}
            public static int run(int x){return read(new Child(x));}
        }`,
	}, "finalobj/Parent", "finalobj/Child")
	childParsed := parseStaticsClass(t, classes["finalobj/Child"])
	_, putPC := verifyM4bMemberInstruction(t, childParsed, childParsed.method(t, "<init>", "(I)V"), verifyM4bPutfield, "value", "I")
	parent := verifyM4bMutate(t, classes["finalobj/Parent"], func(out []byte, c staticsClass) {
		f := c.field(t, "value", "I")
		binary.BigEndian.PutUint16(out[f.accessOffset:], f.access|accFinal)
	})
	verifyM4bAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["finalobj/Child"], parent}, "finalobj/Child", "run", []int32{9}, verifyM4bGasLimit)
	}, "FieldError(uint256,uint256)", 4, uint64(putPC))
}

func TestVerifyM4bNewAndSpecialMalformedOperandsAndBranchTargets(t *testing.T) {
	original := compileJava(t, "ObjectShapes", `public final class ObjectShapes {
        int[] descriptorAnchor; ObjectShapes(){super();}
        private int secret(){return 7;} public static int run(){return new ObjectShapes().secret();}
    }`)
	parsed := parseStaticsClass(t, original)
	run := parsed.method(t, "run", "()I")
	newRef, newPC := verifyM4bMemberInstruction(t, parsed, run, verifyM4bNew, "ObjectShapes", "")
	callRef, callPC := verifyM4bMemberInstruction(t, parsed, run, verifyM4bInvokespecial, "secret", "()I")
	newCases := []struct {
		name string
		make func() []byte
	}{
		{"zero", func() []byte {
			return verifyM4bMutate(t, original, func(out []byte, c staticsClass) {
				binary.BigEndian.PutUint16(c.method(t, "run", "()I").code[newPC+1:], 0)
			})
		}},
		{"range", func() []byte {
			return verifyM4bMutate(t, original, func(out []byte, c staticsClass) {
				binary.BigEndian.PutUint16(c.method(t, "run", "()I").code[newPC+1:], uint16(c.cpCount))
			})
		}},
		{"wrong-tag", func() []byte {
			return verifyM4bAliasNewClass(t, original, "run", func(out []byte, c staticsClass, alias uint16) {
				out[c.entry(t, alias).offset] = 8
			})
		}},
		{"zero-name", func() []byte {
			return verifyM4bAliasNewClass(t, original, "run", func(out []byte, c staticsClass, alias uint16) {
				binary.BigEndian.PutUint16(out[c.entry(t, alias).offset+1:], 0)
			})
		}},
		{"array-name", func() []byte {
			return verifyM4bAliasNewClass(t, original, "run", func(out []byte, c staticsClass, alias uint16) {
				binary.BigEndian.PutUint16(out[c.entry(t, alias).offset+1:], c.utfIndex(t, "[I"))
			})
		}},
	}
	for _, tc := range newCases {
		t.Run("new-"+tc.name, func(t *testing.T) {
			bad := tc.make()
			verifyM4bAssertError(t, func() (Result, error) { return Run(bad, "run", nil, verifyM4bGasLimit) },
				"ObjectError(uint256,uint256)", 1, uint64(newPC))
		})
	}
	specialCases := []struct {
		name string
		make func([]byte, staticsClass)
	}{
		{"zero", func(out []byte, c staticsClass) {
			binary.BigEndian.PutUint16(c.method(t, "run", "()I").code[callPC+1:], 0)
		}},
		{"range", func(out []byte, c staticsClass) {
			binary.BigEndian.PutUint16(c.method(t, "run", "()I").code[callPC+1:], uint16(c.cpCount))
		}},
		{"wrong-tag", func(out []byte, c staticsClass) { out[c.entry(t, callRef).offset] = 11 }},
		{"zero-owner", func(out []byte, c staticsClass) { binary.BigEndian.PutUint16(out[c.entry(t, callRef).offset+1:], 0) }},
		{"zero-name-type", func(out []byte, c staticsClass) { binary.BigEndian.PutUint16(out[c.entry(t, callRef).offset+3:], 0) }},
	}
	for _, tc := range specialCases {
		t.Run("special-"+tc.name, func(t *testing.T) {
			bad := verifyM4bMutate(t, original, tc.make)
			verifyM4bAssertError(t, func() (Result, error) { return Run(bad, "run", nil, verifyM4bGasLimit) },
				"CallError(uint256,uint256)", 1, uint64(callPC))
		})
	}

	truncatedNew := verifyM4bRewriteAtEnd(t, original, "run", "()I", verifyM4bNew)
	pc := len(parseStaticsClass(t, truncatedNew).method(t, "run", "()I").code) - 1
	verifyM4bAssertError(t, func() (Result, error) { return Run(truncatedNew, "run", nil, verifyM4bGasLimit) },
		"BytecodeError(uint256,uint256)", 2, uint64(pc))
	truncatedCall := verifyM4bRewriteAtEnd(t, original, "run", "()I", verifyM4bInvokespecial)
	pc = len(parseStaticsClass(t, truncatedCall).method(t, "run", "()I").code) - 1
	verifyM4bAssertError(t, func() (Result, error) { return Run(truncatedCall, "run", nil, verifyM4bGasLimit) },
		"BytecodeError(uint256,uint256)", 2, uint64(pc))

	branchCode := []byte{0x03, 0x99, 0, 5, verifyM4bNew, byte(newRef >> 8), byte(newRef), 0x57, 0x03, 0xac}
	branch := verifyM4bRewriteCode(t, original, "run", "()I", branchCode)
	verifyM4bAssertError(t, func() (Result, error) { return Run(branch, "run", nil, verifyM4bGasLimit) },
		"BytecodeError(uint256,uint256)", 12, 1)
}

func TestVerifyM4bAbstractInaccessibleAndUnsupportedLayoutsUseObjectError2(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"shape/Target.java":    `package shape; public class Target { public Target(){} }`,
		"shape/LongField.java": `package shape; public class LongField { long unsupported; public LongField(){} }`,
		"shapeuser/Root.java": `package shapeuser; public final class Root {
            public static int target(){new shape.Target();return 1;}
            public static int wide(){new shape.LongField();return 2;}
        }`,
	}, "shape/Target", "shape/LongField", "shapeuser/Root")
	root := classes["shapeuser/Root"]
	targetPC := verifyM4bOpcodePC(t, parseStaticsClass(t, root).method(t, "target", "()I").code, verifyM4bNew, 0)
	for _, tc := range []struct {
		name  string
		flags uint16
	}{
		{"abstract", 0x0400},
	} {
		t.Run(tc.name, func(t *testing.T) {
			target := verifyM4bMutate(t, classes["shape/Target"], func(out []byte, c staticsClass) {
				flags := binary.BigEndian.Uint16(out[c.cpEnd:])
				binary.BigEndian.PutUint16(out[c.cpEnd:], flags|tc.flags)
			})
			verifyM4bAssertError(t, func() (Result, error) {
				return RunClasses([][]byte{root, target}, "shapeuser/Root", "target", nil, verifyM4bGasLimit)
			},
				"ObjectError(uint256,uint256)", 2, uint64(targetPC))
		})
	}
	inaccessible := verifyM4bMutate(t, classes["shape/Target"], func(out []byte, c staticsClass) {
		flags := binary.BigEndian.Uint16(out[c.cpEnd:])
		binary.BigEndian.PutUint16(out[c.cpEnd:], flags&^accPublic)
	})
	verifyM4bAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{root, inaccessible}, "shapeuser/Root", "target", nil, verifyM4bGasLimit)
	}, "ObjectError(uint256,uint256)", 2, uint64(targetPC))

	widePC := verifyM4bOpcodePC(t, parseStaticsClass(t, root).method(t, "wide", "()I").code, verifyM4bNew, 0)
	verifyM4bAssertError(t, func() (Result, error) {
		return RunClasses(verifyM4bBundle(classes), "shapeuser/Root", "wide", nil, verifyM4bGasLimit)
	},
		"ObjectError(uint256,uint256)", 2, uint64(widePC))
}

func TestVerifyM4bNullSpecialAndConstructorReceiverValidation(t *testing.T) {
	original := compileJava(t, "NullSpecial", `public final class NullSpecial {
        NullSpecial(){super();} private int secret(){return 5;}
        public static int call(){NullSpecial n=null;return n.secret();}
        public static int construct(){new NullSpecial();return 1;}
    }`)
	verifyM4bAssertException(t, func() (Result, error) { return Run(original, "call", nil, verifyM4bGasLimit) },
		"java.lang.NullPointerException", 6)
	parsed := parseStaticsClass(t, original)
	m := parsed.method(t, "construct", "()I")
	_, newPC := verifyM4bMemberInstruction(t, parsed, m, verifyM4bNew, "NullSpecial", "")
	_, ctorPC := verifyM4bMemberInstruction(t, parsed, m, verifyM4bInvokespecial, "<init>", "()V")
	nullCtor := verifyM4bMutate(t, original, func(out []byte, c staticsClass) {
		code := c.method(t, "construct", "()I").code
		code[newPC], code[newPC+1], code[newPC+2] = 0x01, 0, 0
	})
	verifyM4bAssertError(t, func() (Result, error) { return Run(nullCtor, "construct", nil, verifyM4bGasLimit) },
		"BytecodeError(uint256,uint256)", 14, uint64(ctorPC))
}

func TestVerifyM4bClassInitializationNewReentrancyAndConstructorOutcomes(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"initobj/Reentrant.java": `package initobj; public final class Reentrant {
            static int starts; static Reentrant first=new Reentrant(3); int x;
            Reentrant(int v){super();starts=starts+1;x=v;}
            static int read(Reentrant r){return r.x;}
            public static int run(){Reentrant b=new Reentrant(4);return starts*100+read(first)*10+read(b);}
        }`,
		"initobj/Arithmetic.java": `package initobj; public final class Arithmetic {
            Arithmetic(int x){super();int y=9/x;} public static int run(int x){new Arithmetic(x);return 1;}
        }`,
		"initobj/InitArithmetic.java": `package initobj; public final class InitArithmetic {
            static Arithmetic value=new Arithmetic(0); public static int run(){return 1;}
        }`,
		"initobj/Recursive.java": `package initobj; public final class Recursive {
            Recursive(){this(1);} Recursive(int x){super();} public static int run(){new Recursive();return 1;}
        }`,
	}, "initobj/Reentrant", "initobj/Arithmetic", "initobj/InitArithmetic", "initobj/Recursive")
	verifyM4bAssertNoVirtual(t, classes)
	verifyM4bAssertValue(t, func() (Result, error) { return Run(classes["initobj/Reentrant"], "run", nil, verifyM4bGasLimit) }, 234)
	verifyM4bAssertException(t, func() (Result, error) {
		return Run(classes["initobj/Arithmetic"], "run", []int32{0}, verifyM4bGasLimit)
	},
		"java.lang.ArithmeticException", 1)
	verifyM4bAssertException(t, func() (Result, error) {
		return RunClasses([][]byte{classes["initobj/Arithmetic"], classes["initobj/InitArithmetic"]}, "initobj/InitArithmetic", "run", nil, verifyM4bGasLimit)
	},
		"java.lang.ExceptionInInitializerError", 3)
	recursive := verifyM4bMutate(t, classes["initobj/Recursive"], func(out []byte, c staticsClass) {
		m := c.method(t, "<init>", "(I)V")
		ref, _ := verifyM4bMemberInstruction(t, c, m, verifyM4bInvokespecial, "<init>", "()V")
		binary.BigEndian.PutUint16(out[c.entry(t, ref).offset+1:], verifyM4bClassIndex(t, c, "initobj/Recursive"))
	})
	verifyM4bAssertException(t, func() (Result, error) { return Run(recursive, "run", nil, verifyM4bGasLimit) },
		"java.lang.StackOverflowError", 2)
}

func TestVerifyM4bObjectArrayAndFieldCapsAreIndependentNoGCAndReset(t *testing.T) {
	classfile := compileJava(t, "ObjectCaps", `public final class ObjectCaps {
        ObjectCaps(){super();}
        public static int objects(int n){ObjectCaps waste=null;for(int i=0;i<n;i++)waste=new ObjectCaps();return n+(waste==null?0:0);}
        public static int arraysThenObjects(){int[] a=null;ObjectCaps o=null;for(int i=0;i<1024;i++)a=new int[0];for(int i=0;i<1024;i++)o=new ObjectCaps();return (a==null?0:1)+(o==null?0:1);}
    }`)
	verifyM4bAssertValue(t, func() (Result, error) { return Run(classfile, "objects", []int32{1024}, verifyM4bCapacityGasLimit) }, 1024)
	verifyM4bAssertException(t, func() (Result, error) { return Run(classfile, "objects", []int32{1025}, verifyM4bCapacityGasLimit) },
		"java.lang.OutOfMemoryError", 7)
	// Unreachable allocations count (no GC), while a fresh invocation resets.
	verifyM4bAssertValue(t, func() (Result, error) { return Run(classfile, "objects", []int32{1024}, verifyM4bCapacityGasLimit) }, 1024)
	verifyM4bAssertValue(t, func() (Result, error) { return Run(classfile, "arraysThenObjects", nil, verifyM4bCapacityGasLimit) }, 2)
}

func TestVerifyM4bPerObjectAndTotalFieldSlotCaps(t *testing.T) {
	var fields strings.Builder
	fields.WriteString("public final class ManyFields {")
	for i := 0; i < 1024; i++ {
		fmt.Fprintf(&fields, "int f%d;", i)
	}
	fields.WriteString("ManyFields(){super();} public static int allocate(int n){ManyFields x=null;for(int i=0;i<n;i++)x=new ManyFields();return n+(x==null?0:0);}}")
	classfile := compileJava(t, "ManyFields", fields.String())
	verifyM4bAssertValue(t, func() (Result, error) { return Run(classfile, "allocate", []int32{64}, verifyM4bCapacityGasLimit) }, 64)
	verifyM4bAssertException(t, func() (Result, error) { return Run(classfile, "allocate", []int32{65}, verifyM4bCapacityGasLimit) },
		"java.lang.OutOfMemoryError", 7)

	fields.Reset()
	fields.WriteString("public final class TooManyFields {")
	for i := 0; i < 1025; i++ {
		fmt.Fprintf(&fields, "int f%d;", i)
	}
	fields.WriteString("TooManyFields(){super();} public static int run(){new TooManyFields();return 1;}}")
	tooMany := compileJava(t, "TooManyFields", fields.String())
	verifyM4bAssertException(t, func() (Result, error) { return Run(tooMany, "run", nil, verifyM4bCapacityGasLimit) },
		"java.lang.OutOfMemoryError", 7)
}

func TestVerifyM4bObjectOOMAndEVMOutOfGasRemainDistinct(t *testing.T) {
	classfile := compileJava(t, "OOMDistinction", `public final class OOMDistinction {
        OOMDistinction(){super();} public static int run(int n){for(int i=0;i<n;i++)new OOMDistinction();return n;}
    }`)
	verifyM4bAssertException(t, func() (Result, error) { return Run(classfile, "run", []int32{1025}, verifyM4bCapacityGasLimit) },
		"java.lang.OutOfMemoryError", 7)
	result, err := Run(classfile, "run", []int32{1}, 1)
	if err == nil || !errors.Is(err, vm.ErrOutOfGas) {
		t.Fatalf("result/error=%+v/%v, want EVM OOG", result, err)
	}
	if result.ExceptionClass != "" || len(result.RevertData) != 0 {
		t.Fatalf("OOG mislabeled as Java OOM: %+v", result)
	}
}

func TestVerifyM4bRootObjectSignaturesRemainRejected(t *testing.T) {
	classfile := compileJava(t, "ObjectRoots", `public final class ObjectRoots {
        public static int takes(Object o){return o==null?1:2;} public static Object gives(){return new Object();}
        public static int scalar(int x){return x;}
    }`)
	for _, tc := range []struct {
		method string
		args   []int32
	}{{"takes", nil}, {"takes", []int32{0}}, {"gives", nil}} {
		t.Run(tc.method+fmt.Sprint(tc.args), func(t *testing.T) {
			result, err := Run(classfile, tc.method, tc.args, verifyM4bGasLimit)
			verifyM4bAssertMethodError(t, result, err, 11)
		})
	}
	verifyM4bAssertValue(t, func() (Result, error) { return Run(classfile, "scalar", []int32{9}, verifyM4bGasLimit) }, 9)
}

func verifyM4bBundle(classes map[string][]byte) [][]byte {
	names := make([]string, 0, len(classes))
	for name := range classes {
		names = append(names, name)
	}
	// Deliberately avoid relying on map iteration while also varying declaration
	// order from source order. Lexicographic order is sufficient for identity tests.
	for i := 0; i < len(names); i++ {
		for j := i + 1; j < len(names); j++ {
			if names[j] < names[i] {
				names[i], names[j] = names[j], names[i]
			}
		}
	}
	out := make([][]byte, len(names))
	for i, name := range names {
		out[i] = classes[name]
	}
	return out
}

func verifyM4bAssertNoVirtual(t *testing.T, classes map[string][]byte) {
	t.Helper()
	for name, data := range classes {
		for _, m := range parseStaticsClass(t, data).methods {
			if bytes.IndexByte(m.code, verifyM4bInvokevirtual) >= 0 {
				t.Fatalf("trusted M4b class %s method %s%s contains invokevirtual: %x", name, m.name, m.descriptor, m.code)
			}
			if bytes.IndexByte(m.code, 0xb9) >= 0 {
				t.Fatalf("trusted M4b class %s method %s%s contains invokeinterface: %x", name, m.name, m.descriptor, m.code)
			}
		}
	}
}

func verifyM4bMutate(t *testing.T, original []byte, change func([]byte, staticsClass)) []byte {
	t.Helper()
	out := append([]byte(nil), original...)
	change(out, parseStaticsClass(t, out))
	return out
}

func verifyM4bClassIndex(t *testing.T, c staticsClass, name string) uint16 {
	t.Helper()
	for i := 1; i < len(c.entries); i++ {
		e := c.entries[i]
		if e.tag == 7 && c.utf8[c.u2(t, e.offset+1)] == name {
			return uint16(i)
		}
	}
	t.Fatalf("Class constant %q not found", name)
	return 0
}

func verifyM4bMemberInstruction(t *testing.T, c staticsClass, m staticsMethod, opcode byte, name, descriptor string) (uint16, int) {
	t.Helper()
	for pc := 0; pc+2 < len(m.code); pc++ {
		if m.code[pc] != opcode {
			continue
		}
		ref := binary.BigEndian.Uint16(m.code[pc+1:])
		if ref == 0 || int(ref) >= len(c.entries) {
			continue
		}
		e := c.entries[ref]
		if opcode == verifyM4bNew {
			if e.tag == 7 && c.utf8[c.u2(t, e.offset+1)] == name {
				return ref, pc
			}
			continue
		}
		if e.tag != 9 && e.tag != 10 {
			continue
		}
		nat := c.entry(t, c.u2(t, e.offset+3))
		if nat.tag != 12 {
			continue
		}
		gotName := c.utf8[c.u2(t, nat.offset+1)]
		gotDescriptor := c.utf8[c.u2(t, nat.offset+3)]
		if gotName == name && gotDescriptor == descriptor {
			return ref, pc
		}
	}
	t.Fatalf("method %s%s lacks opcode 0x%02x for %s%s: %x", m.name, m.descriptor, opcode, name, descriptor, m.code)
	return 0, 0
}

func verifyM4bOpcodePC(t *testing.T, code []byte, opcode byte, occurrence int) int {
	t.Helper()
	seen := 0
	for pc, op := range code {
		if op == opcode {
			if seen == occurrence {
				return pc
			}
			seen++
		}
	}
	t.Fatalf("opcode 0x%02x occurrence %d missing: %x", opcode, occurrence, code)
	return -1
}

func verifyM4bAliasNewClass(t *testing.T, original []byte, method string, change func([]byte, staticsClass, uint16)) []byte {
	t.Helper()
	c := parseStaticsClass(t, original)
	m := c.namedMethod(t, method)
	classIndex, _ := verifyM4bMemberInstruction(t, c, m, verifyM4bNew, c.utf8[c.u2(t, c.entry(t, c.thisClass).offset+1)], "")
	nameIndex := c.u2(t, c.entry(t, classIndex).offset+1)
	if c.cpCount >= 65535 {
		t.Fatal("test constant pool is full")
	}
	out := make([]byte, len(original)+3)
	copy(out, original[:c.cpEnd])
	out[c.cpEnd] = 7
	binary.BigEndian.PutUint16(out[c.cpEnd+1:], nameIndex)
	copy(out[c.cpEnd+3:], original[c.cpEnd:])
	binary.BigEndian.PutUint16(out[8:10], uint16(c.cpCount+1))
	parsed := parseStaticsClass(t, out)
	alias := uint16(c.cpCount)
	_, pc := verifyM4bMemberInstruction(t, parsed, parsed.namedMethod(t, method), verifyM4bNew,
		parsed.utf8[nameIndex], "")
	binary.BigEndian.PutUint16(parsed.namedMethod(t, method).code[pc+1:], alias)
	change(out, parseStaticsClass(t, out), alias)
	return out
}

func verifyM4bRewriteCode(t *testing.T, original []byte, name, descriptor string, code []byte) []byte {
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
	binary.BigEndian.PutUint16(out[start-8:], 16)
	binary.BigEndian.PutUint16(out[start-6:], 16)
	for i := range m.code {
		m.code[i] = 0
	}
	copy(m.code, code)
	return out
}

func verifyM4bRewriteAtEnd(t *testing.T, original []byte, name, descriptor string, opcode byte) []byte {
	t.Helper()
	out := verifyM4bRewriteCode(t, original, name, descriptor, nil)
	m := parseStaticsClass(t, out).method(t, name, descriptor)
	m.code[len(m.code)-1] = opcode
	return out
}

func verifyM4bRetargetAllocation(t *testing.T, original []byte, method, from, to string) []byte {
	t.Helper()
	return verifyM4bMutate(t, original, func(out []byte, c staticsClass) {
		m := c.namedMethod(t, method)
		_, newPC := verifyM4bMemberInstruction(t, c, m, verifyM4bNew, from, "")
		ctorRef, _ := verifyM4bMemberInstruction(t, c, m, verifyM4bInvokespecial, "<init>", "()V")
		toIndex := verifyM4bClassIndex(t, c, to)
		binary.BigEndian.PutUint16(m.code[newPC+1:], toIndex)
		binary.BigEndian.PutUint16(out[c.entry(t, ctorRef).offset+1:], toIndex)
	})
}

func verifyM4bAssertValue(t *testing.T, run func() (Result, error), want int32) {
	t.Helper()
	result, err := run()
	if err != nil {
		t.Fatalf("EVM execution failed: %v (result=%+v)", err, result)
	}
	if result.ExceptionClass != "" || result.Value != want || result.GasUsed == 0 || len(result.RevertData) != 0 {
		t.Fatalf("result=%+v, want value %d", result, want)
	}
}

func verifyM4bAssertException(t *testing.T, run func() (Result, error), want string, kind byte) {
	t.Helper()
	result, err := run()
	if err != nil {
		t.Fatalf("Java outcome returned EVM failure: %v (result=%+v)", err, result)
	}
	selector := crypto.Keccak256([]byte("JavaException(uint256)"))[:4]
	if result.ExceptionClass != want || result.GasUsed == 0 || len(result.RevertData) != 36 || !bytes.Equal(result.RevertData[:4], selector) || !bytes.Equal(result.RevertData[4:35], make([]byte, 31)) || result.RevertData[35] != kind {
		t.Fatalf("result=%+v data=%x, want exact %s kind %d", result, result.RevertData, want, kind)
	}
}

func verifyM4bAssertError(t *testing.T, run func() (Result, error), signature string, code, pc uint64) {
	t.Helper()
	result, err := run()
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error=%+v/%v, want %s", result, err, signature)
	}
	selector := crypto.Keccak256([]byte(signature))[:4]
	if result.ExceptionClass != "" || result.GasUsed == 0 || len(result.RevertData) != 68 || !bytes.Equal(result.RevertData[:4], selector) {
		t.Fatalf("result=%+v, want exact %s payload", result, signature)
	}
	if got := verifyM4bUint256(t, result.RevertData[4:36]); got != code {
		t.Fatalf("%s code=%d want %d data=%x", signature, got, code, result.RevertData)
	}
	if got := verifyM4bUint256(t, result.RevertData[36:68]); got != pc {
		t.Fatalf("%s pc=%d want %d data=%x", signature, got, pc, result.RevertData)
	}
}

func verifyM4bAssertMethodError(t *testing.T, result Result, err error, code uint64) {
	t.Helper()
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error=%+v/%v, want MethodError", result, err)
	}
	selector := crypto.Keccak256([]byte("MethodError(uint256)"))[:4]
	if result.ExceptionClass != "" || result.GasUsed == 0 || len(result.RevertData) != 36 || !bytes.Equal(result.RevertData[:4], selector) || verifyM4bUint256(t, result.RevertData[4:]) != code {
		t.Fatalf("result=%+v data=%x, want MethodError(%d)", result, result.RevertData, code)
	}
}

func verifyM4bUint256(t *testing.T, word []byte) uint64 {
	t.Helper()
	if len(word) != 32 || !bytes.Equal(word[:24], make([]byte, 24)) {
		t.Fatalf("noncanonical uint256: %x", word)
	}
	return binary.BigEndian.Uint64(word[24:])
}

func TestVerifyM4bSynchronizedSpecialCalleeRejected(t *testing.T) {
	classfile := compileJava(t, "SyncPrivate", `public final class SyncPrivate {
        private synchronized int f(int x) { return x + 1; }
        public static int run(int x) { return new SyncPrivate().f(x); }
    }`)
	parsed := parseStaticsClass(t, classfile)
	_, pc := verifyM4bMemberInstruction(t, parsed, parsed.method(t, "run", "(I)I"), verifyM4bInvokespecial, "f", "(I)I")
	verifyM4bAssertError(t, func() (Result, error) {
		return Run(classfile, "run", []int32{41}, verifyM4bGasLimit)
	}, "CallError(uint256,uint256)", 4, uint64(pc))
}
