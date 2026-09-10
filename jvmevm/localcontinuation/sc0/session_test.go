package sc0

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"math/big"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"runtime"
	"strconv"
	"strings"
	"testing"
	"time"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
)

const (
	sc0HarnessOrdinaryGas = uint64(100_000_000)
	sc0HarnessBoundaryGas = uint64(1_000_000_000)
)

type sc0HarnessClass struct {
	Name   string `json:"name"`
	SHA256 string `json:"sha256"`
}

type sc0HarnessOutcome struct {
	Lifecycle    string `json:"lifecycle"`
	Result       int32  `json:"result"`
	JavaKind     uint8  `json:"javaKind"`
	JavaClassHex string `json:"javaClassHex"`
}

type sc0HarnessFixture struct {
	ID           string            `json:"id"`
	Group        string            `json:"group"`
	Source       string            `json:"source"`
	SourceSHA256 string            `json:"sourceSHA256"`
	EntryClass   string            `json:"entryClass"`
	Entry        string            `json:"entry"`
	Args         []int32           `json:"args"`
	Outcome      sc0HarnessOutcome `json:"outcome"`
	Classes      []sc0HarnessClass `json:"classes"`
	Raw          [][]byte          `json:"-"`
	JavaClass    []byte            `json:"-"`
}

type sc0HarnessFixtureManifest struct {
	Schema   uint32              `json:"schema"`
	Compiler string              `json:"compiler"`
	Fixtures []sc0HarnessFixture `json:"fixtures"`
}

func sc0HarnessFixtureRoot(t *testing.T) string {
	t.Helper()
	_, source, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("cannot locate SC0 test source")
	}
	return filepath.Clean(filepath.Join(filepath.Dir(source), "../../testdata/local/sc0"))
}

func sc0HarnessFixtures(t *testing.T) []sc0HarnessFixture {
	t.Helper()
	root := sc0HarnessFixtureRoot(t)
	rawManifest, err := os.ReadFile(filepath.Join(root, "manifest.json"))
	if err != nil {
		t.Fatal(err)
	}
	var manifest sc0HarnessFixtureManifest
	if err := json.Unmarshal(rawManifest, &manifest); err != nil {
		t.Fatal(err)
	}
	if manifest.Schema != 1 || manifest.Compiler != "javac --release 8 -g:none" || len(manifest.Fixtures) != 24 {
		t.Fatalf("unexpected fixture manifest header: schema=%d compiler=%q fixtures=%d", manifest.Schema, manifest.Compiler, len(manifest.Fixtures))
	}
	groups := map[string]int{}
	ids := make(map[string]bool)
	for i := range manifest.Fixtures {
		fixture := &manifest.Fixtures[i]
		if fixture.ID == "" || ids[fixture.ID] {
			t.Fatalf("empty or duplicate fixture id %q", fixture.ID)
		}
		ids[fixture.ID] = true
		groups[fixture.Group]++
		source, err := os.ReadFile(filepath.Join(root, "src", fixture.Source))
		if err != nil {
			t.Fatal(err)
		}
		if got := sha256.Sum256(source); hex.EncodeToString(got[:]) != fixture.SourceSHA256 {
			t.Fatalf("fixture %s source hash=%x want=%s", fixture.ID, got, fixture.SourceSHA256)
		}
		if len(fixture.Classes) == 0 || len(fixture.Classes) > 4 {
			t.Fatalf("fixture %s bundle has %d classes", fixture.ID, len(fixture.Classes))
		}
		total := 0
		for _, class := range fixture.Classes {
			classfile, err := os.ReadFile(filepath.Join(root, "classes", class.Name))
			if err != nil {
				t.Fatal(err)
			}
			hash := sha256.Sum256(classfile)
			if hex.EncodeToString(hash[:]) != class.SHA256 {
				t.Fatalf("fixture %s class %s sha256=%x want=%s", fixture.ID, class.Name, hash, class.SHA256)
			}
			fixture.Raw = append(fixture.Raw, classfile)
			total += len(classfile)
		}
		if total > 64*1024 {
			t.Fatalf("fixture %s raw bundle=%d", fixture.ID, total)
		}
		fixture.JavaClass, err = hex.DecodeString(fixture.Outcome.JavaClassHex)
		if err != nil {
			t.Fatalf("fixture %s javaClassHex: %v", fixture.ID, err)
		}
	}
	wantGroups := map[string]int{"SC0Chars": 8, "SC0CopyIntern": 8, "SC0Flow": 8}
	if len(groups) != len(wantGroups) {
		t.Fatalf("fixture groups=%v want=%v", groups, wantGroups)
	}
	for group, count := range wantGroups {
		if groups[group] != count {
			t.Fatalf("fixture group %s has %d roots, want %d", group, groups[group], count)
		}
	}
	return manifest.Fixtures
}

func sc0HarnessRequireRuntime(t *testing.T) {
	t.Helper()
	code, err := Runtime()
	if err != nil {
		t.Fatalf("required pinned SC0 runtime dependency unavailable: %v", err)
	}
	if len(code) == 0 || len(code) > 256*1024 {
		t.Fatalf("runtime length %d outside frozen LOCAL bound", len(code))
	}
	if _, err := ABI(); err != nil {
		t.Fatal(err)
	}
}

func TestSC0HarnessFrozenOuterABI(t *testing.T) {
	wantAddress := common.HexToAddress("0x4a564d45564d53433052554e54494d4500000001")
	if sc0HarnessContractAddress != wantAddress || sc0HarnessStoreMarker != "JVMEVM-MC-SC0-DISK-STORE-1\n" {
		t.Fatalf("address/marker mismatch: %s %q", sc0HarnessContractAddress, sc0HarnessStoreMarker)
	}
	valid := []SliceResult{
		{Schema: 1, Lifecycle: 1}, {Schema: 1, Lifecycle: 2, Result: -7},
		{Schema: 1, Lifecycle: 3, JavaKind: 1, JavaRef: 4},
		{Schema: 1, Lifecycle: 3, JavaRef: 5, JavaClass: []byte{0xff, 0x00}},
	}
	for kind := uint8(2); kind <= 12; kind++ {
		valid = append(valid, SliceResult{Schema: 1, Lifecycle: 3, JavaKind: kind, JavaRef: uint32(kind)})
	}
	for _, result := range valid {
		if err := sc0HarnessValidateSliceResult(result); err != nil {
			t.Fatalf("valid shape %+v: %v", result, err)
		}
	}
	invalid := []SliceResult{
		{Schema: 0, Lifecycle: 1}, {Schema: 1, Lifecycle: 1, JavaRef: 1},
		{Schema: 1, Lifecycle: 2, JavaClass: []byte("X")},
		{Schema: 1, Lifecycle: 3, JavaRef: 1},
		{Schema: 1, Lifecycle: 3, JavaKind: 1, JavaRef: 1, JavaClass: []byte("java/lang/ArithmeticException")},
		{Schema: 1, Lifecycle: 3, JavaKind: 13, JavaRef: 1},
	}
	for _, result := range invalid {
		if err := sc0HarnessValidateSliceResult(result); err == nil {
			t.Fatalf("invalid shape accepted: %+v", result)
		}
	}
}

func TestSC0HarnessFixturePins(t *testing.T) {
	fixtures := sc0HarnessFixtures(t)
	wantIDs := []string{
		"chars-empty", "chars-ascii-length", "chars-nul-units", "chars-surrogate-pair",
		"chars-isolated-high", "chars-isolated-low", "chars-defensive", "chars-hash-cache",
		"copy-distinct", "copy-hash", "copy-category2-caller", "copy-literal-intern",
		"copy-constructed-first", "copy-earlier-handle-insert", "copy-hash-collision", "copy-interface-dispatch",
		"flow-null-chars", "flow-null-copy", "flow-fail-then-valid", "flow-chars-in-clinit",
		"flow-init-failure-then-ncdfe", "flow-loop64", "flow-argument-failure", "flow-throwable-integration",
	}
	wantResults := []int32{0, 5, 1, 1, 55296, 56320, 97099, 2112, 1, 2112, 1, 111, 111, 1, 1, 1, 1, 1, 12, 1, 3, 64076, 1, 1}
	for i, fixture := range fixtures {
		if fixture.ID != wantIDs[i] || fixture.Outcome.Lifecycle != "RETURNED" || fixture.Outcome.Result != wantResults[i] || fixture.Outcome.JavaKind != 0 || len(fixture.JavaClass) != 0 {
			t.Fatalf("fixture %d differs from frozen root/outcome: %+v", i, fixture)
		}
	}
}

func TestSC0HarnessJavaOracles(t *testing.T) {
	fixtures := sc0HarnessFixtures(t)
	root := sc0HarnessFixtureRoot(t)
	compiled := t.TempDir()
	sources := []string{}
	for _, name := range []string{"SC0Chars", "SC0CopyIntern", "SC0Flow"} {
		sources = append(sources, filepath.Join(root, "src", name+".java"))
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	output, err := exec.CommandContext(ctx, "javac", append([]string{"--release", "8", "-g:none", "-d", compiled}, sources...)...).CombinedOutput()
	cancel()
	if err != nil {
		t.Fatalf("trusted javac --release 8: %v\n%s", err, output)
	}
	checked := make(map[string]bool)
	for _, fixture := range fixtures {
		for i, class := range fixture.Classes {
			if checked[class.Name] {
				continue
			}
			got, err := os.ReadFile(filepath.Join(compiled, class.Name))
			if err != nil {
				t.Fatal(err)
			}
			if !bytes.Equal(got, fixture.Raw[i]) {
				t.Fatalf("rebuilt %s differs from pinned raw bytes", class.Name)
			}
			checked[class.Name] = true
		}
	}
	oracleSource := `import java.lang.reflect.*;
public final class SC0HarnessOracle {
  public static void main(String[] a) throws Exception {
    Class<?> owner = Class.forName(a[1]);
    Class<?>[] types = new Class<?>[a.length - 3]; Object[] values = new Object[types.length];
    for (int i=0; i<types.length; i++) { types[i]=Integer.TYPE; values[i]=Integer.valueOf(a[i+3]); }
    Method method = owner.getDeclaredMethod(a[2], types); method.setAccessible(true);
    try { System.out.print("R:" + ((Integer)method.invoke(null, values)).intValue()); }
    catch (InvocationTargetException wrapped) { System.out.print("U:" + wrapped.getCause().getClass().getName().replace('.', '/')); }
  }
}`
	oraclePath := filepath.Join(compiled, "SC0HarnessOracle.java")
	if err := os.WriteFile(oraclePath, []byte(oracleSource), 0o600); err != nil {
		t.Fatal(err)
	}
	ctx, cancel = context.WithTimeout(context.Background(), 30*time.Second)
	output, err = exec.CommandContext(ctx, "javac", "--release", "8", "-g:none", "-cp", compiled, "-d", compiled, oraclePath).CombinedOutput()
	cancel()
	if err != nil {
		t.Fatalf("compile trusted host-only oracle: %v\n%s", err, output)
	}
	java8 := "/usr/lib/jvm/java-8-openjdk/bin/java"
	if home := os.Getenv("JAVA8_HOME"); home != "" {
		java8 = filepath.Join(home, "bin", "java")
	}
	java21 := "/usr/lib/jvm/jdk-21.0.9/bin/java"
	if home := os.Getenv("JAVA21_HOME"); home != "" {
		java21 = filepath.Join(home, "bin", "java")
	}
	for _, oracle := range []struct{ name, path string }{{"java8", java8}, {"java21", java21}} {
		if _, err := os.Stat(oracle.path); err != nil {
			t.Fatalf("required %s oracle unavailable at %s: %v", oracle.name, oracle.path, err)
		}
		for _, fixture := range fixtures {
			args := []string{"-Xmx64m", "-cp", compiled, "SC0HarnessOracle", fixture.ID, fixture.EntryClass, fixture.Entry}
			for _, value := range fixture.Args {
				args = append(args, strconv.FormatInt(int64(value), 10))
			}
			ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			output, err := exec.CommandContext(ctx, oracle.path, args...).CombinedOutput()
			cancel()
			want := fmt.Sprintf("R:%d", fixture.Outcome.Result)
			if fixture.Outcome.Lifecycle == "UNCAUGHT_JAVA" {
				name := string(fixture.JavaClass)
				if fixture.Outcome.JavaKind == 1 {
					name = "java/lang/ArithmeticException"
				}
				want = "U:" + name
			}
			if err != nil || strings.TrimSpace(string(output)) != want {
				t.Fatalf("%s %s output=%q want=%q error=%v", oracle.name, fixture.ID, output, want, err)
			}
		}
	}
}

func TestSC0HarnessContinuationCorpus(t *testing.T) {
	sc0HarnessRequireRuntime(t)
	code, _ := Runtime()
	runtimeSHA, _ := RuntimeHash()
	t.Logf("SC0 runtime bytes=%d sha256=%s codeHash=%s", len(code), runtimeSHA, crypto.Keccak256Hash(code))
	owner := common.HexToAddress("0x10000000000000000000000000000000000000d0")
	session, err := NewMemory(owner)
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	if session.testCodeInstalls != 1 {
		t.Fatalf("code installations=%d want=1", session.testCodeInstalls)
	}
	unknown, err := session.Head(crypto.Keccak256Hash([]byte("unknown")))
	if err != nil || unknown != (Head{}) {
		t.Fatalf("unknown head=%+v error=%v", unknown, err)
	}
	chainIDs := map[string]bool{
		"chars-defensive": true, "chars-surrogate-pair": true, "copy-distinct": true,
		"copy-literal-intern": true, "copy-constructed-first": true, "copy-earlier-handle-insert": true,
		"copy-hash-collision": true, "flow-fail-then-valid": true,
		"flow-init-failure-then-ncdfe": true, "flow-argument-failure": true,
	}
	for _, fixture := range sc0HarnessFixtures(t) {
		fixture := fixture
		t.Run(fixture.ID, func(t *testing.T) {
			control := sc0HarnessRunChain(t, session, fixture, "one-call", 4096, 4096)
			if control.Slice.Epoch != 1 {
				t.Fatalf("one-call epoch=%d", control.Slice.Epoch)
			}
			if fixture.ID == "flow-loop64" {
				got := sc0HarnessRunChain(t, session, fixture, "q7", 7, 4096)
				if got.Slice.MachineStateRoot != control.Slice.MachineStateRoot || got.Slice.TotalJvmSteps != control.Slice.TotalJvmSteps || got.Slice.TotalInternalSteps != control.Slice.TotalInternalSteps || !sc0HarnessSameOutcome(got.Slice, control.Slice) {
					t.Fatalf("loop64 q7 final mismatch: slice=%+v control=%+v", got.Slice, control.Slice)
				}
				return
			}
			if !chainIDs[fixture.ID] {
				return
			}
			for _, profile := range []struct {
				name string
				jvm  uint64
			}{{"q1", 1}, {"q7", 7}} {
				got := sc0HarnessRunChain(t, session, fixture, profile.name, profile.jvm, 4096)
				if got.Slice.MachineStateRoot != control.Slice.MachineStateRoot || got.Slice.TotalJvmSteps != control.Slice.TotalJvmSteps || got.Slice.TotalInternalSteps != control.Slice.TotalInternalSteps || !sc0HarnessSameOutcome(got.Slice, control.Slice) {
					t.Fatalf("%s final mismatch: slice=%+v control=%+v", profile.name, got.Slice, control.Slice)
				}
				if got.Slice.CheckpointRoot == control.Slice.CheckpointRoot {
					t.Fatalf("%s history root unexpectedly equals one-call root", profile.name)
				}
			}
		})
	}
}

func TestSC0HarnessPreOpcodeSnapshots(t *testing.T) {
	sc0HarnessRequireRuntime(t)
	wanted := map[string]bool{
		"chars-defensive": true, "chars-surrogate-pair": true, "copy-distinct": true,
		"copy-literal-intern": true, "copy-constructed-first": true, "copy-earlier-handle-insert": true,
		"copy-hash-collision": true, "flow-fail-then-valid": true,
		"flow-init-failure-then-ncdfe": true, "flow-argument-failure": true,
	}
	session, err := NewMemory(common.HexToAddress("0x12000000000000000000000000000000000000d0"))
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	for _, fixture := range sc0HarnessFixtures(t) {
		if !wanted[fixture.ID] {
			continue
		}
		id := crypto.Keccak256Hash([]byte(t.Name() + ":" + fixture.ID))
		result, err := session.Start(id, fixture.Raw, fixture.EntryClass, fixture.Entry, fixture.Args, 1, 1, sc0HarnessOrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
		inspection, err := sc0HarnessInspectMachine(result.Checkpoint)
		if err != nil {
			t.Fatal(err)
		}
		if result.Slice.Lifecycle != 1 || result.Slice.ExecutedJvmSteps != 0 || result.Slice.ExecutedInternalSteps != 1 || inspection.NextHandle != 0 {
			t.Fatalf("%s initial internal-unit snapshot already executed/allotted Java state: slice=%+v machine=%+v", fixture.ID, result.Slice, inspection)
		}
	}
}

func sc0HarnessSameOutcome(a, b SliceResult) bool {
	return a.Lifecycle == b.Lifecycle && a.Result == b.Result && a.JavaKind == b.JavaKind && a.JavaRef == b.JavaRef && bytes.Equal(a.JavaClass, b.JavaClass)
}

func sc0HarnessLegacyTL0Fixtures(t *testing.T) []sc0HarnessFixture {
	t.Helper()
	root := filepath.Clean(filepath.Join(sc0HarnessFixtureRoot(t), "../tl0"))
	rawManifest, err := os.ReadFile(filepath.Join(root, "manifest.json"))
	if err != nil {
		t.Fatal(err)
	}
	var manifest sc0HarnessFixtureManifest
	if err := json.Unmarshal(rawManifest, &manifest); err != nil {
		t.Fatal(err)
	}
	if manifest.Schema != 1 || len(manifest.Fixtures) != 24 {
		t.Fatalf("unexpected retained TL0 fixture count/schema: %d/%d", manifest.Schema, len(manifest.Fixtures))
	}
	for i := range manifest.Fixtures {
		fixture := &manifest.Fixtures[i]
		for _, class := range fixture.Classes {
			raw, err := os.ReadFile(filepath.Join(root, "classes", class.Name))
			if err != nil {
				t.Fatal(err)
			}
			if hash := sha256.Sum256(raw); hex.EncodeToString(hash[:]) != class.SHA256 {
				t.Fatalf("retained TL0 class %s hash mismatch", class.Name)
			}
			fixture.Raw = append(fixture.Raw, raw)
		}
		fixture.JavaClass, err = hex.DecodeString(fixture.Outcome.JavaClassHex)
		if err != nil {
			t.Fatal(err)
		}
	}
	return manifest.Fixtures
}

func TestSC0HarnessRetainsTL0Corpus(t *testing.T) {
	sc0HarnessRequireRuntime(t)
	selected := map[string]bool{
		"construction-custom-fields": true, "identity-call-unwind": true, "identity-rethrow": true,
		"initialization-init-before-new": true, "initialization-wraps-non-error": true,
		"initialization-propagates-custom-error": true, "constructor-self-direct": true,
		"constructor-self-through-call": true, "constructor-self-escaped-after-failure": true,
		"constructor-self-in-class-init": true,
	}
	session, err := NewMemory(common.HexToAddress("0x13000000000000000000000000000000000000d0"))
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	for _, fixture := range sc0HarnessLegacyTL0Fixtures(t) {
		control := sc0HarnessRunChain(t, session, fixture, "tl0-control", 4096, 4096)
		if !selected[fixture.ID] {
			continue
		}
		for _, profile := range []struct {
			name string
			jvm  uint64
		}{{"tl0-q1", 1}, {"tl0-q7", 7}} {
			got := sc0HarnessRunChain(t, session, fixture, profile.name, profile.jvm, 4096)
			if got.Slice.TotalJvmSteps != control.Slice.TotalJvmSteps || got.Slice.TotalInternalSteps != control.Slice.TotalInternalSteps || !sc0HarnessSameOutcome(got.Slice, control.Slice) {
				t.Fatalf("retained %s %s counters/outcome mismatch: got=%+v control=%+v", fixture.ID, profile.name, got.Slice, control.Slice)
			}
		}
	}
}

func TestSC0HarnessAcceptedLC0FixtureBytes(t *testing.T) {
	sc0HarnessRequireRuntime(t)
	root := filepath.Clean(filepath.Join(sc0HarnessFixtureRoot(t), "../lc0/classes"))
	load := func(names ...string) [][]byte {
		t.Helper()
		var raw [][]byte
		for _, name := range names {
			b, err := os.ReadFile(filepath.Join(root, name))
			if err != nil {
				t.Fatal(err)
			}
			raw = append(raw, b)
		}
		return raw
	}
	fixtures := []sc0HarnessFixture{
		{ID: "lc0-call-loop", EntryClass: "LC0CallLoop", Entry: "run", Args: []int32{5}, Outcome: sc0HarnessOutcome{Lifecycle: "RETURNED", Result: 15}, Raw: load("LC0CallLoop.class")},
		{ID: "lc0-alias-string", EntryClass: "LC0AliasString", Entry: "run", Outcome: sc0HarnessOutcome{Lifecycle: "RETURNED", Result: 36}, Raw: load("LC0AliasString.class", "LC0AliasBox.class")},
		{ID: "lc0-init-exception", EntryClass: "LC0InitException", Entry: "run", Outcome: sc0HarnessOutcome{Lifecycle: "RETURNED", Result: 10}, Raw: load("LC0InitException.class", "LC0InitDep.class")},
	}
	session, err := NewMemory(common.HexToAddress("0x11000000000000000000000000000000000000d0"))
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	for _, fixture := range fixtures {
		control := sc0HarnessRunChain(t, session, fixture, "lc0-one", 4096, 4096)
		for _, profile := range []struct {
			name     string
			jvm      uint64
			internal uint32
		}{{"lc0-q1", 1, 4096}, {"lc0-q7", 7, 4096}, {"lc0-internal1", 4096, 1}} {
			got := sc0HarnessRunChain(t, session, fixture, profile.name, profile.jvm, profile.internal)
			if got.Slice.MachineStateRoot != control.Slice.MachineStateRoot || got.Slice.TotalJvmSteps != control.Slice.TotalJvmSteps || got.Slice.TotalInternalSteps != control.Slice.TotalInternalSteps || !sc0HarnessSameOutcome(got.Slice, control.Slice) {
				t.Fatalf("%s %s final mismatch: got=%+v control=%+v", fixture.ID, profile.name, got.Slice, control.Slice)
			}
		}
	}
}

func sc0HarnessCompileTrustedSource(t *testing.T, className, source string) []byte {
	t.Helper()
	dir := t.TempDir()
	path := filepath.Join(dir, className+".java")
	if err := os.WriteFile(path, []byte(source), 0o600); err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	output, err := exec.CommandContext(ctx, "javac", "--release", "8", "-g:none", "-d", dir, path).CombinedOutput()
	cancel()
	if err != nil {
		t.Fatalf("compile trusted supplementary class: %v\n%s", err, output)
	}
	raw, err := os.ReadFile(filepath.Join(dir, className+".class"))
	if err != nil {
		t.Fatal(err)
	}
	return raw
}

func sc0HarnessRunChain(t *testing.T, session *Session, fixture sc0HarnessFixture, profile string, jvm uint64, internal uint32) Result {
	t.Helper()
	instance := crypto.Keccak256Hash([]byte(t.Name() + ":" + fixture.ID + ":" + profile))
	result, err := session.Start(instance, fixture.Raw, fixture.EntryClass, fixture.Entry, fixture.Args, jvm, internal, sc0HarnessOrdinaryGas)
	if err != nil {
		t.Fatalf("%s start: %v", profile, err)
	}
	var units uint64
	var maxHandle uint32
	var sawPending, sawCause, sawNested, sawEscapedCause bool
	var sawConstructorBeforeSuper, sawConstructorAfterSuper, sawConstructorFieldWrite, sawPendingStaticAlias bool
	for slices := 1; ; slices++ {
		sc0HarnessCheckSlice(t, session, instance, result, jvm, internal, slices)
		units += result.Slice.ExecutedJvmSteps + uint64(result.Slice.ExecutedInternalSteps)
		if units > 4096 {
			t.Fatalf("%s exceeded frozen ordinary 4096-dispatch-unit allowance", profile)
		}
		inspection, inspectErr := sc0HarnessInspectMachine(result.Checkpoint)
		if inspectErr != nil {
			t.Fatalf("%s inspect epoch %d: %v", profile, result.Slice.Epoch, inspectErr)
		}
		if inspection.NextHandle > maxHandle {
			maxHandle = inspection.NextHandle
		}
		sawPending = sawPending || inspection.Pending
		sawConstructorBeforeSuper = sawConstructorBeforeSuper || inspection.ConstructorBeforeSuper
		sawConstructorAfterSuper = sawConstructorAfterSuper || inspection.ConstructorAfterSuper
		for _, value := range inspection.ObjectInts {
			if value == fixture.Outcome.Result {
				sawConstructorFieldWrite = true
			}
		}
		for _, ref := range inspection.StaticRefs {
			if inspection.Pending && ref == inspection.PendingRef {
				sawPendingStaticAlias = true
			}
		}
		sawCause = sawCause || len(inspection.WrapperCauses) != 0
		for _, relation := range inspection.WrapperCauses {
			if relation.Cause == 0 || relation.Cause >= relation.Wrapper {
				t.Fatalf("%s invalid cause relation %+v", fixture.ID, relation)
			}
			for _, ref := range inspection.StaticRefs {
				if ref == relation.Cause {
					sawEscapedCause = true
				}
			}
		}
		sawNested = sawNested || inspection.Depth > 1
		if result.Slice.Lifecycle != 1 {
			wantLifecycle := uint8(2)
			if fixture.Outcome.Lifecycle == "UNCAUGHT_JAVA" {
				wantLifecycle = 3
			}
			if result.Slice.Lifecycle != wantLifecycle || result.Slice.Result != fixture.Outcome.Result || result.Slice.JavaKind != fixture.Outcome.JavaKind || !bytes.Equal(result.Slice.JavaClass, fixture.JavaClass) {
				t.Fatalf("%s terminal slice=%+v want=%+v class=%x", profile, result.Slice, fixture.Outcome, fixture.JavaClass)
			}
			if wantLifecycle == 3 && result.Slice.JavaRef == 0 {
				t.Fatalf("%s uncaught result has zero ref", profile)
			}
			if profile == "q1" {
				if maxHandle == 0 {
					t.Fatalf("%s q1 produced no authoritative heap allocation", fixture.ID)
				}
				if strings.HasPrefix(fixture.ID, "constructor-self-") && (!sawPending || !sawConstructorBeforeSuper || !sawConstructorAfterSuper || !sawConstructorFieldWrite) {
					t.Fatalf("%s q1 missed constructor phase/write/throw snapshots: pending=%v beforeSuper=%v afterSuper=%v fieldWrite=%v", fixture.ID, sawPending, sawConstructorBeforeSuper, sawConstructorAfterSuper, sawConstructorFieldWrite)
				}
				if fixture.ID == "constructor-self-escaped-after-failure" && !sawPendingStaticAlias {
					t.Fatalf("%s did not retain an initialized escaped REF while constructor throw was pending", fixture.ID)
				}
				if (fixture.ID == "initialization-wraps-non-error" || fixture.ID == "constructor-self-in-class-init" || fixture.ID == "flow-init-failure-then-ncdfe") && !sawCause {
					t.Fatalf("%s q1 did not retain an EIIE cause record", fixture.ID)
				}
				if fixture.ID == "constructor-self-in-class-init" && !sawEscapedCause {
					t.Fatalf("%s EIIE cause was never the receiver retained in a static REF", fixture.ID)
				}
				if fixture.ID == "identity-call-unwind" && !sawNested {
					t.Fatalf("%s q1 did not capture nested call frames", fixture.ID)
				}
			}
			return result
		}
		if slices >= 256 {
			t.Fatalf("%s exceeded 256 slices", profile)
		}
		result, err = session.Resume(instance, result.Slice.Epoch, result.Slice.CheckpointRoot, fixture.Raw, result.Checkpoint, jvm, internal, sc0HarnessOrdinaryGas)
		if err != nil {
			t.Fatalf("%s resume epoch %d: %v", profile, result.Slice.Epoch, err)
		}
	}
}

func sc0HarnessCheckSlice(t *testing.T, session *Session, instance common.Hash, result Result, jvm uint64, internal uint32, number int) {
	t.Helper()
	if result.Slice.Schema != 1 || result.Slice.Epoch != uint64(number) || result.Slice.ExecutedJvmSteps > jvm || result.Slice.ExecutedInternalSteps > internal {
		t.Fatalf("invalid slice %d: %+v budgets=%d/%d", number, result.Slice, jvm, internal)
	}
	if len(result.Logs) != 1 || result.Logs[0].Address != sc0HarnessContractAddress {
		t.Fatalf("slice %d logs=%d/address mismatch", number, len(result.Logs))
	}
	if crypto.Keccak256Hash(result.Checkpoint) != result.Slice.CheckpointRoot {
		t.Fatalf("slice %d checkpoint hash mismatch", number)
	}
	stored, err := session.ReadCheckpoint(result.Slice.CheckpointRoot)
	if err != nil || !bytes.Equal(stored, result.Checkpoint) {
		t.Fatalf("slice %d stored checkpoint: %v equal=%v", number, err, bytes.Equal(stored, result.Checkpoint))
	}
	head, err := session.Head(instance)
	if err != nil {
		t.Fatal(err)
	}
	if head.Owner != session.owner || head.Epoch != result.Slice.Epoch || head.CheckpointRoot != result.Slice.CheckpointRoot || head.MachineStateRoot != result.Slice.MachineStateRoot || head.Lifecycle != result.Slice.Lifecycle || head.RuntimeCodeHash != session.codeHash {
		t.Fatalf("slice %d head mismatch: %+v slice=%+v", number, head, result.Slice)
	}
	t.Logf("epoch=%d checkpoint=%s machine=%s trie=%s code=%s jvm=%d+%d internal=%d+%d gas=%d bytes=%d lifecycle=%d", result.Slice.Epoch, result.Slice.CheckpointRoot, result.Slice.MachineStateRoot, session.stateRoot, session.codeHash, result.Slice.TotalJvmSteps, result.Slice.ExecutedJvmSteps, result.Slice.TotalInternalSteps, result.Slice.ExecutedInternalSteps, result.GasUsed, len(result.Checkpoint), result.Slice.Lifecycle)
}

func TestSC0HarnessEVMFailuresPreserveHead(t *testing.T) {
	sc0HarnessRequireRuntime(t)
	owner := common.HexToAddress("0x18000000000000000000000000000000000000c0")
	session, err := NewMemory(owner)
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	fixture := sc0HarnessFixtures(t)[0]
	instance := crypto.Keccak256Hash([]byte(t.Name()))
	parent, err := session.Start(instance, fixture.Raw, fixture.EntryClass, fixture.Entry, fixture.Args, 1, 4096, sc0HarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	sc0HarnessExpectFailurePreservesHead(t, session, instance, func() (Result, error) {
		return session.Start(instance, fixture.Raw, fixture.EntryClass, fixture.Entry, fixture.Args, 1, 4096, sc0HarnessOrdinaryGas)
	})
	sc0HarnessExpectFailurePreservesHead(t, session, instance, func() (Result, error) {
		return session.Resume(instance, parent.Slice.Epoch+1, parent.Slice.CheckpointRoot, fixture.Raw, parent.Checkpoint, 1, 4096, sc0HarnessOrdinaryGas)
	})
	sc0HarnessExpectFailurePreservesHead(t, session, instance, func() (Result, error) {
		return session.Resume(instance, parent.Slice.Epoch, crypto.Keccak256Hash([]byte("wrong-root")), fixture.Raw, parent.Checkpoint, 1, 4096, sc0HarnessOrdinaryGas)
	})
	wrongRaw := make([][]byte, len(fixture.Raw))
	for i := range fixture.Raw {
		wrongRaw[i] = append([]byte(nil), fixture.Raw[i]...)
	}
	wrongRaw[0][len(wrongRaw[0])-1] ^= 1
	sc0HarnessExpectFailurePreservesHead(t, session, instance, func() (Result, error) {
		return session.Resume(instance, parent.Slice.Epoch, parent.Slice.CheckpointRoot, wrongRaw, parent.Checkpoint, 1, 4096, sc0HarnessOrdinaryGas)
	})
	sc0HarnessExpectFailurePreservesHead(t, session, instance, func() (Result, error) {
		return session.Resume(instance, parent.Slice.Epoch, parent.Slice.CheckpointRoot, fixture.Raw, parent.Checkpoint, 1, 4096, 50_000)
	})
	other := crypto.Keccak256Hash([]byte("wrong-instance"))
	sc0HarnessExpectFailurePreservesHead(t, session, instance, func() (Result, error) {
		return session.Resume(other, parent.Slice.Epoch, parent.Slice.CheckpointRoot, fixture.Raw, parent.Checkpoint, 1, 4096, sc0HarnessOrdinaryGas)
	})
	terminalInstance := crypto.Keccak256Hash([]byte("terminal" + t.Name()))
	terminal, err := session.Start(terminalInstance, fixture.Raw, fixture.EntryClass, fixture.Entry, fixture.Args, 4096, 4096, sc0HarnessOrdinaryGas)
	if err != nil || terminal.Slice.Lifecycle != 2 {
		t.Fatalf("terminal setup lifecycle=%d error=%v", terminal.Slice.Lifecycle, err)
	}
	sc0HarnessExpectFailurePreservesHead(t, session, terminalInstance, func() (Result, error) {
		return session.Resume(terminalInstance, terminal.Slice.Epoch, terminal.Slice.CheckpointRoot, fixture.Raw, terminal.Checkpoint, 1, 4096, sc0HarnessOrdinaryGas)
	})
}

func TestSC0HarnessMidCopyOOGRollbackRetry(t *testing.T) {
	sc0HarnessRequireRuntime(t)
	fixture := sc0HarnessFixtures(t)[6]
	session, err := NewMemory(common.HexToAddress("0x19000000000000000000000000000000000000c0"))
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	instance := crypto.Keccak256Hash([]byte(t.Name()))
	parent, err := session.Start(instance, fixture.Raw, fixture.EntryClass, fixture.Entry, fixture.Args, 1, 4096, sc0HarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	for slices := 1; slices < 192; slices++ {
		inspection, err := sc0HarnessInspectMachine(parent.Checkpoint)
		if err != nil {
			t.Fatal(err)
		}
		midCopy := false
		for _, nonzero := range inspection.ArrayNonzero {
			midCopy = midCopy || inspection.ConstructorAfterSuper && nonzero > 0 && nonzero < 3
		}
		if midCopy {
			break
		}
		parent, err = session.Resume(instance, parent.Slice.Epoch, parent.Slice.CheckpointRoot, fixture.Raw, parent.Checkpoint, 1, 4096, sc0HarnessOrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
		if parent.Slice.Lifecycle != 1 || slices == 191 {
			t.Fatal("did not reach a runnable partial defensive-copy checkpoint")
		}
	}
	before, err := session.Head(instance)
	if err != nil {
		t.Fatal(err)
	}
	failed, err := session.Resume(instance, parent.Slice.Epoch, parent.Slice.CheckpointRoot, fixture.Raw, parent.Checkpoint, 1, 4096, 50_000)
	if err == nil {
		t.Fatal("mid-copy low-gas resume unexpectedly succeeded")
	}
	if failed.GasUsed == 0 || !reflect.DeepEqual(failed.Slice, SliceResult{}) || len(failed.Checkpoint) != 0 || len(failed.Logs) != 0 {
		t.Fatalf("failed mid-copy resume exposed child state: %+v", failed)
	}
	after, err := session.Head(instance)
	if err != nil || after != before {
		t.Fatalf("mid-copy OOG changed head: before=%+v after=%+v err=%v", before, after, err)
	}
	retry, err := session.Resume(instance, parent.Slice.Epoch, parent.Slice.CheckpointRoot, fixture.Raw, parent.Checkpoint, 1, 4096, sc0HarnessOrdinaryGas)
	if err != nil || retry.Slice.Epoch != parent.Slice.Epoch+1 {
		t.Fatalf("mid-copy retry failed: slice=%+v err=%v", retry.Slice, err)
	}
}

func sc0HarnessExpectFailurePreservesHead(t *testing.T, session *Session, instance common.Hash, call func() (Result, error)) {
	t.Helper()
	before, err := session.Head(instance)
	if err != nil {
		t.Fatal(err)
	}
	result, err := call()
	if err == nil {
		t.Fatal("hard EVM failure returned success")
	}
	if len(result.Logs) != 0 {
		t.Fatalf("failed call returned %d child logs", len(result.Logs))
	}
	after, headErr := session.Head(instance)
	if headErr != nil || after != before {
		t.Fatalf("failed call changed head: before=%+v after=%+v error=%v", before, after, headErr)
	}
}

// A failed publication must not expose its speculative child. Derive the retry
// expectation from a separate successful EVM run, not from failed-call output.
func sc0HarnessControlChild(t *testing.T, owner common.Address, instance common.Hash, fixture sc0HarnessFixture, parent Result) Result {
	t.Helper()
	control, err := NewMemory(owner)
	if err != nil {
		t.Fatal(err)
	}
	defer control.Close()
	cp, err := control.Start(instance, fixture.Raw, fixture.EntryClass, fixture.Entry, fixture.Args, 1, 4096, sc0HarnessOrdinaryGas)
	if err != nil || cp.Slice.CheckpointRoot != parent.Slice.CheckpointRoot {
		t.Fatalf("control parent mismatch: %v", err)
	}
	child, err := control.Resume(instance, cp.Slice.Epoch, cp.Slice.CheckpointRoot, fixture.Raw, cp.Checkpoint, 1, 4096, sc0HarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	return child
}

func TestSC0HarnessDiskFailuresAndReopen(t *testing.T) {
	sc0HarnessRequireRuntime(t)
	owner := common.HexToAddress("0x20000000000000000000000000000000000000c0")
	fixture := sc0HarnessFixtures(t)[0]
	for _, point := range []sc0HarnessFaultPoint{sc0HarnessFaultAfterBlob, sc0HarnessFaultAfterTrie, sc0HarnessFaultBeforeManifest} {
		t.Run(fmt.Sprint(point), func(t *testing.T) {
			dir := t.TempDir()
			session, err := Open(dir, owner)
			if err != nil {
				t.Fatal(err)
			}
			instance := crypto.Keccak256Hash([]byte(t.Name()))
			parent, err := session.Start(instance, fixture.Raw, fixture.EntryClass, fixture.Entry, fixture.Args, 1, 4096, sc0HarnessOrdinaryGas)
			if err != nil {
				t.Fatal(err)
			}
			controlChild := sc0HarnessControlChild(t, owner, instance, fixture, parent)
			fired := false
			session.testFault = func(got sc0HarnessFaultPoint) error {
				if got == point && !fired {
					fired = true
					return errors.New("test durable failure")
				}
				return nil
			}
			failedChild, err := session.Resume(instance, parent.Slice.Epoch, parent.Slice.CheckpointRoot, fixture.Raw, parent.Checkpoint, 1, 4096, sc0HarnessOrdinaryGas)
			if err == nil || !fired {
				t.Fatalf("fault point %d did not fail", point)
			}
			if len(failedChild.Logs) != 0 || len(failedChild.Checkpoint) != 0 || !reflect.DeepEqual(failedChild.Slice, SliceResult{}) || failedChild.GasUsed == 0 {
				t.Fatalf("fault point %d exposed an unpublished child or lost diagnostic gas", point)
			}
			session.testFault = nil
			head, err := session.Head(instance)
			if err != nil {
				t.Fatal(err)
			}
			if head.Epoch != parent.Slice.Epoch || head.CheckpointRoot != parent.Slice.CheckpointRoot {
				t.Fatalf("head advanced before manifest: %+v parent=%+v", head, parent.Slice)
			}
			retry, err := session.Resume(instance, parent.Slice.Epoch, parent.Slice.CheckpointRoot, fixture.Raw, parent.Checkpoint, 1, 4096, sc0HarnessOrdinaryGas)
			if err != nil {
				t.Fatal(err)
			}
			if retry.Slice.CheckpointRoot != controlChild.Slice.CheckpointRoot || !bytes.Equal(retry.Checkpoint, controlChild.Checkpoint) {
				t.Fatal("retry from old durable root differs from independent successful control")
			}
			if err := session.Close(); err != nil {
				t.Fatal(err)
			}
			reopened, err := Open(dir, owner)
			if err != nil {
				t.Fatal(err)
			}
			defer reopened.Close()
			if reopened.testCodeInstalls != 0 {
				t.Fatalf("reopen installed code %d times", reopened.testCodeInstalls)
			}
			reopenedHead, err := reopened.Head(instance)
			if err != nil || reopenedHead.CheckpointRoot != retry.Slice.CheckpointRoot {
				t.Fatalf("reopened head=%+v err=%v", reopenedHead, err)
			}
		})
	}
	t.Run("after-publication-ambiguous", func(t *testing.T) {
		dir := t.TempDir()
		session, err := Open(dir, owner)
		if err != nil {
			t.Fatal(err)
		}
		instance := crypto.Keccak256Hash([]byte(t.Name()))
		parent, err := session.Start(instance, fixture.Raw, fixture.EntryClass, fixture.Entry, fixture.Args, 1, 4096, sc0HarnessOrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
		controlChild := sc0HarnessControlChild(t, owner, instance, fixture, parent)
		session.testFault = func(point sc0HarnessFaultPoint) error {
			if point == sc0HarnessFaultAfterManifestRename {
				return errors.New("ambiguous directory fsync")
			}
			return nil
		}
		child, err := session.Resume(instance, parent.Slice.Epoch, parent.Slice.CheckpointRoot, fixture.Raw, parent.Checkpoint, 1, 4096, sc0HarnessOrdinaryGas)
		if err == nil {
			t.Fatal("after-publication failure was hidden")
		}
		if len(child.Logs) != 0 || len(child.Checkpoint) != 0 || !reflect.DeepEqual(child.Slice, SliceResult{}) {
			t.Fatal("ambiguous publication exposed a speculative child before reopen")
		}
		if _, err := session.Head(instance); err == nil {
			t.Fatal("ambiguous session remained usable")
		}
		session.Close()
		reopened, err := Open(dir, owner)
		if err != nil {
			t.Fatal(err)
		}
		defer reopened.Close()
		head, err := reopened.Head(instance)
		if err != nil || head.CheckpointRoot != controlChild.Slice.CheckpointRoot {
			t.Fatalf("published child not recovered by reopen: head=%+v control=%+v err=%v", head, controlChild.Slice, err)
		}
	})
}

func TestSC0HarnessDiskOwnerBinding(t *testing.T) {
	sc0HarnessRequireRuntime(t)
	dir := t.TempDir()
	owner := common.HexToAddress("0x28000000000000000000000000000000000000c0")
	session, err := Open(dir, owner)
	if err != nil {
		t.Fatal(err)
	}
	if err := session.Close(); err != nil {
		t.Fatal(err)
	}
	wrong := common.HexToAddress("0x29000000000000000000000000000000000000c0")
	if other, err := Open(dir, wrong); err == nil {
		other.Close()
		t.Fatal("disk store reopened under wrong owner")
	}
	reopened, err := Open(dir, owner)
	if err != nil {
		t.Fatal(err)
	}
	defer reopened.Close()
	if reopened.testCodeInstalls != 0 {
		t.Fatal("owner-binding reopen reinstalled code")
	}
}

func TestSC0HarnessRefusesUnrelatedDirectory(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "user-file")
	if err := os.WriteFile(path, []byte("preserve me"), 0o600); err != nil {
		t.Fatal(err)
	}
	fresh, err := sc0HarnessPrepareDirectory(dir)
	if err == nil || fresh {
		t.Fatal("unrelated nonempty directory accepted")
	}
	got, readErr := os.ReadFile(path)
	if readErr != nil || string(got) != "preserve me" {
		t.Fatalf("user file changed: %q %v", got, readErr)
	}
}

func TestSC0HarnessInvalidMetadataBeforeLevelDB(t *testing.T) {
	dir := t.TempDir()
	for _, name := range []string{sc0HarnessStateDirectory, sc0HarnessBlobDirectory} {
		if err := os.Mkdir(filepath.Join(dir, name), 0o700); err != nil {
			t.Fatal(err)
		}
	}
	if err := os.WriteFile(filepath.Join(dir, sc0HarnessStoreMarkerName), []byte("JVMEVM-MC-LC0-DISK-STORE-1\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, sc0HarnessManifestName), []byte("{}"), 0o600); err != nil {
		t.Fatal(err)
	}
	if session, err := Open(dir, common.HexToAddress("0x1234")); err == nil {
		session.Close()
		t.Fatal("cross-namespace metadata accepted")
	}
	entries, err := os.ReadDir(filepath.Join(dir, sc0HarnessStateDirectory))
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) != 0 {
		t.Fatalf("invalid metadata caused LevelDB side effects: %v", entries)
	}
}

func TestSC0HarnessOwnedManifestTemporaryPreserved(t *testing.T) {
	sc0HarnessRequireRuntime(t)
	dir := t.TempDir()
	owner := common.HexToAddress("0x1234")
	session, err := Open(dir, owner)
	if err != nil {
		t.Fatal(err)
	}
	fixture := sc0HarnessFixtures(t)[0]
	id := crypto.Keccak256Hash([]byte(t.Name()))
	parent, err := session.Start(id, fixture.Raw, fixture.EntryClass, fixture.Entry, fixture.Args, 1, 4096, sc0HarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	if err := session.Close(); err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(dir, ".durable-head-owned-leftover")
	if err := os.WriteFile(path, []byte("unpublished"), 0o600); err != nil {
		t.Fatal(err)
	}
	reopened, err := Open(dir, owner)
	if err != nil {
		t.Fatal(err)
	}
	defer reopened.Close()
	head, err := reopened.Head(id)
	if err != nil || head.CheckpointRoot != parent.Slice.CheckpointRoot {
		t.Fatalf("old head=%+v error=%v", head, err)
	}
	if _, err := os.Stat(path); err != nil {
		t.Fatalf("owned unpublished temporary was removed: %v", err)
	}
}

func TestSC0HarnessExistingBlobMustSync(t *testing.T) {
	sc0HarnessRequireRuntime(t)
	dir := t.TempDir()
	owner := common.HexToAddress("0x1234")
	session, err := Open(dir, owner)
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	fixture := sc0HarnessFixtures(t)[0]
	id := crypto.Keccak256Hash([]byte(t.Name()))
	parent, err := session.Start(id, fixture.Raw, fixture.EntryClass, fixture.Entry, fixture.Args, 1, 4096, sc0HarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	control := sc0HarnessControlChild(t, owner, id, fixture, parent)
	session.testFault = func(point sc0HarnessFaultPoint) error {
		if point == sc0HarnessFaultAfterBlob {
			return errors.New("orphan blob")
		}
		return nil
	}
	failed, err := session.Resume(id, parent.Slice.Epoch, parent.Slice.CheckpointRoot, fixture.Raw, parent.Checkpoint, 1, 4096, sc0HarnessOrdinaryGas)
	if err == nil || failed.GasUsed == 0 || !reflect.DeepEqual(failed.Slice, SliceResult{}) || len(failed.Checkpoint) != 0 || len(failed.Logs) != 0 {
		t.Fatal("failed publication leaked child or lost gas")
	}
	seen := false
	session.testFault = func(point sc0HarnessFaultPoint) error {
		if point == sc0HarnessFaultBeforeExistingBlobSync {
			seen = true
			return errors.New("sync unavailable")
		}
		return nil
	}
	failed, err = session.Resume(id, parent.Slice.Epoch, parent.Slice.CheckpointRoot, fixture.Raw, parent.Checkpoint, 1, 4096, sc0HarnessOrdinaryGas)
	if err == nil || !seen || failed.GasUsed == 0 || !reflect.DeepEqual(failed.Slice, SliceResult{}) || len(failed.Checkpoint) != 0 || len(failed.Logs) != 0 {
		t.Fatal("existing orphan skipped sync boundary")
	}
	head, err := session.Head(id)
	if err != nil || head.CheckpointRoot != parent.Slice.CheckpointRoot {
		t.Fatalf("failed sync advanced head: %+v %v", head, err)
	}
	session.testFault = nil
	child, err := session.Resume(id, parent.Slice.Epoch, parent.Slice.CheckpointRoot, fixture.Raw, parent.Checkpoint, 1, 4096, sc0HarnessOrdinaryGas)
	if err != nil || !bytes.Equal(child.Checkpoint, control.Checkpoint) {
		t.Fatalf("orphan retry diverged: %v", err)
	}
}

func TestSC0HarnessEntryTypesAndBoundedReads(t *testing.T) {
	sc0HarnessRequireRuntime(t)
	owner := common.HexToAddress("0x1234")
	for _, entry := range []string{sc0HarnessStateDirectory, sc0HarnessBlobDirectory, sc0HarnessManifestName} {
		t.Run(entry, func(t *testing.T) {
			dir := filepath.Join(t.TempDir(), "store")
			session, err := Open(dir, owner)
			if err != nil {
				t.Fatal(err)
			}
			if err := session.Close(); err != nil {
				t.Fatal(err)
			}
			original := filepath.Join(dir, entry)
			moved := filepath.Join(filepath.Dir(dir), "saved-entry")
			if err := os.Rename(original, moved); err != nil {
				t.Fatal(err)
			}
			if err := os.Symlink(moved, original); err != nil {
				t.Fatal(err)
			}
			if bad, err := Open(dir, owner); err == nil {
				bad.Close()
				t.Fatal("linked internal store entry accepted")
			}
			if _, err := os.Stat(moved); err != nil {
				t.Fatalf("saved entry changed: %v", err)
			}
		})
	}
	dir := t.TempDir()
	session, err := Open(dir, owner)
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	root := crypto.Keccak256Hash([]byte("oversized"))
	path := session.sc0HarnessBlobPath(root)
	if err := os.WriteFile(path, make([]byte, sc0HarnessMaxCheckpointSize+1), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := session.ReadCheckpoint(root); err == nil {
		t.Fatal("oversized blob accepted")
	}
	if err := os.Remove(path); err != nil {
		t.Fatal(err)
	}
	target := filepath.Join(t.TempDir(), "opaque")
	if err := os.WriteFile(target, []byte("opaque"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(target, path); err != nil {
		t.Fatal(err)
	}
	if _, err := session.ReadCheckpoint(root); err == nil {
		t.Fatal("linked blob accepted")
	}
}

func TestSC0HarnessProcessReopen(t *testing.T) {
	if os.Getenv("JVMEVM_SC0_CHILD") != "" {
		sc0HarnessProcessChild(t)
		return
	}
	sc0HarnessRequireRuntime(t)
	fixtures := sc0HarnessFixtures(t)
	owner := common.HexToAddress("0x30000000000000000000000000000000000000c0")
	// Reopen a genuine mid-copy constructor checkpoint and a checkpoint carrying
	// the null-constructor initialization failure/cause in genuinely new processes.
	// Start installs code once; children only load committed trie/code and blobs.
	for _, fixtureIndex := range []int{6, 20} {
		fixture := fixtures[fixtureIndex]
		t.Run(fixture.ID, func(t *testing.T) {
			controlSession, err := NewMemory(owner)
			if err != nil {
				t.Fatal(err)
			}
			control := sc0HarnessRunChain(t, controlSession, fixture, "process-control", 4096, 4096)
			controlSession.Close()

			dir := t.TempDir()
			session, err := Open(dir, owner)
			if err != nil {
				t.Fatal(err)
			}
			budget := uint64(1)
			instance := crypto.Keccak256Hash([]byte(t.Name()))
			checkpoint, err := session.Start(instance, fixture.Raw, fixture.EntryClass, fixture.Entry, fixture.Args, budget, 4096, sc0HarnessOrdinaryGas)
			if err != nil {
				t.Fatal(err)
			}
			var sawNullPending bool
			for slices := 1; slices < 192; slices++ {
				inspection, err := sc0HarnessInspectMachine(checkpoint.Checkpoint)
				if err != nil {
					t.Fatal(err)
				}
				sawNullPending = sawNullPending || inspection.Pending && inspection.PendingKind == 6
				ready := false
				if fixtureIndex == 6 {
					for _, nonzero := range inspection.ArrayNonzero {
						ready = ready || inspection.ConstructorAfterSuper && nonzero > 0 && nonzero < 3
					}
				} else {
					ready = sawNullPending && len(inspection.WrapperCauses) != 0
				}
				if ready {
					break
				}
				if checkpoint.Slice.Lifecycle != 1 {
					t.Fatalf("fixture terminated before restart state: slice=%+v machine=%+v", checkpoint.Slice, inspection)
				}
				checkpoint, err = session.Resume(instance, checkpoint.Slice.Epoch, checkpoint.Slice.CheckpointRoot, fixture.Raw, checkpoint.Checkpoint, 1, 4096, sc0HarnessOrdinaryGas)
				if err != nil {
					t.Fatal(err)
				}
				if slices == 191 {
					t.Fatal("did not reach frozen mid-copy/pending-cause restart state")
				}
			}
			inspection, err := sc0HarnessInspectMachine(checkpoint.Checkpoint)
			if err != nil {
				t.Fatal(err)
			}
			if checkpoint.Slice.Lifecycle != 1 || inspection.Lifecycle != 1 {
				t.Fatalf("q1 restart checkpoint is not runnable: slice=%+v machine=%+v", checkpoint.Slice, inspection)
			}
			if err := session.Close(); err != nil {
				t.Fatal(err)
			}
			alias := filepath.Join(filepath.Dir(dir), filepath.Base(dir)+"-alias")
			if err := os.Symlink(dir, alias); err != nil {
				t.Fatal(err)
			}
			command := exec.Command(os.Args[0], "-test.run=^TestSC0HarnessProcessReopen$")
			command.Env = append(os.Environ(),
				"JVMEVM_SC0_CHILD=1", "JVMEVM_SC0_DIR="+alias, "JVMEVM_SC0_OWNER="+owner.Hex(),
				"JVMEVM_SC0_FIXTURE="+strconv.Itoa(fixtureIndex), "JVMEVM_SC0_INSTANCE="+instance.Hex(),
				"JVMEVM_SC0_EPOCH="+strconv.FormatUint(checkpoint.Slice.Epoch, 10), "JVMEVM_SC0_ROOT="+checkpoint.Slice.CheckpointRoot.Hex())
			output, err := command.Output()
			if err != nil {
				t.Fatalf("child process: %v stdout=%s stderr=%s", err, output, sc0HarnessExitStderr(err))
			}
			var child struct {
				Machine  common.Hash `json:"machine"`
				Result   int32       `json:"result"`
				Jvm      uint64      `json:"jvm"`
				Internal uint64      `json:"internal"`
			}
			var payload []byte
			for _, line := range bytes.Split(output, []byte{'\n'}) {
				if bytes.HasPrefix(bytes.TrimSpace(line), []byte{'{'}) {
					payload = bytes.TrimSpace(line)
					break
				}
			}
			if err := json.Unmarshal(payload, &child); err != nil {
				t.Fatalf("decode child output %q: %v", output, err)
			}
			if child.Machine != control.Slice.MachineStateRoot || child.Result != fixture.Outcome.Result || child.Jvm != control.Slice.TotalJvmSteps || child.Internal != control.Slice.TotalInternalSteps {
				t.Fatalf("restarted result=%+v control=%+v", child, control.Slice)
			}
		})
	}
}

func sc0HarnessProcessChild(t *testing.T) {
	fixtures := sc0HarnessFixtures(t)
	index, err := strconv.Atoi(os.Getenv("JVMEVM_SC0_FIXTURE"))
	if err != nil || index < 0 || index >= len(fixtures) {
		t.Fatal("bad child fixture")
	}
	owner := common.HexToAddress(os.Getenv("JVMEVM_SC0_OWNER"))
	instance := common.HexToHash(os.Getenv("JVMEVM_SC0_INSTANCE"))
	epoch, err := strconv.ParseUint(os.Getenv("JVMEVM_SC0_EPOCH"), 10, 64)
	if err != nil {
		t.Fatal(err)
	}
	root := common.HexToHash(os.Getenv("JVMEVM_SC0_ROOT"))
	session, err := Open(os.Getenv("JVMEVM_SC0_DIR"), owner)
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	if session.testCodeInstalls != 0 {
		t.Fatal("child process reinstalled runtime code")
	}
	checkpoint, err := session.ReadCheckpoint(root)
	if err != nil {
		t.Fatal(err)
	}
	fixture := fixtures[index]
	var result Result
	for slices := 0; slices < 256; slices++ {
		result, err = session.Resume(instance, epoch, root, fixture.Raw, checkpoint, 7, 1, sc0HarnessOrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
		if result.Slice.Lifecycle != 1 {
			if result.Slice.Lifecycle != 2 {
				t.Fatalf("child lifecycle=%d", result.Slice.Lifecycle)
			}
			encoded, _ := json.Marshal(struct {
				Machine  common.Hash `json:"machine"`
				Result   int32       `json:"result"`
				Jvm      uint64      `json:"jvm"`
				Internal uint64      `json:"internal"`
			}{result.Slice.MachineStateRoot, result.Slice.Result, result.Slice.TotalJvmSteps, result.Slice.TotalInternalSteps})
			fmt.Println(string(encoded))
			return
		}
		epoch, root, checkpoint = result.Slice.Epoch, result.Slice.CheckpointRoot, result.Checkpoint
	}
	t.Fatal("child exceeded 256 slices")
}

func sc0HarnessExitStderr(err error) string {
	var exit *exec.ExitError
	if errors.As(err, &exit) {
		return string(exit.Stderr)
	}
	return ""
}

type sc0HarnessCause struct {
	Wrapper uint32
	Cause   uint32
}

type sc0HarnessMachineInspection struct {
	Lifecycle              uint8
	Depth                  uint16
	NextHandle             uint32
	Pending                bool
	PendingKind            uint8
	PendingRef             uint32
	PendingPC              uint64
	PendingPCOverflow      bool
	WrapperCauses          []sc0HarnessCause
	StaticRefs             []uint32
	ObjectInts             []int32
	ArrayNonzero           []uint32
	ConstructorBeforeSuper bool
	ConstructorAfterSuper  bool
}

type sc0HarnessCursor struct {
	blob []byte
	off  int
}

func (c *sc0HarnessCursor) take(size int) ([]byte, error) {
	if size < 0 || c.off > len(c.blob)-size {
		return nil, fmt.Errorf("truncated at %d taking %d", c.off, size)
	}
	out := c.blob[c.off : c.off+size]
	c.off += size
	return out, nil
}
func (c *sc0HarnessCursor) u8() (uint8, error) {
	b, e := c.take(1)
	if e != nil {
		return 0, e
	}
	return b[0], nil
}
func (c *sc0HarnessCursor) u16() (uint16, error) {
	b, e := c.take(2)
	if e != nil {
		return 0, e
	}
	return binary.BigEndian.Uint16(b), nil
}
func (c *sc0HarnessCursor) u32() (uint32, error) {
	b, e := c.take(4)
	if e != nil {
		return 0, e
	}
	return binary.BigEndian.Uint32(b), nil
}

// Test-only inspection records counters/IDs for assertions. Its output is never
// supplied to Start or Resume and production Go has no machine parser.
func sc0HarnessInspectMachine(checkpoint []byte) (sc0HarnessMachineInspection, error) {
	var out sc0HarnessMachineInspection
	if len(checkpoint) < 216 || string(checkpoint[:8]) != "JVMSC001" {
		return out, errors.New("bad checkpoint envelope")
	}
	length := binary.BigEndian.Uint32(checkpoint[212:216])
	if int(length) != len(checkpoint)-216 {
		return out, errors.New("machine length mismatch")
	}
	c := &sc0HarnessCursor{blob: checkpoint[216:]}
	magic, _ := c.take(4)
	if string(magic) != "SCS1" {
		return out, errors.New("bad machine magic")
	}
	out.Lifecycle, _ = c.u8()
	if _, err := c.take(4 + 1 + 4 + 8 + 8); err != nil {
		return out, err
	}
	for i := 0; i < 2; i++ {
		n, err := c.u16()
		if err != nil {
			return out, err
		}
		if _, err := c.take(int(n)); err != nil {
			return out, err
		}
	}
	argc, err := c.u8()
	if err != nil {
		return out, err
	}
	if _, err := c.take(int(argc) * 4); err != nil {
		return out, err
	}
	classes, err := c.u16()
	if err != nil {
		return out, err
	}
	for i := 0; i < int(classes); i++ {
		if _, err := c.take(2); err != nil {
			return out, err
		}
		statics, err := c.u16()
		if err != nil {
			return out, err
		}
		for j := uint16(0); j < statics; j++ {
			if _, err := c.take(2); err != nil {
				return out, err
			}
			cell, err := c.take(32)
			if err != nil {
				return out, err
			}
			value := new(big.Int).SetBytes(cell)
			tag := new(big.Int).Rsh(new(big.Int).Set(value), 64).Uint64()
			if tag == 2 && value.Uint64() != 0 {
				out.StaticRefs = append(out.StaticRefs, uint32(value.Uint64()))
			}
		}
	}
	out.Depth, err = c.u16()
	if err != nil {
		return out, err
	}
	for i := 0; i < int(out.Depth); i++ {
		if _, err := c.take(2 + 2 + 4 + 32); err != nil {
			return out, err
		}
		flags, err := c.u8()
		if err != nil {
			return out, err
		}
		if flags&(1<<2) != 0 {
			if flags&(1<<3) == 0 {
				out.ConstructorBeforeSuper = true
			} else {
				out.ConstructorAfterSuper = true
			}
		}
		if _, err := c.take(4); err != nil {
			return out, err
		}
		sp, err := c.u16()
		if err != nil {
			return out, err
		}
		if _, err := c.take(int(sp) * 32); err != nil {
			return out, err
		}
		locals, err := c.u16()
		if err != nil {
			return out, err
		}
		if _, err := c.take((int(locals)+7)/8 + int(locals)*32); err != nil {
			return out, err
		}
	}
	nextHandle, err := c.u32()
	if err != nil {
		return out, err
	}
	out.NextHandle = nextHandle
	if _, err := c.take(2 + 2 + 4 + 4 + 4 + 2 + 4); err != nil {
		return out, err
	}
	for i := uint32(0); i < nextHandle; i++ {
		if _, err := c.take(4 + 32 + 2); err != nil {
			return out, err
		}
		rank, err := c.u8()
		if err != nil {
			return out, err
		}
		count, err := c.u32()
		if err != nil {
			return out, err
		}
		if rank != 0 {
			cells, err := c.take(int(count) * 8)
			if err != nil {
				return out, err
			}
			var nonzero uint32
			for j := uint32(0); j < count; j++ {
				if !bytes.Equal(cells[int(j)*8:int(j+1)*8], make([]byte, 8)) {
					nonzero++
				}
			}
			out.ArrayNonzero = append(out.ArrayNonzero, nonzero)
			continue
		}
		for j := uint32(0); j < count; j++ {
			cell, err := c.take(32)
			if err != nil {
				return out, err
			}
			value := new(big.Int).SetBytes(cell)
			if new(big.Int).Rsh(new(big.Int).Set(value), 64).Uint64() == 1 {
				out.ObjectInts = append(out.ObjectInts, int32(uint32(value.Uint64())))
			}
		}
	}
	active, err := c.u8()
	if err != nil {
		return out, err
	}
	out.Pending = active != 0
	out.PendingKind, err = c.u8()
	if err != nil {
		return out, err
	}
	out.PendingRef, err = c.u32()
	if err != nil {
		return out, err
	}
	pc, err := c.take(32)
	if err != nil {
		return out, err
	}
	for _, b := range pc[:24] {
		if b != 0 {
			out.PendingPCOverflow = true
			break
		}
	}
	out.PendingPC = binary.BigEndian.Uint64(pc[24:])
	causeCount, err := c.u16()
	if err != nil {
		return out, err
	}
	for i := uint16(0); i < causeCount; i++ {
		wrapper, err := c.u32()
		if err != nil {
			return out, err
		}
		cause, err := c.u32()
		if err != nil {
			return out, err
		}
		out.WrapperCauses = append(out.WrapperCauses, sc0HarnessCause{Wrapper: wrapper, Cause: cause})
	}
	return out, nil
}
