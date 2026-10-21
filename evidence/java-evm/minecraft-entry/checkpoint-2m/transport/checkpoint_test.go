package transport

import (
	"testing"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
)

func TestProfilesKeepLegacyOneMiBDefaultAndExplicitTwoMiB(t *testing.T) {
	legacyLimit, err := (CheckpointProfile(0)).MaxBytes()
	if err != nil || legacyLimit != 1048576 {
		t.Fatalf("zero/legacy profile limit=%d err=%v", legacyLimit, err)
	}
	newLimit, err := MinecraftCheckpoint2MiB.MaxBytes()
	if err != nil || newLimit != 2097152 {
		t.Fatalf("checkpoint-2m profile limit=%d err=%v", newLimit, err)
	}

	legacy := make([]byte, legacyLimit)
	if err := ValidateOpaque(Legacy1MiB, legacy, crypto.Keccak256Hash(legacy)); err != nil {
		t.Fatalf("legacy exact boundary rejected: %v", err)
	}
	legacyPlusOne := make([]byte, legacyLimit+1)
	if err := ValidateSize(Legacy1MiB, legacyPlusOne); err == nil {
		t.Fatal("legacy 1 MiB default accepted 1 MiB+1")
	}
	if err := ValidateOpaque(MinecraftCheckpoint2MiB, legacyPlusOne,
		crypto.Keccak256Hash(legacyPlusOne)); err != nil {
		t.Fatalf("explicit 2 MiB profile rejected 1 MiB+1 opaque bytes: %v", err)
	}

	newLimitBytes := make([]byte, newLimit)
	if err := ValidateOpaque(MinecraftCheckpoint2MiB, newLimitBytes,
		crypto.Keccak256Hash(newLimitBytes)); err != nil {
		t.Fatalf("2 MiB exact boundary rejected: %v", err)
	}
	newLimitPlusOne := make([]byte, newLimit+1)
	if err := ValidateSize(MinecraftCheckpoint2MiB, newLimitPlusOne); err == nil {
		t.Fatal("2 MiB profile accepted the 2 MiB+1 negative-validator size")
	}
	if err := ValidateOpaque(MinecraftCheckpoint2MiB, newLimitBytes, common.Hash{}); err == nil {
		t.Fatal("zero root accepted")
	}
	if _, err := CheckpointProfile(99).MaxBytes(); err == nil {
		t.Fatal("unknown profile accepted")
	}
}
