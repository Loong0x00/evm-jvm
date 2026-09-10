package zi0

import (
	"bytes"
	"errors"
	"sync"
	"testing"

	"github.com/ethereum/go-ethereum/common"
	evmruntime "github.com/ethereum/go-ethereum/core/vm/runtime"
	"github.com/ethereum/go-ethereum/crypto"
)

func TestZI0HarnessConstructorOwnerBindingRollbackAndRetry(t *testing.T) {
	z := zi0HarnessSmallZIP()
	owner := common.HexToAddress("0x5a4930730001")
	session, gas := zi0HarnessOpenAndUpload(t, owner, z, "")
	defer session.Close()
	head, _ := session.Head(OrdinaryGas)
	if _, err := session.Seal(head.AS0.Cursor, head.AS0.ChainCommitment, OrdinaryGas); err != nil {
		t.Fatal(err)
	}
	sealed, _ := session.Head(OrdinaryGas)
	wrong := sealed.AS0.ContentCommitment
	wrong[0] ^= 1
	beforeRoot := session.state.Copy().IntermediateRoot(true)
	beforeNonce := session.state.GetNonce(owner)
	op, err := session.CreateIndex(wrong, OrdinaryGas)
	if err == nil || zi0HarnessErrorCode(t, op) != 3 || op.GasUsed == 0 || op.StateRoot != (common.Hash{}) || op.CreatedAddress != (common.Address{}) || len(op.Logs) != 0 {
		t.Fatalf("wrong-content constructor op=%+v err=%v", op, err)
	}
	if session.indexAddress != (common.Address{}) || session.state.GetNonce(owner) != beforeNonce || session.state.Copy().IntermediateRoot(true) != beforeRoot || len(session.state.GetCode(crypto.CreateAddress(owner, beforeNonce))) != 0 {
		t.Fatal("failed constructor changed root/address/code/nonce")
	}
	retry, err := session.CreateIndex(sealed.AS0.ContentCommitment, OrdinaryGas)
	if err != nil || retry.CreatedAddress != crypto.CreateAddress(owner, 1) {
		t.Fatalf("constructor retry=%+v err=%v", retry, err)
	}
	gas.createIndex = retry.GasUsed

	// Constructor owner-zero precedence is exercised directly against a copied
	// EVM state; production Session never adds a caller-selectable owner.
	args, _ := session.zi0ABI.Pack("", session.as0Address, sealed.AS0.ContentCommitment)
	cfg := session.config(session.state.Copy(), OrdinaryGas)
	cfg.Origin = common.Address{}
	out, _, _, createErr := evmruntime.Create(append(append([]byte(nil), session.zi0Init...), args...), cfg)
	if createErr == nil || len(out) != 36 || !bytes.Equal(out[:4], crypto.Keccak256([]byte("ZI0Error(uint256)"))[:4]) || out[35] != 1 {
		t.Fatalf("zero-owner constructor output=0x%x err=%v", out, createErr)
	}

	// Every mutator similarly derives msg.sender from the bound owner. Directly
	// changing Origin confirms error 1 without exposing an override in the API.
	callData, _ := session.zi0ABI.Pack("discover")
	cfg = session.config(session.state.Copy(), OrdinaryGas)
	cfg.Origin = common.HexToAddress("0x5a49307300ff")
	out, _, callErr := evmruntime.Call(session.indexAddress, callData, cfg)
	if callErr == nil || len(out) != 36 || out[35] != 1 {
		t.Fatalf("wrong-owner discover output=0x%x err=%v", out, callErr)
	}
}

func TestZI0HarnessDirectOOGRollbackAndValidRetry(t *testing.T) {
	z := zi0HarnessBuildZIP([]zi0HarnessEnt{{name: bytes.Repeat([]byte{'n'}, 256), data: bytes.Repeat([]byte{7}, 100), method: 8, descriptor: 1}}, 0, nil, nil)
	owner := common.HexToAddress("0x5a4930730002")
	session, err := NewMemory(owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	creation, _ := session.Creation()
	firstPage := append([]byte(nil), z.raw...)
	beforeRoot := session.state.Copy().IntermediateRoot(true)
	oog, err := session.Append(0, firstPage, zi0HarnessPageCommitment(t, creation.Controller, 0, firstPage), 1_000)
	if err == nil || oog.GasUsed != 1_000 || oog.StateRoot != (common.Hash{}) || len(oog.Logs) != 0 || len(oog.RevertData) != 0 || session.state.Copy().IntermediateRoot(true) != beforeRoot || session.state.GetNonce(session.as0Address) != 1 {
		t.Fatalf("AS0 OOG rollback op=%+v err=%v", oog, err)
	}
	if _, err := session.Append(0, firstPage, zi0HarnessPageCommitment(t, creation.Controller, 0, firstPage), OrdinaryGas); err != nil {
		t.Fatalf("AS0 retry: %v", err)
	}
	head, _ := session.Head(OrdinaryGas)
	if _, err := session.Seal(head.AS0.Cursor, head.AS0.ChainCommitment, OrdinaryGas); err != nil {
		t.Fatal(err)
	}
	sealed, _ := session.Head(OrdinaryGas)
	if _, err := session.CreateIndex(sealed.AS0.ContentCommitment, OrdinaryGas); err != nil {
		t.Fatal(err)
	}
	if _, err := session.Discover(OrdinaryGas); err != nil {
		t.Fatal(err)
	}
	staging, _ := session.Head(OrdinaryGas)
	beforeRoot = session.state.Copy().IntermediateRoot(true)
	oog, err = session.Scan(staging.Index.NextEntry, staging.Index.CDCursor, staging.Index.Rolling, 1, 100_000)
	if err == nil || oog.GasUsed != 100_000 || oog.StateRoot != (common.Hash{}) || len(oog.Logs) != 0 || len(oog.RevertData) != 0 || session.state.Copy().IntermediateRoot(true) != beforeRoot {
		t.Fatalf("ZI0 OOG rollback op=%+v err=%v", oog, err)
	}
	after, _ := session.Head(OrdinaryGas)
	if after.Index.NextEntry != staging.Index.NextEntry || after.Index.CDCursor != staging.Index.CDCursor || after.Index.Rolling != staging.Index.Rolling {
		t.Fatal("ZI0 OOG exposed partial batch")
	}
	if _, err := session.Scan(after.Index.NextEntry, after.Index.CDCursor, after.Index.Rolling, 1, BoundaryGas); err != nil {
		t.Fatalf("ZI0 retry: %v", err)
	}
}

func TestZI0HarnessConcurrentStaleScanSerialized(t *testing.T) {
	z := zi0HarnessSmallZIP()
	session, _ := zi0HarnessPrepared(t, common.HexToAddress("0x5a4930730003"), z)
	defer session.Close()
	if _, err := session.Discover(OrdinaryGas); err != nil {
		t.Fatal(err)
	}
	head, _ := session.Head(OrdinaryGas)
	type result struct {
		op  Operation
		err error
	}
	start := make(chan struct{})
	results := make(chan result, 2)
	var ready sync.WaitGroup
	ready.Add(2)
	for i := 0; i < 2; i++ {
		go func() {
			ready.Done()
			<-start
			op, err := session.Scan(head.Index.NextEntry, head.Index.CDCursor, head.Index.Rolling, 1, OrdinaryGas)
			results <- result{op, err}
		}()
	}
	ready.Wait()
	close(start)
	first, second := <-results, <-results
	successes, stale := 0, 0
	for _, got := range []result{first, second} {
		if got.err == nil {
			if got.op.StateRoot == (common.Hash{}) {
				t.Fatal("successful concurrent scan lacks root")
			}
			successes++
		} else if len(got.op.RevertData) == 36 && zi0HarnessErrorCode(t, got.op) == 10 {
			stale++
		} else {
			t.Fatalf("unexpected concurrent result op=%+v err=%v", got.op, got.err)
		}
	}
	if successes != 1 || stale != 1 {
		t.Fatalf("concurrent outcomes success=%d stale=%d", successes, stale)
	}
	finalHead, _ := session.Head(OrdinaryGas)
	if finalHead.Index.NextEntry != 1 {
		t.Fatalf("concurrent scans advanced %d entries", finalHead.Index.NextEntry)
	}
}

func TestZI0HarnessPrepublicationRestoreFailurePoisons(t *testing.T) {
	// The normal injected prepublication paths are retryable. This focused
	// package-level control makes reload of the prior root impossible after trie
	// sync and verifies that no subsequent API silently proceeds on uncertain
	// state. It does not alter production EVM decisions.
	z := zi0HarnessSmallZIP()
	directory := t.TempDir()
	session, gas := zi0HarnessOpenAndUpload(t, common.HexToAddress("0x5a4930730004"), z, directory)
	defer session.Close()
	zi0HarnessSealCreate(t, session, &gas)
	// Make only the in-memory prior-root cache invalid. The durable manifest is
	// left untouched; restore must fail closed rather than continue at the newly
	// committed but unpublished root.
	session.root = common.HexToHash("0xdeadbeef")
	session.testFault = func(point faultPoint) error {
		if point == faultAfterTrie {
			return errors.New("commit publication and reload failure")
		}
		return nil
	}
	op, err := session.Discover(OrdinaryGas)
	if err == nil || op.StateRoot != (common.Hash{}) || len(op.Logs) != 0 {
		t.Fatalf("reload failure leaked success: op=%+v err=%v", op, err)
	}
	if _, err := session.Head(OrdinaryGas); err == nil {
		t.Fatal("uncertain restore remained usable")
	}
}
