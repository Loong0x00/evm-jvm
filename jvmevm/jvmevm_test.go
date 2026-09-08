// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

const expectedRuntimeHash = "b59cf3ff60ed775d21c6344eb832770e980d397721398a70fa1cf3037ba91069"

func TestGenericRuntimeHandlesDifferentRawClassesAndArguments(t *testing.T) {
	addClass := compileJava(t, "Add", `public class Add { public static int add(int a, int b) { return a + b; } }`)
	identityClass := compileJava(t, "Identity", `public class Identity { public static int identity(int b) { return b; } }`)
	if bytes.Equal(addClass, identityClass) {
		t.Fatal("javac unexpectedly produced identical classes")
	}
	runtimeBefore, err := Runtime()
	if err != nil {
		t.Fatal(err)
	}
	cases := []struct {
		class  []byte
		method string
		args   []int32
		want   int32
	}{
		{addClass, "add", []int32{20, 22}, 42},
		{addClass, "add", []int32{-7, 2}, -5},
		{addClass, "add", []int32{2147483647, 1}, -2147483648},
		{identityClass, "identity", []int32{-123456789}, -123456789},
		{identityClass, "identity", []int32{77}, 77},
	}
	for _, tc := range cases {
		result, err := Run(tc.class, tc.method, tc.args, 2_000_000)
		if err != nil {
			t.Fatalf("%s%v: %v", tc.method, tc.args, err)
		}
		if result.Value != tc.want || result.GasUsed == 0 {
			t.Fatalf("%s%v = %+v, want value %d and measured gas", tc.method, tc.args, result, tc.want)
		}
		if result.RuntimeSHA256 != expectedRuntimeHash {
			t.Fatalf("runtime hash = %s, want %s", result.RuntimeSHA256, expectedRuntimeHash)
		}
	}
	runtimeAfter, _ := Runtime()
	if !bytes.Equal(runtimeBefore, runtimeAfter) {
		t.Fatal("generic interpreter runtime changed between classes or arguments")
	}
}

func TestUnsupportedBytecodeAndMalformedClassRevertInsideEVM(t *testing.T) {
	// Scalar long conversion is supported in M5b-a; prove its value with Java 8
	// rather than weakening the former unsupported assertion to "no error".
	longConversion := compileJava(t, "LongConversion", `public class LongConversion { public static int conversion(int n) { return (int)((long)n + 1L); } }`)
	verifyM5baJava8Outcome(t, [][]byte{longConversion}, "LongConversion", "conversion", []int32{3}, "value=4")
	converted, err := Run(longConversion, "conversion", []int32{3}, 2_000_000)
	if err != nil || converted.Value != 4 || converted.ExceptionClass != "" || converted.GasUsed == 0 || len(converted.RevertData) != 0 {
		t.Fatalf("long conversion result/error = %+v/%v, want exact value 4", converted, err)
	}

	// Preserve a distinct unsupported IEEE conversion guard.
	floatConversion := compileJava(t, "FloatConversion", `public class FloatConversion { public static int conversion(int n) { return (int)((float)n + 1.0f); } }`)
	for name, tc := range map[string]struct {
		class  []byte
		method string
		args   []int32
	}{
		"unsupported-float-conversion": {floatConversion, "conversion", []int32{3}},
		"bad-magic":                    {[]byte{0, 1, 2, 3}, "add", []int32{1, 2}},
		"truncated":                    {longConversion[:len(longConversion)-1], "conversion", []int32{3}},
	} {
		t.Run(name, func(t *testing.T) {
			result, err := Run(tc.class, tc.method, tc.args, 2_000_000)
			if err == nil || !strings.Contains(err.Error(), "execution reverted") {
				t.Fatalf("error = %v, want EVM execution revert", err)
			}
			if result.GasUsed == 0 || len(result.RevertData) < 4 {
				t.Fatalf("result = %+v, want measured EVM gas and Solidity custom-error revert data", result)
			}
		})
	}
}

func TestOutOfGasIsEVMFailure(t *testing.T) {
	classfile := compileJava(t, "Add", `public class Add { public static int add(int a, int b) { return a + b; } }`)
	result, err := Run(classfile, "add", []int32{20, 22}, 100)
	if err == nil || !strings.Contains(err.Error(), "out of gas") {
		t.Fatalf("error = %v, want EVM out of gas", err)
	}
	if result.GasUsed != 100 {
		t.Fatalf("gas used = %d, want full gas limit 100", result.GasUsed)
	}
}

func TestSelectedClassInitializerRunsInsideEVM(t *testing.T) {
	withInit := compileJava(t, "WithInit", `public class WithInit { static int x = 1; public static int identity(int a) { return a + x; } }`)
	result, err := Run(withInit, "identity", []int32{7}, 5_000_000)
	if err != nil || result.Value != 8 || result.ExceptionClass != "" {
		t.Fatalf("class initializer result/error = %+v/%v, want value 8", result, err)
	}
}

func TestCheckedInRuntimeHash(t *testing.T) {
	hash, err := RuntimeHash()
	if err != nil {
		t.Fatal(err)
	}
	if hash != expectedRuntimeHash {
		t.Fatalf("runtime hash = %s, want %s; rebuild and review artifact", hash, expectedRuntimeHash)
	}
}

func compileJava(t *testing.T, name, source string) []byte {
	t.Helper()
	dir := t.TempDir()
	path := filepath.Join(dir, name+".java")
	if err := os.WriteFile(path, []byte(source), 0o600); err != nil {
		t.Fatal(err)
	}
	command := exec.Command("javac", "--release", "8", "-d", dir, path)
	if output, err := command.CombinedOutput(); err != nil {
		t.Fatalf("javac failed: %v\n%s", err, output)
	}
	classfile, err := os.ReadFile(filepath.Join(dir, name+".class"))
	if err != nil {
		t.Fatal(err)
	}
	return classfile
}
