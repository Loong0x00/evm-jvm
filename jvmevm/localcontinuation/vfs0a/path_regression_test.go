package vfs0a

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/ethereum/go-ethereum/common"
)

type vfs0aHarnessPathManifest struct {
	Schema       uint32              `json:"schema"`
	Compiler     string              `json:"compiler"`
	Source       string              `json:"source"`
	SourceSHA256 string              `json:"sourceSHA256"`
	Class        string              `json:"class"`
	ClassSHA256  string              `json:"classSHA256"`
	EntryClass   string              `json:"entryClass"`
	Entries      []string            `json:"entries"`
	Seeds        []vfs0aHarnessSeed  `json:"seeds"`
	Outcome      vfs0aHarnessOutcome `json:"outcome"`
}

func vfs0aHarnessPathFixtures(t *testing.T) []vfs0aHarnessFixture {
	t.Helper()
	root := filepath.Join(vfs0aHarnessFixtureRoot(t), "regressions")
	raw, err := os.ReadFile(filepath.Join(root, "manifest.json"))
	if err != nil {
		t.Fatal(err)
	}
	var manifest vfs0aHarnessPathManifest
	if err := json.Unmarshal(raw, &manifest); err != nil {
		t.Fatal(err)
	}
	if manifest.Schema != 1 || manifest.Compiler != "javac --release 8 -g:none" || manifest.EntryClass != "VFS0aPathTraversal" || len(manifest.Entries) != 7 || manifest.Outcome.Lifecycle != "RETURNED" || manifest.Outcome.Result != 1 || manifest.Outcome.JavaKind != 0 || manifest.Outcome.JavaClassHex != "" {
		t.Fatalf("unexpected path-regression manifest: %+v", manifest)
	}
	source, err := os.ReadFile(filepath.Join(root, "src", manifest.Source))
	if err != nil {
		t.Fatal(err)
	}
	classfile, err := os.ReadFile(filepath.Join(root, "classes", manifest.Class))
	if err != nil {
		t.Fatal(err)
	}
	for label, value := range map[string]struct {
		raw  []byte
		want string
	}{
		"source": {source, manifest.SourceSHA256}, "class": {classfile, manifest.ClassSHA256},
	} {
		hash := sha256.Sum256(value.raw)
		if hex.EncodeToString(hash[:]) != value.want {
			t.Fatalf("path-regression %s hash=%x want=%s", label, hash, value.want)
		}
	}
	fixtures := make([]vfs0aHarnessFixture, len(manifest.Entries))
	for i, entry := range manifest.Entries {
		fixture := vfs0aHarnessFixture{ID: entry, Group: "PathTraversal", Source: manifest.Source, SourceSHA256: manifest.SourceSHA256, EntryClass: manifest.EntryClass, Entry: entry, Outcome: manifest.Outcome, Raw: [][]byte{append([]byte(nil), classfile...)}}
		for _, seed := range manifest.Seeds {
			path, pathErr := hex.DecodeString(seed.PathHex)
			data, dataErr := hex.DecodeString(seed.DataHex)
			if pathErr != nil || dataErr != nil {
				t.Fatalf("path-regression seed decode: %v/%v", pathErr, dataErr)
			}
			fixture.Seeds = append(fixture.Seeds, SeedFile{Path: path, Data: data, ReadOnly: seed.ReadOnly})
		}
		fixtures[i] = fixture
	}
	return fixtures
}

func TestVFS0aHarnessPathTraversalJava8And21Oracles(t *testing.T) {
	fixtures := vfs0aHarnessPathFixtures(t)
	root, compiled := filepath.Join(vfs0aHarnessFixtureRoot(t), "regressions"), t.TempDir()
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	output, err := exec.CommandContext(ctx, "javac", "--release", "8", "-g:none", "-d", compiled, filepath.Join(root, "src", "VFS0aPathTraversal.java")).CombinedOutput()
	cancel()
	if err != nil {
		t.Fatalf("trusted path fixture rebuild: %v\n%s", err, output)
	}
	rebuilt, err := os.ReadFile(filepath.Join(compiled, "VFS0aPathTraversal.class"))
	if err != nil || !bytes.Equal(rebuilt, fixtures[0].Raw[0]) {
		t.Fatalf("rebuilt path fixture differs: %v", err)
	}
	oracle := `import java.lang.reflect.*; public final class VFS0aPathOracle { public static void main(String[] a) throws Exception { try { System.out.print("R:" + ((Integer)Class.forName("VFS0aPathTraversal").getDeclaredMethod(a[0]).invoke(null)).intValue()); } catch (InvocationTargetException e) { System.out.print("U:" + e.getCause().getClass().getName()); } } }`
	oraclePath := filepath.Join(compiled, "VFS0aPathOracle.java")
	if err := os.WriteFile(oraclePath, []byte(oracle), 0o600); err != nil {
		t.Fatal(err)
	}
	ctx, cancel = context.WithTimeout(context.Background(), 30*time.Second)
	output, err = exec.CommandContext(ctx, "javac", "--release", "8", "-g:none", "-cp", compiled, "-d", compiled, oraclePath).CombinedOutput()
	cancel()
	if err != nil {
		t.Fatalf("path oracle compile: %v\n%s", err, output)
	}
	java8, java21 := "/usr/lib/jvm/java-8-openjdk/bin/java", "/usr/lib/jvm/jdk-21.0.9/bin/java"
	if home := os.Getenv("JAVA8_HOME"); home != "" {
		java8 = filepath.Join(home, "bin", "java")
	}
	if home := os.Getenv("JAVA21_HOME"); home != "" {
		java21 = filepath.Join(home, "bin", "java")
	}
	for _, jdk := range []struct{ name, path string }{{"java8-primary", java8}, {"java21-secondary", java21}} {
		for _, fixture := range fixtures {
			work := filepath.Join(t.TempDir(), "owned-work")
			if err := os.Mkdir(work, 0o700); err != nil {
				t.Fatal(err)
			}
			vfs0aHarnessMaterializeOracleSeeds(t, work, fixture.Seeds)
			ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			cmd := exec.CommandContext(ctx, jdk.path, "-Xmx64m", "-cp", compiled, "VFS0aPathOracle", fixture.Entry)
			cmd.Dir, cmd.Env = work, vfs0aHarnessCLocaleEnv()
			output, err := cmd.CombinedOutput()
			cancel()
			if err != nil || strings.TrimSpace(string(output)) != "R:1" {
				t.Fatalf("%s %s output=%q error=%v", jdk.name, fixture.ID, output, err)
			}
		}
	}
}

func TestVFS0aHarnessPathTraversalActualEVM(t *testing.T) {
	vfs0aHarnessRequireRuntime(t)
	session, err := NewMemory(common.HexToAddress("0x40000000000000000000000000000000000000e0"))
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	chains := map[string]bool{"fileDotDotInput": true, "fileDotDotOutput": true, "mkdirTraversal": true}
	for _, fixture := range vfs0aHarnessPathFixtures(t) {
		fixture := fixture
		t.Run(fixture.ID, func(t *testing.T) {
			control := vfs0aHarnessRunChain(t, session, fixture, "path-one", 4096, 4096)
			if !chains[fixture.ID] {
				return
			}
			for _, q := range []uint64{1, 7} {
				got := vfs0aHarnessRunChain(t, session, fixture, fmt.Sprintf("path-q%d", q), q, 4096)
				if got.Slice.MachineStateRoot != control.Slice.MachineStateRoot || got.Slice.VFSStateRoot != control.Slice.VFSStateRoot || got.Slice.TotalJvmSteps != control.Slice.TotalJvmSteps || got.Slice.TotalInternalSteps != control.Slice.TotalInternalSteps || !vfs0aHarnessSameOutcome(got.Slice, control.Slice) {
					t.Fatalf("path q%d terminal mismatch", q)
				}
			}
		})
	}
}
