package di0

import (
	"bytes"
	"compress/flate"
	"encoding/binary"
	"hash/crc32"
	"math/big"
	"reflect"
	"testing"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/as0"
	runtimeassets "github.com/ethereum/go-ethereum/jvmevm/artifactstore/di0/runtime"
)

type di0HarnessZIP struct {
	raw, plain, compressed []byte
	name                   []byte
}

func di0HarnessPut16(b *bytes.Buffer, v uint16) { _ = binary.Write(b, binary.LittleEndian, v) }
func di0HarnessPut32(b *bytes.Buffer, v uint32) { _ = binary.Write(b, binary.LittleEndian, v) }

// Fixture construction and flate are trusted test-oracle code only. Production
// transport never parses, inflates, or supplies archive offsets to the EVM.
func di0HarnessZIP1(t testing.TB, name, plain []byte, method uint16) di0HarnessZIP {
	t.Helper()
	payload := append([]byte(nil), plain...)
	if method == 8 {
		var compressed bytes.Buffer
		w, err := flate.NewWriter(&compressed, flate.DefaultCompression)
		if err != nil {
			t.Fatal(err)
		}
		if _, err = w.Write(plain); err != nil {
			t.Fatal(err)
		}
		if err = w.Close(); err != nil {
			t.Fatal(err)
		}
		payload = compressed.Bytes()
	}
	return di0HarnessZIPPayload(name, plain, payload, method)
}

func di0HarnessZIPPayload(name, plain, payload []byte, method uint16) di0HarnessZIP {
	return di0HarnessZIPPayloadPrefix(0, name, plain, payload, method)
}
func di0HarnessZIPPayloadPrefix(prefix int, name, plain, payload []byte, method uint16) di0HarnessZIP {
	crc := crc32.ChecksumIEEE(plain)
	var out bytes.Buffer
	out.Write(bytes.Repeat([]byte{'X'}, prefix))
	di0HarnessPut32(&out, 0x04034b50)
	di0HarnessPut16(&out, 20)
	di0HarnessPut16(&out, 0x800)
	di0HarnessPut16(&out, method)
	di0HarnessPut16(&out, 0)
	di0HarnessPut16(&out, 0)
	di0HarnessPut32(&out, crc)
	di0HarnessPut32(&out, uint32(len(payload)))
	di0HarnessPut32(&out, uint32(len(plain)))
	di0HarnessPut16(&out, uint16(len(name)))
	di0HarnessPut16(&out, 0)
	out.Write(name)
	out.Write(payload)
	cd := uint32(out.Len())
	di0HarnessPut32(&out, 0x02014b50)
	di0HarnessPut16(&out, 0x0314)
	di0HarnessPut16(&out, 20)
	di0HarnessPut16(&out, 0x800)
	di0HarnessPut16(&out, method)
	di0HarnessPut16(&out, 0)
	di0HarnessPut16(&out, 0)
	di0HarnessPut32(&out, crc)
	di0HarnessPut32(&out, uint32(len(payload)))
	di0HarnessPut32(&out, uint32(len(plain)))
	di0HarnessPut16(&out, uint16(len(name)))
	di0HarnessPut16(&out, 0)
	di0HarnessPut16(&out, 0)
	di0HarnessPut16(&out, 0)
	di0HarnessPut16(&out, 0)
	di0HarnessPut32(&out, 0)
	di0HarnessPut32(&out, uint32(prefix))
	out.Write(name)
	eocd := uint32(out.Len())
	di0HarnessPut32(&out, 0x06054b50)
	di0HarnessPut16(&out, 0)
	di0HarnessPut16(&out, 0)
	di0HarnessPut16(&out, 1)
	di0HarnessPut16(&out, 1)
	di0HarnessPut32(&out, eocd-cd)
	di0HarnessPut32(&out, cd)
	di0HarnessPut16(&out, 0)
	return di0HarnessZIP{raw: out.Bytes(), plain: append([]byte(nil), plain...), compressed: append([]byte(nil), payload...), name: append([]byte(nil), name...)}
}

type di0HarnessBitWriter struct {
	b []byte
	n uint8
}

func (w *di0HarnessBitWriter) bits(v uint, n uint8) {
	for i := uint8(0); i < n; i++ {
		if w.n == 0 {
			w.b = append(w.b, 0)
		}
		if (v>>i)&1 != 0 {
			w.b[len(w.b)-1] |= 1 << w.n
		}
		w.n = (w.n + 1) & 7
	}
}
func (w *di0HarnessBitWriter) code(v uint, n uint8) {
	for i := uint8(0); i < n; i++ {
		w.bits((v>>uint(n-1-i))&1, 1)
	}
}
func di0HarnessBalanced(n int) []uint8 {
	x := []uint8{0}
	for len(x) < n {
		at := 0
		for i := range x {
			if x[i] < x[at] {
				at = i
			}
		}
		d := x[at] + 1
		x[at] = d
		x = append(x, d)
	}
	return x
}
func di0HarnessCanonical(lens []uint8) map[int][2]uint {
	counts := [16]uint{}
	for _, n := range lens {
		if n > 0 {
			counts[n]++
		}
	}
	next := [16]uint{}
	code := uint(0)
	for n := 1; n <= 15; n++ {
		code = (code + counts[n-1]) << 1
		next[n] = code
	}
	out := make(map[int][2]uint)
	for symbol, n := range lens {
		if n > 0 {
			out[symbol] = [2]uint{next[n], uint(n)}
			next[n]++
		}
	}
	return out
}
func di0HarnessEmptyDynamic(blocks int) []byte {
	w := di0HarnessBitWriter{}
	ll := make([]uint8, 286)
	ll[256] = 1
	dl := di0HarnessBalanced(30)
	cl := di0HarnessBalanced(19)
	order := []int{16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15}
	cm := di0HarnessCanonical(cl)
	for block := 0; block < blocks; block++ {
		final := uint(0)
		if block+1 == blocks {
			final = 1
		}
		w.bits(final, 1)
		w.bits(2, 2)
		w.bits(uint(len(ll)-257), 5)
		w.bits(uint(len(dl)-1), 5)
		w.bits(15, 4)
		for _, s := range order {
			w.bits(uint(cl[s]), 3)
		}
		put := func(s int) { x := cm[s]; w.code(x[0], uint8(x[1])) }
		for _, x := range ll {
			put(int(x))
		}
		for _, x := range dl {
			put(int(x))
		}
		lm := di0HarnessCanonical(ll)
		x := lm[256]
		w.code(x[0], uint8(x[1]))
	}
	return w.b
}

func di0HarnessABI(t testing.TB, names []string, values ...interface{}) []byte {
	t.Helper()
	var args abi.Arguments
	for _, name := range names {
		typ, err := abi.NewType(name, "", nil)
		if err != nil {
			t.Fatal(err)
		}
		args = append(args, abi.Argument{Type: typ})
	}
	out, err := args.Pack(values...)
	if err != nil {
		t.Fatal(err)
	}
	return out
}
func di0HarnessPageCommitment(t testing.TB, controller common.Address, index uint32, raw []byte) common.Hash {
	return crypto.Keccak256Hash(di0HarnessABI(t, []string{"bytes32", "address", "uint32", "uint32", "bytes32"}, crypto.Keccak256Hash([]byte("MC-AS0/page/v1")), controller, index, uint32(len(raw)), crypto.Keccak256Hash(raw)))
}
func di0HarnessUpload(t testing.TB, s *Session, raw []byte) {
	t.Helper()
	creation, err := s.Creation()
	if err != nil {
		t.Fatal(err)
	}
	head, err := s.Head(OrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	for at := int(head.AS0.Cursor); at < len(raw); at += int(as0.PageSize) {
		end := at + int(as0.PageSize)
		if end > len(raw) {
			end = len(raw)
		}
		page := append([]byte(nil), raw[at:end]...)
		op, err := s.Append(uint32(at), page, di0HarnessPageCommitment(t, creation.Controller, uint32(at)/as0.PageSize, page), OrdinaryGas)
		if err != nil || op.GasUsed == 0 || op.StateRoot == (common.Hash{}) || len(op.Logs) != 1 || len(op.RevertData) != 0 {
			t.Fatalf("append op=%+v err=%v", op, err)
		}
	}
}
func di0HarnessFinishIndex(t testing.TB, s *Session) Head {
	t.Helper()
	h, err := s.Head(OrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	op, err := s.Seal(h.AS0.Cursor, h.AS0.ChainCommitment, OrdinaryGas)
	if err != nil || op.StateRoot == (common.Hash{}) {
		t.Fatalf("seal op=%+v err=%v", op, err)
	}
	h, err = s.Head(OrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	op, err = s.CreateIndex(h.AS0.ContentCommitment, OrdinaryGas)
	if err != nil || op.CreatedAddress != crypto.CreateAddress(h.AS0.Owner, 1) {
		t.Fatalf("create index op=%+v err=%v", op, err)
	}
	if op, err = s.DiscoverIndex(OrdinaryGas); err != nil || op.StateRoot == (common.Hash{}) {
		t.Fatalf("discover op=%+v err=%v", op, err)
	}
	for {
		h, err = s.Head(OrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
		if h.Index.NextEntry == h.Index.Count {
			break
		}
		op, err = s.ScanIndex(h.Index.NextEntry, h.Index.CDCursor, h.Index.Rolling, 64, OrdinaryGas)
		if err != nil || op.StateRoot == (common.Hash{}) {
			t.Fatalf("scan op=%+v err=%v", op, err)
		}
	}
	h, err = s.Head(OrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	op, err = s.FinishIndex(h.Index.Count, h.Index.CDCursor, h.Index.Rolling, OrdinaryGas)
	if err != nil || op.StateRoot == (common.Hash{}) {
		t.Fatalf("finish op=%+v err=%v", op, err)
	}
	h, err = s.Head(OrdinaryGas)
	if err != nil || h.Index.Phase != 2 || h.Index.FinalRoot == (common.Hash{}) {
		t.Fatalf("final index=%+v err=%v", h.Index, err)
	}
	return h
}
func di0HarnessCreate(t testing.TB, s *Session, name []byte) Head {
	t.Helper()
	h, err := s.Head(OrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	op, err := s.CreateDecoder(h.Index.FinalRoot, name, OrdinaryGas)
	if err != nil || op.CreatedAddress != crypto.CreateAddress(h.AS0.Owner, 2) || op.StateRoot == (common.Hash{}) || len(op.Logs) != 0 {
		t.Fatalf("create decoder op=%+v err=%v", op, err)
	}
	h, err = s.Head(OrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	return h
}
func di0HarnessDecode(t testing.TB, s *Session, units uint16) Head {
	t.Helper()
	for {
		h, err := s.Head(OrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
		if h.Decoder.Phase != 1 {
			return h
		}
		before := h.Decoder.Work
		op, err := s.Step(before, units, OrdinaryGas)
		if err != nil || op.StateRoot == (common.Hash{}) || op.GasUsed == 0 || len(op.Logs) != 0 {
			t.Fatalf("step work=%d op=%+v err=%v", before, op, err)
		}
		after, err := s.Head(OrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
		if after.Decoder.Work <= before || after.Decoder.Work > before+uint32(units) {
			t.Fatalf("units is not a positive upper bound: before=%d after=%d units=%d", before, after.Decoder.Work, units)
		}
	}
}
func di0HarnessPublish(t testing.TB, s *Session) Head {
	t.Helper()
	for {
		h, err := s.Head(OrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
		if h.Decoder.Phase == 4 {
			return h
		}
		op, err := s.Publish(h.Decoder.PublishedPages, h.Decoder.PublicationRolling, 1, OrdinaryGas)
		if err != nil || op.StateRoot == (common.Hash{}) || op.GasUsed == 0 || len(op.Logs) != 0 {
			t.Fatalf("publish op=%+v err=%v", op, err)
		}
	}
}
func di0HarnessPrepared(t testing.TB, z di0HarnessZIP, owner common.Address) (*Session, Head) {
	t.Helper()
	s, err := NewMemory(owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatal(err)
	}
	di0HarnessUpload(t, s, z.raw)
	di0HarnessFinishIndex(t, s)
	return s, di0HarnessCreate(t, s, z.name)
}
func di0HarnessError(t testing.TB, op Operation, want uint64) {
	t.Helper()
	selector := crypto.Keccak256([]byte("DI0Error(uint256)"))[:4]
	if len(op.RevertData) != 36 || !bytes.Equal(op.RevertData[:4], selector) || new(big.Int).SetBytes(op.RevertData[4:]).Uint64() != want {
		t.Fatalf("want DI0Error(%d), got 0x%x", want, op.RevertData)
	}
}
func di0HarnessHeadNoGas(h Head) Head {
	h.GasUsed = 0
	h.AS0.GasUsed = 0
	h.Index.GasUsed = 0
	h.Decoder.GasUsed = 0
	return h
}

func TestDI0HarnessPinnedArtifactAndDefensiveAPI(t *testing.T) {
	a, raw, init, run, err := validateArtifact(runtimeassets.Artifact())
	if err != nil {
		t.Fatal(err)
	}
	if len(a.Methods) != 33 || len(a.Events) != 0 || len(a.Errors) != 1 || len(init) != 17216 || len(init)+384 != 17600 || len(run) != 14978 || digest(raw) == "" || crypto.Keccak256Hash(run) != common.HexToHash(runtimeKeccak256) {
		t.Fatal("runtime shape or pins differ")
	}
	one, _ := Runtime()
	two, _ := Runtime()
	one[0] ^= 0xff
	if bytes.Equal(one, two) {
		t.Fatal("Runtime aliases embedded bytes")
	}
	one, _ = InitCode()
	two, _ = InitCode()
	one[0] ^= 0xff
	if bytes.Equal(one, two) {
		t.Fatal("InitCode aliases embedded bytes")
	}
	if _, err := NewMemory(common.Address{}, 1); err == nil {
		t.Fatal("zero owner accepted")
	}
	for _, gas := range []uint64{0, MaxGas + 1} {
		if checkGas(gas) == nil {
			t.Fatalf("gas %d accepted", gas)
		}
	}
}

func TestDI0HarnessMemoryStoredAndDeflateLifecycle(t *testing.T) {
	cases := []di0HarnessZIP{di0HarnessZIP1(t, []byte("stored.txt"), []byte("opaque stored bytes"), 0), di0HarnessZIP1(t, []byte("compressed.bin"), bytes.Repeat([]byte("dynamic-compatible-pattern-"), 40), 8)}
	for i, z := range cases {
		t.Run(string(z.name), func(t *testing.T) {
			s, _ := di0HarnessPrepared(t, z, common.BytesToAddress([]byte{0xd1, byte(i + 1)}))
			defer s.Close()
			input, err := s.InputRead(0, uint32(len(z.raw)), OrdinaryGas)
			if err != nil || !bytes.Equal(input.Bytes, z.raw) {
				t.Fatalf("input read err=%v", err)
			}
			inputPage, err := s.InputPage(0, OrdinaryGas)
			if err != nil || inputPage.Address == (common.Address{}) || inputPage.CodeHash == (common.Hash{}) || inputPage.Commitment == (common.Hash{}) {
				t.Fatalf("input page=%+v err=%v", inputPage, err)
			}
			entry, err := s.Entry(0, OrdinaryGas)
			if err != nil || !bytes.Equal(entry.Name, z.name) {
				t.Fatalf("entry=%+v err=%v", entry, err)
			}
			lookup, err := s.Lookup(z.name, OrdinaryGas)
			if err != nil || !lookup.Found || lookup.Index != 0 || lookup.PackedRecord != entry.PackedRecord {
				t.Fatalf("lookup=%+v err=%v", lookup, err)
			}
			di0HarnessDecode(t, s, 128)
			final := di0HarnessPublish(t, s)
			if final.Decoder.FinalRoot == (common.Hash{}) || final.StateRoot == (common.Hash{}) {
				t.Fatal("missing resource or trie root")
			}
			out, err := s.Read(0, uint32(len(z.plain)), OrdinaryGas)
			if err != nil || !bytes.Equal(out.Bytes, z.plain) {
				t.Fatalf("output mismatch err=%v", err)
			}
			page, err := s.Page(0, OrdinaryGas)
			if err != nil || page.Length != uint32(len(z.plain)) {
				t.Fatalf("page=%+v err=%v", page, err)
			}
			out.Bytes[0] ^= 0xff
			again, _ := s.Read(0, uint32(len(z.plain)), OrdinaryGas)
			if bytes.Equal(out.Bytes, again.Bytes) {
				t.Fatal("read result aliases state")
			}
		})
	}
}

func TestDI0HarnessCASFailureAndFirstActionOOGRollback(t *testing.T) {
	z := di0HarnessZIP1(t, []byte("x"), bytes.Repeat([]byte{0x51}, 256), 0)
	s, h := di0HarnessPrepared(t, z, common.HexToAddress("0xd10003"))
	defer s.Close()
	before := di0HarnessHeadNoGas(h)
	op, err := s.Step(h.Decoder.Work+1, 1, OrdinaryGas)
	if err == nil || op.StateRoot != (common.Hash{}) || op.CreatedAddress != (common.Address{}) || len(op.Logs) != 0 {
		t.Fatalf("stale step op=%+v err=%v", op, err)
	}
	di0HarnessError(t, op, 7)
	after, _ := s.Head(OrdinaryGas)
	if !reflect.DeepEqual(before, di0HarnessHeadNoGas(after)) {
		t.Fatal("failed CAS changed head")
	}
	oog, err := s.Step(h.Decoder.Work, 1, 70_000)
	if err == nil || oog.GasUsed != 70_000 || oog.StateRoot != (common.Hash{}) || len(oog.Logs) != 0 || len(oog.RevertData) != 0 {
		t.Fatalf("first-action OOG op=%+v err=%v", oog, err)
	}
	after, _ = s.Head(OrdinaryGas)
	if !reflect.DeepEqual(before, di0HarnessHeadNoGas(after)) {
		t.Fatal("OOG changed published state")
	}
	if _, err = s.Step(h.Decoder.Work, 1, OrdinaryGas); err != nil {
		t.Fatalf("same-state retry failed: %v", err)
	}
}
