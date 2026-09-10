package zi0

import (
	"archive/zip"
	"bytes"
	"encoding/binary"
	"encoding/json"
	zi0assets "github.com/ethereum/go-ethereum/jvmevm/artifactstore/zi0/runtime"
	"math/big"
	"testing"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/as0"
)

func zi0ParentHash(t *testing.T, ts []string, vals ...any) common.Hash {
	t.Helper()
	var args abi.Arguments
	for _, s := range ts {
		v, e := abi.NewType(s, "", nil)
		if e != nil {
			t.Fatal(e)
		}
		args = append(args, abi.Argument{Type: v})
	}
	b, e := args.Pack(vals...)
	if e != nil {
		t.Fatal(e)
	}
	return crypto.Keccak256Hash(b)
}
func zi0ParentPage(t *testing.T, addr common.Address, i uint32, b []byte) common.Hash {
	return zi0ParentHash(t, []string{"bytes32", "address", "uint32", "uint32", "bytes32"}, crypto.Keccak256Hash([]byte("MC-AS0/page/v1")), addr, i, uint32(len(b)), crypto.Keccak256Hash(b))
}
func zi0ParentZIP(t *testing.T) []byte {
	t.Helper()
	var b bytes.Buffer
	w := zip.NewWriter(&b)
	for _, name := range []string{"first.txt", "dir/second.txt"} {
		f, e := w.CreateHeader(&zip.FileHeader{Name: name, Method: zip.Store})
		if e != nil {
			t.Fatal(e)
		}
		if _, e = f.Write([]byte("parent opaque fixture")); e != nil {
			t.Fatal(e)
		}
	}
	if e := w.Close(); e != nil {
		t.Fatal(e)
	}
	return b.Bytes()
}
func TestZI0ParentFreshOrdinaryCreate(t *testing.T) {
	for _, disk := range []bool{false, true} {
		label := "memory"
		if disk {
			label = "disk"
		}
		t.Run(label, func(t *testing.T) {
			owner := common.HexToAddress("0x5a4930700001")
			var s *Session
			var e error
			if disk {
				s, e = Open(t.TempDir(), owner, 1)
			} else {
				s, e = NewMemory(owner, 1)
			}
			if e != nil {
				t.Fatal(e)
			}
			defer s.Close()
			c, e := s.Creation()
			if e != nil {
				t.Fatal(e)
			}
			if !c.Performed || c.GasUsed == 0 || c.Controller != crypto.CreateAddress(owner, 0) {
				t.Fatalf("fresh session did not actually CREATE AS0: %+v", c)
			}
			h, e := s.Head(OrdinaryGas)
			if e != nil {
				t.Fatal(e)
			}
			if h.AS0.Owner != owner || h.AS0.Controller != c.Controller || h.Index.Address != (common.Address{}) {
				t.Fatal("wrong fresh EVM identity")
			}
		})
	}
}
func TestZI0ParentRealArtifactPipeline(t *testing.T) {
	for _, disk := range []bool{false, true} {
		label := "memory"
		if disk {
			label = "disk"
		}
		t.Run(label, func(t *testing.T) {
			raw := zi0ParentZIP(t)
			owner := common.HexToAddress("0x5a4930700002")
			dir := ""
			var s *Session
			var e error
			if disk {
				dir = t.TempDir()
				s, e = Open(dir, owner, uint32(len(raw)))
			} else {
				s, e = NewMemory(owner, uint32(len(raw)))
			}
			if e != nil {
				t.Fatal(e)
			}
			defer func() { s.Close() }()
			c, e := s.Creation()
			if e != nil {
				t.Fatal(e)
			}
			for at := 0; at < len(raw); at += int(as0.PageSize) {
				end := at + int(as0.PageSize)
				if end > len(raw) {
					end = len(raw)
				}
				b := raw[at:end]
				if _, e = s.Append(uint32(at), b, zi0ParentPage(t, c.Controller, uint32(at)/as0.PageSize, b), OrdinaryGas); e != nil {
					t.Fatal(e)
				}
			}
			h, e := s.Head(OrdinaryGas)
			if e != nil {
				t.Fatal(e)
			}
			if _, e = s.Seal(uint32(len(raw)), h.AS0.ChainCommitment, OrdinaryGas); e != nil {
				t.Fatal(e)
			}
			h, e = s.Head(OrdinaryGas)
			if e != nil {
				t.Fatal(e)
			}
			op, e := s.CreateIndex(h.AS0.ContentCommitment, OrdinaryGas)
			if e != nil {
				t.Fatal(e)
			}
			if op.CreatedAddress != crypto.CreateAddress(owner, 1) {
				t.Fatal("ZI0 not ordinary second CREATE")
			}
			if _, e = s.Discover(OrdinaryGas); e != nil {
				t.Fatal(e)
			}
			h, e = s.Head(OrdinaryGas)
			if e != nil {
				t.Fatal(e)
			}
			if _, e = s.Scan(h.Index.NextEntry, h.Index.CDCursor, h.Index.Rolling, 64, OrdinaryGas); e != nil {
				t.Fatal(e)
			}
			h, e = s.Head(OrdinaryGas)
			if e != nil {
				t.Fatal(e)
			}
			if _, e = s.Finish(h.Index.Count, h.Index.CDCursor, h.Index.Rolling, OrdinaryGas); e != nil {
				t.Fatal(e)
			}
			if disk {
				if e = s.Close(); e != nil {
					t.Fatal(e)
				}
				s, e = Open(dir, owner, uint32(len(raw)))
				if e != nil {
					t.Fatal(e)
				}
			}
			r, e := s.Lookup([]byte("dir/second.txt"), OrdinaryGas)
			if e != nil || !r.Found || r.Index != 1 {
				t.Fatalf("real lookup=%+v err=%v", r, e)
			}
		})
	}
}

func TestZI0ParentExactABINoEvent(t *testing.T) {
	var d struct {
		ABI []map[string]any `json:"abi"`
	}
	if e := json.Unmarshal(zi0assets.Artifact(), &d); e != nil {
		t.Fatal(e)
	}
	d.ABI = append(d.ABI, map[string]any{"type": "event", "name": "NotFrozen", "anonymous": false, "inputs": []any{}})
	raw, e := json.Marshal(d.ABI)
	if e != nil {
		t.Fatal(e)
	}
	a, e := abi.JSON(bytes.NewReader(raw))
	if e != nil {
		t.Fatal(e)
	}
	if e = validateABI(a); e == nil {
		t.Fatal("non-frozen event accepted by exact ABI validator")
	}
}

func TestZI0ParentAS0HeadMalformedCopiedState(t *testing.T) {
	for _, kind := range []string{"page-count-truncation", "partial-before-end", "wrong-owner"} {
		t.Run(kind, func(t *testing.T) {
			s, e := NewMemory(common.HexToAddress("0x5a4930700003"), 8193)
			if e != nil {
				t.Fatal(e)
			}
			defer s.Close()
			original := s.state
			s.state = original.Copy()
			defer func() { s.state = original }()
			// TEST-only changed state, never a production page/state installer.
			if kind == "page-count-truncation" {
				s.state.SetState(s.as0Address, common.BigToHash(big.NewInt(3)), common.BigToHash(new(big.Int).Lsh(big.NewInt(1), 32)))
			} else {
				word := s.state.GetState(s.as0Address, common.Hash{})
				if kind == "partial-before-end" {
					binary.BigEndian.PutUint32(word[4:8], 1)
				} else {
					word[31] ^= 1
				}
				s.state.SetState(s.as0Address, common.Hash{}, word)
			}
			if h, e := s.Head(OrdinaryGas); e == nil {
				t.Fatalf("noncanonical %s accepted: %+v", kind, h.AS0)
			}
		})
	}
}
