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

const controlFlowGasLimit = uint64(5_000_000) // finite test ceiling; loops remain EVM-gas bounded

func TestIntegerControlFlowSumAndFibonacci(t *testing.T) {
	classfile := compileJava(t, "Loops", `
public class Loops {
    public static int sum(int n) {
        int total = 0;
        for (int i = 1; i <= n; i++) total += i;
        return total;
    }
    public static int fib(int n) {
        if (n <= 1) return n;
        int a = 0;
        int b = 1;
        for (int i = 2; i <= n; i++) {
            int next = a + b;
            a = b;
            b = next;
        }
        return b;
    }
}`)
	cases := []struct {
		method string
		arg    int32
		want   int32
	}{
		{"sum", 0, 0}, {"sum", 10, 55}, {"sum", 100, 5050},
		{"fib", 0, 0}, {"fib", 1, 1}, {"fib", 2, 1}, {"fib", 10, 55}, {"fib", 20, 6765},
	}
	for _, tc := range cases {
		result, err := Run(classfile, tc.method, []int32{tc.arg}, controlFlowGasLimit)
		if err != nil {
			t.Fatalf("%s(%d): %v", tc.method, tc.arg, err)
		}
		if result.Value != tc.want {
			t.Fatalf("%s(%d) = %d, want %d", tc.method, tc.arg, result.Value, tc.want)
		}
		t.Logf("%s(%d) = %d, gas=%d", tc.method, tc.arg, result.Value, result.GasUsed)
	}
}

func TestM2IntegerEdgeSemantics(t *testing.T) {
	classfile := compileJava(t, "IntegerEdges", `
public class IntegerEdges {
    public static int constants(int selector) {
        if (selector < 0) return -1;
        if (selector == 0) return 5;
        if (selector == 1) return 100;
        return 20000;
    }
    public static int byteConstant() { return -100; }
    public static int shortConstant() { return -20000; }
    public static int constantThree() { return 3; }
    public static int constantFour() { return 4; }
    public static int genericLocal(int a, int b, int c, int d) {
        int fifth = a + d;
        return fifth;
    }
    public static int increments(int x) {
        int y = x;
        y += 127;
        y += -128;
        return y;
    }
    public static int subtract(int a, int b) { return a - b; }
    public static int eq(int a, int b) { if (a == b) return 1; return 0; }
    public static int ne(int a, int b) { if (a != b) return 1; return 0; }
    public static int lt(int a, int b) { if (a < b) return 1; return 0; }
    public static int ge(int a, int b) { if (a >= b) return 1; return 0; }
    public static int gt(int a, int b) { if (a > b) return 1; return 0; }
    public static int le(int a, int b) { if (a <= b) return 1; return 0; }
    public static int zeq(int x) { if (x == 0) return 1; return 0; }
    public static int zne(int x) { if (x != 0) return 1; return 0; }
    public static int zlt(int x) { if (x < 0) return 1; return 0; }
    public static int zge(int x) { if (x >= 0) return 1; return 0; }
    public static int zgt(int x) { if (x > 0) return 1; return 0; }
    public static int zle(int x) { if (x <= 0) return 1; return 0; }
}`)
	cases := []struct {
		method string
		args   []int32
		want   int32
	}{
		{"constants", []int32{-5}, -1}, {"constants", []int32{0}, 5},
		{"constants", []int32{1}, 100}, {"constants", []int32{2}, 20000},
		{"byteConstant", nil, -100}, {"shortConstant", nil, -20000},
		{"constantThree", nil, 3}, {"constantFour", nil, 4},
		{"genericLocal", []int32{40, 8, 9, 2}, 42},
		{"increments", []int32{0}, -1}, {"increments", []int32{-2147483648}, 2147483647},
		{"subtract", []int32{-2147483648, 1}, 2147483647},
		{"subtract", []int32{2147483647, -1}, -2147483648},
		{"eq", []int32{-1, -1}, 1}, {"eq", []int32{-1, 1}, 0},
		{"ne", []int32{-1, 1}, 1}, {"ne", []int32{7, 7}, 0},
		{"lt", []int32{-2147483648, 2147483647}, 1}, {"lt", []int32{1, -1}, 0},
		{"ge", []int32{2147483647, -2147483648}, 1}, {"ge", []int32{-2, -1}, 0},
		{"gt", []int32{0, -1}, 1}, {"gt", []int32{-1, 0}, 0},
		{"le", []int32{-1, 0}, 1}, {"le", []int32{1, 0}, 0},
		{"zeq", []int32{0}, 1}, {"zeq", []int32{-1}, 0},
		{"zne", []int32{-1}, 1}, {"zne", []int32{0}, 0},
		{"zlt", []int32{-2147483648}, 1}, {"zlt", []int32{0}, 0},
		{"zge", []int32{0}, 1}, {"zge", []int32{-1}, 0},
		{"zgt", []int32{2147483647}, 1}, {"zgt", []int32{0}, 0},
		{"zle", []int32{-1}, 1}, {"zle", []int32{1}, 0},
	}
	for _, tc := range cases {
		result, err := Run(classfile, tc.method, tc.args, controlFlowGasLimit)
		if err != nil {
			t.Fatalf("%s%v: %v", tc.method, tc.args, err)
		}
		if result.Value != tc.want {
			t.Fatalf("%s%v = %d, want %d", tc.method, tc.args, result.Value, tc.want)
		}
	}
}

func TestM2MalformedCodeRevertsInsideEVM(t *testing.T) {
	identity := compileJava(t, "MalformedIdentity", `public class MalformedIdentity { public static int run(int x) { return x; } }`)
	branch := compileJava(t, "MalformedBranch", `public class MalformedBranch { public static int run(int x) { if (x == 0) return 1; return 2; } }`)
	constant := compileJava(t, "MalformedConstant", `public class MalformedConstant { public static int run() { return 1; } }`)
	uninitialized := compileJava(t, "MalformedUninitialized", `public class MalformedUninitialized { public static int run(int x) { int y; if (x == 0) y = 1; else y = 2; return y; } }`)

	cases := map[string][]byte{}
	cases["stack-underflow"] = mutateCode(t, identity, "run", func(code []byte) { code[0] = 0x60 })
	cases["local-out-of-range"] = mutateCode(t, identity, "run", func(code []byte) { code[0] = 0x1d })
	cases["local-uninitialized"] = mutateCode(t, uninitialized, "run", func(code []byte) { code[0] = 0x1b })
	cases["stack-overflow"] = mutateCode(t, constant, "run", func(code []byte) { code[len(code)-1] = 0x04 })
	cases["truncated-one-byte-operand"] = mutateCode(t, constant, "run", func(code []byte) { code[len(code)-1] = 0x10 })
	cases["truncated-two-byte-operand"] = mutateCode(t, constant, "run", func(code []byte) { code[len(code)-1] = 0x11 })
	cases["branch-into-operand"] = mutateFirstBranch(t, branch, "run", 1)
	cases["branch-after-code"] = mutateFirstBranch(t, branch, "run", 0x7fff)
	cases["branch-before-code"] = mutateFirstBranch(t, branch, "run", -0x8000)

	wantCodes := map[string]uint64{
		"stack-underflow": 3, "local-out-of-range": 8, "local-uninitialized": 11,
		"stack-overflow": 9, "truncated-one-byte-operand": 2, "truncated-two-byte-operand": 2,
		"branch-into-operand": 12, "branch-after-code": 12, "branch-before-code": 12,
	}
	selector := crypto.Keccak256([]byte("BytecodeError(uint256,uint256)"))[:4]
	for name, classfile := range cases {
		t.Run(name, func(t *testing.T) {
			args := []int32{0}
			if strings.Contains(name, "overflow") || strings.Contains(name, "truncated") {
				args = nil
			}
			result, err := Run(classfile, "run", args, controlFlowGasLimit)
			if err == nil || !strings.Contains(err.Error(), "execution reverted") {
				t.Fatalf("result/error = %+v/%v, want in-EVM bytecode rejection", result, err)
			}
			if result.GasUsed == 0 || len(result.RevertData) != 68 || !bytes.Equal(result.RevertData[:4], selector) {
				t.Fatalf("result = %+v, want gas and BytecodeError(uint256,uint256)", result)
			}
			if code := binary.BigEndian.Uint64(result.RevertData[28:36]); code != wantCodes[name] {
				t.Fatalf("BytecodeError code = %d, want %d (data=%x)", code, wantCodes[name], result.RevertData)
			}
		})
	}
}

func TestNonterminatingJavaLoopRunsOutOfGas(t *testing.T) {
	classfile := compileJava(t, "Forever", `public class Forever { public static int loop() { while (true) {} } }`)
	const gasLimit = uint64(300_000)
	result, err := Run(classfile, "loop", nil, gasLimit)
	if err == nil || !strings.Contains(err.Error(), "out of gas") {
		t.Fatalf("result/error = %+v/%v, want EVM out of gas", result, err)
	}
	if result.GasUsed != gasLimit || len(result.RevertData) != 0 {
		t.Fatalf("result = %+v, want all finite gas consumed and no fake Java result", result)
	}
}

func mutateFirstBranch(t *testing.T, classfile []byte, method string, delta int16) []byte {
	t.Helper()
	return mutateCode(t, classfile, method, func(code []byte) {
		for pc := 0; pc < len(code); pc += testInstructionWidth(t, code[pc]) {
			if code[pc] >= 0x99 && code[pc] <= 0xa7 {
				binary.BigEndian.PutUint16(code[pc+1:pc+3], uint16(delta))
				return
			}
		}
		t.Fatal("javac method had no branch")
	})
}

func mutateCode(t *testing.T, classfile []byte, method string, mutate func([]byte)) []byte {
	t.Helper()
	out := append([]byte(nil), classfile...)
	off, n := findMethodCode(t, out, method)
	mutate(out[off : off+n]) // test-only malformed class manipulation; Run still receives raw bytes
	return out
}

// findMethodCode is deliberately test-only. Production Run never parses or changes a classfile.
func findMethodCode(t *testing.T, classfile []byte, wanted string) (int, int) {
	t.Helper()
	pos := 8
	need := func(n int) {
		if n < 0 || pos+n > len(classfile) {
			t.Fatalf("test class parser truncated at %d needing %d", pos, n)
		}
	}
	u1 := func() byte { need(1); v := classfile[pos]; pos++; return v }
	u2 := func() uint16 { need(2); v := binary.BigEndian.Uint16(classfile[pos:]); pos += 2; return v }
	u4 := func() uint32 { need(4); v := binary.BigEndian.Uint32(classfile[pos:]); pos += 4; return v }
	skip := func(n int) { need(n); pos += n }

	cpCount := int(u2())
	utf := make([]string, cpCount)
	for i := 1; i < cpCount; i++ {
		switch tag := u1(); tag {
		case 1:
			n := int(u2())
			need(n)
			utf[i] = string(classfile[pos : pos+n])
			skip(n)
		case 3, 4:
			skip(4)
		case 5, 6:
			skip(8)
			i++
		case 7, 8, 16, 19, 20:
			skip(2)
		case 9, 10, 11, 12, 17, 18:
			skip(4)
		case 15:
			skip(3)
		default:
			t.Fatalf("test class parser unknown constant-pool tag %d", tag)
		}
	}
	skip(6)
	for n := int(u2()); n > 0; n-- {
		skip(2)
	}
	skipMembers := func() {
		for n := int(u2()); n > 0; n-- {
			skip(6)
			for a := int(u2()); a > 0; a-- {
				skip(2)
				skip(int(u4()))
			}
		}
	}
	skipMembers() // fields
	for n := int(u2()); n > 0; n-- {
		skip(2)
		nameIndex := int(u2())
		skip(2)
		attrs := int(u2())
		for a := 0; a < attrs; a++ {
			attributeName := int(u2())
			attributeLength := int(u4())
			start := pos
			if utf[nameIndex] == wanted && utf[attributeName] == "Code" {
				need(8)
				codeLength := int(binary.BigEndian.Uint32(classfile[start+4:]))
				if codeLength < 1 || 8+codeLength > attributeLength {
					t.Fatal("invalid test Code attribute")
				}
				return start + 8, codeLength
			}
			skip(attributeLength)
		}
	}
	t.Fatalf("method %q Code attribute not found", wanted)
	return 0, 0
}

func testInstructionWidth(t *testing.T, op byte) int {
	t.Helper()
	switch {
	case op >= 0x02 && op <= 0x08, op >= 0x1a && op <= 0x1d,
		op >= 0x3b && op <= 0x3e, op == 0x60, op == 0x64, op == 0xac:
		return 1
	case op == 0x10, op == 0x15, op == 0x36:
		return 2
	case op == 0x11, op == 0x84, op >= 0x99 && op <= 0xa4, op == 0xa7:
		return 3
	default:
		t.Fatal(fmt.Sprintf("unexpected javac opcode 0x%02x", op))
		return 0
	}
}
