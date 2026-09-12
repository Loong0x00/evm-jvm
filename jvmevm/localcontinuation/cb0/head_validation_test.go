package cb0

import (
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/tracing"
)

func cb0HeadRepairOwner() common.Address {
	return common.HexToAddress("0xCB00000000000000000000000000000000000002")
}

func TestCB0HeadValidationInitialWorld(t *testing.T) {
	s, err := NewMemory(cb0HeadRepairOwner(), 1)
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()
	head, err := s.Head(OrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	if head.AS0.Owner != cb0HeadRepairOwner() || head.AS0.Sealed || head.Index.Address != (common.Address{}) { // retain an explicit EVM head call before shape probes.
		t.Fatalf("unexpected initialized head: %#v", head)
	}
	if len(head.Decoders) != 0 || head.Coordinator.Address != (common.Address{}) || head.Java.Epoch != 0 {
		t.Fatalf("unexpected active routes in initialized head: %#v", head)
	}
}

// TestCB0HeadValidationBoundaryGas is explicitly the 1B LOCAL boundary check;
// ordinary head tests use the frozen 100M ordinary-call allowance.
func TestCB0HeadValidationBoundaryGas(t *testing.T) {
	s, err := NewMemory(cb0HeadRepairOwner(), 1)
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()
	if _, err := s.Head(BoundaryGas); err != nil {
		t.Fatal(err)
	}
}

func TestCB0HeadValidationRejectsCopiedStateShape(t *testing.T) {
	for _, tc := range []struct {
		name   string
		mutate func(*Session)
	}{
		{
			name: "AS0 controller code pin",
			mutate: func(s *Session) {
				// This is deliberately a copied-state shape probe, not a mutation
				// through any CB0 ownership API or a claim that live ownership can
				// be bypassed.
				s.state = s.state.Copy()
				s.state.SetCode(s.as0Address, []byte{0x00}, tracing.CodeChangeUnspecified)
			},
		},
		{
			name: "ordinary creator nonce",
			mutate: func(s *Session) {
				s.state = s.state.Copy()
				s.state.SetNonce(s.owner, 7, tracing.NonceChangeUnspecified)
			},
		},
		{
			name: "fixed engine code pin",
			mutate: func(s *Session) {
				s.state = s.state.Copy()
				s.state.SetCode(cb0EngineAddress, []byte{0x00}, tracing.CodeChangeUnspecified)
			},
		},
	} {
		t.Run(tc.name, func(t *testing.T) {
			s, err := NewMemory(cb0HeadRepairOwner(), 1)
			if err != nil {
				t.Fatal(err)
			}
			defer s.Close()
			tc.mutate(s)
			_, err = s.Head(OrdinaryGas)
			if err == nil || !strings.Contains(err.Error(), "cb0:") {
				t.Fatalf("invalid copied shape accepted: %v", err)
			}
		})
	}
}
