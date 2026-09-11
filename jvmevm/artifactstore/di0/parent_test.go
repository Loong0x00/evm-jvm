package di0

import (
	"bytes"
	"compress/flate"
	"encoding/binary"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"testing"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
)

// Parent independently constructs raw stored DEFLATE, not ZIP method0. Its pending
// LEN is a block byte count (up to65535), NOT a Huffman match length/distance pair.
func di0ParentStored(t *testing.T, n int) di0HarnessZIP {
	t.Helper()
	plain := make([]byte, n)
	for i := range plain {
		plain[i] = byte(i*73 + 11)
	}
	raw := []byte{1, 0, 0, 0, 0}
	binary.LittleEndian.PutUint16(raw[1:3], uint16(n))
	binary.LittleEndian.PutUint16(raw[3:5], ^uint16(n))
	raw = append(raw, plain...)
	rd := flate.NewReader(bytes.NewReader(raw))
	out, e := io.ReadAll(rd)
	rd.Close()
	if e != nil || !bytes.Equal(out, plain) {
		t.Fatalf("invalid parent positive fixture: %v", e)
	}
	return di0HarnessZIPPayload([]byte("parent-stored"), plain, raw, 8)
}
func TestDI0ParentStoredBlockPendingHeadAndReopen(t *testing.T) {
	z := di0ParentStored(t, 65535)
	dir := t.TempDir()
	owner := common.HexToAddress("0xd1009001")
	s, e := Open(dir, owner, uint32(len(z.raw)))
	if e != nil {
		t.Fatal(e)
	}
	defer func() {
		if s != nil {
			s.Close()
		}
	}()
	di0HarnessUpload(t, s, z.raw)
	di0HarnessFinishIndex(t, s)
	di0HarnessCreate(t, s, z.name)
	op, e := s.Step(0, 1, OrdinaryGas)
	if e != nil || op.StateRoot == (common.Hash{}) {
		t.Fatalf("legal stored header failed: %+v %v", op, e)
	}
	h, e := s.Head(OrdinaryGas)
	if e != nil {
		t.Fatalf("successful EVM stored header is unroutable via Head: %v", e)
	}
	if h.Decoder.BlockMode != 1 || h.Decoder.PendingLength != 65535 || h.Decoder.PendingDistance != 0 || h.Decoder.OutputCount != 0 {
		t.Fatalf("stored header: %+v", h.Decoder)
	}
	saved := s.root
	if e = s.Close(); e != nil {
		t.Fatal(e)
	}
	s = nil
	s, e = Open(dir, owner, uint32(len(z.raw)))
	if e != nil {
		t.Fatalf("reopen legal stored pending state: %v", e)
	}
	if s.root != saved {
		t.Fatal("reopen altered trie root")
	}
	h = di0HarnessDecode(t, s, 128)
	h = di0HarnessPublish(t, s)
	for at := uint32(0); at < uint32(len(z.plain)); {
		n := MaxRead
		if n > uint32(len(z.plain))-at {
			n = uint32(len(z.plain)) - at
		}
		r, e := s.Read(at, n, OrdinaryGas)
		if e != nil || !bytes.Equal(r.Bytes, z.plain[at:at+n]) {
			t.Fatalf("read %d: %v", at, e)
		}
		at += n
	}
	if h.Decoder.Phase != 4 {
		t.Fatal("not final")
	}
}

// These stages run in distinct OS processes using the embedded real artifact.
// The older worker test only Close/Open'ed within one process despite its name.
type di0ParentProcessReceipt struct {
	PID      int
	Root     common.Hash
	Resource common.Hash
	Work     uint32
	Phase    uint8
	Pages    uint8
}

func di0ParentProcessZIP(t *testing.T, kind string) di0HarnessZIP {
	if kind == "stored" {
		return di0ParentStored(t, 65535)
	}
	plain := bytes.Repeat([]byte("parent dynamic cached table state\n"), 3000)[:90309]
	comp := di0HarnessDeflate(t, plain)
	if (comp[0]>>1)&3 != 2 {
		t.Fatal("parent fixture must exercise dynamic tables")
	}
	return di0HarnessZIPPayloadPrefix(9000, []byte("parent-dynamic"), plain, comp, 8)
}
func TestDI0ParentProcessChild(t *testing.T) {
	stageText := os.Getenv("DI0_PARENT_STAGE")
	if stageText == "" {
		t.Skip("child process entry only")
	}
	stage, e := strconv.Atoi(stageText)
	if e != nil {
		t.Fatal(e)
	}
	z := di0ParentProcessZIP(t, os.Getenv("DI0_PARENT_KIND"))
	owner := common.HexToAddress("0xd1009002")
	s, e := Open(os.Getenv("DI0_PARENT_DIR"), owner, uint32(len(z.raw)))
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	cr, e := s.Creation()
	if e != nil {
		t.Fatal(e)
	}
	if stage == 0 {
		if !cr.Performed || cr.GasUsed == 0 {
			t.Fatal("missing fresh ordinary CREATE")
		}
	} else {
		if cr.Performed || cr.GasUsed != 0 || s.root != common.HexToHash(os.Getenv("DI0_PARENT_ROOT")) {
			t.Fatal("new process redeployed or changed durable root")
		}
	}
	head := func() Head {
		h, e := s.Head(OrdinaryGas)
		if e != nil {
			t.Fatal(e)
		}
		return h
	}
	h := head()
	switch stage {
	case 0:
		raw := z.raw[:8192]
		_, e = s.Append(0, raw, di0HarnessPageCommitment(t, cr.Controller, 0, raw), OrdinaryGas)
	case 1:
		if h.AS0.Cursor != 8192 || h.Index.Address != (common.Address{}) {
			t.Fatal("mid-upload state")
		}
		di0HarnessUpload(t, s, z.raw)
		h = head()
		_, e = s.Seal(h.AS0.Cursor, h.AS0.ChainCommitment, OrdinaryGas)
		if e != nil {
			t.Fatal(e)
		}
		h = head()
		_, e = s.CreateIndex(h.AS0.ContentCommitment, OrdinaryGas)
		if e != nil {
			t.Fatal(e)
		}
		_, e = s.DiscoverIndex(OrdinaryGas)
	case 2:
		if h.Index.Phase != 1 || h.Index.NextEntry != 0 {
			t.Fatal("mid-index state")
		}
		_, e = s.ScanIndex(h.Index.NextEntry, h.Index.CDCursor, h.Index.Rolling, 1, OrdinaryGas)
		if e != nil {
			t.Fatal(e)
		}
		h = head()
		_, e = s.FinishIndex(h.Index.Count, h.Index.CDCursor, h.Index.Rolling, OrdinaryGas)
		if e != nil {
			t.Fatal(e)
		}
		di0HarnessCreate(t, s, z.name)
		_, e = s.Step(0, 1, OrdinaryGas)
	case 3:
		if h.Decoder.Work != 1 || h.Decoder.Phase != 1 {
			t.Fatal("mid-header state")
		}
		if os.Getenv("DI0_PARENT_KIND") == "stored" {
			if h.Decoder.BlockMode != 1 || h.Decoder.PendingLength != 65535 {
				t.Fatal("stored LEN lost")
			}
		} else {
			if h.Decoder.BlockMode != 2 || h.Decoder.FixedBlock {
				t.Fatal("dynamic table not persisted")
			}
		}
		h = di0HarnessDecode(t, s, 128)
		if h.Decoder.Phase != 2 {
			t.Fatal("not VERIFIED")
		}
	case 4:
		if h.Decoder.Phase != 2 {
			t.Fatal("VERIFIED reopen")
		}
		_, e = s.Publish(0, h.Decoder.PublicationRolling, 1, OrdinaryGas)
	case 5:
		if h.Decoder.Phase != 3 || h.Decoder.PublishedPages != 1 {
			t.Fatal("mid-publication reopen")
		}
		di0HarnessPublish(t, s)
	case 6:
		if h.Decoder.Phase != 4 {
			t.Fatal("FINAL reopen")
		}
		for at := uint32(0); at < uint32(len(z.plain)); {
			n := MaxRead
			if n > uint32(len(z.plain))-at {
				n = uint32(len(z.plain)) - at
			}
			r, x := s.Read(at, n, OrdinaryGas)
			if x != nil || !bytes.Equal(r.Bytes, z.plain[at:at+n]) {
				t.Fatalf("read %d: %v", at, x)
			}
			at += n
		}
	default:
		t.Fatal("unknown stage")
	}
	if e != nil {
		t.Fatal(e)
	}
	h = head()
	r := di0ParentProcessReceipt{os.Getpid(), s.root, h.Decoder.FinalRoot, h.Decoder.Work, h.Decoder.Phase, h.Decoder.PublishedPages}
	b, _ := json.Marshal(r)
	if e = os.WriteFile(os.Getenv("DI0_PARENT_REPORT"), b, 0600); e != nil {
		t.Fatal(e)
	}
	if e = s.Close(); e != nil {
		t.Fatal(e)
	}
}
func TestDI0ParentTrueNewProcessChains(t *testing.T) {
	exe, e := os.Executable()
	if e != nil {
		t.Fatal(e)
	}
	for _, kind := range []string{"stored", "dynamic"} {
		t.Run(kind, func(t *testing.T) {
			base := t.TempDir()
			dir := filepath.Join(base, "state")
			pids := map[int]bool{}
			var last di0ParentProcessReceipt
			for stage := 0; stage <= 6; stage++ {
				report := filepath.Join(base, fmt.Sprintf("stage-%d.json", stage))
				cmd := exec.Command(exe, "-test.run=^TestDI0ParentProcessChild$", "-test.timeout=2m")
				cmd.Dir = base // No source checkout/runtime files in the child working directory.
				cmd.Env = append(os.Environ(), "DI0_PARENT_STAGE="+strconv.Itoa(stage), "DI0_PARENT_KIND="+kind, "DI0_PARENT_DIR="+dir, "DI0_PARENT_ROOT="+last.Root.Hex(), "DI0_PARENT_REPORT="+report)
				out, e := cmd.CombinedOutput()
				if e != nil {
					t.Fatalf("stage%d: %v\n%s", stage, e, out)
				}
				b, e := os.ReadFile(report)
				if e != nil {
					t.Fatal(e)
				}
				var r di0ParentProcessReceipt
				if e = json.Unmarshal(b, &r); e != nil {
					t.Fatal(e)
				}
				if r.PID == os.Getpid() || pids[r.PID] {
					t.Fatal("not a distinct child process")
				}
				pids[r.PID] = true
				if stage == 6 && (r.Root != last.Root || r.Resource != last.Resource) {
					t.Fatal("FINAL readonly reopen changed commitments")
				}
				t.Logf("stage%d pid%d work%d phase%d pages%d trie=%s resource=%s", stage, r.PID, r.Work, r.Phase, r.Pages, r.Root, r.Resource)
				last = r
			}
		})
	}
}

// Counts completed REAL underlying code/trie synchronizations, then optionally
// reports a failure. This is not a mock replacing disk synchronization.
type di0ParentSyncDB struct {
	durableDB
	count int
	fail  bool
}

func (d *di0ParentSyncDB) SyncKeyValue() error {
	e := d.durableDB.SyncKeyValue()
	if e != nil {
		return e
	}
	d.count++
	if d.fail {
		return errors.New("parent after actual disk sync")
	}
	return nil
}
func TestDI0ParentOutputPublicationFailureMatrix(t *testing.T) {
	for _, kind := range []string{"EVM-CREATE", "sync-return", "after-trie", "before-manifest", "after-rename"} {
		t.Run(kind, func(t *testing.T) {
			z := di0HarnessZIP1(t, []byte("page-fault"), bytes.Repeat([]byte("Z"), 9000), 0)
			dir := t.TempDir()
			owner := common.HexToAddress("0xd1009003")
			s, e := Open(dir, owner, uint32(len(z.raw)))
			if e != nil {
				t.Fatal(e)
			}
			defer func() { s.Close() }()
			di0HarnessUpload(t, s, z.raw)
			di0HarnessFinishIndex(t, s)
			di0HarnessCreate(t, s, z.name)
			h := di0HarnessDecode(t, s, 128)
			old := s.root
			before := s.state.Copy().IntermediateRoot(true)
			child := crypto.CreateAddress(s.decoderAddress, 1)
			disk := &di0ParentSyncDB{durableDB: s.disk}
			s.disk = disk
			gas := OrdinaryGas
			switch kind {
			case "EVM-CREATE":
				gas = 7400000
			case "sync-return":
				disk.fail = true
			default:
				s.testFault = func(p faultPoint) error {
					if (kind == "after-trie" && p == faultAfterTrie) || (kind == "before-manifest" && p == faultBeforeManifest) || (kind == "after-rename" && p == faultAfterManifestRename) {
						return errors.New("parent publication point")
					}
					return nil
				}
			}
			op, e := s.Publish(0, h.Decoder.PublicationRolling, 1, gas)
			if e == nil || op.GasUsed == 0 || op.StateRoot != (common.Hash{}) || op.CreatedAddress != (common.Address{}) || len(op.Logs) != 0 {
				t.Fatalf("failed receipt: %+v %v", op, e)
			}
			if kind == "EVM-CREATE" {
				di0HarnessError(t, op, 30)
				if disk.count != 0 {
					t.Fatal("EVM failure was durably published")
				}
			} else {
				if len(op.RevertData) != 0 || disk.count != 1 {
					t.Fatalf("publication failure did not follow exactly one actual sync: %+v count%d", op, disk.count)
				}
			}
			disk.fail = false
			s.testFault = nil
			if kind == "after-rename" {
				if s.poison == nil {
					t.Fatal("ambiguous rename not poisoned")
				}
				if _, e = s.Head(OrdinaryGas); e == nil {
					t.Fatal("poisoned Head succeeded")
				}
				if _, e = s.Read(0, 1, OrdinaryGas); e == nil {
					t.Fatal("poisoned Read succeeded")
				}
				if e = s.Close(); e != nil {
					t.Fatal(e)
				}
				s, e = Open(dir, owner, uint32(len(z.raw)))
				if e != nil {
					t.Fatal(e)
				}
				h, e = s.Head(OrdinaryGas)
				if e != nil || h.Decoder.Phase != 3 || h.Decoder.PublishedPages != 1 || s.root == old {
					t.Fatalf("renamed root not reopened: %+v %v", h, e)
				}
			} else {
				m, e := readManifest(filepath.Join(dir, manifestName))
				if e != nil {
					t.Fatal(e)
				}
				if m.StateRoot != old || s.root != old || s.state.Copy().IntermediateRoot(true) != before || s.state.GetNonce(s.decoderAddress) != 1 || len(s.state.GetCode(child)) != 0 {
					t.Fatal("failed page publication changed committed root/nonce/child")
				}
				op, e = s.Publish(0, h.Decoder.PublicationRolling, 1, OrdinaryGas)
				if e != nil || op.StateRoot == (common.Hash{}) {
					t.Fatalf("page retry: %+v %v", op, e)
				}
			}
			h = di0HarnessPublish(t, s)
			p, e := s.Page(0, OrdinaryGas)
			if e != nil || p.Address != child || p.Length != 8192 {
				t.Fatalf("same-child publication: %+v %v", p, e)
			}
			if h.Decoder.Phase != 4 {
				t.Fatal("not final after retry")
			}
		})
	}
}
func TestDI0ParentPlainSizeFrontiersThroughTransport(t *testing.T) {
	for _, n := range []int{0, 90309, 158794, 262144, 262145} {
		t.Run(strconv.Itoa(n), func(t *testing.T) {
			plain := bytes.Repeat([]byte{0xa7}, n)
			name := []byte{0, 0xff, '/', '.', '.'}
			z := di0HarnessZIP1(t, name, plain, 8)
			owner := common.HexToAddress("0xd1009004")
			s, e := NewMemory(owner, uint32(len(z.raw)))
			if e != nil {
				t.Fatal(e)
			}
			defer s.Close()
			di0HarnessUpload(t, s, z.raw)
			h := di0HarnessFinishIndex(t, s)
			old := s.root
			op, e := s.CreateDecoder(h.Index.FinalRoot, name, OrdinaryGas)
			if n > int(MaxOutput) {
				if e == nil {
					t.Fatal("overcap accepted")
				}
				di0HarnessError(t, op, 5)
				if s.root != old || s.decoderAddress != (common.Address{}) {
					t.Fatal("overcap changed root/route")
				}
				return
			}
			if e != nil {
				t.Fatal(e)
			}
			di0HarnessDecode(t, s, 128)
			h = di0HarnessPublish(t, s)
			if h.Decoder.OutputCount != uint32(n) || h.Decoder.PublishedPages != uint8((n+8191)/8192) || h.Decoder.FinalRoot == (common.Hash{}) {
				t.Fatalf("size head: %+v", h.Decoder)
			}
			for at := uint32(0); at < uint32(n); {
				nn := MaxRead
				if nn > uint32(n)-at {
					nn = uint32(n) - at
				}
				r, e := s.Read(at, nn, OrdinaryGas)
				if e != nil || !bytes.Equal(r.Bytes, plain[at:at+nn]) {
					t.Fatalf("read %d: %v", at, e)
				}
				at += nn
			}
			r, e := s.Read(uint32(n), 0, OrdinaryGas)
			if e != nil || len(r.Bytes) != 0 {
				t.Fatal("zero length EOF read")
			}
			if _, e = s.Read(uint32(n), 1, OrdinaryGas); e == nil {
				t.Fatal("read beyond EOF")
			}
			if _, e = s.Read(0, 4097, OrdinaryGas); e == nil {
				t.Fatal("oversized read")
			}
			if _, e = s.Page(h.Decoder.PublishedPages, OrdinaryGas); e == nil {
				t.Fatal("page beyond end")
			}
		})
	}
}

func TestDI0ParentStoredHeadValidationNotRelaxedForOtherModes(t *testing.T) {
	z := di0ParentStored(t, 65535)
	s, _ := di0HarnessPrepared(t, z, common.HexToAddress("0xd1009005"))
	defer s.Close()
	if _, e := s.Step(0, 1, OrdinaryGas); e != nil {
		t.Fatal(e)
	}
	original := s.state
	// TEST-only copied-state corruption; not a live ownership bypass claim.
	// Slot/offsets are pinned by the final artifact storage-layout hash.
	for _, c := range []struct {
		name string
		slot byte
		edit func(*common.Hash)
	}{
		{"stored-has-distance", 12, func(w *common.Hash) { w[25] = 1 }},
		{"stored-fixed-flag", 12, func(w *common.Hash) { w[18] = 1 }},
		{"stored-bit-offset", 12, func(w *common.Hash) { w[23] = 1 }},
		{"large-huffman-match", 12, func(w *common.Hash) { w[20] = 2; w[25] = 1 }},
		{"pending-at-header", 12, func(w *common.Hash) { w[20] = 0 }},
		{"method0-with-stored-state", 12, func(w *common.Hash) { w[22] = 0 }},
		{"premature-publication-root", 9, func(w *common.Hash) { w[31] = 1 }},
	} {
		t.Run(c.name, func(t *testing.T) {
			s.state = original.Copy()
			defer func() { s.state = original }()
			key := common.BytesToHash([]byte{c.slot})
			word := s.state.GetState(s.decoderAddress, key)
			c.edit(&word)
			s.state.SetState(s.decoderAddress, key, word)
			if _, e := s.Head(OrdinaryGas); e == nil {
				t.Fatal("copied impossible state accepted")
			}
		})
	}
	if _, e := s.Head(OrdinaryGas); e != nil {
		t.Fatalf("legal original rejected: %v", e)
	}
}
