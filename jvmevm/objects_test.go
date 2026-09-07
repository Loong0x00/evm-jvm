// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

const runtimeM4bGasLimit = uint64(120_000_000)

func runtimeM4bBundle(classes map[string][]byte, names ...string) [][]byte {
	out := make([][]byte, 0, len(names))
	for _, name := range names {
		out = append(out, classes[name])
	}
	return out
}

func TestRuntimeM4bBootstrapObjectIsReproducibleAndEmbedded(t *testing.T) {
	const source = "package java.lang; public class Object { public Object() {} }\n"
	const wantHash = "af9136af3be2c44ce120ac403beccb8b1cc963fc83dc1457e63f8b69dd497fe0"
	checkedSource, err := os.ReadFile("runtime/bootstrap/Object.java")
	if err != nil || string(checkedSource) != source {
		t.Fatalf("bootstrap source = %q, error %v", checkedSource, err)
	}
	checkedHex, err := os.ReadFile("runtime/bootstrap/Object.class.hex")
	if err != nil {
		t.Fatal(err)
	}
	want, err := hex.DecodeString(strings.TrimSpace(string(checkedHex)))
	if err != nil {
		t.Fatal(err)
	}
	dir := t.TempDir()
	src := filepath.Join(dir, "java", "lang", "Object.java")
	if err := os.MkdirAll(filepath.Dir(src), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(src, []byte(source), 0o600); err != nil {
		t.Fatal(err)
	}
	out := filepath.Join(dir, "out")
	cmd := exec.Command("javac", "--release", "8", "-g:none", "-Xlint:-options", "-d", out, src)
	if output, err := cmd.CombinedOutput(); err != nil {
		t.Fatalf("javac bootstrap: %v\n%s", err, output)
	}
	got, err := os.ReadFile(filepath.Join(out, "java", "lang", "Object.class"))
	if err != nil {
		t.Fatal(err)
	}
	hash := sha256.Sum256(got)
	if len(got) != 95 || !bytes.Equal(got, want) || hex.EncodeToString(hash[:]) != wantHash {
		t.Fatalf("bootstrap bytes=%d hash=%x, want 95/%s", len(got), hash, wantHash)
	}
	solidity, err := os.ReadFile("runtime/JVMSubsetInterpreter.sol")
	if err != nil || !bytes.Contains(solidity, []byte(`return hex"`+hex.EncodeToString(got)+`";`)) {
		t.Fatalf("bootstrap class is not embedded exactly in Solidity (read error %v)", err)
	}
}

func TestRuntimeM4bObjectsConstructorsFieldsAndSpecialCalls(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"m4b/Base.java": `package m4b;
public class Base {
  public int x;
  public Object ref;
  public int[] array;
  public Base(int x) { this.x = x; this.ref = this; this.array = new int[2]; this.array[1] = x + 1; }
  protected int direct(int n) { return n + 3; }
}`,
		"m4b/Child.java": `package m4b;
public class Child extends Base {
  public int x;
  public final int fin;
  public int superValue;
  public Child(int n) { this(n, n + 2); }
  private Child(int a, int b) { super(a); this.x = b; this.fin = a + b; this.superValue = super.direct(4); }
}`,
		"m4b/Root.java": `package m4b;
public class Root {
  private int bias;
  private Root(int bias) { this.bias = bias; }
  private int twice(int n) { return n == 0 ? bias : 2 + twice(n - 1); }
  static Object pass(Object x) { return x; }
  static int score(Child c) {
    Base b = c;
    return b.x * 1000 + c.x * 100 + c.fin * 10 + c.array[1] + (pass(c) == c ? 1 : 0);
  }
  public static int run(int n) {
    Child c = new Child(n);
    Root r = new Root(7);
    return score(c) + r.twice(2) + c.superValue;
  }
}`,
	})
	result, err := RunClasses(
		runtimeM4bBundle(classes, "m4b/Root", "m4b/Child", "m4b/Base"),
		"m4b/Root", "run", []int32{3}, runtimeM4bGasLimit,
	)
	// 3*1000 + 5*100 + 8*10 + 4 + 1 + 11 + 7
	if err != nil || result.ExceptionClass != "" || result.Value != 3603 || len(result.RevertData) != 0 {
		t.Fatalf("object result/error = %+v/%v, want 3603", result, err)
	}
}

func TestRuntimeM4bSingleClassRunUsesParsedBootstrapObject(t *testing.T) {
	classfile := compileJava(t, "SingleObject", `public class SingleObject {
  int x; SingleObject(int x) { this.x = x; }
  private int add(int n) { return x + n; }
  public static int run(int n) { SingleObject x = new SingleObject(n); return x.add(5); }
}`)
	result, err := Run(classfile, "run", []int32{37}, runtimeM4bGasLimit)
	if err != nil || result.ExceptionClass != "" || result.Value != 42 || len(result.RevertData) != 0 {
		t.Fatalf("single object result/error = %+v/%v, want 42", result, err)
	}
}

func TestRuntimeM4bClassInitializationAndReferenceSpecialReturns(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"initobj/Box.java": `package initobj; public class Box { public int value; public Box(int n) { value = n; } }`,
		"initobj/Root.java": `package initobj;
public class Root {
  static int seed = 4;
  static Box box = new Box(seed + 2);
  static Object object = box;
  private Box pass(Box x) { return x; }
  public static int run(int n) {
    Root r = new Root(); Box x = r.pass(box);
    return x.value + (object == box ? 10 : 0) + n;
  }
}`,
	})
	result, err := RunClasses(runtimeM4bBundle(classes, "initobj/Root", "initobj/Box"),
		"initobj/Root", "run", []int32{3}, runtimeM4bGasLimit)
	if err != nil || result.ExceptionClass != "" || result.Value != 19 || len(result.RevertData) != 0 {
		t.Fatalf("class initialization object result/error = %+v/%v, want 19", result, err)
	}
}

func TestRuntimeM4bNullFieldReceiverIsJavaNPE(t *testing.T) {
	classfile := compileJava(t, "NullField", `public class NullField {
  int value; public static int run(int n) { NullField x = null; return x.value + n; }
}`)
	result, err := Run(classfile, "run", []int32{1}, runtimeM4bGasLimit)
	if err != nil || result.ExceptionClass != "java.lang.NullPointerException" || len(result.RevertData) != 36 {
		t.Fatalf("null field result/error = %+v/%v, want structured NPE", result, err)
	}
}

func TestRuntimeM4bObjectCountLimitIsOOMAndHeapResets(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"caps/Item.java": `package caps; public class Item { public Item() {} }`,
		"caps/Root.java": `package caps; public class Root {
  public static int run(int n) { Item x = null; for (int i = 0; i < n; i++) x = new Item(); return x == null ? 0 : n; }
}`,
	})
	bundle := runtimeM4bBundle(classes, "caps/Root", "caps/Item")
	ok, err := RunClasses(bundle, "caps/Root", "run", []int32{1024}, 250_000_000)
	if err != nil || ok.ExceptionClass != "" || ok.Value != 1024 {
		t.Fatalf("1024 objects result/error = %+v/%v", ok, err)
	}
	oom, err := RunClasses(bundle, "caps/Root", "run", []int32{1025}, 250_000_000)
	if err != nil || oom.ExceptionClass != "java.lang.OutOfMemoryError" || len(oom.RevertData) != 36 {
		t.Fatalf("1025 objects result/error = %+v/%v, want Java OOM", oom, err)
	}
	fresh, err := RunClasses(bundle, "caps/Root", "run", []int32{1}, runtimeM4bGasLimit)
	if err != nil || fresh.ExceptionClass != "" || fresh.Value != 1 {
		t.Fatalf("fresh heap result/error = %+v/%v", fresh, err)
	}
}

func TestRuntimeM4bMixedArrayObjectHandlesAndFreshDefaults(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"Mixed.java": `public class Mixed {
  int value;
  Object ref;
  int[] ints;
  Mixed() {}
  static int inspect(Mixed x) {
    return (x.value == 0 ? 1 : 0) + (x.ref == null ? 2 : 0) + (x.ints == null ? 4 : 0);
  }
  public static int run(int n) {
    int[] a = new int[1]; Mixed x = new Mixed(); int[] b = new int[2]; Mixed y = new Mixed();
    x.ref = b; x.ints = b; b[1] = n;
    return inspect(y) * 100 + (x.ref == b ? 10 : 0) + x.ints[1] + a.length;
  }
}`,
	})
	result, err := RunClasses([][]byte{classes["Mixed"]}, "Mixed", "run", []int32{9}, runtimeM4bGasLimit)
	if err != nil || result.ExceptionClass != "" || result.Value != 720 || len(result.RevertData) != 0 {
		t.Fatalf("mixed heap result/error = %+v/%v, want 720", result, err)
	}
}
