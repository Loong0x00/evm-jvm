package stock

import (
	"bytes"
	"context"
	"crypto/ecdsa"
	"crypto/sha256"
	"encoding/hex"
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
	"github.com/ethereum/go-ethereum/node"
	"github.com/ethereum/go-ethereum/p2p"
	"github.com/ethereum/go-ethereum/params"
	"github.com/ethereum/go-ethereum/triedb"
)

const (
	stockHarnessChainID     = uint64(1337)
	stockHarnessBlockGas    = uint64(30_000_000)
	stockHarnessCreateGas   = uint64(8_000_000)
	stockHarnessResumeGas   = uint64(2_000_000)
	stockHarnessFixtureRoot = "../testdata/stock"
	stockHarnessTestKeyHex  = "b71c71a67e1177ad4e901695e1b4b9ee17ae16c6668d313eac2f96dbcda3f291"
)

var (
	stockHarnessFeeCap = new(big.Int).Mul(big.NewInt(100), big.NewInt(params.GWei))
	stockHarnessTipCap = new(big.Int).SetUint64(params.GWei)
)

type stockHarnessFixtureManifest struct {
	Schema            uint64                `json:"schema"`
	CompilerCommand   []string              `json:"compilerCommand"`
	CompilerUsedToPin string                `json:"compilerUsedToPin"`
	Fixtures          []stockHarnessFixture `json:"fixtures"`
}

type stockHarnessFixture struct {
	Name         string `json:"name"`
	Source       string `json:"source"`
	ClassHex     string `json:"classHex"`
	SourceSHA256 string `json:"sourceSha256"`
	ClassSHA256  string `json:"classSha256"`
	ClassBytes   int    `json:"classBytes"`
	Expected     int32  `json:"expected"`
	Note         string `json:"note"`
	Raw          []byte `json:"-"`
}

type stockHarnessMachine struct {
	PC          uint32      `abi:"pc"`
	SP          uint8       `abi:"sp"`
	Initialized uint8       `abi:"initialized"`
	Stack       [8]*big.Int `abi:"stack"`
	Locals      [4]*big.Int `abi:"locals"`
	Done        bool        `abi:"done"`
	Result      int32       `abi:"result"`
}

type stockHarnessCheckpoint struct {
	Epoch       uint64              `abi:"epoch"`
	TotalSteps  uint64              `abi:"totalSteps"`
	StateDigest [32]byte            `abi:"stateDigest"`
	Machine     stockHarnessMachine `abi:"machine"`
}

type stockHarnessEvent struct {
	Epoch       uint64
	TotalSteps  uint64   `abi:"totalSteps"`
	PC          uint32   `abi:"pc"`
	SP          uint8    `abi:"sp"`
	Done        bool     `abi:"done"`
	Result      int32    `abi:"result"`
	Executed    uint8    `abi:"executed"`
	DirtyWords  uint8    `abi:"dirtyWords"`
	StateDigest [32]byte `abi:"stateDigest"`
}

type stockHarnessExpectedTerminal struct {
	steps       uint64
	pc          uint32
	initialized uint8
	locals      [4]int32
}

var stockHarnessExpectedTerminals = map[string]stockHarnessExpectedTerminal{
	"CanonicalTwelve":    {steps: 7, pc: 9, initialized: 1, locals: [4]int32{4}},
	"OverflowAdd":        {steps: 6, pc: 7, initialized: 1, locals: [4]int32{2147483647}},
	"OverflowMultiply":   {steps: 6, pc: 7, initialized: 1, locals: [4]int32{1073741824}},
	"MinimumNegation":    {steps: 5, pc: 6, initialized: 1, locals: [4]int32{-2147483648}},
	"IincWrap":           {steps: 5, pc: 8, initialized: 1, locals: [4]int32{-2147483648}},
	"NegativeImmediates": {steps: 8, pc: 11, initialized: 3, locals: [4]int32{-100, -30000}},
	"LiveStackLocals":    {steps: 10, pc: 11, initialized: 3, locals: [4]int32{7, 4}},
	"WideLdc":            {steps: 4, pc: 6, initialized: 1, locals: [4]int32{123456789}},
}

type stockHarnessTxRecord struct {
	Kind    string
	Tx      *types.Transaction
	Header  *types.Header
	Receipt *types.Receipt
}

type stockHarnessRun struct {
	Fixture      stockHarnessFixture
	Budget       uint8
	Sender       common.Address
	Page         common.Address
	Module       common.Address
	Coordinator  common.Address
	PageHash     common.Hash
	PayloadHash  common.Hash
	ModuleHash   common.Hash
	Checkpoint   stockHarnessCheckpoint
	Checkpoints  []stockHarnessCheckpoint
	Events       []stockHarnessEvent
	Records      []stockHarnessTxRecord
	PositiveGas  uint64
	NegativeGas  uint64
	PositiveTxs  int
	HeaderHashes []common.Hash
	StateRoots   []common.Hash
}

func stockHarnessLoadFixtures(t *testing.T) []stockHarnessFixture {
	t.Helper()
	raw, err := os.ReadFile(filepath.Join(stockHarnessFixtureRoot, "manifest.json"))
	if err != nil {
		t.Fatal(err)
	}
	var manifest stockHarnessFixtureManifest
	if err := json.Unmarshal(raw, &manifest); err != nil {
		t.Fatal(err)
	}
	if manifest.Schema != 1 || len(manifest.Fixtures) < 8 {
		t.Fatalf("invalid stock fixture manifest schema=%d fixtures=%d", manifest.Schema, len(manifest.Fixtures))
	}
	seen := make(map[string]bool)
	for i := range manifest.Fixtures {
		fixture := &manifest.Fixtures[i]
		if seen[fixture.Name] || fixture.Name == "" {
			t.Fatalf("duplicate/empty fixture name %q", fixture.Name)
		}
		seen[fixture.Name] = true
		source, err := os.ReadFile(filepath.Join(stockHarnessFixtureRoot, fixture.Source))
		if err != nil {
			t.Fatal(err)
		}
		if got := fmt.Sprintf("%x", sha256.Sum256(source)); got != fixture.SourceSHA256 {
			t.Fatalf("%s source hash got %s want %s", fixture.Name, got, fixture.SourceSHA256)
		}
		hexBytes, err := os.ReadFile(filepath.Join(stockHarnessFixtureRoot, fixture.ClassHex))
		if err != nil {
			t.Fatal(err)
		}
		fixture.Raw, err = hex.DecodeString(strings.TrimSpace(string(hexBytes)))
		if err != nil {
			t.Fatalf("%s class hex: %v", fixture.Name, err)
		}
		if len(fixture.Raw) != fixture.ClassBytes || len(fixture.Raw) > 4096 {
			t.Fatalf("%s class size got %d manifest %d limit 4096", fixture.Name, len(fixture.Raw), fixture.ClassBytes)
		}
		if got := fmt.Sprintf("%x", sha256.Sum256(fixture.Raw)); got != fixture.ClassSHA256 {
			t.Fatalf("%s class hash got %s want %s", fixture.Name, got, fixture.ClassSHA256)
		}
		if _, ok := stockHarnessExpectedTerminals[fixture.Name]; !ok {
			t.Fatalf("%s has no independently pinned terminal state", fixture.Name)
		}
	}
	return manifest.Fixtures
}

func TestStockHarnessTrustedFixturesRegenerateAndJVMOracle(t *testing.T) {
	fixtures := stockHarnessLoadFixtures(t)
	javac, err := exec.LookPath("javac")
	if err != nil {
		t.Fatalf("trusted fixture check requires javac: %v", err)
	}
	java, err := exec.LookPath("java")
	if err != nil {
		t.Fatalf("trusted JVM oracle requires java: %v", err)
	}
	outDir := t.TempDir()
	args := []string{"--release", "8", "-g:none", "-d", outDir}
	for _, fixture := range fixtures {
		args = append(args, filepath.Join(stockHarnessFixtureRoot, fixture.Source))
	}
	args = append(args, filepath.Join(stockHarnessFixtureRoot, "oracle", "StockOracle.java"))
	cmd := exec.Command(javac, args...)
	if output, err := cmd.CombinedOutput(); err != nil {
		t.Fatalf("javac --release 8 fixture regeneration: %v\n%s", err, output)
	}
	for _, fixture := range fixtures {
		compiled, err := os.ReadFile(filepath.Join(outDir, fixture.Name+".class"))
		if err != nil {
			t.Fatal(err)
		}
		if !bytes.Equal(compiled, fixture.Raw) {
			t.Fatalf("%s changed under deterministic javac --release 8 -g:none: got sha256 %x want %s", fixture.Name, sha256.Sum256(compiled), fixture.ClassSHA256)
		}
		output, err := exec.Command(java, "-cp", outDir, "StockOracle", fixture.Name).CombinedOutput()
		if err != nil {
			t.Fatalf("trusted JVM oracle %s: %v\n%s", fixture.Name, err, output)
		}
		got, err := strconv.ParseInt(strings.TrimSpace(string(output)), 10, 32)
		if err != nil || int32(got) != fixture.Expected {
			t.Fatalf("trusted JVM oracle %s got %q (%v), want %d", fixture.Name, output, err, fixture.Expected)
		}
	}
}

func TestStockHarnessArtifactLoader(t *testing.T) {
	for _, name := range []string{ArtifactPage, TinyJvmStepModule, VMCoordinator} {
		artifact, err := LoadArtifact(name)
		if err != nil {
			t.Fatalf("required runtime artifact dependency %s: %v", name, err)
		}
		if len(artifact.InitCode) == 0 || len(artifact.RuntimeCode) == 0 {
			t.Fatalf("%s contains empty code", name)
		}
	}
	if _, err := LoadArtifact("not-an-s0-artifact"); err == nil {
		t.Fatal("unknown artifact unexpectedly loaded")
	}
}

func TestStockHarnessSignedCanonicalAndDeterministicReplay(t *testing.T) {
	fixture := stockHarnessFixtureNamed(t, stockHarnessLoadFixtures(t), "CanonicalTwelve")
	first := stockHarnessRunSigned(t, fixture, 3, true)
	second := stockHarnessRunSigned(t, fixture, 3, true)
	stockHarnessAssertEquivalentRuns(t, first, second)

	if first.PositiveTxs > 8 || len(first.Events) < 3 {
		t.Fatalf("canonical demo positive tx/resume bounds: tx=%d resumes=%d", first.PositiveTxs, len(first.Events))
	}
	stockHarnessAssertCanonicalTrace(t, first)

	direct1 := stockHarnessReplayDirect(t, first)
	direct2 := stockHarnessReplayDirect(t, first)
	if direct1.Root != direct2.Root {
		t.Fatalf("identical ApplyMessage contexts produced roots %s and %s", direct1.Root, direct2.Root)
	}
	if !reflect.DeepEqual(direct1.GasUsed, direct2.GasUsed) || !reflect.DeepEqual(direct1.Checkpoint, direct2.Checkpoint) {
		t.Fatal("identical ApplyMessage replay changed gas or canonical VM checkpoint")
	}
	if !reflect.DeepEqual(direct1.GasUsed, stockHarnessGas(first.Records)) {
		t.Fatalf("ApplyMessage gas %v does not match signed receipts %v", direct1.GasUsed, stockHarnessGas(first.Records))
	}
	stockHarnessAssertCheckpoint(t, fixture, direct1.Checkpoint, first.ModuleHash, first.PayloadHash)

	// SimulatedBackend stamps committed headers from wall time. We report those
	// headers and intentionally do not use their hashes/roots as a deterministic
	// replay assertion. Determinism above is over explicit identical contexts.
	t.Logf("canonical signed run1 headers=%v roots=%v", first.HeaderHashes, first.StateRoots)
	t.Logf("canonical signed run2 headers=%v roots=%v", second.HeaderHashes, second.StateRoots)
	t.Logf("canonical measurements positiveTx=%d resume=%d positiveGas=%d failedGas=%d page=%s module=%s coordinator=%s pageHash=%s payloadHash=%s moduleHash=%s", first.PositiveTxs, len(first.Events), first.PositiveGas, first.NegativeGas, first.Page, first.Module, first.Coordinator, first.PageHash, first.PayloadHash, first.ModuleHash)
}

func TestStockHarnessTrustedFixtureMatrix(t *testing.T) {
	for _, fixture := range stockHarnessLoadFixtures(t) {
		fixture := fixture
		t.Run(fixture.Name, func(t *testing.T) {
			var terminalMachines []stockHarnessMachine
			for _, budget := range []uint8{1, 3, 16} {
				run := stockHarnessRunSigned(t, fixture, budget, false)
				if run.PositiveTxs > 19 || run.PositiveGas > 30_000_000 {
					t.Fatalf("budget=%d case bounds positiveTx=%d gas=%d", budget, run.PositiveTxs, run.PositiveGas)
				}
				stockHarnessAssertCheckpoint(t, fixture, run.Checkpoint, run.ModuleHash, run.PayloadHash)
				direct := stockHarnessReplayDirect(t, run)
				if !reflect.DeepEqual(direct.GasUsed, stockHarnessGas(run.Records)) {
					t.Fatalf("budget=%d direct gas %v signed gas %v", budget, direct.GasUsed, stockHarnessGas(run.Records))
				}
				if !reflect.DeepEqual(direct.Checkpoint, run.Checkpoint) {
					t.Fatalf("budget=%d direct ApplyMessage checkpoint differs from signed in-process chain", budget)
				}
				terminalMachines = append(terminalMachines, run.Checkpoint.Machine)
				t.Logf("fixture=%s budget=%d expected=%d classSha256=%s positiveTx=%d gas=%d resumes=%d", fixture.Name, budget, fixture.Expected, fixture.ClassSHA256, run.PositiveTxs, run.PositiveGas, len(run.Events))
			}
			for i := 1; i < len(terminalMachines); i++ {
				if !reflect.DeepEqual(terminalMachines[0], terminalMachines[i]) {
					t.Fatalf("terminal canonical Machine differs between budgets 1 and %d", []uint8{3, 16}[i-1])
				}
			}
		})
	}
}

func stockHarnessFixtureNamed(t *testing.T, fixtures []stockHarnessFixture, name string) stockHarnessFixture {
	t.Helper()
	for _, fixture := range fixtures {
		if fixture.Name == name {
			return fixture
		}
	}
	t.Fatalf("fixture %s not found", name)
	return stockHarnessFixture{}
}

func stockHarnessNewBackend(t *testing.T, sender common.Address) *simulated.Backend {
	t.Helper()
	config := *params.AllDevChainProtocolChanges
	backend := simulated.NewBackend(types.GenesisAlloc{
		sender: {Balance: new(big.Int).Exp(big.NewInt(10), big.NewInt(25), nil)},
	}, func(nodeConf *node.Config, ethConf *ethconfig.Config) {
		nodeConf.HTTPHost = ""
		nodeConf.WSHost = ""
		nodeConf.IPCPath = ""
		nodeConf.P2P = p2p.Config{ListenAddr: "", MaxPeers: 0, NoDiscovery: true, DiscoveryV4: false, DiscoveryV5: false}
		ethConf.Genesis = &core.Genesis{
			Config:   &config,
			GasLimit: stockHarnessBlockGas,
			Alloc: types.GenesisAlloc{
				sender: {Balance: new(big.Int).Exp(big.NewInt(10), big.NewInt(25), nil)},
			},
		}
		ethConf.Miner.GasCeil = stockHarnessBlockGas
	})
	t.Cleanup(func() {
		if err := backend.Close(); err != nil {
			t.Errorf("close simulated backend: %v", err)
		}
	})
	chainID, err := backend.Client().ChainID(context.Background())
	if err != nil || chainID.Uint64() != stockHarnessChainID {
		t.Fatalf("simulated chain ID got %v err=%v", chainID, err)
	}
	return backend
}

func stockHarnessRunSigned(t *testing.T, fixture stockHarnessFixture, budget uint8, atomicityProbe bool) stockHarnessRun {
	t.Helper()
	if budget == 0 || budget > 16 {
		t.Fatalf("invalid test step budget %d", budget)
	}
	key, err := crypto.HexToECDSA(stockHarnessTestKeyHex)
	if err != nil {
		t.Fatal(err)
	}
	sender := crypto.PubkeyToAddress(key.PublicKey)
	backend := stockHarnessNewBackend(t, sender)
	client := backend.Client()
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()

	pageArtifact, err := LoadArtifact(ArtifactPage)
	if err != nil {
		t.Fatalf("required page artifact: %v", err)
	}
	moduleArtifact, err := LoadArtifact(TinyJvmStepModule)
	if err != nil {
		t.Fatalf("required module artifact: %v", err)
	}
	coordinatorArtifact, err := LoadArtifact(VMCoordinator)
	if err != nil {
		t.Fatalf("required coordinator artifact: %v", err)
	}

	run := stockHarnessRun{Fixture: fixture, Budget: budget, Sender: sender}
	nonce := uint64(0)
	pageArgs, err := pageArtifact.ABI.Pack("", fixture.Raw)
	if err != nil {
		t.Fatal(err)
	}
	run.Page, nonce = stockHarnessDeploy(t, ctx, backend, key, nonce, append(append([]byte{}, pageArtifact.InitCode...), pageArgs...), "page", &run)
	run.Module, nonce = stockHarnessDeploy(t, ctx, backend, key, nonce, append([]byte{}, moduleArtifact.InitCode...), "module", &run)

	pageCode := append([]byte{0}, fixture.Raw...)
	run.PageHash = crypto.Keccak256Hash(pageCode)
	run.PayloadHash = crypto.Keccak256Hash(fixture.Raw)
	run.ModuleHash = crypto.Keccak256Hash(moduleArtifact.RuntimeCode)
	coordinatorArgs, err := coordinatorArtifact.ABI.Pack("", run.Module, run.Page, run.ModuleHash, run.PageHash, run.PayloadHash)
	if err != nil {
		t.Fatal(err)
	}
	run.Coordinator, nonce = stockHarnessDeploy(t, ctx, backend, key, nonce, append(append([]byte{}, coordinatorArtifact.InitCode...), coordinatorArgs...), "coordinator", &run)

	actualPage, err := client.CodeAt(ctx, run.Page, nil)
	if err != nil || !bytes.Equal(actualPage, pageCode) {
		t.Fatalf("deployed page is not exact STOP||class bytes: len=%d err=%v", len(actualPage), err)
	}
	actualModule, err := client.CodeAt(ctx, run.Module, nil)
	if err != nil || !bytes.Equal(actualModule, moduleArtifact.RuntimeCode) {
		t.Fatalf("deployed module differs from pinned compiler artifact: len=%d err=%v", len(actualModule), err)
	}
	actualCoordinator, err := client.CodeAt(ctx, run.Coordinator, nil)
	if err != nil {
		t.Fatal(err)
	}
	stockHarnessAssertCoordinatorCode(t, coordinatorArtifact.RuntimeCode, actualCoordinator)
	stockHarnessAssertGetters(t, ctx, client, coordinatorArtifact.ABI, run)

	checkpoint := stockHarnessReadCheckpoint(t, ctx, client, coordinatorArtifact.ABI, run.Coordinator)
	stockHarnessAssertInitialCheckpoint(t, checkpoint, run.ModuleHash, run.PayloadHash)
	failedInjected := false
	for !checkpoint.Machine.Done {
		data, err := coordinatorArtifact.ABI.Pack("resume", checkpoint.Epoch, budget, uint8(32))
		if err != nil {
			t.Fatal(err)
		}
		record := stockHarnessSend(t, ctx, backend, key, nonce, &run.Coordinator, data, stockHarnessResumeGas, "resume", true)
		nonce++
		stockHarnessRecord(&run, record, true)
		event := stockHarnessDecodeCheckpointEvent(t, coordinatorArtifact.ABI, record.Receipt)
		run.Events = append(run.Events, event)
		previous := checkpoint
		checkpoint = stockHarnessReadCheckpoint(t, ctx, client, coordinatorArtifact.ABI, run.Coordinator)
		run.Checkpoints = append(run.Checkpoints, checkpoint)
		stockHarnessAssertEventMatchesCheckpoint(t, event, checkpoint, previous, budget, run.ModuleHash, run.PayloadHash)

		if atomicityProbe && !failedInjected && !checkpoint.Machine.Done {
			beforeFailure := checkpoint
			stale, err := coordinatorArtifact.ABI.Pack("resume", checkpoint.Epoch-1, budget, uint8(32))
			if err != nil {
				t.Fatal(err)
			}
			failed := stockHarnessSend(t, ctx, backend, key, nonce, &run.Coordinator, stale, stockHarnessResumeGas, "stale-resume", false)
			nonce++
			stockHarnessRecord(&run, failed, false)
			if len(failed.Receipt.Logs) != 0 {
				t.Fatalf("failed stale transaction emitted %d logs", len(failed.Receipt.Logs))
			}
			afterFailure := stockHarnessReadCheckpoint(t, ctx, client, coordinatorArtifact.ABI, run.Coordinator)
			if !reflect.DeepEqual(beforeFailure, afterFailure) {
				t.Fatal("failed transaction changed VM checkpoint")
			}
			chainNonce, err := client.NonceAt(ctx, sender, nil)
			if err != nil || chainNonce != nonce || failed.Receipt.GasUsed == 0 {
				t.Fatalf("failed tx normal chain effects nonce=%d want=%d gas=%d err=%v", chainNonce, nonce, failed.Receipt.GasUsed, err)
			}
			failedInjected = true
		}
		if len(run.Events) > 16 {
			t.Fatal("fixture exceeded frozen maximum of 16 successful resumes")
		}
	}
	run.Checkpoint = checkpoint
	stockHarnessAssertCheckpoint(t, fixture, checkpoint, run.ModuleHash, run.PayloadHash)
	if run.PositiveGas > 30_000_000 {
		t.Fatalf("successful aggregate gas %d exceeds 30M", run.PositiveGas)
	}
	return run
}

func stockHarnessDeploy(t *testing.T, ctx context.Context, backend *simulated.Backend, key *ecdsa.PrivateKey, nonce uint64, initCode []byte, kind string, run *stockHarnessRun) (common.Address, uint64) {
	t.Helper()
	if len(initCode) > params.MaxInitCodeSize {
		t.Fatalf("%s constructor input %d exceeds EIP-3860", kind, len(initCode))
	}
	record := stockHarnessSend(t, ctx, backend, key, nonce, nil, initCode, stockHarnessCreateGas, "deploy-"+kind, true)
	stockHarnessRecord(run, record, true)
	address := crypto.CreateAddress(run.Sender, nonce)
	if record.Receipt.ContractAddress != address {
		t.Fatalf("%s address got %s want %s", kind, record.Receipt.ContractAddress, address)
	}
	return address, nonce + 1
}

func stockHarnessSend(t *testing.T, ctx context.Context, backend *simulated.Backend, key *ecdsa.PrivateKey, nonce uint64, to *common.Address, data []byte, gas uint64, kind string, success bool) stockHarnessTxRecord {
	t.Helper()
	if gas >= params.MaxTxGas || (to == nil && gas > stockHarnessCreateGas) || (to != nil && gas > stockHarnessResumeGas) {
		t.Fatalf("%s gas %d violates frozen transaction bounds", kind, gas)
	}
	tx := types.NewTx(&types.DynamicFeeTx{
		ChainID:   new(big.Int).SetUint64(stockHarnessChainID),
		Nonce:     nonce,
		GasTipCap: new(big.Int).Set(stockHarnessTipCap),
		GasFeeCap: new(big.Int).Set(stockHarnessFeeCap),
		Gas:       gas,
		To:        to,
		Data:      append([]byte{}, data...),
	})
	signed, err := types.SignTx(tx, types.LatestSignerForChainID(new(big.Int).SetUint64(stockHarnessChainID)), key)
	if err != nil {
		t.Fatal(err)
	}
	if err := backend.Client().SendTransaction(ctx, signed); err != nil {
		t.Fatalf("send %s nonce %d: %v", kind, nonce, err)
	}
	backend.Commit()
	receipt, err := backend.Client().TransactionReceipt(ctx, signed.Hash())
	if err != nil {
		t.Fatalf("receipt %s: %v", kind, err)
	}
	wantStatus := uint64(types.ReceiptStatusFailed)
	if success {
		wantStatus = types.ReceiptStatusSuccessful
	}
	if receipt.Status != wantStatus || receipt.GasUsed > gas {
		t.Fatalf("%s receipt status=%d want=%d gas=%d limit=%d", kind, receipt.Status, wantStatus, receipt.GasUsed, gas)
	}
	header, err := backend.Client().HeaderByNumber(ctx, receipt.BlockNumber)
	if err != nil {
		t.Fatal(err)
	}
	if header.GasLimit != stockHarnessBlockGas || !params.AllDevChainProtocolChanges.IsOsaka(header.Number, header.Time) {
		t.Fatalf("%s not under frozen Osaka/all-dev 30M profile", kind)
	}
	return stockHarnessTxRecord{Kind: kind, Tx: signed, Header: header, Receipt: receipt}
}

func stockHarnessReadCheckpoint(t *testing.T, ctx context.Context, client simulated.Client, contractABI abi.ABI, coordinator common.Address) stockHarnessCheckpoint {
	t.Helper()
	data, err := contractABI.Pack("checkpoint")
	if err != nil {
		t.Fatal(err)
	}
	output, err := client.CallContract(ctx, ethereum.CallMsg{To: &coordinator, Gas: stockHarnessResumeGas, Data: data}, nil)
	if err != nil {
		t.Fatalf("checkpoint call: %v", err)
	}
	var checkpoint stockHarnessCheckpoint
	if err := contractABI.UnpackIntoInterface(&checkpoint, "checkpoint", output); err != nil {
		t.Fatalf("decode checkpoint: %v", err)
	}
	return checkpoint
}

func stockHarnessDecodeCheckpointEvent(t *testing.T, contractABI abi.ABI, receipt *types.Receipt) stockHarnessEvent {
	t.Helper()
	eventABI, ok := contractABI.Events["Checkpoint"]
	if !ok {
		t.Fatal("coordinator ABI has no Checkpoint event")
	}
	if len(receipt.Logs) != 1 || len(receipt.Logs[0].Topics) != 2 || receipt.Logs[0].Topics[0] != eventABI.ID {
		t.Fatalf("successful resume logs=%d or wrong Checkpoint signature", len(receipt.Logs))
	}
	var event stockHarnessEvent
	event.Epoch = new(big.Int).SetBytes(receipt.Logs[0].Topics[1][:]).Uint64()
	if err := contractABI.UnpackIntoInterface(&event, "Checkpoint", receipt.Logs[0].Data); err != nil {
		t.Fatalf("decode Checkpoint event: %v", err)
	}
	return event
}

func stockHarnessAssertEventMatchesCheckpoint(t *testing.T, event stockHarnessEvent, after, before stockHarnessCheckpoint, budget uint8, moduleHash, payloadHash common.Hash) {
	t.Helper()
	if event.Epoch != before.Epoch+1 || after.Epoch != event.Epoch || event.TotalSteps != after.TotalSteps || event.Executed == 0 || event.Executed > budget || after.TotalSteps != before.TotalSteps+uint64(event.Executed) {
		t.Fatalf("bad epoch/step transition before=(%d,%d) event=(%d,%d,%d) after=(%d,%d)", before.Epoch, before.TotalSteps, event.Epoch, event.TotalSteps, event.Executed, after.Epoch, after.TotalSteps)
	}
	machine := after.Machine
	if event.PC != machine.PC || event.SP != machine.SP || event.Done != machine.Done || event.Result != machine.Result || event.StateDigest != after.StateDigest {
		t.Fatal("Checkpoint event does not match checkpoint() canonical state")
	}
	if event.DirtyWords == 0 || event.DirtyWords > 32 {
		t.Fatalf("invalid conservative dirtyWords %d", event.DirtyWords)
	}
	stockHarnessAssertCanonicalMachine(t, machine)
	if want := stockHarnessStateDigest(t, moduleHash, payloadHash, machine, after.Epoch, after.TotalSteps); after.StateDigest != want {
		t.Fatalf("state digest got %x want independently encoded %x", after.StateDigest, want)
	}
}

func stockHarnessAssertInitialCheckpoint(t *testing.T, checkpoint stockHarnessCheckpoint, moduleHash, payloadHash common.Hash) {
	t.Helper()
	zero := stockHarnessZeroMachine()
	if checkpoint.Epoch != 0 || checkpoint.TotalSteps != 0 || !reflect.DeepEqual(checkpoint.Machine, zero) {
		t.Fatalf("noncanonical initial checkpoint: %+v", checkpoint)
	}
	if want := stockHarnessStateDigest(t, moduleHash, payloadHash, checkpoint.Machine, 0, 0); checkpoint.StateDigest != want {
		t.Fatalf("initial digest got %x want %x", checkpoint.StateDigest, want)
	}
}

func stockHarnessAssertCheckpoint(t *testing.T, fixture stockHarnessFixture, checkpoint stockHarnessCheckpoint, moduleHash, payloadHash common.Hash) {
	t.Helper()
	expected := stockHarnessExpectedTerminals[fixture.Name]
	if checkpoint.TotalSteps != expected.steps || checkpoint.Machine.PC != expected.pc || !checkpoint.Machine.Done || checkpoint.Machine.Result != fixture.Expected || checkpoint.Machine.SP != 0 || checkpoint.Machine.Initialized != expected.initialized {
		t.Fatalf("%s terminal checkpoint %+v", fixture.Name, checkpoint)
	}
	for i, value := range expected.locals {
		want := big.NewInt(0)
		if expected.initialized&(1<<i) != 0 {
			want = stockHarnessTagged(value)
		}
		if checkpoint.Machine.Locals[i] == nil || checkpoint.Machine.Locals[i].Cmp(want) != 0 {
			t.Fatalf("%s local%d got %v want %v", fixture.Name, i, checkpoint.Machine.Locals[i], want)
		}
	}
	stockHarnessAssertCanonicalMachine(t, checkpoint.Machine)
	if want := stockHarnessStateDigest(t, moduleHash, payloadHash, checkpoint.Machine, checkpoint.Epoch, checkpoint.TotalSteps); checkpoint.StateDigest != want {
		t.Fatalf("%s terminal digest got %x want %x", fixture.Name, checkpoint.StateDigest, want)
	}
}

func stockHarnessAssertCanonicalTrace(t *testing.T, run stockHarnessRun) {
	t.Helper()
	if len(run.Events) != 3 {
		t.Fatalf("canonical budget3 expected 3 resumptions, got %d", len(run.Events))
	}
	want := []struct {
		epoch, steps uint64
		pc           uint32
		sp           uint8
		done         bool
		result       int32
		executed     uint8
	}{
		{1, 3, 5, 0, false, 0, 3},
		{2, 6, 8, 1, false, 0, 3},
		{3, 7, 9, 0, true, 12, 1},
	}
	for i, event := range run.Events {
		w := want[i]
		if event.Epoch != w.epoch || event.TotalSteps != w.steps || event.PC != w.pc || event.SP != w.sp || event.Done != w.done || event.Result != w.result || event.Executed != w.executed {
			t.Fatalf("canonical event %d got %+v want %+v", i, event, w)
		}
	}
	if len(run.Checkpoints) != 3 {
		t.Fatalf("canonical checkpoints got %d want 3", len(run.Checkpoints))
	}
	first, second := run.Checkpoints[0].Machine, run.Checkpoints[1].Machine
	if first.Initialized != 1 || first.Locals[0].Cmp(stockHarnessTagged(4)) != 0 || first.SP != 0 {
		t.Fatalf("first pause did not preserve initialized local x=4: %+v", first)
	}
	if second.Initialized != 1 || second.Locals[0].Cmp(stockHarnessTagged(4)) != 0 || second.SP != 1 || second.Stack[0].Cmp(stockHarnessTagged(12)) != 0 {
		t.Fatalf("second pause did not preserve live stack value 12 and local x=4: %+v", second)
	}
}

func stockHarnessZeroMachine() stockHarnessMachine {
	machine := stockHarnessMachine{}
	for i := range machine.Stack {
		machine.Stack[i] = new(big.Int)
	}
	for i := range machine.Locals {
		machine.Locals[i] = new(big.Int)
	}
	return machine
}

func stockHarnessTagged(value int32) *big.Int {
	return new(big.Int).Or(new(big.Int).Lsh(big.NewInt(1), 64), new(big.Int).SetUint64(uint64(uint32(value))))
}

func stockHarnessAssertCanonicalMachine(t *testing.T, machine stockHarnessMachine) {
	t.Helper()
	if machine.SP > 8 || machine.Initialized&0xf0 != 0 || (!machine.Done && machine.Result != 0) {
		t.Fatalf("noncanonical scalar Machine fields: %+v", machine)
	}
	for i, cell := range machine.Stack {
		if cell == nil {
			t.Fatalf("nil stack cell %d", i)
		}
		if i >= int(machine.SP) {
			if cell.Sign() != 0 {
				t.Fatalf("unused stack cell %d is %s", i, cell)
			}
		} else if !stockHarnessCanonicalTag(cell) {
			t.Fatalf("active stack cell %d has bad tag %x", i, cell)
		}
	}
	for i, cell := range machine.Locals {
		if cell == nil {
			t.Fatalf("nil local cell %d", i)
		}
		if machine.Initialized&(1<<i) == 0 {
			if cell.Sign() != 0 {
				t.Fatalf("uninitialized local %d is %s", i, cell)
			}
		} else if !stockHarnessCanonicalTag(cell) {
			t.Fatalf("initialized local %d has bad tag %x", i, cell)
		}
	}
}

func stockHarnessCanonicalTag(value *big.Int) bool {
	if value.Sign() < 0 || value.BitLen() > 65 || value.Bit(64) != 1 {
		return false
	}
	return value.Cmp(stockHarnessTagged(int32(uint32(value.Uint64())))) == 0
}

func stockHarnessStateDigest(t *testing.T, moduleHash, payloadHash common.Hash, machine stockHarnessMachine, epoch, total uint64) common.Hash {
	t.Helper()
	u32, _ := abi.NewType("uint32", "", nil)
	b32, _ := abi.NewType("bytes32", "", nil)
	u64, _ := abi.NewType("uint64", "", nil)
	machineType, err := abi.NewType("tuple", "", []abi.ArgumentMarshaling{
		{Name: "pc", Type: "uint32"}, {Name: "sp", Type: "uint8"}, {Name: "initialized", Type: "uint8"},
		{Name: "stack", Type: "uint256[8]"}, {Name: "locals", Type: "uint256[4]"}, {Name: "done", Type: "bool"}, {Name: "result", Type: "int32"},
	})
	if err != nil {
		t.Fatal(err)
	}
	encoded, err := (abi.Arguments{{Type: u32}, {Type: b32}, {Type: b32}, {Type: machineType}, {Type: u64}, {Type: u64}}).Pack(uint32(1), payloadHash, moduleHash, machine, epoch, total)
	if err != nil {
		t.Fatalf("encode stateDigest: %v", err)
	}
	return crypto.Keccak256Hash(encoded)
}

func stockHarnessAssertCoordinatorCode(t *testing.T, template, actual []byte) {
	t.Helper()
	if len(actual) != len(template) {
		t.Fatalf("coordinator runtime length got %d want compiler template %d", len(actual), len(template))
	}
	refs, err := CompilerImmutableReferences(VMCoordinator)
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
		if !mutable[i] && actual[i] != template[i] {
			t.Fatalf("coordinator differs from compiler template outside immutableReferences at byte %d", i)
		}
	}
}

func stockHarnessAssertGetters(t *testing.T, ctx context.Context, client simulated.Client, contractABI abi.ABI, run stockHarnessRun) {
	t.Helper()
	checks := map[string]interface{}{
		"module":              run.Module,
		"page":                run.Page,
		"expectedModuleHash":  run.ModuleHash,
		"expectedPageHash":    run.PageHash,
		"expectedPayloadHash": run.PayloadHash,
	}
	names := make([]string, 0, len(checks))
	for name := range checks {
		names = append(names, name)
	}
	sort.Strings(names)
	for _, name := range names {
		data, err := contractABI.Pack(name)
		if err != nil {
			t.Fatalf("pack getter %s: %v", name, err)
		}
		output, err := client.CallContract(ctx, ethereum.CallMsg{To: &run.Coordinator, Gas: 200_000, Data: data}, nil)
		if err != nil {
			t.Fatalf("call getter %s: %v", name, err)
		}
		values, err := contractABI.Unpack(name, output)
		if err != nil || len(values) != 1 {
			t.Fatalf("getter %s got %v err=%v want %v", name, values, err, checks[name])
		}
		equal := reflect.DeepEqual(values[0], checks[name])
		if rawHash, ok := values[0].([32]byte); ok {
			wantHash, isHash := checks[name].(common.Hash)
			equal = isHash && common.Hash(rawHash) == wantHash
		}
		if !equal {
			t.Fatalf("getter %s got %v want %v", name, values[0], checks[name])
		}
	}
}

func stockHarnessAssertEquivalentRuns(t *testing.T, first, second stockHarnessRun) {
	t.Helper()
	if first.Page != second.Page || first.Module != second.Module || first.Coordinator != second.Coordinator || first.PageHash != second.PageHash || first.PayloadHash != second.PayloadHash || first.ModuleHash != second.ModuleHash {
		t.Fatal("same key/nonces/calldata changed addresses or deployed code hashes")
	}
	if !reflect.DeepEqual(first.Checkpoint, second.Checkpoint) || !reflect.DeepEqual(first.Events, second.Events) || !reflect.DeepEqual(stockHarnessGas(first.Records), stockHarnessGas(second.Records)) {
		t.Fatal("signed replay changed canonical VM state/checkpoints or gas")
	}
}

func stockHarnessRecord(run *stockHarnessRun, record stockHarnessTxRecord, positive bool) {
	run.Records = append(run.Records, record)
	run.HeaderHashes = append(run.HeaderHashes, record.Header.Hash())
	run.StateRoots = append(run.StateRoots, record.Header.Root)
	if positive {
		run.PositiveTxs++
		run.PositiveGas += record.Receipt.GasUsed
	} else {
		run.NegativeGas += record.Receipt.GasUsed
	}
}

func stockHarnessGas(records []stockHarnessTxRecord) []uint64 {
	gas := make([]uint64, len(records))
	for i, record := range records {
		gas[i] = record.Receipt.GasUsed
	}
	return gas
}

type stockHarnessDirectResult struct {
	Root       common.Hash
	GasUsed    []uint64
	Checkpoint stockHarnessCheckpoint
}

func stockHarnessSignedTransactionToMessage(t *testing.T, tx *types.Transaction, header *types.Header) *core.Message {
	t.Helper()
	message, err := core.TransactionToMessage(tx, types.LatestSignerForChainID(new(big.Int).SetUint64(stockHarnessChainID)), header.BaseFee)
	if err != nil {
		t.Fatalf("TransactionToMessage: %v", err)
	}
	if message.SkipNonceChecks || message.SkipTransactionChecks {
		t.Fatal("signed TransactionToMessage unexpectedly disabled nonce/transaction checks")
	}
	return message
}

func stockHarnessReplayDirect(t *testing.T, run stockHarnessRun) stockHarnessDirectResult {
	t.Helper()
	config := *params.AllDevChainProtocolChanges
	genesis := &core.Genesis{
		Config:   &config,
		GasLimit: stockHarnessBlockGas,
		Alloc: types.GenesisAlloc{
			run.Sender: {Balance: new(big.Int).Exp(big.NewInt(10), big.NewInt(25), nil)},
		},
	}
	disk := rawdb.NewMemoryDatabase()
	trieDB := triedb.NewDatabase(disk, triedb.HashDefaults)
	genesisBlock := genesis.MustCommit(disk, trieDB)
	stateDB, err := state.New(genesisBlock.Root(), state.NewDatabase(trieDB, nil))
	if err != nil {
		t.Fatal(err)
	}
	result := stockHarnessDirectResult{GasUsed: make([]uint64, 0, len(run.Records))}
	for index, record := range run.Records {
		header := record.Header
		if !config.IsOsaka(header.Number, header.Time) || header.GasLimit != stockHarnessBlockGas {
			t.Fatal("direct replay context is not frozen Osaka/30M")
		}
		blockContext := stockHarnessBlockContext(header)
		message := stockHarnessSignedTransactionToMessage(t, record.Tx, header)
		stateDB.SetTxContext(record.Tx.Hash(), index)
		evm := vm.NewEVM(blockContext, stateDB, &config, vm.Config{})
		execution, err := core.ApplyMessage(evm, message, new(core.GasPool).AddGas(header.GasLimit))
		if err != nil {
			t.Fatalf("ApplyMessage %s: %v", record.Kind, err)
		}
		wantFailed := record.Receipt.Status == types.ReceiptStatusFailed
		if execution.Failed() != wantFailed || execution.UsedGas != record.Receipt.GasUsed {
			t.Fatalf("ApplyMessage %s failed=%v gas=%d; receipt failed=%v gas=%d", record.Kind, execution.Failed(), execution.UsedGas, wantFailed, record.Receipt.GasUsed)
		}
		result.GasUsed = append(result.GasUsed, execution.UsedGas)
		stateDB.Finalise(config.IsEIP158(header.Number))
		result.Root = stateDB.IntermediateRoot(config.IsEIP158(header.Number))
	}
	actualPage := stateDB.GetCode(run.Page)
	if !bytes.Equal(actualPage, append([]byte{0}, run.Fixture.Raw...)) {
		t.Fatal("direct replay page is not STOP||identical class bytes")
	}
	moduleArtifact, err := LoadArtifact(TinyJvmStepModule)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(stateDB.GetCode(run.Module), moduleArtifact.RuntimeCode) || crypto.Keccak256Hash(stateDB.GetCode(run.Module)) != run.ModuleHash {
		t.Fatal("direct replay module differs from pinned compiler artifact/hash")
	}
	coordinatorArtifact, err := LoadArtifact(VMCoordinator)
	if err != nil {
		t.Fatal(err)
	}
	stockHarnessAssertCoordinatorCode(t, coordinatorArtifact.RuntimeCode, stateDB.GetCode(run.Coordinator))
	lastHeader := run.Records[len(run.Records)-1].Header
	result.Checkpoint = stockHarnessReadCheckpointDirect(t, stateDB, &config, stockHarnessBlockContext(lastHeader), coordinatorArtifact.ABI, run.Coordinator)
	return result
}

func stockHarnessBlockContext(header *types.Header) vm.BlockContext {
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
	return vm.BlockContext{
		CanTransfer: core.CanTransfer,
		Transfer:    core.Transfer,
		GetHash:     func(uint64) common.Hash { return common.Hash{} },
		Coinbase:    header.Coinbase,
		GasLimit:    header.GasLimit,
		BlockNumber: new(big.Int).Set(header.Number),
		Time:        header.Time,
		Difficulty:  difficulty,
		BaseFee:     baseFee,
		BlobBaseFee: new(big.Int),
		Random:      random,
	}
}

func stockHarnessReadCheckpointDirect(t *testing.T, stateDB *state.StateDB, config *params.ChainConfig, blockContext vm.BlockContext, contractABI abi.ABI, coordinator common.Address) stockHarnessCheckpoint {
	t.Helper()
	data, err := contractABI.Pack("checkpoint")
	if err != nil {
		t.Fatal(err)
	}
	evm := vm.NewEVM(blockContext, stateDB, config, vm.Config{})
	output, _, err := evm.StaticCall(common.Address{}, coordinator, data, stockHarnessResumeGas)
	if err != nil {
		t.Fatalf("direct checkpoint static call: %v", err)
	}
	var checkpoint stockHarnessCheckpoint
	if err := contractABI.UnpackIntoInterface(&checkpoint, "checkpoint", output); err != nil {
		t.Fatalf("decode direct checkpoint: %v", err)
	}
	return checkpoint
}
