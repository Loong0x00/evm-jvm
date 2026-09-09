// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"context"
	"crypto/sha256"
	"embed"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"testing"
	"time"
)

const (
	mcLB0HarnessOrdinaryGas      = uint64(100_000_000)
	mcLB0HarnessBoundaryGas      = uint64(1_000_000_000)
	mcLB0HarnessOrdinaryWatchdog = 30 * time.Second
	mcLB0HarnessBoundaryWatchdog = 120 * time.Second
)

//go:embed testdata/local/lb0
var mcLB0HarnessFixtures embed.FS

type mcLB0HarnessProfile struct {
	Gas             uint64 `json:"gas"`
	WatchdogSeconds int    `json:"watchdog_seconds"`
}

type mcLB0HarnessCase struct {
	ID         string   `json:"id"`
	Profile    string   `json:"profile"`
	ABI        string   `json:"abi"`
	Classes    []string `json:"classes"`
	EntryClass string   `json:"entry_class"`
	Method     string   `json:"method"`
	Args       []int32  `json:"args"`
	Expected   int32    `json:"expected"`
	Repeat     int      `json:"repeat"`
}

type mcLB0HarnessCatalogue struct {
	Schema    int                            `json:"schema"`
	CaseCount int                            `json:"case_count"`
	Profiles  map[string]mcLB0HarnessProfile `json:"profiles"`
	Cases     []mcLB0HarnessCase             `json:"cases"`
}

type mcLB0HarnessManifestEntry struct {
	Bytes    int    `json:"bytes"`
	RawBytes int    `json:"raw_bytes"`
	SHA256   string `json:"sha256"`
}

type mcLB0HarnessManifest struct {
	Schema      int                                  `json:"schema"`
	ClassCount  int                                  `json:"class_count"`
	Classes     map[string]mcLB0HarnessManifestEntry `json:"classes"`
	SourceCount int                                  `json:"source_count"`
	Sources     map[string]mcLB0HarnessManifestEntry `json:"sources"`
	Catalogue   mcLB0HarnessManifestEntry            `json:"catalogue"`
}

type mcLB0HarnessEVMRequest struct {
	ABI        string   `json:"abi"`
	Classes    [][]byte `json:"classes"`
	EntryClass string   `json:"entry_class"`
	Method     string   `json:"method"`
	Args       []int32  `json:"args"`
	Gas        uint64   `json:"gas"`
}

type mcLB0HarnessEVMResponse struct {
	Result Result `json:"result"`
	Error  string `json:"error,omitempty"`
}

func mcLB0HarnessReadJSON(t *testing.T, name string, out interface{}) []byte {
	t.Helper()
	path := "testdata/local/lb0/" + name
	data, err := mcLB0HarnessFixtures.ReadFile(path)
	if err != nil {
		t.Fatalf("read %s: %v", path, err)
	}
	if err := json.Unmarshal(data, out); err != nil {
		t.Fatalf("decode %s: %v", path, err)
	}
	return data
}

func mcLB0HarnessLoadCatalogue(t *testing.T) mcLB0HarnessCatalogue {
	t.Helper()
	var catalogue mcLB0HarnessCatalogue
	mcLB0HarnessReadJSON(t, "catalogue.json", &catalogue)
	if catalogue.Schema != 1 || catalogue.CaseCount != 64 || len(catalogue.Cases) != 64 {
		t.Fatalf("catalogue schema/count = %d/%d/%d, want 1/64/64", catalogue.Schema, catalogue.CaseCount, len(catalogue.Cases))
	}
	wantProfiles := map[string]mcLB0HarnessProfile{
		"ordinary": {Gas: mcLB0HarnessOrdinaryGas, WatchdogSeconds: int(mcLB0HarnessOrdinaryWatchdog / time.Second)},
		"boundary": {Gas: mcLB0HarnessBoundaryGas, WatchdogSeconds: int(mcLB0HarnessBoundaryWatchdog / time.Second)},
	}
	for name, want := range wantProfiles {
		if got := catalogue.Profiles[name]; got != want {
			t.Fatalf("profile %s = %+v, want %+v", name, got, want)
		}
	}
	ids := make(map[string]bool)
	profileCounts := make(map[string]int)
	for i, test := range catalogue.Cases {
		if test.ID == "" || ids[test.ID] {
			t.Fatalf("catalogue row %d has empty/duplicate id %q", i, test.ID)
		}
		ids[test.ID] = true
		if _, ok := wantProfiles[test.Profile]; !ok {
			t.Fatalf("catalogue row %s has unknown profile %q", test.ID, test.Profile)
		}
		profileCounts[test.Profile]++
		if test.ABI != "run" && test.ABI != "run_classes" {
			t.Fatalf("catalogue row %s has unknown ABI %q", test.ID, test.ABI)
		}
		if len(test.Classes) == 0 || test.EntryClass == "" || test.Method == "" || test.Repeat < 1 {
			t.Fatalf("catalogue row %s has incomplete invocation metadata", test.ID)
		}
		if test.ABI == "run" && (len(test.Classes) != 1 || test.EntryClass != test.Classes[0]) {
			t.Fatalf("catalogue row %s is not a single-class Run invocation", test.ID)
		}
	}
	if profileCounts["ordinary"] != 62 || profileCounts["boundary"] != 2 {
		t.Fatalf("catalogue profile counts = %v, want ordinary=62 boundary=2", profileCounts)
	}
	return catalogue
}

func mcLB0HarnessClass(t *testing.T, name string) []byte {
	t.Helper()
	data, err := mcLB0HarnessFixtures.ReadFile("testdata/local/lb0/classes/" + name + ".class.hex")
	if err != nil {
		t.Fatalf("read class %s: %v", name, err)
	}
	classfile, err := hex.DecodeString(strings.TrimSpace(string(data)))
	if err != nil {
		t.Fatalf("decode class %s: %v", name, err)
	}
	return classfile
}

func mcLB0HarnessBundle(t *testing.T, names []string) [][]byte {
	t.Helper()
	bundle := make([][]byte, len(names))
	for i, name := range names {
		bundle[i] = mcLB0HarnessClass(t, name)
	}
	return bundle
}

func mcLB0HarnessJava(t *testing.T, env, fallback string, version *regexp.Regexp) string {
	t.Helper()
	path := os.Getenv(env)
	if path == "" {
		path = fallback
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	output, err := exec.CommandContext(ctx, path, "-version").CombinedOutput()
	if err != nil || !version.Match(output) {
		t.Fatalf("%s=%q is not the required JVM: %v\n%s", env, path, err, output)
	}
	return path
}

func mcLB0HarnessOracleDir(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	manifest := mcLB0HarnessLoadManifest(t)
	for file := range manifest.Classes {
		name := strings.TrimSuffix(file, ".class.hex")
		if err := os.WriteFile(filepath.Join(dir, name+".class"), mcLB0HarnessClass(t, name), 0o600); err != nil {
			t.Fatal(err)
		}
	}
	const source = `public final class MCLB0Oracle { public static void main(String[] a)throws Exception{Class<?> c=Class.forName(a[0]);Class<?>[] p=new Class<?>[a.length-2];Object[] v=new Object[p.length];for(int i=0;i<p.length;i++){p[i]=Integer.TYPE;v[i]=Integer.valueOf(a[i+2]);}System.out.print(c.getMethod(a[1],p).invoke(null,v));}}`
	path := filepath.Join(dir, "MCLB0Oracle.java")
	if err := os.WriteFile(path, []byte(source), 0o600); err != nil {
		t.Fatal(err)
	}
	javac := os.Getenv("JAVA_EVM_JAVAC21")
	if javac == "" {
		javac = "/usr/lib/jvm/jdk-21.0.9/bin/javac"
	}
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	if output, err := exec.CommandContext(ctx, javac, "-J-Xmx64m", "--release", "8", "-g:none", "-d", dir, path).CombinedOutput(); err != nil {
		t.Fatalf("compile trusted MC-LB0 host oracle with %q: %v\n%s", javac, err, output)
	}
	return dir
}

func mcLB0HarnessOracleValue(t *testing.T, java, classPath string, test mcLB0HarnessCase) int32 {
	t.Helper()
	argv := []string{"-Xmx64m", "-cp", classPath, "MCLB0Oracle", test.EntryClass, test.Method}
	for _, arg := range test.Args {
		argv = append(argv, strconv.FormatInt(int64(arg), 10))
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	output, err := exec.CommandContext(ctx, java, argv...).CombinedOutput()
	if err != nil {
		t.Fatalf("bounded JVM oracle %s.%s%v failed: %v\n%s", test.EntryClass, test.Method, test.Args, err, output)
	}
	value, err := strconv.ParseInt(strings.TrimSpace(string(output)), 10, 32)
	if err != nil {
		t.Fatalf("JVM oracle %s.%s%v returned non-int32 %q: %v", test.EntryClass, test.Method, test.Args, output, err)
	}
	return int32(value)
}

func mcLB0HarnessLoadManifest(t *testing.T) mcLB0HarnessManifest {
	t.Helper()
	var manifest mcLB0HarnessManifest
	mcLB0HarnessReadJSON(t, "manifest.json", &manifest)
	return manifest
}

func mcLB0HarnessHash(data []byte) string {
	hash := sha256.Sum256(data)
	return hex.EncodeToString(hash[:])
}

func mcLB0HarnessOpcodes(t *testing.T, classfile []byte, method string) map[byte]int {
	t.Helper()
	code := parseTestClass(t, classfile).methodCode(t, method)
	counts := make(map[byte]int)
	for pc := 0; pc < len(code); {
		counts[code[pc]]++
		pc += verifyM5baInstructionWidth(t, code, pc)
	}
	return counts
}

func mcLB0HarnessRequireOpcode(t *testing.T, classfile []byte, method string, opcode byte, minimum int) {
	t.Helper()
	if got := mcLB0HarnessOpcodes(t, classfile, method)[opcode]; got < minimum {
		t.Fatalf("%s has %d opcode 0x%02x, want at least %d", method, got, opcode, minimum)
	}
}

func TestMCLB0HarnessPinnedCatalogueFixturesAndBytecode(t *testing.T) {
	catalogue := mcLB0HarnessLoadCatalogue(t)
	manifest := mcLB0HarnessLoadManifest(t)
	if manifest.Schema != 1 || manifest.ClassCount != 9 || len(manifest.Classes) != 9 || manifest.SourceCount != 11 || len(manifest.Sources) != 11 {
		t.Fatalf("manifest counts = schema%d classes%d/%d sources%d/%d", manifest.Schema, manifest.ClassCount, len(manifest.Classes), manifest.SourceCount, len(manifest.Sources))
	}
	catalogueBytes, err := mcLB0HarnessFixtures.ReadFile("testdata/local/lb0/catalogue.json")
	if err != nil {
		t.Fatal(err)
	}
	if got := mcLB0HarnessHash(catalogueBytes); got != manifest.Catalogue.SHA256 || len(catalogueBytes) != manifest.Catalogue.Bytes {
		t.Fatalf("catalogue pin = %s/%d, want %s/%d", got, len(catalogueBytes), manifest.Catalogue.SHA256, manifest.Catalogue.Bytes)
	}
	for file, pin := range manifest.Classes {
		name := strings.TrimSuffix(file, ".class.hex")
		classfile := mcLB0HarnessClass(t, name)
		if got := mcLB0HarnessHash(classfile); got != pin.SHA256 || len(classfile) != pin.RawBytes {
			t.Fatalf("class %s pin = %s/%d, want %s/%d", file, got, len(classfile), pin.SHA256, pin.RawBytes)
		}
	}
	for file, pin := range manifest.Sources {
		data, err := mcLB0HarnessFixtures.ReadFile("testdata/local/lb0/" + file)
		if err != nil {
			t.Fatal(err)
		}
		if got := mcLB0HarnessHash(data); got != pin.SHA256 || len(data) != pin.Bytes {
			t.Fatalf("source %s pin = %s/%d, want %s/%d", file, got, len(data), pin.SHA256, pin.Bytes)
		}
		for _, forbidden := range []string{"new String", ".getClass(", "static void main", "String.format", "System.out", "System.err"} {
			if bytes.Contains(data, []byte(forbidden)) {
				t.Fatalf("positive fixture source %s contains excluded API marker %q", file, forbidden)
			}
		}
	}
	for _, test := range catalogue.Cases {
		class := parseStaticsClass(t, mcLB0HarnessClass(t, test.EntryClass))
		wantDescriptor := "(" + strings.Repeat("I", len(test.Args)) + ")I"
		found := false
		for _, method := range class.methods {
			if method.name == test.Method && method.descriptor == wantDescriptor {
				found = true
				if method.access&0x0009 != 0x0009 || len(method.code) == 0 {
					t.Fatalf("catalogue row %s root flags/code = 0x%x/%d, want public static Code", test.ID, method.access, len(method.code))
				}
			}
		}
		if !found {
			t.Fatalf("catalogue row %s lacks exact root %s.%s%s", test.ID, test.EntryClass, test.Method, wantDescriptor)
		}
	}

	root := mcLB0HarnessClass(t, "MCLB0Root")
	for _, method := range []string{"emptyLength", "nulChar", "wrappedHash", "equalsNonString", "compareUnsignedUnit", "toStringIdentity", "internIdentity", "cpHitAfterCalls"} {
		mcLB0HarnessRequireOpcode(t, root, method, 0x12, 1) // ldc: literal not folded away
		mcLB0HarnessRequireOpcode(t, root, method, 0xb6, 1) // invokevirtual: requested String call remains
	}
	mcLB0HarnessRequireOpcode(t, root, "cpHitAfterCalls", 0x12, 2)
	mcLB0HarnessRequireOpcode(t, root, "crossFieldIdentity", 0xb2, 1)
	mcLB0HarnessRequireOpcode(t, root, "staticNonfinalIdentity", 0xb2, 1)
	mcLB0HarnessRequireOpcode(t, root, "charSequenceLength", 0xb9, 1)
	mcLB0HarnessRequireOpcode(t, root, "charSequenceChar", 0xb9, 1)
	for _, method := range []string{"comparableLess", "bridgeCCE", "bridgeNPE"} {
		mcLB0HarnessRequireOpcode(t, root, method, 0xb9, 1)
	}
	mcLB0HarnessRequireOpcode(t, root, "stringBeforeMixed", 0xbc, 1)
	mcLB0HarnessRequireOpcode(t, root, "stringBeforeMixed", 0xbb, 1)
	mcLB0HarnessRequireOpcode(t, root, "stringThenException", 0xbc, 1)
	mcLB0HarnessRequireOpcode(t, mcLB0HarnessClass(t, "MCLB0RawStaticConsumer"), "run", 0xb2, 2)

	for _, raw := range []struct {
		name       string
		wantStatic bool
	}{
		{"MCLB0RawStatic", true},
		{"MCLB0RawInstance", false},
	} {
		class := parseStaticsClass(t, mcLB0HarnessClass(t, raw.name))
		if len(class.fields) != 1 || class.fields[0].descriptor != "Ljava/lang/String;" || class.fields[0].attribute(t, "ConstantValue") == nil {
			t.Fatalf("%s does not retain one String ConstantValue field", raw.name)
		}
		flags := class.fields[0].access
		if flags&0x0010 != 0 || (flags&0x0008 != 0) != raw.wantStatic {
			t.Fatalf("%s field flags = 0x%x, want non-final static=%v", raw.name, flags, raw.wantStatic)
		}
	}
	if !bytes.Contains(root, []byte{0xc0, 0x80}) || !bytes.Contains(root, []byte{0xed, 0xa0, 0x80}) || !bytes.Contains(root, []byte{0xed, 0xb0, 0x80}) {
		t.Fatal("root class lacks pinned MUTF-8 NUL/high-surrogate/low-surrogate payloads")
	}
	if catalogue.Cases[0].ABI != "run" {
		t.Fatal("catalogue must exercise Run as well as RunClasses")
	}
}

func TestMCLB0HarnessJava8And21Catalogue(t *testing.T) {
	catalogue := mcLB0HarnessLoadCatalogue(t)
	java8 := mcLB0HarnessJava(t, "JAVA_EVM_JAVA8", "/usr/lib/jvm/java-8-openjdk/bin/java", regexp.MustCompile(`(?m)version "1\.8\.`))
	java21 := mcLB0HarnessJava(t, "JAVA_EVM_JAVA21", "/usr/lib/jvm/jdk-21.0.9/bin/java", regexp.MustCompile(`(?m)version "21\.`))
	classPath := mcLB0HarnessOracleDir(t)
	for _, test := range catalogue.Cases {
		test := test
		t.Run(test.ID, func(t *testing.T) {
			got8 := mcLB0HarnessOracleValue(t, java8, classPath, test)
			got21 := mcLB0HarnessOracleValue(t, java21, classPath, test)
			if got8 != got21 || got8 != test.Expected {
				t.Fatalf("Java8/21 %s.%s%v = %d/%d, pinned %d", test.EntryClass, test.Method, test.Args, got8, got21, test.Expected)
			}
		})
	}
}

// TestMCLB0HarnessEVMProcess is a subprocess-only watchdog target. It invokes the
// same public Run/RunClasses ABI as callers; the parent transports only raw class
// bytes and invocation metadata and kills this process at the frozen wall limit.
func TestMCLB0HarnessEVMProcess(t *testing.T) {
	if os.Getenv("MC_LB0_EVM_PROCESS") != "1" {
		return
	}
	requestPath, responsePath := os.Getenv("MC_LB0_EVM_REQUEST"), os.Getenv("MC_LB0_EVM_RESPONSE")
	requestData, err := os.ReadFile(requestPath)
	if err != nil {
		t.Fatal(err)
	}
	var request mcLB0HarnessEVMRequest
	if err := json.Unmarshal(requestData, &request); err != nil {
		t.Fatal(err)
	}
	var result Result
	if request.ABI == "run" {
		if len(request.Classes) != 1 {
			err = fmt.Errorf("Run received %d classes", len(request.Classes))
		} else {
			result, err = Run(request.Classes[0], request.Method, request.Args, request.Gas)
		}
	} else if request.ABI == "run_classes" {
		result, err = RunClasses(request.Classes, request.EntryClass, request.Method, request.Args, request.Gas)
	} else {
		err = fmt.Errorf("unknown ABI %q", request.ABI)
	}
	response := mcLB0HarnessEVMResponse{Result: result}
	if err != nil {
		response.Error = err.Error()
	}
	data, marshalErr := json.Marshal(response)
	if marshalErr != nil {
		t.Fatal(marshalErr)
	}
	if writeErr := os.WriteFile(responsePath, data, 0o600); writeErr != nil {
		t.Fatal(writeErr)
	}
}

func mcLB0HarnessEVMValue(t *testing.T, test mcLB0HarnessCase, profile mcLB0HarnessProfile) Result {
	t.Helper()
	dir := t.TempDir()
	requestPath, responsePath := filepath.Join(dir, "request.json"), filepath.Join(dir, "response.json")
	request := mcLB0HarnessEVMRequest{
		ABI: test.ABI, Classes: mcLB0HarnessBundle(t, test.Classes), EntryClass: test.EntryClass,
		Method: test.Method, Args: test.Args, Gas: profile.Gas,
	}
	data, err := json.Marshal(request)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(requestPath, data, 0o600); err != nil {
		t.Fatal(err)
	}
	watchdog := time.Duration(profile.WatchdogSeconds) * time.Second
	ctx, cancel := context.WithTimeout(context.Background(), watchdog)
	defer cancel()
	command := exec.CommandContext(ctx, os.Args[0], "-test.run=^TestMCLB0HarnessEVMProcess$", "-test.count=1")
	command.Env = append(os.Environ(), "MC_LB0_EVM_PROCESS=1", "MC_LB0_EVM_REQUEST="+requestPath, "MC_LB0_EVM_RESPONSE="+responsePath)
	output, commandErr := command.CombinedOutput()
	if ctx.Err() == context.DeadlineExceeded {
		t.Fatalf("EVM watchdog expired after %s for %s (finite gas=%d)\n%s", watchdog, test.ID, profile.Gas, output)
	}
	if commandErr != nil {
		t.Fatalf("EVM subprocess failed for %s: %v\n%s", test.ID, commandErr, output)
	}
	responseData, err := os.ReadFile(responsePath)
	if err != nil {
		t.Fatalf("read EVM response for %s: %v\n%s", test.ID, err, output)
	}
	var response mcLB0HarnessEVMResponse
	if err := json.Unmarshal(responseData, &response); err != nil {
		t.Fatalf("decode EVM response for %s: %v", test.ID, err)
	}
	if response.Error != "" {
		t.Fatalf("EVM %s.%s%v failed: %s (result=%+v)", test.EntryClass, test.Method, test.Args, response.Error, response.Result)
	}
	if response.Result.ExceptionClass != "" || len(response.Result.RevertData) != 0 || response.Result.GasUsed == 0 || response.Result.GasUsed > profile.Gas {
		t.Fatalf("EVM %s.%s%v returned non-value/unbounded result %+v", test.EntryClass, test.Method, test.Args, response.Result)
	}
	return response.Result
}

func TestMCLB0HarnessEVMMatchesPinnedJavaCatalogue(t *testing.T) {
	catalogue := mcLB0HarnessLoadCatalogue(t)
	for _, test := range catalogue.Cases {
		test := test
		t.Run(test.ID, func(t *testing.T) {
			profile := catalogue.Profiles[test.Profile]
			for repetition := 0; repetition < test.Repeat; repetition++ {
				result := mcLB0HarnessEVMValue(t, test, profile)
				if result.Value != test.Expected {
					t.Fatalf("EVM %s.%s%v repetition %d = %d, Java8/21 pinned %d (gas=%d)", test.EntryClass, test.Method, test.Args, repetition+1, result.Value, test.Expected, result.GasUsed)
				}
				t.Logf("profile=%s repetition=%d gas=%d runtime=%s", test.Profile, repetition+1, result.GasUsed, result.RuntimeSHA256)
			}
		})
	}
}
