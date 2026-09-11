package di0

import (
	"bytes"
	"errors"
	"os"
	"path/filepath"
	"reflect"
	"sync"
	"testing"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/as0"
)

func TestDI0HarnessDurableFreshProcessStagesAndFullPageReads(t *testing.T) {
	plain := bytes.Repeat([]byte("durable-dynamic-output-"), 430) // > one output page
	compressed := di0HarnessDeflate(t, plain)
	if (compressed[0]>>1)&3 != 2 {
		t.Fatal("trusted continuation fixture is not a dynamic block")
	}
	z := di0HarnessZIPPayloadPrefix(9000, []byte("resource.bin"), plain, compressed, 8)
	directory := t.TempDir()
	owner := common.HexToAddress("0xd1001001")
	s, err := Open(directory, owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatal(err)
	}
	creation, err := s.Creation()
	if err != nil || !creation.Performed || creation.Controller != crypto.CreateAddress(owner, 0) || creation.GasUsed == 0 {
		t.Fatalf("fresh creation=%+v err=%v", creation, err)
	}
	h, err := s.Head(OrdinaryGas)
	if err != nil || h.Index.Address != (common.Address{}) || h.Decoder.Address != (common.Address{}) {
		t.Fatalf("fresh head=%+v err=%v", h, err)
	}
	// Publish exactly one input page, then reopen before the upload is complete.
	firstRaw := append([]byte(nil), z.raw[:as0.PageSize]...)
	firstOp, err := s.Append(0, firstRaw, di0HarnessPageCommitment(t, creation.Controller, 0, firstRaw), OrdinaryGas)
	if err != nil || firstOp.StateRoot == (common.Hash{}) {
		t.Fatalf("first input page op=%+v err=%v", firstOp, err)
	}
	if err = s.Close(); err != nil {
		t.Fatal(err)
	}

	// Mid-upload/fully-uploaded reopen performs no CREATE and retains only AS0.
	s, err = Open(filepath.Join(directory, "."), owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatal(err)
	}
	creation, _ = s.Creation()
	if creation.Performed || creation.GasUsed != 0 || creation.Controller != crypto.CreateAddress(owner, 0) {
		t.Fatalf("reopen creation=%+v", creation)
	}
	h, err = s.Head(OrdinaryGas)
	if err != nil || h.AS0.Cursor != as0.PageSize || h.AS0.Sealed {
		t.Fatalf("mid-upload reopen=%+v err=%v", h.AS0, err)
	}
	di0HarnessUpload(t, s, z.raw)
	h, err = s.Head(OrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	if _, err = s.Seal(h.AS0.Cursor, h.AS0.ChainCommitment, OrdinaryGas); err != nil {
		t.Fatal(err)
	}
	h, err = s.Head(OrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	if _, err = s.CreateIndex(h.AS0.ContentCommitment, OrdinaryGas); err != nil {
		t.Fatal(err)
	}
	if _, err = s.DiscoverIndex(OrdinaryGas); err != nil {
		t.Fatal(err)
	}
	if err = s.Close(); err != nil {
		t.Fatal(err)
	}

	// Reopen a discovered but unscanned index, then publish each remaining stage.
	s, err = Open(directory, owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatal(err)
	}
	h, err = s.Head(OrdinaryGas)
	if err != nil || h.Index.Phase != 1 || h.Index.NextEntry != 0 {
		t.Fatalf("mid-index reopen=%+v err=%v", h.Index, err)
	}
	for h.Index.NextEntry < h.Index.Count {
		if _, err = s.ScanIndex(h.Index.NextEntry, h.Index.CDCursor, h.Index.Rolling, 1, OrdinaryGas); err != nil {
			t.Fatal(err)
		}
		h, err = s.Head(OrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
	}
	if _, err = s.FinishIndex(h.Index.Count, h.Index.CDCursor, h.Index.Rolling, OrdinaryGas); err != nil {
		t.Fatal(err)
	}
	if err = s.Close(); err != nil {
		t.Fatal(err)
	}

	// Reopen a FINAL index without constructing another index.
	s, err = Open(directory, owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatal(err)
	}
	h, err = s.Head(OrdinaryGas)
	if err != nil || h.Index.Phase != 2 || h.Decoder.Address != (common.Address{}) {
		t.Fatalf("final-index reopen=%+v err=%v", h, err)
	}
	h = di0HarnessCreate(t, s, z.name)
	before := h.Decoder.Work
	if _, err = s.Step(before, 1, OrdinaryGas); err != nil {
		t.Fatal(err)
	}
	h, err = s.Head(OrdinaryGas)
	if err != nil || h.Decoder.Work != before+1 || h.Decoder.Phase != 1 || h.Decoder.BlockMode != 2 || h.Decoder.FixedBlock {
		t.Fatalf("mid-dynamic-table head=%+v err=%v", h.Decoder, err)
	}
	if err = s.Close(); err != nil {
		t.Fatal(err)
	}

	// Dynamic/fixed table and exact reader cursor state are EVM state, not manifest fields.
	s, err = Open(directory, owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatal(err)
	}
	h, err = s.Head(OrdinaryGas)
	if err != nil || h.Decoder.Work != before+1 {
		t.Fatalf("mid-decode reopen=%+v err=%v", h.Decoder, err)
	}
	h = di0HarnessDecode(t, s, 128)
	if h.Decoder.Phase != 2 || h.Decoder.OutputCount != uint32(len(plain)) {
		t.Fatalf("verified=%+v", h.Decoder)
	}
	if err = s.Close(); err != nil {
		t.Fatal(err)
	}

	s, err = Open(directory, owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatal(err)
	}
	h, err = s.Head(OrdinaryGas)
	if err != nil || h.Decoder.Phase != 2 {
		t.Fatalf("verified reopen=%+v err=%v", h.Decoder, err)
	}
	if _, err = s.Publish(0, h.Decoder.PublicationRolling, 1, OrdinaryGas); err != nil {
		t.Fatal(err)
	}
	h, _ = s.Head(OrdinaryGas)
	if h.Decoder.Phase != 3 || h.Decoder.PublishedPages != 1 {
		t.Fatalf("mid-publication=%+v", h.Decoder)
	}
	first, err := s.Page(0, OrdinaryGas)
	if err == nil || first.GasUsed == 0 {
		t.Fatalf("page became readable before FINAL: page=%+v err=%v", first, err)
	}
	if err = s.Close(); err != nil {
		t.Fatal(err)
	}

	s, err = Open(directory, owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatal(err)
	}
	h, _ = s.Head(OrdinaryGas)
	if h.Decoder.Phase != 3 || h.Decoder.PublishedPages != 1 {
		t.Fatalf("mid-publication reopen=%+v", h.Decoder)
	}
	final := di0HarnessPublish(t, s)
	resourceRoot, trieRoot := final.Decoder.FinalRoot, final.StateRoot
	if resourceRoot == (common.Hash{}) || trieRoot == (common.Hash{}) || resourceRoot == trieRoot {
		t.Fatal("resource FinalRoot and transport StateRoot labels are not distinct")
	}
	if err = s.Close(); err != nil {
		t.Fatal(err)
	}

	s, err = Open(directory, owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()
	creation, _ = s.Creation()
	if creation.Performed || creation.GasUsed != 0 {
		t.Fatalf("FINAL reopen created controller: %+v", creation)
	}
	h, err = s.Head(OrdinaryGas)
	if err != nil || h.Decoder.Phase != 4 || h.Decoder.FinalRoot != resourceRoot || h.StateRoot != trieRoot {
		t.Fatalf("FINAL reopen=%+v err=%v", h, err)
	}
	var got []byte
	for at := uint32(0); at < uint32(len(plain)); {
		n := uint32(MaxRead)
		if left := uint32(len(plain)) - at; left < n {
			n = left
		}
		r, err := s.Read(at, n, OrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
		got = append(got, r.Bytes...)
		at += n
	}
	if !bytes.Equal(got, plain) {
		t.Fatal("full-byte EVM output reads differ from oracle")
	}
	for at := uint8(0); at < h.Decoder.PublishedPages; at++ {
		p, err := s.Page(at, OrdinaryGas)
		if err != nil || p.Address == (common.Address{}) || p.CodeHash == (common.Hash{}) || p.Commitment == (common.Hash{}) || p.Length == 0 {
			t.Fatalf("page %d=%+v err=%v", at, p, err)
		}
	}
}

func TestDI0HarnessPublicationFailureRecoveryAndPostRenamePoison(t *testing.T) {
	z := di0HarnessZIP1(t, []byte("p"), bytes.Repeat([]byte{0x61}, 512), 0)
	directory := t.TempDir()
	owner := common.HexToAddress("0xd1001002")
	s, err := Open(directory, owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatal(err)
	}
	di0HarnessUpload(t, s, z.raw)
	di0HarnessFinishIndex(t, s)
	h := di0HarnessCreate(t, s, z.name)
	oldRoot := h.StateRoot
	s.testFault = func(p faultPoint) error {
		if p == faultBeforeManifest {
			return errors.New("injected before manifest")
		}
		return nil
	}
	op, err := s.Step(h.Decoder.Work, 1, OrdinaryGas)
	if err == nil || op.GasUsed == 0 || op.StateRoot != (common.Hash{}) || op.CreatedAddress != (common.Address{}) || len(op.Logs) != 0 || len(op.RevertData) != 0 {
		t.Fatalf("prepublication failure op=%+v err=%v", op, err)
	}
	after, err := s.Head(OrdinaryGas)
	if err != nil || after.StateRoot != oldRoot || after.Decoder.Work != h.Decoder.Work {
		t.Fatalf("old root not restored: %+v err=%v", after, err)
	}
	s.testFault = nil
	if _, err = s.Step(h.Decoder.Work, 1, OrdinaryGas); err != nil {
		t.Fatal(err)
	}
	h, _ = s.Head(OrdinaryGas)
	s.testFault = func(p faultPoint) error {
		if p == faultAfterManifestRename {
			return errors.New("injected after rename")
		}
		return nil
	}
	op, err = s.Step(h.Decoder.Work, 1, OrdinaryGas)
	if err == nil || op.GasUsed == 0 || op.StateRoot != (common.Hash{}) || len(op.Logs) != 0 || len(op.RevertData) != 0 {
		t.Fatalf("postrename failure op=%+v err=%v", op, err)
	}
	if _, err = s.Head(OrdinaryGas); err == nil {
		t.Fatal("poisoned session remained usable")
	}
	if _, err = s.Creation(); err == nil {
		t.Fatal("poison did not cover Creation")
	}
	if err = s.Close(); err != nil {
		t.Fatal(err)
	}
	s, err = Open(directory, owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()
	after, err = s.Head(OrdinaryGas)
	if err != nil || after.Decoder.Work <= h.Decoder.Work {
		t.Fatalf("exact manifest reopen did not retain renamed root: %+v err=%v", after, err)
	}
}

func TestDI0HarnessConcurrentStaleStepSerializedAndCopiedViews(t *testing.T) {
	z := di0HarnessZIP1(t, []byte("c"), bytes.Repeat([]byte{0x35}, 512), 0)
	s, h := di0HarnessPrepared(t, z, common.HexToAddress("0xd1001003"))
	defer s.Close()
	start := make(chan struct{})
	type result struct {
		op  Operation
		err error
	}
	results := make(chan result, 2)
	var ready sync.WaitGroup
	ready.Add(2)
	for i := 0; i < 2; i++ {
		go func() {
			ready.Done()
			<-start
			op, err := s.Step(h.Decoder.Work, 1, OrdinaryGas)
			results <- result{op, err}
		}()
	}
	ready.Wait()
	close(start)
	success, stale := 0, 0
	for i := 0; i < 2; i++ {
		r := <-results
		if r.err == nil {
			success++
		} else if len(r.op.RevertData) == 36 {
			di0HarnessError(t, r.op, 7)
			stale++
		} else {
			t.Fatalf("unexpected result op=%+v err=%v", r.op, r.err)
		}
	}
	if success != 1 || stale != 1 {
		t.Fatalf("success=%d stale=%d", success, stale)
	}
	before, _ := s.Head(OrdinaryGas)
	r, err := s.InputRead(0, uint32(len(z.raw)), OrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	r.Bytes[0] ^= 1
	after, _ := s.Head(OrdinaryGas)
	if !reflect.DeepEqual(di0HarnessHeadNoGas(before), di0HarnessHeadNoGas(after)) {
		t.Fatal("copied view changed state")
	}
}

func TestDI0HarnessNamespaceMetadataAndInternalSymlinkRefusal(t *testing.T) {
	owner := common.HexToAddress("0xd1001004")
	z := di0HarnessZIP1(t, []byte("n"), []byte("x"), 0)
	incomplete := t.TempDir()
	if err := os.WriteFile(filepath.Join(incomplete, "keep"), []byte("x"), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := Open(incomplete, owner, uint32(len(z.raw))); err == nil {
		t.Fatal("nonempty foreign directory adopted")
	}
	if _, err := os.Stat(filepath.Join(incomplete, "keep")); err != nil {
		t.Fatal("foreign directory was modified")
	}
	dir := t.TempDir()
	s, err := Open(dir, owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatal(err)
	}
	if err = s.Close(); err != nil {
		t.Fatal(err)
	}
	marker, err := os.ReadFile(filepath.Join(dir, markerName))
	if err != nil || string(marker) != storeMarker {
		t.Fatalf("marker=%q err=%v", marker, err)
	}
	current := filepath.Join(dir, stateDirectory, "CURRENT")
	if _, err = os.Lstat(current); err != nil {
		t.Fatal(err)
	}
	saved := current + ".saved"
	if err = os.Rename(current, saved); err != nil {
		t.Fatal(err)
	}
	if err = os.Symlink(saved, current); err != nil {
		t.Fatal(err)
	}
	if _, err = Open(dir, owner, uint32(len(z.raw))); err == nil {
		t.Fatal("internal CURRENT symlink accepted")
	}
}
