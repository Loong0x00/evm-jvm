// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"encoding/binary"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/crypto"
)

const callValidationGasLimit = uint64(50_000_000)

func TestM3aCallFramesPreserveCallerStateAndResolveExactOverloads(t *testing.T) {
	original := compileJava(t, "CallFrameState", `
public final class CallFrameState {
    private static int combine(int a, int b, int c) { return a * 100 + b * 10 + c; }
    private static int combine(int x) { return x + 1000; }
    private static int discarded(int x) { return x + 99; }
    private static void sink(int x) { }
    private static int frames(int n) {
        int keep = n * 10;
        if (n == 0) return keep;
        return keep + frames(n - 1);
    }
    public static int run(int a, int b, int c) {
        int saved = a - b;
        sink(discarded(7));
        discarded(9);
        return 5000 + combine(a, b, c) + combine(saved) + frames(c);
    }
}`)
	cases := []struct {
		name      string
		classfile []byte
	}{
		{name: "ordinary-owner-entry", classfile: original},
		// A Methodref owner is equivalent by binary class name, not by CP index.
		{name: "duplicate-owner-entry-same-name", classfile: duplicateCallOwner(t, original, "run")},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			result, err := Run(tc.classfile, "run", []int32{1, 2, 3}, callValidationGasLimit)
			if err != nil {
				t.Fatal(err)
			}
			// 5000 + 123 + 999 + (30+20+10+0). This simultaneously checks
			// argument order, overload selection, caller prefixes/locals, void
			// return, pop, and independent recursive frame state.
			if result.ExceptionClass != "" || result.Value != 6182 {
				t.Fatalf("result = %+v, want value 6182", result)
			}
			if result.GasUsed == 0 || len(result.RevertData) != 0 {
				t.Fatalf("result = %+v, want measured successful EVM result", result)
			}
		})
	}
}

func TestM3aInvalidCallConstantPoolStructuresUseCallError1(t *testing.T) {
	original := compileCallValidationClass(t)
	cases := map[string]func() []byte{
		"methodref-zero-index": func() []byte {
			return mutateCallValidationClass(t, original, func(out []byte, c callValidationClass) {
				_, pc := c.callRef(t, "run")
				binary.BigEndian.PutUint16(c.method(t, "run", "(II)I").code[pc+1:], 0)
			})
		},
		"methodref-out-of-range-index": func() []byte {
			return mutateCallValidationClass(t, original, func(out []byte, c callValidationClass) {
				_, pc := c.callRef(t, "run")
				binary.BigEndian.PutUint16(c.method(t, "run", "(II)I").code[pc+1:], uint16(c.cpCount))
			})
		},
		"methodref-wrong-tag": func() []byte {
			return mutateCallValidationClass(t, original, func(out []byte, c callValidationClass) {
				ref, _ := c.callRef(t, "run")
				out[c.entry(t, ref).offset] = 9 // Fieldref is not a valid invokestatic reference.
			})
		},
		"class-zero-index": func() []byte {
			return mutateCallValidationClass(t, original, func(out []byte, c callValidationClass) {
				ref, _ := c.callRef(t, "run")
				binary.BigEndian.PutUint16(out[c.entry(t, ref).offset+1:], 0)
			})
		},
		"class-wrong-tag": func() []byte {
			return mutateCallValidationClass(t, original, func(out []byte, c callValidationClass) {
				ref, _ := c.callRef(t, "run")
				nameType := c.u2(t, c.entry(t, ref).offset+3)
				binary.BigEndian.PutUint16(out[c.entry(t, ref).offset+1:], nameType)
			})
		},
		"name-and-type-zero-index": func() []byte {
			return mutateCallValidationClass(t, original, func(out []byte, c callValidationClass) {
				ref, _ := c.callRef(t, "run")
				binary.BigEndian.PutUint16(out[c.entry(t, ref).offset+3:], 0)
			})
		},
		"name-and-type-wrong-tag": func() []byte {
			return mutateCallValidationClass(t, original, func(out []byte, c callValidationClass) {
				ref, _ := c.callRef(t, "run")
				classIndex := c.u2(t, c.entry(t, ref).offset+1)
				binary.BigEndian.PutUint16(out[c.entry(t, ref).offset+3:], classIndex)
			})
		},
		"owner-utf8-zero-index": func() []byte {
			out := duplicateCallOwner(t, original, "run")
			return mutateCallValidationClass(t, out, func(out []byte, c callValidationClass) {
				ref, _ := c.callRef(t, "run")
				owner := c.u2(t, c.entry(t, ref).offset+1)
				binary.BigEndian.PutUint16(out[c.entry(t, owner).offset+1:], 0)
			})
		},
		"owner-utf8-wrong-tag": func() []byte {
			out := duplicateCallOwner(t, original, "run")
			return mutateCallValidationClass(t, out, func(out []byte, c callValidationClass) {
				ref, _ := c.callRef(t, "run")
				owner := c.u2(t, c.entry(t, ref).offset+1)
				binary.BigEndian.PutUint16(out[c.entry(t, owner).offset+1:], ref)
			})
		},
		"method-name-utf8-zero-index": func() []byte {
			return mutateCallValidationClass(t, original, func(out []byte, c callValidationClass) {
				nameType := c.callNameType(t, "run")
				binary.BigEndian.PutUint16(out[c.entry(t, nameType).offset+1:], 0)
			})
		},
		"descriptor-utf8-wrong-tag": func() []byte {
			return mutateCallValidationClass(t, original, func(out []byte, c callValidationClass) {
				nameType := c.callNameType(t, "run")
				binary.BigEndian.PutUint16(out[c.entry(t, nameType).offset+3:], nameType)
			})
		},
	}
	for name, makeClass := range cases {
		t.Run(name, func(t *testing.T) {
			classfile := makeClass()
			_, pc := parseCallValidationClass(t, classfile).callRef(t, "run")
			assertCallValidationError(t, classfile, "run", []int32{4, 2}, "CallError(uint256,uint256)", 1, &pc)
		})
	}

	t.Run("interface-methodref-class-owner", func(t *testing.T) {
		classfile := mutateCallValidationClass(t, original, func(out []byte, c callValidationClass) {
			ref, _ := c.callRef(t, "run")
			out[c.entry(t, ref).offset] = 11
		})
		_, pc := parseCallValidationClass(t, classfile).callRef(t, "run")
		assertCallValidationError(t, classfile, "run", []int32{4, 2}, "InterfaceError(uint256,uint256)", 1, &pc)
	})
}

func TestM3aCallResolutionErrorCodes(t *testing.T) {
	original := compileCallValidationClass(t)
	cases := []struct {
		name string
		code uint64
		make func() []byte
	}{
		{
			name: "external-owner", code: 2,
			make: func() []byte {
				return mutateCallValidationClass(t, original, func(out []byte, c callValidationClass) {
					ref, _ := c.callRef(t, "run")
					binary.BigEndian.PutUint16(out[c.entry(t, ref).offset+1:], c.classIndex(t, "java/lang/Object"))
				})
			},
		},
		{
			name: "missing-name", code: 3,
			make: func() []byte {
				return mutateCallValidationClass(t, original, func(out []byte, c callValidationClass) {
					nameType := c.callNameType(t, "run")
					binary.BigEndian.PutUint16(out[c.entry(t, nameType).offset+1:], c.utfIndex(t, "CallValidationTarget"))
				})
			},
		},
		{
			name: "missing-descriptor", code: 3,
			make: func() []byte {
				return mutateCallValidationClass(t, original, func(out []byte, c callValidationClass) {
					nameType := c.callNameType(t, "run")
					binary.BigEndian.PutUint16(out[c.entry(t, nameType).offset+3:], c.utfIndex(t, "()V"))
				})
			},
		},
		{
			name: "callee-nonstatic", code: 4,
			make: func() []byte {
				return mutateCallValidationClass(t, original, func(out []byte, c callValidationClass) {
					m := c.method(t, "helper", "(II)I")
					binary.BigEndian.PutUint16(out[m.accessOffset:], m.access&^0x0008)
				})
			},
		},
		{
			name: "callee-native-flag", code: 4,
			make: func() []byte {
				return mutateCallValidationClass(t, original, func(out []byte, c callValidationClass) {
					m := c.method(t, "helper", "(II)I")
					binary.BigEndian.PutUint16(out[m.accessOffset:], m.access|0x0100)
				})
			},
		},
		{
			name: "callee-without-code", code: 4,
			make: func() []byte {
				return mutateCallValidationClass(t, original, func(out []byte, c callValidationClass) {
					m := c.method(t, "helper", "(II)I")
					binary.BigEndian.PutUint16(out[m.codeNameOffset:], c.utfIndex(t, "SourceFile"))
				})
			},
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			classfile := tc.make()
			_, pc := parseCallValidationClass(t, classfile).callRef(t, "run")
			assertCallValidationError(t, classfile, "run", []int32{4, 2}, "CallError(uint256,uint256)", tc.code, &pc)
		})
	}
	for _, descriptor := range []string{"(J)J", "(F)F", "(D)D"} {
		t.Run("callee-typed-descriptor-"+descriptor, func(t *testing.T) {
			classfile := mutateCallValidationClass(t, original, func(out []byte, c callValidationClass) {
				nameType := c.callNameType(t, "run")
				binary.BigEndian.PutUint16(out[c.entry(t, nameType).offset+3:], c.utfIndex(t, descriptor))
			})
			_, pc := parseCallValidationClass(t, classfile).callRef(t, "run")
			// J/F/D descriptors resolve now; the caller's category-1 int top value
			// must not be implicitly reinterpreted as the selected parameter kind.
			assertCallValidationError(t, classfile, "run", []int32{4, 2}, "BytecodeError(uint256,uint256)", 14, &pc)
		})
	}
}

func TestM3aReturnDescriptorMismatchUsesCallError5(t *testing.T) {
	cases := []struct {
		name, source, helperDescriptor string
		from, to                       byte
	}{
		{
			name: "ireturn-from-void", helperDescriptor: "()V", from: 0xb1, to: 0xac,
			source: `public final class ReturnMismatch {
private static void helper() {} public static int run() { helper(); return 7; } }`,
		},
		{
			name: "return-from-int", helperDescriptor: "()I", from: 0xac, to: 0xb1,
			source: `public final class ReturnMismatch {
private static int helper() { return 7; } public static int run() { return helper(); } }`,
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			original := compileJava(t, "ReturnMismatch", tc.source)
			returnPC := -1
			classfile := mutateCallValidationClass(t, original, func(out []byte, c callValidationClass) {
				m := c.method(t, "helper", tc.helperDescriptor)
				changed := false
				for i := range m.code {
					if m.code[i] == tc.from {
						m.code[i] = tc.to
						returnPC = i
						changed = true
					}
				}
				if !changed {
					t.Fatalf("helper bytecode %x has no opcode 0x%02x", m.code, tc.from)
				}
			})
			// Code 5 reports the mismatched return's offset in the entered callee,
			// unlike codes 1-4 which identify the caller's invokestatic site.
			assertCallValidationError(t, classfile, "run", nil, "CallError(uint256,uint256)", 5, &returnPC)
		})
	}
}

func TestM3aCallUnderflowAndTruncationRemainBytecodeErrors(t *testing.T) {
	original := compileCallValidationClass(t)
	underflow := mutateCallValidationClass(t, original, func(out []byte, c callValidationClass) {
		m := c.method(t, "run", "(II)I")
		_, pc := c.callRef(t, "run")
		if pc < 2 || m.code[pc-2] != 0x1a || m.code[pc-1] != 0x1b {
			t.Fatalf("run bytecode = %x, want iload_0 iload_1 invokestatic", m.code)
		}
		m.code[pc-1] = 0x57 // pop the sole remaining argument immediately before the call
	})
	_, callPC := parseCallValidationClass(t, underflow).callRef(t, "run")
	assertCallValidationError(t, underflow, "run", []int32{4, 2}, "BytecodeError(uint256,uint256)", 3, &callPC)

	truncated := mutateCallValidationClass(t, original, func(out []byte, c callValidationClass) {
		m := c.method(t, "run", "(II)I")
		if len(m.code) == 0 || m.code[len(m.code)-1] != 0xac {
			t.Fatalf("run bytecode = %x, want final ireturn", m.code)
		}
		m.code[len(m.code)-1] = 0xb8 // invokestatic without its two-byte CP operand
	})
	truncatedPC := len(parseCallValidationClass(t, truncated).method(t, "run", "(II)I").code) - 1
	assertCallValidationError(t, truncated, "run", []int32{4, 2}, "BytecodeError(uint256,uint256)", 2, &truncatedPC)
}

func compileCallValidationClass(t *testing.T) []byte {
	t.Helper()
	return compileJava(t, "CallValidationTarget", `
public final class CallValidationTarget {
    private static int helper(int a, int b) { return a * 10 + b; }
    private static long helper(long x) { return x; }
    private static float helper(float x) { return x; }
    private static double helper(double x) { return x; }
    public static int run(int a, int b) { return helper(a, b); }
}`)
}

func assertCallValidationError(t *testing.T, classfile []byte, method string, args []int32, signature string, wantCode uint64, wantPC *int) {
	t.Helper()
	result, err := Run(classfile, method, args, callValidationGasLimit)
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error = %+v/%v, want exact %s revert", result, err, signature)
	}
	selector := crypto.Keccak256([]byte(signature))[:4]
	if result.ExceptionClass != "" || result.GasUsed == 0 || len(result.RevertData) != 68 || !bytes.Equal(result.RevertData[:4], selector) {
		t.Fatalf("result = %+v, want exact %s payload", result, signature)
	}
	code := callValidationUint256(t, result.RevertData[4:36])
	if code != wantCode {
		t.Fatalf("%s code = %d, want %d (data=%x)", signature, code, wantCode, result.RevertData)
	}
	if wantPC != nil {
		pc := callValidationUint256(t, result.RevertData[36:68])
		if pc != uint64(*wantPC) {
			t.Fatalf("%s pc = %d, want %d (data=%x)", signature, pc, *wantPC, result.RevertData)
		}
	}
}

func callValidationUint256(t *testing.T, word []byte) uint64 {
	t.Helper()
	if len(word) != 32 || !bytes.Equal(word[:24], make([]byte, 24)) {
		t.Fatalf("noncanonical or oversized uint256 word: %x", word)
	}
	return binary.BigEndian.Uint64(word[24:])
}

// The structures below inspect and mutate javac output only in tests. Production
// Run still receives unchanged-or-deliberately-malformed raw class bytes and does
// all actual parsing and resolution inside EVM.
type callValidationCPEntry struct {
	tag    byte
	offset int
}

type callValidationMethod struct {
	access         uint16
	accessOffset   int
	name           string
	descriptor     string
	codeNameOffset int
	code           []byte
}

type callValidationClass struct {
	data      []byte
	cpCount   int
	cpEnd     int
	entries   []callValidationCPEntry
	utf8      map[uint16]string
	methods   []callValidationMethod
	thisClass uint16
}

func parseCallValidationClass(t *testing.T, data []byte) callValidationClass {
	t.Helper()
	pos := 0
	need := func(n int) {
		if n < 0 || pos < 0 || pos+n > len(data) {
			t.Fatalf("truncated test class at offset %d, need %d", pos, n)
		}
	}
	u1 := func() byte { need(1); v := data[pos]; pos++; return v }
	u2 := func() uint16 { need(2); v := binary.BigEndian.Uint16(data[pos:]); pos += 2; return v }
	u4 := func() uint32 { need(4); v := binary.BigEndian.Uint32(data[pos:]); pos += 4; return v }
	skip := func(n int) { need(n); pos += n }
	if len(data) < 10 || binary.BigEndian.Uint32(data[:4]) != 0xcafebabe {
		t.Fatal("javac fixture has bad magic")
	}
	pos = 8
	cpCount := int(u2())
	c := callValidationClass{
		data: data, cpCount: cpCount, entries: make([]callValidationCPEntry, cpCount),
		utf8: make(map[uint16]string),
	}
	for i := 1; i < cpCount; i++ {
		off := pos
		tag := u1()
		c.entries[i] = callValidationCPEntry{tag: tag, offset: off}
		switch tag {
		case 1:
			n := int(u2())
			need(n)
			c.utf8[uint16(i)] = string(data[pos : pos+n])
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
			t.Fatalf("unknown test constant-pool tag %d", tag)
		}
	}
	c.cpEnd = pos
	skip(2) // class access flags
	c.thisClass = u2()
	skip(2) // super_class
	for n := int(u2()); n > 0; n-- {
		skip(2)
	}
	skipMembers := func(record bool) {
		for n := int(u2()); n > 0; n-- {
			accessOffset := pos
			access, nameIndex, descriptorIndex := u2(), u2(), u2()
			m := callValidationMethod{
				access: access, accessOffset: accessOffset,
				name: c.utf8[nameIndex], descriptor: c.utf8[descriptorIndex],
				codeNameOffset: -1,
			}
			for a := int(u2()); a > 0; a-- {
				nameOffset := pos
				attributeName := c.utf8[u2()]
				attributeLength := int(u4())
				start := pos
				need(attributeLength)
				if record && attributeName == "Code" {
					if attributeLength < 8 {
						t.Fatal("invalid test Code attribute")
					}
					codeLength := int(binary.BigEndian.Uint32(data[start+4:]))
					if codeLength < 1 || 8+codeLength > attributeLength {
						t.Fatal("invalid test Code length")
					}
					m.codeNameOffset = nameOffset
					m.code = data[start+8 : start+8+codeLength]
				}
				pos = start + attributeLength
			}
			if record {
				c.methods = append(c.methods, m)
			}
		}
	}
	skipMembers(false) // fields
	skipMembers(true)  // methods
	return c
}

func (c callValidationClass) entry(t *testing.T, index uint16) callValidationCPEntry {
	t.Helper()
	if index == 0 || int(index) >= len(c.entries) || c.entries[index].tag == 0 {
		t.Fatalf("invalid test CP index %d", index)
	}
	return c.entries[index]
}

func (c callValidationClass) u2(t *testing.T, offset int) uint16 {
	t.Helper()
	if offset < 0 || offset+2 > len(c.data) {
		t.Fatalf("invalid test u2 offset %d", offset)
	}
	return binary.BigEndian.Uint16(c.data[offset:])
}

func (c callValidationClass) method(t *testing.T, name, descriptor string) callValidationMethod {
	t.Helper()
	for _, m := range c.methods {
		if m.name == name && m.descriptor == descriptor {
			return m
		}
	}
	t.Fatalf("test method %s%s not found", name, descriptor)
	return callValidationMethod{}
}

func (c callValidationClass) callRef(t *testing.T, method string) (uint16, int) {
	t.Helper()
	var selected *callValidationMethod
	for i := range c.methods {
		if c.methods[i].name == method {
			if selected != nil {
				t.Fatalf("test root name %q is overloaded", method)
			}
			selected = &c.methods[i]
		}
	}
	if selected == nil {
		t.Fatalf("test method %q not found", method)
	}
	for pc := 0; pc+2 < len(selected.code); pc++ {
		if selected.code[pc] == 0xb8 {
			return binary.BigEndian.Uint16(selected.code[pc+1:]), pc
		}
	}
	t.Fatalf("test method %q bytecode has no complete invokestatic: %x", method, selected.code)
	return 0, 0
}

func (c callValidationClass) callNameType(t *testing.T, method string) uint16 {
	t.Helper()
	ref, _ := c.callRef(t, method)
	entry := c.entry(t, ref)
	if entry.tag != 10 {
		t.Fatalf("call CP tag = %d, want Methodref", entry.tag)
	}
	return c.u2(t, entry.offset+3)
}

func (c callValidationClass) utfIndex(t *testing.T, value string) uint16 {
	t.Helper()
	for index, text := range c.utf8 {
		if text == value {
			return index
		}
	}
	t.Fatalf("test UTF8 %q not found", value)
	return 0
}

func (c callValidationClass) classIndex(t *testing.T, name string) uint16 {
	t.Helper()
	for i := 1; i < len(c.entries); i++ {
		if c.entries[i].tag == 7 && c.utf8[c.u2(t, c.entries[i].offset+1)] == name {
			return uint16(i)
		}
	}
	t.Fatalf("test Class %q not found", name)
	return 0
}

func mutateCallValidationClass(t *testing.T, original []byte, mutate func([]byte, callValidationClass)) []byte {
	t.Helper()
	out := append([]byte(nil), original...)
	mutate(out, parseCallValidationClass(t, out))
	return out
}

func duplicateCallOwner(t *testing.T, original []byte, caller string) []byte {
	t.Helper()
	c := parseCallValidationClass(t, original)
	ref, _ := c.callRef(t, caller)
	refEntry := c.entry(t, ref)
	owner := c.u2(t, refEntry.offset+1)
	ownerEntry := c.entry(t, owner)
	if refEntry.tag != 10 || ownerEntry.tag != 7 || c.cpCount >= 65535 {
		t.Fatalf("unexpected call owner Methodref/Class shape")
	}
	nameIndex := c.u2(t, ownerEntry.offset+1)
	out := make([]byte, len(original)+3)
	copy(out, original[:c.cpEnd])
	out[c.cpEnd] = 7
	binary.BigEndian.PutUint16(out[c.cpEnd+1:], nameIndex)
	copy(out[c.cpEnd+3:], original[c.cpEnd:])
	binary.BigEndian.PutUint16(out[8:10], uint16(c.cpCount+1))
	binary.BigEndian.PutUint16(out[refEntry.offset+1:], uint16(c.cpCount))
	return out
}
