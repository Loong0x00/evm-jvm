package cb0

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math/big"
	"os"
	"path/filepath"
	"strings"
	"sync"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/rawdb"
	"github.com/ethereum/go-ethereum/core/state"
	"github.com/ethereum/go-ethereum/core/tracing"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/core/vm"
	evmruntime "github.com/ethereum/go-ethereum/core/vm/runtime"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/ethdb"
	"github.com/ethereum/go-ethereum/ethdb/leveldb"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/as0"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/di0"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/zi0"
	"github.com/ethereum/go-ethereum/jvmevm/localcontinuation/vfs0a"
	"github.com/ethereum/go-ethereum/params"
	"github.com/ethereum/go-ethereum/triedb"
)

const (
	cb0MarkerName     = "STORE-FORMAT"
	cb0ManifestName   = "durable-head.json"
	cb0StateDirectory = "state"
	cb0BlobDirectory  = "checkpoints"
	cb0Context        = "all-dev-chain:block=1,time=1,coinbase=0000000000000000000000000000000000000000,value=0"
)

type cb0Disk interface {
	ethdb.Database
	SyncKeyValue() error
}
type cb0Manifest struct {
	Format              uint32           `json:"format"`
	Context             string           `json:"context"`
	Owner               common.Address   `json:"owner"`
	Length              uint32           `json:"length"`
	StateRoot           common.Hash      `json:"stateRoot"`
	Engine              common.Address   `json:"engine"`
	EngineCodeHash      common.Hash      `json:"engineCodeHash"`
	AS0                 common.Address   `json:"as0"`
	Index               common.Address   `json:"index"`
	Decoders            []common.Address `json:"decoders"`
	Coordinator         common.Address   `json:"coordinator"`
	PackageRoot         common.Hash      `json:"packageRoot"`
	JavaHead            common.Hash      `json:"javaHead"`
	AS0CodeHash         common.Hash      `json:"as0CodeHash"`
	ZI0CodeHash         common.Hash      `json:"zi0CodeHash"`
	DI0CodeHash         common.Hash      `json:"di0CodeHash"`
	CoordinatorCodeHash common.Hash      `json:"coordinatorCodeHash"`
}

type Session struct {
	mu                                                                                sync.Mutex
	owner                                                                             common.Address
	length                                                                            uint32
	as0ABI, zi0ABI, di0ABI, coordABI                                                  abi.ABI
	as0Init, as0Run, zi0Init, zi0Run, di0Init, di0Run, coordInit, coordRun, engineRun []byte
	as0Hash, zi0Hash, di0Hash, coordHash, engineHash                                  common.Hash
	as0Address, indexAddress                                                          common.Address
	decoders                                                                          []common.Address
	coordinator                                                                       common.Address
	packageRoot                                                                       common.Hash
	instanceID                                                                        common.Hash
	javaHead                                                                          common.Hash
	directory                                                                         string
	disk                                                                              cb0Disk
	trie                                                                              *triedb.Database
	state                                                                             *state.StateDB
	root                                                                              common.Hash
	latestBlob                                                                        []byte
	initialization                                                                    Initialization
	closed                                                                            bool
	poison                                                                            error
	// Tests may inject only transport boundaries. It is deliberately unexported.
	testFault func(cb0FaultPoint) error
}
type cb0FaultPoint uint8

const (
	cb0FaultAfterBlob cb0FaultPoint = iota + 1
	cb0FaultAfterTrie
	cb0FaultBeforeManifest
	cb0FaultAfterRename
)

// NewMemory creates the atomic initial root: pinned LOCAL engine installation
// plus one ordinary AS0 CREATE. No intermediate engine-only route is exposed.
func NewMemory(owner common.Address, length uint32) (*Session, error) {
	return cb0New("", owner, length, rawdb.NewMemoryDatabase())
}
func Open(directory string, owner common.Address, length uint32) (*Session, error) {
	if directory == "" {
		return nil, errors.New("cb0: directory must not be empty")
	}
	if err := cb0Inputs(owner, length); err != nil {
		return nil, err
	}
	abs, err := filepath.Abs(directory)
	if err != nil {
		return nil, err
	}
	if resolved, e := filepath.EvalSymlinks(abs); e == nil {
		abs = resolved
	} else if !errors.Is(e, os.ErrNotExist) {
		return nil, fmt.Errorf("cb0: resolve store root: %w", e)
	}
	fresh, err := cb0PrepareDirectory(abs)
	if err != nil {
		return nil, err
	}
	if fresh {
		if err := cb0WriteNewRegular(filepath.Join(abs, cb0MarkerName), []byte(StoreMarker)); err != nil {
			return nil, err
		}
		if err := os.Mkdir(filepath.Join(abs, cb0BlobDirectory), 0700); err != nil {
			return nil, err
		}
		if err := cb0SyncDir(abs); err != nil {
			return nil, err
		}
	}
	// Validate the bounded namespace/identity BEFORE even attempting LevelDB open.
	if !fresh {
		loaded, err := cb0ArtifactLoad()
		if err != nil {
			return nil, err
		}
		if _, err = cb0ReadDiskMetadata(abs, owner, length, loaded.runtimeHash); err != nil {
			return nil, err
		}
	}
	kv, err := leveldb.New(filepath.Join(abs, cb0StateDirectory), 16, 16, "jvmevm/cb0", false)
	if err != nil {
		return nil, fmt.Errorf("cb0: open state database: %w", err)
	}
	s, err := cb0New(abs, owner, length, rawdb.NewDatabase(kv))
	if err != nil {
		return nil, err
	}
	if fresh {
		if err = s.cb0Initialize(); err != nil {
			s.Close()
			return nil, err
		}
		return s, nil
	}
	if err = s.cb0Reopen(); err != nil {
		s.Close()
		return nil, err
	}
	return s, nil
}
func cb0New(dir string, owner common.Address, length uint32, d cb0Disk) (*Session, error) {
	if err := cb0Inputs(owner, length); err != nil {
		d.Close()
		return nil, err
	}
	x, err := cb0LoadArtifacts()
	if err != nil {
		d.Close()
		return nil, err
	}
	t := triedb.NewDatabase(d, triedb.HashDefaults)
	st, err := state.New(types.EmptyRootHash, state.NewDatabase(t, nil))
	if err != nil {
		t.Close()
		d.Close()
		return nil, err
	}
	s := &Session{owner: owner, length: length, directory: dir, disk: d, trie: t, state: st, root: types.EmptyRootHash, as0ABI: x.as0ABI, zi0ABI: x.zi0ABI, di0ABI: x.di0ABI, coordABI: x.coordABI, as0Init: x.as0Init, as0Run: x.as0Run, zi0Init: x.zi0Init, zi0Run: x.zi0Run, di0Init: x.di0Init, di0Run: x.di0Run, coordInit: x.coordInit, coordRun: x.coordRun, engineRun: x.engineRun, as0Hash: crypto.Keccak256Hash(x.as0Run), zi0Hash: crypto.Keccak256Hash(x.zi0Run), di0Hash: crypto.Keccak256Hash(x.di0Run), coordHash: crypto.Keccak256Hash(x.coordRun), engineHash: crypto.Keccak256Hash(x.engineRun)}
	if dir == "" {
		if err := s.cb0Initialize(); err != nil {
			s.Close()
			return nil, err
		}
	}
	return s, nil
}

type cb0Artifacts struct {
	as0ABI, zi0ABI, di0ABI, coordABI                                                  abi.ABI
	as0Init, as0Run, zi0Init, zi0Run, di0Init, di0Run, coordInit, coordRun, engineRun []byte
}

func cb0LoadArtifacts() (cb0Artifacts, error) {
	var x cb0Artifacts
	var err error
	if x.as0Init, err = as0.InitCode(); err != nil {
		return x, err
	}
	if x.as0Run, err = as0.Runtime(); err != nil {
		return x, err
	}
	if x.as0ABI, err = as0.ABI(); err != nil {
		return x, err
	}
	if x.zi0Init, err = zi0.InitCode(); err != nil {
		return x, err
	}
	if x.zi0Run, err = zi0.Runtime(); err != nil {
		return x, err
	}
	if x.zi0ABI, err = zi0.ABI(); err != nil {
		return x, err
	}
	if x.di0Init, err = di0.InitCode(); err != nil {
		return x, err
	}
	if x.di0Run, err = di0.Runtime(); err != nil {
		return x, err
	}
	if x.di0ABI, err = di0.ABI(); err != nil {
		return x, err
	}
	c, err := cb0ArtifactLoad()
	if err != nil {
		return x, err
	}
	x.coordABI, x.coordInit, x.coordRun = c.abi, c.init, c.runtime
	if x.engineRun, err = vfs0a.Runtime(); err != nil {
		return x, err
	}
	if crypto.Keccak256Hash(x.as0Run) != cb0AS0Code || crypto.Keccak256Hash(x.zi0Run) != cb0ZI0Code || crypto.Keccak256Hash(x.di0Run) != cb0DI0Code || crypto.Keccak256Hash(x.engineRun) != cb0VFSCode {
		return x, errors.New("cb0: accepted dependency code pin differs")
	}
	return x, nil
}
func cb0Inputs(owner common.Address, length uint32) error {
	if owner == (common.Address{}) {
		return errors.New("cb0: owner must be nonzero")
	}
	if length == 0 || length > as0.MaxLength {
		return errors.New("cb0: declared length must be in 1..33554432")
	}
	return nil
}
func (s *Session) cb0Initialize() error {
	// This is the only permitted SetCode, explicit gas zero, and it shares the
	// AS0 creation root rather than publishing a routable engine-only root.
	s.state.CreateAccount(cb0EngineAddress)
	s.state.SetCode(cb0EngineAddress, s.engineRun, tracing.CodeChangeUnspecified)
	args, err := s.as0ABI.Pack("", s.length)
	if err != nil {
		return err
	}
	out, addr, left, err := evmruntime.Create(append(append([]byte(nil), s.as0Init...), args...), s.cb0Config(s.state, OrdinaryGas))
	used := OrdinaryGas - left
	if err != nil {
		return fmt.Errorf("cb0: AS0 initial CREATE failed after %d gas: %w", used, err)
	}
	if !bytes.Equal(out, s.as0Run) || s.state.GetCodeHash(addr) != s.as0Hash {
		return errors.New("cb0: AS0 initial CREATE installed unexpected runtime")
	}
	s.as0Address = addr
	root, err := s.cb0Commit()
	if err != nil {
		return err
	}
	s.root = root
	if err = s.cb0Reload(root); err != nil {
		return err
	}
	s.initialization = Initialization{true, cb0EngineAddress, s.engineHash, root, as0.Creation{Performed: true, Controller: addr, GasUsed: used, RuntimeCodeHash: s.as0Hash, StateRoot: root}}
	if s.directory != "" {
		if err = s.cb0Publish(root, nil, common.Hash{}); err != nil {
			return err
		}
	}
	return nil
}
func (s *Session) Initialization() (Initialization, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if err := s.cb0Usable(); err != nil {
		return Initialization{}, err
	}
	out := s.initialization
	return out, nil
}

func (s *Session) Append(cursor uint32, raw []byte, pi common.Hash, gas uint64) (Operation, error) {
	return s.cb0Mutate(s.as0Address, s.as0ABI, "append", gas, cursor, append([]byte(nil), raw...), pi)
}
func (s *Session) Seal(cursor uint32, chain common.Hash, gas uint64) (Operation, error) {
	return s.cb0Mutate(s.as0Address, s.as0ABI, "seal", gas, cursor, chain)
}
func (s *Session) CreateIndex(content common.Hash, gas uint64) (Operation, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var op Operation
	if err := s.cb0Usable(); err != nil {
		return op, err
	}
	if err := s.cb0Gas(gas); err != nil {
		return op, err
	}
	if s.indexAddress != (common.Address{}) {
		return op, errors.New("cb0: index already created")
	}
	args, err := s.zi0ABI.Pack("", s.as0Address, content)
	if err != nil {
		return op, err
	}
	old, snap := s.root, s.state.Snapshot()
	out, addr, left, err := evmruntime.Create(append(append([]byte(nil), s.zi0Init...), args...), s.cb0Config(s.state, gas))
	op.GasUsed = gas - left
	if err != nil {
		return s.cb0EVMFailure(op, old, snap, out, err, "index constructor")
	}
	if !bytes.Equal(out, s.zi0Run) || s.state.GetCodeHash(addr) != s.zi0Hash {
		s.cb0Rollback(snap, old)
		return Operation{GasUsed: op.GasUsed}, errors.New("cb0: ZI0 CREATE installed unexpected code")
	}
	s.indexAddress = addr
	if err = s.cb0Persist(old, nil, common.Hash{}); err != nil {
		if s.poison == nil {
			s.indexAddress = common.Address{}
		}
		return Operation{GasUsed: op.GasUsed}, err
	}
	op.StateRoot = s.root
	op.CreatedAddress = addr
	return op, nil
}
func (s *Session) DiscoverIndex(gas uint64) (Operation, error) {
	return s.cb0MutateIndex("discover", gas)
}
func (s *Session) ScanIndex(entry, cursor uint32, rolling common.Hash, units uint16, gas uint64) (Operation, error) {
	return s.cb0MutateIndex("scan", gas, entry, cursor, rolling, units)
}
func (s *Session) FinishIndex(count, cursor uint32, rolling common.Hash, gas uint64) (Operation, error) {
	return s.cb0MutateIndex("finish", gas, count, cursor, rolling)
}
func (s *Session) cb0MutateIndex(name string, gas uint64, args ...interface{}) (Operation, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.indexAddress == (common.Address{}) {
		return Operation{}, errors.New("cb0: index is not constructed")
	}
	return s.cb0MutateLocked(s.indexAddress, s.zi0ABI, name, gas, args...)
}

// CreateDecoder only accepts the next contiguous slot and stops forever after
// coordinator creation. It does not inspect resource bytes or ZIP metadata.
func (s *Session) CreateDecoder(slot uint8, indexRoot common.Hash, rawName []byte, gas uint64) (Operation, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var op Operation
	if err := s.cb0Usable(); err != nil {
		return op, err
	}
	if err := s.cb0Gas(gas); err != nil {
		return op, err
	}
	if s.indexAddress == (common.Address{}) {
		return op, errors.New("cb0: index is not constructed")
	}
	if s.coordinator != (common.Address{}) {
		return op, errors.New("cb0: coordinator already created")
	}
	if slot != uint8(len(s.decoders)) || slot >= MaxResources {
		return op, errors.New("cb0: decoder slot is not next bounded slot")
	}
	if len(rawName) == 0 || len(rawName) > int(MaxRawNameBytes) {
		return op, errors.New("cb0: raw name length is outside frozen bound")
	}
	args, err := s.di0ABI.Pack("", s.indexAddress, indexRoot, append([]byte(nil), rawName...))
	if err != nil {
		return op, err
	}
	old, snap := s.root, s.state.Snapshot()
	out, addr, left, err := evmruntime.Create(append(append([]byte(nil), s.di0Init...), args...), s.cb0Config(s.state, gas))
	op.GasUsed = gas - left
	if err != nil {
		return s.cb0EVMFailure(op, old, snap, out, err, "decoder constructor")
	}
	if !bytes.Equal(out, s.di0Run) || s.state.GetCodeHash(addr) != s.di0Hash {
		s.cb0Rollback(snap, old)
		return Operation{GasUsed: op.GasUsed}, errors.New("cb0: DI0 CREATE installed unexpected code")
	}
	s.decoders = append(s.decoders, addr)
	if err = s.cb0Persist(old, nil, common.Hash{}); err != nil {
		if s.poison == nil {
			s.decoders = s.decoders[:len(s.decoders)-1]
		}
		return Operation{GasUsed: op.GasUsed}, err
	}
	op.StateRoot = s.root
	op.CreatedAddress = addr
	return op, nil
}
func (s *Session) StepDecoder(slot uint8, work uint32, units uint16, gas uint64) (Operation, error) {
	return s.cb0MutateDecoder(slot, "step", gas, work, units)
}
func (s *Session) PublishDecoder(slot uint8, page uint8, rolling common.Hash, units uint8, gas uint64) (Operation, error) {
	return s.cb0MutateDecoder(slot, "publish", gas, page, rolling, units)
}
func (s *Session) cb0MutateDecoder(slot uint8, name string, gas uint64, args ...interface{}) (Operation, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if int(slot) >= len(s.decoders) {
		return Operation{}, errors.New("cb0: decoder slot is absent")
	}
	return s.cb0MutateLocked(s.decoders[slot], s.di0ABI, name, gas, args...)
}

func (s *Session) CreateCoordinator(salt common.Hash, bindings []ResourceBinding, asserted common.Hash, gas uint64) (Operation, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var op Operation
	if err := s.cb0Usable(); err != nil {
		return op, err
	}
	if err := s.cb0Gas(gas); err != nil {
		return op, err
	}
	if s.coordinator != (common.Address{}) {
		return op, errors.New("cb0: coordinator already created")
	}
	if len(bindings) == 0 || len(bindings) > int(MaxResources) || len(bindings) > len(s.decoders) {
		return op, errors.New("cb0: coordinator binding count differs")
	}
	decs := make([]common.Address, len(bindings))
	names := make([][]byte, len(bindings))
	indices := make([]common.Hash, len(bindings))
	resources := make([]common.Hash, len(bindings))
	seenSlots := make(map[uint8]bool, len(bindings))
	for i, b := range bindings {
		if seenSlots[b.Slot] || b.Slot >= uint8(len(s.decoders)) || len(b.RawName) == 0 || len(b.RawName) > int(MaxRawNameBytes) || b.IndexRoot == (common.Hash{}) || b.ResourceRoot == (common.Hash{}) {
			return op, errors.New("cb0: invalid bounded resource binding")
		}
		seenSlots[b.Slot] = true
		decs[i] = s.decoders[b.Slot]
		names[i] = append([]byte(nil), b.RawName...)
		indices[i], resources[i] = b.IndexRoot, b.ResourceRoot
	}
	args, err := s.coordABI.Pack("", s.owner, salt, decs, names, indices, resources, asserted)
	if err != nil {
		return op, err
	}
	if len(s.coordInit)+len(args) > 49152 {
		return op, errors.New("cb0: complete coordinator init exceeds frozen cap")
	}
	old, snap := s.root, s.state.Snapshot()
	out, addr, left, err := evmruntime.Create(append(append([]byte(nil), s.coordInit...), args...), s.cb0Config(s.state, gas))
	op.GasUsed = gas - left
	if err != nil {
		return s.cb0EVMFailure(op, old, snap, out, err, "coordinator constructor")
	}
	if !bytes.Equal(out, s.coordRun) || s.state.GetCodeHash(addr) != s.coordHash {
		s.cb0Rollback(snap, old)
		return Operation{GasUsed: op.GasUsed}, errors.New("cb0: coordinator CREATE installed unexpected code")
	}
	s.coordinator = addr
	s.packageRoot = asserted
	s.instanceID = crypto.Keccak256Hash(crypto.Keccak256([]byte("MC-CB0/vm/v1")), common.LeftPadBytes(addr[:], 32), asserted[:], salt[:])
	if err = s.cb0Persist(old, nil, common.Hash{}); err != nil {
		if s.poison == nil {
			s.coordinator = common.Address{}
			s.packageRoot = common.Hash{}
			s.instanceID = common.Hash{}
		}
		return Operation{GasUsed: op.GasUsed}, err
	}
	op.StateRoot = s.root
	op.CreatedAddress = addr
	return op, nil
}

func (s *Session) Start(pkg common.Hash, entryAt uint8, entry string, args []int32, jvm uint64, internal uint32, gas uint64) (JavaResult, error) {
	return s.cb0Java("start", gas, pkg, entryAt, entry, append([]int32(nil), args...), jvm, internal)
}
func (s *Session) Resume(pkg common.Hash, epoch uint64, root common.Hash, checkpoint []byte, jvm uint64, internal uint32, gas uint64) (JavaResult, error) {
	return s.cb0Java("resume", gas, pkg, epoch, root, append([]byte(nil), checkpoint...), jvm, internal)
}

func (s *Session) cb0Mutate(to common.Address, a abi.ABI, name string, gas uint64, args ...interface{}) (Operation, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.cb0MutateLocked(to, a, name, gas, args...)
}
func (s *Session) cb0MutateLocked(to common.Address, a abi.ABI, name string, gas uint64, args ...interface{}) (Operation, error) {
	var op Operation
	if err := s.cb0Usable(); err != nil {
		return op, err
	}
	if err := s.cb0Gas(gas); err != nil {
		return op, err
	}
	data, err := a.Pack(name, args...)
	if err != nil {
		return op, err
	}
	old, snapshot := s.root, s.state.Snapshot()
	before := len(s.state.Logs())
	out, left, err := evmruntime.Call(to, data, s.cb0Config(s.state, gas))
	op.GasUsed = gas - left
	if err != nil {
		return s.cb0EVMFailure(op, old, snapshot, out, err, name)
	}
	logs := s.state.Logs()
	if len(out) != 0 || len(logs) < before {
		s.cb0Rollback(snapshot, old)
		return Operation{GasUsed: op.GasUsed}, errors.New("cb0: successful mutation emitted output or removed logs")
	}
	if to == s.as0Address && (name == "append" || name == "seal") {
		if len(logs)-before != 1 {
			s.cb0Rollback(snapshot, old)
			return Operation{GasUsed: op.GasUsed}, errors.New("cb0: AS0 mutation emitted wrong number of logs")
		}
		want := s.as0ABI.Events["PageIssued"].ID
		if name == "seal" {
			want = s.as0ABI.Events["Sealed"].ID
		}
		if logs[before].Address != s.as0Address || len(logs[before].Topics) == 0 || logs[before].Topics[0] != want {
			s.cb0Rollback(snapshot, old)
			return Operation{GasUsed: op.GasUsed}, errors.New("cb0: AS0 mutation emitted wrong event")
		}
		op.Logs = copiedLogs(logs[before:])
	} else if len(logs) != before {
		s.cb0Rollback(snapshot, old)
		return Operation{GasUsed: op.GasUsed}, errors.New("cb0: successful mutation emitted logs")
	}
	if err = s.cb0Persist(old, nil, common.Hash{}); err != nil {
		return Operation{GasUsed: op.GasUsed}, err
	}
	op.StateRoot = s.root
	return op, nil
}
func (s *Session) cb0EVMFailure(op Operation, old common.Hash, snap int, out []byte, err error, label string) (Operation, error) {
	if rerr := s.cb0Rollback(snap, old); rerr != nil {
		return Operation{GasUsed: op.GasUsed, RevertData: append([]byte(nil), out...)}, rerr
	}
	op.RevertData = append([]byte(nil), out...)
	return op, fmt.Errorf("cb0: EVM %s failed: %w (revert_data=0x%x)", label, err, out)
}

func (s *Session) cb0Java(method string, gas uint64, args ...interface{}) (JavaResult, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var result JavaResult
	if err := s.cb0Usable(); err != nil {
		return result, err
	}
	if s.coordinator == (common.Address{}) {
		return result, errors.New("cb0: coordinator is not constructed")
	}
	if err := s.cb0Gas(gas); err != nil {
		return result, err
	}
	data, err := s.coordABI.Pack(method, args...)
	if err != nil {
		return result, err
	}
	old, snap := s.root, s.state.Snapshot()
	beforeLogs := len(s.state.Logs())
	out, left, err := evmruntime.Call(s.coordinator, data, s.cb0Config(s.state, gas))
	result.GasUsed = gas - left
	if err != nil {
		s.cb0Rollback(snap, old)
		result.RevertData = append([]byte(nil), out...)
		return result, fmt.Errorf("cb0: EVM coordinator %s failed: %w (revert_data=0x%x)", method, err, out)
	}
	values, err := s.coordABI.Unpack(method, out)
	if err != nil || len(values) != 1 {
		s.cb0Rollback(snap, old)
		return JavaResult{GasUsed: result.GasUsed}, errors.New("cb0: malformed coordinator outer result")
	}
	engineReturn, ok := values[0].([]byte)
	if !ok {
		s.cb0Rollback(snap, old)
		return JavaResult{GasUsed: result.GasUsed}, errors.New("cb0: coordinator outer result is not bytes")
	}
	var decoded struct {
		Result     vfs0a.SliceResult
		Checkpoint []byte
	}
	if method == "start" {
		err = s.cb0EngineUnpack("start", engineReturn, &decoded)
	} else {
		var r struct {
			Result          vfs0a.SliceResult
			ChildCheckpoint []byte
		}
		err = s.cb0EngineUnpack("resume", engineReturn, &r)
		decoded.Result, decoded.Checkpoint = r.Result, r.ChildCheckpoint
	}
	if err != nil || !s.cb0SliceValid(decoded.Result) || decoded.Result.ExecutedJvmSteps > args[len(args)-2].(uint64) || decoded.Result.ExecutedInternalSteps > args[len(args)-1].(uint32) || (method == "start" && decoded.Result.Epoch != 1) || (method == "resume" && (args[1].(uint64) == ^uint64(0) || decoded.Result.Epoch != args[1].(uint64)+1)) || len(decoded.Checkpoint) == 0 || len(decoded.Checkpoint) > int(MaxCheckpointBytes) || crypto.Keccak256Hash(decoded.Checkpoint) != decoded.Result.CheckpointRoot {
		s.cb0Rollback(snap, old)
		return JavaResult{GasUsed: result.GasUsed}, errors.New("cb0: invalid EVM Java slice or checkpoint")
	}
	// The unchanged engine emits one exact CheckpointCommitted; CB0 itself
	// emits no events. Validate nested logs, do not silently drop them.
	engineABI, err := vfs0a.ABI()
	if err != nil {
		return JavaResult{GasUsed: result.GasUsed}, err
	}
	event := engineABI.Events["CheckpointCommitted"]
	expectedData, err := event.Inputs.NonIndexed().Pack(decoded.Result.CheckpointRoot, decoded.Result.MachineStateRoot, decoded.Result.VFSStateRoot, decoded.Result.Lifecycle, decoded.Result.TotalJvmSteps, decoded.Result.TotalInternalSteps)
	logs := s.state.Logs()
	if err != nil || len(logs) != beforeLogs+1 || logs[beforeLogs].Address != cb0EngineAddress || len(logs[beforeLogs].Topics) != 3 || logs[beforeLogs].Topics[0] != event.ID || logs[beforeLogs].Topics[1] != s.instanceID || logs[beforeLogs].Topics[2] != common.BigToHash(new(big.Int).SetUint64(decoded.Result.Epoch)) || !bytes.Equal(logs[beforeLogs].Data, expectedData) {
		s.cb0Rollback(snap, old)
		return JavaResult{GasUsed: result.GasUsed}, errors.New("cb0: engine checkpoint event differs from slice")
	}
	result.Logs = copiedLogs(logs[beforeLogs:])
	result.Slice, result.Checkpoint = decoded.Result, append([]byte(nil), decoded.Checkpoint...)
	// The manifest must publish the exact EVM-issued Java head alongside the
	// trie root. Restore the prior route before a pre-rename failure.
	previousHead := s.javaHead
	s.javaHead = result.Slice.CheckpointRoot
	if err = s.cb0Persist(old, result.Checkpoint, result.Slice.CheckpointRoot); err != nil {
		if s.poison == nil {
			s.javaHead = previousHead
		}
		return JavaResult{GasUsed: result.GasUsed}, err
	}
	result.StateRoot = s.root
	return result, nil
}
func (s *Session) cb0EngineUnpack(method string, out []byte, v interface{}) error {
	a, err := vfs0a.ABI()
	if err != nil {
		return err
	}
	return a.UnpackIntoInterface(v, method, out)
}
func (s *Session) cb0SliceValid(r vfs0a.SliceResult) bool {
	if len(r.JavaClass) > 65535 || r.ExecutedJvmSteps > r.TotalJvmSteps || uint64(r.ExecutedInternalSteps) > r.TotalInternalSteps || r.Schema != 1 || r.Epoch == 0 || r.CheckpointRoot == (common.Hash{}) || r.MachineStateRoot == (common.Hash{}) || r.VFSStateRoot == (common.Hash{}) || r.InodeCount < 3 || r.InodeCount > 64 || r.DescriptorCount > 32 || r.LogicalFileBytes > 65536 || r.Lifecycle < 1 || r.Lifecycle > 3 {
		return false
	}
	if r.Lifecycle == 1 {
		return r.Result == 0 && r.JavaKind == 0 && r.JavaRef == 0 && len(r.JavaClass) == 0
	}
	if r.Lifecycle == 2 {
		return r.JavaKind == 0 && r.JavaRef == 0 && len(r.JavaClass) == 0
	}
	return r.Result == 0 && r.JavaRef != 0 && r.JavaKind <= 12 && (r.JavaKind == 0) == (len(r.JavaClass) != 0)
}

func (s *Session) ResourceRead(slot uint8, off, n uint32, gas uint64) (Read, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if int(slot) >= len(s.decoders) {
		return Read{}, errors.New("cb0: decoder slot is absent")
	}
	return s.cb0DIRead(s.decoders[slot], off, n, gas)
}
func (s *Session) ResourcePage(slot, at uint8, gas uint64) (Page, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if int(slot) >= len(s.decoders) {
		return Page{}, errors.New("cb0: decoder slot is absent")
	}
	return s.cb0DIPage(s.decoders[slot], at, gas)
}
func (s *Session) InputRead(off, n uint32, gas uint64) (as0.Read, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.cb0ASRead(off, n, gas)
}
func (s *Session) InputPage(at uint64, gas uint64) (as0.Page, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.cb0ASPage(at, gas)
}
func (s *Session) Entry(at uint32, gas uint64) (di0.Entry, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.indexAddress == (common.Address{}) {
		return di0.Entry{}, errors.New("cb0: index is absent")
	}
	out, u, err := s.cb0View(s.indexAddress, s.zi0ABI, "entry", gas, at)
	if err != nil {
		return di0.Entry{GasUsed: u}, err
	}
	v, err := s.zi0ABI.Unpack("entry", out)
	if err != nil || len(v) != 2 {
		return di0.Entry{GasUsed: u}, errors.New("cb0: malformed index entry")
	}
	n, ok := v[0].([]byte)
	p, ok2 := v[1].([32]byte)
	if !ok || !ok2 || len(n) == 0 || len(n) > int(MaxRawNameBytes) {
		return di0.Entry{GasUsed: u}, errors.New("cb0: noncanonical index entry")
	}
	return di0.Entry{Name: append([]byte(nil), n...), PackedRecord: common.Hash(p), GasUsed: u}, nil
}
func (s *Session) Lookup(name []byte, gas uint64) (di0.LookupResult, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.indexAddress == (common.Address{}) {
		return di0.LookupResult{}, errors.New("cb0: index is absent")
	}
	out, u, err := s.cb0View(s.indexAddress, s.zi0ABI, "lookup", gas, append([]byte(nil), name...))
	if err != nil {
		return di0.LookupResult{GasUsed: u}, err
	}
	v, err := s.zi0ABI.Unpack("lookup", out)
	if err != nil || len(v) != 3 {
		return di0.LookupResult{GasUsed: u}, errors.New("cb0: malformed index lookup")
	}
	f, o1 := v[0].(bool)
	i, o2 := v[1].(uint32)
	p, o3 := v[2].([32]byte)
	if !o1 || !o2 || !o3 {
		return di0.LookupResult{GasUsed: u}, errors.New("cb0: noncanonical index lookup")
	}
	return di0.LookupResult{Found: f, Index: i, PackedRecord: common.Hash(p), GasUsed: u}, nil
}

func (s *Session) ReadCheckpoint(root common.Hash) ([]byte, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if err := s.cb0Usable(); err != nil {
		return nil, err
	}
	if root == (common.Hash{}) || root != s.javaHead {
		return nil, errors.New("cb0: checkpoint is not the latest published Java head")
	}
	var b []byte
	var err error
	if s.directory == "" {
		b = append([]byte(nil), s.latestBlob...)
	} else {
		b, err = cb0ReadRegular(filepath.Join(s.directory, cb0BlobDirectory, root.Hex()[2:]+".checkpoint"), int64(MaxCheckpointBytes))
	}
	if err != nil {
		return nil, err
	}
	if len(b) == 0 || crypto.Keccak256Hash(b) != root {
		return nil, errors.New("cb0: checkpoint blob integrity differs")
	}
	return append([]byte(nil), b...), nil
}

func (s *Session) cb0DIRead(addr common.Address, off, n uint32, gas uint64) (Read, error) {
	if n > MaxResourceRead {
		return Read{}, errors.New("cb0: resource read exceeds cap")
	}
	out, u, err := s.cb0View(addr, s.di0ABI, "read", gas, off, n)
	if err != nil {
		return Read{GasUsed: u}, err
	}
	v, err := s.di0ABI.Unpack("read", out)
	if err != nil || len(v) != 1 {
		return Read{GasUsed: u}, errors.New("cb0: malformed resource read")
	}
	b, ok := v[0].([]byte)
	if !ok || len(b) != int(n) {
		return Read{GasUsed: u}, errors.New("cb0: noncanonical resource read")
	}
	return Read{Bytes: append([]byte(nil), b...), GasUsed: u}, nil
}
func (s *Session) cb0DIPage(addr common.Address, at uint8, gas uint64) (Page, error) {
	out, u, err := s.cb0View(addr, s.di0ABI, "page", gas, at)
	if err != nil {
		return Page{GasUsed: u}, err
	}
	v, err := s.di0ABI.Unpack("page", out)
	if err != nil || len(v) != 4 {
		return Page{GasUsed: u}, errors.New("cb0: malformed resource page")
	}
	a, o1 := v[0].(common.Address)
	h, o2 := v[1].([32]byte)
	p, o3 := v[2].([32]byte)
	n, o4 := v[3].(uint32)
	if !o1 || !o2 || !o3 || !o4 || a == (common.Address{}) || n == 0 || n > di0.OutputPageSize {
		return Page{GasUsed: u}, errors.New("cb0: noncanonical resource page")
	}
	return Page{Address: a, CodeHash: common.Hash(h), Commitment: common.Hash(p), Length: n, GasUsed: u}, nil
}
func (s *Session) cb0ASRead(off, n uint32, gas uint64) (as0.Read, error) {
	out, u, err := s.cb0View(s.as0Address, s.as0ABI, "read", gas, off, n)
	if err != nil {
		return as0.Read{GasUsed: u}, err
	}
	v, err := s.as0ABI.Unpack("read", out)
	if err != nil || len(v) != 1 {
		return as0.Read{GasUsed: u}, errors.New("cb0: malformed AS0 read")
	}
	b, ok := v[0].([]byte)
	if !ok || len(b) != int(n) {
		return as0.Read{GasUsed: u}, errors.New("cb0: noncanonical AS0 read")
	}
	return as0.Read{Bytes: append([]byte(nil), b...), GasUsed: u}, nil
}
func (s *Session) cb0ASPage(at uint64, gas uint64) (as0.Page, error) {
	out, u, err := s.cb0View(s.as0Address, s.as0ABI, "page", gas, new(big.Int).SetUint64(at))
	if err != nil {
		return as0.Page{GasUsed: u}, err
	}
	v, err := s.as0ABI.Unpack("page", out)
	if err != nil || len(v) != 3 {
		return as0.Page{GasUsed: u}, errors.New("cb0: malformed AS0 page")
	}
	a, o1 := v[0].(common.Address)
	h, o2 := v[1].([32]byte)
	p, o3 := v[2].([32]byte)
	if !o1 || !o2 || !o3 || a == (common.Address{}) {
		return as0.Page{GasUsed: u}, errors.New("cb0: noncanonical AS0 page")
	}
	return as0.Page{Address: a, CodeHash: common.Hash(h), Commitment: common.Hash(p), GasUsed: u}, nil
}

func (s *Session) cb0View(to common.Address, a abi.ABI, name string, gas uint64, args ...interface{}) ([]byte, uint64, error) {
	if err := s.cb0Usable(); err != nil {
		return nil, 0, err
	}
	if err := s.cb0Gas(gas); err != nil {
		return nil, 0, err
	}
	data, err := a.Pack(name, args...)
	if err != nil {
		return nil, 0, err
	}
	out, left, err := evmruntime.Call(to, data, s.cb0Config(s.state.Copy(), gas))
	u := gas - left
	if err != nil {
		return nil, u, fmt.Errorf("cb0: EVM view %s failed: %w (revert_data=0x%x)", name, err, out)
	}
	return out, u, nil
}

func (s *Session) cb0Persist(old common.Hash, blob []byte, blobRoot common.Hash) error {
	if s.directory != "" && len(blob) > 0 {
		if err := s.cb0WriteBlob(blobRoot, blob); err != nil {
			s.cb0Restore(old)
			return err
		}
		if err := s.cb0Inject(cb0FaultAfterBlob); err != nil {
			s.cb0Restore(old)
			return err
		}
	}
	root, err := s.cb0Commit()
	if err != nil {
		s.cb0Restore(old)
		return err
	}
	if err = s.cb0Inject(cb0FaultAfterTrie); err != nil {
		s.cb0Restore(old)
		return err
	}
	if s.directory != "" {
		if err = s.cb0Publish(root, blob, blobRoot); err != nil {
			if errors.Is(err, errCB0Published) {
				s.poison = fmt.Errorf("cb0: manifest publication ambiguous; exact reopen required: %w", err)
				return s.poison
			}
			s.cb0Restore(old)
			return err
		}
	}
	s.root = root
	if err = s.cb0Reload(root); err != nil {
		s.poison = fmt.Errorf("cb0: published state cannot reload: %w", err)
		return s.poison
	}
	if s.directory == "" && len(blob) > 0 {
		s.latestBlob = append([]byte(nil), blob...)
	}
	return nil
}
func (s *Session) cb0Commit() (common.Hash, error) {
	r, e := s.state.Commit(1, true, true)
	if e != nil {
		return common.Hash{}, e
	}
	if e = s.trie.Commit(r, false); e != nil {
		return common.Hash{}, e
	}
	if e = s.disk.SyncKeyValue(); e != nil {
		return common.Hash{}, e
	}
	return r, nil
}
func (s *Session) cb0Reload(r common.Hash) error {
	st, e := state.New(r, state.NewDatabase(s.trie, nil))
	if e == nil {
		s.state, s.root = st, r
	}
	return e
}
func (s *Session) cb0Restore(r common.Hash) {
	if e := s.cb0Reload(r); e != nil {
		s.poison = fmt.Errorf("cb0: cannot restore prior root: %w", e)
	}
}
func (s *Session) cb0Rollback(snapshot int, root common.Hash) error {
	s.state.RevertToSnapshot(snapshot)
	if e := s.cb0Reload(root); e != nil {
		s.poison = e
		return e
	}
	return nil
}

var errCB0Published = errors.New("cb0: manifest renamed")

func (s *Session) cb0Publish(root common.Hash, blob []byte, blobRoot common.Hash) error {
	if err := s.cb0Inject(cb0FaultBeforeManifest); err != nil {
		return err
	}
	m := s.cb0Manifest(root)
	raw, err := json.Marshal(m)
	if err != nil {
		return err
	}
	f, err := os.CreateTemp(s.directory, ".durable-head-")
	if err != nil {
		return err
	}
	name := f.Name()
	if err = f.Chmod(0600); err == nil {
		_, err = f.Write(append(raw, '\n'))
	}
	if err == nil {
		err = f.Sync()
	}
	if closeErr := f.Close(); err == nil {
		err = closeErr
	}
	if err != nil {
		return err
	}
	if err = os.Rename(name, filepath.Join(s.directory, cb0ManifestName)); err != nil {
		return err
	}
	if err = s.cb0Inject(cb0FaultAfterRename); err != nil {
		return fmt.Errorf("%w: %v", errCB0Published, err)
	}
	if err = cb0SyncDir(s.directory); err != nil {
		return fmt.Errorf("%w: %v", errCB0Published, err)
	}
	return nil
}
func (s *Session) cb0Manifest(root common.Hash) cb0Manifest {
	return cb0Manifest{Format: StoreFormat, Context: cb0Context, Owner: s.owner, Length: s.length, StateRoot: root, Engine: cb0EngineAddress, EngineCodeHash: s.engineHash, AS0: s.as0Address, Index: s.indexAddress, Decoders: append([]common.Address(nil), s.decoders...), Coordinator: s.coordinator, PackageRoot: s.packageRoot, JavaHead: s.javaHead, AS0CodeHash: s.as0Hash, ZI0CodeHash: s.zi0Hash, DI0CodeHash: s.di0Hash, CoordinatorCodeHash: s.coordHash}
}
func (s *Session) cb0WriteBlob(root common.Hash, b []byte) error {
	if root == (common.Hash{}) || len(b) == 0 || len(b) > int(MaxCheckpointBytes) || crypto.Keccak256Hash(b) != root {
		return errors.New("cb0: refusing invalid checkpoint blob")
	}
	path := filepath.Join(s.directory, cb0BlobDirectory, root.Hex()[2:]+".checkpoint")
	if old, e := cb0ReadRegular(path, int64(MaxCheckpointBytes)); e == nil {
		if !bytes.Equal(old, b) {
			return errors.New("cb0: checkpoint collision")
		}
		f, e := os.Open(path)
		if e != nil {
			return e
		}
		e = f.Sync()
		c := f.Close()
		if e != nil {
			return e
		}
		if c != nil {
			return c
		}
		return cb0SyncDir(filepath.Dir(path))
	} else if !errors.Is(e, os.ErrNotExist) {
		return e
	}
	f, e := os.CreateTemp(filepath.Dir(path), ".checkpoint-")
	if e != nil {
		return e
	}
	name := f.Name()
	if e = f.Chmod(0600); e == nil {
		_, e = f.Write(b)
	}
	if e == nil {
		e = f.Sync()
	}
	if c := f.Close(); e == nil {
		e = c
	}
	if e != nil {
		return e
	}
	if e = os.Rename(name, path); e != nil {
		return e
	}
	return cb0SyncDir(filepath.Dir(path))
}

func (s *Session) cb0Reopen() error {
	m, err := cb0ReadManifest(filepath.Join(s.directory, cb0ManifestName))
	if err != nil {
		return err
	}
	if m.Format != StoreFormat || m.Context != cb0Context || m.Owner != s.owner || m.Length != s.length || m.StateRoot == (common.Hash{}) || m.StateRoot == types.EmptyRootHash || m.Engine != cb0EngineAddress || m.EngineCodeHash != s.engineHash || m.AS0CodeHash != s.as0Hash || m.ZI0CodeHash != s.zi0Hash || m.DI0CodeHash != s.di0Hash || m.CoordinatorCodeHash != s.coordHash || len(m.Decoders) > int(MaxResources) {
		return errors.New("cb0: manifest identity or cap differs")
	}
	if err = s.cb0Reload(m.StateRoot); err != nil {
		return err
	}
	if s.state.GetCodeHash(cb0EngineAddress) != s.engineHash || s.state.GetNonce(cb0EngineAddress) != 0 {
		return errors.New("cb0: engine anchor differs")
	}
	if m.AS0 != crypto.CreateAddress(s.owner, 0) || s.state.GetCodeHash(m.AS0) != s.as0Hash {
		return errors.New("cb0: AS0 route differs")
	}
	if m.Index != (common.Address{}) && m.Index != crypto.CreateAddress(s.owner, 1) {
		return errors.New("cb0: index route differs")
	}
	for i, a := range m.Decoders {
		if a != crypto.CreateAddress(s.owner, uint64(i)+2) || s.state.GetCodeHash(a) != s.di0Hash {
			return errors.New("cb0: decoder route differs")
		}
	}
	if m.Coordinator != (common.Address{}) && (m.Coordinator != crypto.CreateAddress(s.owner, uint64(2+len(m.Decoders))) || s.state.GetCodeHash(m.Coordinator) != s.coordHash) {
		return errors.New("cb0: coordinator route differs")
	}
	s.as0Address, s.indexAddress, s.decoders, s.coordinator, s.packageRoot, s.javaHead = m.AS0, m.Index, append([]common.Address(nil), m.Decoders...), m.Coordinator, m.PackageRoot, m.JavaHead
	s.initialization = Initialization{false, cb0EngineAddress, s.engineHash, m.StateRoot, as0.Creation{Performed: false, Controller: m.AS0, RuntimeCodeHash: s.as0Hash, StateRoot: m.StateRoot}}
	if m.JavaHead != (common.Hash{}) {
		b, e := cb0ReadRegular(filepath.Join(s.directory, cb0BlobDirectory, m.JavaHead.Hex()[2:]+".checkpoint"), int64(MaxCheckpointBytes))
		if e != nil || len(b) == 0 || crypto.Keccak256Hash(b) != m.JavaHead {
			return errors.New("cb0: latest checkpoint blob differs")
		}
	}
	// Re-read all reachable controller/engine anchors from EVM state; the
	// manifest routes are bounded transport pointers, never authority.
	head, err := s.Head(OrdinaryGas)
	if err != nil {
		return fmt.Errorf("cb0: reopen EVM anchors: %w", err)
	}
	s.instanceID = head.Coordinator.InstanceID
	return nil
}

func (s *Session) Close() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.closed {
		return nil
	}
	s.closed = true
	var e error
	if s.trie != nil {
		e = errors.Join(e, s.trie.Close())
	}
	if s.disk != nil {
		e = errors.Join(e, s.disk.Close())
	}
	return e
}
func (s *Session) cb0Usable() error {
	if s.closed {
		return errors.New("cb0: session is closed")
	}
	if s.poison != nil {
		return s.poison
	}
	return nil
}
func (s *Session) cb0Gas(g uint64) error {
	if g == 0 || g > MaxGas {
		return errors.New("cb0: gas must be in frozen range 1..1000000000")
	}
	return nil
}
func (s *Session) cb0Config(st *state.StateDB, gas uint64) *evmruntime.Config {
	z := common.Hash{}
	return &evmruntime.Config{ChainConfig: params.AllDevChainProtocolChanges, Difficulty: new(big.Int), Origin: s.owner, Coinbase: common.Address{}, BlockNumber: big.NewInt(1), Time: 1, GasLimit: gas, GasPrice: new(big.Int), Value: new(big.Int), BaseFee: new(big.Int).SetUint64(params.InitialBaseFee), BlobBaseFee: new(big.Int).SetUint64(params.BlobTxMinBlobGasprice), Random: &z, State: st, GetHashFn: func(uint64) common.Hash { return common.Hash{} }, EVMConfig: vm.Config{}}
}
func (s *Session) cb0Inject(p cb0FaultPoint) error {
	if s.testFault != nil {
		return s.testFault(p)
	}
	return nil
}

func cb0PrepareDirectory(dir string) (bool, error) {
	info, e := os.Lstat(dir)
	if errors.Is(e, os.ErrNotExist) {
		if e = os.MkdirAll(dir, 0700); e != nil {
			return false, e
		}
		return true, nil
	}
	if e != nil {
		return false, e
	}
	if !info.IsDir() {
		return false, errors.New("cb0: store path is not a directory")
	}
	entries, e := os.ReadDir(dir)
	if e != nil {
		return false, e
	}
	if len(entries) == 0 {
		return true, nil
	}
	want := map[string]bool{cb0MarkerName: true, cb0ManifestName: true, cb0StateDirectory: true, cb0BlobDirectory: true}
	seen := map[string]bool{}
	for _, entry := range entries {
		info, e := entry.Info()
		if e != nil {
			return false, e
		}
		if strings.HasPrefix(entry.Name(), ".durable-head-") && info.Mode().IsRegular() {
			continue
		}
		if !want[entry.Name()] || entry.Type()&os.ModeSymlink != 0 {
			return false, fmt.Errorf("cb0: refuse unsupported directory entry %q", entry.Name())
		}
		isDataDir := entry.Name() == cb0StateDirectory || entry.Name() == cb0BlobDirectory
		if isDataDir != info.IsDir() || (!isDataDir && !info.Mode().IsRegular()) {
			return false, fmt.Errorf("cb0: unsupported entry shape %q", entry.Name())
		}
		if isDataDir {
			if e = filepath.WalkDir(filepath.Join(dir, entry.Name()), func(path string, d os.DirEntry, err error) error {
				if err != nil {
					return err
				}
				if d.Type()&os.ModeSymlink != 0 {
					return fmt.Errorf("cb0: linked internal entry %q", path)
				}
				i, err := d.Info()
				if err != nil {
					return err
				}
				if !i.IsDir() && !i.Mode().IsRegular() {
					return fmt.Errorf("cb0: unsupported internal entry %q", path)
				}
				return nil
			}); e != nil {
				return false, e
			}
		}
		seen[entry.Name()] = true
	}
	for n := range want {
		if !seen[n] {
			return false, errors.New("cb0: incomplete nonempty store directory")
		}
	}
	return false, nil
}
func cb0ReadRegular(path string, limit int64) ([]byte, error) {
	info, e := os.Lstat(path)
	if e != nil {
		return nil, e
	}
	if !info.Mode().IsRegular() || info.Size() < 0 || info.Size() > limit {
		return nil, errors.New("cb0: unsupported regular file")
	}
	f, e := os.Open(path)
	if e != nil {
		return nil, e
	}
	defer f.Close()
	opened, e := f.Stat()
	if e != nil {
		return nil, e
	}
	if !opened.Mode().IsRegular() || !os.SameFile(info, opened) {
		return nil, errors.New("cb0: file changed while opening")
	}
	b, e := io.ReadAll(io.LimitReader(f, limit+1))
	if e != nil {
		return nil, e
	}
	if int64(len(b)) > limit {
		return nil, errors.New("cb0: file exceeds bound")
	}
	return b, nil
}
func cb0ReadManifest(path string) (cb0Manifest, error) {
	var m cb0Manifest
	b, e := cb0ReadRegular(path, 32768)
	if e != nil {
		return m, e
	}
	d := json.NewDecoder(bytes.NewReader(b))
	d.DisallowUnknownFields()
	if e = d.Decode(&m); e != nil {
		return m, e
	}
	var x any
	if e = d.Decode(&x); e != io.EOF {
		return m, errors.New("cb0: trailing manifest data")
	}
	return m, nil
}
func cb0SyncDir(path string) error {
	d, e := os.Open(path)
	if e != nil {
		return e
	}
	defer d.Close()
	return d.Sync()
}

// Only bounded metadata/routing assertions are checked here. The EVM remains
// the class/ZIP/decoder authority; no byte catalogue or evaluator is involved.
func cb0ReadDiskMetadata(dir string, owner common.Address, length uint32, coordHash common.Hash) (cb0Manifest, error) {
	marker, e := cb0ReadRegular(filepath.Join(dir, cb0MarkerName), int64(len(StoreMarker)))
	if e != nil || string(marker) != StoreMarker {
		return cb0Manifest{}, errors.New("cb0: invalid namespace marker")
	}
	m, e := cb0ReadManifest(filepath.Join(dir, cb0ManifestName))
	if e != nil {
		return m, e
	}
	if m.Format != StoreFormat || m.Context != cb0Context || m.Owner != owner || m.Length != length || m.StateRoot == (common.Hash{}) || m.StateRoot == types.EmptyRootHash || m.Engine != cb0EngineAddress || m.EngineCodeHash != cb0VFSCode || m.AS0CodeHash != cb0AS0Code || m.ZI0CodeHash != cb0ZI0Code || m.DI0CodeHash != cb0DI0Code || m.CoordinatorCodeHash != coordHash || m.AS0 != crypto.CreateAddress(owner, 0) || len(m.Decoders) > int(MaxResources) {
		return m, errors.New("cb0: manifest binding mismatch")
	}
	if m.Index == (common.Address{}) {
		if len(m.Decoders) != 0 || m.Coordinator != (common.Address{}) {
			return m, errors.New("cb0: manifest absent index has dependent routes")
		}
	} else if m.Index != crypto.CreateAddress(owner, 1) {
		return m, errors.New("cb0: manifest index route mismatch")
	}
	for i, a := range m.Decoders {
		if a != crypto.CreateAddress(owner, uint64(i)+2) {
			return m, errors.New("cb0: manifest decoder route mismatch")
		}
	}
	if m.Coordinator == (common.Address{}) {
		if m.PackageRoot != (common.Hash{}) || m.JavaHead != (common.Hash{}) {
			return m, errors.New("cb0: manifest absent coordinator has Java/package data")
		}
	} else if len(m.Decoders) == 0 || m.Coordinator != crypto.CreateAddress(owner, uint64(2+len(m.Decoders))) || m.PackageRoot == (common.Hash{}) {
		return m, errors.New("cb0: manifest coordinator binding mismatch")
	}
	return m, nil
}
func cb0WriteNewRegular(path string, b []byte) error {
	f, e := os.OpenFile(path, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	if e != nil {
		return e
	}
	if _, e = f.Write(b); e == nil {
		e = f.Sync()
	}
	if x := f.Close(); e == nil {
		e = x
	}
	return e
}
