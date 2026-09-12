package cb0

import (
	"testing"

	"github.com/ethereum/go-ethereum/common"
)

func cb0TransportOwner() common.Address {
	return common.HexToAddress("0xCB00000000000000000000000000000000000001")
}

func TestCB0AtomicInitialRootAndReopen(t *testing.T) {
	s, err := NewMemory(cb0TransportOwner(), 1)
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()
	initial, err := s.Initialization()
	if err != nil {
		t.Fatal(err)
	}
	if !initial.EngineInstalled || initial.EngineAddress != cb0EngineAddress || initial.EngineCodeHash != cb0VFSCode || initial.StateRoot == (common.Hash{}) || !initial.AS0Creation.Performed || initial.AS0Creation.Controller == (common.Address{}) || initial.AS0Creation.StateRoot != initial.StateRoot {
		t.Fatalf("non-atomic initial receipt: %#v", initial)
	}
	if initial.AS0Creation.GasUsed == 0 {
		t.Fatal("ordinary AS0 CREATE reports zero gas")
	}
	if head, err := s.Head(OrdinaryGas); err != nil || head.StateRoot != initial.StateRoot || head.AS0.Controller != initial.AS0Creation.Controller || head.Index.Address != (common.Address{}) || head.Coordinator.Address != (common.Address{}) {
		t.Fatalf("initial shared-world head differs: head=%#v err=%v", head, err)
	}
	if _, err := s.CreateDecoder(0, common.Hash{}, []byte("Never.class"), OrdinaryGas); err == nil {
		t.Fatal("decoder creation before an index must fail")
	}
	if _, err := s.ReadCheckpoint(common.Hash{}); err == nil {
		t.Fatal("zero/stale checkpoint was accepted")
	}
}

func TestCB0DiskInitialRootReopensWithoutCreate(t *testing.T) {
	dir := t.TempDir()
	s, err := Open(dir, cb0TransportOwner(), 1)
	if err != nil {
		t.Fatal(err)
	}
	before, err := s.Initialization()
	if err != nil {
		t.Fatal(err)
	}
	if err := s.Close(); err != nil {
		t.Fatal(err)
	}
	reopened, err := Open(dir, cb0TransportOwner(), 1)
	if err != nil {
		t.Fatal(err)
	}
	defer reopened.Close()
	after, err := reopened.Initialization()
	if err != nil {
		t.Fatal(err)
	}
	if after.AS0Creation.Performed || after.AS0Creation.GasUsed != 0 || after.StateRoot != before.StateRoot || after.AS0Creation.Controller != before.AS0Creation.Controller || after.EngineCodeHash != before.EngineCodeHash {
		t.Fatalf("reopen repaired or changed initial root: before=%#v after=%#v", before, after)
	}
}

func TestCB0ArtifactAndFrozenRanges(t *testing.T) {
	loaded, err := cb0ArtifactLoad()
	if err != nil {
		t.Fatal(err)
	}
	if len(loaded.runtime) == 0 || len(loaded.init) == 0 || loaded.runtimeHash == (common.Hash{}) {
		t.Fatal("unusable pinned coordinator artifact")
	}
	if _, err := NewMemory(common.Address{}, 1); err == nil {
		t.Fatal("zero owner accepted")
	}
	if _, err := NewMemory(cb0TransportOwner(), 0); err == nil {
		t.Fatal("zero archive length accepted")
	}
	if _, err := NewMemory(cb0TransportOwner(), 33554433); err == nil {
		t.Fatal("oversized archive length accepted")
	}
}
