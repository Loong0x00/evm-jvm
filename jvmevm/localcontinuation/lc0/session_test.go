package lc0

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"testing"
	"time"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
	jvmevmmonolith "github.com/ethereum/go-ethereum/jvmevm"
)

const (
	lc0HarnessOrdinaryGas = uint64(100_000_000)
	lc0HarnessBoundaryGas = uint64(1_000_000_000)
)

type lc0HarnessFixture struct {
	ID         string   `json:"id"`
	EntryClass string   `json:"entryClass"`
	Entry      string   `json:"entry"`
	Args       []int32  `json:"args"`
	Want       int32    `json:"result"`
	Classes    []string `json:"classes"`
	SHA256     []string `json:"sha256"`
	Raw        [][]byte `json:"-"`
}

type lc0HarnessFixtureManifest struct {
	Schema   uint32              `json:"schema"`
	Compiler string              `json:"compiler"`
	Fixtures []lc0HarnessFixture `json:"fixtures"`
}

func lc0HarnessFixtureRoot(t *testing.T) string {
	t.Helper()
	_, source, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("cannot locate LC0 test source")
	}
	return filepath.Clean(filepath.Join(filepath.Dir(source), "../../testdata/local/lc0"))
}

func lc0HarnessFixtures(t *testing.T) []lc0HarnessFixture {
	t.Helper()
	root := lc0HarnessFixtureRoot(t)
	rawManifest, err := os.ReadFile(filepath.Join(root, "manifest.json"))
	if err != nil {
		t.Fatal(err)
	}
	var manifest lc0HarnessFixtureManifest
	if err := json.Unmarshal(rawManifest, &manifest); err != nil {
		t.Fatal(err)
	}
	if manifest.Schema != 1 || manifest.Compiler != "javac --release 8 -g:none" || len(manifest.Fixtures) != 3 {
		t.Fatalf("unexpected fixture manifest header: %+v", manifest)
	}
	seen := make(map[string]bool)
	for i := range manifest.Fixtures {
		fixture := &manifest.Fixtures[i]
		if len(fixture.Classes) != len(fixture.SHA256) {
			t.Fatalf("fixture %s hash count mismatch", fixture.ID)
		}
		for j, name := range fixture.Classes {
			classfile, err := os.ReadFile(filepath.Join(root, "classes", name))
			if err != nil {
				t.Fatal(err)
			}
			hash := sha256.Sum256(classfile)
			if hex.EncodeToString(hash[:]) != fixture.SHA256[j] {
				t.Fatalf("fixture %s class %s sha256=%x want=%s", fixture.ID, name, hash, fixture.SHA256[j])
			}
			fixture.Raw = append(fixture.Raw, classfile)
			seen[name] = true
		}
	}
	if len(seen) != 5 {
		t.Fatalf("fixture catalogue names %d classes, want exact five", len(seen))
	}
	return manifest.Fixtures
}

func lc0HarnessRequireRuntime(t *testing.T) {
	t.Helper()
	code, err := Runtime()
	if err != nil {
		t.Fatalf("required pinned LC0 runtime dependency unavailable: %v", err)
	}
	if len(code) == 0 || len(code) > 256*1024 {
		t.Fatalf("runtime length %d outside frozen LOCAL bound", len(code))
	}
	if _, err := ABI(); err != nil {
		t.Fatal(err)
	}
}

func TestLC0HarnessFixturePins(t *testing.T) {
	fixtures := lc0HarnessFixtures(t)
	want := map[string]int32{"call-loop": 15, "alias-string": 36, "init-exception": 10}
	for _, fixture := range fixtures {
		if fixture.Want != want[fixture.ID] {
			t.Fatalf("fixture %s result=%d want=%d", fixture.ID, fixture.Want, want[fixture.ID])
		}
	}
}

func TestLC0HarnessJavaOracles(t *testing.T) {
	fixtures := lc0HarnessFixtures(t)
	root := lc0HarnessFixtureRoot(t)
	compiled := t.TempDir()
	sources := make([]string, 0, 5)
	for _, name := range []string{"LC0CallLoop", "LC0AliasBox", "LC0AliasString", "LC0InitDep", "LC0InitException"} {
		sources = append(sources, filepath.Join(root, "src", name+".java"))
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	output, err := exec.CommandContext(ctx, "javac", append([]string{"--release", "8", "-g:none", "-d", compiled}, sources...)...).CombinedOutput()
	cancel()
	if err != nil {
		t.Fatalf("trusted javac --release 8: %v\n%s", err, output)
	}
	for _, fixture := range fixtures {
		for i, name := range fixture.Classes {
			got, err := os.ReadFile(filepath.Join(compiled, name))
			if err != nil {
				t.Fatal(err)
			}
			if !bytes.Equal(got, fixture.Raw[i]) {
				t.Fatalf("rebuilt %s differs from pinned raw bytes", name)
			}
		}
	}
	oracleDir := t.TempDir()
	for _, fixture := range fixtures {
		for i, name := range fixture.Classes {
			if err := os.WriteFile(filepath.Join(oracleDir, name), fixture.Raw[i], 0o600); err != nil {
				t.Fatal(err)
			}
		}
	}
	oracleSource := `public final class LC0HarnessOracle {
  public static void main(String[] a) {
    if (a[0].equals("call-loop")) System.out.print(LC0CallLoop.run(Integer.parseInt(a[1])));
    else if (a[0].equals("alias-string")) System.out.print(LC0AliasString.run());
    else if (a[0].equals("init-exception")) System.out.print(LC0InitException.run());
    else throw new AssertionError(a[0]);
  }
}`
	oraclePath := filepath.Join(oracleDir, "LC0HarnessOracle.java")
	if err := os.WriteFile(oraclePath, []byte(oracleSource), 0o600); err != nil {
		t.Fatal(err)
	}
	ctx, cancel = context.WithTimeout(context.Background(), 30*time.Second)
	output, err = exec.CommandContext(ctx, "javac", "--release", "8", "-g:none", "-cp", oracleDir, "-d", oracleDir, oraclePath).CombinedOutput()
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
			args := []string{"-Xmx64m", "-cp", oracleDir, "LC0HarnessOracle", fixture.ID}
			for _, value := range fixture.Args {
				args = append(args, strconv.FormatInt(int64(value), 10))
			}
			ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			output, err := exec.CommandContext(ctx, oracle.path, args...).CombinedOutput()
			cancel()
			if err != nil || strings.TrimSpace(string(output)) != strconv.FormatInt(int64(fixture.Want), 10) {
				t.Fatalf("%s %s output=%q error=%v", oracle.name, fixture.ID, output, err)
			}
		}
	}
	for _, fixture := range fixtures {
		result, err := jvmevmmonolith.RunClasses(fixture.Raw, fixture.EntryClass, fixture.Entry, fixture.Args, lc0HarnessOrdinaryGas)
		if err != nil || result.ExceptionClass != "" || result.Value != fixture.Want {
			t.Fatalf("accepted monolith %s value=%d exception=%q error=%v", fixture.ID, result.Value, result.ExceptionClass, err)
		}
		t.Logf("accepted monolith fixture=%s runtimeSHA256=%s gas=%d result=%d", fixture.ID, result.RuntimeSHA256, result.GasUsed, result.Value)
	}
}

func TestLC0HarnessContinuationCorpus(t *testing.T) {
	lc0HarnessRequireRuntime(t)
	runtimeSHA, err := RuntimeHash()
	if err != nil {
		t.Fatal(err)
	}
	code, err := Runtime()
	if err != nil {
		t.Fatal(err)
	}
	t.Logf("LC0 runtime bytes=%d sha256=%s codeHash=%s", len(code), runtimeSHA, crypto.Keccak256Hash(code))
	owner := common.HexToAddress("0x10000000000000000000000000000000000000c0")
	session, err := NewMemory(owner)
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	if session.testCodeInstalls != 1 {
		t.Fatalf("code installations=%d want=1", session.testCodeInstalls)
	}
	unknown, err := session.Head(crypto.Keccak256Hash([]byte("unknown")))
	if err != nil {
		t.Fatal(err)
	}
	if unknown != (Head{}) {
		t.Fatalf("unknown head is nonzero: %+v", unknown)
	}
	for _, fixture := range lc0HarnessFixtures(t) {
		fixture := fixture
		t.Run(fixture.ID, func(t *testing.T) {
			control := lc0HarnessRunChain(t, session, fixture, "one-call", 4096, 4096)
			if control.Slice.Epoch != 1 {
				t.Fatalf("one-call epoch=%d want=1", control.Slice.Epoch)
			}
			for _, profile := range []struct {
				name     string
				jvm      uint64
				internal uint32
			}{{"q1", 1, 4096}, {"q7", 7, 4096}, {"internal-q1", 4096, 1}} {
				got := lc0HarnessRunChain(t, session, fixture, profile.name, profile.jvm, profile.internal)
				if got.Slice.MachineStateRoot != control.Slice.MachineStateRoot || got.Slice.TotalJvmSteps != control.Slice.TotalJvmSteps || got.Slice.TotalInternalSteps != control.Slice.TotalInternalSteps || got.Slice.Result != fixture.Want {
					t.Fatalf("%s final mismatch: slice=%+v control=%+v", profile.name, got.Slice, control.Slice)
				}
				if got.Slice.CheckpointRoot == control.Slice.CheckpointRoot {
					t.Fatalf("%s history root unexpectedly equals one-call root", profile.name)
				}
			}
		})
	}
	negative := lc0HarnessFixtures(t)[0]
	negative.Args = []int32{-3}
	negative.Want = 0
	lc0HarnessRunChain(t, session, negative, "negative-int", 4096, 4096)

	faultRaw := lc0HarnessCompileTrustedSource(t, "LC0HarnessUncaught", `public final class LC0HarnessUncaught {
  public static int run(int divisor) { return 10 / divisor; }
}`)
	monolithFault, err := jvmevmmonolith.RunClasses([][]byte{faultRaw}, "LC0HarnessUncaught", "run", []int32{0}, lc0HarnessOrdinaryGas)
	if err != nil || monolithFault.ExceptionClass != "java.lang.ArithmeticException" {
		t.Fatalf("accepted monolith uncaught outcome=%+v error=%v", monolithFault, err)
	}
	faultInstance := crypto.Keccak256Hash([]byte(t.Name() + ":known-uncaught"))
	fault, err := session.Start(faultInstance, [][]byte{faultRaw}, "LC0HarnessUncaught", "run", []int32{0}, 4096, 4096, lc0HarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	if fault.Slice.Lifecycle != 3 || fault.Slice.Result != 0 || fault.Slice.JavaKind != 1 || fault.Slice.JavaRef == 0 {
		t.Fatalf("known uncaught ArithmeticException is not canonical: %+v", fault.Slice)
	}
	inspection, err := lc0HarnessInspectMachine(fault.Checkpoint)
	if err != nil || inspection.Depth != 0 || !inspection.Pending || inspection.PendingKind != 1 || inspection.PendingRef != fault.Slice.JavaRef {
		t.Fatalf("known uncaught checkpoint=%+v error=%v", inspection, err)
	}
	t.Logf("known uncaught classSHA256=%x javaKind=%d javaRef=%d machine=%s gas=%d", sha256.Sum256(faultRaw), fault.Slice.JavaKind, fault.Slice.JavaRef, fault.Slice.MachineStateRoot, fault.GasUsed)
}

func lc0HarnessCompileTrustedSource(t *testing.T, className, source string) []byte {
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

func lc0HarnessRunChain(t *testing.T, session *Session, fixture lc0HarnessFixture, profile string, jvm uint64, internal uint32) Result {
	t.Helper()
	instance := crypto.Keccak256Hash([]byte(t.Name() + ":" + fixture.ID + ":" + profile))
	result, err := session.Start(instance, fixture.Raw, fixture.EntryClass, fixture.Entry, fixture.Args, jvm, internal, lc0HarnessOrdinaryGas)
	if err != nil {
		t.Fatalf("%s start: %v", profile, err)
	}
	for slices := 1; ; slices++ {
		lc0HarnessCheckSlice(t, session, instance, result, jvm, internal, slices)
		if result.Slice.Lifecycle != 1 {
			if result.Slice.Lifecycle != 2 || result.Slice.Result != fixture.Want || result.Slice.JavaKind != 0 || result.Slice.JavaRef != 0 {
				t.Fatalf("%s terminal slice=%+v want returned %d", profile, result.Slice, fixture.Want)
			}
			return result
		}
		if slices >= 256 {
			t.Fatalf("%s exceeded 256 slices", profile)
		}
		result, err = session.Resume(instance, result.Slice.Epoch, result.Slice.CheckpointRoot, fixture.Raw, result.Checkpoint, jvm, internal, lc0HarnessOrdinaryGas)
		if err != nil {
			t.Fatalf("%s resume epoch %d: %v", profile, result.Slice.Epoch, err)
		}
	}
}

func lc0HarnessCheckSlice(t *testing.T, session *Session, instance common.Hash, result Result, jvm uint64, internal uint32, number int) {
	t.Helper()
	if result.Slice.Schema != 1 || result.Slice.Epoch != uint64(number) || result.Slice.ExecutedJvmSteps > jvm || result.Slice.ExecutedInternalSteps > internal {
		t.Fatalf("invalid slice %d: %+v budgets=%d/%d", number, result.Slice, jvm, internal)
	}
	if len(result.Logs) != 1 || result.Logs[0].Address != lc0HarnessContractAddress {
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

func TestLC0HarnessEVMFailuresPreserveHead(t *testing.T) {
	lc0HarnessRequireRuntime(t)
	owner := common.HexToAddress("0x18000000000000000000000000000000000000c0")
	session, err := NewMemory(owner)
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	fixture := lc0HarnessFixtures(t)[0]
	instance := crypto.Keccak256Hash([]byte(t.Name()))
	parent, err := session.Start(instance, fixture.Raw, fixture.EntryClass, fixture.Entry, fixture.Args, 1, 4096, lc0HarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	lc0HarnessExpectFailurePreservesHead(t, session, instance, func() (Result, error) {
		return session.Start(instance, fixture.Raw, fixture.EntryClass, fixture.Entry, fixture.Args, 1, 4096, lc0HarnessOrdinaryGas)
	})
	lc0HarnessExpectFailurePreservesHead(t, session, instance, func() (Result, error) {
		return session.Resume(instance, parent.Slice.Epoch+1, parent.Slice.CheckpointRoot, fixture.Raw, parent.Checkpoint, 1, 4096, lc0HarnessOrdinaryGas)
	})
	lc0HarnessExpectFailurePreservesHead(t, session, instance, func() (Result, error) {
		return session.Resume(instance, parent.Slice.Epoch, crypto.Keccak256Hash([]byte("wrong-root")), fixture.Raw, parent.Checkpoint, 1, 4096, lc0HarnessOrdinaryGas)
	})
	wrongRaw := make([][]byte, len(fixture.Raw))
	for i := range fixture.Raw {
		wrongRaw[i] = append([]byte(nil), fixture.Raw[i]...)
	}
	wrongRaw[0][len(wrongRaw[0])-1] ^= 1
	lc0HarnessExpectFailurePreservesHead(t, session, instance, func() (Result, error) {
		return session.Resume(instance, parent.Slice.Epoch, parent.Slice.CheckpointRoot, wrongRaw, parent.Checkpoint, 1, 4096, lc0HarnessOrdinaryGas)
	})
	lc0HarnessExpectFailurePreservesHead(t, session, instance, func() (Result, error) {
		return session.Resume(instance, parent.Slice.Epoch, parent.Slice.CheckpointRoot, fixture.Raw, parent.Checkpoint, 1, 4096, 50_000)
	})
	other := crypto.Keccak256Hash([]byte("wrong-instance"))
	lc0HarnessExpectFailurePreservesHead(t, session, instance, func() (Result, error) {
		return session.Resume(other, parent.Slice.Epoch, parent.Slice.CheckpointRoot, fixture.Raw, parent.Checkpoint, 1, 4096, lc0HarnessOrdinaryGas)
	})
	terminalInstance := crypto.Keccak256Hash([]byte("terminal" + t.Name()))
	terminal, err := session.Start(terminalInstance, fixture.Raw, fixture.EntryClass, fixture.Entry, fixture.Args, 4096, 4096, lc0HarnessOrdinaryGas)
	if err != nil || terminal.Slice.Lifecycle != 2 {
		t.Fatalf("terminal setup lifecycle=%d error=%v", terminal.Slice.Lifecycle, err)
	}
	lc0HarnessExpectFailurePreservesHead(t, session, terminalInstance, func() (Result, error) {
		return session.Resume(terminalInstance, terminal.Slice.Epoch, terminal.Slice.CheckpointRoot, fixture.Raw, terminal.Checkpoint, 1, 4096, lc0HarnessOrdinaryGas)
	})
}

func lc0HarnessExpectFailurePreservesHead(t *testing.T, session *Session, instance common.Hash, call func() (Result, error)) {
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
func lc0HarnessControlChild(t *testing.T, owner common.Address, instance common.Hash, fixture lc0HarnessFixture, parent Result) Result {
	t.Helper()
	control, err := NewMemory(owner)
	if err != nil {
		t.Fatal(err)
	}
	defer control.Close()
	cp, err := control.Start(instance, fixture.Raw, fixture.EntryClass, fixture.Entry, fixture.Args, 1, 4096, lc0HarnessOrdinaryGas)
	if err != nil || cp.Slice.CheckpointRoot != parent.Slice.CheckpointRoot {
		t.Fatalf("control parent mismatch: %v", err)
	}
	child, err := control.Resume(instance, cp.Slice.Epoch, cp.Slice.CheckpointRoot, fixture.Raw, cp.Checkpoint, 1, 4096, lc0HarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	return child
}

func TestLC0HarnessDiskFailuresAndReopen(t *testing.T) {
	lc0HarnessRequireRuntime(t)
	owner := common.HexToAddress("0x20000000000000000000000000000000000000c0")
	fixture := lc0HarnessFixtures(t)[0]
	for _, point := range []lc0HarnessFaultPoint{lc0HarnessFaultAfterBlob, lc0HarnessFaultAfterTrie, lc0HarnessFaultBeforeManifest} {
		t.Run(fmt.Sprint(point), func(t *testing.T) {
			dir := t.TempDir()
			session, err := Open(dir, owner)
			if err != nil {
				t.Fatal(err)
			}
			instance := crypto.Keccak256Hash([]byte(t.Name()))
			parent, err := session.Start(instance, fixture.Raw, fixture.EntryClass, fixture.Entry, fixture.Args, 1, 4096, lc0HarnessOrdinaryGas)
			if err != nil {
				t.Fatal(err)
			}
			controlChild := lc0HarnessControlChild(t, owner, instance, fixture, parent)
			fired := false
			session.testFault = func(got lc0HarnessFaultPoint) error {
				if got == point && !fired {
					fired = true
					return errors.New("test durable failure")
				}
				return nil
			}
			failedChild, err := session.Resume(instance, parent.Slice.Epoch, parent.Slice.CheckpointRoot, fixture.Raw, parent.Checkpoint, 1, 4096, lc0HarnessOrdinaryGas)
			if err == nil || !fired {
				t.Fatalf("fault point %d did not fail", point)
			}
			if len(failedChild.Logs) != 0 || len(failedChild.Checkpoint) != 0 || failedChild.Slice != (SliceResult{}) || failedChild.GasUsed == 0 {
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
			retry, err := session.Resume(instance, parent.Slice.Epoch, parent.Slice.CheckpointRoot, fixture.Raw, parent.Checkpoint, 1, 4096, lc0HarnessOrdinaryGas)
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
		parent, err := session.Start(instance, fixture.Raw, fixture.EntryClass, fixture.Entry, fixture.Args, 1, 4096, lc0HarnessOrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
		controlChild := lc0HarnessControlChild(t, owner, instance, fixture, parent)
		session.testFault = func(point lc0HarnessFaultPoint) error {
			if point == lc0HarnessFaultAfterManifestRename {
				return errors.New("ambiguous directory fsync")
			}
			return nil
		}
		child, err := session.Resume(instance, parent.Slice.Epoch, parent.Slice.CheckpointRoot, fixture.Raw, parent.Checkpoint, 1, 4096, lc0HarnessOrdinaryGas)
		if err == nil {
			t.Fatal("after-publication failure was hidden")
		}
		if len(child.Logs) != 0 || len(child.Checkpoint) != 0 || child.Slice != (SliceResult{}) {
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

func TestLC0HarnessDiskOwnerBinding(t *testing.T) {
	lc0HarnessRequireRuntime(t)
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

func TestLC0HarnessRefusesUnrelatedDirectory(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "user-file")
	if err := os.WriteFile(path, []byte("preserve me"), 0o600); err != nil {
		t.Fatal(err)
	}
	fresh, err := lc0HarnessPrepareDirectory(dir)
	if err == nil || fresh {
		t.Fatal("unrelated nonempty directory accepted")
	}
	got, readErr := os.ReadFile(path)
	if readErr != nil || string(got) != "preserve me" {
		t.Fatalf("user file changed: %q %v", got, readErr)
	}
}

func TestLC0HarnessProcessReopen(t *testing.T) {
	if os.Getenv("JVMEVM_LC0_CHILD") != "" {
		lc0HarnessProcessChild(t)
		return
	}
	lc0HarnessRequireRuntime(t)
	fixtures := lc0HarnessFixtures(t)
	owner := common.HexToAddress("0x30000000000000000000000000000000000000c0")
	for _, fixtureIndex := range []int{1, 2} {
		fixture := fixtures[fixtureIndex]
		t.Run(fixture.ID, func(t *testing.T) {
			controlSession, err := NewMemory(owner)
			if err != nil {
				t.Fatal(err)
			}
			control := lc0HarnessRunChain(t, controlSession, fixture, "process-control", 4096, 4096)
			controlSession.Close()

			dir := t.TempDir()
			session, err := Open(dir, owner)
			if err != nil {
				t.Fatal(err)
			}
			budget := uint64(7)
			if fixture.ID == "init-exception" {
				budget = 10
			}
			instance := crypto.Keccak256Hash([]byte(t.Name()))
			checkpoint, err := session.Start(instance, fixture.Raw, fixture.EntryClass, fixture.Entry, fixture.Args, budget, 4096, lc0HarnessOrdinaryGas)
			if err != nil {
				t.Fatal(err)
			}
			inspection, err := lc0HarnessInspectMachine(checkpoint.Checkpoint)
			if err != nil {
				t.Fatal(err)
			}
			if fixture.ID == "alias-string" && inspection.Depth < 2 {
				t.Fatalf("alias checkpoint depth=%d, want live nested frames", inspection.Depth)
			}
			if fixture.ID == "init-exception" && (!inspection.Pending || inspection.PendingKind != 1 || inspection.PendingRef == 0 || inspection.PendingPCOverflow || inspection.PendingPC != 15) {
				t.Fatalf("q10 did not capture real pending ArithmeticException: %+v", inspection)
			}
			if err := session.Close(); err != nil {
				t.Fatal(err)
			}
			alias := filepath.Join(filepath.Dir(dir), filepath.Base(dir)+"-alias")
			if err := os.Symlink(dir, alias); err != nil {
				t.Fatal(err)
			}
			command := exec.Command(os.Args[0], "-test.run=^TestLC0HarnessProcessReopen$")
			command.Env = append(os.Environ(),
				"JVMEVM_LC0_CHILD=1", "JVMEVM_LC0_DIR="+alias, "JVMEVM_LC0_OWNER="+owner.Hex(),
				"JVMEVM_LC0_FIXTURE="+strconv.Itoa(fixtureIndex), "JVMEVM_LC0_INSTANCE="+instance.Hex(),
				"JVMEVM_LC0_EPOCH="+strconv.FormatUint(checkpoint.Slice.Epoch, 10), "JVMEVM_LC0_ROOT="+checkpoint.Slice.CheckpointRoot.Hex())
			output, err := command.Output()
			if err != nil {
				t.Fatalf("child process: %v stdout=%s stderr=%s", err, output, lc0HarnessExitStderr(err))
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
			if child.Machine != control.Slice.MachineStateRoot || child.Result != fixture.Want || child.Jvm != control.Slice.TotalJvmSteps || child.Internal != control.Slice.TotalInternalSteps {
				t.Fatalf("restarted result=%+v control=%+v", child, control.Slice)
			}
		})
	}
}

func lc0HarnessProcessChild(t *testing.T) {
	fixtures := lc0HarnessFixtures(t)
	index, err := strconv.Atoi(os.Getenv("JVMEVM_LC0_FIXTURE"))
	if err != nil || index < 0 || index >= len(fixtures) {
		t.Fatal("bad child fixture")
	}
	owner := common.HexToAddress(os.Getenv("JVMEVM_LC0_OWNER"))
	instance := common.HexToHash(os.Getenv("JVMEVM_LC0_INSTANCE"))
	epoch, err := strconv.ParseUint(os.Getenv("JVMEVM_LC0_EPOCH"), 10, 64)
	if err != nil {
		t.Fatal(err)
	}
	root := common.HexToHash(os.Getenv("JVMEVM_LC0_ROOT"))
	session, err := Open(os.Getenv("JVMEVM_LC0_DIR"), owner)
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
		result, err = session.Resume(instance, epoch, root, fixture.Raw, checkpoint, 7, 1, lc0HarnessOrdinaryGas)
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

func lc0HarnessExitStderr(err error) string {
	var exit *exec.ExitError
	if errors.As(err, &exit) {
		return string(exit.Stderr)
	}
	return ""
}

type lc0HarnessMachineInspection struct {
	Lifecycle         uint8
	Depth             uint16
	Pending           bool
	PendingKind       uint8
	PendingRef        uint32
	PendingPC         uint64
	PendingPCOverflow bool
}

type lc0HarnessCursor struct {
	blob []byte
	off  int
}

func (c *lc0HarnessCursor) take(size int) ([]byte, error) {
	if size < 0 || c.off > len(c.blob)-size {
		return nil, fmt.Errorf("truncated at %d taking %d", c.off, size)
	}
	out := c.blob[c.off : c.off+size]
	c.off += size
	return out, nil
}
func (c *lc0HarnessCursor) u8() (uint8, error) {
	b, e := c.take(1)
	if e != nil {
		return 0, e
	}
	return b[0], nil
}
func (c *lc0HarnessCursor) u16() (uint16, error) {
	b, e := c.take(2)
	if e != nil {
		return 0, e
	}
	return binary.BigEndian.Uint16(b), nil
}
func (c *lc0HarnessCursor) u32() (uint32, error) {
	b, e := c.take(4)
	if e != nil {
		return 0, e
	}
	return binary.BigEndian.Uint32(b), nil
}

// Test-only inspection records counters/IDs for assertions. Its output is never
// supplied to Start or Resume and production Go has no machine parser.
func lc0HarnessInspectMachine(checkpoint []byte) (lc0HarnessMachineInspection, error) {
	var out lc0HarnessMachineInspection
	if len(checkpoint) < 216 || string(checkpoint[:8]) != "JVMELC01" {
		return out, errors.New("bad checkpoint envelope")
	}
	length := binary.BigEndian.Uint32(checkpoint[212:216])
	if int(length) != len(checkpoint)-216 {
		return out, errors.New("machine length mismatch")
	}
	c := &lc0HarnessCursor{blob: checkpoint[216:]}
	magic, _ := c.take(4)
	if string(magic) != "LCS1" {
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
		if _, err := c.take(int(statics) * 34); err != nil {
			return out, err
		}
	}
	out.Depth, err = c.u16()
	if err != nil {
		return out, err
	}
	for i := 0; i < int(out.Depth); i++ {
		if _, err := c.take(2 + 2 + 4 + 32 + 1 + 4); err != nil {
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
		cell := 32
		if rank != 0 {
			cell = 8
		}
		if _, err := c.take(int(count) * cell); err != nil {
			return out, err
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
	return out, nil
}
