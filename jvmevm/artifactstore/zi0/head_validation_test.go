package zi0

import (
	"math/big"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/common"
)

func zi0HarnessSetPackedField(word common.Hash, shift, width uint, value uint64) common.Hash {
	n := new(big.Int).SetBytes(word[:])
	mask := new(big.Int).Sub(new(big.Int).Lsh(big.NewInt(1), width), big.NewInt(1))
	n.AndNot(n, new(big.Int).Lsh(new(big.Int).Set(mask), shift))
	n.Or(n, new(big.Int).Lsh(new(big.Int).SetUint64(value), shift))
	return common.BigToHash(n)
}

func TestZI0HarnessHeadRejectsAlteredPhaseRootCapsAndBindings(t *testing.T) {
	z := zi0HarnessSmallZIP()
	session, gas := zi0HarnessOpenAndUpload(t, common.HexToAddress("0x5a4930740001"), z, "")
	defer session.Close()
	zi0HarnessSealCreate(t, session, &gas)
	zi0HarnessIndex(t, session, 64, &gas)

	type mutation struct {
		name string
		slot uint64
		set  func(common.Hash) common.Hash
		want string
	}
	for _, tc := range []mutation{
		{"content-binding", 2, func(v common.Hash) common.Hash { v[31] ^= 1; return v }, "bindings"},
		{"phase", 3, func(v common.Hash) common.Hash { return zi0HarnessSetPackedField(v, 32, 8, 3) }, "phase"},
		{"cd-cap", 3, func(v common.Hash) common.Hash { return zi0HarnessSetPackedField(v, 13*8, 32, uint64(MaxCD)+1) }, "caps"},
		{"final-root", 5, func(common.Hash) common.Hash { return common.Hash{} }, "FINAL"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			slot := common.BigToHash(new(big.Int).SetUint64(tc.slot))
			old := session.state.GetState(session.indexAddress, slot)
			session.state.SetState(session.indexAddress, slot, tc.set(old))
			if _, err := session.Head(OrdinaryGas); err == nil || !strings.Contains(err.Error(), tc.want) {
				t.Fatalf("altered %s head error=%v", tc.name, err)
			}
			if err := session.reload(session.root); err != nil {
				t.Fatalf("reload after %s mutation: %v", tc.name, err)
			}
			if _, err := session.Head(OrdinaryGas); err != nil {
				t.Fatalf("restored %s head: %v", tc.name, err)
			}
		})
	}
}
