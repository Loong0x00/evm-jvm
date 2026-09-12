package cb0

import (
	"bytes"
	_ "embed"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
)

//go:embed testdata/shared-two.zip
var cb0ParentZIP []byte
var cb0ParentOwner = common.HexToAddress("0xcb00000000000000000000000000000000000901")

func cb0ParentPack(t testing.TB, types []string, values ...interface{}) []byte {
	t.Helper()
	var a abi.Arguments
	for _, n := range types {
		x, e := abi.NewType(n, "", nil)
		if e != nil {
			t.Fatal(e)
		}
		a = append(a, abi.Argument{Type: x})
	}
	b, e := a.Pack(values...)
	if e != nil {
		t.Fatal(e)
	}
	return b
}
func cb0ParentHead(t testing.TB, s *Session) Head {
	t.Helper()
	h, e := s.Head(OrdinaryGas)
	if e != nil {
		t.Fatal(e)
	}
	return h
}
func cb0ParentUpload(t testing.TB, s *Session) {
	t.Helper()
	cb0ParentLoad(t, s, cb0ParentZIP, []string{"SharedEntry.class", "SharedHelper.class"})
}
func cb0ParentLoad(t testing.TB, s *Session, rawZIP []byte, names []string) {
	t.Helper()
	init, e := s.Initialization()
	if e != nil {
		t.Fatal(e)
	}
	for at := int(cb0ParentHead(t, s).AS0.Cursor); at < len(rawZIP); at += 8192 {
		end := at + 8192
		if end > len(rawZIP) {
			end = len(rawZIP)
		}
		raw := rawZIP[at:end]
		pi := crypto.Keccak256Hash(cb0ParentPack(t, []string{"bytes32", "address", "uint32", "uint32", "bytes32"}, crypto.Keccak256Hash([]byte("MC-AS0/page/v1")), init.AS0Creation.Controller, uint32(at/8192), uint32(len(raw)), crypto.Keccak256Hash(raw)))
		if _, e = s.Append(uint32(at), raw, pi, OrdinaryGas); e != nil {
			t.Fatal(e)
		}
	}
	h := cb0ParentHead(t, s)
	if !h.AS0.Sealed {
		if _, e = s.Seal(h.AS0.Cursor, h.AS0.ChainCommitment, OrdinaryGas); e != nil {
			t.Fatal(e)
		}
	}
	h = cb0ParentHead(t, s)
	if h.Index.Address == (common.Address{}) {
		if _, e = s.CreateIndex(h.AS0.ContentCommitment, OrdinaryGas); e != nil {
			t.Fatal(e)
		}
	}
	if cb0ParentHead(t, s).Index.Phase == 0 {
		if _, e = s.DiscoverIndex(OrdinaryGas); e != nil {
			t.Fatal(e)
		}
	}
	for h = cb0ParentHead(t, s); h.Index.NextEntry < h.Index.Count; h = cb0ParentHead(t, s) {
		if _, e = s.ScanIndex(h.Index.NextEntry, h.Index.CDCursor, h.Index.Rolling, 64, OrdinaryGas); e != nil {
			t.Fatal(e)
		}
	}
	if h.Index.Phase != 2 {
		if _, e = s.FinishIndex(h.Index.Count, h.Index.CDCursor, h.Index.Rolling, OrdinaryGas); e != nil {
			t.Fatal(e)
		}
	}
	for slot, name := range names {
		h = cb0ParentHead(t, s)
		if len(h.Decoders) <= slot {
			if _, e = s.CreateDecoder(uint8(slot), h.Index.FinalRoot, []byte(name), OrdinaryGas); e != nil {
				t.Fatal(e)
			}
		}
		for h = cb0ParentHead(t, s); h.Decoders[slot].Phase == 1; h = cb0ParentHead(t, s) {
			if _, e = s.StepDecoder(uint8(slot), h.Decoders[slot].Work, 128, OrdinaryGas); e != nil {
				t.Fatal(e)
			}
		}
		for h = cb0ParentHead(t, s); h.Decoders[slot].Phase != 4; h = cb0ParentHead(t, s) {
			if _, e = s.PublishDecoder(uint8(slot), h.Decoders[slot].PublishedPages, h.Decoders[slot].PublicationRolling, 1, OrdinaryGas); e != nil {
				t.Fatal(e)
			}
		}
	}
}
func cb0ParentPackage(t testing.TB, s *Session, slots []uint8) ([]ResourceBinding, common.Hash) {
	t.Helper()
	return cb0ParentPackageNamed(t, s, slots, []string{"SharedEntry.class", "SharedHelper.class"})
}
func cb0ParentPackageNamed(t testing.TB, s *Session, slots []uint8, names []string) ([]ResourceBinding, common.Hash) {
	t.Helper()
	h := cb0ParentHead(t, s)
	addr := crypto.CreateAddress(cb0ParentOwner, uint64(2+len(h.Decoders)))
	H := crypto.Keccak256Hash
	roll := H(cb0ParentPack(t, []string{"bytes32", "address", "address", "address", "bytes32", "bytes32", "bytes32", "uint8"}, H([]byte("MC-CB0/package/v1")), addr, cb0ParentOwner, cb0EngineAddress, cb0VFSCode, cb0DI0Code, cb0ZI0Code, uint8(len(slots))))
	var refs []ResourceBinding
	var total uint32
	for i, slot := range slots {
		d := h.Decoders[slot]
		raw := []byte(names[slot])
		refs = append(refs, ResourceBinding{slot, raw, d.IndexRoot, d.FinalRoot})
		total += d.PlainSize
		roll = H(cb0ParentPack(t, []string{"bytes32", "bytes32", "uint8", "address", "bytes32", "bytes32", "bytes32", "uint32"}, H([]byte("MC-CB0/resource/v1")), roll, uint8(i), d.Address, H(raw), d.IndexRoot, d.FinalRoot, d.PlainSize))
	}
	return refs, H(cb0ParentPack(t, []string{"bytes32", "bytes32", "uint32", "address", "bytes32"}, H([]byte("MC-CB0/package/v1")), roll, total, h.Index.Address, h.Index.FinalRoot))
}
func cb0ParentReady(t testing.TB, dir string, slots []uint8) *Session {
	t.Helper()
	var s *Session
	var e error
	if dir == "" {
		s, e = NewMemory(cb0ParentOwner, uint32(len(cb0ParentZIP)))
	} else {
		s, e = Open(dir, cb0ParentOwner, uint32(len(cb0ParentZIP)))
	}
	if e != nil {
		t.Fatal(e)
	}
	t.Cleanup(func() { s.Close() })
	cb0ParentUpload(t, s)
	refs, pkg := cb0ParentPackage(t, s, slots)
	if _, e = s.CreateCoordinator(common.Hash{}, refs, pkg, OrdinaryGas); e != nil {
		t.Fatalf("legal ordered package %v: %v", slots, e)
	}
	h := cb0ParentHead(t, s)
	if int(h.Coordinator.ClassCount) != len(slots) {
		t.Fatal("wrong package count")
	}
	return s
}
func TestCB0ParentGeneratedJavaPipeline(t *testing.T) {
	for _, slots := range [][]uint8{{0, 1}, {1, 0}, {0}} {
		t.Run(fmt.Sprint(slots), func(t *testing.T) {
			s := cb0ParentReady(t, "", slots)
			h := cb0ParentHead(t, s)
			if len(slots) == 1 {
				return
			} // Constructor subset is legal; execution would lack helper.
			entry := uint8(0)
			if slots[0] == 1 {
				entry = 1
			}
			r, e := s.Start(h.Coordinator.PackageRoot, entry, "run", []int32{7}, 7, 4096, OrdinaryGas)
			if e != nil {
				t.Fatal(e)
			}
			for r.Slice.Lifecycle == 1 {
				r, e = s.Resume(h.Coordinator.PackageRoot, r.Slice.Epoch, r.Slice.CheckpointRoot, r.Checkpoint, 7, 4096, OrdinaryGas)
				if e != nil {
					t.Fatal(e)
				}
			}
			if r.Slice.Lifecycle != 2 || r.Slice.Result != 317 || r.Slice.TotalJvmSteps != 36 || r.Slice.TotalInternalSteps != 5 {
				t.Fatalf("wrong actual Java: %+v", r.Slice)
			}
			cp, e := s.ReadCheckpoint(r.Slice.CheckpointRoot)
			if e != nil || !bytes.Equal(cp, r.Checkpoint) {
				t.Fatalf("terminal blob: %v", e)
			}
		})
	}
}
func TestCB0ParentMetadataBeforeDB(t *testing.T) {
	dir := t.TempDir()
	s, e := Open(dir, cb0ParentOwner, 1)
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	path := filepath.Join(dir, cb0ManifestName)
	raw, e := os.ReadFile(path)
	if e != nil {
		t.Fatal(e)
	}
	var m cb0Manifest
	if e = json.Unmarshal(raw, &m); e != nil {
		t.Fatal(e)
	}
	m.Context = "wrong"
	b, _ := json.Marshal(m)
	if e = os.WriteFile(path, b, 0600); e != nil {
		t.Fatal(e)
	}
	defer os.WriteFile(path, raw, 0600)
	other, e := Open(dir, cb0ParentOwner, 1)
	if other != nil {
		other.Close()
	}
	if e == nil || !strings.Contains(e.Error(), "manifest") {
		t.Fatalf("invalid metadata reached locked DB: %v", e)
	}
}
func TestCB0ParentMarkerAndNestedLinks(t *testing.T) {
	for _, kind := range []string{"marker", "link"} {
		t.Run(kind, func(t *testing.T) {
			dir := t.TempDir()
			s, e := Open(dir, cb0ParentOwner, 1)
			if e != nil {
				t.Fatal(e)
			}
			s.Close()
			if kind == "marker" {
				e = os.WriteFile(filepath.Join(dir, cb0MarkerName), []byte("foreign namespace\n"), 0600)
			} else {
				path := filepath.Join(dir, cb0StateDirectory, "CURRENT")
				e = os.Rename(path, path+".saved")
				if e == nil {
					e = os.Symlink(path+".saved", path)
				}
			}
			if e != nil {
				t.Fatal(e)
			}
			other, e := Open(dir, cb0ParentOwner, 1)
			if other != nil {
				other.Close()
			}
			if e == nil {
				t.Fatal("foreign/linked state accepted")
			}
		})
	}
}
func TestCB0ParentChild(t *testing.T) {
	stage := os.Getenv("CB0_PARENT_STAGE")
	if stage == "" {
		t.Skip("child entry")
	}
	dir := os.Getenv("CB0_PARENT_DIR")
	s, e := Open(dir, cb0ParentOwner, uint32(len(cb0ParentZIP)))
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	init, _ := s.Initialization()
	if stage != "input" && (init.EngineInstalled || init.AS0Creation.Performed || init.AS0Creation.GasUsed != 0) {
		t.Fatal("reopen reports reinstall/CREATE")
	}
	h := cb0ParentHead(t, s)
	switch stage {
	case "input":
		raw := cb0ParentZIP
		pi := crypto.Keccak256Hash(cb0ParentPack(t, []string{"bytes32", "address", "uint32", "uint32", "bytes32"}, crypto.Keccak256Hash([]byte("MC-AS0/page/v1")), h.AS0.Controller, uint32(0), uint32(len(raw)), crypto.Keccak256Hash(raw)))
		_, e = s.Append(0, raw, pi, OrdinaryGas)
	case "index":
		if h.AS0.Sealed || h.AS0.Cursor != uint32(len(cb0ParentZIP)) {
			t.Fatal("not input-stage reopen")
		}
		if _, e = s.Seal(h.AS0.Cursor, h.AS0.ChainCommitment, OrdinaryGas); e == nil {
			h = cb0ParentHead(t, s)
			_, e = s.CreateIndex(h.AS0.ContentCommitment, OrdinaryGas)
		}
		if e == nil {
			_, e = s.DiscoverIndex(OrdinaryGas)
		}
	case "decode":
		if h.Index.Phase != 1 {
			t.Fatal("not index-stage reopen")
		}
		for h.Index.NextEntry < h.Index.Count {
			if _, e = s.ScanIndex(h.Index.NextEntry, h.Index.CDCursor, h.Index.Rolling, 64, OrdinaryGas); e != nil {
				t.Fatal(e)
			}
			h = cb0ParentHead(t, s)
		}
		if _, e = s.FinishIndex(h.Index.Count, h.Index.CDCursor, h.Index.Rolling, OrdinaryGas); e == nil {
			h = cb0ParentHead(t, s)
			_, e = s.CreateDecoder(0, h.Index.FinalRoot, []byte("SharedEntry.class"), OrdinaryGas)
		}
		if e == nil {
			_, e = s.StepDecoder(0, 0, 1, OrdinaryGas)
		}
	case "ready":
		if len(h.Decoders) != 1 || h.Decoders[0].Phase != 1 || h.Decoders[0].Work != 1 {
			t.Fatal("not live decode-stage reopen")
		}
		cb0ParentUpload(t, s)
		refs, p := cb0ParentPackage(t, s, []uint8{0, 1})
		_, e = s.CreateCoordinator(common.Hash{}, refs, p, OrdinaryGas)
	}
	if e != nil {
		t.Fatal(e)
	}
	if stage == "input" || stage == "index" || stage == "decode" || stage == "ready" {
		t.Logf("stage%s pid%d state%s", stage, os.Getpid(), cb0ParentHead(t, s).StateRoot)
		return
	}
	if stage == "final" {
		cp, e := s.ReadCheckpoint(h.Java.CheckpointRoot)
		if e != nil || crypto.Keccak256Hash(cp) != h.Java.CheckpointRoot || h.Java.Lifecycle != 2 {
			t.Fatal("terminal reopen blob")
		}
		return
	}
	var r JavaResult
	if stage == "start" {
		r, e = s.Start(h.Coordinator.PackageRoot, 0, "run", []int32{7}, 7, 4096, OrdinaryGas)
	} else {
		cp, x := s.ReadCheckpoint(h.Java.CheckpointRoot)
		if x != nil {
			t.Fatal(x)
		}
		r, e = s.Resume(h.Coordinator.PackageRoot, h.Java.Epoch, h.Java.CheckpointRoot, cp, 7, 4096, OrdinaryGas)
	}
	if e != nil {
		t.Fatal(e)
	}
	if stage == "finish" {
		for r.Slice.Lifecycle == 1 {
			r, e = s.Resume(h.Coordinator.PackageRoot, r.Slice.Epoch, r.Slice.CheckpointRoot, r.Checkpoint, 7, 4096, OrdinaryGas)
			if e != nil {
				t.Fatal(e)
			}
		}
		if r.Slice.Result != 317 {
			t.Fatal("guest result")
		}
	}
	t.Logf("stage%s pid%d epoch%d state=%s", stage, os.Getpid(), r.Slice.Epoch, r.StateRoot)
}
func TestCB0ParentActualNewProcesses(t *testing.T) {
	exe, e := os.Executable()
	if e != nil {
		t.Fatal(e)
	}
	base := t.TempDir()
	dir := filepath.Join(base, "world")
	seen := map[int]bool{os.Getpid(): true}
	for _, stage := range []string{"input", "index", "decode", "ready", "start", "resume", "finish", "final"} {
		cmd := exec.Command(exe, "-test.v", "-test.run=^TestCB0ParentChild$", "-test.timeout=2m")
		cmd.Dir = base
		cmd.Env = append(os.Environ(), "CB0_PARENT_STAGE="+stage, "CB0_PARENT_DIR="+dir)
		out, e := cmd.CombinedOutput()
		if cmd.Process == nil || seen[cmd.Process.Pid] {
			t.Fatal("not distinct child process")
		}
		seen[cmd.Process.Pid] = true
		t.Logf("actual child pid%d stage%s", cmd.Process.Pid, stage)
		t.Logf("%s", out)
		if e != nil {
			t.Fatalf("stage%s: %v", stage, e)
		}
	}
}
