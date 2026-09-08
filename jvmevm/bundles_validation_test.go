// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"encoding/binary"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/crypto"
)

const bundleValidationGasLimit = uint64(80_000_000)

func TestRunClassesValidatesBundleCardinalityAndIdentity(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"validation/Root.java": `package validation; public final class Root {
			public static int run(int x) { return x + 1; }
		}`,
		"validation/Other.java": `package validation; public final class Other {
			public static int run(int x) { return x + 2; }
		}`,
	}, "validation/Root", "validation/Other")

	result, err := RunClasses(nil, "validation/Root", "run", []int32{4}, bundleValidationGasLimit)
	assertBundleValidationError(t, result, err, "LinkError(uint256,uint256)", 1, 0)

	// Cardinality must be checked before attempting to parse any member.
	result, err = RunClasses(make([][]byte, 65), "validation/Root", "run", []int32{4}, bundleValidationGasLimit)
	assertBundleValidationError(t, result, err, "LinkError(uint256,uint256)", 1, 65)

	result, err = RunClasses(
		[][]byte{classes["validation/Other"], classes["validation/Root"], classes["validation/Root"]},
		"validation/Root", "run", []int32{4}, bundleValidationGasLimit,
	)
	assertBundleValidationError(t, result, err, "LinkError(uint256,uint256)", 2, 2)

	result, err = RunClasses(
		[][]byte{classes["validation/Root"]}, "validation/Absent", "run", []int32{4}, bundleValidationGasLimit,
	)
	assertBundleValidationError(t, result, err, "LinkError(uint256,uint256)", 3, 0)
}

func TestRunClassesMissingOwnerReportsCallerPC(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"missing/Root.java": `package missing; public final class Root {
			public static int run(int x) { return Helper.value(x); }
		}`,
		"missing/Helper.java": `package missing; public final class Helper {
			public static int value(int x) { return x + 8; }
		}`,
	}, "missing/Root", "missing/Helper")
	_, callPC := parseCallValidationClass(t, classes["missing/Root"]).callRef(t, "run")

	result, err := RunClasses(
		[][]byte{classes["missing/Root"]}, "missing/Root", "run", []int32{4}, bundleValidationGasLimit,
	)
	assertBundleValidationError(
		t, result, err, "LinkError(uint256,uint256)", 4, uint64(callPC),
	)
}

func TestRunClassesAcceptsEnteredInterfaceStaticAtInputIndex(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"entered/Plain.java": `package entered; public final class Plain { public static int run() { return 1; } }`,
		"entered/Face.java":  `package entered; public interface Face { static int run() { return 2; } }`,
	}, "entered/Plain", "entered/Face")
	result, err := RunClasses(
		[][]byte{classes["entered/Plain"], classes["entered/Face"]},
		"entered/Face", "run", nil, bundleValidationGasLimit,
	)
	if err != nil || result.ExceptionClass != "" || result.Value != 2 || result.GasUsed == 0 || len(result.RevertData) != 0 {
		t.Fatalf("interface static root result = %+v/%v, want 2", result, err)
	}
}

func TestRunClassesAcceptsProvidedSuperclassAndInheritedInitialization(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"entered/Parent.java": `package entered; public class Parent {
			static int marker = 20;
			public static int inherited() { return marker + 1; }
		}`,
		"entered/Child.java": `package entered; public final class Child extends Parent {
			static int child = marker + 2;
			public static int run() { return inherited() * 100 + child; }
		}`,
	}, "entered/Parent", "entered/Child")
	result, err := RunClasses(
		[][]byte{classes["entered/Parent"], classes["entered/Child"]},
		"entered/Child", "run", nil, bundleValidationGasLimit,
	)
	if err != nil {
		t.Fatalf("provided superclass failed: %v (result=%+v)", err, result)
	}
	if result.ExceptionClass != "" || result.Value != 2122 || result.GasUsed == 0 || len(result.RevertData) != 0 {
		t.Fatalf("result = %+v, want inherited initialized value 2122", result)
	}
}

func TestRunClassesAcceptsFormerlyRejectedClassInitializer(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"entered/Plain.java": `package entered; public final class Plain { public static int run() { return 1; } }`,
		"entered/WithInit.java": `package entered; public final class WithInit {
			static int marker = 7; public static int run() { return marker; }
		}`,
	}, "entered/Plain", "entered/WithInit")
	result, err := RunClasses(
		[][]byte{classes["entered/Plain"], classes["entered/WithInit"]},
		"entered/WithInit", "run", nil, bundleValidationGasLimit,
	)
	if err != nil {
		t.Fatalf("formerly rejected initializer failed: %v (result=%+v)", err, result)
	}
	if result.ExceptionClass != "" || result.Value != 7 || result.GasUsed == 0 || len(result.RevertData) != 0 {
		t.Fatalf("result = %+v, want initialized value 7", result)
	}
}

func TestRunClassesCallStructureAndMissingSignatureKeepExactCallErrors(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"calls/Root.java": `package calls; public final class Root {
			public static int run(int x) { return Target.open(x); }
		}`,
		"calls/Target.java": `package calls; public final class Target {
			public static int open(int x) { return x + 1; }
		}`,
	}, "calls/Root", "calls/Target")
	_, callPC := parseCallValidationClass(t, classes["calls/Root"]).callRef(t, "run")

	badTag := mutateCallValidationClass(t, classes["calls/Root"], func(out []byte, parsed callValidationClass) {
		ref, _ := parsed.callRef(t, "run")
		out[parsed.entry(t, ref).offset] = 9 // Fieldref is not a valid invokestatic reference.
	})
	result, err := RunClasses(
		[][]byte{classes["calls/Target"], badTag}, "calls/Root", "run", []int32{4}, bundleValidationGasLimit,
	)
	assertBundleValidationError(t, result, err, "CallError(uint256,uint256)", 1, uint64(callPC))

	wrongKind := mutateCallValidationClass(t, classes["calls/Root"], func(out []byte, parsed callValidationClass) {
		ref, _ := parsed.callRef(t, "run")
		out[parsed.entry(t, ref).offset] = 11 // Valid InterfaceMethodref, but Target is a class.
	})
	result, err = RunClasses(
		[][]byte{classes["calls/Target"], wrongKind}, "calls/Root", "run", []int32{4}, bundleValidationGasLimit,
	)
	assertBundleValidationError(t, result, err, "InterfaceError(uint256,uint256)", 1, uint64(callPC))

	missing := mutateCallValidationClass(t, classes["calls/Root"], func(out []byte, parsed callValidationClass) {
		nameType := parsed.callNameType(t, "run")
		binary.BigEndian.PutUint16(out[parsed.entry(t, nameType).offset+1:], parsed.utfIndex(t, "run"))
	})
	result, err = RunClasses(
		[][]byte{missing, classes["calls/Target"]}, "calls/Root", "run", []int32{4}, bundleValidationGasLimit,
	)
	assertBundleValidationError(t, result, err, "CallError(uint256,uint256)", 3, uint64(callPC))
}

func TestRunClassesMalformedRawClassRetainsClassError(t *testing.T) {
	result, err := RunClasses(
		[][]byte{{0, 1, 2, 3}}, "Malformed", "run", nil, bundleValidationGasLimit,
	)
	assertBundleValidationError(t, result, err, "ClassError(uint256,uint256)", 1, 0)
}

func TestLegacyRunExternalOwnerStillUsesCallError2(t *testing.T) {
	classfile := compileJava(t, "LegacyExternal", `public final class LegacyExternal {
		public static int run(int x) { return Math.abs(x); }
	}`)
	_, callPC := parseCallValidationClass(t, classfile).callRef(t, "run")
	result, err := Run(classfile, "run", []int32{-9}, bundleValidationGasLimit)
	assertBundleValidationError(
		t, result, err, "CallError(uint256,uint256)", 2, uint64(callPC),
	)
}

func TestRunClassesCrossClassAccessChecksUseCallError4(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"accessa/Root.java": `package accessa; import accessb.Target; public final class Root {
			public static int run(int x) { return Target.open(x); }
		}`,
		"accessb/Target.java": `package accessb; public final class Target {
			public static int open(int x) { return x + 1; }
		}`,
	}, "accessa/Root", "accessb/Target")
	_, callPC := parseCallValidationClass(t, classes["accessa/Root"]).callRef(t, "run")

	cases := []struct {
		name   string
		mutate func([]byte, callValidationClass)
	}{
		{
			name: "private-method",
			mutate: func(out []byte, parsed callValidationClass) {
				method := parsed.method(t, "open", "(I)I")
				flags := method.access &^ (uint16(0x0001) | uint16(0x0004))
				binary.BigEndian.PutUint16(out[method.accessOffset:], flags|0x0002)
			},
		},
		{
			name: "package-method-from-different-package",
			mutate: func(out []byte, parsed callValidationClass) {
				method := parsed.method(t, "open", "(I)I")
				flags := method.access &^ (uint16(0x0001) | uint16(0x0002) | uint16(0x0004))
				binary.BigEndian.PutUint16(out[method.accessOffset:], flags)
			},
		},
		{
			name: "nonpublic-class-from-different-package",
			mutate: func(out []byte, parsed callValidationClass) {
				flags := binary.BigEndian.Uint16(out[parsed.cpEnd:]) &^ uint16(0x0001)
				binary.BigEndian.PutUint16(out[parsed.cpEnd:], flags)
			},
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			target := append([]byte(nil), classes["accessb/Target"]...)
			tc.mutate(target, parseCallValidationClass(t, target))
			result, err := RunClasses(
				[][]byte{target, classes["accessa/Root"]},
				"accessa/Root", "run", []int32{4}, bundleValidationGasLimit,
			)
			assertBundleValidationError(
				t, result, err, "CallError(uint256,uint256)", 4, uint64(callPC),
			)
		})
	}
}

func TestRunClassesOrderRootIdentityAndPerClassCachesAreIndependent(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"bundle/Root.java": `package bundle; public final class Root {
			public static int run(int x) {
				return Left.compute(x) * 10000 + Right.compute(x) * 1000
					+ PackageTarget.packageValue(x) * 100
					+ PackageTarget.protectedValue(x) * 10 + publicapi.Target.value(x);
			}
		}`,
		"bundle/Left.java": `package bundle; public final class Left {
			private static int helper(int x) { return x + 1; }
			public static int compute(int x) { return helper(x); }
		}`,
		"bundle/Right.java": `package bundle; public final class Right {
			private static int helper(int x) { return x * 2; }
			public static int compute(int x) { return helper(x); }
		}`,
		"bundle/PackageTarget.java": `package bundle; public final class PackageTarget {
			static int packageValue(int x) { return x + 3; }
			protected static int protectedValue(int x) { return x + 4; }
		}`,
		"bundle/Decoy.java": `package bundle; public final class Decoy {
			public static int run(int x) { return -1; }
		}`,
		"bundle/UnusedInit.java": `package bundle; public final class UnusedInit {
			static int marker = 99; public static int value() { return marker; }
		}`,
		"publicapi/Target.java": `package publicapi; public final class Target {
			public static int value(int x) { return x + 5; }
		}`,
	}, "bundle/Root", "bundle/Left", "bundle/Right", "bundle/PackageTarget",
		"bundle/Decoy", "bundle/UnusedInit", "publicapi/Target")

	orders := [][]string{
		{"bundle/Decoy", "bundle/Right", "bundle/UnusedInit", "bundle/Root", "publicapi/Target", "bundle/Left", "bundle/PackageTarget"},
		{"bundle/PackageTarget", "bundle/Left", "publicapi/Target", "bundle/Root", "bundle/UnusedInit", "bundle/Right", "bundle/Decoy"},
	}
	var runtimeHash string
	for i, order := range orders {
		inputs := make([][]byte, len(order))
		for j, name := range order {
			inputs[j] = classes[name]
		}
		result, err := RunClasses(inputs, "bundle/Root", "run", []int32{4}, bundleValidationGasLimit)
		if err != nil {
			t.Fatalf("order %d: %v (result=%+v)", i, err, result)
		}
		// 5*10000 + 8*1000 + 7*100 + 8*10 + 9.
		if result.ExceptionClass != "" || result.Value != 58789 || result.GasUsed == 0 || len(result.RevertData) != 0 {
			t.Fatalf("order %d result = %+v, want value 58789", i, result)
		}
		if i == 0 {
			runtimeHash = result.RuntimeSHA256
		} else if result.RuntimeSHA256 == "" || result.RuntimeSHA256 != runtimeHash {
			t.Fatalf("runtime hash changed with class order: %q != %q", result.RuntimeSHA256, runtimeHash)
		}
	}
}

func assertBundleValidationError(t *testing.T, result Result, err error, signature string, code, detail uint64) {
	t.Helper()
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error = %+v/%v, want exact %s revert", result, err, signature)
	}
	selector := crypto.Keccak256([]byte(signature))[:4]
	if result.ExceptionClass != "" || result.GasUsed == 0 || len(result.RevertData) != 68 || !bytes.Equal(result.RevertData[:4], selector) {
		t.Fatalf("result = %+v, want exact %s payload", result, signature)
	}
	if got := bundleValidationUint256(t, result.RevertData[4:36]); got != code {
		t.Fatalf("%s code = %d, want %d (data=%x)", signature, got, code, result.RevertData)
	}
	if got := bundleValidationUint256(t, result.RevertData[36:68]); got != detail {
		t.Fatalf("%s detail = %d, want %d (data=%x)", signature, got, detail, result.RevertData)
	}
}

func bundleValidationUint256(t *testing.T, word []byte) uint64 {
	t.Helper()
	if len(word) != 32 || !bytes.Equal(word[:24], make([]byte, 24)) {
		t.Fatalf("noncanonical or oversized uint256 word: %x", word)
	}
	return binary.BigEndian.Uint64(word[24:])
}

// compileBundleValidationJava compiles only trusted inline test sources. Test
// code reads the resulting files to select inputs and make negative mutations;
// production RunClasses receives only raw bytes and explicit internal-name metadata.
func compileBundleValidationJava(t *testing.T, sources map[string]string, internalNames ...string) map[string][]byte {
	t.Helper()
	dir := t.TempDir()
	paths := make([]string, 0, len(sources))
	for relative, source := range sources {
		path := filepath.Join(dir, filepath.FromSlash(relative))
		if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(source), 0o600); err != nil {
			t.Fatal(err)
		}
		paths = append(paths, path)
	}
	sort.Strings(paths)
	args := []string{"--release", "8", "-d", dir}
	args = append(args, paths...)
	command := exec.Command("javac", args...)
	if output, err := command.CombinedOutput(); err != nil {
		t.Fatalf("javac failed: %v\n%s", err, output)
	}
	classes := make(map[string][]byte, len(internalNames))
	for _, name := range internalNames {
		path := filepath.Join(dir, filepath.FromSlash(name+".class"))
		classfile, err := os.ReadFile(path)
		if err != nil {
			t.Fatalf("read compiled %s: %v", name, err)
		}
		classes[name] = classfile
	}
	return classes
}
