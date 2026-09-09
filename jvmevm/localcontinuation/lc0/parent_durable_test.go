package lc0

import (
	"bytes"
	"errors"
	"os"
	"path/filepath"
	"testing"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
)

func TestLC0ParentInvalidStoreMetadataDoesNotOpenDatabase(t *testing.T) {
	dir := t.TempDir()
	for _, name := range []string{lc0HarnessStateDirectory, lc0HarnessBlobDirectory} {
		if err := os.Mkdir(filepath.Join(dir, name), 0700); err != nil {
			t.Fatal(err)
		}
	}
	if err := os.WriteFile(filepath.Join(dir, lc0HarnessStoreMarkerName), []byte("unrelated marker"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, lc0HarnessManifestName), []byte("{}"), 0600); err != nil {
		t.Fatal(err)
	}
	s, err := Open(dir, common.HexToAddress("0x1234"))
	if s != nil {
		s.Close()
	}
	if err == nil {
		t.Fatal("invalid metadata accepted")
	}
	files, err := os.ReadDir(filepath.Join(dir, lc0HarnessStateDirectory))
	if err != nil {
		t.Fatal(err)
	}
	if len(files) != 0 {
		t.Fatalf("invalid store created database files before rejecting metadata: %v", files)
	}
}

func TestLC0ParentAbandonedManifestTemporaryPreservesOldHead(t *testing.T) {
	dir := t.TempDir()
	owner := common.HexToAddress("0x1234")
	s, err := Open(dir, owner)
	if err != nil {
		t.Fatal(err)
	}
	f := lc0HarnessFixtures(t)[0]
	id := crypto.Keccak256Hash([]byte("parent-manifest-leftover"))
	parent, err := s.Start(id, f.Raw, f.EntryClass, f.Entry, f.Args, 1, 4096, lc0HarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	if err := s.Close(); err != nil {
		t.Fatal(err)
	}
	// A process can stop after writing its own temporary manifest but before rename.
	path := filepath.Join(dir, ".durable-head-parent-leftover")
	if err := os.WriteFile(path, []byte("incomplete unpublished manifest"), 0600); err != nil {
		t.Fatal(err)
	}
	reopened, err := Open(dir, owner)
	if err != nil {
		t.Fatalf("old durable state stranded by an unpublished temporary: %v", err)
	}
	defer reopened.Close()
	head, err := reopened.Head(id)
	if err != nil || head.CheckpointRoot != parent.Slice.CheckpointRoot {
		t.Fatalf("old head changed: %+v %v", head, err)
	}
	if _, err := os.Stat(path); err != nil {
		t.Fatalf("unpublished file was removed: %v", err)
	}
}

func TestLC0ParentExistingOrphanIsSyncedBeforePublication(t *testing.T) {
	dir := t.TempDir()
	owner := common.HexToAddress("0x1234")
	s, err := Open(dir, owner)
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()
	f := lc0HarnessFixtures(t)[0]
	id := crypto.Keccak256Hash([]byte("parent-orphan-sync"))
	parent, err := s.Start(id, f.Raw, f.EntryClass, f.Entry, f.Args, 1, 4096, lc0HarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	control := lc0HarnessControlChild(t, owner, id, f, parent)
	s.testFault = func(p lc0HarnessFaultPoint) error {
		if p == lc0HarnessFaultAfterBlob {
			return errors.New("stop before head publication")
		}
		return nil
	}
	failed, err := s.Resume(id, parent.Slice.Epoch, parent.Slice.CheckpointRoot, f.Raw, parent.Checkpoint, 1, 4096, lc0HarnessOrdinaryGas)
	if err == nil || len(failed.Checkpoint) != 0 || failed.Slice != (SliceResult{}) {
		t.Fatal("failed publication exposed child")
	}
	seen := false
	s.testFault = func(p lc0HarnessFaultPoint) error {
		if p == lc0HarnessFaultBeforeExistingBlobSync {
			seen = true
			return errors.New("existing blob sync unavailable")
		}
		return nil
	}
	failed, err = s.Resume(id, parent.Slice.Epoch, parent.Slice.CheckpointRoot, f.Raw, parent.Checkpoint, 1, 4096, lc0HarnessOrdinaryGas)
	if err == nil || !seen || len(failed.Logs) != 0 || len(failed.Checkpoint) != 0 {
		t.Fatal("existing blob skipped durable sync/failure boundary")
	}
	head, err := s.Head(id)
	if err != nil || head.CheckpointRoot != parent.Slice.CheckpointRoot {
		t.Fatal("failed sync advanced head", err)
	}
	s.testFault = nil
	child, err := s.Resume(id, parent.Slice.Epoch, parent.Slice.CheckpointRoot, f.Raw, parent.Checkpoint, 1, 4096, lc0HarnessOrdinaryGas)
	if err != nil || !bytes.Equal(child.Checkpoint, control.Checkpoint) {
		t.Fatal("orphan retry diverged", err)
	}
}

func TestLC0ParentStoreEntryTypesAndBoundedBlobRead(t *testing.T) {
	owner := common.HexToAddress("0x1234")
	for _, entry := range []string{lc0HarnessStateDirectory, lc0HarnessBlobDirectory, lc0HarnessManifestName} {
		t.Run(entry, func(t *testing.T) {
			dir := filepath.Join(t.TempDir(), "store")
			s, err := Open(dir, owner)
			if err != nil {
				t.Fatal(err)
			}
			if err := s.Close(); err != nil {
				t.Fatal(err)
			}
			original := filepath.Join(dir, entry)
			moved := filepath.Join(filepath.Dir(dir), "saved-entry")
			if err := os.Rename(original, moved); err != nil {
				t.Fatal(err)
			}
			if err := os.Symlink(moved, original); err != nil {
				t.Fatal(err)
			}
			bad, err := Open(dir, owner)
			if bad != nil {
				bad.Close()
			}
			if err == nil {
				t.Fatal("unsupported linked store entry accepted")
			}
			if _, err := os.Stat(moved); err != nil {
				t.Fatalf("saved entry changed: %v", err)
			}
		})
	}
	dir := t.TempDir()
	s, err := Open(dir, owner)
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()
	root := crypto.Keccak256Hash([]byte("oversized-test-blob"))
	path := s.lc0HarnessBlobPath(root)
	if err := os.WriteFile(path, make([]byte, lc0HarnessMaxCheckpointSize+1), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := s.ReadCheckpoint(root); err == nil {
		t.Fatal("oversized blob accepted")
	}
	if err := os.Remove(path); err != nil {
		t.Fatal(err)
	}
	file := filepath.Join(t.TempDir(), "opaque")
	if err := os.WriteFile(file, []byte("opaque"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(file, path); err != nil {
		t.Fatal(err)
	}
	if _, err := s.ReadCheckpoint(root); err == nil {
		t.Fatal("linked blob accepted")
	}
}
