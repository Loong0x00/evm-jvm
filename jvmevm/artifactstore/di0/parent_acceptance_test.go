package di0

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"hash/crc32"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/rawdb"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/ethdb/leveldb"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/as0"
)

func TestDI0ParentEveryMutationReallySyncsAndReloads(t *testing.T) {
	for _, diskMode := range []bool{false, true} {
		t.Run(fmt.Sprint(diskMode), func(t *testing.T) {
			z := di0HarnessZIP1(t, []byte("counted"), bytes.Repeat([]byte("K"), 9000), 0)
			owner := common.HexToAddress("0xd100a001")
			dir := ""
			var db durableDB
			if diskMode {
				dir = t.TempDir()
				kv, e := leveldb.New(filepath.Join(dir, stateDirectory), 16, 16, "di0-parent-count", false)
				if e != nil {
					t.Fatal(e)
				}
				db = rawdb.NewDatabase(kv)
			} else {
				db = rawdb.NewMemoryDatabase()
			}
			counter := &di0ParentSyncDB{durableDB: db}
			// Same private construction path as Open/NewMemory, wrapping the REAL database
			// before initial CREATE so that its synchronization is observed too.
			s, e := newSession(owner, uint32(len(z.raw)), dir, counter)
			if e != nil {
				t.Fatal(e)
			}
			defer s.Close()
			if diskMode {
				e = s.initDisk()
			} else {
				e = s.createAS0()
			}
			if e != nil {
				t.Fatal(e)
			}
			if counter.count != 1 {
				t.Fatalf("initial CREATE syncs=%d", counter.count)
			}
			count := 1
			head := func() Head {
				before := counter.count
				h, e := s.Head(OrdinaryGas)
				if e != nil {
					t.Fatal(e)
				}
				if before != counter.count {
					t.Fatal("view synchronized a mutation")
				}
				return h
			}
			call := func(label string, fn func() (Operation, error)) {
				oldState, oldRoot := s.state, s.root
				before := counter.count
				op, e := fn()
				if e != nil {
					t.Fatalf("%s: %v", label, e)
				}
				if counter.count != before+1 || s.state == oldState || s.root == oldRoot || op.StateRoot != s.root || op.GasUsed == 0 {
					t.Fatalf("%s no exact sync/reload/root: count=%d op=%+v", label, counter.count, op)
				}
				if diskMode {
					m, e := readManifest(filepath.Join(dir, manifestName))
					if e != nil || m.StateRoot != s.root {
						t.Fatalf("%s returned before publication: %v", label, e)
					}
				}
				count++
				head()
			}
			h := head()
			for at := 0; at < len(z.raw); at += int(as0.PageSize) {
				end := at + int(as0.PageSize)
				if end > len(z.raw) {
					end = len(z.raw)
				}
				raw := z.raw[at:end]
				call("append", func() (Operation, error) {
					return s.Append(uint32(at), raw, di0HarnessPageCommitment(t, h.AS0.Controller, uint32(at)/as0.PageSize, raw), OrdinaryGas)
				})
			}
			h = head()
			call("seal", func() (Operation, error) { return s.Seal(h.AS0.Cursor, h.AS0.ChainCommitment, OrdinaryGas) })
			h = head()
			call("index CREATE", func() (Operation, error) { return s.CreateIndex(h.AS0.ContentCommitment, OrdinaryGas) })
			call("discover", func() (Operation, error) { return s.DiscoverIndex(OrdinaryGas) })
			h = head()
			call("scan", func() (Operation, error) {
				return s.ScanIndex(h.Index.NextEntry, h.Index.CDCursor, h.Index.Rolling, 1, OrdinaryGas)
			})
			h = head()
			call("finish", func() (Operation, error) {
				return s.FinishIndex(h.Index.Count, h.Index.CDCursor, h.Index.Rolling, OrdinaryGas)
			})
			h = head()
			call("decoder CREATE", func() (Operation, error) { return s.CreateDecoder(h.Index.FinalRoot, z.name, OrdinaryGas) })
			for h = head(); h.Decoder.Phase == 1; h = head() {
				call("step", func() (Operation, error) { return s.Step(h.Decoder.Work, 128, OrdinaryGas) })
			}
			for h = head(); h.Decoder.Phase != 4; h = head() {
				call("publish", func() (Operation, error) {
					return s.Publish(h.Decoder.PublishedPages, h.Decoder.PublicationRolling, 1, OrdinaryGas)
				})
			}
			if count != 14 || counter.count != count {
				t.Fatalf("actual syncs=%d expected14 across all mutation families", counter.count)
			}
			before := counter.count
			_, e = s.Read(0, MaxRead, OrdinaryGas)
			if e != nil {
				t.Fatal(e)
			}
			_, e = s.Page(0, OrdinaryGas)
			if e != nil {
				t.Fatal(e)
			}
			_, e = s.Step(h.Decoder.Work, 1, OrdinaryGas)
			if e == nil || counter.count != before {
				t.Fatal("failed step/view published")
			}
			if diskMode {
				root := s.root
				if e = s.Close(); e != nil {
					t.Fatal(e)
				}
				r, e := Open(dir, owner, uint32(len(z.raw)))
				if e != nil {
					t.Fatal(e)
				}
				defer r.Close()
				if r.root != root {
					t.Fatal("disk root differs")
				}
				c, e := r.Creation()
				if e != nil || c.Performed || c.GasUsed != 0 {
					t.Fatal("reopen CREATE")
				}
			}
			t.Logf("actual completed sync calls=%d; initial CREATE included; every success reloaded; disk=%v", count, diskMode)
		})
	}
}

func TestDI0ParentFull32MiBHighOffsetDurableInput(t *testing.T) {
	plain := []byte("actual EVM high-offset resource")
	comp := di0HarnessDeflate(t, plain)
	name := []byte("high-resource")
	small := di0HarnessZIPPayload(name, plain, comp, 8)
	z := di0HarnessZIPPayloadPrefix(int(as0.MaxLength)-len(small.raw), name, plain, comp, 8)
	if len(z.raw) != int(as0.MaxLength) {
		t.Fatal("not exactly32MiB")
	}
	dir := t.TempDir()
	owner := common.HexToAddress("0xd100a002")
	s, e := Open(dir, owner, uint32(len(z.raw)))
	if e != nil {
		t.Fatal(e)
	}
	defer func() { s.Close() }()
	counter := &di0ParentSyncDB{durableDB: s.disk}
	s.disk = counter
	di0HarnessUpload(t, s, z.raw)
	di0HarnessFinishIndex(t, s)
	di0HarnessCreate(t, s, z.name)
	h := di0HarnessDecode(t, s, 128)
	h = di0HarnessPublish(t, s)
	if h.Decoder.DataStart < as0.MaxLength-1024 || h.AS0.PageCount != 4096 || counter.count != 4104 {
		t.Fatalf("high offset=%d pages=%d observed post-Open syncs=%d", h.Decoder.DataStart, h.AS0.PageCount, counter.count)
	}
	root, resource := s.root, h.Decoder.FinalRoot
	// Independently read ALL32MiB through EVM AS0 read, not host ZIP/page extraction.
	for at := uint32(0); at < as0.MaxLength; at += MaxRead {
		r, e := s.InputRead(at, MaxRead, OrdinaryGas)
		if e != nil || !bytes.Equal(r.Bytes, z.raw[at:at+MaxRead]) {
			t.Fatalf("input read at%d: %v", at, e)
		}
	}
	if counter.count != 4104 || s.root != root {
		t.Fatal("input reads published or changed root")
	}
	if e = s.Close(); e != nil {
		t.Fatal(e)
	}
	s, e = Open(dir, owner, uint32(len(z.raw)))
	if e != nil {
		t.Fatal(e)
	}
	h, e = s.Head(OrdinaryGas)
	if e != nil || s.root != root || h.Decoder.FinalRoot != resource {
		t.Fatalf("high-offset reopen: %v", e)
	}
	r, e := s.Read(0, uint32(len(plain)), OrdinaryGas)
	if e != nil || !bytes.Equal(r.Bytes, plain) {
		t.Fatalf("final output: %v", e)
	}
	t.Logf("input=%d pages=%d dataStart=%d full EVM reads=8192 post-Open real syncs=4104 (initial Open CREATE excluded); trie=%s resource=%s", len(z.raw), h.AS0.PageCount, h.Decoder.DataStart, root, resource)
}

func TestDI0ParentRealManifestFilesystemFailures(t *testing.T) {
	for _, kind := range []string{"create-temp", "rename"} {
		t.Run(kind, func(t *testing.T) {
			base := t.TempDir()
			dir := filepath.Join(base, "session")
			owner := common.HexToAddress("0xd100a003")
			z := di0HarnessZIP1(t, []byte("fs"), []byte("file-system failure"), 0)
			s, e := Open(dir, owner, uint32(len(z.raw)))
			if e != nil {
				t.Fatal(e)
			}
			defer s.Close()
			old := s.root
			manifestPath := filepath.Join(dir, manifestName)
			saved, e := os.ReadFile(manifestPath)
			if e != nil {
				t.Fatal(e)
			}
			backup := filepath.Join(base, "saved-manifest")
			s.testFault = func(p faultPoint) error {
				if p != faultBeforeManifest {
					return nil
				}
				if kind == "create-temp" {
					s.directory = filepath.Join(dir, "missing-parent")
					return nil
				}
				if e := os.Rename(manifestPath, backup); e != nil {
					return e
				}
				return os.Mkdir(manifestPath, 0700)
			}
			op, e := s.Append(0, z.raw, di0HarnessPageCommitment(t, s.as0Address, 0, z.raw), OrdinaryGas)
			s.directory = dir
			s.testFault = nil
			if kind == "rename" {
				if e := os.Remove(manifestPath); e != nil {
					t.Fatal(e)
				}
				if e := os.Rename(backup, manifestPath); e != nil {
					t.Fatal(e)
				}
			}
			if e == nil || op.GasUsed == 0 || op.StateRoot != (common.Hash{}) || len(op.Logs) != 0 || len(op.RevertData) != 0 || s.poison != nil || s.root != old {
				t.Fatalf("real filesystem error: op=%+v error=%v", op, e)
			}
			got, e := os.ReadFile(manifestPath)
			if e != nil || !bytes.Equal(saved, got) {
				t.Fatal("old manifest changed")
			}
			if _, e = s.Append(0, z.raw, di0HarnessPageCommitment(t, s.as0Address, 0, z.raw), OrdinaryGas); e != nil {
				t.Fatal(e)
			}
			t.Logf("real OS %s failure left prior root/manifest and gas-only receipt; normal retry passed", kind)
		})
	}
}

func TestDI0ParentTemporaryManifestStages(t *testing.T) {
	for _, point := range []faultPoint{faultAfterTempCreate, faultAfterTempWrite, faultAfterTempSync, faultAfterTempClose, faultAfterDirectorySync} {
		t.Run(fmt.Sprint(point), func(t *testing.T) {
			dir := t.TempDir()
			owner := common.HexToAddress("0xd100a004")
			z := di0HarnessZIP1(t, []byte("temp"), []byte("durable temporary bytes"), 0)
			s, e := Open(dir, owner, uint32(len(z.raw)))
			if e != nil {
				t.Fatal(e)
			}
			defer func() {
				if s != nil {
					s.Close()
				}
			}()
			old := s.root
			counter := &di0ParentSyncDB{durableDB: s.disk}
			s.disk = counter
			hits := 0
			s.testFault = func(p faultPoint) error {
				if p == point {
					hits++
					return errors.New("parent after real manifest OS operation")
				}
				return nil
			}
			pi := di0HarnessPageCommitment(t, s.as0Address, 0, z.raw)
			op, e := s.Append(0, z.raw, pi, OrdinaryGas)
			if e == nil || hits != 1 || counter.count != 1 || op.GasUsed == 0 || op.StateRoot != (common.Hash{}) || len(op.Logs) != 0 || len(op.RevertData) != 0 {
				t.Fatalf("point%d op=%+v err=%v syncs%d hits%d", point, op, e, counter.count, hits)
			}
			m, e := readManifest(filepath.Join(dir, manifestName))
			if e != nil {
				t.Fatal(e)
			}
			s.testFault = nil
			if point == faultAfterDirectorySync {
				if s.poison == nil || m.StateRoot == old {
					t.Fatal("completed rename+dirsync not poisoned")
				}
				if _, e = s.Creation(); e == nil {
					t.Fatal("poisoned Creation succeeded")
				}
			} else {
				if s.poison != nil || m.StateRoot != old || s.root != old || s.state.GetNonce(s.as0Address) != 1 {
					t.Fatal("prepublication state not restored")
				}
				temps, e := filepath.Glob(filepath.Join(dir, ".durable-head-*"))
				if e != nil || len(temps) != 1 {
					t.Fatalf("owned diagnostic temp not preserved: %v %v", temps, e)
				}
				if point == faultAfterTempSync || point == faultAfterTempClose {
					tmp, e := readManifest(temps[0])
					if e != nil || tmp.StateRoot == old {
						t.Fatal("test did not follow actual new temporary manifest sync")
					}
				}
			}
			if e = s.Close(); e != nil {
				t.Fatal(e)
			}
			s = nil
			s, e = Open(dir, owner, uint32(len(z.raw)))
			if e != nil {
				t.Fatal(e)
			}
			if point != faultAfterDirectorySync {
				if s.root != old {
					t.Fatal("unpublished temp adopted")
				}
				if _, e = s.Append(0, z.raw, pi, OrdinaryGas); e != nil {
					t.Fatal(e)
				}
			}
			h, e := s.Head(OrdinaryGas)
			if e != nil || h.AS0.Cursor != uint32(len(z.raw)) || h.AS0.PageCount != 1 {
				t.Fatalf("retry/reopen: %+v %v", h.AS0, e)
			}
		})
	}
}

func TestDI0ParentMetadataRejectedBeforeDatabaseOpen(t *testing.T) {
	dir := t.TempDir()
	owner := common.HexToAddress("0xd100a005")
	z := di0HarnessZIP1(t, []byte("meta"), []byte("m"), 0)
	s, e := Open(dir, owner, uint32(len(z.raw)))
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	path := filepath.Join(dir, manifestName)
	original, e := os.ReadFile(path)
	if e != nil {
		t.Fatal(e)
	}
	var base manifest
	if e = json.Unmarshal(original, &base); e != nil {
		t.Fatal(e)
	}
	// Keep the real DB lock held. An invalid manifest must fail BEFORE attempting
	// LevelDB open, not merely fail because this original session holds its lock.
	for _, c := range []struct {
		name   string
		change func(*manifest)
	}{
		{"context", func(m *manifest) { m.Context = "different" }},
		{"format", func(m *manifest) { m.Format++ }},
		{"owner", func(m *manifest) { m.Owner[0] ^= 1 }},
		{"length", func(m *manifest) { m.Length++ }},
		{"AS0-route", func(m *manifest) { m.AS0[0] ^= 1 }},
		{"index-without-content", func(m *manifest) { m.Index = crypto.CreateAddress(owner, 1) }},
		{"decoder-without-index", func(m *manifest) { m.Decoder = crypto.CreateAddress(owner, 2) }},
		{"absent-decoder-name", func(m *manifest) { m.RawName = []byte("x") }},
		{"oversized-name", func(m *manifest) { m.RawName = bytes.Repeat([]byte("x"), 257) }},
		{"DI0-pin", func(m *manifest) { m.DI0CodeHash[0] ^= 1 }},
		{"ZI0-pin", func(m *manifest) { m.ZI0CodeHash[0] ^= 1 }},
		{"AS0-pin", func(m *manifest) { m.AS0CodeHash[0] ^= 1 }},
		{"zero-root", func(m *manifest) { m.StateRoot = common.Hash{} }},
		{"empty-trie-root", func(m *manifest) { m.StateRoot = types.EmptyRootHash }},
	} {
		t.Run(c.name, func(t *testing.T) {
			m := base
			c.change(&m)
			b, _ := json.Marshal(m)
			if e = os.WriteFile(path, b, 0600); e != nil {
				t.Fatal(e)
			}
			defer os.WriteFile(path, original, 0600)
			other, e := Open(dir, owner, uint32(len(z.raw)))
			if other != nil {
				other.Close()
			}
			if e == nil || !strings.Contains(e.Error(), "manifest binding mismatch") {
				t.Fatalf("not rejected before database open: %v", e)
			}
		})
	}
}

func TestDI0ParentIndependentResourceCommitments(t *testing.T) {
	for _, n := range []int{0, 16391} {
		t.Run(fmt.Sprint(n), func(t *testing.T) {
			plain := make([]byte, n)
			for i := range plain {
				plain[i] = byte(i*29 + i/71)
			}
			z := di0HarnessZIP1(t, []byte{0, '/', 255, 'r'}, plain, 0)
			owner := common.HexToAddress("0xd100a006")
			s, h := di0HarnessPrepared(t, z, owner)
			defer s.Close()
			lookup, e := s.Lookup(z.name, OrdinaryGas)
			if e != nil || !lookup.Found {
				t.Fatal(e)
			}
			H := crypto.Keccak256Hash
			bind := H(di0HarnessABI(t, []string{"bytes32", "address", "address", "address", "bytes32", "bytes32", "address", "bytes32", "bytes32", "uint32", "bytes32", "bytes32", "uint32"}, H([]byte("MC-DI0/binding/v1")), h.Decoder.Address, owner, h.Index.Address, zi0CodeHash, h.Index.FinalRoot, h.AS0.Controller, as0CodeHash, h.AS0.ContentCommitment, lookup.Index, H(z.name), lookup.PackedRecord, MaxOutput))
			if bind != h.Decoder.Binding {
				t.Fatal("independent constructor binding mismatch")
			}
			rolling := H(di0HarnessABI(t, []string{"bytes32", "bytes32"}, H([]byte("MC-DI0/output/v1")), bind))
			for i, b := range plain {
				rolling = H(di0HarnessABI(t, []string{"bytes32", "bytes32", "uint32", "uint8"}, H([]byte("MC-DI0/byte/v1")), rolling, uint32(i), b))
			}
			h = di0HarnessDecode(t, s, 128)
			if h.Decoder.OutputRolling != rolling {
				t.Fatal("independent plaintext byte chain mismatch")
			}
			crc := crc32.ChecksumIEEE(plain) // Generated-fixture oracle ONLY, never production authority.
			pub := H(di0HarnessABI(t, []string{"bytes32", "bytes32", "uint32", "uint32", "bytes32", "uint32"}, H([]byte("MC-DI0/publication/v1")), bind, uint32(n), crc, rolling, OutputPageSize))
			h = di0HarnessPublish(t, s)
			for i := uint8(0); i < h.Decoder.PublishedPages; i++ {
				start := int(i) * int(OutputPageSize)
				end := start + int(OutputPageSize)
				if end > n {
					end = n
				}
				raw := plain[start:end]
				size := uint32(len(raw))
				addr := crypto.CreateAddress(h.Decoder.Address, uint64(i)+1)
				ch := H(append([]byte{0}, raw...))
				pc := H(di0HarnessABI(t, []string{"bytes32", "bytes32", "uint8", "uint32", "bytes32"}, H([]byte("MC-DI0/page/v1")), bind, i, size, H(raw)))
				p, e := s.Page(i, OrdinaryGas)
				if e != nil || p.Address != addr || p.CodeHash != ch || p.Commitment != pc || p.Length != size {
					t.Fatalf("independent page%d: %v", i, e)
				}
				pub = H(di0HarnessABI(t, []string{"bytes32", "bytes32", "uint8", "uint32", "address", "bytes32", "bytes32"}, H([]byte("MC-DI0/published/v1")), pub, i, size, addr, ch, pc))
			}
			f := H(di0HarnessABI(t, []string{"bytes32", "bytes32", "uint32", "uint32", "bytes32", "uint8", "bytes32"}, H([]byte("MC-DI0/final/v1")), bind, uint32(n), crc, rolling, h.Decoder.PublishedPages, pub))
			if h.Decoder.PublicationRolling != pub || h.Decoder.FinalRoot != f {
				t.Fatal("independent ordered/final commitment mismatch")
			}
		})
	}
}
