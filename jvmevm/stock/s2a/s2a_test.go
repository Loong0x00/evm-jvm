package s2a

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
	stockS2aHarnessChainID       = uint64(1337)
	stockS2aHarnessBlockGas      = uint64(30_000_000)
	stockS2aHarnessCreateGas     = uint64(8_000_000)
	stockS2aHarnessResumeGas     = uint64(2_000_000)
	stockS2aHarnessMaxTotalSteps = uint64(1024)
	stockS2aHarnessSourceRoot    = "../../testdata/differential"
	stockS2aHarnessCataloguePath = "../../testdata/stock/s2a/catalogue.json"
	stockS2aHarnessTestKeyHex    = "2cfb1db9f8e9a812561a042fc460a41fbc36ee90ba938589a94eb5ad4b632108"
	stockS2aHarnessCatalogueRoot = "0x1273f2302d2898a2eb0ff391f9cf7ff2c9b64749fd0821df891b921499aa8d0d"
)

var (
	stockS2aHarnessFeeCap = new(big.Int).Mul(big.NewInt(100), big.NewInt(params.GWei))
	stockS2aHarnessTipCap = new(big.Int).SetUint64(params.GWei)
)

type stockS2aHarnessCatalogue struct {
	Schema               uint32                          `json:"schema"`
	CatalogueCount       uint16                          `json:"catalogueCount"`
	CatalogueRoot        string                          `json:"catalogueRoot"`
	LegacyManifestSHA256 string                          `json:"legacyManifestSha256"`
	CompilerCommand      []string                        `json:"compilerCommand"`
	CompilerUsedToPin    string                          `json:"compilerUsedToPin"`
	Java8UsedToPin       string                          `json:"java8UsedToPin"`
	Java21UsedToPin      string                          `json:"java21UsedToPin"`
	Classes              []stockS2aHarnessCatalogueClass `json:"classes"`
	Cases                []stockS2aHarnessCase           `json:"cases"`
}

type stockS2aHarnessCatalogueClass struct {
	Name           string `json:"name"`
	Source         string `json:"source"`
	SourceSHA256   string `json:"sourceSha256"`
	ClassSHA256    string `json:"classSha256"`
	ClassBytes     int    `json:"classBytes"`
	RawPayloadHash string `json:"rawPayloadHash"`
}

type stockS2aHarnessCase struct {
	Index             uint16   `json:"index"`
	ID                string   `json:"id"`
	Stage             string   `json:"stage"`
	Sources           []string `json:"sources"`
	Smoke             bool     `json:"smoke"`
	Class             string   `json:"class"`
	Entry             string   `json:"entry"`
	Descriptor        string   `json:"descriptor"`
	Args              []int32  `json:"args"`
	ArgsHash          string   `json:"argsHash"`
	LegacyGasLimit    uint64   `json:"legacyGasLimit"`
	TimeoutSeconds    uint64   `json:"timeoutSeconds"`
	ExpectedKind      string   `json:"expectedKind"`
	Expected          int32    `json:"expected"`
	ExpectedException string   `json:"expectedException"`
	Steps             uint64   `json:"steps"`
	PC                uint32   `json:"pc"`
	SP                uint8    `json:"sp"`
	Initialized       uint8    `json:"initialized"`
	Lifecycle         uint8    `json:"lifecycle"`
	JavaFaultKind     uint8    `json:"javaFaultKind"`
	FaultPC           uint32   `json:"faultPC"`
	Stack             []int32  `json:"stack"`
	Locals            []int32  `json:"locals"`
	MaxStack          uint8    `json:"maxStack"`
	MaxLocals         uint8    `json:"maxLocals"`
	CodeLength        uint16   `json:"codeLength"`
	MethodIndex       uint16   `json:"methodIndex"`
	Leaf              string   `json:"leaf"`
}

type stockS2aHarnessLegacyManifest struct {
	Schema uint64                      `json:"schema_version"`
	Cases  []stockS2aHarnessLegacyCase `json:"cases"`
}

type stockS2aHarnessLegacyCase struct {
	ID                string   `json:"id"`
	Stage             string   `json:"stage"`
	Sources           []string `json:"sources"`
	Class             string   `json:"class"`
	Method            string   `json:"method"`
	Args              []int32  `json:"args"`
	GasLimit          uint64   `json:"gas_limit"`
	TimeoutSeconds    uint64   `json:"timeout_seconds"`
	ExpectedKind      string   `json:"expected_kind"`
	ExpectedException string   `json:"expected_exception"`
	Smoke             bool     `json:"smoke"`
}

type stockS2aHarnessMethod struct {
	Index      uint16
	Name       string
	Descriptor string
	Access     uint16
	CodeOffset uint32
	MaxStack   uint8
	MaxLocals  uint8
	Code       []byte
}

type stockS2aHarnessClass struct {
	Name    string
	Raw     []byte
	CPCount uint16
	CPInts  map[uint16]int32
	Methods []stockS2aHarnessMethod
}

type stockS2aHarnessMachine struct {
	PC            uint32      `abi:"pc"`
	SP            uint8       `abi:"sp"`
	Initialized   uint8       `abi:"initialized"`
	Lifecycle     uint8       `abi:"lifecycle"`
	Stack         [8]*big.Int `abi:"stack"`
	Locals        [8]*big.Int `abi:"locals"`
	Result        int32       `abi:"result"`
	JavaFaultKind uint8       `abi:"javaFaultKind"`
	FaultPC       uint32      `abi:"faultPC"`
}

type stockS2aHarnessCheckpoint struct {
	Schema      uint32
	ClassID     [32]byte
	ProgramID   [32]byte
	InputRoot   [32]byte
	Epoch       uint64
	TotalSteps  uint64
	StateDigest [32]byte
	Machine     stockS2aHarnessMachine
}

type stockS2aHarnessProgramContext struct {
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

type stockS2aHarnessEvent struct {
	Epoch         uint64
	ProgramID     [32]byte
	TotalSteps    uint64   `abi:"totalSteps"`
	PC            uint32   `abi:"pc"`
	SP            uint8    `abi:"sp"`
	Lifecycle     uint8    `abi:"lifecycle"`
	JavaFaultKind uint8    `abi:"javaFaultKind"`
	Result        int32    `abi:"result"`
	Executed      uint16   `abi:"executed"`
	DirtyWords    uint8    `abi:"dirtyWords"`
	StateDigest   [32]byte `abi:"stateDigest"`
}

type stockS2aHarnessClassDeployment struct {
	Class           stockS2aHarnessClass
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

type stockS2aHarnessTxRecord struct {
	Kind    string
	Tx      *types.Transaction
	Header  *types.Header
	Receipt *types.Receipt
}

type stockS2aHarnessCaseRun struct {
	Case        stockS2aHarnessCase
	Budget      uint16
	Coordinator common.Address
	Checkpoint  stockS2aHarnessCheckpoint
	Resumes     int
	Gas         uint64
	SamePC      int
}

type stockS2aHarnessEnvironment struct {
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
	Classes            map[string]stockS2aHarnessClassDeployment
	Records            []stockS2aHarnessTxRecord
	Runs               []stockS2aHarnessCaseRun
	SharedSetupRecords int
}

func TestStockS2aHarnessArtifactLoader(t *testing.T) {
	for _, name := range []string{S2aMetadataPage, S2aClassParser, S2aStepModule, S2aCoordinator} {
		artifact, err := LoadArtifact(name)
		if err != nil {
			t.Fatalf("required runtime artifact dependency %s: %v", name, err)
		}
		if len(artifact.InitCode) == 0 || len(artifact.RuntimeCode) == 0 {
			t.Fatalf("%s contains empty code", name)
		}
	}
	if _, err := LoadArtifact("not-a-stock-s2a-artifact"); err == nil {
		t.Fatal("unknown S2a artifact unexpectedly loaded")
	}
	if _, err := LoadArtifact(stock.ArtifactPage); err == nil {
		t.Fatal("S0 ArtifactPage unexpectedly accepted by the S2a loader")
	}
	if _, err := stock.LoadArtifact(stock.ArtifactPage); err != nil {
		t.Fatalf("accepted S0 ArtifactPage dependency: %v", err)
	}
	if class, ok := JavaFaultClass(1); !ok || class != "java.lang.ArithmeticException" {
		t.Fatalf("fault kind 1 mapping=%q/%v", class, ok)
	}
	for _, kind := range []uint8{0, 2, 255} {
		if class, ok := JavaFaultClass(kind); ok || class != "" {
			t.Fatalf("fault kind %d unexpectedly mapped to %q/%v", kind, class, ok)
		}
	}
}

func TestStockS2aHarnessCatalogueJVM8JVM21MonolithAndBoundedTrace(t *testing.T) {
	catalogue, classes, output := stockS2aHarnessLoadAndCompile(t)
	legacy := stockS2aHarnessReadLegacy(t)
	stockS2aHarnessCheckCatalogueEncoding(t, catalogue, classes, legacy)

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
		method := stockS2aHarnessMethodNamed(t, guest, tc.Entry)
		machine, steps := stockS2aHarnessTrace(t, guest, method, tc.Args, 100_000)
		if steps != tc.Steps || machine.PC != tc.PC || machine.SP != tc.SP || machine.Lifecycle != tc.Lifecycle || machine.Result != tc.Expected || machine.Initialized != tc.Initialized || machine.JavaFaultKind != tc.JavaFaultKind || machine.FaultPC != tc.FaultPC {
			t.Fatalf("%s pinned trace mismatch steps=%d machine=%+v", tc.ID, steps, machine)
		}
		stockS2aHarnessAssertCatalogueCells(t, tc, machine)
		wantText := stockS2aHarnessExpectedText(tc)
		for _, java := range []string{java8, java21} {
			args := []string{"-Xmx64m", "-Xss512k", "-Xverify:all", "-cp", output, "OracleMain", tc.Class, tc.Entry}
			for _, value := range tc.Args {
				args = append(args, strconv.FormatInt(int64(value), 10))
			}
			text := stockS2aHarnessCommand(t, time.Duration(tc.TimeoutSeconds)*time.Second, java, args...)
			if text != wantText {
				t.Fatalf("%s JVM %s got %q want %q", tc.ID, java, text, wantText)
			}
		}
		monolith, err := jvmevm.Run(guest.Raw, tc.Entry, tc.Args, tc.LegacyGasLimit)
		if err != nil || monolith.ExceptionClass != tc.ExpectedException || (tc.ExpectedKind == "value" && monolith.Value != tc.Expected) {
			t.Fatalf("%s monolith got value=%d exception=%q gas=%d err=%v, want %s", tc.ID, monolith.Value, monolith.ExceptionClass, monolith.GasUsed, err, wantText)
		}
		totalSteps += steps
		programs[tc.Class+"\x00"+tc.Entry] = true
	}
	if totalSteps != 2642 || len(programs) != 60 {
		t.Fatalf("catalogue totals steps=%d programs=%d, want 2642/60", totalSteps, len(programs))
	}
	wide := classes["WideIntegerConstant"]
	populate := stockS2aHarnessMethodNamed(t, wide, "populateIntegerPool")
	loadWide := stockS2aHarnessMethodNamed(t, wide, "loadWide")
	if wide.CPCount != 277 || len(wide.Methods) != 3 || len(populate.Code) != 793 || len(stockS2aHarnessMethodLiterals(t, wide, populate)) != 260 || len(stockS2aHarnessMethodLiterals(t, wide, populate))+len(stockS2aHarnessMethodLiterals(t, wide, loadWide)) != 261 || len(loadWide.Code) != 4 || loadWide.Code[0] != 0x13 || len(stockS2aHarnessMethodLiterals(t, wide, loadWide)) != 1 {
		t.Fatalf("wide fixture shape CP/methods/Code/literals=%d/%d/%d/%d/%d/%x", wide.CPCount, len(wide.Methods), len(populate.Code), len(stockS2aHarnessMethodLiterals(t, wide, populate)), len(loadWide.Code), loadWide.Code)
	}
	monolithHash := stockS2aHarnessMonolithHash(t)
	if monolithHash != "dfc81dbbea8253c644be2532a809a417bb40cd07eaca8ab5be72a84721eae929" {
		t.Fatalf("monolith TEST oracle runtime SHA-256=%s", monolithHash)
	}
	t.Logf("actual oracles agree: catalogue=%d programs=%d instructions=%d javac=%s java8=%s java21=%s monolithRuntime=%s", len(catalogue.Cases), len(programs), totalSteps, catalogue.CompilerUsedToPin, catalogue.Java8UsedToPin, catalogue.Java21UsedToPin, monolithHash)
}

func TestStockS2aHarnessSignedAll201ReuseBudgetsPrefixesAndDirectReplay(t *testing.T) {
	if testing.Short() {
		t.Skip("signed Stock S2a all-201 deployment/replay gate")
	}
	catalogue, classes, _ := stockS2aHarnessLoadAndCompile(t)
	env := stockS2aHarnessNewEnvironment(t, classes)
	defer env.close(t)
	if env.SharedSetupRecords != 24 {
		t.Fatalf("shared setup external transactions=%d want exactly 24", env.SharedSetupRecords)
	}

	programs := make(map[common.Hash]bool)
	inputs := make(map[common.Hash]bool)
	for _, budget := range []uint16{64, 128} {
		for _, tc := range catalogue.Cases {
			run := stockS2aHarnessRunCase(t, env, tc, budget, 0)
			stockS2aHarnessAssertCaseBounds(t, env, run, true)
			programs[common.Hash(run.Checkpoint.ProgramID)] = true
			inputs[common.Hash(run.Checkpoint.InputRoot)] = true
		}
	}
	if len(programs) != 60 || len(inputs) != 201 {
		t.Fatalf("on-chain commitments programs=%d inputs=%d want 60/201", len(programs), len(inputs))
	}

	// Every non-loop row is also complete at the three frozen small budgets.
	for _, budget := range []uint16{1, 7, 16} {
		for _, tc := range catalogue.Cases {
			if stockS2aHarnessLongLoop(tc) {
				continue
			}
			run := stockS2aHarnessRunCase(t, env, tc, budget, 0)
			stockS2aHarnessAssertCaseBounds(t, env, run, true)
		}
	}
	// Loop rows use bounded prefixes at small quanta; their complete executions
	// above at 64/128 remain the terminal-value evidence.
	for _, budget := range []uint16{1, 7, 16} {
		for _, tc := range catalogue.Cases {
			if !stockS2aHarnessLongLoop(tc) {
				continue
			}
			stockS2aHarnessRunCase(t, env, tc, budget, 4)
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

	first := stockS2aHarnessReplayDirect(t, env)
	second := stockS2aHarnessReplayDirect(t, env)
	if first.Root != second.Root || !reflect.DeepEqual(first.Gas, second.Gas) || !reflect.DeepEqual(first.Checkpoints, second.Checkpoints) {
		t.Fatal("identical signed TransactionToMessage replay contexts changed roots, gas, or VM checkpoints")
	}
	if !reflect.DeepEqual(first.Gas, stockS2aHarnessReceiptGas(env.Records)) {
		t.Fatal("direct replay gas differs from signed in-process receipts")
	}

	var sharedGas uint64
	for _, r := range env.Records[:env.SharedSetupRecords] {
		sharedGas += r.Receipt.GasUsed
	}
	firstHeader, lastHeader := env.Records[0].Header, env.Records[len(env.Records)-1].Header
	gasByKind, txByKind := stockS2aHarnessGasAccounting(env.Records)
	var maxIsolatedGas uint64
	var maxIsolatedTx, maxResumes int
	for _, run := range env.Runs {
		class := env.Classes[run.Case.Class]
		gas := env.ParserDeployGas + env.ModuleDeployGas + class.PageGas + class.RegisterGas + run.Gas
		txs := 5 + run.Resumes
		if gas > maxIsolatedGas {
			maxIsolatedGas = gas
		}
		if txs > maxIsolatedTx {
			maxIsolatedTx = txs
		}
		if run.Resumes > maxResumes {
			maxResumes = run.Resumes
		}
	}
	t.Logf("Stock S2a measurements catalogue=%d programs=%d inputs=%d sharedSetupTx=%d sharedSetupGas=%d maxIsolatedGas=%d maxIsolatedTx=%d maxResumes=%d allSignedTx=%d allSignedGas=%d failedTx=0 failedGas=0 gasByKind=%v txByKind=%v directRoot=%s signedWallTimeHeaders(first=%s/root=%s/time=%d last=%s/root=%s/time=%d; intentionally not compared as global roots)", len(catalogue.Cases), len(programs), len(inputs), env.SharedSetupRecords, sharedGas, maxIsolatedGas, maxIsolatedTx, maxResumes, len(env.Records), stockS2aHarnessSumGas(env.Records), gasByKind, txByKind, first.Root, firstHeader.Hash(), firstHeader.Root, firstHeader.Time, lastHeader.Hash(), lastHeader.Root, lastHeader.Time)
}

func TestStockS2aHarnessCapsFaultPrecedenceTerminalAndRollback(t *testing.T) {
	if testing.Short() {
		t.Skip("signed Stock S2a cap/fault/rollback gate")
	}
	catalogue, classes, _ := stockS2aHarnessLoadAndCompile(t)
	env := stockS2aHarnessNewEnvironment(t, classes)
	defer env.close(t)
	find := func(id string) stockS2aHarnessCase {
		for _, tc := range catalogue.Cases {
			if tc.ID == id {
				return tc
			}
		}
		t.Fatalf("missing catalogue case %s", id)
		return stockS2aHarnessCase{}
	}
	deploy := func(tc stockS2aHarnessCase, cap uint64) (stock.Artifact, common.Address, stockS2aHarnessCheckpoint, common.Hash, common.Hash) {
		class := env.Classes[tc.Class]
		coordinator := stockS2aHarnessLoadArtifact(t, S2aCoordinator)
		constructor, err := coordinator.ABI.Pack("", env.Parser, env.ParserHash, class.ClassID, env.Module, env.ModuleHash, []byte(tc.Entry), tc.Args, cap)
		if err != nil {
			t.Fatal(err)
		}
		address, _ := stockS2aHarnessDeploy(t, env, append(append([]byte{}, coordinator.InitCode...), constructor...), stockS2aHarnessCreateGas, fmt.Sprintf("cap-%s-%d", tc.ID, cap))
		stockS2aHarnessAssertCoordinatorTemplate(t, coordinator.RuntimeCode, stockS2aHarnessCodeAt(t, env, address))
		programID := stockS2aHarnessProgramID(t, class.ClassID, tc, env.ModuleHash)
		argsHash := stockS2aHarnessArgsHash(t, tc.Args)
		inputRoot := stockS2aHarnessInputRootFor(t, programID, argsHash, cap)
		stockS2aHarnessAssertCoordinatorGetters(t, env, coordinator.ABI, address, class, tc, programID, argsHash, inputRoot, cap)
		return coordinator, address, stockS2aHarnessReadCheckpoint(t, env, coordinator.ABI, address), programID, inputRoot
	}
	var failedTx int
	var failedGas uint64
	resume := func(coordinator stock.Artifact, address common.Address, before stockS2aHarnessCheckpoint, budget uint16, dirty uint8, gas uint64, success bool) stockS2aHarnessCheckpoint {
		data, err := coordinator.ABI.Pack("resume", before.Epoch, budget, dirty)
		if err != nil {
			t.Fatal(err)
		}
		record := stockS2aHarnessSend(t, env, &address, data, gas, fmt.Sprintf("resume-boundary-e%d", before.Epoch), success)
		after := stockS2aHarnessReadCheckpoint(t, env, coordinator.ABI, address)
		if !success {
			failedTx++
			failedGas += record.Receipt.GasUsed
			if !stockS2aHarnessCheckpointEqual(before, after) || len(record.Receipt.Logs) != 0 {
				t.Fatal("failed resume changed checkpoint or emitted a log")
			}
			return after
		}
		stockS2aHarnessAssertEvent(t, stockS2aHarnessCase{ID: "boundary"}, before, after, stockS2aHarnessDecodeEvent(t, coordinator.ABI, record.Receipt), budget)
		return after
	}

	fault := find("m2b-idiv-zero-divisor")
	for _, cap := range []uint64{2, 3} {
		coordinator, address, before, programID, inputRoot := deploy(fault, cap)
		if cap == 3 {
			before = resume(coordinator, address, before, 128, 32, 100_000, false) // OOG while attempting the fault.
			before = resume(coordinator, address, before, 128, 1, stockS2aHarnessResumeGas, false)
		}
		after := resume(coordinator, address, before, 128, 32, stockS2aHarnessResumeGas, true)
		model := stockS2aHarnessTracePrefix(t, env.Classes[fault.Class].Class, stockS2aHarnessMethodNamed(t, env.Classes[fault.Class].Class, fault.Entry), fault.Args, cap)
		if cap == 2 {
			model.Lifecycle = 2 // The cap wins before idiv executes.
		} else if model.Lifecycle != 3 {
			t.Fatal("TEST model did not reach the fault at cap")
		}
		stockS2aHarnessAssertCheckpoint(t, env, fault, env.Classes[fault.Class], after, model, 1, cap, programID, inputRoot)
		terminal := resume(coordinator, address, after, 1, 32, stockS2aHarnessResumeGas, false)
		if !stockS2aHarnessCheckpointEqual(after, terminal) {
			t.Fatal("terminal resume changed state")
		}
	}

	value := find("m2b-idiv-exact")
	coordinator, address, before, programID, inputRoot := deploy(value, 4)
	after := resume(coordinator, address, before, 128, 32, stockS2aHarnessResumeGas, true)
	model := stockS2aHarnessTracePrefix(t, env.Classes[value.Class].Class, stockS2aHarnessMethodNamed(t, env.Classes[value.Class].Class, value.Entry), value.Args, 4)
	stockS2aHarnessAssertCheckpoint(t, env, value, env.Classes[value.Class], after, model, 1, 4, programID, inputRoot)
	if after.Machine.Lifecycle != 1 || after.Machine.Result != 7 {
		t.Fatal("return landing at cap did not take precedence")
	}

	loop := find("m2-sum-100")
	coordinator, address, before, _, _ = deploy(loop, stockS2aHarnessMaxTotalSteps)
	progress := resume(coordinator, address, before, 1, 32, stockS2aHarnessResumeGas, true)
	if progress.TotalSteps != 1 || progress.Machine.Lifecycle != 0 {
		t.Fatal("expected one nonzero-progress instruction")
	}
	_ = resume(coordinator, address, progress, 128, 1, stockS2aHarnessResumeGas, false)
	_ = resume(coordinator, address, progress, 128, 32, 100_000, false) // OOG rollback after nonzero prior progress.
	_ = resume(coordinator, address, progress, 128, 32, 900_000, false) // commit-reserve failure after progress.

	first := stockS2aHarnessReplayDirect(t, env)
	second := stockS2aHarnessReplayDirect(t, env)
	if first.Root != second.Root || !reflect.DeepEqual(first.Gas, second.Gas) || !reflect.DeepEqual(first.Gas, stockS2aHarnessReceiptGas(env.Records)) {
		t.Fatal("boundary signed direct replay was not deterministic")
	}
	if failedTx != 7 || failedGas == 0 {
		t.Fatalf("boundary failed transaction accounting=%d/%d", failedTx, failedGas)
	}
	t.Logf("Stock S2a rollback measurements failedTx=%d failedGas=%d directRoot=%s", failedTx, failedGas, first.Root)
}

func stockS2aHarnessLoadAndCompile(t *testing.T) (stockS2aHarnessCatalogue, map[string]stockS2aHarnessClass, string) {
	t.Helper()
	raw, err := os.ReadFile(stockS2aHarnessCataloguePath)
	if err != nil {
		t.Fatal(err)
	}
	var catalogue stockS2aHarnessCatalogue
	if err := json.Unmarshal(raw, &catalogue); err != nil {
		t.Fatal(err)
	}
	if catalogue.Schema != 3 || catalogue.CatalogueCount != 201 || len(catalogue.Cases) != 201 || catalogue.CatalogueRoot != stockS2aHarnessCatalogueRoot {
		t.Fatalf("invalid pinned catalogue schema=%d count=%d rows=%d root=%s", catalogue.Schema, catalogue.CatalogueCount, len(catalogue.Cases), catalogue.CatalogueRoot)
	}
	javac, err := exec.LookPath("javac")
	if err != nil {
		t.Fatalf("trusted fixture regeneration requires javac: %v", err)
	}
	output := t.TempDir()
	args := []string{"--release", "8", "-d", output, filepath.Join(stockS2aHarnessSourceRoot, "OracleMain.java")}
	for _, class := range catalogue.Classes {
		args = append(args, filepath.Join(stockS2aHarnessSourceRoot, class.Source))
	}
	stockS2aHarnessCommand(t, time.Minute, javac, args...)
	classes := make(map[string]stockS2aHarnessClass, len(catalogue.Classes))
	for _, pin := range catalogue.Classes {
		source, err := os.ReadFile(filepath.Join(stockS2aHarnessSourceRoot, pin.Source))
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
		parsed := stockS2aHarnessParseClass(t, classfile)
		if parsed.Name != pin.Name {
			t.Fatalf("parsed binary name %q want %q", parsed.Name, pin.Name)
		}
		classes[pin.Name] = parsed
	}
	return catalogue, classes, output
}

func stockS2aHarnessReadLegacy(t *testing.T) []stockS2aHarnessLegacyCase {
	t.Helper()
	path := filepath.Join(stockS2aHarnessSourceRoot, "cases.json")
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	var manifest stockS2aHarnessLegacyManifest
	if err := json.Unmarshal(raw, &manifest); err != nil {
		t.Fatal(err)
	}
	if manifest.Schema != 1 {
		t.Fatalf("legacy manifest schema=%d", manifest.Schema)
	}
	var selected []stockS2aHarnessLegacyCase
	for _, row := range manifest.Cases {
		if row.Stage == "m1" || row.Stage == "m2" || row.Stage == "m2b" {
			selected = append(selected, row)
		}
	}
	if len(selected) != 201 {
		t.Fatalf("legacy M1/M2/M2b rows=%d want 201", len(selected))
	}
	return selected
}

func stockS2aHarnessCheckCatalogueEncoding(t *testing.T, catalogue stockS2aHarnessCatalogue, classes map[string]stockS2aHarnessClass, legacy []stockS2aHarnessLegacyCase) {
	t.Helper()
	manifest, err := os.ReadFile(filepath.Join(stockS2aHarnessSourceRoot, "cases.json"))
	if err != nil {
		t.Fatal(err)
	}
	if got := fmt.Sprintf("%x", sha256.Sum256(manifest)); got != catalogue.LegacyManifestSHA256 {
		t.Fatalf("legacy manifest SHA-256 got %s want %s", got, catalogue.LegacyManifestSHA256)
	}
	leaves := make([][32]byte, len(catalogue.Cases))
	seen := make(map[string]bool)
	values, faults := 0, 0
	for i, tc := range catalogue.Cases {
		old := legacy[i]
		if int(tc.Index) != i || seen[tc.ID] || tc.ID != old.ID || tc.Stage != old.Stage || tc.Class != old.Class || tc.Entry != old.Method || !reflect.DeepEqual(tc.Args, old.Args) || tc.LegacyGasLimit != old.GasLimit || tc.TimeoutSeconds != old.TimeoutSeconds || tc.ExpectedKind != old.ExpectedKind || tc.ExpectedException != old.ExpectedException || tc.Smoke != old.Smoke || !reflect.DeepEqual(tc.Sources, old.Sources) || len(old.Sources) != 1 || old.Sources[0] != tc.Class+".java" {
			t.Fatalf("catalogue row %d does not preserve the ordered legacy row: new=%+v old=%+v", i, tc, old)
		}
		seen[tc.ID] = true
		if tc.Descriptor != stockS2aHarnessDescriptor(len(tc.Args)) || len(tc.Args) > 4 || len(tc.Locals) != 8 || len(tc.Stack) != 8 {
			t.Fatalf("%s invalid descriptor/argument/cell catalogue fields", tc.ID)
		}
		switch tc.ExpectedKind {
		case "value":
			values++
			if tc.ExpectedException != "" || tc.Lifecycle != 1 || tc.SP != 0 || tc.JavaFaultKind != 0 || tc.FaultPC != 0 {
				t.Fatalf("%s noncanonical value catalogue outcome", tc.ID)
			}
		case "java_exception":
			faults++
			class, ok := JavaFaultClass(tc.JavaFaultKind)
			if !ok || class != tc.ExpectedException || tc.Lifecycle != 3 || tc.Expected != 0 || tc.PC != tc.FaultPC || tc.SP < 2 {
				t.Fatalf("%s noncanonical Java-fault catalogue outcome", tc.ID)
			}
		default:
			t.Fatalf("%s unknown expected kind %q", tc.ID, tc.ExpectedKind)
		}
		method := stockS2aHarnessMethodNamed(t, classes[tc.Class], tc.Entry)
		if method.Index != tc.MethodIndex || uint16(len(method.Code)) != tc.CodeLength || method.MaxStack != tc.MaxStack || method.MaxLocals != tc.MaxLocals {
			t.Fatalf("%s selected method metadata differs from raw class", tc.ID)
		}
		argsHash := stockS2aHarnessArgsHash(t, tc.Args)
		if argsHash.Hex() != tc.ArgsHash {
			t.Fatalf("%s args hash got %s want %s", tc.ID, argsHash, tc.ArgsHash)
		}
		payloadHash := crypto.Keccak256Hash(classes[tc.Class].Raw)
		encoded := stockS2aHarnessABIPack(t,
			[]string{"uint32", "uint16", "bytes32", "bytes32", "bytes32", "bytes32", "bytes32", "bytes32"},
			uint32(3), uint16(i), crypto.Keccak256Hash([]byte(tc.ID)), payloadHash,
			crypto.Keccak256Hash([]byte(tc.Class)), crypto.Keccak256Hash([]byte(tc.Entry)),
			crypto.Keccak256Hash([]byte(tc.Descriptor)), argsHash)
		leaf := crypto.Keccak256Hash(encoded)
		if leaf.Hex() != tc.Leaf {
			t.Fatalf("%s leaf got %s want %s", tc.ID, leaf, tc.Leaf)
		}
		leaves[i] = leaf
	}
	if values != 199 || faults != 2 {
		t.Fatalf("catalogue outcome counts values/faults=%d/%d want 199/2", values, faults)
	}
	root := crypto.Keccak256Hash(stockS2aHarnessABIPack(t, []string{"uint32", "uint16", "bytes32[]"}, uint32(3), uint16(201), leaves))
	if root.Hex() != catalogue.CatalogueRoot || root.Hex() != stockS2aHarnessCatalogueRoot {
		t.Fatalf("ordered catalogue root got %s want %s", root, catalogue.CatalogueRoot)
	}
}

func stockS2aHarnessDescriptor(argc int) string {
	return "(" + strings.Repeat("I", argc) + ")I"
}

func stockS2aHarnessExpectedText(tc stockS2aHarnessCase) string {
	if tc.ExpectedKind == "java_exception" {
		return "exception=" + tc.ExpectedException
	}
	return fmt.Sprintf("value=%d", tc.Expected)
}

func stockS2aHarnessCommand(t *testing.T, timeout time.Duration, command string, args ...string) string {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	output, err := exec.CommandContext(ctx, command, args...).CombinedOutput()
	if err != nil {
		t.Fatalf("%s %s: %v\n%s", command, strings.Join(args, " "), err, output)
	}
	return strings.TrimSpace(string(output))
}

func stockS2aHarnessMonolithHash(t *testing.T) string {
	t.Helper()
	hash, err := jvmevm.RuntimeHash()
	if err != nil {
		t.Fatal(err)
	}
	return hash
}

func stockS2aHarnessMethodNamed(t *testing.T, class stockS2aHarnessClass, name string) stockS2aHarnessMethod {
	t.Helper()
	var found *stockS2aHarnessMethod
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

func stockS2aHarnessParseClass(t *testing.T, raw []byte) stockS2aHarnessClass {
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
	integerConstants := make(map[uint16]int32)
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
		case 3:
			if p+4 > len(raw) {
				fail("truncated integer constant")
			}
			integerConstants[i] = int32(binary.BigEndian.Uint32(raw[p : p+4]))
			p += 4
		case 4:
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
	result := stockS2aHarnessClass{Name: utf8[className[thisClass]], Raw: append([]byte(nil), raw...), CPCount: cpCount, CPInts: integerConstants}
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
		method := stockS2aHarnessMethod{Index: uint16(i), Name: utf8[nameIndex], Descriptor: utf8[descriptorIndex], Access: access}
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

func stockS2aHarnessZeroMachine() stockS2aHarnessMachine {
	machine := stockS2aHarnessMachine{}
	for i := range machine.Stack {
		machine.Stack[i] = new(big.Int)
	}
	for i := range machine.Locals {
		machine.Locals[i] = new(big.Int)
	}
	return machine
}

func stockS2aHarnessTrace(t *testing.T, class stockS2aHarnessClass, method stockS2aHarnessMethod, args []int32, limit uint64) (stockS2aHarnessMachine, uint64) {
	t.Helper()
	machine := stockS2aHarnessZeroMachine()
	for i, value := range args {
		machine.Locals[i] = stockS2aHarnessTagged(value)
		machine.Initialized |= 1 << i
	}
	var steps uint64
	for machine.Lifecycle == 0 {
		if steps == limit {
			t.Fatalf("TEST-only bounded trace exceeded %d steps", limit)
		}
		stockS2aHarnessTraceOne(t, class, method, &machine)
		steps++
	}
	return machine, steps
}

func stockS2aHarnessTracePrefix(t *testing.T, class stockS2aHarnessClass, method stockS2aHarnessMethod, args []int32, steps uint64) stockS2aHarnessMachine {
	t.Helper()
	machine := stockS2aHarnessZeroMachine()
	for i, value := range args {
		machine.Locals[i] = stockS2aHarnessTagged(value)
		machine.Initialized |= 1 << i
	}
	for i := uint64(0); i < steps && machine.Lifecycle == 0; i++ {
		stockS2aHarnessTraceOne(t, class, method, &machine)
	}
	return machine
}

func stockS2aHarnessTraceOne(t *testing.T, class stockS2aHarnessClass, method stockS2aHarnessMethod, machine *stockS2aHarnessMachine) {
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
		machine.Stack[machine.SP] = stockS2aHarnessTagged(value)
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
		machine.Locals[index] = stockS2aHarnessTagged(pop())
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
	case op == 0x12 || op == 0x13:
		index := uint16(code[pc+1])
		width := 2
		if op == 0x13 {
			index = binary.BigEndian.Uint16(code[pc+1 : pc+3])
			width = 3
		}
		value, ok := class.CPInts[index]
		if !ok {
			t.Fatalf("TEST trace non-integer constant #%d", index)
		}
		push(value)
		next(width)
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
	case op == 0x6c || op == 0x70:
		if machine.SP < 2 {
			t.Fatal("TEST trace divide/remainder underflow")
		}
		divisor := int32(uint32(machine.Stack[machine.SP-1].Uint64()))
		dividend := int32(uint32(machine.Stack[machine.SP-2].Uint64()))
		if divisor == 0 {
			machine.Lifecycle = 3
			machine.JavaFaultKind = 1
			machine.FaultPC = machine.PC
			break
		}
		_ = pop()
		_ = pop()
		quotient := int32(int64(dividend) / int64(divisor))
		if op == 0x6c {
			push(quotient)
		} else {
			push(int32(int64(dividend) - int64(quotient)*int64(divisor)))
		}
		next(1)
	case op == 0x74:
		value := pop()
		push(int32(0 - uint32(value)))
		next(1)
	case op == 0x78 || op == 0x7a || op == 0x7c:
		distance, value := uint32(pop())&31, pop()
		switch op {
		case 0x78:
			push(int32(uint32(value) << distance))
		case 0x7a:
			push(value >> distance)
		case 0x7c:
			push(int32(uint32(value) >> distance))
		}
		next(1)
	case op == 0x7e || op == 0x80 || op == 0x82:
		right, left := uint32(pop()), uint32(pop())
		switch op {
		case 0x7e:
			push(int32(left & right))
		case 0x80:
			push(int32(left | right))
		case 0x82:
			push(int32(left ^ right))
		}
		next(1)
	case op == 0x84:
		index, delta := code[pc+1], int8(code[pc+2])
		if machine.Initialized&(1<<index) == 0 {
			t.Fatal("TEST trace iinc uninitialized")
		}
		value := int32(uint32(machine.Locals[index].Uint64()))
		machine.Locals[index] = stockS2aHarnessTagged(int32(uint32(value) + uint32(int32(delta))))
		next(3)
	case op == 0x91:
		push(int32(int8(pop())))
		next(1)
	case op == 0x92:
		push(int32(uint16(pop())))
		next(1)
	case op == 0x93:
		push(int32(int16(pop())))
		next(1)
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
	stockS2aHarnessAssertCanonicalMachine(t, *machine)
}

func stockS2aHarnessTagged(value int32) *big.Int {
	return new(big.Int).Or(new(big.Int).Lsh(big.NewInt(1), 64), new(big.Int).SetUint64(uint64(uint32(value))))
}

func stockS2aHarnessAssertCanonicalMachine(t *testing.T, machine stockS2aHarnessMachine) {
	t.Helper()
	if machine.SP > 8 || machine.Initialized&^uint8(0xff) != 0 || machine.Lifecycle > 3 || (machine.Lifecycle != 1 && machine.Result != 0) || (machine.Lifecycle == 1 && machine.SP != 0) || (machine.Lifecycle != 3 && (machine.JavaFaultKind != 0 || machine.FaultPC != 0)) || (machine.Lifecycle == 3 && (machine.JavaFaultKind != 1 || machine.PC != machine.FaultPC || machine.SP < 2)) {
		t.Fatalf("noncanonical machine scalars %+v", machine)
	}
	for i, cell := range machine.Stack {
		if cell == nil || (i >= int(machine.SP) && cell.Sign() != 0) || (i < int(machine.SP) && !stockS2aHarnessCanonicalTag(cell)) {
			t.Fatalf("noncanonical stack[%d]=%v sp=%d", i, cell, machine.SP)
		}
	}
	for i, cell := range machine.Locals {
		if cell == nil || (machine.Initialized&(1<<i) == 0 && cell.Sign() != 0) || (machine.Initialized&(1<<i) != 0 && !stockS2aHarnessCanonicalTag(cell)) {
			t.Fatalf("noncanonical local[%d]=%v initialized=%02x", i, cell, machine.Initialized)
		}
	}
}

func stockS2aHarnessCanonicalTag(value *big.Int) bool {
	if value.Sign() < 0 || value.BitLen() > 65 || value.Bit(64) != 1 {
		return false
	}
	return value.Cmp(stockS2aHarnessTagged(int32(uint32(value.Uint64())))) == 0
}

func stockS2aHarnessAssertCatalogueCells(t *testing.T, tc stockS2aHarnessCase, machine stockS2aHarnessMachine) {
	t.Helper()
	for i, value := range tc.Stack {
		want := new(big.Int)
		if i < int(tc.SP) {
			want = stockS2aHarnessTagged(value)
		}
		if machine.Stack[i].Cmp(want) != 0 {
			t.Fatalf("%s stack%d got %v want %v", tc.ID, i, machine.Stack[i], want)
		}
	}
	for i, value := range tc.Locals {
		want := new(big.Int)
		if tc.Initialized&(1<<i) != 0 {
			want = stockS2aHarnessTagged(value)
		}
		if machine.Locals[i].Cmp(want) != 0 {
			t.Fatalf("%s local%d got %v want %v", tc.ID, i, machine.Locals[i], want)
		}
	}
}

func stockS2aHarnessABIType(t *testing.T, name string) abi.Type {
	t.Helper()
	typ, err := abi.NewType(name, "", nil)
	if err != nil {
		t.Fatal(err)
	}
	return typ
}

func stockS2aHarnessABIPack(t *testing.T, types []string, values ...interface{}) []byte {
	t.Helper()
	arguments := make(abi.Arguments, len(types))
	for i, name := range types {
		arguments[i].Type = stockS2aHarnessABIType(t, name)
	}
	encoded, err := arguments.Pack(values...)
	if err != nil {
		t.Fatalf("abi.encode %v: %v", types, err)
	}
	return encoded
}

func stockS2aHarnessArgsHash(t *testing.T, args []int32) common.Hash {
	t.Helper()
	return crypto.Keccak256Hash(stockS2aHarnessABIPack(t, []string{"int32[]"}, args))
}

func stockS2aHarnessDomain(label string) common.Hash { return crypto.Keccak256Hash([]byte(label)) }

func stockS2aHarnessClassID(t *testing.T, parserHash common.Hash, class stockS2aHarnessClassDeployment) common.Hash {
	t.Helper()
	return crypto.Keccak256Hash(stockS2aHarnessABIPack(t,
		[]string{"bytes32", "uint32", "bytes32", "address", "bytes32", "bytes32", "bytes32"},
		stockS2aHarnessDomain("JVMEVM:S2A:CLASS"), uint32(3), parserHash, class.Page, class.PageHash, class.PayloadHash, class.MetadataHash))
}

func stockS2aHarnessProgramID(t *testing.T, classID common.Hash, tc stockS2aHarnessCase, moduleHash common.Hash) common.Hash {
	t.Helper()
	return crypto.Keccak256Hash(stockS2aHarnessABIPack(t,
		[]string{"bytes32", "uint32", "bytes32", "uint16", "bytes32", "bytes32", "bytes32"},
		stockS2aHarnessDomain("JVMEVM:S2A:PROGRAM"), uint32(3), classID, tc.MethodIndex,
		crypto.Keccak256Hash([]byte(tc.Entry)), crypto.Keccak256Hash([]byte(tc.Descriptor)), moduleHash))
}

func stockS2aHarnessInputRoot(t *testing.T, programID, argsHash common.Hash) common.Hash {
	t.Helper()
	return stockS2aHarnessInputRootFor(t, programID, argsHash, stockS2aHarnessMaxTotalSteps)
}

func stockS2aHarnessInputRootFor(t *testing.T, programID, argsHash common.Hash, maxTotalSteps uint64) common.Hash {
	t.Helper()
	return crypto.Keccak256Hash(stockS2aHarnessABIPack(t,
		[]string{"bytes32", "bytes32", "bytes32", "uint64"}, stockS2aHarnessDomain("JVMEVM:S2A:INPUT"), programID, argsHash, maxTotalSteps))
}

func stockS2aHarnessStateDigest(t *testing.T, inputRoot, parserHash, moduleHash common.Hash, machine stockS2aHarnessMachine, epoch, total uint64) common.Hash {
	t.Helper()
	machineType, err := abi.NewType("tuple", "", []abi.ArgumentMarshaling{
		{Name: "pc", Type: "uint32"}, {Name: "sp", Type: "uint8"}, {Name: "initialized", Type: "uint8"}, {Name: "lifecycle", Type: "uint8"},
		{Name: "stack", Type: "uint256[8]"}, {Name: "locals", Type: "uint256[8]"}, {Name: "result", Type: "int32"},
		{Name: "javaFaultKind", Type: "uint8"}, {Name: "faultPC", Type: "uint32"},
	})
	if err != nil {
		t.Fatal(err)
	}
	arguments := abi.Arguments{{Type: stockS2aHarnessABIType(t, "uint32")}, {Type: stockS2aHarnessABIType(t, "bytes32")}, {Type: stockS2aHarnessABIType(t, "bytes32")}, {Type: stockS2aHarnessABIType(t, "bytes32")}, {Type: machineType}, {Type: stockS2aHarnessABIType(t, "uint64")}, {Type: stockS2aHarnessABIType(t, "uint64")}}
	encoded, err := arguments.Pack(uint32(3), inputRoot, parserHash, moduleHash, machine, epoch, total)
	if err != nil {
		t.Fatal(err)
	}
	return crypto.Keccak256Hash(encoded)
}

func stockS2aHarnessNewEnvironment(t *testing.T, classes map[string]stockS2aHarnessClass) *stockS2aHarnessEnvironment {
	t.Helper()
	key, err := crypto.HexToECDSA(stockS2aHarnessTestKeyHex)
	if err != nil {
		t.Fatal(err)
	}
	sender := crypto.PubkeyToAddress(key.PublicKey)
	env := &stockS2aHarnessEnvironment{Key: key, Sender: sender, Classes: make(map[string]stockS2aHarnessClassDeployment)}
	env.Backend = stockS2aHarnessNewBackend(t, sender)

	parser := stockS2aHarnessLoadArtifact(t, S2aClassParser)
	module := stockS2aHarnessLoadArtifact(t, S2aStepModule)
	pageArtifact, err := stock.LoadArtifact(stock.ArtifactPage)
	if err != nil {
		t.Fatalf("accepted S0 page artifact dependency: %v", err)
	}
	env.Parser, env.ParserDeployGas = stockS2aHarnessDeploy(t, env, parser.InitCode, stockS2aHarnessCreateGas, "parser")
	env.Module, env.ModuleDeployGas = stockS2aHarnessDeploy(t, env, module.InitCode, stockS2aHarnessCreateGas, "module")
	env.ParserHash = crypto.Keccak256Hash(parser.RuntimeCode)
	env.ModuleHash = crypto.Keccak256Hash(module.RuntimeCode)
	stockS2aHarnessAssertExactCode(t, env, env.Parser, parser.RuntimeCode, "parser")
	stockS2aHarnessAssertExactCode(t, env, env.Module, module.RuntimeCode, "module")

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
		page, pageGas := stockS2aHarnessDeploy(t, env, append(append([]byte{}, pageArtifact.InitCode...), constructor...), stockS2aHarnessCreateGas, "page-"+name)
		pageCode := append([]byte{0}, class.Raw...)
		stockS2aHarnessAssertExactCode(t, env, page, pageCode, "raw page "+name)
		deployment := stockS2aHarnessClassDeployment{Class: class, Page: page, PageHash: crypto.Keccak256Hash(pageCode), PayloadHash: crypto.Keccak256Hash(class.Raw), PageGas: pageGas}
		deployment = stockS2aHarnessRegister(t, env, parser, deployment)
		env.Classes[name] = deployment
	}
	env.SharedSetupRecords = len(env.Records)
	if env.SharedSetupRecords != 24 {
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
		record := stockS2aHarnessSend(t, env, &env.Parser, data, stockS2aHarnessCreateGas, "register-idempotent-"+name, true)
		if len(record.Receipt.Logs) != 0 {
			t.Fatalf("idempotent registration %s emitted %d logs", name, len(record.Receipt.Logs))
		}
		page, hash := stockS2aHarnessClassRecord(t, env, parser.ABI, before.ClassID)
		if page != before.MetadataPage || hash != before.MetadataHash {
			t.Fatalf("idempotent registration %s changed registry", name)
		}
		if code := stockS2aHarnessCodeAt(t, env, before.MetadataPage); crypto.Keccak256Hash(code) != before.MetadataHash {
			t.Fatalf("idempotent registration %s changed metadata code", name)
		}
	}
	return env
}

func stockS2aHarnessLoadArtifact(t *testing.T, name string) stock.Artifact {
	t.Helper()
	artifact, err := LoadArtifact(name)
	if err != nil {
		t.Fatalf("required S2a artifact %s: %v", name, err)
	}
	return artifact
}

func stockS2aHarnessNewBackend(t *testing.T, sender common.Address) *simulated.Backend {
	t.Helper()
	config := *params.AllDevChainProtocolChanges
	backend := simulated.NewBackend(types.GenesisAlloc{
		sender: {Balance: new(big.Int).Exp(big.NewInt(10), big.NewInt(25), nil)},
	}, func(nodeConf *node.Config, ethConf *ethconfig.Config) {
		nodeConf.HTTPHost, nodeConf.WSHost, nodeConf.IPCPath = "", "", ""
		nodeConf.P2P = p2p.Config{ListenAddr: "", MaxPeers: 0, NoDiscovery: true, DiscoveryV4: false, DiscoveryV5: false}
		ethConf.Genesis = &core.Genesis{Config: &config, GasLimit: stockS2aHarnessBlockGas, Alloc: types.GenesisAlloc{
			sender: {Balance: new(big.Int).Exp(big.NewInt(10), big.NewInt(25), nil)},
		}}
		ethConf.Miner.GasCeil = stockS2aHarnessBlockGas
	})
	chainID, err := backend.Client().ChainID(context.Background())
	if err != nil || chainID.Uint64() != stockS2aHarnessChainID {
		t.Fatalf("simulated chain ID=%v err=%v", chainID, err)
	}
	return backend
}

func (env *stockS2aHarnessEnvironment) close(t *testing.T) {
	t.Helper()
	if err := env.Backend.Close(); err != nil {
		t.Errorf("close simulated backend: %v", err)
	}
}

func stockS2aHarnessSend(t *testing.T, env *stockS2aHarnessEnvironment, to *common.Address, data []byte, gas uint64, kind string, success bool) stockS2aHarnessTxRecord {
	t.Helper()
	if gas >= params.MaxTxGas || gas > stockS2aHarnessCreateGas || (to != nil && strings.HasPrefix(kind, "resume") && gas > stockS2aHarnessResumeGas) {
		t.Fatalf("%s gas %d violates frozen transaction bounds", kind, gas)
	}
	tx := types.NewTx(&types.DynamicFeeTx{ChainID: new(big.Int).SetUint64(stockS2aHarnessChainID), Nonce: env.Nonce,
		GasTipCap: new(big.Int).Set(stockS2aHarnessTipCap), GasFeeCap: new(big.Int).Set(stockS2aHarnessFeeCap), Gas: gas, To: to, Data: append([]byte(nil), data...)})
	signed, err := types.SignTx(tx, types.LatestSignerForChainID(new(big.Int).SetUint64(stockS2aHarnessChainID)), env.Key)
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
	if header.GasLimit != stockS2aHarnessBlockGas || !params.AllDevChainProtocolChanges.IsOsaka(header.Number, header.Time) {
		t.Fatalf("%s not frozen Osaka/30M context", kind)
	}
	record := stockS2aHarnessTxRecord{Kind: kind, Tx: signed, Header: header, Receipt: receipt}
	env.Records = append(env.Records, record)
	env.Nonce++
	return record
}

func stockS2aHarnessDeploy(t *testing.T, env *stockS2aHarnessEnvironment, initCode []byte, gas uint64, kind string) (common.Address, uint64) {
	t.Helper()
	if len(initCode) > params.MaxInitCodeSize {
		t.Fatalf("%s initcode=%d exceeds EIP-3860", kind, len(initCode))
	}
	nonce := env.Nonce
	record := stockS2aHarnessSend(t, env, nil, initCode, gas, "deploy-"+kind, true)
	address := crypto.CreateAddress(env.Sender, nonce)
	if record.Receipt.ContractAddress != address {
		t.Fatalf("%s CREATE address=%s want=%s", kind, record.Receipt.ContractAddress, address)
	}
	return address, record.Receipt.GasUsed
}

func stockS2aHarnessCodeAt(t *testing.T, env *stockS2aHarnessEnvironment, address common.Address) []byte {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	code, err := env.Backend.Client().CodeAt(ctx, address, nil)
	if err != nil {
		t.Fatal(err)
	}
	return code
}

func stockS2aHarnessAssertExactCode(t *testing.T, env *stockS2aHarnessEnvironment, address common.Address, want []byte, label string) {
	t.Helper()
	got := stockS2aHarnessCodeAt(t, env, address)
	if !bytes.Equal(got, want) {
		t.Fatalf("%s deployed code differs: got len/hash %d/%s want %d/%s", label, len(got), crypto.Keccak256Hash(got), len(want), crypto.Keccak256Hash(want))
	}
}

func stockS2aHarnessRegister(t *testing.T, env *stockS2aHarnessEnvironment, parser stock.Artifact, class stockS2aHarnessClassDeployment) stockS2aHarnessClassDeployment {
	t.Helper()
	data, err := parser.ABI.Pack("registerClass", class.Page, class.PageHash, class.PayloadHash)
	if err != nil {
		t.Fatal(err)
	}
	record := stockS2aHarnessSend(t, env, &env.Parser, data, stockS2aHarnessCreateGas, "register-"+class.Class.Name, true)
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
	metadataCode := stockS2aHarnessCodeAt(t, env, metadataPage)
	if len(metadataCode) < 1 || len(metadataCode) > 8192 || metadataCode[0] != 0 || crypto.Keccak256Hash(metadataCode) != class.MetadataHash {
		t.Fatalf("%s invalid immutable metadata page len/hash", class.Class.Name)
	}
	class.ClassID = stockS2aHarnessClassID(t, env.ParserHash, class)
	if common.Hash(log.Topics[1]) != class.ClassID {
		t.Fatalf("%s classId event=%s want=%s", class.Class.Name, log.Topics[1], class.ClassID)
	}
	page, hash := stockS2aHarnessClassRecord(t, env, parser.ABI, class.ClassID)
	if page != metadataPage || hash != class.MetadataHash {
		t.Fatalf("%s classRecord mismatch", class.Class.Name)
	}
	stockS2aHarnessAssertMetadata(t, class, metadataCode)
	return class
}

func stockS2aHarnessClassRecord(t *testing.T, env *stockS2aHarnessEnvironment, parserABI abi.ABI, classID common.Hash) (common.Address, common.Hash) {
	t.Helper()
	values := stockS2aHarnessCall(t, env, parserABI, env.Parser, "classRecord", classID)
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

func stockS2aHarnessCall(t *testing.T, env *stockS2aHarnessEnvironment, contractABI abi.ABI, address common.Address, method string, args ...interface{}) []interface{} {
	t.Helper()
	data, err := contractABI.Pack(method, args...)
	if err != nil {
		t.Fatalf("pack %s: %v", method, err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	output, err := env.Backend.Client().CallContract(ctx, ethereum.CallMsg{To: &address, Gas: stockS2aHarnessResumeGas, Data: data}, nil)
	if err != nil {
		t.Fatalf("call %s: %v", method, err)
	}
	values, err := contractABI.Unpack(method, output)
	if err != nil {
		t.Fatalf("unpack %s: %v", method, err)
	}
	return values
}

func stockS2aHarnessAssertMetadata(t *testing.T, class stockS2aHarnessClassDeployment, code []byte) {
	t.Helper()
	payload := code[1:]
	word := func(i int) []byte {
		start := i * 32
		if start+32 > len(payload) {
			t.Fatalf("%s metadata truncated at word %d", class.Class.Name, i)
		}
		return payload[start : start+32]
	}
	if common.BytesToHash(word(0)) != stockS2aHarnessDomain("JVMEVM:S2A:METADATA:3") || common.BytesToAddress(word(1)[12:]) != class.Page || common.BytesToHash(word(2)) != class.PageHash || common.BytesToHash(word(3)) != class.PayloadHash || common.BytesToHash(word(4)) != crypto.Keccak256Hash([]byte(class.Class.Name)) {
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
	literals := stockS2aHarnessExpectedLiterals(t, class.Class)
	if rawLength != uint32(len(class.Class.Raw)) || cpCount != class.Class.CPCount || methodCount != class.DeclaredMethods || methodCount != uint16(len(class.Class.Methods)) || literalCount != uint16(len(literals)) || len(payload) != 6*32+int(methodCount)*4*32+len(literals)*8 {
		t.Fatalf("%s metadata counts raw=%d cp=%d methods=%d/%d literals=%d/%d bytes=%d", class.Class.Name, rawLength, cpCount, methodCount, len(class.Class.Methods), literalCount, len(literals), len(payload))
	}
	literalBase := uint16(0)
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
		if method.Name == "<init>" || len(method.Code) > 256 {
			wantCode := uint64(6)
			if len(method.Code) > 256 {
				wantCode = 5
			}
			if field(32, 0xffffffffffffffff) != 0 || field(96, 0xff) != 0 || field(104, 0xff) != 1 || field(112, 0xff) != wantCode || field(120, 0xffffffff) != uint64(method.Index) || field(152, 0xffffffff) != 0 || new(big.Int).SetBytes(word(base+3)).Sign() != 0 {
				t.Fatalf("%s method %d ineligible packed metadata=%x", class.Class.Name, method.Index, packed)
			}
			continue
		}
		argc := strings.Count(strings.TrimSuffix(strings.TrimPrefix(method.Descriptor, "("), ")I"), "I")
		methodLiterals := stockS2aHarnessMethodLiterals(t, class.Class, method)
		if field(32, 0xffffffff) != uint64(method.CodeOffset) || field(64, 0xffff) != uint64(len(method.Code)) || field(80, 0xff) != uint64(method.MaxStack) || field(88, 0xff) != uint64(method.MaxLocals) || field(96, 0xff) != uint64(argc) || field(104, 0xff) != 0 || field(112, 0xff) != 0 || field(120, 0xffffffff) != 0 || field(152, 0xffff) != uint64(literalBase) || field(168, 0xffff) != uint64(len(methodLiterals)) {
			t.Fatalf("%s method %d eligible packed metadata=%x", class.Class.Name, method.Index, packed)
		}
		literalBase += uint16(len(methodLiterals))
		starts := stockS2aHarnessInstructionStarts(t, method.Code)
		if new(big.Int).SetBytes(word(base+3)).Cmp(starts) != 0 {
			t.Fatalf("%s method %d instruction-start map", class.Class.Name, method.Index)
		}
	}
	literalOffset := 6*32 + int(methodCount)*4*32
	for i, literal := range literals {
		got := payload[literalOffset+i*8 : literalOffset+(i+1)*8]
		if binary.BigEndian.Uint16(got) != literal.Method || binary.BigEndian.Uint16(got[2:]) != literal.PC || binary.BigEndian.Uint32(got[4:]) != literal.Bits {
			t.Fatalf("%s literal %d got=%x want=%+v", class.Class.Name, i, got, literal)
		}
	}
}

type stockS2aHarnessLiteral struct {
	Method uint16
	PC     uint16
	Bits   uint32
}

func stockS2aHarnessExpectedLiterals(t *testing.T, class stockS2aHarnessClass) []stockS2aHarnessLiteral {
	t.Helper()
	var out []stockS2aHarnessLiteral
	for _, method := range class.Methods {
		if method.Name == "<init>" || len(method.Code) > 256 {
			continue
		}
		out = append(out, stockS2aHarnessMethodLiterals(t, class, method)...)
	}
	return out
}

func stockS2aHarnessMethodLiterals(t *testing.T, class stockS2aHarnessClass, method stockS2aHarnessMethod) []stockS2aHarnessLiteral {
	t.Helper()
	var out []stockS2aHarnessLiteral
	for pc := 0; pc < len(method.Code); {
		op := method.Code[pc]
		width := stockS2aHarnessInstructionWidth(t, method.Code, pc)
		if op == 0x12 || op == 0x13 {
			index := uint16(method.Code[pc+1])
			if op == 0x13 {
				index = binary.BigEndian.Uint16(method.Code[pc+1 : pc+3])
			}
			value, ok := class.CPInts[index]
			if !ok {
				t.Fatalf("%s.%s literal at pc %d is not CONSTANT_Integer", class.Name, method.Name, pc)
			}
			out = append(out, stockS2aHarnessLiteral{Method: method.Index, PC: uint16(pc), Bits: uint32(value)})
		}
		pc += width
	}
	return out
}

func stockS2aHarnessInstructionWidth(t *testing.T, code []byte, pc int) int {
	t.Helper()
	op := code[pc]
	width := 0
	switch {
	case op == 0x00, op >= 0x02 && op <= 0x08, op >= 0x1a && op <= 0x1d, op >= 0x3b && op <= 0x3e, op == 0x60, op == 0x64, op == 0x68, op == 0x6c, op == 0x70, op == 0x74, op == 0x78, op == 0x7a, op == 0x7c, op == 0x7e, op == 0x80, op == 0x82, op == 0x91, op == 0x92, op == 0x93, op == 0xac:
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
	return width
}

func stockS2aHarnessInstructionStarts(t *testing.T, code []byte) *big.Int {
	t.Helper()
	starts := new(big.Int)
	for pc := 0; pc < len(code); {
		starts.SetBit(starts, pc, 1)
		pc += stockS2aHarnessInstructionWidth(t, code, pc)
	}
	return starts
}

func stockS2aHarnessRunCase(t *testing.T, env *stockS2aHarnessEnvironment, tc stockS2aHarnessCase, budget uint16, resumeLimit int) stockS2aHarnessCaseRun {
	t.Helper()
	if budget == 0 || budget > 128 {
		t.Fatalf("%s invalid budget %d", tc.ID, budget)
	}
	class := env.Classes[tc.Class]
	coordinator := stockS2aHarnessLoadArtifact(t, S2aCoordinator)
	constructor, err := coordinator.ABI.Pack("", env.Parser, env.ParserHash, class.ClassID, env.Module, env.ModuleHash, []byte(tc.Entry), tc.Args, stockS2aHarnessMaxTotalSteps)
	if err != nil {
		t.Fatalf("%s coordinator constructor: %v", tc.ID, err)
	}
	address, createGas := stockS2aHarnessDeploy(t, env, append(append([]byte{}, coordinator.InitCode...), constructor...), stockS2aHarnessCreateGas, "coordinator-"+tc.ID+fmt.Sprintf("-b%d", budget))
	actual := stockS2aHarnessCodeAt(t, env, address)
	stockS2aHarnessAssertCoordinatorTemplate(t, coordinator.RuntimeCode, actual)

	programID := stockS2aHarnessProgramID(t, class.ClassID, tc, env.ModuleHash)
	argsHash := stockS2aHarnessArgsHash(t, tc.Args)
	inputRoot := stockS2aHarnessInputRoot(t, programID, argsHash)
	stockS2aHarnessAssertCoordinatorGetters(t, env, coordinator.ABI, address, class, tc, programID, argsHash, inputRoot, stockS2aHarnessMaxTotalSteps)
	checkpoint := stockS2aHarnessReadCheckpoint(t, env, coordinator.ABI, address)
	initial := stockS2aHarnessTracePrefix(t, class.Class, stockS2aHarnessMethodNamed(t, class.Class, tc.Entry), tc.Args, 0)
	stockS2aHarnessAssertCheckpoint(t, env, tc, class, checkpoint, initial, 0, 0, programID, inputRoot)

	run := stockS2aHarnessCaseRun{Case: tc, Budget: budget, Coordinator: address, Gas: createGas}
	method := stockS2aHarnessMethodNamed(t, class.Class, tc.Entry)
	for checkpoint.Machine.Lifecycle == 0 && (resumeLimit == 0 || run.Resumes < resumeLimit) {
		before := checkpoint
		data, err := coordinator.ABI.Pack("resume", checkpoint.Epoch, budget, uint8(32))
		if err != nil {
			t.Fatal(err)
		}
		record := stockS2aHarnessSend(t, env, &address, data, stockS2aHarnessResumeGas, "resume-"+tc.ID+fmt.Sprintf("-b%d-e%d", budget, checkpoint.Epoch), true)
		run.Gas += record.Receipt.GasUsed
		run.Resumes++
		checkpoint = stockS2aHarnessReadCheckpoint(t, env, coordinator.ABI, address)
		if checkpoint.Epoch != before.Epoch+1 || checkpoint.TotalSteps <= before.TotalSteps || checkpoint.TotalSteps-before.TotalSteps > uint64(budget) {
			t.Fatalf("%s invalid epoch/step transition before=%d/%d after=%d/%d", tc.ID, before.Epoch, before.TotalSteps, checkpoint.Epoch, checkpoint.TotalSteps)
		}
		if checkpoint.Machine.PC == before.Machine.PC && checkpoint.Machine.Lifecycle == 0 {
			run.SamePC++
		}
		model := stockS2aHarnessTracePrefix(t, class.Class, method, tc.Args, checkpoint.TotalSteps)
		stockS2aHarnessAssertCheckpoint(t, env, tc, class, checkpoint, model, checkpoint.Epoch, checkpoint.TotalSteps, programID, inputRoot)
		event := stockS2aHarnessDecodeEvent(t, coordinator.ABI, record.Receipt)
		stockS2aHarnessAssertEvent(t, tc, before, checkpoint, event, budget)
		if run.Resumes > 13 && resumeLimit == 0 {
			t.Fatalf("%s budget=%d exceeds frozen max 13 resumes at the primary budgets", tc.ID, budget)
		}
	}
	run.Checkpoint = checkpoint
	if resumeLimit == 0 {
		if checkpoint.Machine.Lifecycle != tc.Lifecycle || checkpoint.TotalSteps != tc.Steps || checkpoint.Machine.Result != tc.Expected || checkpoint.Machine.JavaFaultKind != tc.JavaFaultKind || checkpoint.Machine.FaultPC != tc.FaultPC {
			t.Fatalf("%s budget=%d did not terminate exactly: %+v", tc.ID, budget, checkpoint)
		}
		stockS2aHarnessAssertCatalogueCells(t, tc, checkpoint.Machine)
	}
	env.Runs = append(env.Runs, run)
	return run
}

func stockS2aHarnessLongLoop(tc stockS2aHarnessCase) bool {
	return tc.Class == "Loops" && (tc.Entry == "sum" || tc.Entry == "fibonacci")
}

func stockS2aHarnessAssertCaseBounds(t *testing.T, env *stockS2aHarnessEnvironment, run stockS2aHarnessCaseRun, terminal bool) {
	t.Helper()
	class := env.Classes[run.Case.Class]
	isolatedGas := env.ParserDeployGas + env.ModuleDeployGas + class.PageGas + class.RegisterGas + run.Gas
	isolatedTx := 4 + 1 + run.Resumes
	if terminal && (isolatedTx > 19 || isolatedGas > 30_000_000) {
		t.Fatalf("%s budget=%d isolated positive tx/gas=%d/%d exceeds 19/30M", run.Case.ID, run.Budget, isolatedTx, isolatedGas)
	}
	for _, record := range env.Records[len(env.Records)-run.Resumes:] {
		if record.Receipt.GasUsed > stockS2aHarnessResumeGas {
			t.Fatalf("%s resume gas=%d", run.Case.ID, record.Receipt.GasUsed)
		}
	}
}

func stockS2aHarnessAssertCoordinatorTemplate(t *testing.T, template, actual []byte) {
	t.Helper()
	if len(actual) != len(template) {
		t.Fatalf("coordinator runtime len=%d want template=%d", len(actual), len(template))
	}
	refs, err := CompilerImmutableReferences(S2aCoordinator)
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

func stockS2aHarnessAssertCoordinatorGetters(t *testing.T, env *stockS2aHarnessEnvironment, contractABI abi.ABI, address common.Address, class stockS2aHarnessClassDeployment, tc stockS2aHarnessCase, programID, argsHash, inputRoot common.Hash, maxTotalSteps uint64) {
	t.Helper()
	checks := map[string]interface{}{
		"parser": env.Parser, "expectedParserHash": env.ParserHash, "module": env.Module, "expectedModuleHash": env.ModuleHash,
		"classId": class.ClassID, "programId": programID, "argsHash": argsHash, "inputRoot": inputRoot, "maxTotalSteps": maxTotalSteps,
	}
	names := make([]string, 0, len(checks))
	for name := range checks {
		names = append(names, name)
	}
	sort.Strings(names)
	for _, name := range names {
		values := stockS2aHarnessCall(t, env, contractABI, address, name)
		if len(values) != 1 || !stockS2aHarnessABIEqual(values[0], checks[name]) {
			t.Fatalf("%s getter %s got %v want %v", tc.ID, name, values, checks[name])
		}
	}
	values := stockS2aHarnessCall(t, env, contractABI, address, "programContext")
	if len(values) != 1 {
		t.Fatalf("%s programContext outputs=%d", tc.ID, len(values))
	}
	contextValue, ok := abi.ConvertType(values[0], new(stockS2aHarnessProgramContext)).(*stockS2aHarnessProgramContext)
	if !ok || contextValue.Parser != env.Parser || common.Hash(contextValue.ParserCodeHash) != env.ParserHash || common.Hash(contextValue.ClassID) != class.ClassID || contextValue.RawPage != class.Page || common.Hash(contextValue.RawPageHash) != class.PageHash || common.Hash(contextValue.PayloadHash) != class.PayloadHash || contextValue.MetadataPage != class.MetadataPage || common.Hash(contextValue.MetadataHash) != class.MetadataHash || contextValue.MethodIndex != tc.MethodIndex || common.Hash(contextValue.ProgramID) != programID {
		t.Fatalf("%s programContext mismatch %+v", tc.ID, contextValue)
	}
}

func stockS2aHarnessABIEqual(got, want interface{}) bool {
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

func stockS2aHarnessReadCheckpoint(t *testing.T, env *stockS2aHarnessEnvironment, contractABI abi.ABI, address common.Address) stockS2aHarnessCheckpoint {
	t.Helper()
	data, err := contractABI.Pack("checkpoint")
	if err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	output, err := env.Backend.Client().CallContract(ctx, ethereum.CallMsg{To: &address, Gas: stockS2aHarnessResumeGas, Data: data}, nil)
	if err != nil {
		t.Fatalf("checkpoint call: %v", err)
	}
	return stockS2aHarnessDecodeCheckpoint(t, contractABI, output)
}

func stockS2aHarnessDecodeCheckpoint(t *testing.T, contractABI abi.ABI, output []byte) stockS2aHarnessCheckpoint {
	t.Helper()
	values, err := contractABI.Unpack("checkpoint", output)
	if err != nil || len(values) != 8 {
		t.Fatalf("checkpoint decode values=%d err=%v", len(values), err)
	}
	machine, ok := abi.ConvertType(values[7], new(stockS2aHarnessMachine)).(*stockS2aHarnessMachine)
	if !ok {
		t.Fatalf("checkpoint machine type %T", values[7])
	}
	checkpoint := stockS2aHarnessCheckpoint{Machine: *machine}
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

func stockS2aHarnessAssertCheckpoint(t *testing.T, env *stockS2aHarnessEnvironment, tc stockS2aHarnessCase, class stockS2aHarnessClassDeployment, checkpoint stockS2aHarnessCheckpoint, model stockS2aHarnessMachine, epoch, total uint64, programID, inputRoot common.Hash) {
	t.Helper()
	if checkpoint.Schema != 3 || common.Hash(checkpoint.ClassID) != class.ClassID || common.Hash(checkpoint.ProgramID) != programID || common.Hash(checkpoint.InputRoot) != inputRoot || checkpoint.Epoch != epoch || checkpoint.TotalSteps != total || !stockS2aHarnessMachineEqual(checkpoint.Machine, model) {
		t.Fatalf("%s checkpoint mismatch got=%+v model=%+v", tc.ID, checkpoint, model)
	}
	stockS2aHarnessAssertCanonicalMachine(t, checkpoint.Machine)
	if checkpoint.Machine.Lifecycle == 3 {
		method := stockS2aHarnessMethodNamed(t, class.Class, tc.Entry)
		pc := checkpoint.Machine.FaultPC
		if pc >= uint32(len(method.Code)) || (method.Code[pc] != 0x6c && method.Code[pc] != 0x70) || checkpoint.Machine.Stack[checkpoint.Machine.SP-1].Cmp(stockS2aHarnessTagged(0)) != 0 {
			t.Fatalf("%s malformed fault provenance pc=%d sp=%d", tc.ID, pc, checkpoint.Machine.SP)
		}
	}
	wantDigest := stockS2aHarnessStateDigest(t, inputRoot, env.ParserHash, env.ModuleHash, checkpoint.Machine, epoch, total)
	if common.Hash(checkpoint.StateDigest) != wantDigest {
		t.Fatalf("%s stateDigest=%x want=%s", tc.ID, checkpoint.StateDigest, wantDigest)
	}
}

func stockS2aHarnessMachineEqual(a, b stockS2aHarnessMachine) bool {
	if a.PC != b.PC || a.SP != b.SP || a.Initialized != b.Initialized || a.Lifecycle != b.Lifecycle || a.Result != b.Result || a.JavaFaultKind != b.JavaFaultKind || a.FaultPC != b.FaultPC {
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

func stockS2aHarnessDecodeEvent(t *testing.T, contractABI abi.ABI, receipt *types.Receipt) stockS2aHarnessEvent {
	t.Helper()
	eventABI, ok := contractABI.Events["CheckpointV3"]
	if !ok {
		t.Fatal("coordinator ABI has no CheckpointV3")
	}
	if len(receipt.Logs) != 1 || len(receipt.Logs[0].Topics) != 3 || receipt.Logs[0].Topics[0] != eventABI.ID {
		t.Fatalf("resume logs malformed count=%d", len(receipt.Logs))
	}
	var event stockS2aHarnessEvent
	event.Epoch = new(big.Int).SetBytes(receipt.Logs[0].Topics[1][:]).Uint64()
	event.ProgramID = receipt.Logs[0].Topics[2]
	if err := contractABI.UnpackIntoInterface(&event, "CheckpointV3", receipt.Logs[0].Data); err != nil {
		t.Fatalf("decode CheckpointV3: %v", err)
	}
	return event
}

func stockS2aHarnessAssertEvent(t *testing.T, tc stockS2aHarnessCase, before, after stockS2aHarnessCheckpoint, event stockS2aHarnessEvent, budget uint16) {
	t.Helper()
	executed := uint16(after.TotalSteps - before.TotalSteps)
	if event.Epoch != after.Epoch || common.Hash(event.ProgramID) != common.Hash(after.ProgramID) || event.TotalSteps != after.TotalSteps || event.PC != after.Machine.PC || event.SP != after.Machine.SP || event.Lifecycle != after.Machine.Lifecycle || event.JavaFaultKind != after.Machine.JavaFaultKind || event.Result != after.Machine.Result || event.Executed != executed || executed == 0 || executed > budget || common.Hash(event.StateDigest) != common.Hash(after.StateDigest) {
		t.Fatalf("%s CheckpointV3 does not match checkpoint: event=%+v after=%+v", tc.ID, event, after)
	}
	actualDirty := stockS2aHarnessDirtyWords(before, after)
	if event.DirtyWords < actualDirty || event.DirtyWords > 32 {
		t.Fatalf("%s dirtyWords=%d actual logical=%d", tc.ID, event.DirtyWords, actualDirty)
	}
}

func stockS2aHarnessDirtyWords(before, after stockS2aHarnessCheckpoint) uint8 {
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
	if before.Machine.JavaFaultKind != after.Machine.JavaFaultKind {
		changed++
	}
	if before.Machine.FaultPC != after.Machine.FaultPC {
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

type stockS2aHarnessDirectResult struct {
	Root        common.Hash
	Gas         []uint64
	Checkpoints map[common.Address]stockS2aHarnessCheckpoint
}

func stockS2aHarnessReplayDirect(t *testing.T, env *stockS2aHarnessEnvironment) stockS2aHarnessDirectResult {
	t.Helper()
	config := *params.AllDevChainProtocolChanges
	genesis := &core.Genesis{Config: &config, GasLimit: stockS2aHarnessBlockGas, Alloc: types.GenesisAlloc{
		env.Sender: {Balance: new(big.Int).Exp(big.NewInt(10), big.NewInt(25), nil)},
	}}
	disk := rawdb.NewMemoryDatabase()
	trieDB := triedb.NewDatabase(disk, triedb.HashDefaults)
	genesisBlock := genesis.MustCommit(disk, trieDB)
	stateDB, err := state.New(genesisBlock.Root(), state.NewDatabase(trieDB, nil))
	if err != nil {
		t.Fatal(err)
	}
	result := stockS2aHarnessDirectResult{Gas: make([]uint64, 0, len(env.Records)), Checkpoints: make(map[common.Address]stockS2aHarnessCheckpoint)}
	for index, record := range env.Records {
		header := record.Header
		if !config.IsOsaka(header.Number, header.Time) || header.GasLimit != stockS2aHarnessBlockGas {
			t.Fatal("direct replay context is not frozen Osaka/30M")
		}
		message, err := core.TransactionToMessage(record.Tx, types.LatestSignerForChainID(new(big.Int).SetUint64(stockS2aHarnessChainID)), header.BaseFee)
		if err != nil {
			t.Fatalf("TransactionToMessage %s: %v", record.Kind, err)
		}
		if message.From != env.Sender || message.Nonce != uint64(index) || message.SkipNonceChecks || message.SkipTransactionChecks {
			t.Fatalf("%s signed message recovery/checks mismatch", record.Kind)
		}
		stateDB.SetTxContext(record.Tx.Hash(), index)
		evm := vm.NewEVM(stockS2aHarnessBlockContext(header), stateDB, &config, vm.Config{})
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
	parser := stockS2aHarnessLoadArtifact(t, S2aClassParser)
	module := stockS2aHarnessLoadArtifact(t, S2aStepModule)
	coordinator := stockS2aHarnessLoadArtifact(t, S2aCoordinator)
	if !bytes.Equal(stateDB.GetCode(env.Parser), parser.RuntimeCode) || !bytes.Equal(stateDB.GetCode(env.Module), module.RuntimeCode) {
		t.Fatal("direct replay changed parser/module deployed bytes")
	}
	for _, class := range env.Classes {
		if !bytes.Equal(stateDB.GetCode(class.Page), append([]byte{0}, class.Class.Raw...)) || crypto.Keccak256Hash(stateDB.GetCode(class.MetadataPage)) != class.MetadataHash {
			t.Fatalf("direct replay class/metadata page mismatch %s", class.Class.Name)
		}
	}
	last := stockS2aHarnessBlockContext(env.Records[len(env.Records)-1].Header)
	for _, run := range env.Runs {
		stockS2aHarnessAssertCoordinatorTemplate(t, coordinator.RuntimeCode, stateDB.GetCode(run.Coordinator))
		checkpoint := stockS2aHarnessReadCheckpointDirect(t, stateDB, &config, last, coordinator.ABI, run.Coordinator)
		if !stockS2aHarnessCheckpointEqual(checkpoint, run.Checkpoint) {
			t.Fatalf("direct replay checkpoint mismatch %s budget=%d", run.Case.ID, run.Budget)
		}
		result.Checkpoints[run.Coordinator] = checkpoint
	}
	return result
}

func stockS2aHarnessCheckpointEqual(a, b stockS2aHarnessCheckpoint) bool {
	return a.Schema == b.Schema && a.ClassID == b.ClassID && a.ProgramID == b.ProgramID && a.InputRoot == b.InputRoot && a.Epoch == b.Epoch && a.TotalSteps == b.TotalSteps && a.StateDigest == b.StateDigest && stockS2aHarnessMachineEqual(a.Machine, b.Machine)
}

func stockS2aHarnessBlockContext(header *types.Header) vm.BlockContext {
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

func stockS2aHarnessReadCheckpointDirect(t *testing.T, stateDB *state.StateDB, config *params.ChainConfig, blockContext vm.BlockContext, contractABI abi.ABI, address common.Address) stockS2aHarnessCheckpoint {
	t.Helper()
	data, err := contractABI.Pack("checkpoint")
	if err != nil {
		t.Fatal(err)
	}
	evm := vm.NewEVM(blockContext, stateDB, config, vm.Config{})
	output, _, err := evm.StaticCall(common.Address{}, address, data, stockS2aHarnessResumeGas)
	if err != nil {
		t.Fatalf("direct checkpoint: %v", err)
	}
	return stockS2aHarnessDecodeCheckpoint(t, contractABI, output)
}

func stockS2aHarnessReceiptGas(records []stockS2aHarnessTxRecord) []uint64 {
	gas := make([]uint64, len(records))
	for i, record := range records {
		gas[i] = record.Receipt.GasUsed
	}
	return gas
}

func stockS2aHarnessSumGas(records []stockS2aHarnessTxRecord) uint64 {
	var gas uint64
	for _, record := range records {
		gas += record.Receipt.GasUsed
	}
	return gas
}

func stockS2aHarnessGasAccounting(records []stockS2aHarnessTxRecord) (map[string]uint64, map[string]int) {
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
