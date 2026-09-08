// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.

package jvmevm

import (
	"bytes"
	"encoding/binary"
	"sort"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/crypto"
)

const runtimeM4dGasLimit = uint64(250_000_000)

func runtimeM4dBundle(classes map[string][]byte) [][]byte {
	names := make([]string, 0, len(classes))
	for name := range classes {
		names = append(names, name)
	}
	sort.Strings(names)
	out := make([][]byte, 0, len(names))
	for _, name := range names {
		out = append(out, classes[name])
	}
	return out
}

func runtimeM4dRun(t *testing.T, classes map[string][]byte, entry, method string) Result {
	t.Helper()
	result, err := RunClasses(runtimeM4dBundle(classes), entry, method, nil, runtimeM4dGasLimit)
	if err != nil {
		t.Fatalf("RunClasses(%s.%s): %v", entry, method, err)
	}
	return result
}

func runtimeM4dWantValue(t *testing.T, classes map[string][]byte, entry, method string, want int32) {
	t.Helper()
	result := runtimeM4dRun(t, classes, entry, method)
	if result.ExceptionClass != "" || result.Value != want {
		t.Fatalf("%s.%s result = %+v, want value %d", entry, method, result, want)
	}
}

func runtimeM4dWantException(t *testing.T, classes map[string][]byte, entry, method, want string) {
	t.Helper()
	result := runtimeM4dRun(t, classes, entry, method)
	if result.ExceptionClass != want {
		t.Fatalf("%s.%s result = %+v, want %s", entry, method, result, want)
	}
}

func runtimeM4dOpcodePC(t *testing.T, classfile []byte, method string, opcode byte) int {
	t.Helper()
	code := parseStaticsClass(t, classfile).namedMethod(t, method).code
	pc := bytes.IndexByte(code, opcode)
	if pc < 0 {
		t.Fatalf("%s bytecode %x has no opcode 0x%02x", method, code, opcode)
	}
	return pc
}

func runtimeM4dClassIndex(t *testing.T, classfile []byte, name string) uint16 {
	t.Helper()
	class := parseStaticsClass(t, classfile)
	for index := 1; index < class.cpCount; index++ {
		entry := class.entries[index]
		if entry.tag != 7 {
			continue
		}
		nameIndex := binary.BigEndian.Uint16(classfile[entry.offset+1:])
		if class.utf8[nameIndex] == name {
			return uint16(index)
		}
	}
	t.Fatalf("CONSTANT_Class %q not found", name)
	return 0
}

func runtimeM4dWantSolidityError(t *testing.T, result Result, err error, signature string, code, detail uint64) {
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

func TestRuntimeM4dReferenceArraySemantics(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"m4d/Base.java":         `package m4d; public class Base { int value; Base(){value=3;} }`,
		"m4d/Child.java":        `package m4d; public class Child extends Base { Child(){value=7;} }`,
		"m4d/Other.java":        `package m4d; public class Other { }`,
		"m4d/AbstractPart.java": `package m4d; public abstract class AbstractPart { }`,
		"m4d/Component.java":    `package m4d; public class Component { static int marker=Root.bump(); }`,
		"m4d/Holder.java": `package m4d; public class Holder {
			static Child[] shared; final Base[] finalArray; Child[][] nested;
			Holder(){finalArray=new Child[1];}
			static Child[] pass(Child[] x){return x;}
			Base[] virtualPass(Base[] x){return x;}
		}`,
		"m4d/Root.java": `package m4d; public class Root {
			static int initialized; static int bump(){initialized++;return 1;}
			public static int defaults(){Object[] a=new Object[2];return a.length*10+(a[0]==null?1:0)+(a[1]==null?2:0);}
			public static int identity(){Object[] a=new Object[0];Object[] b=new Object[0];return a==b?0:1;}
			public static int aliases(){Child[] a=new Child[1];Child[] b=a;b[0]=new Child();return a[0].value;}
			public static int fieldsCalls(){Holder h=new Holder();Holder.shared=new Child[1];Holder.shared[0]=new Child();h.finalArray[0]=Holder.shared[0];Child[] x=Holder.pass(Holder.shared);Base[] y=h.virtualPass(x);return y[0].value;}
			public static int abstractComponent(){AbstractPart[] a=new AbstractPart[1];return a.length+(a[0]==null?4:0);}
			public static int componentNoInit(){Component[] a=new Component[0];return a.length+initialized;}
			public static int heterogeneous(){Object[] a=new Object[3];a[0]=new Child();a[1]=new Base();a[2]=new int[2];return ((Child)a[0]).value+((Base)a[1]).value+((int[])a[2]).length;}
			public static int nested(){int[][] a=new int[2][];a[0]=new int[3];a[1]=new int[1];a[0][2]=9;return a.length+a[0].length+a[1].length+a[0][2];}
			public static int covariance(){Child[][] c=new Child[1][];c[0]=new Child[1];c[0][0]=new Child();Base[][] b=c;Object[] o=c;return b[0][0].value+(o==c?5:0);}
			public static int recursiveTests(){int[][] a=new int[1][];Child[][] c=new Child[1][];return (a instanceof Object[]?1:0)+(((Object)a) instanceof Object[][]?2:0)+(c instanceof Base[][]?4:0)+(c instanceof Object[]?8:0);}
			public static int nestedStore(){int[][] a=new int[1][];Object[] o=a;o[0]=new int[4];return a[0].length;}
			public static int badStore(){Base[] a=new Child[1];a[0]=new Base();return 0;}
			public static int badNestedStore(){Object[][] a=new Child[1][];a[0]=new Object[1];return 0;}
			public static int boundsBeforeStore(){Base[] a=new Child[1];a[1]=new Base();return 0;}
			public static int nullLoad(){Object[] a=null;return a[0]==null?1:0;}
			public static int boundsLoad(){Object[] a=new Object[0];return a[0]==null?1:0;}
		}`,
	})
	for method, want := range map[string]int32{
		"defaults": 23, "identity": 1, "aliases": 7, "fieldsCalls": 7,
		"abstractComponent": 5, "componentNoInit": 0, "heterogeneous": 12,
		"nested": 15, "covariance": 12, "recursiveTests": 13, "nestedStore": 4,
	} {
		t.Run(method, func(t *testing.T) { runtimeM4dWantValue(t, classes, "m4d/Root", method, want) })
	}
	for method, want := range map[string]string{
		"badStore":          "java.lang.ArrayStoreException",
		"badNestedStore":    "java.lang.ArrayStoreException",
		"boundsBeforeStore": "java.lang.ArrayIndexOutOfBoundsException",
		"nullLoad":          "java.lang.NullPointerException",
		"boundsLoad":        "java.lang.ArrayIndexOutOfBoundsException",
	} {
		t.Run(method, func(t *testing.T) { runtimeM4dWantException(t, classes, "m4d/Root", method, want) })
	}
}

func TestRuntimeM4dANewArrayResolvesComponentBeforeEveryLength(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"missingm4d/Component.java": `package missingm4d; public class Component { }`,
		"missingm4d/Root.java": `package missingm4d; public class Root {
			public static int negative(){return new Component[-1].length;}
			public static int zero(){return new Component[0].length;}
			public static int positive(){return new Component[1].length;}
		}`,
	})
	root := classes["missingm4d/Root"]
	for _, method := range []string{"negative", "zero", "positive"} {
		t.Run("missing-"+method, func(t *testing.T) {
			pc := runtimeM4dOpcodePC(t, root, method, 0xbd)
			result, err := RunClasses([][]byte{root}, "missingm4d/Root", method, nil, runtimeM4dGasLimit)
			runtimeM4dWantSolidityError(t, result, err, "LinkError(uint256,uint256)", 4, uint64(pc))
		})
	}
	result := runtimeM4dRun(t, classes, "missingm4d/Root", "negative")
	if result.ExceptionClass != "java.lang.NegativeArraySizeException" {
		t.Fatalf("present component negative result = %+v, want NegativeArraySizeException", result)
	}
	runtimeM4dWantValue(t, classes, "missingm4d/Root", "zero", 0)
	runtimeM4dWantValue(t, classes, "missingm4d/Root", "positive", 1)
}

func TestRuntimeM4dRank255Boundary(t *testing.T) {
	rank254 := strings.Repeat("[", 254) + "I"
	rank255Java := "int" + strings.Repeat("[]", 255)
	source := `public class RankBoundary {
		public static int allowed(){return new int[1]` + strings.Repeat("[]", 254) + `.length;}
		public static int pool(Object x){return x instanceof ` + rank255Java + `?1:0;}
	}`
	classfile := compileJava(t, "RankBoundary", source)
	result, err := Run(classfile, "allowed", nil, runtimeM4dGasLimit)
	if err != nil || result.ExceptionClass != "" || result.Value != 1 {
		t.Fatalf("rank-255 allocation result/error = %+v/%v, want 1", result, err)
	}
	pc := runtimeM4dOpcodePC(t, classfile, "allowed", 0xbd)
	rank255Index := runtimeM4dClassIndex(t, classfile, "["+rank254)
	overflow := append([]byte(nil), classfile...)
	method := parseStaticsClass(t, overflow).namedMethod(t, "allowed")
	binary.BigEndian.PutUint16(method.code[pc+1:], rank255Index)
	result, err = Run(overflow, "allowed", nil, runtimeM4dGasLimit)
	runtimeM4dWantSolidityError(t, result, err, "ArrayError(uint256,uint256)", 2, uint64(pc))
}

func TestRuntimeM4dArrayStoreFromClassInitializerWraps(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"initm4d/Base.java":  `package initm4d; public class Base { }`,
		"initm4d/Child.java": `package initm4d; public class Child extends Base { }`,
		"initm4d/Fail.java":  `package initm4d; public class Fail { static int x=bad(); static int bad(){Base[] a=new Child[1];a[0]=new Base();return 1;} public static int run(){return x;} }`,
	})
	runtimeM4dWantException(t, classes, "initm4d/Fail", "run", "java.lang.ExceptionInInitializerError")
}
