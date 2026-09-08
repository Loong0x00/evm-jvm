// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
	"testing"
)

func runtimeM4cCompileClasses(t *testing.T, sources map[string]string) map[string][]byte {
	t.Helper()
	dir := t.TempDir()
	paths := make([]string, 0, len(sources))
	for name, source := range sources {
		path := filepath.Join(dir, filepath.FromSlash(name)+".java")
		if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(source), 0o600); err != nil {
			t.Fatal(err)
		}
		paths = append(paths, path)
	}
	sort.Strings(paths)
	args := append([]string{"--release", "8", "-d", dir}, paths...)
	if output, err := exec.Command("javac", args...).CombinedOutput(); err != nil {
		t.Fatalf("javac failed: %v\n%s", err, output)
	}
	classes := make(map[string][]byte)
	if err := filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.IsDir() || filepath.Ext(path) != ".class" {
			return nil
		}
		rel, err := filepath.Rel(dir, path)
		if err != nil {
			return err
		}
		data, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		classes[strings.TrimSuffix(filepath.ToSlash(rel), ".class")] = data
		return nil
	}); err != nil {
		t.Fatal(err)
	}
	return classes
}

func runtimeM4cBundle(classes map[string][]byte, omit ...string) [][]byte {
	skipped := make(map[string]bool)
	for _, name := range omit {
		skipped[name] = true
	}
	names := make([]string, 0, len(classes))
	for name := range classes {
		if !skipped[name] {
			names = append(names, name)
		}
	}
	sort.Strings(names)
	bundle := make([][]byte, 0, len(names))
	for _, name := range names {
		bundle = append(bundle, classes[name])
	}
	return bundle
}

func runtimeM4cRunValue(t *testing.T, classes map[string][]byte, entryClass, method string, want int32) {
	t.Helper()
	result, err := RunClasses(runtimeM4cBundle(classes), entryClass, method, nil, 80_000_000)
	if err != nil {
		t.Fatalf("%s.%s: %v", entryClass, method, err)
	}
	if result.ExceptionClass != "" || result.Value != want {
		t.Fatalf("%s.%s result = %+v, want value %d", entryClass, method, result, want)
	}
}

func TestRuntimeM4cVirtualDispatchAndConstructorCallback(t *testing.T) {
	classes := runtimeM4cCompileClasses(t, map[string]string{
		"Dispatch": `
public class Dispatch {
  public static int base() { Base x = new Base(); return x.value(); }
  public static int child() { Base x = new Child(); return x.value(); }
  public static int grandchild() { Base x = new Grandchild(); return x.value(); }
  public static int inherited() { Base x = new Inherited(); return x.value(); }
  public static int callback() { Child x = new Child(); return x.seen * 10 + x.value; }
  public static int alternating() { return call(new Base()) * 10 + call(new Grandchild()); }
  static int call(Base x) { return x.value(); }
  public static int referenceAndVoid() {
    Base x = new Child(); x.put(4); return x.self() == x ? x.value() : -1;
  }
}
class Base {
  int seen;
  Base() { seen = value(); }
  int value() { return 1; }
  void put(int x) { seen = x; }
  Base self() { return this; }
}
class Child extends Base {
  int value = 9;
  int value() { return value; }
  void put(int x) { value = x; }
  Base self() { return this; }
}
class Grandchild extends Child { int value() { return 3; } }
class Inherited extends Child { }
`,
	})
	for method, want := range map[string]int32{
		"base": 1, "child": 9, "grandchild": 3, "inherited": 9, "callback": 9,
		"alternating": 13, "referenceAndVoid": 4,
	} {
		t.Run(method, func(t *testing.T) { runtimeM4cRunValue(t, classes, "Dispatch", method, want) })
	}
}

func TestRuntimeM4cResolvedUnsupportedMethodsMaySelectOrdinaryOverrides(t *testing.T) {
	classes := runtimeM4cCompileClasses(t, map[string]string{
		"ResolvedKinds": `
public class ResolvedKinds {
  public static int abstractOverride() { AbstractBase x = new AbstractChild(); return x.f(); }
  public static int nativeOverride() { NativeBase x = new NativeChild(); return x.f(); }
  public static int synchronizedOverride() { SyncBase x = new SyncChild(); return x.f(); }
}
abstract class AbstractBase { abstract int f(); }
class AbstractChild extends AbstractBase { int f() { return 11; } }
class NativeBase { native int f(); }
class NativeChild extends NativeBase { int f() { return 12; } }
class SyncBase { synchronized int f() { return 1; } }
class SyncChild extends SyncBase { int f() { return 13; } }
`,
	})
	for method, want := range map[string]int32{
		"abstractOverride": 11, "nativeOverride": 12, "synchronizedOverride": 13,
	} {
		t.Run(method, func(t *testing.T) { runtimeM4cRunValue(t, classes, "ResolvedKinds", method, want) })
	}
}

func TestRuntimeM4cPackagePrivateOverrideChains(t *testing.T) {
	classes := runtimeM4cCompileClasses(t, map[string]string{
		"Entry": `
import p.A;
public class Entry {
  public static int transitive() { return A.call(new q.C()); }
  public static int gap() { return p.Gap.call(new q.GapC()); }
  public static int finalGap() { return p.FinalGap.call(new q.FinalGapChild()); }
}
`,
		"p/A":             `package p; public class A { int f(){return 1;} public static int call(A x){return x.f();} }`,
		"p/B":             `package p; public class B extends A { public int f(){return 2;} }`,
		"q/C":             `package q; public class C extends p.B { public int f(){return 3;} }`,
		"p/Gap":           `package p; public class Gap { int f(){return 4;} public static int call(Gap x){return x.f();} }`,
		"q/GapB":          `package q; public class GapB extends p.Gap { public int f(){return 5;} }`,
		"q/GapC":          `package q; public class GapC extends GapB { public int f(){return 6;} }`,
		"p/FinalGap":      `package p; public class FinalGap { final int f(){return 7;} public static int call(FinalGap x){return x.f();} }`,
		"q/FinalGapChild": `package q; public class FinalGapChild extends p.FinalGap { public int f(){return 8;} }`,
	})
	for method, want := range map[string]int32{"transitive": 3, "gap": 4, "finalGap": 7} {
		t.Run(method, func(t *testing.T) { runtimeM4cRunValue(t, classes, "Entry", method, want) })
	}
}

func TestRuntimeM4cNullVirtualResolvesBeforeThrowAndSelectedSynchronizedFails(t *testing.T) {
	classes := runtimeM4cCompileClasses(t, map[string]string{
		"VirtualErrors": `
public class VirtualErrors {
  public static int nullAbstract() { AbstractReceiver x = null; return x.f(); }
  public static int selectedSynchronized() { OrdinaryReceiver x = new SynchronizedChild(); return x.f(); }
}
abstract class AbstractReceiver { abstract int f(); }
class OrdinaryReceiver { int f() { return 1; } }
class SynchronizedChild extends OrdinaryReceiver { synchronized int f() { return 2; } }
`,
	})
	result, err := RunClasses(runtimeM4cBundle(classes), "VirtualErrors", "nullAbstract", nil, 80_000_000)
	if err != nil || result.ExceptionClass != "java.lang.NullPointerException" {
		t.Fatalf("null abstract call result/error = %+v/%v, want NullPointerException", result, err)
	}
	result, err = RunClasses(runtimeM4cBundle(classes), "VirtualErrors", "selectedSynchronized", nil, 80_000_000)
	if err == nil || result.ExceptionClass != "" || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("selected synchronized result/error = %+v/%v, want ordinary EVM CallError", result, err)
	}
}

func TestRuntimeM4cCastsInstanceofArraysAndNullMissingTarget(t *testing.T) {
	classes := runtimeM4cCompileClasses(t, map[string]string{
		"Types": `
public class Types {
  public static int classTests() {
    Object a = new TypeChild();
    return (a instanceof TypeChild ? 1 : 0) + (a instanceof TypeBase ? 2 : 0)
      + (a instanceof Other ? 4 : 0) + (((TypeBase)a) == a ? 8 : 0);
  }
  public static int arrayTests() {
    Object a = new int[2];
    return (a instanceof int[] ? 1 : 0) + (a instanceof Object ? 2 : 0)
      + (a instanceof TypeBase ? 4 : 0) + (((int[])a) == a ? 8 : 0);
  }
  public static int nullMissing() { Object a = null; return a instanceof Missing ? 1 : 0; }
  public static int nullCastMissing() { Object a = null; return ((Missing)a) == null ? 1 : 0; }
  public static int missingNonNull() { Object a = new Other(); return a instanceof Missing ? 1 : 0; }
  public static int targetNotInitialized() { Object a = new Other(); return a instanceof LazyTarget ? 1 : 0; }
  public static int badCast() { Object a = new Other(); return ((TypeBase)a).x; }
}
class LazyTarget { static int fail = 1 / 0; }
class TypeBase { int x = 1; }
class TypeChild extends TypeBase { }
class Other { }
class Missing { }
class InitCast {
  static int value = ((TypeBase)(Object)new Other()).x;
  public static int read() { return value; }
}
`,
	})
	runtimeM4cRunValue(t, classes, "Types", "classTests", 11)
	runtimeM4cRunValue(t, classes, "Types", "arrayTests", 11)

	withoutMissing := runtimeM4cBundle(classes, "Missing")
	result, err := RunClasses(withoutMissing, "Types", "nullMissing", nil, 80_000_000)
	if err != nil || result.ExceptionClass != "" || result.Value != 0 {
		t.Fatalf("null instanceof missing result/error = %+v/%v, want value 0", result, err)
	}
	result, err = RunClasses(withoutMissing, "Types", "nullCastMissing", nil, 80_000_000)
	if err != nil || result.ExceptionClass != "" || result.Value != 1 {
		t.Fatalf("null checkcast missing result/error = %+v/%v, want value 1", result, err)
	}
	result, err = RunClasses(withoutMissing, "Types", "missingNonNull", nil, 80_000_000)
	if err == nil || result.ExceptionClass != "" || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("nonnull instanceof missing result/error = %+v/%v, want LinkError", result, err)
	}
	runtimeM4cRunValue(t, classes, "Types", "targetNotInitialized", 0)
	result, err = RunClasses(runtimeM4cBundle(classes), "Types", "badCast", nil, 80_000_000)
	if err != nil || result.ExceptionClass != "java.lang.ClassCastException" {
		t.Fatalf("bad cast result/error = %+v/%v, want ClassCastException", result, err)
	}
	result, err = RunClasses(runtimeM4cBundle(classes), "InitCast", "read", nil, 80_000_000)
	if err != nil || result.ExceptionClass != "java.lang.ExceptionInInitializerError" {
		t.Fatalf("initializer cast result/error = %+v/%v, want ExceptionInInitializerError", result, err)
	}
}
