package vfs0a

import (
	"bytes"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strconv"
	"testing"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
)

func TestVFS0aHarnessSliceResultCounterValidation(t *testing.T) {
	valid := SliceResult{
		Schema: 1, Lifecycle: 2, Epoch: 1,
		CheckpointRoot: common.HexToHash("0x01"), MachineStateRoot: common.HexToHash("0x02"), VFSStateRoot: common.HexToHash("0x03"),
		TotalJvmSteps: 7, TotalInternalSteps: 5, ExecutedJvmSteps: 7, ExecutedInternalSteps: 5,
		Result: 1, InodeCount: 3,
	}
	if err := vfs0aHarnessValidateSliceResult(valid, 7, 5); err != nil {
		t.Fatal(err)
	}
	for name, mutate := range map[string]func(*SliceResult){
		"zero epoch":           func(r *SliceResult) { r.Epoch = 0 },
		"zero checkpoint":      func(r *SliceResult) { r.CheckpointRoot = common.Hash{} },
		"zero machine":         func(r *SliceResult) { r.MachineStateRoot = common.Hash{} },
		"JVM call budget":      func(r *SliceResult) { r.ExecutedJvmSteps = 8 },
		"internal call budget": func(r *SliceResult) { r.ExecutedInternalSteps = 6 },
		"JVM cumulative":       func(r *SliceResult) { r.TotalJvmSteps = 6 },
		"internal cumulative":  func(r *SliceResult) { r.TotalInternalSteps = 4 },
	} {
		t.Run(name, func(t *testing.T) {
			bad := valid
			mutate(&bad)
			if err := vfs0aHarnessValidateSliceResult(bad, 7, 5); err == nil {
				t.Fatalf("invalid result accepted: %+v", bad)
			}
		})
	}
}

func TestVFS0aHarnessSeedConfigAndCopiedInspectProvenance(t *testing.T) {
	vfs0aHarnessRequireRuntime(t)
	fixture := vfs0aHarnessFixtures(t)[10] // createRoundtrip
	ownerA := common.HexToAddress("0x50000000000000000000000000000000000000e0")
	sessionA, err := NewMemory(ownerA)
	if err != nil {
		t.Fatal(err)
	}
	defer sessionA.Close()
	result := vfs0aHarnessRunChain(t, sessionA, fixture, "inspect-source", 4096, 4096)
	view := vfs0aHarnessReadCheckpointView(t, result.Checkpoint)

	// Independently reconstruct only the frozen seed commitment. This is test
	// evidence; production transports SeedFile values without interpreting them.
	seedType := sessionA.contractABI.Methods["start"].Inputs[5].Type
	bytes32Type, err := abi.NewType("bytes32", "", nil)
	if err != nil {
		t.Fatal(err)
	}
	encoded, err := (abi.Arguments{{Type: bytes32Type}, {Type: seedType}}).Pack(
		crypto.Keccak256Hash([]byte("JVMEVM:MC:VFS0A:SEED:1")), fixture.Seeds,
	)
	if err != nil {
		t.Fatal(err)
	}
	if want := crypto.Keccak256Hash(encoded); view.Seed != want {
		t.Fatalf("seed root=%s want=%s", view.Seed, want)
	}
	if view.Config == (common.Hash{}) || view.Artifact == (common.Hash{}) {
		t.Fatal("zero config/artifact commitment")
	}

	// An unrelated copied-state EVM may validate and inspect checkpoint bytes,
	// but that view must not create a head or grant resume provenance.
	sessionB, err := NewMemory(common.HexToAddress("0x51000000000000000000000000000000000000e0"))
	if err != nil {
		t.Fatal(err)
	}
	defer sessionB.Close()
	instance := crypto.Keccak256Hash([]byte(t.Name() + ":inspect-source:" + fixture.ID))
	before, err := sessionB.Head(instance)
	if err != nil || !reflect.DeepEqual(before, Head{}) {
		t.Fatalf("unexpected copied-state head before inspect: %+v %v", before, err)
	}
	inspection, err := sessionB.InspectFile(fixture.Raw, result.Checkpoint, []byte("created"), 0, 3)
	if err != nil || !bytes.Equal(inspection.Data, []byte{65, 67, 68}) {
		t.Fatalf("copied-state EVM inspection=%+v error=%v", inspection, err)
	}
	after, err := sessionB.Head(instance)
	if err != nil || after != before {
		t.Fatalf("inspect published copied-state head: before=%+v after=%+v err=%v", before, after, err)
	}
	failed, err := sessionB.Resume(instance, result.Slice.Epoch, result.Slice.CheckpointRoot, fixture.Raw, result.Checkpoint, 1, 1, vfs0aHarnessOrdinaryGas)
	if err == nil || failed.GasUsed == 0 || !reflect.DeepEqual(failed.Slice, SliceResult{}) || len(failed.Checkpoint) != 0 || len(failed.Logs) != 0 {
		t.Fatalf("copied inspection granted resume provenance: result=%+v error=%v", failed, err)
	}
}

func TestVFS0aHarnessRuntimeHasNoSourceTreeFallback(t *testing.T) {
	if os.Getenv("JVMEVM_VFS0A_EMBED_CHILD") != "" {
		wantHash := os.Getenv("JVMEVM_VFS0A_EMBED_HASH")
		wantSize, err := strconv.Atoi(os.Getenv("JVMEVM_VFS0A_EMBED_SIZE"))
		if err != nil {
			t.Fatal(err)
		}
		code, err := Runtime()
		if err != nil {
			t.Fatal(err)
		}
		hash, err := RuntimeHash()
		if err != nil || hash != wantHash || len(code) != wantSize {
			t.Fatalf("embedded runtime changed outside source tree: size=%d hash=%s error=%v", len(code), hash, err)
		}
		return
	}
	code, err := Runtime()
	if err != nil {
		t.Fatal(err)
	}
	hash, err := RuntimeHash()
	if err != nil {
		t.Fatal(err)
	}
	empty := t.TempDir()
	cmd := exec.Command(os.Args[0], "-test.run=^TestVFS0aHarnessRuntimeHasNoSourceTreeFallback$")
	cmd.Dir = empty
	cmd.Env = append(os.Environ(), "JVMEVM_VFS0A_EMBED_CHILD=1", "JVMEVM_VFS0A_EMBED_HASH="+hash, "JVMEVM_VFS0A_EMBED_SIZE="+strconv.Itoa(len(code)))
	if output, err := cmd.CombinedOutput(); err != nil {
		t.Fatalf("new-process embedded runtime check: %v\n%s", err, output)
	}
}

func TestVFS0aHarnessOldStoresAndCheckpointReadBounds(t *testing.T) {
	vfs0aHarnessRequireRuntime(t)
	owner := common.HexToAddress("0x52000000000000000000000000000000000000e0")

	old := t.TempDir()
	if err := os.WriteFile(filepath.Join(old, vfs0aHarnessStoreMarkerName), []byte("JVMEVM-MC-IOE0-DISK-STORE-1\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(old, vfs0aHarnessManifestName), []byte("{}\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.Mkdir(filepath.Join(old, vfs0aHarnessStateDirectory), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.Mkdir(filepath.Join(old, vfs0aHarnessBlobDirectory), 0o700); err != nil {
		t.Fatal(err)
	}
	if session, err := Open(old, owner); err == nil {
		session.Close()
		t.Fatal("old-profile store was reinterpreted")
	}
	marker, err := os.ReadFile(filepath.Join(old, vfs0aHarnessStoreMarkerName))
	if err != nil || string(marker) != "JVMEVM-MC-IOE0-DISK-STORE-1\n" {
		t.Fatalf("old store was modified: %q %v", marker, err)
	}

	dir := t.TempDir()
	session, err := Open(dir, owner)
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	for _, size := range []int{0, vfs0aHarnessMaxCheckpointSize + 1} {
		blob := bytes.Repeat([]byte{byte(size)}, size)
		root := crypto.Keccak256Hash(blob)
		if err := os.WriteFile(session.vfs0aHarnessBlobPath(root), blob, 0o600); err != nil {
			t.Fatal(err)
		}
		if got, err := session.ReadCheckpoint(root); err == nil || got != nil {
			t.Fatalf("checkpoint size %d accepted: bytes=%d error=%v", size, len(got), err)
		}
	}
	wrongBytes := []byte("not-the-requested-root")
	wrongRoot := crypto.Keccak256Hash([]byte("different"))
	if err := os.WriteFile(session.vfs0aHarnessBlobPath(wrongRoot), wrongBytes, 0o600); err != nil {
		t.Fatal(err)
	}
	if got, err := session.ReadCheckpoint(wrongRoot); err == nil || got != nil {
		t.Fatalf("root-mismatched checkpoint accepted: %x %v", got, err)
	}
}

func TestVFS0aHarnessDurabilityFailureReturnsDiagnosticGasOnly(t *testing.T) {
	vfs0aHarnessRequireRuntime(t)
	fixture := vfs0aHarnessFixtures(t)[0]
	session, err := Open(t.TempDir(), common.HexToAddress("0x53000000000000000000000000000000000000e0"))
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	instance := crypto.Keccak256Hash([]byte(t.Name()))
	session.testFault = func(point vfs0aHarnessFaultPoint) error {
		if point == vfs0aHarnessFaultAfterBlob {
			return errors.New("durability boundary")
		}
		return nil
	}
	failed, err := session.Start(instance, fixture.Raw, fixture.EntryClass, fixture.Entry, nil, fixture.Seeds, 4096, 4096, vfs0aHarnessOrdinaryGas)
	if err == nil || failed.GasUsed == 0 || len(failed.RevertData) != 0 || !reflect.DeepEqual(failed.Slice, SliceResult{}) || failed.Checkpoint != nil || failed.Logs != nil {
		t.Fatalf("durability failure leaked more than gas: %+v error=%v", failed, err)
	}
	session.testFault = nil
	head, err := session.Head(instance)
	if err != nil || !reflect.DeepEqual(head, Head{}) {
		t.Fatalf("failed start published head: %+v %v", head, err)
	}
}
