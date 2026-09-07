// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.
//
// The go-ethereum library is free software: you can redistribute it and/or modify
// it under the terms of the GNU Lesser General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// The go-ethereum library is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU Lesser General Public License for more details.
//
// You should have received a copy of the GNU Lesser General Public License
// along with the go-ethereum library. If not, see <http://www.gnu.org/licenses/>.

package javaevm

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestAddClassRunsWithDynamicArguments(t *testing.T) {
	classfile := compileJava(t, "Add", `public class Add { public static int add(int a, int b) { return a + b; } }`)
	program, err := CompileClass(classfile, "add")
	if err != nil {
		t.Fatal(err)
	}
	emitted := append([]byte(nil), program.Code...)
	first, err := Run(program, []int32{20, 22}, 100000)
	if err != nil {
		t.Fatal(err)
	}
	if first.Value != 42 || first.GasUsed == 0 {
		t.Fatalf("first run = %+v, want result 42 and measured gas", first)
	}
	second, err := Run(program, []int32{-7, 2}, 100000)
	if err != nil {
		t.Fatal(err)
	}
	if second.Value != -5 {
		t.Fatalf("negative run = %d, want -5", second.Value)
	}
	if string(program.Code) != string(emitted) {
		t.Fatal("running with different arguments changed emitted bytecode")
	}
	wrapped, err := Run(program, []int32{2147483647, 1}, 100000)
	if err != nil {
		t.Fatal(err)
	}
	if wrapped.Value != -2147483648 {
		t.Fatalf("wrapped run = %d, want INT_MIN", wrapped.Value)
	}
}

func TestUnsupportedOpcodeFails(t *testing.T) {
	classfile := compileJava(t, "Multiply", `public class Multiply { public static int add(int a, int b) { return a * b; } }`)
	_, err := CompileClass(classfile, "add")
	if err == nil || !strings.Contains(err.Error(), "unsupported opcode 0x68") {
		t.Fatalf("error = %v, want unsupported imul", err)
	}
}

func TestMalformedAndTruncatedClassFail(t *testing.T) {
	if _, err := CompileClass([]byte{0, 1, 2, 3}, "add"); err == nil {
		t.Fatal("bad magic unexpectedly compiled")
	}
	classfile := compileJava(t, "Add", `public class Add { public static int add(int a, int b) { return a + b; } }`)
	if _, err := CompileClass(classfile[:len(classfile)-1], "add"); err == nil {
		t.Fatal("truncated classfile unexpectedly compiled")
	}
}

func TestOutOfGasFails(t *testing.T) {
	classfile := compileJava(t, "Add", `public class Add { public static int add(int a, int b) { return a + b; } }`)
	program := mustCompile(t, classfile, "add")
	result, err := Run(program, []int32{20, 22}, 1)
	if err == nil || !strings.Contains(err.Error(), "out of gas") {
		t.Fatalf("error = %v, want out of gas", err)
	}
	if result.GasUsed != 1 {
		t.Fatalf("gas used = %d, want full 1", result.GasUsed)
	}
}

func mustCompile(t *testing.T, classfile []byte, method string) Program {
	t.Helper()
	program, err := CompileClass(classfile, method)
	if err != nil {
		t.Fatal(err)
	}
	return program
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
