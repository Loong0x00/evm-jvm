// Generated main(String[]) preflight driver. Copy this file to a fresh ignored
// build directory as main.go; it uses only public cb0.Session APIs.
package main

import (
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/ethereum/go-ethereum/accounts/abi"
	cb0 "github.com/ethereum/go-ethereum/build/java-diff-mc-capacity-proto-smoke/capacitycb0"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
)

var owner = common.HexToAddress("0x4341504143495459000000000000000000000001")

const ordinaryGas = uint64(100000000)

type output struct {
	Command                 string        `json:"command"`
	PID                     int           `json:"pid"`
	PackageRoot             common.Hash   `json:"packageRoot"`
	StateRoot               common.Hash   `json:"stateRoot"`
	MachineRoot             common.Hash   `json:"machineRoot"`
	VFSRoot                 common.Hash   `json:"vfsRoot"`
	Epoch                   uint64        `json:"epoch"`
	Lifecycle               uint8         `json:"lifecycle"`
	Result                  int32         `json:"result"`
	JavaKind                uint8         `json:"javaKind"`
	JavaClass               string        `json:"javaClass,omitempty"`
	JVM                     uint64        `json:"totalJvmSteps"`
	Internal                uint64        `json:"totalInternalSteps"`
	Gas                     uint64        `json:"gasUsed"`
	CheckpointSHA256        string        `json:"checkpointSHA256"`
	CheckpointRoot          common.Hash   `json:"checkpointRoot"`
	Logs                    int           `json:"nestedEngineLogs"`
	ReopenedEngineInstalled bool          `json:"reopenedEngineInstalled"`
	AS0Root                 common.Hash   `json:"as0ContentRoot"`
	IndexRoot               common.Hash   `json:"indexRoot"`
	DecoderRoots            []common.Hash `json:"decoderRoots"`
}

func must(e error) {
	if e != nil {
		panic(e)
	}
}
func pack(types []string, values ...interface{}) []byte {
	var a abi.Arguments
	for _, name := range types {
		t, e := abi.NewType(name, "", nil)
		must(e)
		a = append(a, abi.Argument{Type: t})
	}
	b, e := a.Pack(values...)
	must(e)
	return b
}
func head(s *cb0.Session) cb0.Head   { h, e := s.Head(ordinaryGas); must(e); return h }
func write(v interface{})            { b, e := json.MarshalIndent(v, "", "  "); must(e); fmt.Println(string(b)) }
func checkpointHash(b []byte) string { x := sha256.Sum256(b); return hex.EncodeToString(x[:]) }

// This consumes an opaque fixture only. It never opens/parses the ZIP or classes.
func prepare(s *cb0.Session, raw []byte, names []string) common.Hash {
	init, e := s.Initialization()
	must(e)
	for off := uint32(0); off < uint32(len(raw)); {
		end := off + 8192
		if end > uint32(len(raw)) {
			end = uint32(len(raw))
		}
		page := raw[off:end]
		pi := crypto.Keccak256Hash(pack([]string{"bytes32", "address", "uint32", "uint32", "bytes32"}, crypto.Keccak256Hash([]byte("MC-AS0/page/v1")), init.AS0Creation.Controller, off/8192, uint32(len(page)), crypto.Keccak256Hash(page)))
		_, e = s.Append(off, page, pi, ordinaryGas)
		must(e)
		off = end
	}
	h := head(s)
	_, e = s.Seal(h.AS0.Cursor, h.AS0.ChainCommitment, ordinaryGas)
	must(e)
	h = head(s)
	_, e = s.CreateIndex(h.AS0.ContentCommitment, ordinaryGas)
	must(e)
	_, e = s.DiscoverIndex(ordinaryGas)
	must(e)
	for h = head(s); h.Index.NextEntry < h.Index.Count; h = head(s) {
		_, e = s.ScanIndex(h.Index.NextEntry, h.Index.CDCursor, h.Index.Rolling, 64, ordinaryGas)
		must(e)
	}
	h = head(s)
	_, e = s.FinishIndex(h.Index.Count, h.Index.CDCursor, h.Index.Rolling, ordinaryGas)
	must(e)
	rawNames := make([][]byte, len(names))
	for i, name := range names {
		rawNames[i] = []byte(name + ".class")
	}
	for slot, name := range rawNames {
		h = head(s)
		if slot == 8 {
			before := h
			op, refusal := s.CreateDecoder(uint8(slot), h.Index.FinalRoot, name, ordinaryGas)
			after := head(s)
			write(map[string]interface{}{"command": "fifth-class-refusal", "attemptedRawName": string(name), "error": fmt.Sprint(refusal), "gasUsed": op.GasUsed, "beforeStateRoot": before.StateRoot, "afterStateRoot": after.StateRoot, "decoderCount": len(after.Decoders), "stateUnchanged": before.StateRoot == after.StateRoot})
			return common.Hash{}
		}
		_, e = s.CreateDecoder(uint8(slot), h.Index.FinalRoot, name, ordinaryGas)
		must(e)
		for h = head(s); h.Decoders[slot].Phase == 1; h = head(s) {
			_, e = s.StepDecoder(uint8(slot), h.Decoders[slot].Work, 128, ordinaryGas)
			must(e)
		}
		for h = head(s); h.Decoders[slot].Phase != 4; h = head(s) {
			_, e = s.PublishDecoder(uint8(slot), h.Decoders[slot].PublishedPages, h.Decoders[slot].PublicationRolling, 1, ordinaryGas)
			must(e)
		}
	}
	// This is assertion construction from EVM Head metadata, using frozen CB0 domains.
	h = head(s)
	addr := crypto.CreateAddress(owner, uint64(2+len(h.Decoders)))
	H := crypto.Keccak256Hash
	roll := H(pack([]string{"bytes32", "address", "address", "address", "bytes32", "bytes32", "bytes32", "uint8"}, H([]byte("MC-CAPACITY-PREFLIGHT/package/v1")), addr, owner, init.EngineAddress, init.EngineCodeHash, common.HexToHash("0x946686a0a4f09ec9a03e3eb63e9bbeac008212061d6f316586034cf800380c37"), common.HexToHash("0x0c22eca78e00865ce03e8e298708bfe51ce9856cff138d1046905fc285ad5a77"), uint8(len(rawNames))))
	refs := make([]cb0.ResourceBinding, 0, len(rawNames))
	var total uint32
	for i, name := range rawNames {
		d := h.Decoders[i]
		refs = append(refs, cb0.ResourceBinding{Slot: uint8(i), RawName: name, IndexRoot: d.IndexRoot, ResourceRoot: d.FinalRoot})
		total += d.PlainSize
		roll = H(pack([]string{"bytes32", "bytes32", "uint8", "address", "bytes32", "bytes32", "bytes32", "uint32"}, H([]byte("MC-CAPACITY-PREFLIGHT/resource/v1")), roll, uint8(i), d.Address, H(name), d.IndexRoot, d.FinalRoot, d.PlainSize))
	}
	pkg := H(pack([]string{"bytes32", "bytes32", "uint32", "address", "bytes32"}, H([]byte("MC-CAPACITY-PREFLIGHT/package/v1")), roll, total, h.Index.Address, h.Index.FinalRoot))
	_, e = s.CreateCoordinator(common.Hash{}, refs, pkg, ordinaryGas)
	must(e)
	return pkg
}

// The two constants above are the accepted DI0/ZI0 runtime Keccak pins from the
// CB0 review. They are package-identity inputs, never ZIP/class authority; CB0
// independently checks the same pins in EVM.

func emit(command string, h cb0.Head, r cb0.JavaResult, reopenedInstalled bool) {
	cp, e := safelyCheckpoint(r)
	must(e)
	o := output{command, os.Getpid(), h.Coordinator.PackageRoot, r.StateRoot, r.Slice.MachineStateRoot, r.Slice.VFSStateRoot, r.Slice.Epoch, r.Slice.Lifecycle, r.Slice.Result, r.Slice.JavaKind, string(r.Slice.JavaClass), r.Slice.TotalJvmSteps, r.Slice.TotalInternalSteps, r.GasUsed, checkpointHash(cp), r.Slice.CheckpointRoot, len(r.Logs), reopenedInstalled, h.AS0.ContentCommitment, h.Index.FinalRoot, nil}
	for _, d := range h.Decoders {
		o.DecoderRoots = append(o.DecoderRoots, d.FinalRoot)
	}
	write(o)
}
func safelyCheckpoint(r cb0.JavaResult) ([]byte, error) {
	if len(r.Checkpoint) == 0 {
		return nil, fmt.Errorf("no published checkpoint")
	}
	if crypto.Keccak256Hash(r.Checkpoint) != r.Slice.CheckpointRoot {
		return nil, fmt.Errorf("bad EVM checkpoint hash")
	}
	return r.Checkpoint, nil
}
func main() {
	dir := flag.String("dir", "", "durable world directory")
	zipPath := flag.String("zip", "", "opaque generated ZIP for setup")
	length := flag.Uint("length", 0, "immutable archive byte length required when reopening")
	namesText := flag.String("names", "", "comma-separated known selected class stems")
	entryAt := flag.Uint("entry-at", 0, "selected entry index")
	entry := flag.String("entry", "run", "public static int entry method")
	allowFailure := flag.Bool("allow-failure", false, "record expected EVM refusal instead of exiting")
	mode := flag.Int("mode", 0, "Launcher.run mode")
	quantum := flag.Uint64("quantum", 4096, "JVM units per EVM slice")
	command := flag.String("command", "setup", "setup or slice")
	flag.Parse()
	if *dir == "" {
		panic("-dir required")
	}
	if *command == "setup" {
		if *zipPath == "" {
			panic("-zip required")
		}
		raw, e := os.ReadFile(*zipPath)
		must(e)
		s, e := cb0.Open(*dir, owner, uint32(len(raw)))
		must(e)
		defer s.Close()
		if *namesText == "" {
			panic("-names required")
		}
		names := strings.Split(*namesText, ",")
		if len(names) == 0 || len(names) > 9 {
			panic("names must be 1..5")
		}
		pkg := prepare(s, raw, names)
		h := head(s)
		if len(names) > 8 {
			return
		}
		if h.Coordinator.PackageRoot != pkg {
			panic("EVM package root mismatch")
		}
		write(map[string]interface{}{"command": "setup", "pid": os.Getpid(), "packageRoot": pkg, "stateRoot": h.StateRoot, "classCount": h.Coordinator.ClassCount, "totalClassBytes": h.Coordinator.TotalClassBytes, "as0Root": h.AS0.ContentCommitment, "indexRoot": h.Index.FinalRoot})
		return
	}
	if *length == 0 || *length > 33554432 {
		panic("-length 1..33554432 required for reopen")
	}
	s, e := cb0.Open(*dir, owner, uint32(*length))
	must(e)
	defer s.Close()
	reopened, e := s.Initialization()
	must(e)
	if reopened.EngineInstalled {
		panic("reopen reinstalled engine")
	}
	h := head(s)
	if *command == "terminal" {
		cp, e := s.ReadCheckpoint(h.Java.CheckpointRoot)
		must(e)
		if crypto.Keccak256Hash(cp) != h.Java.CheckpointRoot {
			panic("terminal checkpoint hash mismatch")
		}
		write(map[string]interface{}{"command": "terminal", "pid": os.Getpid(), "reopenedEngineInstalled": reopened.EngineInstalled, "epoch": h.Java.Epoch, "lifecycle": h.Java.Lifecycle, "checkpointRoot": h.Java.CheckpointRoot, "checkpointSHA256": checkpointHash(cp), "machineRoot": h.Java.MachineStateRoot, "vfsRoot": h.Java.VFSStateRoot, "packageRoot": h.Coordinator.PackageRoot})
		return
	}
	var r cb0.JavaResult
	if h.Java.Epoch == 0 {
		r, e = s.Start(h.Coordinator.PackageRoot, uint8(*entryAt), *entry, []int32{int32(*mode)}, *quantum, 4096, ordinaryGas)
	} else {
		cp, ce := s.ReadCheckpoint(h.Java.CheckpointRoot)
		must(ce)
		r, e = s.Resume(h.Coordinator.PackageRoot, h.Java.Epoch, h.Java.CheckpointRoot, cp, *quantum, 4096, ordinaryGas)
	}
	if e != nil {
		if !*allowFailure {
			panic(e)
		}
		after := head(s)
		selector, code, detail := refusal(r.RevertData)
		write(map[string]interface{}{"command": "refusal", "pid": os.Getpid(), "error": e.Error(), "gasUsed": r.GasUsed, "revertData": "0x" + hex.EncodeToString(r.RevertData), "selector": selector, "code": code, "detail": detail, "beforeStateRoot": h.StateRoot, "afterStateRoot": after.StateRoot, "beforeEpoch": h.Java.Epoch, "afterEpoch": after.Java.Epoch, "beforeCheckpointRoot": h.Java.CheckpointRoot, "afterCheckpointRoot": after.Java.CheckpointRoot, "stateUnchanged": h.StateRoot == after.StateRoot && h.Java.Epoch == after.Java.Epoch && h.Java.CheckpointRoot == after.Java.CheckpointRoot})
		return
	}
	emit("slice", h, r, reopened.EngineInstalled)
}

// Keep filepath imported as a compile-time guard that durable paths are caller supplied.
var _ = filepath.Separator

func refusal(b []byte) (string, string, string) {
	if len(b) < 4 {
		return "0x" + hex.EncodeToString(b), "", ""
	}
	sel := "0x" + hex.EncodeToString(b[:4])
	if len(b) != 68 {
		return sel, "", ""
	}
	return sel, fmt.Sprint(binary.BigEndian.Uint64(b[28:36])), fmt.Sprint(binary.BigEndian.Uint64(b[60:68]))
}
