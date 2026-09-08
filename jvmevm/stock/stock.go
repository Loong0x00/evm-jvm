// Package stock contains the small artifact-loading surface shared by the S0
// stock-EVM harness and its independent verifier.
package stock

import (
	"bytes"
	"embed"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"path"
	"strings"

	"github.com/ethereum/go-ethereum/accounts/abi"
)

const (
	ArtifactPage      = "ArtifactPage"
	TinyJvmStepModule = "TinyJvmStepModule"
	VMCoordinator     = "VMCoordinator"
)

// Artifact is the deployable output of the pinned S0 Solidity build. InitCode
// excludes constructor arguments; RuntimeCode is the compiler's deployed-code
// template and can therefore contain zero placeholders for immutables.
type Artifact struct {
	ABI         abi.ABI
	InitCode    []byte
	RuntimeCode []byte
}

// CompilerImmutableReference identifies a byte range in the compiler's
// deployed-code template which is filled from a constructor immutable.
type CompilerImmutableReference struct {
	Start  uint64 `json:"start"`
	Length uint64 `json:"length"`
}

//go:embed runtime/artifacts/*.json
var stockArtifactFiles embed.FS

type stockArtifactJSON struct {
	ContractName        string                                  `json:"contractName"`
	ABI                 json.RawMessage                         `json:"abi"`
	Bytecode            string                                  `json:"bytecode"`
	DeployedBytecode    string                                  `json:"deployedBytecode"`
	ImmutableReferences map[string][]CompilerImmutableReference `json:"immutableReferences"`
}

func stockArtifactName(name string) error {
	switch name {
	case ArtifactPage, TinyJvmStepModule, VMCoordinator:
		return nil
	default:
		return fmt.Errorf("stock: unknown artifact %q", name)
	}
}

func stockReadArtifact(name string) (stockArtifactJSON, error) {
	if err := stockArtifactName(name); err != nil {
		return stockArtifactJSON{}, err
	}
	filename := path.Join("runtime", "artifacts", name+".json")
	raw, err := fs.ReadFile(stockArtifactFiles, filename)
	if err != nil {
		return stockArtifactJSON{}, fmt.Errorf("stock: required pinned artifact %s is unavailable: %w", name, err)
	}
	var doc stockArtifactJSON
	if err := json.Unmarshal(raw, &doc); err != nil {
		return stockArtifactJSON{}, fmt.Errorf("stock: decode artifact %s: %w", name, err)
	}
	if doc.ContractName != name {
		return stockArtifactJSON{}, fmt.Errorf("stock: artifact %s has contractName %q", name, doc.ContractName)
	}
	if len(doc.ABI) == 0 || bytes.Equal(bytes.TrimSpace(doc.ABI), []byte("null")) {
		return stockArtifactJSON{}, fmt.Errorf("stock: artifact %s has no ABI", name)
	}
	return doc, nil
}

func stockDecodeCode(name, field, encoded string) ([]byte, error) {
	encoded = strings.TrimPrefix(encoded, "0x")
	if encoded == "" {
		return nil, fmt.Errorf("stock: artifact %s has empty %s", name, field)
	}
	if len(encoded)%2 != 0 {
		return nil, fmt.Errorf("stock: artifact %s has odd-length %s", name, field)
	}
	code, err := hex.DecodeString(encoded)
	if err != nil {
		return nil, fmt.Errorf("stock: artifact %s has invalid %s: %w", name, field, err)
	}
	return code, nil
}

// LoadArtifact loads one of the three pinned, embedded S0 build artifacts.
// Missing build output is returned as a hard dependency error; this loader does
// not substitute prototype or fabricated bytecode.
func LoadArtifact(name string) (Artifact, error) {
	doc, err := stockReadArtifact(name)
	if err != nil {
		return Artifact{}, err
	}
	contractABI, err := abi.JSON(bytes.NewReader(doc.ABI))
	if err != nil {
		return Artifact{}, fmt.Errorf("stock: parse ABI for %s: %w", name, err)
	}
	initCode, err := stockDecodeCode(name, "bytecode", doc.Bytecode)
	if err != nil {
		return Artifact{}, err
	}
	runtimeCode, err := stockDecodeCode(name, "deployedBytecode", doc.DeployedBytecode)
	if err != nil {
		return Artifact{}, err
	}
	if len(initCode) > 24*1024 {
		return Artifact{}, fmt.Errorf("stock: artifact %s initcode is %d bytes (limit %d)", name, len(initCode), 24*1024)
	}
	if len(runtimeCode) > 12*1024 {
		return Artifact{}, fmt.Errorf("stock: artifact %s runtime is %d bytes (limit %d)", name, len(runtimeCode), 12*1024)
	}
	if err := stockValidateImmutableReferences(name, uint64(len(runtimeCode)), doc.ImmutableReferences); err != nil {
		return Artifact{}, err
	}
	return Artifact{ABI: contractABI, InitCode: initCode, RuntimeCode: runtimeCode}, nil
}

// CompilerImmutableReferences returns a defensive copy of the pinned solc
// immutableReferences metadata. The ranges are validated by LoadArtifact and
// are intended for comparing a coordinator's actual deployed code with the
// compiler runtime template.
func CompilerImmutableReferences(name string) (map[string][]CompilerImmutableReference, error) {
	doc, err := stockReadArtifact(name)
	if err != nil {
		return nil, err
	}
	runtimeCode, err := stockDecodeCode(name, "deployedBytecode", doc.DeployedBytecode)
	if err != nil {
		return nil, err
	}
	if err := stockValidateImmutableReferences(name, uint64(len(runtimeCode)), doc.ImmutableReferences); err != nil {
		return nil, err
	}
	out := make(map[string][]CompilerImmutableReference, len(doc.ImmutableReferences))
	for id, refs := range doc.ImmutableReferences {
		out[id] = append([]CompilerImmutableReference(nil), refs...)
	}
	return out, nil
}

func stockValidateImmutableReferences(name string, runtimeLen uint64, refs map[string][]CompilerImmutableReference) error {
	type interval struct{ start, end uint64 }
	var occupied []interval
	for id, locations := range refs {
		if id == "" {
			return fmt.Errorf("stock: artifact %s has an empty immutable id", name)
		}
		for _, ref := range locations {
			if ref.Length == 0 || ref.Start > runtimeLen || ref.Length > runtimeLen-ref.Start {
				return fmt.Errorf("stock: artifact %s immutable %s range [%d,%d) is outside runtime length %d", name, id, ref.Start, ref.Start+ref.Length, runtimeLen)
			}
			current := interval{ref.Start, ref.Start + ref.Length}
			for _, previous := range occupied {
				if current.start < previous.end && previous.start < current.end {
					return fmt.Errorf("stock: artifact %s has overlapping immutable ranges", name)
				}
			}
			occupied = append(occupied, current)
		}
	}
	if name == VMCoordinator && len(occupied) == 0 {
		return errors.New("stock: VMCoordinator artifact has no compiler immutableReferences")
	}
	if name != VMCoordinator && len(occupied) != 0 {
		return fmt.Errorf("stock: stateless artifact %s unexpectedly has compiler immutableReferences", name)
	}
	return nil
}
