package as0

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"math/big"
	"os"
	"path/filepath"
	"reflect"
	"testing"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
)

const (
	as0HarnessOrdinaryGas = uint64(100_000_000)
	as0HarnessAppendGas   = uint64(3_000_000)
)

func as0HarnessEncoded(t *testing.T, types []string, values ...interface{}) []byte {
	t.Helper()
	var args abi.Arguments
	for _, name := range types {
		typ, err := abi.NewType(name, "", nil)
		if err != nil {
			t.Fatal(err)
		}
		args = append(args, abi.Argument{Type: typ})
	}
	out, err := args.Pack(values...)
	if err != nil {
		t.Fatal(err)
	}
	return out
}

func as0HarnessPageCommitment(t *testing.T, controller common.Address, index uint32, raw []byte) common.Hash {
	t.Helper()
	return crypto.Keccak256Hash(as0HarnessEncoded(t,
		[]string{"bytes32", "address", "uint32", "uint32", "bytes32"},
		crypto.Keccak256Hash([]byte("MC-AS0/page/v1")), controller, index, uint32(len(raw)), crypto.Keccak256Hash(raw)))
}

func as0HarnessInitialChain(t *testing.T, controller, owner common.Address, length uint32) common.Hash {
	t.Helper()
	return crypto.Keccak256Hash(as0HarnessEncoded(t,
		[]string{"bytes32", "address", "address", "uint32", "uint32"},
		crypto.Keccak256Hash([]byte("MC-AS0/chain/v1")), controller, owner, length, PageSize))
}

func as0HarnessNextChain(t *testing.T, previous common.Hash, index, length uint32, page common.Address, codeHash, pi common.Hash) common.Hash {
	t.Helper()
	return crypto.Keccak256Hash(as0HarnessEncoded(t,
		[]string{"bytes32", "bytes32", "uint32", "uint32", "address", "bytes32", "bytes32"},
		crypto.Keccak256Hash([]byte("MC-AS0/ordered/v1")), previous, index, length, page, codeHash, pi))
}

func as0HarnessContent(t *testing.T, controller, owner common.Address, length, pages uint32, chain common.Hash) common.Hash {
	t.Helper()
	return crypto.Keccak256Hash(as0HarnessEncoded(t,
		[]string{"bytes32", "address", "address", "uint32", "uint32", "uint32", "bytes32"},
		crypto.Keccak256Hash([]byte("MC-AS0/content/v1")), controller, owner, length, pages, PageSize, chain))
}

func as0HarnessGeneratedPage(index uint32, length int) []byte {
	raw := make([]byte, length)
	x := uint32(0x53305eed) ^ index*0x9e3779b9
	for i := range raw {
		x ^= x << 13
		x ^= x >> 17
		x ^= x << 5
		raw[i] = byte(x)
	}
	return raw
}

func as0HarnessErrorCode(t *testing.T, result Operation) uint64 {
	t.Helper()
	if len(result.RevertData) != 36 {
		t.Fatalf("revert length=%d data=0x%x", len(result.RevertData), result.RevertData)
	}
	contractABI, err := ABI()
	if err != nil {
		t.Fatal(err)
	}
	definition := contractABI.Errors["AS0Error"]
	if !bytes.Equal(result.RevertData[:4], definition.ID[:4]) {
		t.Fatalf("wrong error selector 0x%x", result.RevertData[:4])
	}
	return new(big.Int).SetBytes(result.RevertData[4:]).Uint64()
}

func TestAS0HarnessEmbeddedArtifactAndOrdinaryCreate(t *testing.T) {
	runtimeCode, err := Runtime()
	if err != nil {
		t.Fatal(err)
	}
	initCode, err := InitCode()
	if err != nil {
		t.Fatal(err)
	}
	contractABI, err := ABI()
	if err != nil {
		t.Fatal(err)
	}
	if len(runtimeCode) != 2831 || len(initCode) != 3166 {
		t.Fatalf("artifact sizes runtime/init=%d/%d", len(runtimeCode), len(initCode))
	}
	if got := crypto.Keccak256Hash(runtimeCode); got == (common.Hash{}) {
		t.Fatal("zero runtime code hash")
	} else {
		t.Logf("runtime=%dB sha256=%s codeHash=%s init=%dB sha256=%s", len(runtimeCode), as0HarnessSHA256(runtimeCode), got, len(initCode), as0HarnessSHA256(initCode))
	}
	if len(contractABI.Methods) != 14 || len(contractABI.Events) != 2 || len(contractABI.Errors) != 1 {
		t.Fatal("ABI shape changed")
	}
	owner := common.HexToAddress("0x4153300000000000000000000000000000000011")
	session, err := NewMemory(owner, 1)
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	creation, err := session.Creation()
	if err != nil {
		t.Fatal(err)
	}
	if !creation.Performed || creation.Controller == (common.Address{}) || creation.GasUsed == 0 || creation.GasUsed > as0HarnessOrdinaryGas || creation.RuntimeCodeHash != crypto.Keccak256Hash(runtimeCode) || creation.StateRoot == (common.Hash{}) {
		t.Fatalf("creation=%+v", creation)
	}
	if creation.Controller != crypto.CreateAddress(owner, 0) || !bytes.Equal(session.stateDB.GetCode(creation.Controller), runtimeCode) {
		t.Fatal("controller was not ordinary CREATE address/code")
	}
	head, err := session.Head(as0HarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	if head.Owner != owner || head.Controller != creation.Controller || head.DeclaredLength != 1 || head.Cursor != 0 || head.Sealed || head.PageCount != 0 || head.ContentCommitment != (common.Hash{}) || head.PageSize != PageSize || head.MaxPages != MaxPages || head.MaxLength != MaxLength || head.GasUsed == 0 {
		t.Fatalf("head=%+v", head)
	}
	// All public defensive-copy surfaces must be independent.
	runtimeCode[0] ^= 0xff
	initCode[0] ^= 0xff
	if again, _ := Runtime(); bytes.Equal(runtimeCode, again) {
		t.Fatal("Runtime aliases embedded bytes")
	}
	if again, _ := InitCode(); bytes.Equal(initCode, again) {
		t.Fatal("InitCode aliases embedded bytes")
	}
}

func as0HarnessSHA256(raw []byte) string {
	// Host SHA-256 here is only an embedded-artifact transport/report pin.
	h := sha256.Sum256(raw)
	return hex.EncodeToString(h[:])
}

func TestAS0HarnessOneBytePartialExactFullAndReads(t *testing.T) {
	for _, length := range []uint32{1, PageSize + 1, PageSize} {
		t.Run(big.NewInt(int64(length)).String(), func(t *testing.T) {
			owner := common.BytesToAddress([]byte{byte(length), 0x51})
			session, err := NewMemory(owner, length)
			if err != nil {
				t.Fatal(err)
			}
			defer session.Close()
			creation, _ := session.Creation()
			cursor := uint32(0)
			expectedChain := as0HarnessInitialChain(t, creation.Controller, owner, length)
			for index := uint32(0); cursor < length; index++ {
				n := int(PageSize)
				if remain := int(length - cursor); remain < n {
					n = remain
				}
				raw := as0HarnessGeneratedPage(index, n)
				result, err := session.Append(cursor, raw, as0HarnessPageCommitment(t, creation.Controller, index, raw), as0HarnessAppendGas)
				if err != nil || result.GasUsed == 0 || result.StateRoot == (common.Hash{}) || len(result.Logs) != 1 || len(result.RevertData) != 0 {
					t.Fatalf("append %d: result=%+v err=%v", index, result, err)
				}
				page, err := session.Page(uint64(index), as0HarnessOrdinaryGas)
				if err != nil {
					t.Fatal(err)
				}
				wantCode := append([]byte{0}, raw...)
				pi := as0HarnessPageCommitment(t, creation.Controller, index, raw)
				if page.Address != crypto.CreateAddress(creation.Controller, uint64(index+1)) || page.CodeHash != crypto.Keccak256Hash(wantCode) || page.Commitment != pi || !bytes.Equal(session.stateDB.GetCode(page.Address), wantCode) {
					t.Fatalf("page %d=%+v", index, page)
				}
				expectedChain = as0HarnessNextChain(t, expectedChain, index, uint32(n), page.Address, page.CodeHash, pi)
				cursor += uint32(n)
			}
			head, err := session.Head(as0HarnessOrdinaryGas)
			if err != nil {
				t.Fatal(err)
			}
			if head.Cursor != length || head.PageCount != (length+PageSize-1)/PageSize || head.Sealed || head.ChainCommitment != expectedChain {
				t.Fatalf("full-before-seal head=%+v expectedChain=%s", head, expectedChain)
			}
			empty, err := session.Append(length, nil, as0HarnessPageCommitment(t, creation.Controller, head.PageCount, nil), as0HarnessAppendGas)
			if err == nil || as0HarnessErrorCode(t, empty) != 5 {
				t.Fatalf("at-full empty append result=%+v err=%v", empty, err)
			}
			afterEmpty, _ := session.Head(as0HarnessOrdinaryGas)
			if afterEmpty.Cursor != head.Cursor || afterEmpty.PageCount != head.PageCount || afterEmpty.ChainCommitment != head.ChainCommitment || session.stateDB.GetNonce(creation.Controller) != uint64(head.PageCount)+1 {
				t.Fatalf("empty append changed full shape: before=%+v after=%+v nonce=%d", head, afterEmpty, session.stateDB.GetNonce(creation.Controller))
			}
			sealed, err := session.Seal(length, head.ChainCommitment, as0HarnessOrdinaryGas)
			if err != nil || sealed.GasUsed == 0 || len(sealed.Logs) != 1 || sealed.StateRoot == (common.Hash{}) {
				t.Fatalf("seal=%+v err=%v", sealed, err)
			}
			final, err := session.Head(as0HarnessOrdinaryGas)
			wantContent := as0HarnessContent(t, creation.Controller, owner, length, head.PageCount, expectedChain)
			if err != nil || !final.Sealed || final.ContentCommitment != wantContent || final.PageCount != head.PageCount {
				t.Fatalf("final=%+v wantContent=%s err=%v", final, wantContent, err)
			}
			all := make([]byte, 0, length)
			for i := uint32(0); i < final.PageCount; i++ {
				n := int(PageSize)
				if remain := int(length - uint32(len(all))); remain < n {
					n = remain
				}
				all = append(all, as0HarnessGeneratedPage(i, n)...)
			}
			got, err := session.Read(0, min32(length, MaxRead), as0HarnessOrdinaryGas)
			if err != nil || got.GasUsed == 0 || !bytes.Equal(got.Bytes, all[:min32(length, MaxRead)]) {
				t.Fatalf("read=%x gas=%d err=%v", got.Bytes, got.GasUsed, err)
			}
			end, err := session.Read(length, 0, as0HarnessOrdinaryGas)
			if err != nil || len(end.Bytes) != 0 {
				t.Fatalf("end empty=%+v err=%v", end, err)
			}
		})
	}
}

func min32(a, b uint32) uint32 {
	if a < b {
		return a
	}
	return b
}

func TestAS0HarnessPostCreateRollbackOOGAndRetryAddress(t *testing.T) {
	owner := common.HexToAddress("0x4153300000000000000000000000000000000022")
	session, err := NewMemory(owner, PageSize)
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	creation, _ := session.Creation()
	raw := as0HarnessGeneratedPage(0, int(PageSize))
	pi := as0HarnessPageCommitment(t, creation.Controller, 0, raw)
	beforeRoot := session.stateDB.Copy().IntermediateRoot(false)
	beforeNonce, beforeLogs := session.stateDB.GetNonce(creation.Controller), len(session.stateDB.Logs())
	child := crypto.CreateAddress(creation.Controller, beforeNonce)
	wrong := pi
	wrong[0] ^= 1
	bad, err := session.Append(0, raw, wrong, as0HarnessAppendGas)
	if err == nil || as0HarnessErrorCode(t, bad) != 8 || bad.GasUsed == 0 || bad.StateRoot != (common.Hash{}) || len(bad.Logs) != 0 {
		t.Fatalf("wrong Pi=%+v err=%v", bad, err)
	}
	if session.stateDB.Copy().IntermediateRoot(false) != beforeRoot || session.stateDB.GetNonce(creation.Controller) != beforeNonce || len(session.stateDB.GetCode(child)) != 0 || len(session.stateDB.Logs()) != beforeLogs {
		t.Fatal("post-CREATE assertion did not restore root/nonce/code/logs")
	}
	oog, err := session.Append(0, raw, pi, 1_800_000)
	if err == nil || oog.GasUsed != 1_800_000 || len(oog.RevertData) != 0 || session.stateDB.Copy().IntermediateRoot(false) != beforeRoot || session.stateDB.GetNonce(creation.Controller) != beforeNonce || len(session.stateDB.GetCode(child)) != 0 || len(session.stateDB.Logs()) != beforeLogs {
		t.Fatalf("OOG rollback=%+v err=%v", oog, err)
	}
	good, err := session.Append(0, raw, pi, as0HarnessAppendGas)
	if err != nil {
		t.Fatal(err)
	}
	page, err := session.Page(0, as0HarnessOrdinaryGas)
	if err != nil || page.Address != child || good.StateRoot == (common.Hash{}) || !bytes.Equal(session.stateDB.GetCode(child), append([]byte{0}, raw...)) {
		t.Fatalf("retry page=%+v operation=%+v err=%v", page, good, err)
	}
}

func TestAS0HarnessDiskEveryCallReopenAndPublicationFailures(t *testing.T) {
	owner := common.HexToAddress("0x4153300000000000000000000000000000000033")
	directory := t.TempDir()
	session, err := Open(directory, owner, PageSize+1)
	if err != nil {
		t.Fatal(err)
	}
	creation, _ := session.Creation()
	if !creation.Performed || creation.GasUsed == 0 {
		t.Fatalf("fresh creation=%+v", creation)
	}
	raw0 := as0HarnessGeneratedPage(0, int(PageSize))
	first, err := session.Append(0, raw0, as0HarnessPageCommitment(t, creation.Controller, 0, raw0), as0HarnessAppendGas)
	if err != nil {
		t.Fatal(err)
	}
	published0, err := readManifest(filepath.Join(directory, manifestName))
	if err != nil || published0.StateRoot != first.StateRoot {
		t.Fatalf("append not published per call: %+v %v", published0, err)
	}
	if err := session.Close(); err != nil {
		t.Fatal(err)
	}

	reopened, err := Open(directory, owner, PageSize+1)
	if err != nil {
		t.Fatal(err)
	}
	defer reopened.Close()
	reopenCreation, _ := reopened.Creation()
	if reopenCreation.Performed || reopenCreation.GasUsed != 0 || reopenCreation.Controller != creation.Controller {
		t.Fatalf("reopen redeployment record=%+v", reopenCreation)
	}
	head, err := reopened.Head(as0HarnessOrdinaryGas)
	if err != nil || head.Cursor != PageSize || head.PageCount != 1 || head.StateRoot != first.StateRoot {
		t.Fatalf("reopened head=%+v err=%v", head, err)
	}

	for _, point := range []faultPoint{faultAfterTrie, faultBeforeManifest} {
		t.Run(big.NewInt(int64(point)).String(), func(t *testing.T) {
			before, _ := reopened.Head(as0HarnessOrdinaryGas)
			fired := false
			reopened.testFault = func(got faultPoint) error {
				if got == point && !fired {
					fired = true
					return errors.New("durability fault")
				}
				return nil
			}
			raw1 := []byte{0xa5}
			failed, err := reopened.Append(PageSize, raw1, as0HarnessPageCommitment(t, creation.Controller, 1, raw1), as0HarnessAppendGas)
			if err == nil || !fired || failed.GasUsed == 0 || failed.StateRoot != (common.Hash{}) || len(failed.Logs) != 0 || len(failed.RevertData) != 0 {
				t.Fatalf("failed publication leaked=%+v err=%v", failed, err)
			}
			after, headErr := reopened.Head(as0HarnessOrdinaryGas)
			if headErr != nil || !reflect.DeepEqual(headWithoutGas(after), headWithoutGas(before)) {
				t.Fatalf("old root not restored: before=%+v after=%+v err=%v", before, after, headErr)
			}
			reopened.testFault = nil
		})
	}
	raw1 := []byte{0xa5}
	second, err := reopened.Append(PageSize, raw1, as0HarnessPageCommitment(t, creation.Controller, 1, raw1), as0HarnessAppendGas)
	if err != nil {
		t.Fatal(err)
	}
	full, _ := reopened.Head(as0HarnessOrdinaryGas)
	sealed, err := reopened.Seal(PageSize+1, full.ChainCommitment, as0HarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	publishedSeal, _ := readManifest(filepath.Join(directory, manifestName))
	if second.StateRoot == first.StateRoot || sealed.StateRoot == second.StateRoot || publishedSeal.StateRoot != sealed.StateRoot {
		t.Fatal("append/seal roots were not individually published")
	}
	got, err := reopened.Read(PageSize-2, 3, as0HarnessOrdinaryGas)
	if err != nil || !bytes.Equal(got.Bytes, []byte{raw0[PageSize-2], raw0[PageSize-1], 0xa5}) {
		t.Fatalf("cross-page read=%x err=%v", got.Bytes, err)
	}
}

func headWithoutGas(h Head) Head { h.GasUsed = 0; return h }

func TestAS0HarnessAmbiguousRenamePoisonsAndReopenRecovers(t *testing.T) {
	owner, directory := common.HexToAddress("0x4153300000000000000000000000000000000044"), t.TempDir()
	session, err := Open(directory, owner, 1)
	if err != nil {
		t.Fatal(err)
	}
	creation, _ := session.Creation()
	session.testFault = func(point faultPoint) error {
		if point == faultAfterManifestRename {
			return errors.New("ambiguous directory fsync")
		}
		return nil
	}
	raw := []byte{9}
	failed, err := session.Append(0, raw, as0HarnessPageCommitment(t, creation.Controller, 0, raw), as0HarnessAppendGas)
	if err == nil || failed.GasUsed == 0 || failed.StateRoot != (common.Hash{}) || len(failed.Logs) != 0 {
		t.Fatalf("ambiguous=%+v err=%v", failed, err)
	}
	if _, err := session.Head(as0HarnessOrdinaryGas); err == nil {
		t.Fatal("poisoned session usable")
	}
	session.Close()
	reopened, err := Open(directory, owner, 1)
	if err != nil {
		t.Fatal(err)
	}
	defer reopened.Close()
	head, err := reopened.Head(as0HarnessOrdinaryGas)
	if err != nil || head.Cursor != 1 || head.PageCount != 1 {
		t.Fatalf("renamed root not recovered: %+v %v", head, err)
	}
}

func TestAS0HarnessNamespaceInitialFailureAndInternalLinks(t *testing.T) {
	owner := common.HexToAddress("0x4153300000000000000000000000000000000055")
	unrelated := t.TempDir()
	keep := filepath.Join(unrelated, "keep")
	if err := os.WriteFile(keep, []byte("preserve"), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := Open(unrelated, owner, 1); err == nil {
		t.Fatal("unrelated directory accepted")
	}
	if got, _ := os.ReadFile(keep); string(got) != "preserve" {
		t.Fatal("unrelated file changed")
	}

	incomplete := t.TempDir()
	if err := os.WriteFile(filepath.Join(incomplete, markerName), []byte(storeMarker), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.Mkdir(filepath.Join(incomplete, stateDirectory), 0o700); err != nil {
		t.Fatal(err)
	}
	if _, err := Open(incomplete, owner, 1); err == nil {
		t.Fatal("initial incomplete directory invented a root")
	}
	if _, err := os.Stat(filepath.Join(incomplete, markerName)); err != nil {
		t.Fatal("incomplete diagnostics removed")
	}

	store := t.TempDir()
	session, err := Open(store, owner, 1)
	if err != nil {
		t.Fatal(err)
	}
	session.Close()
	alias := filepath.Join(t.TempDir(), "alias")
	if err := os.Symlink(store, alias); err != nil {
		t.Fatal(err)
	}
	viaAlias, err := Open(alias, owner, 1)
	if err != nil {
		t.Fatalf("root alias refused: %v", err)
	}
	viaAlias.Close()
	for _, name := range []string{markerName, manifestName, stateDirectory} {
		t.Run(name, func(t *testing.T) {
			copyRoot := t.TempDir()
			copyStore := filepath.Join(copyRoot, "store")
			if err := as0HarnessCopyDir(store, copyStore); err != nil {
				t.Fatal(err)
			}
			original := filepath.Join(copyStore, name)
			moved := filepath.Join(t.TempDir(), "moved")
			if err := os.Rename(original, moved); err != nil {
				t.Fatal(err)
			}
			if err := os.Symlink(moved, original); err != nil {
				t.Fatal(err)
			}
			if bad, err := Open(copyStore, owner, 1); err == nil {
				bad.Close()
				t.Fatal("internal link accepted")
			}
		})
	}
}

func as0HarnessCopyDir(src, dst string) error {
	return filepath.Walk(src, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		rel, _ := filepath.Rel(src, path)
		target := filepath.Join(dst, rel)
		if info.IsDir() {
			return os.MkdirAll(target, info.Mode())
		}
		raw, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		return os.WriteFile(target, raw, info.Mode())
	})
}
