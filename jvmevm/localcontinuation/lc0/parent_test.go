package lc0

import (
	"bytes"
	"context"
	"encoding/binary"
	"encoding/hex"
	"fmt"
	monolith "github.com/ethereum/go-ethereum/jvmevm"
	"math/big"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

// Parent-created well-encoded but type-invalid checkpoint mutations are TEST
// inputs to the read-only validator, never execution metadata or trusted heads.
func TestLC0ParentTypedHeapAndStaticValidation(t *testing.T) {
	src := `public class LC0ParentTyped {LC0ParentTyped self;boolean z;byte b;short s;char c;static LC0ParentTyped saved;static String[] strings;static boolean flag;public static int run(){LC0ParentTyped h=new LC0ParentTyped();h.self=h;h.z=true;h.b=-1;h.s=-2;h.c='x';saved=h;strings=new String[]{"s"};flag=true;return h.b+h.s+h.c+(h.self==h?1:0);}}`
	raw := [][]byte{lc0VerifyCompileTrusted(t, map[string]string{"LC0ParentTyped.java": src}, []string{"LC0ParentTyped"})["LC0ParentTyped"]}
	e := lc0VerifyNewEnv(t)
	defer e.close()
	s, blob, c := e.start(lc0VerifyOwner, lc0VerifyInstance("parent-typed"), raw, "LC0ParentTyped", "run", nil, 4096, 4096, lc0VerifyOrdinaryGas)
	lc0VerifyAssertSuccess(t, s, blob, c)
	if s.Result != 118 {
		t.Fatal(s)
	}
	cp, err := lc0VerifyDecodeCheckpoint(blob)
	if err != nil {
		t.Fatal(err)
	}
	var holder, str lc0VerifyHeapRecord
	var refs lc0VerifyHeapRecord
	for _, r := range cp.Machine.Heap {
		if r.Object && r.Class == 0 && r.Count == 5 {
			holder = r
		}
		if r.Object && r.Class != 0 && r.Count == 2 {
			str = r
		}
		if !r.Object && r.Rank == 1 && r.Metadata.Cmp(big.NewInt(256)) >= 0 {
			refs = r
		}
	}
	if holder.Handle == 0 || str.Handle == 0 || refs.Handle == 0 {
		t.Fatalf("records not found holder=%+v string=%+v refs=%+v", holder, str, refs)
	}
	putTagged := func(b []byte, kind, bits uint64) {
		v := new(big.Int).Lsh(new(big.Int).SetUint64(kind), 64)
		v.Or(v, new(big.Int).SetUint64(bits))
		v.FillBytes(b[:32])
	}
	cases := []struct {
		name   string
		offset int
		mutate func([]byte)
	}{
		{"object-ref-class", holder.CellOffsets[0], func(b []byte) { putTagged(b, 2, uint64(str.Handle)) }},
		{"object-boolean", holder.CellOffsets[1], func(b []byte) { putTagged(b, 1, 2) }},
		{"object-byte", holder.CellOffsets[2], func(b []byte) { putTagged(b, 1, 128) }},
		{"object-short", holder.CellOffsets[3], func(b []byte) { putTagged(b, 1, 32768) }},
		{"object-char", holder.CellOffsets[4], func(b []byte) { putTagged(b, 1, 65536) }},
		{"reference-array-class", refs.CellOffsets[0], func(b []byte) { binary.BigEndian.PutUint64(b, uint64(holder.Handle)) }},
		{"static-ref-class", cp.Machine.StaticValueOffsets[0][0], func(b []byte) { putTagged(b, 2, uint64(str.Handle)) }},
		{"static-boolean", cp.Machine.StaticValueOffsets[0][2], func(b []byte) { putTagged(b, 1, 2) }},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			bad := lc0VerifyMutateRehash(t, blob, tc.offset, tc.mutate)
			r := lc0VerifyValidate(e, raw, bad, lc0VerifyOrdinaryGas)
			if r.err == nil {
				t.Fatalf("type-invalid checkpoint accepted, output=%x", r.output)
			}
			if _, _, ok := lc0VerifyStateError(r.output); !ok {
				t.Fatalf("not checkpoint State error: %x %v", r.output, r.err)
			}
		})
	}
}

func TestLC0ParentExactCheckpointLimit(t *testing.T) {
	for _, n := range []int{65464, 65465, 65466} {
		t.Run(fmt.Sprint(n), func(t *testing.T) {
			source := fmt.Sprintf("public class LCcap {public static int r(){long[] a=new long[65536];long[] b=new long[%d];return a.length+b.length;}}", n)
			raw := [][]byte{lc0VerifyCompileTrusted(t, map[string]string{"LCcap.java": source}, []string{"LCcap"})["LCcap"]}
			e := lc0VerifyNewEnv(t)
			defer e.close()
			id := lc0VerifyInstance(fmt.Sprintf("parent-cap-%d", n))
			s, blob, c := e.start(lc0VerifyOwner, id, raw, "LCcap", "r", nil, 4096, 4096, lc0VerifyBoundaryGas)
			if n == 65466 {
				lc0VerifyAssertState(t, c, 1, 0)
				if e.head(id) != (lc0VerifyHead{}) {
					t.Fatal("oversize child registered")
				}
				return
			}
			lc0VerifyAssertSuccess(t, s, blob, c)
			want := 1048576 + (n-65465)*8
			if len(blob) != want || s.Result != int32(65536+n) {
				t.Fatalf("bytes%d want%d result%d", len(blob), want, s.Result)
			}
			validated := lc0VerifyValidate(e, raw, blob, lc0VerifyBoundaryGas)
			if validated.err != nil {
				t.Fatalf("boundary validate: %v %x", validated.err, validated.output)
			}
			t.Logf("checkpoint bytes%d gas%d result%d", len(blob), lc0VerifyBoundaryGas-c.left, s.Result)
		})
	}
}

func TestLC0ParentCheckpointOverflowRollbackAndLargeRetry(t *testing.T) {
	source := `public class LCcap {public static int r(){long[] a=new long[65536];long[] b=new long[65465];return a.length+b.length;}}`
	raw := [][]byte{lc0VerifyCompileTrusted(t, map[string]string{"LCcap.java": source}, []string{"LCcap"})["LCcap"]}
	e := lc0VerifyNewEnv(t)
	defer e.close()
	id := lc0VerifyInstance("parent-large-resume")
	s, blob, c := e.start(lc0VerifyOwner, id, raw, "LCcap", "r", nil, 3, 4096, lc0VerifyBoundaryGas)
	lc0VerifyAssertSuccess(t, s, blob, c)
	before := e.head(id)
	_, _, failed := e.resume(lc0VerifyOwner, id, s.Epoch, lc0VerifySliceRoot(s), raw, blob, 3, 4096, lc0VerifyBoundaryGas)
	lc0VerifyAssertState(t, failed, 1, 0)
	lc0VerifyAssertHeadEqual(t, e.head(id), before)
	done, out, retry := e.resume(lc0VerifyOwner, id, s.Epoch, lc0VerifySliceRoot(s), raw, blob, 4096, 4096, lc0VerifyBoundaryGas)
	lc0VerifyAssertSuccess(t, done, out, retry)
	control, controlBlob, cc := e.start(lc0VerifyOwner, lc0VerifyInstance("parent-large-control"), raw, "LCcap", "r", nil, 4096, 4096, lc0VerifyBoundaryGas)
	lc0VerifyAssertSuccess(t, control, controlBlob, cc)
	if done.Result != 131001 || len(out) != 1048576 || done.MachineStateRoot != control.MachineStateRoot || done.TotalJvmSteps != control.TotalJvmSteps {
		t.Fatal("large retry/control mismatch")
	}
	t.Logf("parentBytes=%d finalBytes=%d startGas=%d retryGas=%d", len(blob), len(out), lc0VerifyBoundaryGas-c.left, lc0VerifyBoundaryGas-retry.left)
}

func TestLC0ParentTrimpathBinaryReopen(t *testing.T) {
	raw := lc0VerifyReadClass(t, "LC0CallLoop")
	dir := t.TempDir()
	source := filepath.Join(dir, "main.go")
	binary := filepath.Join(dir, "lc0-child")
	store := filepath.Join(dir, "store")
	text := fmt.Sprintf(`package main
 import("encoding/hex";"fmt";"os";"github.com/ethereum/go-ethereum/common";"github.com/ethereum/go-ethereum/crypto";l "github.com/ethereum/go-ethereum/jvmevm/localcontinuation/lc0")
 func main(){raw,e:=hex.DecodeString(%q);if e!=nil{panic(e)};s,e:=l.Open(os.Args[1],common.HexToAddress("0x123456"));if e!=nil{panic(e)};defer s.Close();id:=crypto.Keccak256Hash([]byte("relocatable"));
 if os.Args[2]=="start"{r,e:=s.Start(id,[][]byte{raw},"LC0CallLoop","run",[]int32{5},1,4096,100000000);if e!=nil{panic(e)};fmt.Println("start",r.Slice.Epoch);return};
 h,e:=s.Head(id);if e!=nil{panic(e)};for n:=0;n<256;n++{b,e:=s.ReadCheckpoint(h.CheckpointRoot);if e!=nil{panic(e)};r,e:=s.Resume(id,h.Epoch,h.CheckpointRoot,[][]byte{raw},b,7,4096,100000000);if e!=nil{panic(e)};if r.Slice.Lifecycle==2{fmt.Println("done",r.Slice.Result);return};h,e=s.Head(id);if e!=nil{panic(e)}};panic("slice cap")}
 `, hex.EncodeToString(raw))
	if err := os.WriteFile(source, []byte(text), 0600); err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()
	if out, err := exec.CommandContext(ctx, "go", "build", "-trimpath", "-o", binary, source).CombinedOutput(); err != nil {
		t.Fatalf("trimpath build %v %s", err, out)
	}
	cwd := filepath.Join(dir, "empty-cwd")
	if err := os.Mkdir(cwd, 0700); err != nil {
		t.Fatal(err)
	}
	for _, tc := range []struct{ mode, want string }{{"start", "start 1"}, {"resume", "done 15"}} {
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		cmd := exec.CommandContext(ctx, binary, store, tc.mode)
		cmd.Dir = cwd
		out, err := cmd.CombinedOutput()
		cancel()
		if err != nil || strings.TrimSpace(string(out)) != tc.want {
			t.Fatalf("relocated %s: %v %s", tc.mode, err, out)
		}
	}
}

func TestLC0ParentSpecialReceiverLocalMayBeOverwritten(t *testing.T) {
	src := `public class LCthis {private int m(){int x=5;return x;}public static int run(){return new LCthis().m();}public static void main(String[] args){System.out.print(run());}}`
	raw := lc0VerifyCompileTrusted(t, map[string]string{"LCthis.java": src}, []string{"LCthis"})["LCthis"]
	old := []byte{0x08, 0x3c, 0x1b, 0xac}
	if bytes.Count(raw, old) != 1 {
		t.Fatal("expected exact private Code pattern")
	}
	raw = bytes.Replace(raw, old, []byte{0x08, 0x3b, 0x1a, 0xac}, 1) // valid istore_0 / iload_0, not receiver-preserving
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "LCthis.class"), raw, 0600); err != nil {
		t.Fatal(err)
	}
	for _, java := range []string{"/usr/lib/jvm/java-8-openjdk/bin/java", "java"} {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		out, err := exec.CommandContext(ctx, java, "-Xverify:all", "-cp", dir, "LCthis").CombinedOutput()
		cancel()
		if err != nil || string(out) != "5" {
			t.Fatalf("oracle %s %v %s", java, err, out)
		}
	}
	r, err := monolith.Run(raw, "run", nil, 100_000_000)
	if err != nil || r.Value != 5 {
		t.Fatalf("base %+v %v", r, err)
	}
	e := lc0VerifyNewEnv(t)
	defer e.close()
	id := lc0VerifyInstance("parent-overwritten-this")
	s, b, c := e.start(lc0VerifyOwner, id, [][]byte{raw}, "LCthis", "run", nil, 1, 4096, lc0VerifyOrdinaryGas)
	lc0VerifyAssertSuccess(t, s, b, c)
	for n := 0; s.Lifecycle == lc0VerifyRunnable && n < 64; n++ {
		s, b, c = e.resume(lc0VerifyOwner, id, s.Epoch, lc0VerifySliceRoot(s), [][]byte{raw}, b, 1, 4096, lc0VerifyOrdinaryGas)
		lc0VerifyAssertSuccess(t, s, b, c)
	}
	if s.Lifecycle != lc0VerifyReturned || s.Result != 5 {
		t.Fatal(s)
	}
}
