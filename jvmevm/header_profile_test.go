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
)

const headerProfileGasLimit = 100_000_000

func TestLegacyRunRejectsOmittedSuperclassInitialization(t *testing.T) {
	classfile := compileHeaderProfileFixture(t, map[string]string{
		"Child.java": `public class Child extends Parent {
	static int touched;
	public static int run() { return touched; }
}
class Parent {
	static int value = mark();
	static int mark() { Child.touched = 7; return 7; }
}`,
	}, "Child", `System.out.print(Child.run());`, "7")

	result, err := Run(classfile, "run", nil, headerProfileGasLimit)
	assertSolidityError(t, result, err, "HierarchyError(uint256,uint256)", 1, 0)
	t.Logf("legacy custom-super guard gas=%d", result.GasUsed)
}

func TestLegacyRunRejectsOmittedDefaultInterfaceInitialization(t *testing.T) {
	classfile := compileHeaderProfileFixture(t, map[string]string{
		"Leaf.java": `public class Leaf implements Marker {
	static int touched;
	public static int mark() { touched = 9; return 9; }
	public static int run() { return touched; }
}
interface Marker {
	int X = Leaf.mark();
	default int marker() { return 1; }
}`,
	}, "Leaf", `System.out.print(Leaf.run());`, "9")

	result, err := Run(classfile, "run", nil, headerProfileGasLimit)
	// M4f-a resolves direct interface edges instead of rejecting every interface.
	// Marker is still deliberately omitted: never silently skip its initialization.
	assertSolidityError(t, result, err, "LinkError(uint256,uint256)", 4, 0)
	t.Logf("legacy interface guard gas=%d", result.GasUsed)
}

func TestLegacyRunHeaderProfileValidationAndCompatibility(t *testing.T) {
	plain := compileHeaderProfileFixture(t, map[string]string{
		"Plain.java": `public final class Plain {
	static int value = 40;
	public static int run() { return value + 2; }
}`,
	}, "Plain", `System.out.print(Plain.run());`, "42")

	positive, err := Run(plain, "run", nil, headerProfileGasLimit)
	if err != nil || positive.ExceptionClass != "" || positive.Value != 42 || len(positive.RevertData) != 0 {
		t.Fatalf("ordinary Object-super class result/error = %+v/%v, want value 42", positive, err)
	}

	parsed := parseCallTestClass(t, plain)
	utfIndex := parsed.utfIndex("Plain")
	if utfIndex == 0 || parsed.tags[utfIndex] != 1 {
		t.Fatalf("fixture has no Plain Utf8 constant: index=%d", utfIndex)
	}
	accessOffset := bundleClassAccessOffset(t, plain)

	badSuperTag := append([]byte(nil), plain...)
	binary.BigEndian.PutUint16(badSuperTag[accessOffset+4:], utfIndex)
	badResult, badErr := Run(badSuperTag, "run", nil, headerProfileGasLimit)
	assertSolidityError(
		t, badResult, badErr, "ClassError(uint256,uint256)", 10, uint64(accessOffset+6),
	)

	zeroSuper := append([]byte(nil), plain...)
	binary.BigEndian.PutUint16(zeroSuper[accessOffset+4:], 0)
	zeroResult, zeroErr := Run(zeroSuper, "run", nil, headerProfileGasLimit)
	assertSolidityError(t, zeroResult, zeroErr, "HierarchyError(uint256,uint256)", 4, 0)

	marker := compileJava(t, "DirectFace", `public interface DirectFace {
	static int run() { return 1; }
}`)
	interfaceResult, interfaceErr := Run(marker, "run", nil, headerProfileGasLimit)
	if interfaceErr != nil || interfaceResult.ExceptionClass != "" || interfaceResult.Value != 1 || interfaceResult.GasUsed == 0 || len(interfaceResult.RevertData) != 0 {
		t.Fatalf("legacy interface static root result/error = %+v/%v, want value 1", interfaceResult, interfaceErr)
	}

	t.Logf(
		"legacy header profile gas: ordinary=%d malformed-super=%d zero-super=%d direct-interface=%d",
		positive.GasUsed, badResult.GasUsed, zeroResult.GasUsed, interfaceResult.GasUsed,
	)
}

// compileHeaderProfileFixture compiles only trusted inline test sources and runs a
// host-JVM oracle before returning the requested unchanged classfile. The oracle
// evidence is important here: the omitted superclass/interface initialization has
// a real observable effect, rather than merely being an unsupported header shape.
func compileHeaderProfileFixture(
	t *testing.T,
	sources map[string]string,
	className string,
	oracleStatement string,
	wantOracle string,
) []byte {
	t.Helper()
	dir := t.TempDir()
	rels := make([]string, 0, len(sources))
	for rel := range sources {
		rels = append(rels, rel)
	}
	sort.Strings(rels)
	paths := make([]string, 0, len(rels)+1)
	for _, rel := range rels {
		path := filepath.Join(dir, filepath.FromSlash(rel))
		if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(sources[rel]), 0o600); err != nil {
			t.Fatal(err)
		}
		paths = append(paths, path)
	}
	oraclePath := filepath.Join(dir, "HeaderProfileOracle.java")
	oracleSource := "public final class HeaderProfileOracle {" +
		" public static void main(String[] args) { " + oracleStatement + " } }"
	if err := os.WriteFile(oraclePath, []byte(oracleSource), 0o600); err != nil {
		t.Fatal(err)
	}
	paths = append(paths, oraclePath)

	javacArgs := append([]string{"--release", "8", "-d", dir}, paths...)
	if output, err := exec.Command("javac", javacArgs...).CombinedOutput(); err != nil {
		t.Fatalf("javac failed: %v\n%s", err, output)
	}
	output, err := exec.Command("java", "-cp", dir, "HeaderProfileOracle").CombinedOutput()
	if err != nil {
		t.Fatalf("host JVM oracle failed: %v\n%s", err, output)
	}
	if got := strings.TrimSpace(string(output)); got != wantOracle {
		t.Fatalf("host JVM oracle = %q, want %q", got, wantOracle)
	}

	classfile, err := os.ReadFile(filepath.Join(dir, filepath.FromSlash(className)+".class"))
	if err != nil {
		t.Fatal(err)
	}
	return classfile
}

func assertHeaderProfileMethodError(t *testing.T, result Result, err error, code uint64) {
	t.Helper()
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error = %+v/%v, want MethodError revert", result, err)
	}
	selector := cryptoSelector("MethodError(uint256)")
	if len(result.RevertData) != 36 || !bytes.Equal(result.RevertData[:4], selector) {
		t.Fatalf("revert data = 0x%x, want exact MethodError payload", result.RevertData)
	}
	if got := binary.BigEndian.Uint64(result.RevertData[28:36]); got != code {
		t.Fatalf("MethodError code = %d, want %d (data=%x)", got, code, result.RevertData)
	}
}
