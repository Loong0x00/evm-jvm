package zi0

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
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/core/vm"
	evmruntime "github.com/ethereum/go-ethereum/core/vm/runtime"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/ethdb"
	"github.com/ethereum/go-ethereum/ethdb/leveldb"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/as0"
	"github.com/ethereum/go-ethereum/params"
	"github.com/ethereum/go-ethereum/triedb"
)

type durableDB interface {
	ethdb.Database
	SyncKeyValue() error
}
type manifest struct {
	Format      uint32         `json:"format"`
	Context     string         `json:"context"`
	Owner       common.Address `json:"owner"`
	Length      uint32         `json:"length"`
	AS0         common.Address `json:"as0"`
	Index       common.Address `json:"index"`
	Content     common.Hash    `json:"content"`
	AS0CodeHash common.Hash    `json:"as0CodeHash"`
	ZI0CodeHash common.Hash    `json:"zi0CodeHash"`
	StateRoot   common.Hash    `json:"stateRoot"`
}
type faultPoint uint8

const (
	faultAfterTrie faultPoint = iota + 1
	faultBeforeManifest
	faultAfterManifestRename
)

type Session struct {
	mu                                       sync.Mutex
	owner                                    common.Address
	length                                   uint32
	as0ABI, zi0ABI                           abi.ABI
	as0Init, as0Runtime, zi0Init, zi0Runtime []byte
	as0Hash, zi0Hash                         common.Hash
	as0Address, indexAddress                 common.Address
	creation                                 as0.Creation
	directory                                string
	disk                                     durableDB
	trie                                     *triedb.Database
	state                                    *state.StateDB
	root                                     common.Hash
	closed                                   bool
	poison                                   error
	testFault                                func(faultPoint) error
}

func NewMemory(owner common.Address, length uint32) (*Session, error) {
	if e := validateInputs(owner, length); e != nil {
		return nil, e
	}
	s, e := newSession(owner, length, "", rawdb.NewMemoryDatabase())
	if e != nil {
		return nil, e
	}
	if e = s.createAS0(); e != nil {
		s.Close()
		return nil, e
	}
	return s, nil
}
func Open(directory string, owner common.Address, length uint32) (*Session, error) {
	if e := validateInputs(owner, length); e != nil {
		return nil, e
	}
	if directory == "" {
		return nil, errors.New("zi0: directory must not be empty")
	}
	x, e := loadArtifacts()
	if e != nil {
		return nil, e
	}
	abs, e := filepath.Abs(directory)
	if e != nil {
		return nil, e
	}
	if r, x := filepath.EvalSymlinks(abs); x == nil {
		abs = r
	} else if !errors.Is(x, os.ErrNotExist) {
		return nil, fmt.Errorf("zi0: resolve store root: %w", x)
	}
	fresh, e := prepareDirectory(abs)
	if e != nil {
		return nil, e
	}
	var m manifest
	if !fresh {
		m, e = readDiskMetadata(abs, owner, length, crypto.Keccak256Hash(x.as0Run), crypto.Keccak256Hash(x.zi0Run))
		if e != nil {
			return nil, e
		}
	}
	kv, e := leveldb.New(filepath.Join(abs, stateDirectory), 16, 16, "jvmevm/zi0", false)
	if e != nil {
		return nil, fmt.Errorf("zi0: open state database: %w", e)
	}
	s, e := newSession(owner, length, abs, rawdb.NewDatabase(kv))
	if e != nil {
		kv.Close()
		return nil, e
	}
	if fresh {
		if e = s.initDisk(); e != nil {
			s.Close()
			return nil, e
		}
		return s, nil
	}
	if e = s.reopen(m); e != nil {
		s.Close()
		return nil, e
	}
	return s, nil
}
func validateInputs(owner common.Address, length uint32) error {
	if owner == (common.Address{}) {
		return errors.New("zi0: owner must be nonzero")
	}
	if length == 0 || length > as0.MaxLength {
		return errors.New("zi0: declared length must be in 1..33554432")
	}
	return nil
}

type loaded struct {
	as0Init, as0Run, zi0Init, zi0Run []byte
	as0ABI, zi0ABI                   abi.ABI
}

func loadArtifacts() (loaded, error) {
	var x loaded
	var e error
	if x.as0Init, e = as0.InitCode(); e != nil {
		return x, e
	}
	if x.as0Run, e = as0.Runtime(); e != nil {
		return x, e
	}
	if x.as0ABI, e = as0.ABI(); e != nil {
		return x, e
	}
	if crypto.Keccak256Hash(x.as0Run) != as0CodeHash {
		return x, errors.New("zi0: AS0 runtime is not the accepted pinned controller")
	}
	if x.zi0Init, e = InitCode(); e != nil {
		return x, e
	}
	if x.zi0Run, e = Runtime(); e != nil {
		return x, e
	}
	if x.zi0ABI, e = ABI(); e != nil {
		return x, e
	}
	return x, nil
}
func newSession(owner common.Address, length uint32, dir string, d durableDB) (*Session, error) {
	x, e := loadArtifacts()
	if e != nil {
		d.Close()
		return nil, fmt.Errorf("zi0: load artifacts: %w", e)
	}
	td := triedb.NewDatabase(d, triedb.HashDefaults)
	st, e := state.New(types.EmptyRootHash, state.NewDatabase(td, nil))
	if e != nil {
		td.Close()
		d.Close()
		return nil, e
	}
	return &Session{owner: owner, length: length, directory: dir, disk: d, trie: td, state: st, root: types.EmptyRootHash, as0ABI: x.as0ABI, zi0ABI: x.zi0ABI, as0Init: x.as0Init, as0Runtime: x.as0Run, zi0Init: x.zi0Init, zi0Runtime: x.zi0Run, as0Hash: crypto.Keccak256Hash(x.as0Run), zi0Hash: crypto.Keccak256Hash(x.zi0Run)}, nil
}

func (s *Session) createAS0() error {
	args, e := s.as0ABI.Pack("", s.length)
	if e != nil {
		return e
	}
	out, addr, left, e := evmruntime.Create(append(append([]byte(nil), s.as0Init...), args...), s.config(s.state, OrdinaryGas))
	used := OrdinaryGas - left
	if e != nil {
		return fmt.Errorf("zi0: AS0 constructor failed after %d gas: %w", used, e)
	}
	if !bytes.Equal(out, s.as0Runtime) || !bytes.Equal(s.state.GetCode(addr), s.as0Runtime) || s.state.GetCodeHash(addr) != s.as0Hash {
		return errors.New("zi0: AS0 constructor installed unexpected code")
	}
	s.as0Address = addr
	r, e := s.commit()
	if e != nil {
		return e
	}
	if e = s.reload(r); e != nil {
		return e
	}
	s.creation = as0.Creation{Performed: true, Controller: addr, GasUsed: used, RuntimeCodeHash: s.as0Hash, StateRoot: r}
	return nil
}
func (s *Session) initDisk() error {
	if e := writeNewRegular(filepath.Join(s.directory, markerName), []byte(storeMarker), 0600); e != nil {
		return e
	}
	if e := syncDir(s.directory); e != nil {
		return e
	}
	return s.publish(s.root)
}
func (s *Session) reopen(m manifest) error {
	if m.Format != storeFormat || m.Context != contextID || m.Owner != s.owner || m.Length != s.length || m.AS0 == (common.Address{}) || m.AS0CodeHash != s.as0Hash || m.ZI0CodeHash != s.zi0Hash || m.StateRoot == (common.Hash{}) {
		return errors.New("zi0: manifest identity or code pin mismatch")
	}
	if e := s.reload(m.StateRoot); e != nil {
		return e
	}
	s.as0Address, s.indexAddress = m.AS0, m.Index
	if s.as0Address != crypto.CreateAddress(s.owner, 0) || (s.indexAddress != (common.Address{}) && s.indexAddress != crypto.CreateAddress(s.owner, 1)) {
		return errors.New("zi0: manifest addresses are not the ordinary CREATE addresses")
	}
	if s.state.GetCodeHash(s.as0Address) != s.as0Hash {
		return errors.New("zi0: committed AS0 code differs from embedded artifact")
	}
	if s.indexAddress != (common.Address{}) && (s.indexAddress == s.as0Address || s.state.GetCodeHash(s.indexAddress) != s.zi0Hash || s.state.GetNonce(s.owner) != 2) {
		return errors.New("zi0: committed ZI0 code or creator nonce differs from embedded artifact")
	}
	if s.indexAddress == (common.Address{}) && (s.state.GetNonce(s.owner) != 1 || len(s.state.GetCode(crypto.CreateAddress(s.owner, 1))) != 0) {
		return errors.New("zi0: absent ZI0 does not agree with creator state")
	}
	ah, e := s.as0Head(OrdinaryGas)
	if e != nil {
		return e
	}
	if ah.Owner != s.owner || ah.Controller != s.as0Address || ah.DeclaredLength != s.length {
		return errors.New("zi0: reopened AS0 getters differ from manifest")
	}
	if s.indexAddress != (common.Address{}) {
		ih, e := s.indexHead(OrdinaryGas)
		if e != nil {
			return e
		}
		if ih.Owner != s.owner || ih.Store != s.as0Address || ih.Length != s.length || ih.RuntimeCodeHash != s.zi0Hash || ih.Content != m.Content || ih.Phase > 2 {
			return errors.New("zi0: reopened ZI0 getters differ from manifest")
		}
	} else if m.Content != (common.Hash{}) {
		return errors.New("zi0: absent index has content")
	}
	s.creation = as0.Creation{Controller: s.as0Address, RuntimeCodeHash: s.as0Hash, StateRoot: m.StateRoot}
	return nil
}

func (s *Session) Creation() (as0.Creation, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if e := s.usable(); e != nil {
		return as0.Creation{}, e
	}
	return s.creation, nil
}
func (s *Session) CreateIndex(content common.Hash, gas uint64) (Operation, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var op Operation
	if e := s.usable(); e != nil {
		return op, e
	}
	if e := checkGas(gas); e != nil {
		return op, e
	}
	if s.indexAddress != (common.Address{}) {
		return op, errors.New("zi0: index already created")
	}
	data, e := s.zi0ABI.Pack("", s.as0Address, content)
	if e != nil {
		return op, e
	}
	old, snap := s.root, s.state.Snapshot()
	out, addr, left, e := evmruntime.Create(append(append([]byte(nil), s.zi0Init...), data...), s.config(s.state, gas))
	op.GasUsed = gas - left
	if e != nil {
		if rerr := s.rollback(snap, old); rerr != nil {
			return Operation{GasUsed: op.GasUsed, RevertData: append([]byte(nil), out...)}, rerr
		}
		op.RevertData = append([]byte(nil), out...)
		return op, fmt.Errorf("zi0: EVM index constructor failed: %w (revert_data=0x%x)", e, out)
	}
	if !bytes.Equal(out, s.zi0Runtime) || !bytes.Equal(s.state.GetCode(addr), s.zi0Runtime) || s.state.GetCodeHash(addr) != s.zi0Hash {
		if rerr := s.rollback(snap, old); rerr != nil {
			return Operation{GasUsed: op.GasUsed}, rerr
		}
		return op, errors.New("zi0: index constructor installed unexpected code")
	}
	s.indexAddress = addr
	if _, e = s.persist(old); e != nil {
		s.indexAddress = common.Address{}
		return Operation{GasUsed: op.GasUsed}, e
	}
	op.StateRoot = s.root
	op.CreatedAddress = addr
	return op, nil
}
func (s *Session) Append(cursor uint32, raw []byte, pi common.Hash, gas uint64) (Operation, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.as0Mutate("append", gas, cursor, append([]byte(nil), raw...), pi)
}
func (s *Session) Seal(cursor uint32, chain common.Hash, gas uint64) (Operation, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.as0Mutate("seal", gas, cursor, chain)
}
func (s *Session) as0Mutate(method string, gas uint64, args ...interface{}) (Operation, error) {
	var op Operation
	if e := s.usable(); e != nil {
		return op, e
	}
	if e := checkGas(gas); e != nil {
		return op, e
	}
	data, e := s.as0ABI.Pack(method, args...)
	if e != nil {
		return op, e
	}
	old, snap := s.root, s.state.Snapshot()
	before := len(s.state.Logs())
	out, left, e := evmruntime.Call(s.as0Address, data, s.config(s.state, gas))
	op.GasUsed = gas - left
	if e != nil {
		if rerr := s.rollback(snap, old); rerr != nil {
			return Operation{GasUsed: op.GasUsed, RevertData: append([]byte(nil), out...)}, rerr
		}
		op.RevertData = append([]byte(nil), out...)
		return op, fmt.Errorf("zi0: EVM AS0 %s failed: %w (revert_data=0x%x)", method, e, out)
	}
	logs := s.state.Logs()
	if before > len(logs) || len(logs)-before != 1 {
		if rerr := s.rollback(snap, old); rerr != nil {
			return Operation{GasUsed: op.GasUsed}, rerr
		}
		return Operation{GasUsed: op.GasUsed}, fmt.Errorf("zi0: AS0 %s emitted unexpected success logs", method)
	}
	op.Logs = copyLogs(logs[before:])
	want := s.as0ABI.Events["PageIssued"].ID
	if method == "seal" {
		want = s.as0ABI.Events["Sealed"].ID
	}
	if op.Logs[0].Address != s.as0Address || len(op.Logs[0].Topics) == 0 || op.Logs[0].Topics[0] != want {
		if rerr := s.rollback(snap, old); rerr != nil {
			return Operation{GasUsed: op.GasUsed}, rerr
		}
		return Operation{GasUsed: op.GasUsed}, fmt.Errorf("zi0: AS0 %s emitted wrong success event", method)
	}
	if _, e = s.persist(old); e != nil {
		return Operation{GasUsed: op.GasUsed}, e
	}
	op.StateRoot = s.root
	return op, nil
}
func (s *Session) Discover(gas uint64) (Operation, error) { return s.ziMutate("discover", gas) }
func (s *Session) Scan(entry, cursor uint32, rolling common.Hash, units uint16, gas uint64) (Operation, error) {
	return s.ziMutate("scan", gas, entry, cursor, rolling, units)
}
func (s *Session) Finish(count, cursor uint32, rolling common.Hash, gas uint64) (Operation, error) {
	return s.ziMutate("finish", gas, count, cursor, rolling)
}
func (s *Session) ziMutate(method string, gas uint64, args ...interface{}) (Operation, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var op Operation
	if e := s.usable(); e != nil {
		return op, e
	}
	if s.indexAddress == (common.Address{}) {
		return op, errors.New("zi0: index is not constructed")
	}
	if e := checkGas(gas); e != nil {
		return op, e
	}
	data, e := s.zi0ABI.Pack(method, args...)
	if e != nil {
		return op, e
	}
	old, snap := s.root, s.state.Snapshot()
	out, left, e := evmruntime.Call(s.indexAddress, data, s.config(s.state, gas))
	op.GasUsed = gas - left
	if e != nil {
		if rerr := s.rollback(snap, old); rerr != nil {
			return Operation{GasUsed: op.GasUsed, RevertData: append([]byte(nil), out...)}, rerr
		}
		op.RevertData = append([]byte(nil), out...)
		return op, fmt.Errorf("zi0: EVM %s failed: %w (revert_data=0x%x)", method, e, out)
	}
	if len(out) != 0 {
		if rerr := s.rollback(snap, old); rerr != nil {
			return Operation{GasUsed: op.GasUsed}, rerr
		}
		return Operation{GasUsed: op.GasUsed}, fmt.Errorf("zi0: EVM %s returned unexpected bytes", method)
	}
	if _, e = s.persist(old); e != nil {
		return Operation{GasUsed: op.GasUsed}, e
	}
	op.StateRoot = s.root
	return op, nil
}

func (s *Session) Read(offset, length uint32, gas uint64) (as0.Read, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var r as0.Read
	if e := s.usable(); e != nil {
		return r, e
	}
	out, u, e := s.view(s.state.Copy(), s.as0Address, s.as0ABI, "read", gas, offset, length)
	r.GasUsed = u
	if e != nil {
		return r, e
	}
	v, e := s.as0ABI.Unpack("read", out)
	if e != nil || len(v) != 1 {
		return r, e
	}
	b, ok := v[0].([]byte)
	if !ok || len(b) != int(length) {
		return as0.Read{GasUsed: u}, errors.New("zi0: noncanonical AS0 read result")
	}
	r.Bytes = append([]byte(nil), b...)
	return r, nil
}
func (s *Session) Page(index uint64, gas uint64) (as0.Page, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var r as0.Page
	if e := s.usable(); e != nil {
		return r, e
	}
	out, u, e := s.view(s.state.Copy(), s.as0Address, s.as0ABI, "page", gas, new(big.Int).SetUint64(index))
	r.GasUsed = u
	if e != nil {
		return r, e
	}
	v, e := s.as0ABI.Unpack("page", out)
	if e != nil || len(v) != 3 {
		return r, e
	}
	a, ok0 := v[0].(common.Address)
	ch, ok1 := v[1].([32]byte)
	pi, ok2 := v[2].([32]byte)
	if !ok0 || !ok1 || !ok2 {
		return as0.Page{GasUsed: u}, errors.New("zi0: noncanonical AS0 page result")
	}
	r.Address, r.CodeHash, r.Commitment = a, common.Hash(ch), common.Hash(pi)
	return r, nil
}
func (s *Session) Entry(index uint32, gas uint64) (Entry, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var r Entry
	if e := s.usable(); e != nil {
		return r, e
	}
	if s.indexAddress == (common.Address{}) {
		return r, errors.New("zi0: index is not constructed")
	}
	out, u, e := s.view(s.state.Copy(), s.indexAddress, s.zi0ABI, "entry", gas, index)
	r.GasUsed = u
	if e != nil {
		return r, e
	}
	v, e := s.zi0ABI.Unpack("entry", out)
	if e != nil || len(v) != 2 {
		return r, e
	}
	n, ok := v[0].([]byte)
	p, okp := v[1].([32]byte)
	if !ok || !okp {
		return Entry{GasUsed: u}, errors.New("zi0: noncanonical EVM entry result")
	}
	r.Name = append([]byte(nil), n...)
	r.PackedRecord = common.Hash(p)
	return r, nil
}
func (s *Session) Lookup(name []byte, gas uint64) (LookupResult, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var r LookupResult
	if e := s.usable(); e != nil {
		return r, e
	}
	if s.indexAddress == (common.Address{}) {
		return r, errors.New("zi0: index is not constructed")
	}
	out, u, e := s.view(s.state.Copy(), s.indexAddress, s.zi0ABI, "lookup", gas, append([]byte(nil), name...))
	r.GasUsed = u
	if e != nil {
		return r, e
	}
	v, e := s.zi0ABI.Unpack("lookup", out)
	if e != nil || len(v) != 3 {
		return r, e
	}
	f, ok0 := v[0].(bool)
	i, ok1 := v[1].(uint32)
	p, ok2 := v[2].([32]byte)
	if !ok0 || !ok1 || !ok2 {
		return LookupResult{GasUsed: u}, errors.New("zi0: noncanonical lookup result")
	}
	r.Found, r.Index, r.PackedRecord = f, i, common.Hash(p)
	return r, nil
}

func (s *Session) Head(gas uint64) (Head, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if e := s.usable(); e != nil {
		return Head{}, e
	}
	if e := checkGas(gas); e != nil {
		return Head{}, e
	}
	a, e := s.as0Head(gas)
	h := Head{AS0: a, StateRoot: s.root, GasUsed: a.GasUsed}
	if e != nil {
		return h, e
	}
	if s.indexAddress != (common.Address{}) {
		i, e := s.indexHead(gas)
		h.Index = i
		h.GasUsed += i.GasUsed
		if e != nil {
			return h, e
		}
	}
	return h, nil
}
func (s *Session) as0Head(gas uint64) (as0.Head, error) {
	var h as0.Head
	names := []string{"owner", "declaredLength", "cursor", "isSealed", "pageCount", "chainCommitment", "contentCommitment", "PAGE_SIZE", "MAX_PAGES", "MAX_LENGTH"}
	st := s.state.Copy()
	vals := make([]interface{}, len(names))
	for i, n := range names {
		o, u, e := s.view(st, s.as0Address, s.as0ABI, n, gas)
		h.GasUsed += u
		if e != nil {
			return h, e
		}
		v, e := s.as0ABI.Unpack(n, o)
		if e != nil || len(v) != 1 {
			return h, e
		}
		vals[i] = v[0]
	}
	var ok bool
	if h.Owner, ok = vals[0].(common.Address); !ok {
		return h, errors.New("zi0: AS0 owner type")
	}
	if h.DeclaredLength, ok = vals[1].(uint32); !ok {
		return h, errors.New("zi0: AS0 length type")
	}
	if h.Cursor, ok = vals[2].(uint32); !ok {
		return h, errors.New("zi0: AS0 cursor type")
	}
	if h.Sealed, ok = vals[3].(bool); !ok {
		return h, errors.New("zi0: AS0 sealed type")
	}
	n, yes := vals[4].(*big.Int)
	if !yes || !n.IsUint64() {
		return h, errors.New("zi0: AS0 page count type")
	}
	h.PageCount = uint32(n.Uint64())
	h.ChainCommitment = common.Hash(vals[5].([32]byte))
	h.ContentCommitment = common.Hash(vals[6].([32]byte))
	h.PageSize = vals[7].(uint32)
	h.MaxPages = vals[8].(uint32)
	h.MaxLength = vals[9].(uint32)
	h.Controller = s.as0Address
	h.RuntimeCodeHash = s.as0Hash
	h.StateRoot = s.root
	return h, nil
}
func (s *Session) indexHead(gas uint64) (IndexHead, error) {
	h := IndexHead{Address: s.indexAddress, RuntimeCodeHash: s.zi0Hash}
	names := []string{"owner", "store", "content", "length", "phase", "eocd", "cdOffset", "cdSize", "count", "nextEntry", "cdCursor", "rolling", "finalRoot"}
	st := s.state.Copy()
	vals := make([]interface{}, len(names))
	for i, n := range names {
		o, u, e := s.view(st, s.indexAddress, s.zi0ABI, n, gas)
		h.GasUsed += u
		if e != nil {
			return h, e
		}
		v, e := s.zi0ABI.Unpack(n, o)
		if e != nil || len(v) != 1 {
			return h, e
		}
		vals[i] = v[0]
	}
	var ok bool
	if h.Owner, ok = vals[0].(common.Address); !ok {
		return h, errors.New("zi0: ZI0 owner type")
	}
	if h.Store, ok = vals[1].(common.Address); !ok {
		return h, errors.New("zi0: ZI0 store type")
	}
	h.Content = common.Hash(vals[2].([32]byte))
	if h.Length, ok = vals[3].(uint32); !ok {
		return h, errors.New("zi0: ZI0 length type")
	}
	if h.Phase, ok = vals[4].(uint8); !ok {
		return h, errors.New("zi0: ZI0 phase type")
	}
	if h.EOCD, ok = vals[5].(uint32); !ok {
		return h, errors.New("zi0: ZI0 eocd type")
	}
	if h.CDOffset, ok = vals[6].(uint32); !ok {
		return h, errors.New("zi0: ZI0 cdOffset type")
	}
	if h.CDSize, ok = vals[7].(uint32); !ok {
		return h, errors.New("zi0: ZI0 cdSize type")
	}
	if h.Count, ok = vals[8].(uint32); !ok {
		return h, errors.New("zi0: ZI0 count type")
	}
	if h.NextEntry, ok = vals[9].(uint32); !ok {
		return h, errors.New("zi0: ZI0 nextEntry type")
	}
	if h.CDCursor, ok = vals[10].(uint32); !ok {
		return h, errors.New("zi0: ZI0 cdCursor type")
	}
	h.Rolling = common.Hash(vals[11].([32]byte))
	h.FinalRoot = common.Hash(vals[12].([32]byte))
	return h, nil
}
func (s *Session) view(st *state.StateDB, to common.Address, a abi.ABI, method string, gas uint64, args ...interface{}) ([]byte, uint64, error) {
	if e := checkGas(gas); e != nil {
		return nil, 0, e
	}
	d, e := a.Pack(method, args...)
	if e != nil {
		return nil, 0, e
	}
	o, left, e := evmruntime.Call(to, d, s.config(st, gas))
	u := gas - left
	if e != nil {
		return append([]byte(nil), o...), u, fmt.Errorf("zi0: EVM view %s failed: %w (revert_data=0x%x)", method, e, o)
	}
	return o, u, nil
}

func (s *Session) persist(old common.Hash) (common.Hash, error) {
	r, e := s.commit()
	if e != nil {
		s.restore(old)
		return common.Hash{}, e
	}
	if s.directory == "" {
		if e = s.reload(r); e != nil {
			s.poison = e
			return common.Hash{}, e
		}
		return r, nil
	}
	if e = s.inject(faultAfterTrie); e != nil {
		s.restore(old)
		return common.Hash{}, e
	}
	if e = s.publish(r); e != nil {
		if errors.Is(e, errPublished) {
			s.poison = fmt.Errorf("zi0: ambiguous manifest publication; reopen required: %w", e)
			return common.Hash{}, s.poison
		}
		s.restore(old)
		return common.Hash{}, e
	}
	if e = s.reload(r); e != nil {
		s.poison = fmt.Errorf("zi0: published state cannot reload: %w", e)
		return common.Hash{}, s.poison
	}
	return r, nil
}
func (s *Session) commit() (common.Hash, error) {
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
func (s *Session) reload(r common.Hash) error {
	st, e := state.New(r, state.NewDatabase(s.trie, nil))
	if e != nil {
		return e
	}
	s.state, s.root = st, r
	return nil
}
func (s *Session) restore(r common.Hash) {
	if e := s.reload(r); e != nil {
		s.poison = e
	}
}
func (s *Session) rollback(snapshot int, root common.Hash) error {
	s.state.RevertToSnapshot(snapshot)
	if e := s.reload(root); e != nil {
		s.poison = fmt.Errorf("zi0: failed to reload prior published root: %w", e)
		return s.poison
	}
	return nil
}
func (s *Session) publish(r common.Hash) error {
	if e := s.inject(faultBeforeManifest); e != nil {
		return e
	}
	content, e := s.contentForManifest()
	if e != nil {
		return e
	}
	m := s.manifest(r, content)
	b, e := json.MarshalIndent(m, "", "  ")
	if e != nil {
		return e
	}
	b = append(b, '\n')
	f, e := os.CreateTemp(s.directory, ".durable-head-")
	if e != nil {
		return e
	}
	name := f.Name()
	if e = f.Chmod(0600); e != nil {
		f.Close()
		return e
	}
	if _, e = f.Write(b); e != nil {
		f.Close()
		return e
	}
	if e = f.Sync(); e != nil {
		f.Close()
		return e
	}
	if e = f.Close(); e != nil {
		return e
	}
	if e = os.Rename(name, filepath.Join(s.directory, manifestName)); e != nil {
		return e
	}
	if e = s.inject(faultAfterManifestRename); e != nil {
		return fmt.Errorf("%w: %v", errPublished, e)
	}
	if e = syncDir(s.directory); e != nil {
		return fmt.Errorf("%w: %v", errPublished, e)
	}
	return nil
}

var errPublished = errors.New("manifest renamed")

func (s *Session) manifest(r, content common.Hash) manifest {
	return manifest{Format: storeFormat, Context: contextID, Owner: s.owner, Length: s.length, AS0: s.as0Address, Index: s.indexAddress, Content: content, AS0CodeHash: s.as0Hash, ZI0CodeHash: s.zi0Hash, StateRoot: r}
}
func (s *Session) contentForManifest() (common.Hash, error) {
	if s.indexAddress == (common.Address{}) {
		return common.Hash{}, nil
	}
	o, _, e := s.view(s.state.Copy(), s.indexAddress, s.zi0ABI, "content", OrdinaryGas)
	if e != nil {
		return common.Hash{}, e
	}
	v, e := s.zi0ABI.Unpack("content", o)
	if e != nil || len(v) != 1 {
		return common.Hash{}, errors.New("zi0: decode content getter for manifest")
	}
	h, ok := v[0].([32]byte)
	if !ok || common.Hash(h) == (common.Hash{}) {
		return common.Hash{}, errors.New("zi0: noncanonical content getter for manifest")
	}
	return common.Hash(h), nil
}
func (s *Session) config(st *state.StateDB, gas uint64) *evmruntime.Config {
	z := common.Hash{}
	return &evmruntime.Config{ChainConfig: params.AllDevChainProtocolChanges, Difficulty: new(big.Int), Origin: s.owner, Coinbase: common.Address{}, BlockNumber: big.NewInt(1), Time: 1, GasLimit: gas, GasPrice: new(big.Int), Value: new(big.Int), BaseFee: new(big.Int).SetUint64(params.InitialBaseFee), BlobBaseFee: new(big.Int).SetUint64(params.BlobTxMinBlobGasprice), Random: &z, State: st, GetHashFn: func(uint64) common.Hash { return common.Hash{} }, EVMConfig: vm.Config{}}
}
func checkGas(g uint64) error {
	if g == 0 || g > MaxGas {
		return errors.New("zi0: gas must be in frozen range 1..1000000000")
	}
	return nil
}
func (s *Session) usable() error {
	if s.closed {
		return errors.New("zi0: session is closed")
	}
	if s.poison != nil {
		return s.poison
	}
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
func prepareDirectory(dir string) (bool, error) {
	i, e := os.Lstat(dir)
	if errors.Is(e, os.ErrNotExist) {
		if e = os.MkdirAll(dir, 0700); e != nil {
			return false, e
		}
		return true, nil
	}
	if e != nil {
		return false, e
	}
	if !i.IsDir() {
		return false, errors.New("zi0: store path is not a directory")
	}
	es, e := os.ReadDir(dir)
	if e != nil {
		return false, e
	}
	if len(es) == 0 {
		return true, nil
	}
	seen := map[string]bool{}
	for _, x := range es {
		name := x.Name()
		fi, e := x.Info()
		if e != nil {
			return false, e
		}
		if strings.HasPrefix(name, ".durable-head-") && fi.Mode().IsRegular() {
			continue
		}
		seen[name] = true
		switch name {
		case stateDirectory:
			if x.Type()&os.ModeSymlink != 0 || !fi.IsDir() {
				return false, fmt.Errorf("zi0: state must be a real directory")
			}
			e = filepath.WalkDir(filepath.Join(dir, name), func(p string, d os.DirEntry, e error) error {
				if e != nil {
					return e
				}
				if d.Type()&os.ModeSymlink != 0 {
					return fmt.Errorf("zi0: linked state entry %q is not supported", p)
				}
				return nil
			})
			if e != nil {
				return false, e
			}
		case markerName, manifestName:
			if x.Type()&os.ModeSymlink != 0 || !fi.Mode().IsRegular() {
				return false, fmt.Errorf("zi0: metadata %q must be regular", name)
			}
		default:
			return false, fmt.Errorf("zi0: refuse unrelated nonempty directory entry %q", name)
		}
	}
	if !seen[markerName] || !seen[manifestName] || !seen[stateDirectory] {
		return false, errors.New("zi0: incomplete nonempty ZI0 directory; refusing to overwrite")
	}
	return false, nil
}
func readDiskMetadata(dir string, owner common.Address, length uint32, as0Hash, zi0Hash common.Hash) (manifest, error) {
	b, e := readRegular(filepath.Join(dir, markerName), int64(len(storeMarker)))
	if e != nil || string(b) != storeMarker {
		return manifest{}, errors.New("zi0: invalid store marker")
	}
	m, e := readManifest(filepath.Join(dir, manifestName))
	if e != nil {
		return m, e
	}
	if m.Format != storeFormat || m.Context != contextID || m.Owner != owner || m.Length != length || m.AS0 != crypto.CreateAddress(owner, 0) || (m.Index != (common.Address{}) && m.Index != crypto.CreateAddress(owner, 1)) || m.Index == m.AS0 || m.AS0CodeHash != as0Hash || m.ZI0CodeHash != zi0Hash || (m.Index == (common.Address{})) != (m.Content == (common.Hash{})) || m.StateRoot == (common.Hash{}) {
		return manifest{}, errors.New("zi0: manifest binding mismatch")
	}
	return m, nil
}
func readRegular(path string, max int64) ([]byte, error) {
	i, e := os.Lstat(path)
	if e != nil {
		return nil, e
	}
	if !i.Mode().IsRegular() || i.Size() < 0 || i.Size() > max {
		return nil, fmt.Errorf("zi0: unsupported or oversized metadata %s", path)
	}
	f, e := os.Open(path)
	if e != nil {
		return nil, e
	}
	defer f.Close()
	j, e := f.Stat()
	if e != nil || !j.Mode().IsRegular() || !os.SameFile(i, j) {
		return nil, errors.New("zi0: metadata changed while opening")
	}
	b, e := io.ReadAll(io.LimitReader(f, max+1))
	if e != nil {
		return nil, e
	}
	if int64(len(b)) > max {
		return nil, errors.New("zi0: metadata exceeds bound")
	}
	return b, nil
}
func readManifest(path string) (manifest, error) {
	var m manifest
	b, e := readRegular(path, manifestMaxSize)
	if e != nil {
		return m, e
	}
	d := json.NewDecoder(bytes.NewReader(b))
	d.DisallowUnknownFields()
	if e = d.Decode(&m); e != nil {
		return m, e
	}
	var x interface{}
	if e = d.Decode(&x); !errors.Is(e, io.EOF) {
		return m, errors.New("zi0: trailing manifest data")
	}
	return m, nil
}
func writeNewRegular(path string, b []byte, mode os.FileMode) error {
	f, e := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, mode)
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
func syncDir(path string) error {
	f, e := os.Open(path)
	if e != nil {
		return e
	}
	defer f.Close()
	return f.Sync()
}
func (s *Session) inject(p faultPoint) error {
	if s.testFault != nil {
		return s.testFault(p)
	}
	return nil
}
func copyLogs(in []*types.Log) []*types.Log {
	out := make([]*types.Log, len(in))
	for i, l := range in {
		c := *l
		c.Topics = append([]common.Hash(nil), l.Topics...)
		c.Data = append([]byte(nil), l.Data...)
		out[i] = &c
	}
	return out
}
