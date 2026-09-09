package s2b

import (
	"bufio"
	"bytes"
	"context"
	"crypto/ecdsa"
	"crypto/sha256"
	"encoding/binary"
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
	"github.com/ethereum/go-ethereum/jvmevm/stock"
	"github.com/ethereum/go-ethereum/jvmevm/stock/s2a"
	"github.com/ethereum/go-ethereum/node"
	"github.com/ethereum/go-ethereum/p2p"
	"github.com/ethereum/go-ethereum/params"
	"github.com/ethereum/go-ethereum/triedb"
)

const (
	stockS2bLinkHarnessChainID       = uint64(1337)
	stockS2bLinkHarnessBlockGas      = uint64(30_000_000)
	stockS2bLinkHarnessTxGas         = uint64(8_000_000)
	stockS2bLinkHarnessCallGas       = uint64(8_000_000)
	stockS2bLinkHarnessFixtureRoot   = "../../testdata/stock/s2b-link"
	stockS2bLinkHarnessSourceRoot    = "../../testdata/differential"
	stockS2bLinkHarnessTestKeyHex    = "4b2b4b2b4b2b4b2b4b2b4b2b4b2b4b2b4b2b4b2b4b2b4b2b4b2b4b2b4b2b4b2b"
	stockS2bLinkHarnessCatalogueHash = "77d8000e5533803a7113f51dbf9db9eb1fa0cc2a566fc4e6852fa18581486d55"
	stockS2bLinkHarnessCapHash       = "0e3e962a3de46d9c019c8e8e3e846b304622fc969144713f9ad6922c33946f33"
)

var (
	stockS2bLinkHarnessFeeCap = new(big.Int).Mul(big.NewInt(100), big.NewInt(params.GWei))
	stockS2bLinkHarnessTipCap = new(big.Int).SetUint64(params.GWei)
)

type stockS2bLinkHarnessManifest struct {
	Schema               uint32                        `json:"schema"`
	LegacyManifestSHA256 string                        `json:"legacyManifestSha256"`
	CatalogueSHA256      string                        `json:"catalogueSha256"`
	CatalogueRows        int                           `json:"catalogueRows"`
	CatalogueRoots       int                           `json:"catalogueRoots"`
	M3aRows              int                           `json:"m3aRows"`
	Classes              []stockS2bLinkHarnessClassPin `json:"classes"`
	Cap                  stockS2bLinkHarnessCapPin     `json:"cap"`
	CFG                  stockS2bLinkHarnessCFGPin     `json:"cfg"`
}

type stockS2bLinkHarnessClassPin struct {
	Name         string `json:"name"`
	Source       string `json:"source"`
	SourceSHA256 string `json:"sourceSha256"`
	ClassSHA256  string `json:"classSha256"`
	ClassBytes   int    `json:"classBytes"`
	Methods      int    `json:"methods"`
	Literals     int    `json:"literals"`
	Calls        int    `json:"calls"`
	Errors       int    `json:"errors"`
	Adapter      bool   `json:"adapter"`
}

type stockS2bLinkHarnessCapPin struct {
	ClassHex             string `json:"classHex"`
	Generator            string `json:"generator"`
	ClassSHA256          string `json:"classSha256"`
	ClassBytes           int    `json:"classBytes"`
	Methods              int    `json:"methods"`
	Literals             int    `json:"literals"`
	Calls                int    `json:"calls"`
	MetadataPayloadBytes int    `json:"metadataPayloadBytes"`
}

type stockS2bLinkHarnessCFGPin struct {
	Source       string `json:"source"`
	ClassHex     string `json:"classHex"`
	SourceSHA256 string `json:"sourceSha256"`
	ClassSHA256  string `json:"classSha256"`
	ClassBytes   int    `json:"classBytes"`
}

type stockS2bLinkHarnessLegacyManifest struct {
	Schema uint64                          `json:"schema_version"`
	Cases  []stockS2bLinkHarnessLegacyCase `json:"cases"`
}

type stockS2bLinkHarnessLegacyCase struct {
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

type stockS2bLinkHarnessOutcome struct {
	Kind      string `json:"kind"`
	Value     int32  `json:"value"`
	Exception string `json:"exception"`
	GasUsed   uint64 `json:"gas_used"`
}

type stockS2bLinkHarnessCatalogueRow struct {
	Index             int                        `json:"index"`
	ID                string                     `json:"id"`
	Stage             string                     `json:"stage"`
	Class             string                     `json:"class"`
	Method            string                     `json:"method"`
	Descriptor        string                     `json:"descriptor"`
	ExpectedKind      string                     `json:"expected_kind"`
	ExpectedException string                     `json:"expected_exception"`
	Sources           []string                   `json:"sources"`
	Args              []int32                    `json:"args"`
	GasLimit          uint64                     `json:"gas_limit"`
	TimeoutSeconds    uint64                     `json:"timeout_seconds"`
	Smoke             bool                       `json:"smoke"`
	RawClassBytes     int                        `json:"raw_class_bytes"`
	RawClassSHA256    string                     `json:"raw_class_sha256"`
	JVM8              stockS2bLinkHarnessOutcome `json:"jvm8"`
	JVM21             stockS2bLinkHarnessOutcome `json:"jvm21"`
	Monolith          stockS2bLinkHarnessOutcome `json:"monolith"`
	Trace             struct {
		Kind       string `json:"kind"`
		Exception  string `json:"exception"`
		Value      int32  `json:"value"`
		Calls      int    `json:"calls"`
		Dispatches int    `json:"dispatches"`
		MaxFrames  int    `json:"max_frames"`
	} `json:"trace"`
}

type stockS2bLinkHarnessCP struct {
	Tag  byte
	A, B uint16
	Text string
	Bits uint32
}

type stockS2bLinkHarnessMethod struct {
	Index               uint16
	Name, Descriptor    string
	Access              uint16
	CodeOffset          uint32
	MaxStack, MaxLocals uint8
	Code                []byte
}

type stockS2bLinkHarnessClass struct {
	Name            string
	Access, CPCount uint16
	Raw             []byte
	CP              []stockS2bLinkHarnessCP
	Methods         []stockS2bLinkHarnessMethod
}

type stockS2bLinkHarnessMetadata struct {
	Code                     []byte
	Methods, Literals, Calls uint16
	ErrorMethods             int
}

type stockS2bLinkHarnessRegistration struct {
	Name                                         string
	Class                                        stockS2bLinkHarnessClass
	Page, MetadataPage                           common.Address
	PageHash, PayloadHash, MetadataHash, ClassID common.Hash
	Methods, Literals, Calls                     uint16
	PageGas, RegisterGas                         uint64
}

type stockS2bLinkHarnessTxRecord struct {
	Kind    string
	Tx      *types.Transaction
	Header  *types.Header
	Receipt *types.Receipt
}

type stockS2bLinkHarnessEnvironment struct {
	Backend                                 *simulated.Backend
	Key                                     *ecdsa.PrivateKey
	Sender                                  common.Address
	Nonce                                   uint64
	Analyzer, Linker, OldParser             common.Address
	AnalyzerHash, LinkerHash, OldParserHash common.Hash
	Records                                 []stockS2bLinkHarnessTxRecord
}

func TestStockS2bLinkHarnessArtifactLoader(t *testing.T) {
	for _, name := range []string{S2bMetadataPage, S2bAnalyzeModule, S2bClassLinker} {
		artifact, err := LoadArtifact(name)
		if err != nil {
			t.Fatalf("required S2b-L artifact dependency %s: %v", name, err)
		}
		if len(artifact.InitCode) == 0 || len(artifact.RuntimeCode) == 0 {
			t.Fatalf("%s has empty code", name)
		}
		refs, err := CompilerImmutableReferences(name)
		if err != nil {
			t.Fatal(err)
		}
		if (name == S2bClassLinker) != (len(refs) > 0) {
			t.Fatalf("%s immutable reference presence=%v", name, len(refs) > 0)
		}
	}
	for _, name := range []string{"not-an-artifact", stock.ArtifactPage, s2a.S2aClassParser} {
		if _, err := LoadArtifact(name); err == nil {
			t.Fatalf("foreign/unknown artifact %q unexpectedly loaded", name)
		}
	}
}

func TestStockS2bLinkHarnessPinnedCatalogueAndJVMOracles(t *testing.T) {
	manifest, classes, output := stockS2bLinkHarnessLoadFixtures(t)
	cataloguePath := filepath.Join(stockS2bLinkHarnessFixtureRoot, "catalogue", "catalogue.jsonl")
	catalogueRaw, err := os.ReadFile(cataloguePath)
	if err != nil {
		t.Fatal(err)
	}
	if got := fmt.Sprintf("%x", sha256.Sum256(catalogueRaw)); got != manifest.CatalogueSHA256 || got != stockS2bLinkHarnessCatalogueHash {
		t.Fatalf("catalogue SHA-256=%s", got)
	}
	legacyRaw, err := os.ReadFile(filepath.Join(stockS2bLinkHarnessSourceRoot, "cases.json"))
	if err != nil {
		t.Fatal(err)
	}
	if got := fmt.Sprintf("%x", sha256.Sum256(legacyRaw)); got != manifest.LegacyManifestSHA256 {
		t.Fatalf("legacy manifest SHA-256=%s", got)
	}
	var legacy stockS2bLinkHarnessLegacyManifest
	if err := json.Unmarshal(legacyRaw, &legacy); err != nil || legacy.Schema != 1 {
		t.Fatalf("legacy manifest: schema=%d err=%v", legacy.Schema, err)
	}
	var selected []stockS2bLinkHarnessLegacyCase
	for _, row := range legacy.Cases {
		if row.Stage == "m1" || row.Stage == "m2" || row.Stage == "m2b" || row.Stage == "m3a" {
			selected = append(selected, row)
		}
	}
	rows := stockS2bLinkHarnessReadCatalogue(t, catalogueRaw)
	if len(rows) != manifest.CatalogueRows || len(selected) != manifest.CatalogueRows {
		t.Fatalf("catalogue/legacy rows=%d/%d", len(rows), len(selected))
	}
	java8 := "/usr/lib/jvm/java-8-openjdk/bin/java"
	if _, err := os.Stat(java8); err != nil {
		t.Fatalf("Java 8 oracle unavailable: %v", err)
	}
	java21, err := exec.LookPath("java")
	if err != nil {
		t.Fatalf("Java 21 oracle unavailable: %v", err)
	}
	if version := stockS2bLinkHarnessCommand(t, 10*time.Second, java8, "-version"); !strings.Contains(version, `version "1.8.`) {
		t.Fatalf("Java 8 oracle has unexpected version: %s", version)
	}
	if version := stockS2bLinkHarnessCommand(t, 10*time.Second, java21, "-version"); !strings.Contains(version, `version "21.`) {
		t.Fatalf("Java 21 oracle has unexpected version: %s", version)
	}
	roots := make(map[string]bool)
	m3aRows, values, arithmetic, overflow, dispatches, dynamicCalls := 0, 0, 0, 0, 0, 0
	for i, row := range rows {
		old := selected[i]
		if row.Index != i || row.ID != old.ID || row.Stage != old.Stage || row.Class != old.Class || row.Method != old.Method || !reflect.DeepEqual(row.Args, old.Args) || !reflect.DeepEqual(row.Sources, old.Sources) || row.GasLimit != old.GasLimit || row.TimeoutSeconds != old.TimeoutSeconds || row.ExpectedKind != old.ExpectedKind || row.ExpectedException != old.ExpectedException || row.Smoke != old.Smoke {
			t.Fatalf("catalogue row %d changed: row=%+v legacy=%+v", i, row, old)
		}
		class := classes[row.Class]
		if len(class.Raw) != row.RawClassBytes || fmt.Sprintf("%x", sha256.Sum256(class.Raw)) != row.RawClassSHA256 {
			t.Fatalf("%s row raw identity mismatch", row.ID)
		}
		method := stockS2bLinkHarnessFindMethod(t, class, row.Method, row.Descriptor)
		_ = method
		roots[row.Class+"\x00"+row.Method+"\x00"+row.Descriptor] = true
		if row.Stage == "m3a" {
			m3aRows++
		}
		switch row.ExpectedKind {
		case "value":
			values++
			if row.JVM8.Kind != "value" || row.JVM21.Kind != "value" || row.Monolith.Kind != "value" || row.Trace.Kind != "value" || row.JVM8.Value != row.JVM21.Value || row.JVM8.Value != row.Monolith.Value || row.JVM8.Value != row.Trace.Value {
				t.Fatalf("%s pinned value oracles disagree", row.ID)
			}
		case "java_exception":
			if row.ExpectedException == "java.lang.ArithmeticException" {
				arithmetic++
			} else if row.ExpectedException == "java.lang.StackOverflowError" {
				overflow++
			} else {
				t.Fatalf("%s unexpected exception %q", row.ID, row.ExpectedException)
			}
			if row.JVM8.Kind != "java_exception" || row.JVM21.Kind != "java_exception" || row.Monolith.Kind != "java_exception" || row.Trace.Kind != "java_exception" || row.JVM8.Exception != row.ExpectedException || row.JVM21.Exception != row.ExpectedException || row.Monolith.Exception != row.ExpectedException || row.Trace.Exception != row.ExpectedException {
				t.Fatalf("%s pinned exception oracles disagree", row.ID)
			}
		default:
			t.Fatalf("%s unexpected kind %q", row.ID, row.ExpectedKind)
		}
		dispatches += row.Trace.Dispatches
		dynamicCalls += row.Trace.Calls
		want := "value=" + strconv.FormatInt(int64(row.JVM8.Value), 10)
		if row.ExpectedKind == "java_exception" {
			want = "exception=" + row.ExpectedException
		}
		for _, java := range []string{java8, java21} {
			args := []string{"-Xmx64m", "-Xss512k", "-XX:-OmitStackTraceInFastThrow", "-Xverify:all", "-cp", output, "OracleMain", row.Class, row.Method}
			for _, value := range row.Args {
				args = append(args, strconv.FormatInt(int64(value), 10))
			}
			if got := stockS2bLinkHarnessCommand(t, 20*time.Second, java, args...); got != want {
				t.Fatalf("%s JVM %s got %q want %q", row.ID, java, got, want)
			}
		}
	}
	if len(roots) != manifest.CatalogueRoots || m3aRows != manifest.M3aRows || values != 261 || arithmetic != 6 || overflow != 1 || dispatches != 6702 || dynamicCalls != 512 {
		t.Fatalf("catalogue totals roots/m3a/value/arithmetic/SOE/dispatch/calls=%d/%d/%d/%d/%d/%d/%d", len(roots), m3aRows, values, arithmetic, overflow, dispatches, dynamicCalls)
	}
	t.Logf("unchanged TEST oracle catalogue: rows=%d roots=%d M3a=%d values=%d ArithmeticException=%d StackOverflowError=%d dispatches=%d dynamicCalls=%d (no stock execution claim)", len(rows), len(roots), m3aRows, values, arithmetic, overflow, dispatches, dynamicCalls)
}

func TestStockS2bLinkHarnessCapGeneratorAndJava8Java21(t *testing.T) {
	manifest, _, output := stockS2bLinkHarnessLoadFixtures(t)
	cap := stockS2bLinkHarnessReadHex(t, filepath.Join(stockS2bLinkHarnessFixtureRoot, manifest.Cap.ClassHex))
	if len(cap) != manifest.Cap.ClassBytes || fmt.Sprintf("%x", sha256.Sum256(cap)) != manifest.Cap.ClassSHA256 || manifest.Cap.ClassSHA256 != stockS2bLinkHarnessCapHash {
		t.Fatalf("cap identity bytes/hash=%d/%x", len(cap), sha256.Sum256(cap))
	}
	generator, err := os.ReadFile(filepath.Join(stockS2bLinkHarnessFixtureRoot, manifest.Cap.Generator))
	if err != nil {
		t.Fatal(err)
	}
	generatorDir := t.TempDir()
	if err := os.WriteFile(filepath.Join(generatorDir, "make_class.py"), generator, 0o644); err != nil {
		t.Fatal(err)
	}
	stockS2bLinkHarnessCommand(t, 30*time.Second, "python3", filepath.Join(generatorDir, "make_class.py"))
	generated, err := os.ReadFile(filepath.Join(generatorDir, "classes", "S2bValidCaps.class"))
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(generated, cap) {
		t.Fatalf("cap generator changed raw bytes: generated=%x pinned=%s", sha256.Sum256(generated), manifest.Cap.ClassSHA256)
	}
	if err := os.WriteFile(filepath.Join(output, "S2bValidCaps.class"), cap, 0o644); err != nil {
		t.Fatal(err)
	}
	for _, java := range []string{"/usr/lib/jvm/java-8-openjdk/bin/java", stockS2bLinkHarnessLookPath(t, "java")} {
		if got := stockS2bLinkHarnessCommand(t, 20*time.Second, java, "-Xmx64m", "-Xss512k", "-Xverify:all", "-cp", output, "OracleMain", "S2bValidCaps", "root"); got != "value=0" {
			t.Fatalf("cap JVM %s got %q", java, got)
		}
	}
	parsed := stockS2bLinkHarnessParseClass(t, cap)
	if len(parsed.Methods) != 32 {
		t.Fatalf("cap methods=%d", len(parsed.Methods))
	}

	cfgSource := filepath.Join(stockS2bLinkHarnessFixtureRoot, manifest.CFG.Source)
	cfgRaw := stockS2bLinkHarnessReadHex(t, filepath.Join(stockS2bLinkHarnessFixtureRoot, manifest.CFG.ClassHex))
	source, err := os.ReadFile(cfgSource)
	if err != nil {
		t.Fatal(err)
	}
	if fmt.Sprintf("%x", sha256.Sum256(source)) != manifest.CFG.SourceSHA256 || len(cfgRaw) != manifest.CFG.ClassBytes || fmt.Sprintf("%x", sha256.Sum256(cfgRaw)) != manifest.CFG.ClassSHA256 {
		t.Fatal("valid revisit CFG source/raw identity changed")
	}
	cfgOut := t.TempDir()
	stockS2bLinkHarnessCommand(t, 30*time.Second, stockS2bLinkHarnessLookPath(t, "javac"), "--release", "8", "-d", cfgOut, cfgSource)
	compiled, err := os.ReadFile(filepath.Join(cfgOut, "ValidRevisitCFG.class"))
	if err != nil || !bytes.Equal(compiled, cfgRaw) {
		t.Fatalf("valid revisit CFG regeneration err=%v hash=%x", err, sha256.Sum256(compiled))
	}
	if err := os.WriteFile(filepath.Join(output, "ValidRevisitCFG.class"), cfgRaw, 0o644); err != nil {
		t.Fatal(err)
	}
	for _, java := range []string{"/usr/lib/jvm/java-8-openjdk/bin/java", stockS2bLinkHarnessLookPath(t, "java")} {
		if got := stockS2bLinkHarnessCommand(t, 20*time.Second, java, "-Xmx64m", "-Xss512k", "-Xverify:all", "-cp", output, "OracleMain", "ValidRevisitCFG", "revisit", "5"); got != "value=0" {
			t.Fatalf("valid revisit CFG JVM %s got %q", java, got)
		}
	}
	t.Logf("JVM-valid caps pinned: raw=%d methods=%d literals=%d calls=%d metadata=%d; valid revisit CFG raw=%d", len(cap), manifest.Cap.Methods, manifest.Cap.Literals, manifest.Cap.Calls, manifest.Cap.MetadataPayloadBytes, len(cfgRaw))
}

func TestStockS2bLinkHarnessSignedDirectAdapterIdempotencyCapAndReplay(t *testing.T) {
	if testing.Short() {
		t.Skip("signed Stock S2b-L ordinary deployment/registration/replay gate")
	}
	manifest, classes, _ := stockS2bLinkHarnessLoadFixtures(t)
	env := stockS2bLinkHarnessNewEnvironment(t)
	defer env.close(t)
	pageArtifact := stockS2bLinkHarnessLoadStockArtifact(t, stock.ArtifactPage)
	linker := stockS2bLinkHarnessLoadArtifact(t, S2bClassLinker)
	oldParser := stockS2bLinkHarnessLoadS2aArtifact(t, s2a.S2aClassParser)

	stockS2bLinkHarnessAssertLinkerConfiguration(t, env, linker)
	registrations := make(map[string]stockS2bLinkHarnessRegistration)
	names := make([]string, 0, len(manifest.Classes))
	pins := make(map[string]stockS2bLinkHarnessClassPin)
	for _, pin := range manifest.Classes {
		names = append(names, pin.Name)
		pins[pin.Name] = pin
	}
	sort.Strings(names)
	var directGas, adapterGas uint64
	var totalCalls int
	for _, name := range names {
		pin := pins[name]
		class := classes[name]
		reg := stockS2bLinkHarnessDeployRawPage(t, env, pageArtifact, name, class.Raw)
		reg.Class = class
		old := stockS2bLinkHarnessRegisterOld(t, env, oldParser, reg, name)
		if pin.Adapter {
			reg = stockS2bLinkHarnessRegisterNew(t, env, linker, reg, true, old.ClassID, "adapter-"+name)
			adapterGas += reg.RegisterGas
			stockS2bLinkHarnessAssertIdempotent(t, env, linker, reg, false, common.Hash{}, "direct-after-adapter-"+name)
		} else {
			reg = stockS2bLinkHarnessRegisterNew(t, env, linker, reg, false, common.Hash{}, "direct-"+name)
			directGas += reg.RegisterGas
			// Every M3a class is old-S2a registerable even though its call/private/
			// void methods were not executable by the frozen one-frame S2a runtime.
			stockS2bLinkHarnessAssertIdempotent(t, env, linker, reg, true, old.ClassID, "adapter-after-direct-"+name)
		}
		stockS2bLinkHarnessAssertOldRecordUnchanged(t, env, oldParser.ABI, old)
		metadata := stockS2bLinkHarnessReadMetadata(t, env, reg)
		if int(reg.Methods) != pin.Methods || int(reg.Literals) != pin.Literals || int(reg.Calls) != pin.Calls || metadata.ErrorMethods != pin.Errors {
			t.Fatalf("%s schema-4 counts methods/literals/calls/errors=%d/%d/%d/%d want %d/%d/%d/%d", name, reg.Methods, reg.Literals, reg.Calls, metadata.ErrorMethods, pin.Methods, pin.Literals, pin.Calls, pin.Errors)
		}
		stockS2bLinkHarnessVerifyCallRecords(t, class, metadata)
		totalCalls += int(reg.Calls)
		registrations[name] = reg
	}
	if len(registrations) != 14 || totalCalls != 51 {
		t.Fatalf("registration corpus classes/callrecords=%d/%d", len(registrations), totalCalls)
	}

	// The exact simultaneous cap must fit both a fresh direct path and a fresh
	// S2a-adapter path under 8M. Distinct ordinary raw pages make each issuance
	// fresh; no state/code injection or idempotent shortcut is involved.
	capRaw := stockS2bLinkHarnessReadHex(t, filepath.Join(stockS2bLinkHarnessFixtureRoot, manifest.Cap.ClassHex))
	capClass := stockS2bLinkHarnessParseClass(t, capRaw)
	capDirect := stockS2bLinkHarnessDeployRawPage(t, env, pageArtifact, "cap-direct", capRaw)
	capDirect.Class = capClass
	capDirect = stockS2bLinkHarnessRegisterNew(t, env, linker, capDirect, false, common.Hash{}, "cap-direct")
	directGas += capDirect.RegisterGas
	capDirectMeta := stockS2bLinkHarnessReadMetadata(t, env, capDirect)
	stockS2bLinkHarnessAssertCap(t, manifest, capDirect, capDirectMeta)
	stockS2bLinkHarnessVerifyCallRecords(t, capClass, capDirectMeta)

	capAdapter := stockS2bLinkHarnessDeployRawPage(t, env, pageArtifact, "cap-adapter", capRaw)
	capAdapter.Class = capClass
	capOld := stockS2bLinkHarnessRegisterOld(t, env, oldParser, capAdapter, "cap-adapter")
	capAdapter = stockS2bLinkHarnessRegisterNew(t, env, linker, capAdapter, true, capOld.ClassID, "cap-adapter")
	adapterGas += capAdapter.RegisterGas
	stockS2bLinkHarnessAssertOldRecordUnchanged(t, env, oldParser.ABI, capOld)
	capAdapterMeta := stockS2bLinkHarnessReadMetadata(t, env, capAdapter)
	stockS2bLinkHarnessAssertCap(t, manifest, capAdapter, capAdapterMeta)
	stockS2bLinkHarnessVerifyCallRecords(t, capClass, capAdapterMeta)

	// Register the valid revisit CFG through the real analyzer. This specifically
	// exercises convergence after a back-edge local-init intersection tightens.
	cfgRaw := stockS2bLinkHarnessReadHex(t, filepath.Join(stockS2bLinkHarnessFixtureRoot, manifest.CFG.ClassHex))
	cfg := stockS2bLinkHarnessDeployRawPage(t, env, pageArtifact, "valid-revisit-cfg", cfgRaw)
	cfg.Class = stockS2bLinkHarnessParseClass(t, cfgRaw)
	cfg = stockS2bLinkHarnessRegisterNew(t, env, linker, cfg, false, common.Hash{}, "valid-revisit-cfg")
	cfgMeta := stockS2bLinkHarnessReadMetadata(t, env, cfg)
	if cfgMeta.ErrorMethods != 1 { // constructor only; revisit itself is eligible.
		t.Fatalf("valid revisit CFG deferred errors=%d want constructor only", cfgMeta.ErrorMethods)
	}

	first := stockS2bLinkHarnessReplayDirect(t, env)
	second := stockS2bLinkHarnessReplayDirect(t, env)
	if first.Root != second.Root || !reflect.DeepEqual(first.Gas, second.Gas) || !reflect.DeepEqual(first.Gas, stockS2bLinkHarnessReceiptGas(env.Records)) {
		t.Fatal("identical signed TransactionToMessage/ApplyMessage replay changed root or gas")
	}
	for name, reg := range registrations {
		if hash := crypto.Keccak256Hash(first.State.GetCode(reg.MetadataPage)); hash != reg.MetadataHash {
			t.Fatalf("direct replay changed metadata %s", name)
		}
	}
	firstHeader, lastHeader := env.Records[0].Header, env.Records[len(env.Records)-1].Header
	t.Logf("Stock S2b-L registration only: classes=%d EVM-issuedCallRecords=%d signedTx=%d signedGas=%d directRegistrationGas=%d adapterRegistrationGas=%d capDirectGas=%d capAdapterGas=%d analyzerHash=%s actualLinkerHash=%s replayRoot=%s signedWallTimeHeaders(first=%s/root=%s/time=%d last=%s/root=%s/time=%d; not compared as global roots); no frame/resume/268-stock-execution/Java-outcome claim", len(registrations), totalCalls, len(env.Records), stockS2bLinkHarnessSumGas(env.Records), directGas, adapterGas, capDirect.RegisterGas, capAdapter.RegisterGas, env.AnalyzerHash, env.LinkerHash, first.Root, firstHeader.Hash(), firstHeader.Root, firstHeader.Time, lastHeader.Hash(), lastHeader.Root, lastHeader.Time)
}

type stockS2bLinkHarnessReplay struct {
	Root  common.Hash
	Gas   []uint64
	State *state.StateDB
}

func stockS2bLinkHarnessNewEnvironment(t *testing.T) *stockS2bLinkHarnessEnvironment {
	t.Helper()
	key, err := crypto.HexToECDSA(stockS2bLinkHarnessTestKeyHex)
	if err != nil {
		t.Fatal(err)
	}
	sender := crypto.PubkeyToAddress(key.PublicKey)
	env := &stockS2bLinkHarnessEnvironment{Key: key, Sender: sender}
	env.Backend = stockS2bLinkHarnessNewBackend(t, sender)
	analyzer := stockS2bLinkHarnessLoadArtifact(t, S2bAnalyzeModule)
	oldParser := stockS2bLinkHarnessLoadS2aArtifact(t, s2a.S2aClassParser)
	linker := stockS2bLinkHarnessLoadArtifact(t, S2bClassLinker)
	env.Analyzer, _ = stockS2bLinkHarnessDeploy(t, env, analyzer.InitCode, "analyzer")
	env.OldParser, _ = stockS2bLinkHarnessDeploy(t, env, oldParser.InitCode, "old-s2a-parser")
	stockS2bLinkHarnessAssertExactCode(t, env, env.Analyzer, analyzer.RuntimeCode, "analyzer")
	stockS2bLinkHarnessAssertExactCode(t, env, env.OldParser, oldParser.RuntimeCode, "old S2a parser")
	env.AnalyzerHash = crypto.Keccak256Hash(stockS2bLinkHarnessCodeAt(t, env, env.Analyzer))
	env.OldParserHash = crypto.Keccak256Hash(stockS2bLinkHarnessCodeAt(t, env, env.OldParser))
	constructor, err := linker.ABI.Pack("", env.Analyzer, env.AnalyzerHash, env.OldParserHash)
	if err != nil {
		t.Fatalf("linker three-argument constructor: %v", err)
	}
	env.Linker, _ = stockS2bLinkHarnessDeploy(t, env, append(append([]byte{}, linker.InitCode...), constructor...), "linker")
	actual := stockS2bLinkHarnessCodeAt(t, env, env.Linker)
	stockS2bLinkHarnessAssertImmutableTemplate(t, linker.RuntimeCode, actual, S2bClassLinker)
	env.LinkerHash = crypto.Keccak256Hash(actual)
	return env
}

func stockS2bLinkHarnessNewBackend(t *testing.T, sender common.Address) *simulated.Backend {
	t.Helper()
	config := *params.AllDevChainProtocolChanges
	balance := new(big.Int).Exp(big.NewInt(10), big.NewInt(26), nil)
	backend := simulated.NewBackend(types.GenesisAlloc{sender: {Balance: balance}}, func(nodeConf *node.Config, ethConf *ethconfig.Config) {
		// All external interfaces and all discovery/listener paths stay disabled.
		nodeConf.HTTPHost, nodeConf.WSHost, nodeConf.IPCPath = "", "", ""
		nodeConf.P2P = p2p.Config{ListenAddr: "", MaxPeers: 0, NoDiscovery: true, DiscoveryV4: false, DiscoveryV5: false}
		ethConf.Genesis = &core.Genesis{Config: &config, GasLimit: stockS2bLinkHarnessBlockGas, Alloc: types.GenesisAlloc{sender: {Balance: new(big.Int).Set(balance)}}}
		ethConf.Miner.GasCeil = stockS2bLinkHarnessBlockGas
	})
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	chainID, err := backend.Client().ChainID(ctx)
	if err != nil || chainID.Uint64() != stockS2bLinkHarnessChainID {
		t.Fatalf("simulated chain ID=%v err=%v", chainID, err)
	}
	return backend
}

func (env *stockS2bLinkHarnessEnvironment) close(t *testing.T) {
	t.Helper()
	if err := env.Backend.Close(); err != nil {
		t.Errorf("close backend: %v", err)
	}
}

func stockS2bLinkHarnessSend(t *testing.T, env *stockS2bLinkHarnessEnvironment, to *common.Address, data []byte, kind string, success bool) stockS2bLinkHarnessTxRecord {
	t.Helper()
	if stockS2bLinkHarnessTxGas >= params.MaxTxGas {
		t.Fatal("frozen transaction gas violates Osaka EIP-7825")
	}
	tx := types.NewTx(&types.DynamicFeeTx{ChainID: new(big.Int).SetUint64(stockS2bLinkHarnessChainID), Nonce: env.Nonce, GasTipCap: new(big.Int).Set(stockS2bLinkHarnessTipCap), GasFeeCap: new(big.Int).Set(stockS2bLinkHarnessFeeCap), Gas: stockS2bLinkHarnessTxGas, To: to, Data: append([]byte(nil), data...)})
	signer := types.LatestSignerForChainID(new(big.Int).SetUint64(stockS2bLinkHarnessChainID))
	signed, err := types.SignTx(tx, signer, env.Key)
	if err != nil {
		t.Fatal(err)
	}
	from, err := types.Sender(signer, signed)
	if err != nil || from != env.Sender {
		t.Fatalf("%s signed sender=%s err=%v", kind, from, err)
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
	if receipt.Status != want || receipt.GasUsed > stockS2bLinkHarnessTxGas {
		t.Fatalf("%s receipt status/gas=%d/%d want status=%d cap=%d", kind, receipt.Status, receipt.GasUsed, want, stockS2bLinkHarnessTxGas)
	}
	header, err := env.Backend.Client().HeaderByNumber(ctx, receipt.BlockNumber)
	if err != nil {
		t.Fatal(err)
	}
	if header.GasLimit != stockS2bLinkHarnessBlockGas || !params.AllDevChainProtocolChanges.IsOsaka(header.Number, header.Time) {
		t.Fatalf("%s not Osaka/30M", kind)
	}
	record := stockS2bLinkHarnessTxRecord{Kind: kind, Tx: signed, Header: header, Receipt: receipt}
	env.Records = append(env.Records, record)
	env.Nonce++
	return record
}

func stockS2bLinkHarnessDeploy(t *testing.T, env *stockS2bLinkHarnessEnvironment, initCode []byte, kind string) (common.Address, uint64) {
	t.Helper()
	if len(initCode) > params.MaxInitCodeSize {
		t.Fatalf("%s initcode=%d exceeds EIP-3860", kind, len(initCode))
	}
	nonce := env.Nonce
	record := stockS2bLinkHarnessSend(t, env, nil, initCode, "deploy-"+kind, true)
	address := crypto.CreateAddress(env.Sender, nonce)
	if record.Receipt.ContractAddress != address {
		t.Fatalf("%s CREATE address=%s want=%s", kind, record.Receipt.ContractAddress, address)
	}
	code := stockS2bLinkHarnessCodeAt(t, env, address)
	if len(code) == 0 || len(code) > params.MaxCodeSize {
		t.Fatalf("%s runtime size=%d", kind, len(code))
	}
	return address, record.Receipt.GasUsed
}

func stockS2bLinkHarnessDeployRawPage(t *testing.T, env *stockS2bLinkHarnessEnvironment, pageArtifact stock.Artifact, name string, raw []byte) stockS2bLinkHarnessRegistration {
	t.Helper()
	constructor, err := pageArtifact.ABI.Pack("", raw)
	if err != nil {
		t.Fatal(err)
	}
	page, gas := stockS2bLinkHarnessDeploy(t, env, append(append([]byte{}, pageArtifact.InitCode...), constructor...), "raw-page-"+name)
	code := append([]byte{0}, raw...)
	stockS2bLinkHarnessAssertExactCode(t, env, page, code, "raw page "+name)
	return stockS2bLinkHarnessRegistration{Name: name, Page: page, PageHash: crypto.Keccak256Hash(code), PayloadHash: crypto.Keccak256Hash(raw), PageGas: gas}
}

func stockS2bLinkHarnessRegisterOld(t *testing.T, env *stockS2bLinkHarnessEnvironment, parser stock.Artifact, reg stockS2bLinkHarnessRegistration, name string) stockS2bLinkHarnessRegistration {
	t.Helper()
	data, err := parser.ABI.Pack("registerClass", reg.Page, reg.PageHash, reg.PayloadHash)
	if err != nil {
		t.Fatal(err)
	}
	record := stockS2bLinkHarnessSend(t, env, &env.OldParser, data, "old-s2a-register-"+name, true)
	if len(record.Receipt.Logs) != 1 {
		t.Fatalf("old S2a registration %s logs=%d", name, len(record.Receipt.Logs))
	}
	values := stockS2bLinkHarnessCall(t, env, parser.ABI, env.OldParser, "registerClass", reg.Page, reg.PageHash, reg.PayloadHash)
	if len(values) != 4 {
		t.Fatalf("old registration %s returns=%d", name, len(values))
	}
	reg.ClassID = common.Hash(values[0].([32]byte))
	reg.MetadataPage = values[1].(common.Address)
	reg.MetadataHash = common.Hash(values[2].([32]byte))
	reg.Methods = values[3].(uint16)
	if code := stockS2bLinkHarnessCodeAt(t, env, reg.MetadataPage); len(code) < 1 || code[0] != 0 || crypto.Keccak256Hash(code) != reg.MetadataHash {
		t.Fatalf("old S2a registration %s metadata identity", name)
	}
	return reg
}

func stockS2bLinkHarnessRegisterNew(t *testing.T, env *stockS2bLinkHarnessEnvironment, linker stock.Artifact, reg stockS2bLinkHarnessRegistration, adapter bool, oldClassID common.Hash, kind string) stockS2bLinkHarnessRegistration {
	t.Helper()
	method := "registerClass"
	args := []interface{}{reg.Page, reg.PageHash, reg.PayloadHash}
	if adapter {
		method = "registerFromS2a"
		args = []interface{}{env.OldParser, oldClassID}
	}
	data, err := linker.ABI.Pack(method, args...)
	if err != nil {
		t.Fatalf("pack %s: %v", method, err)
	}
	beforeNonce := stockS2bLinkHarnessAccountNonce(t, env, env.Linker)
	record := stockS2bLinkHarnessSend(t, env, &env.Linker, data, "register-"+kind, true)
	afterNonce := stockS2bLinkHarnessAccountNonce(t, env, env.Linker)
	if afterNonce != beforeNonce+1 {
		t.Fatalf("fresh %s metadata CREATE nonce before/after=%d/%d", kind, beforeNonce, afterNonce)
	}
	if len(record.Receipt.Logs) != 1 {
		t.Fatalf("fresh %s logs=%d", kind, len(record.Receipt.Logs))
	}
	values := stockS2bLinkHarnessCall(t, env, linker.ABI, env.Linker, method, args...)
	got := stockS2bLinkHarnessDecodeRegistration(t, values)
	got.Name, got.Class, got.Page, got.PageHash, got.PayloadHash, got.PageGas, got.RegisterGas = reg.Name, reg.Class, reg.Page, reg.PageHash, reg.PayloadHash, reg.PageGas, record.Receipt.GasUsed
	if got.RegisterGas > stockS2bLinkHarnessTxGas {
		t.Fatalf("%s registration gas=%d", kind, got.RegisterGas)
	}
	stockS2bLinkHarnessAssertRegistrationEvent(t, linker.ABI, record.Receipt, got)
	stockS2bLinkHarnessAssertClassRecord(t, env, linker.ABI, got)
	return got
}

func stockS2bLinkHarnessAssertIdempotent(t *testing.T, env *stockS2bLinkHarnessEnvironment, linker stock.Artifact, want stockS2bLinkHarnessRegistration, adapter bool, oldClassID common.Hash, kind string) {
	t.Helper()
	method := "registerClass"
	args := []interface{}{want.Page, want.PageHash, want.PayloadHash}
	if adapter {
		method = "registerFromS2a"
		args = []interface{}{env.OldParser, oldClassID}
	}
	data, err := linker.ABI.Pack(method, args...)
	if err != nil {
		t.Fatal(err)
	}
	beforeNonce := stockS2bLinkHarnessAccountNonce(t, env, env.Linker)
	beforeCode := stockS2bLinkHarnessCodeAt(t, env, want.MetadataPage)
	record := stockS2bLinkHarnessSend(t, env, &env.Linker, data, "idempotent-"+kind, true)
	afterNonce := stockS2bLinkHarnessAccountNonce(t, env, env.Linker)
	if len(record.Receipt.Logs) != 0 || afterNonce != beforeNonce {
		t.Fatalf("idempotent %s emitted logs or attempted CREATE: logs=%d nonce=%d/%d", kind, len(record.Receipt.Logs), beforeNonce, afterNonce)
	}
	got := stockS2bLinkHarnessDecodeRegistration(t, stockS2bLinkHarnessCall(t, env, linker.ABI, env.Linker, method, args...))
	if got.ClassID != want.ClassID || got.MetadataPage != want.MetadataPage || got.MetadataHash != want.MetadataHash || got.Methods != want.Methods || got.Literals != want.Literals || got.Calls != want.Calls {
		t.Fatalf("idempotent %s did not return real original six fields: got=%+v want=%+v", kind, got, want)
	}
	if afterCode := stockS2bLinkHarnessCodeAt(t, env, want.MetadataPage); !bytes.Equal(afterCode, beforeCode) {
		t.Fatalf("idempotent %s changed metadata code", kind)
	}
	stockS2bLinkHarnessAssertClassRecord(t, env, linker.ABI, want)
}

func stockS2bLinkHarnessDecodeRegistration(t *testing.T, values []interface{}) stockS2bLinkHarnessRegistration {
	t.Helper()
	if len(values) != 6 {
		t.Fatalf("registration return values=%d want 6", len(values))
	}
	return stockS2bLinkHarnessRegistration{ClassID: common.Hash(values[0].([32]byte)), MetadataPage: values[1].(common.Address), MetadataHash: common.Hash(values[2].([32]byte)), Methods: values[3].(uint16), Literals: values[4].(uint16), Calls: values[5].(uint16)}
}

func stockS2bLinkHarnessAssertRegistrationEvent(t *testing.T, contractABI abi.ABI, receipt *types.Receipt, reg stockS2bLinkHarnessRegistration) {
	t.Helper()
	event, ok := contractABI.Events["ClassRegistered"]
	if !ok {
		t.Fatal("linker ABI missing ClassRegistered")
	}
	log := receipt.Logs[0]
	if len(log.Topics) != 3 || log.Topics[0] != event.ID || log.Topics[1] != reg.ClassID || common.BytesToAddress(log.Topics[2][12:]) != reg.Page {
		t.Fatalf("malformed registration indexed event topics=%v", log.Topics)
	}
	values, err := event.Inputs.NonIndexed().Unpack(log.Data)
	if err != nil || len(values) != 5 || values[0].(common.Address) != reg.MetadataPage || common.Hash(values[1].([32]byte)) != reg.MetadataHash || values[2].(uint16) != reg.Methods || values[3].(uint16) != reg.Literals || values[4].(uint16) != reg.Calls {
		t.Fatalf("malformed registration event values=%v err=%v", values, err)
	}
}

func stockS2bLinkHarnessAssertClassRecord(t *testing.T, env *stockS2bLinkHarnessEnvironment, contractABI abi.ABI, reg stockS2bLinkHarnessRegistration) {
	t.Helper()
	values := stockS2bLinkHarnessCall(t, env, contractABI, env.Linker, "classRecord", reg.ClassID)
	if len(values) != 2 || values[0].(common.Address) != reg.MetadataPage || common.Hash(values[1].([32]byte)) != reg.MetadataHash {
		t.Fatalf("classRecord %s=%v", reg.Name, values)
	}
}

func stockS2bLinkHarnessReadMetadata(t *testing.T, env *stockS2bLinkHarnessEnvironment, reg stockS2bLinkHarnessRegistration) stockS2bLinkHarnessMetadata {
	t.Helper()
	code := stockS2bLinkHarnessCodeAt(t, env, reg.MetadataPage)
	wantLen := 1 + 256 + int(reg.Methods)*160 + int(reg.Literals)*8 + int(reg.Calls)*16
	if len(code) != wantLen || len(code) > 8192 || code[0] != 0 || crypto.Keccak256Hash(code) != reg.MetadataHash {
		t.Fatalf("%s metadata len/hash=%d/%s want=%d/%s", reg.Name, len(code), crypto.Keccak256Hash(code), wantLen, reg.MetadataHash)
	}
	word := func(index int) *big.Int {
		return new(big.Int).SetBytes(code[1+index*32 : 1+(index+1)*32])
	}
	if common.BigToHash(word(0)) != crypto.Keccak256Hash([]byte("JVMEVM:S2B:LINK:METADATA:4")) {
		t.Fatalf("%s metadata H0", reg.Name)
	}
	h1 := word(1)
	low160 := new(big.Int).And(new(big.Int).Set(h1), new(big.Int).Sub(new(big.Int).Lsh(big.NewInt(1), 160), big.NewInt(1)))
	if common.BigToAddress(low160) != reg.Page || stockS2bLinkHarnessField(h1, 160, 16) != uint64(reg.Class.Access) || new(big.Int).Rsh(new(big.Int).Set(h1), 176).Sign() != 0 {
		t.Fatalf("%s metadata H1 page/access/reserved", reg.Name)
	}
	if common.BigToHash(word(2)) != reg.PageHash || common.BigToHash(word(3)) != reg.PayloadHash || common.BigToHash(word(4)) != crypto.Keccak256Hash([]byte(reg.Class.Name)) || common.BigToHash(word(6)) != env.AnalyzerHash || word(7).Sign() != 0 {
		t.Fatalf("%s metadata identity headers", reg.Name)
	}
	h5 := word(5)
	if stockS2bLinkHarnessField(h5, 0, 32) != uint64(len(reg.Class.Raw)) || stockS2bLinkHarnessField(h5, 32, 16) != uint64(reg.Class.CPCount) || stockS2bLinkHarnessField(h5, 48, 16) != uint64(reg.Methods) || stockS2bLinkHarnessField(h5, 64, 16) != uint64(reg.Literals) || stockS2bLinkHarnessField(h5, 80, 16) != uint64(reg.Calls) || new(big.Int).Rsh(new(big.Int).Set(h5), 96).Sign() != 0 {
		t.Fatalf("%s metadata H5", reg.Name)
	}
	errors := 0
	for i := 0; i < int(reg.Methods); i++ {
		method := reg.Class.Methods[i]
		if common.BigToHash(word(8+i*5)) != crypto.Keccak256Hash([]byte(method.Name)) || common.BigToHash(word(8+i*5+1)) != crypto.Keccak256Hash([]byte(method.Descriptor)) {
			t.Fatalf("%s method %d name/descriptor hash", reg.Name, i)
		}
		m2 := word(8 + i*5 + 2)
		if stockS2bLinkHarnessField(m2, 0, 16) != uint64(i) || stockS2bLinkHarnessField(m2, 16, 16) != uint64(method.Access) {
			t.Fatalf("%s method %d index/access", reg.Name, i)
		}
		domain := stockS2bLinkHarnessField(m2, 112, 8)
		if domain != 0 {
			errors++
			for _, field := range [][2]uint{{32, 80}, {160, 64}, {224, 32}} {
				if stockS2bLinkHarnessField(m2, field[0], field[1]) != 0 {
					t.Fatalf("%s ineligible method %d leaked body/cache fields", reg.Name, i)
				}
			}
			if word(8+i*5+3).Sign() != 0 {
				t.Fatalf("%s ineligible method %d leaked start map", reg.Name, i)
			}
		} else {
			argc, returnKind := stockS2bLinkHarnessDescriptorEffect(t, method.Descriptor)
			if stockS2bLinkHarnessField(m2, 32, 32) != uint64(method.CodeOffset) || stockS2bLinkHarnessField(m2, 64, 16) != uint64(len(method.Code)) || stockS2bLinkHarnessField(m2, 80, 8) != uint64(method.MaxStack) || stockS2bLinkHarnessField(m2, 88, 8) != uint64(method.MaxLocals) || stockS2bLinkHarnessField(m2, 96, 8) != uint64(argc) || stockS2bLinkHarnessField(m2, 104, 8) != uint64(returnKind) || word(8+i*5+3).Bit(0) != 1 {
				t.Fatalf("%s eligible method %d body/envelope fields", reg.Name, i)
			}
		}
		if word(8+i*5+4).Sign() != 0 {
			t.Fatalf("%s method %d reserved word nonzero", reg.Name, i)
		}
	}
	literalBase := 1 + 256 + int(reg.Methods)*160
	lastMethod, lastPC := -1, -1
	for i := 0; i < int(reg.Literals); i++ {
		record := code[literalBase+i*8 : literalBase+(i+1)*8]
		methodIndex, pc := int(binary.BigEndian.Uint16(record)), int(binary.BigEndian.Uint16(record[2:]))
		if methodIndex >= len(reg.Class.Methods) || methodIndex < lastMethod || (methodIndex == lastMethod && pc <= lastPC) {
			t.Fatalf("%s malformed/unsorted literal %d: %x", reg.Name, i, record)
		}
		lastMethod, lastPC = methodIndex, pc
		method := reg.Class.Methods[methodIndex]
		if pc >= len(method.Code) {
			t.Fatalf("%s literal %d PC outside raw Code", reg.Name, i)
		}
		var cpIndex uint16
		switch method.Code[pc] {
		case 0x12:
			if pc+1 >= len(method.Code) {
				t.Fatalf("%s truncated ldc", reg.Name)
			}
			cpIndex = uint16(method.Code[pc+1])
		case 0x13:
			if pc+2 >= len(method.Code) {
				t.Fatalf("%s truncated ldc_w", reg.Name)
			}
			cpIndex = binary.BigEndian.Uint16(method.Code[pc+1:])
		default:
			t.Fatalf("%s literal %d is not raw ldc/ldc_w", reg.Name, i)
		}
		if int(cpIndex) >= len(reg.Class.CP) || reg.Class.CP[cpIndex].Tag != 3 || binary.BigEndian.Uint32(record[4:]) != reg.Class.CP[cpIndex].Bits {
			t.Fatalf("%s literal %d does not match raw CONSTANT_Integer", reg.Name, i)
		}
	}
	classID := crypto.Keccak256Hash(stockS2bLinkHarnessABIPack(t,
		[]string{"bytes32", "uint32", "bytes32", "bytes32", "address", "bytes32", "bytes32", "bytes32"},
		crypto.Keccak256Hash([]byte("JVMEVM:S2B:LINK:CLASS:4")), uint32(4), env.LinkerHash, env.AnalyzerHash, reg.Page, reg.PageHash, reg.PayloadHash, reg.MetadataHash))
	if classID != reg.ClassID {
		t.Fatalf("%s actual-code class ID=%s want %s", reg.Name, classID, reg.ClassID)
	}
	return stockS2bLinkHarnessMetadata{Code: code, Methods: reg.Methods, Literals: reg.Literals, Calls: reg.Calls, ErrorMethods: errors}
}

func stockS2bLinkHarnessVerifyCallRecords(t *testing.T, class stockS2bLinkHarnessClass, metadata stockS2bLinkHarnessMetadata) {
	t.Helper()
	code := metadata.Code
	word := func(index int) *big.Int { return new(big.Int).SetBytes(code[1+index*32 : 1+(index+1)*32]) }
	base := 1 + 256 + int(metadata.Methods)*160 + int(metadata.Literals)*8
	lastCaller, lastPC := -1, -1
	privateTarget, voidTarget, sixArgs, recursive, overload := false, false, false, false, false
	seenNames := make(map[string]string)
	for i := 0; i < int(metadata.Calls); i++ {
		record := code[base+i*16 : base+(i+1)*16]
		caller := int(binary.BigEndian.Uint16(record[0:2]))
		pc := int(binary.BigEndian.Uint16(record[2:4]))
		cpIndex := binary.BigEndian.Uint16(record[4:6])
		target := int(binary.BigEndian.Uint16(record[6:8]))
		argc, returnKind := record[8], record[9]
		if caller >= len(class.Methods) || target >= len(class.Methods) || !bytes.Equal(record[10:], make([]byte, 6)) || caller < lastCaller || (caller == lastCaller && pc <= lastPC) {
			t.Fatalf("%s malformed/unsorted call record %d: %x", class.Name, i, record)
		}
		lastCaller, lastPC = caller, pc
		packed := word(8 + caller*5 + 2)
		codeOffset := int(stockS2bLinkHarnessField(packed, 32, 32))
		codeLen := int(stockS2bLinkHarnessField(packed, 64, 16))
		if pc+2 >= codeLen || codeOffset+pc+2 >= len(class.Raw) || class.Raw[codeOffset+pc] != 0xb8 || binary.BigEndian.Uint16(class.Raw[codeOffset+pc+1:codeOffset+pc+3]) != cpIndex {
			t.Fatalf("%s call %d is not bound to raw b8 operand", class.Name, i)
		}
		if int(cpIndex) >= len(class.CP) || class.CP[cpIndex].Tag != 10 {
			t.Fatalf("%s call %d CP #%d is not Methodref", class.Name, i, cpIndex)
		}
		ref := class.CP[cpIndex]
		if int(ref.A) >= len(class.CP) || class.CP[ref.A].Tag != 7 || int(ref.B) >= len(class.CP) || class.CP[ref.B].Tag != 12 {
			t.Fatalf("%s call %d malformed TEST CP chain", class.Name, i)
		}
		ownerEntry, nat := class.CP[ref.A], class.CP[ref.B]
		owner := stockS2bLinkHarnessCPUtf8(t, class, ownerEntry.A)
		name := stockS2bLinkHarnessCPUtf8(t, class, nat.A)
		descriptor := stockS2bLinkHarnessCPUtf8(t, class, nat.B)
		if owner != class.Name {
			t.Fatalf("%s call %d owner=%q", class.Name, i, owner)
		}
		resolved := stockS2bLinkHarnessFindMethod(t, class, name, descriptor)
		if int(resolved.Index) != target {
			t.Fatalf("%s call %d target=%d raw exact target=%d %s%s", class.Name, i, target, resolved.Index, name, descriptor)
		}
		wantArgc, wantReturn := stockS2bLinkHarnessDescriptorEffect(t, descriptor)
		if argc != wantArgc || returnKind != wantReturn {
			t.Fatalf("%s call %d effect=%d/%d want=%d/%d", class.Name, i, argc, returnKind, wantArgc, wantReturn)
		}
		privateTarget = privateTarget || resolved.Access&0x0002 != 0
		voidTarget = voidTarget || returnKind == 0
		sixArgs = sixArgs || argc == 6
		recursive = recursive || caller == target
		if previous, ok := seenNames[name]; ok && previous != descriptor {
			overload = true
		} else {
			seenNames[name] = descriptor
		}
	}
	switch class.Name {
	case "M3aFrames":
		if !privateTarget || !voidTarget {
			t.Fatal("M3aFrames schema-4 calls did not retain private and void targets")
		}
	case "M3aRecursion":
		if !privateTarget || !recursive {
			t.Fatal("M3aRecursion schema-4 calls did not retain private recursion")
		}
	case "M3aStaticCalls":
		if !privateTarget || !sixArgs || !overload {
			t.Fatal("M3aStaticCalls schema-4 calls did not retain private/six-arg/overload targets")
		}
	}
}

func stockS2bLinkHarnessAssertCap(t *testing.T, manifest stockS2bLinkHarnessManifest, reg stockS2bLinkHarnessRegistration, metadata stockS2bLinkHarnessMetadata) {
	t.Helper()
	if int(reg.Methods) != manifest.Cap.Methods || int(reg.Literals) != manifest.Cap.Literals || int(reg.Calls) != manifest.Cap.Calls || len(metadata.Code)-1 != manifest.Cap.MetadataPayloadBytes || len(metadata.Code) != 7937 || metadata.ErrorMethods != 1 || reg.RegisterGas > stockS2bLinkHarnessTxGas {
		t.Fatalf("cap %s methods/literals/calls/payload/errors/gas=%d/%d/%d/%d/%d/%d", reg.Name, reg.Methods, reg.Literals, reg.Calls, len(metadata.Code)-1, metadata.ErrorMethods, reg.RegisterGas)
	}
}

func stockS2bLinkHarnessAssertOldRecordUnchanged(t *testing.T, env *stockS2bLinkHarnessEnvironment, parserABI abi.ABI, old stockS2bLinkHarnessRegistration) {
	t.Helper()
	values := stockS2bLinkHarnessCall(t, env, parserABI, env.OldParser, "classRecord", old.ClassID)
	if len(values) != 2 || values[0].(common.Address) != old.MetadataPage || common.Hash(values[1].([32]byte)) != old.MetadataHash || crypto.Keccak256Hash(stockS2bLinkHarnessCodeAt(t, env, old.MetadataPage)) != old.MetadataHash {
		t.Fatalf("S2b adapter changed old S2a record/page %s", old.Name)
	}
}

func stockS2bLinkHarnessAssertLinkerConfiguration(t *testing.T, env *stockS2bLinkHarnessEnvironment, linker stock.Artifact) {
	t.Helper()
	checks := []struct {
		method string
		want   interface{}
	}{{"analyzer", env.Analyzer}, {"analyzerCodeHash", [32]byte(env.AnalyzerHash)}, {"acceptedS2aParserHash", [32]byte(env.OldParserHash)}}
	for _, check := range checks {
		values := stockS2bLinkHarnessCall(t, env, linker.ABI, env.Linker, check.method)
		if len(values) != 1 || !reflect.DeepEqual(values[0], check.want) {
			t.Fatalf("linker getter %s=%v want %v", check.method, values, check.want)
		}
	}
	actual := stockS2bLinkHarnessCodeAt(t, env, env.Linker)
	stockS2bLinkHarnessAssertImmutableTemplate(t, linker.RuntimeCode, actual, S2bClassLinker)
	if crypto.Keccak256Hash(actual) != env.LinkerHash || env.LinkerHash == crypto.Keccak256Hash(linker.RuntimeCode) {
		t.Fatalf("actual linker immutable code hash=%s template=%s", env.LinkerHash, crypto.Keccak256Hash(linker.RuntimeCode))
	}
}

func stockS2bLinkHarnessAssertImmutableTemplate(t *testing.T, template, actual []byte, name string) {
	t.Helper()
	if len(template) != len(actual) {
		t.Fatalf("%s actual/template lengths=%d/%d", name, len(actual), len(template))
	}
	refs, err := CompilerImmutableReferences(name)
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
			t.Fatalf("%s deployed byte differs outside immutable at %d", name, i)
		}
	}
}

func stockS2bLinkHarnessCall(t *testing.T, env *stockS2bLinkHarnessEnvironment, contractABI abi.ABI, address common.Address, method string, args ...interface{}) []interface{} {
	t.Helper()
	data, err := contractABI.Pack(method, args...)
	if err != nil {
		t.Fatalf("pack %s: %v", method, err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()
	output, err := env.Backend.Client().CallContract(ctx, ethereum.CallMsg{To: &address, Gas: stockS2bLinkHarnessCallGas, Data: data}, nil)
	if err != nil {
		t.Fatalf("eth_call %s: %v", method, err)
	}
	values, err := contractABI.Unpack(method, output)
	if err != nil {
		t.Fatalf("unpack %s (%x): %v", method, output, err)
	}
	return values
}

func stockS2bLinkHarnessAccountNonce(t *testing.T, env *stockS2bLinkHarnessEnvironment, address common.Address) uint64 {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	nonce, err := env.Backend.Client().NonceAt(ctx, address, nil)
	if err != nil {
		t.Fatal(err)
	}
	return nonce
}

func stockS2bLinkHarnessCodeAt(t *testing.T, env *stockS2bLinkHarnessEnvironment, address common.Address) []byte {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	code, err := env.Backend.Client().CodeAt(ctx, address, nil)
	if err != nil {
		t.Fatal(err)
	}
	return code
}

func stockS2bLinkHarnessAssertExactCode(t *testing.T, env *stockS2bLinkHarnessEnvironment, address common.Address, want []byte, label string) {
	t.Helper()
	got := stockS2bLinkHarnessCodeAt(t, env, address)
	if !bytes.Equal(got, want) {
		t.Fatalf("%s code got len/hash=%d/%s want=%d/%s", label, len(got), crypto.Keccak256Hash(got), len(want), crypto.Keccak256Hash(want))
	}
}

func stockS2bLinkHarnessReplayDirect(t *testing.T, env *stockS2bLinkHarnessEnvironment) stockS2bLinkHarnessReplay {
	t.Helper()
	config := *params.AllDevChainProtocolChanges
	genesis := &core.Genesis{Config: &config, GasLimit: stockS2bLinkHarnessBlockGas, Alloc: types.GenesisAlloc{env.Sender: {Balance: new(big.Int).Exp(big.NewInt(10), big.NewInt(26), nil)}}}
	disk := rawdb.NewMemoryDatabase()
	trieDB := triedb.NewDatabase(disk, triedb.HashDefaults)
	genesisBlock := genesis.MustCommit(disk, trieDB)
	stateDB, err := state.New(genesisBlock.Root(), state.NewDatabase(trieDB, nil))
	if err != nil {
		t.Fatal(err)
	}
	result := stockS2bLinkHarnessReplay{Gas: make([]uint64, 0, len(env.Records)), State: stateDB}
	signer := types.LatestSignerForChainID(new(big.Int).SetUint64(stockS2bLinkHarnessChainID))
	for i, record := range env.Records {
		header := record.Header
		message, err := core.TransactionToMessage(record.Tx, signer, header.BaseFee)
		if err != nil {
			t.Fatalf("TransactionToMessage %s: %v", record.Kind, err)
		}
		if message.From != env.Sender || message.Nonce != uint64(i) || message.SkipNonceChecks || message.SkipTransactionChecks {
			t.Fatalf("%s direct signed message checks", record.Kind)
		}
		stateDB.SetTxContext(record.Tx.Hash(), i)
		evm := vm.NewEVM(stockS2bLinkHarnessBlockContext(header), stateDB, &config, vm.Config{})
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
	if crypto.Keccak256Hash(stateDB.GetCode(env.Analyzer)) != env.AnalyzerHash || crypto.Keccak256Hash(stateDB.GetCode(env.Linker)) != env.LinkerHash || crypto.Keccak256Hash(stateDB.GetCode(env.OldParser)) != env.OldParserHash {
		t.Fatal("direct replay changed deployed component code")
	}
	return result
}

func stockS2bLinkHarnessBlockContext(header *types.Header) vm.BlockContext {
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
	return vm.BlockContext{CanTransfer: core.CanTransfer, Transfer: core.Transfer, GetHash: func(uint64) common.Hash { return common.Hash{} }, Coinbase: header.Coinbase, GasLimit: header.GasLimit, BlockNumber: new(big.Int).Set(header.Number), Time: header.Time, Difficulty: difficulty, BaseFee: baseFee, BlobBaseFee: new(big.Int), Random: random}
}

func stockS2bLinkHarnessLoadFixtures(t *testing.T) (stockS2bLinkHarnessManifest, map[string]stockS2bLinkHarnessClass, string) {
	t.Helper()
	raw, err := os.ReadFile(filepath.Join(stockS2bLinkHarnessFixtureRoot, "manifest.json"))
	if err != nil {
		t.Fatal(err)
	}
	var manifest stockS2bLinkHarnessManifest
	if err := json.Unmarshal(raw, &manifest); err != nil {
		t.Fatal(err)
	}
	if manifest.Schema != 4 || manifest.CatalogueRows != 268 || manifest.CatalogueRoots != 94 || manifest.M3aRows != 67 || len(manifest.Classes) != 14 || manifest.Cap.ClassSHA256 != stockS2bLinkHarnessCapHash {
		t.Fatalf("invalid fixture manifest schema/rows/roots/M3a/classes/cap=%d/%d/%d/%d/%d/%s", manifest.Schema, manifest.CatalogueRows, manifest.CatalogueRoots, manifest.M3aRows, len(manifest.Classes), manifest.Cap.ClassSHA256)
	}
	output := t.TempDir()
	args := []string{"--release", "8", "-d", output, filepath.Join(stockS2bLinkHarnessSourceRoot, "OracleMain.java")}
	seen := make(map[string]bool)
	for _, pin := range manifest.Classes {
		if pin.Name == "" || seen[pin.Name] || pin.Source != pin.Name+".java" {
			t.Fatalf("bad duplicate/source class pin %+v", pin)
		}
		seen[pin.Name] = true
		sourcePath := filepath.Join(stockS2bLinkHarnessSourceRoot, pin.Source)
		source, err := os.ReadFile(sourcePath)
		if err != nil {
			t.Fatal(err)
		}
		if got := fmt.Sprintf("%x", sha256.Sum256(source)); got != pin.SourceSHA256 {
			t.Fatalf("%s source SHA-256=%s want %s", pin.Name, got, pin.SourceSHA256)
		}
		args = append(args, sourcePath)
	}
	stockS2bLinkHarnessCommand(t, time.Minute, stockS2bLinkHarnessLookPath(t, "javac"), args...)
	classes := make(map[string]stockS2bLinkHarnessClass, len(manifest.Classes))
	for _, pin := range manifest.Classes {
		classRaw, err := os.ReadFile(filepath.Join(output, pin.Name+".class"))
		if err != nil {
			t.Fatal(err)
		}
		if len(classRaw) != pin.ClassBytes || fmt.Sprintf("%x", sha256.Sum256(classRaw)) != pin.ClassSHA256 {
			t.Fatalf("%s javac --release 8 raw bytes/hash=%d/%x want=%d/%s", pin.Name, len(classRaw), sha256.Sum256(classRaw), pin.ClassBytes, pin.ClassSHA256)
		}
		class := stockS2bLinkHarnessParseClass(t, classRaw)
		if class.Name != pin.Name || len(class.Methods) != pin.Methods {
			t.Fatalf("%s parsed name/methods=%s/%d", pin.Name, class.Name, len(class.Methods))
		}
		classes[pin.Name] = class
	}
	return manifest, classes, output
}

func stockS2bLinkHarnessReadCatalogue(t *testing.T, raw []byte) []stockS2bLinkHarnessCatalogueRow {
	t.Helper()
	scanner := bufio.NewScanner(bytes.NewReader(raw))
	scanner.Buffer(make([]byte, 4096), 1<<20)
	var rows []stockS2bLinkHarnessCatalogueRow
	for scanner.Scan() {
		var row stockS2bLinkHarnessCatalogueRow
		if err := json.Unmarshal(scanner.Bytes(), &row); err != nil {
			t.Fatalf("catalogue line %d: %v", len(rows)+1, err)
		}
		rows = append(rows, row)
	}
	if err := scanner.Err(); err != nil {
		t.Fatal(err)
	}
	return rows
}

func stockS2bLinkHarnessParseClass(t *testing.T, raw []byte) stockS2bLinkHarnessClass {
	t.Helper()
	if len(raw) < 10 || binary.BigEndian.Uint32(raw[:4]) != 0xcafebabe {
		t.Fatal("TEST-only class parser: bad header")
	}
	p := 8
	need := func(n int) {
		if n < 0 || p+n > len(raw) {
			t.Fatalf("TEST-only class parser: truncated at %d need %d of %d", p, n, len(raw))
		}
	}
	u1 := func() byte { need(1); v := raw[p]; p++; return v }
	u2 := func() uint16 { need(2); v := binary.BigEndian.Uint16(raw[p : p+2]); p += 2; return v }
	u4 := func() uint32 { need(4); v := binary.BigEndian.Uint32(raw[p : p+4]); p += 4; return v }
	cpCount := u2()
	cp := make([]stockS2bLinkHarnessCP, cpCount)
	for i := uint16(1); i < cpCount; i++ {
		tag := u1()
		cp[i].Tag = tag
		switch tag {
		case 1:
			n := int(u2())
			need(n)
			cp[i].Text = string(raw[p : p+n])
			p += n
		case 3:
			cp[i].Bits = u4()
		case 4:
			need(4)
			p += 4
		case 5, 6:
			need(8)
			p += 8
			i++
		case 7, 8, 16, 19, 20:
			cp[i].A = u2()
		case 9, 10, 11, 12, 17, 18:
			cp[i].A, cp[i].B = u2(), u2()
		case 15:
			_ = u1()
			cp[i].A = u2()
		default:
			t.Fatalf("TEST-only class parser: unsupported CP tag %d at %d", tag, i)
		}
	}
	access, thisClass := u2(), u2()
	_ = u2() // super
	if int(thisClass) >= len(cp) || cp[thisClass].Tag != 7 {
		t.Fatal("TEST-only class parser: bad this_class")
	}
	className := stockS2bLinkHarnessCPUtf8Raw(t, cp, cp[thisClass].A)
	interfaces := int(u2())
	need(2 * interfaces)
	p += 2 * interfaces
	skipAttributes := func(count int) {
		for i := 0; i < count; i++ {
			_ = u2()
			n := int(u4())
			need(n)
			p += n
		}
	}
	fields := int(u2())
	for i := 0; i < fields; i++ {
		need(6)
		p += 6
		skipAttributes(int(u2()))
	}
	methodCount := int(u2())
	methods := make([]stockS2bLinkHarnessMethod, methodCount)
	for i := 0; i < methodCount; i++ {
		method := stockS2bLinkHarnessMethod{Index: uint16(i), Access: u2()}
		nameIndex, descriptorIndex, attributes := u2(), u2(), int(u2())
		method.Name = stockS2bLinkHarnessCPUtf8Raw(t, cp, nameIndex)
		method.Descriptor = stockS2bLinkHarnessCPUtf8Raw(t, cp, descriptorIndex)
		for j := 0; j < attributes; j++ {
			attributeName := stockS2bLinkHarnessCPUtf8Raw(t, cp, u2())
			length := int(u4())
			need(length)
			end := p + length
			if attributeName == "Code" {
				maxStack, maxLocals := u2(), u2()
				if maxStack > 255 || maxLocals > 255 {
					t.Fatalf("TEST-only class parser: oversized stack/locals")
				}
				method.MaxStack, method.MaxLocals = uint8(maxStack), uint8(maxLocals)
				codeLength := int(u4())
				need(codeLength)
				method.CodeOffset = uint32(p)
				method.Code = append([]byte(nil), raw[p:p+codeLength]...)
			}
			p = end
		}
		methods[i] = method
	}
	skipAttributes(int(u2()))
	if p != len(raw) {
		t.Fatalf("TEST-only class parser: trailing bytes %d/%d", p, len(raw))
	}
	return stockS2bLinkHarnessClass{Name: className, Access: access, CPCount: cpCount, Raw: append([]byte(nil), raw...), CP: cp, Methods: methods}
}

func stockS2bLinkHarnessCPUtf8Raw(t *testing.T, cp []stockS2bLinkHarnessCP, index uint16) string {
	t.Helper()
	if int(index) >= len(cp) || cp[index].Tag != 1 {
		t.Fatalf("TEST-only class parser: CP #%d is not Utf8", index)
	}
	return cp[index].Text
}

func stockS2bLinkHarnessCPUtf8(t *testing.T, class stockS2bLinkHarnessClass, index uint16) string {
	t.Helper()
	return stockS2bLinkHarnessCPUtf8Raw(t, class.CP, index)
}

func stockS2bLinkHarnessFindMethod(t *testing.T, class stockS2bLinkHarnessClass, name, descriptor string) stockS2bLinkHarnessMethod {
	t.Helper()
	var found *stockS2bLinkHarnessMethod
	for i := range class.Methods {
		if class.Methods[i].Name == name && class.Methods[i].Descriptor == descriptor {
			if found != nil {
				t.Fatalf("TEST-only exact method lookup duplicate %s.%s%s", class.Name, name, descriptor)
			}
			copy := class.Methods[i]
			found = &copy
		}
	}
	if found == nil {
		t.Fatalf("TEST-only exact method lookup missing %s.%s%s", class.Name, name, descriptor)
	}
	return *found
}

func stockS2bLinkHarnessDescriptorEffect(t *testing.T, descriptor string) (uint8, uint8) {
	t.Helper()
	if len(descriptor) < 3 || descriptor[0] != '(' {
		t.Fatalf("bad TEST descriptor %q", descriptor)
	}
	end := strings.IndexByte(descriptor, ')')
	if end < 1 || end+2 != len(descriptor) {
		t.Fatalf("bad TEST descriptor %q", descriptor)
	}
	for _, c := range descriptor[1:end] {
		if c != 'I' {
			t.Fatalf("non-int TEST descriptor %q", descriptor)
		}
	}
	argc := end - 1
	if argc > 6 || (descriptor[end+1] != 'I' && descriptor[end+1] != 'V') {
		t.Fatalf("out-of-profile TEST descriptor %q", descriptor)
	}
	return uint8(argc), map[bool]uint8{false: 0, true: 1}[descriptor[end+1] == 'I']
}

func stockS2bLinkHarnessReadHex(t *testing.T, path string) []byte {
	t.Helper()
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	decoded, err := hex.DecodeString(strings.TrimSpace(string(raw)))
	if err != nil {
		t.Fatalf("decode %s: %v", path, err)
	}
	return decoded
}

func stockS2bLinkHarnessCommand(t *testing.T, timeout time.Duration, command string, args ...string) string {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	output, err := exec.CommandContext(ctx, command, args...).CombinedOutput()
	if err != nil {
		t.Fatalf("%s %s: %v\n%s", command, strings.Join(args, " "), err, output)
	}
	return strings.TrimSpace(string(output))
}

func stockS2bLinkHarnessLookPath(t *testing.T, name string) string {
	t.Helper()
	path, err := exec.LookPath(name)
	if err != nil {
		t.Fatalf("required test tool %s: %v", name, err)
	}
	return path
}

func stockS2bLinkHarnessLoadArtifact(t *testing.T, name string) stock.Artifact {
	t.Helper()
	artifact, err := LoadArtifact(name)
	if err != nil {
		t.Fatalf("required S2b-L artifact %s: %v", name, err)
	}
	return artifact
}

func stockS2bLinkHarnessLoadS2aArtifact(t *testing.T, name string) stock.Artifact {
	t.Helper()
	artifact, err := s2a.LoadArtifact(name)
	if err != nil {
		t.Fatalf("accepted S2a artifact %s: %v", name, err)
	}
	return artifact
}

func stockS2bLinkHarnessLoadStockArtifact(t *testing.T, name string) stock.Artifact {
	t.Helper()
	artifact, err := stock.LoadArtifact(name)
	if err != nil {
		t.Fatalf("accepted stock artifact %s: %v", name, err)
	}
	return artifact
}

func stockS2bLinkHarnessField(word *big.Int, shift, bits uint) uint64 {
	value := new(big.Int).Rsh(new(big.Int).Set(word), shift)
	value.And(value, new(big.Int).Sub(new(big.Int).Lsh(big.NewInt(1), bits), big.NewInt(1)))
	return value.Uint64()
}

func stockS2bLinkHarnessABIPack(t *testing.T, typeNames []string, values ...interface{}) []byte {
	t.Helper()
	if len(typeNames) != len(values) {
		t.Fatalf("ABI type/value count %d/%d", len(typeNames), len(values))
	}
	arguments := make(abi.Arguments, len(typeNames))
	for i, name := range typeNames {
		typ, err := abi.NewType(name, "", nil)
		if err != nil {
			t.Fatal(err)
		}
		arguments[i] = abi.Argument{Type: typ}
	}
	encoded, err := arguments.Pack(values...)
	if err != nil {
		t.Fatal(err)
	}
	return encoded
}

func stockS2bLinkHarnessReceiptGas(records []stockS2bLinkHarnessTxRecord) []uint64 {
	gas := make([]uint64, len(records))
	for i, record := range records {
		gas[i] = record.Receipt.GasUsed
	}
	return gas
}

func stockS2bLinkHarnessSumGas(records []stockS2bLinkHarnessTxRecord) uint64 {
	var gas uint64
	for _, record := range records {
		gas += record.Receipt.GasUsed
	}
	return gas
}
