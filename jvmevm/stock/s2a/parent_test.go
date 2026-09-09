package s2a

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
	"time"

	"github.com/ethereum/go-ethereum/crypto"
)

// Trusted parent-authored Java. Reference results never enter production calls;
// stock receives only the unchanged class, entry name and integer arguments.
func TestStockS2aParentJVMIntegerAndFaultPrefixes(t *testing.T) {
	dir := t.TempDir()
	source := `public class ParentS2aProbe {
 public static int divPrefix(int a,int b,int c){int saved=c+3;return saved+a/b;}
 public static int remPrefix(int a,int b,int c){int saved=c+3;return saved+a%b;}
 public static int mix(int a,int n,int b,int c){int x=((a<<n)|(a>>>n))&(b^c);int y=(a>>n)^~b;return x+y+(byte)b+(short)c+(char)c;}
 }`
	guest := filepath.Join(dir, "ParentS2aProbe.java")
	if err := os.WriteFile(guest, []byte(source), 0600); err != nil {
		t.Fatal(err)
	}
	stockS2aParentCommand(t, "javac", "--release", "8", "-g:none", "-d", dir, guest, "../../testdata/differential/OracleMain.java")
	raw, err := os.ReadFile(filepath.Join(dir, "ParentS2aProbe.class"))
	if err != nil {
		t.Fatal(err)
	}
	page := stockS2aVerifyLoadPage(t)
	parser := stockS2aVerifyLoadArtifact(t, "S2aClassParser")
	module := stockS2aVerifyLoadArtifact(t, "S2aStepModule")
	coord := stockS2aVerifyLoadArtifact(t, "S2aCoordinator")
	e := stockS2aVerifyNewEnv(t)
	defer e.close()
	pa, _ := e.mustCreate(parser.init, stockS2aVerifyCreateGas)
	ma, _ := e.mustCreate(module.init, stockS2aVerifyCreateGas)
	ph, mh := crypto.Keccak256Hash(parser.runtime), crypto.Keccak256Hash(module.runtime)
	_, _, _, id, _, _, _ := stockS2aVerifyDeployRegistered(t, e, page, parser, pa, raw)
	type probe struct {
		method string
		args   []int32
	}
	var cases []probe
	values := []int32{-2147483648, 2147483647, -1, 0, 1, 0x12345678, -1431655766}
	for _, a := range values {
		for _, b := range []int32{0, -1, 1, 2, -2, -2147483648, 2147483647} {
			for _, m := range []string{"divPrefix", "remPrefix"} {
				cases = append(cases, probe{m, []int32{a, b, a ^ 2147483647}})
			}
		}
	}
	for i, a := range values {
		for _, n := range []int32{-1, 0, 1, 31, 32, 33, -2147483648, 2147483647} {
			cases = append(cases, probe{"mix", []int32{a, n, values[(i+2)%len(values)], values[(i+3)%len(values)]}})
		}
	}
	if len(cases) != 154 {
		t.Fatal("case count changed")
	}
	for index, tc := range cases {
		cmd := []string{"-Xmx64m", "-Xss512k", "-Xverify:all", "-cp", dir, "OracleMain", "ParentS2aProbe", tc.method}
		for _, v := range tc.args {
			cmd = append(cmd, strconv.FormatInt(int64(v), 10))
		}
		j8 := strings.TrimSpace(stockS2aParentCommand(t, "/usr/lib/jvm/java-8-openjdk/bin/java", cmd...))
		j21 := strings.TrimSpace(stockS2aParentCommand(t, "java", cmd...))
		if j8 != j21 {
			t.Fatalf("JVM mismatch %s / %s", j8, j21)
		}
		fault := j8 == "exception=java.lang.ArithmeticException"
		var want int32
		if !fault {
			v, err := strconv.ParseInt(strings.TrimPrefix(j8, "value="), 10, 32)
			if err != nil {
				t.Fatalf("unexpected oracle %q", j8)
			}
			want = int32(v)
		}
		for _, budget := range []uint16{1, 128} {
			t.Run(fmt.Sprintf("case%03d/%s/q%d", index, tc.method, budget), func(t *testing.T) {
				at, _ := stockS2aVerifyDeployCoordinator(t, e, coord, pa, ph, id, ma, mh, tc.method, tc.args, 1024)
				state := stockS2aVerifyCheckpointAt(t, e, coord, at)
				for state.Machine.Lifecycle == stockS2aVerifyRunnable {
					if state.Epoch >= 64 {
						t.Fatal("bounded probe did not terminate")
					}
					r := stockS2aVerifyResume(t, e, coord, at, state.Epoch, budget, 32, stockS2aVerifyCallGas)
					if r.coreErr != nil || r.result == nil || r.result.Failed() {
						t.Fatalf("resume failed %v/%v", r.coreErr, stockS2aVerifyResultErr(r.result))
					}
					state = stockS2aVerifyCheckpointAt(t, e, coord, at)
				}
				if fault {
					if state.Machine.Lifecycle != stockS2aVerifyJavaFault || state.Machine.JavaFaultKind != 1 || state.Machine.Result != 0 || state.Machine.Pc != 7 || state.Machine.FaultPC != 7 || state.TotalSteps != 8 || state.Machine.Sp != 3 || state.Machine.Initialized != 15 {
						t.Fatalf("wrong fault %+v", state)
					}
					for i, v := range []int32{tc.args[2] + 3, tc.args[0], 0} {
						if state.Machine.Stack[i].Cmp(stockS2aVerifyTagged(uint32(v))) != 0 {
							t.Fatalf("lost prefix/operand%d", i)
						}
					}
					if state.Machine.Locals[3].Cmp(stockS2aVerifyTagged(uint32(tc.args[2]+3))) != 0 {
						t.Fatal("lost saved local")
					}
				} else if state.Machine.Lifecycle != stockS2aVerifyReturned || state.Machine.Result != want || state.Machine.JavaFaultKind != 0 || state.Machine.FaultPC != 0 {
					t.Fatalf("wrong return %+v want%d", state, want)
				}
			})
		}
	}
	// Stop just BEFORE the fault, then independently show the fault wins AT cap.
	for _, method := range []string{"divPrefix", "remPrefix"} {
		for _, cap := range []uint64{7, 8} {
			t.Run(fmt.Sprintf("%s/cap%d", method, cap), func(t *testing.T) {
				at, _ := stockS2aVerifyDeployCoordinator(t, e, coord, pa, ph, id, ma, mh, method, []int32{-2147483648, 0, 2147483647}, cap)
				r := stockS2aVerifyResume(t, e, coord, at, 0, 7, 32, stockS2aVerifyCallGas)
				if r.coreErr != nil || r.result.Err != nil {
					t.Fatal("prefix failed")
				}
				before := stockS2aVerifyCheckpointAt(t, e, coord, at)
				if before.TotalSteps != 7 || before.Machine.Pc != 7 || before.Machine.JavaFaultKind != 0 || before.Machine.Sp != 3 {
					t.Fatal("fault predicted before instruction")
				}
				if cap == 7 {
					if before.Machine.Lifecycle != stockS2aVerifyStepLimit {
						t.Fatal("wrong pre-fault cap")
					}
					return
				}
				rejected := stockS2aVerifyResume(t, e, coord, at, before.Epoch, 128, 5, stockS2aVerifyCallGas)
				stockS2aVerifyAssertRevert(t, rejected, "S2aControlError(uint256)", 6)
				stockS2aVerifyAssertRollback(t, e, coord, at, before, rejected)
				r = stockS2aVerifyResume(t, e, coord, at, before.Epoch, 128, 32, stockS2aVerifyCallGas)
				if r.coreErr != nil || r.result.Err != nil {
					t.Fatal("fault retry failed")
				}
				after := stockS2aVerifyCheckpointAt(t, e, coord, at)
				if after.TotalSteps != 8 || after.Epoch != before.Epoch+1 || after.Machine.Lifecycle != stockS2aVerifyJavaFault || after.Machine.JavaFaultKind != 1 || after.Machine.Pc != 7 || after.Machine.FaultPC != 7 {
					t.Fatalf("wrong fault at cap %+v", after)
				}
				terminal := stockS2aVerifyResume(t, e, coord, at, after.Epoch, 1, 32, stockS2aVerifyCallGas)
				stockS2aVerifyAssertRevert(t, terminal, "S2aControlError(uint256)", 1)
			})
		}
	}
}

func stockS2aParentCommand(t *testing.T, name string, args ...string) string {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	b, err := exec.CommandContext(ctx, name, args...).CombinedOutput()
	if err != nil {
		t.Fatalf("%s: %v\n%s", name, err, b)
	}
	return string(b)
}
