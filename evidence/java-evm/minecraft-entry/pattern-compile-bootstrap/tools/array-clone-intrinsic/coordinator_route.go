package main

import (
	"archive/zip"
	"bytes"
	"errors"
	"fmt"
	"hash/crc32"
	"math/big"
	"os"
	"path/filepath"
	"strings"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/tracing"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/core/vm"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/as0"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/di0"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/zi0"
)

type coordinatorClass struct {
	decoder common.Address
	name    []byte
	root    common.Hash
	size    uint32
}

type coordinatorRouteReport struct {
	Status                   string         `json:"status"`
	RawCount                 int            `json:"rawCount"`
	RawBytes                 int            `json:"rawBytes"`
	BootstrapCount           int            `json:"bootstrapCount"`
	DiagnosticClassCount     int            `json:"diagnosticClassCount"`
	ArrayCloneHeapAudit      heapAudit      `json:"arrayCloneHeapAudit"`
	Coordinator              common.Address `json:"coordinator"`
	CoordinatorRuntimeBytes  int            `json:"coordinatorRuntimeBytes"`
	CoordinatorRuntimeHash   common.Hash    `json:"coordinatorRuntimeKeccak256"`
	CoordinatorRuntimeSHA256 string         `json:"coordinatorRuntimeSHA256"`
	EngineRuntimeBytes       int            `json:"engineRuntimeBytes"`
	EngineRuntimeHash        common.Hash    `json:"engineRuntimeKeccak256"`
	EngineRuntimeSHA256      string         `json:"engineRuntimeSHA256"`
	AS0RuntimeBytes          int            `json:"as0RuntimeBytes"`
	AS0RuntimeKeccak256      common.Hash    `json:"as0RuntimeKeccak256"`
	AS0RuntimeSHA256         string         `json:"as0RuntimeSHA256"`
	ZI0RuntimeBytes          int            `json:"zi0RuntimeBytes"`
	ZI0RuntimeKeccak256      common.Hash    `json:"zi0RuntimeKeccak256"`
	ZI0RuntimeSHA256         string         `json:"zi0RuntimeSHA256"`
	DI0RuntimeBytes          int            `json:"di0RuntimeBytes"`
	DI0RuntimeKeccak256      common.Hash    `json:"di0RuntimeKeccak256"`
	DI0RuntimeSHA256         string         `json:"di0RuntimeSHA256"`
	ArtifactStore            common.Address `json:"as0Controller"`
	Index                    common.Address `json:"zi0Index"`
	DecoderCount             int            `json:"di0DecoderCount"`
	ArchiveBytes             int            `json:"generatedZipBytes"`
	ArchiveSHA256            string         `json:"generatedZipSHA256"`
	IndexRoot                common.Hash    `json:"indexRoot"`
	PackageRoot              common.Hash    `json:"packageRoot"`
	FinalTrieRoot            common.Hash    `json:"finalStateRoot"`
	MachineStateRoot         common.Hash    `json:"machineStateRoot"`
	CheckpointRoot           common.Hash    `json:"checkpointRoot"`
	CheckpointBytes          int            `json:"checkpointBytes"`
	Lifecycle                uint8          `json:"lifecycle"`
	Outcome                  uint8          `json:"outcome"`
	Epoch                    uint64         `json:"epoch"`
	JvmSteps                 uint64         `json:"jvmSteps"`
	InternalSteps            uint64         `json:"internalSteps"`
	TotalGas                 uint64         `json:"totalGas"`
	MaxCallGas               uint64         `json:"maxCallGas"`
	EVMCallCount             uint64         `json:"evmCallCount"`
	MutationGas              uint64         `json:"deploymentAndMutationGas"`
	MaxMutationGas           uint64         `json:"maxDeploymentAndMutationGas"`
	CountRefusal             errorDetail    `json:"coordinator151CountRefusal"`
	NamespaceRefusal         errorDetail    `json:"coordinatorNamespaceRefusal"`
	NamespaceHeadPreserved   bool           `json:"namespaceHeadPreserved"`
}

func raw150ZIP(fc fixtureCase, classes [][]byte) ([]byte, error) {
	if len(classes) != len(fc.RawClasses) || len(classes) != 150 {
		return nil, fmt.Errorf("generated ZIP input count %d differs from exact150 manifest", len(classes))
	}
	var archive bytes.Buffer
	zw := zip.NewWriter(&archive)
	for i, row := range fc.RawClasses {
		name := strings.ReplaceAll(row.BinaryName, ".", "/") + ".class"
		data := classes[i]
		if len(data) == 0 || len(data) > int(di0.MaxOutput) {
			return nil, fmt.Errorf("generated DI0 resource %s length %d outside 1..%d", name, len(data), di0.MaxOutput)
		}
		header := &zip.FileHeader{Name: name, Method: zip.Store}
		header.Flags = 0
		header.CRC32 = crc32.ChecksumIEEE(data)
		header.CompressedSize64 = uint64(len(data))
		header.UncompressedSize64 = uint64(len(data))
		file, err := zw.CreateRaw(header)
		if err != nil {
			return nil, fmt.Errorf("create generated stored ZIP member %s: %w", name, err)
		}
		if _, err := file.Write(data); err != nil {
			return nil, fmt.Errorf("write generated ZIP member %s: %w", name, err)
		}
	}
	if err := zw.Close(); err != nil {
		return nil, fmt.Errorf("close generated ZIP: %w", err)
	}
	return append([]byte(nil), archive.Bytes()...), nil
}

func typedABI(types []string, values ...interface{}) ([]byte, error) {
	if len(types) != len(values) {
		return nil, fmt.Errorf("ABI type/value arity mismatch: %d/%d", len(types), len(values))
	}
	args := make(abi.Arguments, len(types))
	for i, name := range types {
		typ, err := abi.NewType(name, "", nil)
		if err != nil {
			return nil, err
		}
		args[i] = abi.Argument{Type: typ}
	}
	return args.Pack(values...)
}

func abiKeccak(types []string, values ...interface{}) (common.Hash, error) {
	encoded, err := typedABI(types, values...)
	if err != nil {
		return common.Hash{}, err
	}
	return crypto.Keccak256Hash(encoded), nil
}

func (r *runner) createConstructor(a abi.ABI, initCode, runtimeCode []byte, label string, args ...interface{}) (common.Address, uint64, error) {
	data, err := a.Pack("", args...)
	if err != nil {
		return common.Address{}, 0, fmt.Errorf("%s constructor ABI pack: %w", label, err)
	}
	input := append(append([]byte(nil), initCode...), data...)
	out, address, gasUsed, createErr, _ := r.create(input)
	if createErr != nil {
		classification := "EVM-positive-call-failure"
		if errors.Is(createErr, vm.ErrOutOfGas) {
			classification = "test-only-gas-budget"
		}
		return common.Address{}, gasUsed, &positiveCallError{classification: classification, name: "coordinator-" + label,
			gas: r.gas, err: fmt.Errorf("%w revert=0x%x", createErr, out)}
	}
	if address == (common.Address{}) || !bytes.Equal(out, runtimeCode) || !bytes.Equal(current.st.GetCode(address), runtimeCode) {
		return common.Address{}, gasUsed, fmt.Errorf("%s CREATE installed an unexpected runtime", label)
	}
	return address, gasUsed, nil
}

func (r *runner) dependencyCall(a abi.ABI, to common.Address, method string, persist bool, args ...interface{}) ([]interface{}, uint64, error) {
	data, err := a.Pack(method, args...)
	if err != nil {
		return nil, 0, fmt.Errorf("%s ABI pack: %w", method, err)
	}
	out, gasUsed, callErr, _ := r.call(to, data)
	if callErr != nil {
		classification := "EVM-positive-call-failure"
		if errors.Is(callErr, vm.ErrOutOfGas) {
			classification = "test-only-gas-budget"
		}
		return nil, gasUsed, &positiveCallError{classification: classification, name: "coordinator-" + method,
			gas: r.gas, err: fmt.Errorf("%w revert=0x%x", callErr, out)}
	}
	if persist {
		if err = current.persistAndReload(); err != nil {
			return nil, gasUsed, fmt.Errorf("persist after %s: %w", method, err)
		}
	}
	values, err := a.Unpack(method, out)
	if err != nil {
		return nil, gasUsed, fmt.Errorf("%s ABI decode: %w", method, err)
	}
	return values, gasUsed, nil
}

func (r *runner) dependencyView(a abi.ABI, to common.Address, method string, args ...interface{}) ([]interface{}, error) {
	data, err := a.Pack(method, args...)
	if err != nil {
		return nil, fmt.Errorf("%s view ABI pack: %w", method, err)
	}
	out, used, callErr, _ := r.callReadOnly(to, data)
	if callErr != nil {
		classification := "EVM-positive-call-failure"
		if errors.Is(callErr, vm.ErrOutOfGas) {
			classification = "test-only-gas-budget"
		}
		return nil, &positiveCallError{classification: classification, name: "coordinator-view-" + method,
			gas: r.gas, err: fmt.Errorf("%w after %d gas; output=0x%x", callErr, used, out)}
	}
	values, err := a.Unpack(method, out)
	if err != nil {
		return nil, fmt.Errorf("%s view ABI decode: %w", method, err)
	}
	return values, nil
}

func asU64(value interface{}) (uint64, error) {
	switch v := value.(type) {
	case uint8:
		return uint64(v), nil
	case uint16:
		return uint64(v), nil
	case uint32:
		return uint64(v), nil
	case uint64:
		return v, nil
	case *big.Int:
		if !v.IsUint64() {
			return 0, fmt.Errorf("ABI integer %s is not uint64", v)
		}
		return v.Uint64(), nil
	default:
		return 0, fmt.Errorf("unexpected ABI integer type %T", value)
	}
}

func (r *runner) oneUint(a abi.ABI, to common.Address, method string, args ...interface{}) (uint64, error) {
	values, err := r.dependencyView(a, to, method, args...)
	if err != nil {
		return 0, err
	}
	if len(values) != 1 {
		return 0, fmt.Errorf("%s returned %d values, want1", method, len(values))
	}
	return asU64(values[0])
}

func (r *runner) oneHash(a abi.ABI, to common.Address, method string, args ...interface{}) (common.Hash, error) {
	values, err := r.dependencyView(a, to, method, args...)
	if err != nil {
		return common.Hash{}, err
	}
	if len(values) != 1 {
		return common.Hash{}, fmt.Errorf("%s returned %d values, want1", method, len(values))
	}
	return asHash(values[0]), nil
}

func (r *runner) coordinatorRoute() error {
	const caseName = "raw-bytes-exact"
	fc, classes := r.loadCase(caseName)
	if fc.RawCount != 150 || fc.RawBytes != 1063930 || fc.EntryClass != "ArrayCloneMatrix" {
		return fmt.Errorf("coordinator route fixture is not exact150/1,063,930 with ArrayCloneMatrix entry: count=%d bytes=%d entry=%s", fc.RawCount, fc.RawBytes, fc.EntryClass)
	}
	archive, err := raw150ZIP(fc, classes)
	if err != nil {
		return err
	}
	routeGasStart := r.evmGasTotal
	if err = osMkdirWorld(r.reportDir); err != nil {
		return err
	}
	w, err := openWorld(filepath.Join(r.reportDir, "worlds", "coordinator-raw-bytes-exact"), types.EmptyRootHash)
	if err != nil {
		return err
	}
	r.setCurrent(w)
	defer w.close()
	w.st.CreateAccount(engineAddress)
	w.st.SetCode(engineAddress, r.engineCode, tracing.CodeChangeUnspecified)
	if err = w.persistAndReload(); err != nil {
		return err
	}

	asABI, err := as0.ABI()
	if err != nil {
		return err
	}
	asInit, err := as0.InitCode()
	if err != nil {
		return err
	}
	asRuntime, err := as0.Runtime()
	if err != nil {
		return err
	}
	ziABI, err := zi0.ABI()
	if err != nil {
		return err
	}
	ziInit, err := zi0.InitCode()
	if err != nil {
		return err
	}
	ziRuntime, err := zi0.Runtime()
	if err != nil {
		return err
	}
	diABI, err := di0.ABI()
	if err != nil {
		return err
	}
	diInit, err := di0.InitCode()
	if err != nil {
		return err
	}
	diRuntime, err := di0.Runtime()
	if err != nil {
		return err
	}

	var totalGas, maxGas uint64
	measure := func(gas uint64) {
		totalGas += gas
		if gas > maxGas {
			maxGas = gas
		}
	}
	zipLength := uint32(len(archive))
	asAddress, gasUsed, err := r.createConstructor(asABI, asInit, asRuntime, "AS0", zipLength)
	measure(gasUsed)
	if err != nil {
		return err
	}
	if asAddress != crypto.CreateAddress(callerAddress, 0) {
		return fmt.Errorf("AS0 CREATE address %s differs from ordinary nonce0 address", asAddress)
	}
	if err = w.persistAndReload(); err != nil {
		return err
	}
	for offset := uint32(0); offset < zipLength; {
		end := offset + as0.PageSize
		if end > zipLength {
			end = zipLength
		}
		chunk := append([]byte(nil), archive[offset:end]...)
		pageNumber := offset / as0.PageSize
		pageHash := crypto.Keccak256Hash(chunk)
		pageCommitment, packErr := abiKeccak(
			[]string{"bytes32", "address", "uint32", "uint32", "bytes32"},
			crypto.Keccak256Hash([]byte("MC-AS0/page/v1")), asAddress, pageNumber,
			uint32(len(chunk)), pageHash,
		)
		if packErr != nil {
			return packErr
		}
		_, gasUsed, err = r.dependencyCall(asABI, asAddress, "append", true, offset, chunk, pageCommitment)
		measure(gasUsed)
		if err != nil {
			return err
		}
		offset = end
	}
	cursor, err := r.oneUint(asABI, asAddress, "cursor")
	if err != nil {
		return err
	}
	chain, err := r.oneHash(asABI, asAddress, "chainCommitment")
	if err != nil {
		return err
	}
	if cursor != uint64(zipLength) {
		return fmt.Errorf("AS0 cursor=%d expected archive length=%d", cursor, zipLength)
	}
	_, gasUsed, err = r.dependencyCall(asABI, asAddress, "seal", true, uint32(cursor), chain)
	measure(gasUsed)
	if err != nil {
		return err
	}
	content, err := r.oneHash(asABI, asAddress, "contentCommitment")
	if err != nil {
		return err
	}

	ziAddress, gasUsed, err := r.createConstructor(ziABI, ziInit, ziRuntime, "ZI0", asAddress, content)
	measure(gasUsed)
	if err != nil {
		return err
	}
	if ziAddress != crypto.CreateAddress(callerAddress, 1) {
		return fmt.Errorf("ZI0 CREATE address %s differs from ordinary nonce1 address", ziAddress)
	}
	if err = w.persistAndReload(); err != nil {
		return err
	}
	_, gasUsed, err = r.dependencyCall(ziABI, ziAddress, "discover", true)
	measure(gasUsed)
	if err != nil {
		return err
	}
	entryCount, err := r.oneUint(ziABI, ziAddress, "count")
	if err != nil {
		return err
	}
	if entryCount != 150 {
		return fmt.Errorf("EVM ZI0 discovered %d entries, expected150", entryCount)
	}
	for {
		next, getErr := r.oneUint(ziABI, ziAddress, "nextEntry")
		if getErr != nil {
			return getErr
		}
		if next == entryCount {
			break
		}
		cdCursor, getErr := r.oneUint(ziABI, ziAddress, "cdCursor")
		if getErr != nil {
			return getErr
		}
		rolling, getErr := r.oneHash(ziABI, ziAddress, "rolling")
		if getErr != nil {
			return getErr
		}
		units := uint16(64)
		if remaining := entryCount - next; remaining < uint64(units) {
			units = uint16(remaining)
		}
		_, gasUsed, err = r.dependencyCall(ziABI, ziAddress, "scan", true,
			uint32(next), uint32(cdCursor), rolling, units)
		measure(gasUsed)
		if err != nil {
			return err
		}
	}
	cdCursor, err := r.oneUint(ziABI, ziAddress, "cdCursor")
	if err != nil {
		return err
	}
	rolling, err := r.oneHash(ziABI, ziAddress, "rolling")
	if err != nil {
		return err
	}
	_, gasUsed, err = r.dependencyCall(ziABI, ziAddress, "finish", true,
		uint32(entryCount), uint32(cdCursor), rolling)
	measure(gasUsed)
	if err != nil {
		return err
	}
	indexRoot, err := r.oneHash(ziABI, ziAddress, "finalRoot")
	if err != nil {
		return err
	}
	phase, err := r.oneUint(ziABI, ziAddress, "phase")
	if err != nil {
		return err
	}
	if phase != 2 || indexRoot == (common.Hash{}) {
		return fmt.Errorf("ZI0 final phase/root mismatch: phase=%d root=%s", phase, indexRoot)
	}

	packageClasses := make([]coordinatorClass, len(fc.RawClasses))
	decoders := make([]common.Address, len(fc.RawClasses))
	rawNames := make([][]byte, len(fc.RawClasses))
	indexRoots := make([]common.Hash, len(fc.RawClasses))
	classRoots := make([]common.Hash, len(fc.RawClasses))
	var totalClassBytes uint32
	for i, row := range fc.RawClasses {
		rawName := []byte(strings.ReplaceAll(row.BinaryName, ".", "/") + ".class")
		decoder, createGas, createErr := r.createConstructor(diABI, diInit, diRuntime,
			fmt.Sprintf("DI0[%d]", i), ziAddress, indexRoot, rawName)
		measure(createGas)
		if createErr != nil {
			return createErr
		}
		if decoder != crypto.CreateAddress(callerAddress, uint64(i+2)) {
			return fmt.Errorf("DI0[%d] CREATE address %s differs from ordinary nonce%d", i, decoder, i+2)
		}
		if err = w.persistAndReload(); err != nil {
			return err
		}
		for {
			decoderPhase, viewErr := r.oneUint(diABI, decoder, "phase")
			if viewErr != nil {
				return viewErr
			}
			if decoderPhase != 1 {
				if decoderPhase != 2 {
					return fmt.Errorf("DI0[%d] entered unexpected prepublication phase %d", i, decoderPhase)
				}
				break
			}
			work, viewErr := r.oneUint(diABI, decoder, "work")
			if viewErr != nil {
				return viewErr
			}
			_, gasUsed, err = r.dependencyCall(diABI, decoder, "step", true, uint32(work), uint16(di0.MaxStepUnits))
			measure(gasUsed)
			if err != nil {
				return err
			}
		}
		for {
			decoderPhase, viewErr := r.oneUint(diABI, decoder, "phase")
			if viewErr != nil {
				return viewErr
			}
			if decoderPhase == 4 {
				break
			}
			if decoderPhase != 2 && decoderPhase != 3 {
				return fmt.Errorf("DI0[%d] entered unexpected publication phase %d", i, decoderPhase)
			}
			page, viewErr := r.oneUint(diABI, decoder, "publishedPages")
			if viewErr != nil {
				return viewErr
			}
			publication, viewErr := r.oneHash(diABI, decoder, "publicationRolling")
			if viewErr != nil {
				return viewErr
			}
			_, gasUsed, err = r.dependencyCall(diABI, decoder, "publish", true,
				uint8(page), publication, uint8(di0.PublishUnits))
			measure(gasUsed)
			if err != nil {
				return err
			}
		}
		classRoot, viewErr := r.oneHash(diABI, decoder, "finalRoot")
		if viewErr != nil {
			return viewErr
		}
		size64, viewErr := r.oneUint(diABI, decoder, "plainSize")
		if viewErr != nil {
			return viewErr
		}
		if size64 != uint64(len(classes[i])) || classRoot == (common.Hash{}) {
			return fmt.Errorf("DI0[%d] final size/root differs from generated input", i)
		}
		packageClasses[i] = coordinatorClass{decoder: decoder, name: rawName, root: classRoot, size: uint32(size64)}
		decoders[i], rawNames[i], indexRoots[i], classRoots[i] = decoder, rawName, indexRoot, classRoot
		totalClassBytes += uint32(size64)
	}
	if current.st.GetNonce(callerAddress) != 152 {
		return fmt.Errorf("creator nonce before coordinator CREATE is %d, expected152", current.st.GetNonce(callerAddress))
	}

	coordinatorAddressExpected := crypto.CreateAddress(callerAddress, 152)
	packageDomain := crypto.Keccak256Hash([]byte("MC-ARRAY-CLONE-INTRINSIC-P37/package/v1"))
	classDomain := crypto.Keccak256Hash([]byte("MC-ARRAY-CLONE-INTRINSIC-P37/class/v1"))
	engineHash := crypto.Keccak256Hash(r.engineCode)
	diHash := crypto.Keccak256Hash(diRuntime)
	ziHash := crypto.Keccak256Hash(ziRuntime)
	rollingRoot, err := abiKeccak(
		[]string{"bytes32", "address", "address", "address", "bytes32", "bytes32", "bytes32", "uint8"},
		packageDomain, coordinatorAddressExpected, callerAddress, engineAddress, engineHash, diHash, ziHash, uint8(150),
	)
	if err != nil {
		return err
	}
	for i, entry := range packageClasses {
		nameHash := crypto.Keccak256Hash(entry.name)
		rollingRoot, err = abiKeccak(
			[]string{"bytes32", "bytes32", "uint8", "address", "bytes32", "bytes32", "bytes32", "uint32"},
			classDomain, rollingRoot, uint8(i), entry.decoder, nameHash, indexRoot, entry.root, entry.size,
		)
		if err != nil {
			return err
		}
	}
	packageRoot, err := abiKeccak(
		[]string{"bytes32", "bytes32", "uint32", "address", "bytes32", "uint8"},
		packageDomain, rollingRoot, totalClassBytes, ziAddress, indexRoot, uint8(0),
	)
	if err != nil {
		return err
	}
	salt := crypto.Keccak256Hash([]byte("generated-raw150-byte1063930-coordinator-salt"))
	coordArgs, err := r.coordABI.Pack("", callerAddress, salt, decoders, rawNames,
		indexRoots, classRoots, common.Address{}, []byte{}, common.Hash{}, common.Hash{}, packageRoot)
	if err != nil {
		return fmt.Errorf("coordinator constructor ABI pack: %w", err)
	}
	coordInit := append(append([]byte(nil), r.coordInit...), coordArgs...)
	coordOut, coordAddress, gasUsed, createErr, _ := r.create(coordInit)
	measure(gasUsed)
	if createErr != nil {
		classification := "EVM-positive-call-failure"
		if errors.Is(createErr, vm.ErrOutOfGas) {
			classification = "test-only-gas-budget"
		}
		return &positiveCallError{classification: classification, name: "coordinator-create-exact150",
			gas: r.gas, err: fmt.Errorf("%w revert=0x%x", createErr, coordOut)}
	}
	if coordAddress != coordinatorAddressExpected || !bytes.Equal(coordOut, r.coordCode) ||
		!bytes.Equal(current.st.GetCode(coordAddress), r.coordCode) ||
		crypto.Keccak256Hash(current.st.GetCode(coordAddress)) != crypto.Keccak256Hash(r.coordCode) {
		return fmt.Errorf("coordinator CREATE address/runtime mismatch: %s", coordAddress)
	}
	if err = w.persistAndReload(); err != nil {
		return err
	}
	storedPackageRoot, err := r.oneHash(r.coordABI, coordAddress, "packageRoot")
	if err != nil {
		return err
	}
	storedTotal, err := r.oneUint(r.coordABI, coordAddress, "totalClassBytes")
	if err != nil {
		return err
	}
	storedCount, err := r.oneUint(r.coordABI, coordAddress, "classCount")
	if err != nil {
		return err
	}
	if storedPackageRoot != packageRoot || storedTotal != 1063930 || storedCount != 150 {
		return fmt.Errorf("coordinator stored package metadata mismatch: root=%s bytes=%d count=%d", storedPackageRoot, storedTotal, storedCount)
	}
	for _, at := range []uint8{0, 149} {
		values, viewErr := r.dependencyView(r.coordABI, coordAddress, "classBinding", at)
		if viewErr != nil {
			return viewErr
		}
		if len(values) != 4 || values[0].(common.Address) != packageClasses[at].decoder ||
			!bytes.Equal(values[1].([]byte), packageClasses[at].name) || asHash(values[2]) != packageClasses[at].root ||
			asU64Must(values[3]) != uint64(packageClasses[at].size) {
			return fmt.Errorf("coordinator classBinding(%d) differs from real decoder metadata", at)
		}
	}
	instanceID, err := r.oneHash(r.coordABI, coordAddress, "instanceId")
	if err != nil {
		return err
	}
	startInput, err := r.coordABI.Pack("startMain", packageRoot, uint8(0), uint64(maxJvm), uint32(maxInternal))
	if err != nil {
		return err
	}
	startBytes, startGas, startErr, _ := r.call(coordAddress, startInput)
	measure(startGas)
	if startErr != nil {
		detail := r.decodeError(startBytes)
		classification := "EVM-positive-call-failure"
		if isTestOnlyGasBudget(startErr, detail) {
			classification = "test-only-gas-budget"
		}
		return &positiveCallError{classification: classification, name: "coordinator-start-exact150-byte-envelope",
			gas: r.gas, err: fmt.Errorf("%w typed=%s args=%v revert=0x%x", startErr, detail.Name, detail.Args, startBytes)}
	}
	coordinatorValues, err := r.coordABI.Unpack("startMain", startBytes)
	if err != nil || len(coordinatorValues) != 1 {
		return fmt.Errorf("coordinator start return decode: values=%d err=%v", len(coordinatorValues), err)
	}
	engineReturn, ok := coordinatorValues[0].([]byte)
	if !ok {
		return fmt.Errorf("coordinator start returned %T instead of engine bytes", coordinatorValues[0])
	}
	started := unpackOutput(r.engineABI, "startMain", engineReturn)
	if started.Result.Lifecycle != 2 || started.Result.Outcome != 2 || started.Result.JavaKind != 0 ||
		started.Result.CheckpointRoot != crypto.Keccak256Hash(started.Checkpoint) {
		return fmt.Errorf("coordinator raw150 terminal result invalid: lifecycle=%d outcome=%d kind=%d", started.Result.Lifecycle, started.Result.Outcome, started.Result.JavaKind)
	}
	if started.Result.Epoch != 1 {
		return fmt.Errorf("coordinator direct terminal epoch=%d expected1", started.Result.Epoch)
	}
	if err = r.validateCheckpoint(classes, started.Checkpoint, started.Result.MachineStateRoot); err != nil {
		return err
	}
	audit, err := r.checkCP(started.Checkpoint, started.Result.CheckpointRoot, classes)
	if err != nil {
		return err
	}
	if audit.RawCount != 150 || audit.BootstrapCount != 103 || audit.ClassCount != 253 {
		return fmt.Errorf("coordinator terminal MR01 diagnostic count mismatch: %+v", audit)
	}
	if fc.EntryClass == "PatternCompileMatrix" {
		if err = r.validatePatternCompileAudit(audit); err != nil {
			return fmt.Errorf("coordinator Pattern compile audit: %w", err)
		}
	}
	if err = w.persistAndReload(); err != nil {
		return err
	}
	engineOwner, epoch, headRoot, lifecycle, err := r.getHead(instanceID)
	if err != nil {
		return err
	}
	if engineOwner != coordAddress || epoch != 1 || headRoot != started.Result.CheckpointRoot || lifecycle != 2 {
		return fmt.Errorf("coordinator->engine committed head mismatch owner=%s epoch=%d lifecycle=%d", engineOwner, epoch, lifecycle)
	}

	// Count guard runs before any decoder getter or EVM codehash query.
	countErr, err := r.coordinator151CountRefusal()
	if err != nil {
		return err
	}
	// The reserved class namespace check is exercised against a genuine DI0
	// decoder; only the supplied name is malformed and it must fail before the
	// coordinator links or publishes a package.
	namespaceErr, err := r.coordinatorNamespaceRefusal(packageClasses[0], packageRoot)
	if err != nil {
		return err
	}
	ownerAfter, epochAfter, rootAfter, lifeAfter, err := r.getHead(instanceID)
	if err != nil {
		return err
	}
	if ownerAfter != coordAddress || epochAfter != epoch || rootAfter != headRoot || lifeAfter != lifecycle {
		return fmt.Errorf("namespace refusal changed the prior terminal MR01 head")
	}
	checkpointDir := filepath.Join(r.reportDir, "checkpoints")
	if err = os.MkdirAll(checkpointDir, 0700); err != nil {
		return err
	}
	if err = os.WriteFile(filepath.Join(checkpointDir, "coordinator-raw-bytes-exact.checkpoint.bin"), started.Checkpoint, 0600); err != nil {
		return err
	}

	out := coordinatorRouteReport{
		Status:   "generated ArrayCloneMatrix exact150/exact1063930 positive through ordinary AS0+ZI0+DI0 CREATE, coordinator CREATE, and pinned local engine Call; MR01 terminal/checkpoint/head validation passed",
		RawCount: 150, RawBytes: 1063930, BootstrapCount: 103, DiagnosticClassCount: 253,
		ArrayCloneHeapAudit: audit,
		Coordinator:         coordAddress, CoordinatorRuntimeBytes: len(r.coordCode),
		CoordinatorRuntimeHash: crypto.Keccak256Hash(r.coordCode), CoordinatorRuntimeSHA256: sha256Hex(r.coordCode),
		EngineRuntimeBytes: len(r.engineCode), EngineRuntimeHash: engineHash, EngineRuntimeSHA256: sha256Hex(r.engineCode),
		AS0RuntimeBytes: len(asRuntime), AS0RuntimeKeccak256: crypto.Keccak256Hash(asRuntime), AS0RuntimeSHA256: sha256Hex(asRuntime),
		ZI0RuntimeBytes: len(ziRuntime), ZI0RuntimeKeccak256: crypto.Keccak256Hash(ziRuntime), ZI0RuntimeSHA256: sha256Hex(ziRuntime),
		DI0RuntimeBytes: len(diRuntime), DI0RuntimeKeccak256: crypto.Keccak256Hash(diRuntime), DI0RuntimeSHA256: sha256Hex(diRuntime),
		ArtifactStore: asAddress, Index: ziAddress,
		DecoderCount: len(packageClasses), ArchiveBytes: len(archive), ArchiveSHA256: sha256Hex(archive),
		IndexRoot: indexRoot, PackageRoot: packageRoot, FinalTrieRoot: w.root,
		MachineStateRoot: started.Result.MachineStateRoot, CheckpointRoot: started.Result.CheckpointRoot,
		CheckpointBytes: len(started.Checkpoint), Lifecycle: started.Result.Lifecycle,
		Outcome: started.Result.Outcome, Epoch: started.Result.Epoch, JvmSteps: started.Result.TotalJvmSteps,
		InternalSteps: started.Result.TotalInternalSteps,
		TotalGas:      r.evmGasTotal - routeGasStart, MaxCallGas: r.evmMaxGas,
		EVMCallCount: r.evmCallCount,
		MutationGas:  totalGas, MaxMutationGas: maxGas,
		CountRefusal: countErr, NamespaceRefusal: namespaceErr,
		NamespaceHeadPreserved: true,
	}
	return writeJSON(filepath.Join(r.reportDir, "coordinator-summary.json"), out)
}

func asU64Must(value interface{}) uint64 {
	v, err := asU64(value)
	if err != nil {
		panic(err)
	}
	return v
}

func osMkdirWorld(reportDir string) error {
	return os.MkdirAll(filepath.Join(reportDir, "worlds"), 0700)
}

func (r *runner) coordinator151CountRefusal() (errorDetail, error) {
	previousWorld := current
	w, err := openWorld(filepath.Join(r.reportDir, "worlds", "coordinator-151-refusal"), types.EmptyRootHash)
	if err != nil {
		return errorDetail{}, err
	}
	r.setCurrent(w)
	defer func() {
		w.close()
		current = previousWorld
	}()
	before := w.st.IntermediateRoot(false)
	decoders := make([]common.Address, 151)
	names := make([][]byte, 151)
	indexRoots := make([]common.Hash, 151)
	classRoots := make([]common.Hash, 151)
	for i := range decoders {
		decoders[i] = callerAddress
		names[i] = []byte(fmt.Sprintf("Generated%d.class", i))
	}
	zero := common.Hash{}
	args, err := r.coordABI.Pack("", callerAddress, zero, decoders, names,
		indexRoots, classRoots, common.Address{}, []byte{}, zero, zero, zero)
	if err != nil {
		return errorDetail{}, err
	}
	_, _, _, createErr, _ := r.create(append(append([]byte(nil), r.coordInit...), args...))
	if createErr == nil {
		return errorDetail{}, fmt.Errorf("coordinator accepted raw class count151")
	}
	detail := decodeABIError(r.coordABI, lastCallOutput)
	if detail.Name != "MR0Error" || len(detail.Args) == 0 || detail.Args[0] != "2" {
		return errorDetail{}, fmt.Errorf("coordinator151 guard returned %s args=%v revert=0x%x", detail.Name, detail.Args, lastCallOutput)
	}
	if w.st.GetCode(crypto.CreateAddress(callerAddress, 0)) != nil {
		return errorDetail{}, errors.New("raw151 coordinator refusal published CREATE code")
	}
	_ = before // Failed top-level CREATE follows EVM creator-nonce semantics; no package/contract is published.
	return detail, nil
}

func (r *runner) coordinatorNamespaceRefusal(sample coordinatorClass, packageRoot common.Hash) (errorDetail, error) {
	badName := []byte("generated.bad.namespace.class")
	zero := common.Hash{}
	args, err := r.coordABI.Pack("", callerAddress, packageRoot,
		[]common.Address{sample.decoder}, [][]byte{badName}, []common.Hash{zero}, []common.Hash{zero},
		common.Address{}, []byte{}, zero, zero, zero)
	if err != nil {
		return errorDetail{}, err
	}
	_, _, _, createErr, _ := r.create(append(append([]byte(nil), r.coordInit...), args...))
	if createErr == nil {
		return errorDetail{}, fmt.Errorf("coordinator accepted invalid raw class namespace name")
	}
	detail := decodeABIError(r.coordABI, lastCallOutput)
	if detail.Name != "MR0Error" || len(detail.Args) == 0 || detail.Args[0] != "6" {
		return errorDetail{}, fmt.Errorf("coordinator namespace guard returned %s args=%v revert=0x%x", detail.Name, detail.Args, lastCallOutput)
	}
	return detail, nil
}

func decodeABIError(a abi.ABI, out []byte) errorDetail {
	if len(out) < 4 {
		return errorDetail{Selector: "0x" + fmt.Sprintf("%x", out)}
	}
	for _, e := range a.Errors {
		if bytes.Equal(out[:4], e.ID[:4]) {
			values, err := e.Inputs.Unpack(out[4:])
			if err != nil {
				return errorDetail{Name: e.Name, Selector: "0x" + fmt.Sprintf("%x", out[:4]), Args: []string{"<decode-error>"}}
			}
			args := make([]string, len(values))
			for i, value := range values {
				args[i] = fmt.Sprint(value)
			}
			return errorDetail{Name: e.Name, Selector: "0x" + fmt.Sprintf("%x", out[:4]), Args: args}
		}
	}
	return errorDetail{Selector: "0x" + fmt.Sprintf("%x", out[:4])}
}
