package lc0

import (
	"encoding/binary"
	"fmt"
	"math/big"
	"testing"
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
