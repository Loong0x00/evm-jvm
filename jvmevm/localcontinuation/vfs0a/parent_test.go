package vfs0a

// These preparation probes deliberately use the ACCEPTED IOE0 runtime with
// candidate library images supplied as raw guest classes. They exercise Java
// Code only, never a VFS native or VFS0a's new constructor/native identity gates.
// Passing them is not acceptance of the production VFS0a runtime.
import (
	"context"
	"crypto/sha256"
	"encoding/hex"
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
	"github.com/ethereum/go-ethereum/jvmevm/localcontinuation/ioe0"
)

var vfsParentImagePins = map[string]string{
	"java/lang/AutoCloseable":  "cafa160ddd47f90df802399cbd3ea0f4a62dc0d382c77fde7917b8b84fa51ea8",
	"java/io/Closeable":        "79fae4d62aee6a6f46bd7483265bb3a19ba9fcc89c3f6dc8a14d5814a10ed86f",
	"java/io/Flushable":        "b5679864201f2fe3eb8e7fad6a7121790281ad1ca87391d928ca9c1bc9277513",
	"java/io/File":             "aee6861b45213674f41d257a87a0508b3b9ca1d900ec995234bd51d129b83bc4",
	"java/io/InputStream":      "224fd0acae8f99ca75c2cba79902dca8408fe91fa839599a96377a31a687ba72",
	"java/io/OutputStream":     "2698b53831772935d798d8739ffe77b786f343e30f7bc5d7b1d1ae5c8efeb4c2",
	"java/io/FileInputStream":  "cdda6fb532785d7e43d535bea0225e0bd5e920e28b39353c54f13e3d41ef9a65",
	"java/io/FileOutputStream": "50aa63fa914989dada682851a65c9ce0c5400fd0f8e4e52246553ee2fc084315",
}

func vfsParentImage(t *testing.T, name string) []byte {
	t.Helper()
	_, source, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("locate parent test")
	}
	p := filepath.Join(filepath.Dir(source), "../../runtime/local/vfs0a/bootstrap", name+".class.hex")
	text, err := os.ReadFile(p)
	if err != nil {
		t.Fatal(err)
	}
	raw, err := hex.DecodeString(strings.TrimSpace(string(text)))
	if err != nil {
		t.Fatal(err)
	}
	got := sha256.Sum256(raw)
	if hex.EncodeToString(got[:]) != vfsParentImagePins[name] {
		t.Fatalf("%s pin changed: %x", name, got)
	}
	if len(raw) < 8 || hex.EncodeToString(raw[:8]) != "cafebabe00000034" {
		t.Fatalf("%s is not classfile52", name)
	}
	return raw
}

func TestVFS0aParentFrozenEightImages(t *testing.T) {
	total := 0
	for name := range vfsParentImagePins {
		total += len(vfsParentImage(t, name))
	}
	if total != 6050 {
		t.Fatalf("eight images total %d", total)
	}
}

// Host execution below is a trusted TEST oracle, never a production Java or
// filesystem evaluator. Only the root class bytes are passed to the EVM.
func vfsParentCompileOracle(t *testing.T, class, source string, want int32, setup ...string) []byte {
	t.Helper()
	d := t.TempDir()
	paths := []string{filepath.Join(d, class+".java"), filepath.Join(d, "OracleMain.java")}
	sources := []string{source, "public class OracleMain {public static void main(String[] a)throws Exception{" + strings.Join(setup, "\n") + "System.out.println(" + class + ".run());}}"}
	for i, p := range paths {
		if err := os.WriteFile(p, []byte(sources[i]), 0600); err != nil {
			t.Fatal(err)
		}
	}
	run := func(bin string, args ...string) string {
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		cmd := exec.CommandContext(ctx, bin, args...)
		cmd.Dir = d
		for _, e := range os.Environ() {
			if !strings.HasPrefix(e, "LC_ALL=") && !strings.HasPrefix(e, "LANG=") {
				cmd.Env = append(cmd.Env, e)
			}
		}
		cmd.Env = append(cmd.Env, "LC_ALL=C", "LANG=C")
		var stderr strings.Builder
		cmd.Stderr = &stderr
		out, err := cmd.Output()
		if err != nil {
			t.Fatalf("%s %v: %v\n%s\n%s", bin, args, err, out, stderr.String())
		}
		return strings.TrimSpace(string(out))
	}
	args := append([]string{"-J-Xmx256m", "-source", "8", "-target", "8", "-g:none", "-d", d}, paths...)
	run("/usr/lib/jvm/java-8-openjdk/bin/javac", args...)
	for _, java := range []string{"/usr/lib/jvm/java-8-openjdk/bin/java", "java"} {
		text := run(java, "-Xmx64m", "-cp", d, "OracleMain")
		n, err := strconv.ParseInt(text, 10, 32)
		if err != nil || int32(n) != want {
			t.Fatalf("oracle %s=%q, want %d (%v)", java, text, want, err)
		}
	}
	raw, err := os.ReadFile(filepath.Join(d, class+".class"))
	if err != nil {
		t.Fatal(err)
	}
	return raw
}

func vfsParentIOE0Code(t *testing.T, class string, raw [][]byte, want int32, quantum uint64, internal uint32) ioe0.SliceResult {
	t.Helper()
	s, err := ioe0.NewMemory(common.HexToAddress("0x7e01"))
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()
	id := crypto.Keccak256Hash([]byte(fmt.Sprintf("parent-wrapper-code:%s:%d", class, quantum)))
	const gas = uint64(100_000_000)
	r, err := s.Start(id, raw, class, "run", nil, quantum, internal, gas)
	calls := 1
	var maxGas uint64
	for {
		if err != nil {
			t.Fatalf("q%d call%d: %v revert=%x", quantum, calls, err, r.RevertData)
		}
		if r.GasUsed > maxGas {
			maxGas = r.GasUsed
		}
		if r.Slice.TotalJvmSteps+r.Slice.TotalInternalSteps > 4096 {
			t.Fatal("IOE0 ordinary total-unit limit")
		}
		if r.Slice.Lifecycle != 1 {
			break
		}
		// Retain the OLD IOE0 256-slice budget: the VFS0a4096 allowance
		// does not apply when using this accepted dependency runtime.
		if calls >= 256 {
			t.Fatal("IOE0 ordinary 256-slice limit")
		}
		r, err = s.Resume(id, r.Slice.Epoch, r.Slice.CheckpointRoot, raw, r.Checkpoint, quantum, internal, gas)
		calls++
	}
	if r.Slice.Lifecycle != 2 || r.Slice.Result != want {
		t.Fatalf("q%d result=%+v, want %d", quantum, r.Slice, want)
	}
	if quantum == 4096 && internal == 4096 && calls != 1 {
		t.Fatalf("expected genuine one-call Code control, got %d calls", calls)
	}
	t.Logf("IOE0 Code-only q%d/internal%d calls=%d jvm=%d internal=%d maxGas=%d checkpoint=%d machine=%s", quantum, internal, calls, r.Slice.TotalJvmSteps, r.Slice.TotalInternalSteps, maxGas, len(r.Checkpoint), r.Slice.MachineStateRoot)
	return r.Slice
}

func TestVFS0aParentFileCodeOnAcceptedIOE0(t *testing.T) {
	source := `import java.io.File; public class PFileCode {
 public static int run(){File a=new File("a//b/");File b=new File("a/b");Comparable c=a;int v=0;
 if(a instanceof Comparable)v|=1;if(c.compareTo(b)==0)v|=2;
 if(a.compareTo(new File("b"))<0)v|=4;
 try{c.compareTo("x");}catch(ClassCastException e){v|=8;}return v;}}
 `
	raw := [][]byte{vfsParentCompileOracle(t, "PFileCode", source, 15), vfsParentImage(t, "java/io/File")}
	a := vfsParentIOE0Code(t, "PFileCode", raw, 15, 4096, 4096)
	b := vfsParentIOE0Code(t, "PFileCode", raw, 15, 7, 1)
	if a.MachineStateRoot != b.MachineStateRoot || a.TotalJvmSteps != b.TotalJvmSteps || a.TotalInternalSteps != b.TotalInternalSteps {
		t.Fatal("File Code continuation mismatch")
	}
}

func TestVFS0aParentInputStreamCodeOnAcceptedIOE0(t *testing.T) {
	source := `import java.io.*; public class PInputCode extends InputStream {
 int n; public int read()throws IOException{if(n++==0)return 65;throw new IOException("next");}
 public static int run()throws IOException{PInputCode r=new PInputCode();byte[] b=new byte[3];int v=0;
 if(r.read(b)==1&&b[0]==65)v|=1;
 try{r.read(b);}catch(IOException e){if(e.getMessage().equals("next"))v|=2;}
 r.close();try{r.read(null,-1,-1);}catch(NullPointerException e){v|=4;}
 if(r.read(b,3,0)==0)v|=8;
 try{r.read(b,4,0);}catch(IndexOutOfBoundsException e){v|=16;}return v;}}
 `
	raw := [][]byte{vfsParentCompileOracle(t, "PInputCode", source, 31), vfsParentImage(t, "java/io/InputStream"), vfsParentImage(t, "java/io/Closeable"), vfsParentImage(t, "java/lang/AutoCloseable")}
	a := vfsParentIOE0Code(t, "PInputCode", raw, 31, 4096, 4096)
	b := vfsParentIOE0Code(t, "PInputCode", raw, 31, 7, 1)
	if a.MachineStateRoot != b.MachineStateRoot || a.TotalJvmSteps != b.TotalJvmSteps || a.TotalInternalSteps != b.TotalInternalSteps {
		t.Fatal("InputStream Code continuation mismatch")
	}
}

// Host-only expectations for newly found path-traversal gaps. These are NOT
// passing VFS EVM tests. The root Code can be reused against the completed VFS
// runtime with equivalent raw seeds; setup executes only in the trusted oracle.
func TestVFS0aParentPathTraversalHostOracles(t *testing.T) {
	setup := `try(java.io.FileOutputStream f=new java.io.FileOutputStream("file")){f.write(120);}
 try(java.io.FileOutputStream f=new java.io.FileOutputStream("seed")){f.write(121);}`
	cases := []struct{ path, message string }{
		{"file/child", "file/child (Not a directory)"},
		{"missing/../seed", "missing/../seed (No such file or directory)"},
		{"file/../seed", "file/../seed (Not a directory)"},
	}
	for i, c := range cases {
		t.Run(c.path, func(t *testing.T) {
			class := fmt.Sprintf("PPath%d", i)
			source := fmt.Sprintf(`import java.io.*;public class %s {
    public static int run()throws IOException{File f=new File(%q);int v=f.exists()?0:1;
    try(FileInputStream in=new FileInputStream(f)){return -1;}
    catch(FileNotFoundException e){if(e.getMessage().equals(%q))v|=2;}return v;}}`, class, c.path, c.message)
			vfsParentCompileOracle(t, class, source, 3, setup)
		})
	}
	source := `import java.io.*;public class PPathMkdir {
 public static int run(){int v=0;
 if(!new File("missing/../onea").mkdir())v|=1;
 if(new File("missing/../manya").mkdirs())v|=2;
 if(!new File("file/../oneb").mkdir())v|=4;
 if(new File("file/../manyb").mkdirs())v|=8;return v;}}`
	// Fresh directory names on every JVM run, because the oracle helper reuses
	// its owned temporary CWD across JVM8 and21.
	cleanup := `new java.io.File("onea").delete();new java.io.File("manya").delete();
 new java.io.File("oneb").delete();new java.io.File("manyb").delete();`
	vfsParentCompileOracle(t, "PPathMkdir", source, 15, setup, cleanup)
}
