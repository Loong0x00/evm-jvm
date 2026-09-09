// Package s2b exposes the pinned artifact-loading surface for the Stock S2b-L
// registration/link slice. It has no frame, resume, or Java-outcome API.
package s2b

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
	"github.com/ethereum/go-ethereum/jvmevm/stock"
)

const (
	S2bMetadataPage  = "S2bMetadataPage"
	S2bAnalyzeModule = "S2bAnalyzeModule"
	S2bClassLinker   = "S2bClassLinker"
)

// CompilerImmutableReference identifies a deployed-bytecode template range that
// solc fills from a constructor immutable.
type CompilerImmutableReference = stock.CompilerImmutableReference

//go:embed runtime/artifacts/*.json
var stockS2bLinkArtifactFiles embed.FS

type stockS2bLinkArtifactJSON struct {
	ContractName        string                                  `json:"contractName"`
	ABI                 json.RawMessage                         `json:"abi"`
	Bytecode            string                                  `json:"bytecode"`
	DeployedBytecode    string                                  `json:"deployedBytecode"`
	ImmutableReferences map[string][]CompilerImmutableReference `json:"immutableReferences"`
}

func stockS2bLinkArtifactName(name string) error {
	switch name {
	case S2bMetadataPage, S2bAnalyzeModule, S2bClassLinker:
		return nil
	default:
		return fmt.Errorf("stock s2b link: unknown artifact %q", name)
	}
}

func stockS2bLinkReadArtifact(name string) (stockS2bLinkArtifactJSON, error) {
	if err := stockS2bLinkArtifactName(name); err != nil {
		return stockS2bLinkArtifactJSON{}, err
	}
	filename := path.Join("runtime", "artifacts", name+".json")
	raw, err := fs.ReadFile(stockS2bLinkArtifactFiles, filename)
	if err != nil {
		return stockS2bLinkArtifactJSON{}, fmt.Errorf("stock s2b link: required pinned artifact %s is unavailable: %w", name, err)
	}
	var doc stockS2bLinkArtifactJSON
	if err := json.Unmarshal(raw, &doc); err != nil {
		return stockS2bLinkArtifactJSON{}, fmt.Errorf("stock s2b link: decode artifact %s: %w", name, err)
	}
	if doc.ContractName != name {
		return stockS2bLinkArtifactJSON{}, fmt.Errorf("stock s2b link: artifact %s has contractName %q", name, doc.ContractName)
	}
	if len(doc.ABI) == 0 || bytes.Equal(bytes.TrimSpace(doc.ABI), []byte("null")) {
		return stockS2bLinkArtifactJSON{}, fmt.Errorf("stock s2b link: artifact %s has no ABI", name)
	}
	return doc, nil
}

func stockS2bLinkDecodeCode(name, field, encoded string) ([]byte, error) {
	encoded = strings.TrimPrefix(encoded, "0x")
	if encoded == "" {
		return nil, fmt.Errorf("stock s2b link: artifact %s has empty %s", name, field)
	}
	if len(encoded)%2 != 0 {
		return nil, fmt.Errorf("stock s2b link: artifact %s has odd-length %s", name, field)
	}
	code, err := hex.DecodeString(encoded)
	if err != nil {
		return nil, fmt.Errorf("stock s2b link: artifact %s has invalid %s: %w", name, field, err)
	}
	return code, nil
}

// LoadArtifact loads one of the three pinned Stock S2b-L build artifacts. A
// missing runtime delivery is a hard dependency error; this package never
// substitutes prototype, generated, or fabricated bytecode.
func LoadArtifact(name string) (stock.Artifact, error) {
	doc, err := stockS2bLinkReadArtifact(name)
	if err != nil {
		return stock.Artifact{}, err
	}
	contractABI, err := abi.JSON(bytes.NewReader(doc.ABI))
	if err != nil {
		return stock.Artifact{}, fmt.Errorf("stock s2b link: parse ABI for %s: %w", name, err)
	}
	initCode, err := stockS2bLinkDecodeCode(name, "bytecode", doc.Bytecode)
	if err != nil {
		return stock.Artifact{}, err
	}
	runtimeCode, err := stockS2bLinkDecodeCode(name, "deployedBytecode", doc.DeployedBytecode)
	if err != nil {
		return stock.Artifact{}, err
	}
	if len(initCode) > 24*1024 {
		return stock.Artifact{}, fmt.Errorf("stock s2b link: artifact %s initcode is %d bytes (limit %d)", name, len(initCode), 24*1024)
	}
	runtimeLimit := 12 * 1024
	if name == S2bAnalyzeModule {
		runtimeLimit = 20 * 1024
	}
	if len(runtimeCode) > runtimeLimit {
		return stock.Artifact{}, fmt.Errorf("stock s2b link: artifact %s runtime is %d bytes (limit %d)", name, len(runtimeCode), runtimeLimit)
	}
	if err := stockS2bLinkValidateImmutableReferences(name, uint64(len(runtimeCode)), doc.ImmutableReferences); err != nil {
		return stock.Artifact{}, err
	}
	return stock.Artifact{ABI: contractABI, InitCode: initCode, RuntimeCode: runtimeCode}, nil
}

// CompilerImmutableReferences returns a defensive copy of the pinned compiler
// immutable ranges. Deployment tests use it to compare the linker's actual code
// to its template while separately checking all immutable getters and values.
func CompilerImmutableReferences(name string) (map[string][]CompilerImmutableReference, error) {
	doc, err := stockS2bLinkReadArtifact(name)
	if err != nil {
		return nil, err
	}
	runtimeCode, err := stockS2bLinkDecodeCode(name, "deployedBytecode", doc.DeployedBytecode)
	if err != nil {
		return nil, err
	}
	if err := stockS2bLinkValidateImmutableReferences(name, uint64(len(runtimeCode)), doc.ImmutableReferences); err != nil {
		return nil, err
	}
	out := make(map[string][]CompilerImmutableReference, len(doc.ImmutableReferences))
	for id, refs := range doc.ImmutableReferences {
		out[id] = append([]CompilerImmutableReference(nil), refs...)
	}
	return out, nil
}

func stockS2bLinkValidateImmutableReferences(name string, runtimeLen uint64, refs map[string][]CompilerImmutableReference) error {
	type interval struct{ start, end uint64 }
	var occupied []interval
	for id, locations := range refs {
		if id == "" {
			return fmt.Errorf("stock s2b link: artifact %s has an empty immutable id", name)
		}
		for _, ref := range locations {
			if ref.Length == 0 || ref.Start > runtimeLen || ref.Length > runtimeLen-ref.Start {
				return fmt.Errorf("stock s2b link: artifact %s immutable %s range [%d,%d) is outside runtime length %d", name, id, ref.Start, ref.Start+ref.Length, runtimeLen)
			}
			current := interval{ref.Start, ref.Start + ref.Length}
			for _, previous := range occupied {
				if current.start < previous.end && previous.start < current.end {
					return fmt.Errorf("stock s2b link: artifact %s has overlapping immutable ranges", name)
				}
			}
			occupied = append(occupied, current)
		}
	}
	if name == S2bClassLinker && len(occupied) == 0 {
		return errors.New("stock s2b link: S2bClassLinker artifact has no compiler immutableReferences")
	}
	if name != S2bClassLinker && len(occupied) != 0 {
		return fmt.Errorf("stock s2b link: stateless artifact %s unexpectedly has compiler immutableReferences", name)
	}
	return nil
}
