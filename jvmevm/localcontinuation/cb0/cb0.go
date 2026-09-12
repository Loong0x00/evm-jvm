// Copyright 2026 The go-ethereum Authors
// SPDX-License-Identifier: LGPL-3.0-or-later

// Package cb0 transports one bounded, opaque EVM-owned class package into the
// frozen LOCAL VFS0a interpreter. Go never parses ZIP or class bytes: AS0, ZI0,
// DI0 and CB0ClassCoordinator are the resource and class identity authorities.
package cb0

import (
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/as0"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/di0"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/zi0"
	"github.com/ethereum/go-ethereum/jvmevm/localcontinuation/vfs0a"
)

const (
	StoreMarker        = "JVMEVM-MC-CB0-LOCAL-STORE-1\n"
	StoreFormat uint32 = 1

	MaxResources       = uint8(4)
	MaxClassBytes      = uint32(65536)
	MaxRawNameBytes    = uint32(256)
	MaxResourceRead    = uint32(4096)
	MaxCheckpointBytes = uint32(1 << 20)
	MaxGas             = uint64(1_000_000_000)
	OrdinaryGas        = uint64(100_000_000)
	BoundaryGas        = uint64(1_000_000_000)
)

// ResourceBinding is a caller assertion for one ordered DI0 resource. The EVM
// coordinator revalidates every field, including the package root; this value
// must never be populated from host ZIP or class metadata.
type ResourceBinding struct {
	Slot         uint8
	RawName      []byte
	IndexRoot    common.Hash
	ResourceRoot common.Hash
}

// Initialization describes the one atomically-published fresh root. The engine
// installation is an explicit LOCAL initial-state operation (zero gas), while
// AS0Creation records the sole ordinary CREATE included in that same root.
type Initialization struct {
	EngineInstalled bool
	EngineAddress   common.Address
	EngineCodeHash  common.Hash
	StateRoot       common.Hash
	AS0Creation     as0.Creation
}

// JavaResult is the successful outer coordinator result. Checkpoint is opaque
// and is retained only after its EVM hash and lifecycle invariants are checked.
// EVM failures return only GasUsed and RevertData; publication failures return
// only GasUsed.
type JavaResult struct {
	Slice      vfs0a.SliceResult
	Checkpoint []byte
	StateRoot  common.Hash
	GasUsed    uint64
	RevertData []byte
}

// CoordinatorClass is the EVM-returned binding metadata for one resource.
type CoordinatorClass struct {
	Decoder      common.Address
	RawName      []byte
	ResourceRoot common.Hash
	ClassSize    uint32
}

// CoordinatorHead contains the fixed coordinator identity, seven scalar
// getters, and ordered EVM-returned class bindings. No host-derived class
// catalogue is retained here.
type CoordinatorHead struct {
	Address         common.Address
	RuntimeCodeHash common.Hash
	Owner           common.Address
	FinalIndex      common.Address
	FinalIndexRoot  common.Hash
	PackageRoot     common.Hash
	InstanceID      common.Hash
	TotalClassBytes uint32
	ClassCount      uint8
	Classes         []CoordinatorClass
	GasUsed         uint64
}

// Head is a copied-state EVM view of the complete shared world.
type Head struct {
	StateRoot   common.Hash
	GasUsed     uint64
	AS0         as0.Head
	Index       zi0.IndexHead
	Decoders    []di0.DI0Head
	Coordinator CoordinatorHead
	Java        vfs0a.Head
}

// Operation is the CB0 mutation receipt. It deliberately matches DI0's public
// receipt behavior: EVM errors expose gas and revert bytes; durability errors
// expose gas only.
type Operation = di0.Operation

// Read, Page, Entry and Lookup retain the accepted opaque view types.
type Read = di0.Read
type Page = di0.Page
type Entry = di0.Entry
type Lookup = di0.LookupResult

// copiedLogs creates a defensive result without exposing StateDB-owned logs.
func copiedLogs(in []*types.Log) []*types.Log {
	out := make([]*types.Log, len(in))
	for i, log := range in {
		if log == nil {
			continue
		}
		copyLog := *log
		copyLog.Topics = append([]common.Hash(nil), log.Topics...)
		copyLog.Data = append([]byte(nil), log.Data...)
		out[i] = &copyLog
	}
	return out
}
