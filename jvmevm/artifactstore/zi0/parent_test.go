package zi0

import (
	"archive/zip"
	"bytes"
	"encoding/binary"
	"encoding/json"
	"errors"
	zi0assets "github.com/ethereum/go-ethereum/jvmevm/artifactstore/zi0/runtime"
	"math/big"
	"os"
	"os/exec"
	"path/filepath"
	"testing"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/as0"
)

func zi0ParentHash(t *testing.T, ts []string, vals ...any) common.Hash {
	t.Helper()
	var args abi.Arguments
	for _, s := range ts {
		v, e := abi.NewType(s, "", nil)
		if e != nil {
			t.Fatal(e)
		}
		args = append(args, abi.Argument{Type: v})
	}
	b, e := args.Pack(vals...)
	if e != nil {
		t.Fatal(e)
	}
	return crypto.Keccak256Hash(b)
}
func zi0ParentPage(t *testing.T, addr common.Address, i uint32, b []byte) common.Hash {
	return zi0ParentHash(t, []string{"bytes32", "address", "uint32", "uint32", "bytes32"}, crypto.Keccak256Hash([]byte("MC-AS0/page/v1")), addr, i, uint32(len(b)), crypto.Keccak256Hash(b))
}
func zi0ParentZIP(t *testing.T) []byte {
	t.Helper()
	var b bytes.Buffer
	w := zip.NewWriter(&b)
	for _, name := range []string{"first.txt", "dir/second.txt"} {
		f, e := w.CreateHeader(&zip.FileHeader{Name: name, Method: zip.Store})
		if e != nil {
			t.Fatal(e)
		}
		if _, e = f.Write([]byte("parent opaque fixture")); e != nil {
			t.Fatal(e)
		}
	}
	if e := w.Close(); e != nil {
		t.Fatal(e)
	}
	return b.Bytes()
}
func TestZI0ParentFreshOrdinaryCreate(t *testing.T) {
	for _, disk := range []bool{false, true} {
		label := "memory"
		if disk {
			label = "disk"
		}
		t.Run(label, func(t *testing.T) {
			owner := common.HexToAddress("0x5a4930700001")
			var s *Session
			var e error
			if disk {
				s, e = Open(t.TempDir(), owner, 1)
			} else {
				s, e = NewMemory(owner, 1)
			}
			if e != nil {
				t.Fatal(e)
			}
			defer s.Close()
			c, e := s.Creation()
			if e != nil {
				t.Fatal(e)
			}
			if !c.Performed || c.GasUsed == 0 || c.Controller != crypto.CreateAddress(owner, 0) {
				t.Fatalf("fresh session did not actually CREATE AS0: %+v", c)
			}
			h, e := s.Head(OrdinaryGas)
			if e != nil {
				t.Fatal(e)
			}
			if h.AS0.Owner != owner || h.AS0.Controller != c.Controller || h.Index.Address != (common.Address{}) {
				t.Fatal("wrong fresh EVM identity")
			}
		})
	}
}
func TestZI0ParentRealArtifactPipeline(t *testing.T) {
	for _, disk := range []bool{false, true} {
		label := "memory"
		if disk {
			label = "disk"
		}
		t.Run(label, func(t *testing.T) {
			raw := zi0ParentZIP(t)
			owner := common.HexToAddress("0x5a4930700002")
			dir := ""
			var s *Session
			var e error
			if disk {
				dir = t.TempDir()
				s, e = Open(dir, owner, uint32(len(raw)))
			} else {
				s, e = NewMemory(owner, uint32(len(raw)))
			}
			if e != nil {
				t.Fatal(e)
			}
			defer func() { s.Close() }()
			c, e := s.Creation()
			if e != nil {
				t.Fatal(e)
			}
			for at := 0; at < len(raw); at += int(as0.PageSize) {
				end := at + int(as0.PageSize)
				if end > len(raw) {
					end = len(raw)
				}
				b := raw[at:end]
				if _, e = s.Append(uint32(at), b, zi0ParentPage(t, c.Controller, uint32(at)/as0.PageSize, b), OrdinaryGas); e != nil {
					t.Fatal(e)
				}
			}
			h, e := s.Head(OrdinaryGas)
			if e != nil {
				t.Fatal(e)
			}
			if _, e = s.Seal(uint32(len(raw)), h.AS0.ChainCommitment, OrdinaryGas); e != nil {
				t.Fatal(e)
			}
			h, e = s.Head(OrdinaryGas)
			if e != nil {
				t.Fatal(e)
			}
			op, e := s.CreateIndex(h.AS0.ContentCommitment, OrdinaryGas)
			if e != nil {
				t.Fatal(e)
			}
			if op.CreatedAddress != crypto.CreateAddress(owner, 1) {
				t.Fatal("ZI0 not ordinary second CREATE")
			}
			if _, e = s.Discover(OrdinaryGas); e != nil {
				t.Fatal(e)
			}
			h, e = s.Head(OrdinaryGas)
			if e != nil {
				t.Fatal(e)
			}
			if _, e = s.Scan(h.Index.NextEntry, h.Index.CDCursor, h.Index.Rolling, 64, OrdinaryGas); e != nil {
				t.Fatal(e)
			}
			h, e = s.Head(OrdinaryGas)
			if e != nil {
				t.Fatal(e)
			}
			if _, e = s.Finish(h.Index.Count, h.Index.CDCursor, h.Index.Rolling, OrdinaryGas); e != nil {
				t.Fatal(e)
			}
			if disk {
				if e = s.Close(); e != nil {
					t.Fatal(e)
				}
				s, e = Open(dir, owner, uint32(len(raw)))
				if e != nil {
					t.Fatal(e)
				}
			}
			r, e := s.Lookup([]byte("dir/second.txt"), OrdinaryGas)
			if e != nil || !r.Found || r.Index != 1 {
				t.Fatalf("real lookup=%+v err=%v", r, e)
			}
		})
	}
}

func TestZI0ParentExactABINoEvent(t *testing.T) {
	var d struct {
		ABI []map[string]any `json:"abi"`
	}
	if e := json.Unmarshal(zi0assets.Artifact(), &d); e != nil {
		t.Fatal(e)
	}
	d.ABI = append(d.ABI, map[string]any{"type": "event", "name": "NotFrozen", "anonymous": false, "inputs": []any{}})
	raw, e := json.Marshal(d.ABI)
	if e != nil {
		t.Fatal(e)
	}
	a, e := abi.JSON(bytes.NewReader(raw))
	if e != nil {
		t.Fatal(e)
	}
	if e = validateABI(a); e == nil {
		t.Fatal("non-frozen event accepted by exact ABI validator")
	}
}

func TestZI0ParentAS0HeadMalformedCopiedState(t *testing.T) {
	for _, kind := range []string{"page-count-truncation", "partial-before-end", "wrong-owner"} {
		t.Run(kind, func(t *testing.T) {
			s, e := NewMemory(common.HexToAddress("0x5a4930700003"), 8193)
			if e != nil {
				t.Fatal(e)
			}
			defer s.Close()
			original := s.state
			s.state = original.Copy()
			defer func() { s.state = original }()
			// TEST-only changed state, never a production page/state installer.
			if kind == "page-count-truncation" {
				s.state.SetState(s.as0Address, common.BigToHash(big.NewInt(3)), common.BigToHash(new(big.Int).Lsh(big.NewInt(1), 32)))
			} else {
				word := s.state.GetState(s.as0Address, common.Hash{})
				if kind == "partial-before-end" {
					binary.BigEndian.PutUint32(word[4:8], 1)
				} else {
					word[31] ^= 1
				}
				s.state.SetState(s.as0Address, common.Hash{}, word)
			}
			if h, e := s.Head(OrdinaryGas); e == nil {
				t.Fatalf("noncanonical %s accepted: %+v", kind, h.AS0)
			}
		})
	}
}

// Count real database synchronization, not a caller-maintained operation count.
type zi0ParentSyncDB struct {
	durableDB
	syncs    int
	failNext bool
}

func (d *zi0ParentSyncDB) SyncKeyValue() error {
	d.syncs++
	if e := d.durableDB.SyncKeyValue(); e != nil {
		return e
	}
	if d.failNext {
		d.failNext = false
		return errors.New("parent failure after actual DB sync")
	}
	return nil
}
func TestZI0ParentRealSyncFailureAndEveryPublication(t *testing.T) {
	raw := zi0ParentZIP(t)
	owner := common.HexToAddress("0x5a4930700004")
	dir := t.TempDir()
	s, e := Open(dir, owner, uint32(len(raw)))
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	c, e := s.Creation()
	if e != nil {
		t.Fatal(e)
	}
	before, e := s.Head(OrdinaryGas)
	if e != nil {
		t.Fatal(e)
	}
	d := &zi0ParentSyncDB{durableDB: s.disk, failNext: true}
	s.disk = d
	op, e := s.Append(0, raw, zi0ParentPage(t, c.Controller, 0, raw), OrdinaryGas)
	if e == nil || d.syncs != 1 || op.GasUsed == 0 || op.StateRoot != (common.Hash{}) || op.CreatedAddress != (common.Address{}) || len(op.Logs) != 0 || len(op.RevertData) != 0 {
		t.Fatalf("failed sync leaked success: %+v %v syncs=%d", op, e, d.syncs)
	}
	after, e := s.Head(OrdinaryGas)
	if e != nil || after.StateRoot != before.StateRoot || after.AS0.PageCount != 0 || s.state.Copy().IntermediateRoot(true) != before.StateRoot {
		t.Fatal("real DB-sync failure did not restore old root", e)
	}
	m, e := readManifest(filepath.Join(dir, manifestName))
	if e != nil || m.StateRoot != before.StateRoot {
		t.Fatal("failed sync changed manifest", e)
	}
	publish := func(run func() (Operation, error)) {
		t.Helper()
		oldSyncs := d.syncs
		r, e := run()
		if e != nil {
			t.Fatal(e)
		}
		if d.syncs != oldSyncs+1 || r.StateRoot == (common.Hash{}) {
			t.Fatalf("not exactly one actual sync: before%d after%d result%+v", oldSyncs, d.syncs, r)
		}
		m, e := readManifest(filepath.Join(dir, manifestName))
		if e != nil || m.StateRoot != r.StateRoot || s.state.Copy().IntermediateRoot(true) != r.StateRoot {
			t.Fatal("published/root/actual EVM state mismatch", e)
		}
	}
	publish(func() (Operation, error) {
		return s.Append(0, raw, zi0ParentPage(t, c.Controller, 0, raw), OrdinaryGas)
	})
	page, e := s.Page(0, OrdinaryGas)
	if e != nil || page.Address != crypto.CreateAddress(c.Controller, 1) {
		t.Fatal("retry did not reuse actual child CREATE address", e)
	}
	h, e := s.Head(OrdinaryGas)
	if e != nil {
		t.Fatal(e)
	}
	publish(func() (Operation, error) { return s.Seal(uint32(len(raw)), h.AS0.ChainCommitment, OrdinaryGas) })
	h, e = s.Head(OrdinaryGas)
	if e != nil {
		t.Fatal(e)
	}
	publish(func() (Operation, error) { return s.CreateIndex(h.AS0.ContentCommitment, OrdinaryGas) })
	publish(func() (Operation, error) { return s.Discover(OrdinaryGas) })
	h, e = s.Head(OrdinaryGas)
	if e != nil {
		t.Fatal(e)
	}
	publish(func() (Operation, error) {
		return s.Scan(h.Index.NextEntry, h.Index.CDCursor, h.Index.Rolling, 64, OrdinaryGas)
	})
	h, e = s.Head(OrdinaryGas)
	if e != nil {
		t.Fatal(e)
	}
	publish(func() (Operation, error) {
		return s.Finish(h.Index.Count, h.Index.CDCursor, h.Index.Rolling, OrdinaryGas)
	})
	if d.syncs != 7 {
		t.Fatal("wrong actual sync count", d.syncs)
	}
	t.Log("six successful API mutations each synchronized/published; failed real DB sync restored old head and retry address")
}

func TestZI0ParentFullDiskNewProcessResume(t *testing.T) {
	const total = 20554
	owner := common.HexToAddress("0x5a4930700090")
	if dir := os.Getenv("ZI0_PARENT_FULL_RESUME"); dir != "" {
		s, e := Open(dir, owner, 4057736)
		if e != nil {
			t.Fatal(e)
		}
		defer s.Close()
		c, e := s.Creation()
		if e != nil || c.Performed || c.GasUsed != 0 {
			t.Fatal("reopen redeployed", e)
		}
		h, e := s.Head(OrdinaryGas)
		if e != nil || h.Index.Phase != 1 || h.Index.NextEntry != 10240 || h.Index.Count != total {
			t.Fatalf("bad mid-index reopen: %+v %v", h.Index, e)
		}
		syncDB := &zi0ParentSyncDB{durableDB: s.disk}
		s.disk = syncDB
		calls := 0
		for h.Index.NextEntry < h.Index.Count {
			op, e := s.Scan(h.Index.NextEntry, h.Index.CDCursor, h.Index.Rolling, 64, OrdinaryGas)
			if e != nil {
				t.Fatal(e)
			}
			calls++
			m, e := readManifest(filepath.Join(dir, manifestName))
			if e != nil || m.StateRoot != op.StateRoot {
				t.Fatal("child publication mismatch", e)
			}
			h, e = s.Head(OrdinaryGas)
			if e != nil {
				t.Fatal(e)
			}
		}
		if _, e = s.Finish(h.Index.Count, h.Index.CDCursor, h.Index.Rolling, OrdinaryGas); e != nil {
			t.Fatal(e)
		}
		calls++
		if syncDB.syncs != calls || calls != 163 {
			t.Fatalf("child actual syncs=%d calls=%d", syncDB.syncs, calls)
		}
		final, e := s.Head(OrdinaryGas)
		if e != nil {
			t.Fatal(e)
		}
		if s.indexContent != final.Index.Content || s.indexContent != final.AS0.ContentCommitment {
			t.Fatal("verified constructor binding cache differs from EVM")
		}
		raw, e := json.Marshal(final)
		if e != nil {
			t.Fatal(e)
		}
		if e = os.WriteFile(os.Getenv("ZI0_PARENT_FULL_REPORT"), raw, 0600); e != nil {
			t.Fatal(e)
		}
		return
	}
	z := zi0HarnessBuildZIP(zi0HarnessNamesN(total, 1155312), 0, nil, nil)
	dir := t.TempDir()
	s, e := Open(dir, owner, uint32(len(z.raw)))
	if e != nil {
		t.Fatal(e)
	}
	defer func() {
		if s != nil {
			s.Close()
		}
	}()
	c, e := s.Creation()
	if e != nil {
		t.Fatal(e)
	}
	for at := 0; at < len(z.raw); at += 8192 {
		end := at + 8192
		if end > len(z.raw) {
			end = len(z.raw)
		}
		b := z.raw[at:end]
		if _, e = s.Append(uint32(at), b, zi0ParentPage(t, c.Controller, uint32(at/8192), b), OrdinaryGas); e != nil {
			t.Fatal(e)
		}
	}
	h, e := s.Head(OrdinaryGas)
	if e != nil {
		t.Fatal(e)
	}
	if _, e = s.Seal(h.AS0.Cursor, h.AS0.ChainCommitment, OrdinaryGas); e != nil {
		t.Fatal(e)
	}
	h, e = s.Head(OrdinaryGas)
	if e != nil {
		t.Fatal(e)
	}
	if _, e = s.CreateIndex(h.AS0.ContentCommitment, OrdinaryGas); e != nil {
		t.Fatal(e)
	}
	if _, e = s.Discover(OrdinaryGas); e != nil {
		t.Fatal(e)
	}
	h, e = s.Head(OrdinaryGas)
	if e != nil {
		t.Fatal(e)
	}
	for h.Index.NextEntry < 10240 {
		if _, e = s.Scan(h.Index.NextEntry, h.Index.CDCursor, h.Index.Rolling, 64, OrdinaryGas); e != nil {
			t.Fatal(e)
		}
		h, e = s.Head(OrdinaryGas)
		if e != nil {
			t.Fatal(e)
		}
	}
	if e = s.Close(); e != nil {
		t.Fatal(e)
	}
	s = nil
	binary, e := os.Executable()
	if e != nil {
		t.Fatal(e)
	}
	report := filepath.Join(t.TempDir(), "child-head.json")
	cmd := exec.Command(binary, "-test.run=^TestZI0ParentFullDiskNewProcessResume$", "-test.count=1", "-test.v")
	cmd.Env = append(os.Environ(), "ZI0_PARENT_FULL_RESUME="+dir, "ZI0_PARENT_FULL_REPORT="+report)
	output, e := cmd.CombinedOutput()
	if e != nil {
		t.Fatalf("full resume child: %v\n%s", e, output)
	}
	raw, e := os.ReadFile(report)
	if e != nil {
		t.Fatal(e)
	}
	var child Head
	if e = json.Unmarshal(raw, &child); e != nil {
		t.Fatal(e)
	}
	s, e = Open(dir, owner, uint32(len(z.raw)))
	if e != nil {
		t.Fatal(e)
	}
	h, e = s.Head(OrdinaryGas)
	if e != nil || h.StateRoot != child.StateRoot || h.Index.FinalRoot != child.Index.FinalRoot || h.Index.Phase != 2 || h.Index.Count != total {
		t.Fatal("parent/child final roots differ", e)
	}
	for _, i := range []int{0, 10240, total - 1} {
		v, e := s.Lookup(z.entries[i].name, OrdinaryGas)
		if e != nil || !v.Found || v.Index != uint32(i) {
			t.Fatal("full resumed lookup differs", e)
		}
	}
	t.Logf("full20554 true new-process resume at10240, child163 actual synced mutations, root=%s index=%s", h.StateRoot, h.Index.FinalRoot)
}
