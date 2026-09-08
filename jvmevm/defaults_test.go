// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
	"testing"
	"time"
)

const runtimeM4fbGasLimit = uint64(220_000_000)

func runtimeM4fbBundle(classes map[string][]byte) [][]byte {
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

func runtimeM4fbAssertValue(t *testing.T, classes map[string][]byte, root, method string, want int32) {
	t.Helper()
	result, err := RunClasses(runtimeM4fbBundle(classes), root, method, nil, runtimeM4fbGasLimit)
	if err != nil || result.ExceptionClass != "" || result.Value != want {
		t.Fatalf("%s.%s = %+v/%v, want %d", root, method, result, err, want)
	}
}

func runtimeM4fbAssertException(t *testing.T, classes map[string][]byte, root, method, want string) {
	t.Helper()
	result, err := RunClasses(runtimeM4fbBundle(classes), root, method, nil, runtimeM4fbGasLimit)
	if err != nil || result.ExceptionClass != want || len(result.RevertData) != 36 {
		t.Fatalf("%s.%s = %+v/%v, want %s", root, method, result, err, want)
	}
}

func TestRuntimeM4fbDefaultsMostSpecificClassWinsAndInterfaceSuper(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"defaults/Box.java": `package defaults; public final class Box { int x; }`,
		"defaults/I.java": `package defaults; public interface I {
			default int f(int x){return x+1;} default void put(Box b,int x){b.x=x;}
			default Box pass(Box b){return b;} default int recurse(int n){return n==0?1:n+recurse(n-1);}
		}`,
		"defaults/J.java": `package defaults; public interface J extends I {
			default int f(int x){return I.super.f(x)+2;}
			default int combine(Box b){I.super.put(b,4);return I.super.pass(b).x+I.super.f(3);}
		}`,
		"defaults/K.java": `package defaults; public interface K extends I { }`,
		"defaults/D.java": `package defaults; public interface D extends J,K { }`,
		"defaults/C.java": `package defaults; public class C implements D {
			public int direct(){return D.super.f(4);} public int classSite(){return f(5);}
		}`,
		"defaults/Winner.java": `package defaults; public final class Winner extends C {
			public int f(int x){return x+20;}
		}`,
		"defaults/Root.java": `package defaults; public final class Root {
			static int viaI(I x){return x.f(2);} static int viaD(D x){return x.f(3);}
			public static int run(){C c=new C();Box b=new Box();return viaI(c)*100000+viaD(c)*10000
				+c.direct()*1000+c.classSite()*100+c.combine(b)*10+c.recurse(3)+(viaI(new Winner()));}
		}`,
	})
	// 5,6,7,8,8,7,22 exercise b9, b6 fallback, most-specific J,
	// class-wins dispatch, interface-to-parent and class-to-interface super calls.
	runtimeM4fbAssertValue(t, classes, "defaults/Root", "run", 567909)
}

func TestRuntimeM4fbDefaultInterfaceInitializationOrderAndDedup(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"initdefault/Tracker.java": `package initdefault; public final class Tracker {
			static int n; public static int mark(int x){n=n*10+x;return x;}
		}`,
		"initdefault/A.java": `package initdefault; public interface A {
			int X=Tracker.mark(1); default int a(){return 1;}
		}`,
		"initdefault/B.java": `package initdefault; public interface B extends A {
			int X=Tracker.mark(2); default int b(){return 2;}
		}`,
		"initdefault/C.java": `package initdefault; public interface C extends A {
			int X=Tracker.mark(5);
		}`,
		"initdefault/D.java": `package initdefault; public interface D extends B,C {
			int X=Tracker.mark(6); default int d(){return 6;}
		}`,
		"initdefault/AbstractOnly.java": `package initdefault; public interface AbstractOnly {
			int X=Tracker.mark(9); int missing();
		}`,
		"initdefault/Super.java": `package initdefault; public class Super {
			static int X=Tracker.mark(3);
		}`,
		"initdefault/Root.java": `package initdefault; public final class Root extends Super implements D,AbstractOnly {
			static int X=Tracker.mark(4); public int missing(){return 0;}
			public static int run(){return Tracker.n;}
		}`,
	})
	// Super first, then A/B. C merely inherits A's default and is omitted, D is
	// initialized, the diamond A is deduplicated, and AbstractOnly is untouched.
	runtimeM4fbAssertValue(t, classes, "initdefault/Root", "run", 31264)
}

func TestRuntimeM4fbInitializationReentrancyAndExceptionWrapping(t *testing.T) {
	reentrant := compileJavaSources(t, map[string]string{
		"reinit/Tracker.java": `package reinit; public final class Tracker { static int n; }`,
		"reinit/Helper.java": `package reinit; public final class Helper {
			public static int mark(){Tracker.n=Tracker.n*10+1;return Root.peek();}
		}`,
		"reinit/I.java": `package reinit; public interface I {
			int X=Helper.mark(); default int f(){return 1;}
		}`,
		"reinit/Root.java": `package reinit; public final class Root implements I {
			static int value=finish(); static int finish(){Tracker.n=Tracker.n*10+2;return 7;}
			public static int peek(){return value;} public static int run(){return Tracker.n;}
		}`,
	})
	// Root is marked active before I; Helper's reentrant Root.peek observes the
	// prepared zero and does not restart Root. Root.<clinit> then runs once.
	runtimeM4fbAssertValue(t, reentrant, "reinit/Root", "run", 12)

	wrapping := compileJavaSources(t, map[string]string{
		"wrapdefault/Helper.java": `package wrapdefault; public final class Helper {
			public static int boom(){return 1/zero();} static int zero(){return 0;}
		}`,
		"wrapdefault/I.java": `package wrapdefault; public interface I {
			int X=Helper.boom(); default int f(){return 1;}
		}`,
		"wrapdefault/Root.java": `package wrapdefault; public final class Root implements I {
			public static int run(){return 1;}
		}`,
	})
	runtimeM4fbAssertException(t, wrapping, "wrapdefault/Root", "run", "java.lang.ExceptionInInitializerError")
}

func TestRuntimeM4fbSyntheticBridgeDeclaresInitializationObligation(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"bridgeinit/Tracker.java": `package bridgeinit; public final class Tracker {
			static int n; public static int mark(int x){n=n*10+x;return x;}
		}`,
		"bridgeinit/Parent.java": `package bridgeinit; public interface Parent<T> {
			int X=Tracker.mark(9); T value();
		}`,
		"bridgeinit/Box.java": `package bridgeinit; public final class Box { }`,
		"bridgeinit/Child.java": `package bridgeinit; public interface Child extends Parent<Box> {
			int X=Tracker.mark(2); Box value();
		}`,
		"bridgeinit/Root.java": `package bridgeinit; public final class Root implements Child {
			public Box value(){return new Box();} public static int run(){return Tracker.n;}
		}`,
	})
	child := parseStaticsClass(t, classes["bridgeinit/Child"])
	bridge := child.method(t, "value", "()Ljava/lang/Object;")
	if bridge.access&0x1040 != 0x1040 || len(bridge.code) == 0 {
		t.Fatalf("synthetic interface bridge flags/code = %x/%x", bridge.access, bridge.code)
	}
	// Parent is abstract-only and stays untouched. Child's synthetic concrete
	// bridge is itself enough to require Child initialization.
	runtimeM4fbAssertValue(t, classes, "bridgeinit/Root", "run", 2)
}

func TestRuntimeM4fbBinaryEvolutionICCEAndAME(t *testing.T) {
	conflictOld := compileJavaSources(t, map[string]string{
		"evolve/A.java": `package evolve; public interface A { }`,
		"evolve/B.java": `package evolve; public interface B { }`,
		"evolve/C.java": `package evolve; public class C implements A,B { public C(){} }`,
	})
	conflictCaller := compileJavaSources(t, map[string]string{
		"evolve/A.java": `package evolve; public interface A { int f(); }`,
		"evolve/C.java": `package evolve; public class C implements A { public C(){} public int f(){return 7;} }`,
		"evolve/Root.java": `package evolve; public final class Root {
			public static int run(){A x=new C();return x.f();}
			public static int virtual(){return new C().f();}
			public static int nullCall(){A x=null;return x.f();}
			public static int allocateOnly(){return new C()!=null?1:0;}
			public static void main(String[] x){run();}
		}`,
	})
	newA := compileJavaSources(t, map[string]string{
		"evolve/A.java": `package evolve; public interface A { default int f(){return 1;} }`,
	})
	newB := compileJavaSources(t, map[string]string{
		"evolve/B.java": `package evolve; public interface B { default int f(){return 2;} }`,
	})
	conflict := map[string][]byte{
		"evolve/A": newA["evolve/A"], "evolve/B": newB["evolve/B"],
		"evolve/C": conflictOld["evolve/C"], "evolve/Root": conflictCaller["evolve/Root"],
	}
	runtimeM4fbAssertException(t, conflict, "evolve/Root", "run", "java.lang.IncompatibleClassChangeError")
	runtimeM4fbAssertException(t, conflict, "evolve/Root", "virtual", "java.lang.IncompatibleClassChangeError")
	runtimeM4fbAssertException(t, conflict, "evolve/Root", "nullCall", "java.lang.NullPointerException")
	runtimeM4fbAssertValue(t, conflict, "evolve/Root", "allocateOnly", 1)
	runtimeM4fbJava8Error(t, conflict, "evolve.Root", "java.lang.IncompatibleClassChangeError")

	missingOld := compileJavaSources(t, map[string]string{
		"missing/I.java": `package missing; public interface I { }`,
		"missing/C.java": `package missing; public class C implements I { public C(){} }`,
	})
	missingCaller := compileJavaSources(t, map[string]string{
		"missing/I.java": `package missing; public interface I { int f(); }`,
		"missing/C.java": `package missing; public class C implements I { public C(){} public int f(){return 1;} }`,
		"missing/Root.java": `package missing; public final class Root {
			public static int run(){I x=new C();return x.f();}
			public static void main(String[] x){run();}
		}`,
	})
	missing := map[string][]byte{
		"missing/I": missingCaller["missing/I"], "missing/C": missingOld["missing/C"],
		"missing/Root": missingCaller["missing/Root"],
	}
	runtimeM4fbAssertException(t, missing, "missing/Root", "run", "java.lang.AbstractMethodError")
	runtimeM4fbJava8Error(t, missing, "missing.Root", "java.lang.AbstractMethodError")
}

func TestRuntimeM4fbAbstractSuppressionAndUnrelatedAbstractMaximum(t *testing.T) {
	base := compileJavaSources(t, map[string]string{
		"maxima/A.java": `package maxima; public interface A { default int f(){return 7;} }`,
		"maxima/B.java": `package maxima; public interface B { }`,
		"maxima/C.java": `package maxima; public final class C implements A,B { }`,
		"maxima/Root.java": `package maxima; public final class Root {
			public static int run(){A x=new C();return x.f();}
			public static void main(String[] x){System.out.print(run());}
		}`,
	})
	abstractB := compileJavaSources(t, map[string]string{
		"maxima/B.java": `package maxima; public interface B { int f(); }`,
	})
	unique := map[string][]byte{
		"maxima/A": base["maxima/A"], "maxima/B": abstractB["maxima/B"],
		"maxima/C": base["maxima/C"], "maxima/Root": base["maxima/Root"],
	}
	runtimeM4fbAssertValue(t, unique, "maxima/Root", "run", 7)
	runtimeM4fbJava8Value(t, unique, "maxima.Root", "7")

	suppressionBase := compileJavaSources(t, map[string]string{
		"suppress/P.java": `package suppress; public interface P { default int f(){return 3;} }`,
		"suppress/A.java": `package suppress; public interface A extends P { }`,
		"suppress/C.java": `package suppress; public final class C implements A { }`,
		"suppress/Root.java": `package suppress; public final class Root {
			public static int run(){A x=new C();return x.f();}
			public static void main(String[] x){run();}
		}`,
	})
	abstractA := compileJavaSources(t, map[string]string{
		"suppress/P.java": `package suppress; public interface P { default int f(){return 3;} }`,
		"suppress/A.java": `package suppress; public interface A extends P { int f(); }`,
	})
	suppressed := map[string][]byte{
		"suppress/P": suppressionBase["suppress/P"], "suppress/A": abstractA["suppress/A"],
		"suppress/C": suppressionBase["suppress/C"], "suppress/Root": suppressionBase["suppress/Root"],
	}
	runtimeM4fbAssertException(t, suppressed, "suppress/Root", "run", "java.lang.AbstractMethodError")
	runtimeM4fbJava8Error(t, suppressed, "suppress.Root", "java.lang.AbstractMethodError")
}

func runtimeM4fbJava8Value(t *testing.T, classes map[string][]byte, mainClass, want string) {
	t.Helper()
	output, err := runtimeM4fbRunJava8(t, classes, mainClass)
	if err != nil || strings.TrimSpace(string(output)) != want {
		t.Fatalf("Java 8 %s = %q/%v, want %q", mainClass, output, err, want)
	}
}

func runtimeM4fbRunJava8(t *testing.T, classes map[string][]byte, mainClass string) ([]byte, error) {
	t.Helper()
	java8 := os.Getenv("JAVA_EVM_JAVA8")
	if java8 == "" {
		java8 = "/usr/lib/jvm/java-8-openjdk/bin/java"
	}
	versionOut, err := exec.Command(java8, "-version").CombinedOutput()
	if err != nil || !strings.Contains(string(versionOut), `version "1.8.`) {
		t.Fatalf("Java 8 oracle unavailable or not major 8 at %q: %v\n%s", java8, err, versionOut)
	}
	dir := t.TempDir()
	for name, data := range classes {
		path := filepath.Join(dir, filepath.FromSlash(name)+".class")
		if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, data, 0o600); err != nil {
			t.Fatal(err)
		}
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	output, err := exec.CommandContext(ctx, java8, "-Xmx64m", "-cp", dir, mainClass).CombinedOutput()
	if ctx.Err() != nil {
		t.Fatalf("Java 8 oracle timed out: %v", ctx.Err())
	}
	return output, err
}

func runtimeM4fbJava8Error(t *testing.T, classes map[string][]byte, mainClass, want string) {
	t.Helper()
	java8 := os.Getenv("JAVA_EVM_JAVA8")
	if java8 == "" {
		java8 = "/usr/lib/jvm/java-8-openjdk/bin/java"
	}
	version := exec.Command(java8, "-version")
	versionOut, err := version.CombinedOutput()
	if err != nil || !strings.Contains(string(versionOut), `version "1.8.`) {
		t.Fatalf("Java 8 oracle unavailable or not major 8 at %q: %v\n%s", java8, err, versionOut)
	}
	dir := t.TempDir()
	for name, data := range classes {
		path := filepath.Join(dir, filepath.FromSlash(name)+".class")
		if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, data, 0o600); err != nil {
			t.Fatal(err)
		}
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, java8, "-Xmx64m", "-cp", dir, mainClass)
	output, err := cmd.CombinedOutput()
	if ctx.Err() != nil {
		t.Fatalf("Java 8 oracle timed out: %v", ctx.Err())
	}
	if err == nil || !strings.Contains(string(output), want) {
		t.Fatalf("Java 8 oracle = %v\n%s, want uncaught %s", err, output, want)
	}
}
