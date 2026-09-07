// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package main

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/jvmevm"
)

func TestRepeatableClassFlag(t *testing.T) {
	var paths classPaths
	if err := paths.Set("first.class"); err != nil {
		t.Fatal(err)
	}
	if err := paths.Set("second.class"); err != nil {
		t.Fatal(err)
	}
	if got := paths.String(); got != "first.class,second.class" {
		t.Fatalf("paths = %q", got)
	}
}

func TestCLILegacyAndExplicitBundleModes(t *testing.T) {
	dir := t.TempDir()
	rootSource := filepath.Join(dir, "Root.java")
	peerSource := filepath.Join(dir, "Peer.java")
	if err := os.WriteFile(rootSource, []byte(`public class Root {
    public static int add(int a, int b) { return a + b; }
    public static int bundled(int a) { return Peer.twice(a) + 2; }
}`), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(peerSource, []byte(`public class Peer { public static int twice(int a) { return a * 2; } }`), 0o600); err != nil {
		t.Fatal(err)
	}
	if output, err := exec.Command("javac", "--release", "8", "-d", dir, rootSource, peerSource).CombinedOutput(); err != nil {
		t.Fatalf("javac: %v\n%s", err, output)
	}
	misleading := filepath.Join(dir, "not-the-declared-name.bin")
	root, err := os.ReadFile(filepath.Join(dir, "Root.class"))
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(misleading, root, 0o600); err != nil {
		t.Fatal(err)
	}

	legacy := exec.Command("go", "run", ".", "-class", misleading, "-method", "add", "-args", "20,22", "-gas", "5000000")
	legacyOut, err := legacy.CombinedOutput()
	if err != nil || !strings.Contains(string(legacyOut), "result=42") {
		t.Fatalf("legacy CLI: %v\n%s", err, legacyOut)
	}
	bundle := exec.Command("go", "run", ".",
		"-class", filepath.Join(dir, "Peer.class"), "-class", misleading,
		"-entry-class", "Root", "-method", "bundled", "-args", "20", "-gas", "30000000")
	bundleOut, err := bundle.CombinedOutput()
	if err != nil || !strings.Contains(string(bundleOut), "result=42") {
		t.Fatalf("bundle CLI: %v\n%s", err, bundleOut)
	}
	missingMetadata := exec.Command("go", "run", ".",
		"-class", filepath.Join(dir, "Peer.class"), "-class", misleading, "-method", "bundled")
	missingOut, err := missingMetadata.CombinedOutput()
	if err == nil || !strings.Contains(string(missingOut), "usage: jvmevm") {
		t.Fatalf("missing entry-class CLI: %v\n%s", err, missingOut)
	}
}

func TestFormatOutcomeUsesExactlyOneOutcomeKey(t *testing.T) {
	if got := formatOutcome(jvmevm.Result{Value: -7}); got != "result=-7" {
		t.Fatalf("value outcome = %q", got)
	}
	if got := formatOutcome(jvmevm.Result{ExceptionClass: "java.lang.ArithmeticException"}); got != "exception=java.lang.ArithmeticException" {
		t.Fatalf("exception outcome = %q", got)
	}
}
