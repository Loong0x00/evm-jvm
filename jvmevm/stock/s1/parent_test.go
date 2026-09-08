package s1

import (
	"bytes"
	"context"
	"fmt"
	"github.com/ethereum/go-ethereum/crypto"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
	"time"
)

// This oracle executes only our trusted generated quota class on reference JVMs.
// Its reflection/string usage is host TEST code, never an S1 execution service.
func stockS1ParentAssertAggregateJVM(t *testing.T, raw []byte) {
	t.Helper()
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "S1Aggregate.class"), raw, 0600); err != nil {
		t.Fatal(err)
	}
	source := `public class ParentS1AggregateOracle {
 public static void main(String[] args)throws Exception {
 Class<?> c=Class.forName("S1Aggregate");
 for(int i=0;i<31;i++) {
 int n=((Integer)c.getMethod(String.format("m%02d",i)).invoke(null)).intValue();
 if(n!=(i<4?0x12345678:0))throw new AssertionError("wrong result");
 }
 System.out.print("31 methods verified");
 }} `
	file := filepath.Join(dir, "ParentS1AggregateOracle.java")
	if err := os.WriteFile(file, []byte(source), 0600); err != nil {
		t.Fatal(err)
	}
	stockS1ParentCommand(t, "javac", "--release", "8", "-g:none", "-d", dir, file)
	for _, java := range []string{"/usr/lib/jvm/java-8-openjdk/bin/java", "java"} {
		got := stockS1ParentCommand(t, java, "-Xmx64m", "-Xss512k", "-Xverify:all", "-cp", dir, "ParentS1AggregateOracle")
		if strings.TrimSpace(got) != "31 methods verified" {
			t.Fatalf("oracle %s: %q", java, got)
		}
	}
}
func stockS1ParentCommand(t *testing.T, command string, args ...string) string {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	b, err := exec.CommandContext(ctx, command, args...).CombinedOutput()
	if err != nil {
		t.Fatalf("%s: %v\n%s", command, err, b)
	}
	return string(b)
}

func TestStockS1ParentEightLocalLoopsAndResumeBoundaries(t *testing.T) {
	dir := t.TempDir()
	guest := `public class ParentS1Loops {
 public static int mixed(int seed,int n,int x,int y){
 int a=seed+x,b=seed-y,c=n+x,d=n-y;
 while(n>0){if(a<0)b+=x;else b-=y;c=c*b-a;d=-d;a+=n;n--;}
 return a+b+c+d;
 }} `
	oracle := `public class ParentS1LoopOracle {public static void main(String[] a){System.out.print(ParentS1Loops.mixed(Integer.parseInt(a[0]),Integer.parseInt(a[1]),Integer.parseInt(a[2]),Integer.parseInt(a[3])));}}`
	for name, source := range map[string]string{"ParentS1Loops": guest, "ParentS1LoopOracle": oracle} {
		if err := os.WriteFile(filepath.Join(dir, name+".java"), []byte(source), 0600); err != nil {
			t.Fatal(err)
		}
	}
	stockS1ParentCommand(t, "javac", "--release", "8", "-g:none", "-d", dir, filepath.Join(dir, "ParentS1Loops.java"), filepath.Join(dir, "ParentS1LoopOracle.java"))
	raw, err := os.ReadFile(filepath.Join(dir, "ParentS1Loops.class"))
	if err != nil {
		t.Fatal(err)
	}
	page := stockS1VerifyLoadPage(t)
	parser := stockS1VerifyLoadArtifact(t, "S1ClassParser")
	module := stockS1VerifyLoadArtifact(t, "S1StepModule")
	coord := stockS1VerifyLoadArtifact(t, "S1Coordinator")
	e := stockS1VerifyNewEnv(t)
	defer e.close()
	parserAt, parserTx := e.mustCreate(parser.init, stockS1VerifyCreateGas)
	moduleAt, moduleTx := e.mustCreate(module.init, stockS1VerifyCreateGas)
	rawAt, pageHash, payloadHash, pageTx := stockS1VerifyDeployPage(t, e, page, raw)
	id, _, _, _, registerTx := stockS1VerifyRegister(t, e, parser, parserAt, rawAt, pageHash, payloadHash)
	setupGas := parserTx.result.UsedGas + moduleTx.result.UsedGas + pageTx.result.UsedGas + registerTx.result.UsedGas
	parserHash, moduleHash := crypto.Keccak256Hash(parser.runtime), crypto.Keccak256Hash(module.runtime)
	edges := []int32{-2147483648, 2147483647, -1, 0, 1, 12345678}
	for si, seed := range edges {
		for _, n := range []int32{0, 1, 4, 12} {
			x, y := edges[(si+2)%len(edges)], edges[(si+3)%len(edges)]
			args := []int32{seed, n, x, y}
			textArgs := []string{}
			for _, v := range args {
				textArgs = append(textArgs, strconv.FormatInt(int64(v), 10))
			}
			var want int32
			for j, java := range []string{"/usr/lib/jvm/java-8-openjdk/bin/java", "java"} {
				cmd := append([]string{"-Xmx64m", "-Xss512k", "-Xverify:all", "-cp", dir, "ParentS1LoopOracle"}, textArgs...)
				text := stockS1ParentCommand(t, java, cmd...)
				v, err := strconv.ParseInt(strings.TrimSpace(text), 10, 32)
				if err != nil {
					t.Fatal(err)
				}
				if j == 0 {
					want = int32(v)
				} else if want != int32(v) {
					t.Fatal("JVM8/21 mismatch")
				}
			}
			// Expected terminal locals are TEST-only assertions, checked against the
			// real JVM return above. They are never passed into parser or step calls.
			a, b, c, d := seed+x, seed-y, n+x, n-y
			for k := n; k > 0; k-- {
				if a < 0 {
					b += x
				} else {
					b -= y
				}
				c = c*b - a
				d = -d
				a += k
			}
			if a+b+c+d != want {
				t.Fatal("test-local oracle disagrees with JVM")
			}
			for _, budget := range []uint16{64, 128} {
				t.Run(fmt.Sprintf("seed%d/n%d/q%d", si, n, budget), func(t *testing.T) {
					at, create := stockS1VerifyDeployCoordinator(t, e, coord, parserAt, parserHash, id, moduleAt, moduleHash, "mixed", args, 512)
					before := stockS1VerifyCheckpointAt(t, e, coord, at)
					gas := setupGas + create.result.UsedGas
					failed := false
					for before.Machine.Lifecycle == stockS1VerifyRunnable {
						if before.Epoch >= 13 {
							t.Fatal("resume bound")
						}
						q := budget
						if si == 0 && n == 12 && budget == 64 && before.Epoch < 5 {
							q = 1
						}
						if before.Epoch > 0 && !failed {
							bad := stockS1VerifyResume(t, e, coord, at, before.Epoch, q, 1, stockS1VerifyCallGas)
							stockS1VerifyAssertRevert(t, bad, "S1ControlError(uint256)", 6)
							stockS1VerifyAssertRollback(t, e, coord, at, before, bad)
							failed = true
						}
						tx := stockS1VerifyResume(t, e, coord, at, before.Epoch, q, 32, stockS1VerifyCallGas)
						if tx.coreErr != nil || tx.result == nil || tx.result.Failed() {
							t.Fatalf("resume failed: %v/%v", tx.coreErr, stockS1VerifyResultErr(tx.result))
						}
						gas += tx.result.UsedGas
						after := stockS1VerifyCheckpointAt(t, e, coord, at)
						if after.Epoch != before.Epoch+1 || after.TotalSteps <= before.TotalSteps || after.TotalSteps-before.TotalSteps > uint64(q) {
							t.Fatal("bad epoch/step transition")
						}
						before = after
					}
					if before.Machine.Lifecycle != stockS1VerifyReturned || before.Machine.Result != want || before.Machine.Initialized != 255 || before.Machine.Sp != 0 {
						t.Fatalf("wrong terminal %+v want%d", before, want)
					}
					locals := []int32{seed, 0, x, y, a, b, c, d}
					for i, v := range locals {
						if before.Machine.Locals[i].Cmp(stockS1VerifyTagged(uint32(v))) != 0 {
							t.Fatalf("local%d=%v want%d", i, before.Machine.Locals[i], v)
						}
					}
					if gas > 30_000_000 || before.Epoch+5 > 19 {
						t.Fatal("isolated case budget")
					}
					t.Logf("args=%v q=%d result=%d steps=%d epochs=%d isolatedGas=%d", args, budget, want, before.TotalSteps, before.Epoch, gas)
				})
			}
		}
	}
}

func TestStockS1ParentEightLocalReserveThresholds(t *testing.T) {
	page := stockS1VerifyLoadPage(t)
	parser := stockS1VerifyLoadArtifact(t, "S1ClassParser")
	module := stockS1VerifyLoadArtifact(t, "S1StepModule")
	coord := stockS1VerifyLoadArtifact(t, "S1Coordinator")
	e := stockS1VerifyNewEnv(t)
	defer e.close()
	p, _ := e.mustCreate(parser.init, stockS1VerifyCreateGas)
	m, _ := e.mustCreate(module.init, stockS1VerifyCreateGas)
	ph, mh := crypto.Keccak256Hash(parser.runtime), crypto.Keccak256Hash(module.runtime)
	code := []byte{0x1a, 0x36, 4, 0x1b, 0x36, 5, 0x1c, 0x36, 6, 0x1d, 0x36, 7, 0x15, 4, 0x15, 5, 0x60, 0x15, 6, 0x60, 0x15, 7, 0x60, 0xac}
	raw := stockS1VerifySimpleClass(code, 2, 8, "(IIII)I")
	_, _, _, id, _, _, _ := stockS1VerifyDeployRegistered(t, e, page, parser, p, raw.bytes)
	for _, phase := range []uint64{0, 1} {
		for gas := uint64(850_000); gas <= 1_100_000; gas += 10_000 {
			t.Run(fmt.Sprintf("phase%d/gas%d", phase, gas), func(t *testing.T) {
				at, _ := stockS1VerifyDeployCoordinator(t, e, coord, p, ph, id, m, mh, "entry", []int32{-2147483648, 1, 2147483647, -1}, 64)
				if phase == 1 {
					e.mustCall(at, stockS1VerifyCallData(t, coord, "resume", uint64(0), uint16(8), uint8(32)), stockS1VerifyCallGas)
				}
				before := stockS1VerifyCheckpointAt(t, e, coord, at)
				r := stockS1VerifyResume(t, e, coord, at, phase, 8, 32, gas)
				if r.coreErr != nil || r.result == nil {
					t.Fatalf("unexpected precheck %v", r.coreErr)
				}
				if r.result.Failed() {
					if bytes.HasPrefix(r.result.ReturnData, crypto.Keccak256([]byte("Panic(uint256)"))[:4]) {
						t.Fatalf("reserve panic at gas%d: %x", gas, r.result.ReturnData)
					}
					if len(r.result.ReturnData) != 0 {
						stockS1VerifyAssertRevert(t, r, "S1ControlError(uint256)", 5)
					}
					stockS1VerifyAssertRollback(t, e, coord, at, before, r)
				} else {
					after := stockS1VerifyCheckpointAt(t, e, coord, at)
					if after.Epoch != before.Epoch+1 || after.TotalSteps != before.TotalSteps+8 || after.Machine.Initialized != 255 {
						t.Fatal("wrong threshold success")
					}
					if phase == 1 && (after.Machine.Lifecycle != stockS1VerifyReturned || after.Machine.Result != -1) {
						t.Fatal("wrong threshold return")
					}
				}
			})
		}
	}
}
