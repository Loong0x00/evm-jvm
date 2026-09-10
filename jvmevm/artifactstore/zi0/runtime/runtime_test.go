package runtimeassets

import (
	"bytes"
	"compress/flate"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"hash/crc32"
	"math/big"
	"testing"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/state"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/core/vm"
	evmruntime "github.com/ethereum/go-ethereum/core/vm/runtime"
	"github.com/ethereum/go-ethereum/crypto"
	as0runtime "github.com/ethereum/go-ethereum/jvmevm/artifactstore/as0/runtime"
	"github.com/ethereum/go-ethereum/params"
)

const zi0TestGas = uint64(100_000_000)

var zi0TestOwner = common.HexToAddress("0x5a49300000000000000000000000000000000001")

type zi0TestArtifact struct {
	ContractName     string          `json:"contractName"`
	ABI              json.RawMessage `json:"abi"`
	Bytecode         string          `json:"bytecode"`
	DeployedBytecode string          `json:"deployedBytecode"`
	Immutable        map[string]any  `json:"immutableReferences"`
	Compiler         struct {
		Version    string `json:"version"`
		ViaIR      bool   `json:"viaIR"`
		EVMVersion string `json:"evmVersion"`
		Optimizer  struct {
			Enabled bool `json:"enabled"`
			Runs    int  `json:"runs"`
		} `json:"optimizer"`
		Metadata struct {
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
	DependencyPins map[string]string `json:"dependencyPins"`
}

func zi0TestLoadArtifact(t *testing.T, raw []byte, wantName string) (zi0TestArtifact, abi.ABI, []byte, []byte) {
	t.Helper()
	var doc zi0TestArtifact
	if err := json.Unmarshal(raw, &doc); err != nil {
		t.Fatal(err)
	}
	if doc.ContractName != wantName {
		t.Fatalf("contract=%q want %q", doc.ContractName, wantName)
	}
	contractABI, err := abi.JSON(bytes.NewReader(doc.ABI))
	if err != nil {
		t.Fatal(err)
	}
	decode := func(label, value string) []byte {
		t.Helper()
		out, err := hex.DecodeString(value)
		if err != nil || len(out) == 0 {
			t.Fatalf("decode %s: %v", label, err)
		}
		return out
	}
	return doc, contractABI, decode("init", doc.Bytecode), decode("runtime", doc.DeployedBytecode)
}

func TestZI0EmbeddedArtifactPinsAndDefensiveCopy(t *testing.T) {
	first := Artifact()
	second := Artifact()
	if len(first) == 0 || len(second) == 0 {
		t.Fatal("empty embedded artifact")
	}
	first[0] ^= 0xff
	if bytes.Equal(first, second) || !bytes.Equal(second, Artifact()) {
		t.Fatal("Artifact did not return a defensive copy")
	}

	doc, contractABI, initCode, runtimeCode := zi0TestLoadArtifact(t, second, "ZI0ZipIndex")
	if len(contractABI.Methods) != 18 || len(contractABI.Errors) != 1 || len(contractABI.Events) != 0 || contractABI.HasFallback() || contractABI.HasReceive() {
		t.Fatalf("unexpected ABI surface: methods=%d errors=%d events=%d", len(contractABI.Methods), len(contractABI.Errors), len(contractABI.Events))
	}
	if len(runtimeCode) > 24576 || len(initCode)+64 > 49152 || len(doc.Immutable) != 0 {
		t.Fatalf("artifact limits: init+args=%d runtime=%d immutables=%d", len(initCode)+64, len(runtimeCode), len(doc.Immutable))
	}
	if doc.Compiler.Version != "0.8.30+commit.73712a01.Emscripten.clang" || !doc.Compiler.ViaIR || doc.Compiler.EVMVersion != "cancun" || !doc.Compiler.Optimizer.Enabled || doc.Compiler.Optimizer.Runs != 200 || doc.Compiler.Metadata.AppendCBOR || doc.Compiler.Metadata.BytecodeHash != "none" {
		t.Fatalf("compiler settings differ: %+v", doc.Compiler)
	}
	if len(doc.SourceHashes) != 1 || doc.SourceHashes["ZI0ZipIndex.sol"] == "" {
		t.Fatalf("source pins differ: %+v", doc.SourceHashes)
	}
	initSHA := sha256.Sum256(initCode)
	runtimeSHA := sha256.Sum256(runtimeCode)
	if hex.EncodeToString(initSHA[:]) != doc.CodeHashes.BytecodeSHA256 || hex.EncodeToString(runtimeSHA[:]) != doc.CodeHashes.DeployedSHA256 || crypto.Keccak256Hash(runtimeCode).Hex()[2:] != doc.CodeHashes.DeployedKeccak256 {
		t.Fatal("artifact code hash pins do not match embedded code")
	}
	if doc.DependencyPins["AS0RuntimeCodeKeccak256"] != "c8cec283e80fd82b15254bd50a9f2aea3a91305ba71f756f834439280600f896" {
		t.Fatal("accepted AS0 runtime pin differs")
	}
}

func zi0TestConfig(st *state.StateDB, owner common.Address, gas uint64) *evmruntime.Config {
	zero := common.Hash{}
	return &evmruntime.Config{
		ChainConfig: params.AllDevChainProtocolChanges,
		Difficulty:  new(big.Int), Origin: owner, Coinbase: common.Address{},
		BlockNumber: big.NewInt(1), Time: 1, GasLimit: gas,
		GasPrice: new(big.Int), Value: new(big.Int),
		BaseFee:     new(big.Int).SetUint64(params.InitialBaseFee),
		BlobBaseFee: new(big.Int).SetUint64(params.BlobTxMinBlobGasprice),
		Random:      &zero, State: st, GetHashFn: func(uint64) common.Hash { return common.Hash{} },
		EVMConfig: vm.Config{},
	}
}

func zi0TestCall(t *testing.T, st *state.StateDB, contract common.Address, contractABI abi.ABI, method string, args ...any) ([]any, uint64) {
	t.Helper()
	input, err := contractABI.Pack(method, args...)
	if err != nil {
		t.Fatal(err)
	}
	output, left, err := evmruntime.Call(contract, input, zi0TestConfig(st, zi0TestOwner, zi0TestGas))
	if err != nil {
		t.Fatalf("%s failed after %d gas: %v output=0x%x", method, zi0TestGas-left, err, output)
	}
	values, err := contractABI.Unpack(method, output)
	if err != nil {
		t.Fatalf("unpack %s: %v", method, err)
	}
	return values, zi0TestGas - left
}

func zi0TestErrorCall(t *testing.T, st *state.StateDB, caller, contract common.Address, contractABI abi.ABI, method string, want uint64, args ...any) uint64 {
	t.Helper()
	input, err := contractABI.Pack(method, args...)
	if err != nil {
		t.Fatal(err)
	}
	output, left, callErr := evmruntime.Call(contract, input, zi0TestConfig(st, caller, zi0TestGas))
	if callErr == nil {
		t.Fatalf("%s unexpectedly succeeded", method)
	}
	definition := contractABI.Errors["ZI0Error"]
	if len(output) != 36 || !bytes.Equal(output[:4], definition.ID[:4]) || new(big.Int).SetBytes(output[4:]).Uint64() != want {
		t.Fatalf("%s revert=0x%x want ZI0Error(%d), err=%v", method, output, want, callErr)
	}
	return zi0TestGas - left
}

func zi0TestGetter[T any](t *testing.T, st *state.StateDB, at common.Address, contractABI abi.ABI, method string) T {
	t.Helper()
	values, _ := zi0TestCall(t, st, at, contractABI, method)
	if len(values) != 1 {
		t.Fatalf("%s returned %d values", method, len(values))
	}
	value, ok := values[0].(T)
	if !ok {
		t.Fatalf("%s returned %T", method, values[0])
	}
	return value
}

func zi0TestHash(t *testing.T, typesList []string, values ...any) common.Hash {
	t.Helper()
	arguments := make(abi.Arguments, len(typesList))
	for i, text := range typesList {
		typ, err := abi.NewType(text, "", nil)
		if err != nil {
			t.Fatal(err)
		}
		arguments[i] = abi.Argument{Type: typ}
	}
	encoded, err := arguments.Pack(values...)
	if err != nil {
		t.Fatal(err)
	}
	return crypto.Keccak256Hash(encoded)
}

type zi0TestEntry struct {
	name, plain, compressed []byte
	flags, method           uint16
	crc, local, dataStart   uint32
	recordEnd, centralEnd   uint32
	descriptor              uint8
}

type zi0TestZIP struct {
	raw           []byte
	entries       []zi0TestEntry
	central, eocd uint32
	centralSize   uint32
}

func zi0TestBuildZIP(t *testing.T) zi0TestZIP {
	t.Helper()
	entries := []zi0TestEntry{
		{name: []byte{0x00, 'a', '/', 0xff}, plain: []byte("opaque-store"), method: 0},
		{name: []byte("deflated.bin"), plain: bytes.Repeat([]byte{0x42, 0x00, 0xfe}, 17), method: 8, flags: 0x0808, descriptor: 2},
	}
	var archive bytes.Buffer
	for i := range entries {
		entry := &entries[i]
		entry.crc = crc32.ChecksumIEEE(entry.plain)
		if entry.method == 0 {
			entry.compressed = append([]byte(nil), entry.plain...)
		} else {
			var encoded bytes.Buffer
			writer, err := flate.NewWriter(&encoded, flate.BestSpeed)
			if err != nil {
				t.Fatal(err)
			}
			if _, err := writer.Write(entry.plain); err != nil {
				t.Fatal(err)
			}
			if err := writer.Close(); err != nil {
				t.Fatal(err)
			}
			entry.compressed = encoded.Bytes()
		}
		entry.local = uint32(archive.Len())
		header := make([]byte, 30)
		binary.LittleEndian.PutUint32(header[0:], 0x04034b50)
		binary.LittleEndian.PutUint16(header[4:], 20)
		binary.LittleEndian.PutUint16(header[6:], entry.flags)
		binary.LittleEndian.PutUint16(header[8:], entry.method)
		if entry.flags&8 == 0 {
			binary.LittleEndian.PutUint32(header[14:], entry.crc)
			binary.LittleEndian.PutUint32(header[18:], uint32(len(entry.compressed)))
			binary.LittleEndian.PutUint32(header[22:], uint32(len(entry.plain)))
		}
		binary.LittleEndian.PutUint16(header[26:], uint16(len(entry.name)))
		archive.Write(header)
		archive.Write(entry.name)
		entry.dataStart = uint32(archive.Len())
		archive.Write(entry.compressed)
		if entry.descriptor == 2 {
			descriptor := make([]byte, 16)
			binary.LittleEndian.PutUint32(descriptor[0:], 0x08074b50)
			binary.LittleEndian.PutUint32(descriptor[4:], entry.crc)
			binary.LittleEndian.PutUint32(descriptor[8:], uint32(len(entry.compressed)))
			binary.LittleEndian.PutUint32(descriptor[12:], uint32(len(entry.plain)))
			archive.Write(descriptor)
		}
		entry.recordEnd = uint32(archive.Len())
	}

	central := uint32(archive.Len())
	for i := range entries {
		entry := &entries[i]
		header := make([]byte, 46)
		binary.LittleEndian.PutUint32(header[0:], 0x02014b50)
		binary.LittleEndian.PutUint16(header[4:], 20)
		binary.LittleEndian.PutUint16(header[6:], 20)
		binary.LittleEndian.PutUint16(header[8:], entry.flags)
		binary.LittleEndian.PutUint16(header[10:], entry.method)
		binary.LittleEndian.PutUint32(header[16:], entry.crc)
		binary.LittleEndian.PutUint32(header[20:], uint32(len(entry.compressed)))
		binary.LittleEndian.PutUint32(header[24:], uint32(len(entry.plain)))
		binary.LittleEndian.PutUint16(header[28:], uint16(len(entry.name)))
		binary.LittleEndian.PutUint32(header[42:], entry.local)
		archive.Write(header)
		archive.Write(entry.name)
		entry.centralEnd = uint32(archive.Len())
	}
	centralSize := uint32(archive.Len()) - central
	eocd := uint32(archive.Len())
	end := make([]byte, 22)
	binary.LittleEndian.PutUint32(end[0:], 0x06054b50)
	binary.LittleEndian.PutUint16(end[8:], uint16(len(entries)))
	binary.LittleEndian.PutUint16(end[10:], uint16(len(entries)))
	binary.LittleEndian.PutUint32(end[12:], centralSize)
	binary.LittleEndian.PutUint32(end[16:], central)
	archive.Write(end)
	return zi0TestZIP{raw: archive.Bytes(), entries: entries, central: central, eocd: eocd, centralSize: centralSize}
}

func TestZI0FinalArtifactThroughOrdinaryAS0Create(t *testing.T) {
	fixture := zi0TestBuildZIP(t)
	_, as0ABI, as0Init, as0Runtime := zi0TestLoadArtifact(t, as0runtime.Artifact(), "AS0ArtifactStore")
	_, zi0ABI, zi0Init, zi0Runtime := zi0TestLoadArtifact(t, Artifact(), "ZI0ZipIndex")
	st, err := state.New(types.EmptyRootHash, state.NewDatabaseForTesting())
	if err != nil {
		t.Fatal(err)
	}

	as0Args, err := as0ABI.Pack("", uint32(len(fixture.raw)))
	if err != nil {
		t.Fatal(err)
	}
	as0Output, as0Address, as0Left, err := evmruntime.Create(append(append([]byte(nil), as0Init...), as0Args...), zi0TestConfig(st, zi0TestOwner, zi0TestGas))
	if err != nil || !bytes.Equal(as0Output, as0Runtime) || !bytes.Equal(st.GetCode(as0Address), as0Runtime) {
		t.Fatalf("ordinary AS0 CREATE failed after %d gas: %v", zi0TestGas-as0Left, err)
	}

	pageCommitment := zi0TestHash(t,
		[]string{"bytes32", "address", "uint32", "uint32", "bytes32"},
		crypto.Keccak256Hash([]byte("MC-AS0/page/v1")), as0Address, uint32(0), uint32(len(fixture.raw)), crypto.Keccak256Hash(fixture.raw),
	)
	_, appendGas := zi0TestCall(t, st, as0Address, as0ABI, "append", uint32(0), fixture.raw, pageCommitment)
	pageAddress := crypto.CreateAddress(as0Address, 1)
	if want := append([]byte{0}, fixture.raw...); !bytes.Equal(st.GetCode(pageAddress), want) {
		t.Fatal("AS0 page was not installed through ordinary child CREATE")
	}
	chain := zi0TestGetter[[32]byte](t, st, as0Address, as0ABI, "chainCommitment")
	_, sealGas := zi0TestCall(t, st, as0Address, as0ABI, "seal", uint32(len(fixture.raw)), chain)
	contentArray := zi0TestGetter[[32]byte](t, st, as0Address, as0ABI, "contentCommitment")
	content := common.Hash(contentArray)

	zi0Args, err := zi0ABI.Pack("", as0Address, content)
	if err != nil {
		t.Fatal(err)
	}
	zi0Output, zi0Address, zi0Left, err := evmruntime.Create(append(append([]byte(nil), zi0Init...), zi0Args...), zi0TestConfig(st, zi0TestOwner, zi0TestGas))
	if err != nil || !bytes.Equal(zi0Output, zi0Runtime) || !bytes.Equal(st.GetCode(zi0Address), zi0Runtime) {
		t.Fatalf("ordinary ZI0 CREATE failed after %d gas: %v output=0x%x", zi0TestGas-zi0Left, err, zi0Output)
	}

	// A valid dependency must not weaken the constructor's first zero-owner guard.
	zeroState := st.Copy()
	zeroOutput, _, _, zeroErr := evmruntime.Create(append(append([]byte(nil), zi0Init...), zi0Args...), zi0TestConfig(zeroState, common.Address{}, zi0TestGas))
	definition := zi0ABI.Errors["ZI0Error"]
	if zeroErr == nil || len(zeroOutput) != 36 || !bytes.Equal(zeroOutput[:4], definition.ID[:4]) || new(big.Int).SetBytes(zeroOutput[4:]).Uint64() != 1 {
		t.Fatalf("zero-owner constructor did not return exact ZI0Error(1): output=0x%x err=%v", zeroOutput, zeroErr)
	}

	_, discoverGas := zi0TestCall(t, st, zi0Address, zi0ABI, "discover")
	if discoverGas == 0 || zi0TestGetter[uint8](t, st, zi0Address, zi0ABI, "phase") != 1 || zi0TestGetter[uint32](t, st, zi0Address, zi0ABI, "eocd") != fixture.eocd || zi0TestGetter[uint32](t, st, zi0Address, zi0ABI, "cdOffset") != fixture.central || zi0TestGetter[uint32](t, st, zi0Address, zi0ABI, "cdSize") != fixture.centralSize || zi0TestGetter[uint32](t, st, zi0Address, zi0ABI, "count") != uint32(len(fixture.entries)) {
		t.Fatal("discover getters differ from EVM ZIP geometry")
	}
	zi0TestErrorCall(t, st, zi0TestOwner, zi0Address, zi0ABI, "entry", 30, uint32(0))

	as0CodeHash := common.HexToHash("c8cec283e80fd82b15254bd50a9f2aea3a91305ba71f756f834439280600f896")
	scanGas := make([]uint64, 0, len(fixture.entries))
	root := zi0TestHash(t,
		[]string{"bytes32", "address", "address", "address", "bytes32", "bytes32", "uint32", "uint32", "uint32", "uint32", "uint32"},
		crypto.Keccak256Hash([]byte("MC-ZI0/index/v1")), zi0Address, zi0TestOwner, as0Address, as0CodeHash, content,
		uint32(len(fixture.raw)), fixture.eocd, fixture.central, fixture.centralSize, uint32(len(fixture.entries)),
	)
	if got := common.Hash(zi0TestGetter[[32]byte](t, st, zi0Address, zi0ABI, "rolling")); got != root {
		t.Fatalf("initial root=%s want %s", got, root)
	}

	cursor := fixture.central
	for i, entry := range fixture.entries {
		_, used := zi0TestCall(t, st, zi0Address, zi0ABI, "scan", uint32(i), cursor, root, uint16(1))
		scanGas = append(scanGas, used)
		root = zi0TestHash(t,
			[]string{"bytes32", "bytes32", "uint32", "bytes32", "uint16", "uint16", "uint16", "uint32", "uint32", "uint32", "uint32", "uint32", "uint32", "uint32", "uint32"},
			crypto.Keccak256Hash([]byte("MC-ZI0/entry/v1")), root, uint32(i), crypto.Keccak256Hash(entry.name), uint16(len(entry.name)), entry.flags, entry.method,
			entry.crc, uint32(len(entry.compressed)), uint32(len(entry.plain)), entry.local, entry.dataStart, entry.dataStart+uint32(len(entry.compressed)), entry.recordEnd, entry.centralEnd,
		)
		cursor = entry.centralEnd
		if got := common.Hash(zi0TestGetter[[32]byte](t, st, zi0Address, zi0ABI, "rolling")); got != root {
			t.Fatalf("rolling after %d=%s want %s", i, got, root)
		}
	}
	if cursor != fixture.eocd {
		t.Fatalf("central cursor=%d eocd=%d", cursor, fixture.eocd)
	}

	// Correct CAS at EOF is forbidden rather than accepted as a no-op.
	zi0TestErrorCall(t, st, zi0TestOwner, zi0Address, zi0ABI, "scan", 11, uint32(len(fixture.entries)), cursor, root, uint16(1))
	zi0TestErrorCall(t, st, zi0TestOwner, zi0Address, zi0ABI, "scan", 11, uint32(len(fixture.entries)), cursor, root, uint16(0))
	if zi0TestGetter[uint32](t, st, zi0Address, zi0ABI, "nextEntry") != uint32(len(fixture.entries)) || common.Hash(zi0TestGetter[[32]byte](t, st, zi0Address, zi0ABI, "finalRoot")) != (common.Hash{}) {
		t.Fatal("failed EOF scan changed staging authority or prematurely published root")
	}

	_, finishGas := zi0TestCall(t, st, zi0Address, zi0ABI, "finish", uint32(len(fixture.entries)), cursor, root)
	if zi0TestGetter[uint8](t, st, zi0Address, zi0ABI, "phase") != 2 || common.Hash(zi0TestGetter[[32]byte](t, st, zi0Address, zi0ABI, "finalRoot")) != root {
		t.Fatal("finish did not publish exact rolling root")
	}

	for i, entry := range fixture.entries {
		values, _ := zi0TestCall(t, st, zi0Address, zi0ABI, "entry", uint32(i))
		if !bytes.Equal(values[0].([]byte), entry.name) {
			t.Fatalf("entry %d raw name differs: 0x%x", i, values[0])
		}
		packed := common.Hash(values[1].([32]byte))
		wantPacked := new(big.Int).SetUint64(uint64(fixture.central))
		namePosition := uint32(fixture.central)
		if i != 0 {
			namePosition = fixture.entries[i-1].centralEnd
		}
		namePosition += 46
		wantPacked.SetUint64(uint64(namePosition))
		fields := []struct {
			value uint64
			shift uint
		}{
			{uint64(entry.local), 25}, {uint64(entry.dataStart), 50}, {uint64(len(entry.compressed)), 75},
			{uint64(len(entry.plain)), 100}, {uint64(entry.crc), 132}, {uint64(len(entry.name)), 164},
			{uint64(entry.flags), 173}, {uint64(entry.method), 189}, {uint64(entry.descriptor), 193},
		}
		for _, field := range fields {
			term := new(big.Int).Lsh(new(big.Int).SetUint64(field.value), field.shift)
			wantPacked.Or(wantPacked, term)
		}
		if packed != common.BigToHash(wantPacked) {
			t.Fatalf("entry %d packed=%s want %s", i, packed, common.BigToHash(wantPacked))
		}
		lookup, _ := zi0TestCall(t, st, zi0Address, zi0ABI, "lookup", entry.name)
		if !lookup[0].(bool) || lookup[1].(uint32) != uint32(i) || common.Hash(lookup[2].([32]byte)) != packed {
			t.Fatalf("lookup %d differs: %+v", i, lookup)
		}
	}
	missing, _ := zi0TestCall(t, st, zi0Address, zi0ABI, "lookup", []byte("missing"))
	if missing[0].(bool) || missing[1].(uint32) != 0 || common.Hash(missing[2].([32]byte)) != (common.Hash{}) {
		t.Fatalf("missing lookup differs: %+v", missing)
	}
	t.Logf("final artifact gas: as0_create=%d append=%d seal=%d zi0_create=%d discover=%d scan_q1=%v finish=%d root=%s", zi0TestGas-as0Left, appendGas, sealGas, zi0TestGas-zi0Left, discoverGas, scanGas, finishGas, root)
}
