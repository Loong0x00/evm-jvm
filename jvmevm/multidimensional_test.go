// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"encoding/binary"
	"sort"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/crypto"
)

const runtimeM4eGasLimit = uint64(250_000_000)

func runtimeM4eBundle(classes map[string][]byte, omit ...string) [][]byte {
	testingOmit := make(map[string]bool, len(omit))
	for _, name := range omit {
		testingOmit[name] = true
	}
	names := make([]string, 0, len(classes))
	for name := range classes {
		if !testingOmit[name] {
			names = append(names, name)
		}
	}
	sort.Strings(names)
	bundle := make([][]byte, 0, len(names))
	for _, name := range names {
		bundle = append(bundle, classes[name])
	}
	return bundle
}

func runtimeM4eRun(t *testing.T, classes map[string][]byte, entry, method string, args ...int32) Result {
	t.Helper()
	result, err := RunClasses(runtimeM4eBundle(classes), entry, method, args, runtimeM4eGasLimit)
	if err != nil {
		t.Fatalf("RunClasses(%s.%s): %v", entry, method, err)
	}
	return result
}

func runtimeM4eWantValue(t *testing.T, classes map[string][]byte, entry, method string, want int32, args ...int32) {
	t.Helper()
	result := runtimeM4eRun(t, classes, entry, method, args...)
	if result.ExceptionClass != "" || result.Value != want {
		t.Fatalf("%s.%s result = %+v, want value %d", entry, method, result, want)
	}
}

func runtimeM4eWantException(t *testing.T, classes map[string][]byte, entry, method, want string, args ...int32) {
	t.Helper()
	result := runtimeM4eRun(t, classes, entry, method, args...)
	if result.ExceptionClass != want {
		t.Fatalf("%s.%s result = %+v, want %s", entry, method, result, want)
	}
}

func runtimeM4eWantSolidityError(t *testing.T, result Result, err error, signature string, code, detail uint64) {
	t.Helper()
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error = %+v/%v, want %s", result, err, signature)
	}
	want := make([]byte, 68)
	copy(want, crypto.Keccak256([]byte(signature))[:4])
	binary.BigEndian.PutUint64(want[28:36], code)
	binary.BigEndian.PutUint64(want[60:68], detail)
	if !bytes.Equal(result.RevertData, want) || result.ExceptionClass != "" {
		t.Fatalf("revert = 0x%x, want %s(%d,%d)", result.RevertData, signature, code, detail)
	}
}

func runtimeM4eOpcodePC(t *testing.T, classfile []byte, method string) int {
	t.Helper()
	code := parseStaticsClass(t, classfile).namedMethod(t, method).code
	pc := bytes.IndexByte(code, 0xc5)
	if pc < 0 {
		t.Fatalf("%s bytecode %x has no multianewarray", method, code)
	}
	return pc
}

func runtimeM4eClassIndex(t *testing.T, classfile []byte, name string) uint16 {
	t.Helper()
	class := parseStaticsClass(t, classfile)
	for index := 1; index < class.cpCount; index++ {
		entry := class.entries[index]
		if entry.tag == 7 && class.utf8[binary.BigEndian.Uint16(classfile[entry.offset+1:])] == name {
			return uint16(index)
		}
	}
	t.Fatalf("CONSTANT_Class %q not found", name)
	return 0
}

func runtimeM4eReplaceMethodCode(t *testing.T, classfile []byte, method string, code []byte) []byte {
	t.Helper()
	out := append([]byte(nil), classfile...)
	parsed := parseTestClass(t, out)
	off, length := parsed.codeOffsets[method], parsed.codeLengths[method]
	if len(code) > length {
		t.Fatalf("replacement code length %d exceeds available %d", len(code), length)
	}
	for i := 0; i < length; i++ {
		out[off+i] = 0x00
	}
	copy(out[off:], code)
	binary.BigEndian.PutUint16(out[off-8:], 1024)
	binary.BigEndian.PutUint16(out[off-6:], 1024)
	return out
}

func TestRuntimeM4eRectangularPartialIdentityAndMetadata(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"m4e/AbstractPart.java": `package m4e; public abstract class AbstractPart { }`,
		"m4e/Base.java":         `package m4e; public class Base { int value; Base(){value=3;} }`,
		"m4e/Child.java":        `package m4e; public class Child extends Base { Child(){value=7;} }`,
		"m4e/Node.java": `package m4e; public class Node {
			static int marker=Root.bump(); Node(){Root.constructed++;}
		}`,
		"m4e/Holder.java": `package m4e; public class Holder {
			int[][] ints; static Child[][] children;
			static int[][] echo(int[][] x){return x;}
			int[][] virtualEcho(int[][] x){return x;}
		}`,
		"m4e/Root.java": `package m4e; public class Root {
			static int initialized,constructed; static int bump(){initialized++;return 1;}
			public static int ints(){int[][] a=new int[2][3];a[0][1]=7;return a.length*100+a[0].length*10+a[1].length+(a[0]==a[1]?1000:0)+a[0][0]+a[0][1]+a[1][2];}
			public static int refs(){Node[][] a=new Node[2][3];return a.length*100+a[0].length*10+(a[0]!=a[1]?4:0)+(a[0][0]==null?2:0)+initialized+constructed;}
			public static int abstractLeaf(){AbstractPart[][] a=new AbstractPart[1][2];return a.length+a[0].length+(a[0][0]==null?4:0);}
			public static int partial(){int[][][] a=new int[2][3][];return a.length*100+a[0].length*10+(a[0]!=a[1]?4:0)+(a[0][0]==null?2:0);}
			public static int zeroInner(){int[][][] a=new int[2][0][5];return a.length*100+a[0].length*10+(a[0]!=a[1]?4:0);}
			public static int aliases(){int[][] a=new int[2][2];int[][] b=a;b[1][1]=9;return a[1][1]+(a==b?3:0);}
			public static int fieldsCalls(){Holder h=new Holder();h.ints=new int[1][2];Holder.children=new Child[1][1];Holder.children[0][0]=new Child();int[][] a=Holder.echo(h.ints);int[][] b=h.virtualEcho(a);return b[0].length+Holder.children[0][0].value;}
			public static int covariance(){Child[][] c=new Child[1][1];Base[][] b=c;Object[] o=c;c[0][0]=new Child();return b[0][0].value+(o==c?4:0)+(c instanceof Base[][]?2:0);}
			public static int badNestedStore(){Object[][] a=new Child[1][1];a[0]=new Object[1];return 0;}
		}`,
	})
	for method, want := range map[string]int32{
		"ints": 240, "refs": 236, "abstractLeaf": 7, "partial": 236,
		"zeroInner": 204, "aliases": 12, "fieldsCalls": 9, "covariance": 13,
	} {
		t.Run(method, func(t *testing.T) { runtimeM4eWantValue(t, classes, "m4e/Root", method, want) })
	}
	runtimeM4eWantException(t, classes, "m4e/Root", "badNestedStore", "java.lang.ArrayStoreException")
}

func TestRuntimeM4eCountsOrderingZeroAndQuotas(t *testing.T) {
	classfile := compileJava(t, "MultiCounts", `public class MultiCounts {
		public static int shape(int a,int b){return new int[a][b].length;}
		public static int limitOK(){return new int[1023][0].length;}
		public static int limitOOM(){return new int[1024][0].length;}
		public static int elementLimitOK(){return new int[4][65535].length;}
		public static int totalOOM(){return new int[4][65536].length;}
		public static int priorArraysOOM(){for(int i=0;i<1023;i++){int[] x=new int[0];}return new int[1][0].length;}
		public static int objectsIndependent(){Object o=new Object();return new int[1023][0].length+(o==null?1:0);}
	}`)
	for _, tc := range []struct {
		name string
		a, b int32
		want int32
	}{{"zero-huge", 0, 2147483647, 0}, {"ordinary", 2, 3, 2}} {
		result, err := Run(classfile, "shape", []int32{tc.a, tc.b}, runtimeM4eGasLimit)
		if err != nil || result.ExceptionClass != "" || result.Value != tc.want {
			t.Fatalf("%s = %+v/%v, want %d", tc.name, result, err, tc.want)
		}
	}
	for _, tc := range []struct {
		name string
		a, b int32
	}{{"zero-negative", 0, -1}, {"cap-before-negative", 65537, -1}, {"negative-first", -1, 65537}} {
		result, err := Run(classfile, "shape", []int32{tc.a, tc.b}, runtimeM4eGasLimit)
		if err != nil || result.ExceptionClass != "java.lang.NegativeArraySizeException" {
			t.Fatalf("%s = %+v/%v, want NASE", tc.name, result, err)
		}
	}
	for invocation := 0; invocation < 2; invocation++ {
		result, err := Run(classfile, "limitOK", nil, runtimeM4eGasLimit)
		if err != nil || result.ExceptionClass != "" || result.Value != 1023 {
			t.Fatalf("limitOK invocation %d = %+v/%v", invocation, result, err)
		}
	}
	for method, want := range map[string]int32{"elementLimitOK": 4, "objectsIndependent": 1023} {
		result, err := Run(classfile, method, nil, runtimeM4eGasLimit)
		if err != nil || result.ExceptionClass != "" || result.Value != want {
			t.Fatalf("%s = %+v/%v, want %d", method, result, err, want)
		}
	}
	tooLong, err := Run(classfile, "shape", []int32{1, 65537}, runtimeM4eGasLimit)
	if err != nil || tooLong.ExceptionClass != "java.lang.OutOfMemoryError" {
		t.Fatalf("materialized overlong inner = %+v/%v, want OOM", tooLong, err)
	}
	for _, method := range []string{"limitOOM", "totalOOM", "priorArraysOOM"} {
		result, err := Run(classfile, method, nil, runtimeM4eGasLimit)
		if err != nil || result.ExceptionClass != "java.lang.OutOfMemoryError" {
			t.Fatalf("%s = %+v/%v, want OOM", method, result, err)
		}
	}
}

func TestRuntimeM4eResolutionBeforeCountsAndNoInitialization(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"missingm4e/Component.java": `package missingm4e; public class Component { }`,
		"missingm4e/Root.java": `package missingm4e; public class Root {
			public static int shape(int a,int b){return new Component[a][b].length;}
		}`,
		"accessm4e/Hidden.java": `package accessm4e; public class Hidden { }`,
		"otherm4e/Root.java": `package otherm4e; public class Root {
			public static int shape(int a,int b){return new accessm4e.Hidden[a][b].length;}
		}`,
	})
	root := classes["missingm4e/Root"]
	pc := runtimeM4eOpcodePC(t, root, "shape")
	for _, args := range [][]int32{{-1, -1}, {0, -1}, {0, 0}, {1, 1}} {
		result, err := RunClasses([][]byte{root}, "missingm4e/Root", "shape", args, runtimeM4eGasLimit)
		runtimeM4eWantSolidityError(t, result, err, "LinkError(uint256,uint256)", 4, uint64(pc))
	}

	inaccessible := append([]byte(nil), classes["accessm4e/Hidden"]...)
	accessOffset := bundleClassAccessOffset(t, inaccessible)
	flags := binary.BigEndian.Uint16(inaccessible[accessOffset:])
	binary.BigEndian.PutUint16(inaccessible[accessOffset:], flags&^uint16(0x0001))
	accessRoot := classes["otherm4e/Root"]
	pc = runtimeM4eOpcodePC(t, accessRoot, "shape")
	result, err := RunClasses([][]byte{accessRoot, inaccessible}, "otherm4e/Root", "shape", []int32{-1, -1}, runtimeM4eGasLimit)
	runtimeM4eWantSolidityError(t, result, err, "TypeError(uint256,uint256)", 2, uint64(pc))
}

func TestRuntimeM4eInitializerOutcomes(t *testing.T) {
	negative := compileJava(t, "InitMultiNegative", `public class InitMultiNegative {
		static int[][] value=new int[0][-1]; public static int run(){return 1;}
	}`)
	result, err := Run(negative, "run", nil, runtimeM4eGasLimit)
	if err != nil || result.ExceptionClass != "java.lang.ExceptionInInitializerError" {
		t.Fatalf("initializer NASE = %+v/%v, want EIIE", result, err)
	}
	oom := compileJava(t, "InitMultiOOM", `public class InitMultiOOM {
		static int[][] value=new int[1024][0]; public static int run(){return 1;}
	}`)
	result, err = Run(oom, "run", nil, runtimeM4eGasLimit)
	if err != nil || result.ExceptionClass != "java.lang.OutOfMemoryError" {
		t.Fatalf("initializer OOM = %+v/%v, want unwrapped OOM", result, err)
	}
}

func TestRuntimeM4eDimensionOneAndFullRank255AreIterative(t *testing.T) {
	base := compileJava(t, "DimensionOne", `public class DimensionOne {
		public static int run(){return 7+new int[2][3].length;}
		public static int pool(Object x){return x instanceof int[]?1:0;}
	}`)
	mutated := append([]byte(nil), base...)
	parsed := parseTestClass(t, mutated)
	pc := runtimeM4eOpcodePC(t, mutated, "run")
	if pc < 2 || parsed.methodCode(t, "run")[pc-2] != 0x05 {
		t.Fatalf("unexpected dimension-one template %x", parsed.methodCode(t, "run"))
	}
	mutated[parsed.codeOffsets["run"]+pc-2] = 0x00
	binary.BigEndian.PutUint16(mutated[parsed.codeOffsets["run"]+pc+1:], runtimeM4eClassIndex(t, mutated, "[I"))
	mutated[parsed.codeOffsets["run"]+pc+3] = 1
	result, err := Run(mutated, "run", nil, runtimeM4eGasLimit)
	if err != nil || result.ExceptionClass != "" || result.Value != 10 {
		t.Fatalf("controlled dimensions=1 = %+v/%v, want 10", result, err)
	}

	rank255 := compileJava(t, "FullRank255", `public class FullRank255 { public static int run(){return new int`+strings.Repeat("[1]", 255)+`.length;} }`)
	code := parseTestClass(t, rank255).methodCode(t, "run")
	pc = runtimeM4eOpcodePC(t, rank255, "run")
	if code[pc+3] != 255 {
		t.Fatalf("rank-255 dimensions = %d, bytecode %x", code[pc+3], code)
	}
	result, err = Run(rank255, "run", nil, runtimeM4eGasLimit)
	if err != nil || result.ExceptionClass != "" || result.Value != 1 {
		t.Fatalf("full rank-255 = %+v/%v, want 1", result, err)
	}
}

func TestRuntimeM4eStructuralDimensionsStackAndBoundaries(t *testing.T) {
	base := compileJava(t, "MultiValidation", `public class MultiValidation {
		public static int run(int a,int b){return new int[a][b].length;}
		public static int room(int x){x=x+1;x=x+2;x=x+3;x=x+4;x=x+5;x=x+6;x=x+7;x=x+8;return x;}
	}`)
	parsed := parseTestClass(t, base)
	pc := runtimeM4eOpcodePC(t, base, "run")
	codeOffset := parsed.codeOffsets["run"]
	arrayIndex := binary.BigEndian.Uint16(base[codeOffset+pc+1:])
	thisIndex := runtimeM4eClassIndex(t, base, "MultiValidation")

	for _, tc := range []struct {
		name   string
		mutate func([]byte)
		sig    string
		code   uint64
	}{
		{"dimensions-zero", func(out []byte) { out[codeOffset+pc+3] = 0 }, "ArrayError(uint256,uint256)", 3},
		{"dimensions-over-rank", func(out []byte) { out[codeOffset+pc+3] = 3 }, "ArrayError(uint256,uint256)", 3},
		{"non-array", func(out []byte) { binary.BigEndian.PutUint16(out[codeOffset+pc+1:], thisIndex) }, "ArrayError(uint256,uint256)", 3},
		{"zero-cp", func(out []byte) { binary.BigEndian.PutUint16(out[codeOffset+pc+1:], 0) }, "TypeError(uint256,uint256)", 1},
	} {
		t.Run(tc.name, func(t *testing.T) {
			out := append([]byte(nil), base...)
			tc.mutate(out)
			result, err := Run(out, "run", []int32{1, 1}, runtimeM4eGasLimit)
			runtimeM4eWantSolidityError(t, result, err, tc.sig, tc.code, uint64(pc))
		})
	}

	t.Run("non-class-cp-tag", func(t *testing.T) {
		out := append([]byte(nil), base...)
		class := parseCallTestClass(t, out)
		nameIndex := binary.BigEndian.Uint16(out[class.cpOffsets[arrayIndex]+1:])
		binary.BigEndian.PutUint16(out[codeOffset+pc+1:], nameIndex)
		result, err := Run(out, "run", []int32{1, 1}, runtimeM4eGasLimit)
		runtimeM4eWantSolidityError(t, result, err, "TypeError(uint256,uint256)", 1, uint64(pc))
	})
	t.Run("malformed-array-name", func(t *testing.T) {
		out := append([]byte(nil), base...)
		class := parseCallTestClass(t, out)
		nameIndex := binary.BigEndian.Uint16(out[class.cpOffsets[arrayIndex]+1:])
		copy(out[class.cpOffsets[nameIndex]+3:], []byte("[;I"))
		result, err := Run(out, "run", []int32{1, 1}, runtimeM4eGasLimit)
		runtimeM4eWantSolidityError(t, result, err, "TypeError(uint256,uint256)", 1, uint64(pc))
	})
	t.Run("byte-primitive-negative-size", func(t *testing.T) {
		out := append([]byte(nil), base...)
		class := parseCallTestClass(t, out)
		nameIndex := binary.BigEndian.Uint16(out[class.cpOffsets[arrayIndex]+1:])
		copy(out[class.cpOffsets[nameIndex]+3:], []byte("[[B"))
		verifyM4eAssertException(t, func() (Result, error) {
			return Run(out, "run", []int32{-1, -1}, runtimeM4eGasLimit)
		}, "java.lang.NegativeArraySizeException", 4)
	})
	t.Run("deferred-long-primitive", func(t *testing.T) {
		out := append([]byte(nil), base...)
		class := parseCallTestClass(t, out)
		nameIndex := binary.BigEndian.Uint16(out[class.cpOffsets[arrayIndex]+1:])
		copy(out[class.cpOffsets[nameIndex]+3:], []byte("[[J"))
		result, err := Run(out, "run", []int32{1, 1}, runtimeM4eGasLimit)
		runtimeM4eWantSolidityError(t, result, err, "TypeError(uint256,uint256)", 2, uint64(pc))
	})

	underflow := runtimeM4eReplaceMethodCode(t, base, "room", []byte{0x04, 0xc5, byte(arrayIndex >> 8), byte(arrayIndex), 0x02, 0xbe, 0xac})
	result, err := Run(underflow, "room", []int32{0}, runtimeM4eGasLimit)
	runtimeM4eWantSolidityError(t, result, err, "BytecodeError(uint256,uint256)", 3, 1)
	wrongKind := runtimeM4eReplaceMethodCode(t, base, "room", []byte{0x01, 0x04, 0xc5, byte(arrayIndex >> 8), byte(arrayIndex), 0x02, 0xbe, 0xac})
	result, err = Run(wrongKind, "room", []int32{0}, runtimeM4eGasLimit)
	runtimeM4eWantSolidityError(t, result, err, "BytecodeError(uint256,uint256)", 14, 2)

	for available := 1; available <= 3; available++ {
		t.Run("truncated-"+string(rune('0'+available)), func(t *testing.T) {
			out := runtimeM4eReplaceMethodCode(t, base, "room", nil)
			p := parseTestClass(t, out)
			badPC := p.codeLengths["room"] - available
			out[p.codeOffsets["room"]+badPC] = 0xc5
			result, err := Run(out, "room", []int32{0}, runtimeM4eGasLimit)
			runtimeM4eWantSolidityError(t, result, err, "BytecodeError(uint256,uint256)", 2, uint64(badPC))
		})
	}
	for operand := 1; operand <= 3; operand++ {
		t.Run("branch-into-operand-"+string(rune('0'+operand)), func(t *testing.T) {
			seq := []byte{0xa7, 0, byte(5 + operand), 0x04, 0x04, 0xc5, byte(arrayIndex >> 8), byte(arrayIndex), 0x02, 0xbe, 0xac}
			out := runtimeM4eReplaceMethodCode(t, base, "room", seq)
			result, err := Run(out, "room", []int32{0}, runtimeM4eGasLimit)
			runtimeM4eWantSolidityError(t, result, err, "BytecodeError(uint256,uint256)", 12, 0)
		})
	}
}
