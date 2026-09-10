package as0

import (
	"bytes"
	"encoding/json"
	"math/big"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	evmruntime "github.com/ethereum/go-ethereum/core/vm/runtime"
)

func TestAS0HarnessErrorPrecedenceBoundsAndCopiedViews(t *testing.T) {
	owner := common.HexToAddress("0x4153300000000000000000000000000000000088")
	session, err := NewMemory(owner, 1)
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	creation, _ := session.Creation()
	directViewCode := func(method string, inputs ...interface{}) uint64 {
		t.Helper()
		callData, err := session.contractABI.Pack(method, inputs...)
		if err != nil {
			t.Fatal(err)
		}
		output, _, callErr := evmruntime.Call(creation.Controller, callData, session.runtimeConfig(session.stateDB.Copy(), as0HarnessOrdinaryGas))
		if callErr == nil {
			t.Fatalf("expected %s view failure", method)
		}
		return as0HarnessRawErrorCode(t, output)
	}
	if code := directViewCode("read", uint32(0), uint32(0)); code != 12 {
		t.Fatalf("unsealed read code=%d", code)
	}
	if code := directViewCode("page", new(big.Int)); code != 11 {
		t.Fatalf("empty page code=%d", code)
	}
	expect := func(want uint64, call func() (Operation, error)) Operation {
		t.Helper()
		result, err := call()
		if err == nil || as0HarnessErrorCode(t, result) != want {
			t.Fatalf("want AS0Error(%d): result=%+v err=%v", want, result, err)
		}
		return result
	}
	expect(4, func() (Operation, error) { return session.Append(1, nil, common.Hash{}, as0HarnessAppendGas) }) // cursor precedes page length
	expect(5, func() (Operation, error) { return session.Append(0, nil, common.Hash{}, as0HarnessAppendGas) })
	expect(9, func() (Operation, error) { return session.Seal(0, common.Hash{}, as0HarnessOrdinaryGas) })

	// The production session always calls as its bound owner. Exercise error 2
	// directly without adding a caller-selectable authority bypass to its API.
	raw := []byte{7}
	callData, err := session.contractABI.Pack("append", uint32(0), raw, as0HarnessPageCommitment(t, creation.Controller, 0, raw))
	if err != nil {
		t.Fatal(err)
	}
	cfg := session.runtimeConfig(session.stateDB, as0HarnessAppendGas)
	cfg.Origin = common.HexToAddress("0x4153300000000000000000000000000000000099")
	output, _, callErr := evmruntime.Call(creation.Controller, callData, cfg)
	if callErr == nil || as0HarnessRawErrorCode(t, output) != 2 {
		t.Fatalf("wrong-owner output=0x%x err=%v", output, callErr)
	}

	good, err := session.Append(0, raw, as0HarnessPageCommitment(t, creation.Controller, 0, raw), as0HarnessAppendGas)
	if err != nil {
		t.Fatal(err)
	}
	full, _ := session.Head(as0HarnessOrdinaryGas)
	wrongChain := full.ChainCommitment
	wrongChain[0] ^= 1
	expect(10, func() (Operation, error) { return session.Seal(1, wrongChain, as0HarnessOrdinaryGas) })
	sealed, err := session.Seal(1, full.ChainCommitment, as0HarnessOrdinaryGas)
	if err != nil || sealed.StateRoot == good.StateRoot {
		t.Fatalf("seal=%+v err=%v", sealed, err)
	}
	expect(3, func() (Operation, error) { return session.Append(1, nil, common.Hash{}, as0HarnessAppendGas) }) // sealed precedes cursor/length
	expect(3, func() (Operation, error) { return session.Seal(0, common.Hash{}, as0HarnessOrdinaryGas) })

	beforeRoot := session.stateDB.Copy().IntermediateRoot(false)
	beforeNonce, beforeLogs := session.stateDB.GetNonce(creation.Controller), len(session.stateDB.Logs())
	if _, err := session.Read(0, MaxRead+1, as0HarnessOrdinaryGas); err == nil || !strings.Contains(err.Error(), "revert_data") {
		t.Fatal("4097-byte read accepted or lost EVM diagnostic")
	}
	if code := directViewCode("read", uint32(0), MaxRead+1); code != 13 {
		t.Fatalf("oversized read code=%d", code)
	}
	if _, err := session.Read(2, 0, as0HarnessOrdinaryGas); err == nil {
		t.Fatal("offset>end empty read accepted")
	}
	if _, err := session.Page(1, as0HarnessOrdinaryGas); err == nil {
		t.Fatal("out-of-range page accepted")
	}
	if _, err := session.Page(0, 0); err == nil {
		t.Fatal("zero gas accepted")
	}
	if _, err := session.Head(MaxGas + 1); err == nil {
		t.Fatal("over-bound gas accepted")
	}
	page, err := session.Page(0, as0HarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	read, err := session.Read(0, 1, as0HarnessOrdinaryGas)
	if err != nil || !bytes.Equal(read.Bytes, raw) {
		t.Fatalf("read=%+v err=%v", read, err)
	}
	if _, err := session.Head(as0HarnessOrdinaryGas); err != nil {
		t.Fatal(err)
	}
	if page.Address == (common.Address{}) || session.stateDB.Copy().IntermediateRoot(false) != beforeRoot || session.stateDB.GetNonce(creation.Controller) != beforeNonce || len(session.stateDB.Logs()) != beforeLogs {
		t.Fatal("copied Head/Page/Read view mutated authority state")
	}
}

func as0HarnessRawErrorCode(t *testing.T, raw []byte) uint64 {
	t.Helper()
	contractABI, err := ABI()
	if err != nil {
		t.Fatal(err)
	}
	def := contractABI.Errors["AS0Error"]
	if len(raw) != 36 || !bytes.Equal(raw[:4], def.ID[:4]) {
		t.Fatalf("non-AS0 revert 0x%x", raw)
	}
	return new(big.Int).SetBytes(raw[4:]).Uint64()
}

func TestAS0HarnessManifestIdentityCodeStateAndMetadataHardening(t *testing.T) {
	owner := common.HexToAddress("0x41533000000000000000000000000000000000aa")
	store := t.TempDir()
	session, err := Open(store, owner, 1)
	if err != nil {
		t.Fatal(err)
	}
	session.Close()
	original, err := readManifest(filepath.Join(store, manifestName))
	if err != nil {
		t.Fatal(err)
	}

	for name, mutate := range map[string]func(*manifest){
		"format":     func(m *manifest) { m.Format++ },
		"context":    func(m *manifest) { m.Context += ":bad" },
		"owner":      func(m *manifest) { m.Owner[0] ^= 1 },
		"controller": func(m *manifest) { m.Controller = common.Address{} },
		"length":     func(m *manifest) { m.DeclaredLength++ },
		"runtime":    func(m *manifest) { m.RuntimeCodeHash[0] ^= 1 },
		"root":       func(m *manifest) { m.StateRoot = common.Hash{} },
	} {
		t.Run(name, func(t *testing.T) {
			copyStore := filepath.Join(t.TempDir(), "store")
			if err := as0HarnessCopyDir(store, copyStore); err != nil {
				t.Fatal(err)
			}
			bad := original
			mutate(&bad)
			as0HarnessWriteManifestRaw(t, copyStore, bad)
			if got, err := Open(copyStore, owner, 1); err == nil {
				got.Close()
				t.Fatal("mismatched manifest accepted")
			}
		})
	}

	// A syntactically valid manifest can name a real but unrelated empty trie
	// root. Metadata passes, then exact controller-code verification refuses it.
	codeMismatch := filepath.Join(t.TempDir(), "store")
	if err := as0HarnessCopyDir(store, codeMismatch); err != nil {
		t.Fatal(err)
	}
	badState := original
	badState.StateRoot = types.EmptyRootHash
	as0HarnessWriteManifestRaw(t, codeMismatch, badState)
	if got, err := Open(codeMismatch, owner, 1); err == nil {
		got.Close()
		t.Fatal("missing controller code at manifest root accepted")
	}

	ownedTemp := filepath.Join(store, ".durable-head-preserve")
	if err := os.WriteFile(ownedTemp, []byte("diagnostic"), 0o600); err != nil {
		t.Fatal(err)
	}
	reopened, err := Open(store, owner, 1)
	if err != nil {
		t.Fatal(err)
	}
	reopened.Close()
	if got, err := os.ReadFile(ownedTemp); err != nil || string(got) != "diagnostic" {
		t.Fatal("owned unpublished temp was removed")
	}

	oversized := filepath.Join(t.TempDir(), "store")
	if err := as0HarnessCopyDir(store, oversized); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(oversized, manifestName), bytes.Repeat([]byte{'x'}, int(manifestMaxSize)+1), 0o600); err != nil {
		t.Fatal(err)
	}
	if got, err := Open(oversized, owner, 1); err == nil {
		got.Close()
		t.Fatal("oversized manifest accepted")
	}
}

func as0HarnessWriteManifestRaw(t *testing.T, directory string, value manifest) {
	t.Helper()
	raw, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(directory, manifestName), raw, 0o600); err != nil {
		t.Fatal(err)
	}
}

func TestAS0HarnessClosedAndArgumentValidation(t *testing.T) {
	if _, err := NewMemory(common.Address{}, 0); err == nil || !strings.Contains(err.Error(), "length") {
		t.Fatal("host validation did not preserve length-before-owner precedence")
	}
	if _, err := NewMemory(common.Address{}, 1); err == nil || !strings.Contains(err.Error(), "owner") {
		t.Fatal("zero owner accepted")
	}
	if _, err := NewMemory(common.HexToAddress("0x1"), MaxLength+1); err == nil {
		t.Fatal("oversized length accepted")
	}
	if _, err := Open("", common.HexToAddress("0x1"), 1); err == nil {
		t.Fatal("empty directory accepted")
	}
	session, err := NewMemory(common.HexToAddress("0x1"), 1)
	if err != nil {
		t.Fatal(err)
	}
	if err := session.Close(); err != nil {
		t.Fatal(err)
	}
	if err := session.Close(); err != nil {
		t.Fatal(err)
	}
	if _, err := session.Head(as0HarnessOrdinaryGas); err == nil {
		t.Fatal("closed session usable")
	}
}
