package zi0

import (
	"bytes"
	"compress/flate"
	"encoding/binary"
	"encoding/json"
	"errors"
	"fmt"
	"hash/crc32"
	"math/big"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/as0"
	zi0assets "github.com/ethereum/go-ethereum/jvmevm/artifactstore/zi0/runtime"
)

type zi0HarnessEnt struct {
	name           []byte
	data           []byte
	method         uint16
	descriptor     int // -1 none, 0 unsigned twelve-byte, 1 signed sixteen-byte
	flags          uint16
	extra, comment []byte
}
type zi0HarnessZIP struct {
	raw              []byte
	cd, eocd         uint32
	locals, dataAt   []uint32
	central          [][]byte
	centralNameAt    []uint32
	centralRecordEnd []uint32
	entries          []zi0HarnessEnt
}
type zi0HarnessGas struct {
	createAS0, appendSum, appendMax, seal, createIndex uint64
	discover, scanSum, scanMax, finish, views          uint64
	appends, scans, publications                       int
}

func zi0HarnessPut16(b *bytes.Buffer, value uint16) { _ = binary.Write(b, binary.LittleEndian, value) }
func zi0HarnessPut32(b *bytes.Buffer, value uint32) { _ = binary.Write(b, binary.LittleEndian, value) }
func zi0HarnessDeflate(raw []byte) []byte {
	var b bytes.Buffer
	w, err := flate.NewWriter(&b, flate.DefaultCompression)
	if err != nil {
		panic(err)
	}
	_, _ = w.Write(raw)
	_ = w.Close()
	return b.Bytes()
}

// zi0HarnessBuildZIP is trusted test-fixture construction only. Production Go
// never parses a ZIP or supplies a name/offset catalogue to the EVM.
func zi0HarnessBuildZIP(entries []zi0HarnessEnt, prefix int, order []int, archiveComment []byte) zi0HarnessZIP {
	var out bytes.Buffer
	out.Write(bytes.Repeat([]byte{'X'}, prefix))
	z := zi0HarnessZIP{entries: append([]zi0HarnessEnt(nil), entries...)}
	for _, entry := range entries {
		z.locals = append(z.locals, uint32(out.Len()))
		name := entry.name
		payload := entry.data
		if entry.method == 8 {
			payload = zi0HarnessDeflate(entry.data)
		}
		flags := uint16(0x800) | entry.flags
		if entry.descriptor >= 0 {
			flags |= 8
		}
		crc := crc32.ChecksumIEEE(entry.data)
		zi0HarnessPut32(&out, 0x04034b50)
		zi0HarnessPut16(&out, 20)
		zi0HarnessPut16(&out, flags)
		zi0HarnessPut16(&out, entry.method)
		zi0HarnessPut16(&out, 0)
		zi0HarnessPut16(&out, 0)
		if entry.descriptor >= 0 {
			zi0HarnessPut32(&out, 0)
			zi0HarnessPut32(&out, 0)
			zi0HarnessPut32(&out, 0)
		} else {
			zi0HarnessPut32(&out, crc)
			zi0HarnessPut32(&out, uint32(len(payload)))
			zi0HarnessPut32(&out, uint32(len(entry.data)))
		}
		zi0HarnessPut16(&out, uint16(len(name)))
		zi0HarnessPut16(&out, uint16(len(entry.extra)))
		out.Write(name)
		out.Write(entry.extra)
		z.dataAt = append(z.dataAt, uint32(out.Len()))
		out.Write(payload)
		if entry.descriptor >= 0 {
			if entry.descriptor == 1 {
				zi0HarnessPut32(&out, 0x08074b50)
			}
			zi0HarnessPut32(&out, crc)
			zi0HarnessPut32(&out, uint32(len(payload)))
			zi0HarnessPut32(&out, uint32(len(entry.data)))
		}
		var central bytes.Buffer
		zi0HarnessPut32(&central, 0x02014b50)
		zi0HarnessPut16(&central, 0x0314)
		zi0HarnessPut16(&central, 20)
		zi0HarnessPut16(&central, flags)
		zi0HarnessPut16(&central, entry.method)
		zi0HarnessPut16(&central, 0)
		zi0HarnessPut16(&central, 0)
		zi0HarnessPut32(&central, crc)
		zi0HarnessPut32(&central, uint32(len(payload)))
		zi0HarnessPut32(&central, uint32(len(entry.data)))
		zi0HarnessPut16(&central, uint16(len(name)))
		zi0HarnessPut16(&central, uint16(len(entry.extra)))
		zi0HarnessPut16(&central, uint16(len(entry.comment)))
		zi0HarnessPut16(&central, 0)
		zi0HarnessPut16(&central, 0)
		zi0HarnessPut32(&central, 0)
		zi0HarnessPut32(&central, z.locals[len(z.locals)-1])
		central.Write(name)
		central.Write(entry.extra)
		central.Write(entry.comment)
		z.central = append(z.central, central.Bytes())
	}
	z.cd = uint32(out.Len())
	if order == nil {
		order = make([]int, len(entries))
		for i := range order {
			order[i] = i
		}
	}
	for _, index := range order {
		z.centralNameAt = append(z.centralNameAt, uint32(out.Len()+46))
		out.Write(z.central[index])
		z.centralRecordEnd = append(z.centralRecordEnd, uint32(out.Len()))
	}
	z.eocd = uint32(out.Len())
	zi0HarnessPut32(&out, 0x06054b50)
	zi0HarnessPut16(&out, 0)
	zi0HarnessPut16(&out, 0)
	zi0HarnessPut16(&out, uint16(len(entries)))
	zi0HarnessPut16(&out, uint16(len(entries)))
	zi0HarnessPut32(&out, z.eocd-z.cd)
	zi0HarnessPut32(&out, z.cd)
	zi0HarnessPut16(&out, uint16(len(archiveComment)))
	out.Write(archiveComment)
	z.raw = out.Bytes()
	return z
}

func zi0HarnessABIEncode(t testing.TB, typeNames []string, values ...interface{}) []byte {
	t.Helper()
	var args abi.Arguments
	for _, name := range typeNames {
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
func zi0HarnessPageCommitment(t testing.TB, controller common.Address, index uint32, raw []byte) common.Hash {
	t.Helper()
	return crypto.Keccak256Hash(zi0HarnessABIEncode(t,
		[]string{"bytes32", "address", "uint32", "uint32", "bytes32"},
		crypto.Keccak256Hash([]byte("MC-AS0/page/v1")), controller, index, uint32(len(raw)), crypto.Keccak256Hash(raw)))
}
func zi0HarnessErrorCode(t testing.TB, op Operation) uint64 {
	t.Helper()
	if len(op.RevertData) != 36 || !bytes.Equal(op.RevertData[:4], crypto.Keccak256([]byte("ZI0Error(uint256)"))[:4]) {
		t.Fatalf("not exact ZI0Error: 0x%x", op.RevertData)
	}
	return new(big.Int).SetBytes(op.RevertData[4:]).Uint64()
}

func zi0HarnessUpload(t testing.TB, session *Session, raw []byte, begin, end int, gas *zi0HarnessGas) {
	t.Helper()
	creation, err := session.Creation()
	if err != nil {
		t.Fatal(err)
	}
	if end < 0 || end > len(raw) {
		end = len(raw)
	}
	for at := begin; at < end; at += int(as0.PageSize) {
		stop := at + int(as0.PageSize)
		if stop > end {
			stop = end
		}
		page := append([]byte(nil), raw[at:stop]...)
		op, err := session.Append(uint32(at), page, zi0HarnessPageCommitment(t, creation.Controller, uint32(at)/as0.PageSize, page), OrdinaryGas)
		if err != nil || op.GasUsed == 0 || op.StateRoot == (common.Hash{}) || len(op.Logs) != 1 || len(op.RevertData) != 0 {
			t.Fatalf("append at %d: op=%+v err=%v", at, op, err)
		}
		gas.appendSum += op.GasUsed
		gas.appends++
		gas.publications++
		if op.GasUsed > gas.appendMax {
			gas.appendMax = op.GasUsed
		}
		if session.directory != "" {
			m, err := readManifest(filepath.Join(session.directory, manifestName))
			if err != nil || m.StateRoot != op.StateRoot {
				t.Fatalf("append at %d was not individually published: manifest=%+v err=%v", at, m, err)
			}
		}
	}
}

func zi0HarnessSealCreate(t testing.TB, session *Session, gas *zi0HarnessGas) Head {
	t.Helper()
	head, err := session.Head(OrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	gas.views += head.GasUsed
	op, err := session.Seal(head.AS0.Cursor, head.AS0.ChainCommitment, OrdinaryGas)
	if err != nil || op.StateRoot == (common.Hash{}) || len(op.Logs) != 1 {
		t.Fatalf("seal: op=%+v err=%v", op, err)
	}
	gas.seal, gas.publications = op.GasUsed, gas.publications+1
	head, err = session.Head(OrdinaryGas)
	if err != nil || !head.AS0.Sealed {
		t.Fatalf("sealed head=%+v err=%v", head, err)
	}
	gas.views += head.GasUsed
	op, err = session.CreateIndex(head.AS0.ContentCommitment, OrdinaryGas)
	if err != nil || op.CreatedAddress != crypto.CreateAddress(head.AS0.Owner, 1) || op.StateRoot == (common.Hash{}) || len(op.Logs) != 0 {
		t.Fatalf("create index: op=%+v err=%v", op, err)
	}
	gas.createIndex, gas.publications = op.GasUsed, gas.publications+1
	head, err = session.Head(OrdinaryGas)
	if err != nil || head.Index.Phase != 0 || head.Index.Address != op.CreatedAddress {
		t.Fatalf("bound head=%+v err=%v", head, err)
	}
	gas.views += head.GasUsed
	return head
}

func zi0HarnessIndex(t testing.TB, session *Session, units uint16, gas *zi0HarnessGas) Head {
	t.Helper()
	op, err := session.Discover(OrdinaryGas)
	if err != nil || op.StateRoot == (common.Hash{}) || len(op.Logs) != 0 {
		t.Fatalf("discover: op=%+v err=%v", op, err)
	}
	gas.discover, gas.publications = op.GasUsed, gas.publications+1
	for {
		head, err := session.Head(OrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
		gas.views += head.GasUsed
		if head.Index.NextEntry == head.Index.Count {
			break
		}
		op, err = session.Scan(head.Index.NextEntry, head.Index.CDCursor, head.Index.Rolling, units, BoundaryGas)
		if err != nil || op.StateRoot == (common.Hash{}) || len(op.Logs) != 0 {
			t.Fatalf("scan %d/%d: op=%+v err=%v", head.Index.NextEntry, head.Index.Count, op, err)
		}
		gas.scanSum += op.GasUsed
		gas.scans++
		gas.publications++
		if op.GasUsed > gas.scanMax {
			gas.scanMax = op.GasUsed
		}
		if session.directory != "" {
			m, err := readManifest(filepath.Join(session.directory, manifestName))
			if err != nil || m.StateRoot != op.StateRoot {
				t.Fatalf("scan root was not individually published: manifest=%+v err=%v", m, err)
			}
		}
	}
	head, err := session.Head(OrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	gas.views += head.GasUsed
	op, err = session.Finish(head.Index.Count, head.Index.CDCursor, head.Index.Rolling, OrdinaryGas)
	if err != nil || op.StateRoot == (common.Hash{}) || len(op.Logs) != 0 {
		t.Fatalf("finish: op=%+v err=%v", op, err)
	}
	gas.finish, gas.publications = op.GasUsed, gas.publications+1
	head, err = session.Head(OrdinaryGas)
	if err != nil || head.Index.Phase != 2 || head.Index.FinalRoot == (common.Hash{}) || head.Index.FinalRoot != head.Index.Rolling {
		t.Fatalf("final head=%+v err=%v", head, err)
	}
	gas.views += head.GasUsed
	return head
}

func zi0HarnessOpenAndUpload(t testing.TB, owner common.Address, z zi0HarnessZIP, directory string) (*Session, zi0HarnessGas) {
	t.Helper()
	var session *Session
	var err error
	if directory == "" {
		session, err = NewMemory(owner, uint32(len(z.raw)))
	} else {
		session, err = Open(directory, owner, uint32(len(z.raw)))
	}
	if err != nil {
		t.Fatal(err)
	}
	creation, err := session.Creation()
	if err != nil || !creation.Performed || creation.Controller != crypto.CreateAddress(owner, 0) || creation.GasUsed == 0 {
		t.Fatalf("AS0 creation=%+v err=%v", creation, err)
	}
	gas := zi0HarnessGas{createAS0: creation.GasUsed, publications: 1}
	zi0HarnessUpload(t, session, z.raw, 0, len(z.raw), &gas)
	return session, gas
}

func zi0HarnessSmallZIP() zi0HarnessZIP {
	return zi0HarnessBuildZIP([]zi0HarnessEnt{
		{name: []byte("first.txt"), data: []byte("stored"), method: 0, descriptor: -1},
		{name: []byte("dir/second.bin"), data: bytes.Repeat([]byte{0x5a}, 91), method: 8, descriptor: 1},
	}, 7, nil, []byte("comment"))
}

func zi0HarnessHeadWithoutGas(h Head) Head {
	h.GasUsed, h.AS0.GasUsed, h.Index.GasUsed = 0, 0, 0
	return h
}

func TestZI0HarnessPinnedCombinedArtifactAndExactABI(t *testing.T) {
	raw := zi0assets.Artifact()
	a, abiRaw, init, runtimeCode, err := validateArtifact(raw)
	if err != nil {
		t.Fatal(err)
	}
	if len(raw) != 49837 || len(init) != 9873 || len(init)+64 != 9937 || len(runtimeCode) != 9177 || digest(raw) != artifactSHA256 || digest(init) != initSHA256 || digest(runtimeCode) != runtimeSHA256 || crypto.Keccak256Hash(runtimeCode) != common.HexToHash(runtimeKeccak256) {
		t.Fatal("combined artifact bytes or independent pins differ")
	}
	if len(a.Methods) != 18 || len(a.Errors) != 1 || len(a.Events) != 0 || a.HasFallback() || a.HasReceive() || len(abiRaw) == 0 {
		t.Fatal("ABI is not exact constructor+error+18-function/no-event surface")
	}
	for _, mutate := range []func([]byte) []byte{
		func(b []byte) []byte { return append(b, ' ') },
		func(b []byte) []byte { b[len(b)/2] ^= 1; return b },
		func(b []byte) []byte {
			return bytes.Replace(b, []byte(compilerVersion), []byte(strings.Repeat("x", len(compilerVersion))), 1)
		},
		func(b []byte) []byte {
			return bytes.Replace(b, []byte(runtimeKeccak256), []byte(strings.Repeat("0", 64)), 1)
		},
	} {
		copyRaw := append([]byte(nil), raw...)
		if _, _, _, _, err := validateArtifact(mutate(copyRaw)); err == nil {
			t.Fatal("altered combined artifact accepted")
		}
	}
	var doc struct {
		ABI []map[string]interface{} `json:"abi"`
	}
	if err := json.Unmarshal(raw, &doc); err != nil {
		t.Fatal(err)
	}
	for _, extra := range []map[string]interface{}{
		{"type": "event", "name": "Extra", "anonymous": false, "inputs": []interface{}{}},
		{"type": "fallback", "stateMutability": "nonpayable"},
		{"type": "receive", "stateMutability": "payable"},
	} {
		entries := append(append([]map[string]interface{}(nil), doc.ABI...), extra)
		encoded, _ := json.Marshal(entries)
		changed, err := abi.JSON(bytes.NewReader(encoded))
		if err != nil {
			t.Fatal(err)
		}
		if err := validateABI(changed); err == nil {
			t.Fatalf("extra ABI entry accepted: %v", extra["type"])
		}
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
}

func TestZI0HarnessRealLifecycleRecordsRootsCASAndOpaqueViews(t *testing.T) {
	z := zi0HarnessSmallZIP()
	owner := common.HexToAddress("0x5a4930701001")
	session, gas := zi0HarnessOpenAndUpload(t, owner, z, "")
	defer session.Close()
	zi0HarnessSealCreate(t, session, &gas)
	bound, _ := session.Head(OrdinaryGas)
	if _, err := session.Entry(0, OrdinaryGas); err == nil || !strings.Contains(err.Error(), "revert_data") {
		t.Fatal("staging entry did not fail in EVM")
	}
	if op, err := session.Scan(0, 0, common.Hash{}, 0, OrdinaryGas); err == nil || zi0HarnessErrorCode(t, op) != 4 {
		t.Fatalf("scan before discover op=%+v err=%v", op, err)
	}
	if _, err := session.Discover(OrdinaryGas); err != nil {
		t.Fatal(err)
	}
	staging, err := session.Head(OrdinaryGas)
	if err != nil || staging.Index.Phase != 1 || staging.Index.Count != 2 || staging.Index.CDOffset != z.cd || staging.Index.EOCD != z.eocd {
		t.Fatalf("staging=%+v err=%v", staging, err)
	}
	for _, tc := range []struct {
		entry, cursor uint32
		rolling       common.Hash
		units         uint16
		code          uint64
	}{
		{staging.Index.NextEntry + 1, staging.Index.CDCursor, staging.Index.Rolling, 1, 10},
		{staging.Index.NextEntry, staging.Index.CDCursor + 1, staging.Index.Rolling, 1, 10},
		{staging.Index.NextEntry, staging.Index.CDCursor, common.Hash{}, 1, 10},
		{staging.Index.NextEntry, staging.Index.CDCursor, staging.Index.Rolling, 0, 11},
		{staging.Index.NextEntry, staging.Index.CDCursor, staging.Index.Rolling, 65, 11},
	} {
		before, _ := session.Head(OrdinaryGas)
		op, err := session.Scan(tc.entry, tc.cursor, tc.rolling, tc.units, OrdinaryGas)
		if err == nil || zi0HarnessErrorCode(t, op) != tc.code || op.StateRoot != (common.Hash{}) || len(op.Logs) != 0 {
			t.Fatalf("CAS/units tc=%+v op=%+v err=%v", tc, op, err)
		}
		after, _ := session.Head(OrdinaryGas)
		if !reflect.DeepEqual(zi0HarnessHeadWithoutGas(before), zi0HarnessHeadWithoutGas(after)) {
			t.Fatal("failed scan changed committed head")
		}
	}
	first, err := session.Scan(staging.Index.NextEntry, staging.Index.CDCursor, staging.Index.Rolling, 1, OrdinaryGas)
	if err != nil || first.StateRoot == bound.StateRoot {
		t.Fatalf("first scan=%+v err=%v", first, err)
	}
	mid, _ := session.Head(OrdinaryGas)
	if mid.Index.NextEntry != 1 {
		t.Fatal("q1 did not publish one entry")
	}
	if op, err := session.Finish(mid.Index.Count, mid.Index.CDCursor, mid.Index.Rolling, OrdinaryGas); err == nil || zi0HarnessErrorCode(t, op) != 29 {
		t.Fatalf("early finish op=%+v err=%v", op, err)
	}
	if _, err := session.Scan(mid.Index.NextEntry, mid.Index.CDCursor, mid.Index.Rolling, 64, OrdinaryGas); err != nil {
		t.Fatal(err)
	}
	atEnd, _ := session.Head(OrdinaryGas)
	if op, err := session.Scan(atEnd.Index.NextEntry, atEnd.Index.CDCursor, atEnd.Index.Rolling, 1, OrdinaryGas); err == nil || zi0HarnessErrorCode(t, op) != 11 {
		t.Fatalf("at-end no-op scan op=%+v err=%v", op, err)
	}
	if _, err := session.Finish(atEnd.Index.Count, atEnd.Index.CDCursor, atEnd.Index.Rolling, OrdinaryGas); err != nil {
		t.Fatal(err)
	}
	final, err := session.Head(OrdinaryGas)
	if err != nil || final.Index.Phase != 2 || final.Index.FinalRoot != final.Index.Rolling {
		t.Fatalf("final=%+v err=%v", final, err)
	}
	for index, want := range [][]byte{[]byte("first.txt"), []byte("dir/second.bin")} {
		entry, err := session.Entry(uint32(index), OrdinaryGas)
		if err != nil || !bytes.Equal(entry.Name, want) || entry.PackedRecord == (common.Hash{}) || entry.GasUsed == 0 {
			t.Fatalf("entry %d=%+v err=%v", index, entry, err)
		}
		lookup, err := session.Lookup(want, OrdinaryGas)
		if err != nil || !lookup.Found || lookup.Index != uint32(index) || lookup.PackedRecord != entry.PackedRecord || lookup.GasUsed == 0 {
			t.Fatalf("lookup %d=%+v err=%v", index, lookup, err)
		}
	}
	miss, err := session.Lookup([]byte("FIRST.TXT"), OrdinaryGas)
	if err != nil || miss.Found || miss.Index != 0 || miss.PackedRecord != (common.Hash{}) {
		t.Fatalf("miss=%+v err=%v", miss, err)
	}
	if _, err := session.Entry(2, OrdinaryGas); err == nil {
		t.Fatal("entry EOF accepted")
	}
	for _, name := range [][]byte{nil, bytes.Repeat([]byte{'n'}, 257)} {
		if _, err := session.Lookup(name, OrdinaryGas); err == nil {
			t.Fatal("lookup name bound accepted")
		}
	}
	if _, err := session.Finish(final.Index.Count, final.Index.CDCursor, final.Index.Rolling, OrdinaryGas); err == nil {
		t.Fatal("finish after FINAL accepted")
	}
	read, err := session.Read(z.dataAt[0], uint32(len(z.entries[0].data)), OrdinaryGas)
	if err != nil || !bytes.Equal(read.Bytes, z.entries[0].data) {
		t.Fatalf("AS0 raw read=%x err=%v", read.Bytes, err)
	}
	if _, err := session.Read(uint32(len(z.raw)), 0, OrdinaryGas); err != nil {
		t.Fatalf("exact EOF empty read: %v", err)
	}
	if _, err := session.Read(uint32(len(z.raw))+1, 0, OrdinaryGas); err == nil {
		t.Fatal("past-EOF empty read accepted")
	}
}

func TestZI0HarnessPublicationRollbackRetryAndAmbiguousCreateIndex(t *testing.T) {
	z := zi0HarnessSmallZIP()
	ownerBase := common.HexToAddress("0x5a4930702000")
	for _, point := range []faultPoint{faultAfterTrie, faultBeforeManifest} {
		t.Run(fmt.Sprintf("prepublication-%d", point), func(t *testing.T) {
			owner := ownerBase
			owner[19] += byte(point)
			directory := t.TempDir()
			session, gas := zi0HarnessOpenAndUpload(t, owner, z, directory)
			defer session.Close()
			zi0HarnessSealCreate(t, session, &gas) // establish ordinary index, then test discover publication
			before, _ := session.Head(OrdinaryGas)
			fired := false
			session.testFault = func(got faultPoint) error {
				if got == point && !fired {
					fired = true
					return errors.New("injected durability failure")
				}
				return nil
			}
			op, err := session.Discover(OrdinaryGas)
			if err == nil || !fired || op.GasUsed == 0 || op.StateRoot != (common.Hash{}) || op.CreatedAddress != (common.Address{}) || len(op.Logs) != 0 || len(op.RevertData) != 0 {
				t.Fatalf("publication failure leaked success: op=%+v err=%v", op, err)
			}
			after, headErr := session.Head(OrdinaryGas)
			if headErr != nil || !reflect.DeepEqual(zi0HarnessHeadWithoutGas(before), zi0HarnessHeadWithoutGas(after)) {
				t.Fatalf("old published root not restored: before=%+v after=%+v err=%v", before, after, headErr)
			}
			session.testFault = nil
			if _, err := session.Discover(OrdinaryGas); err != nil {
				t.Fatalf("retry failed: %v", err)
			}
		})
	}

	for _, point := range []faultPoint{faultAfterTrie, faultBeforeManifest, faultAfterManifestRename} {
		t.Run(fmt.Sprintf("create-index-%d", point), func(t *testing.T) {
			owner := ownerBase
			owner[18], owner[19] = 1, byte(point)
			directory := t.TempDir()
			session, _ := zi0HarnessOpenAndUpload(t, owner, z, directory)
			defer session.Close()
			head, _ := session.Head(OrdinaryGas)
			if _, err := session.Seal(head.AS0.Cursor, head.AS0.ChainCommitment, OrdinaryGas); err != nil {
				t.Fatal(err)
			}
			sealed, _ := session.Head(OrdinaryGas)
			fired := false
			session.testFault = func(got faultPoint) error {
				if got == point && !fired {
					fired = true
					return errors.New("index publication failure")
				}
				return nil
			}
			op, err := session.CreateIndex(sealed.AS0.ContentCommitment, OrdinaryGas)
			if err == nil || !fired || op.GasUsed == 0 || op.StateRoot != (common.Hash{}) || op.CreatedAddress != (common.Address{}) || len(op.Logs) != 0 || len(op.RevertData) != 0 {
				t.Fatalf("failed CreateIndex leaked success: op=%+v err=%v", op, err)
			}
			if point != faultAfterManifestRename {
				if session.indexAddress != (common.Address{}) || session.state.GetNonce(owner) != 1 {
					t.Fatal("prepublication CreateIndex did not reset address/creator nonce")
				}
				session.testFault = nil
				retry, err := session.CreateIndex(sealed.AS0.ContentCommitment, OrdinaryGas)
				if err != nil || retry.CreatedAddress != crypto.CreateAddress(owner, 1) {
					t.Fatalf("CreateIndex retry=%+v err=%v", retry, err)
				}
				return
			}
			if _, err := session.Head(OrdinaryGas); err == nil {
				t.Fatal("post-rename ambiguous session remained usable")
			}
			if err := session.Close(); err != nil {
				t.Fatal(err)
			}
			reopened, err := Open(directory, owner, uint32(len(z.raw)))
			if err != nil {
				t.Fatalf("reopen renamed index root: %v", err)
			}
			defer reopened.Close()
			creation, _ := reopened.Creation()
			reopenedHead, err := reopened.Head(OrdinaryGas)
			if err != nil || creation.Performed || reopenedHead.Index.Address != crypto.CreateAddress(owner, 1) || reopenedHead.Index.Phase != 0 {
				t.Fatalf("renamed root not recovered: creation=%+v head=%+v err=%v", creation, reopenedHead, err)
			}
		})
	}
}

func TestZI0HarnessManifestNamespacePinsLinksAndNoRecreate(t *testing.T) {
	owner := common.HexToAddress("0x5a4930703001")
	z := zi0HarnessSmallZIP()
	directory := t.TempDir()
	session, gas := zi0HarnessOpenAndUpload(t, owner, z, directory)
	zi0HarnessSealCreate(t, session, &gas)
	zi0HarnessIndex(t, session, 64, &gas)
	final, _ := session.Head(OrdinaryGas)
	if err := session.Close(); err != nil {
		t.Fatal(err)
	}
	reopened, err := Open(directory, owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatal(err)
	}
	creation, _ := reopened.Creation()
	head, err := reopened.Head(OrdinaryGas)
	if err != nil || creation.Performed || creation.GasUsed != 0 || creation.Controller != crypto.CreateAddress(owner, 0) || head.StateRoot != final.StateRoot || head.Index.Address != crypto.CreateAddress(owner, 1) || reopened.state.GetNonce(owner) != 2 {
		t.Fatalf("reopen recreated or changed identity: creation=%+v head=%+v err=%v", creation, head, err)
	}
	reopened.Close()

	original, err := readManifest(filepath.Join(directory, manifestName))
	if err != nil {
		t.Fatal(err)
	}
	for name, mutate := range map[string]func(*manifest){
		"format": func(m *manifest) { m.Format++ }, "context": func(m *manifest) { m.Context += ":bad" },
		"owner": func(m *manifest) { m.Owner[0] ^= 1 }, "length": func(m *manifest) { m.Length++ },
		"as0": func(m *manifest) { m.AS0 = common.Address{} }, "index": func(m *manifest) { m.Index = common.Address{} },
		"content": func(m *manifest) { m.Content[0] ^= 1 }, "as0-pin": func(m *manifest) { m.AS0CodeHash[0] ^= 1 },
		"zi0-pin": func(m *manifest) { m.ZI0CodeHash[0] ^= 1 }, "root": func(m *manifest) { m.StateRoot = types.EmptyRootHash },
	} {
		t.Run(name, func(t *testing.T) {
			copyDir := filepath.Join(t.TempDir(), "store")
			zi0HarnessCopyDir(t, directory, copyDir)
			bad := original
			mutate(&bad)
			raw, _ := json.Marshal(bad)
			if err := os.WriteFile(filepath.Join(copyDir, manifestName), raw, 0600); err != nil {
				t.Fatal(err)
			}
			if got, err := Open(copyDir, owner, uint32(len(z.raw))); err == nil {
				got.Close()
				t.Fatal("bad manifest accepted")
			}
		})
	}
	unknown := filepath.Join(t.TempDir(), "store")
	zi0HarnessCopyDir(t, directory, unknown)
	raw, _ := os.ReadFile(filepath.Join(unknown, manifestName))
	raw = bytes.Replace(raw, []byte("\n}"), []byte(",\n  \"unknown\": 1\n}"), 1)
	_ = os.WriteFile(filepath.Join(unknown, manifestName), raw, 0600)
	if got, err := Open(unknown, owner, uint32(len(z.raw))); err == nil {
		got.Close()
		t.Fatal("unknown manifest field accepted")
	}
	over := filepath.Join(t.TempDir(), "store")
	zi0HarnessCopyDir(t, directory, over)
	_ = os.WriteFile(filepath.Join(over, manifestName), bytes.Repeat([]byte{'x'}, int(manifestMaxSize)+1), 0600)
	if got, err := Open(over, owner, uint32(len(z.raw))); err == nil {
		got.Close()
		t.Fatal("oversized manifest accepted")
	}

	unrelated := t.TempDir()
	keep := filepath.Join(unrelated, "keep")
	_ = os.WriteFile(keep, []byte("preserve"), 0600)
	if got, err := Open(unrelated, owner, 1); err == nil {
		got.Close()
		t.Fatal("unrelated namespace adopted")
	}
	if got, _ := os.ReadFile(keep); string(got) != "preserve" {
		t.Fatal("unrelated namespace was wiped")
	}
	incomplete := t.TempDir()
	_ = os.WriteFile(filepath.Join(incomplete, markerName), []byte(storeMarker), 0600)
	_ = os.Mkdir(filepath.Join(incomplete, stateDirectory), 0700)
	if got, err := Open(incomplete, owner, 1); err == nil {
		got.Close()
		t.Fatal("incomplete store adopted")
	}
	if _, err := os.Stat(filepath.Join(incomplete, markerName)); err != nil {
		t.Fatal("incomplete evidence removed")
	}

	alias := filepath.Join(t.TempDir(), "alias")
	if err := os.Symlink(directory, alias); err != nil {
		t.Fatal(err)
	}
	viaAlias, err := Open(alias, owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatalf("explicit root alias rejected: %v", err)
	}
	viaAlias.Close()
	tempLinkStore := filepath.Join(t.TempDir(), "store")
	zi0HarnessCopyDir(t, directory, tempLinkStore)
	externalTemp := filepath.Join(t.TempDir(), "external-temp")
	if err := os.WriteFile(externalTemp, []byte("preserve"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(externalTemp, filepath.Join(tempLinkStore, ".durable-head-evil")); err != nil {
		t.Fatal(err)
	}
	if got, err := Open(tempLinkStore, owner, uint32(len(z.raw))); err == nil {
		got.Close()
		t.Fatal("linked publication temp accepted")
	}
	if got, _ := os.ReadFile(externalTemp); string(got) != "preserve" {
		t.Fatal("linked publication temp target changed")
	}

	for _, rel := range []string{markerName, manifestName, stateDirectory, filepath.Join(stateDirectory, "CURRENT")} {
		t.Run("link-"+strings.ReplaceAll(rel, string(filepath.Separator), "-"), func(t *testing.T) {
			copyDir := filepath.Join(t.TempDir(), "store")
			zi0HarnessCopyDir(t, directory, copyDir)
			originalPath := filepath.Join(copyDir, rel)
			moved := filepath.Join(t.TempDir(), "moved")
			if err := os.Rename(originalPath, moved); err != nil {
				t.Fatal(err)
			}
			if err := os.Symlink(moved, originalPath); err != nil {
				t.Fatal(err)
			}
			if got, err := Open(copyDir, owner, uint32(len(z.raw))); err == nil {
				got.Close()
				t.Fatal("internal link accepted")
			}
		})
	}
}

func zi0HarnessCopyDir(t testing.TB, source, target string) {
	t.Helper()
	if err := filepath.Walk(source, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		relative, err := filepath.Rel(source, path)
		if err != nil {
			return err
		}
		destination := filepath.Join(target, relative)
		if info.IsDir() {
			return os.MkdirAll(destination, info.Mode())
		}
		raw, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		return os.WriteFile(destination, raw, info.Mode())
	}); err != nil {
		t.Fatal(err)
	}
}

func TestZI0HarnessClosedGasArgumentsAndHeadDecoderBounds(t *testing.T) {
	if _, err := NewMemory(common.Address{}, 1); err == nil {
		t.Fatal("zero owner accepted")
	}
	if _, err := NewMemory(common.HexToAddress("0x1"), 0); err == nil {
		t.Fatal("zero length accepted")
	}
	if _, err := NewMemory(common.HexToAddress("0x1"), as0.MaxLength+1); err == nil {
		t.Fatal("oversized length accepted")
	}
	if _, err := Open("", common.HexToAddress("0x1"), 1); err == nil {
		t.Fatal("empty directory accepted")
	}
	session, err := NewMemory(common.HexToAddress("0x5a4930704001"), 1)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := session.Head(0); err == nil {
		t.Fatal("zero gas accepted")
	}
	if _, err := session.Head(MaxGas + 1); err == nil {
		t.Fatal("over-bound gas accepted")
	}
	// pageCount is the length of AS0's pages array at storage slot 3. A value
	// above 4096 used to truncate uint64->uint32 in this package.
	pageCountSlot := common.BigToHash(big.NewInt(3))
	before := session.state.GetState(session.as0Address, pageCountSlot)
	session.state.SetState(session.as0Address, pageCountSlot, common.BigToHash(new(big.Int).SetUint64(uint64(as0.MaxPages)+1)))
	if _, err := session.Head(OrdinaryGas); err == nil || !strings.Contains(err.Error(), "page count") {
		t.Fatalf("oversized AS0 pageCount accepted: %v", err)
	}
	session.state.SetState(session.as0Address, pageCountSlot, before)
	// Altering only the local ABI decoder must return an explicit type error,
	// never panic or a nil-error empty success.
	badABI := session.as0ABI
	method := badABI.Methods["owner"]
	uintType, _ := abi.NewType("uint256", "", nil)
	method.Outputs = abi.Arguments{{Type: uintType}}
	badABI.Methods["owner"] = method
	session.as0ABI = badABI
	if _, err := session.Head(OrdinaryGas); err == nil || !strings.Contains(err.Error(), "owner") {
		t.Fatalf("wrong getter decoder type was not explicit: %v", err)
	}
	session.as0ABI, _ = as0.ABI()
	if err := session.Close(); err != nil {
		t.Fatal(err)
	}
	if err := session.Close(); err != nil {
		t.Fatal(err)
	}
	if _, err := session.Head(OrdinaryGas); err == nil {
		t.Fatal("closed session usable")
	}
}
