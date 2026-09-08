// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"testing"
	"time"
)

const (
	verifyM5cbGasLimit         = uint64(220_000_000)
	verifyM5cbCapacityGasLimit = uint64(320_000_000)
)

// These verifier-only probes compile only bounded, trusted Java 8 inputs. The
// host JVM is an oracle, never an execution fallback. Finite values, infinities,
// and signed zero are checked bit-for-bit. Signaling NaNs are deliberately not
// asserted against every JVM: some JVM/hardware paths quiet them. EVM-only
// probes separately require raw payload preservation and the frozen canonical
// conversion-NaN policy.

func TestVerifyM5cbFiveBootstrapImagesAreExactAndReproducible(t *testing.T) {
	images := []struct {
		name, source, hash string
		size               int
	}{
		{"Object", "package java.lang; public class Object { public Object() {} }\n", "af9136af3be2c44ce120ac403beccb8b1cc963fc83dc1457e63f8b69dd497fe0", 95},
		{"Cloneable", "package java.lang; public interface Cloneable {}\n", "07930c21cec8dfc8a031c04590af290511e2be6dbae7ad1282a2cfa00a06c457", 71},
		{"Serializable", "package java.io; public interface Serializable {}\n", "90bd3c397ef8d1f81a72b59b80c6a96ac158ac9fc97c95851d246eff8e66a70a", 72},
		{"Float", "package java.lang; public final class Float { private Float() {} public static native float intBitsToFloat(int bits); public static native int floatToRawIntBits(float value); }\n", "437d784b11d0b632017a94cc2c0d99b35cd93c39f49b98b0660e4316d9960dd4", 197},
		{"Double", "package java.lang; public final class Double { private Double() {} public static native double longBitsToDouble(long bits); public static native long doubleToRawLongBits(double value); }\n", "d9ac93be34df21e1ec5872e307f67b1301c0606c1ccd57ee6a61030b0aa45363", 202},
	}
	solidity, err := os.ReadFile("runtime/JVMSubsetInterpreter.sol")
	if err != nil {
		t.Fatal(err)
	}
	for _, image := range images {
		t.Run(image.name, func(t *testing.T) {
			pkg := "java/lang"
			if image.name == "Serializable" {
				pkg = "java/io"
			}
			sourcePath := filepath.Join("runtime", "bootstrap", image.name+".java")
			hexPath := filepath.Join("runtime", "bootstrap", image.name+".class.hex")
			checkedSource, err := os.ReadFile(sourcePath)
			if err != nil || string(checkedSource) != image.source {
				t.Fatalf("checked source=%q error=%v", checkedSource, err)
			}
			checkedHex, err := os.ReadFile(hexPath)
			if err != nil {
				t.Fatal(err)
			}
			checked, err := hex.DecodeString(strings.TrimSpace(string(checkedHex)))
			if err != nil {
				t.Fatal(err)
			}
			dir := t.TempDir()
			src := filepath.Join(dir, filepath.FromSlash(pkg), image.name+".java")
			if err := os.MkdirAll(filepath.Dir(src), 0o700); err != nil {
				t.Fatal(err)
			}
			if err := os.WriteFile(src, []byte(image.source), 0o600); err != nil {
				t.Fatal(err)
			}
			out := filepath.Join(dir, "out")
			ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
			defer cancel()
			output, err := exec.CommandContext(ctx, "javac", "-J-Xmx64m", "--release", "8", "-g:none", "-Xlint:-options", "-d", out, src).CombinedOutput()
			if err != nil {
				t.Fatalf("bounded bootstrap javac: %v\n%s", err, output)
			}
			got, err := os.ReadFile(filepath.Join(out, filepath.FromSlash(pkg), image.name+".class"))
			if err != nil {
				t.Fatal(err)
			}
			digest := sha256.Sum256(got)
			if len(got) != image.size || hex.EncodeToString(digest[:]) != image.hash || !bytes.Equal(got, checked) {
				t.Fatalf("bytes/hash=%d/%x want %d/%s and checked hex identity", len(got), digest, image.size, image.hash)
			}
			if !bytes.Contains(solidity, []byte(hex.EncodeToString(got))) {
				t.Fatal("exact image is not embedded in the EVM runtime source")
			}
		})
	}
}

func TestVerifyM5cbConstantPoolBitsHolesFieldsCallsAndCache(t *testing.T) {
	classes := verifyM5cbCompile(t, map[string]string{
		"ieeetransport/I.java":    `package ieeetransport; public interface I { int mix(double d,long j,float f,int i); }`,
		"ieeetransport/Base.java": `package ieeetransport; public class Base { float hidden=Float.intBitsToFloat(0x80000000); }`,
		"ieeetransport/Box.java": `package ieeetransport; public final class Box extends Base implements I {
			static final float CF=1.5f; static final double CD=-0.0d; static float sf; static double sd; static float zsf; static double zsd;
			final float f; final double d; float hidden=Float.intBitsToFloat(0x3f800000); float zf; double zd; Box(float x,double y){f=x;d=y;}
			static { sf=Float.intBitsToFloat(0x7fc12345); sd=Double.longBitsToDouble(0x8000000000000000L); }
			static float fs(float x){return x;} static double ds(double x){return x;} static float cfv(){return CF;} static double cdv(){return CD;}
			static void writeSF(float x){sf=x;} static void writeHidden(Box b,float x){b.hidden=x;}
			public int mix(double x,long j,float y,int i){return Float.floatToRawIntBits(y)^i^(int)Double.doubleToRawLongBits(x)^(int)j;}
		}`,
		"ieeetransport/Root.java": `package ieeetransport; public final class Root {
			static int fold(long x){return (int)(x^(x>>>32));}
			public static int constants(){return Float.floatToRawIntBits(Box.cfv())^fold(Double.doubleToRawLongBits(Box.cdv()));}
			public static int fields(int x){Box b=new Box(Float.intBitsToFloat(x),Double.longBitsToDouble(0x3ff0000000000000L));
				return Float.floatToRawIntBits(Box.fs(b.f))^fold(Double.doubleToRawLongBits(Box.ds(b.d)))^Float.floatToRawIntBits(b.hidden)^Float.floatToRawIntBits(((Base)b).hidden);}
			public static int defaults(){Box b=new Box(0f,0d);return Float.floatToRawIntBits(b.zf)^fold(Double.doubleToRawLongBits(b.zd))^Float.floatToRawIntBits(Box.zsf)^fold(Double.doubleToRawLongBits(Box.zsd));}
			public static int writeStatic(int x){Box.writeSF(Float.intBitsToFloat(x));return 0;} public static int writeInstance(int x){Box b=new Box(0f,0d);Box.writeHidden(b,Float.intBitsToFloat(x));return 0;}
			public static int statics(){return Float.floatToRawIntBits(Box.sf)^fold(Double.doubleToRawLongBits(Box.sd));}
			public static int iface(int x){I b=new Box(Float.intBitsToFloat(x),Double.longBitsToDouble(0x4000000000000000L));
				return b.mix(Double.longBitsToDouble(0x4008000000000000L),0x100000002L,Float.intBitsToFloat(0x3f000000),7);}
		}`,
	}, "ieeetransport/I", "ieeetransport/Base", "ieeetransport/Box", "ieeetransport/Root")
	box := parseStaticsClass(t, classes["ieeetransport/Box"])
	floats, doubles := verifyM5cbCPIndices(box, 4), verifyM5cbCPIndices(box, 6)
	if len(floats) == 0 || len(doubles) == 0 {
		t.Fatalf("CP4=%v CP6=%v want both exact IEEE constant kinds", floats, doubles)
	}
	for _, index := range doubles {
		if int(index)+1 >= box.cpCount || box.entries[index+1].tag != 0 {
			t.Fatalf("CONSTANT_Double #%d does not reserve unusable #%d", index, index+1)
		}
		if int(index)+2 < box.cpCount && box.entries[index+2].tag != 0 && box.entries[index+2].offset != box.entries[index].offset+9 {
			t.Fatalf("entry after CP6 serialized a hole at #%d", index)
		}
	}
	cf := verifyM5cbFieldConstantIndex(t, box, "CF", "F")
	cd := verifyM5cbFieldConstantIndex(t, box, "CD", "D")
	if box.entry(t, cf).tag != 4 || binary.BigEndian.Uint32(box.data[box.entry(t, cf).offset+1:]) != 0x3fc00000 {
		t.Fatalf("float ConstantValue tag/bits not exact")
	}
	if box.entry(t, cd).tag != 6 || binary.BigEndian.Uint64(box.data[box.entry(t, cd).offset+1:]) != 0x8000000000000000 {
		t.Fatalf("double ConstantValue tag/bits not exact")
	}

	root := parseStaticsClass(t, classes["ieeetransport/Root"])
	iface := root.method(t, "iface", "(I)I")
	pc := verifyM5cbMemberPC(t, root, iface, 0xb9, 11, "mix", "(DJFI)I")
	if got := iface.code[pc+3 : pc+5]; !bytes.Equal(got, []byte{7, 0}) {
		t.Fatalf("invokeinterface (DJFI)I suffix=%x want seven argument/receiver words and zero", got)
	}
	bundle := verifyM5cbBundle(classes)
	for _, tc := range []struct {
		method string
		args   []int32
	}{
		{"constants", nil}, {"fields", []int32{verifyM5cbI32(0x80000000)}},
		{"fields", []int32{verifyM5cbI32(0x7fc12345)}}, {"defaults", nil}, {"statics", nil}, {"iface", []int32{3}},
	} {
		want := verifyM5cbJava8Int(t, bundle, "ieeetransport.Root", tc.method, tc.args)
		verifyM5cbAssertValue(t, func() (Result, error) {
			return RunClasses(bundle, "ieeetransport/Root", tc.method, tc.args, verifyM5cbGasLimit)
		}, want)
	}
	// Repeat an initialization-bearing invocation: field caches and statics must
	// preserve type/bits within a run but reset for every independent VM call.
	for i := 0; i < 2; i++ {
		verifyM5cbAssertValue(t, func() (Result, error) {
			return RunClasses(bundle, "ieeetransport/Root", "statics", nil, verifyM5cbGasLimit)
		}, verifyM5cbI32(0xffc12345))
	}

	badCount := verifyM5cbMutate(t, classes["ieeetransport/Root"], func(_ []byte, c staticsClass) {
		m := c.method(t, "iface", "(I)I")
		p := verifyM5cbMemberPC(t, c, m, 0xb9, 11, "mix", "(DJFI)I")
		m.code[p+3] = 6
	})
	badBundle := verifyM5cbReplaceClass(classes, "ieeetransport/Root", badCount)
	verifyM5cbAssertError(t, func() (Result, error) {
		return RunClasses(verifyM5cbBundle(badBundle), "ieeetransport/Root", "iface", []int32{1}, verifyM5cbGasLimit)
	}, "CallError(uint256,uint256)", 1, uint64(pc))

	for _, tc := range []struct{ field, descriptor string }{{"CF", "F"}, {"CD", "D"}} {
		bad := verifyM5cbMutate(t, classes["ieeetransport/Box"], func(raw []byte, c staticsClass) {
			index := verifyM5cbFieldConstantIndex(t, c, tc.field, tc.descriptor)
			if tc.descriptor == "F" {
				raw[c.entry(t, index).offset] = 3
			} else {
				raw[c.entry(t, index).offset] = 5
			}
		})
		parsed := parseStaticsClass(t, bad)
		badClasses := verifyM5cbReplaceClass(classes, "ieeetransport/Box", bad)
		verifyM5cbAssertError(t, func() (Result, error) {
			return RunClasses(verifyM5cbBundle(badClasses), "ieeetransport/Root", "constants", nil, verifyM5cbGasLimit)
		}, "FieldError(uint256,uint256)", 5, uint64(parsed.field(t, tc.field, tc.descriptor).index))
	}
	for _, tc := range []struct {
		field, descriptor, setter, setterDescriptor, root string
		opcode                                            byte
	}{
		{"sf", "F", "writeSF", "(F)V", "writeStatic", 0xb3},
		{"hidden", "F", "writeHidden", "(Lieeetransport/Box;F)V", "writeInstance", 0xb5},
	} {
		bad := verifyM5cbMutate(t, classes["ieeetransport/Box"], func(raw []byte, c staticsClass) {
			field := c.field(t, tc.field, tc.descriptor)
			binary.BigEndian.PutUint16(raw[field.accessOffset:], field.access|accFinal)
		})
		parsed := parseStaticsClass(t, bad)
		putPC := verifyM5cbFieldPC(t, parsed, parsed.method(t, tc.setter, tc.setterDescriptor), tc.opcode, tc.field, tc.descriptor)
		badClasses := verifyM5cbReplaceClass(classes, "ieeetransport/Box", bad)
		verifyM5cbAssertError(t, func() (Result, error) {
			return RunClasses(verifyM5cbBundle(badClasses), "ieeetransport/Root", tc.root, []int32{1}, verifyM5cbGasLimit)
		}, "FieldError(uint256,uint256)", 4, uint64(putPC))
	}
}

func TestVerifyM5cbInstanceConstantValuesAreIgnored(t *testing.T) {
	classfile := verifyM5cbCompile(t, map[string]string{
		"VerifyM5cbInstanceCV.java": `public final class VerifyM5cbInstanceCV {
			final float f=1.5f; final double d=-0.0d; float mutableF; double mutableD; static int fold(long x){return (int)(x^(x>>>32));}
			int read(){return Float.floatToRawIntBits(mutableF)^fold(Double.doubleToRawLongBits(mutableD));}
			public static int run(){return new VerifyM5cbInstanceCV().read();}
		}`,
	}, "VerifyM5cbInstanceCV")["VerifyM5cbInstanceCV"]
	parsed := parseStaticsClass(t, classfile)
	for _, tc := range []struct{ field, descriptor string }{{"f", "F"}, {"d", "D"}} {
		index := verifyM5cbFieldConstantIndex(t, parsed, tc.field, tc.descriptor)
		wantTag := byte(4)
		if tc.descriptor == "D" {
			wantTag = 6
		}
		if parsed.entry(t, index).tag != wantTag {
			t.Fatalf("instance %s ConstantValue tag=%d want %d", tc.field, parsed.entry(t, index).tag, wantTag)
		}
	}
	mutated := verifyM5cbMutate(t, classfile, func(_ []byte, c staticsClass) {
		ctor := c.method(t, "<init>", "()V")
		read := c.method(t, "read", "()I")
		for _, tc := range []struct{ field, mutable, descriptor string }{{"f", "mutableF", "F"}, {"d", "mutableD", "D"}} {
			put := verifyM5cbFieldPC(t, c, ctor, 0xb5, tc.field, tc.descriptor)
			finalRef := binary.BigEndian.Uint16(ctor.code[put+1:])
			get := verifyM5cbFieldPC(t, c, read, 0xb4, tc.mutable, tc.descriptor)
			binary.BigEndian.PutUint16(read.code[get+1:], finalRef)
			constant := verifyM5cbPreviousInstruction(t, ctor.code, put)
			aload := verifyM5cbPreviousInstruction(t, ctor.code, constant)
			if ctor.code[aload] != 0x2a {
				t.Fatalf("unexpected constructor assignment for %s: %x", tc.field, ctor.code)
			}
			for pc := aload; pc < put+3; pc++ {
				ctor.code[pc] = 0
			}
		}
	})
	mutated = verifyM5cbMajor49(mutated)
	verifyM5cbJava8Outcome(t, [][]byte{mutated}, "VerifyM5cbInstanceCV", "run", nil, 0)
	verifyM5cbAssertValue(t, func() (Result, error) { return Run(mutated, "run", nil, verifyM5cbGasLimit) }, 0)
}

func TestVerifyM5cbLdcTagMatrixHolesAndTypedConstantCalls(t *testing.T) {
	base := verifyM5cbCompile(t, map[string]string{
		"VerifyM5cbCP.java": `public final class VerifyM5cbCP {
			static int fr(float x){return Float.floatToRawIntBits(x);} static int dr(double x){return (int)(Double.doubleToRawLongBits(x)>>>32);}
			public static int refs(){return fr(1.5f)^dr(-0.0d);} public static int padding(){int x=0;` + strings.Repeat("x=x+1;", 80) + `return x;}
		}`,
	}, "VerifyM5cbCP")["VerifyM5cbCP"]
	c := parseStaticsClass(t, base)
	floats, doubles := verifyM5cbCPIndices(c, 4), verifyM5cbCPIndices(c, 6)
	if len(floats) == 0 || len(doubles) == 0 {
		t.Fatalf("CP4=%v CP6=%v want method-only constants", floats, doubles)
	}
	// These entries are deliberately not referenced by ConstantValue fields.
	// Retagging them therefore reaches the intended typed call guard rather
	// than failing earlier during field parsing (covered separately above).
	fi, di := floats[0], doubles[0]
	fr := verifyM5cbFindMethodref(t, c, "VerifyM5cbCP", "fr", "(F)I")
	dr := verifyM5cbFindMethodref(t, c, "VerifyM5cbCP", "dr", "(D)I")
	valid := []struct {
		name string
		code []byte
		want int32
	}{
		{"ldc-float", []byte{0x12, byte(fi), 0xb8, byte(fr >> 8), byte(fr), 0xac}, verifyM5cbI32(0x3fc00000)},
		{"ldc-w-float", []byte{0x13, byte(fi >> 8), byte(fi), 0xb8, byte(fr >> 8), byte(fr), 0xac}, verifyM5cbI32(0x3fc00000)},
		{"ldc2-double", []byte{0x14, byte(di >> 8), byte(di), 0xb8, byte(dr >> 8), byte(dr), 0xac}, verifyM5cbI32(0x80000000)},
	}
	if fi > 255 {
		valid = valid[1:]
	}
	for _, tc := range valid {
		t.Run(tc.name, func(t *testing.T) {
			classfile := verifyM5cbRewriteCode(t, base, "padding", "()I", tc.code, 2, 1)
			verifyM5cbJava8Outcome(t, [][]byte{verifyM5cbMajor49(classfile)}, "VerifyM5cbCP", "padding", nil, tc.want)
			verifyM5cbAssertValue(t, func() (Result, error) { return Run(classfile, "padding", nil, verifyM5cbGasLimit) }, tc.want)
		})
	}
	invalid := []struct {
		name string
		code []byte
	}{
		{"ldc-w-double", []byte{0x13, byte(di >> 8), byte(di), 0xac}},
		{"ldc2-float", []byte{0x14, byte(fi >> 8), byte(fi), 0xac}},
		{"ldc2-double-hole", []byte{0x14, byte((di + 1) >> 8), byte(di + 1), 0xac}},
		{"ldc-zero", []byte{0x12, 0, 0xac}},
	}
	for _, tc := range invalid {
		t.Run(tc.name, func(t *testing.T) {
			classfile := verifyM5cbRewriteCode(t, base, "padding", "()I", tc.code, 2, 1)
			verifyM5cbAssertError(t, func() (Result, error) { return Run(classfile, "padding", nil, verifyM5cbGasLimit) },
				"BytecodeError(uint256,uint256)", 13, 0)
		})
	}
	for _, tc := range []struct {
		name  string
		index uint16
		tag   byte
		code  []byte
		pc    uint64
	}{
		// ldc_w is valid at every CP index and avoids silently skipping the
		// float/int kind check if this generated pool grows beyond index 255.
		{"float-retagged-int", fi, 3, []byte{0x13, byte(fi >> 8), byte(fi), 0xb8, byte(fr >> 8), byte(fr), 0xac}, 3},
		{"double-retagged-long", di, 5, []byte{0x14, byte(di >> 8), byte(di), 0xb8, byte(dr >> 8), byte(dr), 0xac}, 3},
	} {
		t.Run(tc.name, func(t *testing.T) {
			bad := verifyM5cbMutate(t, base, func(raw []byte, parsed staticsClass) { raw[parsed.entry(t, tc.index).offset] = tc.tag })
			bad = verifyM5cbRewriteCode(t, bad, "padding", "()I", tc.code, 2, 1)
			verifyM5cbAssertError(t, func() (Result, error) { return Run(bad, "padding", nil, verifyM5cbGasLimit) },
				"BytecodeError(uint256,uint256)", 14, tc.pc)
		})
	}
}

func TestVerifyM5cbConversionsKnownRNETiesSaturationAndGradualUnderflow(t *testing.T) {
	classfile := verifyM5cbConversionClass(t)
	tests := []struct {
		name, method string
		args         []int32
		want         int32
		java8        bool
	}{
		{"i2f-zero", "i2f", []int32{0}, verifyM5cbI32(0x00000000), true},
		{"i2f-negzero-unavailable", "i2f", []int32{-1}, verifyM5cbI32(0xbf800000), true},
		{"i2f-before-2p24", "i2f", []int32{16777215}, verifyM5cbI32(0x4b7fffff), true},
		{"i2f-half-even", "i2f", []int32{16777217}, verifyM5cbI32(0x4b800000), true},
		{"i2f-after-half", "i2f", []int32{16777218}, verifyM5cbI32(0x4b800001), true},
		{"i2f-max", "i2f", []int32{2147483647}, verifyM5cbI32(0x4f000000), true},
		{"i2f-min", "i2f", []int32{-2147483648}, verifyM5cbI32(0xcf000000), true},
		{"i2d-max-hi", "i2dHi", []int32{2147483647}, verifyM5cbI32(0x41dfffff), true},
		{"i2d-max-lo", "i2dLo", []int32{2147483647}, verifyM5cbI32(0xffc00000), true},
		{"i2d-min-hi", "i2dHi", []int32{-2147483648}, verifyM5cbI32(0xc1e00000), true},
		{"j2d-2p53m1-lo", "l2dLo", []int32{0x001fffff, -1}, -1, true},
		{"j2d-2p53-half-hi", "l2dHi", []int32{0x00200000, 1}, verifyM5cbI32(0x43400000), true},
		{"j2d-2p53-half-lo", "l2dLo", []int32{0x00200000, 1}, 0, true},
		{"j2d-max-hi", "l2dHi", []int32{2147483647, -1}, verifyM5cbI32(0x43e00000), true},
		{"j2d-min-hi", "l2dHi", []int32{-2147483648, 0}, verifyM5cbI32(0xc3e00000), true},
		{"j2f-max", "l2f", []int32{2147483647, -1}, verifyM5cbI32(0x5f000000), true},
		{"f2i-qnan", "f2i", []int32{verifyM5cbI32(0x7fc12345)}, 0, true},
		{"f2i-posinf", "f2i", []int32{verifyM5cbI32(0x7f800000)}, 2147483647, true},
		{"f2i-neginf", "f2i", []int32{verifyM5cbI32(0xff800000)}, -2147483648, true},
		{"f2i-pos-fraction", "f2i", []int32{verifyM5cbI32(0x3ff33333)}, 1, true},
		{"f2i-neg-fraction", "f2i", []int32{verifyM5cbI32(0xbff33333)}, -1, true},
		{"f2i-saturate", "f2i", []int32{verifyM5cbI32(0x4f000000)}, 2147483647, true},
		{"d2i-qnan", "d2i", []int32{verifyM5cbI32(0x7ff81234), 0x56789abc}, 0, true},
		{"d2i-posinf", "d2i", []int32{verifyM5cbI32(0x7ff00000), 0}, 2147483647, true},
		{"d2i-neginf", "d2i", []int32{verifyM5cbI32(0xfff00000), 0}, -2147483648, true},
		{"d2i-negative-fraction", "d2i", []int32{verifyM5cbI32(0xbffe6666), verifyM5cbI32(0x66666666)}, -1, true},
		{"f2l-fraction-hi", "f2lHi", []int32{verifyM5cbI32(0x3ff33333)}, 0, true},
		{"f2l-fraction-lo", "f2lLo", []int32{verifyM5cbI32(0x3ff33333)}, 1, true},
		{"f2l-nan", "f2lLo", []int32{verifyM5cbI32(0x7fc12345)}, 0, true},
		{"f2l-max-hi", "f2lHi", []int32{verifyM5cbI32(0x7f7fffff)}, 2147483647, true},
		{"f2l-max-lo", "f2lLo", []int32{verifyM5cbI32(0x7f7fffff)}, -1, true},
		{"d2l-below-2p63-hi", "d2lHi", []int32{verifyM5cbI32(0x43dfffff), -1}, 2147483647, true},
		{"d2l-below-2p63-lo", "d2lLo", []int32{verifyM5cbI32(0x43dfffff), -1}, -1024, true},
		{"d2l-negative-fraction", "d2lLo", []int32{verifyM5cbI32(0xbffe6666), verifyM5cbI32(0x66666666)}, -1, true},
		{"d2l-min-hi", "d2lHi", []int32{verifyM5cbI32(0xc3e00000), 0}, -2147483648, true},
		{"d2l-min-lo", "d2lLo", []int32{verifyM5cbI32(0xc3e00000), 0}, 0, true},
		{"d2l-pos-saturate-hi", "d2lHi", []int32{verifyM5cbI32(0x43e00000), 0}, 2147483647, true},
		{"d2l-pos-saturate-lo", "d2lLo", []int32{verifyM5cbI32(0x43e00000), 0}, -1, true},
		{"f2d-minsub-hi", "f2dHi", []int32{1}, verifyM5cbI32(0x36a00000), true},
		{"f2d-minsub-lo", "f2dLo", []int32{1}, 0, true},
		// A normal float below 1.0 catches unsigned exponent rebiasing done in
		// the wrong order (59-127+1023 previously caused Solidity panic 0x11).
		{"f2d-half-hi", "f2dHi", []int32{verifyM5cbI32(0x3f000000)}, verifyM5cbI32(0x3fe00000), true},
		{"f2d-half-lo", "f2dLo", []int32{verifyM5cbI32(0x3f000000)}, 0, true},
		{"f2d-max-hi", "f2dHi", []int32{verifyM5cbI32(0x7f7fffff)}, verifyM5cbI32(0x47efffff), true},
		{"f2d-max-lo", "f2dLo", []int32{verifyM5cbI32(0x7f7fffff)}, verifyM5cbI32(0xe0000000), true},
		{"f2d-negative-zero-hi", "f2dHi", []int32{verifyM5cbI32(0x80000000)}, verifyM5cbI32(0x80000000), true},
		{"d2f-half-to-zero", "d2f", []int32{verifyM5cbI32(0x36900000), 0}, 0, true},
		{"d2f-above-half", "d2f", []int32{verifyM5cbI32(0x36900000), 1}, 1, true},
		{"d2f-minsub", "d2f", []int32{verifyM5cbI32(0x36a00000), 0}, 1, true},
		{"d2f-largest-subnormal", "d2f", []int32{verifyM5cbI32(0x380fffff), verifyM5cbI32(0xc0000000)}, verifyM5cbI32(0x007fffff), true},
		{"d2f-boundary-below-half", "d2f", []int32{verifyM5cbI32(0x380fffff), verifyM5cbI32(0xdfffffff)}, verifyM5cbI32(0x007fffff), true},
		{"d2f-boundary-half-even", "d2f", []int32{verifyM5cbI32(0x380fffff), verifyM5cbI32(0xe0000000)}, verifyM5cbI32(0x00800000), true},
		{"d2f-minnormal", "d2f", []int32{verifyM5cbI32(0x38100000), 0}, verifyM5cbI32(0x00800000), true},
		{"d2f-normal-rounding-carry", "d2f", []int32{verifyM5cbI32(0x3fffffff), verifyM5cbI32(0xf0000000)}, verifyM5cbI32(0x40000000), true},
		{"d2f-max", "d2f", []int32{verifyM5cbI32(0x47efffff), verifyM5cbI32(0xe0000000)}, verifyM5cbI32(0x7f7fffff), true},
		{"d2f-overflow-half", "d2f", []int32{verifyM5cbI32(0x47efffff), verifyM5cbI32(0xf0000000)}, verifyM5cbI32(0x7f800000), true},
		{"d2f-negative-half-underflow", "d2f", []int32{verifyM5cbI32(0xb6900000), 0}, verifyM5cbI32(0x80000000), true},
		{"d2f-negative-zero", "d2f", []int32{verifyM5cbI32(0x80000000), 0}, verifyM5cbI32(0x80000000), true},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			if tc.java8 {
				verifyM5cbJava8Outcome(t, [][]byte{classfile}, "VerifyM5cbConversions", tc.method, tc.args, tc.want)
			}
			verifyM5cbAssertValue(t, func() (Result, error) {
				return Run(classfile, tc.method, tc.args, verifyM5cbGasLimit)
			}, tc.want)
		})
	}

	// Java does not specify conversion NaN payloads. The EVM policy is instead
	// deterministic and canonical; do not normalize any finite or zero result.
	for _, tc := range []struct {
		method string
		args   []int32
		want   int32
	}{
		{"f2dHi", []int32{verifyM5cbI32(0xff812345)}, verifyM5cbI32(0x7ff80000)},
		{"f2dLo", []int32{verifyM5cbI32(0xff812345)}, 0},
		{"d2f", []int32{verifyM5cbI32(0xfff01234), 0x56789abc}, verifyM5cbI32(0x7fc00000)},
	} {
		verifyM5cbAssertValue(t, func() (Result, error) { return Run(classfile, tc.method, tc.args, verifyM5cbGasLimit) }, tc.want)
	}
}

func TestVerifyM5cbComparisonsNegationAndRawNaNPayloadPolicy(t *testing.T) {
	base := verifyM5cbCompile(t, map[string]string{
		"VerifyM5cbRaw.java": `public final class VerifyM5cbRaw {
			static float fb(int x){return Float.intBitsToFloat(x);} static double db(int h,int l){return Double.longBitsToDouble(((long)h<<32)|(l&0xffffffffL));}
			static int raw(float x){return Float.floatToRawIntBits(x);} static long draw(double x){return Double.doubleToRawLongBits(x);} static int useDb(int h,int l){return (int)draw(db(h,l));}
			public static int fcmp(int a,int b){int x=0;` + strings.Repeat("x=x+1;", 80) + `return x;}
			public static int dcmp(int ah,int al,int bh,int bl){int x=0;` + strings.Repeat("x=x+1;", 80) + `return x;}
			public static int fneg(int x){int y=0;` + strings.Repeat("y=y+1;", 80) + `return y;}
			public static int dneg(int h,int l){int y=0;` + strings.Repeat("y=y+1;", 80) + `return y;}
		}`,
	}, "VerifyM5cbRaw")["VerifyM5cbRaw"]
	c := parseStaticsClass(t, base)
	fbRef := verifyM5cbCallRef(t, c, c.method(t, "fb", "(I)F"), "intBitsToFloat", "(I)F")
	dbCall := c.method(t, "db", "(II)D")
	dbRef := verifyM5cbCallRef(t, c, dbCall, "longBitsToDouble", "(J)D")
	// For raw snippets call the ordinary same-class db helper, not the native
	// (J)D binding directly, so external double bits remain two int root words.
	dbSelfRef := verifyM5cbFindMethodref(t, c, "VerifyM5cbRaw", "db", "(II)D")
	floatRawRef := verifyM5cbFindMethodref(t, c, "java/lang/Float", "floatToRawIntBits", "(F)I")
	doubleRawRef := verifyM5cbFindMethodref(t, c, "java/lang/Double", "doubleToRawLongBits", "(D)J")
	_ = dbRef

	fclass := func(op byte) []byte {
		code := []byte{0x1a, 0xb8, byte(fbRef >> 8), byte(fbRef), 0x1b, 0xb8, byte(fbRef >> 8), byte(fbRef), op, 0xac}
		return verifyM5cbRewriteCode(t, base, "fcmp", "(II)I", code, 2, 2)
	}
	dclass := func(op byte) []byte {
		code := []byte{0x1a, 0x1b, 0xb8, byte(dbSelfRef >> 8), byte(dbSelfRef), 0x1c, 0x1d, 0xb8, byte(dbSelfRef >> 8), byte(dbSelfRef), op, 0xac}
		return verifyM5cbRewriteCode(t, base, "dcmp", "(IIII)I", code, 4, 4)
	}
	comparisons := []struct {
		name, method string
		class        []byte
		args         []int32
		want         int32
	}{
		{"fcmpl-less", "fcmp", fclass(0x95), []int32{verifyM5cbI32(0xbf800000), verifyM5cbI32(0x3f800000)}, -1},
		{"fcmpg-greater", "fcmp", fclass(0x96), []int32{verifyM5cbI32(0x7f800000), verifyM5cbI32(0x7f7fffff)}, 1},
		{"fcmpl-signed-zero", "fcmp", fclass(0x95), []int32{verifyM5cbI32(0x80000000), 0}, 0},
		{"fcmpl-nan", "fcmp", fclass(0x95), []int32{verifyM5cbI32(0x7fc12345), 0}, -1},
		{"fcmpg-nan", "fcmp", fclass(0x96), []int32{0, verifyM5cbI32(0xffc12345)}, 1},
		{"dcmpl-less", "dcmp", dclass(0x97), []int32{verifyM5cbI32(0xbff00000), 0, verifyM5cbI32(0x3ff00000), 0}, -1},
		{"dcmpg-inf", "dcmp", dclass(0x98), []int32{verifyM5cbI32(0x7ff00000), 0, verifyM5cbI32(0x7fefffff), -1}, 1},
		{"dcmpl-signed-zero", "dcmp", dclass(0x97), []int32{verifyM5cbI32(0x80000000), 0, 0, 0}, 0},
		{"dcmpl-nan", "dcmp", dclass(0x97), []int32{verifyM5cbI32(0x7ff81234), 0x56789abc, 0, 0}, -1},
		{"dcmpg-nan", "dcmp", dclass(0x98), []int32{0, 0, verifyM5cbI32(0xfff81234), 0x56789abc}, 1},
	}
	for _, tc := range comparisons {
		t.Run(tc.name, func(t *testing.T) {
			// Quiet-NaN patterns are suitable for exact Java 8 comparison outcomes;
			// comparisons do not expose their payload.
			verifyM5cbJava8Outcome(t, [][]byte{verifyM5cbMajor49(tc.class)}, "VerifyM5cbRaw", tc.method, tc.args, tc.want)
			verifyM5cbAssertValue(t, func() (Result, error) { return Run(tc.class, tc.method, tc.args, verifyM5cbGasLimit) }, tc.want)
		})
	}

	fnegCode := []byte{0x1a, 0xb8, byte(fbRef >> 8), byte(fbRef), 0x76, 0xb8, byte(floatRawRef >> 8), byte(floatRawRef), 0xac}
	fnegClass := verifyM5cbRewriteCode(t, base, "fneg", "(I)I", fnegCode, 1, 1)
	dnegCode := []byte{0x1a, 0x1b, 0xb8, byte(dbSelfRef >> 8), byte(dbSelfRef), 0x77, 0xb8, byte(doubleRawRef >> 8), byte(doubleRawRef), 0x10, 32, 0x7d, 0x88, 0xac}
	dnegClass := verifyM5cbRewriteCode(t, base, "dneg", "(II)I", dnegCode, 3, 2)
	for _, bits := range []uint32{0, 0x80000000, 0x7f800000, 0x7fc12345, 0x7f812345} {
		want := verifyM5cbI32(bits ^ 0x80000000)
		// The signaling case is EVM-only; requiring every host JVM to preserve it
		// through an F register would overstate Java portability.
		if bits != 0x7f812345 {
			verifyM5cbJava8Outcome(t, [][]byte{verifyM5cbMajor49(fnegClass)}, "VerifyM5cbRaw", "fneg", []int32{verifyM5cbI32(bits)}, want)
		}
		verifyM5cbAssertValue(t, func() (Result, error) {
			return Run(fnegClass, "fneg", []int32{verifyM5cbI32(bits)}, verifyM5cbGasLimit)
		}, want)
	}
	for _, tc := range []struct{ hi, lo, want int32 }{
		{0, 0, verifyM5cbI32(0x80000000)}, {verifyM5cbI32(0x80000000), 0, 0},
		{verifyM5cbI32(0x7ff81234), 0x56789abc, verifyM5cbI32(0xfff81234)},
		{verifyM5cbI32(0x7ff01234), 0x56789abc, verifyM5cbI32(0xfff01234)},
	} {
		verifyM5cbAssertValue(t, func() (Result, error) { return Run(dnegClass, "dneg", []int32{tc.hi, tc.lo}, verifyM5cbGasLimit) }, tc.want)
	}
}

func TestVerifyM5cbLocalsWideCategoryKindsStackCapacityAndReturns(t *testing.T) {
	base := verifyM5cbCompile(t, map[string]string{
		"VerifyM5cbSlots.java": `public final class VerifyM5cbSlots {
			static int fr(float x){return Float.floatToRawIntBits(x);} static int dr(double x){return (int)(Double.doubleToRawLongBits(x)>>>32);}
			static float rf(){return 1.0f;} static double rd(){return 1.0d;} public static int callRf(){return fr(rf());} public static int callRd(){return dr(rd());}
			public static float rootF(float x){return x;} public static double rootD(){return 0.0d;}
			public static int padding(){int x=0;` + strings.Repeat("x=x+1;", 400) + `return x;}
		}`,
	}, "VerifyM5cbSlots")["VerifyM5cbSlots"]
	c := parseStaticsClass(t, base)
	fr := verifyM5cbFindMethodref(t, c, "VerifyM5cbSlots", "fr", "(F)I")
	dr := verifyM5cbFindMethodref(t, c, "VerifyM5cbSlots", "dr", "(D)I")
	valid := []struct {
		name       string
		code       []byte
		maxS, maxL uint16
		want       int32
	}{
		{"float-short", []byte{0x0c, 0x45, 0x24, 0xb8, byte(fr >> 8), byte(fr), 0xac}, 1, 3, verifyM5cbI32(0x3f800000)},
		{"float-wide", []byte{0x0d, 0xc4, 0x38, 1, 4, 0xc4, 0x17, 1, 4, 0xb8, byte(fr >> 8), byte(fr), 0xac}, 1, 261, verifyM5cbI32(0x40000000)},
		{"double-odd-wide", []byte{0x0f, 0xc4, 0x39, 1, 3, 0xc4, 0x18, 1, 3, 0xb8, byte(dr >> 8), byte(dr), 0xac}, 2, 261, verifyM5cbI32(0x3ff00000)},
		// D and J share category-2 stack forms without sharing value kinds.
		{"pop2-double", []byte{0x0f, 0x58, 0x10, 7, 0xac}, 2, 1, 7},
		{"pop2-two-floats", []byte{0x0c, 0x0d, 0x58, 0x10, 7, 0xac}, 2, 1, 7},
		{"dup2-double", []byte{0x0f, 0x5c, 0x58, 0xb8, byte(dr >> 8), byte(dr), 0xac}, 4, 1, verifyM5cbI32(0x3ff00000)},
		{"dup-x2-double-float", []byte{0x0f, 0x0c, 0x5b, 0x57, 0xb8, byte(dr >> 8), byte(dr), 0x5f, 0x57, 0xac}, 4, 1, verifyM5cbI32(0x3ff00000)},
		{"dup2-x1-float-double", []byte{0x0c, 0x0f, 0x5d, 0x58, 0x57, 0xb8, byte(dr >> 8), byte(dr), 0xac}, 5, 1, verifyM5cbI32(0x3ff00000)},
		{"swap-two-floats", []byte{0x0c, 0x0d, 0x5f, 0xb8, byte(fr >> 8), byte(fr), 0x5f, 0x57, 0xac}, 2, 1, verifyM5cbI32(0x3f800000)},
		{"mixed-d-j-dup2x2", []byte{0x0f, 0x0a, 0x5e, 0x58, 0xb8, byte(dr >> 8), byte(dr), 0x5b, 0x57, 0x58, 0xac}, 6, 1, verifyM5cbI32(0x3ff00000)},
	}
	for _, tc := range valid {
		t.Run(tc.name, func(t *testing.T) {
			classfile := verifyM5cbRewriteCode(t, base, "padding", "()I", tc.code, tc.maxS, tc.maxL)
			verifyM5cbJava8Outcome(t, [][]byte{verifyM5cbMajor49(classfile)}, "VerifyM5cbSlots", "padding", nil, tc.want)
			verifyM5cbAssertValue(t, func() (Result, error) { return Run(classfile, "padding", nil, verifyM5cbGasLimit) }, tc.want)
		})
	}

	invalid := []struct {
		name       string
		code       []byte
		maxS, maxL uint16
		kind, pc   uint64
	}{
		{"dstore-range", []byte{0x0f, 0x47, 0x03, 0xac}, 2, 1, 8, 1},
		{"dload-uninitialized", []byte{0x26, 0xb8, byte(dr >> 8), byte(dr), 0xac}, 2, 2, 11, 0},
		{"double-tail-load", []byte{0x0f, 0x47, 0x27, 0xb8, byte(dr >> 8), byte(dr), 0xac}, 2, 3, 14, 2},
		{"double-as-long", []byte{0x0f, 0x47, 0x1e, 0x88, 0xac}, 2, 2, 14, 2},
		{"long-as-double", []byte{0x0a, 0x3f, 0x26, 0xb8, byte(dr >> 8), byte(dr), 0xac}, 2, 2, 14, 2},
		{"int-invalidates-double-tail", []byte{0x0f, 0x47, 0x04, 0x3c, 0x26, 0xb8, byte(dr >> 8), byte(dr), 0xac}, 2, 2, 11, 4},
		{"float-as-int", []byte{0x0c, 0x3b, 0x1a, 0xac}, 1, 1, 14, 1},
		{"reference-as-float", []byte{0x01, 0x43, 0x22, 0xb8, byte(fr >> 8), byte(fr), 0xac}, 1, 1, 14, 1},
		{"float-as-reference", []byte{0x0c, 0x4b, 0x03, 0xac}, 1, 1, 14, 1},
		{"double-max-stack-word", []byte{0x0f, 0x58, 0x03, 0xac}, 1, 1, 9, 0},
	}
	for _, tc := range invalid {
		t.Run(tc.name, func(t *testing.T) {
			classfile := verifyM5cbRewriteCode(t, base, "padding", "()I", tc.code, tc.maxS, tc.maxL)
			verifyM5cbAssertError(t, func() (Result, error) { return Run(classfile, "padding", nil, verifyM5cbGasLimit) },
				"BytecodeError(uint256,uint256)", tc.kind, tc.pc)
		})
	}

	verifyM5cbAssertMethodError(t, func() (Result, error) { return Run(base, "rootF", []int32{1}, verifyM5cbGasLimit) }, 11)
	verifyM5cbAssertMethodError(t, func() (Result, error) { return Run(base, "rootD", nil, verifyM5cbGasLimit) }, 11)
	for _, tc := range []struct {
		method, descriptor, root string
		from, to                 byte
	}{
		{"rf", "()F", "callRf", 0xae, 0xac}, {"rd", "()D", "callRd", 0xaf, 0xad},
	} {
		bad := verifyM5cbReplaceOpcode(t, base, tc.method, tc.descriptor, tc.from, tc.to, 1)
		pc := verifyM5cbInstructionPC(t, parseStaticsClass(t, bad).method(t, tc.method, tc.descriptor).code, tc.to, 0)
		verifyM5cbAssertError(t, func() (Result, error) { return Run(bad, tc.root, nil, verifyM5cbGasLimit) },
			"CallError(uint256,uint256)", 5, uint64(pc))
	}
}

func TestVerifyM5cbNativeRegistryExactBindingsInitializationCodeOverrideAndDepth(t *testing.T) {
	native := verifyM5cbCompile(t, map[string]string{
		"java/lang/Float.java": `package java.lang; public final class Float { public static int marker=initialize(); static int initialize(){return 9;} private Float(){} public static native float intBitsToFloat(int x); public static native int floatToRawIntBits(float x); }`,
		"NativeRoot.java": `public final class NativeRoot {
			static int recurse(int bits,int n){return n==0?Float.floatToRawIntBits(Float.intBitsToFloat(bits)):recurse(bits,n-1);}
			public static int run(int bits){return Float.floatToRawIntBits(Float.intBitsToFloat(bits))^Float.marker;}
			public static int depth(int bits,int n){int initialized=Float.marker;return recurse(bits,n)^initialized^initialized;}
		}`,
	}, "java/lang/Float", "NativeRoot")
	bundle := verifyM5cbBundle(native)
	verifyM5cbAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "NativeRoot", "run", []int32{verifyM5cbI32(0x7fc12345)}, verifyM5cbGasLimit)
	}, verifyM5cbI32(0x7fc1234c))
	verifyM5cbAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "NativeRoot", "depth", []int32{verifyM5cbI32(0x80000000), 4}, verifyM5cbGasLimit)
	}, verifyM5cbI32(0x80000000))
	// Float is initialized before recursion, isolating the native registry's one
	// entered-call depth accounting: root + 126 recursive Code frames leaves one
	// slot, while one more recursive frame makes the binding overflow the cap.
	verifyM5cbAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "NativeRoot", "depth", []int32{1, 125}, verifyM5cbGasLimit)
	}, 1)
	verifyM5cbAssertException(t, func() (Result, error) {
		return RunClasses(bundle, "NativeRoot", "depth", []int32{1, 126}, verifyM5cbGasLimit)
	}, "java.lang.StackOverflowError", 2)

	ordinary := verifyM5cbCompile(t, map[string]string{
		"java/lang/Float.java": `package java.lang; public final class Float { private Float(){} public static float intBitsToFloat(int x){return 1.0f;} public static int floatToRawIntBits(float x){return 77;} }`,
		"CodeRoot.java":        `public final class CodeRoot { public static int run(int x){return Float.floatToRawIntBits(Float.intBitsToFloat(x));} }`,
	}, "java/lang/Float", "CodeRoot")
	// A familiar canonical signature with ordinary Code is guest bytecode, not a
	// native interception hook.
	verifyM5cbAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM5cbBundle(ordinary), "CodeRoot", "run", []int32{123}, verifyM5cbGasLimit)
	}, 77)

	root := parseStaticsClass(t, native["NativeRoot"])
	callPC := verifyM5cbMemberPC(t, root, root.method(t, "run", "(I)I"), 0xb8, 10, "intBitsToFloat", "(I)F")
	for _, tc := range []struct {
		name string
		edit func(uint16) uint16
	}{
		{"private", func(f uint16) uint16 { return (f &^ accPublic) | accPrivate }},
		{"nonstatic", func(f uint16) uint16 { return f &^ accStatic }},
		{"abstract", func(f uint16) uint16 { return f | 0x0400 }},
		{"synchronized", func(f uint16) uint16 { return f | 0x0020 }},
	} {
		t.Run(tc.name, func(t *testing.T) {
			badFloat := verifyM5cbMutate(t, native["java/lang/Float"], func(raw []byte, c staticsClass) {
				m := c.method(t, "intBitsToFloat", "(I)F")
				binary.BigEndian.PutUint16(raw[m.accessOffset:], tc.edit(m.access))
			})
			bad := verifyM5cbReplaceClass(native, "java/lang/Float", badFloat)
			verifyM5cbAssertError(t, func() (Result, error) {
				return RunClasses(verifyM5cbBundle(bad), "NativeRoot", "run", []int32{1}, verifyM5cbGasLimit)
			}, "CallError(uint256,uint256)", 4, uint64(callPC))
		})
	}

	withNativeCode := verifyM5cbMutate(t, ordinary["java/lang/Float"], func(raw []byte, c staticsClass) {
		m := c.method(t, "intBitsToFloat", "(I)F")
		binary.BigEndian.PutUint16(raw[m.accessOffset:], m.access|accNative)
	})
	badCode := verifyM5cbReplaceClass(ordinary, "java/lang/Float", withNativeCode)
	codeRoot := parseStaticsClass(t, ordinary["CodeRoot"])
	codePC := verifyM5cbMemberPC(t, codeRoot, codeRoot.method(t, "run", "(I)I"), 0xb8, 10, "intBitsToFloat", "(I)F")
	verifyM5cbAssertError(t, func() (Result, error) {
		return RunClasses(verifyM5cbBundle(badCode), "CodeRoot", "run", []int32{1}, verifyM5cbGasLimit)
	}, "CallError(uint256,uint256)", 4, uint64(codePC))

	unknowns := []struct {
		name, owner, method string
		classes             map[string][]byte
	}{
		{"unknown-owner", "UnknownNative", "bits", verifyM5cbCompile(t, map[string]string{
			"UnknownNative.java": `public final class UnknownNative { public static native int bits(int x); }`,
			"UnknownRoot.java":   `public final class UnknownRoot { public static int run(int x){return UnknownNative.bits(x);} }`,
		}, "UnknownNative", "UnknownRoot")},
		{"canonical-owner-wrong-descriptor", "java/lang/Float", "intBitsToFloat", verifyM5cbCompile(t, map[string]string{
			"java/lang/Float.java": `package java.lang; public final class Float { private Float(){} public static native int intBitsToFloat(int x); }`,
			"UnknownRoot.java":     `public final class UnknownRoot { public static int run(int x){return Float.intBitsToFloat(x);} }`,
		}, "java/lang/Float", "UnknownRoot")},
	}
	for _, tc := range unknowns {
		t.Run(tc.name, func(t *testing.T) {
			unknownRoot := parseStaticsClass(t, tc.classes["UnknownRoot"])
			method := unknownRoot.method(t, "run", "(I)I")
			unknownPC := verifyM5cbMemberPC(t, unknownRoot, method, 0xb8, 10, tc.method, "(I)I")
			if got, want := binary.BigEndian.Uint16(method.code[unknownPC+1:]), verifyM5cbFindMethodref(t, unknownRoot, tc.owner, tc.method, "(I)I"); got != want {
				t.Fatalf("call Methodref=%d want owner-qualified #%d", got, want)
			}
			verifyM5cbAssertError(t, func() (Result, error) {
				return RunClasses(verifyM5cbBundle(tc.classes), "UnknownRoot", "run", []int32{1}, verifyM5cbGasLimit)
			}, "CallError(uint256,uint256)", 4, uint64(unknownPC))
		})
	}
}

func TestVerifyM5cbSixtyFourUserClassesAppendFiveInternalsAndDoubleUsesTwoWords(t *testing.T) {
	sources := make(map[string]string, 64)
	names := make([]string, 0, 64)
	sources["cap/Root.java"] = `package cap; public final class Root { public static int run(int hi,int lo){long x=((long)hi<<32)|(lo&0xffffffffL);return (int)Double.doubleToRawLongBits(Double.longBitsToDouble(x));} }`
	names = append(names, "cap/Root")
	for i := 0; i < 63; i++ {
		name := fmt.Sprintf("cap/C%02d", i)
		sources[name+".java"] = fmt.Sprintf("package cap; public final class C%02d {}", i)
		names = append(names, name)
	}
	classes := verifyM5cbCompile(t, sources, names...)
	if len(classes) != 64 {
		t.Fatalf("user classes=%d want unchanged cap 64", len(classes))
	}
	verifyM5cbAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM5cbBundle(classes), "cap/Root", "run", []int32{verifyM5cbI32(0x7ff81234), 0x56789abc}, verifyM5cbCapacityGasLimit)
	}, 0x56789abc)
}

func TestVerifyM5cbArithmeticAcceptedArraysAndOtherNativesStayRejected(t *testing.T) {
	classes := verifyM5cbCompile(t, map[string]string{
		"DeferredM5cb.java": `public final class DeferredM5cb {
			public static int arithmetic(int x){return Float.floatToRawIntBits(Float.intBitsToFloat(x)+1.0f);}
			public static int floatArray(){return new float[1].length;} public static int doubleArray(){return new double[1].length;}
			public static int other(int x){return Float.floatToIntBits(Float.intBitsToFloat(x));}
		}`,
	}, "DeferredM5cb")
	classfile := classes["DeferredM5cb"]
	parsed := parseStaticsClass(t, classfile)
	verifyM5cbJava8Outcome(t, [][]byte{classfile}, "DeferredM5cb", "arithmetic", []int32{1}, 1065353216)
	verifyM5cbAssertValue(t, func() (Result, error) {
		return Run(classfile, "arithmetic", []int32{1}, verifyM5cbGasLimit)
	}, 1065353216)
	for _, method := range []string{"floatArray", "doubleArray"} {
		code := parsed.method(t, method, "()I").code
		pc := verifyM5cbInstructionPC(t, code, 0xbc, 0)
		if code[pc+1] != 6 && code[pc+1] != 7 {
			t.Fatalf("%s atype=%d want F/D", method, code[pc+1])
		}
		verifyM5cbAssertValue(t, func() (Result, error) { return Run(classfile, method, nil, verifyM5cbGasLimit) }, 1)
	}
	otherPC := verifyM5cbMemberPC(t, parsed, parsed.method(t, "other", "(I)I"), 0xb8, 10, "floatToIntBits", "(F)I")
	verifyM5cbAssertError(t, func() (Result, error) { return Run(classfile, "other", []int32{1}, verifyM5cbGasLimit) },
		"CallError(uint256,uint256)", 3, uint64(otherPC))
}

// --- M5c-b verifier-only helpers ---

func verifyM5cbConversionClass(t *testing.T) []byte {
	t.Helper()
	return verifyM5cbCompile(t, map[string]string{
		"VerifyM5cbConversions.java": `public final class VerifyM5cbConversions {
			static long join(int h,int l){return ((long)h<<32)|(l&0xffffffffL);} static double d(int h,int l){return Double.longBitsToDouble(join(h,l));}
			static long db(double x){return Double.doubleToRawLongBits(x);} static float f(int x){return Float.intBitsToFloat(x);}
			public static int i2f(int x){return Float.floatToRawIntBits((float)x);} public static int i2dHi(int x){return (int)(db((double)x)>>>32);} public static int i2dLo(int x){return (int)db((double)x);}
			public static int l2f(int h,int l){return Float.floatToRawIntBits((float)join(h,l));} public static int l2dHi(int h,int l){return (int)(db((double)join(h,l))>>>32);} public static int l2dLo(int h,int l){return (int)db((double)join(h,l));}
			public static int f2i(int x){return (int)f(x);} public static int f2lHi(int x){return (int)(((long)f(x))>>>32);} public static int f2lLo(int x){return (int)(long)f(x);}
			public static int f2dHi(int x){return (int)(db((double)f(x))>>>32);} public static int f2dLo(int x){return (int)db((double)f(x));}
			public static int d2i(int h,int l){return (int)d(h,l);} public static int d2lHi(int h,int l){return (int)(((long)d(h,l))>>>32);} public static int d2lLo(int h,int l){return (int)(long)d(h,l);}
			public static int d2f(int h,int l){return Float.floatToRawIntBits((float)d(h,l));}
		}`,
	}, "VerifyM5cbConversions")["VerifyM5cbConversions"]
}

func verifyM5cbCompile(t *testing.T, sources map[string]string, internalNames ...string) map[string][]byte {
	t.Helper()
	return verifyM5baCompile(t, sources, internalNames...)
}

func verifyM5cbBundle(classes map[string][]byte) [][]byte {
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

func verifyM5cbReplaceClass(classes map[string][]byte, name string, replacement []byte) map[string][]byte {
	return verifyM5baReplaceClass(classes, name, replacement)
}

func verifyM5cbMutate(t *testing.T, original []byte, edit func([]byte, staticsClass)) []byte {
	t.Helper()
	return verifyM5baMutate(t, original, edit)
}

func verifyM5cbRewriteCode(t *testing.T, original []byte, name, descriptor string, code []byte, maxStack, maxLocals uint16) []byte {
	t.Helper()
	return verifyM5baRewriteCode(t, original, name, descriptor, code, maxStack, maxLocals)
}

func verifyM5cbReplaceOpcode(t *testing.T, original []byte, name, descriptor string, from, to byte, want int) []byte {
	t.Helper()
	return verifyM5baReplaceOpcode(t, original, name, descriptor, from, to, want)
}

func verifyM5cbCPIndices(c staticsClass, tag byte) []uint16 { return verifyM5baCPIndices(c, tag) }

func verifyM5cbFieldConstantIndex(t *testing.T, c staticsClass, name, descriptor string) uint16 {
	t.Helper()
	return verifyM5baFieldConstantIndex(t, c, name, descriptor)
}

func verifyM5cbFieldPC(t *testing.T, c staticsClass, m staticsMethod, opcode byte, name, descriptor string) int {
	t.Helper()
	return verifyM5baFieldPC(t, c, m, opcode, name, descriptor)
}

func verifyM5cbMemberPC(t *testing.T, c staticsClass, m staticsMethod, opcode, tag byte, name, descriptor string) int {
	t.Helper()
	return verifyM5baMemberPC(t, c, m, opcode, tag, name, descriptor)
}

func verifyM5cbPreviousInstruction(t *testing.T, code []byte, target int) int {
	t.Helper()
	return verifyM5baPreviousInstruction(t, code, target)
}

func verifyM5cbInstructionPC(t *testing.T, code []byte, opcode byte, occurrence int) int {
	t.Helper()
	return verifyM5baInstructionPC(t, code, opcode, occurrence)
}

func verifyM5cbCallRef(t *testing.T, c staticsClass, m staticsMethod, name, descriptor string) uint16 {
	t.Helper()
	pc := verifyM5cbMemberPC(t, c, m, 0xb8, 10, name, descriptor)
	return binary.BigEndian.Uint16(m.code[pc+1:])
}

func verifyM5cbFindMethodref(t *testing.T, c staticsClass, owner, name, descriptor string) uint16 {
	t.Helper()
	for index := 1; index < c.cpCount; index++ {
		e := c.entries[index]
		if e.tag != 10 {
			continue
		}
		classEntry := c.entry(t, c.u2(t, e.offset+1))
		if classEntry.tag != 7 || c.utf8[c.u2(t, classEntry.offset+1)] != owner {
			continue
		}
		nat := c.entry(t, c.u2(t, e.offset+3))
		if nat.tag == 12 && c.utf8[c.u2(t, nat.offset+1)] == name && c.utf8[c.u2(t, nat.offset+3)] == descriptor {
			return uint16(index)
		}
	}
	t.Fatalf("missing Methodref %s.%s%s", owner, name, descriptor)
	return 0
}

func verifyM5cbMajor49(classfile []byte) []byte { return verifyM5baMajor49(classfile) }

func verifyM5cbJava8Outcome(t *testing.T, bundle [][]byte, mainClass, method string, args []int32, want int32) {
	t.Helper()
	verifyM5baJava8Outcome(t, bundle, mainClass, method, args, "value="+strconv.FormatInt(int64(want), 10))
}

func verifyM5cbJava8Int(t *testing.T, bundle [][]byte, mainClass, method string, args []int32) int32 {
	t.Helper()
	return verifyM5baJava8Int(t, bundle, mainClass, method, args)
}

func verifyM5cbAssertValue(t *testing.T, run func() (Result, error), want int32) {
	t.Helper()
	verifyM5baAssertValue(t, run, want)
}

func verifyM5cbAssertException(t *testing.T, run func() (Result, error), want string, kind byte) {
	t.Helper()
	verifyM5baAssertException(t, run, want, kind)
}

func verifyM5cbAssertError(t *testing.T, run func() (Result, error), signature string, code, location uint64) {
	t.Helper()
	verifyM5baAssertError(t, run, signature, code, location)
}

func verifyM5cbAssertMethodError(t *testing.T, run func() (Result, error), code uint64) {
	t.Helper()
	verifyM5baAssertMethodError(t, run, code)
}

func verifyM5cbI32(bits uint32) int32 { return int32(bits) }
