package zi0

import (
	"bytes"
	"errors"
	"reflect"
	"testing"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/as0"
)

func TestZI0HarnessAS0PublicationFailureHidesEventPageAndSeal(t *testing.T) {
	owner := common.HexToAddress("0x5a4930750001")
	directory := t.TempDir()
	session, err := Open(directory, owner, as0.PageSize+1)
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	creation, _ := session.Creation()
	firstRaw := bytes.Repeat([]byte{0xa5}, int(as0.PageSize))
	if _, err := session.Append(0, firstRaw, zi0HarnessPageCommitment(t, creation.Controller, 0, firstRaw), OrdinaryGas); err != nil {
		t.Fatal(err)
	}
	before, _ := session.Head(OrdinaryGas)
	fired := false
	session.testFault = func(point faultPoint) error {
		if point == faultBeforeManifest && !fired {
			fired = true
			return errors.New("append publication failure")
		}
		return nil
	}
	lastRaw := []byte{0x5a}
	failed, err := session.Append(as0.PageSize, lastRaw, zi0HarnessPageCommitment(t, creation.Controller, 1, lastRaw), OrdinaryGas)
	if err == nil || !fired || failed.GasUsed == 0 || failed.StateRoot != (common.Hash{}) || len(failed.Logs) != 0 || len(failed.RevertData) != 0 {
		t.Fatalf("failed append leaked root/event: op=%+v err=%v", failed, err)
	}
	after, headErr := session.Head(OrdinaryGas)
	if headErr != nil || !reflect.DeepEqual(zi0HarnessHeadWithoutGas(before), zi0HarnessHeadWithoutGas(after)) || session.state.GetNonce(creation.Controller) != 2 {
		t.Fatalf("failed append did not restore old page/nonce: before=%+v after=%+v err=%v", before, after, headErr)
	}
	if _, err := session.Page(1, OrdinaryGas); err == nil {
		t.Fatal("failed publication exposed tentative page")
	}
	session.testFault = nil
	retry, err := session.Append(as0.PageSize, lastRaw, zi0HarnessPageCommitment(t, creation.Controller, 1, lastRaw), OrdinaryGas)
	if err != nil || len(retry.Logs) != 1 {
		t.Fatalf("append retry=%+v err=%v", retry, err)
	}
	page, err := session.Page(1, OrdinaryGas)
	if err != nil || page.Address != crypto.CreateAddress(creation.Controller, 2) {
		t.Fatalf("retry page=%+v err=%v", page, err)
	}
	full, _ := session.Head(OrdinaryGas)
	fired = false
	session.testFault = func(point faultPoint) error {
		if point == faultAfterTrie && !fired {
			fired = true
			return errors.New("seal publication failure")
		}
		return nil
	}
	failed, err = session.Seal(full.AS0.Cursor, full.AS0.ChainCommitment, OrdinaryGas)
	if err == nil || !fired || failed.GasUsed == 0 || failed.StateRoot != (common.Hash{}) || len(failed.Logs) != 0 || len(failed.RevertData) != 0 {
		t.Fatalf("failed seal leaked root/event: op=%+v err=%v", failed, err)
	}
	unsealed, err := session.Head(OrdinaryGas)
	if err != nil || unsealed.AS0.Sealed || unsealed.AS0.ContentCommitment != (common.Hash{}) {
		t.Fatalf("failed seal published completion: head=%+v err=%v", unsealed, err)
	}
	session.testFault = nil
	sealed, err := session.Seal(unsealed.AS0.Cursor, unsealed.AS0.ChainCommitment, OrdinaryGas)
	if err != nil || len(sealed.Logs) != 1 {
		t.Fatalf("seal retry=%+v err=%v", sealed, err)
	}
}
