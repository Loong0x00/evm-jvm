package s2b

// Parent-owned TEST-only raw inputs, generated independently before integration.
// Original preflight wrongly rejected the valid CFG and depended on declaration
// order for invalid callee bodies. These require production SUCCESS, not old failure.
import (
	"bytes"
	"context"
	"encoding/hex"
	"fmt"
	"github.com/ethereum/go-ethereum/crypto"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
	"time"
)

var stockS2bLinkParentRaw = map[string]string{
	"CallerFirst":   "cafebabe00000034000b01000b506172656e744f726465720700010100106a6176612f6c616e672f4f626a65637407000301000463616c6c010003282949010003626164010004436f64650c000700060a0002000900210002000400000000000200090005000600010008000000100001000000000004b8000aac00000000000900070006000100080000000e00010001000000021aac000000000000",
	"BadFirst":      "cafebabe00000034000b01000b506172656e744f726465720700010100106a6176612f6c616e672f4f626a65637407000301000463616c6c010003282949010003626164010004436f64650c000700060a00020009002100020004000000000002000900070006000100080000000e00010001000000021aac0000000000090005000600010008000000100001000000000004b8000aac000000000000",
	"ParentRevisit": "cafebabe00000034000901000d506172656e74526576697369740700010100106a6176612f6c616e672f4f626a656374070003010004436f646501000d537461636b4d61705461626c6501000372756e01000428492949002100020004000000000001000900070008000100050000009c00010002000000861a99002e00000000000000000000000000000000000000000000000000000000000000000000000000000000a70008043ca70003000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000003ac0000000100060000000400022f040000",
}

func stockS2bLinkParentBytes(t *testing.T, name string) []byte {
	t.Helper()
	b, err := hex.DecodeString(stockS2bLinkParentRaw[name])
	if err != nil || len(b) == 0 {
		t.Fatal(name, err)
	}
	return b
}
func TestStockS2bLinkParentOriginalOrderAndQueueRegressions(t *testing.T) {
	s := stockS2bLinkVerifySetupRuntime(t)
	defer s.close()
	for _, name := range []string{"CallerFirst", "BadFirst", "ParentRevisit"} {
		raw := stockS2bLinkParentBytes(t, name)
		r, m, _, _, _ := s.register(t, stockS2bLinkVerifyClass{bytes: raw})
		if name == "ParentRevisit" {
			if r.methods != 1 || r.calls != 0 {
				t.Fatal(r)
			}
			stockS2bLinkVerifyMethodRecord(t, m.methods[0], 0, 0, 0)
			if m.methods[0].codeLen != 134 || m.methods[0].maxLocals != 2 {
				t.Fatal("CFG envelope")
			}
			for pc := 0; pc < 256; pc++ {
				want := pc < 134 && pc != 2 && pc != 3 && pc != 45 && pc != 46 && pc != 50 && pc != 51
				if (m.methods[0].starts.Bit(pc) == 1) != want {
					t.Fatalf("pc%d starts mismatch", pc)
				}
			}
		} else {
			caller, bad := 0, 1
			if name == "BadFirst" {
				caller, bad = 1, 0
			}
			if r.methods != 2 || r.calls != 1 || len(m.calls) != 1 {
				t.Fatal(r)
			}
			stockS2bLinkVerifyMethodRecord(t, m.methods[caller], 0, 0, 0)
			stockS2bLinkVerifyMethodRecord(t, m.methods[bad], 2, 11, 0)
			c := m.calls[0]
			if c.caller != uint16(caller) || c.target != uint16(bad) || c.pc != 0 || c.cpIndex != 10 || c.argc != 0 || c.returnKind != 1 {
				t.Fatal(c)
			}
		}
		t.Logf("%s raw%d gas%d methods%d calls%d", name, len(raw), r.tx.result.UsedGas, r.methods, r.calls)
	}
}
func TestStockS2bLinkParentOriginalQueueJVM8And21(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "ParentRevisit.class"), stockS2bLinkParentBytes(t, "ParentRevisit"), 0600); err != nil {
		t.Fatal(err)
	}
	src := `public class ParentOracle {public static void main(String[] a)throws Exception {java.lang.reflect.Method m=Class.forName("ParentRevisit").getMethod("run",int.class);for(int n:new int[]{0,1,-1,Integer.MIN_VALUE,Integer.MAX_VALUE})System.out.println(n+"="+m.invoke(null,n));}}`
	file := filepath.Join(dir, "ParentOracle.java")
	if err := os.WriteFile(file, []byte(src), 0600); err != nil {
		t.Fatal(err)
	}
	run := func(exe string, args ...string) []byte {
		t.Helper()
		ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
		defer cancel()
		out, err := exec.CommandContext(ctx, exe, args...).CombinedOutput()
		if err != nil {
			t.Fatalf("%s: %v %s", exe, err, out)
		}
		return out
	}
	run("javac", "--release", "8", "-d", dir, file)
	java8 := os.Getenv("JAVA_EVM_JAVA8")
	if java8 == "" {
		java8 = "/usr/lib/jvm/java-8-openjdk/bin/java"
	}
	want := []byte("0=0\n1=0\n-1=0\n-2147483648=0\n2147483647=0\n")
	for _, java := range []string{java8, "java"} {
		got := run(java, "-Xverify:all", "-cp", dir, "ParentOracle")
		if !bytes.Equal(got, want) {
			t.Fatalf("%s: %s", java, got)
		}
	}
}
func TestStockS2bLinkParentBoundedRevertPropagation(t *testing.T) {
	s := stockS2bLinkVerifySetupRuntime(t)
	defer s.close()
	raw := stockS2bLinkParentBytes(t, "ParentRevisit")
	page, ph, pvh, _ := stockS2bLinkVerifyDeployPage(t, s.e, s.page, raw)
	for _, size := range []int{0, 1, 31, 32, 63, 64, 65, 68, 96, 128, 255, 256, 257, 8097} {
		t.Run(fmt.Sprint(size), func(t *testing.T) {
			payload := bytes.Repeat([]byte{0xa5}, size)
			if size > 0 {
				payload[size-1] = byte(size)
			}
			mock := stockS2bLinkVerifyMockReturnRuntime(payload, false)
			mock[18] = 0xfd // TEST bytecode: REVERT instead of RETURN.
			addr, _ := stockS2bLinkVerifyDeployRaw(t, s.e, mock)
			linker, _ := stockS2bLinkVerifyDeployLinker(t, s.e, s.linker, addr, crypto.Keccak256Hash(mock), crypto.Keccak256Hash([]byte("TEST-LEGACY")))
			nonce := s.e.state.StateDB.GetNonce(linker)
			tx := s.e.apply(&linker, stockS2bLinkVerifyCallData(t, s.linker, "registerClass", page, ph, pvh), 8_000_000)
			if size == 0 || size > 256 {
				stockS2bLinkVerifyAssertRevert(t, tx, "S2bLinkError(uint256)", 2)
			} else {
				if tx.result == nil || !tx.result.Failed() || !bytes.Equal(tx.result.ReturnData, payload) {
					t.Fatalf("size%d result=%+v", size, tx.result)
				}
			}
			if len(tx.logs) != 0 || s.e.state.StateDB.GetNonce(linker) != nonce || len(s.e.state.StateDB.GetCode(crypto.CreateAddress(linker, nonce))) != 0 {
				t.Fatal("partial issuance")
			}
		})
	}
}
