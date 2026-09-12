package cb0

import (
	"errors"
	"fmt"
	"math/big"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/as0"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/di0"
	"github.com/ethereum/go-ethereum/jvmevm/artifactstore/zi0"
	"github.com/ethereum/go-ethereum/jvmevm/localcontinuation/vfs0a"
)

// Head reads every published route from copied EVM state. The returned fields
// are never reconstructed from ZIP/class data or manifest claims.
func (s *Session) Head(gas uint64) (Head, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var h Head
	if err := s.cb0Usable(); err != nil {
		return h, err
	}
	if err := s.cb0Gas(gas); err != nil {
		return h, err
	}
	h.StateRoot = s.root
	as, err := s.cb0ASHead(gas)
	h.AS0 = as
	h.GasUsed += as.GasUsed
	if err != nil {
		return h, err
	}
	if s.indexAddress == (common.Address{}) {
		if len(s.decoders) != 0 || s.coordinator != (common.Address{}) || s.state.GetNonce(s.owner) != 1 {
			return h, errors.New("cb0: absent index disagrees with ordinary CREATE nonce")
		}
		return h, nil
	}
	wantNonce := uint64(2 + len(s.decoders))
	if s.coordinator != (common.Address{}) {
		wantNonce++
	}
	if s.state.GetNonce(s.owner) != wantNonce || s.indexAddress != crypto.CreateAddress(s.owner, 1) {
		return h, errors.New("cb0: controller routes disagree with ordinary CREATE nonce")
	}
	ix, err := s.cb0IndexHead(gas)
	h.Index = ix
	h.GasUsed += ix.GasUsed
	if err != nil {
		return h, err
	}
	for _, address := range s.decoders {
		d, err := s.cb0DecoderHead(address, gas)
		h.Decoders = append(h.Decoders, d)
		h.GasUsed += d.GasUsed
		if err != nil {
			return h, err
		}
	}
	if s.coordinator == (common.Address{}) {
		return h, nil
	}
	co, err := s.cb0CoordinatorHead(gas)
	h.Coordinator = co
	h.GasUsed += co.GasUsed
	if err != nil {
		return h, err
	}
	if ix.Phase != 2 || co.FinalIndexRoot != ix.FinalRoot || len(h.Decoders) != len(co.Classes) {
		return h, errors.New("cb0: coordinator/index/decoder bindings differ")
	}
	var classTotal uint32
	for i, class := range co.Classes {
		decoder := h.Decoders[i]
		if decoder.Phase != 4 || decoder.IndexRoot != ix.FinalRoot || decoder.FinalRoot != class.ResourceRoot || decoder.PlainSize != class.ClassSize {
			return h, errors.New("cb0: coordinator class binding differs from FINAL DI0")
		}
		if MaxClassBytes-classTotal < class.ClassSize {
			return h, errors.New("cb0: coordinator class total overflow")
		}
		classTotal += class.ClassSize
	}
	if classTotal != co.TotalClassBytes {
		return h, errors.New("cb0: coordinator total differs from EVM class bindings")
	}
	java, used, err := s.cb0JavaHead(co.InstanceID, gas)
	h.Java = java
	h.GasUsed += used
	if err != nil {
		return h, err
	}
	if java.Epoch != 0 && (java.Owner != s.coordinator || (s.javaHead != (common.Hash{}) && java.CheckpointRoot != s.javaHead)) {
		return h, errors.New("cb0: Java anchor differs from published coordinator head")
	}
	if java.Epoch == 0 && s.javaHead != (common.Hash{}) {
		return h, errors.New("cb0: published Java blob lacks an EVM head")
	}
	return h, nil
}
func (s *Session) cb0ASHead(gas uint64) (as0.Head, error) {
	var h as0.Head
	names := []string{"owner", "declaredLength", "cursor", "isSealed", "pageCount", "chainCommitment", "contentCommitment", "PAGE_SIZE", "MAX_PAGES", "MAX_LENGTH"}
	vals := make([]interface{}, len(names))
	for i, n := range names {
		out, u, e := s.cb0View(s.as0Address, s.as0ABI, n, gas)
		h.GasUsed += u
		if e != nil {
			return h, e
		}
		v, e := s.as0ABI.Unpack(n, out)
		if e != nil || len(v) != 1 {
			return h, fmt.Errorf("cb0: malformed AS0 getter %s", n)
		}
		vals[i] = v[0]
	}
	var ok bool
	h.Owner, ok = vals[0].(common.Address)
	if !ok {
		return h, errors.New("cb0: AS0 owner type")
	}
	h.DeclaredLength, ok = vals[1].(uint32)
	if !ok {
		return h, errors.New("cb0: AS0 length type")
	}
	h.Cursor, ok = vals[2].(uint32)
	if !ok {
		return h, errors.New("cb0: AS0 cursor type")
	}
	h.Sealed, ok = vals[3].(bool)
	if !ok {
		return h, errors.New("cb0: AS0 seal type")
	}
	pc, ok := vals[4].(*big.Int)
	if !ok || !pc.IsUint64() || pc.Uint64() > uint64(as0.MaxPages) {
		return h, errors.New("cb0: AS0 page count")
	}
	h.PageCount = uint32(pc.Uint64())
	chain, o1 := vals[5].([32]byte)
	content, o2 := vals[6].([32]byte)
	h.PageSize, ok = vals[7].(uint32)
	if !ok {
		return h, errors.New("cb0: AS0 page size")
	}
	h.MaxPages, ok = vals[8].(uint32)
	if !ok {
		return h, errors.New("cb0: AS0 max pages")
	}
	h.MaxLength, ok = vals[9].(uint32)
	if !ok || !o1 || !o2 {
		return h, errors.New("cb0: AS0 hash type")
	}
	h.ChainCommitment, h.ContentCommitment = common.Hash(chain), common.Hash(content)
	h.Controller, h.RuntimeCodeHash, h.StateRoot = s.as0Address, s.as0Hash, s.root
	if h.Owner != s.owner || h.DeclaredLength != s.length || h.Cursor > h.DeclaredLength || h.PageSize != as0.PageSize || h.MaxPages != as0.MaxPages || h.MaxLength != as0.MaxLength || h.ChainCommitment == (common.Hash{}) {
		return h, errors.New("cb0: AS0 identity/cap differs")
	}
	return h, nil
}
func (s *Session) cb0IndexHead(gas uint64) (zi0.IndexHead, error) {
	var h zi0.IndexHead
	names := []string{"owner", "store", "content", "length", "phase", "eocd", "cdOffset", "cdSize", "count", "nextEntry", "cdCursor", "rolling", "finalRoot"}
	vals := make([]interface{}, len(names))
	for i, n := range names {
		out, u, e := s.cb0View(s.indexAddress, s.zi0ABI, n, gas)
		h.GasUsed += u
		if e != nil {
			return h, e
		}
		v, e := s.zi0ABI.Unpack(n, out)
		if e != nil || len(v) != 1 {
			return h, fmt.Errorf("cb0: malformed ZI0 getter %s", n)
		}
		vals[i] = v[0]
	}
	var ok bool
	h.Owner, ok = vals[0].(common.Address)
	if !ok {
		return h, errors.New("cb0: ZI0 owner")
	}
	h.Store, ok = vals[1].(common.Address)
	if !ok {
		return h, errors.New("cb0: ZI0 store")
	}
	content, o := vals[2].([32]byte)
	if !o {
		return h, errors.New("cb0: ZI0 content")
	}
	h.Content = common.Hash(content)
	h.Length, ok = vals[3].(uint32)
	if !ok {
		return h, errors.New("cb0: ZI0 length")
	}
	h.Phase, ok = vals[4].(uint8)
	if !ok {
		return h, errors.New("cb0: ZI0 phase")
	}
	dst := []*uint32{&h.EOCD, &h.CDOffset, &h.CDSize, &h.Count, &h.NextEntry, &h.CDCursor}
	for i, p := range dst {
		x, ok := vals[i+5].(uint32)
		if !ok {
			return h, errors.New("cb0: ZI0 scalar")
		}
		*p = x
	}
	roll, o1 := vals[11].([32]byte)
	final, o2 := vals[12].([32]byte)
	if !o1 || !o2 {
		return h, errors.New("cb0: ZI0 roots")
	}
	h.Rolling, h.FinalRoot = common.Hash(roll), common.Hash(final)
	h.Address, h.RuntimeCodeHash = s.indexAddress, s.zi0Hash
	if h.Owner != s.owner || h.Store != s.as0Address || h.Length != s.length || h.Phase > 2 || h.Count > zi0.MaxEntries {
		return h, errors.New("cb0: ZI0 identity/cap differs")
	}
	return h, nil
}
func (s *Session) cb0DecoderHead(address common.Address, gas uint64) (di0.DI0Head, error) {
	var h di0.DI0Head
	names := []string{"owner", "index", "store", "indexRoot", "content", "packedRecord", "nameHash", "binding", "outputRolling", "publicationRolling", "finalRoot", "entryIndex", "dataStart", "compressedSize", "plainSize", "expectedCRC", "outputCount", "inputByte", "work", "crc", "pendingLength", "pendingDistance", "inputBit", "method", "phase", "blockMode", "blockFinal", "fixedBlock", "publishedPages"}
	vals := make([]interface{}, len(names))
	for i, n := range names {
		out, u, e := s.cb0View(address, s.di0ABI, n, gas)
		h.GasUsed += u
		if e != nil {
			return h, e
		}
		v, e := s.di0ABI.Unpack(n, out)
		if e != nil || len(v) != 1 {
			return h, fmt.Errorf("cb0: malformed DI0 getter %s", n)
		}
		vals[i] = v[0]
	}
	var ok bool
	h.Owner, ok = vals[0].(common.Address)
	if !ok {
		return h, errors.New("cb0: DI0 owner")
	}
	h.Index, ok = vals[1].(common.Address)
	if !ok {
		return h, errors.New("cb0: DI0 index")
	}
	h.Store, ok = vals[2].(common.Address)
	if !ok {
		return h, errors.New("cb0: DI0 store")
	}
	hashes := []*common.Hash{&h.IndexRoot, &h.Content, &h.PackedRecord, &h.NameHash, &h.Binding, &h.OutputRolling, &h.PublicationRolling, &h.FinalRoot}
	for i, p := range hashes {
		x, ok := vals[i+3].([32]byte)
		if !ok {
			return h, errors.New("cb0: DI0 hash")
		}
		*p = common.Hash(x)
	}
	u32s := []*uint32{&h.EntryIndex, &h.DataStart, &h.CompressedSize, &h.PlainSize, &h.ExpectedCRC, &h.OutputCount, &h.InputByte, &h.Work, &h.CRC}
	for i, p := range u32s {
		x, ok := vals[11+i].(uint32)
		if !ok {
			return h, errors.New("cb0: DI0 scalar")
		}
		*p = x
	}
	h.PendingLength, ok = vals[20].(uint16)
	if !ok {
		return h, errors.New("cb0: DI0 pending length")
	}
	h.PendingDistance, ok = vals[21].(uint16)
	if !ok {
		return h, errors.New("cb0: DI0 pending distance")
	}
	u8s := []*uint8{&h.InputBit, &h.Method, &h.Phase, &h.BlockMode}
	for i, p := range u8s {
		x, ok := vals[22+i].(uint8)
		if !ok {
			return h, errors.New("cb0: DI0 byte")
		}
		*p = x
	}
	h.BlockFinal, ok = vals[26].(bool)
	if !ok {
		return h, errors.New("cb0: DI0 final")
	}
	h.FixedBlock, ok = vals[27].(bool)
	if !ok {
		return h, errors.New("cb0: DI0 fixed")
	}
	h.PublishedPages, ok = vals[28].(uint8)
	if !ok {
		return h, errors.New("cb0: DI0 pages")
	}
	h.Address, h.RuntimeCodeHash = address, s.di0Hash
	if h.Owner != s.owner || h.Index != s.indexAddress || h.Store != s.as0Address || h.PlainSize > di0.MaxOutput || h.Phase < 1 || h.Phase > 4 {
		return h, errors.New("cb0: DI0 identity/cap differs")
	}
	return h, nil
}
func (s *Session) cb0CoordinatorHead(gas uint64) (CoordinatorHead, error) {
	var h CoordinatorHead
	names := []string{"owner", "finalIndex", "finalIndexRoot", "packageRoot", "instanceId", "totalClassBytes", "classCount"}
	vals := make([]interface{}, len(names))
	for i, n := range names {
		out, u, e := s.cb0View(s.coordinator, s.coordABI, n, gas)
		h.GasUsed += u
		if e != nil {
			return h, e
		}
		v, e := s.coordABI.Unpack(n, out)
		if e != nil || len(v) != 1 {
			return h, fmt.Errorf("cb0: malformed coordinator getter %s", n)
		}
		vals[i] = v[0]
	}
	var ok bool
	h.Owner, ok = vals[0].(common.Address)
	if !ok {
		return h, errors.New("cb0: coordinator owner")
	}
	h.FinalIndex, ok = vals[1].(common.Address)
	if !ok {
		return h, errors.New("cb0: coordinator final index")
	}
	roots := []*common.Hash{&h.FinalIndexRoot, &h.PackageRoot, &h.InstanceID}
	for i, p := range roots {
		x, ok := vals[i+2].([32]byte)
		if !ok {
			return h, errors.New("cb0: coordinator root")
		}
		*p = common.Hash(x)
	}
	h.TotalClassBytes, ok = vals[5].(uint32)
	if !ok {
		return h, errors.New("cb0: coordinator total")
	}
	h.ClassCount, ok = vals[6].(uint8)
	if !ok {
		return h, errors.New("cb0: coordinator count")
	}
	h.Address, h.RuntimeCodeHash = s.coordinator, s.coordHash
	if h.Owner != s.owner || h.FinalIndex != s.indexAddress || h.PackageRoot != s.packageRoot || h.ClassCount == 0 || h.ClassCount > MaxResources || h.TotalClassBytes == 0 || h.TotalClassBytes > MaxClassBytes {
		return h, errors.New("cb0: coordinator identity/cap differs")
	}
	for i := uint8(0); i < h.ClassCount; i++ {
		out, u, e := s.cb0View(s.coordinator, s.coordABI, "classBinding", gas, i)
		h.GasUsed += u
		if e != nil {
			return h, e
		}
		v, e := s.coordABI.Unpack("classBinding", out)
		if e != nil || len(v) != 4 {
			return h, errors.New("cb0: malformed coordinator binding")
		}
		a, o1 := v[0].(common.Address)
		n, o2 := v[1].([]byte)
		r, o3 := v[2].([32]byte)
		size, o4 := v[3].(uint32)
		if !o1 || !o2 || !o3 || !o4 || a != s.decoders[i] || len(n) == 0 || len(n) > int(MaxRawNameBytes) || size == 0 || size > MaxClassBytes {
			return h, errors.New("cb0: coordinator binding differs")
		}
		h.Classes = append(h.Classes, CoordinatorClass{a, append([]byte(nil), n...), common.Hash(r), size})
	}
	return h, nil
}
func (s *Session) cb0JavaHead(instance common.Hash, gas uint64) (vfs0a.Head, uint64, error) {
	a, e := vfs0a.ABI()
	if e != nil {
		return vfs0a.Head{}, 0, e
	}
	out, u, e := s.cb0View(cb0EngineAddress, a, "head", gas, instance)
	if e != nil {
		return vfs0a.Head{}, u, e
	}
	var h vfs0a.Head
	if e = a.UnpackIntoInterface(&h, "head", out); e != nil {
		return h, u, e
	}
	if h.Epoch == 0 {
		if h != (vfs0a.Head{}) {
			return h, u, errors.New("cb0: noncanonical absent Java engine head")
		}
		return h, u, nil
	}
	if h.RuntimeCodeHash != s.engineHash {
		return h, u, errors.New("cb0: invalid Java engine head")
	}
	return h, u, nil
}
