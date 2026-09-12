package cb0

import (
	"archive/zip"
	"bytes"
	_ "embed"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/ethereum/go-ethereum/core/types"
	"io"
	"os"
	"path/filepath"
	"sync"
	"testing"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
)

//go:embed testdata/boundary-seven.zip
var cb0ParentBoundaryZIP []byte

//go:embed testdata/fault.zip
var cb0ParentFaultZIP []byte

type cb0ParentDisk struct {
	cb0Disk
	syncs int
	fail  bool
}

func (d *cb0ParentDisk) SyncKeyValue() error {
	e := d.cb0Disk.SyncKeyValue()
	if e != nil {
		return e
	}
	d.syncs++
	if d.fail {
		return errors.New("parent after actual DB sync")
	}
	return nil
}

func TestCB0ParentJavaPublicationFailures(t *testing.T) {
	for _, which := range []string{"blob", "sync", "trie", "manifest", "rename"} {
		t.Run(which, func(t *testing.T) {
			dir := t.TempDir()
			s := cb0ParentReady(t, dir, []uint8{0, 1})
			defer func() { s.Close() }()
			h := cb0ParentHead(t, s)
			first, e := s.Start(h.Coordinator.PackageRoot, 0, "run", []int32{7}, 7, 4096, OrdinaryGas)
			if e != nil {
				t.Fatal(e)
			}
			if len(first.Logs) != 1 || first.Logs[0].Address != cb0EngineAddress {
				t.Fatal("nested checkpoint event not returned")
			}
			old := s.root
			oldHead := s.javaHead
			before := s.state.Copy().IntermediateRoot(true)
			d := &cb0ParentDisk{cb0Disk: s.disk}
			s.disk = d
			point := map[string]cb0FaultPoint{"blob": cb0FaultAfterBlob, "trie": cb0FaultAfterTrie, "manifest": cb0FaultBeforeManifest, "rename": cb0FaultAfterRename}[which]
			d.fail = which == "sync"
			s.testFault = func(p cb0FaultPoint) error {
				if p == point {
					return errors.New("parent injected publication fault")
				}
				return nil
			}
			bad, e := s.Resume(h.Coordinator.PackageRoot, first.Slice.Epoch, first.Slice.CheckpointRoot, first.Checkpoint, 7, 4096, OrdinaryGas)
			if e == nil || bad.GasUsed == 0 || bad.Slice.Schema != 0 || bad.StateRoot != (common.Hash{}) || len(bad.Checkpoint) != 0 || len(bad.Logs) != 0 || len(bad.RevertData) != 0 {
				t.Fatalf("leaked failed receipt: %+v %v", bad, e)
			}
			if which == "blob" {
				if d.syncs != 0 {
					t.Fatal("blob-stage failure had DB sync")
				}
			} else {
				if d.syncs != 1 {
					t.Fatalf("actual DB sync count%d", d.syncs)
				}
			}
			d.fail = false
			s.testFault = nil
			if which == "rename" {
				if s.poison == nil {
					t.Fatal("postrename not poisoned")
				}
				if _, e = s.ReadCheckpoint(oldHead); e == nil {
					t.Fatal("poisoned read")
				}
				if _, e = s.Head(OrdinaryGas); e == nil {
					t.Fatal("poisoned Head")
				}
				s.Close()
				s, e = Open(dir, cb0ParentOwner, uint32(len(cb0ParentZIP)))
				if e != nil {
					t.Fatal(e)
				}
				next := cb0ParentHead(t, s)
				if next.Java.Epoch != first.Slice.Epoch+1 || s.root == old {
					t.Fatal("new durable Java anchor not reopened")
				}
			} else {
				m, e := cb0ReadManifest(filepath.Join(dir, cb0ManifestName))
				if e != nil {
					t.Fatal(e)
				}
				if s.root != old || s.javaHead != oldHead || m.StateRoot != old || m.JavaHead != oldHead || s.state.Copy().IntermediateRoot(true) != before {
					t.Fatal("old Java root/anchor/manifest not restored")
				}
				cp, e := s.ReadCheckpoint(oldHead)
				if e != nil || !bytes.Equal(cp, first.Checkpoint) {
					t.Fatal("old checkpoint not retained")
				}
				retry, e := s.Resume(h.Coordinator.PackageRoot, first.Slice.Epoch, first.Slice.CheckpointRoot, cp, 7, 4096, OrdinaryGas)
				if e != nil || retry.Slice.Epoch != first.Slice.Epoch+1 || len(retry.Logs) != 1 {
					t.Fatalf("retry: %+v %v", retry, e)
				}
				if _, e = s.ReadCheckpoint(oldHead); e == nil {
					t.Fatal("stale blob still published")
				}
			}
		})
	}
}
func TestCB0ParentActualSyncAndEventCounts(t *testing.T) {
	for _, disk := range []bool{false, true} {
		t.Run(fmt.Sprint(disk), func(t *testing.T) {
			var s *Session
			var e error
			if disk {
				s, e = Open(t.TempDir(), cb0ParentOwner, uint32(len(cb0ParentZIP)))
			} else {
				s, e = NewMemory(cb0ParentOwner, uint32(len(cb0ParentZIP)))
			}
			if e != nil {
				t.Fatal(e)
			}
			defer s.Close()
			count := &cb0ParentDisk{cb0Disk: s.disk}
			s.disk = count // Initial atomic root precedes this observed count.
			cb0ParentLoad(t, s, cb0ParentZIP, []string{"SharedEntry.class", "SharedHelper.class"})
			refs, p := cb0ParentPackage(t, s, []uint8{0, 1})
			if _, e = s.CreateCoordinator(common.Hash{}, refs, p, OrdinaryGas); e != nil {
				t.Fatal(e)
			}
			n := count.syncs
			oldState := s.state
			r, e := s.Start(p, 0, "run", []int32{7}, 7, 4096, OrdinaryGas)
			if e != nil {
				t.Fatal(e)
			}
			slices := 1
			if count.syncs != n+1 || s.state == oldState || r.StateRoot != s.root || len(r.Logs) != 1 {
				t.Fatal("start did not sync/reload/publish one event")
			}
			for r.Slice.Lifecycle == 1 {
				n = count.syncs
				oldState = s.state
				prev := r.Slice.Epoch
				r, e = s.Resume(p, r.Slice.Epoch, r.Slice.CheckpointRoot, r.Checkpoint, 7, 4096, OrdinaryGas)
				if e != nil {
					t.Fatal(e)
				}
				slices++
				if count.syncs != n+1 || s.state == oldState || len(r.Logs) != 1 || r.Slice.Epoch != prev+1 {
					t.Fatal("resume did not sync/reload/publish")
				}
			}
			if slices != 6 || r.Slice.Result != 317 || count.syncs != 21 {
				t.Fatalf("slices%d syncs%d", slices, count.syncs)
			}
			n = count.syncs
			h := cb0ParentHead(t, s)
			cp, e := s.ReadCheckpoint(h.Java.CheckpointRoot)
			if e != nil {
				t.Fatal(e)
			}
			cp[0] ^= 1
			_, e = s.Resume(p, r.Slice.Epoch, r.Slice.CheckpointRoot, r.Checkpoint, 7, 4096, OrdinaryGas)
			if e == nil || count.syncs != n {
				t.Fatal("view/failure synced")
			}
			t.Logf("disk=%v actual post-initial syncs=%d, Java events/slices=%d", disk, count.syncs, slices)
		})
	}
}
func TestCB0ParentClassBoundaryAndJavaException(t *testing.T) {
	for _, kind := range []string{"65536", "65537", "exception"} {
		t.Run(kind, func(t *testing.T) {
			raw := cb0ParentBoundaryZIP
			names := []string{"P1.class", "P2.class", "P3.class", "P4.class"}
			slots := []uint8{0, 1, 2, 3}
			if kind == "65537" {
				names[3] = "P4B.class"
			}
			if kind == "exception" {
				raw = cb0ParentFaultZIP
				names = []string{"CB0Fault.class"}
				slots = []uint8{0}
			}
			s, e := NewMemory(cb0ParentOwner, uint32(len(raw)))
			if e != nil {
				t.Fatal(e)
			}
			defer s.Close()
			cb0ParentLoad(t, s, raw, names)
			refs, p := cb0ParentPackageNamed(t, s, slots, names)
			old := s.root
			op, e := s.CreateCoordinator(common.Hash{}, refs, p, OrdinaryGas)
			if kind == "65537" {
				if e == nil || s.root != old || op.StateRoot != (common.Hash{}) || len(op.RevertData) != 36 || op.RevertData[35] != 12 {
					t.Fatalf("+1 accepted or misclassified %+v %v", op, e)
				}
				return
			}
			if e != nil {
				t.Fatal(e)
			}
			input := int32(7)
			if kind == "exception" {
				input = 0
			}
			r, e := s.Start(p, 0, "run", []int32{input}, 4096, 4096, OrdinaryGas)
			if e != nil {
				t.Fatal(e)
			}
			if kind == "exception" {
				if r.Slice.Lifecycle != 3 || r.Slice.JavaRef == 0 || r.Slice.Result != 0 {
					t.Fatalf("not actual Java exception: %+v", r.Slice)
				}
			} else {
				if r.Slice.Lifecycle != 2 || r.Slice.Result != 9 {
					t.Fatalf("boundary execution: %+v", r.Slice)
				}
			}
			blob, e := s.ReadCheckpoint(r.Slice.CheckpointRoot)
			if e != nil || crypto.Keccak256Hash(blob) != r.Slice.CheckpointRoot || len(r.Logs) != 1 {
				t.Fatal("terminal checkpoint/event missing")
			}
		})
	}
}

func TestCB0ParentQuantumAndConcurrentCAS(t *testing.T) {
	var machine, vfs, pkg common.Hash
	for _, q := range []uint64{4096, 1, 7} {
		s := cb0ParentReady(t, "", []uint8{0, 1})
		h := cb0ParentHead(t, s)
		r, e := s.Start(h.Coordinator.PackageRoot, 0, "run", []int32{7}, q, 4096, OrdinaryGas)
		if e != nil {
			t.Fatal(e)
		}
		n := 1
		for r.Slice.Lifecycle == 1 {
			r, e = s.Resume(h.Coordinator.PackageRoot, r.Slice.Epoch, r.Slice.CheckpointRoot, r.Checkpoint, q, 4096, OrdinaryGas)
			if e != nil {
				t.Fatal(e)
			}
			n++
		}
		if r.Slice.Result != 317 || r.Slice.TotalJvmSteps != 36 || r.Slice.TotalInternalSteps != 5 || n != map[uint64]int{4096: 1, 1: 36, 7: 6}[q] {
			t.Fatal("quantum behavior")
		}
		if q == 4096 {
			machine = r.Slice.MachineStateRoot
			vfs = r.Slice.VFSStateRoot
			pkg = h.Coordinator.PackageRoot
		} else if machine != r.Slice.MachineStateRoot || vfs != r.Slice.VFSStateRoot || pkg != h.Coordinator.PackageRoot {
			t.Fatal("grouping changed fixed package or machine")
		}
		s.Close()
	}
	s := cb0ParentReady(t, "", []uint8{0, 1})
	h := cb0ParentHead(t, s)
	first, e := s.Start(h.Coordinator.PackageRoot, 0, "run", []int32{7}, 1, 4096, OrdinaryGas)
	if e != nil {
		t.Fatal(e)
	}
	var wg sync.WaitGroup
	start := make(chan struct{})
	results := make(chan JavaResult, 2)
	errs := make(chan error, 2)
	for i := 0; i < 2; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			<-start
			r, e := s.Resume(h.Coordinator.PackageRoot, first.Slice.Epoch, first.Slice.CheckpointRoot, first.Checkpoint, 1, 4096, OrdinaryGas)
			results <- r
			errs <- e
		}()
	}
	close(start)
	wg.Wait()
	success, stale := 0, 0
	for i := 0; i < 2; i++ {
		r := <-results
		if r.Slice.Epoch == 2 && len(r.Logs) == 1 {
			success++
		} else if r.Slice.Epoch == 0 && len(r.RevertData) == 36 && r.RevertData[35] == 3 && len(r.Logs) == 0 {
			stale++
		} else {
			t.Fatalf("concurrent result %+v", r)
		}
		<-errs
	}
	if success != 1 || stale != 1 {
		t.Fatal("CAS not serialized")
	}
}
func TestCB0ParentMetadataMatrix(t *testing.T) {
	dir := t.TempDir()
	s := cb0ParentReady(t, dir, []uint8{0, 1})
	path := filepath.Join(dir, cb0ManifestName)
	original, e := os.ReadFile(path)
	if e != nil {
		t.Fatal(e)
	}
	for _, mut := range []struct {
		name  string
		apply func(*cb0Manifest)
	}{
		{"format", func(m *cb0Manifest) { m.Format++ }}, {"owner", func(m *cb0Manifest) { m.Owner[0] ^= 1 }}, {"length", func(m *cb0Manifest) { m.Length++ }},
		{"engine", func(m *cb0Manifest) { m.Engine[0] ^= 1 }}, {"engine-code", func(m *cb0Manifest) { m.EngineCodeHash[0] ^= 1 }}, {"coordinator-code", func(m *cb0Manifest) { m.CoordinatorCodeHash[0] ^= 1 }},
		{"index-route", func(m *cb0Manifest) { m.Index[0] ^= 1 }}, {"decoder-route", func(m *cb0Manifest) { m.Decoders[0][0] ^= 1 }}, {"AS0-route", func(m *cb0Manifest) { m.AS0[0] ^= 1 }},
		{"no-coordinator", func(m *cb0Manifest) { m.Coordinator = common.Address{} }}, {"zero-package", func(m *cb0Manifest) { m.PackageRoot = common.Hash{} }},
		{"empty-root", func(m *cb0Manifest) { m.StateRoot = types.EmptyRootHash }}, {"zero-root", func(m *cb0Manifest) { m.StateRoot = common.Hash{} }},
	} {
		t.Run(mut.name, func(t *testing.T) {
			var m cb0Manifest
			json.Unmarshal(original, &m)
			mut.apply(&m)
			raw, _ := json.Marshal(m)
			if e = os.WriteFile(path, raw, 0600); e != nil {
				t.Fatal(e)
			}
			defer os.WriteFile(path, original, 0600)
			other, e := Open(dir, cb0ParentOwner, uint32(len(cb0ParentZIP)))
			if other != nil {
				other.Close()
			}
			if e == nil || !bytes.Contains([]byte(e.Error()), []byte("manifest")) {
				t.Fatalf("invalid manifest not rejected before held DB lock: %v", e)
			}
		})
	}
	// The latest checkpoint is integrity-checked against the EVM head on reopen.
	h := cb0ParentHead(t, s)
	r, e := s.Start(h.Coordinator.PackageRoot, 0, "run", []int32{7}, 7, 4096, OrdinaryGas)
	if e != nil {
		t.Fatal(e)
	}
	s.Close()
	blob := filepath.Join(dir, cb0BlobDirectory, r.Slice.CheckpointRoot.Hex()[2:]+".checkpoint")
	raw, e := os.ReadFile(blob)
	if e != nil {
		t.Fatal(e)
	}
	raw[0] ^= 1
	os.WriteFile(blob, raw, 0600)
	other, e := Open(dir, cb0ParentOwner, uint32(len(cb0ParentZIP)))
	if other != nil {
		other.Close()
	}
	if e == nil {
		t.Fatal("corrupt checkpoint accepted")
	}
}

func TestCB0ParentFullArchiveHighOffset(t *testing.T) {
	// Trusted fixture repack only, copying compressed bytes without inflation.
	// This ZIP machinery is test-only and never a transport/Java input authority.
	build := func(prefix int) []byte {
		var out bytes.Buffer
		out.Write(bytes.Repeat([]byte{'X'}, prefix))
		zw := zip.NewWriter(&out)
		zw.SetOffset(int64(prefix))
		zr, e := zip.NewReader(bytes.NewReader(cb0ParentZIP), int64(len(cb0ParentZIP)))
		if e != nil {
			t.Fatal(e)
		}
		for _, f := range zr.File {
			hdr := f.FileHeader
			w, e := zw.CreateRaw(&hdr)
			if e != nil {
				t.Fatal(e)
			}
			r, e := f.OpenRaw()
			if e != nil {
				t.Fatal(e)
			}
			if _, e = io.Copy(w, r); e != nil {
				t.Fatal(e)
			}
		}
		if e := zw.Close(); e != nil {
			t.Fatal(e)
		}
		return out.Bytes()
	}
	raw := build(33554432 - len(build(0)))
	if len(raw) != 33554432 {
		t.Fatal("not full32MiB")
	}
	dir := t.TempDir()
	s, e := Open(dir, cb0ParentOwner, uint32(len(raw)))
	if e != nil {
		t.Fatal(e)
	}
	defer func() { s.Close() }()
	cb0ParentLoad(t, s, raw, []string{"SharedEntry.class", "SharedHelper.class"})
	h := cb0ParentHead(t, s)
	if h.AS0.PageCount != 4096 || h.Decoders[0].DataStart < 33553000 {
		t.Fatalf("high offset not tested: %+v", h.Decoders[0])
	}
	for at := uint32(0); at < uint32(len(raw)); at += 4096 {
		r, e := s.InputRead(at, 4096, OrdinaryGas)
		if e != nil || !bytes.Equal(r.Bytes, raw[at:at+4096]) {
			t.Fatalf("full input EVM read %d: %v", at, e)
		}
	}
	refs, p := cb0ParentPackage(t, s, []uint8{0, 1})
	if _, e = s.CreateCoordinator(common.Hash{}, refs, p, OrdinaryGas); e != nil {
		t.Fatal(e)
	}
	result, e := s.Start(p, 0, "run", []int32{7}, 4096, 4096, OrdinaryGas)
	if e != nil || result.Slice.Result != 317 {
		t.Fatalf("actual high-offset Java: %v", e)
	}
	root := s.root
	head := result.Slice.CheckpointRoot
	s.Close()
	s, e = Open(dir, cb0ParentOwner, uint32(len(raw)))
	if e != nil {
		t.Fatal(e)
	}
	cp, e := s.ReadCheckpoint(head)
	if e != nil || s.root != root || crypto.Keccak256Hash(cp) != head {
		t.Fatal("high-offset terminal reopen")
	}
	t.Logf("full32MiB/4096inputpages/8192EVMreads, classdata=%d, result317, trie=%s", h.Decoders[0].DataStart, root)
}

func TestCB0ParentRealFilesystemPublicationErrors(t *testing.T) {
	for _, kind := range []string{"blob-dir", "temp-create", "manifest-rename"} {
		t.Run(kind, func(t *testing.T) {
			base := t.TempDir()
			dir := filepath.Join(base, "world")
			s := cb0ParentReady(t, dir, []uint8{0, 1})
			h := cb0ParentHead(t, s)
			first, e := s.Start(h.Coordinator.PackageRoot, 0, "run", []int32{7}, 7, 4096, OrdinaryGas)
			if e != nil {
				t.Fatal(e)
			}
			old := s.root
			manifestPath := filepath.Join(dir, cb0ManifestName)
			original, e := os.ReadFile(manifestPath)
			if e != nil {
				t.Fatal(e)
			}
			backup := filepath.Join(base, "saved")
			blobdir := filepath.Join(dir, cb0BlobDirectory)
			if kind == "blob-dir" {
				if e = os.Rename(blobdir, backup); e != nil {
					t.Fatal(e)
				}
				if e = os.WriteFile(blobdir, []byte("not a directory"), 0600); e != nil {
					t.Fatal(e)
				}
			} else {
				s.testFault = func(p cb0FaultPoint) error {
					if p != cb0FaultBeforeManifest {
						return nil
					}
					if kind == "temp-create" {
						s.directory = filepath.Join(dir, "missing-parent")
						return nil
					}
					if e := os.Rename(manifestPath, backup); e != nil {
						return e
					}
					return os.Mkdir(manifestPath, 0700)
				}
			}
			bad, e := s.Resume(h.Coordinator.PackageRoot, first.Slice.Epoch, first.Slice.CheckpointRoot, first.Checkpoint, 7, 4096, OrdinaryGas)
			s.directory = dir
			s.testFault = nil
			if kind == "blob-dir" {
				if e := os.Remove(blobdir); e != nil {
					t.Fatal(e)
				}
				if e := os.Rename(backup, blobdir); e != nil {
					t.Fatal(e)
				}
			}
			if kind == "manifest-rename" {
				if e := os.Remove(manifestPath); e != nil {
					t.Fatal(e)
				}
				if e := os.Rename(backup, manifestPath); e != nil {
					t.Fatal(e)
				}
			}
			if e == nil || s.poison != nil || s.root != old || bad.GasUsed == 0 || bad.StateRoot != (common.Hash{}) || bad.Slice.Schema != 0 || len(bad.Logs) != 0 || len(bad.Checkpoint) != 0 || len(bad.RevertData) != 0 {
				t.Fatalf("real IO failure receipt: %+v %v", bad, e)
			}
			now, e := os.ReadFile(manifestPath)
			if e != nil || !bytes.Equal(now, original) {
				t.Fatal("old manifest changed")
			}
			if _, e = s.Resume(h.Coordinator.PackageRoot, first.Slice.Epoch, first.Slice.CheckpointRoot, first.Checkpoint, 7, 4096, OrdinaryGas); e != nil {
				t.Fatal(e)
			}
		})
	}
}

func TestCB0ParentRealDirectorySyncFailure(t *testing.T) {
	// A read-only procfs directory opens normally but fsync returns EINVAL on Linux.
	// Redirect ONLY the final test-injected sync target AFTER real manifest rename;
	// no procfs contents are modified, and all publications still use our owned world.
	f, e := os.Open("/proc/self")
	if e != nil {
		t.Skip("procfs fault fixture unavailable")
	}
	e = f.Sync()
	f.Close()
	if e == nil {
		t.Skip("procfs supports directory sync")
	}
	dir := t.TempDir()
	s := cb0ParentReady(t, dir, []uint8{0, 1})
	h := cb0ParentHead(t, s)
	first, e := s.Start(h.Coordinator.PackageRoot, 0, "run", []int32{7}, 7, 4096, OrdinaryGas)
	if e != nil {
		t.Fatal(e)
	}
	s.testFault = func(p cb0FaultPoint) error {
		if p == cb0FaultAfterRename {
			s.directory = "/proc/self"
		}
		return nil
	}
	r, e := s.Resume(h.Coordinator.PackageRoot, first.Slice.Epoch, first.Slice.CheckpointRoot, first.Checkpoint, 7, 4096, OrdinaryGas)
	s.directory = dir
	s.testFault = nil
	if e == nil || s.poison == nil || !errors.Is(e, errCB0Published) || !bytes.Contains([]byte(e.Error()), []byte("sync /proc/self: invalid argument")) || r.GasUsed == 0 || r.StateRoot != (common.Hash{}) || len(r.Checkpoint) != 0 || len(r.Logs) != 0 || r.Slice.Schema != 0 {
		t.Fatalf("real dirsync error: %+v %v", r, e)
	}
	s.Close()
	again, e := Open(dir, cb0ParentOwner, uint32(len(cb0ParentZIP)))
	if e != nil {
		t.Fatal(e)
	}
	defer again.Close()
	if cb0ParentHead(t, again).Java.Epoch != first.Slice.Epoch+1 {
		t.Fatal("postrename root not reopened")
	}
}
