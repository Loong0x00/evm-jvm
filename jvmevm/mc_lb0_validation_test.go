// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
	"testing"
	"time"

	"github.com/ethereum/go-ethereum/core/vm"
	"github.com/ethereum/go-ethereum/crypto"
)

const (
	mcLB0VerifyOrdinaryGas = uint64(100_000_000)
	mcLB0VerifyBoundaryGas = uint64(1_000_000_000)
)

// These are verifier-only probes for JAVA_EVM_MC_LB0_PLAN.md. The host compiles
// bounded trusted Java 8 fixtures and makes narrow classfile mutations; it never
// supplies decoded text, resolved members, bootstrap replacements, or evaluated
// Java values to Run/RunClasses. Every String operation under test executes in EVM.

func TestMCLB0VerifyBootstrapImagesAndReservedNamesInBothAPIs(t *testing.T) {
	images := []struct {
		name, source, hash string
		size               int
	}{
		{"Comparable", "package java.lang; public interface Comparable<T> { public int compareTo(T other); }\n", "9d291a315ca765cdcb404feb72aa3d6f1216e542476ec071238fe105f2b85775", 196},
		{"CharSequence", "package java.lang; public interface CharSequence { public int length(); public char charAt(int index); public CharSequence subSequence(int start, int end); public String toString(); }\n", "c996ea063c00b6a8e320c73d81660bf2a733e492c312a032205c8d4f1e051576", 216},
		{"String", "package java.lang; public final class String implements java.io.Serializable, Comparable<String>, CharSequence { private final char[] value; private int hash; private String() { value = null; } public native int length(); public native boolean isEmpty(); public native char charAt(int index); public native boolean equals(Object other); public native int hashCode(); public native String toString(); public native int compareTo(String other); public native String intern(); public native CharSequence subSequence(int start, int end); }\n", "5582fd23db2e4bfeb3e6cc3b82de587c74cadb4773883e9bd71e08aafd95f4fe", 787},
	}
	solidity, err := os.ReadFile("runtime/JVMSubsetInterpreter.sol")
	if err != nil {
		t.Fatal(err)
	}
	for _, image := range images {
		t.Run(image.name, func(t *testing.T) {
			source, err := os.ReadFile(filepath.Join("runtime", "bootstrap", image.name+".java"))
			if err != nil || string(source) != image.source {
				t.Fatalf("checked source=%q error=%v", source, err)
			}
			rawHex, err := os.ReadFile(filepath.Join("runtime", "bootstrap", image.name+".class.hex"))
			if err != nil {
				t.Fatal(err)
			}
			checked, err := hex.DecodeString(strings.TrimSpace(string(rawHex)))
			if err != nil {
				t.Fatal(err)
			}
			got := mcLB0VerifyCompileBootstrap(t, image.name, image.source)
			digest := sha256.Sum256(got)
			if len(got) != image.size || hex.EncodeToString(digest[:]) != image.hash || !bytes.Equal(got, checked) {
				t.Fatalf("bootstrap bytes/hash=%d/%x, want %d/%s and checked identity", len(got), digest, image.size, image.hash)
			}
			if !bytes.Contains(solidity, []byte(hex.EncodeToString(got))) {
				t.Fatal("exact bootstrap image is not embedded in Solidity")
			}
		})
	}

	ordinary, _, _ := mcLB0VerifyLiteralClass(t, "Ordinary", []byte("x"), false, false, 0, false)
	for _, name := range []string{"java/lang/String", "java/lang/Comparable", "java/lang/CharSequence"} {
		reserved := mcLB0VerifyRenameClass(t, ordinary, name)
		t.Run(strings.TrimPrefix(name, "java/lang/")+"-single", func(t *testing.T) {
			mcLB0VerifyAssertError(t, func() (Result, error) { return Run(reserved, "run", nil, mcLB0VerifyOrdinaryGas) },
				"BootstrapProfileError(uint256,uint256)", 1, 0)
		})
		t.Run(strings.TrimPrefix(name, "java/lang/")+"-bundle-index1", func(t *testing.T) {
			mcLB0VerifyAssertError(t, func() (Result, error) {
				return RunClasses([][]byte{ordinary, reserved}, "Ordinary", "run", nil, mcLB0VerifyOrdinaryGas)
			}, "BootstrapProfileError(uint256,uint256)", 1, 1)
		})
	}
}

func TestMCLB0VerifyStrictMUTF8MatrixForwardChainsWideAndOffsets(t *testing.T) {
	tests := []struct {
		name    string
		payload []byte
		code    uint64
		rel     int
	}{
		{"raw-zero", []byte{0}, 2, 0},
		{"stray-continuation", []byte{0x80}, 2, 0},
		{"four-byte-lead", []byte{0xf0, 0x90, 0x80, 0x80}, 2, 0},
		{"invalid-lead-ff", []byte{0xff}, 2, 0},
		{"truncated-two", []byte{0xc2}, 3, 0},
		{"truncated-three-one", []byte{0xe1}, 3, 0},
		{"truncated-three-two", []byte{0xe1, 0x80}, 3, 0},
		{"bad-second", []byte{0xc2, 'A'}, 4, 1},
		{"bad-third", []byte{0xe1, 0x80, 'A'}, 4, 2},
		{"overlong-two", []byte{0xc0, 0x81}, 5, 0},
		{"overlong-three", []byte{0xe0, 0x80, 0x80}, 5, 0},
	}
	for i, tc := range tests {
		for _, shape := range []struct {
			name          string
			wide, forward bool
			prefix        int
		}{
			{"ldc", false, false, i % 3},
			{"ldc-forward", false, true, 1 + i%2},
			{"ldc_w-forward", true, true, 260},
		} {
			t.Run(tc.name+"-"+shape.name, func(t *testing.T) {
				raw, stringIndex, payloadOffset := mcLB0VerifyLiteralClass(t, "BadMUTF", tc.payload, shape.wide, shape.forward, shape.prefix, false)
				mcLB0VerifyAssertStringConstantError(t, func() (Result, error) {
					return Run(raw, "run", nil, mcLB0VerifyOrdinaryGas)
				}, tc.code, 0, uint64(stringIndex), uint64(payloadOffset+tc.rel))
			})
		}
	}

	// Complete-payload bounds must be checked before any continuation read; bytes
	// after the declared Utf8 payload are never consumed as part of the sequence.
	raw, stringIndex, payloadOffset := mcLB0VerifyLiteralClass(t, "PayloadBoundary", []byte{0xc2}, false, true, 0, false)
	mcLB0VerifyAssertStringConstantError(t, func() (Result, error) {
		return Run(raw, "run", nil, mcLB0VerifyOrdinaryGas)
	}, 3, 0, uint64(stringIndex), uint64(payloadOffset))
	ordinary, _, _ := mcLB0VerifyLiteralClass(t, "OffsetPeer", []byte("ok"), false, false, 0, false)
	mcLB0VerifyAssertStringConstantError(t, func() (Result, error) {
		return RunClasses([][]byte{ordinary, raw}, "PayloadBoundary", "run", nil, mcLB0VerifyOrdinaryGas)
	}, 3, 1, uint64(stringIndex), uint64(payloadOffset))

	empty, _, _ := mcLB0VerifyLiteralClass(t, "EmptyMUTF", nil, false, true, 0, false)
	mcLB0VerifyAssertValue(t, func() (Result, error) { return Run(empty, "run", nil, mcLB0VerifyOrdinaryGas) }, 1)

	for _, tc := range []struct {
		name    string
		payload []byte
		want    int32
	}{
		{"encoded-nul", []byte{0xc0, 0x80}, 0},
		{"shortest-2-low", []byte{0xc2, 0x80}, 0x80},
		{"shortest-2-high", []byte{0xdf, 0xbf}, 0x7ff},
		{"shortest-3-low", []byte{0xe0, 0xa0, 0x80}, 0x800},
		{"shortest-3-high", []byte{0xef, 0xbf, 0xbf}, 0xffff},
		{"unpaired-high", []byte{0xed, 0xa0, 0x80}, 0xd800},
		{"unpaired-low", []byte{0xed, 0xb0, 0x80}, 0xdc00},
		{"paired-high-unit", []byte{0xed, 0xa0, 0xbd, 0xed, 0xb8, 0x80}, 0xd83d},
		{"paired-low-unit", []byte{0xed, 0xa0, 0xbd, 0xed, 0xb8, 0x80}, 0xde00},
	} {
		t.Run("valid-"+tc.name, func(t *testing.T) {
			index := 0
			if tc.name == "paired-low-unit" {
				index = 1
			}
			raw, _, _ := mcLB0VerifyLiteralClassWithCharAt(t, "ValidMUTF", tc.payload, index)
			mcLB0VerifyAssertValue(t, func() (Result, error) { return Run(raw, "run", nil, mcLB0VerifyOrdinaryGas) }, tc.want)
		})
	}
}

func TestMCLB0VerifyTag8ChainsPredecodeAndDeferredMethods(t *testing.T) {
	valid, tag8, _ := mcLB0VerifyLiteralClass(t, "TagChains", []byte("x"), false, true, 0, false)
	parsed := mcLB0VerifyParse(t, valid)
	entry := parsed.cp[tag8]
	for _, tc := range []struct {
		name   string
		target uint16
	}{
		{"zero", 0},
		{"out-of-range", uint16(len(parsed.cp))},
		{"wrong-tag", parsed.thisClass},
	} {
		t.Run(tc.name, func(t *testing.T) {
			bad := append([]byte(nil), valid...)
			binary.BigEndian.PutUint16(bad[entry.offset+1:], tc.target)
			mcLB0VerifyAssertStringConstantError(t, func() (Result, error) {
				return Run(bad, "run", nil, mcLB0VerifyOrdinaryGas)
			}, 1, 0, uint64(tag8), 0)
		})
	}

	// A malformed String in unreachable bytecode of the selected method is still
	// validated during predecode; no allocation is implied by that validation.
	unreachable, badIndex, payload := mcLB0VerifyLiteralClass(t, "Unreachable", []byte{0}, false, true, 0, true)
	mcLB0VerifyAssertStringConstantError(t, func() (Result, error) {
		return Run(unreachable, "run", nil, mcLB0VerifyOrdinaryGas)
	}, 2, 0, uint64(badIndex), uint64(payload))

	compiled := mcLB0VerifyCompile(t, map[string]string{
		"Deferred.java": `public final class Deferred {
			public static int run(){ return 7; }
			public static int unsupported(){ return "abc".substring(1).length(); }
		}`,
	}, "Deferred")
	mcLB0VerifyAssertValue(t, func() (Result, error) { return Run(compiled.classes["Deferred"], "run", nil, mcLB0VerifyOrdinaryGas) }, 7)
	pc := mcLB0VerifyFindInvoke(t, compiled.classes["Deferred"], "unsupported", "substring", "(I)Ljava/lang/String;")
	mcLB0VerifyAssertError(t, func() (Result, error) {
		return Run(compiled.classes["Deferred"], "unsupported", nil, mcLB0VerifyOrdinaryGas)
	}, "StringProfileError(uint256,uint256)", 1, uint64(pc))
	malformed := append([]byte(nil), compiled.classes["Deferred"]...)
	mp := mcLB0VerifyParse(t, malformed)
	badTag8, badPayload := mcLB0VerifyStringEntry(t, mp, "abc")
	malformed[badPayload] = 0
	// The same malformed CP entry is dormant when run is selected, but validated
	// (before the deferred substring profile boundary) when unsupported is selected.
	mcLB0VerifyAssertValue(t, func() (Result, error) { return Run(malformed, "run", nil, mcLB0VerifyOrdinaryGas) }, 7)
	mcLB0VerifyAssertStringConstantError(t, func() (Result, error) {
		return Run(malformed, "unsupported", nil, mcLB0VerifyOrdinaryGas)
	}, 2, 0, uint64(badTag8), uint64(badPayload))
}

func TestMCLB0VerifyNativeMethodsInterfacesBridgeAndJavaOracles(t *testing.T) {
	compiled := mcLB0VerifyCompile(t, map[string]string{
		"MCLB0Native.java": `public final class MCLB0Native {
			public static int basic(){String a="",b="A\u0000\u07ff\u0800\ud800\udc00";return (a.isEmpty()?100:0)+b.length()*10+b.charAt(1)+b.charAt(4)-0xd800;}
			public static int identity(){String a="same",b="same";return (a==b&&a.intern()==a&&a.toString()==a)?1:0;}
			public static int equality(){Object o=new Object();String a="Aa",b="BB",c="Aa";return (a.hashCode()==b.hashCode()?100:0)+(a.equals(c)?10:0)+(a.equals(b)?0:1)+(a.equals(o)?0:2)+(a.equals(null)?0:4);}
			public static int compare(){return "a\uffff".compareTo("b\u0000")+"abc".compareTo("ab");}
			public static int charSeq(){CharSequence c="Az";return c.length()*100+c.charAt(1);}
			public static int comparable(){Comparable<String> c="b";return c.compareTo("a");}
			@SuppressWarnings({"rawtypes","unchecked"}) public static int bridge(){Comparable c="x";try{return c.compareTo(new Object());}catch(ClassCastException e){return 8;}}
			public static int nulls(){String s=null;try{return s.length();}catch(NullPointerException e){return 6;}}
		}`,
		"NoTag8.java":      `public final class NoTag8 {public static int run(){String s=null;CharSequence c=(CharSequence)s;Comparable x=(Comparable)s;try{return c.length()+x.compareTo(s);}catch(NullPointerException e){return 6;}}}`,
		"MCLB0Oracle.java": `public final class MCLB0Oracle {public static void main(String[] x){System.out.print(MCLB0Native.basic()+","+MCLB0Native.identity()+","+MCLB0Native.equality()+","+MCLB0Native.compare()+","+MCLB0Native.charSeq()+","+MCLB0Native.comparable()+","+MCLB0Native.bridge()+","+MCLB0Native.nulls());}}`,
	}, "MCLB0Native", "NoTag8", "MCLB0Oracle")
	want := []int32{160, 1, 117, 0, 322, 1, 8, 6}
	mcLB0VerifySameRawJava8And21(t, compiled.dir, "MCLB0Oracle", "160,1,117,0,322,1,8,6")
	methods := []string{"basic", "identity", "equality", "compare", "charSeq", "comparable", "bridge", "nulls"}
	for i, method := range methods {
		t.Run(method, func(t *testing.T) {
			mcLB0VerifyAssertValue(t, func() (Result, error) {
				return Run(compiled.classes["MCLB0Native"], method, nil, mcLB0VerifyOrdinaryGas)
			}, want[i])
		})
	}
	noTag8 := compiled.classes["NoTag8"]
	for i, cp := range mcLB0VerifyParse(t, noTag8).cp {
		if cp.tag == 8 {
			t.Fatalf("NoTag8 CP #%d unexpectedly has CONSTANT_String", i)
		}
	}
	mcLB0VerifyAssertValue(t, func() (Result, error) { return Run(noTag8, "run", nil, mcLB0VerifyOrdinaryGas) }, 6)
	mcLB0VerifyAssertValue(t, func() (Result, error) {
		return RunClasses([][]byte{noTag8}, "NoTag8", "run", nil, mcLB0VerifyOrdinaryGas)
	}, 6)

	p := mcLB0VerifyParse(t, compiled.classes["MCLB0Native"])
	for _, cp := range p.cp {
		if cp.tag == 8 && p.utf8[binary.BigEndian.Uint16(p.data[cp.offset+1:])] == "" {
			// Empty is represented by a real tag8/tag1 pair, not a null shortcut.
			goto emptyFound
		}
	}
	t.Fatal("empty String CONSTANT_String not found")
emptyFound:
	// nulls has symbolic String use but no ldc/tag8 in its selected Code. It proves
	// the three new bootstraps are appended for every invocation, not tag8-triggered.
	if mcLB0VerifyMethodHasOpcode(t, p.method(t, "nulls", "()I").code, 0x12) || mcLB0VerifyMethodHasOpcode(t, p.method(t, "nulls", "()I").code, 0x13) {
		t.Fatal("nulls unexpectedly contains a String load")
	}
}

func TestMCLB0VerifyBoundsDeferredNewNativeAndConstantTagGuards(t *testing.T) {
	compiled := mcLB0VerifyCompile(t, map[string]string{
		"Profile.java": `public final class Profile {
			public static int charAt(int i){return "x".charAt(i);}
			public static int substring(){return "xy".substring(1).length();}
			public static int subSequence(){return "xy".subSequence(0,1).length();}
			public static int allocate(){return new String().length();}
			public static int classLiteral(){Object o=String.class;return o==null?0:1;}
			public static int isEmpty(){return "".isEmpty()?1:0;}
		}`,
		"Fake.java": `public class Fake {public Fake(){} public native int length(); public synchronized native int flagged(); private native int hidden(); public static native int staticLength(); public static int run(){return new Fake().length();} public static int flags(){return new Fake().flagged();} public static int privateCall(){return new Fake().hidden();} public static int staticCall(){return staticLength();}}`,
	}, "Profile", "Fake")
	profile := compiled.classes["Profile"]
	charPC := mcLB0VerifyFindInvoke(t, profile, "charAt", "charAt", "(I)C")
	for _, i := range []int32{-1, 1} {
		mcLB0VerifyAssertError(t, func() (Result, error) { return Run(profile, "charAt", []int32{i}, mcLB0VerifyOrdinaryGas) },
			"StringProfileError(uint256,uint256)", 2, uint64(charPC))
	}
	for _, tc := range []struct{ method, member, desc string }{
		{"substring", "substring", "(I)Ljava/lang/String;"},
		{"subSequence", "subSequence", "(II)Ljava/lang/CharSequence;"},
	} {
		pc := mcLB0VerifyFindInvoke(t, profile, tc.method, tc.member, tc.desc)
		mcLB0VerifyAssertError(t, func() (Result, error) { return Run(profile, tc.method, nil, mcLB0VerifyOrdinaryGas) },
			"StringProfileError(uint256,uint256)", 1, uint64(pc))
	}
	newPC := mcLB0VerifyOpcodePC(t, mcLB0VerifyParse(t, profile).method(t, "allocate", "()I").code, 0xbb, 0)
	mcLB0VerifyAssertError(t, func() (Result, error) { return Run(profile, "allocate", nil, mcLB0VerifyOrdinaryGas) },
		"StringProfileError(uint256,uint256)", 1, uint64(newPC))
	classPC := mcLB0VerifyOpcodePC(t, mcLB0VerifyParse(t, profile).method(t, "classLiteral", "()I").code, 0x12, 0)
	mcLB0VerifyAssertError(t, func() (Result, error) { return Run(profile, "classLiteral", nil, mcLB0VerifyOrdinaryGas) },
		"BytecodeError(uint256,uint256)", 13, uint64(classPC))

	fakePC := mcLB0VerifyFindInvoke(t, compiled.classes["Fake"], "run", "length", "()I")
	mcLB0VerifyAssertError(t, func() (Result, error) { return Run(compiled.classes["Fake"], "run", nil, mcLB0VerifyOrdinaryGas) },
		"CallError(uint256,uint256)", 4, uint64(fakePC))
	for _, method := range []string{"flags", "privateCall", "staticCall"} {
		m := mcLB0VerifyParse(t, compiled.classes["Fake"]).method(t, method, "()I")
		pc := -1
		for at := 0; at < len(m.code); at += mcLB0VerifyInstructionWidth(t, m.code, at) {
			if m.code[at] == 0xb6 || m.code[at] == 0xb7 || m.code[at] == 0xb8 {
				pc = at
			}
		}
		if pc < 0 {
			t.Fatalf("%s has no native call", method)
		}
		mcLB0VerifyAssertError(t, func() (Result, error) { return Run(compiled.classes["Fake"], method, nil, mcLB0VerifyOrdinaryGas) },
			"CallError(uint256,uint256)", 4, uint64(pc))
	}

	// A non-Methodref operand is rejected by the old call-shape guard and can
	// never select a String intrinsic merely because its bytes name one.
	badTag := append([]byte(nil), profile...)
	bp := mcLB0VerifyParse(t, badTag)
	m := bp.method(t, "isEmpty", "()I")
	invokePC := mcLB0VerifyOpcodePC(t, m.code, 0xb6, 0)
	ref := binary.BigEndian.Uint16(m.code[invokePC+1:])
	badTag[bp.cp[ref].offset] = 9 // Methodref -> Fieldref, same four-byte payload
	mcLB0VerifyAssertError(t, func() (Result, error) { return Run(badTag, "isEmpty", nil, mcLB0VerifyOrdinaryGas) },
		"CallError(uint256,uint256)", 1, uint64(invokePC))

	// Exact descriptor binding: valid-but-wrong ()I must not bind isEmpty()Z.
	badDescriptor := append([]byte(nil), profile...)
	bd := mcLB0VerifyParse(t, badDescriptor)
	pc := mcLB0VerifyFindInvoke(t, badDescriptor, "isEmpty", "isEmpty", "()Z")
	ref = binary.BigEndian.Uint16(bd.method(t, "isEmpty", "()I").code[pc+1:])
	nt := binary.BigEndian.Uint16(bd.data[bd.cp[ref].offset+3:])
	descIndex := binary.BigEndian.Uint16(bd.data[bd.cp[nt].offset+3:])
	desc := bd.cp[descIndex]
	if bd.utf8[descIndex] != "()Z" {
		t.Fatalf("isEmpty descriptor=%q", bd.utf8[descIndex])
	}
	badDescriptor[desc.payloadOffset+2] = 'I'
	mcLB0VerifyAssertError(t, func() (Result, error) { return Run(badDescriptor, "isEmpty", nil, mcLB0VerifyOrdinaryGas) },
		"StringProfileError(uint256,uint256)", 1, uint64(pc))
}

func TestMCLB0VerifyBackingFieldsWrongTypedArgumentAndBridgeCCE(t *testing.T) {
	getValue, getPC := mcLB0VerifyStringFieldProbe(t, "BackingGet", "value", "[C", false)
	mcLB0VerifyAssertError(t, func() (Result, error) { return Run(getValue, "run", nil, mcLB0VerifyOrdinaryGas) },
		"FieldError(uint256,uint256)", 4, uint64(getPC))
	putValue, putPC := mcLB0VerifyStringFieldProbe(t, "BackingPut", "value", "[C", true)
	mcLB0VerifyAssertError(t, func() (Result, error) { return Run(putValue, "run", nil, mcLB0VerifyOrdinaryGas) },
		"FieldError(uint256,uint256)", 4, uint64(putPC))
	putHash, hashPC := mcLB0VerifyStringFieldProbe(t, "HashPut", "hash", "I", true)
	mcLB0VerifyAssertError(t, func() (Result, error) { return Run(putHash, "run", nil, mcLB0VerifyOrdinaryGas) },
		"FieldError(uint256,uint256)", 4, uint64(hashPC))

	wrong, invokePC := mcLB0VerifyWrongStringArgument(t)
	mcLB0VerifyAssertError(t, func() (Result, error) { return Run(wrong, "run", nil, mcLB0VerifyOrdinaryGas) },
		"BytecodeError(uint256,uint256)", 14, uint64(invokePC))
}

func TestMCLB0VerifyStringConstantValueProfile(t *testing.T) {
	for _, tc := range []struct {
		name       string
		spec       mcLB0VerifyConstantSpec
		want       int32
		errorCode  uint64
		stringCode uint64
	}{
		{"static-nonfinal", mcLB0VerifyConstantSpec{static: true, descriptor: "Ljava/lang/String;", payload: []byte("abc"), useString: true}, 3, 0, 0},
		{"instance-ignored-invalid-payload", mcLB0VerifyConstantSpec{static: false, descriptor: "Ljava/lang/String;", payload: []byte{0}, useString: true}, 7, 0, 0},
		{"wrong-descriptor", mcLB0VerifyConstantSpec{static: true, descriptor: "Ljava/lang/Object;", payload: []byte("x"), useString: true}, 0, 5, 0},
		{"wrong-tag", mcLB0VerifyConstantSpec{static: true, descriptor: "Ljava/lang/String;", payload: []byte("x"), constantInteger: true}, 0, 5, 0},
		{"wrong-tag8-chain", mcLB0VerifyConstantSpec{static: true, descriptor: "Ljava/lang/String;", payload: []byte("x"), useString: true, badChain: true}, 0, 5, 0},
		{"duplicate", mcLB0VerifyConstantSpec{static: true, descriptor: "Ljava/lang/String;", payload: []byte("x"), useString: true, duplicate: true}, 0, 5, 0},
		{"static-invalid-mutf", mcLB0VerifyConstantSpec{static: true, descriptor: "Ljava/lang/String;", payload: []byte{0}, useString: true}, 0, 0, 2},
	} {
		t.Run(tc.name, func(t *testing.T) {
			raw, tag8, payloadOffset := mcLB0VerifyConstantClass(t, "ConstantProfile", tc.spec)
			if tc.errorCode != 0 {
				mcLB0VerifyAssertError(t, func() (Result, error) { return Run(raw, "run", nil, mcLB0VerifyOrdinaryGas) },
					"FieldError(uint256,uint256)", tc.errorCode, 0)
			} else if tc.stringCode != 0 {
				mcLB0VerifyAssertStringConstantError(t, func() (Result, error) { return Run(raw, "run", nil, mcLB0VerifyOrdinaryGas) },
					tc.stringCode, 0, uint64(tag8), uint64(payloadOffset))
			} else {
				mcLB0VerifyAssertValue(t, func() (Result, error) { return Run(raw, "run", nil, mcLB0VerifyOrdinaryGas) }, tc.want)
			}
		})
	}
}

func TestMCLB0VerifyPreparationOOMPoisonAndDormantRoot(t *testing.T) {
	mcLB0VerifyBoundaryWatchdog(t, "dependent-poison", 120*time.Second, func(t *testing.T) {
		compiled := mcLB0VerifyCompile(t, map[string]string{
			"oom/Box.java":  `package oom; public final class Box {public Box(){}}`,
			"oom/Dep.java":  `package oom; public final class Dep {static final String S="dep"; public static int read(){return S.length();}}`,
			"oom/Root.java": `package oom; public final class Root {public static int run(){for(int i=0;i<1024;i++)new Box();int r=0;try{Dep.read();}catch(OutOfMemoryError e){r=7;}try{Dep.read();}catch(NoClassDefFoundError e){r+=12;}return r;}}`,
		}, "oom/Box", "oom/Dep", "oom/Root")
		bundle := [][]byte{compiled.classes["oom/Box"], compiled.classes["oom/Dep"], compiled.classes["oom/Root"]}
		r := mcLB0VerifyAssertValue(t, func() (Result, error) { return RunClasses(bundle, "oom/Root", "run", nil, mcLB0VerifyBoundaryGas) }, 19)
		t.Logf("dependent preparation OOM/poison gas=%d", r.GasUsed)
	})

	mcLB0VerifyBoundaryWatchdog(t, "dormant-root", 120*time.Second, func(t *testing.T) {
		var src strings.Builder
		src.WriteString("public final class DormantRoot {")
		for i := 0; i < 1025; i++ {
			fmt.Fprintf(&src, "static final String S%d=\"v%d\";", i, i)
		}
		src.WriteString("public static int run(){try{return 1;}catch(OutOfMemoryError e){return 9;}}}")
		class := mcLB0VerifyCompile(t, map[string]string{"DormantRoot.java": src.String()}, "DormantRoot").classes["DormantRoot"]
		// Constant preparation precedes entry of the dormant root. Its own handler
		// therefore cannot catch the 1025th miss; the exact uncaught Error survives.
		r := mcLB0VerifyAssertException(t, func() (Result, error) { return Run(class, "run", nil, mcLB0VerifyBoundaryGas) }, "java.lang.OutOfMemoryError", 7)
		t.Logf("dormant root preparation OOM gas=%d", r.GasUsed)
	})
}

func TestMCLB0VerifyMixedHeapRegistryAndReachableQuotaBoundaries(t *testing.T) {
	mcLB0VerifyBoundaryWatchdog(t, "mixed-quotas", 120*time.Second, func(t *testing.T) {
		compiled := mcLB0VerifyCompile(t, map[string]string{
			"mix/Box.java": `package mix; public final class Box {int x;Box(int x){this.x=x;}}`,
			"mix/Root.java": `package mix; public final class Root {
			public static int aliases(){String a="Aa",b="BB",a2="Aa";int[] x=new int[]{4};Box o=new Box(5);int e=0;try{int q=1/0;}catch(ArithmeticException z){e=7;}return (a==a2?1000:0)+(a==b?100:0)+a.length()*10+x[0]+o.x+e;}
			public static int objectQuota(){String s="q";for(int i=0;i<1023;i++)new Box(i);try{new Box(0);return 0;}catch(OutOfMemoryError e){return s.intern()==s?7:1;}}
			public static int arrayQuota(){String s="q";int[] a=null;for(int i=0;i<1023;i++)a=new int[0];try{a=new int[0];return 0;}catch(OutOfMemoryError e){return s.length()+6;}}
			public static int elementQuota(){String s="q";int[] a=new int[65536],b=new int[65536],c=new int[65536],d=new int[65535];try{a=new int[1];return 0;}catch(OutOfMemoryError e){return s.length()+8;}}
		}`,
		}, "mix/Box", "mix/Root")
		bundle := [][]byte{compiled.classes["mix/Box"], compiled.classes["mix/Root"]}
		for _, tc := range []struct {
			method string
			want   int32
			gas    uint64
		}{{"aliases", 1036, mcLB0VerifyOrdinaryGas}, {"objectQuota", 7, mcLB0VerifyBoundaryGas}, {"arrayQuota", 7, mcLB0VerifyBoundaryGas}, {"elementQuota", 9, mcLB0VerifyBoundaryGas}} {
			t.Run(tc.method, func(t *testing.T) {
				r := mcLB0VerifyAssertValue(t, func() (Result, error) { return RunClasses(bundle, "mix/Root", tc.method, nil, tc.gas) }, tc.want)
				t.Logf("%s gas=%d", tc.method, r.GasUsed)
			})
		}
	})
	// A separate independently-reachable handle-overflow point does not exist:
	// ordinary handles are exactly bounded by MAX_OBJECTS+MAX_ARRAYS, while the
	// exception arena contributes at most MAX_EXCEPTION_OBJECTS plus its reserved
	// emergency OOM handle. Reaching the next handle necessarily reaches one of
	// those constituent caps first. We test all reachable ordinary dimensions and
	// the shared alias stream rather than fabricate an impossible counter state.
}

func TestMCLB0VerifyOrdinaryFieldQuotaWithString(t *testing.T) {
	mcLB0VerifyBoundaryWatchdog(t, "field-quota", 120*time.Second, func(t *testing.T) {
		var big, tail strings.Builder
		big.WriteString("package mixfields; final class Big {")
		for i := 0; i < 1024; i++ {
			fmt.Fprintf(&big, "int f%d;", i)
		}
		big.WriteString("}")
		tail.WriteString("package mixfields; final class Tail {")
		for i := 0; i < 1022; i++ {
			fmt.Fprintf(&tail, "int f%d;", i)
		}
		tail.WriteString("}")
		compiled := mcLB0VerifyCompile(t, map[string]string{
			"mixfields/Big.java":  big.String(),
			"mixfields/Tail.java": tail.String(),
			"mixfields/One.java":  `package mixfields; final class One {int f;}`,
			"mixfields/Root.java": `package mixfields; public final class Root {public static int run(){String s="q";for(int i=0;i<63;i++)new Big();new Tail();try{new One();return 0;}catch(OutOfMemoryError e){return s.length()+7;}}}`,
		}, "mixfields/Big", "mixfields/Tail", "mixfields/One", "mixfields/Root")
		bundle := [][]byte{compiled.classes["mixfields/Big"], compiled.classes["mixfields/Tail"], compiled.classes["mixfields/One"], compiled.classes["mixfields/Root"]}
		// String contributes its real value/hash slots: 2 + 63*1024 + 1022
		// reaches 65536 exactly, so the next one-field object must raise Java OOM.
		r := mcLB0VerifyAssertValue(t, func() (Result, error) {
			return RunClasses(bundle, "mixfields/Root", "run", nil, mcLB0VerifyBoundaryGas)
		}, 8)
		t.Logf("ordinary field quota with String gas=%d", r.GasUsed)
	})
}

func TestMCLB0VerifyFullPoolHitFailedMissAtomicityAndHashCollisions(t *testing.T) {
	mcLB0VerifyBoundaryWatchdog(t, "full-pool", 120*time.Second, func(t *testing.T) {
		var src strings.Builder
		src.WriteString("public final class FullPool {public static int run(){int x=0;")
		for i := 0; i < 1024; i++ {
			fmt.Fprintf(&src, "x^=\"p%d\".length();", i)
		}
		src.WriteString("int caught=0;try{x^=\"miss\".length();}catch(OutOfMemoryError e){caught=1;}return caught*10+\"p0\".intern().length();}}")
		raw := mcLB0VerifyCompile(t, map[string]string{"FullPool.java": src.String()}, "FullPool").classes["FullPool"]
		// 1024 distinct misses simultaneously fill the object, array, and intern
		// quotas. Their equality is structural, so no honest test can isolate which
		// of those three equal limits fires first. The 1025th miss must be atomic;
		// the subsequent full-quota hit must allocate nothing and return length 2.
		r := mcLB0VerifyAssertValue(t, func() (Result, error) { return Run(raw, "run", nil, mcLB0VerifyBoundaryGas) }, 12)
		t.Logf("full pool hit/failed miss gas=%d", r.GasUsed)
	})

	compiled := mcLB0VerifyCompile(t, map[string]string{
		"Collision.java": `public final class Collision {public static int run(){String a="Aa",b="BB",c="Aa";return (a.hashCode()==b.hashCode()?100:0)+(a==b?0:10)+(a==c?1:0)+(a.equals(b)?0:2);}}`,
	}, "Collision")
	mcLB0VerifyAssertValue(t, func() (Result, error) { return Run(compiled.classes["Collision"], "run", nil, mcLB0VerifyOrdinaryGas) }, 113)
}

func TestMCLB0VerifyLongPrefixAndMaximumMUTF8Payload(t *testing.T) {
	mcLB0VerifyBoundaryWatchdog(t, "long-prefix", 120*time.Second, func(t *testing.T) {
		prefix := strings.Repeat("a", 32766)
		source := `public final class LongPrefix {public static int run(){String a="` + prefix + `x",b="` + prefix + `y";return a.compareTo(b)*100+(a.equals(b)?1:0)+a.length();}}`
		raw := mcLB0VerifyCompile(t, map[string]string{"LongPrefix.java": source}, "LongPrefix").classes["LongPrefix"]
		r := mcLB0VerifyAssertValue(t, func() (Result, error) { return Run(raw, "run", nil, mcLB0VerifyBoundaryGas) }, 32667)
		t.Logf("long-prefix compare gas=%d", r.GasUsed)
	})
	mcLB0VerifyBoundaryWatchdog(t, "max-utf8", 120*time.Second, func(t *testing.T) {
		payload := bytes.Repeat([]byte{'z'}, 65535)
		raw, _, _ := mcLB0VerifyLiteralClassWithCharAt(t, "MaxMUTF", payload, 65534)
		r := mcLB0VerifyAssertValue(t, func() (Result, error) { return Run(raw, "run", nil, mcLB0VerifyBoundaryGas) }, 'z')
		t.Logf("max-65535 MUTF8 gas=%d", r.GasUsed)
	})
}

func TestMCLB0VerifyExactJavaExceptionDecoderStillOneThroughTwelve(t *testing.T) {
	selector := crypto.Keccak256([]byte("JavaException(uint256)"))[:4]
	names := []string{"java.lang.ArithmeticException", "java.lang.StackOverflowError", "java.lang.ExceptionInInitializerError", "java.lang.NegativeArraySizeException", "java.lang.ArrayIndexOutOfBoundsException", "java.lang.NullPointerException", "java.lang.OutOfMemoryError", "java.lang.ClassCastException", "java.lang.ArrayStoreException", "java.lang.IncompatibleClassChangeError", "java.lang.AbstractMethodError", "java.lang.NoClassDefFoundError"}
	for i, want := range names {
		payload := append(append([]byte(nil), selector...), make([]byte, 32)...)
		payload[35] = byte(i + 1)
		if got, ok := decodeJavaException(payload); !ok || got != want {
			t.Fatalf("kind %d decoded as %q/%v, want %q", i+1, got, ok, want)
		}
	}
	for _, payload := range [][]byte{
		append(append([]byte(nil), selector...), make([]byte, 31)...),
		append(append([]byte(nil), selector...), append(make([]byte, 31), 13)...),
		append(append([]byte(nil), selector...), append([]byte{1}, make([]byte, 31)...)...),
		append([]byte{0, 0, 0, 0}, make([]byte, 32)...),
	} {
		if got, ok := decodeJavaException(payload); ok || got != "" {
			t.Fatalf("noncanonical payload %x decoded as %q/%v", payload, got, ok)
		}
	}
	one, _, _ := mcLB0VerifyLiteralClass(t, "OOGString", []byte("x"), false, false, 0, false)
	r, err := Run(one, "run", nil, 1)
	if err == nil || !errors.Is(err, vm.ErrOutOfGas) || r.ExceptionClass != "" || len(r.RevertData) != 0 {
		t.Fatalf("result/error=%+v/%v, want unlabeled EVM OOG", r, err)
	}
}

// ---- bounded fixture/compiler and classfile helpers ----

type mcLB0VerifyCompiled struct {
	dir     string
	classes map[string][]byte
}

func mcLB0VerifyCompile(t *testing.T, sources map[string]string, names ...string) mcLB0VerifyCompiled {
	t.Helper()
	dir := t.TempDir()
	rels := make([]string, 0, len(sources))
	for rel := range sources {
		rels = append(rels, rel)
	}
	sort.Strings(rels)
	args := []string{"-J-Xmx96m", "--release", "8", "-g:none", "-Xlint:-options", "-d", dir}
	for _, rel := range rels {
		path := filepath.Join(dir, filepath.FromSlash(rel))
		if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(sources[rel]), 0o600); err != nil {
			t.Fatal(err)
		}
		args = append(args, path)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	output, err := exec.CommandContext(ctx, "javac", args...).CombinedOutput()
	if err != nil {
		t.Fatalf("bounded trusted javac --release 8: %v\n%s", err, output)
	}
	result := mcLB0VerifyCompiled{dir: dir, classes: make(map[string][]byte, len(names))}
	for _, name := range names {
		data, err := os.ReadFile(filepath.Join(dir, filepath.FromSlash(name+".class")))
		if err != nil {
			t.Fatal(err)
		}
		result.classes[name] = data
	}
	return result
}

func mcLB0VerifyCompileBootstrap(t *testing.T, name, source string) []byte {
	t.Helper()
	pkg := "java/lang"
	pathName := name
	compiled := mcLB0VerifyCompile(t, map[string]string{filepath.ToSlash(filepath.Join(pkg, pathName+".java")): source}, filepath.ToSlash(filepath.Join(pkg, pathName)))
	return compiled.classes[filepath.ToSlash(filepath.Join(pkg, pathName))]
}

func mcLB0VerifySameRawJava8And21(t *testing.T, classPath, main, want string) {
	t.Helper()
	java8 := "/usr/lib/jvm/java-8-openjdk/bin/java"
	if home := os.Getenv("JAVA8_HOME"); home != "" {
		java8 = filepath.Join(home, "bin", "java")
	}
	java21 := "/usr/lib/jvm/jdk-21.0.9/bin/java"
	if home := os.Getenv("JAVA21_HOME"); home != "" {
		java21 = filepath.Join(home, "bin", "java")
	}
	for _, tc := range []struct{ name, exe string }{{"java8-authoritative", java8}, {"java21-secondary", java21}} {
		t.Run(tc.name, func(t *testing.T) {
			if _, err := os.Stat(tc.exe); err != nil {
				t.Fatalf("required %s oracle unavailable at %s: %v", tc.name, tc.exe, err)
			}
			ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			defer cancel()
			cmd := exec.CommandContext(ctx, tc.exe, "-Xmx64m", "-cp", classPath, main)
			output, err := cmd.CombinedOutput()
			if err != nil || strings.TrimSpace(string(output)) != want {
				t.Fatalf("same Java-8-target raw class bytes oracle=%q error=%v, want %q", output, err, want)
			}
		})
	}
}

type mcLB0VerifyCP struct {
	tag                   byte
	offset, payloadOffset int
	payloadLength         int
}
type mcLB0VerifyMethod struct {
	name, descriptor string
	code             []byte
	codeOffset       int
}
type mcLB0VerifyClass struct {
	data      []byte
	cp        []mcLB0VerifyCP
	utf8      map[uint16]string
	methods   []mcLB0VerifyMethod
	thisClass uint16
	cpEnd     int
}

func mcLB0VerifyParse(t *testing.T, data []byte) mcLB0VerifyClass {
	t.Helper()
	if len(data) < 10 || binary.BigEndian.Uint32(data[:4]) != 0xcafebabe {
		t.Fatal("bad test class magic")
	}
	pos := 8
	need := func(n int) {
		if n < 0 || pos+n > len(data) {
			t.Fatalf("truncated test class at %d need %d", pos, n)
		}
	}
	u1 := func() byte { need(1); v := data[pos]; pos++; return v }
	u2 := func() uint16 { need(2); v := binary.BigEndian.Uint16(data[pos:]); pos += 2; return v }
	u4 := func() uint32 { need(4); v := binary.BigEndian.Uint32(data[pos:]); pos += 4; return v }
	skip := func(n int) { need(n); pos += n }
	count := int(u2())
	c := mcLB0VerifyClass{data: data, cp: make([]mcLB0VerifyCP, count), utf8: make(map[uint16]string)}
	for i := 1; i < count; i++ {
		off := pos
		tag := u1()
		c.cp[i] = mcLB0VerifyCP{tag: tag, offset: off}
		switch tag {
		case 1:
			n := int(u2())
			need(n)
			c.cp[i].payloadOffset, c.cp[i].payloadLength = pos, n
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
			t.Fatalf("unknown CP tag %d at #%d", tag, i)
		}
	}
	c.cpEnd = pos
	skip(2)
	c.thisClass = u2()
	skip(2)
	for n := int(u2()); n > 0; n-- {
		skip(2)
	}
	readAttrs := func() []struct {
		name   uint16
		off    int
		length uint32
	} {
		n := int(u2())
		out := make([]struct {
			name   uint16
			off    int
			length uint32
		}, 0, n)
		for i := 0; i < n; i++ {
			name := u2()
			length := u4()
			off := pos
			skip(int(length))
			out = append(out, struct {
				name   uint16
				off    int
				length uint32
			}{name, off, length})
		}
		return out
	}
	for n := int(u2()); n > 0; n-- {
		skip(6)
		readAttrs()
	}
	for n := int(u2()); n > 0; n-- {
		skip(2)
		name, desc := u2(), u2()
		attrs := readAttrs()
		m := mcLB0VerifyMethod{name: c.utf8[name], descriptor: c.utf8[desc]}
		for _, a := range attrs {
			if c.utf8[a.name] == "Code" {
				if a.length < 12 || a.off+8 > len(data) {
					t.Fatal("bad Code attribute")
				}
				length := int(binary.BigEndian.Uint32(data[a.off+4:]))
				if a.off+8+length > len(data) {
					t.Fatal("truncated Code")
				}
				m.codeOffset, m.code = a.off+8, data[a.off+8:a.off+8+length]
			}
		}
		c.methods = append(c.methods, m)
	}
	return c
}

func (c mcLB0VerifyClass) method(t *testing.T, name, desc string) mcLB0VerifyMethod {
	t.Helper()
	for _, m := range c.methods {
		if m.name == name && m.descriptor == desc {
			return m
		}
	}
	t.Fatalf("method %s%s absent", name, desc)
	return mcLB0VerifyMethod{}
}

func mcLB0VerifyStringEntry(t *testing.T, c mcLB0VerifyClass, text string) (uint16, int) {
	t.Helper()
	for i, entry := range c.cp {
		if entry.tag != 8 {
			continue
		}
		target := binary.BigEndian.Uint16(c.data[entry.offset+1:])
		if int(target) < len(c.cp) && c.cp[target].tag == 1 && c.utf8[target] == text {
			return uint16(i), c.cp[target].payloadOffset
		}
	}
	t.Fatalf("CONSTANT_String %q absent", text)
	return 0, 0
}

// mcLB0VerifyCPBuilder emits only classfile constants needed by these probes.
type mcLB0VerifyCPBuilder struct{ entries [][]byte }

func (b *mcLB0VerifyCPBuilder) add(tag byte, payload []byte) uint16 {
	b.entries = append(b.entries, append([]byte{tag}, payload...))
	return uint16(len(b.entries))
}
func (b *mcLB0VerifyCPBuilder) utf(raw []byte) uint16 {
	p := make([]byte, 2+len(raw))
	binary.BigEndian.PutUint16(p, uint16(len(raw)))
	copy(p[2:], raw)
	return b.add(1, p)
}
func (b *mcLB0VerifyCPBuilder) class(name uint16) uint16 {
	p := []byte{0, 0}
	binary.BigEndian.PutUint16(p, name)
	return b.add(7, p)
}
func (b *mcLB0VerifyCPBuilder) string(utf uint16) uint16 {
	p := []byte{0, 0}
	binary.BigEndian.PutUint16(p, utf)
	return b.add(8, p)
}
func (b *mcLB0VerifyCPBuilder) pair(tag byte, a, c uint16) uint16 {
	p := make([]byte, 4)
	binary.BigEndian.PutUint16(p, a)
	binary.BigEndian.PutUint16(p[2:], c)
	return b.add(tag, p)
}

func mcLB0VerifyBaseCP(name string) (*mcLB0VerifyCPBuilder, uint16, uint16, uint16, uint16, uint16) {
	b := new(mcLB0VerifyCPBuilder)
	nameUTF := b.utf([]byte(name))
	thisClass := b.class(nameUTF)
	objectUTF := b.utf([]byte("java/lang/Object"))
	superClass := b.class(objectUTF)
	runName := b.utf([]byte("run"))
	runDesc := b.utf([]byte("()I"))
	codeName := b.utf([]byte("Code"))
	return b, thisClass, superClass, runName, runDesc, codeName
}

func mcLB0VerifyEmitClass(t *testing.T, b *mcLB0VerifyCPBuilder, thisClass, superClass uint16, fields, methods []byte) []byte {
	t.Helper()
	var out bytes.Buffer
	binary.Write(&out, binary.BigEndian, uint32(0xcafebabe))
	binary.Write(&out, binary.BigEndian, uint16(0))
	binary.Write(&out, binary.BigEndian, uint16(52))
	binary.Write(&out, binary.BigEndian, uint16(len(b.entries)+1))
	for _, e := range b.entries {
		out.Write(e)
	}
	binary.Write(&out, binary.BigEndian, uint16(0x0031))
	binary.Write(&out, binary.BigEndian, thisClass)
	binary.Write(&out, binary.BigEndian, superClass)
	binary.Write(&out, binary.BigEndian, uint16(0))
	out.Write(fields)
	out.Write(methods)
	binary.Write(&out, binary.BigEndian, uint16(0))
	return out.Bytes()
}

func mcLB0VerifyMethodBytes(name, desc, codeName uint16, code []byte, maxStack, maxLocals uint16, handlers []byte) []byte {
	var out bytes.Buffer
	binary.Write(&out, binary.BigEndian, uint16(1))
	binary.Write(&out, binary.BigEndian, uint16(0x0009))
	binary.Write(&out, binary.BigEndian, name)
	binary.Write(&out, binary.BigEndian, desc)
	binary.Write(&out, binary.BigEndian, uint16(1))
	binary.Write(&out, binary.BigEndian, codeName)
	attrLength := uint32(12 + len(code) + len(handlers))
	binary.Write(&out, binary.BigEndian, attrLength)
	binary.Write(&out, binary.BigEndian, maxStack)
	binary.Write(&out, binary.BigEndian, maxLocals)
	binary.Write(&out, binary.BigEndian, uint32(len(code)))
	out.Write(code)
	binary.Write(&out, binary.BigEndian, uint16(len(handlers)/8))
	out.Write(handlers)
	binary.Write(&out, binary.BigEndian, uint16(0))
	return out.Bytes()
}

func mcLB0VerifyLiteralClass(t *testing.T, name string, payload []byte, wide, forward bool, prefix int, unreachable bool) ([]byte, uint16, int) {
	t.Helper()
	b, thisClass, superClass, runName, runDesc, codeName := mcLB0VerifyBaseCP(name)
	for i := 0; i < prefix; i++ {
		b.utf([]byte(fmt.Sprintf("padding-%03d", i)))
	}
	var stringIndex uint16
	if forward {
		stringIndex = uint16(len(b.entries) + 1)
		b.string(stringIndex + 1)
		b.utf(payload)
	} else {
		utf := b.utf(payload)
		stringIndex = b.string(utf)
	}
	var code []byte
	if wide {
		code = []byte{0x13, byte(stringIndex >> 8), byte(stringIndex), 0x57, 0x04, 0xac}
	} else {
		if stringIndex > 255 {
			t.Fatal("ldc index exceeds u1")
		}
		code = []byte{0x12, byte(stringIndex), 0x57, 0x04, 0xac}
	}
	if unreachable {
		code = []byte{0xa7, 0, 5, 0x12, byte(stringIndex), 0x04, 0xac}
	}
	methods := mcLB0VerifyMethodBytes(runName, runDesc, codeName, code, 2, 0, nil)
	raw := mcLB0VerifyEmitClass(t, b, thisClass, superClass, []byte{0, 0}, methods)
	p := mcLB0VerifyParse(t, raw)
	target := binary.BigEndian.Uint16(raw[p.cp[stringIndex].offset+1:])
	return raw, stringIndex, p.cp[target].payloadOffset
}

func mcLB0VerifyLiteralClassWithCharAt(t *testing.T, name string, payload []byte, index int) ([]byte, uint16, int) {
	t.Helper()
	b, thisClass, superClass, runName, runDesc, codeName := mcLB0VerifyBaseCP(name)
	utf := b.utf(payload)
	str := b.string(utf)
	indexCP := b.add(3, []byte{byte(uint32(index) >> 24), byte(uint32(index) >> 16), byte(uint32(index) >> 8), byte(uint32(index))})
	stringUTF := b.utf([]byte("java/lang/String"))
	stringClass := b.class(stringUTF)
	methodName := b.utf([]byte("charAt"))
	methodDesc := b.utf([]byte("(I)C"))
	nt := b.pair(12, methodName, methodDesc)
	ref := b.pair(10, stringClass, nt)
	code := []byte{0x13, byte(str >> 8), byte(str), 0x13, byte(indexCP >> 8), byte(indexCP), 0xb6, byte(ref >> 8), byte(ref), 0xac}
	methods := mcLB0VerifyMethodBytes(runName, runDesc, codeName, code, 3, 0, nil)
	raw := mcLB0VerifyEmitClass(t, b, thisClass, superClass, []byte{0, 0}, methods)
	p := mcLB0VerifyParse(t, raw)
	return raw, str, p.cp[utf].payloadOffset
}

func mcLB0VerifyRenameClass(t *testing.T, raw []byte, name string) []byte {
	t.Helper()
	p := mcLB0VerifyParse(t, raw)
	nameIndex := binary.BigEndian.Uint16(raw[p.cp[p.thisClass].offset+1:])
	e := p.cp[nameIndex]
	delta := len(name) - e.payloadLength
	out := make([]byte, len(raw)+delta)
	copy(out, raw[:e.payloadOffset])
	copy(out[e.payloadOffset:], name)
	copy(out[e.payloadOffset+len(name):], raw[e.payloadOffset+e.payloadLength:])
	binary.BigEndian.PutUint16(out[e.offset+1:], uint16(len(name)))
	return out
}

func mcLB0VerifyInstructionWidth(t *testing.T, code []byte, pc int) int {
	t.Helper()
	if pc < 0 || pc >= len(code) {
		t.Fatalf("bad pc %d", pc)
	}
	w := 1
	switch code[pc] {
	case 0x10, 0x12, 0x15, 0x16, 0x17, 0x18, 0x19, 0x36, 0x37, 0x38, 0x39, 0x3a, 0xa9, 0xbc:
		w = 2
	case 0x11, 0x13, 0x14, 0x84, 0x99, 0x9a, 0x9b, 0x9c, 0x9d, 0x9e, 0x9f, 0xa0, 0xa1, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6, 0xa7, 0xa8, 0xb2, 0xb3, 0xb4, 0xb5, 0xb6, 0xb7, 0xb8, 0xbb, 0xbd, 0xc0, 0xc1, 0xc6, 0xc7:
		w = 3
	case 0xb9, 0xba, 0xc8, 0xc9:
		w = 5
	case 0xc5:
		w = 4
	case 0xc4:
		if pc+1 >= len(code) {
			t.Fatal("truncated wide")
		}
		if code[pc+1] == 0x84 {
			w = 6
		} else {
			w = 4
		}
	case 0xaa:
		h := pc + 1 + (4-(pc+1)%4)%4
		if h+12 > len(code) {
			t.Fatal("truncated tableswitch")
		}
		lo := int64(int32(binary.BigEndian.Uint32(code[h+4:])))
		hi := int64(int32(binary.BigEndian.Uint32(code[h+8:])))
		w = h - pc + 12 + int(hi-lo+1)*4
	case 0xab:
		h := pc + 1 + (4-(pc+1)%4)%4
		if h+8 > len(code) {
			t.Fatal("truncated lookupswitch")
		}
		n := int(int32(binary.BigEndian.Uint32(code[h+4:])))
		w = h - pc + 8 + n*8
	}
	if w < 1 || pc+w > len(code) {
		t.Fatalf("truncated opcode %02x at %d", code[pc], pc)
	}
	return w
}
func mcLB0VerifyOpcodePC(t *testing.T, code []byte, opcode byte, occ int) int {
	t.Helper()
	seen := 0
	for pc := 0; pc < len(code); pc += mcLB0VerifyInstructionWidth(t, code, pc) {
		if code[pc] == opcode {
			if seen == occ {
				return pc
			}
			seen++
		}
	}
	t.Fatalf("opcode %02x occurrence %d absent in %x", opcode, occ, code)
	return 0
}
func mcLB0VerifyMethodHasOpcode(t *testing.T, code []byte, opcode byte) bool {
	t.Helper()
	for pc := 0; pc < len(code); pc += mcLB0VerifyInstructionWidth(t, code, pc) {
		if code[pc] == opcode {
			return true
		}
	}
	return false
}

func mcLB0VerifyFindInvoke(t *testing.T, raw []byte, method, member, desc string) int {
	t.Helper()
	p := mcLB0VerifyParse(t, raw)
	var m mcLB0VerifyMethod
	found := false
	for _, x := range p.methods {
		if x.name == method {
			m = x
			found = true
			break
		}
	}
	if !found {
		t.Fatalf("method %s absent", method)
	}
	for pc := 0; pc < len(m.code); pc += mcLB0VerifyInstructionWidth(t, m.code, pc) {
		if m.code[pc] != 0xb6 && m.code[pc] != 0xb9 {
			continue
		}
		idx := binary.BigEndian.Uint16(m.code[pc+1:])
		if idx == 0 || int(idx) >= len(p.cp) || (p.cp[idx].tag != 10 && p.cp[idx].tag != 11) {
			continue
		}
		nt := binary.BigEndian.Uint16(raw[p.cp[idx].offset+3:])
		if nt == 0 || int(nt) >= len(p.cp) || p.cp[nt].tag != 12 {
			continue
		}
		n := binary.BigEndian.Uint16(raw[p.cp[nt].offset+1:])
		d := binary.BigEndian.Uint16(raw[p.cp[nt].offset+3:])
		if p.utf8[n] == member && p.utf8[d] == desc {
			return pc
		}
	}
	t.Fatalf("invoke %s%s absent in %s", member, desc, method)
	return 0
}

func mcLB0VerifyStringFieldProbe(t *testing.T, name, field, desc string, put bool) ([]byte, int) {
	t.Helper()
	b, thisClass, superClass, runName, runDesc, codeName := mcLB0VerifyBaseCP(name)
	litUTF := b.utf([]byte("x"))
	lit := b.string(litUTF)
	stringUTF := b.utf([]byte("java/lang/String"))
	stringClass := b.class(stringUTF)
	fieldUTF := b.utf([]byte(field))
	descUTF := b.utf([]byte(desc))
	nt := b.pair(12, fieldUTF, descUTF)
	ref := b.pair(9, stringClass, nt)
	var code []byte
	pc := 3
	if !put {
		code = []byte{0x13, byte(lit >> 8), byte(lit), 0xb4, byte(ref >> 8), byte(ref), 0x57, 0x04, 0xac}
	} else if desc == "I" {
		code = []byte{0x13, byte(lit >> 8), byte(lit), 0x03, 0xb5, byte(ref >> 8), byte(ref), 0x04, 0xac}
		pc = 4
	} else {
		code = []byte{0x13, byte(lit >> 8), byte(lit), 0x01, 0xb5, byte(ref >> 8), byte(ref), 0x04, 0xac}
		pc = 4
	}
	methods := mcLB0VerifyMethodBytes(runName, runDesc, codeName, code, 3, 0, nil)
	return mcLB0VerifyEmitClass(t, b, thisClass, superClass, []byte{0, 0}, methods), pc
}

func mcLB0VerifyWrongStringArgument(t *testing.T) ([]byte, int) {
	t.Helper()
	b, thisClass, superClass, runName, runDesc, codeName := mcLB0VerifyBaseCP("WrongStringArg")
	litUTF := b.utf([]byte("a"))
	lit := b.string(litUTF)
	stringUTF := b.utf([]byte("java/lang/String"))
	stringClass := b.class(stringUTF)
	compareUTF := b.utf([]byte("compareTo"))
	compareDesc := b.utf([]byte("(Ljava/lang/String;)I"))
	compareNT := b.pair(12, compareUTF, compareDesc)
	compareRef := b.pair(10, stringClass, compareNT)
	initUTF := b.utf([]byte("<init>"))
	voidDesc := b.utf([]byte("()V"))
	initNT := b.pair(12, initUTF, voidDesc)
	initRef := b.pair(10, superClass, initNT)
	code := []byte{0x13, byte(lit >> 8), byte(lit), 0xbb, byte(superClass >> 8), byte(superClass), 0x59, 0xb7, byte(initRef >> 8), byte(initRef), 0xb6, byte(compareRef >> 8), byte(compareRef), 0xac}
	invokePC := 10
	methods := mcLB0VerifyMethodBytes(runName, runDesc, codeName, code, 4, 0, nil)
	return mcLB0VerifyEmitClass(t, b, thisClass, superClass, []byte{0, 0}, methods), invokePC
}

type mcLB0VerifyConstantSpec struct {
	static                                          bool
	descriptor                                      string
	payload                                         []byte
	useString, constantInteger, badChain, duplicate bool
}

func mcLB0VerifyConstantClass(t *testing.T, name string, s mcLB0VerifyConstantSpec) ([]byte, uint16, int) {
	t.Helper()
	b, thisClass, superClass, runName, runDesc, codeName := mcLB0VerifyBaseCP(name)
	fieldName := b.utf([]byte("S"))
	fieldDesc := b.utf([]byte(s.descriptor))
	cvName := b.utf([]byte("ConstantValue"))
	utf := b.utf(s.payload)
	tag8 := b.string(utf)
	constant := tag8
	if s.constantInteger {
		constant = b.add(3, []byte{0, 0, 0, 7})
	}
	if s.badChain {
		p := b.entries[tag8-1]
		binary.BigEndian.PutUint16(p[1:], thisClass)
	}
	var fields bytes.Buffer
	binary.Write(&fields, binary.BigEndian, uint16(1))
	access := uint16(0x0001)
	if s.static {
		access |= 0x0008
	}
	binary.Write(&fields, binary.BigEndian, access)
	binary.Write(&fields, binary.BigEndian, fieldName)
	binary.Write(&fields, binary.BigEndian, fieldDesc)
	count := uint16(1)
	if s.duplicate {
		count = 2
	}
	binary.Write(&fields, binary.BigEndian, count)
	for i := uint16(0); i < count; i++ {
		binary.Write(&fields, binary.BigEndian, cvName)
		binary.Write(&fields, binary.BigEndian, uint32(2))
		binary.Write(&fields, binary.BigEndian, constant)
	}
	code := []byte{0x10, 7, 0xac}
	if s.static && s.useString && !s.constantInteger && !s.badChain && !s.duplicate && s.descriptor == "Ljava/lang/String;" {
		classUTF := b.utf([]byte(name))
		owner := b.class(classUTF)
		nt := b.pair(12, fieldName, fieldDesc)
		fieldRef := b.pair(9, owner, nt)
		stringUTF := b.utf([]byte("java/lang/String"))
		stringClass := b.class(stringUTF)
		lenUTF := b.utf([]byte("length"))
		lenDesc := b.utf([]byte("()I"))
		lenNT := b.pair(12, lenUTF, lenDesc)
		lenRef := b.pair(10, stringClass, lenNT)
		code = []byte{0xb2, byte(fieldRef >> 8), byte(fieldRef), 0xb6, byte(lenRef >> 8), byte(lenRef), 0xac}
	}
	methods := mcLB0VerifyMethodBytes(runName, runDesc, codeName, code, 2, 0, nil)
	raw := mcLB0VerifyEmitClass(t, b, thisClass, superClass, fields.Bytes(), methods)
	p := mcLB0VerifyParse(t, raw)
	return raw, tag8, p.cp[utf].payloadOffset
}

func mcLB0VerifyBoundaryWatchdog(t *testing.T, key string, limit time.Duration, fn func(*testing.T)) {
	t.Helper()
	envKey := "MC_LB0_VERIFY_BOUNDARY"
	if active := os.Getenv(envKey); active != "" {
		if active == key {
			fn(t)
		}
		return
	}
	ctx, cancel := context.WithTimeout(context.Background(), limit)
	defer cancel()
	cmd := exec.CommandContext(ctx, os.Args[0], "-test.run=^"+mcLB0VerifyRegexpQuoteMeta(t.Name())+"$", "-test.timeout="+(limit+5*time.Second).String(), "-test.v")
	cmd.Env = append(os.Environ(), envKey+"="+key)
	output, err := cmd.CombinedOutput()
	if ctx.Err() == context.DeadlineExceeded {
		t.Fatalf("%s exceeded %s; child output:\n%s", key, limit, output)
	}
	if err != nil {
		t.Fatalf("%s bounded child failed: %v\n%s", key, err, output)
	}
	t.Logf("%s bounded child:\n%s", key, strings.TrimSpace(string(output)))
}
func mcLB0VerifyRegexpQuoteMeta(s string) string {
	var b strings.Builder
	for _, r := range s {
		if strings.ContainsRune(`\\.+*?()|[]{}^$`, r) {
			b.WriteByte('\\')
		}
		b.WriteRune(r)
	}
	return b.String()
}

func mcLB0VerifyAssertValue(t *testing.T, run func() (Result, error), want int32) Result {
	t.Helper()
	r, e := run()
	if e != nil || r.ExceptionClass != "" || r.Value != want || r.GasUsed == 0 || len(r.RevertData) != 0 {
		t.Fatalf("result/error=%+v/%v, want value %d", r, e, want)
	}
	return r
}
func mcLB0VerifyAssertException(t *testing.T, run func() (Result, error), name string, kind byte) Result {
	t.Helper()
	r, e := run()
	sel := crypto.Keccak256([]byte("JavaException(uint256)"))[:4]
	if e != nil || r.ExceptionClass != name || r.GasUsed == 0 || len(r.RevertData) != 36 || !bytes.Equal(r.RevertData[:4], sel) || !bytes.Equal(r.RevertData[4:35], make([]byte, 31)) || r.RevertData[35] != kind {
		t.Fatalf("result/error=%+v/%v data=%x, want JavaException(%d) %s", r, e, r.RevertData, kind, name)
	}
	return r
}
func mcLB0VerifyWord(t *testing.T, b []byte) uint64 {
	t.Helper()
	if len(b) != 32 || !bytes.Equal(b[:24], make([]byte, 24)) {
		t.Fatalf("noncanonical uint256 %x", b)
	}
	return binary.BigEndian.Uint64(b[24:])
}
func mcLB0VerifyAssertError(t *testing.T, run func() (Result, error), sig string, want ...uint64) Result {
	t.Helper()
	r, e := run()
	if e == nil || !strings.Contains(e.Error(), "execution reverted") || r.ExceptionClass != "" || r.GasUsed == 0 || len(r.RevertData) != 4+32*len(want) || !bytes.Equal(r.RevertData[:4], crypto.Keccak256([]byte(sig))[:4]) {
		t.Fatalf("result/error=%+v/%v data=%x, want exact %s%v", r, e, r.RevertData, sig, want)
	}
	for i, w := range want {
		if got := mcLB0VerifyWord(t, r.RevertData[4+32*i:36+32*i]); got != w {
			t.Fatalf("%s word[%d]=%d want %d data=%x", sig, i, got, w, r.RevertData)
		}
	}
	return r
}
func mcLB0VerifyAssertStringConstantError(t *testing.T, run func() (Result, error), code, classIndex, cpIndex, offset uint64) Result {
	t.Helper()
	return mcLB0VerifyAssertError(t, run, "StringConstantError(uint256,uint256,uint256,uint256)", code, classIndex, cpIndex, offset)
}
