package cb0

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"strings"
	"sync"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
	runtimeassets "github.com/ethereum/go-ethereum/jvmevm/localcontinuation/cb0/runtime"
)

const (
	cb0ArtifactSHA256 = "b7a4c0e7affbc0a94850433f14f013ed10631261db7cfac5eac861323a196955"
	cb0SourceSHA256   = "bd21b94644e46f53d4c981b2c009f05d2c7f740a2b88a812febfb51dc0a47c04"
	cb0InitSHA256     = "6da48cfe0b04917473fd2a519cc49b027bb84c886ccc8b2c9f3dfc5a57ee68e6"
	cb0RuntimeSHA256  = "c4f72b172b43eff872a73a3c35663a1d3580937df3ae41375931b04007f953bb"
	cb0ABISHA256      = "24167399ecaf9269c33414693f4d915ecd4a30acd1413ea0cd834a4380eb92d0"
	cb0LayoutSHA256   = "8119393c6cef7af91a63b701db3298014a3770f464b2d413a08067e2241fb326"
	cb0RuntimeKeccak  = "0377ea7221ada38bbc85344b0ee8fc057774040c92b3995981cbe7ada316aebc"
)

var (
	cb0AS0Code       = common.HexToHash("0xc8cec283e80fd82b15254bd50a9f2aea3a91305ba71f756f834439280600f896")
	cb0ZI0Code       = common.HexToHash("0x0c22eca78e00865ce03e8e298708bfe51ce9856cff138d1046905fc285ad5a77")
	cb0DI0Code       = common.HexToHash("0x946686a0a4f09ec9a03e3eb63e9bbeac008212061d6f316586034cf800380c37")
	cb0VFSCode       = common.HexToHash("0xe7f4de699588a3d58624e8ab717a00809759d112952ca1fac8bbc74637118c84")
	cb0EngineAddress = common.HexToAddress("0x4a564d45564d564653304152554e54494d450001")
)

type cb0Artifact struct {
	ContractName        string                     `json:"contractName"`
	ABI                 json.RawMessage            `json:"abi"`
	Bytecode            string                     `json:"bytecode"`
	DeployedBytecode    string                     `json:"deployedBytecode"`
	ImmutableReferences map[string]json.RawMessage `json:"immutableReferences"`
	Compiler            struct {
		Version   string `json:"version"`
		Optimizer struct {
			Enabled bool   `json:"enabled"`
			Runs    uint32 `json:"runs"`
		} `json:"optimizer"`
		ViaIR      bool   `json:"viaIR"`
		EVMVersion string `json:"evmVersion"`
		Metadata   struct {
			AppendCBOR   bool   `json:"appendCBOR"`
			BytecodeHash string `json:"bytecodeHash"`
		} `json:"metadata"`
	} `json:"compiler"`
	SourceHashes map[string]string `json:"sourceHashes"`
	CodeHashes   struct {
		BytecodeSHA256    string `json:"bytecodeSHA256"`
		DeployedSHA256    string `json:"deployedBytecodeSHA256"`
		DeployedKeccak256 string `json:"deployedBytecodeKeccak256"`
	} `json:"codeHashes"`
	DependencyPins struct {
		AS0        string `json:"AS0RuntimeCodeKeccak256"`
		ZI0        string `json:"ZI0RuntimeCodeKeccak256"`
		DI0        string `json:"DI0RuntimeCodeKeccak256"`
		VFS        string `json:"VFS0aRuntimeCodeKeccak256"`
		VFSAddress string `json:"VFS0aAddress"`
	} `json:"dependencyPins"`
	Limits struct {
		ArchiveBytes       uint32 `json:"archiveBytes"`
		Resources          uint8  `json:"resources"`
		ClassBytes         uint32 `json:"classBytes"`
		RawNameBytes       uint32 `json:"rawNameBytes"`
		ResourceReadBytes  uint32 `json:"resourceReadBytes"`
		CheckpointBytes    uint32 `json:"checkpointBytes"`
		JVMUnits           uint32 `json:"jvmUnits"`
		InternalUnits      uint32 `json:"internalUnits"`
		EngineRuntimeBytes uint32 `json:"engineRuntimeBytes"`
		RuntimeBytes       uint32 `json:"runtimeBytes"`
		CompleteInitBytes  uint32 `json:"completeInitBytes"`
		SeedFiles          uint8  `json:"seedFiles"`
	} `json:"limits"`
	StorageLayout json.RawMessage `json:"storageLayout"`
}

type cb0Loaded struct {
	abi                abi.ABI
	raw, init, runtime []byte
	runtimeHash        common.Hash
}

var cb0LoadOnce sync.Once
var cb0Load cb0Loaded
var cb0LoadErr error

func cb0ArtifactLoad() (cb0Loaded, error) {
	cb0LoadOnce.Do(func() { cb0Load, cb0LoadErr = cb0ValidateArtifact(runtimeassets.Artifact()) })
	return cb0Load, cb0LoadErr
}

func cb0ValidateArtifact(raw []byte) (cb0Loaded, error) {
	var d cb0Artifact
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&d); err != nil {
		return cb0Loaded{}, fmt.Errorf("cb0: decode runtime artifact: %w", err)
	}
	var trailing any
	if err := decoder.Decode(&trailing); err != io.EOF {
		return cb0Loaded{}, errors.New("cb0: runtime artifact has trailing data")
	}
	if cb0Digest(raw) != cb0ArtifactSHA256 || d.ContractName != "CB0ClassCoordinator" {
		return cb0Loaded{}, errors.New("cb0: combined artifact pin or contract differs")
	}
	canonicalABI, err := cb0CanonicalJSON(d.ABI)
	if err != nil || cb0Digest(canonicalABI) != cb0ABISHA256 {
		return cb0Loaded{}, errors.New("cb0: ABI schema pin differs")
	}
	a, err := abi.JSON(bytes.NewReader(d.ABI))
	if err != nil {
		return cb0Loaded{}, fmt.Errorf("cb0: parse coordinator ABI: %w", err)
	}
	if err := cb0ValidateABI(a); err != nil {
		return cb0Loaded{}, err
	}
	init, err := cb0Code("init", d.Bytecode)
	if err != nil {
		return cb0Loaded{}, err
	}
	run, err := cb0Code("runtime", d.DeployedBytecode)
	if err != nil {
		return cb0Loaded{}, err
	}
	if cb0Digest(init) != cb0InitSHA256 || cb0Digest(run) != cb0RuntimeSHA256 || len(init)+2016 > 49152 || len(run) > 24576 {
		return cb0Loaded{}, errors.New("cb0: coordinator code hash or frozen size differs")
	}
	runHash := crypto.Keccak256Hash(run)
	if runHash != common.HexToHash("0x"+cb0RuntimeKeccak) {
		return cb0Loaded{}, errors.New("cb0: computed runtime Keccak pin differs")
	}
	if d.CodeHashes.BytecodeSHA256 != cb0InitSHA256 || d.CodeHashes.DeployedSHA256 != cb0RuntimeSHA256 || d.CodeHashes.DeployedKeccak256 != strings.TrimPrefix(runHash.Hex(), "0x") {
		return cb0Loaded{}, errors.New("cb0: artifact code hash fields differ")
	}
	if len(d.ImmutableReferences) != 0 || d.Compiler.Version != "0.8.30+commit.73712a01.Emscripten.clang" || !d.Compiler.Optimizer.Enabled || d.Compiler.Optimizer.Runs != 200 || !d.Compiler.ViaIR || d.Compiler.EVMVersion != "cancun" || d.Compiler.Metadata.AppendCBOR || d.Compiler.Metadata.BytecodeHash != "none" {
		return cb0Loaded{}, errors.New("cb0: compiler or immutable settings differ")
	}
	if len(d.SourceHashes) != 1 || d.SourceHashes["CB0ClassCoordinator.sol"] != cb0SourceSHA256 {
		return cb0Loaded{}, errors.New("cb0: source pin differs")
	}
	if d.DependencyPins.AS0 != strings.TrimPrefix(cb0AS0Code.Hex(), "0x") || d.DependencyPins.ZI0 != strings.TrimPrefix(cb0ZI0Code.Hex(), "0x") || d.DependencyPins.DI0 != strings.TrimPrefix(cb0DI0Code.Hex(), "0x") || d.DependencyPins.VFS != strings.TrimPrefix(cb0VFSCode.Hex(), "0x") || d.DependencyPins.VFSAddress != strings.ToLower(strings.TrimPrefix(cb0EngineAddress.Hex(), "0x")) {
		return cb0Loaded{}, errors.New("cb0: dependency pins differ")
	}
	want := struct {
		ArchiveBytes       uint32
		Resources          uint8
		ClassBytes         uint32
		RawNameBytes       uint32
		ResourceReadBytes  uint32
		CheckpointBytes    uint32
		JVMUnits           uint32
		InternalUnits      uint32
		EngineRuntimeBytes uint32
		RuntimeBytes       uint32
		CompleteInitBytes  uint32
		SeedFiles          uint8
	}{33554432, 4, 65536, 256, 4096, 1048576, 4096, 4096, 327680, 24576, 49152, 0}
	got := struct {
		ArchiveBytes       uint32
		Resources          uint8
		ClassBytes         uint32
		RawNameBytes       uint32
		ResourceReadBytes  uint32
		CheckpointBytes    uint32
		JVMUnits           uint32
		InternalUnits      uint32
		EngineRuntimeBytes uint32
		RuntimeBytes       uint32
		CompleteInitBytes  uint32
		SeedFiles          uint8
	}{d.Limits.ArchiveBytes, d.Limits.Resources, d.Limits.ClassBytes, d.Limits.RawNameBytes, d.Limits.ResourceReadBytes, d.Limits.CheckpointBytes, d.Limits.JVMUnits, d.Limits.InternalUnits, d.Limits.EngineRuntimeBytes, d.Limits.RuntimeBytes, d.Limits.CompleteInitBytes, d.Limits.SeedFiles}
	if got != want {
		return cb0Loaded{}, errors.New("cb0: frozen limits differ")
	}
	layout, err := cb0CanonicalJSON(d.StorageLayout)
	if err != nil || cb0Digest(layout) != cb0LayoutSHA256 {
		return cb0Loaded{}, errors.New("cb0: storage layout pin differs")
	}
	return cb0Loaded{a, append([]byte(nil), d.ABI...), init, run, runHash}, nil
}
func cb0CanonicalJSON(raw []byte) ([]byte, error) {
	var value interface{}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.UseNumber()
	if err := decoder.Decode(&value); err != nil {
		return nil, err
	}
	var trailing interface{}
	if err := decoder.Decode(&trailing); err != io.EOF {
		return nil, errors.New("cb0: trailing canonical JSON")
	}
	return json.Marshal(value)
}

func cb0Digest(b []byte) string { h := sha256.Sum256(b); return hex.EncodeToString(h[:]) }
func cb0Code(label, s string) ([]byte, error) {
	s = strings.TrimSpace(s)
	if strings.HasPrefix(s, "0x") || s == "" || len(s)%2 != 0 || s != strings.ToLower(s) {
		return nil, fmt.Errorf("cb0: %s must be nonempty lowercase hex without 0x", label)
	}
	b, e := hex.DecodeString(s)
	if e != nil {
		return nil, fmt.Errorf("cb0: decode %s: %w", label, e)
	}
	return b, nil
}

func cb0ValidateABI(a abi.ABI) error {
	if a.HasFallback() || a.HasReceive() || len(a.Events) != 0 {
		return errors.New("cb0: ABI has forbidden surface")
	}
	type methodShape struct {
		sig, mut                             string
		inNames, inTypes, outNames, outTypes []string
	}
	want := map[string]methodShape{
		"owner":           {"owner()", "view", nil, nil, []string{""}, []string{"address"}},
		"finalIndex":      {"finalIndex()", "view", nil, nil, []string{""}, []string{"address"}},
		"finalIndexRoot":  {"finalIndexRoot()", "view", nil, nil, []string{""}, []string{"bytes32"}},
		"packageRoot":     {"packageRoot()", "view", nil, nil, []string{""}, []string{"bytes32"}},
		"instanceId":      {"instanceId()", "view", nil, nil, []string{""}, []string{"bytes32"}},
		"totalClassBytes": {"totalClassBytes()", "view", nil, nil, []string{""}, []string{"uint32"}},
		"classCount":      {"classCount()", "view", nil, nil, []string{""}, []string{"uint8"}},
		"classBinding":    {"classBinding(uint8)", "view", []string{"at"}, []string{"uint8"}, []string{"decoder", "rawName", "resourceRoot", "classSize"}, []string{"address", "bytes", "bytes32", "uint32"}},
		"start":           {"start(bytes32,uint8,string,int32[],uint64,uint32)", "nonpayable", []string{"assertedPackageRoot", "entryAt", "entry", "args", "maxJvmSteps", "maxInternalSteps"}, []string{"bytes32", "uint8", "string", "int32[]", "uint64", "uint32"}, []string{"engineReturn"}, []string{"bytes"}},
		"resume":          {"resume(bytes32,uint64,bytes32,bytes,uint64,uint32)", "nonpayable", []string{"assertedPackageRoot", "expectedEpoch", "expectedCheckpointRoot", "checkpoint", "maxJvmSteps", "maxInternalSteps"}, []string{"bytes32", "uint64", "bytes32", "bytes", "uint64", "uint32"}, []string{"engineReturn"}, []string{"bytes"}},
	}
	if len(a.Methods) != len(want) {
		return errors.New("cb0: ABI method count differs")
	}
	for name, shape := range want {
		m, ok := a.Methods[name]
		if !ok || m.RawName != name || m.Sig != shape.sig || m.StateMutability != shape.mut || !cb0ABIArguments(m.Inputs, shape.inNames, shape.inTypes) || !cb0ABIArguments(m.Outputs, shape.outNames, shape.outTypes) {
			return fmt.Errorf("cb0: ABI method %s differs", name)
		}
	}
	constructorNames := []string{"fixedOwner", "fixedInstanceSalt", "fixedDecoders", "fixedRawNames", "assertedIndexRoots", "assertedResourceRoots", "assertedPackageRoot"}
	constructorTypes := []string{"address", "bytes32", "address[]", "bytes[]", "bytes32[]", "bytes32[]", "bytes32"}
	if a.Constructor.StateMutability != "nonpayable" || !cb0ABIArguments(a.Constructor.Inputs, constructorNames, constructorTypes) || len(a.Constructor.Outputs) != 0 {
		return errors.New("cb0: constructor differs")
	}
	e, ok := a.Errors["CB0Error"]
	if !ok || len(a.Errors) != 1 || e.Name != "CB0Error" || e.Sig != "CB0Error(uint256)" || !cb0ABIArguments(e.Inputs, []string{"code"}, []string{"uint256"}) {
		return errors.New("cb0: error surface differs")
	}
	return nil
}

func cb0ABIArguments(got abi.Arguments, names, types []string) bool {
	if len(got) != len(names) || len(got) != len(types) {
		return false
	}
	for i, arg := range got {
		if arg.Name != names[i] || arg.Type.String() != types[i] {
			return false
		}
	}
	return true
}
