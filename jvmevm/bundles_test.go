// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"encoding/binary"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/crypto"
)

func TestRunClassesResolvesDeclaredNamesOrderAndPerClassState(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"p/Root.java": `package p;
public class Root {
    private static int helper(int x) { return x + 1; }
    private static int helper(int x, int y) { return x * 10 + y; }
    public static int run(int x) {
        return helper(x) + helper(x, 3) + PackagePeer.helper(x) + q.PublicPeer.helper(x);
    }
}`,
		"p/PackagePeer.java": `package p;
class PackagePeer { protected static int helper(int x) { return x * 100; } }`,
		"q/PublicPeer.java": `package q;
public class PublicPeer { public static int helper(int x) { return x * 1000; } }`,
	})
	orders := [][][]byte{
		{classes["p/Root"], classes["p/PackagePeer"], classes["q/PublicPeer"]},
		{classes["q/PublicPeer"], classes["p/Root"], classes["p/PackagePeer"]},
		{classes["p/PackagePeer"], classes["q/PublicPeer"], classes["p/Root"]},
	}
	for i, order := range orders {
		result, err := RunClasses(order, "p/Root", "run", []int32{2}, 30_000_000)
		if err != nil {
			t.Fatalf("order %d: %v", i, err)
		}
		// (2+1) + (2*10+3) + 200 + 2000
		if result.Value != 2226 || result.ExceptionClass != "" || result.GasUsed == 0 {
			t.Fatalf("order %d result = %+v, want 2226", i, result)
		}
		t.Logf("order=%d gas=%d", i, result.GasUsed)
	}
}

func TestRunClassesDefaultPackageAndCrossClassRecursionOutcomes(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"Root.java": `public class Root {
    public static int parity(int n) { return Left.even(n); }
    public static int divide(int n) { return Right.divide(n); }
    public static int overflow(int n) { return Left.forever(n); }
}`,
		"Left.java": `class Left {
    static int even(int n) { return n == 0 ? 1 : Right.odd(n - 1); }
    static int forever(int n) { return Right.forever(n + 1); }
}`,
		"Right.java": `class Right {
    static int odd(int n) { return n == 0 ? 0 : Left.even(n - 1); }
    static int divide(int n) { return 10 / n; }
    static int forever(int n) { return Left.forever(n + 1); }
}`,
	})
	leftRef := firstBundleCallRef(t, classes["Left"], "forever")
	rightRef := firstBundleCallRef(t, classes["Right"], "forever")
	if leftRef != rightRef {
		t.Fatalf("fixture did not produce equal cross-class Methodref indices: Left=%d Right=%d", leftRef, rightRef)
	}
	bundle := [][]byte{classes["Right"], classes["Root"], classes["Left"]}
	for _, tc := range []struct {
		n int32
		w int32
	}{{12, 1}, {13, 0}} {
		got, err := RunClasses(bundle, "Root", "parity", []int32{tc.n}, 30_000_000)
		if err != nil || got.Value != tc.w {
			t.Fatalf("parity(%d) = %+v/%v, want %d", tc.n, got, err, tc.w)
		}
	}
	arithmetic, err := RunClasses(bundle, "Root", "divide", []int32{0}, 30_000_000)
	if err != nil || arithmetic.ExceptionClass != "java.lang.ArithmeticException" {
		t.Fatalf("cross-class arithmetic = %+v/%v", arithmetic, err)
	}
	overflow, err := RunClasses(bundle, "Root", "overflow", []int32{0}, 100_000_000)
	if err != nil || overflow.ExceptionClass != "java.lang.StackOverflowError" {
		t.Fatalf("cross-class overflow = %+v/%v", overflow, err)
	}
	t.Logf("parity/cross-exception/frame-cap gas: arithmetic=%d overflow=%d shared_ref_index=%d", arithmetic.GasUsed, overflow.GasUsed, leftRef)
}

func TestRunClassesFrozenLinkErrorsAndLazyUnsupportedClasses(t *testing.T) {
	base := compileJavaSources(t, map[string]string{
		"a/Root.java":       `package a; public class Root { public static int run(int x) { return b.Peer.go(x); } }`,
		"b/Peer.java":       `package b; public class Peer { public static int go(int x) { return x + 1; } }`,
		"Initialized.java":  `public class Initialized { static int value = 7; public static int get(int x) { return x + value; } }`,
		"Caller.java":       `public class Caller { public static int run(int x) { return Initialized.get(x); } }`,
		"Synchronized.java": `public class Synchronized { public synchronized static int get(int x) { return x; } }`,
		"Base.java":         `public class Base { }`,
		"Child.java":        `public class Child extends Base { public static int run(int x) { return x; } }`,
		"Face.java":         `public interface Face { static int run(int x) { return x; } }`,
	})
	root, peer, initialized := base["a/Root"], base["b/Peer"], base["Initialized"]

	assertBundleError(t, nil, "a/Root", "run", nil, "LinkError(uint256,uint256)", 1, 0)
	tooMany := make([][]byte, 65)
	for i := range tooMany {
		tooMany[i] = root
	}
	assertBundleError(t, tooMany, "a/Root", "run", []int32{1}, "LinkError(uint256,uint256)", 1, 65)
	assertBundleError(t, [][]byte{peer, root, peer}, "a/Root", "run", []int32{1}, "LinkError(uint256,uint256)", 2, 2)
	assertBundleError(t, [][]byte{peer}, "a/Root", "run", []int32{1}, "LinkError(uint256,uint256)", 3, 0)

	parsed := parseCallTestClass(t, root)
	callPC := bytes.IndexByte(parsed.code(t, "run"), 0xb8)
	if callPC < 0 {
		t.Fatal("root has no invokestatic")
	}
	assertBundleError(t, [][]byte{root}, "a/Root", "run", []int32{1}, "LinkError(uint256,uint256)", 4, uint64(callPC))

	// A supplied initializer is lazy, but runs when its class is actually entered.
	ok, err := RunClasses([][]byte{initialized, root, peer}, "a/Root", "run", []int32{41}, 30_000_000)
	if err != nil || ok.Value != 42 {
		t.Fatalf("unused initializer affected execution: %+v/%v", ok, err)
	}
	entered, err := RunClasses([][]byte{root, initialized}, "Initialized", "get", []int32{7}, 30_000_000)
	if err != nil || entered.Value != 14 {
		t.Fatalf("entered initializer result = %+v/%v, want 14", entered, err)
	}
	called, err := RunClasses([][]byte{base["Caller"], initialized}, "Caller", "run", []int32{7}, 30_000_000)
	if err != nil || called.Value != 14 {
		t.Fatalf("callee initializer result = %+v/%v, want 14", called, err)
	}
	unsupportedResult, unsupportedErr := RunClasses(
		[][]byte{base["Synchronized"]}, "Synchronized", "get", []int32{7}, 30_000_000,
	)
	assertErrorSelector(t, unsupportedResult, unsupportedErr, "MethodError(uint256)")
	inherited, err := RunClasses(
		[][]byte{base["Base"], base["Child"]}, "Child", "run", []int32{7}, 30_000_000,
	)
	if err != nil || inherited.Value != 7 {
		t.Fatalf("supplied ordinary superclass result = %+v/%v, want 7", inherited, err)
	}
	assertBundleError(t, [][]byte{base["Face"]}, "Face", "run", []int32{7}, "LinkError(uint256,uint256)", 5, 0)

	bad := append([]byte(nil), peer...)
	bad[0] = 0
	result, err := RunClasses([][]byte{root, bad}, "a/Root", "run", []int32{1}, 30_000_000)
	assertErrorSelector(t, result, err, "ClassError(uint256,uint256)")
}

func TestRunClassesExactSignatureAndAccessChecks(t *testing.T) {
	compiled := compileJavaSources(t, map[string]string{
		"a/Root.java": `package a; public class Root { public static int run(int x) { return b.Peer.go(x); } }`,
		"b/Peer.java": `package b; public class Peer { public static int go(int x) { return x + 1; } }`,
	})
	root, peer := compiled["a/Root"], compiled["b/Peer"]
	rootParsed := parseCallTestClass(t, root)
	callPC := bytes.IndexByte(rootParsed.code(t, "run"), 0xb8)

	privatePeer := append([]byte(nil), peer...)
	peerParsed := parseCallTestClass(t, privatePeer)
	off := peerParsed.methodAccess["go"]
	flags := binary.BigEndian.Uint16(privatePeer[off:])
	binary.BigEndian.PutUint16(privatePeer[off:], (flags&^0x0001)|0x0002)
	assertBundleError(t, [][]byte{privatePeer, root}, "a/Root", "run", []int32{1}, "CallError(uint256,uint256)", 4, uint64(callPC))

	packagePeer := append([]byte(nil), peer...)
	binary.BigEndian.PutUint16(packagePeer[off:], flags&^0x0001)
	assertBundleError(t, [][]byte{root, packagePeer}, "a/Root", "run", []int32{1}, "CallError(uint256,uint256)", 4, uint64(callPC))

	nonpublicPeer := append([]byte(nil), peer...)
	classOff := bundleClassAccessOffset(t, nonpublicPeer)
	classFlags := binary.BigEndian.Uint16(nonpublicPeer[classOff:])
	binary.BigEndian.PutUint16(nonpublicPeer[classOff:], classFlags&^0x0001)
	assertBundleError(t, [][]byte{root, nonpublicPeer}, "a/Root", "run", []int32{1}, "CallError(uint256,uint256)", 4, uint64(callPC))

	// Keep the owner declaration but supply a separately compiled version without the exact method.
	other := compileJavaSources(t, map[string]string{
		"b/Peer.java": `package b; public class Peer { public static int other(int x) { return x; } }`,
	})["b/Peer"]
	assertBundleError(t, [][]byte{root, other}, "a/Root", "run", []int32{1}, "CallError(uint256,uint256)", 3, uint64(callPC))
}

func assertBundleError(t *testing.T, classes [][]byte, entryClass, method string, args []int32, signature string, code, detail uint64) {
	t.Helper()
	result, err := RunClasses(classes, entryClass, method, args, 100_000_000)
	assertSolidityError(t, result, err, signature, code, detail)
}

func assertErrorSelector(t *testing.T, result Result, err error, signature string) {
	t.Helper()
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error = %+v/%v, want %s", result, err, signature)
	}
	selector := cryptoSelector(signature)
	if len(result.RevertData) < 4 || !bytes.Equal(result.RevertData[:4], selector) {
		t.Fatalf("revert data = 0x%x, want %s selector", result.RevertData, signature)
	}
}

func cryptoSelector(signature string) []byte {
	// Keccak is already an execution dependency; keeping this helper local makes
	// malformed-class checks independent of the numeric ClassError payload.
	return crypto.Keccak256([]byte(signature))[:4]
}

func firstBundleCallRef(t *testing.T, classfile []byte, method string) uint16 {
	t.Helper()
	parsed := parseCallTestClass(t, classfile)
	code := parsed.code(t, method)
	pc := bytes.IndexByte(code, 0xb8)
	if pc < 0 || pc+2 >= len(code) {
		t.Fatalf("%s has no complete invokestatic: %x", method, code)
	}
	return binary.BigEndian.Uint16(code[pc+1 : pc+3])
}

func bundleClassAccessOffset(t *testing.T, data []byte) int {
	t.Helper()
	p := &testClassParser{t: t, data: data}
	if p.u4() != 0xcafebabe {
		t.Fatal("bad class magic")
	}
	p.skip(4)
	cpCount := int(p.u2())
	for i := 1; i < cpCount; i++ {
		switch tag := p.u1(); tag {
		case 1:
			p.skip(int(p.u2()))
		case 3, 4:
			p.skip(4)
		case 5, 6:
			p.skip(8)
			i++
		case 7, 8, 16, 19, 20:
			p.skip(2)
		case 9, 10, 11, 12, 17, 18:
			p.skip(4)
		case 15:
			p.skip(3)
		default:
			t.Fatalf("unknown constant-pool tag %d", tag)
		}
	}
	return p.pos
}

func compileJavaSources(t *testing.T, sources map[string]string) map[string][]byte {
	t.Helper()
	dir := t.TempDir()
	paths := make([]string, 0, len(sources))
	for rel, source := range sources {
		path := filepath.Join(dir, filepath.FromSlash(rel))
		if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(source), 0o600); err != nil {
			t.Fatal(err)
		}
		paths = append(paths, path)
	}
	argv := append([]string{"--release", "8", "-d", dir}, paths...)
	if output, err := exec.Command("javac", argv...).CombinedOutput(); err != nil {
		t.Fatalf("javac failed: %v\n%s", err, output)
	}
	classes := make(map[string][]byte)
	err := filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
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
	})
	if err != nil {
		t.Fatal(err)
	}
	return classes
}
