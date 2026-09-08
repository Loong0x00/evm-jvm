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
	verifyM5baGasLimit         = uint64(180_000_000)
	verifyM5baCapacityGasLimit = uint64(300_000_000)
)

// These verifier-only tests use bounded trusted Java 8 inputs. Valid mutated
// classes are checked with an actual Java 8 VM. Invalid CP, slot, and category
// forms are EVM validation probes, not claims about a complete JVM verifier.
// Production still receives only unchanged opaque classfile bytes.

func TestVerifyM5baConstantPoolLongHolesLdc2AndRootABI(t *testing.T) {
	classfile := verifyM5baCompile(t, map[string]string{
		"cp5/Constants.java": `package cp5; public final class Constants {
			static long A=0x1122334455667788L; static long B=-0x102030405060708L;
			static final double D=1.25; static final int I=23;
			public static int a(){return (int)(A^(A>>>32));}
			public static int b(){return (int)(B^(B>>>32));}
			public static long rootArg(long x){return x;} public static long rootReturn(int x){return x;}
			public static int padding(){int x=0;` + strings.Repeat("x=x+1;", 80) + `return x;}
		}`,
	}, "cp5/Constants")["cp5/Constants"]
	c := parseStaticsClass(t, classfile)
	longs := verifyM5baCPIndices(c, 5)
	if len(longs) < 2 {
		t.Fatalf("CONSTANT_Long entries=%v want at least two", longs)
	}
	for _, index := range longs {
		if int(index)+1 >= c.cpCount || c.entries[index+1].tag != 0 {
			t.Fatalf("CONSTANT_Long #%d does not reserve unusable index #%d", index, index+1)
		}
		if int(index)+2 < c.cpCount && c.entries[index+2].tag != 0 &&
			c.entries[index+2].offset != c.entries[index].offset+9 {
			t.Fatalf("entry after long starts at %d, want %d (no serialized hole)", c.entries[index+2].offset, c.entries[index].offset+9)
		}
	}
	clinit := c.method(t, "<clinit>", "()V").code
	for occurrence := 0; occurrence < 2; occurrence++ {
		pc := verifyM5baInstructionPC(t, clinit, 0x14, occurrence)
		index := binary.BigEndian.Uint16(clinit[pc+1:])
		if c.entry(t, index).tag != 5 {
			t.Fatalf("<clinit> ldc2_w index/tag=%d/%d want CONSTANT_Long", index, c.entry(t, index).tag)
		}
	}
	verifyM5baJava8Outcome(t, [][]byte{classfile}, "cp5.Constants", "a", nil, "value=1145324748")
	verifyM5baAssertValue(t, func() (Result, error) { return Run(classfile, "a", nil, verifyM5baGasLimit) }, 1145324748)

	for _, tc := range []struct {
		method string
		args   []int32
	}{
		{"rootArg", []int32{1}}, {"rootReturn", []int32{1}},
	} {
		t.Run("root-J-"+tc.method, func(t *testing.T) {
			verifyM5baAssertMethodError(t, func() (Result, error) {
				return Run(classfile, tc.method, tc.args, verifyM5baGasLimit)
			}, 11)
		})
	}

	padding := c.namedMethod(t, "padding")
	longIndex := longs[0]
	doubleIndex := verifyM5baCPIndices(c, 6)[0]
	integerIndex := verifyM5baCPIndices(c, 3)[0]
	wrong := []struct {
		name       string
		index      uint16
		kind, atPC uint64
	}{
		{"zero", 0, 13, 0}, {"range", uint16(c.cpCount), 13, 0},
		{"hole", longIndex + 1, 13, 0}, {"integer", integerIndex, 13, 0},
		// Double is a valid ldc2_w kind in M5c-b; the following l2i at pc 3
		// precisely guards D/J kind separation instead of obsolete rejection.
		{"double-then-l2i", doubleIndex, 14, 3},
	}
	for _, tc := range wrong {
		t.Run("ldc2-"+tc.name, func(t *testing.T) {
			code := []byte{0x14, byte(tc.index >> 8), byte(tc.index), 0x88, 0xac}
			bad := verifyM5baRewriteCode(t, classfile, "padding", "()I", code, 2, 0)
			verifyM5baAssertError(t, func() (Result, error) { return Run(bad, "padding", nil, verifyM5baGasLimit) },
				"BytecodeError(uint256,uint256)", tc.kind, tc.atPC)
		})
	}
	for _, op := range []byte{0x12, 0x13} {
		if op == 0x12 && longIndex > 255 {
			continue
		}
		code := []byte{op}
		if op == 0x12 {
			code = append(code, byte(longIndex))
		} else {
			code = append(code, byte(longIndex>>8), byte(longIndex))
		}
		code = append(code, 0xac)
		bad := verifyM5baRewriteCode(t, classfile, "padding", "()I", code, 2, 0)
		verifyM5baAssertError(t, func() (Result, error) { return Run(bad, "padding", nil, verifyM5baGasLimit) },
			"BytecodeError(uint256,uint256)", 13, 0)
	}

	truncated := append([]byte(nil), classfile[:c.entry(t, longIndex).offset+8]...)
	verifyM5baAssertError(t, func() (Result, error) { return Run(truncated, "a", nil, verifyM5baGasLimit) },
		"ClassError(uint256,uint256)", 12, uint64(c.entry(t, longIndex).offset+5))

	last := c.cpCount - 1
	if c.entries[last].tag == 0 {
		t.Fatalf("fixture's last CP index is unexpectedly a category-2 hole")
	}
	lastLong := append([]byte(nil), classfile...)
	lastLong[c.entries[last].offset] = 5
	verifyM5baAssertError(t, func() (Result, error) { return Run(lastLong, "a", nil, verifyM5baGasLimit) },
		"ClassError(uint256,uint256)", 3, uint64(c.entries[last].offset+9))

	truncatedLdc := verifyM5baRewriteAtEnd(t, classfile, "padding", "()I", []byte{0x14, 0})
	truncatedPC := len(parseStaticsClass(t, truncatedLdc).namedMethod(t, "padding").code) - 2
	verifyM5baAssertError(t, func() (Result, error) { return Run(truncatedLdc, "padding", nil, verifyM5baGasLimit) },
		"BytecodeError(uint256,uint256)", 2, uint64(truncatedPC))
	_ = padding
}

func TestVerifyM5baFullWidthArithmeticConversionsComparisonAndExceptions(t *testing.T) {
	classfile := verifyM5baCompile(t, map[string]string{
		"LongMath.java": `public final class LongMath {
			static long id(long x){return x;} static int fold(long x){return (int)(x^(x>>>32));}
			public static int constants(){return fold(id(0x1122334455667788L))+fold(id(-0x102030405060708L));}
			public static int add(){return fold(id(Long.MAX_VALUE)+id(1L));}
			public static int sub(){return fold(id(Long.MIN_VALUE)-id(1L));}
			public static int mul(){return fold(id(0x123456789abcdef0L)*id(0x102030405L));}
			public static int divNeg(){return fold(id(-9223372036854775807L)/id(3L));}
			public static int remNeg(){return fold(id(-9223372036854775807L)%id(3L));}
			public static int minDiv(){long x=id(Long.MIN_VALUE);return (x/id(-1L)==x?10:0)+(int)(x%id(-1L));}
			public static int neg(){return fold(-id(Long.MIN_VALUE));}
			public static int shifts(){long x=id(0x8123456789abcdefL);return fold(x<<idInt(-1))+fold(x>>idInt(65))+fold(x>>>idInt(65))+fold(x<<idInt(64));}
			static int idInt(int x){return x;}
			public static int bits(){long a=id(0xf0f00f0ff00ff00fL),b=id(0x33333333ccccccccL);return fold(a&b)+fold(a|b)+fold(a^b);}
			public static int cmp(){long hi=id(0x100000000L), neg=id(-1L);return (hi>id(1L)?1:0)+(neg<hi?2:0)+(hi==id(hi)?4:0);}
			public static int conversions(int x){long y=x;return (int)(y+id(0x100000000L));}
			public static int low(){return (int)id(0x89abcdef76543210L);}
			public static int divZero(){long z=0;return (int)(7L/z);}
			public static int remZero(){long z=0;return (int)(7L%z);}
		}`,
	}, "LongMath")["LongMath"]
	seenOps := make(map[byte]bool)
	for _, method := range parseStaticsClass(t, classfile).methods {
		for pc := 0; pc < len(method.code); pc += verifyM5baInstructionWidth(t, method.code, pc) {
			seenOps[method.code[pc]] = true
		}
	}
	for _, opcode := range []byte{0x61, 0x65, 0x69, 0x6d, 0x71, 0x75, 0x79, 0x7b, 0x7d, 0x7f, 0x81, 0x83, 0x85, 0x88, 0x94} {
		if !seenOps[opcode] {
			t.Fatalf("trusted LongMath fixture lacks required opcode 0x%02x", opcode)
		}
	}
	cases := []struct {
		method string
		args   []int32
	}{
		{"constants", nil}, {"add", nil}, {"sub", nil}, {"mul", nil},
		{"divNeg", nil}, {"remNeg", nil}, {"minDiv", nil}, {"neg", nil},
		{"shifts", nil}, {"bits", nil}, {"cmp", nil},
		{"conversions", []int32{-2147483648}}, {"conversions", []int32{-1}}, {"low", nil},
	}
	for _, tc := range cases {
		t.Run(tc.method+fmt.Sprint(tc.args), func(t *testing.T) {
			want := verifyM5baJava8Int(t, [][]byte{classfile}, "LongMath", tc.method, tc.args)
			verifyM5baAssertValue(t, func() (Result, error) { return Run(classfile, tc.method, tc.args, verifyM5baGasLimit) }, want)
		})
	}
	for _, method := range []string{"divZero", "remZero"} {
		t.Run(method, func(t *testing.T) {
			verifyM5baJava8Outcome(t, [][]byte{classfile}, "LongMath", method, nil, "exception=java.lang.ArithmeticException")
			verifyM5baAssertException(t, func() (Result, error) { return Run(classfile, method, nil, verifyM5baGasLimit) },
				"java.lang.ArithmeticException", 1)
		})
	}
	result, err := Run(classfile, "add", nil, 1)
	if err == nil || !errors.Is(err, vm.ErrOutOfGas) || result.ExceptionClass != "" || len(result.RevertData) != 0 {
		t.Fatalf("result/error=%+v/%v want unlabeled EVM out of gas", result, err)
	}
}

func TestVerifyM5baLongArgumentsReturnsAllCallModesAndWordOffsets(t *testing.T) {
	classes := verifyM5baCompile(t, map[string]string{
		"callsj/I.java": `package callsj; public interface I {
			long iface(long x); default long def(long x){return x+5L;}
			static long stat(long x){return x+1L;}
		}`,
		"callsj/C.java": `package callsj; public final class C implements I {
			long value; public C(long x){value=x;} public long virtual(long x){return value+x+3L;}
			public long iface(long x){return value+x+4L;}
		}`,
		"callsj/Root.java": `package callsj; public final class Root {
			private long special(long x){return x+2L;} static long helper(long x){return x+6L;}
			static long mixed(int a,long b,int c){return a+b+c;}
			static long callInterface(I i,long x){return i.iface(x);}
			static long recursive(long x,int n){return n==0?x:recursive(x+1,n-1);}
			public static int overflow(int x){return (int)recursive(x,200);}
			public static int run(int x){long n=((long)x<<33)+7L;C c=new C(n);
				long r=I.stat(n)+new Root().special(n)+c.virtual(n)+callInterface(c,n)+c.def(n)+helper(n)+mixed(2,n,3);
				return (int)(r^(r>>>32));}
		}`,
	}, "callsj/I", "callsj/C", "callsj/Root")
	bundle := verifyM5baBundle(classes)
	for _, x := range []int32{-7, 0, 19, 2147483647} {
		want := verifyM5baJava8Int(t, bundle, "callsj.Root", "run", []int32{x})
		verifyM5baAssertValue(t, func() (Result, error) {
			return RunClasses(bundle, "callsj/Root", "run", []int32{x}, verifyM5baGasLimit)
		}, want)
	}
	verifyM5baAssertException(t, func() (Result, error) {
		return RunClasses(bundle, "callsj/Root", "overflow", []int32{1}, verifyM5baGasLimit)
	}, "java.lang.StackOverflowError", 2)
	root := parseStaticsClass(t, classes["callsj/Root"])
	method := root.method(t, "callInterface", "(Lcallsj/I;J)J")
	pc := verifyM5baMemberPC(t, root, method, 0xb9, 11, "iface", "(J)J")
	if got := method.code[pc+3 : pc+5]; !bytes.Equal(got, []byte{3, 0}) {
		t.Fatalf("invokeinterface (J)J suffix=%x want word count 3 and trailing zero", got)
	}
	for _, count := range []byte{2, 4} {
		badRoot := verifyM5baMutate(t, classes["callsj/Root"], func(_ []byte, c staticsClass) {
			m := c.method(t, "callInterface", "(Lcallsj/I;J)J")
			p := verifyM5baMemberPC(t, c, m, 0xb9, 11, "iface", "(J)J")
			m.code[p+3] = count
		})
		bad := verifyM5baReplaceClass(classes, "callsj/Root", badRoot)
		verifyM5baAssertError(t, func() (Result, error) {
			return RunClasses(verifyM5baBundle(bad), "callsj/Root", "run", []int32{1}, verifyM5baGasLimit)
		}, "CallError(uint256,uint256)", 1, uint64(pc))
	}

	for _, tc := range []struct {
		method, descriptor string
		from, to           byte
	}{
		{"helper", "(J)J", 0xad, 0xac}, {"mixed", "(IJI)J", 0xad, 0xac},
	} {
		badRoot := verifyM5baReplaceOpcode(t, classes["callsj/Root"], tc.method, tc.descriptor, tc.from, tc.to, 1)
		bad := verifyM5baReplaceClass(classes, "callsj/Root", badRoot)
		returnPC := verifyM5baInstructionPC(t, parseStaticsClass(t, badRoot).method(t, tc.method, tc.descriptor).code, tc.to, 0)
		verifyM5baAssertError(t, func() (Result, error) {
			return RunClasses(verifyM5baBundle(bad), "callsj/Root", "run", []int32{1}, verifyM5baGasLimit)
		}, "CallError(uint256,uint256)", 5, uint64(returnPC))
	}
}

func TestVerifyM5baLocalsUseTwoWordsOddStartsAndInvalidateEveryOverlap(t *testing.T) {
	base := verifyM5baRawFixture(t)
	valid := []struct {
		name      string
		code      []byte
		maxLocals uint16
		want      int32
	}{
		{"short-0", []byte{0x0a, 0x3f, 0x1e, 0x88, 0xac}, 2, 1},
		{"odd-short-1", []byte{0x0a, 0x40, 0x1f, 0x88, 0xac}, 3, 1},
		{"short-2", []byte{0x0a, 0x41, 0x20, 0x88, 0xac}, 4, 1},
		{"odd-short-3", []byte{0x0a, 0x42, 0x21, 0x88, 0xac}, 5, 1},
		{"odd-indexed", []byte{0x0a, 0x37, 3, 0x16, 3, 0x88, 0xac}, 5, 1},
		{"int-beside-long", []byte{0x08, 0x3b, 0x0a, 0x40, 0x1a, 0x1f, 0x88, 0x60, 0xac}, 3, 6},
	}
	for _, tc := range valid {
		t.Run(tc.name, func(t *testing.T) {
			classfile := verifyM5baRewriteCode(t, base, "padding", "()I", tc.code, 4, tc.maxLocals)
			verifyM5baJava8Outcome(t, [][]byte{verifyM5baMajor49(classfile)}, "M5baRaw", "padding", nil, "value="+strconv.Itoa(int(tc.want)))
			verifyM5baAssertValue(t, func() (Result, error) { return Run(classfile, "padding", nil, verifyM5baGasLimit) }, tc.want)
		})
	}

	invalid := []struct {
		name string
		code []byte
		max  uint16
		kind uint64
		pc   int
	}{
		{"lstore-range", []byte{0x0a, 0x3f, 0x03, 0xac}, 1, 8, 1},
		{"lload-range", []byte{0x1e, 0x88, 0xac}, 1, 8, 0},
		{"lload-uninitialized", []byte{0x1e, 0x88, 0xac}, 2, 11, 0},
		{"tail-lload", []byte{0x0a, 0x3f, 0x1f, 0x88, 0xac}, 3, 14, 2},
		{"head-iload", []byte{0x0a, 0x3f, 0x1a, 0xac}, 2, 14, 2},
		{"tail-iload", []byte{0x0a, 0x3f, 0x1b, 0xac}, 2, 14, 2},
		{"iinc-head", []byte{0x0a, 0x3f, 0x84, 0, 1, 0x03, 0xac}, 2, 14, 2},
		{"iinc-tail", []byte{0x0a, 0x3f, 0x84, 1, 1, 0x03, 0xac}, 2, 14, 2},
		{"istore-tail-invalidates-head", []byte{0x0a, 0x3f, 0x04, 0x3c, 0x1e, 0x88, 0xac}, 2, 11, 4},
		{"istore-head-retypes-head", []byte{0x0a, 0x3f, 0x04, 0x3b, 0x1e, 0x88, 0xac}, 2, 14, 4},
		{"astore-tail-invalidates-head", []byte{0x0a, 0x3f, 0x01, 0x4c, 0x1e, 0x88, 0xac}, 2, 11, 4},
		{"astore-head-retypes-head", []byte{0x0a, 0x3f, 0x01, 0x4b, 0x1e, 0x88, 0xac}, 2, 14, 4},
		{"lstore-overlaps-left", []byte{0x0a, 0x3f, 0x0a, 0x41, 0x0a, 0x40, 0x1e, 0x88, 0xac}, 4, 11, 6},
		{"lstore-overlaps-right-head", []byte{0x0a, 0x3f, 0x0a, 0x41, 0x0a, 0x40, 0x20, 0x88, 0xac}, 4, 14, 6},
	}
	for _, tc := range invalid {
		t.Run(tc.name, func(t *testing.T) {
			classfile := verifyM5baRewriteCode(t, base, "padding", "()I", tc.code, 6, tc.max)
			verifyM5baAssertError(t, func() (Result, error) { return Run(classfile, "padding", nil, verifyM5baGasLimit) },
				"BytecodeError(uint256,uint256)", tc.kind, uint64(tc.pc))
		})
	}
}

func TestVerifyM5baEveryCategoryTwoStackPermutationForm(t *testing.T) {
	base := verifyM5baRawFixture(t)
	forms := []struct {
		name string
		code []byte
		want int32
	}{
		{"pop2-cat2", []byte{0x0a, 0x58, 0x10, 7, 0xac}, 7},
		{"pop2-two-cat1", []byte{0x04, 0x05, 0x58, 0x10, 7, 0xac}, 7},
		{"dup2-cat2", []byte{0x0a, 0x5c, 0x61, 0x88, 0xac}, 2},
		{"dup2-two-cat1", []byte{0x05, 0x06, 0x5c, 0x60, 0x5f, 0x60, 0x60, 0xac}, 10},
		{"dup-x2-three-cat1", []byte{0x04, 0x05, 0x06, 0x5b, 0x60, 0x60, 0x60, 0xac}, 9},
		{"dup-x2-long-below-int", []byte{0x0a, 0x05, 0x5b, 0x57, 0x88, 0x60, 0xac}, 3},
		{"dup2-x1-three-cat1", []byte{0x04, 0x05, 0x06, 0x5d, 0x60, 0x60, 0x60, 0x60, 0xac}, 11},
		{"dup2-x1-int-below-long", []byte{0x05, 0x0a, 0x5d, 0x58, 0x57, 0x88, 0xac}, 1},
		{"dup2-x2-form1", []byte{0x04, 0x05, 0x06, 0x07, 0x5e, 0x60, 0x60, 0x60, 0x60, 0x60, 0xac}, 17},
		{"dup2-x2-form2", []byte{0x04, 0x05, 0x0a, 0x5e, 0x58, 0x57, 0x57, 0x88, 0xac}, 1},
		{"dup2-x2-form3", []byte{0x0a, 0x05, 0x06, 0x5e, 0x57, 0x57, 0x58, 0x60, 0xac}, 5},
		{"dup2-x2-form4", []byte{0x0a, 0x09, 0x5e, 0x58, 0x88, 0x57, 0x88, 0xac}, 0},
	}
	for _, tc := range forms {
		t.Run(tc.name, func(t *testing.T) {
			classfile := verifyM5baRewriteCode(t, base, "padding", "()I", tc.code, 10, 1)
			verifyM5baJava8Outcome(t, [][]byte{verifyM5baMajor49(classfile)}, "M5baRaw", "padding", nil, "value="+strconv.Itoa(int(tc.want)))
			verifyM5baAssertValue(t, func() (Result, error) { return Run(classfile, "padding", nil, verifyM5baGasLimit) }, tc.want)
		})
	}
}

func TestVerifyM5baMixedReferenceAndUninitializedCategoryTwoTransport(t *testing.T) {
	classes := verifyM5baCompile(t, map[string]string{
		"transport/Box.java": `package transport; public final class Box { public Box(){} }`,
		"transport/Root.java": `package transport; public final class Root {
			static int use(Box b){return b==null?0:7;} public static int padding(){Box b=new Box();int x=0;` + strings.Repeat("x=x+1;", 80) + `return use(b)+x-x;}
		}`,
	}, "transport/Box", "transport/Root")
	root := classes["transport/Root"]
	c := parseStaticsClass(t, root)
	m := c.namedMethod(t, "padding")
	newPC := verifyM5baInstructionPC(t, m.code, 0xbb, 0)
	classIndex := binary.BigEndian.Uint16(m.code[newPC+1:])
	ctorPC := verifyM5baMemberPC(t, c, m, 0xb7, 10, "<init>", "()V")
	ctorRef := binary.BigEndian.Uint16(m.code[ctorPC+1:])
	usePC := verifyM5baMemberPC(t, c, m, 0xb8, 10, "use", "(Ltransport/Box;)I")
	useRef := binary.BigEndian.Uint16(m.code[usePC+1:])

	codes := []struct {
		name string
		code []byte
		want int32
	}{
		{
			"dup2-x1-uninitialized",
			[]byte{0xbb, byte(classIndex >> 8), byte(classIndex), 0x0a, 0x5d, 0x58,
				0xb7, byte(ctorRef >> 8), byte(ctorRef), 0x88, 0xac}, 1,
		},
		{
			"dup-x2-uninitialized-alias",
			[]byte{0x0a, 0xbb, byte(classIndex >> 8), byte(classIndex), 0x5b,
				0xb7, byte(ctorRef >> 8), byte(ctorRef), 0x58,
				0xb8, byte(useRef >> 8), byte(useRef), 0xac}, 7,
		},
		{
			"dup2-x2-form2-reference",
			[]byte{0x04, 0xbb, byte(classIndex >> 8), byte(classIndex), 0x0a, 0x5e, 0x58,
				0xb7, byte(ctorRef >> 8), byte(ctorRef), 0x57, 0x88, 0xac}, 1,
		},
	}
	for _, tc := range codes {
		t.Run(tc.name, func(t *testing.T) {
			mutated := verifyM5baRewriteCode(t, root, "padding", "()I", tc.code, 8, 2)
			bundle := [][]byte{classes["transport/Box"], verifyM5baMajor49(mutated)}
			verifyM5baJava8Outcome(t, bundle, "transport.Root", "padding", nil, "value="+strconv.Itoa(int(tc.want)))
			verifyM5baAssertValue(t, func() (Result, error) {
				return RunClasses([][]byte{classes["transport/Box"], mutated}, "transport/Root", "padding", nil, verifyM5baGasLimit)
			}, tc.want)
		})
	}

	uninitializedStores := []struct {
		name string
		code []byte
		kind uint64
		pc   int
	}{
		{"uninit-astore-tail-invalidates-long", []byte{0x0a, 0x3f, 0xbb, byte(classIndex >> 8), byte(classIndex), 0x4c, 0x1e, 0x88, 0xac}, 11, 6},
		{"lstore-invalidates-uninit-head", []byte{0xbb, byte(classIndex >> 8), byte(classIndex), 0x4b, 0x0a, 0x3f, 0x2a, 0x03, 0xac}, 14, 6},
	}
	for _, tc := range uninitializedStores {
		t.Run(tc.name, func(t *testing.T) {
			mutated := verifyM5baRewriteCode(t, root, "padding", "()I", tc.code, 4, 2)
			verifyM5baAssertError(t, func() (Result, error) {
				return RunClasses([][]byte{classes["transport/Box"], mutated}, "transport/Root", "padding", nil, verifyM5baGasLimit)
			}, "BytecodeError(uint256,uint256)", tc.kind, uint64(tc.pc))
		})
	}
}

func TestVerifyM5baIllegalCategoryFormsUnderflowAndWordCapacity(t *testing.T) {
	base := verifyM5baRawFixture(t)
	categoryOne := []struct {
		name string
		code []byte
		want int32
	}{
		{"pop", []byte{0x04, 0x57, 0x05, 0xac}, 2},
		{"dup", []byte{0x05, 0x59, 0x60, 0xac}, 4},
		{"dup-x1", []byte{0x04, 0x05, 0x5a, 0x60, 0x60, 0xac}, 5},
		{"swap", []byte{0x04, 0x05, 0x5f, 0x60, 0xac}, 3},
	}
	for _, tc := range categoryOne {
		t.Run("category1-"+tc.name, func(t *testing.T) {
			classfile := verifyM5baRewriteCode(t, base, "padding", "()I", tc.code, 4, 1)
			verifyM5baAssertValue(t, func() (Result, error) { return Run(classfile, "padding", nil, verifyM5baGasLimit) }, tc.want)
		})
	}

	illegal := []struct {
		name string
		code []byte
		pc   int
	}{
		{"pop-long", []byte{0x0a, 0x57, 0x03, 0xac}, 1},
		{"dup-long", []byte{0x0a, 0x59, 0x58, 0x03, 0xac}, 1},
		{"dup-x1-long-top", []byte{0x04, 0x0a, 0x5a, 0x03, 0xac}, 2},
		{"dup-x1-long-below", []byte{0x0a, 0x04, 0x5a, 0x03, 0xac}, 2},
		{"swap-long-top", []byte{0x04, 0x0a, 0x5f, 0x03, 0xac}, 2},
		{"swap-long-below", []byte{0x0a, 0x04, 0x5f, 0x03, 0xac}, 2},
		{"pop2-cat1-atop-long", []byte{0x0a, 0x04, 0x58, 0x03, 0xac}, 2},
		{"dup2-cat1-atop-long", []byte{0x0a, 0x04, 0x5c, 0x03, 0xac}, 2},
		{"dup-x2-long-on-top", []byte{0x04, 0x0a, 0x5b, 0x03, 0xac}, 2},
		{"dup2-x1-long-below-cat1", []byte{0x0a, 0x04, 0x5d, 0x03, 0xac}, 2},
		// bottom->top [long,int] has an invalid one-value category-1 top group;
		// it is a category-form error, not an operand-word underflow.
		{"dup2-x2-long-cat1", []byte{0x0a, 0x04, 0x5e, 0x03, 0xac}, 2},
		{"dup2-x2-no-form", []byte{0x0a, 0x04, 0x0a, 0x5e, 0x03, 0xac}, 3},
	}
	for _, tc := range illegal {
		t.Run(tc.name, func(t *testing.T) {
			bad := verifyM5baRewriteCode(t, base, "padding", "()I", tc.code, 8, 1)
			verifyM5baAssertError(t, func() (Result, error) { return Run(bad, "padding", nil, verifyM5baGasLimit) },
				"BytecodeError(uint256,uint256)", 14, uint64(tc.pc))
		})
	}

	underflow := []struct {
		name string
		code []byte
		pc   int
	}{
		{"pop2-one-cat1", []byte{0x04, 0x58, 0x03, 0xac}, 1},
		{"dup-x2-two-cat1", []byte{0x04, 0x05, 0x5b, 0x03, 0xac}, 2},
		{"dup2-empty", []byte{0x5c, 0x03, 0xac}, 0},
		{"dup2-x1-one-long", []byte{0x0a, 0x5d, 0x03, 0xac}, 1},
		{"dup2-x2-one-long", []byte{0x0a, 0x5e, 0x03, 0xac}, 1},
		{"dup2-x2-two-cat1", []byte{0x04, 0x05, 0x5e, 0x03, 0xac}, 2},
	}
	for _, tc := range underflow {
		t.Run(tc.name, func(t *testing.T) {
			bad := verifyM5baRewriteCode(t, base, "padding", "()I", tc.code, 8, 1)
			verifyM5baAssertError(t, func() (Result, error) { return Run(bad, "padding", nil, verifyM5baGasLimit) },
				"BytecodeError(uint256,uint256)", 3, uint64(tc.pc))
		})
	}

	capacity := []struct {
		name     string
		code     []byte
		maxStack uint16
		pc       int
	}{
		{"dup", []byte{0x04, 0x59, 0x60, 0xac}, 1, 1},
		{"dup-x1", []byte{0x04, 0x05, 0x5a, 0x60, 0x60, 0xac}, 2, 2},
		{"dup-x2", []byte{0x0a, 0x04, 0x5b, 0x57, 0x88, 0x60, 0xac}, 3, 2},
		{"dup2-long", []byte{0x0a, 0x5c, 0x61, 0x88, 0xac}, 2, 1},
		{"dup2-two-cat1", []byte{0x04, 0x05, 0x5c, 0x58, 0x60, 0xac}, 2, 2},
		{"dup2-x1", []byte{0x04, 0x0a, 0x5d, 0x58, 0x57, 0x88, 0xac}, 3, 2},
		{"dup2-x2", []byte{0x0a, 0x09, 0x5e, 0x58, 0x58, 0x03, 0xac}, 4, 2},
	}
	for _, tc := range capacity {
		t.Run(tc.name, func(t *testing.T) {
			bad := verifyM5baRewriteCode(t, base, "padding", "()I", tc.code, tc.maxStack, 1)
			verifyM5baAssertError(t, func() (Result, error) { return Run(bad, "padding", nil, verifyM5baGasLimit) },
				"BytecodeError(uint256,uint256)", 9, uint64(tc.pc))
		})
	}

	full := bytes.Repeat([]byte{0x0a}, 512)
	full = append(full, bytes.Repeat([]byte{0x58}, 512)...)
	full = append(full, 0x03, 0xac)
	fullClass := verifyM5baRewriteCode(t, base, "padding", "()I", full, 1024, 1024)
	verifyM5baJava8Outcome(t, [][]byte{verifyM5baMajor49(fullClass)}, "M5baRaw", "padding", nil, "value=0")
	verifyM5baAssertValue(t, func() (Result, error) { return Run(fullClass, "padding", nil, verifyM5baCapacityGasLimit) }, 0)

	overflow := append(bytes.Repeat([]byte{0x0a}, 513), 0x03, 0xac)
	overflowClass := verifyM5baRewriteCode(t, base, "padding", "()I", overflow, 1024, 1)
	verifyM5baAssertError(t, func() (Result, error) { return Run(overflowClass, "padding", nil, verifyM5baCapacityGasLimit) },
		"BytecodeError(uint256,uint256)", 9, 512)

	tooManyLocals := verifyM5baRewriteCode(t, base, "padding", "()I", []byte{0x03, 0xac}, 1, 1025)
	verifyM5baAssertError(t, func() (Result, error) { return Run(tooManyLocals, "padding", nil, verifyM5baGasLimit) },
		"BytecodeError(uint256,uint256)", 10, 0)
}

func TestVerifyM5baLongCallFailuresReturnsAndPrefixCapacity(t *testing.T) {
	classfile := verifyM5baCompile(t, map[string]string{
		"CallShapeJ.java": `public final class CallShapeJ {
			static long j(long x){long copy=x;return copy;} static long noarg(){return 1L;} static int i(){return 3;}
			public static int call(){return (int)j(1L);}
			public static int padding(){int x=0;` + strings.Repeat("x=x+1;", 80) + `return x;}
		}`,
	}, "CallShapeJ")["CallShapeJ"]
	c := parseStaticsClass(t, classfile)
	callMethod := c.namedMethod(t, "call")
	callPC := verifyM5baMemberPC(t, c, callMethod, 0xb8, 10, "j", "(J)J")
	callRef := binary.BigEndian.Uint16(callMethod.code[callPC+1:])
	// A no-argument long-return call can grow a preserved caller prefix by two
	// words; compile a separate canonical Methodref for that capacity probe.
	withNoargCall := verifyM5baCompile(t, map[string]string{
		"CallNoargJ.java": `public final class CallNoargJ { static long noarg(){return 1L;} public static int call(){return (int)noarg();} public static int padding(){int x=0;` + strings.Repeat("x=x+1;", 80) + `return x;} }`,
	}, "CallNoargJ")["CallNoargJ"]
	noargClass := parseStaticsClass(t, withNoargCall)
	noargCallMethod := noargClass.namedMethod(t, "call")
	noargCallPC := verifyM5baMemberPC(t, noargClass, noargCallMethod, 0xb8, 10, "noarg", "()J")
	noargRef := binary.BigEndian.Uint16(noargCallMethod.code[noargCallPC+1:])

	for _, tc := range []struct {
		name string
		code []byte
		kind uint64
		pc   int
	}{
		{"underflow", []byte{0xb8, byte(callRef >> 8), byte(callRef), 0x88, 0xac}, 3, 0},
		{"int-instead-of-long", []byte{0x04, 0xb8, byte(callRef >> 8), byte(callRef), 0x88, 0xac}, 14, 1},
	} {
		bad := verifyM5baRewriteCode(t, classfile, "padding", "()I", tc.code, 4, 1)
		verifyM5baAssertError(t, func() (Result, error) { return Run(bad, "padding", nil, verifyM5baGasLimit) },
			"BytecodeError(uint256,uint256)", tc.kind, uint64(tc.pc))
	}

	prefix := []byte{0x04, 0xb8, byte(noargRef >> 8), byte(noargRef), 0x58, 0xac}
	badCapacity := verifyM5baRewriteCode(t, withNoargCall, "padding", "()I", prefix, 1, 1)
	verifyM5baAssertError(t, func() (Result, error) { return Run(badCapacity, "padding", nil, verifyM5baGasLimit) },
		"BytecodeError(uint256,uint256)", 9, 1)

	badLocals := verifyM5baMutate(t, classfile, func(raw []byte, c staticsClass) {
		m := c.method(t, "j", "(J)J")
		start := verifyM5baCodeStart(t, raw, m)
		binary.BigEndian.PutUint16(raw[start-6:], 1)
	})
	verifyM5baAssertError(t, func() (Result, error) { return Run(badLocals, "call", nil, verifyM5baGasLimit) },
		"CallError(uint256,uint256)", 4, uint64(callPC))

	for _, tc := range []struct {
		name, method, descriptor string
		code                     []byte
		codeKind                 uint64
	}{
		{"long-return-half", "j", "(J)J", []byte{0x04, 0xad}, 14},
		{"long-return-extra-prefix", "j", "(J)J", []byte{0x04, 0x0a, 0xad}, 4},
	} {
		bad := verifyM5baRewriteCode(t, classfile, tc.method, tc.descriptor, tc.code, 4, 2)
		pc := verifyM5baInstructionPC(t, tc.code, 0xad, 0)
		verifyM5baAssertError(t, func() (Result, error) { return Run(bad, "call", nil, verifyM5baGasLimit) },
			"BytecodeError(uint256,uint256)", tc.codeKind, uint64(pc))
	}
	badI := verifyM5baReplaceOpcode(t, classfile, "i", "()I", 0xac, 0xad, 1)
	returnPC := verifyM5baInstructionPC(t, parseStaticsClass(t, badI).method(t, "i", "()I").code, 0xad, 0)
	verifyM5baAssertError(t, func() (Result, error) { return Run(badI, "i", nil, verifyM5baGasLimit) },
		"CallError(uint256,uint256)", 5, uint64(returnPC))
}

func TestVerifyM5baLongFieldsConstantValueCachesFinalAccessAndInitialization(t *testing.T) {
	classes := verifyM5baCompile(t, map[string]string{
		"fieldsj/Base.java":      `package fieldsj; public class Base { public long hidden=0x100000002L; }`,
		"fieldsj/Child.java":     `package fieldsj; public final class Child extends Base { public long hidden=0x300000004L; public final long fin; Child(long x){fin=x;} }`,
		"fieldsj/Constants.java": `package fieldsj; public interface Constants { long V=0x5566778811223344L; }`,
		"fieldsj/State.java": `package fieldsj; public final class State {
			static long count; static long value=init(); static long init(){count++;return 0x123456789abcdef0L;}
			static long cached(long x){value=x;return value+value;}
		}`,
		"fieldsj/Root.java": `package fieldsj; public final class Root {
			static int fold(long x){return (int)(x^(x>>>32));}
			public static int fields(int x){Child c=new Child(((long)x<<40)+9);c.hidden=((long)x<<36)+7;
				return fold(((Base)c).hidden)+fold(c.hidden)+fold(c.fin)+fold(Constants.V);}
			public static int statics(int x){long prefix=0x400000005L;return fold(prefix+State.value)+fold(State.cached(((long)x<<41)+11))+fold(State.count);}
		}`,
	}, "fieldsj/Base", "fieldsj/Child", "fieldsj/Constants", "fieldsj/State", "fieldsj/Root")
	bundle := verifyM5baBundle(classes)
	for _, tc := range []struct {
		method string
		arg    int32
	}{
		{"fields", -17}, {"fields", 29}, {"statics", -7}, {"statics", 19},
	} {
		want := verifyM5baJava8Int(t, bundle, "fieldsj.Root", tc.method, []int32{tc.arg})
		verifyM5baAssertValue(t, func() (Result, error) {
			return RunClasses(bundle, "fieldsj/Root", tc.method, []int32{tc.arg}, verifyM5baGasLimit)
		}, want)
	}
	// Every VM invocation starts with fresh long statics and resolution caches.
	want := verifyM5baJava8Int(t, bundle, "fieldsj.Root", "statics", []int32{19})
	verifyM5baAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "fieldsj/Root", "statics", []int32{19}, verifyM5baGasLimit)
	}, want)

	oldCV := verifyM5baCompile(t, map[string]string{
		"binarycv/Holder.java": `package binarycv; public final class Holder { public static long V; }`,
		"binarycv/Root.java":   `package binarycv; public final class Root { public static int run(){long x=Holder.V;return (int)(x^(x>>>32));} }`,
	}, "binarycv/Holder", "binarycv/Root")
	freshCV := verifyM5baCompile(t, map[string]string{
		"binarycv/Holder.java": `package binarycv; public final class Holder { public static final long V=0x123456789abcdef0L; }`,
	}, "binarycv/Holder")
	cvBundle := [][]byte{freshCV["binarycv/Holder"], oldCV["binarycv/Root"]}
	verifyM5baJava8Outcome(t, cvBundle, "binarycv.Root", "run", nil, "value=-2004318072")
	verifyM5baAssertValue(t, func() (Result, error) {
		return RunClasses(cvBundle, "binarycv/Root", "run", nil, verifyM5baGasLimit)
	}, -2004318072)

	cv := verifyM5baCompile(t, map[string]string{
		"LongCV.java": `public final class LongCV {
			static final int I=7; static final double D=1.5; static final long V=0x123456789abcdef0L;
			static final long W; static { W=9L; }
			public static int run(){return (int)(V^(V>>>32));}
			public static int padding(){int x=0;` + strings.Repeat("x=x+1;", 40) + `return x;}
		}`,
	}, "LongCV")["LongCV"]
	parsedCV := parseStaticsClass(t, cv)
	vAttr := parsedCV.field(t, "V", "J").attribute(t, "ConstantValue")
	if vAttr == nil || vAttr.length != 2 {
		t.Fatal("long field lacks canonical ConstantValue")
	}
	vIndex := binary.BigEndian.Uint16(cv[vAttr.dataOffset:])
	if parsedCV.entry(t, vIndex).tag != 5 {
		t.Fatalf("long ConstantValue tag=%d want 5", parsedCV.entry(t, vIndex).tag)
	}
	verifyM5baAssertValue(t, func() (Result, error) { return Run(cv, "run", nil, verifyM5baGasLimit) }, -2004318072)
	for _, tc := range []struct {
		name  string
		index uint16
	}{
		{"integer", verifyM5baFieldConstantIndex(t, parsedCV, "I", "I")},
		{"double", verifyM5baFieldConstantIndex(t, parsedCV, "D", "D")},
	} {
		bad := verifyM5baMutate(t, cv, func(raw []byte, c staticsClass) {
			a := c.field(t, "V", "J").attribute(t, "ConstantValue")
			binary.BigEndian.PutUint16(raw[a.dataOffset:], tc.index)
		})
		verifyM5baAssertError(t, func() (Result, error) { return Run(bad, "run", nil, verifyM5baGasLimit) },
			"FieldError(uint256,uint256)", 5, uint64(parsedCV.field(t, "V", "J").index))
	}

	clinit := parsedCV.method(t, "<clinit>", "()V")
	putPC := verifyM5baFieldPC(t, parsedCV, clinit, 0xb3, "W", "J")
	putRef := binary.BigEndian.Uint16(clinit.code[putPC+1:])
	illegalFinalCode := []byte{0x0a, 0xb3, byte(putRef >> 8), byte(putRef), 0x03, 0xac}
	illegalFinal := verifyM5baRewriteCode(t, cv, "padding", "()I", illegalFinalCode, 2, 0)
	verifyM5baAssertError(t, func() (Result, error) { return Run(illegalFinal, "padding", nil, verifyM5baGasLimit) },
		"FieldError(uint256,uint256)", 4, 1)

	instance := verifyM5baCompile(t, map[string]string{
		"InstanceLongCV.java": `public final class InstanceLongCV {
			final long ignored=0x123456789abcdef0L; long mutable;
			public static int run(){InstanceLongCV x=new InstanceLongCV();return (int)x.mutable;}
		}`,
	}, "InstanceLongCV")["InstanceLongCV"]
	instanceParsed := parseStaticsClass(t, instance)
	ignoredIndex := verifyM5baFieldConstantIndex(t, instanceParsed, "ignored", "J")
	if instanceParsed.entry(t, ignoredIndex).tag != 5 {
		t.Fatalf("instance long ConstantValue tag=%d want 5", instanceParsed.entry(t, ignoredIndex).tag)
	}
	// Remove javac's constructor assignment, then retarget the ordinary mutable-J
	// getfield to ignored. Reading ignored in Java source would inline the literal
	// and would not prove that an instance ConstantValue is ignored by the heap.
	instance = verifyM5baMutate(t, instance, func(_ []byte, c staticsClass) {
		ctor := c.method(t, "<init>", "()V")
		putPC := verifyM5baFieldPC(t, c, ctor, 0xb5, "ignored", "J")
		ignoredRef := binary.BigEndian.Uint16(ctor.code[putPC+1:])
		ldc := verifyM5baPreviousInstruction(t, ctor.code, putPC)
		aload := verifyM5baPreviousInstruction(t, ctor.code, ldc)
		if ctor.code[ldc] != 0x14 || ctor.code[aload] != 0x2a {
			t.Fatalf("unexpected instance ConstantValue assignment %x", ctor.code)
		}
		for i := aload; i < putPC+3; i++ {
			ctor.code[i] = 0
		}
		run := c.method(t, "run", "()I")
		getPC := verifyM5baFieldPC(t, c, run, 0xb4, "mutable", "J")
		binary.BigEndian.PutUint16(run.code[getPC+1:], ignoredRef)
	})
	mutatedInstance := verifyM5baMajor49(instance)
	verifyM5baFieldPC(t, parseStaticsClass(t, mutatedInstance),
		parseStaticsClass(t, mutatedInstance).method(t, "run", "()I"), 0xb4, "ignored", "J")
	verifyM5baJava8Outcome(t, [][]byte{mutatedInstance}, "InstanceLongCV", "run", nil, "value=0")
	verifyM5baAssertValue(t, func() (Result, error) { return Run(mutatedInstance, "run", nil, verifyM5baGasLimit) }, 0)

	privateOwner := verifyM5baCompile(t, map[string]string{
		"accessj/Owner.java": `package accessj; public final class Owner { public static long value=9L; }`,
		"accessj/Root.java":  `package accessj; public final class Root { public static int run(){return (int)Owner.value;} }`,
	}, "accessj/Owner", "accessj/Root")
	owner := verifyM5baMutate(t, privateOwner["accessj/Owner"], func(raw []byte, c staticsClass) {
		f := c.field(t, "value", "J")
		binary.BigEndian.PutUint16(raw[f.accessOffset:], (f.access&^uint16(0x0001))|0x0002)
	})
	accessPC := verifyM5baFieldPC(t, parseStaticsClass(t, privateOwner["accessj/Root"]),
		parseStaticsClass(t, privateOwner["accessj/Root"]).namedMethod(t, "run"), 0xb2, "value", "J")
	verifyM5baAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{owner, privateOwner["accessj/Root"]}, "accessj/Root", "run", nil, verifyM5baGasLimit)
	}, "FieldError(uint256,uint256)", 4, uint64(accessPC))

	initFailure := verifyM5baCompile(t, map[string]string{
		"InitLongFailure.java": `public final class InitLongFailure {
			static int zero(){return 0;} static long value=7L/zero(); public static int run(){return (int)value;}
		}`,
	}, "InitLongFailure")["InitLongFailure"]
	verifyM5baJava8Outcome(t, [][]byte{initFailure}, "InitLongFailure", "run", nil,
		"exception=java.lang.ExceptionInInitializerError")
	verifyM5baAssertException(t, func() (Result, error) { return Run(initFailure, "run", nil, verifyM5baGasLimit) },
		"java.lang.ExceptionInInitializerError", 3)
}

func TestVerifyM5baLongFieldIsOneObjectQuotaSlotAndDeferredIEEEArrays(t *testing.T) {
	for _, count := range []int{1024, 1025} {
		t.Run(strconv.Itoa(count), func(t *testing.T) {
			var source strings.Builder
			source.WriteString("public final class LongFieldQuota {")
			for i := 0; i < count; i++ {
				fmt.Fprintf(&source, "long f%d;", i)
			}
			source.WriteString("public static int run(){return new LongFieldQuota()==null?0:1;}}")
			classfile := verifyM5baCompile(t, map[string]string{"LongFieldQuota.java": source.String()}, "LongFieldQuota")["LongFieldQuota"]
			if count == 1024 {
				verifyM5baAssertValue(t, func() (Result, error) { return Run(classfile, "run", nil, verifyM5baCapacityGasLimit) }, 1)
			} else {
				verifyM5baAssertException(t, func() (Result, error) { return Run(classfile, "run", nil, verifyM5baCapacityGasLimit) },
					"java.lang.OutOfMemoryError", 7)
			}
		})
	}

	base := verifyM5baRawFixture(t)
	longArray := verifyM5baRewriteCode(t, base, "padding", "()I", []byte{0x04, 0xbc, 11, 0xbe, 0xac}, 2, 1)
	longOracle := verifyM5baCompile(t, map[string]string{
		"M5baLongArrayOracle.java": `public final class M5baLongArrayOracle { public static int run(){return new long[1].length;} }`,
	}, "M5baLongArrayOracle")["M5baLongArrayOracle"]
	oracleCode := parseStaticsClass(t, longOracle).namedMethod(t, "run").code
	oraclePC := verifyM5baInstructionPC(t, oracleCode, 0xbc, 0)
	if oracleCode[oraclePC+1] != 11 {
		t.Fatalf("javac long[] atype=%d want 11", oracleCode[oraclePC+1])
	}
	verifyM5baJava8Outcome(t, [][]byte{longOracle}, "M5baLongArrayOracle", "run", nil, "value=1")
	verifyM5baAssertValue(t, func() (Result, error) { return Run(longArray, "padding", nil, verifyM5baGasLimit) }, 1)

	guards := verifyM5baCompile(t, map[string]string{
		"DeferredJFD.java": `public final class DeferredJFD {
			public static int longs(){Object x=new int[0];return x instanceof long[]?1:0;}
			public static int floats(){Object x=new int[0];return x instanceof float[]?1:0;}
			public static int doubles(){Object x=new int[0];return x instanceof double[]?1:0;}
		}`,
	}, "DeferredJFD")["DeferredJFD"]
	verifyM5baJava8Outcome(t, [][]byte{guards}, "DeferredJFD", "longs", nil, "value=0")
	verifyM5baAssertValue(t, func() (Result, error) { return Run(guards, "longs", nil, verifyM5baGasLimit) }, 0)
	for _, method := range []string{"floats", "doubles"} {
		verifyM5baJava8Outcome(t, [][]byte{guards}, "DeferredJFD", method, nil, "value=0")
		verifyM5baAssertValue(t, func() (Result, error) { return Run(guards, method, nil, verifyM5baGasLimit) }, 0)
	}
}

func TestVerifyM5baPredecodeUsesInstructionBoundariesNotOperandBytes(t *testing.T) {
	base := verifyM5baCompile(t, map[string]string{
		"BoundaryJ.java": `public final class BoundaryJ {
			static final long V=0x1122334455667788L;
			public static int padding(){int x=0;` + strings.Repeat("x=x+1;", 80) + `return x;}
		}`,
	}, "BoundaryJ")["BoundaryJ"]
	index := verifyM5baCPIndices(parseStaticsClass(t, base), 5)[0]
	// ifeq at PC 1 targets PC 6, the second operand byte of ldc2_w at PC 4.
	// A byte scan could mistake that operand for an instruction; predecode must not.
	code := []byte{0x03, 0x99, 0, 5, 0x14, byte(index >> 8), byte(index), 0x58, 0x03, 0xac}
	if verifyM5baInstructionPC(t, code, 0x14, 0) != 4 {
		t.Fatal("test plan lost ldc2_w boundary")
	}
	bad := verifyM5baRewriteCode(t, base, "padding", "()I", code, 2, 1)
	verifyM5baAssertError(t, func() (Result, error) { return Run(bad, "padding", nil, verifyM5baGasLimit) },
		"BytecodeError(uint256,uint256)", 12, 1)
}

// --- M5b-a verifier-only helpers ---

func verifyM5baCompile(t *testing.T, sources map[string]string, internalNames ...string) map[string][]byte {
	t.Helper()
	dir := t.TempDir()
	rels := make([]string, 0, len(sources))
	for rel := range sources {
		rels = append(rels, rel)
	}
	sort.Strings(rels)
	argv := []string{"-J-Xmx96m", "--release", "8", "-d", dir}
	for _, rel := range rels {
		path := filepath.Join(dir, filepath.FromSlash(rel))
		if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(sources[rel]), 0600); err != nil {
			t.Fatal(err)
		}
		argv = append(argv, path)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 25*time.Second)
	defer cancel()
	if output, err := exec.CommandContext(ctx, "javac", argv...).CombinedOutput(); err != nil {
		t.Fatalf("bounded trusted javac --release 8 failed: %v\n%s", err, output)
	}
	out := make(map[string][]byte, len(internalNames))
	for _, name := range internalNames {
		data, err := os.ReadFile(filepath.Join(dir, filepath.FromSlash(name+".class")))
		if err != nil {
			t.Fatalf("read %s: %v", name, err)
		}
		out[name] = data
	}
	return out
}

func verifyM5baBundle(classes map[string][]byte) [][]byte {
	names := make([]string, 0, len(classes))
	for name := range classes {
		names = append(names, name)
	}
	sort.Strings(names)
	out := make([][]byte, len(names))
	for i, name := range names {
		out[i] = classes[name]
	}
	return out
}

func verifyM5baReplaceClass(classes map[string][]byte, name string, replacement []byte) map[string][]byte {
	out := make(map[string][]byte, len(classes))
	for key, value := range classes {
		out[key] = value
	}
	out[name] = replacement
	return out
}

func verifyM5baRawFixture(t *testing.T) []byte {
	t.Helper()
	return verifyM5baCompile(t, map[string]string{
		"M5baRaw.java": `public final class M5baRaw { public static int padding(){int x=0;` + strings.Repeat("x=x+1;", 400) + `return x;} }`,
	}, "M5baRaw")["M5baRaw"]
}

func verifyM5baMutate(t *testing.T, original []byte, edit func([]byte, staticsClass)) []byte {
	t.Helper()
	out := append([]byte(nil), original...)
	edit(out, parseStaticsClass(t, out))
	return out
}

func verifyM5baCodeStart(t *testing.T, raw []byte, method staticsMethod) int {
	t.Helper()
	if len(method.code) == 0 {
		t.Fatalf("%s%s has no Code", method.name, method.descriptor)
	}
	for i := range raw {
		if &raw[i] == &method.code[0] {
			if i < 8 {
				t.Fatalf("invalid Code start %d", i)
			}
			return i
		}
	}
	t.Fatalf("cannot locate Code for %s%s", method.name, method.descriptor)
	return -1
}

func verifyM5baRewriteCode(t *testing.T, original []byte, name, descriptor string, code []byte, maxStack, maxLocals uint16) []byte {
	t.Helper()
	out := append([]byte(nil), original...)
	method := parseStaticsClass(t, out).method(t, name, descriptor)
	if len(code) > len(method.code) {
		t.Fatalf("replacement %s%s has %d bytes, Code has %d", name, descriptor, len(code), len(method.code))
	}
	start := verifyM5baCodeStart(t, out, method)
	binary.BigEndian.PutUint16(out[start-8:], maxStack)
	binary.BigEndian.PutUint16(out[start-6:], maxLocals)
	for i := range method.code {
		method.code[i] = 0
	}
	copy(method.code, code)
	return out
}

func verifyM5baRewriteAtEnd(t *testing.T, original []byte, name, descriptor string, ending []byte) []byte {
	t.Helper()
	out := verifyM5baRewriteCode(t, original, name, descriptor, nil, 16, 16)
	method := parseStaticsClass(t, out).method(t, name, descriptor)
	copy(method.code[len(method.code)-len(ending):], ending)
	return out
}

func verifyM5baReplaceOpcode(t *testing.T, original []byte, name, descriptor string, from, to byte, want int) []byte {
	t.Helper()
	return verifyM5baMutate(t, original, func(_ []byte, c staticsClass) {
		code := c.method(t, name, descriptor).code
		count := 0
		for pc := 0; pc < len(code); pc += verifyM5baInstructionWidth(t, code, pc) {
			if code[pc] == from {
				code[pc] = to
				count++
			}
		}
		if count != want {
			t.Fatalf("%s%s replaced %d boundary-aligned 0x%02x, want %d", name, descriptor, count, from, want)
		}
	})
}

func verifyM5baCPIndices(c staticsClass, tag byte) []uint16 {
	out := []uint16{}
	for i := 1; i < c.cpCount; i++ {
		if c.entries[i].tag == tag {
			out = append(out, uint16(i))
		}
	}
	return out
}

func verifyM5baFieldConstantIndex(t *testing.T, c staticsClass, name, descriptor string) uint16 {
	t.Helper()
	a := c.field(t, name, descriptor).attribute(t, "ConstantValue")
	if a == nil || a.length != 2 {
		t.Fatalf("%s:%s lacks ConstantValue", name, descriptor)
	}
	return binary.BigEndian.Uint16(c.data[a.dataOffset:])
}

func verifyM5baFieldPC(t *testing.T, c staticsClass, m staticsMethod, opcode byte, name, descriptor string) int {
	t.Helper()
	for pc := 0; pc < len(m.code); pc += verifyM5baInstructionWidth(t, m.code, pc) {
		if m.code[pc] != opcode || pc+2 >= len(m.code) {
			continue
		}
		ref := binary.BigEndian.Uint16(m.code[pc+1:])
		if ref == 0 || int(ref) >= c.cpCount || c.entries[ref].tag != 9 {
			continue
		}
		e := c.entry(t, ref)
		nat := c.entry(t, c.u2(t, e.offset+3))
		if nat.tag == 12 && c.utf8[c.u2(t, nat.offset+1)] == name && c.utf8[c.u2(t, nat.offset+3)] == descriptor {
			return pc
		}
	}
	t.Fatalf("%s%s lacks field 0x%02x %s:%s at an instruction boundary", m.name, m.descriptor, opcode, name, descriptor)
	return -1
}

func verifyM5baMemberPC(t *testing.T, c staticsClass, m staticsMethod, opcode, tag byte, name, descriptor string) int {
	t.Helper()
	for pc := 0; pc < len(m.code); pc += verifyM5baInstructionWidth(t, m.code, pc) {
		if m.code[pc] != opcode || pc+2 >= len(m.code) {
			continue
		}
		ref := binary.BigEndian.Uint16(m.code[pc+1:])
		if ref == 0 || int(ref) >= c.cpCount || c.entries[ref].tag != tag {
			continue
		}
		e := c.entry(t, ref)
		nat := c.entry(t, c.u2(t, e.offset+3))
		if nat.tag == 12 && c.utf8[c.u2(t, nat.offset+1)] == name && c.utf8[c.u2(t, nat.offset+3)] == descriptor {
			return pc
		}
	}
	t.Fatalf("%s%s lacks call 0x%02x %s%s at an instruction boundary", m.name, m.descriptor, opcode, name, descriptor)
	return -1
}

func verifyM5baPreviousInstruction(t *testing.T, code []byte, target int) int {
	t.Helper()
	previous := -1
	for pc := 0; pc < len(code); pc += verifyM5baInstructionWidth(t, code, pc) {
		if pc == target {
			if previous < 0 {
				t.Fatalf("instruction at pc %d has no predecessor", target)
			}
			return previous
		}
		if pc > target {
			break
		}
		previous = pc
	}
	t.Fatalf("pc %d is not an instruction boundary in %x", target, code)
	return -1
}

func verifyM5baInstructionPC(t *testing.T, code []byte, opcode byte, occurrence int) int {
	t.Helper()
	seen := 0
	for pc := 0; pc < len(code); pc += verifyM5baInstructionWidth(t, code, pc) {
		if code[pc] == opcode {
			if seen == occurrence {
				return pc
			}
			seen++
		}
	}
	t.Fatalf("opcode 0x%02x occurrence %d missing at boundaries in %x", opcode, occurrence, code)
	return -1
}

func verifyM5baInstructionWidth(t *testing.T, code []byte, pc int) int {
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
	case 0xaa, 0xab:
		t.Fatalf("boundary walker deliberately rejects switch at pc %d", pc)
	}
	if pc+width > len(code) {
		t.Fatalf("truncated opcode 0x%02x at pc %d", code[pc], pc)
	}
	return width
}

func verifyM5baMajor49(classfile []byte) []byte {
	out := append([]byte(nil), classfile...)
	binary.BigEndian.PutUint16(out[6:8], 49)
	return out
}

func verifyM5baJava8(t *testing.T) string {
	t.Helper()
	path := os.Getenv("JAVA_EVM_JAVA8")
	if path == "" {
		path = "/usr/lib/jvm/java-8-openjdk/bin/java"
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	output, err := exec.CommandContext(ctx, path, "-version").CombinedOutput()
	if err != nil {
		t.Fatalf("M5b-a valid raw-class oracle requires Java 8; JAVA_EVM_JAVA8=%q: %v\n%s", path, err, output)
	}
	if !regexp.MustCompile(`(?m)version "1\.8\.`).Match(output) {
		t.Fatalf("M5b-a oracle requires Java major 8; JAVA_EVM_JAVA8=%q reported:\n%s", path, output)
	}
	return path
}

func verifyM5baJava8Outcome(t *testing.T, bundle [][]byte, mainClass, method string, args []int32, want string) {
	t.Helper()
	dir := t.TempDir()
	oracle := `public final class VerifyM5baOracle {
		public static void main(String[] a) throws Exception { try {
			Class<?> c=Class.forName(a[0]);Class<?>[] p=new Class<?>[a.length-2];Object[] v=new Object[a.length-2];
			for(int i=0;i<p.length;i++){p[i]=Integer.TYPE;v[i]=Integer.valueOf(a[i+2]);}
			Object x=c.getMethod(a[1],p).invoke(null,v);System.out.print("value="+x);
		} catch(java.lang.reflect.InvocationTargetException x){System.out.print("exception="+x.getCause().getClass().getName());}
		catch(Throwable x){System.out.print("exception="+x.getClass().getName());}}
	}`
	path := filepath.Join(dir, "VerifyM5baOracle.java")
	if err := os.WriteFile(path, []byte(oracle), 0600); err != nil {
		t.Fatal(err)
	}
	ctxCompile, cancelCompile := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancelCompile()
	if output, err := exec.CommandContext(ctxCompile, "javac", "-J-Xmx64m", "--release", "8", "-d", dir, path).CombinedOutput(); err != nil {
		t.Fatalf("compile trusted M5b-a oracle: %v\n%s", err, output)
	}
	for _, classfile := range bundle {
		name := verifyM5baClassName(t, classfile)
		classPath := filepath.Join(dir, filepath.FromSlash(name+".class"))
		if err := os.MkdirAll(filepath.Dir(classPath), 0700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(classPath, classfile, 0600); err != nil {
			t.Fatal(err)
		}
	}
	argv := []string{"-Xmx64m", "-cp", dir, "VerifyM5baOracle", mainClass, method}
	for _, arg := range args {
		argv = append(argv, strconv.FormatInt(int64(arg), 10))
	}
	ctxRun, cancelRun := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancelRun()
	output, err := exec.CommandContext(ctxRun, verifyM5baJava8(t), argv...).CombinedOutput()
	if err != nil {
		t.Fatalf("bounded Java8 M5b-a oracle failed: %v\n%s", err, output)
	}
	if got := strings.TrimSpace(string(output)); got != want {
		t.Fatalf("Java8 %s.%s outcome=%q want %q", mainClass, method, got, want)
	}
}

func verifyM5baJava8Int(t *testing.T, bundle [][]byte, mainClass, method string, args []int32) int32 {
	t.Helper()
	dir := t.TempDir()
	// Reuse the exact oracle helper but obtain its result with one bounded direct
	// run so expected arithmetic is never reproduced in Go or host production code.
	oracle := `public final class VerifyM5baValue { public static void main(String[] a)throws Exception{
		Class<?> c=Class.forName(a[0]);Class<?>[] p=new Class<?>[a.length-2];Object[] v=new Object[p.length];
		for(int i=0;i<p.length;i++){p[i]=Integer.TYPE;v[i]=Integer.valueOf(a[i+2]);}
		System.out.print(c.getMethod(a[1],p).invoke(null,v));}}`
	path := filepath.Join(dir, "VerifyM5baValue.java")
	if err := os.WriteFile(path, []byte(oracle), 0600); err != nil {
		t.Fatal(err)
	}
	ctxCompile, cancelCompile := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancelCompile()
	if output, err := exec.CommandContext(ctxCompile, "javac", "-J-Xmx64m", "--release", "8", "-d", dir, path).CombinedOutput(); err != nil {
		t.Fatalf("compile trusted M5b-a value oracle: %v\n%s", err, output)
	}
	for _, classfile := range bundle {
		name := verifyM5baClassName(t, classfile)
		classPath := filepath.Join(dir, filepath.FromSlash(name+".class"))
		if err := os.MkdirAll(filepath.Dir(classPath), 0700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(classPath, classfile, 0600); err != nil {
			t.Fatal(err)
		}
	}
	argv := []string{"-Xmx64m", "-cp", dir, "VerifyM5baValue", mainClass, method}
	for _, arg := range args {
		argv = append(argv, strconv.FormatInt(int64(arg), 10))
	}
	ctxRun, cancelRun := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancelRun()
	output, err := exec.CommandContext(ctxRun, verifyM5baJava8(t), argv...).CombinedOutput()
	if err != nil {
		t.Fatalf("bounded Java8 M5b-a value oracle failed: %v\n%s", err, output)
	}
	value, err := strconv.ParseInt(strings.TrimSpace(string(output)), 10, 32)
	if err != nil {
		t.Fatalf("Java8 %s.%s non-int32 outcome %q: %v", mainClass, method, output, err)
	}
	return int32(value)
}

func verifyM5baClassName(t *testing.T, classfile []byte) string {
	t.Helper()
	c := parseStaticsClass(t, classfile)
	e := c.entry(t, c.thisClass)
	if e.tag != 7 {
		t.Fatalf("this_class tag=%d want Class", e.tag)
	}
	return c.utf8[c.u2(t, e.offset+1)]
}

func verifyM5baAssertValue(t *testing.T, run func() (Result, error), want int32) {
	t.Helper()
	result, err := run()
	if err != nil || result.ExceptionClass != "" || result.Value != want || result.GasUsed == 0 || len(result.RevertData) != 0 {
		t.Fatalf("result/error=%+v/%v want value %d", result, err, want)
	}
}

func verifyM5baAssertException(t *testing.T, run func() (Result, error), want string, kind byte) {
	t.Helper()
	result, err := run()
	selector := crypto.Keccak256([]byte("JavaException(uint256)"))[:4]
	if err != nil || result.ExceptionClass != want || result.GasUsed == 0 || len(result.RevertData) != 36 ||
		!bytes.Equal(result.RevertData[:4], selector) || !bytes.Equal(result.RevertData[4:35], make([]byte, 31)) || result.RevertData[35] != kind {
		t.Fatalf("result/error=%+v/%v data=%x want %s kind %d", result, err, result.RevertData, want, kind)
	}
}

func verifyM5baAssertError(t *testing.T, run func() (Result, error), signature string, code, location uint64) {
	t.Helper()
	result, err := run()
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error=%+v/%v want %s(%d,%d)", result, err, signature, code, location)
	}
	selector := crypto.Keccak256([]byte(signature))[:4]
	if result.ExceptionClass != "" || result.GasUsed == 0 || len(result.RevertData) != 68 || !bytes.Equal(result.RevertData[:4], selector) {
		t.Fatalf("result=%+v data=%x want exact %s", result, result.RevertData, signature)
	}
	if got := verifyM5baUint256(t, result.RevertData[4:36]); got != code {
		t.Fatalf("%s code=%d want %d (data=%x)", signature, got, code, result.RevertData)
	}
	if got := verifyM5baUint256(t, result.RevertData[36:]); got != location {
		t.Fatalf("%s location=%d want %d (data=%x)", signature, got, location, result.RevertData)
	}
}

func verifyM5baAssertMethodError(t *testing.T, run func() (Result, error), code uint64) {
	t.Helper()
	result, err := run()
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error=%+v/%v want MethodError(%d)", result, err, code)
	}
	selector := crypto.Keccak256([]byte("MethodError(uint256)"))[:4]
	if result.ExceptionClass != "" || result.GasUsed == 0 || len(result.RevertData) != 36 ||
		!bytes.Equal(result.RevertData[:4], selector) || verifyM5baUint256(t, result.RevertData[4:]) != code {
		t.Fatalf("result=%+v data=%x want exact MethodError(%d)", result, result.RevertData, code)
	}
}

func verifyM5baUint256(t *testing.T, word []byte) uint64 {
	t.Helper()
	if len(word) != 32 || !bytes.Equal(word[:24], make([]byte, 24)) {
		t.Fatalf("noncanonical uint256 %x", word)
	}
	return binary.BigEndian.Uint64(word[24:])
}
