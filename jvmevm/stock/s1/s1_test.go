package s1

import (
	"bytes"
	"context"
	"crypto/ecdsa"
	"crypto/sha256"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"math/big"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"sort"
	"strconv"
	"strings"
	"testing"
	"time"

	"github.com/ethereum/go-ethereum"
	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core"
	"github.com/ethereum/go-ethereum/core/rawdb"
	"github.com/ethereum/go-ethereum/core/state"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/core/vm"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/eth/ethconfig"
	"github.com/ethereum/go-ethereum/ethclient/simulated"
	jvmevm "github.com/ethereum/go-ethereum/jvmevm"
	"github.com/ethereum/go-ethereum/jvmevm/stock"
	"github.com/ethereum/go-ethereum/node"
	"github.com/ethereum/go-ethereum/p2p"
	"github.com/ethereum/go-ethereum/params"
	"github.com/ethereum/go-ethereum/triedb"
)

const (
	stockS1HarnessChainID       = uint64(1337)
	stockS1HarnessBlockGas      = uint64(30_000_000)
	stockS1HarnessCreateGas     = uint64(8_000_000)
	stockS1HarnessResumeGas     = uint64(2_000_000)
	stockS1HarnessMaxTotalSteps = uint64(1024)
	stockS1HarnessSourceRoot    = "../../testdata/differential"
	stockS1HarnessCataloguePath = "../../testdata/stock/s1/catalogue.json"
	stockS1HarnessTestKeyHex    = "2cfb1db9f8e9a812561a042fc460a41fbc36ee90ba938589a94eb5ad4b632108"
	stockS1HarnessCatalogueRoot = "0xf98038bd7cb12d165c0b22dd7feca869803efce86a8194f4a3ddb1973f84764b"
)

var (
	stockS1HarnessFeeCap = new(big.Int).Mul(big.NewInt(100), big.NewInt(params.GWei))
	stockS1HarnessTipCap = new(big.Int).SetUint64(params.GWei)
)

type stockS1HarnessCatalogue struct {
	Schema               uint32                         `json:"schema"`
	CatalogueCount       uint16                         `json:"catalogueCount"`
	CatalogueRoot        string                         `json:"catalogueRoot"`
	LegacyManifestSHA256 string                         `json:"legacyManifestSha256"`
	CompilerCommand      []string                       `json:"compilerCommand"`
	CompilerUsedToPin    string                         `json:"compilerUsedToPin"`
	Java8UsedToPin       string                         `json:"java8UsedToPin"`
	Java21UsedToPin      string                         `json:"java21UsedToPin"`
	Classes              []stockS1HarnessCatalogueClass `json:"classes"`
	Cases                []stockS1HarnessCase           `json:"cases"`
}

type stockS1HarnessCatalogueClass struct {
	Name           string `json:"name"`
	Source         string `json:"source"`
	SourceSHA256   string `json:"sourceSha256"`
	ClassSHA256    string `json:"classSha256"`
	ClassBytes     int    `json:"classBytes"`
	RawPayloadHash string `json:"rawPayloadHash"`
}

type stockS1HarnessCase struct {
	Index          uint16  `json:"index"`
	ID             string  `json:"id"`
	Stage          string  `json:"stage"`
	Class          string  `json:"class"`
	Entry          string  `json:"entry"`
	Descriptor     string  `json:"descriptor"`
	Args           []int32 `json:"args"`
	ArgsHash       string  `json:"argsHash"`
	LegacyGasLimit uint64  `json:"legacyGasLimit"`
	Expected       int32   `json:"expected"`
	Steps          uint64  `json:"steps"`
	PC             uint32  `json:"pc"`
	Initialized    uint8   `json:"initialized"`
	Locals         []int32 `json:"locals"`
	MaxStack       uint8   `json:"maxStack"`
	MaxLocals      uint8   `json:"maxLocals"`
	CodeLength     uint16  `json:"codeLength"`
	MethodIndex    uint16  `json:"methodIndex"`
	Leaf           string  `json:"leaf"`
}

type stockS1HarnessLegacyManifest struct {
	Schema uint64                     `json:"schema_version"`
	Cases  []stockS1HarnessLegacyCase `json:"cases"`
}

type stockS1HarnessLegacyCase struct {
	ID           string   `json:"id"`
	Stage        string   `json:"stage"`
	Sources      []string `json:"sources"`
	Class        string   `json:"class"`
	Method       string   `json:"method"`
	Args         []int32  `json:"args"`
	GasLimit     uint64   `json:"gas_limit"`
	ExpectedKind string   `json:"expected_kind"`
}

type stockS1HarnessMethod struct {
	Index      uint16
	Name       string
	Descriptor string
	Access     uint16
	CodeOffset uint32
	MaxStack   uint8
	MaxLocals  uint8
	Code       []byte
}

type stockS1HarnessClass struct {
	Name    string
	Raw     []byte
	Methods []stockS1HarnessMethod
}

type stockS1HarnessMachine struct {
	PC          uint32      `abi:"pc"`
	SP          uint8       `abi:"sp"`
	Initialized uint8       `abi:"initialized"`
	Lifecycle   uint8       `abi:"lifecycle"`
	Stack       [8]*big.Int `abi:"stack"`
	Locals      [8]*big.Int `abi:"locals"`
	Result      int32       `abi:"result"`
}

type stockS1HarnessCheckpoint struct {
	Schema      uint32
	ClassID     [32]byte
	ProgramID   [32]byte
	InputRoot   [32]byte
	Epoch       uint64
	TotalSteps  uint64
	StateDigest [32]byte
	Machine     stockS1HarnessMachine
}

type stockS1HarnessProgramContext struct {
	Parser         common.Address `abi:"parser"`
	ParserCodeHash [32]byte       `abi:"parserCodeHash"`
	ClassID        [32]byte       `abi:"classId"`
	RawPage        common.Address `abi:"rawPage"`
	RawPageHash    [32]byte       `abi:"rawPageHash"`
	PayloadHash    [32]byte       `abi:"payloadHash"`
	MetadataPage   common.Address `abi:"metadataPage"`
	MetadataHash   [32]byte       `abi:"metadataHash"`
	MethodIndex    uint16         `abi:"methodIndex"`
	ProgramID      [32]byte       `abi:"programId"`
}

type stockS1HarnessEvent struct {
	Epoch       uint64
	ProgramID   [32]byte
	TotalSteps  uint64   `abi:"totalSteps"`
	PC          uint32   `abi:"pc"`
	SP          uint8    `abi:"sp"`
	Lifecycle   uint8    `abi:"lifecycle"`
	Result      int32    `abi:"result"`
	Executed    uint16   `abi:"executed"`
	DirtyWords  uint8    `abi:"dirtyWords"`
	StateDigest [32]byte `abi:"stateDigest"`
}

type stockS1HarnessClassDeployment struct {
	Class           stockS1HarnessClass
	Page            common.Address
	PageHash        common.Hash
	PayloadHash     common.Hash
	MetadataPage    common.Address
	MetadataHash    common.Hash
	ClassID         common.Hash
	DeclaredMethods uint16
	PageGas         uint64
	RegisterGas     uint64
}

type stockS1HarnessTxRecord struct {
	Kind    string
	Tx      *types.Transaction
	Header  *types.Header
	Receipt *types.Receipt
}

type stockS1HarnessCaseRun struct {
	Case        stockS1HarnessCase
	Budget      uint16
	Coordinator common.Address
	Checkpoint  stockS1HarnessCheckpoint
	Resumes     int
	Gas         uint64
	SamePC      int
}

type stockS1HarnessEnvironment struct {
	Backend            *simulated.Backend
	Key                *ecdsa.PrivateKey
	Sender             common.Address
	Nonce              uint64
	Parser             common.Address
	Module             common.Address
	ParserHash         common.Hash
	ModuleHash         common.Hash
	ParserDeployGas    uint64
	ModuleDeployGas    uint64
	Classes            map[string]stockS1HarnessClassDeployment
	Records            []stockS1HarnessTxRecord
	Runs               []stockS1HarnessCaseRun
	SharedSetupRecords int
}

func TestStockS1HarnessArtifactLoader(t *testing.T) {
	for _, name := range []string{S1MetadataPage, S1ClassParser, S1StepModule, S1Coordinator} {
		artifact, err := LoadArtifact(name)
		if err != nil {
			t.Fatalf("required runtime artifact dependency %s: %v", name, err)
		}
		if len(artifact.InitCode) == 0 || len(artifact.RuntimeCode) == 0 {
			t.Fatalf("%s contains empty code", name)
		}
	}
	if _, err := LoadArtifact("not-a-stock-s1-artifact"); err == nil {
		t.Fatal("unknown S1 artifact unexpectedly loaded")
	}
	if _, err := LoadArtifact(stock.ArtifactPage); err == nil {
		t.Fatal("S0 ArtifactPage unexpectedly accepted by the S1 loader")
	}
	if _, err := stock.LoadArtifact(stock.ArtifactPage); err != nil {
		t.Fatalf("accepted S0 ArtifactPage dependency: %v", err)
	}
}

func TestStockS1HarnessCatalogueJVM8JVM21MonolithAndBoundedTrace(t *testing.T) {
	catalogue, classes, output := stockS1HarnessLoadAndCompile(t)
	legacy := stockS1HarnessReadLegacy(t)
	stockS1HarnessCheckCatalogueEncoding(t, catalogue, classes, legacy)

	java8 := "/usr/lib/jvm/java-8-openjdk/bin/java"
	if _, err := os.Stat(java8); err != nil {
		t.Fatalf("Java 8 oracle missing: %v", err)
	}
	java21, err := exec.LookPath("java")
	if err != nil {
		t.Fatalf("Java 21 oracle missing: %v", err)
	}
	var totalSteps uint64
	programs := make(map[string]bool)
	for _, tc := range catalogue.Cases {
		guest := classes[tc.Class]
		method := stockS1HarnessMethodNamed(t, guest, tc.Entry)
		machine, steps := stockS1HarnessTrace(t, method, tc.Args, 100_000)
		if steps != tc.Steps || machine.PC != tc.PC || machine.Lifecycle != 1 || machine.Result != tc.Expected || machine.Initialized != tc.Initialized {
			t.Fatalf("%s pinned trace mismatch steps=%d machine=%+v", tc.ID, steps, machine)
		}
		stockS1HarnessAssertCatalogueLocals(t, tc, machine)
		for _, java := range []string{java8, java21} {
			args := []string{"-Xmx64m", "-Xss512k", "-Xverify:all", "-cp", output, "OracleMain", tc.Class, tc.Entry}
			for _, value := range tc.Args {
				args = append(args, strconv.FormatInt(int64(value), 10))
			}
			text := stockS1HarnessCommand(t, 30*time.Second, java, args...)
			if text != fmt.Sprintf("value=%d", tc.Expected) {
				t.Fatalf("%s JVM %s got %q want value=%d", tc.ID, java, text, tc.Expected)
			}
		}
		monolith, err := jvmevm.Run(guest.Raw, tc.Entry, tc.Args, tc.LegacyGasLimit)
		if err != nil || monolith.ExceptionClass != "" || monolith.Value != tc.Expected {
			t.Fatalf("%s monolith got value=%d exception=%q gas=%d err=%v, want %d", tc.ID, monolith.Value, monolith.ExceptionClass, monolith.GasUsed, err, tc.Expected)
		}
		totalSteps += steps
		programs[tc.Class+"\x00"+tc.Entry] = true
	}
	if totalSteps != 2213 || len(programs) != 39 {
		t.Fatalf("catalogue totals steps=%d programs=%d, want 2213/39", totalSteps, len(programs))
	}
	monolithHash := stockS1HarnessMonolithHash(t)
	// Preserve the original stock-stage oracle pin; explicitly admit the
	// parent-reviewed MC-LB0 monolith only after the same unchanged catalogue
	// comparisons above. This does not change stock artifacts or gas budgets.
	if monolithHash != "dfc81dbbea8253c644be2532a809a417bb40cd07eaca8ab5be72a84721eae929" &&
		monolithHash != "ff9c9ff093e9d4885d7546e01db7aacd95cf999d5cf9b6d6b130fd43b791b982" {
		t.Fatalf("monolith TEST oracle runtime SHA-256=%s", monolithHash)
	}
	t.Logf("actual oracles agree: catalogue=%d programs=%d instructions=%d javac=%s java8=%s java21=%s monolithRuntime=%s", len(catalogue.Cases), len(programs), totalSteps, catalogue.CompilerUsedToPin, catalogue.Java8UsedToPin, catalogue.Java21UsedToPin, monolithHash)
}

func TestStockS1HarnessSignedAll82ReuseBudgetsPrefixesAndDirectReplay(t *testing.T) {
	if testing.Short() {
		t.Skip("signed Stock S1 all-82 deployment/replay gate")
	}
	catalogue, classes, _ := stockS1HarnessLoadAndCompile(t)
	env := stockS1HarnessNewEnvironment(t, classes)
	defer env.close(t)
	if env.SharedSetupRecords != 12 {
		t.Fatalf("shared setup external transactions=%d want exactly 12", env.SharedSetupRecords)
	}

	programs := make(map[common.Hash]bool)
	inputs := make(map[common.Hash]bool)
	for _, budget := range []uint16{64, 128} {
		for _, tc := range catalogue.Cases {
			run := stockS1HarnessRunCase(t, env, tc, budget, 0)
			stockS1HarnessAssertCaseBounds(t, env, run, true)
			programs[common.Hash(run.Checkpoint.ProgramID)] = true
			inputs[common.Hash(run.Checkpoint.InputRoot)] = true
		}
	}
	if len(programs) != 39 || len(inputs) != 82 {
		t.Fatalf("on-chain commitments programs=%d inputs=%d want 39/82", len(programs), len(inputs))
	}

	// Every non-loop row is also complete at the three frozen small budgets.
	for _, budget := range []uint16{1, 7, 16} {
		for _, tc := range catalogue.Cases {
			if stockS1HarnessLongLoop(tc) {
				continue
			}
			run := stockS1HarnessRunCase(t, env, tc, budget, 0)
			stockS1HarnessAssertCaseBounds(t, env, run, true)
		}
	}
	// Loop rows use bounded prefixes at small quanta; their complete executions
	// above at 64/128 remain the terminal-value evidence.
	for _, budget := range []uint16{1, 7, 16} {
		for _, tc := range catalogue.Cases {
			if !stockS1HarnessLongLoop(tc) {
				continue
			}
			stockS1HarnessRunCase(t, env, tc, budget, 4)
		}
	}
	sum64, sum16 := -1, -1
	for _, run := range env.Runs {
		if run.Case.ID == "m2-sum-100" && run.Budget == 64 && run.Checkpoint.Machine.Lifecycle == 1 {
			sum64 = run.SamePC
		}
		if run.Case.ID == "m2-sum-100" && run.Budget == 16 && run.Resumes == 4 {
			sum16 = run.SamePC
		}
	}
	if sum64 != 11 || sum16 != 3 {
		t.Fatalf("genuine same-PC progress counts sum64=%d want11 sum16prefix=%d want3", sum64, sum16)
	}

	first := stockS1HarnessReplayDirect(t, env)
	second := stockS1HarnessReplayDirect(t, env)
	if first.Root != second.Root || !reflect.DeepEqual(first.Gas, second.Gas) || !reflect.DeepEqual(first.Checkpoints, second.Checkpoints) {
		t.Fatal("identical signed TransactionToMessage replay contexts changed roots, gas, or VM checkpoints")
	}
	if !reflect.DeepEqual(first.Gas, stockS1HarnessReceiptGas(env.Records)) {
		t.Fatal("direct replay gas differs from signed in-process receipts")
	}

	var sharedGas uint64
	for _, r := range env.Records[:env.SharedSetupRecords] {
		sharedGas += r.Receipt.GasUsed
	}
	firstHeader, lastHeader := env.Records[0].Header, env.Records[len(env.Records)-1].Header
	gasByKind, txByKind := stockS1HarnessGasAccounting(env.Records)
	t.Logf("Stock S1 measurements catalogue=%d programs=%d inputs=%d sharedSetupTx=%d sharedSetupGas=%d allSignedTx=%d allSignedGas=%d failedTx=0 failedGas=0 gasByKind=%v txByKind=%v directRoot=%s signedWallTimeHeaders(first=%s/root=%s/time=%d last=%s/root=%s/time=%d; intentionally not compared as global roots)", len(catalogue.Cases), len(programs), len(inputs), env.SharedSetupRecords, sharedGas, len(env.Records), stockS1HarnessSumGas(env.Records), gasByKind, txByKind, first.Root, firstHeader.Hash(), firstHeader.Root, firstHeader.Time, lastHeader.Hash(), lastHeader.Root, lastHeader.Time)
}

func stockS1HarnessLoadAndCompile(t *testing.T) (stockS1HarnessCatalogue, map[string]stockS1HarnessClass, string) {
	t.Helper()
	raw, err := os.ReadFile(stockS1HarnessCataloguePath)
	if err != nil {
		t.Fatal(err)
	}
	var catalogue stockS1HarnessCatalogue
	if err := json.Unmarshal(raw, &catalogue); err != nil {
		t.Fatal(err)
	}
	if catalogue.Schema != 2 || catalogue.CatalogueCount != 82 || len(catalogue.Cases) != 82 || catalogue.CatalogueRoot != stockS1HarnessCatalogueRoot {
		t.Fatalf("invalid pinned catalogue schema=%d count=%d rows=%d root=%s", catalogue.Schema, catalogue.CatalogueCount, len(catalogue.Cases), catalogue.CatalogueRoot)
	}
	javac, err := exec.LookPath("javac")
	if err != nil {
		t.Fatalf("trusted fixture regeneration requires javac: %v", err)
	}
	output := t.TempDir()
	args := []string{"--release", "8", "-d", output, filepath.Join(stockS1HarnessSourceRoot, "OracleMain.java")}
	for _, class := range catalogue.Classes {
		args = append(args, filepath.Join(stockS1HarnessSourceRoot, class.Source))
	}
	stockS1HarnessCommand(t, time.Minute, javac, args...)
	classes := make(map[string]stockS1HarnessClass, len(catalogue.Classes))
	for _, pin := range catalogue.Classes {
		source, err := os.ReadFile(filepath.Join(stockS1HarnessSourceRoot, pin.Source))
		if err != nil {
			t.Fatal(err)
		}
		if got := fmt.Sprintf("%x", sha256.Sum256(source)); got != pin.SourceSHA256 {
			t.Fatalf("%s source SHA-256 got %s want %s", pin.Name, got, pin.SourceSHA256)
		}
		classfile, err := os.ReadFile(filepath.Join(output, pin.Name+".class"))
		if err != nil {
			t.Fatal(err)
		}
		if len(classfile) != pin.ClassBytes || fmt.Sprintf("%x", sha256.Sum256(classfile)) != pin.ClassSHA256 || crypto.Keccak256Hash(classfile).Hex() != pin.RawPayloadHash {
			t.Fatalf("%s default-debug javac --release 8 identity mismatch bytes=%d sha256=%x keccak=%s", pin.Name, len(classfile), sha256.Sum256(classfile), crypto.Keccak256Hash(classfile))
		}
		parsed := stockS1HarnessParseClass(t, classfile)
		if parsed.Name != pin.Name {
			t.Fatalf("parsed binary name %q want %q", parsed.Name, pin.Name)
		}
		classes[pin.Name] = parsed
	}
	return catalogue, classes, output
}

func stockS1HarnessReadLegacy(t *testing.T) []stockS1HarnessLegacyCase {
	t.Helper()
	path := filepath.Join(stockS1HarnessSourceRoot, "cases.json")
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	var manifest stockS1HarnessLegacyManifest
	if err := json.Unmarshal(raw, &manifest); err != nil {
		t.Fatal(err)
	}
	if manifest.Schema != 1 {
		t.Fatalf("legacy manifest schema=%d", manifest.Schema)
	}
	var selected []stockS1HarnessLegacyCase
	for _, row := range manifest.Cases {
		if row.Stage == "m1" || row.Stage == "m2" {
			selected = append(selected, row)
		}
	}
	if len(selected) != 82 {
		t.Fatalf("legacy M1/M2 rows=%d want 82", len(selected))
	}
	return selected
}

func stockS1HarnessCheckCatalogueEncoding(t *testing.T, catalogue stockS1HarnessCatalogue, classes map[string]stockS1HarnessClass, legacy []stockS1HarnessLegacyCase) {
	t.Helper()
	manifest, err := os.ReadFile(filepath.Join(stockS1HarnessSourceRoot, "cases.json"))
	if err != nil {
		t.Fatal(err)
	}
	if got := fmt.Sprintf("%x", sha256.Sum256(manifest)); got != catalogue.LegacyManifestSHA256 {
		t.Fatalf("legacy manifest SHA-256 got %s want %s", got, catalogue.LegacyManifestSHA256)
	}
	leaves := make([][32]byte, len(catalogue.Cases))
	seen := make(map[string]bool)
	for i, tc := range catalogue.Cases {
		old := legacy[i]
		if int(tc.Index) != i || seen[tc.ID] || tc.ID != old.ID || tc.Stage != old.Stage || tc.Class != old.Class || tc.Entry != old.Method || !reflect.DeepEqual(tc.Args, old.Args) || tc.LegacyGasLimit != old.GasLimit || old.ExpectedKind != "value" || len(old.Sources) != 1 || old.Sources[0] != tc.Class+".java" {
			t.Fatalf("catalogue row %d does not preserve the ordered legacy row: new=%+v old=%+v", i, tc, old)
		}
		seen[tc.ID] = true
		if tc.Descriptor != stockS1HarnessDescriptor(len(tc.Args)) || len(tc.Args) > 4 || len(tc.Locals) != 8 {
			t.Fatalf("%s invalid descriptor/argument/local catalogue fields", tc.ID)
		}
		method := stockS1HarnessMethodNamed(t, classes[tc.Class], tc.Entry)
		if method.Index != tc.MethodIndex || uint16(len(method.Code)) != tc.CodeLength || method.MaxStack != tc.MaxStack || method.MaxLocals != tc.MaxLocals {
			t.Fatalf("%s selected method metadata differs from raw class", tc.ID)
		}
		argsHash := stockS1HarnessArgsHash(t, tc.Args)
		if argsHash.Hex() != tc.ArgsHash {
			t.Fatalf("%s args hash got %s want %s", tc.ID, argsHash, tc.ArgsHash)
		}
		payloadHash := crypto.Keccak256Hash(classes[tc.Class].Raw)
		encoded := stockS1HarnessABIPack(t,
			[]string{"uint32", "uint16", "bytes32", "bytes32", "bytes32", "bytes32", "bytes32", "bytes32"},
			uint32(2), uint16(i), crypto.Keccak256Hash([]byte(tc.ID)), payloadHash,
			crypto.Keccak256Hash([]byte(tc.Class)), crypto.Keccak256Hash([]byte(tc.Entry)),
			crypto.Keccak256Hash([]byte(tc.Descriptor)), argsHash)
		leaf := crypto.Keccak256Hash(encoded)
		if leaf.Hex() != tc.Leaf {
			t.Fatalf("%s leaf got %s want %s", tc.ID, leaf, tc.Leaf)
		}
		leaves[i] = leaf
	}
	root := crypto.Keccak256Hash(stockS1HarnessABIPack(t, []string{"uint32", "uint16", "bytes32[]"}, uint32(2), uint16(82), leaves))
	if root.Hex() != catalogue.CatalogueRoot || root.Hex() != stockS1HarnessCatalogueRoot {
		t.Fatalf("ordered catalogue root got %s want %s", root, catalogue.CatalogueRoot)
	}
}

func stockS1HarnessDescriptor(argc int) string {
	return "(" + strings.Repeat("I", argc) + ")I"
}

func stockS1HarnessCommand(t *testing.T, timeout time.Duration, command string, args ...string) string {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	output, err := exec.CommandContext(ctx, command, args...).CombinedOutput()
	if err != nil {
		t.Fatalf("%s %s: %v\n%s", command, strings.Join(args, " "), err, output)
	}
	return strings.TrimSpace(string(output))
}

func stockS1HarnessMonolithHash(t *testing.T) string {
	t.Helper()
	hash, err := jvmevm.RuntimeHash()
	if err != nil {
		t.Fatal(err)
	}
	return hash
}

func stockS1HarnessMethodNamed(t *testing.T, class stockS1HarnessClass, name string) stockS1HarnessMethod {
	t.Helper()
	var found *stockS1HarnessMethod
	for i := range class.Methods {
		if class.Methods[i].Name == name {
			if found != nil {
				t.Fatalf("ambiguous TEST-only method lookup %s.%s", class.Name, name)
			}
			copy := class.Methods[i]
			found = &copy
		}
	}
	if found == nil {
		t.Fatalf("TEST-only method lookup missing %s.%s", class.Name, name)
	}
	return *found
}

func stockS1HarnessParseClass(t *testing.T, raw []byte) stockS1HarnessClass {
	t.Helper()
	fail := func(format string, args ...interface{}) {
		t.Helper()
		t.Fatalf("TEST-only trusted class parser: "+format, args...)
	}
	if len(raw) < 10 || binary.BigEndian.Uint32(raw[:4]) != 0xcafebabe {
		fail("bad header")
	}
	p := 8
	readU1 := func() byte {
		if p >= len(raw) {
			fail("truncated u1 at %d", p)
			return 0
		}
		v := raw[p]
		p++
		return v
	}
	readU2 := func() uint16 {
		if p+2 > len(raw) {
			fail("truncated u2 at %d", p)
			return 0
		}
		v := binary.BigEndian.Uint16(raw[p : p+2])
		p += 2
		return v
	}
	readU4 := func() uint32 {
		if p+4 > len(raw) {
			fail("truncated u4 at %d", p)
			return 0
		}
		v := binary.BigEndian.Uint32(raw[p : p+4])
		p += 4
		return v
	}
	cpCount := readU2()
	utf8 := make([]string, cpCount)
	className := make([]uint16, cpCount)
	for i := uint16(1); i < cpCount; i++ {
		tag := readU1()
		switch tag {
		case 1:
			n := int(readU2())
			if p+n > len(raw) {
				fail("truncated UTF8")
			}
			utf8[i] = string(raw[p : p+n])
			p += n
		case 3, 4:
			p += 4
		case 5, 6:
			p += 8
			i++
		case 7:
			className[i] = readU2()
		case 8, 16, 19, 20:
			p += 2
		case 9, 10, 11, 12, 17, 18:
			p += 4
		case 15:
			p += 3
		default:
			fail("unsupported CP tag %d", tag)
		}
		if p > len(raw) {
			fail("truncated CP")
		}
	}
	_ = readU2()
	thisClass := readU2()
	_ = readU2()
	if int(thisClass) >= len(className) || int(className[thisClass]) >= len(utf8) {
		fail("bad this_class")
	}
	result := stockS1HarnessClass{Name: utf8[className[thisClass]], Raw: append([]byte(nil), raw...)}
	interfaces := int(readU2())
	p += interfaces * 2
	readAttributes := func() []struct {
		name          string
		start, length int
	} {
		return nil
	}
	_ = readAttributes
	var skipAttributes func() []struct {
		name          string
		start, length int
	}
	skipAttributes = func() []struct {
		name          string
		start, length int
	} {
		count := int(readU2())
		out := make([]struct {
			name          string
			start, length int
		}, 0, count)
		for i := 0; i < count; i++ {
			nameIndex := readU2()
			length := int(readU4())
			start := p
			if int(nameIndex) >= len(utf8) || p+length > len(raw) {
				fail("bad attribute")
			}
			out = append(out, struct {
				name          string
				start, length int
			}{utf8[nameIndex], start, length})
			p += length
		}
		return out
	}
	fields := int(readU2())
	for i := 0; i < fields; i++ {
		p += 6
		skipAttributes()
	}
	methodCount := int(readU2())
	for i := 0; i < methodCount; i++ {
		access, nameIndex, descriptorIndex := readU2(), readU2(), readU2()
		attrs := skipAttributes()
		method := stockS1HarnessMethod{Index: uint16(i), Name: utf8[nameIndex], Descriptor: utf8[descriptorIndex], Access: access}
		for _, attr := range attrs {
			if attr.name != "Code" {
				continue
			}
			q := p
			p = attr.start
			maxStack, maxLocals, codeLength := readU2(), readU2(), int(readU4())
			if p+codeLength > attr.start+attr.length {
				fail("bad Code")
			}
			method.MaxStack, method.MaxLocals, method.CodeOffset = uint8(maxStack), uint8(maxLocals), uint32(p)
			method.Code = append([]byte(nil), raw[p:p+codeLength]...)
			p = q
		}
		result.Methods = append(result.Methods, method)
	}
	return result
}

func stockS1HarnessZeroMachine() stockS1HarnessMachine {
	machine := stockS1HarnessMachine{}
	for i := range machine.Stack {
		machine.Stack[i] = new(big.Int)
	}
	for i := range machine.Locals {
		machine.Locals[i] = new(big.Int)
	}
	return machine
}

func stockS1HarnessTrace(t *testing.T, method stockS1HarnessMethod, args []int32, limit uint64) (stockS1HarnessMachine, uint64) {
	t.Helper()
	machine := stockS1HarnessZeroMachine()
	for i, value := range args {
		machine.Locals[i] = stockS1HarnessTagged(value)
		machine.Initialized |= 1 << i
	}
	var steps uint64
	for machine.Lifecycle == 0 {
		if steps == limit {
			t.Fatalf("TEST-only bounded trace exceeded %d steps", limit)
		}
		stockS1HarnessTraceOne(t, method, &machine)
		steps++
	}
	return machine, steps
}

func stockS1HarnessTracePrefix(t *testing.T, method stockS1HarnessMethod, args []int32, steps uint64) stockS1HarnessMachine {
	t.Helper()
	machine := stockS1HarnessZeroMachine()
	for i, value := range args {
		machine.Locals[i] = stockS1HarnessTagged(value)
		machine.Initialized |= 1 << i
	}
	for i := uint64(0); i < steps && machine.Lifecycle == 0; i++ {
		stockS1HarnessTraceOne(t, method, &machine)
	}
	return machine
}

func stockS1HarnessTraceOne(t *testing.T, method stockS1HarnessMethod, machine *stockS1HarnessMachine) {
	t.Helper()
	code := method.Code
	pc := int(machine.PC)
	if machine.Lifecycle != 0 || pc < 0 || pc >= len(code) {
		t.Fatalf("TEST trace invalid pc/lifecycle pc=%d lifecycle=%d", pc, machine.Lifecycle)
	}
	push := func(value int32) {
		if machine.SP >= 8 {
			t.Fatal("TEST trace stack overflow")
		}
		machine.Stack[machine.SP] = stockS1HarnessTagged(value)
		machine.SP++
	}
	pop := func() int32 {
		if machine.SP == 0 {
			t.Fatal("TEST trace stack underflow")
		}
		machine.SP--
		cell := machine.Stack[machine.SP]
		machine.Stack[machine.SP] = new(big.Int)
		return int32(uint32(cell.Uint64()))
	}
	load := func(index uint8) {
		if machine.Initialized&(1<<index) == 0 {
			t.Fatal("TEST trace uninitialized local")
		}
		push(int32(uint32(machine.Locals[index].Uint64())))
	}
	store := func(index uint8) {
		machine.Locals[index] = stockS1HarnessTagged(pop())
		machine.Initialized |= 1 << index
	}
	next := func(width int) { machine.PC += uint32(width) }
	signedOffset := func() int32 { return int32(int16(binary.BigEndian.Uint16(code[pc+1 : pc+3]))) }
	op := code[pc]
	switch {
	case op == 0x00:
		next(1)
	case op >= 0x02 && op <= 0x08:
		push(int32(op) - 3)
		next(1)
	case op == 0x10:
		push(int32(int8(code[pc+1])))
		next(2)
	case op == 0x11:
		push(int32(int16(binary.BigEndian.Uint16(code[pc+1 : pc+3]))))
		next(3)
	case op == 0x15:
		load(code[pc+1])
		next(2)
	case op >= 0x1a && op <= 0x1d:
		load(op - 0x1a)
		next(1)
	case op == 0x36:
		store(code[pc+1])
		next(2)
	case op >= 0x3b && op <= 0x3e:
		store(op - 0x3b)
		next(1)
	case op == 0x60:
		right, left := pop(), pop()
		push(int32(uint32(left) + uint32(right)))
		next(1)
	case op == 0x64:
		right, left := pop(), pop()
		push(int32(uint32(left) - uint32(right)))
		next(1)
	case op == 0x68:
		right, left := pop(), pop()
		push(int32(uint32(left) * uint32(right)))
		next(1)
	case op == 0x74:
		value := pop()
		push(int32(0 - uint32(value)))
		next(1)
	case op == 0x84:
		index, delta := code[pc+1], int8(code[pc+2])
		if machine.Initialized&(1<<index) == 0 {
			t.Fatal("TEST trace iinc uninitialized")
		}
		value := int32(uint32(machine.Locals[index].Uint64()))
		machine.Locals[index] = stockS1HarnessTagged(int32(uint32(value) + uint32(int32(delta))))
		next(3)
	case op >= 0x99 && op <= 0x9e:
		value := pop()
		take := []bool{value == 0, value != 0, value < 0, value >= 0, value > 0, value <= 0}[op-0x99]
		if take {
			machine.PC = uint32(int32(pc) + signedOffset())
		} else {
			next(3)
		}
	case op >= 0x9f && op <= 0xa4:
		right, left := pop(), pop()
		take := []bool{left == right, left != right, left < right, left >= right, left > right, left <= right}[op-0x9f]
		if take {
			machine.PC = uint32(int32(pc) + signedOffset())
		} else {
			next(3)
		}
	case op == 0xa7:
		machine.PC = uint32(int32(pc) + signedOffset())
	case op == 0xac:
		if machine.SP != 1 {
			t.Fatalf("TEST trace bad ireturn shape %d", machine.SP)
		}
		machine.Result = pop()
		machine.PC++
		machine.Lifecycle = 1
	default:
		t.Fatalf("TEST trace unsupported opcode 0x%02x at %d", op, pc)
	}
	stockS1HarnessAssertCanonicalMachine(t, *machine)
}

func stockS1HarnessTagged(value int32) *big.Int {
	return new(big.Int).Or(new(big.Int).Lsh(big.NewInt(1), 64), new(big.Int).SetUint64(uint64(uint32(value))))
}

func stockS1HarnessAssertCanonicalMachine(t *testing.T, machine stockS1HarnessMachine) {
	t.Helper()
	if machine.SP > 8 || machine.Initialized&^uint8(0xff) != 0 || machine.Lifecycle > 2 || (machine.Lifecycle != 1 && machine.Result != 0) || (machine.Lifecycle == 1 && machine.SP != 0) {
		t.Fatalf("noncanonical machine scalars %+v", machine)
	}
	for i, cell := range machine.Stack {
		if cell == nil || (i >= int(machine.SP) && cell.Sign() != 0) || (i < int(machine.SP) && !stockS1HarnessCanonicalTag(cell)) {
			t.Fatalf("noncanonical stack[%d]=%v sp=%d", i, cell, machine.SP)
		}
	}
	for i, cell := range machine.Locals {
		if cell == nil || (machine.Initialized&(1<<i) == 0 && cell.Sign() != 0) || (machine.Initialized&(1<<i) != 0 && !stockS1HarnessCanonicalTag(cell)) {
			t.Fatalf("noncanonical local[%d]=%v initialized=%02x", i, cell, machine.Initialized)
		}
	}
}

func stockS1HarnessCanonicalTag(value *big.Int) bool {
	if value.Sign() < 0 || value.BitLen() > 65 || value.Bit(64) != 1 {
		return false
	}
	return value.Cmp(stockS1HarnessTagged(int32(uint32(value.Uint64())))) == 0
}

func stockS1HarnessAssertCatalogueLocals(t *testing.T, tc stockS1HarnessCase, machine stockS1HarnessMachine) {
	t.Helper()
	for i, value := range tc.Locals {
		want := new(big.Int)
		if tc.Initialized&(1<<i) != 0 {
			want = stockS1HarnessTagged(value)
		}
		if machine.Locals[i].Cmp(want) != 0 {
			t.Fatalf("%s local%d got %v want %v", tc.ID, i, machine.Locals[i], want)
		}
	}
}

func stockS1HarnessABIType(t *testing.T, name string) abi.Type {
	t.Helper()
	typ, err := abi.NewType(name, "", nil)
	if err != nil {
		t.Fatal(err)
	}
	return typ
}

func stockS1HarnessABIPack(t *testing.T, types []string, values ...interface{}) []byte {
	t.Helper()
	arguments := make(abi.Arguments, len(types))
	for i, name := range types {
		arguments[i].Type = stockS1HarnessABIType(t, name)
	}
	encoded, err := arguments.Pack(values...)
	if err != nil {
		t.Fatalf("abi.encode %v: %v", types, err)
	}
	return encoded
}

func stockS1HarnessArgsHash(t *testing.T, args []int32) common.Hash {
	t.Helper()
	return crypto.Keccak256Hash(stockS1HarnessABIPack(t, []string{"int32[]"}, args))
}

func stockS1HarnessDomain(label string) common.Hash { return crypto.Keccak256Hash([]byte(label)) }

func stockS1HarnessClassID(t *testing.T, parserHash common.Hash, class stockS1HarnessClassDeployment) common.Hash {
	t.Helper()
	return crypto.Keccak256Hash(stockS1HarnessABIPack(t,
		[]string{"bytes32", "uint32", "bytes32", "address", "bytes32", "bytes32", "bytes32"},
		stockS1HarnessDomain("JVMEVM:S1:CLASS"), uint32(2), parserHash, class.Page, class.PageHash, class.PayloadHash, class.MetadataHash))
}

func stockS1HarnessProgramID(t *testing.T, classID common.Hash, tc stockS1HarnessCase, moduleHash common.Hash) common.Hash {
	t.Helper()
	return crypto.Keccak256Hash(stockS1HarnessABIPack(t,
		[]string{"bytes32", "uint32", "bytes32", "uint16", "bytes32", "bytes32", "bytes32"},
		stockS1HarnessDomain("JVMEVM:S1:PROGRAM"), uint32(2), classID, tc.MethodIndex,
		crypto.Keccak256Hash([]byte(tc.Entry)), crypto.Keccak256Hash([]byte(tc.Descriptor)), moduleHash))
}

func stockS1HarnessInputRoot(t *testing.T, programID, argsHash common.Hash) common.Hash {
	t.Helper()
	return crypto.Keccak256Hash(stockS1HarnessABIPack(t,
		[]string{"bytes32", "bytes32", "bytes32", "uint64"}, stockS1HarnessDomain("JVMEVM:S1:INPUT"), programID, argsHash, stockS1HarnessMaxTotalSteps))
}

func stockS1HarnessStateDigest(t *testing.T, inputRoot, parserHash, moduleHash common.Hash, machine stockS1HarnessMachine, epoch, total uint64) common.Hash {
	t.Helper()
	machineType, err := abi.NewType("tuple", "", []abi.ArgumentMarshaling{
		{Name: "pc", Type: "uint32"}, {Name: "sp", Type: "uint8"}, {Name: "initialized", Type: "uint8"}, {Name: "lifecycle", Type: "uint8"},
		{Name: "stack", Type: "uint256[8]"}, {Name: "locals", Type: "uint256[8]"}, {Name: "result", Type: "int32"},
	})
	if err != nil {
		t.Fatal(err)
	}
	arguments := abi.Arguments{{Type: stockS1HarnessABIType(t, "uint32")}, {Type: stockS1HarnessABIType(t, "bytes32")}, {Type: stockS1HarnessABIType(t, "bytes32")}, {Type: stockS1HarnessABIType(t, "bytes32")}, {Type: machineType}, {Type: stockS1HarnessABIType(t, "uint64")}, {Type: stockS1HarnessABIType(t, "uint64")}}
	encoded, err := arguments.Pack(uint32(2), inputRoot, parserHash, moduleHash, machine, epoch, total)
	if err != nil {
		t.Fatal(err)
	}
	return crypto.Keccak256Hash(encoded)
}

func stockS1HarnessNewEnvironment(t *testing.T, classes map[string]stockS1HarnessClass) *stockS1HarnessEnvironment {
	t.Helper()
	key, err := crypto.HexToECDSA(stockS1HarnessTestKeyHex)
	if err != nil {
		t.Fatal(err)
	}
	sender := crypto.PubkeyToAddress(key.PublicKey)
	env := &stockS1HarnessEnvironment{Key: key, Sender: sender, Classes: make(map[string]stockS1HarnessClassDeployment)}
	env.Backend = stockS1HarnessNewBackend(t, sender)

	parser := stockS1HarnessLoadArtifact(t, S1ClassParser)
	module := stockS1HarnessLoadArtifact(t, S1StepModule)
	pageArtifact, err := stock.LoadArtifact(stock.ArtifactPage)
	if err != nil {
		t.Fatalf("accepted S0 page artifact dependency: %v", err)
	}
	env.Parser, env.ParserDeployGas = stockS1HarnessDeploy(t, env, parser.InitCode, stockS1HarnessCreateGas, "parser")
	env.Module, env.ModuleDeployGas = stockS1HarnessDeploy(t, env, module.InitCode, stockS1HarnessCreateGas, "module")
	env.ParserHash = crypto.Keccak256Hash(parser.RuntimeCode)
	env.ModuleHash = crypto.Keccak256Hash(module.RuntimeCode)
	stockS1HarnessAssertExactCode(t, env, env.Parser, parser.RuntimeCode, "parser")
	stockS1HarnessAssertExactCode(t, env, env.Module, module.RuntimeCode, "module")

	names := make([]string, 0, len(classes))
	for name := range classes {
		names = append(names, name)
	}
	sort.Strings(names)
	for _, name := range names {
		class := classes[name]
		constructor, err := pageArtifact.ABI.Pack("", class.Raw)
		if err != nil {
			t.Fatal(err)
		}
		page, pageGas := stockS1HarnessDeploy(t, env, append(append([]byte{}, pageArtifact.InitCode...), constructor...), stockS1HarnessCreateGas, "page-"+name)
		pageCode := append([]byte{0}, class.Raw...)
		stockS1HarnessAssertExactCode(t, env, page, pageCode, "raw page "+name)
		deployment := stockS1HarnessClassDeployment{Class: class, Page: page, PageHash: crypto.Keccak256Hash(pageCode), PayloadHash: crypto.Keccak256Hash(class.Raw), PageGas: pageGas}
		deployment = stockS1HarnessRegister(t, env, parser, deployment)
		env.Classes[name] = deployment
	}
	env.SharedSetupRecords = len(env.Records)
	if env.SharedSetupRecords != 12 {
		t.Fatalf("shared setup transactions=%d", env.SharedSetupRecords)
	}

	// Retry all five exact registrations. They are successful protocol probes,
	// not setup transactions: no event, CREATE, code change, or registry change.
	for _, name := range names {
		before := env.Classes[name]
		data, err := parser.ABI.Pack("registerClass", before.Page, before.PageHash, before.PayloadHash)
		if err != nil {
			t.Fatal(err)
		}
		record := stockS1HarnessSend(t, env, &env.Parser, data, stockS1HarnessCreateGas, "register-idempotent-"+name, true)
		if len(record.Receipt.Logs) != 0 {
			t.Fatalf("idempotent registration %s emitted %d logs", name, len(record.Receipt.Logs))
		}
		page, hash := stockS1HarnessClassRecord(t, env, parser.ABI, before.ClassID)
		if page != before.MetadataPage || hash != before.MetadataHash {
			t.Fatalf("idempotent registration %s changed registry", name)
		}
		if code := stockS1HarnessCodeAt(t, env, before.MetadataPage); crypto.Keccak256Hash(code) != before.MetadataHash {
			t.Fatalf("idempotent registration %s changed metadata code", name)
		}
	}
	return env
}

func stockS1HarnessLoadArtifact(t *testing.T, name string) stock.Artifact {
	t.Helper()
	artifact, err := LoadArtifact(name)
	if err != nil {
		t.Fatalf("required S1 artifact %s: %v", name, err)
	}
	return artifact
}

func stockS1HarnessNewBackend(t *testing.T, sender common.Address) *simulated.Backend {
	t.Helper()
	config := *params.AllDevChainProtocolChanges
	backend := simulated.NewBackend(types.GenesisAlloc{
		sender: {Balance: new(big.Int).Exp(big.NewInt(10), big.NewInt(25), nil)},
	}, func(nodeConf *node.Config, ethConf *ethconfig.Config) {
		nodeConf.HTTPHost, nodeConf.WSHost, nodeConf.IPCPath = "", "", ""
		nodeConf.P2P = p2p.Config{ListenAddr: "", MaxPeers: 0, NoDiscovery: true, DiscoveryV4: false, DiscoveryV5: false}
		ethConf.Genesis = &core.Genesis{Config: &config, GasLimit: stockS1HarnessBlockGas, Alloc: types.GenesisAlloc{
			sender: {Balance: new(big.Int).Exp(big.NewInt(10), big.NewInt(25), nil)},
		}}
		ethConf.Miner.GasCeil = stockS1HarnessBlockGas
	})
	chainID, err := backend.Client().ChainID(context.Background())
	if err != nil || chainID.Uint64() != stockS1HarnessChainID {
		t.Fatalf("simulated chain ID=%v err=%v", chainID, err)
	}
	return backend
}

func (env *stockS1HarnessEnvironment) close(t *testing.T) {
	t.Helper()
	if err := env.Backend.Close(); err != nil {
		t.Errorf("close simulated backend: %v", err)
	}
}

func stockS1HarnessSend(t *testing.T, env *stockS1HarnessEnvironment, to *common.Address, data []byte, gas uint64, kind string, success bool) stockS1HarnessTxRecord {
	t.Helper()
	if gas >= params.MaxTxGas || gas > stockS1HarnessCreateGas || (to != nil && strings.HasPrefix(kind, "resume") && gas > stockS1HarnessResumeGas) {
		t.Fatalf("%s gas %d violates frozen transaction bounds", kind, gas)
	}
	tx := types.NewTx(&types.DynamicFeeTx{ChainID: new(big.Int).SetUint64(stockS1HarnessChainID), Nonce: env.Nonce,
		GasTipCap: new(big.Int).Set(stockS1HarnessTipCap), GasFeeCap: new(big.Int).Set(stockS1HarnessFeeCap), Gas: gas, To: to, Data: append([]byte(nil), data...)})
	signed, err := types.SignTx(tx, types.LatestSignerForChainID(new(big.Int).SetUint64(stockS1HarnessChainID)), env.Key)
	if err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()
	if err := env.Backend.Client().SendTransaction(ctx, signed); err != nil {
		t.Fatalf("send %s nonce=%d: %v", kind, env.Nonce, err)
	}
	env.Backend.Commit()
	receipt, err := env.Backend.Client().TransactionReceipt(ctx, signed.Hash())
	if err != nil {
		t.Fatal(err)
	}
	want := uint64(types.ReceiptStatusFailed)
	if success {
		want = types.ReceiptStatusSuccessful
	}
	if receipt.Status != want || receipt.GasUsed > gas {
		t.Fatalf("%s status=%d want=%d gas=%d/%d", kind, receipt.Status, want, receipt.GasUsed, gas)
	}
	header, err := env.Backend.Client().HeaderByNumber(ctx, receipt.BlockNumber)
	if err != nil {
		t.Fatal(err)
	}
	if header.GasLimit != stockS1HarnessBlockGas || !params.AllDevChainProtocolChanges.IsOsaka(header.Number, header.Time) {
		t.Fatalf("%s not frozen Osaka/30M context", kind)
	}
	record := stockS1HarnessTxRecord{Kind: kind, Tx: signed, Header: header, Receipt: receipt}
	env.Records = append(env.Records, record)
	env.Nonce++
	return record
}

func stockS1HarnessDeploy(t *testing.T, env *stockS1HarnessEnvironment, initCode []byte, gas uint64, kind string) (common.Address, uint64) {
	t.Helper()
	if len(initCode) > params.MaxInitCodeSize {
		t.Fatalf("%s initcode=%d exceeds EIP-3860", kind, len(initCode))
	}
	nonce := env.Nonce
	record := stockS1HarnessSend(t, env, nil, initCode, gas, "deploy-"+kind, true)
	address := crypto.CreateAddress(env.Sender, nonce)
	if record.Receipt.ContractAddress != address {
		t.Fatalf("%s CREATE address=%s want=%s", kind, record.Receipt.ContractAddress, address)
	}
	return address, record.Receipt.GasUsed
}

func stockS1HarnessCodeAt(t *testing.T, env *stockS1HarnessEnvironment, address common.Address) []byte {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	code, err := env.Backend.Client().CodeAt(ctx, address, nil)
	if err != nil {
		t.Fatal(err)
	}
	return code
}

func stockS1HarnessAssertExactCode(t *testing.T, env *stockS1HarnessEnvironment, address common.Address, want []byte, label string) {
	t.Helper()
	got := stockS1HarnessCodeAt(t, env, address)
	if !bytes.Equal(got, want) {
		t.Fatalf("%s deployed code differs: got len/hash %d/%s want %d/%s", label, len(got), crypto.Keccak256Hash(got), len(want), crypto.Keccak256Hash(want))
	}
}

func stockS1HarnessRegister(t *testing.T, env *stockS1HarnessEnvironment, parser stock.Artifact, class stockS1HarnessClassDeployment) stockS1HarnessClassDeployment {
	t.Helper()
	data, err := parser.ABI.Pack("registerClass", class.Page, class.PageHash, class.PayloadHash)
	if err != nil {
		t.Fatal(err)
	}
	record := stockS1HarnessSend(t, env, &env.Parser, data, stockS1HarnessCreateGas, "register-"+class.Class.Name, true)
	if len(record.Receipt.Logs) != 1 {
		t.Fatalf("register %s logs=%d want 1", class.Class.Name, len(record.Receipt.Logs))
	}
	event, ok := parser.ABI.Events["ClassRegistered"]
	if !ok {
		t.Fatal("parser ABI has no ClassRegistered")
	}
	log := record.Receipt.Logs[0]
	if len(log.Topics) != 3 || log.Topics[0] != event.ID || common.BytesToAddress(log.Topics[2][12:]) != class.Page {
		t.Fatalf("register %s malformed indexed event", class.Class.Name)
	}
	values, err := event.Inputs.NonIndexed().Unpack(log.Data)
	if err != nil || len(values) != 3 {
		t.Fatalf("decode ClassRegistered: values=%v err=%v", values, err)
	}
	metadataPage, ok := values[0].(common.Address)
	if !ok {
		t.Fatalf("metadata page type %T", values[0])
	}
	metadataHashRaw, ok := values[1].([32]byte)
	if !ok {
		t.Fatalf("metadata hash type %T", values[1])
	}
	declaredMethods, ok := values[2].(uint16)
	if !ok {
		t.Fatalf("declared methods type %T", values[2])
	}
	class.MetadataPage, class.MetadataHash, class.DeclaredMethods, class.RegisterGas = metadataPage, common.Hash(metadataHashRaw), declaredMethods, record.Receipt.GasUsed
	metadataCode := stockS1HarnessCodeAt(t, env, metadataPage)
	if len(metadataCode) < 1 || len(metadataCode) > 8192 || metadataCode[0] != 0 || crypto.Keccak256Hash(metadataCode) != class.MetadataHash {
		t.Fatalf("%s invalid immutable metadata page len/hash", class.Class.Name)
	}
	class.ClassID = stockS1HarnessClassID(t, env.ParserHash, class)
	if common.Hash(log.Topics[1]) != class.ClassID {
		t.Fatalf("%s classId event=%s want=%s", class.Class.Name, log.Topics[1], class.ClassID)
	}
	page, hash := stockS1HarnessClassRecord(t, env, parser.ABI, class.ClassID)
	if page != metadataPage || hash != class.MetadataHash {
		t.Fatalf("%s classRecord mismatch", class.Class.Name)
	}
	stockS1HarnessAssertMetadata(t, class, metadataCode)
	return class
}

func stockS1HarnessClassRecord(t *testing.T, env *stockS1HarnessEnvironment, parserABI abi.ABI, classID common.Hash) (common.Address, common.Hash) {
	t.Helper()
	values := stockS1HarnessCall(t, env, parserABI, env.Parser, "classRecord", classID)
	if len(values) != 2 {
		t.Fatalf("classRecord values=%d", len(values))
	}
	page, ok := values[0].(common.Address)
	if !ok {
		t.Fatalf("classRecord page type %T", values[0])
	}
	hash, ok := values[1].([32]byte)
	if !ok {
		t.Fatalf("classRecord hash type %T", values[1])
	}
	return page, common.Hash(hash)
}

func stockS1HarnessCall(t *testing.T, env *stockS1HarnessEnvironment, contractABI abi.ABI, address common.Address, method string, args ...interface{}) []interface{} {
	t.Helper()
	data, err := contractABI.Pack(method, args...)
	if err != nil {
		t.Fatalf("pack %s: %v", method, err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	output, err := env.Backend.Client().CallContract(ctx, ethereum.CallMsg{To: &address, Gas: stockS1HarnessResumeGas, Data: data}, nil)
	if err != nil {
		t.Fatalf("call %s: %v", method, err)
	}
	values, err := contractABI.Unpack(method, output)
	if err != nil {
		t.Fatalf("unpack %s: %v", method, err)
	}
	return values
}

func stockS1HarnessAssertMetadata(t *testing.T, class stockS1HarnessClassDeployment, code []byte) {
	t.Helper()
	payload := code[1:]
	word := func(i int) []byte {
		start := i * 32
		if start+32 > len(payload) {
			t.Fatalf("%s metadata truncated at word %d", class.Class.Name, i)
		}
		return payload[start : start+32]
	}
	if common.BytesToHash(word(0)) != stockS1HarnessDomain("JVMEVM:S1:METADATA:2") || common.BytesToAddress(word(1)[12:]) != class.Page || common.BytesToHash(word(2)) != class.PageHash || common.BytesToHash(word(3)) != class.PayloadHash || common.BytesToHash(word(4)) != crypto.Keccak256Hash([]byte(class.Class.Name)) {
		t.Fatalf("%s metadata provenance header mismatch", class.Class.Name)
	}
	h1 := new(big.Int).SetBytes(word(1))
	if h1.BitLen() > 176 || new(big.Int).Rsh(new(big.Int).Set(h1), 160).Uint64() != 0x21 {
		t.Fatalf("%s metadata class access/header bits %x", class.Class.Name, h1)
	}
	h5 := new(big.Int).SetBytes(word(5))
	rawLength := uint32(new(big.Int).And(new(big.Int).Set(h5), new(big.Int).SetUint64(0xffffffff)).Uint64())
	cpCount := uint16(new(big.Int).And(new(big.Int).Rsh(new(big.Int).Set(h5), 32), new(big.Int).SetUint64(0xffff)).Uint64())
	methodCount := uint16(new(big.Int).And(new(big.Int).Rsh(new(big.Int).Set(h5), 48), new(big.Int).SetUint64(0xffff)).Uint64())
	literalCount := uint16(new(big.Int).And(new(big.Int).Rsh(new(big.Int).Set(h5), 64), new(big.Int).SetUint64(0xffff)).Uint64())
	if rawLength != uint32(len(class.Class.Raw)) || cpCount == 0 || methodCount != class.DeclaredMethods || methodCount != uint16(len(class.Class.Methods)) || literalCount != 0 || len(payload) != 6*32+int(methodCount)*4*32 {
		t.Fatalf("%s metadata counts raw=%d cp=%d methods=%d/%d literals=%d bytes=%d", class.Class.Name, rawLength, cpCount, methodCount, len(class.Class.Methods), literalCount, len(payload))
	}
	for _, method := range class.Class.Methods {
		base := 6 + int(method.Index)*4
		if common.BytesToHash(word(base)) != crypto.Keccak256Hash([]byte(method.Name)) || common.BytesToHash(word(base+1)) != crypto.Keccak256Hash([]byte(method.Descriptor)) {
			t.Fatalf("%s method %d metadata hashes", class.Class.Name, method.Index)
		}
		packed := new(big.Int).SetBytes(word(base + 2))
		field := func(shift uint, bits uint64) uint64 {
			return new(big.Int).And(new(big.Int).Rsh(new(big.Int).Set(packed), shift), new(big.Int).SetUint64(bits)).Uint64()
		}
		if field(0, 0xffff) != uint64(method.Index) || field(16, 0xffff) != uint64(method.Access) || packed.BitLen() > 184 {
			t.Fatalf("%s method %d immutable identity/access fields", class.Class.Name, method.Index)
		}
		if method.Name == "<init>" {
			continue
		}
		argc := strings.Count(strings.TrimSuffix(strings.TrimPrefix(method.Descriptor, "("), ")I"), "I")
		if field(32, 0xffffffff) != uint64(method.CodeOffset) || field(64, 0xffff) != uint64(len(method.Code)) || field(80, 0xff) != uint64(method.MaxStack) || field(88, 0xff) != uint64(method.MaxLocals) || field(96, 0xff) != uint64(argc) || field(104, 0xff) != 0 || field(112, 0xff) != 0 || field(120, 0xffffffff) != 0 || field(152, 0xffff) != 0 || field(168, 0xffff) != 0 {
			t.Fatalf("%s method %d eligible packed metadata=%x", class.Class.Name, method.Index, packed)
		}
		starts := stockS1HarnessInstructionStarts(t, method.Code)
		if new(big.Int).SetBytes(word(base+3)).Cmp(starts) != 0 {
			t.Fatalf("%s method %d instruction-start map", class.Class.Name, method.Index)
		}
	}
}

func stockS1HarnessInstructionStarts(t *testing.T, code []byte) *big.Int {
	t.Helper()
	starts := new(big.Int)
	for pc := 0; pc < len(code); {
		starts.SetBit(starts, pc, 1)
		op := code[pc]
		width := 0
		switch {
		case op == 0x00, op >= 0x02 && op <= 0x08, op >= 0x1a && op <= 0x1d, op >= 0x3b && op <= 0x3e, op == 0x60, op == 0x64, op == 0x68, op == 0x74, op == 0xac:
			width = 1
		case op == 0x10, op == 0x12, op == 0x15, op == 0x36:
			width = 2
		case op == 0x11, op == 0x13, op == 0x84, op >= 0x99 && op <= 0xa4, op == 0xa7:
			width = 3
		default:
			t.Fatalf("TEST starts unsupported opcode 0x%02x at %d", op, pc)
		}
		if pc+width > len(code) {
			t.Fatalf("TEST starts truncated opcode at %d", pc)
		}
		pc += width
	}
	return starts
}

func stockS1HarnessRunCase(t *testing.T, env *stockS1HarnessEnvironment, tc stockS1HarnessCase, budget uint16, resumeLimit int) stockS1HarnessCaseRun {
	t.Helper()
	if budget == 0 || budget > 128 {
		t.Fatalf("%s invalid budget %d", tc.ID, budget)
	}
	class := env.Classes[tc.Class]
	coordinator := stockS1HarnessLoadArtifact(t, S1Coordinator)
	constructor, err := coordinator.ABI.Pack("", env.Parser, env.ParserHash, class.ClassID, env.Module, env.ModuleHash, []byte(tc.Entry), tc.Args, stockS1HarnessMaxTotalSteps)
	if err != nil {
		t.Fatalf("%s coordinator constructor: %v", tc.ID, err)
	}
	address, createGas := stockS1HarnessDeploy(t, env, append(append([]byte{}, coordinator.InitCode...), constructor...), stockS1HarnessCreateGas, "coordinator-"+tc.ID+fmt.Sprintf("-b%d", budget))
	actual := stockS1HarnessCodeAt(t, env, address)
	stockS1HarnessAssertCoordinatorTemplate(t, coordinator.RuntimeCode, actual)

	programID := stockS1HarnessProgramID(t, class.ClassID, tc, env.ModuleHash)
	argsHash := stockS1HarnessArgsHash(t, tc.Args)
	inputRoot := stockS1HarnessInputRoot(t, programID, argsHash)
	stockS1HarnessAssertCoordinatorGetters(t, env, coordinator.ABI, address, class, tc, programID, argsHash, inputRoot)
	checkpoint := stockS1HarnessReadCheckpoint(t, env, coordinator.ABI, address)
	initial := stockS1HarnessTracePrefix(t, stockS1HarnessMethodNamed(t, class.Class, tc.Entry), tc.Args, 0)
	stockS1HarnessAssertCheckpoint(t, env, tc, class, checkpoint, initial, 0, 0, programID, inputRoot)

	run := stockS1HarnessCaseRun{Case: tc, Budget: budget, Coordinator: address, Gas: createGas}
	method := stockS1HarnessMethodNamed(t, class.Class, tc.Entry)
	for checkpoint.Machine.Lifecycle == 0 && (resumeLimit == 0 || run.Resumes < resumeLimit) {
		before := checkpoint
		data, err := coordinator.ABI.Pack("resume", checkpoint.Epoch, budget, uint8(32))
		if err != nil {
			t.Fatal(err)
		}
		record := stockS1HarnessSend(t, env, &address, data, stockS1HarnessResumeGas, "resume-"+tc.ID+fmt.Sprintf("-b%d-e%d", budget, checkpoint.Epoch), true)
		run.Gas += record.Receipt.GasUsed
		run.Resumes++
		checkpoint = stockS1HarnessReadCheckpoint(t, env, coordinator.ABI, address)
		if checkpoint.Epoch != before.Epoch+1 || checkpoint.TotalSteps <= before.TotalSteps || checkpoint.TotalSteps-before.TotalSteps > uint64(budget) {
			t.Fatalf("%s invalid epoch/step transition before=%d/%d after=%d/%d", tc.ID, before.Epoch, before.TotalSteps, checkpoint.Epoch, checkpoint.TotalSteps)
		}
		if checkpoint.Machine.PC == before.Machine.PC && checkpoint.Machine.Lifecycle == 0 {
			run.SamePC++
		}
		model := stockS1HarnessTracePrefix(t, method, tc.Args, checkpoint.TotalSteps)
		stockS1HarnessAssertCheckpoint(t, env, tc, class, checkpoint, model, checkpoint.Epoch, checkpoint.TotalSteps, programID, inputRoot)
		event := stockS1HarnessDecodeEvent(t, coordinator.ABI, record.Receipt)
		stockS1HarnessAssertEvent(t, tc, before, checkpoint, event, budget)
		if run.Resumes > 16 && resumeLimit == 0 {
			t.Fatalf("%s budget=%d exceeds isolated <=19 external tx bound", tc.ID, budget)
		}
	}
	run.Checkpoint = checkpoint
	if resumeLimit == 0 {
		if checkpoint.Machine.Lifecycle != 1 || checkpoint.TotalSteps != tc.Steps || checkpoint.Machine.Result != tc.Expected {
			t.Fatalf("%s budget=%d did not return exactly: %+v", tc.ID, budget, checkpoint)
		}
		stockS1HarnessAssertCatalogueLocals(t, tc, checkpoint.Machine)
	}
	env.Runs = append(env.Runs, run)
	return run
}

func stockS1HarnessLongLoop(tc stockS1HarnessCase) bool {
	return tc.Class == "Loops" && (tc.Entry == "sum" || tc.Entry == "fibonacci")
}

func stockS1HarnessAssertCaseBounds(t *testing.T, env *stockS1HarnessEnvironment, run stockS1HarnessCaseRun, terminal bool) {
	t.Helper()
	class := env.Classes[run.Case.Class]
	isolatedGas := env.ParserDeployGas + env.ModuleDeployGas + class.PageGas + class.RegisterGas + run.Gas
	isolatedTx := 4 + 1 + run.Resumes
	if terminal && (isolatedTx > 19 || isolatedGas > 30_000_000) {
		t.Fatalf("%s budget=%d isolated positive tx/gas=%d/%d exceeds 19/30M", run.Case.ID, run.Budget, isolatedTx, isolatedGas)
	}
	for _, record := range env.Records[len(env.Records)-run.Resumes:] {
		if record.Receipt.GasUsed > stockS1HarnessResumeGas {
			t.Fatalf("%s resume gas=%d", run.Case.ID, record.Receipt.GasUsed)
		}
	}
	t.Logf("stock_s1 case=%s budget=%d legacyGas(separate)=%d sharedCaseGas=%d isolatedGas=%d isolatedTx=%d resumes=%d result=%d steps=%d", run.Case.ID, run.Budget, run.Case.LegacyGasLimit, run.Gas, isolatedGas, isolatedTx, run.Resumes, run.Checkpoint.Machine.Result, run.Checkpoint.TotalSteps)
}

func stockS1HarnessAssertCoordinatorTemplate(t *testing.T, template, actual []byte) {
	t.Helper()
	if len(actual) != len(template) {
		t.Fatalf("coordinator runtime len=%d want template=%d", len(actual), len(template))
	}
	refs, err := CompilerImmutableReferences(S1Coordinator)
	if err != nil {
		t.Fatal(err)
	}
	mutable := make([]bool, len(template))
	for _, locations := range refs {
		for _, ref := range locations {
			for i := ref.Start; i < ref.Start+ref.Length; i++ {
				mutable[i] = true
			}
		}
	}
	for i := range template {
		if !mutable[i] && template[i] != actual[i] {
			t.Fatalf("coordinator differs outside immutableReferences at byte %d", i)
		}
	}
}

func stockS1HarnessAssertCoordinatorGetters(t *testing.T, env *stockS1HarnessEnvironment, contractABI abi.ABI, address common.Address, class stockS1HarnessClassDeployment, tc stockS1HarnessCase, programID, argsHash, inputRoot common.Hash) {
	t.Helper()
	checks := map[string]interface{}{
		"parser": env.Parser, "expectedParserHash": env.ParserHash, "module": env.Module, "expectedModuleHash": env.ModuleHash,
		"classId": class.ClassID, "programId": programID, "argsHash": argsHash, "inputRoot": inputRoot, "maxTotalSteps": stockS1HarnessMaxTotalSteps,
	}
	names := make([]string, 0, len(checks))
	for name := range checks {
		names = append(names, name)
	}
	sort.Strings(names)
	for _, name := range names {
		values := stockS1HarnessCall(t, env, contractABI, address, name)
		if len(values) != 1 || !stockS1HarnessABIEqual(values[0], checks[name]) {
			t.Fatalf("%s getter %s got %v want %v", tc.ID, name, values, checks[name])
		}
	}
	values := stockS1HarnessCall(t, env, contractABI, address, "programContext")
	if len(values) != 1 {
		t.Fatalf("%s programContext outputs=%d", tc.ID, len(values))
	}
	contextValue, ok := abi.ConvertType(values[0], new(stockS1HarnessProgramContext)).(*stockS1HarnessProgramContext)
	if !ok || contextValue.Parser != env.Parser || common.Hash(contextValue.ParserCodeHash) != env.ParserHash || common.Hash(contextValue.ClassID) != class.ClassID || contextValue.RawPage != class.Page || common.Hash(contextValue.RawPageHash) != class.PageHash || common.Hash(contextValue.PayloadHash) != class.PayloadHash || contextValue.MetadataPage != class.MetadataPage || common.Hash(contextValue.MetadataHash) != class.MetadataHash || contextValue.MethodIndex != tc.MethodIndex || common.Hash(contextValue.ProgramID) != programID {
		t.Fatalf("%s programContext mismatch %+v", tc.ID, contextValue)
	}
}

func stockS1HarnessABIEqual(got, want interface{}) bool {
	if hash, ok := got.([32]byte); ok {
		expected, ok := want.(common.Hash)
		return ok && common.Hash(hash) == expected
	}
	if n, ok := got.(*big.Int); ok {
		switch expected := want.(type) {
		case uint64:
			return n.IsUint64() && n.Uint64() == expected
		case uint16:
			return n.IsUint64() && n.Uint64() == uint64(expected)
		}
	}
	return reflect.DeepEqual(got, want)
}

func stockS1HarnessReadCheckpoint(t *testing.T, env *stockS1HarnessEnvironment, contractABI abi.ABI, address common.Address) stockS1HarnessCheckpoint {
	t.Helper()
	data, err := contractABI.Pack("checkpoint")
	if err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	output, err := env.Backend.Client().CallContract(ctx, ethereum.CallMsg{To: &address, Gas: stockS1HarnessResumeGas, Data: data}, nil)
	if err != nil {
		t.Fatalf("checkpoint call: %v", err)
	}
	return stockS1HarnessDecodeCheckpoint(t, contractABI, output)
}

func stockS1HarnessDecodeCheckpoint(t *testing.T, contractABI abi.ABI, output []byte) stockS1HarnessCheckpoint {
	t.Helper()
	values, err := contractABI.Unpack("checkpoint", output)
	if err != nil || len(values) != 8 {
		t.Fatalf("checkpoint decode values=%d err=%v", len(values), err)
	}
	machine, ok := abi.ConvertType(values[7], new(stockS1HarnessMachine)).(*stockS1HarnessMachine)
	if !ok {
		t.Fatalf("checkpoint machine type %T", values[7])
	}
	checkpoint := stockS1HarnessCheckpoint{Machine: *machine}
	var typeOK bool
	checkpoint.Schema, typeOK = values[0].(uint32)
	if !typeOK {
		t.Fatalf("checkpoint schema type %T", values[0])
	}
	checkpoint.ClassID, typeOK = values[1].([32]byte)
	if !typeOK {
		t.Fatalf("checkpoint class type %T", values[1])
	}
	checkpoint.ProgramID, typeOK = values[2].([32]byte)
	if !typeOK {
		t.Fatalf("checkpoint program type %T", values[2])
	}
	checkpoint.InputRoot, typeOK = values[3].([32]byte)
	if !typeOK {
		t.Fatalf("checkpoint input type %T", values[3])
	}
	checkpoint.Epoch, typeOK = values[4].(uint64)
	if !typeOK {
		t.Fatalf("checkpoint epoch type %T", values[4])
	}
	checkpoint.TotalSteps, typeOK = values[5].(uint64)
	if !typeOK {
		t.Fatalf("checkpoint steps type %T", values[5])
	}
	checkpoint.StateDigest, typeOK = values[6].([32]byte)
	if !typeOK {
		t.Fatalf("checkpoint digest type %T", values[6])
	}
	return checkpoint
}

func stockS1HarnessAssertCheckpoint(t *testing.T, env *stockS1HarnessEnvironment, tc stockS1HarnessCase, class stockS1HarnessClassDeployment, checkpoint stockS1HarnessCheckpoint, model stockS1HarnessMachine, epoch, total uint64, programID, inputRoot common.Hash) {
	t.Helper()
	if checkpoint.Schema != 2 || common.Hash(checkpoint.ClassID) != class.ClassID || common.Hash(checkpoint.ProgramID) != programID || common.Hash(checkpoint.InputRoot) != inputRoot || checkpoint.Epoch != epoch || checkpoint.TotalSteps != total || !stockS1HarnessMachineEqual(checkpoint.Machine, model) {
		t.Fatalf("%s checkpoint mismatch got=%+v model=%+v", tc.ID, checkpoint, model)
	}
	stockS1HarnessAssertCanonicalMachine(t, checkpoint.Machine)
	wantDigest := stockS1HarnessStateDigest(t, inputRoot, env.ParserHash, env.ModuleHash, checkpoint.Machine, epoch, total)
	if common.Hash(checkpoint.StateDigest) != wantDigest {
		t.Fatalf("%s stateDigest=%x want=%s", tc.ID, checkpoint.StateDigest, wantDigest)
	}
}

func stockS1HarnessMachineEqual(a, b stockS1HarnessMachine) bool {
	if a.PC != b.PC || a.SP != b.SP || a.Initialized != b.Initialized || a.Lifecycle != b.Lifecycle || a.Result != b.Result {
		return false
	}
	for i := range a.Stack {
		if a.Stack[i] == nil || b.Stack[i] == nil || a.Stack[i].Cmp(b.Stack[i]) != 0 {
			return false
		}
	}
	for i := range a.Locals {
		if a.Locals[i] == nil || b.Locals[i] == nil || a.Locals[i].Cmp(b.Locals[i]) != 0 {
			return false
		}
	}
	return true
}

func stockS1HarnessDecodeEvent(t *testing.T, contractABI abi.ABI, receipt *types.Receipt) stockS1HarnessEvent {
	t.Helper()
	eventABI, ok := contractABI.Events["CheckpointV2"]
	if !ok {
		t.Fatal("coordinator ABI has no CheckpointV2")
	}
	if len(receipt.Logs) != 1 || len(receipt.Logs[0].Topics) != 3 || receipt.Logs[0].Topics[0] != eventABI.ID {
		t.Fatalf("resume logs malformed count=%d", len(receipt.Logs))
	}
	var event stockS1HarnessEvent
	event.Epoch = new(big.Int).SetBytes(receipt.Logs[0].Topics[1][:]).Uint64()
	event.ProgramID = receipt.Logs[0].Topics[2]
	if err := contractABI.UnpackIntoInterface(&event, "CheckpointV2", receipt.Logs[0].Data); err != nil {
		t.Fatalf("decode CheckpointV2: %v", err)
	}
	return event
}

func stockS1HarnessAssertEvent(t *testing.T, tc stockS1HarnessCase, before, after stockS1HarnessCheckpoint, event stockS1HarnessEvent, budget uint16) {
	t.Helper()
	executed := uint16(after.TotalSteps - before.TotalSteps)
	if event.Epoch != after.Epoch || common.Hash(event.ProgramID) != common.Hash(after.ProgramID) || event.TotalSteps != after.TotalSteps || event.PC != after.Machine.PC || event.SP != after.Machine.SP || event.Lifecycle != after.Machine.Lifecycle || event.Result != after.Machine.Result || event.Executed != executed || executed == 0 || executed > budget || common.Hash(event.StateDigest) != common.Hash(after.StateDigest) {
		t.Fatalf("%s CheckpointV2 does not match checkpoint: event=%+v after=%+v", tc.ID, event, after)
	}
	actualDirty := stockS1HarnessDirtyWords(before, after)
	if event.DirtyWords < actualDirty || event.DirtyWords > 32 {
		t.Fatalf("%s dirtyWords=%d actual logical=%d", tc.ID, event.DirtyWords, actualDirty)
	}
}

func stockS1HarnessDirtyWords(before, after stockS1HarnessCheckpoint) uint8 {
	changed := uint8(3)
	if before.Machine.PC != after.Machine.PC {
		changed++
	}
	if before.Machine.SP != after.Machine.SP {
		changed++
	}
	if before.Machine.Initialized != after.Machine.Initialized {
		changed++
	}
	if before.Machine.Lifecycle != after.Machine.Lifecycle {
		changed++
	}
	if before.Machine.Result != after.Machine.Result {
		changed++
	}
	for i := range before.Machine.Stack {
		if before.Machine.Stack[i].Cmp(after.Machine.Stack[i]) != 0 {
			changed++
		}
	}
	for i := range before.Machine.Locals {
		if before.Machine.Locals[i].Cmp(after.Machine.Locals[i]) != 0 {
			changed++
		}
	}
	return changed
}

type stockS1HarnessDirectResult struct {
	Root        common.Hash
	Gas         []uint64
	Checkpoints map[common.Address]stockS1HarnessCheckpoint
}

func stockS1HarnessReplayDirect(t *testing.T, env *stockS1HarnessEnvironment) stockS1HarnessDirectResult {
	t.Helper()
	config := *params.AllDevChainProtocolChanges
	genesis := &core.Genesis{Config: &config, GasLimit: stockS1HarnessBlockGas, Alloc: types.GenesisAlloc{
		env.Sender: {Balance: new(big.Int).Exp(big.NewInt(10), big.NewInt(25), nil)},
	}}
	disk := rawdb.NewMemoryDatabase()
	trieDB := triedb.NewDatabase(disk, triedb.HashDefaults)
	genesisBlock := genesis.MustCommit(disk, trieDB)
	stateDB, err := state.New(genesisBlock.Root(), state.NewDatabase(trieDB, nil))
	if err != nil {
		t.Fatal(err)
	}
	result := stockS1HarnessDirectResult{Gas: make([]uint64, 0, len(env.Records)), Checkpoints: make(map[common.Address]stockS1HarnessCheckpoint)}
	for index, record := range env.Records {
		header := record.Header
		if !config.IsOsaka(header.Number, header.Time) || header.GasLimit != stockS1HarnessBlockGas {
			t.Fatal("direct replay context is not frozen Osaka/30M")
		}
		message, err := core.TransactionToMessage(record.Tx, types.LatestSignerForChainID(new(big.Int).SetUint64(stockS1HarnessChainID)), header.BaseFee)
		if err != nil {
			t.Fatalf("TransactionToMessage %s: %v", record.Kind, err)
		}
		if message.From != env.Sender || message.Nonce != uint64(index) || message.SkipNonceChecks || message.SkipTransactionChecks {
			t.Fatalf("%s signed message recovery/checks mismatch", record.Kind)
		}
		stateDB.SetTxContext(record.Tx.Hash(), index)
		evm := vm.NewEVM(stockS1HarnessBlockContext(header), stateDB, &config, vm.Config{})
		execution, err := core.ApplyMessage(evm, message, new(core.GasPool).AddGas(header.GasLimit))
		if err != nil {
			t.Fatalf("ApplyMessage %s: %v", record.Kind, err)
		}
		wantFailed := record.Receipt.Status == types.ReceiptStatusFailed
		if execution.Failed() != wantFailed || execution.UsedGas != record.Receipt.GasUsed {
			t.Fatalf("ApplyMessage %s failed/gas=%v/%d receipt=%v/%d", record.Kind, execution.Failed(), execution.UsedGas, wantFailed, record.Receipt.GasUsed)
		}
		result.Gas = append(result.Gas, execution.UsedGas)
		stateDB.Finalise(config.IsEIP158(header.Number))
		result.Root = stateDB.IntermediateRoot(config.IsEIP158(header.Number))
	}
	parser := stockS1HarnessLoadArtifact(t, S1ClassParser)
	module := stockS1HarnessLoadArtifact(t, S1StepModule)
	coordinator := stockS1HarnessLoadArtifact(t, S1Coordinator)
	if !bytes.Equal(stateDB.GetCode(env.Parser), parser.RuntimeCode) || !bytes.Equal(stateDB.GetCode(env.Module), module.RuntimeCode) {
		t.Fatal("direct replay changed parser/module deployed bytes")
	}
	for _, class := range env.Classes {
		if !bytes.Equal(stateDB.GetCode(class.Page), append([]byte{0}, class.Class.Raw...)) || crypto.Keccak256Hash(stateDB.GetCode(class.MetadataPage)) != class.MetadataHash {
			t.Fatalf("direct replay class/metadata page mismatch %s", class.Class.Name)
		}
	}
	last := stockS1HarnessBlockContext(env.Records[len(env.Records)-1].Header)
	for _, run := range env.Runs {
		stockS1HarnessAssertCoordinatorTemplate(t, coordinator.RuntimeCode, stateDB.GetCode(run.Coordinator))
		checkpoint := stockS1HarnessReadCheckpointDirect(t, stateDB, &config, last, coordinator.ABI, run.Coordinator)
		if !stockS1HarnessCheckpointEqual(checkpoint, run.Checkpoint) {
			t.Fatalf("direct replay checkpoint mismatch %s budget=%d", run.Case.ID, run.Budget)
		}
		result.Checkpoints[run.Coordinator] = checkpoint
	}
	return result
}

func stockS1HarnessCheckpointEqual(a, b stockS1HarnessCheckpoint) bool {
	return a.Schema == b.Schema && a.ClassID == b.ClassID && a.ProgramID == b.ProgramID && a.InputRoot == b.InputRoot && a.Epoch == b.Epoch && a.TotalSteps == b.TotalSteps && a.StateDigest == b.StateDigest && stockS1HarnessMachineEqual(a.Machine, b.Machine)
}

func stockS1HarnessBlockContext(header *types.Header) vm.BlockContext {
	difficulty := new(big.Int)
	if header.Difficulty != nil {
		difficulty.Set(header.Difficulty)
	}
	var random *common.Hash
	if difficulty.Sign() == 0 {
		value := header.MixDigest
		random = &value
	}
	baseFee := new(big.Int)
	if header.BaseFee != nil {
		baseFee.Set(header.BaseFee)
	}
	return vm.BlockContext{CanTransfer: core.CanTransfer, Transfer: core.Transfer, GetHash: func(uint64) common.Hash { return common.Hash{} },
		Coinbase: header.Coinbase, GasLimit: header.GasLimit, BlockNumber: new(big.Int).Set(header.Number), Time: header.Time,
		Difficulty: difficulty, BaseFee: baseFee, BlobBaseFee: new(big.Int), Random: random}
}

func stockS1HarnessReadCheckpointDirect(t *testing.T, stateDB *state.StateDB, config *params.ChainConfig, blockContext vm.BlockContext, contractABI abi.ABI, address common.Address) stockS1HarnessCheckpoint {
	t.Helper()
	data, err := contractABI.Pack("checkpoint")
	if err != nil {
		t.Fatal(err)
	}
	evm := vm.NewEVM(blockContext, stateDB, config, vm.Config{})
	output, _, err := evm.StaticCall(common.Address{}, address, data, stockS1HarnessResumeGas)
	if err != nil {
		t.Fatalf("direct checkpoint: %v", err)
	}
	return stockS1HarnessDecodeCheckpoint(t, contractABI, output)
}

func stockS1HarnessReceiptGas(records []stockS1HarnessTxRecord) []uint64 {
	gas := make([]uint64, len(records))
	for i, record := range records {
		gas[i] = record.Receipt.GasUsed
	}
	return gas
}

func stockS1HarnessSumGas(records []stockS1HarnessTxRecord) uint64 {
	var gas uint64
	for _, record := range records {
		gas += record.Receipt.GasUsed
	}
	return gas
}

func stockS1HarnessGasAccounting(records []stockS1HarnessTxRecord) (map[string]uint64, map[string]int) {
	gas := make(map[string]uint64)
	txs := make(map[string]int)
	for _, record := range records {
		kind := "other"
		switch {
		case record.Kind == "deploy-parser":
			kind = "parserCreate"
		case record.Kind == "deploy-module":
			kind = "moduleCreate"
		case strings.HasPrefix(record.Kind, "deploy-page-"):
			kind = "rawPageCreate"
		case strings.HasPrefix(record.Kind, "register-idempotent-"):
			kind = "idempotentRegister"
		case strings.HasPrefix(record.Kind, "register-"):
			kind = "registerAndInternalMetadataCreate"
		case strings.HasPrefix(record.Kind, "deploy-coordinator-"):
			kind = "coordinatorCreate"
		case strings.HasPrefix(record.Kind, "resume-"):
			kind = "resume"
		}
		gas[kind] += record.Receipt.GasUsed
		txs[kind]++
	}
	return gas, txs
}
