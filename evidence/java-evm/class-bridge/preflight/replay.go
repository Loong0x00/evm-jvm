// Disposable MC class-bridge preflight. This is intentionally outside production packages.
// It uses unsafe reflection only to attach the exact accepted LOCAL VFS0a runtime and an
// ordinary-CREATE adapter to the StateDB already owned by the accepted DI0 transport.
// It never reads DI0 plaintext into Go and never supplies a raw class to the JVM ABI.
package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"math/big"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
	"time"
	"unsafe"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/state"
	"github.com/ethereum/go-ethereum/core/tracing"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/core/vm"
	evmruntime "github.com/ethereum/go-ethereum/core/vm/runtime"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/as0"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/di0"
	"github.com/ethereum/go-ethereum/jvmevm/localcontinuation/vfs0a"
	"github.com/ethereum/go-ethereum/params"
)

const ordinaryGas = uint64(100_000_000)

var engineAddress = common.HexToAddress("0x4a564d45564d564653304152554e54494d450001")
var diOwner = common.HexToAddress("0x10000000000000000000000000000000000000d1")
var bridgeOwner = common.HexToAddress("0x20000000000000000000000000000000000000b1")

type measure struct {
	Label  string `json:"label"`
	Gas    uint64 `json:"gas"`
	WallMS int64  `json:"wallMs"`
	Kind   string `json:"kind"`
}
type tracker struct {
	Calls         uint64    `json:"driverOperations"`
	Nested        uint64    `json:"accountedGetterMutationAndAdapterCalls"`
	Gas           uint64    `json:"gas"`
	MaxCallWallMS int64     `json:"maxCallWallMs"`
	Measures      []measure `json:"measures"`
}

func (t *tracker) add(label, kind string, gas uint64, start time.Time, nested uint64) {
	ms := time.Since(start).Milliseconds()
	t.Calls++
	t.Nested += nested
	t.Gas += gas
	if ms > t.MaxCallWallMS {
		t.MaxCallWallMS = ms
	}
	t.Measures = append(t.Measures, measure{label, gas, ms, kind})
}

type resource struct {
	session  *di0.Session
	head     di0.Head
	track    tracker
	zipSHA   string
	zipBytes int
	name     string
}
type slice struct {
	Schema                uint32      `json:"schema"`
	Lifecycle             uint8       `json:"lifecycle"`
	Epoch                 uint64      `json:"epoch"`
	CheckpointRoot        common.Hash `json:"checkpointRoot"`
	MachineStateRoot      common.Hash `json:"machineStateRoot"`
	TotalJvmSteps         uint64      `json:"totalJvmSteps"`
	TotalInternalSteps    uint64      `json:"totalInternalSteps"`
	ExecutedJvmSteps      uint64      `json:"executedJvmSteps"`
	ExecutedInternalSteps uint32      `json:"executedInternalSteps"`
	Result                int32       `json:"result"`
	JavaKind              uint8       `json:"javaKind"`
	JavaRef               uint32      `json:"javaRef"`
	JavaClass             []byte      `json:"javaClass"`
	VFSStateRoot          common.Hash `json:"vfsStateRoot"`
	InodeCount            uint32      `json:"inodeCount"`
	DescriptorCount       uint32      `json:"descriptorCount"`
	LogicalFileBytes      uint64      `json:"logicalFileBytes"`
}
type bridgeResult struct {
	Binding    common.Hash
	Slice      slice
	Checkpoint []byte
	Gas        uint64
	Revert     []byte
}
type chainReport struct {
	Label          string         `json:"label"`
	EntryClass     string         `json:"entryClass"`
	Input          int32          `json:"input"`
	Result         int32          `json:"result"`
	Slices         int            `json:"slices"`
	TotalGas       uint64         `json:"totalGas"`
	Binding        common.Hash    `json:"inputBinding"`
	ResourceF      common.Hash    `json:"resourceF"`
	IndexRoot      common.Hash    `json:"indexRoot"`
	CheckpointRoot common.Hash    `json:"checkpointRoot"`
	MachineRoot    common.Hash    `json:"machineRoot"`
	VFSRoot        common.Hash    `json:"vfsRoot"`
	JVM            uint64         `json:"jvmSteps"`
	Internal       uint64         `json:"internalSteps"`
	EngineOwner    common.Address `json:"engineOwner"`
}
type failureReport struct {
	Label      string `json:"label"`
	Selector   string `json:"selector"`
	Error      string `json:"error"`
	Gas        uint64 `json:"gas"`
	HeadAbsent bool   `json:"headAbsent"`
}
type report struct {
	BaseCommit  string                   `json:"baseCommit"`
	GeneratedAt string                   `json:"generatedAtUTC"`
	Compiler    map[string]interface{}   `json:"compiler"`
	Pins        map[string]interface{}   `json:"pins"`
	Successes   []chainReport            `json:"successes"`
	Failures    []failureReport          `json:"failures"`
	Resources   []map[string]interface{} `json:"resources"`
	Totals      map[string]interface{}   `json:"totals"`
}

func abiPack(types []string, values ...interface{}) []byte {
	var a abi.Arguments
	for _, n := range types {
		t, e := abi.NewType(n, "", nil)
		must(e)
		a = append(a, abi.Argument{Type: t})
	}
	b, e := a.Pack(values...)
	must(e)
	return b
}
func pageCommit(controller common.Address, index uint32, raw []byte) common.Hash {
	return crypto.Keccak256Hash(abiPack([]string{"bytes32", "address", "uint32", "uint32", "bytes32"}, crypto.Keccak256Hash([]byte("MC-AS0/page/v1")), controller, index, uint32(len(raw)), crypto.Keccak256Hash(raw)))
}
func must(e error) {
	if e != nil {
		panic(e)
	}
}
func sha(b []byte) string { x := sha256.Sum256(b); return hex.EncodeToString(x[:]) }

func head(r *resource, label string) di0.Head {
	s := time.Now()
	h, e := r.session.Head(ordinaryGas)
	must(e)
	nested := uint64(10)
	if h.Index.Address != (common.Address{}) {
		nested += 13
	}
	if h.Decoder.Address != (common.Address{}) {
		nested += 29
	}
	r.track.add(label, "view-group", h.GasUsed, s, nested)
	return h
}
func prepare(zipPath, name string, final bool) *resource {
	raw, e := os.ReadFile(zipPath)
	must(e)
	r := &resource{zipSHA: sha(raw), zipBytes: len(raw), name: name}
	s := time.Now()
	r.session, e = di0.NewMemory(diOwner, uint32(len(raw)))
	must(e)
	c, e := r.session.Creation()
	must(e)
	r.track.add("as0-create", "CREATE", c.GasUsed, s, 0)
	for at := 0; at < len(raw); at += int(as0.PageSize) {
		end := at + int(as0.PageSize)
		if end > len(raw) {
			end = len(raw)
		}
		p := raw[at:end]
		s = time.Now()
		op, e := r.session.Append(uint32(at), p, pageCommit(c.Controller, uint32(at)/as0.PageSize, p), ordinaryGas)
		must(e)
		r.track.add("as0-append", "CALL", op.GasUsed, s, 1)
	}
	h := head(r, "as0-head")
	s = time.Now()
	op, e := r.session.Seal(h.AS0.Cursor, h.AS0.ChainCommitment, ordinaryGas)
	must(e)
	r.track.add("as0-seal", "CALL", op.GasUsed, s, 1)
	h = head(r, "sealed-head")
	s = time.Now()
	op, e = r.session.CreateIndex(h.AS0.ContentCommitment, ordinaryGas)
	must(e)
	r.track.add("zi0-create", "CREATE", op.GasUsed, s, 0)
	s = time.Now()
	op, e = r.session.DiscoverIndex(ordinaryGas)
	must(e)
	r.track.add("zi0-discover", "CALL", op.GasUsed, s, 1)
	for {
		h = head(r, "zi0-scan-head")
		if h.Index.NextEntry == h.Index.Count {
			break
		}
		s = time.Now()
		op, e = r.session.ScanIndex(h.Index.NextEntry, h.Index.CDCursor, h.Index.Rolling, 64, ordinaryGas)
		must(e)
		r.track.add("zi0-scan", "CALL", op.GasUsed, s, 1)
	}
	h = head(r, "zi0-finish-head")
	s = time.Now()
	op, e = r.session.FinishIndex(h.Index.Count, h.Index.CDCursor, h.Index.Rolling, ordinaryGas)
	must(e)
	r.track.add("zi0-finish", "CALL", op.GasUsed, s, 1)
	h = head(r, "zi0-final-head")
	s = time.Now()
	op, e = r.session.CreateDecoder(h.Index.FinalRoot, []byte(name), ordinaryGas)
	must(e)
	r.track.add("di0-create", "CREATE", op.GasUsed, s, 0)
	h = head(r, "di0-bound-head")
	r.head = h
	if !final {
		return r
	}
	for h.Decoder.Phase == 1 {
		s = time.Now()
		op, e = r.session.Step(h.Decoder.Work, 128, ordinaryGas)
		must(e)
		r.track.add("di0-step-q128", "CALL", op.GasUsed, s, 1)
		h = head(r, "di0-step-head")
	}
	for h.Decoder.Phase != 4 {
		s = time.Now()
		op, e = r.session.Publish(h.Decoder.PublishedPages, h.Decoder.PublicationRolling, 1, ordinaryGas)
		must(e)
		r.track.add("di0-publish", "CALL", op.GasUsed, s, 1)
		h = head(r, "di0-publish-head")
	}
	r.head = h
	return r
}

// The accepted Session intentionally hides StateDB. This disposable harness takes only
// the pointer; it never reads decoder page code or plaintext through it.
func stateOf(s *di0.Session) *state.StateDB {
	v := reflect.ValueOf(s).Elem().FieldByName("state")
	return *(**state.StateDB)(unsafe.Pointer(v.UnsafeAddr()))
}
func config(st *state.StateDB, origin common.Address, gas uint64) *evmruntime.Config {
	z := common.Hash{}
	return &evmruntime.Config{ChainConfig: params.AllDevChainProtocolChanges, Difficulty: new(big.Int), Origin: origin, Coinbase: common.Address{}, BlockNumber: big.NewInt(1), Time: 1, GasLimit: gas, GasPrice: new(big.Int), Value: new(big.Int), BaseFee: new(big.Int).SetUint64(params.InitialBaseFee), BlobBaseFee: new(big.Int).SetUint64(params.BlobTxMinBlobGasprice), Random: &z, State: st, GetHashFn: func(uint64) common.Hash { return common.Hash{} }, EVMConfig: vm.Config{}}
}

type bridgeEnv struct {
	st      *state.StateDB
	address common.Address
	abi     abi.ABI
	vfsABI  abi.ABI
	track   *tracker
}

func attach(r *resource, artifactPath string) *bridgeEnv {
	st := stateOf(r.session)
	engine, e := vfs0a.Runtime()
	must(e)
	if sha(engine) != "717683f8ba67141bb7b5640a7079d396cda661dd53cd2afb7ab4eb6032ac3e86" {
		panic("VFS runtime pin")
	}
	st.CreateAccount(engineAddress)
	st.SetCode(engineAddress, engine, tracing.CodeChangeUnspecified)
	var a struct {
		ABI      json.RawMessage `json:"abi"`
		Bytecode string          `json:"bytecode"`
		Deployed string          `json:"deployedBytecode"`
	}
	b, e := os.ReadFile(artifactPath)
	must(e)
	must(json.Unmarshal(b, &a))
	wa, e := abi.JSON(bytes.NewReader(a.ABI))
	must(e)
	init, e := hex.DecodeString(a.Bytecode)
	must(e)
	runtime, e := hex.DecodeString(a.Deployed)
	must(e)
	s := time.Now()
	out, addr, left, e := evmruntime.Create(init, config(st, bridgeOwner, ordinaryGas))
	must(e)
	if !bytes.Equal(out, runtime) || !bytes.Equal(st.GetCode(addr), runtime) {
		panic("wrapper CREATE mismatch")
	}
	r.track.add("bridge-create", "CREATE", ordinaryGas-left, s, 0)
	va, e := vfs0a.ABI()
	must(e)
	return &bridgeEnv{st, addr, wa, va, &r.track}
}

func (b *bridgeEnv) call(method string, args ...interface{}) bridgeResult {
	return b.callFrom(bridgeOwner, method, args...)
}
func (b *bridgeEnv) callFrom(origin common.Address, method string, args ...interface{}) bridgeResult {
	data, e := b.abi.Pack(method, args...)
	must(e)
	snap := b.st.Snapshot()
	s := time.Now()
	out, left, e := evmruntime.Call(b.address, data, config(b.st, origin, ordinaryGas))
	gas := ordinaryGas - left
	nested := uint64(7)
	if e != nil {
		b.st.RevertToSnapshot(snap)
		// Exact adapter-internal call count for coded early refusals; bubbled JVM
		// verifier failures have traversed all six DI0 calls plus the engine call.
		if len(out) == 36 && bytes.Equal(out[:4], crypto.Keccak256([]byte("BridgeError(uint256)"))[:4]) {
			switch new(big.Int).SetBytes(out[4:]).Uint64() {
			case 3:
				nested = 0
			case 4:
				nested = 1
			case 5:
				nested = 2
			case 6:
				nested = 3
			case 7:
				nested = 4
			case 8:
				nested = 5
			case 10:
				nested = 0
			}
		}
		b.track.add("bridge-"+method+"-revert", "CALL", gas, s, nested)
		return bridgeResult{Gas: gas, Revert: append([]byte(nil), out...)}
	}
	b.track.add("bridge-"+method, "CALL", gas, s, nested)
	vals, e := b.abi.Unpack(method, out)
	must(e)
	if len(vals) != 2 {
		panic("bridge output")
	}
	binding := common.Hash(vals[0].([32]byte))
	engineOut := vals[1].([]byte)
	var got slice
	var checkpoint []byte
	if method == "start" {
		var d struct {
			Result     slice
			Checkpoint []byte
		}
		must(b.vfsABI.UnpackIntoInterface(&d, method, engineOut))
		got, checkpoint = d.Result, d.Checkpoint
	} else {
		var d struct {
			Result          slice
			ChildCheckpoint []byte
		}
		must(b.vfsABI.UnpackIntoInterface(&d, method, engineOut))
		got, checkpoint = d.Result, d.ChildCheckpoint
	}
	return bridgeResult{Binding: binding, Slice: got, Checkpoint: append([]byte(nil), checkpoint...), Gas: gas}
}
func (b *bridgeEnv) engineHead(id common.Hash) (common.Address, bool) {
	data, e := b.vfsABI.Pack("head", id)
	must(e)
	out, _, e := evmruntime.Call(engineAddress, data, config(b.st, bridgeOwner, ordinaryGas))
	must(e)
	vals, e := b.vfsABI.Unpack("head", out)
	must(e)
	owner := vals[0].(common.Address)
	epoch := vals[1].(uint64)
	return owner, epoch == 0
}
func selector(data []byte) string {
	if len(data) < 4 {
		return "0x"
	}
	return "0x" + hex.EncodeToString(data[:4])
}
func errorName(a abi.ABI, data []byte) string {
	if len(data) < 4 {
		return "non-selector"
	}
	bridgeSel := crypto.Keccak256([]byte("BridgeError(uint256)"))[:4]
	if bytes.Equal(data[:4], bridgeSel) {
		if len(data) == 36 {
			return fmt.Sprintf("BridgeError(%d)", new(big.Int).SetBytes(data[4:]).Uint64())
		}
		return "BridgeError"
	}
	for n, e := range a.Errors {
		if bytes.Equal(data[:4], e.ID[:4]) {
			return n
		}
	}
	return "unknown"
}
func id(label string) common.Hash {
	return crypto.Keccak256Hash([]byte("class-bridge-preflight:" + label))
}

func runChain(b *bridgeEnv, r *resource, label, entryClass string, input int32, quantum uint64) (chainReport, error) {
	h := r.head
	inst := id(label)
	x := b.call("start", h.Decoder.Address, []byte(r.name), h.Index.FinalRoot, h.Decoder.FinalRoot, inst, entryClass, "run", []int32{input}, quantum, uint32(4096))
	if len(x.Revert) > 0 {
		return chainReport{}, fmt.Errorf("start revert %x", x.Revert)
	}
	gas := x.Gas
	slices := 1
	binding := x.Binding
	for x.Slice.Lifecycle == 1 {
		prev := x.Slice
		x = b.call("resume", h.Decoder.Address, []byte(r.name), h.Index.FinalRoot, h.Decoder.FinalRoot, inst, entryClass, prev.Epoch, prev.CheckpointRoot, x.Checkpoint, quantum, uint32(4096))
		if len(x.Revert) > 0 {
			return chainReport{}, fmt.Errorf("resume revert %x", x.Revert)
		}
		if x.Binding != binding {
			return chainReport{}, errors.New("binding changed")
		}
		gas += x.Gas
		slices++
		if slices > 256 {
			return chainReport{}, errors.New("slice bound")
		}
	}
	if x.Slice.Lifecycle != 2 {
		return chainReport{}, fmt.Errorf("terminal lifecycle %d java=%s", x.Slice.Lifecycle, x.Slice.JavaClass)
	}
	owner, _ := b.engineHead(inst)
	if owner != b.address {
		return chainReport{}, fmt.Errorf("engine owner %s != wrapper %s", owner, b.address)
	}
	return chainReport{label, entryClass, input, x.Slice.Result, slices, gas, binding, h.Decoder.FinalRoot, h.Index.FinalRoot, x.Slice.CheckpointRoot, x.Slice.MachineStateRoot, x.Slice.VFSStateRoot, x.Slice.TotalJvmSteps, x.Slice.TotalInternalSteps, owner}, nil
}

func resourceSummary(r *resource) map[string]interface{} {
	return map[string]interface{}{"name": r.name, "zipBytes": r.zipBytes, "zipSHA256": r.zipSHA, "resourceStateRoot": r.head.StateRoot, "indexRoot": r.head.Index.FinalRoot, "resourceF": r.head.Decoder.FinalRoot, "plainBytes": r.head.Decoder.PlainSize, "decoder": r.head.Decoder.Address, "decoderWork": r.head.Decoder.Work, "publishedPages": r.head.Decoder.PublishedPages, "tracker": r.track}
}
func main() {
	if len(os.Args) != 4 {
		panic("usage: replay.go BUILD-DIR BRIDGE-ARTIFACT OUT.json")
	}
	build, artifact, outPath := os.Args[1], os.Args[2], os.Args[3]
	z := filepath.Join(build, "zips")
	rep := report{BaseCommit: "73e17afbb5373b0cc2938b8b90ca950146fe8e9b", GeneratedAt: time.Now().UTC().Format(time.RFC3339), Compiler: map[string]interface{}{}, Pins: map[string]interface{}{"di0RuntimeKeccak": "0x946686a0a4f09ec9a03e3eb63e9bbeac008212061d6f316586034cf800380c37", "di0CombinedSHA256": "72773d5c53533969a6b0d0a1391513330affb11b4cdf300fa4c115bab23613ca", "vfs0aRuntimeSHA256": "717683f8ba67141bb7b5640a7079d396cda661dd53cd2afb7ab4eb6032ac3e86", "vfs0aRuntimeKeccak": "0xe7f4de699588a3d58624e8ab717a00809759d112952ca1fac8bbc74637118c84", "vfsAddress": engineAddress}}
	var art map[string]interface{}
	b0, e := os.ReadFile(artifact)
	must(e)
	must(json.Unmarshal(b0, &art))
	rep.Compiler = map[string]interface{}{"version": art["compiler"], "settings": art["settings"], "sourceSHA256": art["sourceSHA256"], "artifactSHA256": sha(b0)}
	alpha := prepare(filepath.Join(z, "BridgeAlpha.zip"), "BridgeAlpha.class", true)
	ae := attach(alpha, artifact)
	// Refuse caller assertions before any engine anchor can be created.
	badID := id("unauthorized")
	x := ae.callFrom(common.HexToAddress("0x30000000000000000000000000000000000000ff"), "start", alpha.head.Decoder.Address, []byte(alpha.name), alpha.head.Index.FinalRoot, alpha.head.Decoder.FinalRoot, badID, "BridgeAlpha", "run", []int32{int32(7)}, uint64(4096), uint32(4096))
	_, abs := ae.engineHead(badID)
	rep.Failures = append(rep.Failures, failureReport{"unauthorized-caller", selector(x.Revert), errorName(ae.abi, x.Revert), x.Gas, abs})
	badID = id("wrong-final")
	x = ae.call("start", alpha.head.Decoder.Address, []byte(alpha.name), alpha.head.Index.FinalRoot, common.Hash{}, badID, "BridgeAlpha", "run", []int32{int32(7)}, uint64(4096), uint32(4096))
	_, abs = ae.engineHead(badID)
	rep.Failures = append(rep.Failures, failureReport{"wrong-resource-F", selector(x.Revert), errorName(ae.abi, x.Revert), x.Gas, abs})
	badID = id("wrong-name")
	x = ae.call("start", alpha.head.Decoder.Address, []byte("Wrong.class"), alpha.head.Index.FinalRoot, alpha.head.Decoder.FinalRoot, badID, "Wrong", "run", []int32{int32(7)}, uint64(4096), uint32(4096))
	_, abs = ae.engineHead(badID)
	rep.Failures = append(rep.Failures, failureReport{"wrong-archive-name-binding", selector(x.Revert), errorName(ae.abi, x.Revert), x.Gas, abs})
	direct, e := runChain(ae, alpha, "alpha-direct", "BridgeAlpha", 7, 4096)
	must(e)
	q7, e := runChain(ae, alpha, "alpha-q7", "BridgeAlpha", 7, 7)
	must(e)
	if direct.Result != q7.Result || direct.MachineRoot != q7.MachineRoot || direct.JVM != q7.JVM || direct.Internal != q7.Internal {
		panic("alpha grouping mismatch")
	}
	rep.Successes = append(rep.Successes, direct, q7)
	rep.Resources = append(rep.Resources, resourceSummary(alpha))
	alpha.session.Close()
	beta := prepare(filepath.Join(z, "BridgeBeta.zip"), "BridgeBeta.class", true)
	be := attach(beta, artifact)
	br, e := runChain(be, beta, "beta-direct", "BridgeBeta", 8, 4096)
	must(e)
	rep.Successes = append(rep.Successes, br)
	rep.Resources = append(rep.Resources, resourceSummary(beta))
	beta.session.Close()
	unv := prepare(filepath.Join(z, "BridgeMalformed.zip"), "BridgeMalformed.class", false)
	ue := attach(unv, artifact)
	badID = id("unverified")
	x = ue.call("start", unv.head.Decoder.Address, []byte(unv.name), unv.head.Index.FinalRoot, common.HexToHash("0x01"), badID, "BridgeMalformed", "run", []int32{int32(7)}, uint64(4096), uint32(4096))
	_, abs = ue.engineHead(badID)
	rep.Failures = append(rep.Failures, failureReport{"unverified-di0", selector(x.Revert), errorName(ue.abi, x.Revert), x.Gas, abs})
	rep.Resources = append(rep.Resources, resourceSummary(unv))
	unv.session.Close()
	alias := prepare(filepath.Join(z, "BridgeAlias.zip"), "BridgeAlias.class", true)
	ale := attach(alias, artifact)
	badID = id("declared-mismatch")
	x = ale.call("start", alias.head.Decoder.Address, []byte(alias.name), alias.head.Index.FinalRoot, alias.head.Decoder.FinalRoot, badID, "BridgeAlias", "run", []int32{int32(7)}, uint64(4096), uint32(4096))
	_, abs = ale.engineHead(badID)
	rep.Failures = append(rep.Failures, failureReport{"declared-name-mismatch", selector(x.Revert), errorName(ale.vfsABI, x.Revert), x.Gas, abs})
	rep.Resources = append(rep.Resources, resourceSummary(alias))
	alias.session.Close()
	malformed := prepare(filepath.Join(z, "BridgeMalformed.zip"), "BridgeMalformed.class", true)
	me := attach(malformed, artifact)
	badID = id("malformed")
	x = me.call("start", malformed.head.Decoder.Address, []byte(malformed.name), malformed.head.Index.FinalRoot, malformed.head.Decoder.FinalRoot, badID, "BridgeMalformed", "run", []int32{int32(7)}, uint64(4096), uint32(4096))
	_, abs = me.engineHead(badID)
	rep.Failures = append(rep.Failures, failureReport{"malformed-class", selector(x.Revert), errorName(me.vfsABI, x.Revert), x.Gas, abs})
	rep.Resources = append(rep.Resources, resourceSummary(malformed))
	malformed.session.Close()
	var gas, calls, nested uint64
	var maxWall int64
	for _, rr := range rep.Resources {
		t := rr["tracker"].(tracker)
		gas += t.Gas
		calls += t.Calls
		nested += t.Nested
		if t.MaxCallWallMS > maxWall {
			maxWall = t.MaxCallWallMS
		}
	}
	rep.Totals = map[string]interface{}{"gasIncludingGetterViews": gas, "recordedDriverOperations": calls, "accountedGetterMutationAndAdapterCalls": nested, "maxTopLevelCallWallMs": maxWall, "resourceSessions": len(rep.Resources)}
	sort.Slice(rep.Failures, func(i, j int) bool { return rep.Failures[i].Label < rep.Failures[j].Label })
	out, e := json.MarshalIndent(rep, "", "  ")
	must(e)
	must(os.WriteFile(outPath, append(out, '\n'), 0644))
	fmt.Printf("successes=%d failures=%d gas=%d calls=%d nested=%d\n", len(rep.Successes), len(rep.Failures), gas, calls, nested)
}

func init() { _ = strings.Builder{}; _ = types.EmptyRootHash }
