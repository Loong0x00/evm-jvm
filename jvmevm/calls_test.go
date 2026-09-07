// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/crypto"
)

const callsSource = `
public class Calls {
    private static int add(int a, int b) { return a + b; }
    private static int twice(int a) { return a * 2; }
    private static int overload(int a) { return a + 100; }
    private static int overload(int a, int b) { return a * 10 + b; }
    private static int combine(int a, int b, int c) { return add(twice(a), overload(b, c)); }
    private static int zero() { return 9; }
    private static int returnedButDiscarded(int a) { return a + 1000; }
    private static void noResult(int a) { int x = a * 7; }
    private static int fact0(int n) { return n <= 1 ? 1 : n * fact0(n - 1); }
    private static int fib0(int n) { return n <= 1 ? n : fib0(n - 1) + fib0(n - 2); }
    private static int even0(int n) { return n == 0 ? 1 : odd0(n - 1); }
    private static int odd0(int n) { return n == 0 ? 0 : even0(n - 1); }
    private static int explode(int n) { return 100 / n; }
    private static int forever(int n) { return forever(n + 1); }

    public static int nested(int a, int b, int c) {
        int saved = a + 10;
        return 7 + combine(saved, b, c) + saved;
    }
    public static int overloaded(int a, int b) { return overload(a) + overload(a, b); }
    public static int zeroArg(int a) { return a + zero(); }
    public static int discard(int a) { returnedButDiscarded(a); noResult(a); return a + 3; }
    public static int factorial(int n) { return fact0(n); }
    public static int fibonacci(int n) { return fib0(n); }
    public static int mutual(int n) { return even0(n); }
    public static int calleeDivideZero(int n) { return explode(n); }
    public static int overflow(int n) { return forever(n); }
}`

func TestSameClassStaticCallsAndIndependentFrames(t *testing.T) {
	classfile := compileJava(t, "Calls", callsSource)
	cases := []struct {
		method string
		args   []int32
		want   int32
	}{
		{"nested", []int32{2, 3, 4}, 77},     // 7 + (2*(2+10) + (3*10+4)) + (2+10)
		{"nested", []int32{-20, -3, 8}, -45}, // prefix stack and caller local survive nested calls
		{"overloaded", []int32{4, 7}, 151},   // exact name+descriptor overload resolution
		{"zeroArg", []int32{33}, 42},         // zero-argument private helper
		{"discard", []int32{39}, 42},         // int pop followed by internal void return
		{"factorial", []int32{8}, 40320},     // direct recursion
		{"fibonacci", []int32{10}, 55},       // two recursive calls in one expression
		{"mutual", []int32{12}, 1},           // mutual recursion
		{"mutual", []int32{13}, 0},
	}
	for _, tc := range cases {
		t.Run(fmt.Sprintf("%s%v", tc.method, tc.args), func(t *testing.T) {
			result, err := Run(classfile, tc.method, tc.args, 50_000_000)
			if err != nil {
				t.Fatal(err)
			}
			if result.ExceptionClass != "" || result.Value != tc.want {
				t.Fatalf("result = %+v, want value %d", result, tc.want)
			}
			t.Logf("gas=%d", result.GasUsed)
		})
	}
}

func TestCalleeJavaOutcomesPropagateAndFrameCapIsDistinctFromOOG(t *testing.T) {
	classfile := compileJava(t, "Calls", callsSource)
	arithmetic, err := Run(classfile, "calleeDivideZero", []int32{0}, 10_000_000)
	if err != nil || arithmetic.ExceptionClass != "java.lang.ArithmeticException" {
		t.Fatalf("callee arithmetic result/error = %+v/%v", arithmetic, err)
	}
	overflow, err := Run(classfile, "overflow", []int32{0}, 50_000_000)
	if err != nil || overflow.ExceptionClass != "java.lang.StackOverflowError" {
		t.Fatalf("recursive overflow result/error = %+v/%v", overflow, err)
	}
	if len(overflow.RevertData) != 36 || overflow.RevertData[35] != 2 {
		t.Fatalf("overflow revert data = 0x%x, want exact JavaException kind 2", overflow.RevertData)
	}
	lowGas, err := Run(classfile, "overflow", []int32{0}, 1_000)
	if err == nil || !strings.Contains(err.Error(), "out of gas") {
		t.Fatalf("low-gas overflow result/error = %+v/%v, want EVM OOG", lowGas, err)
	}
	if lowGas.ExceptionClass != "" {
		t.Fatalf("low-gas execution fabricated Java outcome: %+v", lowGas)
	}
	t.Logf("frame-limit gas=%d", overflow.GasUsed)
}

func TestFrozenCallErrorsAndCallBytecodeErrors(t *testing.T) {
	original := compileJava(t, "CallErrors", `
public class CallErrors {
    private static int helper(int a, int b) { return a + b; }
    public static int root(int a, int b) { return helper(a, b); }
}`)
	parsed := parseCallTestClass(t, original)
	rootCode := parsed.code(t, "root")
	callPC := bytes.IndexByte(rootCode, 0xb8)
	if callPC < 0 || callPC+2 >= len(rootCode) {
		t.Fatalf("root bytecode = %x, want invokestatic", rootCode)
	}
	refIndex := binary.BigEndian.Uint16(rootCode[callPC+1 : callPC+3])
	if parsed.tags[refIndex] != 10 {
		t.Fatalf("call CP index %d tag = %d, want Methodref", refIndex, parsed.tags[refIndex])
	}
	natIndex := parsed.second[refIndex]
	codeUtf := parsed.utfIndex("Code")

	callCases := map[string]struct {
		code uint64
		edit func([]byte)
	}{
		"bad-methodref-tag": {1, func(class []byte) {
			class[parsed.cpOffsets[refIndex]] = 11 // InterfaceMethodref is explicitly rejected in M3a
		}},
		"bad-name-and-type-tag": {1, func(class []byte) {
			class[parsed.cpOffsets[natIndex]] = 10 // same-width tag, but not NameAndType
		}},
		"missing-exact-signature": {3, func(class []byte) {
			binary.BigEndian.PutUint16(class[parsed.cpOffsets[natIndex]+1:], codeUtf)
		}},
		"nonstatic-target": {4, func(class []byte) {
			off := parsed.methodAccess["helper"]
			flags := binary.BigEndian.Uint16(class[off:]) &^ 0x0008
			binary.BigEndian.PutUint16(class[off:], flags)
		}},
		"return-kind-mismatch": {5, func(class []byte) {
			off := parsed.codeOffsets["helper"] + parsed.codeLengths["helper"] - 1
			class[off] = 0xb1
		}},
	}
	for name, tc := range callCases {
		t.Run(name, func(t *testing.T) {
			classfile := append([]byte(nil), original...)
			tc.edit(classfile)
			result, err := Run(classfile, "root", []int32{20, 22}, 5_000_000)
			wantPC := uint64(callPC)
			if name == "return-kind-mismatch" {
				wantPC = uint64(parsed.codeLengths["helper"] - 1)
			}
			assertSolidityError(t, result, err, "CallError(uint256,uint256)", tc.code, wantPC)
		})
	}

	external := compileJava(t, "ExternalCall", `
public class ExternalCall { public static int root(int a) { return Math.abs(a); } }
`)
	externalParsed := parseCallTestClass(t, external)
	externalPC := bytes.IndexByte(externalParsed.code(t, "root"), 0xb8)
	result, err := Run(external, "root", []int32{-4}, 5_000_000)
	assertSolidityError(t, result, err, "CallError(uint256,uint256)", 2, uint64(externalPC))

	t.Run("operand-underflow-at-call", func(t *testing.T) {
		classfile := append([]byte(nil), original...)
		// javac emits iload_0, iload_1, invokestatic. Pop the first argument instead of
		// loading the second, leaving no arguments at the two-argument call site.
		if rootCode[0] != 0x1a || rootCode[1] != 0x1b {
			t.Fatalf("unexpected root prologue: %x", rootCode)
		}
		classfile[parsed.codeOffsets["root"]+1] = 0x57
		result, err := Run(classfile, "root", []int32{20, 22}, 5_000_000)
		assertSolidityError(t, result, err, "BytecodeError(uint256,uint256)", 3, uint64(callPC))
	})

	t.Run("truncated-invokestatic", func(t *testing.T) {
		classfile := append([]byte(nil), original...)
		last := parsed.codeLengths["root"] - 1
		classfile[parsed.codeOffsets["root"]+last] = 0xb8
		result, err := Run(classfile, "root", []int32{20, 22}, 5_000_000)
		assertSolidityError(t, result, err, "BytecodeError(uint256,uint256)", 2, uint64(last))
	})
}

func assertSolidityError(t *testing.T, result Result, err error, signature string, code, pc uint64) {
	t.Helper()
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error = %+v/%v, want %s revert", result, err, signature)
	}
	selector := crypto.Keccak256([]byte(signature))[:4]
	if len(result.RevertData) != 68 || !bytes.Equal(result.RevertData[:4], selector) {
		t.Fatalf("revert data = 0x%x, want exact %s payload", result.RevertData, signature)
	}
	if got := binary.BigEndian.Uint64(result.RevertData[28:36]); got != code {
		t.Fatalf("error code = %d, want %d (data=%x)", got, code, result.RevertData)
	}
	if got := binary.BigEndian.Uint64(result.RevertData[60:68]); got != pc {
		t.Fatalf("error pc = %d, want %d (data=%x)", got, pc, result.RevertData)
	}
}

type callTestClass struct {
	data         []byte
	tags         []uint8
	cpOffsets    []int
	first        []uint16
	second       []uint16
	utf8         map[uint16]string
	methodAccess map[string]int
	codeOffsets  map[string]int
	codeLengths  map[string]int
}

func (c callTestClass) code(t *testing.T, method string) []byte {
	t.Helper()
	off, ok := c.codeOffsets[method]
	if !ok {
		t.Fatalf("method %q has no Code", method)
	}
	return c.data[off : off+c.codeLengths[method]]
}

func (c callTestClass) utfIndex(value string) uint16 {
	for index, text := range c.utf8 {
		if text == value {
			return index
		}
	}
	return 0
}

func parseCallTestClass(t *testing.T, data []byte) callTestClass {
	t.Helper()
	p := &testClassParser{t: t, data: data}
	if p.u4() != 0xcafebabe {
		t.Fatal("bad class magic")
	}
	p.skip(4)
	cpCount := int(p.u2())
	out := callTestClass{
		data: data, tags: make([]uint8, cpCount), cpOffsets: make([]int, cpCount),
		first: make([]uint16, cpCount), second: make([]uint16, cpCount),
		utf8: make(map[uint16]string), methodAccess: make(map[string]int),
		codeOffsets: make(map[string]int), codeLengths: make(map[string]int),
	}
	for i := 1; i < cpCount; i++ {
		out.cpOffsets[i] = p.pos
		tag := p.u1()
		out.tags[i] = tag
		switch tag {
		case 1:
			n := int(p.u2())
			out.utf8[uint16(i)] = string(p.take(n))
		case 3, 4:
			p.skip(4)
		case 5, 6:
			p.skip(8)
			i++
		case 7, 8, 16, 19, 20:
			out.first[i] = p.u2()
		case 9, 10, 11, 12, 17, 18:
			out.first[i], out.second[i] = p.u2(), p.u2()
		case 15:
			p.skip(3)
		default:
			t.Fatalf("unknown constant-pool tag %d", tag)
		}
	}
	p.skip(6)
	p.skip(2 * int(p.u2()))
	parseCallMembers(p, &out, false)
	parseCallMembers(p, &out, true)
	return out
}

func parseCallMembers(p *testClassParser, out *callTestClass, methods bool) {
	count := int(p.u2())
	for i := 0; i < count; i++ {
		accessOffset := p.pos
		p.skip(2)
		nameIndex := p.u2()
		p.skip(2)
		attributes := int(p.u2())
		name := out.utf8[nameIndex]
		if methods {
			out.methodAccess[name] = accessOffset
		}
		for a := 0; a < attributes; a++ {
			attributeName := out.utf8[p.u2()]
			n := int(p.u4())
			start := p.pos
			if methods && attributeName == "Code" {
				p.skip(4)
				codeLength := int(p.u4())
				out.codeOffsets[name] = p.pos
				out.codeLengths[name] = codeLength
			}
			p.pos = start + n
			p.check(0)
		}
	}
}
