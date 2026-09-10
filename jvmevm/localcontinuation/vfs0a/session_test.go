package vfs0a

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
	vfs0aHarnessOrdinaryGas = uint64(100_000_000)
	vfs0aHarnessBoundaryGas = uint64(1_000_000_000)
)

type vfs0aHarnessClass struct {
	Name   string `json:"name"`
	SHA256 string `json:"sha256"`
}

type vfs0aHarnessSeed struct {
	PathHex  string `json:"pathHex"`
	DataHex  string `json:"dataHex"`
	ReadOnly bool   `json:"readOnly"`
}

type vfs0aHarnessOutcome struct {
	Lifecycle    string `json:"lifecycle"`
	Result       int32  `json:"result"`
	JavaKind     uint8  `json:"javaKind"`
	JavaClassHex string `json:"javaClassHex"`
}

type vfs0aHarnessFixture struct {
	ID           string              `json:"id"`
	Group        string              `json:"group"`
	Source       string              `json:"source"`
	SourceSHA256 string              `json:"sourceSHA256"`
	EntryClass   string              `json:"entryClass"`
	Entry        string              `json:"entry"`
	Args         []int32             `json:"args"`
	SeedRecords  []vfs0aHarnessSeed  `json:"seeds"`
	Outcome      vfs0aHarnessOutcome `json:"outcome"`
	Classes      []vfs0aHarnessClass `json:"classes"`
	Raw          [][]byte            `json:"-"`
	Seeds        []SeedFile          `json:"-"`
	JavaClass    []byte              `json:"-"`
}

type vfs0aHarnessFixtureManifest struct {
	Schema   uint32                `json:"schema"`
	Compiler string                `json:"compiler"`
	Fixtures []vfs0aHarnessFixture `json:"fixtures"`
}

func vfs0aHarnessFixtureRoot(t *testing.T) string {
	t.Helper()
	_, source, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("cannot locate VFS0a test source")
	}
	return filepath.Clean(filepath.Join(filepath.Dir(source), "../../testdata/local/vfs0a"))
}

func vfs0aHarnessFixtures(t *testing.T) []vfs0aHarnessFixture {
	t.Helper()
	root := vfs0aHarnessFixtureRoot(t)
	rawManifest, err := os.ReadFile(filepath.Join(root, "manifest.json"))
	if err != nil {
		t.Fatal(err)
	}
	var manifest vfs0aHarnessFixtureManifest
	if err := json.Unmarshal(rawManifest, &manifest); err != nil {
		t.Fatal(err)
	}
	if manifest.Schema != 1 || manifest.Compiler != "javac --release 8 -g:none" || len(manifest.Fixtures) != 24 {
		t.Fatalf("unexpected fixture manifest header: schema=%d compiler=%q fixtures=%d", manifest.Schema, manifest.Compiler, len(manifest.Fixtures))
	}
	groups, ids := make(map[string]int), make(map[string]bool)
	for i := range manifest.Fixtures {
		fixture := &manifest.Fixtures[i]
		if fixture.ID == "" || ids[fixture.ID] || fixture.Entry != fixture.ID {
			t.Fatalf("invalid or duplicate fixture id/entry %q/%q", fixture.ID, fixture.Entry)
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
		if len(fixture.Classes) == 0 || len(fixture.Classes) > 4 || len(fixture.SeedRecords) > 16 {
			t.Fatalf("fixture %s bundle/seeds=%d/%d", fixture.ID, len(fixture.Classes), len(fixture.SeedRecords))
		}
		totalClasses, totalSeeds := 0, 0
		for _, class := range fixture.Classes {
			classfile, err := os.ReadFile(filepath.Join(root, "classes", class.Name))
			if err != nil {
				t.Fatal(err)
			}
			hash := sha256.Sum256(classfile)
			if hex.EncodeToString(hash[:]) != class.SHA256 {
				t.Fatalf("fixture %s class %s hash mismatch", fixture.ID, class.Name)
			}
			fixture.Raw = append(fixture.Raw, classfile)
			totalClasses += len(classfile)
		}
		for _, seed := range fixture.SeedRecords {
			path, err := hex.DecodeString(seed.PathHex)
			if err != nil {
				t.Fatalf("fixture %s seed path: %v", fixture.ID, err)
			}
			data, err := hex.DecodeString(seed.DataHex)
			if err != nil {
				t.Fatalf("fixture %s seed data: %v", fixture.ID, err)
			}
			fixture.Seeds = append(fixture.Seeds, SeedFile{Path: path, Data: data, ReadOnly: seed.ReadOnly})
			totalSeeds += len(path) + len(data)
		}
		if totalClasses > 64*1024 || totalSeeds > 65536 {
			t.Fatalf("fixture %s exceeds raw class/seed byte bounds", fixture.ID)
		}
		fixture.JavaClass, err = hex.DecodeString(fixture.Outcome.JavaClassHex)
		if err != nil {
			t.Fatal(err)
		}
	}
	if !reflect.DeepEqual(groups, map[string]int{"Paths": 8, "Streams": 8, "Errors": 8}) {
		t.Fatalf("fixture groups=%v", groups)
	}
	return manifest.Fixtures
}

func vfs0aHarnessRequireRuntime(t *testing.T) {
	t.Helper()
	code, err := Runtime()
	if err != nil {
		t.Fatalf("required pinned VFS0a runtime dependency unavailable: %v", err)
	}
	if len(code) == 0 || len(code) > 320*1024 {
		t.Fatalf("runtime length %d outside frozen LOCAL bound", len(code))
	}
	if _, err := ABI(); err != nil {
		t.Fatal(err)
	}
}

func TestVFS0aHarnessFixturePins(t *testing.T) {
	fixtures := vfs0aHarnessFixtures(t)
	want := []string{
		"existsMissing", "seedFile", "seedDirectory", "mkdirOnce", "mkdirsNested", "readonlyMkdir", "lexicalAlias", "comparablePaths",
		"readSingleEOF", "readBulkSlice", "createRoundtrip", "truncate", "append", "twoWriterGap", "staleReadCursor", "closeTwice",
		"nullFileArg", "missingInputMessage", "missingOutputParentMessage", "directoryOpenMessage", "readOnlyOutputMessage", "nullArrayBeforeClosed", "boundsBeforeClosed", "zeroLengthClosed",
	}
	for i, fixture := range fixtures {
		if fixture.ID != want[i] || fixture.Outcome.Lifecycle != "RETURNED" || fixture.Outcome.Result != 1 || fixture.Outcome.JavaKind != 0 || len(fixture.JavaClass) != 0 {
			t.Fatalf("fixture %d differs from frozen root/outcome: %+v", i, fixture)
		}
	}
}

func TestVFS0aHarnessJava8And21Oracles(t *testing.T) {
	fixtures := vfs0aHarnessFixtures(t)
	root, compiled := vfs0aHarnessFixtureRoot(t), t.TempDir()
	sources := []string{filepath.Join(root, "src", "VFS0aPaths.java"), filepath.Join(root, "src", "VFS0aStreams.java"), filepath.Join(root, "src", "VFS0aErrors.java")}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	output, err := exec.CommandContext(ctx, "javac", append([]string{"--release", "8", "-g:none", "-d", compiled}, sources...)...).CombinedOutput()
	cancel()
	if err != nil {
		t.Fatalf("trusted fixture rebuild: %v\n%s", err, output)
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
				t.Fatalf("rebuilt %s differs", class.Name)
			}
			checked[class.Name] = true
		}
	}
	oracle := `import java.lang.reflect.*; public final class VFS0aHarnessOracle { public static void main(String[] a) throws Exception { try { System.out.print("R:" + ((Integer)Class.forName(a[0]).getDeclaredMethod(a[1]).invoke(null)).intValue()); } catch (InvocationTargetException e) { System.out.print("U:" + e.getCause().getClass().getName().replace('.', '/')); } } }`
	oraclePath := filepath.Join(compiled, "VFS0aHarnessOracle.java")
	if err := os.WriteFile(oraclePath, []byte(oracle), 0o600); err != nil {
		t.Fatal(err)
	}
	ctx, cancel = context.WithTimeout(context.Background(), 30*time.Second)
	output, err = exec.CommandContext(ctx, "javac", "--release", "8", "-g:none", "-cp", compiled, "-d", compiled, oraclePath).CombinedOutput()
	cancel()
	if err != nil {
		t.Fatalf("oracle compile: %v\n%s", err, output)
	}
	java8, java21 := "/usr/lib/jvm/java-8-openjdk/bin/java", "/usr/lib/jvm/jdk-21.0.9/bin/java"
	if home := os.Getenv("JAVA8_HOME"); home != "" {
		java8 = filepath.Join(home, "bin", "java")
	}
	if home := os.Getenv("JAVA21_HOME"); home != "" {
		java21 = filepath.Join(home, "bin", "java")
	}
	for _, jdk := range []struct{ name, path string }{{"java8-primary", java8}, {"java21-secondary", java21}} {
		if _, err := os.Stat(jdk.path); err != nil {
			t.Fatalf("required %s unavailable: %v", jdk.name, err)
		}
		for _, fixture := range fixtures {
			work := filepath.Join(t.TempDir(), "owned-work")
			if err := os.Mkdir(work, 0o700); err != nil {
				t.Fatal(err)
			}
			vfs0aHarnessMaterializeOracleSeeds(t, work, fixture.Seeds)
			ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			cmd := exec.CommandContext(ctx, jdk.path, "-Xmx64m", "-cp", compiled, "VFS0aHarnessOracle", fixture.EntryClass, fixture.Entry)
			cmd.Dir = work
			cmd.Env = vfs0aHarnessCLocaleEnv()
			output, err := cmd.CombinedOutput()
			cancel()
			if err != nil || strings.TrimSpace(string(output)) != "R:1" {
				t.Fatalf("%s %s output=%q error=%v", jdk.name, fixture.ID, output, err)
			}
		}
	}
	// The frozen secondary oracle currently has no differing VFS0a root.
}

func vfs0aHarnessCLocaleEnv() []string {
	env := make([]string, 0, len(os.Environ())+2)
	for _, value := range os.Environ() {
		if !strings.HasPrefix(value, "LC_ALL=") && !strings.HasPrefix(value, "LANG=") {
			env = append(env, value)
		}
	}
	return append(env, "LC_ALL=C", "LANG=C")
}

func vfs0aHarnessMaterializeOracleSeeds(t *testing.T, work string, seeds []SeedFile) {
	t.Helper()
	for _, seed := range seeds {
		// Test-only trusted ASCII fixture interpretation; production Start receives
		// the exact opaque bytes and never calls this helper.
		path := filepath.Join(work, filepath.FromSlash(string(seed.Path)))
		if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, seed.Data, 0o600); err != nil {
			t.Fatal(err)
		}
		if seed.ReadOnly {
			if err := os.Chmod(path, 0o400); err != nil {
				t.Fatal(err)
			}
		}
	}
}

func TestVFS0aHarnessContinuationCorpus(t *testing.T) {
	vfs0aHarnessRequireRuntime(t)
	code, _ := Runtime()
	hash, _ := RuntimeHash()
	t.Logf("VFS0a runtime bytes=%d sha256=%s codeHash=%s", len(code), hash, crypto.Keccak256Hash(code))
	session, err := NewMemory(common.HexToAddress("0x10000000000000000000000000000000000000e0"))
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	if session.testCodeInstalls != 1 {
		t.Fatalf("code installs=%d", session.testCodeInstalls)
	}
	chains := map[string]bool{"mkdirsNested": true, "lexicalAlias": true, "readBulkSlice": true, "createRoundtrip": true, "truncate": true, "append": true, "twoWriterGap": true, "staleReadCursor": true, "missingInputMessage": true, "readOnlyOutputMessage": true}
	for _, fixture := range vfs0aHarnessFixtures(t) {
		fixture := fixture
		t.Run(fixture.ID, func(t *testing.T) {
			control := vfs0aHarnessRunChain(t, session, fixture, "one", 4096, 4096)
			if control.Slice.Epoch != 1 {
				t.Fatalf("one-call epoch=%d", control.Slice.Epoch)
			}
			if !chains[fixture.ID] {
				return
			}
			for _, q := range []uint64{1, 7} {
				got := vfs0aHarnessRunChain(t, session, fixture, fmt.Sprintf("q%d", q), q, 4096)
				if got.Slice.MachineStateRoot != control.Slice.MachineStateRoot || got.Slice.VFSStateRoot != control.Slice.VFSStateRoot || got.Slice.TotalJvmSteps != control.Slice.TotalJvmSteps || got.Slice.TotalInternalSteps != control.Slice.TotalInternalSteps || !vfs0aHarnessSameOutcome(got.Slice, control.Slice) {
					t.Fatalf("q%d terminal mismatch: got=%+v control=%+v", q, got.Slice, control.Slice)
				}
			}
		})
	}
}

func vfs0aHarnessRunChain(t *testing.T, session *Session, fixture vfs0aHarnessFixture, profile string, jvm uint64, internal uint32) Result {
	t.Helper()
	instance := crypto.Keccak256Hash([]byte(t.Name() + ":" + fixture.ID + ":" + profile))
	result, err := session.Start(instance, fixture.Raw, fixture.EntryClass, fixture.Entry, fixture.Args, fixture.Seeds, jvm, internal, vfs0aHarnessOrdinaryGas)
	if err != nil {
		t.Fatalf("%s start: %v", profile, err)
	}
	var units uint64
	for slices := 1; ; slices++ {
		vfs0aHarnessCheckSlice(t, session, instance, result, jvm, internal, slices)
		units += result.Slice.ExecutedJvmSteps + uint64(result.Slice.ExecutedInternalSteps)
		if units > 4096 {
			t.Fatalf("%s exceeded ordinary 4096 units", profile)
		}
		if result.Slice.Lifecycle != 1 {
			wantLifecycle := uint8(2)
			if fixture.Outcome.Lifecycle == "UNCAUGHT_JAVA" {
				wantLifecycle = 3
			}
			if result.Slice.Lifecycle != wantLifecycle || result.Slice.Result != fixture.Outcome.Result || result.Slice.JavaKind != fixture.Outcome.JavaKind || !bytes.Equal(result.Slice.JavaClass, fixture.JavaClass) {
				t.Fatalf("%s terminal=%+v want=%+v", profile, result.Slice, fixture.Outcome)
			}
			return result
		}
		if slices >= 4096 {
			t.Fatalf("%s exceeded VFS0a-only 4096-slice allowance", profile)
		}
		result, err = session.Resume(instance, result.Slice.Epoch, result.Slice.CheckpointRoot, fixture.Raw, result.Checkpoint, jvm, internal, vfs0aHarnessOrdinaryGas)
		if err != nil {
			t.Fatalf("%s resume epoch %d: %v", profile, result.Slice.Epoch, err)
		}
	}
}

func vfs0aHarnessCheckSlice(t *testing.T, session *Session, instance common.Hash, result Result, jvm uint64, internal uint32, number int) {
	t.Helper()
	if result.Slice.Schema != 1 || result.Slice.Epoch != uint64(number) || result.Slice.ExecutedJvmSteps > jvm || result.Slice.ExecutedInternalSteps > internal || result.Slice.VFSStateRoot == (common.Hash{}) {
		t.Fatalf("invalid slice %d: %+v", number, result.Slice)
	}
	if len(result.Logs) != 1 || result.Logs[0].Address != vfs0aHarnessContractAddress {
		t.Fatalf("slice %d log mismatch", number)
	}
	stored, err := session.ReadCheckpoint(result.Slice.CheckpointRoot)
	if err != nil || !bytes.Equal(stored, result.Checkpoint) {
		t.Fatalf("stored checkpoint: %v", err)
	}
	if len(result.Checkpoint) < 280 || string(result.Checkpoint[:8]) != "JVMVF0A1" || binary.BigEndian.Uint32(result.Checkpoint[8:12]) != 1 || int(binary.BigEndian.Uint32(result.Checkpoint[276:280])) != len(result.Checkpoint)-280 || common.BytesToHash(result.Checkpoint[180:212]) != result.Slice.MachineStateRoot || common.BytesToHash(result.Checkpoint[244:276]) != result.Slice.VFSStateRoot {
		t.Fatalf("slice %d violates frozen 280-byte envelope", number)
	}
	head, err := session.Head(instance)
	if err != nil || head.Owner != session.owner || head.Epoch != result.Slice.Epoch || head.CheckpointRoot != result.Slice.CheckpointRoot || head.MachineStateRoot != result.Slice.MachineStateRoot || head.VFSStateRoot != result.Slice.VFSStateRoot || head.SeedRoot != common.BytesToHash(result.Checkpoint[212:244]) || head.Lifecycle != result.Slice.Lifecycle || head.RuntimeCodeHash != session.codeHash {
		t.Fatalf("head mismatch: %+v err=%v slice=%+v", head, err, result.Slice)
	}
}

func vfs0aHarnessSameOutcome(a, b SliceResult) bool {
	return a.Lifecycle == b.Lifecycle && a.Result == b.Result && a.JavaKind == b.JavaKind && a.JavaRef == b.JavaRef && bytes.Equal(a.JavaClass, b.JavaClass)
}

func TestVFS0aHarnessInspectFileIsReadOnlyView(t *testing.T) {
	vfs0aHarnessRequireRuntime(t)
	fixture := vfs0aHarnessFixtures(t)[10]
	session, err := NewMemory(common.HexToAddress("0x11000000000000000000000000000000000000e0"))
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	result := vfs0aHarnessRunChain(t, session, fixture, "inspect", 4096, 4096)
	id := crypto.Keccak256Hash([]byte(t.Name() + ":" + fixture.ID + ":inspect"))
	before, err := session.Head(id)
	if err != nil {
		t.Fatal(err)
	}
	view, err := session.InspectFile(fixture.Raw, result.Checkpoint, []byte("created"), 1, 2)
	if err != nil {
		t.Fatal(err)
	}
	if view.Kind != 2 || view.Inode == 0 || view.EffectiveReadOnly || !bytes.Equal(view.Data, []byte{67, 68}) || view.FileRoot == (common.Hash{}) {
		t.Fatalf("view=%+v", view)
	}
	after, err := session.Head(id)
	if err != nil || after != before {
		t.Fatalf("inspect changed head: %+v %+v %v", before, after, err)
	}
	missing, err := session.InspectFile(fixture.Raw, result.Checkpoint, []byte("absent"), 0, 4096)
	if err != nil || !reflect.DeepEqual(missing, FileInspection{}) {
		t.Fatalf("missing view=%+v err=%v", missing, err)
	}
	if _, err := session.InspectFile(fixture.Raw, result.Checkpoint, []byte("created"), 0, 4097); err == nil {
		t.Fatal("4097-byte inspect accepted")
	}
	if _, err := session.Resume(id, result.Slice.Epoch+1, result.Slice.CheckpointRoot, fixture.Raw, result.Checkpoint, 1, 1, vfs0aHarnessOrdinaryGas); err == nil {
		t.Fatal("inspection improperly authorized wrong-epoch resume")
	}
}

func TestVFS0aHarnessDiskFailureNoSpeculativePublication(t *testing.T) {
	vfs0aHarnessRequireRuntime(t)
	fixture, owner := vfs0aHarnessFixtures(t)[4], common.HexToAddress("0x20000000000000000000000000000000000000e0")
	for _, point := range []vfs0aHarnessFaultPoint{vfs0aHarnessFaultAfterBlob, vfs0aHarnessFaultAfterTrie, vfs0aHarnessFaultBeforeManifest} {
		t.Run(strconv.Itoa(int(point)), func(t *testing.T) {
			session, err := Open(t.TempDir(), owner)
			if err != nil {
				t.Fatal(err)
			}
			defer session.Close()
			id := crypto.Keccak256Hash([]byte(t.Name()))
			parent, err := session.Start(id, fixture.Raw, fixture.EntryClass, fixture.Entry, nil, fixture.Seeds, 1, 4096, vfs0aHarnessOrdinaryGas)
			if err != nil {
				t.Fatal(err)
			}
			before, _ := session.Head(id)
			fired := false
			session.testFault = func(got vfs0aHarnessFaultPoint) error {
				if got == point && !fired {
					fired = true
					return errors.New("durability fault")
				}
				return nil
			}
			failed, err := session.Resume(id, parent.Slice.Epoch, parent.Slice.CheckpointRoot, fixture.Raw, parent.Checkpoint, 1, 4096, vfs0aHarnessOrdinaryGas)
			if err == nil || !fired || failed.GasUsed == 0 || !reflect.DeepEqual(failed.Slice, SliceResult{}) || len(failed.Checkpoint) != 0 || len(failed.Logs) != 0 {
				t.Fatalf("failed publication leaked: %+v err=%v", failed, err)
			}
			after, headErr := session.Head(id)
			if headErr != nil || after != before {
				t.Fatalf("head changed: %+v %+v %v", before, after, headErr)
			}
			session.testFault = nil
			if _, err := session.Resume(id, parent.Slice.Epoch, parent.Slice.CheckpointRoot, fixture.Raw, parent.Checkpoint, 1, 4096, vfs0aHarnessOrdinaryGas); err != nil {
				t.Fatalf("old-root retry: %v", err)
			}
		})
	}
}

func TestVFS0aHarnessAmbiguousPublicationPoisonsUntilReopen(t *testing.T) {
	vfs0aHarnessRequireRuntime(t)
	dir, owner := t.TempDir(), common.HexToAddress("0x21000000000000000000000000000000000000e0")
	session, err := Open(dir, owner)
	if err != nil {
		t.Fatal(err)
	}
	fixture, id := vfs0aHarnessFixtures(t)[0], crypto.Keccak256Hash([]byte(t.Name()))
	parent, err := session.Start(id, fixture.Raw, fixture.EntryClass, fixture.Entry, nil, fixture.Seeds, 1, 4096, vfs0aHarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	session.testFault = func(point vfs0aHarnessFaultPoint) error {
		if point == vfs0aHarnessFaultAfterManifestRename {
			return errors.New("ambiguous fsync")
		}
		return nil
	}
	failed, err := session.Resume(id, parent.Slice.Epoch, parent.Slice.CheckpointRoot, fixture.Raw, parent.Checkpoint, 1, 4096, vfs0aHarnessOrdinaryGas)
	if err == nil || failed.GasUsed == 0 || !reflect.DeepEqual(failed.Slice, SliceResult{}) || len(failed.Checkpoint) != 0 || len(failed.Logs) != 0 {
		t.Fatalf("ambiguous output=%+v err=%v", failed, err)
	}
	if _, err := session.Head(id); err == nil {
		t.Fatal("poisoned session usable")
	}
	session.Close()
	reopened, err := Open(dir, owner)
	if err != nil {
		t.Fatal(err)
	}
	defer reopened.Close()
	if reopened.testCodeInstalls != 0 {
		t.Fatal("reopen reinstalled runtime")
	}
	head, err := reopened.Head(id)
	if err != nil || head.Epoch != parent.Slice.Epoch+1 {
		t.Fatalf("published head not recovered: %+v %v", head, err)
	}
}

func TestVFS0aHarnessPendingTruncateNewProcessResume(t *testing.T) {
	if os.Getenv("JVMEVM_VFS0A_PENDING_CHILD") != "" {
		vfs0aHarnessPendingChild(t)
		return
	}
	vfs0aHarnessRequireRuntime(t)
	fixture, owner := vfs0aHarnessFixtures(t)[11], common.HexToAddress("0x30000000000000000000000000000000000000e0")
	controlSession, err := NewMemory(owner)
	if err != nil {
		t.Fatal(err)
	}
	control := vfs0aHarnessRunChain(t, controlSession, fixture, "pending-control", 4096, 4096)
	controlSession.Close()
	dir := t.TempDir()
	session, err := Open(dir, owner)
	if err != nil {
		t.Fatal(err)
	}
	id := crypto.Keccak256Hash([]byte(t.Name()))
	cp, err := session.Start(id, fixture.Raw, fixture.EntryClass, fixture.Entry, nil, fixture.Seeds, 1, 4096, vfs0aHarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	for slices := 1; cp.Slice.DescriptorCount == 0 && slices < 4096; slices++ {
		if cp.Slice.Lifecycle != 1 {
			t.Fatal("truncate terminated before open/bind corridor")
		}
		cp, err = session.Resume(id, cp.Slice.Epoch, cp.Slice.CheckpointRoot, fixture.Raw, cp.Checkpoint, 1, 4096, vfs0aHarnessOrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
	}
	if cp.Slice.Lifecycle != 1 || cp.Slice.DescriptorCount != 1 {
		t.Fatalf("no runnable first descriptor checkpoint: %+v", cp.Slice)
	}
	view, err := session.InspectFile(fixture.Raw, cp.Checkpoint, []byte("truncate"), 0, 16)
	if err != nil || view.Kind != 2 || len(view.Data) != 0 {
		t.Fatalf("truncate was not visible before handle putfield: %+v %v", view, err)
	}
	if err := session.Close(); err != nil {
		t.Fatal(err)
	}
	cmd := exec.Command(os.Args[0], "-test.run=^TestVFS0aHarnessPendingTruncateNewProcessResume$")
	cmd.Env = append(os.Environ(), "JVMEVM_VFS0A_PENDING_CHILD=1", "JVMEVM_VFS0A_DIR="+dir, "JVMEVM_VFS0A_OWNER="+owner.Hex(), "JVMEVM_VFS0A_INSTANCE="+id.Hex(), "JVMEVM_VFS0A_EPOCH="+strconv.FormatUint(cp.Slice.Epoch, 10), "JVMEVM_VFS0A_ROOT="+cp.Slice.CheckpointRoot.Hex())
	output, err := cmd.Output()
	if err != nil {
		t.Fatalf("child: %v stderr=%s", err, vfs0aHarnessExitStderr(err))
	}
	var child struct {
		Machine  common.Hash `json:"machine"`
		VFS      common.Hash `json:"vfs"`
		Result   int32       `json:"result"`
		Jvm      uint64      `json:"jvm"`
		Internal uint64      `json:"internal"`
	}
	for _, line := range bytes.Split(output, []byte{'\n'}) {
		if len(line) > 0 && line[0] == '{' {
			if err := json.Unmarshal(line, &child); err != nil {
				t.Fatal(err)
			}
			break
		}
	}
	if child.Machine != control.Slice.MachineStateRoot || child.VFS != control.Slice.VFSStateRoot || child.Result != 1 || child.Jvm != control.Slice.TotalJvmSteps || child.Internal != control.Slice.TotalInternalSteps {
		t.Fatalf("child=%+v control=%+v output=%s", child, control.Slice, output)
	}
}

func vfs0aHarnessPendingChild(t *testing.T) {
	fixtures := vfs0aHarnessFixtures(t)
	fixture := fixtures[11]
	owner, id := common.HexToAddress(os.Getenv("JVMEVM_VFS0A_OWNER")), common.HexToHash(os.Getenv("JVMEVM_VFS0A_INSTANCE"))
	epoch, err := strconv.ParseUint(os.Getenv("JVMEVM_VFS0A_EPOCH"), 10, 64)
	if err != nil {
		t.Fatal(err)
	}
	root := common.HexToHash(os.Getenv("JVMEVM_VFS0A_ROOT"))
	session, err := Open(os.Getenv("JVMEVM_VFS0A_DIR"), owner)
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	if session.testCodeInstalls != 0 {
		t.Fatal("child reinstalled runtime")
	}
	checkpoint, err := session.ReadCheckpoint(root)
	if err != nil {
		t.Fatal(err)
	}
	var result Result
	for slices := 0; slices < 4096; slices++ {
		result, err = session.Resume(id, epoch, root, fixture.Raw, checkpoint, 7, 4096, vfs0aHarnessOrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
		if result.Slice.Lifecycle != 1 {
			if result.Slice.Lifecycle != 2 {
				t.Fatalf("child lifecycle=%d", result.Slice.Lifecycle)
			}
			payload, _ := json.Marshal(struct {
				Machine  common.Hash `json:"machine"`
				VFS      common.Hash `json:"vfs"`
				Result   int32       `json:"result"`
				Jvm      uint64      `json:"jvm"`
				Internal uint64      `json:"internal"`
			}{result.Slice.MachineStateRoot, result.Slice.VFSStateRoot, result.Slice.Result, result.Slice.TotalJvmSteps, result.Slice.TotalInternalSteps})
			fmt.Println(string(payload))
			return
		}
		epoch, root, checkpoint = result.Slice.Epoch, result.Slice.CheckpointRoot, result.Checkpoint
	}
	t.Fatal("child exceeded 4096 slices")
}

func vfs0aHarnessExitStderr(err error) string {
	var exit *exec.ExitError
	if errors.As(err, &exit) {
		return string(exit.Stderr)
	}
	return ""
}

func TestVFS0aHarnessNamespaceAndBoundedReads(t *testing.T) {
	if vfs0aHarnessContractAddress != common.HexToAddress("0x4a564d45564d564653304152554e54494d450001") || vfs0aHarnessStoreMarker != "JVMEVM-MC-VFS0A-DISK-STORE-1\n" {
		t.Fatal("frozen address/marker mismatch")
	}
	dir := t.TempDir()
	path := filepath.Join(dir, "user-file")
	if err := os.WriteFile(path, []byte("preserve"), 0o600); err != nil {
		t.Fatal(err)
	}
	if fresh, err := vfs0aHarnessPrepareDirectory(dir); err == nil || fresh {
		t.Fatal("unrelated directory accepted")
	}
	if got, _ := os.ReadFile(path); string(got) != "preserve" {
		t.Fatal("unrelated file changed")
	}
	vfs0aHarnessRequireRuntime(t)
	store, owner := t.TempDir(), common.HexToAddress("0x1234")
	session, err := Open(store, owner)
	if err != nil {
		t.Fatal(err)
	}
	session.Close()
	for _, name := range []string{vfs0aHarnessStateDirectory, vfs0aHarnessBlobDirectory, vfs0aHarnessManifestName} {
		t.Run(name, func(t *testing.T) {
			alias := filepath.Join(t.TempDir(), "store")
			if err := copyDirForVFS0aTest(store, alias); err != nil {
				t.Fatal(err)
			}
			original := filepath.Join(alias, name)
			moved := filepath.Join(t.TempDir(), "saved")
			if err := os.Rename(original, moved); err != nil {
				t.Fatal(err)
			}
			if err := os.Symlink(moved, original); err != nil {
				t.Fatal(err)
			}
			if bad, err := Open(alias, owner); err == nil {
				bad.Close()
				t.Fatal("internal symlink accepted")
			}
		})
	}
}

func copyDirForVFS0aTest(src, dst string) error {
	return filepath.Walk(src, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		rel, _ := filepath.Rel(src, path)
		target := filepath.Join(dst, rel)
		if info.IsDir() {
			return os.MkdirAll(target, info.Mode())
		}
		raw, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		return os.WriteFile(target, raw, info.Mode())
	})
}
