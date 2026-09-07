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

const verifyM4aGasLimit = uint64(100_000_000)

// All Java below is trusted test input. Test-only bytecode mutation is used only
// to isolate verifier failures that javac cannot emit. Production Run/RunClasses
// still receive raw classfiles and expose no parser, heap, or reference test API.

func TestVerifyM4aArrayIdentityAliasingLocalsAndRecursiveCalls(t *testing.T) {
	classfile := compileJava(t, "ArrayIdentity", `
public final class ArrayIdentity {
    static int fill(int[] a, int i) {
        if (i == a.length) return 0;
        a[i] = i * 3 + 1;
        return a[i] + fill(a, i + 1);
    }
    static int[] make(int n) { return new int[n]; }
    public static int run(int n) {
        int[] a = make(n);
        int[] alias = a;
        int[] distinct = make(n);
        int sum = fill(alias, 0);
        distinct[0] = 99;
        return sum * 100 + (a == alias ? 10 : 0) + (a != distinct ? 1 : 0);
    }
    public static int zeroIdentity() {
        int[] a = new int[0]; int[] b = new int[0]; int[] alias = a;
        return (a == alias ? 10 : 0) + (a != b ? 1 : 0);
    }
    public static int nullIdentity() {
        int[] a = null; int[] b = null;
        return (a == b ? 10 : 0) + (a != new int[0] ? 1 : 0);
    }
    public static int zeroed(int n) {
        int[] a = new int[n];
        return a[0] + a[n - 1] + a.length;
    }
}`)
	verifyM4aAssertValue(t, func() (Result, error) {
		return Run(classfile, "run", []int32{4}, verifyM4aGasLimit)
	}, 2211)
	verifyM4aAssertValue(t, func() (Result, error) {
		return Run(classfile, "zeroIdentity", nil, verifyM4aGasLimit)
	}, 11)
	verifyM4aAssertValue(t, func() (Result, error) {
		return Run(classfile, "nullIdentity", nil, verifyM4aGasLimit)
	}, 11)
	verifyM4aAssertValue(t, func() (Result, error) {
		return Run(classfile, "zeroed", []int32{3}, verifyM4aGasLimit)
	}, 3)
}

func TestVerifyM4aReferencesCrossFramesStaticsAndInheritance(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"arraycross/Parent.java": `package arraycross; public class Parent {
            public static int[] shared;
            static { shared = Helper.make(3); shared[0] = 4; }
            public static int inherited() { return shared[0]; }
        }`,
		"arraycross/Child.java": `package arraycross; public class Child extends Parent { }`,
		"arraycross/Helper.java": `package arraycross; public final class Helper {
            static int[] make(int n) { return new int[n]; }
            static int[] pass(int[] a) { return a; }
            static void mutate(int[] a, int i, int v) { a[i] = v; }
        }`,
		"arraycross/Root.java": `package arraycross; public final class Root {
            static int recurse(int[] a, int n) {
                if (n == 0) return a[0];
                Helper.mutate(a, 0, a[0] + 1);
                return recurse(Helper.pass(a), n - 1);
            }
            public static int run(int n) {
                int[] before = Child.shared;
                int value = recurse(before, n);
                return value * 100 + (before == Parent.shared ? 10 : 0) + Child.inherited();
            }
        }`,
	}, "arraycross/Parent", "arraycross/Child", "arraycross/Helper", "arraycross/Root")
	bundle := [][]byte{classes["arraycross/Child"], classes["arraycross/Root"], classes["arraycross/Helper"], classes["arraycross/Parent"]}
	verifyM4aAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "arraycross/Root", "run", []int32{3}, verifyM4aGasLimit)
	}, 717)
	// Heap and static state are invocation-local. A second run starts again at 4.
	verifyM4aAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "arraycross/Root", "run", []int32{3}, verifyM4aGasLimit)
	}, 717)
}

func TestVerifyM4aRootReferenceSignaturesRemainRejected(t *testing.T) {
	classfile := compileJava(t, "RootReference", `public final class RootReference {
        public static int takes(int[] a) { return a == null ? 1 : 2; }
        public static int[] returns() { return new int[1]; }
        public static int scalar(int x) { return x; }
    }`)
	for _, tc := range []struct {
		method string
		args   []int32
	}{
		{"takes", nil}, {"takes", []int32{0}}, {"returns", nil},
	} {
		t.Run(tc.method+fmt.Sprint(tc.args), func(t *testing.T) {
			result, err := Run(classfile, tc.method, tc.args, verifyM4aGasLimit)
			verifyM4aAssertMethodError(t, result, err, 11)
		})
	}
	verifyM4aAssertValue(t, func() (Result, error) {
		return Run(classfile, "scalar", []int32{0}, verifyM4aGasLimit)
	}, 0)
}

func TestVerifyM4aNullBoundsNegativeAndOrdering(t *testing.T) {
	classfile := compileJava(t, "ArrayFaults", `public final class ArrayFaults {
        public static int negative(int n) { return new int[n].length; }
        public static int lengthNull(int ignored) { int[] a = null; return a.length; }
        public static int loadNull(int i) { int[] a = null; return a[i]; }
        public static int storeNull(int i) { int[] a = null; a[i] = 7; return 1; }
        public static int loadBounds(int i) { return (new int[2])[i]; }
        public static int storeBounds(int i) { int[] a = new int[2]; a[i] = 7; return 1; }
    }`)
	verifyM4aAssertException(t, func() (Result, error) {
		return Run(classfile, "negative", []int32{-1}, verifyM4aGasLimit)
	}, "java.lang.NegativeArraySizeException", 4)
	verifyM4aAssertException(t, func() (Result, error) {
		return Run(classfile, "negative", []int32{-2147483648}, verifyM4aGasLimit)
	}, "java.lang.NegativeArraySizeException", 4)
	// Null is checked before either negative or high-index bounds checks.
	for _, tc := range []struct {
		method string
		index  int32
	}{
		{"lengthNull", 65537}, {"loadNull", -1}, {"loadNull", 65537},
		{"storeNull", -1}, {"storeNull", 65537},
	} {
		t.Run(tc.method+fmt.Sprint(tc.index), func(t *testing.T) {
			verifyM4aAssertException(t, func() (Result, error) {
				return Run(classfile, tc.method, []int32{tc.index}, verifyM4aGasLimit)
			}, "java.lang.NullPointerException", 6)
		})
	}
	for _, tc := range []struct {
		method string
		index  int32
	}{
		{"loadBounds", -1}, {"loadBounds", 2}, {"storeBounds", -1}, {"storeBounds", 2},
	} {
		t.Run(tc.method+fmt.Sprint(tc.index), func(t *testing.T) {
			verifyM4aAssertException(t, func() (Result, error) {
				return Run(classfile, tc.method, []int32{tc.index}, verifyM4aGasLimit)
			}, "java.lang.ArrayIndexOutOfBoundsException", 5)
		})
	}
}

func TestVerifyM4aInitializerExceptionKindsOOMAndOOG(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"initarray/Negative.java": `package initarray; public final class Negative {
            static int[] value = new int[-1]; public static int run() { return 1; } }`,
		"initarray/Bounds.java": `package initarray; public final class Bounds {
            static int value = initialize(); static int initialize() { return (new int[1])[1]; }
            public static int run() { return value; } }`,
		"initarray/Null.java": `package initarray; public final class Null {
            static int value = initialize(); static int initialize() { int[] a=null; return a.length; }
            public static int run() { return value; } }`,
		"initarray/OOM.java": `package initarray; public final class OOM {
            static int[] value = new int[65537]; public static int run() { return value.length; } }`,
	}, "initarray/Negative", "initarray/Bounds", "initarray/Null", "initarray/OOM")
	for _, name := range []string{"Negative", "Bounds", "Null"} {
		t.Run(name, func(t *testing.T) {
			verifyM4aAssertException(t, func() (Result, error) {
				return Run(classes["initarray/"+name], "run", nil, verifyM4aGasLimit)
			}, "java.lang.ExceptionInInitializerError", 3)
		})
	}
	verifyM4aAssertException(t, func() (Result, error) {
		return Run(classes["initarray/OOM"], "run", nil, verifyM4aGasLimit)
	}, "java.lang.OutOfMemoryError", 7)

	result, err := Run(classes["initarray/OOM"], "run", nil, 1)
	if err == nil || !errors.Is(err, vm.ErrOutOfGas) {
		t.Fatalf("result/error = %+v/%v, want true EVM out of gas", result, err)
	}
	if result.ExceptionClass != "" || len(result.RevertData) != 0 {
		t.Fatalf("OOG was mislabeled as a Java array outcome: %+v", result)
	}
}

func TestVerifyM4aLogicalHeapCapsAndNoGCAccounting(t *testing.T) {
	classfile := compileJava(t, "ArrayCaps", `public final class ArrayCaps {
        public static int one(int n) { return new int[n].length; }
        public static int arrays(int count) {
            int[] waste = null;
            for (int i = 0; i < count; i++) waste = new int[0];
            return count + (waste == null ? 0 : 0);
        }
        public static int exactTotal() {
            int[] waste;
            waste = new int[65536]; waste = new int[65536];
            waste = new int[65536]; waste = new int[65536];
            return 262144 + (waste == null ? 0 : 0);
        }
        public static int overTotal() {
            int[] waste;
            waste = new int[65536]; waste = new int[65536];
            waste = new int[65536]; waste = new int[65536];
            waste = new int[1]; return waste.length;
        }
    }`)
	verifyM4aAssertValue(t, func() (Result, error) {
		return Run(classfile, "one", []int32{65536}, verifyM4aGasLimit)
	}, 65536)
	verifyM4aAssertException(t, func() (Result, error) {
		return Run(classfile, "one", []int32{65537}, verifyM4aGasLimit)
	}, "java.lang.OutOfMemoryError", 7)
	verifyM4aAssertValue(t, func() (Result, error) {
		return Run(classfile, "arrays", []int32{1024}, verifyM4aGasLimit)
	}, 1024)
	verifyM4aAssertException(t, func() (Result, error) {
		return Run(classfile, "arrays", []int32{1025}, verifyM4aGasLimit)
	}, "java.lang.OutOfMemoryError", 7)
	verifyM4aAssertValue(t, func() (Result, error) {
		return Run(classfile, "exactTotal", nil, verifyM4aGasLimit)
	}, 262144)
	verifyM4aAssertException(t, func() (Result, error) {
		return Run(classfile, "overTotal", nil, verifyM4aGasLimit)
	}, "java.lang.OutOfMemoryError", 7)
	// The 1025 allocations above are unreachable immediately, but still count:
	// this stage deliberately has no GC. A fresh invocation resets the counter.
	verifyM4aAssertValue(t, func() (Result, error) {
		return Run(classfile, "arrays", []int32{1024}, verifyM4aGasLimit)
	}, 1024)
}

func TestVerifyM4aFinalReferenceAllowsElementMutationButNotRebinding(t *testing.T) {
	original := compileJava(t, "FinalArray", `public final class FinalArray {
        static final int[] fixed = new int[1];
        static int[] mutable = new int[1];
        public static int element(int x) { fixed[0] = x; return fixed[0]; }
        public static int rebind(int n) { mutable = new int[n]; return mutable.length; }
    }`)
	verifyM4aAssertValue(t, func() (Result, error) {
		return Run(original, "element", []int32{37}, verifyM4aGasLimit)
	}, 37)
	parsed := parseStaticsClass(t, original)
	_, putPC := parsed.fieldInstruction(t, "rebind", opPutstatic, 0)
	mutated := mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
		field := c.field(t, "mutable", "[I")
		binary.BigEndian.PutUint16(out[field.accessOffset:], field.access|accFinal)
	})
	verifyM4aAssertError(t, func() (Result, error) {
		return Run(mutated, "rebind", []int32{2}, verifyM4aGasLimit)
	}, "FieldError(uint256,uint256)", 4, uint64(putPC))
}

func TestVerifyM4aAllCategoryOneStackPermutationFormsPreserveValueAndKind(t *testing.T) {
	original := verifyM4aCompileStackFixture(t, []string{
		"pop", "dup", "pop2", "dupX1", "dupX2", "dup2", "dup2X1", "dup2X2", "swap",
	})
	tests := []struct {
		name string
		code []byte
		want int32
	}{
		{"pop", []byte{0x04, 0x57, 0x10, 41, 0xac}, 41},
		{"dup", []byte{0x06, 0x59, 0x60, 0xac}, 6},
		{"pop2", []byte{0x04, 0xbc, 10, 0x08, 0x58, 0x10, 42, 0xac}, 42},
		// dup_x1: [int(4), ref] -> [ref, int(4), ref]. Typed stores
		// validate kind order; mutation through one saved ref validates identity.
		{"dupX1", []byte{
			0x04, 0xbc, 10, 0x3a, 0,
			0x07, 0x19, 0, 0x5a, 0x3a, 1, 0x36, 2, 0x3a, 3,
			0x19, 1, 0x03, 0x10, 9, 0x4f,
			0x19, 3, 0x03, 0x2e, 0x15, 2, 0x60, 0xac,
		}, 13},
		// dup_x2: [ref,2,3] -> [3,ref,2,3].
		{"dupX2", []byte{
			0x04, 0xbc, 10, 0x3a, 0,
			0x19, 0, 0x05, 0x06, 0x5b, 0x36, 1, 0x36, 2, 0x3a, 3, 0x36, 4,
			0x19, 3, 0x03, 0x10, 7, 0x4f,
			0x15, 1, 0x10, 100, 0x68, 0x15, 2, 0x10, 10, 0x68, 0x60,
			0x15, 4, 0x60, 0x19, 0, 0x03, 0x2e, 0x60, 0xac,
		}, 330},
		// dup2: [ref,2] -> [ref,2,ref,2].
		{"dup2", []byte{
			0x04, 0xbc, 10, 0x3a, 0,
			0x19, 0, 0x05, 0x5c, 0x36, 1, 0x3a, 2, 0x36, 3, 0x3a, 4,
			0x19, 2, 0x03, 0x10, 11, 0x4f,
			0x19, 4, 0x03, 0x2e, 0x15, 1, 0x60, 0x15, 3, 0x60, 0xac,
		}, 15},
		// dup2_x1: [4,ref,2] -> [ref,2,4,ref,2].
		{"dup2X1", []byte{
			0x04, 0xbc, 10, 0x3a, 0,
			0x07, 0x19, 0, 0x05, 0x5d, 0x36, 1, 0x3a, 2, 0x36, 3, 0x36, 4, 0x3a, 5,
			0x19, 2, 0x03, 0x10, 9, 0x4f,
			0x19, 5, 0x03, 0x2e, 0x15, 1, 0x60, 0x15, 3, 0x60, 0x15, 4, 0x60, 0xac,
		}, 17},
		// dup2_x2: [A,2,B,3] -> [B,3,A,2,B,3]. A and B are distinct.
		{"dup2X2", []byte{
			0x04, 0xbc, 10, 0x3a, 0, 0x04, 0xbc, 10, 0x3a, 1,
			0x19, 0, 0x05, 0x19, 1, 0x06, 0x5e,
			0x36, 2, 0x3a, 3, 0x36, 4, 0x3a, 5, 0x36, 6, 0x3a, 7,
			0x19, 5, 0x03, 0x10, 7, 0x4f, 0x19, 3, 0x03, 0x10, 9, 0x4f,
			0x19, 0, 0x03, 0x2e, 0x19, 1, 0x03, 0x2e, 0x60,
			0x15, 2, 0x60, 0x15, 4, 0x60, 0x15, 6, 0x60, 0xac,
		}, 24},
		// swap: [int(4),ref] -> [ref,int(4)].
		{"swap", []byte{
			0x04, 0xbc, 10, 0x3a, 0, 0x07, 0x19, 0, 0x5f, 0x36, 1, 0x3a, 2,
			0x19, 2, 0x03, 0x10, 8, 0x4f, 0x19, 0, 0x03, 0x2e, 0x15, 1, 0x60, 0xac,
		}, 12},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			classfile := verifyM4aRewriteCode(t, original, tc.name, "()I", tc.code)
			verifyM4aAssertValue(t, func() (Result, error) {
				return Run(classfile, tc.name, nil, verifyM4aGasLimit)
			}, tc.want)
		})
	}
}

func TestVerifyM4aTypedLocalsArrayOperationsAndReferenceBranches(t *testing.T) {
	original := verifyM4aCompileStackFixture(t, []string{
		"intAsRef", "refAsInt", "badAstore", "badLoad", "badStore", "badIfNull", "badIfCmp", "badNumeric",
	})
	tests := []struct {
		name string
		code []byte
		pc   uint64
	}{
		{"intAsRef", []byte{0x03, 0x3b, 0x2a, 0xbe, 0xac}, 2},
		{"refAsInt", []byte{0x04, 0xbc, 10, 0x4b, 0x1a, 0xac}, 4},
		{"badAstore", []byte{0x03, 0x4b, 0x03, 0xac}, 1},
		{"badLoad", []byte{0x03, 0x03, 0x2e, 0xac}, 2},
		{"badStore", []byte{0x04, 0xbc, 10, 0x03, 0x01, 0x4f, 0x03, 0xac}, 5},
		{"badIfNull", []byte{0x03, 0xc6, 0, 3, 0x03, 0xac}, 1},
		{"badIfCmp", []byte{0x01, 0x03, 0xa5, 0, 3, 0x03, 0xac}, 2},
		{"badNumeric", []byte{0x01, 0x74, 0xac}, 1},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			classfile := verifyM4aRewriteCode(t, original, tc.name, "()I", tc.code)
			verifyM4aAssertError(t, func() (Result, error) {
				return Run(classfile, tc.name, nil, verifyM4aGasLimit)
			}, "BytecodeError(uint256,uint256)", 14, tc.pc)
		})
	}
	// A raw int must fail its kind check before any heap lookup. Consequently all
	// nonnull refs in reachable well-typed bytecode remain allocation-derived;
	// ReferenceError(1) is defensive and cannot be reached without bypassing these
	// checks. This checks the boundary without adding a production handle-forging API.
}

func TestVerifyM4aCallReturnAndStaticFieldKindChecks(t *testing.T) {
	original := compileJava(t, "ArrayKinds", `public final class ArrayKinds {
        static int[] field;
        static int helperRef(int[] a) { return a.length; }
        static int helperInt(int x) { return x; }
        static int[] give() { return new int[1]; }
        static int giveInt() { return 1; }
        public static int callRef() { return helperRef(new int[1]); }
        public static int callInt() { return helperInt(1); }
        public static int returnRef() { return give().length; }
        public static int returnInt() { return giveInt(); }
        public static int putField() { field = new int[1]; return 1; }
        public static int getField() { return field == null ? 1 : field.length; }
    }`)

	t.Run("call-ref-gets-int", func(t *testing.T) {
		classfile := mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
			m := c.method(t, "callRef", "()I")
			pc := verifyM4aOpcodePC(t, m.code, 0xbc, 0)
			m.code[pc], m.code[pc+1] = 0x00, 0x00
		})
		_, callPC := parseCallValidationClass(t, classfile).callRef(t, "callRef")
		verifyM4aAssertError(t, func() (Result, error) {
			return Run(classfile, "callRef", nil, verifyM4aGasLimit)
		}, "BytecodeError(uint256,uint256)", 14, uint64(callPC))
	})
	t.Run("call-int-gets-ref", func(t *testing.T) {
		classfile := mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
			m := c.method(t, "callInt", "()I")
			pc := verifyM4aOpcodePC(t, m.code, 0x04, 0)
			m.code[pc] = 0x01
		})
		_, callPC := parseCallValidationClass(t, classfile).callRef(t, "callInt")
		verifyM4aAssertError(t, func() (Result, error) {
			return Run(classfile, "callInt", nil, verifyM4aGasLimit)
		}, "BytecodeError(uint256,uint256)", 14, uint64(callPC))
	})
	t.Run("areturn-value-kind", func(t *testing.T) {
		var returnPC int
		classfile := mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
			m := c.method(t, "give", "()[I")
			pc := verifyM4aOpcodePC(t, m.code, 0xbc, 0)
			m.code[pc], m.code[pc+1] = 0x00, 0x00
			returnPC = verifyM4aOpcodePC(t, m.code, 0xb0, 0)
		})
		verifyM4aAssertError(t, func() (Result, error) {
			return Run(classfile, "returnRef", nil, verifyM4aGasLimit)
		}, "BytecodeError(uint256,uint256)", 14, uint64(returnPC))
	})
	t.Run("ireturn-value-kind", func(t *testing.T) {
		var returnPC int
		classfile := mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
			m := c.method(t, "giveInt", "()I")
			m.code[verifyM4aOpcodePC(t, m.code, 0x04, 0)] = 0x01
			returnPC = verifyM4aOpcodePC(t, m.code, 0xac, 0)
		})
		verifyM4aAssertError(t, func() (Result, error) {
			return Run(classfile, "returnInt", nil, verifyM4aGasLimit)
		}, "BytecodeError(uint256,uint256)", 14, uint64(returnPC))
	})
	t.Run("return-opcode-descriptor", func(t *testing.T) {
		var returnPC int
		classfile := mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
			m := c.method(t, "give", "()[I")
			returnPC = verifyM4aOpcodePC(t, m.code, 0xb0, 0)
			m.code[returnPC] = 0xac
		})
		verifyM4aAssertError(t, func() (Result, error) {
			return Run(classfile, "returnRef", nil, verifyM4aGasLimit)
		}, "CallError(uint256,uint256)", 5, uint64(returnPC))
	})
	t.Run("putstatic-value-kind", func(t *testing.T) {
		classfile := mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
			m := c.method(t, "putField", "()I")
			pc := verifyM4aOpcodePC(t, m.code, 0xbc, 0)
			m.code[pc], m.code[pc+1] = 0x00, 0x00
		})
		_, putPC := parseStaticsClass(t, classfile).fieldInstruction(t, "putField", opPutstatic, 0)
		verifyM4aAssertError(t, func() (Result, error) {
			return Run(classfile, "putField", nil, verifyM4aGasLimit)
		}, "BytecodeError(uint256,uint256)", 14, uint64(putPC))
	})
	t.Run("getstatic-value-kind", func(t *testing.T) {
		classfile := mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
			m := c.method(t, "getField", "()I")
			pc := verifyM4aOpcodePC(t, m.code, 0xc7, 0)
			m.code[pc] = 0x99 // ifeq requires int but keeps the same two-byte branch operand.
		})
		_, getPC := parseStaticsClass(t, classfile).fieldInstruction(t, "getField", opGetstatic, 0)
		verifyM4aAssertError(t, func() (Result, error) {
			return Run(classfile, "getField", nil, verifyM4aGasLimit)
		}, "BytecodeError(uint256,uint256)", 14, uint64(getPC+3))
	})
}

func TestVerifyM4aArrayAtypeTruncationAndNewBranchTargets(t *testing.T) {
	original := verifyM4aCompileStackFixture(t, []string{
		"atype", "truncatedArray", "truncatedIfNull", "ifNullTarget", "ifCmpTarget",
	})
	t.Run("unsupported-atype", func(t *testing.T) {
		code := []byte{0x04, 0xbc, 4, 0xbe, 0xac}
		classfile := verifyM4aRewriteCode(t, original, "atype", "()I", code)
		verifyM4aAssertError(t, func() (Result, error) {
			return Run(classfile, "atype", nil, verifyM4aGasLimit)
		}, "ArrayError(uint256,uint256)", 1, 1)
	})
	t.Run("truncated-newarray", func(t *testing.T) {
		classfile := verifyM4aRewriteAtEnd(t, original, "truncatedArray", 0xbc)
		pc := uint64(len(parseStaticsClass(t, classfile).method(t, "truncatedArray", "()I").code) - 1)
		verifyM4aAssertError(t, func() (Result, error) {
			return Run(classfile, "truncatedArray", nil, verifyM4aGasLimit)
		}, "BytecodeError(uint256,uint256)", 2, pc)
	})
	t.Run("truncated-ifnull", func(t *testing.T) {
		classfile := verifyM4aRewriteAtEnd(t, original, "truncatedIfNull", 0xc6)
		pc := uint64(len(parseStaticsClass(t, classfile).method(t, "truncatedIfNull", "()I").code) - 1)
		verifyM4aAssertError(t, func() (Result, error) {
			return Run(classfile, "truncatedIfNull", nil, verifyM4aGasLimit)
		}, "BytecodeError(uint256,uint256)", 2, pc)
	})
	t.Run("ifnull-targets-newarray-operand", func(t *testing.T) {
		code := []byte{0x01, 0xc6, 0, 5, 0x04, 0xbc, 10, 0x57, 0x03, 0xac}
		classfile := verifyM4aRewriteCode(t, original, "ifNullTarget", "()I", code)
		verifyM4aAssertError(t, func() (Result, error) {
			return Run(classfile, "ifNullTarget", nil, verifyM4aGasLimit)
		}, "BytecodeError(uint256,uint256)", 12, 1)
	})
	t.Run("if-acmpeq-targets-newarray-operand", func(t *testing.T) {
		code := []byte{0x01, 0x01, 0xa5, 0, 5, 0x04, 0xbc, 10, 0x57, 0x03, 0xac}
		classfile := verifyM4aRewriteCode(t, original, "ifCmpTarget", "()I", code)
		verifyM4aAssertError(t, func() (Result, error) {
			return Run(classfile, "ifCmpTarget", nil, verifyM4aGasLimit)
		}, "BytecodeError(uint256,uint256)", 12, 2)
	})
}

func verifyM4aAssertValue(t *testing.T, run func() (Result, error), want int32) {
	t.Helper()
	result, err := run()
	if err != nil {
		t.Fatalf("EVM execution failed: %v (result=%+v)", err, result)
	}
	if result.ExceptionClass != "" || result.Value != want || result.GasUsed == 0 || len(result.RevertData) != 0 {
		t.Fatalf("result = %+v, want value %d with measured execution", result, want)
	}
}

func verifyM4aAssertException(t *testing.T, run func() (Result, error), want string, kind byte) {
	t.Helper()
	result, err := run()
	if err != nil {
		t.Fatalf("Java outcome returned EVM failure: %v (result=%+v)", err, result)
	}
	if result.ExceptionClass != want || result.GasUsed == 0 || len(result.RevertData) != 36 {
		t.Fatalf("result = %+v, want exact Java outcome %s", result, want)
	}
	selector := crypto.Keccak256([]byte("JavaException(uint256)"))[:4]
	if !bytes.Equal(result.RevertData[:4], selector) ||
		!bytes.Equal(result.RevertData[4:35], make([]byte, 31)) || result.RevertData[35] != kind {
		t.Fatalf("Java outcome payload = %x, want exact kind %d", result.RevertData, kind)
	}
}

func verifyM4aAssertError(t *testing.T, run func() (Result, error), signature string, code, pc uint64) {
	t.Helper()
	result, err := run()
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error = %+v/%v, want exact %s revert", result, err, signature)
	}
	selector := crypto.Keccak256([]byte(signature))[:4]
	if result.ExceptionClass != "" || result.GasUsed == 0 || len(result.RevertData) != 68 || !bytes.Equal(result.RevertData[:4], selector) {
		t.Fatalf("result = %+v, want exact %s payload", result, signature)
	}
	if got := verifyM4aUint256(t, result.RevertData[4:36]); got != code {
		t.Fatalf("%s code = %d, want %d (data=%x)", signature, got, code, result.RevertData)
	}
	if got := verifyM4aUint256(t, result.RevertData[36:68]); got != pc {
		t.Fatalf("%s pc = %d, want %d (data=%x)", signature, got, pc, result.RevertData)
	}
}

func verifyM4aAssertMethodError(t *testing.T, result Result, err error, code uint64) {
	t.Helper()
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error = %+v/%v, want exact MethodError revert", result, err)
	}
	selector := crypto.Keccak256([]byte("MethodError(uint256)"))[:4]
	if result.ExceptionClass != "" || result.GasUsed == 0 || len(result.RevertData) != 36 || !bytes.Equal(result.RevertData[:4], selector) {
		t.Fatalf("result = %+v, want exact MethodError payload", result)
	}
	if got := verifyM4aUint256(t, result.RevertData[4:]); got != code {
		t.Fatalf("MethodError code = %d, want %d (data=%x)", got, code, result.RevertData)
	}
}

func verifyM4aUint256(t *testing.T, word []byte) uint64 {
	t.Helper()
	if len(word) != 32 || !bytes.Equal(word[:24], make([]byte, 24)) {
		t.Fatalf("noncanonical or oversized uint256 word: %x", word)
	}
	return binary.BigEndian.Uint64(word[24:])
}

func verifyM4aOpcodePC(t *testing.T, code []byte, opcode byte, occurrence int) int {
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
	t.Fatalf("opcode 0x%02x occurrence %d missing from %x", opcode, occurrence, code)
	return -1
}

func verifyM4aCompileStackFixture(t *testing.T, names []string) []byte {
	t.Helper()
	var source strings.Builder
	source.WriteString("public final class M4aStackFixture {\n")
	for _, name := range names {
		fmt.Fprintf(&source, "public static int %s() { int x=0;", name)
		for i := 1; i <= 28; i++ {
			fmt.Fprintf(&source, "x=x+%d;", i)
		}
		source.WriteString("return x;}\n")
	}
	source.WriteString("}\n")
	return compileJava(t, "M4aStackFixture", source.String())
}

func verifyM4aRewriteCode(t *testing.T, original []byte, name, descriptor string, code []byte) []byte {
	t.Helper()
	out := append([]byte(nil), original...)
	parsed := parseStaticsClass(t, out)
	method := parsed.method(t, name, descriptor)
	if len(code) > len(method.code) {
		t.Fatalf("replacement for %s is %d bytes, Code has %d", name, len(code), len(method.code))
	}
	start := -1
	for i := range out {
		if len(method.code) > 0 && &out[i] == &method.code[0] {
			start = i
			break
		}
	}
	if start < 8 {
		t.Fatalf("cannot locate Code bytes for %s", name)
	}
	binary.BigEndian.PutUint16(out[start-8:], 16) // max_stack
	binary.BigEndian.PutUint16(out[start-6:], 16) // max_locals
	for i := range method.code {
		method.code[i] = 0x00 // supported nop; unreachable padding follows the return
	}
	copy(method.code, code)
	return out
}

func verifyM4aRewriteAtEnd(t *testing.T, original []byte, name string, opcode byte) []byte {
	t.Helper()
	out := verifyM4aRewriteCode(t, original, name, "()I", nil)
	method := parseStaticsClass(t, out).method(t, name, "()I")
	method.code[len(method.code)-1] = opcode
	return out
}
