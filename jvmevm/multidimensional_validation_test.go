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
	verifyM4eGasLimit         = uint64(100_000_000)
	verifyM4eCapacityGasLimit = uint64(250_000_000)
	verifyM4eMultianewarray   = byte(0xc5)
)

// Every class below is trusted, locally compiled Java 8 test input. Controlled
// mutations make classfile shapes javac cannot express; production execution
// still receives only unchanged byte slices and has no host parser/heap hook.

func TestVerifyM4eRectangularPartialDefaultsIdentityAndTransport(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"multibasic/Base.java":  `package multibasic; public class Base { int value; Base(){value=3;} }`,
		"multibasic/Child.java": `package multibasic; public final class Child extends Base { Child(){value=7;} }`,
		"multibasic/Holder.java": `package multibasic; public final class Holder {
			int[][] instance; static Child[][] shared;
			static int[][] pass(int[][] value){return value;}
			int virtualLength(int[][] value){return value.length;}
		}`,
		"multibasic/Root.java": `package multibasic; public final class Root {
			public static int ints(){int[][] a=new int[2][3];a[0][2]=7;
				if(a[0][2]!=7||a[1][2]!=0)return -1;
				return a.length*100+a[0].length*10+a[1][2]+(a[0]!=a[1]?1:0);}
			public static int refs(){Child[][] a=new Child[2][3];
				return a.length*100+a[0].length*10+(a[0][0]==null?4:0)+(a[0]!=a[1]?1:0);}
			public static int partial(){int[][][] a=new int[2][3][];
				return a.length*100+a[0].length*10+(a[0][0]==null?4:0)+(a[0]!=a[1]?1:0);}
			public static int zeroInner(){int[][][] a=new int[2][0][5];
				return a.length*100+a[0].length*10+(a[0]!=a[1]?1:0);}
			public static int transport(){int[][] a=new int[2][3];Holder h=new Holder();
				h.instance=Holder.pass(a);Child[][] c=new Child[1][2];Holder.shared=c;
				return h.virtualLength(h.instance)*100+(h.instance==a?10:0)+(Holder.shared==c?1:0);}
			public static int covariance(){Child[][] c=new Child[1][2];Base[][] b=c;Object[] o=c;
				return (b==c?1:0)+(o==c?2:0)+(c instanceof Base[][]?4:0)
					+(c instanceof Object[]?8:0)+(((Object)c) instanceof Object[][]?16:0);}
			public static int compatibleStore(){Base[][] b=new Child[1][1];b[0][0]=new Child();return b[0][0].value;}
			public static int badOuterStore(){Object[][] a=new Child[1][1];a[0]=new Object[1];return 1;}
			public static int badLeafStore(){Base[][] b=new Child[1][1];b[0][0]=new Base();return 1;}
		}`,
	}, "multibasic/Base", "multibasic/Child", "multibasic/Holder", "multibasic/Root")
	root := classes["multibasic/Root"]
	for _, method := range []string{"ints", "refs", "partial", "zeroInner", "transport", "covariance", "compatibleStore", "badOuterStore", "badLeafStore"} {
		pc, descriptor, dimensions := verifyM4eSite(t, root, method)
		if pc < 0 || !strings.HasPrefix(descriptor, "[[") || dimensions < 2 {
			t.Fatalf("%s site=(%d,%q,%d), want a genuine multidimensional instruction", method, pc, descriptor, dimensions)
		}
	}
	bundle := verifyM4eBundle(classes)
	// ints explicitly guards the written and untouched rows; its value is
	// 2*100 + 3*10 + 0 + 1 = 231 on a Java 8 JVM.
	for _, tc := range []struct {
		method string
		want   int32
	}{{"ints", 231}, {"refs", 235}, {"partial", 235}, {"zeroInner", 201}, {"transport", 211}, {"covariance", 31}, {"compatibleStore", 7}} {
		t.Run(tc.method, func(t *testing.T) {
			verifyM4eAssertValue(t, func() (Result, error) {
				return RunClasses(bundle, "multibasic/Root", tc.method, nil, verifyM4eGasLimit)
			}, tc.want)
		})
	}
	for _, method := range []string{"badOuterStore", "badLeafStore"} {
		t.Run(method, func(t *testing.T) {
			verifyM4eAssertException(t, func() (Result, error) {
				return RunClasses(bundle, "multibasic/Root", method, nil, verifyM4eGasLimit)
			}, "java.lang.ArrayStoreException", 9)
		})
	}
	// A fresh VM invocation resets static and heap identity state.
	verifyM4eAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "multibasic/Root", "transport", nil, verifyM4eGasLimit)
	}, 211)
}

func TestVerifyM4eComponentResolutionNoInitializationConstructorsOrInstantiability(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"multilazy/AbstractPart.java": `package multilazy; public abstract class AbstractPart { }`,
		"multilazy/Lazy.java": `package multilazy; public class Lazy {
			static int starts=1/zero(); static int zero(){return 0;}
			public Lazy(){int impossible=1/zero();}
		}`,
		"multilazy/Root.java": `package multilazy; public final class Root {
			public static int lazy(){Lazy[][] a=new Lazy[2][3];return a.length*10+a[0].length+(a[1][2]==null?1:0);}
			public static int abstractValid(){AbstractPart[][] a=new AbstractPart[1][2];return a.length*10+a[0].length+(a[0][0]==null?1:0);}
		}`,
	}, "multilazy/AbstractPart", "multilazy/Lazy", "multilazy/Root")
	bundle := verifyM4eBundle(classes)
	verifyM4eAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "multilazy/Root", "lazy", nil, verifyM4eGasLimit)
	}, 24)
	verifyM4eAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "multilazy/Root", "abstractValid", nil, verifyM4eGasLimit)
	}, 13)
}

func TestVerifyM4eCountOrderPrefixConsumptionAndDimensionOne(t *testing.T) {
	original := verifyM4eCompilePadding(t)
	arrayIndex := verifyM4eAppendTargetIndex(t, &original, "[[I")

	prefix := []byte{0x10, 40, 0x05, 0x06, verifyM4eMultianewarray, byte(arrayIndex >> 8), byte(arrayIndex), 2, 0x57, 0xac}
	classfile := verifyM4eRewriteCode(t, original, "padding", "()I", prefix, 16, 16)
	verifyM4eAssertProgram(t, classfile, "padding", prefix)
	verifyM4eAssertValue(t, func() (Result, error) {
		return Run(classfile, "padding", nil, verifyM4eGasLimit)
	}, 40)

	// javac normally selects newarray for rank one. This controlled instruction
	// proves dimensions=1 is accepted and consumes exactly one count.
	rankOne := []byte{0x10, 41, 0x06, verifyM4eMultianewarray, byte(arrayIndex >> 8), byte(arrayIndex), 1, 0xbe, 0x60, 0xac}
	rankOneClass := verifyM4eRetargetName(t, verifyM4eRewriteCode(t, original, "padding", "()I", rankOne, 16, 16), "padding", "[I")
	verifyM4eAssertValue(t, func() (Result, error) {
		return Run(rankOneClass, "padding", nil, verifyM4eGasLimit)
	}, 44)

	compiled := compileJava(t, "MultiCountOrder", `public final class MultiCountOrder {
		public static int run(int outer,int inner){int[][] a=new int[outer][inner];return a.length*100+a[0].length;}
	}`)
	verifyM4eAssertValue(t, func() (Result, error) {
		return Run(compiled, "run", []int32{2, 3}, verifyM4eGasLimit)
	}, 203)
}

func TestVerifyM4eAllNegativeCountsPrecedeCapsAndZeroMaterialization(t *testing.T) {
	classfile := compileJava(t, "MultiCounts", `public final class MultiCounts {
		public static int run(int outer,int inner){return new int[outer][inner].length;}
	}`)
	for _, args := range [][]int32{{-1, 65537}, {65537, -1}, {0, -1}, {1, -2147483648}} {
		t.Run(fmt.Sprint(args), func(t *testing.T) {
			verifyM4eAssertException(t, func() (Result, error) {
				return Run(classfile, "run", args, verifyM4eGasLimit)
			}, "java.lang.NegativeArraySizeException", 4)
		})
	}
	for _, inner := range []int32{65537, 1_000_000_000, 2147483647} {
		t.Run(fmt.Sprintf("zero-%d", inner), func(t *testing.T) {
			verifyM4eAssertValue(t, func() (Result, error) {
				return Run(classfile, "run", []int32{0, inner}, verifyM4eGasLimit)
			}, 0)
		})
	}
	verifyM4eAssertException(t, func() (Result, error) {
		return Run(classfile, "run", []int32{1, 65537}, verifyM4eGasLimit)
	}, "java.lang.OutOfMemoryError", 7)
}

func TestVerifyM4eStructuralCPDescriptorDimensionsAndTruncation(t *testing.T) {
	original := compileJava(t, "MultiStructure", `public final class MultiStructure {
		public static int run(){return new int[1][2].length;}
		public static int padding(){int x=0;`+strings.Repeat("x=x+1;", 40)+`return x;}
	}`)
	pc, _, _ := verifyM4eSite(t, original, "run")
	for _, tc := range []struct {
		name string
		make func() []byte
	}{
		{"cp-zero", func() []byte {
			return verifyM4eMutate(t, original, func(_ []byte, c staticsClass) { binary.BigEndian.PutUint16(c.namedMethod(t, "run").code[pc+1:], 0) })
		}},
		{"cp-range", func() []byte {
			return verifyM4eMutate(t, original, func(_ []byte, c staticsClass) {
				binary.BigEndian.PutUint16(c.namedMethod(t, "run").code[pc+1:], uint16(c.cpCount))
			})
		}},
		{"cp-wrong-tag", func() []byte {
			out, index := verifyM4eAppendClassExistingName(t, original, "[[I")
			return verifyM4eMutate(t, out, func(raw []byte, c staticsClass) {
				binary.BigEndian.PutUint16(c.namedMethod(t, "run").code[pc+1:], index)
				raw[c.entry(t, index).offset] = 8
			})
		}},
		{"cp-zero-name", func() []byte {
			out, index := verifyM4eAppendClassExistingName(t, original, "[[I")
			return verifyM4eMutate(t, out, func(raw []byte, c staticsClass) {
				binary.BigEndian.PutUint16(c.namedMethod(t, "run").code[pc+1:], index)
				binary.BigEndian.PutUint16(raw[c.entry(t, index).offset+1:], 0)
			})
		}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			verifyM4eAssertError(t, func() (Result, error) { return Run(tc.make(), "run", nil, verifyM4eGasLimit) }, "TypeError(uint256,uint256)", 1, uint64(pc))
		})
	}
	for _, name := range []string{"[Qbad", "bad.Name", strings.Repeat("[", 256) + "I"} {
		t.Run("malformed-"+fmt.Sprint(len(name)), func(t *testing.T) {
			bad := verifyM4eRetargetName(t, original, "run", name)
			verifyM4eAssertError(t, func() (Result, error) { return Run(bad, "run", nil, verifyM4eGasLimit) }, "TypeError(uint256,uint256)", 1, uint64(pc))
		})
	}
	for _, tc := range []struct {
		name       string
		target     string
		dimensions byte
	}{
		{"non-array", "MultiStructure", 1}, {"dimensions-zero", "[[I", 0}, {"dimensions-excess", "[[I", 3},
	} {
		t.Run(tc.name, func(t *testing.T) {
			bad := verifyM4eRetargetName(t, original, "run", tc.target)
			bad = verifyM4eMutate(t, bad, func(_ []byte, c staticsClass) { c.namedMethod(t, "run").code[pc+3] = tc.dimensions })
			verifyM4eAssertError(t, func() (Result, error) { return Run(bad, "run", nil, verifyM4eGasLimit) }, "ArrayError(uint256,uint256)", 3, uint64(pc))
		})
	}
	// Other primitive leaves are well-formed array descriptors but deferred.
	deferred := verifyM4eRetargetName(t, original, "run", "[[J")
	verifyM4eAssertError(t, func() (Result, error) { return Run(deferred, "run", nil, verifyM4eGasLimit) }, "TypeError(uint256,uint256)", 2, uint64(pc))

	for operands := 0; operands <= 2; operands++ {
		t.Run(fmt.Sprintf("truncated-%d-operands", operands), func(t *testing.T) {
			code := append([]byte{verifyM4eMultianewarray}, make([]byte, operands)...)
			bad := verifyM4eRewriteAtEnd(t, original, "padding", "()I", code)
			truncatedPC := len(parseStaticsClass(t, bad).namedMethod(t, "padding").code) - len(code)
			verifyM4eAssertError(t, func() (Result, error) { return Run(bad, "padding", nil, verifyM4eGasLimit) }, "BytecodeError(uint256,uint256)", 2, uint64(truncatedPC))
		})
	}
}

func TestVerifyM4eBranchTargetsRejectEachOperandByteUsingInstructionBoundaries(t *testing.T) {
	// The first 0xc5 below is an ldc_w operand, not an instruction. This guards
	// the PC derivation used throughout this verifier against raw-byte scanning.
	boundaryProbe := []byte{0x13, 0x00, 0xc5, verifyM4eMultianewarray, 0, 1, 1, 0x57}
	if pc := verifyM4eInstructionPC(t, boundaryProbe, verifyM4eMultianewarray, 0); pc != 3 {
		t.Fatalf("boundary-aware multianewarray pc=%d, want 3", pc)
	}
	if pc := verifyM4eInstructionPC(t, boundaryProbe, 0x57, 0); pc != 7 {
		t.Fatalf("multianewarray width is not four: following pop pc=%d, want 7", pc)
	}
	original := verifyM4eCompilePadding(t)
	arrayIndex := verifyM4eAppendTargetIndex(t, &original, "[[I")
	for operand := 1; operand <= 3; operand++ {
		t.Run(fmt.Sprintf("operand-%d", operand), func(t *testing.T) {
			// ifeq is at pc 1 and its signed offset is relative to that pc.
			multiPC := 5
			target := multiPC + operand
			offset := target - 1
			code := []byte{0x03, 0x99, byte(offset >> 8), byte(offset), 0x04, verifyM4eMultianewarray, byte(arrayIndex >> 8), byte(arrayIndex), 2, 0x57, 0x03, 0xac}
			bad := verifyM4eRewriteCode(t, original, "padding", "()I", code, 16, 16)
			if got := verifyM4eInstructionPC(t, code, verifyM4eMultianewarray, 0); got != multiPC {
				t.Fatalf("multianewarray pc=%d want %d", got, multiPC)
			}
			verifyM4eAssertError(t, func() (Result, error) { return Run(bad, "padding", nil, verifyM4eGasLimit) }, "BytecodeError(uint256,uint256)", 12, 1)
		})
	}
}

func TestVerifyM4eResolutionAndAccessPrecedeAllCountChecks(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"multiresolve/Component.java": `package multiresolve; public class Component { }`,
		"multiresolve/I.java":         `package multiresolve; public interface I { }`,
		"multiuser/Root.java": `package multiuser; public final class Root {
			public static int component(int a,int b){return new multiresolve.Component[a][b].length;}
			public static int iface(int a,int b){return new multiresolve.I[a][b].length;}
		}`,
	}, "multiresolve/Component", "multiresolve/I", "multiuser/Root")
	root := classes["multiuser/Root"]
	componentPC, descriptor, _ := verifyM4eSite(t, root, "component")
	if descriptor != "[[Lmultiresolve/Component;" {
		t.Fatalf("component descriptor=%q", descriptor)
	}
	// Component is genuinely absent: only Root is supplied, with no inner-class substitute.
	for _, args := range [][]int32{{0, 0}, {-1, 0}, {0, -1}, {65537, -1}} {
		verifyM4eAssertError(t, func() (Result, error) {
			return RunClasses([][]byte{root}, "multiuser/Root", "component", args, verifyM4eGasLimit)
		}, "LinkError(uint256,uint256)", 4, uint64(componentPC))
	}
	inaccessible := verifyM4eMutate(t, classes["multiresolve/Component"], func(raw []byte, c staticsClass) {
		flags := binary.BigEndian.Uint16(raw[c.cpEnd:])
		binary.BigEndian.PutUint16(raw[c.cpEnd:], flags&^accPublic)
	})
	for _, args := range [][]int32{{0, -1}, {65537, -1}} {
		verifyM4eAssertError(t, func() (Result, error) {
			return RunClasses([][]byte{inaccessible, root}, "multiuser/Root", "component", args, verifyM4eGasLimit)
		}, "TypeError(uint256,uint256)", 2, uint64(componentPC))
	}
	ifacePC, _, _ := verifyM4eSite(t, root, "iface")
	verifyM4eAssertError(t, func() (Result, error) {
		return RunClasses(verifyM4eBundle(classes), "multiuser/Root", "iface", []int32{0, -1}, verifyM4eGasLimit)
	}, "TypeError(uint256,uint256)", 2, uint64(ifacePC))
}

func TestVerifyM4eStackUnderflowAndCountKindsBeforeHeapChecks(t *testing.T) {
	original := verifyM4eCompilePadding(t)
	arrayIndex := verifyM4eAppendTargetIndex(t, &original, "[[I")
	classIndex := verifyM4eClassIndex(t, parseStaticsClass(t, original), "M4ePadding")
	for _, tc := range []struct {
		name string
		code []byte
		kind uint64
	}{
		{"empty", []byte{verifyM4eMultianewarray, byte(arrayIndex >> 8), byte(arrayIndex), 2, 0x03, 0xac}, 3},
		{"one-count", []byte{0x04, verifyM4eMultianewarray, byte(arrayIndex >> 8), byte(arrayIndex), 2, 0x03, 0xac}, 3},
		{"null-as-inner", []byte{0x04, 0x01, verifyM4eMultianewarray, byte(arrayIndex >> 8), byte(arrayIndex), 2, 0x03, 0xac}, 14},
		{"ref-as-inner", []byte{0x04, 0x03, 0xbc, 10, verifyM4eMultianewarray, byte(arrayIndex >> 8), byte(arrayIndex), 2, 0x03, 0xac}, 14},
		{"ref-as-outer", []byte{0x03, 0xbc, 10, 0x04, verifyM4eMultianewarray, byte(arrayIndex >> 8), byte(arrayIndex), 2, 0x03, 0xac}, 14},
		{"uninitialized-as-outer", []byte{0xbb, byte(classIndex >> 8), byte(classIndex), 0x04, verifyM4eMultianewarray, byte(arrayIndex >> 8), byte(arrayIndex), 2, 0x03, 0xac}, 14},
	} {
		t.Run(tc.name, func(t *testing.T) {
			bad := verifyM4eRewriteCode(t, original, "padding", "()I", tc.code, 16, 16)
			verifyM4eAssertProgram(t, bad, "padding", tc.code)
			faultPC := verifyM4eInstructionPC(t, tc.code, verifyM4eMultianewarray, 0)
			verifyM4eAssertError(t, func() (Result, error) { return Run(bad, "padding", nil, verifyM4eGasLimit) }, "BytecodeError(uint256,uint256)", tc.kind, uint64(faultPC))
		})
	}
}

func TestVerifyM4eRank255FullAndPartialStayBounded(t *testing.T) {
	original := verifyM4eCompileLargePadding(t)
	descriptor := strings.Repeat("[", 255) + "I"
	arrayIndex := verifyM4eAppendTargetIndex(t, &original, descriptor)
	full := make([]byte, 0, 800)
	for i := 0; i < 255; i++ {
		full = append(full, 0x04)
	}
	full = append(full, verifyM4eMultianewarray, byte(arrayIndex>>8), byte(arrayIndex), 255)
	// Walk all 255 allocated rank nodes. This checks more than successful
	// planning: each intermediate value must be the correctly typed ref array.
	for i := 0; i < 254; i++ {
		full = append(full, 0x03, 0x32) // iconst_0; aaload
	}
	full = append(full, 0xbe, 0xac) // final int[].length
	fullClass := verifyM4eRewriteCode(t, original, "padding", "()I", full, 300, 16)
	verifyM4eAssertValue(t, func() (Result, error) { return Run(fullClass, "padding", nil, verifyM4eCapacityGasLimit) }, 1)

	partial := []byte{0x04, verifyM4eMultianewarray, byte(arrayIndex >> 8), byte(arrayIndex), 1, 0xbe, 0xac}
	partialClass := verifyM4eRewriteCode(t, original, "padding", "()I", partial, 16, 16)
	verifyM4eAssertValue(t, func() (Result, error) { return Run(partialClass, "padding", nil, verifyM4eGasLimit) }, 1)
}

func TestVerifyM4eSharedArrayAndElementQuotasNoGCResetAndObjectIndependence(t *testing.T) {
	classfile := compileJava(t, "MultiCaps", `public final class MultiCaps {
		public MultiCaps(){}
		public static int rectangular(int outer){int[][] a=new int[outer][0];return a.length;}
		public static int perArray(int inner){return new int[1][inner].length;}
		public static int aggregate(){int[][] a=new int[3][65536];return a.length+a[2].length;}
		public static int aggregateOver(){return new int[4][65536].length;}
		public static int priorArrays(int count){Object waste=null;for(int i=0;i<count;i++)
			waste=(i&1)==0?(Object)new int[0]:(Object)new MultiCaps[0];
			int[][] a=new int[0][0];return count+a.length+(waste==null?0:0);}
		public static int exactElements(){Object waste=null;for(int i=0;i<4;i++)waste=new int[65536];
			int[][] a=new int[0][0];return 262144+a.length+(waste==null?0:0);}
		public static int overElements(){Object waste=null;for(int i=0;i<4;i++)waste=new int[65536];
			int[][] a=new int[1][0];return a.length+(waste==null?0:0);}
		public static int arraysAndObjects(){Object waste=null;for(int i=0;i<1023;i++)waste=new int[0];
			int[][] a=new int[0][0];for(int i=0;i<1024;i++)waste=new MultiCaps();
			return (a==null?0:1)+(waste==null?0:1);}
	}`)
	verifyM4eAssertValue(t, func() (Result, error) { return Run(classfile, "rectangular", []int32{1023}, verifyM4eCapacityGasLimit) }, 1023)
	verifyM4eAssertException(t, func() (Result, error) { return Run(classfile, "rectangular", []int32{1024}, verifyM4eCapacityGasLimit) }, "java.lang.OutOfMemoryError", 7)
	verifyM4eAssertValue(t, func() (Result, error) { return Run(classfile, "perArray", []int32{65536}, verifyM4eCapacityGasLimit) }, 1)
	verifyM4eAssertException(t, func() (Result, error) { return Run(classfile, "perArray", []int32{65537}, verifyM4eGasLimit) }, "java.lang.OutOfMemoryError", 7)
	verifyM4eAssertValue(t, func() (Result, error) { return Run(classfile, "aggregate", nil, verifyM4eCapacityGasLimit) }, 65539)
	verifyM4eAssertException(t, func() (Result, error) { return Run(classfile, "aggregateOver", nil, verifyM4eGasLimit) }, "java.lang.OutOfMemoryError", 7)
	verifyM4eAssertValue(t, func() (Result, error) { return Run(classfile, "priorArrays", []int32{1023}, verifyM4eCapacityGasLimit) }, 1023)
	verifyM4eAssertException(t, func() (Result, error) { return Run(classfile, "priorArrays", []int32{1024}, verifyM4eCapacityGasLimit) }, "java.lang.OutOfMemoryError", 7)
	verifyM4eAssertValue(t, func() (Result, error) { return Run(classfile, "exactElements", nil, verifyM4eCapacityGasLimit) }, 262144)
	verifyM4eAssertException(t, func() (Result, error) { return Run(classfile, "overElements", nil, verifyM4eCapacityGasLimit) }, "java.lang.OutOfMemoryError", 7)
	verifyM4eAssertValue(t, func() (Result, error) { return Run(classfile, "arraysAndObjects", nil, verifyM4eCapacityGasLimit) }, 2)
	// Unreachable prior allocations count within an invocation, but fresh runs reset.
	verifyM4eAssertValue(t, func() (Result, error) { return Run(classfile, "priorArrays", []int32{1023}, verifyM4eCapacityGasLimit) }, 1023)
}

func TestVerifyM4eNASEEIIEOOMAndEVMOOGRemainExact(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"multioutcome/Root.java": `package multioutcome; public final class Root {
			public static int negative(){return new int[1][-1].length;}
			public static int oom(){return new int[1][65537].length;}
		}`,
		"multioutcome/InitNegative.java": `package multioutcome; public final class InitNegative {
			static int[][] value=new int[1][-1];public static int run(){return value.length;}
		}`,
		"multioutcome/InitOOM.java": `package multioutcome; public final class InitOOM {
			static int[][] value=new int[1][65537];public static int run(){return value.length;}
		}`,
	}, "multioutcome/Root", "multioutcome/InitNegative", "multioutcome/InitOOM")
	bundle := verifyM4eBundle(classes)
	verifyM4eAssertException(t, func() (Result, error) {
		return RunClasses(bundle, "multioutcome/Root", "negative", nil, verifyM4eGasLimit)
	}, "java.lang.NegativeArraySizeException", 4)
	verifyM4eAssertException(t, func() (Result, error) {
		return RunClasses(bundle, "multioutcome/InitNegative", "run", nil, verifyM4eGasLimit)
	}, "java.lang.ExceptionInInitializerError", 3)
	verifyM4eAssertException(t, func() (Result, error) { return RunClasses(bundle, "multioutcome/Root", "oom", nil, verifyM4eGasLimit) }, "java.lang.OutOfMemoryError", 7)
	verifyM4eAssertException(t, func() (Result, error) {
		return RunClasses(bundle, "multioutcome/InitOOM", "run", nil, verifyM4eGasLimit)
	}, "java.lang.OutOfMemoryError", 7)
	result, err := RunClasses(bundle, "multioutcome/Root", "oom", nil, 1)
	if err == nil || !errors.Is(err, vm.ErrOutOfGas) || result.ExceptionClass != "" || len(result.RevertData) != 0 {
		t.Fatalf("result/error=%+v/%v, want unlabeled EVM out of gas", result, err)
	}
}

func TestVerifyM4ePostAllocationMissingMethodIsGenuinelyMissing(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"multimethod/Helper.java": `package multimethod; public final class Helper { static int missing(){return 7;} }`,
		"multimethod/Root.java": `package multimethod; public final class Root {
			public static int run(){int[][] a=new int[1][1];return Helper.missing()+a.length;}
		}`,
	}, "multimethod/Helper", "multimethod/Root")
	helper := verifyM4eMutate(t, classes["multimethod/Helper"], func(raw []byte, c staticsClass) {
		index := c.utfIndex(t, "missing")
		e := c.entry(t, index)
		copy(raw[e.offset+3:e.offset+10], []byte("absentz"))
	})
	for _, method := range parseStaticsClass(t, helper).methods {
		if method.name == "missing" {
			t.Fatalf("mutated Helper still declares missing%s", method.descriptor)
		}
	}
	root := classes["multimethod/Root"]
	parsed := parseStaticsClass(t, root)
	_, callPC := verifyM4eMemberInstruction(t, parsed, parsed.namedMethod(t, "run"), 0xb8, "missing", "()I")
	if multiPC := verifyM4eInstructionPC(t, parsed.namedMethod(t, "run").code, verifyM4eMultianewarray, 0); multiPC >= callPC {
		t.Fatalf("multianewarray pc=%d must execute before genuinely missing call pc=%d", multiPC, callPC)
	}
	verifyM4eAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{helper, root}, "multimethod/Root", "run", nil, verifyM4eGasLimit)
	}, "CallError(uint256,uint256)", 3, uint64(callPC))
}

func verifyM4eBundle(classes map[string][]byte) [][]byte {
	names := make([]string, 0, len(classes))
	for name := range classes {
		names = append(names, name)
	}
	for i := range names {
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

func verifyM4eSite(t *testing.T, classfile []byte, method string) (int, string, byte) {
	t.Helper()
	c := parseStaticsClass(t, classfile)
	code := c.namedMethod(t, method).code
	pc := verifyM4eInstructionPC(t, code, verifyM4eMultianewarray, 0)
	if pc+3 >= len(code) {
		t.Fatalf("truncated trusted multianewarray at pc %d", pc)
	}
	index := binary.BigEndian.Uint16(code[pc+1:])
	e := c.entry(t, index)
	if e.tag != 7 {
		t.Fatalf("multianewarray CP tag=%d, want Class", e.tag)
	}
	return pc, c.utf8[c.u2(t, e.offset+1)], code[pc+3]
}

// verifyM4eInstructionPC walks JVM instruction boundaries. It deliberately does
// not bytes.Index through operands, where 0xc5 may be arbitrary CP/branch data.
func verifyM4eInstructionPC(t *testing.T, code []byte, opcode byte, occurrence int) int {
	t.Helper()
	seen := 0
	for pc := 0; pc < len(code); {
		op := code[pc]
		if op == opcode {
			if seen == occurrence {
				return pc
			}
			seen++
		}
		width := verifyM4eInstructionWidth(t, code, pc)
		if width < 1 || pc+width > len(code) {
			t.Fatalf("invalid/truncated instruction 0x%02x at pc %d in %x", op, pc, code)
		}
		pc += width
	}
	t.Fatalf("opcode 0x%02x occurrence %d missing at instruction boundaries in %x", opcode, occurrence, code)
	return -1
}

func verifyM4eInstructionWidth(t *testing.T, code []byte, pc int) int {
	t.Helper()
	op := code[pc]
	switch op {
	case 0x10, 0x12, 0x15, 0x16, 0x17, 0x18, 0x19, 0x36, 0x37, 0x38, 0x39, 0x3a, 0xa9, 0xbc:
		return 2
	case 0x11, 0x13, 0x14, 0x84,
		0x99, 0x9a, 0x9b, 0x9c, 0x9d, 0x9e, 0x9f, 0xa0, 0xa1, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6, 0xa7, 0xa8,
		0xb2, 0xb3, 0xb4, 0xb5, 0xb6, 0xb7, 0xb8, 0xbb, 0xbd, 0xc0, 0xc1, 0xc6, 0xc7:
		return 3
	case 0xb9, 0xba, 0xc8, 0xc9:
		return 5
	case verifyM4eMultianewarray:
		return 4
	case 0xc4:
		if pc+1 >= len(code) {
			return len(code) - pc + 1
		}
		if code[pc+1] == 0x84 {
			return 6
		}
		return 4
	case 0xaa:
		pad := (4 - ((pc + 1) & 3)) & 3
		base := pc + 1 + pad
		if base+12 > len(code) {
			return len(code) - pc + 1
		}
		low := int32(binary.BigEndian.Uint32(code[base+4:]))
		high := int32(binary.BigEndian.Uint32(code[base+8:]))
		if high < low || int64(high)-int64(low) > int64(len(code)) {
			return len(code) - pc + 1
		}
		return 1 + pad + 12 + 4*int(int64(high)-int64(low)+1)
	case 0xab:
		pad := (4 - ((pc + 1) & 3)) & 3
		base := pc + 1 + pad
		if base+8 > len(code) {
			return len(code) - pc + 1
		}
		n := int32(binary.BigEndian.Uint32(code[base+4:]))
		if n < 0 || int64(n) > int64(len(code)) {
			return len(code) - pc + 1
		}
		return 1 + pad + 8 + 8*int(n)
	default:
		return 1
	}
}

func verifyM4eClassIndex(t *testing.T, c staticsClass, name string) uint16 {
	t.Helper()
	for i := 1; i < len(c.entries); i++ {
		e := c.entries[i]
		if e.tag == 7 && c.utf8[c.u2(t, e.offset+1)] == name {
			return uint16(i)
		}
	}
	t.Fatalf("Class constant %q missing", name)
	return 0
}

func verifyM4eMemberInstruction(t *testing.T, c staticsClass, m staticsMethod, opcode byte, name, descriptor string) (uint16, int) {
	t.Helper()
	for pc := 0; pc < len(m.code); pc += verifyM4eInstructionWidth(t, m.code, pc) {
		if m.code[pc] != opcode || pc+2 >= len(m.code) {
			continue
		}
		ref := binary.BigEndian.Uint16(m.code[pc+1:])
		if ref == 0 || int(ref) >= len(c.entries) || c.entries[ref].tag != 10 {
			continue
		}
		e := c.entry(t, ref)
		nat := c.entry(t, c.u2(t, e.offset+3))
		if nat.tag == 12 && c.utf8[c.u2(t, nat.offset+1)] == name && c.utf8[c.u2(t, nat.offset+3)] == descriptor {
			return ref, pc
		}
	}
	t.Fatalf("%s%s lacks boundary-aligned opcode 0x%02x for %s%s: %x", m.name, m.descriptor, opcode, name, descriptor, m.code)
	return 0, 0
}

func verifyM4eCompilePadding(t *testing.T) []byte {
	t.Helper()
	return compileJava(t, "M4ePadding", `public final class M4ePadding { public static int padding(){int x=0;`+strings.Repeat("x=x+1;", 80)+`return x;} }`)
}

func verifyM4eCompileLargePadding(t *testing.T) []byte {
	t.Helper()
	return compileJava(t, "M4eLargePadding", `public final class M4eLargePadding { public static int padding(){int x=0;`+strings.Repeat("x=x+1;", 400)+`return x;} }`)
}

func verifyM4eMutate(t *testing.T, original []byte, change func([]byte, staticsClass)) []byte {
	t.Helper()
	out := append([]byte(nil), original...)
	change(out, parseStaticsClass(t, out))
	return out
}

func verifyM4eAppendClassExistingName(t *testing.T, original []byte, name string) ([]byte, uint16) {
	t.Helper()
	c := parseStaticsClass(t, original)
	nameIndex := c.utfIndex(t, name)
	out := make([]byte, len(original)+3)
	copy(out, original[:c.cpEnd])
	out[c.cpEnd] = 7
	binary.BigEndian.PutUint16(out[c.cpEnd+1:], nameIndex)
	copy(out[c.cpEnd+3:], original[c.cpEnd:])
	binary.BigEndian.PutUint16(out[8:10], uint16(c.cpCount+1))
	return out, uint16(c.cpCount)
}

func verifyM4eAppendTargetIndex(t *testing.T, classfile *[]byte, name string) uint16 {
	t.Helper()
	out, index := verifyM4eAppendNameAndClass(t, *classfile, name)
	*classfile = out
	return index
}

func verifyM4eAppendNameAndClass(t *testing.T, original []byte, name string) ([]byte, uint16) {
	t.Helper()
	c := parseStaticsClass(t, original)
	if c.cpCount+2 > 65535 || len(name) > 65535 {
		t.Fatal("test constant pool/name too large")
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
	return out, uint16(c.cpCount + 1)
}

func verifyM4eRetargetName(t *testing.T, original []byte, method, name string) []byte {
	t.Helper()
	out, index := verifyM4eAppendNameAndClass(t, original, name)
	m := parseStaticsClass(t, out).namedMethod(t, method)
	pc := verifyM4eInstructionPC(t, m.code, verifyM4eMultianewarray, 0)
	binary.BigEndian.PutUint16(m.code[pc+1:], index)
	return out
}

func verifyM4eRewriteCode(t *testing.T, original []byte, name, descriptor string, code []byte, maxStack, maxLocals uint16) []byte {
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
	binary.BigEndian.PutUint16(out[start-8:], maxStack)
	binary.BigEndian.PutUint16(out[start-6:], maxLocals)
	for i := range m.code {
		m.code[i] = 0
	}
	copy(m.code, code)
	return out
}

func verifyM4eRewriteAtEnd(t *testing.T, original []byte, name, descriptor string, ending []byte) []byte {
	t.Helper()
	out := verifyM4eRewriteCode(t, original, name, descriptor, nil, 16, 16)
	m := parseStaticsClass(t, out).method(t, name, descriptor)
	copy(m.code[len(m.code)-len(ending):], ending)
	return out
}

func verifyM4eAssertProgram(t *testing.T, classfile []byte, method string, want []byte) {
	t.Helper()
	got := parseStaticsClass(t, classfile).namedMethod(t, method).code
	if len(got) < len(want) || !bytes.Equal(got[:len(want)], want) {
		t.Fatalf("handcrafted program=%x, want prefix %x", got, want)
	}
	// Force a boundary walk over the complete meaningful prefix.
	for pc := 0; pc < len(want); {
		pc += verifyM4eInstructionWidth(t, want, pc)
	}
}

func verifyM4eAssertValue(t *testing.T, run func() (Result, error), want int32) {
	t.Helper()
	result, err := run()
	if err != nil || result.ExceptionClass != "" || result.Value != want || result.GasUsed == 0 || len(result.RevertData) != 0 {
		t.Fatalf("result/error=%+v/%v, want value %d", result, err, want)
	}
}

func verifyM4eAssertException(t *testing.T, run func() (Result, error), want string, kind byte) {
	t.Helper()
	result, err := run()
	selector := crypto.Keccak256([]byte("JavaException(uint256)"))[:4]
	if err != nil || result.ExceptionClass != want || result.GasUsed == 0 || len(result.RevertData) != 36 ||
		!bytes.Equal(result.RevertData[:4], selector) || !bytes.Equal(result.RevertData[4:35], make([]byte, 31)) || result.RevertData[35] != kind {
		t.Fatalf("result/error=%+v/%v data=%x, want exact %s kind %d", result, err, result.RevertData, want, kind)
	}
}

func verifyM4eAssertError(t *testing.T, run func() (Result, error), signature string, code, pc uint64) {
	t.Helper()
	result, err := run()
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error=%+v/%v, want %s(%d,%d)", result, err, signature, code, pc)
	}
	selector := crypto.Keccak256([]byte(signature))[:4]
	if result.ExceptionClass != "" || result.GasUsed == 0 || len(result.RevertData) != 68 || !bytes.Equal(result.RevertData[:4], selector) {
		t.Fatalf("result=%+v data=%x, want exact %s payload", result, result.RevertData, signature)
	}
	if got := verifyM4eUint256(t, result.RevertData[4:36]); got != code {
		t.Fatalf("%s code=%d want %d data=%x", signature, got, code, result.RevertData)
	}
	if got := verifyM4eUint256(t, result.RevertData[36:]); got != pc {
		t.Fatalf("%s pc=%d want %d data=%x", signature, got, pc, result.RevertData)
	}
}

func verifyM4eUint256(t *testing.T, word []byte) uint64 {
	t.Helper()
	if len(word) != 32 || !bytes.Equal(word[:24], make([]byte, 24)) {
		t.Fatalf("noncanonical uint256 %x", word)
	}
	return binary.BigEndian.Uint64(word[24:])
}
