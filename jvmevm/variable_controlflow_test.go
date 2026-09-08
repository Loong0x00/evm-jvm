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

const runtimeM5caGasLimit = uint64(80_000_000)

func TestRuntimeM5caJavacDenseAndSparseSwitches(t *testing.T) {
	classfile := compileJava(t, "RuntimeM5caSwitch", `
public class RuntimeM5caSwitch {
    public static int dense(int n) {
        switch (n) {
        case -2: return 11;
        case -1: return 12;
        case 0: return 13;
        case 1: return 14;
        case 2: return 15;
        default: return 99;
        }
    }
    public static int sparse(int n) {
        switch (n) {
        case -2147483648: return 21;
        case -1000000: return 22;
        case 7: return 23;
        case 2147483647: return 24;
        default: return 98;
        }
    }
}`)
	if !bytes.Contains(parseTestClass(t, classfile).methodCode(t, "dense"), []byte{0xaa}) {
		t.Fatal("javac dense method did not contain tableswitch")
	}
	if !bytes.Contains(parseTestClass(t, classfile).methodCode(t, "sparse"), []byte{0xab}) {
		t.Fatal("javac sparse method did not contain lookupswitch")
	}
	for _, tc := range []struct {
		method string
		arg    int32
		want   int32
	}{
		{"dense", -2, 11}, {"dense", 0, 13}, {"dense", 2, 15}, {"dense", 3, 99},
		{"sparse", -2147483648, 21}, {"sparse", -1000000, 22}, {"sparse", 7, 23},
		{"sparse", 2147483647, 24}, {"sparse", -1, 98},
	} {
		result, err := Run(classfile, tc.method, []int32{tc.arg}, runtimeM5caGasLimit)
		if err != nil || result.ExceptionClass != "" || result.Value != tc.want {
			t.Fatalf("%s(%d) = %+v/%v, want %d", tc.method, tc.arg, result, err, tc.want)
		}
	}
}

func TestRuntimeM5caSwitchAlignmentAndNonzeroPadding(t *testing.T) {
	template := compileJava(t, "RuntimeM5caRawSwitch", `
public class RuntimeM5caRawSwitch {
    public static int run(int n) {
        switch (n) {
        case -3: return 1; case -2: return 2; case -1: return 3; case 0: return 4;
        case 1: return 5; case 2: return 6; case 3: return 7; default: return 9;
        }
    }
}`)
	for prefix := 0; prefix < 4; prefix++ {
		for _, lookup := range []bool{false, true} {
			name := fmt.Sprintf("prefix-%d-lookup-%t", prefix, lookup)
			t.Run(name, func(t *testing.T) {
				code, _, _ := runtimeM5caSwitchCode(prefix, lookup)
				classfile := runtimeM5caReplaceMethodCode(t, template, "run", code, 1, 1)
				secondKey := int32(0)
				if lookup {
					secondKey = 2
				}
				for _, tc := range []struct{ arg, want int32 }{{-1, 11}, {secondKey, 22}, {7, 99}} {
					result, err := Run(classfile, "run", []int32{tc.arg}, runtimeM5caGasLimit)
					if err != nil || result.ExceptionClass != "" || result.Value != tc.want {
						t.Fatalf("run(%d) = %+v/%v, want %d (code=%x)", tc.arg, result, err, tc.want, code)
					}
				}
			})
		}
	}

	// A zero-pair lookup takes its default while preserving a category-2 prefix.
	zeroPair := []byte{0x0a, 0x1a, 0xab, 0x7f, 0x00, 0x00, 0x00, 0x0a, 0, 0, 0, 0, 0x88, 0xac}
	classfile := runtimeM5caReplaceMethodCode(t, template, "run", zeroPair, 3, 1)
	result, err := Run(classfile, "run", []int32{123}, runtimeM5caGasLimit)
	if err != nil || result.ExceptionClass != "" || result.Value != 1 {
		t.Fatalf("zero-pair lookup with long prefix = %+v/%v, want 1", result, err)
	}

	// Duplicate targets are legal even though duplicate lookup keys are not.
	duplicateTarget, switchPC, header := runtimeM5caSwitchCode(0, false)
	binary.BigEndian.PutUint32(duplicateTarget[header+16:], binary.BigEndian.Uint32(duplicateTarget[header+12:]))
	classfile = runtimeM5caReplaceMethodCode(t, template, "run", duplicateTarget, 1, 1)
	result, err = Run(classfile, "run", []int32{0}, runtimeM5caGasLimit)
	if err != nil || result.Value != 11 {
		t.Fatalf("duplicate table target at switch PC %d = %+v/%v, want 11", switchPC, result, err)
	}
}

func TestRuntimeM5caWideIntLongAndReferenceLocals(t *testing.T) {
	template := compileJava(t, "RuntimeM5caWide", `public class RuntimeM5caWide {
    public static int run(int n) { int x = n; for (int i = 0; i < 20; i++) x += i; return x; }
}`)
	cases := []struct {
		name                string
		code                []byte
		maxStack, maxLocals uint16
		args                []int32
		want                int32
	}{
		{"int-255", []byte{0x10, 41, 0xc4, 0x36, 0x00, 0xff, 0xc4, 0x15, 0x00, 0xff, 0xac}, 1, 256, nil, 41},
		{"int-256", []byte{0x10, 42, 0xc4, 0x36, 0x01, 0x00, 0xc4, 0x15, 0x01, 0x00, 0xac}, 1, 257, nil, 42},
		{"iinc-positive", []byte{0xc4, 0x84, 0x00, 0x00, 0x7f, 0xff, 0x1a, 0xac}, 1, 1, []int32{1}, 32768},
		{"iinc-negative", []byte{0xc4, 0x84, 0x00, 0x00, 0x80, 0x00, 0x1a, 0xac}, 1, 1, []int32{0}, -32768},
		{"iinc-overflow", []byte{0xc4, 0x84, 0x00, 0x00, 0x00, 0x01, 0x1a, 0xac}, 1, 1, []int32{2147483647}, -2147483648},
		{"long-odd", []byte{0x0a, 0xc4, 0x37, 0x01, 0x01, 0xc4, 0x16, 0x01, 0x01, 0x88, 0xac}, 2, 259, nil, 1},
		{"long-1022", []byte{0x0a, 0xc4, 0x37, 0x03, 0xfe, 0xc4, 0x16, 0x03, 0xfe, 0x88, 0xac}, 2, 1024, nil, 1},
		{"reference-256", []byte{0x01, 0xc4, 0x3a, 0x01, 0x00, 0xc4, 0x19, 0x01, 0x00, 0x57, 0x10, 42, 0xac}, 1, 257, nil, 42},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			classfile := runtimeM5caReplaceMethodCode(t, template, "run", tc.code, tc.maxStack, tc.maxLocals)
			args := tc.args
			if args == nil {
				args = []int32{0}
			}
			result, err := Run(classfile, "run", args, runtimeM5caGasLimit)
			if err != nil || result.ExceptionClass != "" || result.Value != tc.want {
				t.Fatalf("result/error = %+v/%v, want %d", result, err, tc.want)
			}
		})
	}
}

func TestRuntimeM5caWideValidationAndOverlap(t *testing.T) {
	template := compileJava(t, "RuntimeM5caWideBad", `public class RuntimeM5caWideBad {
    public static int run() { int x = 0; for (int i = 0; i < 20; i++) x += i; return x; }
}`)
	cases := []struct {
		name                string
		code                []byte
		maxStack, maxLocals uint16
		kind, pc            uint64
	}{
		{"long-1023", []byte{0x0a, 0xc4, 0x37, 0x03, 0xff, 0x03, 0xac}, 2, 1024, 8, 1},
		{"uninitialized", []byte{0xc4, 0x15, 0x01, 0x00, 0xac}, 1, 257, 11, 0},
		{"wrong-load-kind", []byte{0x01, 0xc4, 0x3a, 0x01, 0x00, 0xc4, 0x15, 0x01, 0x00, 0xac}, 1, 257, 14, 5},
		{"store-underflow", []byte{0xc4, 0x36, 0x01, 0x00, 0x03, 0xac}, 1, 257, 3, 0},
		{"overwrite-long-tail", []byte{0x0a, 0xc4, 0x37, 0x01, 0x00, 0x04, 0xc4, 0x36, 0x01, 0x01, 0xc4, 0x16, 0x01, 0x00, 0x88, 0xac}, 2, 258, 11, 10},
		{"overwrite-long-head", []byte{0x0a, 0xc4, 0x37, 0x01, 0x00, 0x04, 0xc4, 0x36, 0x01, 0x00, 0xc4, 0x16, 0x01, 0x00, 0x88, 0xac}, 2, 258, 14, 10},
		{"invalid-nested", []byte{0xc4, 0xc4}, 1, 1, 15, 0},
		{"invalid-opcode", []byte{0xc4, 0x60}, 1, 1, 15, 0},
		// Wide F/D forms are supported in M5c-b. These malformed snippets now
		// retain precise local-initialization and operand-stack guards.
		{"fload-uninitialized", []byte{0xc4, 0x17, 0x00, 0x00}, 1, 1, 11, 0},
		{"dload-uninitialized", []byte{0xc4, 0x18, 0x00, 0x00}, 2, 2, 11, 0},
		{"fstore-underflow", []byte{0xc4, 0x38, 0x00, 0x00}, 1, 1, 3, 0},
		{"dstore-underflow", []byte{0xc4, 0x39, 0x00, 0x00}, 2, 2, 3, 0},
		{"unsupported-ret", []byte{0xc4, 0xa9, 0x00, 0x00}, 1, 1, 6, 0},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			classfile := runtimeM5caReplaceMethodCode(t, template, "run", tc.code, tc.maxStack, tc.maxLocals)
			result, err := Run(classfile, "run", nil, runtimeM5caGasLimit)
			assertSolidityError(t, result, err, "BytecodeError(uint256,uint256)", tc.kind, tc.pc)
		})
	}
}

func TestRuntimeM5caVariableInstructionStructureAndEdges(t *testing.T) {
	template := compileJava(t, "RuntimeM5caMalformed", `public class RuntimeM5caMalformed {
    public static int run(int n) { switch (n) { case 0: return 1; case 1: return 2; default: return 3; } }
}`)
	table, tablePC, tableHeader := runtimeM5caSwitchCode(0, false)
	lookup, lookupPC, lookupHeader := runtimeM5caSwitchCode(0, true)
	put32 := func(code []byte, at int, value int32) { binary.BigEndian.PutUint32(code[at:], uint32(value)) }
	clone := func(code []byte) []byte { return append([]byte(nil), code...) }

	lowHigh := clone(table)
	put32(lowHigh, tableHeader+4, 2)
	put32(lowHigh, tableHeader+8, 1)
	negativePairs := clone(lookup)
	put32(negativePairs, lookupHeader+4, -1)
	duplicateKeys := clone(lookup)
	put32(duplicateKeys, lookupHeader+16, -1)
	unsortedKeys := clone(lookup)
	put32(unsortedKeys, lookupHeader+16, -2)
	badDefault := clone(table)
	put32(badDefault, tableHeader, int32(tableHeader-tablePC))
	badPadding := clone(table)
	put32(badPadding, tableHeader, 1)
	badUntaken := clone(table)
	put32(badUntaken, tableHeader+16, int32(tableHeader-tablePC))
	badLookupUntaken := clone(lookup)
	put32(badLookupUntaken, lookupHeader+20, int32(lookupHeader-lookupPC))

	hugePairs := []byte{0x1a, 0xab, 0, 0, 0, 0, 0, 0, 0x7f, 0xff, 0xff, 0xff}
	extremeTable := []byte{0x1a, 0xaa, 0, 0, 0, 0, 0, 0, 0x80, 0, 0, 0, 0x7f, 0xff, 0xff, 0xff}
	underflowSwitch := clone(table)
	underflowSwitch[0] = 0x00
	cases := []struct {
		name      string
		code      []byte
		maxLocals uint16
		kind, pc  uint64
	}{
		{"truncated-tableswitch", []byte{0x1a, 0xaa}, 1, 2, 1},
		{"truncated-lookupswitch-header", []byte{0x1a, 0xab, 1, 2, 3}, 1, 2, 1},
		{"truncated-lookupswitch-pairs", []byte{0x1a, 0xab, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0}, 1, 2, 1},
		{"low-greater-high", lowHigh, 1, 15, uint64(tablePC)},
		{"negative-npairs", negativePairs, 1, 15, uint64(lookupPC)},
		{"duplicate-keys", duplicateKeys, 1, 15, uint64(lookupPC)},
		{"unsorted-keys", unsortedKeys, 1, 15, uint64(lookupPC)},
		{"huge-npairs-bounded", hugePairs, 1, 2, 1},
		{"extreme-table-range-bounded", extremeTable, 1, 2, 1},
		{"invalid-default", badDefault, 1, 12, uint64(tablePC)},
		{"invalid-padding-target", badPadding, 1, 12, uint64(tablePC)},
		{"invalid-untaken-table", badUntaken, 1, 12, uint64(tablePC)},
		{"invalid-untaken-lookup", badLookupUntaken, 1, 12, uint64(lookupPC)},
		{"switch-underflow", underflowSwitch, 1, 3, uint64(tablePC)},
		{"switch-key-reference", runtimeM5caReferenceSwitch(), 1, 14, 1},
		{"switch-key-long", runtimeM5caLongKeySwitch(), 1, 14, 1},
		{"truncated-goto-w", []byte{0xc8, 0, 0, 0}, 1, 2, 0},
		{"goto-w-positive-outside", []byte{0xc8, 0x7f, 0xff, 0xff, 0xff}, 1, 12, 0},
		{"goto-w-negative-outside", []byte{0xc8, 0x80, 0x00, 0x00, 0x00}, 1, 12, 0},
		{"truncated-wide-prefix", []byte{0xc4}, 1, 2, 0},
		{"truncated-wide-index", []byte{0xc4, 0x15, 0}, 1, 2, 0},
		{"truncated-wide-iinc", []byte{0xc4, 0x84, 0, 0, 0}, 1, 2, 0},
		{"truncated-unsupported-wide", []byte{0xc4, 0x17, 0}, 1, 2, 0},
		{"goto-wide-embedded-opcode", []byte{0xc8, 0, 0, 0, 6, 0xc4, 0x15, 0, 0, 0xac}, 1, 12, 0},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			classfile := runtimeM5caReplaceMethodCode(t, template, "run", tc.code, 2, tc.maxLocals)
			result, err := Run(classfile, "run", []int32{0}, runtimeM5caGasLimit)
			assertSolidityError(t, result, err, "BytecodeError(uint256,uint256)", tc.kind, tc.pc)
		})
	}
}

func TestRuntimeM5caGotoWLongForwardAndBackward(t *testing.T) {
	template := compileJava(t, "RuntimeM5caGoto", `public class RuntimeM5caGoto {
    public static int run(int n) { int x = n; for (int i = 0; i < 20; i++) x += i; return x; }
}`)
	const target = 33000
	forward := make([]byte, target+3)
	forward[0] = 0xc8
	binary.BigEndian.PutUint32(forward[1:5], target)
	forward[target] = 0x10
	forward[target+1] = 42
	forward[target+2] = 0xac
	classfile := runtimeM5caReplaceMethodCode(t, template, "run", forward, 1, 1)
	result, err := Run(classfile, "run", []int32{0}, 300_000_000)
	if err != nil || result.ExceptionClass != "" || result.Value != 42 {
		t.Fatalf("long forward goto_w = %+v/%v, want 42", result, err)
	}

	for name, code := range map[string][]byte{
		"long-prefix":        {0x0a, 0xc8, 0, 0, 0, 5, 0x88, 0xac},
		"reference-prefix":   {0x01, 0xc8, 0, 0, 0, 5, 0x57, 0x10, 42, 0xac},
		"wide-prefix-target": {0xc8, 0, 0, 0, 5, 0xc4, 0x15, 0, 0, 0xac},
	} {
		t.Run(name, func(t *testing.T) {
			withArg := name == "wide-prefix-target"
			args := []int32{0}
			want := int32(1)
			locals := uint16(1)
			if withArg {
				args = []int32{42}
				want = 42
			} else if name == "reference-prefix" {
				want = 42
			}
			class := runtimeM5caReplaceMethodCode(t, template, "run", code, 2, locals)
			got, runErr := Run(class, "run", args, runtimeM5caGasLimit)
			if runErr != nil || got.ExceptionClass != "" || got.Value != want {
				t.Fatalf("prefix goto_w = %+v/%v, want %d", got, runErr, want)
			}
		})
	}

	backward := []byte{
		0x03, 0x3c, // counter = 0
		0x84, 0x01, 0x01, // loop: counter++
		0x1b, 0x06, 0xa2, 0x00, 0x08, // if counter >= 3, exit
		0xc8, 0xff, 0xff, 0xff, 0xf8, // goto_w pc 2
		0x1b, 0xac,
	}
	classfile = runtimeM5caReplaceMethodCode(t, template, "run", backward, 2, 2)
	result, err = Run(classfile, "run", []int32{0}, runtimeM5caGasLimit)
	if err != nil || result.ExceptionClass != "" || result.Value != 3 {
		t.Fatalf("backward goto_w = %+v/%v, want 3", result, err)
	}

	const loopGas = uint64(400_000)
	selfLoop := runtimeM5caReplaceMethodCode(t, template, "run", []byte{0xc8, 0, 0, 0, 0}, 1, 1)
	result, err = Run(selfLoop, "run", []int32{0}, loopGas)
	if err == nil || !strings.Contains(err.Error(), "out of gas") || result.GasUsed != loopGas || len(result.RevertData) != 0 {
		t.Fatalf("self goto_w loop = %+v/%v, want plain finite EVM OOG", result, err)
	}
}

func runtimeM5caSwitchCode(prefix int, lookup bool) (code []byte, switchPC, header int) {
	code = make([]byte, prefix)
	code = append(code, 0x1a)
	switchPC = len(code)
	op := byte(0xaa)
	if lookup {
		op = 0xab
	}
	code = append(code, op)
	padding := (4 - ((switchPC + 1) % 4)) % 4
	for i := 0; i < padding; i++ {
		code = append(code, byte(0xa0+i))
	} // JVMS permits any padding value
	header = len(code)
	if lookup {
		code = append(code, make([]byte, 8+2*8)...)
		binary.BigEndian.PutUint32(code[header+4:], 2)
		binary.BigEndian.PutUint32(code[header+8:], uint32(0xffffffff))
		binary.BigEndian.PutUint32(code[header+16:], uint32(int32(2)))
	} else {
		code = append(code, make([]byte, 12+2*4)...)
		binary.BigEndian.PutUint32(code[header+4:], uint32(0xffffffff))
		binary.BigEndian.PutUint32(code[header+8:], uint32(int32(0)))
	}
	first := len(code)
	code = append(code, 0x10, 11, 0xac)
	second := len(code)
	code = append(code, 0x10, 22, 0xac)
	def := len(code)
	code = append(code, 0x10, 99, 0xac)
	binary.BigEndian.PutUint32(code[header:], uint32(int32(def-switchPC)))
	if lookup {
		binary.BigEndian.PutUint32(code[header+12:], uint32(int32(first-switchPC)))
		binary.BigEndian.PutUint32(code[header+20:], uint32(int32(second-switchPC)))
	} else {
		binary.BigEndian.PutUint32(code[header+12:], uint32(int32(first-switchPC)))
		binary.BigEndian.PutUint32(code[header+16:], uint32(int32(second-switchPC)))
	}
	return code, switchPC, header
}

func runtimeM5caReferenceSwitch() []byte {
	// aconst_null; lookupswitch default -> iconst_0. The key kind fails before dispatch.
	code := []byte{0x01, 0xab, 0x55, 0x66}
	header := len(code)
	code = append(code, make([]byte, 8)...)
	code = append(code, 0x03, 0xac)
	binary.BigEndian.PutUint32(code[header:], uint32(int32(len(code)-2-1)))
	return code
}

func runtimeM5caLongKeySwitch() []byte {
	// lconst_1; tableswitch 0..0, with both edges targeting l2i/ireturn.
	code := []byte{0x0a, 0xaa, 0x55, 0x66}
	header := len(code)
	code = append(code, make([]byte, 16)...)
	label := len(code)
	code = append(code, 0x88, 0xac)
	offset := uint32(int32(label - 1))
	binary.BigEndian.PutUint32(code[header:], offset)
	binary.BigEndian.PutUint32(code[header+12:], offset)
	return code
}

// This helper mutates only trusted test classfiles. Production Run receives unchanged raw bytes.
func runtimeM5caReplaceMethodCode(
	t *testing.T, classfile []byte, method string, code []byte, maxStack, maxLocals uint16,
) []byte {
	t.Helper()
	off, oldLength := findMethodCode(t, classfile, method)
	if len(code) == 0 || len(code) > 65535 {
		t.Fatalf("invalid replacement Code length %d", len(code))
	}
	out := make([]byte, 0, len(classfile)-oldLength+len(code))
	out = append(out, classfile[:off]...)
	out = append(out, code...)
	out = append(out, classfile[off+oldLength:]...)
	oldAttributeLength := binary.BigEndian.Uint32(classfile[off-12 : off-8])
	delta := int64(len(code) - oldLength)
	newAttributeLength := int64(oldAttributeLength) + delta
	if newAttributeLength < 12 || newAttributeLength > int64(^uint32(0)) {
		t.Fatalf("invalid replacement Code attribute length %d", newAttributeLength)
	}
	binary.BigEndian.PutUint32(out[off-12:off-8], uint32(newAttributeLength))
	binary.BigEndian.PutUint16(out[off-8:off-6], maxStack)
	binary.BigEndian.PutUint16(out[off-6:off-4], maxLocals)
	binary.BigEndian.PutUint32(out[off-4:off], uint32(len(code)))
	return out
}

func TestRuntimeM5caJavacEmitsAndExecutesWide(t *testing.T) {
	var source strings.Builder
	source.WriteString("public class RuntimeM5caJavacWide { public static int run(int n) {\n")
	for i := 0; i < 270; i++ {
		fmt.Fprintf(&source, "int v%d = n + %d;\n", i, i)
	}
	source.WriteString("return v0 + v269; } }\n")
	classfile := compileJava(t, "RuntimeM5caJavacWide", source.String())
	code := parseTestClass(t, classfile).methodCode(t, "run")
	if !bytes.Contains(code, []byte{0xc4, 0x36}) || !bytes.Contains(code, []byte{0xc4, 0x15}) {
		t.Fatalf("javac Code does not contain expected wide int load/store (length=%d)", len(code))
	}
	result, err := Run(classfile, "run", []int32{7}, 180_000_000)
	if err != nil || result.ExceptionClass != "" || result.Value != 283 {
		t.Fatalf("javac wide result/error = %+v/%v, want 283", result, err)
	}
}
