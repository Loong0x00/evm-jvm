package zi0

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"hash/crc32"
	"math/big"
	"reflect"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/common"
	evmruntime "github.com/ethereum/go-ethereum/core/vm/runtime"
	"github.com/ethereum/go-ethereum/crypto"
)

func zi0HarnessPrepared(t testing.TB, owner common.Address, z zi0HarnessZIP) (*Session, Head) {
	t.Helper()
	session, gas := zi0HarnessOpenAndUpload(t, owner, z, "")
	zi0HarnessSealCreate(t, session, &gas)
	head, err := session.Head(OrdinaryGas)
	if err != nil {
		session.Close()
		t.Fatal(err)
	}
	return session, head
}
func zi0HarnessWantDiscoverError(t testing.TB, z zi0HarnessZIP, want uint64) uint64 {
	t.Helper()
	session, _ := zi0HarnessPrepared(t, common.BytesToAddress([]byte{0x51, byte(want), byte(len(z.raw))}), z)
	defer session.Close()
	before, _ := session.Head(OrdinaryGas)
	op, err := session.Discover(BoundaryGas)
	if err == nil || zi0HarnessErrorCode(t, op) != want || op.GasUsed == 0 || op.StateRoot != (common.Hash{}) || len(op.Logs) != 0 {
		t.Fatalf("discover want ZI0Error(%d): op=%+v err=%v", want, op, err)
	}
	after, _ := session.Head(OrdinaryGas)
	if !reflect.DeepEqual(zi0HarnessHeadWithoutGas(before), zi0HarnessHeadWithoutGas(after)) {
		t.Fatalf("failed discover changed head: before=%+v after=%+v", before, after)
	}
	return op.GasUsed
}
func zi0HarnessWantScanError(t testing.TB, z zi0HarnessZIP, units uint16, want uint64) uint64 {
	t.Helper()
	session, _ := zi0HarnessPrepared(t, common.BytesToAddress([]byte{0x52, byte(want), byte(len(z.raw))}), z)
	defer session.Close()
	if _, err := session.Discover(BoundaryGas); err != nil {
		t.Fatalf("positive discover failed before scan oracle: %v", err)
	}
	before, _ := session.Head(OrdinaryGas)
	op, err := session.Scan(before.Index.NextEntry, before.Index.CDCursor, before.Index.Rolling, units, BoundaryGas)
	if err == nil || zi0HarnessErrorCode(t, op) != want || op.GasUsed == 0 || op.StateRoot != (common.Hash{}) || len(op.Logs) != 0 {
		t.Fatalf("scan want ZI0Error(%d): op=%+v err=%v", want, op, err)
	}
	after, _ := session.Head(OrdinaryGas)
	if !reflect.DeepEqual(zi0HarnessHeadWithoutGas(before), zi0HarnessHeadWithoutGas(after)) {
		t.Fatalf("failed scan changed head: before=%+v after=%+v", before, after)
	}
	return op.GasUsed
}

func TestZI0HarnessEOCDPrefixAmbiguityEmptyZIP64AndTailPolicy(t *testing.T) {
	short := zi0HarnessZIP{raw: bytes.Repeat([]byte{'x'}, 21)}
	zi0HarnessWantDiscoverError(t, short, 5)

	prefix := zi0HarnessBuildZIP([]zi0HarnessEnt{{name: []byte("p"), data: []byte{1}, method: 0, descriptor: -1}}, 31, nil, nil)
	session, _ := zi0HarnessPrepared(t, common.HexToAddress("0x5a4930710001"), prefix)
	if _, err := session.Discover(OrdinaryGas); err != nil {
		t.Fatalf("opaque prefix rejected: %v", err)
	}
	session.Close()

	empty := zi0HarnessBuildZIP(nil, 0, nil, nil)
	session, gas := zi0HarnessOpenAndUpload(t, common.HexToAddress("0x5a4930710002"), empty, "")
	defer session.Close()
	zi0HarnessSealCreate(t, session, &gas)
	final := zi0HarnessIndex(t, session, 1, &gas)
	if final.Index.Count != 0 || final.Index.CDSize != 0 || final.Index.FinalRoot == (common.Hash{}) {
		t.Fatalf("empty ZIP final=%+v", final)
	}

	locator := zi0HarnessBuildZIP(nil, 20, nil, nil)
	binary.LittleEndian.PutUint32(locator.raw[0:4], 0x07064b50)
	zi0HarnessWantDiscoverError(t, locator, 9)

	ambiguous := zi0HarnessBuildZIP(nil, 0, nil, bytes.Repeat([]byte{0}, 22))
	inner := ambiguous.raw[len(ambiguous.raw)-22:]
	binary.LittleEndian.PutUint32(inner[0:4], 0x06054b50)
	binary.LittleEndian.PutUint32(inner[16:20], uint32(len(ambiguous.raw)-22))
	zi0HarnessWantDiscoverError(t, ambiguous, 6)

	// Maximum classic comment/tail with dense exact-ending candidate signatures.
	dense := zi0HarnessBuildZIP(nil, 0, nil, bytes.Repeat([]byte{0}, 65535))
	for at := 22; at+22 <= len(dense.raw); at += 22 {
		binary.LittleEndian.PutUint32(dense.raw[at:at+4], 0x06054b50)
		binary.LittleEndian.PutUint32(dense.raw[at+16:at+20], uint32(at))
		binary.LittleEndian.PutUint16(dense.raw[at+20:at+22], uint16(len(dense.raw)-at-22))
	}
	gasUsed := zi0HarnessWantDiscoverError(t, dense, 6)
	t.Logf("dense-eocd-tail bytes=%d discoverGas=%d", len(dense.raw), gasUsed)
}

func TestZI0HarnessFramingFlagsMethodsExtrasDescriptorsAndGeometry(t *testing.T) {
	base := func() zi0HarnessZIP {
		return zi0HarnessBuildZIP([]zi0HarnessEnt{{name: []byte("one"), data: []byte("payload"), method: 8, descriptor: -1}}, 0, nil, nil)
	}
	cases := []struct {
		name string
		want uint64
		make func() zi0HarnessZIP
	}{
		{"cen-signature", 12, func() zi0HarnessZIP { z := base(); z.raw[z.cd] = 0; return z }},
		{"cen-name-zero", 13, func() zi0HarnessZIP { z := base(); binary.LittleEndian.PutUint16(z.raw[z.cd+28:], 0); return z }},
		{"unsupported-flags", 14, func() zi0HarnessZIP { z := base(); binary.LittleEndian.PutUint16(z.raw[z.cd+8:], 1); return z }},
		{"zip64-size-sentinel", 14, func() zi0HarnessZIP {
			z := base()
			binary.LittleEndian.PutUint32(z.raw[z.cd+20:], ^uint32(0))
			return z
		}},
		{"unsupported-method", 15, func() zi0HarnessZIP { z := base(); binary.LittleEndian.PutUint16(z.raw[z.cd+10:], 99); return z }},
		{"stored-size-mismatch", 15, func() zi0HarnessZIP {
			z := zi0HarnessBuildZIP([]zi0HarnessEnt{{name: []byte("x"), data: []byte{1}, method: 0, descriptor: -1}}, 0, nil, nil)
			binary.LittleEndian.PutUint32(z.raw[z.cd+20:], 2)
			return z
		}},
		{"central-range", 16, func() zi0HarnessZIP { z := base(); binary.LittleEndian.PutUint16(z.raw[z.cd+28:], 100); return z }},
		{"cen-extra-framing", 17, func() zi0HarnessZIP {
			return zi0HarnessBuildZIP([]zi0HarnessEnt{{name: []byte("x"), data: []byte{1}, method: 0, descriptor: -1, extra: []byte{2, 0, 1, 0}}}, 0, nil, nil)
		}},
		{"zip64-cen-extra", 17, func() zi0HarnessZIP {
			return zi0HarnessBuildZIP([]zi0HarnessEnt{{name: []byte("x"), data: []byte{1}, method: 0, descriptor: -1, extra: []byte{1, 0, 0, 0}}}, 0, nil, nil)
		}},
		{"loc-signature", 20, func() zi0HarnessZIP { z := base(); z.raw[z.locals[0]] = 0; return z }},
		{"loc-length", 21, func() zi0HarnessZIP { z := base(); binary.LittleEndian.PutUint16(z.raw[z.locals[0]+26:], 4); return z }},
		{"loc-name", 22, func() zi0HarnessZIP { z := base(); z.raw[z.locals[0]+30] ^= 1; return z }},
		{"loc-extra", 22, func() zi0HarnessZIP {
			z := zi0HarnessBuildZIP([]zi0HarnessEnt{{name: []byte("x"), data: []byte{1}, method: 0, descriptor: -1, extra: []byte{2, 0, 0, 0}}}, 0, nil, nil)
			binary.LittleEndian.PutUint16(z.raw[z.locals[0]+31:], 1)
			return z
		}},
		{"data-end", 23, func() zi0HarnessZIP { z := base(); binary.LittleEndian.PutUint32(z.raw[z.cd+20:], z.cd); return z }},
		{"loc-crc", 24, func() zi0HarnessZIP { z := base(); z.raw[z.locals[0]+14] ^= 1; return z }},
		{"descriptor", 25, func() zi0HarnessZIP {
			z := zi0HarnessBuildZIP([]zi0HarnessEnt{{name: []byte("x"), data: []byte("payload"), method: 8, descriptor: 1}}, 0, nil, nil)
			z.raw[z.dataAt[0]+uint32(len(zi0HarnessDeflate([]byte("payload"))))+4] ^= 1
			return z
		}},
		{"descriptor-end", 26, func() zi0HarnessZIP {
			z := zi0HarnessBuildZIP([]zi0HarnessEnt{{name: []byte("x"), data: []byte("payload"), method: 8, descriptor: 1}}, 0, nil, nil)
			actual := uint32(len(zi0HarnessDeflate([]byte("payload"))))
			binary.LittleEndian.PutUint32(z.raw[z.cd+20:], actual+5)
			return z
		}},
		{"local-order", 27, func() zi0HarnessZIP {
			entries := []zi0HarnessEnt{{name: []byte("a"), data: []byte{1}, method: 0, descriptor: -1}, {name: []byte("b"), data: []byte{2}, method: 0, descriptor: -1}}
			return zi0HarnessBuildZIP(entries, 0, []int{1, 0}, nil)
		}},
		{"duplicate", 18, func() zi0HarnessZIP {
			return zi0HarnessBuildZIP([]zi0HarnessEnt{{name: []byte("same"), data: []byte{1}, method: 0, descriptor: -1}, {name: []byte("same"), data: []byte{2}, method: 0, descriptor: -1}}, 0, nil, nil)
		}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) { zi0HarnessWantScanError(t, tc.make(), 64, tc.want) })
	}

	valid := []zi0HarnessEnt{
		{name: []byte("stored"), data: []byte("abc"), method: 0, descriptor: -1},
		{name: []byte("deflate-bits"), data: bytes.Repeat([]byte{7}, 100), method: 8, flags: 6, descriptor: 0},
		{name: []byte("signed-descriptor"), data: bytes.Repeat([]byte{8}, 100), method: 8, descriptor: 1},
	}
	z := zi0HarnessBuildZIP(valid, 9, nil, nil)
	session, gas := zi0HarnessOpenAndUpload(t, common.HexToAddress("0x5a4930710003"), z, "")
	defer session.Close()
	zi0HarnessSealCreate(t, session, &gas)
	final := zi0HarnessIndex(t, session, 64, &gas)
	if final.Index.Count != 3 {
		t.Fatal("valid method/descriptor controls did not finish")
	}
}

func zi0HarnessInitialRoot(t testing.TB, head Head) common.Hash {
	t.Helper()
	return crypto.Keccak256Hash(zi0HarnessABIEncode(t,
		[]string{"bytes32", "address", "address", "address", "bytes32", "bytes32", "uint32", "uint32", "uint32", "uint32", "uint32"},
		crypto.Keccak256Hash([]byte("MC-ZI0/index/v1")), head.Index.Address, head.Index.Owner, head.Index.Store, as0CodeHash, head.Index.Content,
		head.Index.Length, head.Index.EOCD, head.Index.CDOffset, head.Index.CDSize, head.Index.Count))
}
func zi0HarnessPacked(z zi0HarnessZIP, index int) (common.Hash, uint32, uint32, uint32, uint32, uint16, uint16, uint16, uint32, uint32, uint32) {
	entry := z.entries[index]
	payload := entry.data
	if entry.method == 8 {
		payload = zi0HarnessDeflate(entry.data)
	}
	flags := uint16(0x800) | entry.flags
	descriptor := uint64(0)
	if entry.descriptor >= 0 {
		flags |= 8
		descriptor = uint64(entry.descriptor + 1)
	}
	comp, plain := uint32(len(payload)), uint32(len(entry.data))
	local, dataStart := z.locals[index], z.dataAt[index]
	dataEnd := dataStart + comp
	recordEnd := dataEnd
	if descriptor == 1 {
		recordEnd += 12
	} else if descriptor == 2 {
		recordEnd += 16
	}
	namePos := z.centralNameAt[index]
	crc := crc32.ChecksumIEEE(entry.data)
	value := new(big.Int)
	put := func(v uint64, shift uint) { value.Or(value, new(big.Int).Lsh(new(big.Int).SetUint64(v), shift)) }
	put(uint64(namePos), 0)
	put(uint64(local), 25)
	put(uint64(dataStart), 50)
	put(uint64(comp), 75)
	put(uint64(plain), 100)
	put(uint64(crc), 132)
	put(uint64(len(entry.name)), 164)
	put(uint64(flags), 173)
	put(uint64(entry.method), 189)
	put(descriptor, 193)
	return common.BigToHash(value), local, dataStart, dataEnd, recordEnd, uint16(len(entry.name)), flags, entry.method, crc, comp, plain
}
func zi0HarnessStepRoot(t testing.TB, previous common.Hash, z zi0HarnessZIP, index int) common.Hash {
	t.Helper()
	_, local, dataStart, dataEnd, recordEnd, nameLen, flags, method, crc, comp, plain := zi0HarnessPacked(z, index)
	return crypto.Keccak256Hash(zi0HarnessABIEncode(t,
		[]string{"bytes32", "bytes32", "uint32", "bytes32", "uint16", "uint16", "uint16", "uint32", "uint32", "uint32", "uint32", "uint32", "uint32", "uint32", "uint32"},
		crypto.Keccak256Hash([]byte("MC-ZI0/entry/v1")), previous, uint32(index), crypto.Keccak256Hash(z.entries[index].name), nameLen, flags, method,
		crc, comp, plain, local, dataStart, dataEnd, recordEnd, z.centralRecordEnd[index]))
}

func TestZI0HarnessIndependentPackedRecordRootAndQ1Q64Equality(t *testing.T) {
	z := zi0HarnessSmallZIP()
	owner := common.HexToAddress("0x5a4930711001")
	session, _ := zi0HarnessPrepared(t, owner, z)
	defer session.Close()
	if _, err := session.Discover(OrdinaryGas); err != nil {
		t.Fatal(err)
	}
	head, _ := session.Head(OrdinaryGas)
	root := zi0HarnessInitialRoot(t, head)
	if head.Index.Rolling != root {
		t.Fatalf("initial rolling=%s want=%s", head.Index.Rolling, root)
	}
	for i := 0; i < len(z.entries); i++ {
		if _, err := session.Scan(head.Index.NextEntry, head.Index.CDCursor, head.Index.Rolling, 1, OrdinaryGas); err != nil {
			t.Fatal(err)
		}
		head, _ = session.Head(OrdinaryGas)
		root = zi0HarnessStepRoot(t, root, z, i)
		if head.Index.Rolling != root {
			t.Fatalf("step %d rolling=%s want=%s", i, head.Index.Rolling, root)
		}
	}
	if _, err := session.Finish(head.Index.Count, head.Index.CDCursor, head.Index.Rolling, OrdinaryGas); err != nil {
		t.Fatal(err)
	}
	for i := range z.entries {
		entry, err := session.Entry(uint32(i), OrdinaryGas)
		want, _, _, _, _, _, _, _, _, _, _ := zi0HarnessPacked(z, i)
		if err != nil || entry.PackedRecord != want {
			t.Fatalf("packed %d=%s want=%s err=%v", i, entry.PackedRecord, want, err)
		}
	}

	entries := make([]zi0HarnessEnt, 128)
	for i := range entries {
		entries[i] = zi0HarnessEnt{name: []byte(fmt.Sprintf("q/%03d", i)), data: []byte{byte(i)}, method: uint16((i % 2) * 8), descriptor: -1}
	}
	large := zi0HarnessBuildZIP(entries, 0, nil, nil)
	var roots [2]common.Hash
	var scans [2]int
	for n, units := range []uint16{1, 64} {
		s, gas := zi0HarnessOpenAndUpload(t, common.HexToAddress("0x5a4930711002"), large, "")
		zi0HarnessSealCreate(t, s, &gas)
		final := zi0HarnessIndex(t, s, units, &gas)
		roots[n], scans[n] = final.Index.FinalRoot, gas.scans
		s.Close()
	}
	if roots[0] != roots[1] || scans != [2]int{128, 2} {
		t.Fatalf("q split changed root/scans: roots=%v scans=%v", roots, scans)
	}
	t.Logf("q1/q64 root=%s scans=%v", roots[0], scans)
}

func TestZI0HarnessOpaqueNamesAndActualFullByteGuard(t *testing.T) {
	names := [][]byte{
		{0, 'a', '/', '.', 0xff}, []byte("a/../b"), []byte("a//b"), []byte("A/b"),
		{0xc0, 0x80, '/', 0xed, 0xa0, 0x80}, []byte("./x"), []byte("x/"),
	}
	entries := make([]zi0HarnessEnt, len(names))
	for i := range names {
		entries[i] = zi0HarnessEnt{name: names[i], data: []byte{byte(i)}, method: 0, descriptor: -1}
	}
	z := zi0HarnessBuildZIP(entries, 0, nil, nil)
	session, gas := zi0HarnessOpenAndUpload(t, common.HexToAddress("0x5a4930712001"), z, "")
	defer session.Close()
	zi0HarnessSealCreate(t, session, &gas)
	zi0HarnessIndex(t, session, 64, &gas)
	for i, name := range names {
		result, err := session.Lookup(name, OrdinaryGas)
		if err != nil || !result.Found || result.Index != uint32(i) {
			t.Fatalf("opaque name %x lookup=%+v err=%v", name, result, err)
		}
	}
	for _, changed := range [][]byte{[]byte("a/b"), []byte("a/./b"), []byte("a\\b"), []byte("A/B")} {
		result, err := session.Lookup(changed, OrdinaryGas)
		if err != nil || result.Found {
			t.Fatalf("normalized-looking miss %x=%+v err=%v", changed, result, err)
		}
	}

	// TEST-only isolated state mutation redirects a different name hash to the
	// first occupied bucket. The EVM must reread and compare all name bytes.
	probe := []byte("not-the-first-name")
	nameHash := crypto.Keccak256Hash(probe)
	slot := crypto.Keccak256Hash(zi0HarnessABIEncode(t, []string{"bytes32", "uint256"}, nameHash, big.NewInt(8)))
	old := session.state.GetState(session.indexAddress, slot)
	session.state.SetState(session.indexAddress, slot, common.BigToHash(big.NewInt(1)))
	callData, _ := session.zi0ABI.Pack("lookup", probe)
	out, _, callErr := evmruntime.Call(session.indexAddress, callData, session.config(session.state.Copy(), OrdinaryGas))
	if callErr == nil || len(out) != 36 || !bytes.Equal(out[:4], crypto.Keccak256([]byte("ZI0Error(uint256)"))[:4]) || new(big.Int).SetBytes(out[4:]).Uint64() != 19 {
		t.Fatalf("full-byte bucket guard output=0x%x err=%v", out, callErr)
	}
	session.state.SetState(session.indexAddress, slot, old)
	original, err := session.Lookup(names[0], OrdinaryGas)
	if err != nil || !original.Found || original.Index != 0 {
		t.Fatalf("original lookup not restored: %+v %v", original, err)
	}
}

func TestZI0HarnessMaxTLVAndAtomicDuplicateAcrossBatch(t *testing.T) {
	extra := make([]byte, 1024)
	binary.LittleEndian.PutUint16(extra, 0x1234)
	binary.LittleEndian.PutUint16(extra[2:], 1020)
	for i := 4; i < len(extra); i++ {
		extra[i] = byte(i)
	}
	entries := make([]zi0HarnessEnt, 64)
	for i := range entries {
		base := fmt.Sprintf("max/%02d/", i)
		entries[i] = zi0HarnessEnt{name: []byte(base + strings.Repeat("n", 256-len(base))), data: []byte{byte(i)}, method: uint16((i % 2) * 8), descriptor: -1, extra: append([]byte(nil), extra...), comment: bytes.Repeat([]byte{byte(i)}, 1024)}
	}
	z := zi0HarnessBuildZIP(entries, 0, nil, nil)
	session, gas := zi0HarnessOpenAndUpload(t, common.HexToAddress("0x5a4930713001"), z, "")
	defer session.Close()
	zi0HarnessSealCreate(t, session, &gas)
	final := zi0HarnessIndex(t, session, 64, &gas)
	if final.Index.Count != 64 || gas.scans != 1 {
		t.Fatal("simultaneous max TLV/name/comment did not finish in q64")
	}
	t.Logf("max-tlv archive=%d cd=%d scanGas=%d", len(z.raw), z.eocd-z.cd, gas.scanMax)

	duplicate := zi0HarnessBuildZIP([]zi0HarnessEnt{{name: []byte("a"), data: []byte{1}, method: 0, descriptor: -1}, {name: []byte("b"), data: []byte{2}, method: 0, descriptor: -1}, {name: []byte("b"), data: []byte{3}, method: 0, descriptor: -1}}, 0, nil, nil)
	s, _ := zi0HarnessPrepared(t, common.HexToAddress("0x5a4930713002"), duplicate)
	defer s.Close()
	if _, err := s.Discover(OrdinaryGas); err != nil {
		t.Fatal(err)
	}
	head, _ := s.Head(OrdinaryGas)
	if _, err := s.Scan(head.Index.NextEntry, head.Index.CDCursor, head.Index.Rolling, 1, OrdinaryGas); err != nil {
		t.Fatal(err)
	}
	before, _ := s.Head(OrdinaryGas)
	op, err := s.Scan(before.Index.NextEntry, before.Index.CDCursor, before.Index.Rolling, 2, OrdinaryGas)
	if err == nil || zi0HarnessErrorCode(t, op) != 18 {
		t.Fatalf("duplicate batch op=%+v err=%v", op, err)
	}
	after, _ := s.Head(OrdinaryGas)
	if !reflect.DeepEqual(zi0HarnessHeadWithoutGas(before), zi0HarnessHeadWithoutGas(after)) {
		t.Fatal("duplicate batch published a prefix")
	}
	miss, err := s.Lookup([]byte("b"), OrdinaryGas)
	if err == nil || !strings.Contains(err.Error(), "revert_data") || miss.Found {
		t.Fatal("staging lookup unexpectedly published duplicate prefix")
	}
}
