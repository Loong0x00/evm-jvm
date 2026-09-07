// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"strings"
	"testing"
)

func TestIntegerExpressionsAndConversions(t *testing.T) {
	classfile := compileJava(t, "IntegerExpressions", `
public class IntegerExpressions {
    public static int constant() { return 0x89abcdef; }
    public static int mul(int a, int b) { return a * b; }
    public static int div(int a, int b) { return a / b; }
    public static int rem(int a, int b) { return a % b; }
    public static int neg(int a) { return -a; }
    public static int shl(int a, int b) { return a << b; }
    public static int shr(int a, int b) { return a >> b; }
    public static int ushr(int a, int b) { return a >>> b; }
    public static int and(int a, int b) { return a & b; }
    public static int or(int a, int b) { return a | b; }
    public static int xor(int a, int b) { return a ^ b; }
    public static int toByte(int a) { return (byte)a; }
    public static int toChar(int a) { return (char)a; }
    public static int toShort(int a) { return (short)a; }
}`)
	cases := []struct {
		name string
		args []int32
		want int32
	}{
		{"constant", nil, -1985229329},
		{"mul", []int32{2147483647, 2}, -2},
		{"mul", []int32{-2147483648, -1}, -2147483648},
		{"div", []int32{-7, 3}, -2},
		{"div", []int32{7, -3}, -2},
		{"div", []int32{-7, -3}, 2},
		{"div", []int32{-2147483648, -1}, -2147483648},
		{"rem", []int32{-7, 3}, -1},
		{"rem", []int32{7, -3}, 1},
		{"rem", []int32{-2147483648, -1}, 0},
		{"neg", []int32{-2147483648}, -2147483648},
		{"shl", []int32{1, -1}, -2147483648}, // -1 & 31 == 31
		{"shl", []int32{-1, 32}, -1},
		{"shr", []int32{-2147483648, 33}, -1073741824},
		{"ushr", []int32{-1, -1}, 1},
		{"and", []int32{-252645136, 0x33333333}, 0x30303030},
		{"or", []int32{0x0f000f00, 0x00330033}, 0x0f330f33},
		{"xor", []int32{-1, 0x55555555}, -1431655766},
		{"toByte", []int32{0x180}, -128},
		{"toByte", []int32{-129}, 127},
		{"toChar", []int32{-1}, 65535},
		{"toShort", []int32{65535}, -1},
		{"toShort", []int32{32768}, -32768},
	}
	for _, tc := range cases {
		t.Run(fmt.Sprintf("%s%v", tc.name, tc.args), func(t *testing.T) {
			result, err := Run(classfile, tc.name, tc.args, 3_000_000)
			if err != nil {
				t.Fatal(err)
			}
			if result.ExceptionClass != "" || result.Value != tc.want {
				t.Fatalf("result = %+v, want value %d", result, tc.want)
			}
			if result.GasUsed == 0 || len(result.RevertData) != 0 {
				t.Fatalf("result = %+v, want measured successful EVM value outcome", result)
			}
		})
	}
}

func TestDivisionByZeroIsTypedJavaOutcome(t *testing.T) {
	classfile := compileJava(t, "DivideByZero", `
public class DivideByZero {
    public static int div(int a, int b) { return a / b; }
    public static int rem(int a, int b) { return a % b; }
}`)
	for _, method := range []string{"div", "rem"} {
		t.Run(method, func(t *testing.T) {
			result, err := Run(classfile, method, []int32{123, 0}, 2_000_000)
			if err != nil {
				t.Fatalf("known uncaught Java outcome returned Go error: %v", err)
			}
			if result.ExceptionClass != "java.lang.ArithmeticException" {
				t.Fatalf("exception = %q, want java.lang.ArithmeticException", result.ExceptionClass)
			}
			if result.GasUsed == 0 || result.RuntimeSHA256 != expectedRuntimeHash {
				t.Fatalf("result = %+v, want gas and generic runtime hash", result)
			}
			if len(result.RevertData) != 36 || !bytes.Equal(result.RevertData[:4], javaExceptionSelector) {
				t.Fatalf("revert data = 0x%x, want exact JavaException(uint256) payload", result.RevertData)
			}
		})
	}
}

func TestJavaExceptionDecoderIsExact(t *testing.T) {
	for kind, want := range map[byte]string{
		1: "java.lang.ArithmeticException",
		2: "java.lang.StackOverflowError",
		3: "java.lang.ExceptionInInitializerError",
	} {
		valid := make([]byte, 36)
		copy(valid, javaExceptionSelector)
		valid[35] = kind
		if class, ok := decodeJavaException(valid); !ok || class != want {
			t.Fatalf("kind %d payload decoded as %q/%v, want %q/true", kind, class, ok, want)
		}
	}

	valid := make([]byte, 36)
	copy(valid, javaExceptionSelector)
	valid[35] = 1
	mutations := map[string]func([]byte) []byte{
		"unknown-selector": func(p []byte) []byte { p[0] ^= 0xff; return p },
		"unknown-kind":     func(p []byte) []byte { p[35] = 255; return p },
		"noncanonical-kind": func(p []byte) []byte {
			p[4] = 1
			return p
		},
		"truncated":  func(p []byte) []byte { return p[:35] },
		"extra-byte": func(p []byte) []byte { return append(p, 0) },
	}
	for name, mutate := range mutations {
		t.Run(name, func(t *testing.T) {
			payload := mutate(append([]byte(nil), valid...))
			if class, ok := decodeJavaException(payload); ok || class != "" {
				t.Fatalf("malformed payload decoded as %q/%v", class, ok)
			}
		})
	}
}

func TestLDCWideUsesConstantPoolIndexAbove255(t *testing.T) {
	var source strings.Builder
	source.WriteString("public class WideConstant {\n")
	// javac emits each earlier String literal into the pool before compiling wide().
	// These methods are not selected or interpreted; they only force a genuine ldc_w.
	for i := 0; i < 270; i++ {
		fmt.Fprintf(&source, "public static String s%03d() { return \"value-%03d\"; }\n", i, i)
	}
	source.WriteString("public static int wide() { return 0x76543210; }\n}\n")
	classfile := compileJava(t, "WideConstant", source.String())
	parsed := parseTestClass(t, classfile)
	code := parsed.methodCode(t, "wide")
	if len(code) != 4 || code[0] != 0x13 || code[3] != 0xac {
		t.Fatalf("wide bytecode = %x, want ldc_w <u2> ireturn", code)
	}
	index := int(binary.BigEndian.Uint16(code[1:3]))
	if index <= 255 || parsed.tags[index] != 3 {
		t.Fatalf("ldc_w index/tag = %d/%d, want CONSTANT_Integer index >255", index, parsed.tags[index])
	}
	result, err := Run(classfile, "wide", nil, 12_000_000)
	if err != nil {
		t.Fatal(err)
	}
	if result.Value != 0x76543210 || result.ExceptionClass != "" {
		t.Fatalf("result = %+v, want 0x76543210", result)
	}
	t.Logf("ldc_w constant_pool_index=%d gas=%d", index, result.GasUsed)
}

func TestRejectsInvalidIntegerConstantReferencesInsideEVM(t *testing.T) {
	original := compileJava(t, "ConstantReference", `
public class ConstantReference { public static int value() { return 0x76543210; } }`)
	parsed := parseTestClass(t, original)
	code := parsed.methodCode(t, "value")
	if len(code) != 3 || code[0] != 0x12 || code[2] != 0xac {
		t.Fatalf("value bytecode = %x, want ldc <u1> ireturn", code)
	}
	nonInteger := 0
	for i := 1; i < len(parsed.tags); i++ {
		if parsed.tags[i] != 0 && parsed.tags[i] != 3 {
			nonInteger = i
			break
		}
	}
	if nonInteger == 0 || nonInteger > 255 || len(parsed.tags) > 255 {
		t.Fatalf("unexpected constant pool shape: count=%d nonInteger=%d", len(parsed.tags), nonInteger)
	}
	cases := map[string]func([]byte){
		"zero-index": func(class []byte) { class[parsed.codeOffsets["value"]+1] = 0 },
		"out-of-range-index": func(class []byte) {
			class[parsed.codeOffsets["value"]+1] = byte(len(parsed.tags))
		},
		"noninteger-index": func(class []byte) {
			class[parsed.codeOffsets["value"]+1] = byte(nonInteger)
		},
		"truncated-ldc-w": func(class []byte) {
			class[parsed.codeOffsets["value"]+2] = 0x13 // only one byte remains in Code
		},
	}
	for name, mutate := range cases {
		t.Run(name, func(t *testing.T) {
			classfile := append([]byte(nil), original...)
			mutate(classfile)
			result, err := Run(classfile, "value", nil, 2_000_000)
			if err == nil || !strings.Contains(err.Error(), "execution reverted") {
				t.Fatalf("result/error = %+v/%v, want in-EVM bytecode rejection", result, err)
			}
			if result.ExceptionClass != "" || result.GasUsed == 0 || len(result.RevertData) < 4 {
				t.Fatalf("result = %+v, must remain an ordinary EVM error", result)
			}
		})
	}
}

// testClass is deliberately test-only classfile inspection. Production Run passes the
// unchanged bytes through ABI and leaves all parsing and constant resolution to the EVM.
type testClass struct {
	data        []byte
	tags        []uint8
	utf8        map[uint16]string
	codeOffsets map[string]int
	codeLengths map[string]int
}

func (c testClass) methodCode(t *testing.T, name string) []byte {
	t.Helper()
	off, ok := c.codeOffsets[name]
	if !ok {
		t.Fatalf("method %q has no Code attribute", name)
	}
	return c.data[off : off+c.codeLengths[name]]
}

func parseTestClass(t *testing.T, data []byte) testClass {
	t.Helper()
	p := &testClassParser{t: t, data: data}
	if p.u4() != 0xcafebabe {
		t.Fatal("javac fixture has bad magic")
	}
	p.skip(4)
	cpCount := int(p.u2())
	out := testClass{data: data, tags: make([]uint8, cpCount), utf8: make(map[uint16]string), codeOffsets: make(map[string]int), codeLengths: make(map[string]int)}
	for i := 1; i < cpCount; i++ {
		tag := p.u1()
		out.tags[i] = tag
		switch tag {
		case 1:
			n := int(p.u2())
			out.utf8[uint16(i)] = string(p.take(n))
		case 3, 4, 9, 10, 11, 12, 17, 18:
			p.skip(4)
		case 5, 6:
			p.skip(8)
			i++
		case 7, 8, 16, 19, 20:
			p.skip(2)
		case 15:
			p.skip(3)
		default:
			t.Fatalf("unknown constant-pool tag %d", tag)
		}
	}
	p.skip(6)
	p.skip(2 * int(p.u2()))
	parseTestMembers(p, out, false)
	parseTestMembers(p, out, true)
	return out
}

func parseTestMembers(p *testClassParser, out testClass, methods bool) {
	count := int(p.u2())
	for i := 0; i < count; i++ {
		p.skip(2)
		nameIndex := p.u2()
		p.skip(2)
		attributes := int(p.u2())
		for a := 0; a < attributes; a++ {
			attributeName := out.utf8[p.u2()]
			n := int(p.u4())
			start := p.pos
			if methods && attributeName == "Code" {
				p.skip(4)
				codeLength := int(p.u4())
				name := out.utf8[nameIndex]
				out.codeOffsets[name] = p.pos
				out.codeLengths[name] = codeLength
			}
			p.pos = start + n
			p.check(0)
		}
	}
}

type testClassParser struct {
	t    *testing.T
	data []byte
	pos  int
}

func (p *testClassParser) check(n int) {
	p.t.Helper()
	if n < 0 || p.pos < 0 || p.pos+n > len(p.data) {
		p.t.Fatalf("truncated test class at offset %d, need %d", p.pos, n)
	}
}

func (p *testClassParser) take(n int) []byte {
	p.t.Helper()
	p.check(n)
	b := p.data[p.pos : p.pos+n]
	p.pos += n
	return b
}
func (p *testClassParser) skip(n int) { p.take(n) }
func (p *testClassParser) u1() uint8  { return p.take(1)[0] }
func (p *testClassParser) u2() uint16 { return binary.BigEndian.Uint16(p.take(2)) }
func (p *testClassParser) u4() uint32 { return binary.BigEndian.Uint32(p.take(4)) }
