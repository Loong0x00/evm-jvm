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
	// Immutable routing metadata established only by a successful, code-pinned
	// EVM constructor assertion, or by a getter-validated durable reopen.
	indexContent common.Hash
	creation     as0.Creation
	directory    string
	disk         durableDB
	trie         *triedb.Database
	state        *state.StateDB
	root         common.Hash
	closed       bool
	poison       error
	testFault    func(faultPoint) error
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
		return fmt.Errorf("zi0: write store marker: %w", e)
	}
	if e := syncDir(s.directory); e != nil {
		return fmt.Errorf("zi0: sync initial store layout: %w", e)
	}
	// A fresh durable ZI0 namespace starts with the same ordinary AS0 CREATE as
	// NewMemory.  Publishing an empty trie here would manufacture an address in
	// metadata without deploying its code and would make the first append call
	// address zero.  CREATE, trie/code sync, and reload happen before the first
	// manifest becomes routable.
	if e := s.createAS0(); e != nil {
		return e
	}
	if e := s.publish(s.root); e != nil {
		return fmt.Errorf("zi0: publish initial AS0 head: %w", e)
	}
	return nil
}
func (s *Session) reopen(m manifest) error {
	if m.Format != storeFormat || m.Context != contextID || m.Owner != s.owner || m.Length != s.length || m.AS0 == (common.Address{}) || m.AS0CodeHash != s.as0Hash || m.ZI0CodeHash != s.zi0Hash || m.StateRoot == (common.Hash{}) {
		return errors.New("zi0: manifest identity or code pin mismatch")
	}
	if e := s.reload(m.StateRoot); e != nil {
		return e
	}
	s.as0Address, s.indexAddress, s.indexContent = m.AS0, m.Index, m.Content
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
		if !ah.Sealed || ah.ContentCommitment != m.Content || ih.Owner != s.owner || ih.Store != s.as0Address || ih.Length != s.length || ih.RuntimeCodeHash != s.zi0Hash || ih.Content != m.Content || ih.Phase > 2 {
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
	// The completed pinned constructor proved this assertion equals the sealed
	// AS0 content. Cache only that immutable binding, never ZIP metadata. Avoid
	// a hidden extra EVM getter during each manifest publication.
	s.indexAddress, s.indexContent = addr, content
	if _, e = s.persist(old); e != nil {
		// Before publication, persist restored the prior root and the tentative
		// route must disappear. After rename, the session is poisoned and its
		// in-memory route is immaterial until an exact manifest reopen; retain it
		// so diagnostics cannot describe the committed state as address zero.
		if s.poison == nil {
			s.indexAddress, s.indexContent = common.Address{}, common.Hash{}
		}
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
	if e != nil {
		return r, fmt.Errorf("zi0: decode EVM AS0 read: %w", e)
	}
	if len(v) != 1 {
		return r, fmt.Errorf("zi0: decode EVM AS0 read: got %d values, want 1", len(v))
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
	if e != nil {
		return r, fmt.Errorf("zi0: decode EVM AS0 page: %w", e)
	}
	if len(v) != 3 {
		return r, fmt.Errorf("zi0: decode EVM AS0 page: got %d values, want 3", len(v))
	}
	a, ok0 := v[0].(common.Address)
	ch, ok1 := v[1].([32]byte)
	pi, ok2 := v[2].([32]byte)
	if !ok0 || !ok1 || !ok2 || a == (common.Address{}) || common.Hash(ch) == (common.Hash{}) || common.Hash(pi) == (common.Hash{}) {
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
	if e != nil {
		return r, fmt.Errorf("zi0: decode EVM entry: %w", e)
	}
	if len(v) != 2 {
		return r, fmt.Errorf("zi0: decode EVM entry: got %d values, want 2", len(v))
	}
	n, ok := v[0].([]byte)
	p, okp := v[1].([32]byte)
	if !ok || !okp || len(n) == 0 || len(n) > int(MaxName) || !canonicalPackedRecord(p) {
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
	if e != nil {
		return r, fmt.Errorf("zi0: decode EVM lookup: %w", e)
	}
	if len(v) != 3 {
		return r, fmt.Errorf("zi0: decode EVM lookup: got %d values, want 3", len(v))
	}
	f, ok0 := v[0].(bool)
	i, ok1 := v[1].(uint32)
	p, ok2 := v[2].([32]byte)
	if !ok0 || !ok1 || !ok2 || (!f && (i != 0 || common.Hash(p) != (common.Hash{}))) || (f && (i >= MaxEntries || !canonicalPackedRecord(p))) {
		return LookupResult{GasUsed: u}, errors.New("zi0: noncanonical lookup result")
	}
	r.Found, r.Index, r.PackedRecord = f, i, common.Hash(p)
	return r, nil
}

func canonicalPackedRecord(p [32]byte) bool {
	if common.Hash(p) == (common.Hash{}) {
		return false
	}
	// Bits 195..255 are frozen zero. In ABI's big-endian bytes32 these are
	// bytes 0..6 and the high five bits of byte 7.
	for i := 0; i < 7; i++ {
		if p[i] != 0 {
			return false
		}
	}
	return p[7]&0xf8 == 0
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
		if !a.Sealed || i.Owner != a.Owner || i.Store != a.Controller || i.Content != a.ContentCommitment || i.Length != a.DeclaredLength {
			return h, errors.New("zi0: AS0 and ZI0 EVM getter bindings disagree")
		}
	}
	return h, nil
}
func (s *Session) as0Head(gas uint64) (as0.Head, error) {
	var h as0.Head
	names := []string{"owner", "declaredLength", "cursor", "isSealed", "pageCount", "chainCommitment", "contentCommitment", "PAGE_SIZE", "MAX_PAGES", "MAX_LENGTH"}
	st := s.state.Copy()
	vals := make([]interface{}, len(names))
	for i, name := range names {
		out, used, err := s.view(st, s.as0Address, s.as0ABI, name, gas)
		h.GasUsed += used
		if err != nil {
			return h, err
		}
		decoded, err := s.as0ABI.Unpack(name, out)
		if err != nil {
			return h, fmt.Errorf("zi0: decode AS0 %s getter: %w", name, err)
		}
		if len(decoded) != 1 {
			return h, fmt.Errorf("zi0: decode AS0 %s getter: got %d values, want 1", name, len(decoded))
		}
		vals[i] = decoded[0]
	}
	var ok bool
	if h.Owner, ok = vals[0].(common.Address); !ok {
		return h, errors.New("zi0: noncanonical AS0 owner getter type")
	}
	if h.DeclaredLength, ok = vals[1].(uint32); !ok {
		return h, errors.New("zi0: noncanonical AS0 length getter type")
	}
	if h.Cursor, ok = vals[2].(uint32); !ok {
		return h, errors.New("zi0: noncanonical AS0 cursor getter type")
	}
	if h.Sealed, ok = vals[3].(bool); !ok {
		return h, errors.New("zi0: noncanonical AS0 sealed getter type")
	}
	pageCount, ok := vals[4].(*big.Int)
	if !ok || pageCount.Sign() < 0 || !pageCount.IsUint64() || pageCount.Uint64() > uint64(as0.MaxPages) {
		return h, errors.New("zi0: AS0 page count is noncanonical or out of range")
	}
	h.PageCount = uint32(pageCount.Uint64())
	chain, ok := vals[5].([32]byte)
	if !ok {
		return h, errors.New("zi0: noncanonical AS0 chain getter type")
	}
	content, ok := vals[6].([32]byte)
	if !ok {
		return h, errors.New("zi0: noncanonical AS0 content getter type")
	}
	h.ChainCommitment, h.ContentCommitment = common.Hash(chain), common.Hash(content)
	if h.PageSize, ok = vals[7].(uint32); !ok {
		return h, errors.New("zi0: noncanonical AS0 page-size getter type")
	}
	if h.MaxPages, ok = vals[8].(uint32); !ok {
		return h, errors.New("zi0: noncanonical AS0 max-pages getter type")
	}
	if h.MaxLength, ok = vals[9].(uint32); !ok {
		return h, errors.New("zi0: noncanonical AS0 max-length getter type")
	}
	h.Controller, h.RuntimeCodeHash, h.StateRoot = s.as0Address, s.as0Hash, s.root
	if h.Controller == (common.Address{}) || s.state.GetCodeHash(h.Controller) != s.as0Hash || h.Owner != s.owner || h.DeclaredLength != s.length || h.Cursor > h.DeclaredLength || h.PageSize != as0.PageSize || h.MaxPages != as0.MaxPages || h.MaxLength != as0.MaxLength || h.ChainCommitment == (common.Hash{}) {
		return as0.Head{GasUsed: h.GasUsed}, errors.New("zi0: AS0 getters violate bound identity or frozen limits")
	}
	covered := uint64(h.PageCount) * uint64(as0.PageSize)
	if covered < uint64(h.Cursor) || covered > uint64(h.Cursor)+uint64(as0.PageSize-1) || (h.Cursor != h.DeclaredLength && h.Cursor%as0.PageSize != 0) {
		return as0.Head{GasUsed: h.GasUsed}, errors.New("zi0: AS0 page/cursor geometry is noncanonical")
	}
	wantPages := (h.DeclaredLength + as0.PageSize - 1) / as0.PageSize
	if h.Sealed {
		if h.Cursor != h.DeclaredLength || h.PageCount != wantPages || h.ContentCommitment == (common.Hash{}) {
			return as0.Head{GasUsed: h.GasUsed}, errors.New("zi0: AS0 sealed head is noncanonical")
		}
	} else if h.ContentCommitment != (common.Hash{}) {
		return as0.Head{GasUsed: h.GasUsed}, errors.New("zi0: AS0 content was published before seal")
	}
	return h, nil
}

func (s *Session) indexHead(gas uint64) (IndexHead, error) {
	h := IndexHead{Address: s.indexAddress, RuntimeCodeHash: s.zi0Hash}
	names := []string{"owner", "store", "content", "length", "phase", "eocd", "cdOffset", "cdSize", "count", "nextEntry", "cdCursor", "rolling", "finalRoot"}
	st := s.state.Copy()
	vals := make([]interface{}, len(names))
	for i, name := range names {
		out, used, err := s.view(st, s.indexAddress, s.zi0ABI, name, gas)
		h.GasUsed += used
		if err != nil {
			return h, err
		}
		decoded, err := s.zi0ABI.Unpack(name, out)
		if err != nil {
			return h, fmt.Errorf("zi0: decode ZI0 %s getter: %w", name, err)
		}
		if len(decoded) != 1 {
			return h, fmt.Errorf("zi0: decode ZI0 %s getter: got %d values, want 1", name, len(decoded))
		}
		vals[i] = decoded[0]
	}
	var ok bool
	if h.Owner, ok = vals[0].(common.Address); !ok {
		return h, errors.New("zi0: noncanonical ZI0 owner getter type")
	}
	if h.Store, ok = vals[1].(common.Address); !ok {
		return h, errors.New("zi0: noncanonical ZI0 store getter type")
	}
	content, ok := vals[2].([32]byte)
	if !ok {
		return h, errors.New("zi0: noncanonical ZI0 content getter type")
	}
	h.Content = common.Hash(content)
	if h.Length, ok = vals[3].(uint32); !ok {
		return h, errors.New("zi0: noncanonical ZI0 length getter type")
	}
	if h.Phase, ok = vals[4].(uint8); !ok {
		return h, errors.New("zi0: noncanonical ZI0 phase getter type")
	}
	uint32Fields := []*uint32{&h.EOCD, &h.CDOffset, &h.CDSize, &h.Count, &h.NextEntry, &h.CDCursor}
	for i, target := range uint32Fields {
		value, valid := vals[5+i].(uint32)
		if !valid {
			return h, fmt.Errorf("zi0: noncanonical ZI0 %s getter type", names[5+i])
		}
		*target = value
	}
	rolling, ok := vals[11].([32]byte)
	if !ok {
		return h, errors.New("zi0: noncanonical ZI0 rolling getter type")
	}
	finalRoot, ok := vals[12].([32]byte)
	if !ok {
		return h, errors.New("zi0: noncanonical ZI0 final-root getter type")
	}
	h.Rolling, h.FinalRoot = common.Hash(rolling), common.Hash(finalRoot)
	if h.Address == (common.Address{}) || s.state.GetCodeHash(h.Address) != s.zi0Hash || h.Owner != s.owner || h.Store != s.as0Address || h.Content == (common.Hash{}) || h.Length != s.length || h.Phase > 2 || h.Count > MaxEntries || h.CDSize > MaxCD || h.NextEntry > h.Count {
		return IndexHead{GasUsed: h.GasUsed}, errors.New("zi0: ZI0 getters violate bound identity, phase, or caps")
	}
	if h.Phase == 0 {
		if h.EOCD != 0 || h.CDOffset != 0 || h.CDSize != 0 || h.Count != 0 || h.NextEntry != 0 || h.CDCursor != 0 || h.Rolling != (common.Hash{}) || h.FinalRoot != (common.Hash{}) {
			return IndexHead{GasUsed: h.GasUsed}, errors.New("zi0: BOUND index has staging or final metadata")
		}
		return h, nil
	}
	cdEnd := uint64(h.CDOffset) + uint64(h.CDSize)
	if h.Length < 22 || cdEnd != uint64(h.EOCD) || uint64(h.EOCD)+22 > uint64(h.Length) || (h.Count == 0) != (h.CDSize == 0) || h.CDCursor < h.CDOffset || uint64(h.CDCursor) > cdEnd || h.Rolling == (common.Hash{}) || h.FinalRoot != (common.Hash{}) && h.Phase != 2 {
		return IndexHead{GasUsed: h.GasUsed}, errors.New("zi0: ZI0 directory/cursor/root metadata is noncanonical")
	}
	if h.NextEntry == 0 && h.CDCursor != h.CDOffset {
		return IndexHead{GasUsed: h.GasUsed}, errors.New("zi0: unscanned ZI0 cursor moved")
	}
	if h.Phase == 2 && (h.NextEntry != h.Count || uint64(h.CDCursor) != cdEnd || h.FinalRoot == (common.Hash{}) || h.FinalRoot != h.Rolling) {
		return IndexHead{GasUsed: h.GasUsed}, errors.New("zi0: FINAL index is incomplete or has mismatched root")
	}
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
	if (s.indexAddress == (common.Address{})) != (s.indexContent == (common.Hash{})) {
		return common.Hash{}, errors.New("zi0: inconsistent verified index binding")
	}
	return s.indexContent, nil
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
		if strings.HasPrefix(name, ".durable-head-") {
			if x.Type()&os.ModeSymlink != 0 || !fi.Mode().IsRegular() {
				return false, fmt.Errorf("zi0: publication temp %q must be a real regular file", name)
			}
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
