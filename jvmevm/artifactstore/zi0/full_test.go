package zi0

import (
	"bytes"
	"encoding/json"
	"fmt"
	"math/big"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"syscall"
	"testing"
	"time"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/as0"
)

func zi0HarnessNamesN(count, targetNameBytes int) []zi0HarnessEnt {
	entries := make([]zi0HarnessEnt, count)
	remaining := targetNameBytes
	for i := range entries {
		left := count - i
		length := remaining / left
		if length < 8 {
			length = 8
		}
		base := fmt.Sprintf("p/%05d/", i)
		if len(base) > length {
			length = len(base)
		}
		name := base + strings.Repeat(string(rune('a'+i%26)), length-len(base))
		entries[i] = zi0HarnessEnt{name: []byte(name), data: []byte{byte(i), byte(i >> 8)}, method: 8, descriptor: -1}
		remaining -= len(name)
	}
	if remaining != 0 {
		panic(fmt.Sprintf("name sizing remainder %d", remaining))
	}
	return entries
}
func zi0HarnessDiskUsage(root string) (int64, int) {
	var total int64
	var files int
	_ = filepath.Walk(root, func(_ string, info os.FileInfo, err error) error {
		if err == nil && !info.IsDir() {
			total += info.Size()
			files++
		}
		return nil
	})
	return total, files
}
func zi0HarnessRSSKiB() int64 {
	var usage syscall.Rusage
	if syscall.Getrusage(syscall.RUSAGE_SELF, &usage) == nil {
		return usage.Maxrss
	}
	return 0
}
func zi0HarnessLogGas(t testing.TB, name string, z zi0HarnessZIP, gas zi0HarnessGas, root common.Hash, directory string, started time.Time) {
	t.Helper()
	diskBytes, diskFiles := int64(0), 0
	if directory != "" {
		diskBytes, diskFiles = zi0HarnessDiskUsage(directory)
	}
	report := map[string]interface{}{
		"name": name, "entries": len(z.entries), "bytes": len(z.raw), "cdBytes": z.eocd - z.cd,
		"as0CreateGas": gas.createAS0, "appendCalls": gas.appends, "appendGasSum": gas.appendSum, "appendGasMax": gas.appendMax,
		"sealGas": gas.seal, "indexCreateGas": gas.createIndex, "discoverGas": gas.discover,
		"scanCalls": gas.scans, "scanGasSum": gas.scanSum, "scanGasMax": gas.scanMax, "finishGas": gas.finish,
		"viewGasSum": gas.views, "publications": gas.publications, "stateRoot": root,
		"diskBytes": diskBytes, "diskFiles": diskFiles, "rssKiB": zi0HarnessRSSKiB(), "elapsedMS": time.Since(started).Milliseconds(),
	}
	raw, _ := json.Marshal(report)
	t.Log(string(raw))
}

func TestZI0HarnessFull20554ExactCDDurableEveryCall(t *testing.T) {
	started := time.Now()
	const count = 20554
	z := zi0HarnessBuildZIP(zi0HarnessNamesN(count, 1155312), 0, nil, nil)
	if got := z.eocd - z.cd; got != 2100796 || len(z.raw) != 4057736 {
		t.Fatalf("target fixture entries=%d bytes=%d CD=%d", len(z.entries), len(z.raw), got)
	}
	owner := common.HexToAddress("0x5a4930720001")
	directory := t.TempDir()
	session, err := Open(directory, owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatal(err)
	}
	creation, _ := session.Creation()
	if !creation.Performed || creation.Controller != crypto.CreateAddress(owner, 0) {
		t.Fatalf("fresh disk creation=%+v", creation)
	}
	gas := zi0HarnessGas{createAS0: creation.GasUsed, publications: 1}
	mid := (len(z.raw) / int(as0.PageSize) / 2) * int(as0.PageSize)
	zi0HarnessUpload(t, session, z.raw, 0, mid, &gas)
	if err := session.Close(); err != nil {
		t.Fatal(err)
	}
	session, err = Open(directory, owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatal(err)
	}
	creation, _ = session.Creation()
	midHead, err := session.Head(OrdinaryGas)
	if err != nil || creation.Performed || midHead.AS0.Cursor != uint32(mid) || midHead.AS0.Sealed || session.state.GetNonce(owner) != 1 {
		t.Fatalf("mid-upload reopen creation=%+v head=%+v err=%v", creation, midHead, err)
	}
	gas.views += midHead.GasUsed
	zi0HarnessUpload(t, session, z.raw, mid, len(z.raw), &gas)
	full, err := session.Head(OrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	gas.views += full.GasUsed
	sealed, err := session.Seal(full.AS0.Cursor, full.AS0.ChainCommitment, OrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	gas.seal, gas.publications = sealed.GasUsed, gas.publications+1
	if published, err := readManifest(filepath.Join(directory, manifestName)); err != nil || published.StateRoot != sealed.StateRoot {
		t.Fatalf("seal was not individually published: manifest=%+v err=%v", published, err)
	}
	if err := session.Close(); err != nil {
		t.Fatal(err)
	}

	session, err = Open(directory, owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatal(err)
	}
	sealedHead, err := session.Head(OrdinaryGas)
	if err != nil || !sealedHead.AS0.Sealed || sealedHead.Index.Address != (common.Address{}) {
		t.Fatalf("sealed-AS0 reopen=%+v err=%v", sealedHead, err)
	}
	gas.views += sealedHead.GasUsed
	created, err := session.CreateIndex(sealedHead.AS0.ContentCommitment, OrdinaryGas)
	if err != nil || created.CreatedAddress != crypto.CreateAddress(owner, 1) {
		t.Fatalf("index create=%+v err=%v", created, err)
	}
	gas.createIndex, gas.publications = created.GasUsed, gas.publications+1
	if published, err := readManifest(filepath.Join(directory, manifestName)); err != nil || published.StateRoot != created.StateRoot || published.Index != created.CreatedAddress {
		t.Fatalf("index CREATE was not individually published: manifest=%+v err=%v", published, err)
	}
	if err := session.Close(); err != nil {
		t.Fatal(err)
	}

	session, err = Open(directory, owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatal(err)
	}
	bound, err := session.Head(OrdinaryGas)
	if err != nil || bound.Index.Phase != 0 {
		t.Fatalf("BOUND reopen=%+v err=%v", bound, err)
	}
	gas.views += bound.GasUsed
	discovered, err := session.Discover(OrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	gas.discover, gas.publications = discovered.GasUsed, gas.publications+1
	if published, err := readManifest(filepath.Join(directory, manifestName)); err != nil || published.StateRoot != discovered.StateRoot {
		t.Fatalf("discover was not individually published: manifest=%+v err=%v", published, err)
	}
	for {
		head, err := session.Head(OrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
		gas.views += head.GasUsed
		if head.Index.NextEntry >= uint32(count/2) {
			break
		}
		op, err := session.Scan(head.Index.NextEntry, head.Index.CDCursor, head.Index.Rolling, 64, BoundaryGas)
		if err != nil {
			t.Fatalf("first-half scan %d: %v", head.Index.NextEntry, err)
		}
		gas.scanSum += op.GasUsed
		gas.scans++
		gas.publications++
		if op.GasUsed > gas.scanMax {
			gas.scanMax = op.GasUsed
		}
		published, err := readManifest(filepath.Join(directory, manifestName))
		if err != nil || published.StateRoot != op.StateRoot {
			t.Fatal("scan was not published before success")
		}
	}
	if err := session.Close(); err != nil {
		t.Fatal(err)
	}

	session, err = Open(directory, owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatal(err)
	}
	staged, err := session.Head(OrdinaryGas)
	if err != nil || staged.Index.Phase != 1 || staged.Index.NextEntry < uint32(count/2) || staged.Index.NextEntry >= uint32(count) {
		t.Fatalf("STAGING reopen=%+v err=%v", staged, err)
	}
	gas.views += staged.GasUsed
	for staged.Index.NextEntry < staged.Index.Count {
		op, err := session.Scan(staged.Index.NextEntry, staged.Index.CDCursor, staged.Index.Rolling, 64, BoundaryGas)
		if err != nil {
			t.Fatalf("second-half scan %d: %v", staged.Index.NextEntry, err)
		}
		gas.scanSum += op.GasUsed
		gas.scans++
		gas.publications++
		if op.GasUsed > gas.scanMax {
			gas.scanMax = op.GasUsed
		}
		if published, publishErr := readManifest(filepath.Join(directory, manifestName)); publishErr != nil || published.StateRoot != op.StateRoot {
			t.Fatalf("second-half scan was not individually published: manifest=%+v err=%v", published, publishErr)
		}
		staged, err = session.Head(OrdinaryGas)
		if err != nil {
			t.Fatal(err)
		}
		gas.views += staged.GasUsed
	}
	finished, err := session.Finish(staged.Index.Count, staged.Index.CDCursor, staged.Index.Rolling, OrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	gas.finish, gas.publications = finished.GasUsed, gas.publications+1
	if published, err := readManifest(filepath.Join(directory, manifestName)); err != nil || published.StateRoot != finished.StateRoot {
		t.Fatalf("finish was not individually published: manifest=%+v err=%v", published, err)
	}
	if gas.appends != 496 || gas.scans != 322 || gas.publications != 823 {
		t.Fatalf("per-call publication chain appends=%d scans=%d publications=%d", gas.appends, gas.scans, gas.publications)
	}
	if err := session.Close(); err != nil {
		t.Fatal(err)
	}

	session, err = Open(directory, owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	final, err := session.Head(OrdinaryGas)
	if err != nil || final.Index.Phase != 2 || final.Index.Count != count || final.Index.CDSize != 2100796 || final.StateRoot != finished.StateRoot {
		t.Fatalf("FINAL reopen=%+v err=%v", final, err)
	}
	gas.views += final.GasUsed
	for _, index := range []int{0, count / 2, count - 1} {
		lookup, err := session.Lookup(z.entries[index].name, OrdinaryGas)
		if err != nil || !lookup.Found || lookup.Index != uint32(index) {
			t.Fatalf("target lookup %d=%+v err=%v", index, lookup, err)
		}
		gas.views += lookup.GasUsed
	}
	zi0HarnessLogGas(t, "target-20554-exact2100796-durable", z, gas, final.StateRoot, directory, started)
}

func TestZI0HarnessCapacity32768Exact4MiBCDAndPlusOne(t *testing.T) {
	started := time.Now()
	const count = 32768
	targetNameBytes := int(MaxCD) - count*46
	z := zi0HarnessBuildZIP(zi0HarnessNamesN(count, targetNameBytes), 0, nil, nil)
	if z.eocd-z.cd != MaxCD {
		t.Fatalf("capacity CD=%d want=%d", z.eocd-z.cd, MaxCD)
	}
	session, gas := zi0HarnessOpenAndUpload(t, common.HexToAddress("0x5a4930720002"), z, "")
	zi0HarnessSealCreate(t, session, &gas)
	final := zi0HarnessIndex(t, session, 64, &gas)
	if final.Index.Count != MaxEntries || final.Index.CDSize != MaxCD || gas.scans != 512 {
		t.Fatalf("capacity final=%+v scans=%d", final, gas.scans)
	}
	session.Close()
	zi0HarnessLogGas(t, "capacity-32768-exact4MiB-CD", z, gas, final.StateRoot, "", started)

	plus := zi0HarnessBuildZIP(zi0HarnessNamesN(count, targetNameBytes+1), 0, nil, nil)
	if plus.eocd-plus.cd != MaxCD+1 {
		t.Fatal("bad +1 CD fixture")
	}
	zi0HarnessWantDiscoverError(t, plus, 7)
}

func TestZI0HarnessExact32MiBHighOffsets(t *testing.T) {
	started := time.Now()
	entry := zi0HarnessEnt{name: []byte("transport/high-offset.bin"), data: []byte("opaque high payload"), method: 0, descriptor: -1}
	base := zi0HarnessBuildZIP([]zi0HarnessEnt{entry}, 0, nil, nil)
	z := zi0HarnessBuildZIP([]zi0HarnessEnt{entry}, int(as0.MaxLength)-len(base.raw), nil, nil)
	if len(z.raw) != int(as0.MaxLength) {
		t.Fatalf("high-offset fixture=%d", len(z.raw))
	}
	session, gas := zi0HarnessOpenAndUpload(t, common.HexToAddress("0x5a4930720003"), z, "")
	defer session.Close()
	zi0HarnessSealCreate(t, session, &gas)
	final := zi0HarnessIndex(t, session, 64, &gas)
	entryResult, err := session.Entry(0, OrdinaryGas)
	if err != nil || !bytes.Equal(entryResult.Name, entry.name) {
		t.Fatalf("high entry=%+v err=%v", entryResult, err)
	}
	packed := new(big.Int).SetBytes(entryResult.PackedRecord[:])
	mask := new(big.Int).SetUint64((1 << 25) - 1)
	for _, field := range []struct {
		shift uint
		want  uint32
	}{{0, z.cd + 46}, {25, z.locals[0]}, {50, z.dataAt[0]}} {
		got := new(big.Int).And(new(big.Int).Rsh(new(big.Int).Set(packed), field.shift), mask).Uint64()
		if got != uint64(field.want) || got < 1<<24 {
			t.Fatalf("high packed field shift=%d got=%d want=%d", field.shift, got, field.want)
		}
	}
	lookup, err := session.Lookup(entry.name, OrdinaryGas)
	if err != nil || !lookup.Found || lookup.PackedRecord != entryResult.PackedRecord {
		t.Fatalf("high lookup=%+v err=%v", lookup, err)
	}
	gas.views += entryResult.GasUsed + lookup.GasUsed
	zi0HarnessLogGas(t, "exact32MiB-high-offsets", z, gas, final.StateRoot, "", started)
}

func zi0HarnessMultiphaseZIP() zi0HarnessZIP {
	entries := make([]zi0HarnessEnt, 65)
	for i := range entries {
		entries[i] = zi0HarnessEnt{name: []byte(fmt.Sprintf("phase/%02d", i)), data: []byte{byte(i)}, method: uint16((i % 2) * 8), descriptor: -1}
	}
	return zi0HarnessBuildZIP(entries, 9000, nil, nil)
}

func TestZI0HarnessNewProcessAllPhasesAndRelocatedBinary(t *testing.T) {
	if stage := os.Getenv("JVMEVM_ZI0_PHASE_CHILD"); stage != "" {
		zi0HarnessPhaseChild(t, stage)
		return
	}
	z := zi0HarnessMultiphaseZIP()
	owner := common.HexToAddress("0x5a4930720004")
	directory := t.TempDir()
	session, err := Open(directory, owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatal(err)
	}
	var gas zi0HarnessGas
	zi0HarnessUpload(t, session, z.raw, 0, int(as0.PageSize), &gas)
	if err := session.Close(); err != nil {
		t.Fatal(err)
	}

	executable, err := os.Executable()
	if err != nil {
		t.Fatal(err)
	}
	relocated := filepath.Join(t.TempDir(), "zi0-relocated.test")
	rawExecutable, err := os.ReadFile(executable)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(relocated, rawExecutable, 0700); err != nil {
		t.Fatal(err)
	}
	for _, stage := range []string{"sealed", "bound", "staging", "final"} {
		binary := executable
		if stage == "bound" {
			binary = relocated
		}
		cmd := exec.Command(binary, "-test.run=^TestZI0HarnessNewProcessAllPhasesAndRelocatedBinary$", "-test.count=1", "-test.v")
		cmd.Env = append(os.Environ(), "JVMEVM_ZI0_PHASE_CHILD="+stage, "JVMEVM_ZI0_PHASE_DIR="+directory)
		output, err := cmd.CombinedOutput()
		if err != nil {
			t.Fatalf("fresh-process %s: %v\n%s", stage, err, output)
		}
		t.Logf("fresh-process stage=%s binary=%s output=%q", stage, filepath.Base(binary), strings.TrimSpace(string(output)))
	}
	final, err := Open(directory, owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatal(err)
	}
	defer final.Close()
	creation, _ := final.Creation()
	head, err := final.Head(OrdinaryGas)
	if err != nil || creation.Performed || head.Index.Phase != 2 || head.Index.Count != 65 || head.Index.FinalRoot == (common.Hash{}) {
		t.Fatalf("final new-process reopen creation=%+v head=%+v err=%v", creation, head, err)
	}
	if runtime.GOOS == "linux" && !bytes.Equal(final.zi0Runtime, mustRuntime(t)) {
		t.Fatal("relocated executable did not retain embedded production runtime")
	}
}

func mustRuntime(t testing.TB) []byte {
	t.Helper()
	raw, err := Runtime()
	if err != nil {
		t.Fatal(err)
	}
	return raw
}

func zi0HarnessPhaseChild(t *testing.T, stage string) {
	z := zi0HarnessMultiphaseZIP()
	owner := common.HexToAddress("0x5a4930720004")
	directory := os.Getenv("JVMEVM_ZI0_PHASE_DIR")
	session, err := Open(directory, owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	creation, _ := session.Creation()
	if creation.Performed {
		t.Fatal("reopen performed CREATE")
	}
	switch stage {
	case "sealed":
		head, err := session.Head(OrdinaryGas)
		if err != nil || head.AS0.Cursor != as0.PageSize || head.AS0.Sealed {
			t.Fatalf("mid-upload=%+v err=%v", head, err)
		}
		var gas zi0HarnessGas
		zi0HarnessUpload(t, session, z.raw, int(as0.PageSize), len(z.raw), &gas)
		head, _ = session.Head(OrdinaryGas)
		if _, err := session.Seal(head.AS0.Cursor, head.AS0.ChainCommitment, OrdinaryGas); err != nil {
			t.Fatal(err)
		}
	case "bound":
		head, err := session.Head(OrdinaryGas)
		if err != nil || !head.AS0.Sealed || head.Index.Address != (common.Address{}) {
			t.Fatalf("sealed-AS0=%+v err=%v", head, err)
		}
		if _, err := session.CreateIndex(head.AS0.ContentCommitment, OrdinaryGas); err != nil {
			t.Fatal(err)
		}
	case "staging":
		head, err := session.Head(OrdinaryGas)
		if err != nil || head.Index.Phase != 0 {
			t.Fatalf("BOUND=%+v err=%v", head, err)
		}
		if _, err := session.Discover(OrdinaryGas); err != nil {
			t.Fatal(err)
		}
		head, _ = session.Head(OrdinaryGas)
		if _, err := session.Scan(head.Index.NextEntry, head.Index.CDCursor, head.Index.Rolling, 1, OrdinaryGas); err != nil {
			t.Fatal(err)
		}
	case "final":
		head, err := session.Head(OrdinaryGas)
		if err != nil || head.Index.Phase != 1 || head.Index.NextEntry != 1 {
			t.Fatalf("STAGING=%+v err=%v", head, err)
		}
		for head.Index.NextEntry < head.Index.Count {
			if _, err := session.Scan(head.Index.NextEntry, head.Index.CDCursor, head.Index.Rolling, 64, BoundaryGas); err != nil {
				t.Fatal(err)
			}
			head, err = session.Head(OrdinaryGas)
			if err != nil {
				t.Fatal(err)
			}
		}
		if _, err := session.Finish(head.Index.Count, head.Index.CDCursor, head.Index.Rolling, OrdinaryGas); err != nil {
			t.Fatal(err)
		}
	default:
		t.Fatalf("unknown child stage %q", stage)
	}
}
