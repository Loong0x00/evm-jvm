package stock

import (
	"bytes"
	"context"
	"crypto/sha256"
	"fmt"
	"math/rand"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
	"time"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
)

// Parent-generated trusted Java inputs. The Java oracle only supplies expected
// results; CREATE/step execution receives the identical raw classes, not metadata.
func TestStockParentGeneratedJVMAndResumeBoundaries(t *testing.T) {
	dir := t.TempDir()
	oracle := `public class StockParentOracle { public static void main(String[] a)throws Exception {
 System.out.print(((Integer)Class.forName(a[0]).getMethod(a[1]).invoke(null)).intValue());}}`
	if err := os.WriteFile(filepath.Join(dir, "StockParentOracle.java"), []byte(oracle), 0600); err != nil {
		t.Fatal(err)
	}
	type probe struct {
		name string
		b    int32
	}
	var probes []probe
	args := []string{"--release", "8", "-g:none", "-d", dir, filepath.Join(dir, "StockParentOracle.java")}
	rng := rand.New(rand.NewSource(0x5300))
	edges := []int32{-2147483648, 2147483647, 0, 1, -1, 32767, -32768, 0x12345678}
	deltas := []int32{-128, -127, -1, 1, 126, 127}
	for i := 0; i < 20; i++ {
		a, b := int32(rng.Uint32()), int32(rng.Uint32())
		if i < len(edges) {
			a = edges[i]
			b = edges[(i+3)%len(edges)]
		}
		delta := deltas[i%len(deltas)]
		name := fmt.Sprintf("StockParent%02d", i)
		source := fmt.Sprintf(`public class %s {
 public static int run(){int a=%d;a+=%d;int b=%d;return(a*b)-a;}
 public static int local(){int a=%d;a+=%d;return a;}}
`, name, a, delta, b, a, delta)
		path := filepath.Join(dir, name+".java")
		if err := os.WriteFile(path, []byte(source), 0600); err != nil {
			t.Fatal(err)
		}
		args = append(args, path)
		probes = append(probes, probe{name, b})
	}
	stockParentCommand(t, "javac", args...)
	java8 := "/usr/lib/jvm/java-8-openjdk/bin/java"
	if _, err := os.Stat(java8); err != nil {
		t.Fatalf("Java8 oracle missing: %v", err)
	}
	page := stockVerifyLoadArtifact(t, "ArtifactPage")
	module := stockVerifyLoadArtifact(t, "TinyJvmStepModule")
	coord := stockVerifyLoadArtifact(t, "VMCoordinator")
	for _, p := range probes {
		raw, err := os.ReadFile(filepath.Join(dir, p.name+".class"))
		if err != nil {
			t.Fatal(err)
		}
		wants := make(map[string]int32)
		for _, method := range []string{"run", "local"} {
			var first int32
			for j, java := range []string{java8, "java"} {
				text := stockParentCommand(t, java, "-Xmx64m", "-Xss512k", "-Xverify:all", "-cp", dir, "StockParentOracle", p.name, method)
				n, err := strconv.ParseInt(strings.TrimSpace(text), 10, 32)
				if err != nil {
					t.Fatal(err)
				}
				if j == 0 {
					first = int32(n)
				} else if first != int32(n) {
					t.Fatalf("oracle mismatch %s/%s", p.name, method)
				}
			}
			wants[method] = first
		}
		for _, budget := range []uint8{1, 2, 7, 16} {
			t.Run(fmt.Sprintf("%s/budget%d", p.name, budget), func(t *testing.T) {
				e := stockVerifyNewEnv(t)
				defer e.close()
				pageAddr, pageTx := e.mustCreate(stockVerifyConstructor(t, page, raw), stockVerifyCreateGas)
				pageHash, payloadHash, pageCode := stockVerifyPageHashes(raw)
				if !bytes.Equal(e.state.StateDB.GetCode(pageAddr), pageCode) {
					t.Fatal("page differs from exact STOP||raw Java bytes")
				}
				moduleAddr, moduleTx := e.mustCreate(module.init, stockVerifyCreateGas)
				moduleHash := crypto.Keccak256Hash(module.runtime)
				at, coordTx := e.mustCreate(stockVerifyConstructor(t, coord, moduleAddr, pageAddr, moduleHash, pageHash, payloadHash), stockVerifyCreateGas)
				creationGas := pageTx.result.UsedGas + moduleTx.result.UsedGas + coordTx.result.UsedGas
				epoch, total, digest, machine := stockVerifyCheckpoint(t, e, coord, at)
				stockParentCheckZero(t, epoch, total, machine)
				var gas uint64
				for !machine.Done {
					if epoch >= 16 {
						t.Fatal("too many successful resumes")
					}
					// Fail a commit after progress, then retry the SAME guest state/epoch.
					if epoch == 2 {
						failed := stockVerifyResume(t, e, coord, at, epoch, budget, 1, stockVerifyCallGas)
						stockVerifyAssertRevert(t, failed, "StockControlError(uint256)", 6)
						stockVerifyAssertFailedRollback(t, e, coord, at, epoch, total, digest, machine, failed)
					}
					before := machine
					r := stockVerifyResume(t, e, coord, at, epoch, budget, 32, stockVerifyCallGas)
					if r.coreErr != nil || r.result == nil || r.result.Failed() {
						t.Fatalf("resume failed: %+v", r)
					}
					gas += r.result.UsedGas
					oldEpoch, oldTotal := epoch, total
					epoch, total, digest, machine = stockVerifyCheckpoint(t, e, coord, at)
					if epoch != oldEpoch+1 || total <= oldTotal || total-oldTotal > uint64(budget) {
						t.Fatal("bad step/epoch transition")
					}
					wantDigest := stockVerifyDigest(t, module, payloadHash, moduleHash, machine, epoch, total)
					if digest != wantDigest {
						t.Fatal("wrong digest")
					}
					stockVerifyCheckEvent(t, coord, r, epoch, total, machine, uint8(total-oldTotal), stockVerifyDirty(before, machine), digest)
				}
				if machine.Result != wants["run"] || total != 11 || machine.Initialized != 3 || machine.Sp != 0 {
					t.Fatalf("machine=%+v total=%d wantResult=%d", machine, total, wants["run"])
				}
				if machine.Locals[0].Cmp(stockVerifyTagged(uint32(wants["local"]))) != 0 || machine.Locals[1].Cmp(stockVerifyTagged(uint32(p.b))) != 0 {
					t.Fatal("wrong preserved locals")
				}
				if epoch+3 > 19 || gas+creationGas > 30_000_000 {
					t.Fatal("case budget exceeded")
				}
				t.Logf("class_sha256=%x budget=%d result=%d epochs=%d resume_gas=%d total_positive_gas=%d digest=%s", sha256.Sum256(raw), budget, machine.Result, epoch, gas, gas+creationGas, common.Hash(digest))
			})
		}
	}
}

func stockParentCommand(t *testing.T, command string, args ...string) string {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	b, err := exec.CommandContext(ctx, command, args...).CombinedOutput()
	if err != nil {
		t.Fatalf("%s: %v\n%s", command, err, b)
	}
	return string(b)
}
func stockParentCheckZero(t *testing.T, epoch, total uint64, m stockVerifyMachine) {
	t.Helper()
	if epoch != 0 || total != 0 || !stockVerifyMachineEqual(m, stockVerifyZeroMachine()) {
		t.Fatal("initial state not numeric zero")
	}
}

func TestStockParentCommitReserveThresholds(t *testing.T) {
	page := stockVerifyLoadArtifact(t, "ArtifactPage")
	module := stockVerifyLoadArtifact(t, "TinyJvmStepModule")
	coord := stockVerifyLoadArtifact(t, "VMCoordinator")
	raw := stockHarnessFixtureNamed(t, stockHarnessLoadFixtures(t), "CanonicalTwelve").Raw
	for _, phase := range []int{0, 1} {
		for gas := uint64(850_000); gas <= 950_000; gas += 5_000 {
			t.Run(fmt.Sprintf("phase%d/gas%d", phase, gas), func(t *testing.T) {
				e := stockVerifyNewEnv(t)
				defer e.close()
				pg, ph, payload := stockVerifyDeployPage(t, e, page, raw)
				mod, _ := e.mustCreate(module.init, stockVerifyCreateGas)
				at, _ := e.mustCreate(stockVerifyConstructor(t, coord, mod, pg, crypto.Keccak256Hash(module.runtime), ph, payload), stockVerifyCreateGas)
				if phase != 0 {
					e.mustCall(at, stockVerifyCallData(t, coord, "resume", uint64(0), uint8(3), uint8(32)), stockVerifyCallGas)
				}
				epoch, total, digest, before := stockVerifyCheckpoint(t, e, coord, at)
				r := stockVerifyResume(t, e, coord, at, epoch, 3, 32, gas)
				if r.coreErr != nil || r.result == nil {
					t.Fatalf("unexpected transaction rejection %+v", r)
				}
				if r.result.Failed() {
					if bytes.HasPrefix(r.result.ReturnData, crypto.Keccak256([]byte("Panic(uint256)"))[:4]) {
						t.Fatalf("reserve arithmetic panicked gas=%d data=%x", gas, r.result.ReturnData)
					}
					if len(r.result.ReturnData) != 0 {
						stockVerifyAssertRevert(t, r, "StockControlError(uint256)", 5)
					}
					stockVerifyAssertFailedRollback(t, e, coord, at, epoch, total, digest, before, r)
				} else {
					next, steps, _, after := stockVerifyCheckpoint(t, e, coord, at)
					if next != epoch+1 || steps != total+3 || after.Done {
						t.Fatalf("incorrect threshold success %+v", after)
					}
				}
			})
		}
	}
}
