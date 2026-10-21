// Package transport supplies profile-aware bounds for opaque EVM-issued MR01
// checkpoint bytes. It never parses or authorizes guest state.
package transport

import (
	"errors"
	"fmt"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
)

const (
	legacyCheckpointBytes = uint32(1 << 20)
	checkpoint2MBytes     = uint32(2 << 20)
)

// CheckpointProfile is an application-level transport bound. The zero value is
// deliberately the legacy 1 MiB profile; 2 MiB must be selected explicitly.
type CheckpointProfile uint8

const (
	Legacy1MiB CheckpointProfile = iota
	MinecraftCheckpoint2MiB
)

func (p CheckpointProfile) MaxBytes() (uint32, error) {
	switch p {
	case Legacy1MiB:
		return legacyCheckpointBytes, nil
	case MinecraftCheckpoint2MiB:
		return checkpoint2MBytes, nil
	default:
		return 0, fmt.Errorf("checkpoint transport: unknown profile %d", p)
	}
}

// ValidateSize applies only the selected opaque transport size bound. It does
// not inspect a header or infer provenance from bytes.
func ValidateSize(p CheckpointProfile, checkpoint []byte) error {
	limit, err := p.MaxBytes()
	if err != nil {
		return err
	}
	if len(checkpoint) == 0 || uint64(len(checkpoint)) > uint64(limit) {
		return fmt.Errorf("checkpoint transport: %d bytes outside 1..%d", len(checkpoint), limit)
	}
	return nil
}

// ValidateOpaque checks the selected size bound and exact EVM-committed Keccak
// root, while retaining checkpoint bytes as opaque data.
func ValidateOpaque(p CheckpointProfile, checkpoint []byte, root common.Hash) error {
	if err := ValidateSize(p, checkpoint); err != nil {
		return err
	}
	if root == (common.Hash{}) || crypto.Keccak256Hash(checkpoint) != root {
		return errors.New("checkpoint transport: opaque bytes do not match nonzero EVM root")
	}
	return nil
}
