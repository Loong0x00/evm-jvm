// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"encoding/binary"
	"errors"
	"fmt"
	"math"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/core/vm"
	"github.com/ethereum/go-ethereum/crypto"
)

const (
	verifyM5daSimpleGas  = uint64(20_000_000)
	verifyM5daComplexGas = uint64(80_000_000)
	verifyM5daQuotaGas   = uint64(250_000_000)
)

// These are independent verifier probes. They compile only bounded, trusted Java 8
// source. Malformed inputs are narrow test-only edits of javac output; production
// Run/RunClasses still receive raw bytes and all parsing, matching, allocation, and
// initialization behavior remains inside EVM bytecode.

func TestVerifyM5daHandlerErrorContractAndBoundaries(t *testing.T) {
	base := verifyM5daCompile(t, map[string]string{
		"VerifyM5daHandlers.java": `public final class VerifyM5daHandlers {
			public static int run(int x) { try { return 100 / x; }
				catch (ArithmeticException e) { return 7; } }
		}`,
	}, "VerifyM5daHandlers")["VerifyM5daHandlers"]
	parsed := verifyM5daParse(t, base)
	method := parsed.method(t, "run", "(I)I")
	if len(method.handlers) != 1 {
		t.Fatalf("javac handler count=%d want 1", len(method.handlers))
	}
	entry := method.handlers[0]
	middle := verifyM5daOperandPC(t, method.code)
	switchClass := verifyM5daCompile(t, map[string]string{
		"VerifyM5daSwitchHandler.java": `public final class VerifyM5daSwitchHandler {public static int run(int x){try{switch(x){case 0:return 1/0;case 1:return 2;case 2:return 3;default:return 4;}}catch(ArithmeticException e){return 7;}}}`,
	}, "VerifyM5daSwitchHandler")["VerifyM5daSwitchHandler"]
	switchMethod := verifyM5daParse(t, switchClass).method(t, "run", "(I)I")
	switchPC := verifyM5daOpcodePC(t, switchMethod.code, 0xaa, 0)

	tests := []struct {
		name        string
		code, entry uint64
		make        func() []byte
	}{
		{"count-cap-257", 1, math.MaxUint64, func() []byte { return verifyM5daExpandHandlers(t, base, "run", 257) }},
		{"incomplete-table", 1, math.MaxUint64, func() []byte {
			out := verifyM5daStripCodeAttributes(t, base, "run")
			return verifyM5daMutate(t, out, func(out []byte, c verifyM5daClass) {
				binary.BigEndian.PutUint16(out[c.method(t, "run", "(I)I").handlerCountOffset:], 2)
			})
		}},
		{"empty-range", 2, 0, func() []byte {
			return verifyM5daEditHandler(t, base, "run", 0, func(h []byte) { copy(h[2:4], h[0:2]) })
		}},
		{"end-after-code", 2, 0, func() []byte {
			return verifyM5daEditHandler(t, base, "run", 0, func(h []byte) { binary.BigEndian.PutUint16(h[2:], uint16(len(method.code)+1)) })
		}},
		{"handler-after-code", 2, 0, func() []byte {
			return verifyM5daEditHandler(t, base, "run", 0, func(h []byte) { binary.BigEndian.PutUint16(h[4:], uint16(len(method.code))) })
		}},
		{"start-in-operand", 3, 0, func() []byte {
			return verifyM5daEditHandler(t, base, "run", 0, func(h []byte) { binary.BigEndian.PutUint16(h[0:], uint16(middle)) })
		}},
		{"end-in-operand", 3, 0, func() []byte {
			return verifyM5daEditHandler(t, base, "run", 0, func(h []byte) {
				binary.BigEndian.PutUint16(h[0:], 0)
				binary.BigEndian.PutUint16(h[2:], uint16(middle))
			})
		}},
		{"handler-in-operand", 3, 0, func() []byte {
			return verifyM5daEditHandler(t, base, "run", 0, func(h []byte) { binary.BigEndian.PutUint16(h[4:], uint16(middle)) })
		}},
		{"start-in-wide-operand", 3, 0, func() []byte {
			wide := verifyM5daMutate(t, base, func(_ []byte, c verifyM5daClass) { copy(c.method(t, "run", "(I)I").code[:4], []byte{0xc4, 0x15, 0, 0}) })
			return verifyM5daEditHandler(t, wide, "run", 0, func(h []byte) { binary.BigEndian.PutUint16(h[0:], 1) })
		}},
		{"start-in-switch-payload", 3, 0, func() []byte {
			return verifyM5daEditHandler(t, switchClass, "run", 0, func(h []byte) { binary.BigEndian.PutUint16(h[0:], uint16(switchPC+1)) })
		}},
		{"catch-cp-oob", 4, 0, func() []byte {
			return verifyM5daEditHandler(t, base, "run", 0, func(h []byte) { binary.BigEndian.PutUint16(h[6:], uint16(parsed.cpCount)) })
		}},
		{"catch-cp-tag", 4, 0, func() []byte {
			return verifyM5daEditHandler(t, base, "run", 0, func(h []byte) { binary.BigEndian.PutUint16(h[6:], parsed.classNameIndex(t, entry.catchType)) })
		}},
		{"catch-array-name", 4, 0, func() []byte {
			out, index := verifyM5daAppendClass(t, base, "[I")
			return verifyM5daEditHandler(t, out, "run", 0, func(h []byte) { binary.BigEndian.PutUint16(h[6:], index) })
		}},
		{"catch-invalid-name-chain", 4, 0, func() []byte {
			out, index := verifyM5daAppendClass(t, base, "bad.name")
			return verifyM5daEditHandler(t, out, "run", 0, func(h []byte) { binary.BigEndian.PutUint16(h[6:], index) })
		}},
		{"catch-non-throwable", 6, 0, func() []byte {
			return verifyM5daEditHandler(t, base, "run", 0, func(h []byte) { binary.BigEndian.PutUint16(h[6:], parsed.classIndex(t, "java/lang/Object")) })
		}},
		{"handler-needs-stack", 7, math.MaxUint64, func() []byte {
			return verifyM5daMutate(t, base, func(out []byte, c verifyM5daClass) {
				binary.BigEndian.PutUint16(out[c.method(t, "run", "(I)I").maxStackOffset:], 0)
			})
		}},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			verifyM5daAssertHandlerError(t, func() (Result, error) { return Run(tc.make(), "run", []int32{0}, verifyM5daSimpleGas) }, tc.code, 0, uint64(method.index), tc.entry)
		})
	}
	t.Run("count-cap-256-valid", func(t *testing.T) {
		verifyM5daAssertValue(t, func() (Result, error) {
			return Run(verifyM5daExpandHandlers(t, base, "run", 256), "run", []int32{0}, verifyM5daComplexGas)
		}, 7)
	})
	t.Run("end-equals-code-length-valid", func(t *testing.T) {
		valid := verifyM5daEditHandler(t, base, "run", 0, func(h []byte) { binary.BigEndian.PutUint16(h[2:], uint16(len(method.code))) })
		verifyM5daAssertValue(t, func() (Result, error) { return Run(valid, "run", []int32{0}, verifyM5daSimpleGas) }, 7)
	})
}

func TestVerifyM5daHandlerLazyResolutionAccessInterfaceAndConstructorLimit(t *testing.T) {
	classes := verifyM5daCompile(t, map[string]string{
		"lazy/Missing.java": `package lazy; public class Missing extends RuntimeException {}`,
		"lazy/Marker.java":  `package lazy; public interface Marker {}`,
		"lazy/Root.java": `package lazy; public final class Root {
			static Marker marker;
			public static int run(int x) {
				if(marker!=null && marker instanceof Marker)return 9;
				try { int y=x+1; if(y==99)return y; } catch(Missing e) { return 1; }
				try { return 10/x; } catch(ArithmeticException e) { return 2; }
			}
		}`,
	}, "lazy/Missing", "lazy/Marker", "lazy/Root")
	root := classes["lazy/Root"]
	p := verifyM5daParse(t, root)
	m := p.method(t, "run", "(I)I")
	if len(m.handlers) != 2 {
		t.Fatalf("lazy handler count=%d want 2", len(m.handlers))
	}
	// A missing catch class is not resolved merely because another PC faults.
	verifyM5daAssertValue(t, func() (Result, error) {
		return RunClasses([][]byte{root}, "lazy/Root", "run", []int32{0}, verifyM5daSimpleGas)
	}, 2)
	// Once the earlier missing entry is range-applicable it fails, rather than
	// being skipped in favor of the later ArithmeticException handler.
	applicable := verifyM5daEditHandler(t, root, "run", 0, func(h []byte) {
		binary.BigEndian.PutUint16(h[0:], m.handlers[1].start)
		binary.BigEndian.PutUint16(h[2:], m.handlers[1].end)
	})
	verifyM5daAssertHandlerError(t, func() (Result, error) {
		return RunClasses([][]byte{applicable}, "lazy/Root", "run", []int32{0}, verifyM5daSimpleGas)
	}, 5, 0, uint64(m.index), 0)

	iface := verifyM5daEditHandler(t, root, "run", 1, func(h []byte) { binary.BigEndian.PutUint16(h[6:], p.classIndex(t, "lazy/Marker")) })
	verifyM5daAssertHandlerError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["lazy/Marker"], iface}, "lazy/Root", "run", []int32{0}, verifyM5daSimpleGas)
	}, 6, 1, uint64(m.index), 1)

	access := verifyM5daCompile(t, map[string]string{
		"hidden/Hidden.java": `package hidden; public class Hidden extends RuntimeException {}`,
		"other/Root.java":    `package other; public final class Root { public static int run(){try{return 1/0;}catch(hidden.Hidden e){return 3;}} }`,
	}, "hidden/Hidden", "other/Root")
	hidden := verifyM5daMutate(t, access["hidden/Hidden"], func(out []byte, c verifyM5daClass) {
		binary.BigEndian.PutUint16(out[c.accessOffset:], c.access&^uint16(0x0001))
	})
	accessRoot := verifyM5daParse(t, access["other/Root"]).method(t, "run", "()I")
	verifyM5daAssertHandlerError(t, func() (Result, error) {
		return RunClasses([][]byte{hidden, access["other/Root"]}, "other/Root", "run", nil, verifyM5daSimpleGas)
	}, 9, 1, uint64(accessRoot.index), 0)

	ctors := verifyM5daCompile(t, map[string]string{
		"ctor/Base.java":  `package ctor; public class Base { Base(){int x=1/0;} }`,
		"ctor/Child.java": `package ctor; public class Child extends Base { Child(){super();try{int x=1/0;}catch(ArithmeticException e){}} public static int run(){try{new Child();}catch(Throwable e){return 8;}return 0;} }`,
	}, "ctor/Base", "ctor/Child")
	child := verifyM5daParse(t, ctors["ctor/Child"])
	ctor := child.method(t, "<init>", "()V")
	if len(ctor.handlers) != 1 {
		t.Fatalf("constructor handler count=%d want 1", len(ctor.handlers))
	}
	unlinked := verifyM5daEditHandler(t, ctors["ctor/Child"], "<init>", 0, func(h []byte) {
		binary.BigEndian.PutUint16(h[0:], 0)
	})
	verifyM5daAssertHandlerError(t, func() (Result, error) {
		return RunClasses([][]byte{ctors["ctor/Base"], unlinked}, "ctor/Child", "run", nil, verifyM5daComplexGas)
	}, 8, 1, uint64(ctor.index), 0)
}

func TestVerifyM5daOrderedRangesStackClearLocalsAndInvokePC(t *testing.T) {
	classes := verifyM5daCompile(t, map[string]string{
		"flow/Helper.java": `package flow; public final class Helper { static int fail(int x){return 10/x;} }`,
		"flow/Root.java": `package flow; public final class Root {
			public static int ordered(int x){try{return 10/x;}catch(ArithmeticException e){return 11;}catch(Throwable e){return 12;}}
			public static int call(int x){long l=20L;float f=3.0f;double d=4.0d;int keep=5;try{return 1000+Helper.fail(x);}catch(ArithmeticException e){return (e!=null?100:0)+(int)l+(int)f+(int)d+keep;}}
			public static int cleanup(){int x=1;try{try{x=2;return 1/0;}finally{x=3;}}catch(Throwable e){return x;}}
		}`,
	}, "flow/Helper", "flow/Root")
	root := classes["flow/Root"]
	ordered := verifyM5daParse(t, root).method(t, "ordered", "(I)I")
	if len(ordered.handlers) != 2 {
		t.Fatalf("ordered handler count=%d want 2", len(ordered.handlers))
	}
	// Replacing the first exact type by RuntimeException makes both entries
	// match; classfile order still requires the first target (11).
	withRuntime, runtimeCP := verifyM5daAppendClass(t, root, "java/lang/RuntimeException")
	broadFirst := verifyM5daEditHandler(t, withRuntime, "ordered", 0, func(h []byte) {
		binary.BigEndian.PutUint16(h[6:], runtimeCP)
	})
	verifyM5daAssertValue(t, func() (Result, error) {
		return RunClasses([][]byte{classes["flow/Helper"], broadFirst}, "flow/Root", "ordered", []int32{0}, verifyM5daSimpleGas)
	}, 11)

	idiv := verifyM5daOpcodePC(t, ordered.code, 0x6c, 0)
	onlyFault := verifyM5daEditHandler(t, root, "ordered", 0, func(h []byte) {
		binary.BigEndian.PutUint16(h[0:], uint16(idiv))
		binary.BigEndian.PutUint16(h[2:], uint16(idiv+1))
	})
	verifyM5daAssertValue(t, func() (Result, error) {
		return RunClasses([][]byte{classes["flow/Helper"], onlyFault}, "flow/Root", "ordered", []int32{0}, verifyM5daSimpleGas)
	}, 11)
	excludesFault := verifyM5daEditHandler(t, root, "ordered", 0, func(h []byte) {
		binary.BigEndian.PutUint16(h[2:], uint16(idiv))
	})
	// The second handler still catches. This distinguishes end-exclusive ranges.
	verifyM5daAssertValue(t, func() (Result, error) {
		return RunClasses([][]byte{classes["flow/Helper"], excludesFault}, "flow/Root", "ordered", []int32{0}, verifyM5daSimpleGas)
	}, 12)

	// The caller's handler range covers its invoke PC. Prefix 1000 must be
	// discarded, while category-1/2 locals survive unwind.
	verifyM5daAssertValue(t, func() (Result, error) {
		return RunClasses([][]byte{classes["flow/Helper"], root}, "flow/Root", "call", []int32{0}, verifyM5daComplexGas)
	}, 132)
	cleanup := verifyM5daParse(t, root).method(t, "cleanup", "()I")
	catchAll := false
	for _, h := range cleanup.handlers {
		catchAll = catchAll || h.catchType == 0
	}
	if !catchAll {
		t.Fatal("javac finally fixture has no catch_type zero entry")
	}
	verifyM5daAssertValue(t, func() (Result, error) {
		return RunClasses([][]byte{classes["flow/Helper"], root}, "flow/Root", "cleanup", nil, verifyM5daSimpleGas)
	}, 3)
}

func TestVerifyM5daAthrowKindsIdentityAndReferenceValidation(t *testing.T) {
	classfile := verifyM5daCompile(t, map[string]string{
		"VerifyM5daThrow.java": `public final class VerifyM5daThrow {
			static Object object(){return new Object();}
			public static int identity(){try{int[] a=null;return a.length;}catch(Throwable e){try{throw e;}catch(Throwable f){return e==f?31:0;}}}
			public static int nullThrow(){try{throw (Throwable)null;}catch(Throwable e){return e instanceof NullPointerException?41:0;}}
			public static int ordinary(){return object()==null?0:1;}
			public static int integer(int x){return x;}
		}`,
	}, "VerifyM5daThrow")["VerifyM5daThrow"]
	verifyM5daAssertValue(t, func() (Result, error) { return Run(classfile, "identity", nil, verifyM5daSimpleGas) }, 31)
	verifyM5daAssertValue(t, func() (Result, error) { return Run(classfile, "nullThrow", nil, verifyM5daSimpleGas) }, 41)

	ordinary := verifyM5daMutate(t, classfile, func(out []byte, c verifyM5daClass) {
		m := c.method(t, "object", "()Ljava/lang/Object;")
		pc := verifyM5daOpcodePC(t, m.code, 0xb0, 0)
		m.code[pc] = 0xbf
	})
	verifyM5daAssertError(t, func() (Result, error) { return Run(ordinary, "ordinary", nil, verifyM5daSimpleGas) }, "BytecodeError(uint256,uint256)", 14, nil)

	uninitialized := verifyM5daMutate(t, classfile, func(out []byte, c verifyM5daClass) {
		m := c.method(t, "object", "()Ljava/lang/Object;")
		call := verifyM5daOpcodePC(t, m.code, 0xb7, 0)
		m.code[call], m.code[call+1], m.code[call+2] = 0x00, 0x00, 0x00
		m.code[verifyM5daOpcodePC(t, m.code, 0xb0, 0)] = 0xbf
	})
	verifyM5daAssertError(t, func() (Result, error) { return Run(uninitialized, "ordinary", nil, verifyM5daSimpleGas) }, "BytecodeError(uint256,uint256)", 14, nil)

	integer := verifyM5daMutate(t, classfile, func(out []byte, c verifyM5daClass) {
		m := c.method(t, "integer", "(I)I")
		m.code[1] = 0xbf // iload_0, athrow: an int cannot forge a registry ref.
	})
	verifyM5daAssertError(t, func() (Result, error) { return Run(integer, "integer", []int32{1}, verifyM5daSimpleGas) }, "BytecodeError(uint256,uint256)", 14, verifyM5daUint64(1))

	underflow := verifyM5daMutate(t, classfile, func(out []byte, c verifyM5daClass) {
		m := c.method(t, "integer", "(I)I")
		m.code[0], m.code[1] = 0xbf, 0xac
	})
	verifyM5daAssertError(t, func() (Result, error) { return Run(underflow, "integer", []int32{1}, verifyM5daSimpleGas) }, "BytecodeError(uint256,uint256)", 3, verifyM5daUint64(0))
}

func TestVerifyM5daEveryInvocationModeAndNativeFrameCaps(t *testing.T) {
	classes := verifyM5daCompile(t, map[string]string{
		"modes/I.java":    `package modes; public interface I {int fail();default int def(){return 1/0;}}`,
		"modes/C.java":    `package modes; public class C implements I {public int fail(){return 1/0;}}`,
		"modes/Boom.java": `package modes; public class Boom {Boom(){int x=1/0;}}`,
		"modes/Root.java": `package modes; public final class Root {
			static int stat(){return 1/0;} private int special(){return 1/0;}
			public static int mode(int n){try{switch(n){case 0:return stat();case 1:return new C().fail();case 2:{I x=new C();return x.fail();}case 3:{I x=new C();return x.def();}case 4:return new Root().special();default:return new Boom()==null?0:1;}}catch(ArithmeticException e){return n+20;}}
			static int deep(int n,int mode){if(n==126){switch(mode){case 0:return Float.floatToRawIntBits(Float.intBitsToFloat(1));case 1:return (int)Double.doubleToRawLongBits(1.0d);case 2:return (int)Double.longBitsToDouble(1L);default:return Float.floatToRawIntBits(1.0f);}}return deep(n+1,mode);}
			public static int nativeCap(int mode){try{return deep(0,mode);}catch(StackOverflowError e){return 2;}}
		}`,
	}, "modes/I", "modes/C", "modes/Boom", "modes/Root")
	bundle := verifyM5daBundle(classes)
	for mode := int32(0); mode < 6; mode++ {
		verifyM5daAssertValue(t, func() (Result, error) {
			return RunClasses(bundle, "modes/Root", "mode", []int32{mode}, verifyM5daComplexGas)
		}, mode+20)
	}
	for mode := int32(0); mode < 4; mode++ {
		verifyM5daAssertValue(t, func() (Result, error) {
			return RunClasses(bundle, "modes/Root", "nativeCap", []int32{mode}, verifyM5daComplexGas)
		}, 2)
	}
}

func TestVerifyM5daEveryFrameCapCallSiteRaisesAtInvokerAndIsCatchable(t *testing.T) {
	classes := verifyM5daCompile(t, map[string]string{
		"caps/V.java": `package caps; public class V {int f(){try{return f();}catch(StackOverflowError e){return 21;}}}`,
		"caps/S.java": `package caps; public class S {private int f(){try{return f();}catch(StackOverflowError e){return 22;}}int run(){return f();}}`,
		"caps/I.java": `package caps; public interface I {int f();}`,
		"caps/C.java": `package caps; public class C implements I {public int f(){try{I x=this;return x.f();}catch(StackOverflowError e){return 23;}}}`,
		"caps/D.java": `package caps; public interface D {default int f(){try{D x=this;return x.f();}catch(StackOverflowError e){return 24;}}}`,
		"caps/E.java": `package caps; public class E implements D {}`,
		"caps/K.java": `package caps; public class K {static int caught;K(){try{new K();}catch(StackOverflowError e){caught=25;}}}`,
		"caps/Root.java": `package caps; public final class Root {
			public static int virtualCap(){return new V().f();}public static int specialCap(){return new S().run();}
			public static int interfaceCap(){I x=new C();return x.f();}public static int defaultCap(){D x=new E();return x.f();}
			public static int constructorCap(){new K();return K.caught;}
		}`,
	}, "caps/V", "caps/S", "caps/I", "caps/C", "caps/D", "caps/E", "caps/K", "caps/Root")
	bundle := verifyM5daBundle(classes)
	for _, tc := range []struct {
		method string
		want   int32
	}{{"virtualCap", 21}, {"specialCap", 22}, {"interfaceCap", 23}, {"defaultCap", 24}, {"constructorCap", 25}} {
		t.Run(tc.method, func(t *testing.T) {
			verifyM5daAssertValue(t, func() (Result, error) { return RunClasses(bundle, "caps/Root", tc.method, nil, verifyM5daComplexGas) }, tc.want)
		})
	}
}

func TestVerifyM5daAllImplicitKindsCatchableAndUncaughtABI(t *testing.T) {
	classes := verifyM5daCompile(t, map[string]string{
		"kinds/Bad.java": `package kinds; public final class Bad { static int value=1/0; }`,
		"kinds/Root.java": `package kinds; public final class Root {
			static int recurse(){return 1+recurse();}
			public static int arithmetic(){try{return 1/0;}catch(ArithmeticException e){return 1;}}
			public static int soe(){try{return recurse();}catch(StackOverflowError e){return 2;}}
			public static int eiie(){try{return Bad.value;}catch(ExceptionInInitializerError e){return 3;}}
			public static int nase(){try{return new int[-1].length;}catch(NegativeArraySizeException e){return 4;}}
			public static int bounds(){try{return (new int[1])[2];}catch(ArrayIndexOutOfBoundsException e){return 5;}}
			public static int npe(){try{int[] x=null;return x.length;}catch(NullPointerException e){return 6;}}
			public static int oom(){try{Object[] x=new Object[1025];for(int i=0;i<x.length;i++)x[i]=new Object();return 0;}catch(OutOfMemoryError e){return 7;}}
			public static int cce(){try{Object x=new Object();return ((Root)x)==null?0:1;}catch(ClassCastException e){return 8;}}
			public static int ase(){try{Root[] x=new Root[1];Object[] y=x;y[0]=new Object();return 0;}catch(ArrayStoreException e){return 9;}}
			public static int ncdf(){try{int x=Bad.value;}catch(Throwable first){}try{return Bad.value;}catch(NoClassDefFoundError e){return 12;}}
			public static int uncaught(){return 1/0;}
		}`,
	}, "kinds/Bad", "kinds/Root")
	bundle := verifyM5daBundle(classes)
	for _, tc := range []struct {
		method string
		want   int32
		gas    uint64
	}{
		{"arithmetic", 1, verifyM5daSimpleGas}, {"soe", 2, verifyM5daComplexGas}, {"eiie", 3, verifyM5daComplexGas},
		{"nase", 4, verifyM5daSimpleGas}, {"bounds", 5, verifyM5daSimpleGas}, {"npe", 6, verifyM5daSimpleGas},
		{"oom", 7, verifyM5daQuotaGas}, {"cce", 8, verifyM5daSimpleGas}, {"ase", 9, verifyM5daSimpleGas}, {"ncdf", 12, verifyM5daComplexGas},
	} {
		t.Run(tc.method, func(t *testing.T) {
			verifyM5daAssertValue(t, func() (Result, error) { return RunClasses(bundle, "kinds/Root", tc.method, nil, tc.gas) }, tc.want)
		})
	}
	verifyM5daAssertException(t, func() (Result, error) { return RunClasses(bundle, "kinds/Root", "uncaught", nil, verifyM5daSimpleGas) }, "java.lang.ArithmeticException", 1)
}

func TestVerifyM5daICCEAndAMEResolutionPathsAreCatchable(t *testing.T) {
	old := verifyM5daCompile(t, map[string]string{
		"evo/A.java": `package evo; public interface A {}`,
		"evo/B.java": `package evo; public interface B {}`,
		"evo/C.java": `package evo; public class C implements A,B {}`,
	}, "evo/A", "evo/B", "evo/C")
	caller := verifyM5daCompile(t, map[string]string{
		"evo/A.java":    `package evo; public interface A {int f();}`,
		"evo/C.java":    `package evo; public class C implements A {public int f(){return 1;}}`,
		"evo/Root.java": `package evo; public final class Root {public static int run(){try{A x=new C();return x.f();}catch(IncompatibleClassChangeError e){return 10;}}}`,
	}, "evo/A", "evo/C", "evo/Root")
	newDefaults := verifyM5daCompile(t, map[string]string{
		"evo/A.java": `package evo; public interface A {default int f(){return 1;}}`,
		"evo/B.java": `package evo; public interface B {default int f(){return 2;}}`,
	}, "evo/A", "evo/B")
	verifyM5daAssertValue(t, func() (Result, error) {
		return RunClasses([][]byte{newDefaults["evo/A"], newDefaults["evo/B"], old["evo/C"], caller["evo/Root"]}, "evo/Root", "run", nil, verifyM5daComplexGas)
	}, 10)

	missingOld := verifyM5daCompile(t, map[string]string{
		"ame/I.java": `package ame; public interface I {}`,
		"ame/C.java": `package ame; public class C implements I {}`,
	}, "ame/I", "ame/C")
	missingCaller := verifyM5daCompile(t, map[string]string{
		"ame/I.java":    `package ame; public interface I {int f();}`,
		"ame/C.java":    `package ame; public class C implements I {public int f(){return 1;}}`,
		"ame/Root.java": `package ame; public final class Root {public static int run(){try{I x=new C();return x.f();}catch(AbstractMethodError e){return 11;}}}`,
	}, "ame/I", "ame/C", "ame/Root")
	verifyM5daAssertValue(t, func() (Result, error) {
		return RunClasses([][]byte{missingCaller["ame/I"], missingOld["ame/C"], missingCaller["ame/Root"]}, "ame/Root", "run", nil, verifyM5daComplexGas)
	}, 11)
}

func TestVerifyM5daOrdinaryHeapFullRaisesFreshCatchableOOMWithoutQuotaSideEffects(t *testing.T) {
	classfile := verifyM5daCompile(t, map[string]string{
		"VerifyM5daQuotas.java": `public final class VerifyM5daQuotas {
			public static int arrays(){Object[] keep=new Object[1024];try{for(int i=0;i<1024;i++)keep[i]=new int[0];return 0;}catch(OutOfMemoryError first){try{int[] ignored=new int[0];return ignored.length-1;}catch(OutOfMemoryError second){return first!=second?21:-2;}}}
			public static int objects(){Object[] keep=new Object[1025];try{for(int i=0;i<1025;i++)keep[i]=new Object();return 0;}catch(OutOfMemoryError first){try{new Object();return -1;}catch(OutOfMemoryError second){return first!=second?22:-2;}}}
			public static int elements(){int[][] keep=new int[4][];for(int i=0;i<3;i++)keep[i]=new int[65536];keep[3]=new int[65532];try{int[] ignored=new int[1];return ignored.length-2;}catch(OutOfMemoryError e){return 23;}}
			public static int perArray(){try{int[] ignored=new int[65537];return ignored.length;}catch(OutOfMemoryError e){return 24;}}
		}`,
	}, "VerifyM5daQuotas")["VerifyM5daQuotas"]
	for _, tc := range []struct {
		method string
		want   int32
	}{{"arrays", 21}, {"objects", 22}, {"elements", 23}, {"perArray", 24}} {
		t.Run(tc.method, func(t *testing.T) {
			verifyM5daAssertValue(t, func() (Result, error) { return Run(classfile, tc.method, nil, verifyM5daQuotaGas) }, tc.want)
		})
	}
}

func TestVerifyM5daExceptionArenaEmergencyRethrowResetAndObjectLayout(t *testing.T) {
	classes := verifyM5daCompile(t, map[string]string{
		"java/lang/Object.java": `package java.lang; public class Object { public int inherited; public Object link; public Object(){} }`,
		"arena/Root.java": `package arena; public final class Root {
			public static int run(int batch){Throwable[] seen=new Throwable[256];
				for(int i=0;i<256;i++){try{int[] x=null;int y=x.length;}catch(Throwable e){if(e.inherited!=0||e.link!=null)return -1;seen[i]=e;}}
				for(int i=batch*16;i<(batch+1)*16;i++)for(int j=0;j<i;j++)if(seen[j]==seen[i])return -2;
				try{int[] x=null;int y=x.length;}catch(OutOfMemoryError emergency){try{throw emergency;}catch(Throwable same){return emergency==same?257:-3;}}
				return 0;}
		}`,
	}, "java/lang/Object", "arena/Root")
	bundle := [][]byte{classes["java/lang/Object"], classes["arena/Root"]}
	// The original all-pairs scan alone costs over 1B gas, not an arena failure.
	// Retain all 32,640 comparisons in 16 bounded runs, each freshly allocating
	// the same 256 exceptions before checking its rows. Every run also checks
	// inherited defaults, the 257th emergency OOM, rethrow identity and reset.
	for batch := int32(0); batch < 16; batch++ {
		t.Run(fmt.Sprintf("rows-%03d-%03d", batch*16, batch*16+15), func(t *testing.T) {
			result := verifyM5daAssertValue(t, func() (Result, error) {
				return RunClasses(bundle, "arena/Root", "run", []int32{batch}, verifyM5daQuotaGas)
			}, 257)
			t.Logf("M5d-a arena batch=%d gas=%d limit=%d", batch, result.GasUsed, verifyM5daQuotaGas)
		})
	}
}

func TestVerifyM5daInitializationBoundariesDependentsRootAndConstructorPoison(t *testing.T) {
	classes := verifyM5daCompile(t, map[string]string{
		"init/Bad.java":       `package init; public class Bad {static int count;static int value=fail();static int fail(){count++;return 1/0;}}`,
		"init/Dependent.java": `package init; public class Dependent extends Bad {static int own=9;}`,
		"init/Caught.java":    `package init; public class Caught {static int value;static {try{value=1/0;}catch(ArithmeticException e){value=7;}}}`,
		"init/Outer.java":     `package init; public class Outer {static int value;static {try{value=Bad.value;}catch(Error e){value=8;}}}`,
		"init/Root.java": `package init; public final class Root {
			static int dormant=Bad.value;
			public static int rootCannotCatch(){try{return 1;}catch(Throwable e){return 99;}}
		}`,
		"init/Body.java": `package init; public final class Body {public static int caught(){return Caught.value;}public static int outer(){return Outer.value;}public static int failed(){try{return Dependent.own;}catch(ExceptionInInitializerError e){}try{return Dependent.own;}catch(NoClassDefFoundError e){try{return Bad.value;}catch(NoClassDefFoundError b){return 12;}}}}`,
	}, "init/Bad", "init/Dependent", "init/Caught", "init/Outer", "init/Root", "init/Body")
	// A separate non-failing root ensures dormant Root initialization does not
	// prevent the body tests from being entered.
	bundle := verifyM5daBundle(classes)
	verifyM5daAssertValue(t, func() (Result, error) { return RunClasses(bundle, "init/Body", "caught", nil, verifyM5daComplexGas) }, 7)
	verifyM5daAssertValue(t, func() (Result, error) { return RunClasses(bundle, "init/Body", "outer", nil, verifyM5daComplexGas) }, 8)
	verifyM5daAssertValue(t, func() (Result, error) { return RunClasses(bundle, "init/Body", "failed", nil, verifyM5daComplexGas) }, 12)
	// Root initialization precedes method eligibility; its catch(Throwable) is dormant.
	verifyM5daAssertException(t, func() (Result, error) {
		return RunClasses(bundle, "init/Root", "rootCannotCatch", nil, verifyM5daComplexGas)
	}, "java.lang.ExceptionInInitializerError", 3)

	ctors := verifyM5daCompile(t, map[string]string{
		"poison/Bad.java":  `package poison; public class Bad {int value;Bad(){value=1/0;}}`,
		"poison/Good.java": `package poison; public class Good {int value;Good(){super();try{helper();}catch(ArithmeticException e){value=7;}}void helper(){int x=1/0;}}`,
		"poison/Root.java": `package poison; public final class Root {public static int run(){try{new Bad();}catch(ArithmeticException e){return new Good().value;}return 0;}}`,
	}, "poison/Bad", "poison/Good", "poison/Root")
	verifyM5daAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM5daBundle(ctors), "poison/Root", "run", nil, verifyM5daComplexGas)
	}, 7)
}

func TestVerifyM5daInitSchedulingAtFrameCapLeavesNoStickyInitializingState(t *testing.T) {
	all := verifyM5daCompile(t, map[string]string{
		"sched/Root.java":   `package sched; public final class Root {static int deep(int n){if(n==126){try{return Target.value;}catch(StackOverflowError e){return 1;}}return deep(n+1);}public static int run(){return deep(0)*10+Target.value;}}`,
		"sched/Target.java": `package sched; public final class Target {static int value=7;}`,
	}, "sched/Root", "sched/Target")
	verifyM5daAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM5daBundle(all), "sched/Root", "run", nil, verifyM5daComplexGas)
	}, 17)
}

func TestVerifyM5daKind12DecoderAndUnknown13RemainStrict(t *testing.T) {
	payload := make([]byte, 36)
	copy(payload, javaExceptionSelector)
	payload[35] = 12
	if got, ok := decodeJavaException(payload); !ok || got != "java.lang.NoClassDefFoundError" {
		t.Fatalf("decode kind12=(%q,%v), want exact NoClassDefFoundError", got, ok)
	}
	payload[35] = 13
	if got, ok := decodeJavaException(payload); ok || got != "" {
		t.Fatalf("decode unknown kind13=(%q,%v), want strict rejection", got, ok)
	}
	payload[4] = 1
	payload[35] = 12
	if got, ok := decodeJavaException(payload); ok || got != "" {
		t.Fatalf("decode noncanonical kind12=(%q,%v), want strict rejection", got, ok)
	}
}

func TestVerifyM5daValidationAndOOGNeverEnterGuestHandlers(t *testing.T) {
	classfile := verifyM5daCompile(t, map[string]string{
		"VerifyM5daHard.java": `public final class VerifyM5daHard {
			static int bad(){return 1/0;}
			public static int validation(){try{return bad();}catch(Throwable e){return 1;}}
			public static int forever(){try{for(;;){}}catch(Throwable e){return 2;}}
		}`,
	}, "VerifyM5daHard")["VerifyM5daHard"]
	malformed := verifyM5daMutate(t, classfile, func(out []byte, c verifyM5daClass) {
		m := c.method(t, "bad", "()I")
		pc := verifyM5daOpcodePC(t, m.code, 0x6c, 0)
		m.code[pc] = 0xca // unsupported breakpoint, a validation failure.
	})
	verifyM5daAssertError(t, func() (Result, error) { return Run(malformed, "validation", nil, verifyM5daSimpleGas) }, "BytecodeError(uint256,uint256)", 6, nil)
	const lowGas = uint64(300_000)
	result, err := Run(classfile, "forever", nil, lowGas)
	if err == nil || !errors.Is(err, vm.ErrOutOfGas) || result.ExceptionClass != "" || result.GasUsed != lowGas || len(result.RevertData) != 0 {
		t.Fatalf("result/error=%+v/%v want hard EVM OOG outside catch(Throwable)", result, err)
	}
}

// --- verifier-only classfile inspection and assertions ---

type verifyM5daCP struct {
	tag    byte
	offset int
}
type verifyM5daHandler struct {
	offset                        int
	start, end, target, catchType uint16
}
type verifyM5daMethod struct {
	index                                                int
	name, descriptor                                     string
	code                                                 []byte
	maxStackOffset, codeLengthOffset, handlerCountOffset int
	codeAttrLengthOffset, codeAttrEnd                    int
	handlers                                             []verifyM5daHandler
}
type verifyM5daClass struct {
	data                         []byte
	cpCount, cpEnd, accessOffset int
	access                       uint16
	cp                           []verifyM5daCP
	utf                          map[uint16]string
	methods                      []verifyM5daMethod
}

func verifyM5daCompile(t *testing.T, sources map[string]string, names ...string) map[string][]byte {
	t.Helper()
	return compileBundleValidationJava(t, sources, names...)
}
func verifyM5daBundle(classes map[string][]byte) [][]byte {
	keys := make([]string, 0, len(classes))
	for k := range classes {
		keys = append(keys, k)
	}
	// Deterministic input order without depending on another stage's helper.
	for i := 1; i < len(keys); i++ {
		for j := i; j > 0 && keys[j] < keys[j-1]; j-- {
			keys[j], keys[j-1] = keys[j-1], keys[j]
		}
	}
	out := make([][]byte, len(keys))
	for i, k := range keys {
		out[i] = classes[k]
	}
	return out
}
func verifyM5daParse(t *testing.T, data []byte) verifyM5daClass {
	t.Helper()
	pos := 0
	need := func(n int) {
		if n < 0 || pos < 0 || pos+n > len(data) {
			t.Fatalf("truncated verifier class at %d need %d", pos, n)
		}
	}
	u1 := func() byte { need(1); v := data[pos]; pos++; return v }
	u2 := func() uint16 { need(2); v := binary.BigEndian.Uint16(data[pos:]); pos += 2; return v }
	u4 := func() uint32 { need(4); v := binary.BigEndian.Uint32(data[pos:]); pos += 4; return v }
	skip := func(n int) { need(n); pos += n }
	if len(data) < 10 || binary.BigEndian.Uint32(data[:4]) != 0xcafebabe {
		t.Fatal("bad verifier fixture magic")
	}
	pos = 8
	count := int(u2())
	c := verifyM5daClass{data: data, cpCount: count, cp: make([]verifyM5daCP, count), utf: map[uint16]string{}}
	for i := 1; i < count; i++ {
		off := pos
		tag := u1()
		c.cp[i] = verifyM5daCP{tag, off}
		switch tag {
		case 1:
			n := int(u2())
			need(n)
			c.utf[uint16(i)] = string(data[pos : pos+n])
			skip(n)
		case 3, 4, 9, 10, 11, 12, 17, 18:
			skip(4)
		case 5, 6:
			skip(8)
			i++
		case 7, 8, 16, 19, 20:
			skip(2)
		case 15:
			skip(3)
		default:
			t.Fatalf("unknown verifier CP tag %d", tag)
		}
	}
	c.cpEnd = pos
	c.accessOffset = pos
	c.access = u2()
	skip(4)
	for n := int(u2()); n > 0; n-- {
		skip(2)
	}
	attrs := func(record bool, index int, name, desc string) []verifyM5daMethod {
		n := int(u2())
		var got []verifyM5daMethod
		for ; n > 0; n-- {
			nameIndex := u2()
			lengthOffset := pos
			length := int(u4())
			start := pos
			need(length)
			if record && c.utf[nameIndex] == "Code" {
				if length < 10 {
					t.Fatal("short verifier Code")
				}
				maxOff := start
				skip(4)
				codeLenOff := pos
				codeLen := int(u4())
				codeOff := pos
				skip(codeLen)
				tableOff := pos
				hn := int(u2())
				hs := make([]verifyM5daHandler, hn)
				for i := range hs {
					off := pos
					hs[i] = verifyM5daHandler{off, u2(), u2(), u2(), u2()}
				}
				got = append(got, verifyM5daMethod{index, name, desc, data[codeOff : codeOff+codeLen], maxOff, codeLenOff, tableOff, lengthOffset, start + length, hs})
			}
			pos = start + length
		}
		return got
	}
	for n := int(u2()); n > 0; n-- {
		skip(6)
		attrs(false, 0, "", "")
	}
	methods := int(u2())
	for i := 0; i < methods; i++ {
		skip(2)
		name := c.utf[u2()]
		desc := c.utf[u2()]
		c.methods = append(c.methods, attrs(true, i, name, desc)...)
	}
	return c
}
func (c verifyM5daClass) method(t *testing.T, name, desc string) verifyM5daMethod {
	t.Helper()
	for _, m := range c.methods {
		if m.name == name && m.descriptor == desc {
			return m
		}
	}
	t.Fatalf("method %s%s absent", name, desc)
	return verifyM5daMethod{}
}
func (c verifyM5daClass) cpEntry(t *testing.T, index uint16) verifyM5daCP {
	t.Helper()
	if index == 0 || int(index) >= len(c.cp) || c.cp[index].tag == 0 {
		t.Fatalf("bad test CP %d", index)
	}
	return c.cp[index]
}
func (c verifyM5daClass) classNameIndex(t *testing.T, index uint16) uint16 {
	t.Helper()
	e := c.cpEntry(t, index)
	if e.tag != 7 {
		t.Fatalf("CP %d tag=%d want Class", index, e.tag)
	}
	return binary.BigEndian.Uint16(c.data[e.offset+1:])
}
func (c verifyM5daClass) classIndex(t *testing.T, name string) uint16 {
	t.Helper()
	for i, e := range c.cp {
		if e.tag == 7 && c.utf[binary.BigEndian.Uint16(c.data[e.offset+1:])] == name {
			return uint16(i)
		}
	}
	t.Fatalf("Class CP %q absent", name)
	return 0
}
func verifyM5daMutate(t *testing.T, in []byte, fn func([]byte, verifyM5daClass)) []byte {
	t.Helper()
	out := append([]byte(nil), in...)
	fn(out, verifyM5daParse(t, out))
	return out
}
func verifyM5daEditHandler(t *testing.T, in []byte, method string, index int, fn func([]byte)) []byte {
	t.Helper()
	return verifyM5daEditHandlerByName(t, in, method, index, fn)
}

func verifyM5daMethodByName(t *testing.T, c verifyM5daClass, name string) verifyM5daMethod {
	t.Helper()
	var found *verifyM5daMethod
	for i := range c.methods {
		if c.methods[i].name == name {
			if found != nil {
				t.Fatalf("overloaded method %s", name)
			}
			found = &c.methods[i]
		}
	}
	if found == nil {
		t.Fatalf("method %s absent", name)
	}
	return *found
}
func verifyM5daEditHandlerByName(t *testing.T, in []byte, method string, index int, fn func([]byte)) []byte {
	t.Helper()
	return verifyM5daMutate(t, in, func(out []byte, c verifyM5daClass) {
		m := verifyM5daMethodByName(t, c, method)
		if index < 0 || index >= len(m.handlers) {
			t.Fatalf("handler %d absent", index)
		}
		fn(out[m.handlers[index].offset : m.handlers[index].offset+8])
	})
}

func verifyM5daStripCodeAttributes(t *testing.T, in []byte, method string) []byte {
	t.Helper()
	c := verifyM5daParse(t, in)
	m := verifyM5daMethodByName(t, c, method)
	attributesCount := m.handlerCountOffset + 2 + 8*len(m.handlers)
	if attributesCount+2 > m.codeAttrEnd {
		t.Fatal("invalid nested Code attributes offset")
	}
	out := make([]byte, len(in)-(m.codeAttrEnd-(attributesCount+2)))
	copy(out, in[:attributesCount])
	// nested attributes_count is zero in the shortened Code attribute.
	copy(out[attributesCount+2:], in[m.codeAttrEnd:])
	dataStart := m.codeAttrEnd - int(binary.BigEndian.Uint32(in[m.codeAttrLengthOffset:]))
	binary.BigEndian.PutUint32(out[m.codeAttrLengthOffset:], uint32(attributesCount+2-dataStart))
	return out
}

func verifyM5daExpandHandlers(t *testing.T, in []byte, method string, want int) []byte {
	t.Helper()
	c := verifyM5daParse(t, in)
	m := verifyM5daMethodByName(t, c, method)
	if len(m.handlers) < 1 || want < len(m.handlers) {
		t.Fatal("bad handler expansion")
	}
	add := want - len(m.handlers)
	insert := m.handlerCountOffset + 2 + 8*len(m.handlers)
	out := make([]byte, len(in)+8*add)
	copy(out, in[:insert])
	for i := 0; i < add; i++ {
		copy(out[insert+8*i:], in[m.handlers[0].offset:m.handlers[0].offset+8])
	}
	copy(out[insert+8*add:], in[insert:])
	binary.BigEndian.PutUint16(out[m.handlerCountOffset:], uint16(want))
	old := binary.BigEndian.Uint32(in[m.codeAttrLengthOffset:])
	binary.BigEndian.PutUint32(out[m.codeAttrLengthOffset:], old+uint32(8*add))
	return out
}
func verifyM5daAppendClass(t *testing.T, in []byte, name string) ([]byte, uint16) {
	t.Helper()
	c := verifyM5daParse(t, in)
	if c.cpCount > 65533 || len(name) > 65535 {
		t.Fatal("CP append overflow")
	}
	extra := 3 + len(name) + 3
	out := make([]byte, len(in)+extra)
	copy(out, in[:c.cpEnd])
	p := c.cpEnd
	out[p] = 1
	binary.BigEndian.PutUint16(out[p+1:], uint16(len(name)))
	copy(out[p+3:], name)
	p += 3 + len(name)
	out[p] = 7
	binary.BigEndian.PutUint16(out[p+1:], uint16(c.cpCount))
	copy(out[p+3:], in[c.cpEnd:])
	binary.BigEndian.PutUint16(out[8:], uint16(c.cpCount+2))
	return out, uint16(c.cpCount + 1)
}
func verifyM5daInstructionWidth(t *testing.T, code []byte, pc int) int {
	t.Helper()
	if pc < 0 || pc >= len(code) {
		t.Fatalf("invalid instruction pc %d", pc)
	}
	width := 1
	switch code[pc] {
	case 0x10, 0x12, 0x15, 0x16, 0x17, 0x18, 0x19, 0x36, 0x37, 0x38, 0x39, 0x3a, 0xa9, 0xbc:
		width = 2
	case 0x11, 0x13, 0x14, 0x84,
		0x99, 0x9a, 0x9b, 0x9c, 0x9d, 0x9e, 0x9f, 0xa0, 0xa1, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6, 0xa7, 0xa8,
		0xb2, 0xb3, 0xb4, 0xb5, 0xb6, 0xb7, 0xb8, 0xbb, 0xbd, 0xc0, 0xc1, 0xc6, 0xc7:
		width = 3
	case 0xb9, 0xba, 0xc8, 0xc9:
		width = 5
	case 0xc5:
		width = 4
	case 0xc4:
		if pc+1 >= len(code) {
			t.Fatalf("truncated wide at pc %d", pc)
		}
		if code[pc+1] == 0x84 {
			width = 6
		} else {
			width = 4
		}
	case 0xaa:
		header := pc + 1 + (4-((pc+1)%4))%4
		if header+12 > len(code) {
			t.Fatalf("truncated tableswitch at pc %d", pc)
		}
		low := int64(int32(binary.BigEndian.Uint32(code[header+4:])))
		high := int64(int32(binary.BigEndian.Uint32(code[header+8:])))
		count := high - low + 1
		if count < 0 || count > int64((len(code)-header-12)/4) {
			t.Fatalf("bad tableswitch count %d", count)
		}
		width = header - pc + 12 + int(count)*4
	case 0xab:
		header := pc + 1 + (4-((pc+1)%4))%4
		if header+8 > len(code) {
			t.Fatalf("truncated lookupswitch at pc %d", pc)
		}
		count := int64(int32(binary.BigEndian.Uint32(code[header+4:])))
		if count < 0 || count > int64((len(code)-header-8)/8) {
			t.Fatalf("bad lookupswitch count %d", count)
		}
		width = header - pc + 8 + int(count)*8
	}
	if pc+width > len(code) {
		t.Fatalf("truncated opcode %02x at pc %d", code[pc], pc)
	}
	return width
}
func verifyM5daOpcodePC(t *testing.T, code []byte, opcode byte, occ int) int {
	t.Helper()
	seen := 0
	for pc := 0; pc < len(code); pc += verifyM5daInstructionWidth(t, code, pc) {
		if code[pc] == opcode {
			if seen == occ {
				return pc
			}
			seen++
		}
	}
	t.Fatalf("opcode %02x occurrence %d absent in %x", opcode, occ, code)
	return 0
}
func verifyM5daOperandPC(t *testing.T, code []byte) int {
	t.Helper()
	for pc := 0; pc < len(code); pc += verifyM5daInstructionWidth(t, code, pc) {
		if verifyM5daInstructionWidth(t, code, pc) > 1 {
			return pc + 1
		}
	}
	t.Fatalf("no operand byte in %x", code)
	return 0
}
func verifyM5daUint64(v uint64) *uint64 { return &v }
func verifyM5daAssertValue(t *testing.T, run func() (Result, error), want int32) Result {
	t.Helper()
	r, e := run()
	if e != nil || r.ExceptionClass != "" || r.Value != want || r.GasUsed == 0 {
		t.Fatalf("result/error=%+v/%v want value %d", r, e, want)
	}
	return r
}
func verifyM5daAssertException(t *testing.T, run func() (Result, error), name string, kind byte) Result {
	t.Helper()
	r, e := run()
	if e != nil || r.ExceptionClass != name || r.GasUsed == 0 || len(r.RevertData) != 36 || !bytes.Equal(r.RevertData[:4], crypto.Keccak256([]byte("JavaException(uint256)"))[:4]) || r.RevertData[35] != kind {
		t.Fatalf("result/error=%+v/%v want JavaException(%d) %s", r, e, kind, name)
	}
	return r
}
func verifyM5daWord(t *testing.T, b []byte) uint64 {
	t.Helper()
	if len(b) != 32 || !bytes.Equal(b[:24], make([]byte, 24)) {
		t.Fatalf("noncanonical uint256 %x", b)
	}
	return binary.BigEndian.Uint64(b[24:])
}
func verifyM5daAssertHandlerError(t *testing.T, run func() (Result, error), code, classIndex, methodIndex, entryIndex uint64) {
	t.Helper()
	r, e := run()
	sig := "HandlerError(uint256,uint256,uint256,uint256)"
	if e == nil || !strings.Contains(e.Error(), "execution reverted") || r.ExceptionClass != "" || r.GasUsed == 0 || len(r.RevertData) != 132 || !bytes.Equal(r.RevertData[:4], crypto.Keccak256([]byte(sig))[:4]) {
		t.Fatalf("result/error=%+v/%v want exact %s", r, e, sig)
	}
	got := []uint64{verifyM5daWord(t, r.RevertData[4:36]), verifyM5daWord(t, r.RevertData[36:68]), verifyM5daWord(t, r.RevertData[68:100])}
	for i, w := range []uint64{code, classIndex, methodIndex} {
		if got[i] != w {
			t.Fatalf("HandlerError words=%v entry=%x want [%d %d %d %d]", got, r.RevertData[100:132], code, classIndex, methodIndex, entryIndex)
		}
	}
	last := r.RevertData[100:132]
	if entryIndex == math.MaxUint64 {
		if !bytes.Equal(last, bytes.Repeat([]byte{0xff}, 32)) {
			t.Fatalf("entryIndex=%x want uint256.max", last)
		}
	} else if verifyM5daWord(t, last) != entryIndex {
		t.Fatalf("entryIndex=%x want %d", last, entryIndex)
	}
}
func verifyM5daAssertError(t *testing.T, run func() (Result, error), sig string, code uint64, location *uint64) {
	t.Helper()
	r, e := run()
	if e == nil || !strings.Contains(e.Error(), "execution reverted") || r.ExceptionClass != "" || r.GasUsed == 0 || len(r.RevertData) != 68 || !bytes.Equal(r.RevertData[:4], crypto.Keccak256([]byte(sig))[:4]) {
		t.Fatalf("result/error=%+v/%v want %s", r, e, sig)
	}
	if verifyM5daWord(t, r.RevertData[4:36]) != code {
		t.Fatalf("%s data=%x want code %d", sig, r.RevertData, code)
	}
	if location != nil && (len(r.RevertData) != 68 || verifyM5daWord(t, r.RevertData[36:68]) != *location) {
		t.Fatalf("%s data=%x want location %d", sig, r.RevertData, *location)
	}
}
