package di0

import (
	"errors"
	"path/filepath"
	"testing"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
)

func TestDI0HarnessPostSyncPrepublicationDecoderCreateRestoresAndRetriesSameChild(t *testing.T) {
	z := di0HarnessZIP1(t, []byte("sync"), []byte("content"), 0)
	owner := common.HexToAddress("0xd1004002")
	directory := t.TempDir()
	s, err := Open(directory, owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()
	di0HarnessUpload(t, s, z.raw)
	h := di0HarnessFinishIndex(t, s)
	oldRoot := h.StateRoot
	oldManifest, err := readManifest(filepath.Join(directory, manifestName))
	if err != nil {
		t.Fatal(err)
	}
	nonce := s.state.GetNonce(owner)
	child := crypto.CreateAddress(owner, nonce)
	s.testFault = func(p faultPoint) error {
		if p == faultAfterTrie {
			return errors.New("after real trie/code sync")
		}
		return nil
	}
	op, err := s.CreateDecoder(h.Index.FinalRoot, z.name, OrdinaryGas)
	if err == nil || op.GasUsed == 0 || op.StateRoot != (common.Hash{}) || op.CreatedAddress != (common.Address{}) || len(op.Logs) != 0 || len(op.RevertData) != 0 {
		t.Fatalf("post-sync publication failure op=%+v err=%v", op, err)
	}
	after, err := s.Head(OrdinaryGas)
	if err != nil || after.StateRoot != oldRoot || after.Decoder.Address != (common.Address{}) || s.state.GetNonce(owner) != nonce || len(s.state.GetCode(child)) != 0 {
		t.Fatalf("prior route/root not restored: head=%+v nonce=%d code=%d err=%v", after, s.state.GetNonce(owner), len(s.state.GetCode(child)), err)
	}
	manifestAfter, err := readManifest(filepath.Join(directory, manifestName))
	if err != nil || manifestAfter.StateRoot != oldManifest.StateRoot || manifestAfter.Decoder != (common.Address{}) {
		t.Fatalf("published manifest changed: %+v err=%v", manifestAfter, err)
	}
	s.testFault = nil
	retry, err := s.CreateDecoder(h.Index.FinalRoot, z.name, OrdinaryGas)
	if err != nil || retry.CreatedAddress != child || retry.StateRoot == (common.Hash{}) {
		t.Fatalf("same-child retry=%+v err=%v", retry, err)
	}
}
