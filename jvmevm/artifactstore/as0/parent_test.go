package as0

import (
	"bytes"
	"crypto/sha256"
	"encoding/binary"
	"encoding/json"
	"errors"
	"fmt"
	"math/big"
	"os"
	"path/filepath"
	"testing"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/state"
	"github.com/ethereum/go-ethereum/core/tracing"
	"github.com/ethereum/go-ethereum/core/types"
	evmruntime "github.com/ethereum/go-ethereum/core/vm/runtime"
	"github.com/ethereum/go-ethereum/crypto"
	as0assets "github.com/ethereum/go-ethereum/jvmevm/artifactstore/as0/runtime"
)

func TestAS0Parent16ExactABI(t *testing.T) {
	var doc struct {
		ABI []map[string]any `json:"abi"`
	}
	if e := json.Unmarshal(as0assets.Artifact(), &doc); e != nil {
		t.Fatal(e)
	}
	for _, kind := range []string{"fallback", "receive", "anonymous-PageIssued", "anonymous-Sealed"} {
		t.Run(kind, func(t *testing.T) {
			data, _ := json.Marshal(doc.ABI)
			var entries []map[string]any
			if e := json.Unmarshal(data, &entries); e != nil {
				t.Fatal(e)
			}
			switch kind {
			case "fallback":
				entries = append(entries, map[string]any{"type": "fallback", "stateMutability": "nonpayable"})
			case "receive":
				entries = append(entries, map[string]any{"type": "receive", "stateMutability": "payable"})
			default:
				for _, entry := range entries {
					if entry["type"] == "event" && "anonymous-"+entry["name"].(string) == kind {
						entry["anonymous"] = true
					}
				}
			}
			encoded, _ := json.Marshal(entries)
			a, e := abi.JSON(bytes.NewReader(encoded))
			if e != nil {
				t.Fatal(e)
			}
			if e := validateABI(a); e == nil {
				t.Fatal("non-frozen ABI shape accepted")
			}
		})
	}
}

func TestAS0Parent15NestedStateLinkRefused(t *testing.T) {
	dir := t.TempDir()
	owner := common.HexToAddress("0xa501")
	s, e := Open(dir, owner, 1)
	if e != nil {
		t.Fatal(e)
	}
	if e = s.Close(); e != nil {
		t.Fatal(e)
	}
	current := filepath.Join(dir, stateDirectory, "CURRENT")
	original, e := os.ReadFile(current)
	if e != nil {
		t.Fatal(e)
	}
	outside := filepath.Join(t.TempDir(), "saved-current")
	if e = os.WriteFile(outside, original, 0600); e != nil {
		t.Fatal(e)
	}
	if e = os.Remove(current); e != nil {
		t.Fatal(e)
	}
	if e = os.Symlink(outside, current); e != nil {
		t.Fatal(e)
	}
	opened, e := Open(dir, owner, 1)
	if opened != nil {
		opened.Close()
	}
	if e == nil {
		t.Fatal("nested LevelDB CURRENT symlink accepted")
	}
	after, e := os.ReadFile(outside)
	if e != nil || !bytes.Equal(after, original) {
		t.Fatal("external file changed during refused open")
	}
}

func as0ParentHash(t *testing.T, types []string, values ...any) common.Hash {
	t.Helper()
	args := make(abi.Arguments, len(types))
	for i, text := range types {
		typ, e := abi.NewType(text, "", nil)
		if e != nil {
			t.Fatal(e)
		}
		args[i] = abi.Argument{Type: typ}
	}
	raw, e := args.Pack(values...)
	if e != nil {
		t.Fatal(e)
	}
	return crypto.Keccak256Hash(raw)
}
func as0ParentPi(t *testing.T, at common.Address, index uint32, raw []byte) common.Hash {
	return as0ParentHash(t, []string{"bytes32", "address", "uint32", "uint32", "bytes32"}, crypto.Keccak256Hash([]byte("MC-AS0/page/v1")), at, index, uint32(len(raw)), crypto.Keccak256Hash(raw))
}

func TestAS0Parent0102ConstructorCodeIdentity(t *testing.T) {
	init, e := InitCode()
	if e != nil {
		t.Fatal(e)
	}
	code, e := Runtime()
	if e != nil {
		t.Fatal(e)
	}
	if len(init) != 3166 || len(code) != 2831 || fmt.Sprintf("%x", sha256.Sum256(code)) != "e7f8e95b0af80bf15e89a01ceb635d8ae858560c606cc86ac3877d8f0de69b13" {
		t.Fatal("artifact pin")
	}
	a, e := ABI()
	if e != nil {
		t.Fatal(e)
	}
	for _, length := range []uint32{0, 1, 8193, MaxLength, MaxLength + 1} {
		for _, owner := range []common.Address{{}, common.HexToAddress("0xa502")} {
			t.Run(fmt.Sprintf("%d/%s", length, owner), func(t *testing.T) {
				st, e := state.New(types.EmptyRootHash, state.NewDatabaseForTesting())
				if e != nil {
					t.Fatal(e)
				}
				cfg := (&Session{owner: owner}).runtimeConfig(st, 100_000_000)
				args, e := a.Pack("", length)
				if e != nil {
					t.Fatal(e)
				}
				out, at, left, e := evmruntime.Create(append(append([]byte(nil), init...), args...), cfg)
				want := uint64(0)
				if length == 0 || length > MaxLength {
					want = 1
				} else if owner == (common.Address{}) {
					want = 2
				}
				if want != 0 {
					if e == nil {
						t.Fatal("invalid constructor succeeded")
					}
					errABI := a.Errors["AS0Error"]
					if len(out) != 36 || !bytes.Equal(out[:4], errABI.ID[:4]) || new(big.Int).SetBytes(out[4:]).Uint64() != want {
						t.Fatalf("constructor error%x want%d", out, want)
					}
					return
				}
				if e != nil || left >= 100_000_000 || !bytes.Equal(out, code) || !bytes.Equal(st.GetCode(at), code) {
					t.Fatalf("ordinary CREATE identity failed %v", e)
				}
			})
		}
	}
}

func TestAS0Parent030405060708PageRootsAndByteRanges(t *testing.T) {
	owner := common.HexToAddress("0xa503")
	const length = 2*8192 + 17
	s, e := NewMemory(owner, length)
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	creation, e := s.Creation()
	if e != nil || !creation.Performed {
		t.Fatal("missing CREATE")
	}
	at := creation.Controller
	chain := as0ParentHash(t, []string{"bytes32", "address", "address", "uint32", "uint32"}, crypto.Keccak256Hash([]byte("MC-AS0/chain/v1")), at, owner, uint32(length), uint32(8192))
	all := make([]byte, length)
	for i := range all {
		all[i] = byte(i*73 + 239)
	}
	for index := 0; index < 3; index++ {
		lo, hi := index*8192, (index+1)*8192
		if hi > len(all) {
			hi = len(all)
		}
		raw := all[lo:hi]
		pi := as0ParentPi(t, at, uint32(index), raw)
		if _, e := s.Append(uint32(lo), raw, pi, 100_000_000); e != nil {
			t.Fatal(e)
		}
		page, e := s.Page(uint64(index), 100_000_000)
		if e != nil {
			t.Fatal(e)
		}
		if page.Address != crypto.CreateAddress(at, uint64(index+1)) {
			t.Fatal("child not ordinary ordered CREATE")
		}
		expectedCode := append([]byte{0}, raw...)
		ch := crypto.Keccak256Hash(expectedCode)
		if !bytes.Equal(s.stateDB.GetCode(page.Address), expectedCode) || page.CodeHash != ch || page.Commitment != pi {
			t.Fatal("page code/commitment")
		}
		chain = as0ParentHash(t, []string{"bytes32", "bytes32", "uint32", "uint32", "address", "bytes32", "bytes32"}, crypto.Keccak256Hash([]byte("MC-AS0/ordered/v1")), chain, uint32(index), uint32(len(raw)), page.Address, ch, pi)
		h, e := s.Head(100_000_000)
		if e != nil || h.ChainCommitment != chain || h.PageCount != uint32(index+1) || h.Cursor != uint32(hi) {
			t.Fatal("independent ordered root")
		}
		// Calling a data page executes STOP, not the bytes that happen to follow it.
		out, _, e := evmruntime.Call(page.Address, []byte{1, 2, 3}, s.runtimeConfig(s.stateDB.Copy(), 100_000_000))
		if e != nil || len(out) != 0 {
			t.Fatal("page bytes executed instead of STOP")
		}
	}
	before, e := s.Head(100_000_000)
	if e != nil {
		t.Fatal(e)
	}
	bad, e := s.Append(length, nil, as0ParentPi(t, at, 3, nil), 100_000_000)
	if e == nil || as0HarnessErrorCode(t, bad) != 5 {
		t.Fatal("at-full empty append")
	}
	after, e := s.Head(100_000_000)
	if e != nil || before.StateRoot != after.StateRoot || before.ChainCommitment != after.ChainCommitment {
		t.Fatal("empty append changed state")
	}
	if _, e = s.Seal(length, chain, 100_000_000); e != nil {
		t.Fatal(e)
	}
	sealed, e := s.Head(100_000_000)
	if e != nil {
		t.Fatal(e)
	}
	root := as0ParentHash(t, []string{"bytes32", "address", "address", "uint32", "uint32", "uint32", "bytes32"}, crypto.Keccak256Hash([]byte("MC-AS0/content/v1")), at, owner, uint32(length), uint32(3), uint32(8192), chain)
	if sealed.ContentCommitment != root {
		t.Fatal("independent seal root")
	}
	for _, offset := range []uint32{0, 1, 4096, 8190, 8191, 8192, 12288, 16380, 16383, 16384, length} {
		for _, n := range []uint32{0, 1, 2, 17, 4096} {
			got, e := s.Read(offset, n, 100_000_000)
			if uint64(offset)+uint64(n) > length {
				if e == nil {
					t.Fatal("range overflow accepted")
				}
				continue
			}
			if e != nil || !bytes.Equal(got.Bytes, all[offset:offset+n]) {
				t.Fatalf("range%d/%d %v", offset, n, e)
			}
		}
	}
	end, e := s.Head(100_000_000)
	if e != nil || end.StateRoot != sealed.StateRoot || end.ContentCommitment != sealed.ContentCommitment {
		t.Fatal("views changed authority")
	}
}

func TestAS0Parent09ReadChecksIssuedCode(t *testing.T) {
	s, e := NewMemory(common.HexToAddress("0xa504"), 1)
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	creation, _ := s.Creation()
	raw := []byte{9}
	if _, e = s.Append(0, raw, as0ParentPi(t, creation.Controller, 0, raw), 100_000_000); e != nil {
		t.Fatal(e)
	}
	h, _ := s.Head(100_000_000)
	if _, e = s.Seal(1, h.ChainCommitment, 100_000_000); e != nil {
		t.Fatal(e)
	}
	p, _ := s.Page(0, 100_000_000)
	copyState := s.stateDB.Copy()
	// TEST-only damaged copied state; no page installer exists in production.
	copyState.SetCode(p.Address, []byte{0, 8}, tracing.CodeChangeUnspecified)
	input, e := s.contractABI.Pack("read", uint32(0), uint32(1))
	if e != nil {
		t.Fatal(e)
	}
	out, _, e := evmruntime.Call(s.controller, input, s.runtimeConfig(copyState, 100_000_000))
	if e == nil || as0HarnessRawErrorCode(t, out) != 14 {
		t.Fatal("changed page code was trusted")
	}
	got, e := s.Read(0, 1, 100_000_000)
	if e != nil || !bytes.Equal(got.Bytes, raw) {
		t.Fatal("control page was changed")
	}
}

type as0ParentSyncDB struct {
	durableDB
	syncs int
}

func (d *as0ParentSyncDB) SyncKeyValue() error { d.syncs++; return d.durableDB.SyncKeyValue() }

func TestAS0Parent101314PerCallPublicationAndRetry(t *testing.T) {
	dir := t.TempDir()
	owner := common.HexToAddress("0xa505")
	s, e := Open(dir, owner, 8193)
	if e != nil {
		t.Fatal(e)
	}
	counted := &as0ParentSyncDB{durableDB: s.disk}
	s.disk = counted
	created, _ := s.Creation()
	raw := bytes.Repeat([]byte{7}, 8192)
	pi := as0ParentPi(t, created.Controller, 0, raw)
	initial, _ := s.Head(100_000_000)
	injected := false
	s.testFault = func(p faultPoint) error {
		if p == faultBeforeManifest && !injected {
			injected = true
			return errors.New("parent publication failure")
		}
		return nil
	}
	failed, e := s.Append(0, raw, pi, 100_000_000)
	if e == nil || failed.GasUsed == 0 || failed.StateRoot != (common.Hash{}) || len(failed.Logs) != 0 || len(failed.RevertData) != 0 {
		t.Fatal("publication failure leaked success")
	}
	old, _ := s.Head(100_000_000)
	if old.StateRoot != initial.StateRoot || old.PageCount != 0 {
		t.Fatal("failed publication moved head")
	}
	s.testFault = nil
	for i, data := range [][]byte{raw, {8}} {
		h, _ := s.Head(100_000_000)
		before := counted.syncs
		op, e := s.Append(h.Cursor, data, as0ParentPi(t, created.Controller, uint32(i), data), 100_000_000)
		if e != nil {
			t.Fatal(e)
		}
		if counted.syncs != before+1 {
			t.Fatal("append not individually synced")
		}
		m, e := readManifest(filepath.Join(dir, manifestName))
		if e != nil || m.StateRoot != op.StateRoot {
			t.Fatal("append not individually published")
		}
	}
	h, _ := s.Head(100_000_000)
	before := counted.syncs
	op, e := s.Seal(h.Cursor, h.ChainCommitment, 100_000_000)
	if e != nil || counted.syncs != before+1 {
		t.Fatal("seal not synced", e)
	}
	m, e := readManifest(filepath.Join(dir, manifestName))
	if e != nil || m.StateRoot != op.StateRoot {
		t.Fatal("seal not published")
	}
	first, _ := s.Page(0, 100_000_000)
	if first.Address != crypto.CreateAddress(created.Controller, 1) {
		t.Fatal("retry did not reuse rolled-back child address")
	}
	if e = s.Close(); e != nil {
		t.Fatal(e)
	}
	s, e = Open(dir, owner, 8193)
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	c, _ := s.Creation()
	if c.Performed || c.GasUsed != 0 {
		t.Fatal("reopen deployed code")
	}
	got, e := s.Read(8191, 2, 100_000_000)
	if e != nil || !bytes.Equal(got.Bytes, []byte{7, 8}) {
		t.Fatal("durable raw bytes differ")
	}
}

func TestAS0Parent09HeadRejectsNonfinalPartialCursor(t *testing.T) {
	s, e := NewMemory(common.HexToAddress("0xa506"), 2*PageSize)
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	c, _ := s.Creation()
	raw := make([]byte, PageSize)
	if _, e = s.Append(0, raw, as0ParentPi(t, c.Controller, 0, raw), 100_000_000); e != nil {
		t.Fatal(e)
	}
	original := s.stateDB
	damaged := original.Copy()
	word := damaged.GetState(c.Controller, common.Hash{})
	// TEST-only corrupt copied storage, never a public controller operation.
	// The pinned compiler packs owner/length/cursor/bool in storage slot0.
	binary.BigEndian.PutUint32(word[4:8], 500)
	damaged.SetState(c.Controller, common.Hash{}, word)
	s.stateDB = damaged
	_, e = s.Head(100_000_000)
	s.stateDB = original
	if e == nil {
		t.Fatal("nonfinal partial-page cursor accepted as canonical head")
	}
	if _, e = s.Head(100_000_000); e != nil {
		t.Fatal("valid control failed", e)
	}
}

func TestAS0Parent11All32MiBReadback(t *testing.T) {
	s, e := NewMemory(common.HexToAddress("0xa507"), MaxLength)
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	c, _ := s.Creation()
	inputHash := sha256.New()
	var total, max uint64
	for i := uint32(0); i < MaxPages; i++ {
		raw := make([]byte, PageSize)
		for j := range raw {
			raw[j] = byte(uint32(j)*73 + i*19 + (i >> 8))
		}
		inputHash.Write(raw)
		op, e := s.Append(i*PageSize, raw, as0ParentPi(t, c.Controller, i, raw), 100_000_000)
		if e != nil {
			t.Fatal(e)
		}
		total += op.GasUsed
		if op.GasUsed > max {
			max = op.GasUsed
		}
	}
	h, e := s.Head(100_000_000)
	if e != nil {
		t.Fatal(e)
	}
	if _, e = s.Seal(MaxLength, h.ChainCommitment, 100_000_000); e != nil {
		t.Fatal(e)
	}
	returnedHash := sha256.New()
	var readGas uint64
	for at := uint32(0); at < MaxLength; at += MaxRead {
		r, e := s.Read(at, MaxRead, 100_000_000)
		if e != nil {
			t.Fatal(e)
		}
		returnedHash.Write(r.Bytes)
		readGas += r.GasUsed
	}
	if !bytes.Equal(inputHash.Sum(nil), returnedHash.Sum(nil)) {
		t.Fatal("full EVM raw readback differs from uploaded input")
	}
	t.Logf("all32MiB EVM readback SHA256(transport only)=%x appendTotalGas=%d maxAppendGas=%d readTotalGas=%d", returnedHash.Sum(nil), total, max, readGas)
}
