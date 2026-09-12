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

// Head reads every published route from copied EVM state. It deliberately
// revalidates lifecycle geometry rather than treating the Session route cache
// or a manifest as an authority.
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
	if s.state.GetCodeHash(cb0EngineAddress) != s.engineHash || s.engineHash != cb0VFSCode || s.state.GetNonce(cb0EngineAddress) != 0 {
		return h, errors.New("cb0: fixed Java engine route is not canonical")
	}
	if s.as0Hash != cb0AS0Code || s.zi0Hash != cb0ZI0Code || s.di0Hash != cb0DI0Code || s.coordHash != common.HexToHash("0x"+cb0RuntimeKeccak) {
		return h, errors.New("cb0: dependency code pin differs")
	}
	h.StateRoot = s.root
	a, err := s.cb0ASHead(gas)
	h.AS0, h.GasUsed = a, a.GasUsed
	if err != nil {
		return h, err
	}
	if s.as0Address != crypto.CreateAddress(s.owner, 0) {
		return h, errors.New("cb0: AS0 route differs from ordinary CREATE")
	}
	if s.indexAddress == (common.Address{}) {
		if len(s.decoders) != 0 || s.coordinator != (common.Address{}) || s.packageRoot != (common.Hash{}) || s.javaHead != (common.Hash{}) || s.state.GetNonce(s.owner) != 1 {
			return h, errors.New("cb0: absent index has active dependent routes")
		}
		return h, nil
	}
	if s.indexAddress != crypto.CreateAddress(s.owner, 1) || len(s.decoders) > int(MaxResources) {
		return h, errors.New("cb0: index or decoder route is noncanonical")
	}
	i, err := s.cb0IndexHead(gas)
	h.Index = i
	h.GasUsed += i.GasUsed
	if err != nil {
		return h, err
	}
	if !a.Sealed || i.Owner != a.Owner || i.Store != a.Controller || i.Content != a.ContentCommitment || i.Length != a.DeclaredLength {
		return h, errors.New("cb0: AS0 and ZI0 bindings differ")
	}
	seenDecoders := make(map[common.Address]struct{}, len(s.decoders))
	for at, address := range s.decoders {
		if address == (common.Address{}) || address != crypto.CreateAddress(s.owner, uint64(at)+2) {
			return h, errors.New("cb0: decoder route differs from ordinary CREATE")
		}
		if _, duplicate := seenDecoders[address]; duplicate {
			return h, errors.New("cb0: duplicate decoder route")
		}
		seenDecoders[address] = struct{}{}
		d, e := s.cb0DecoderHead(address, gas)
		h.Decoders = append(h.Decoders, d)
		h.GasUsed += d.GasUsed
		if e != nil {
			return h, e
		}
		if i.Phase != 2 || d.Index != i.Address || d.Store != a.Controller || d.IndexRoot != i.FinalRoot || d.Content != i.Content {
			return h, errors.New("cb0: ZI0 and DI0 bindings differ")
		}
	}
	wantNonce := uint64(2 + len(s.decoders))
	if s.coordinator == (common.Address{}) {
		if s.packageRoot != (common.Hash{}) || s.javaHead != (common.Hash{}) || s.state.GetNonce(s.owner) != wantNonce {
			return h, errors.New("cb0: absent coordinator has active package state")
		}
		return h, nil
	}
	if s.coordinator != crypto.CreateAddress(s.owner, wantNonce) || s.state.GetNonce(s.owner) != wantNonce+1 || s.state.GetCodeHash(s.coordinator) != s.coordHash || s.coordHash != common.HexToHash("0x"+cb0RuntimeKeccak) {
		return h, errors.New("cb0: coordinator route or code pin differs")
	}
	co, err := s.cb0CoordinatorHead(gas)
	h.Coordinator = co
	h.GasUsed += co.GasUsed
	if err != nil {
		return h, err
	}
	if i.Phase != 2 || co.FinalIndexRoot != i.FinalRoot || co.FinalIndex != i.Address || co.PackageRoot != s.packageRoot {
		return h, errors.New("cb0: coordinator/index binding differs")
	}
	var total uint32
	seenNames := make(map[string]struct{}, co.ClassCount)
	used := make(map[common.Address]struct{}, co.ClassCount)
	for _, class := range co.Classes {
		if _, exists := seenDecoders[class.Decoder]; !exists {
			return h, errors.New("cb0: coordinator references a decoder not created in this world")
		}
		if _, duplicate := used[class.Decoder]; duplicate {
			return h, errors.New("cb0: coordinator repeats a decoder")
		}
		used[class.Decoder] = struct{}{}
		if _, duplicate := seenNames[string(class.RawName)]; duplicate {
			return h, errors.New("cb0: coordinator repeats a raw class name")
		}
		seenNames[string(class.RawName)] = struct{}{}
		if !cb0RawClassName(class.RawName) {
			return h, errors.New("cb0: coordinator class name is invalid")
		}
		var decoder *di0.DI0Head
		for at := range h.Decoders {
			if h.Decoders[at].Address == class.Decoder {
				decoder = &h.Decoders[at]
				break
			}
		}
		if decoder == nil || decoder.Phase != 4 || decoder.NameHash != crypto.Keccak256Hash(class.RawName) || decoder.IndexRoot != i.FinalRoot || decoder.FinalRoot != class.ResourceRoot || decoder.PlainSize != class.ClassSize {
			return h, errors.New("cb0: coordinator class binding differs from FINAL DI0")
		}
		if MaxClassBytes-total < class.ClassSize {
			return h, errors.New("cb0: coordinator class total overflows cap")
		}
		total += class.ClassSize
	}
	if total != co.TotalClassBytes {
		return h, errors.New("cb0: coordinator total differs from class bindings")
	}
	java, usedGas, err := s.cb0JavaHead(co.InstanceID, gas)
	h.Java = java
	h.GasUsed += usedGas
	if err != nil {
		return h, err
	}
	if java.Epoch == 0 {
		if s.javaHead != (common.Hash{}) {
			return h, errors.New("cb0: published checkpoint lacks an EVM Java head")
		}
		return h, nil
	}
	if java.Owner != s.coordinator || java.CheckpointRoot != s.javaHead || java.RuntimeCodeHash != s.engineHash || java.MachineStateRoot == (common.Hash{}) || java.VFSStateRoot == (common.Hash{}) || java.SeedRoot == (common.Hash{}) || java.ArtifactRoot == (common.Hash{}) || java.ConfigRoot == (common.Hash{}) || java.Lifecycle < 1 || java.Lifecycle > 3 {
		return h, errors.New("cb0: active Java head is not canonical")
	}
	return h, nil
}

func cb0RawClassName(name []byte) bool {
	if len(name) <= len(".class") || len(name) > int(MaxRawNameBytes) || string(name[len(name)-6:]) != ".class" {
		return false
	}
	for _, c := range name[:len(name)-6] {
		if c == 0 || c == '\\' || c == '.' {
			return false
		}
	}
	return true
}

func (s *Session) cb0ASHead(gas uint64) (as0.Head, error) {
	var h as0.Head
	names := []string{"owner", "declaredLength", "cursor", "isSealed", "pageCount", "chainCommitment", "contentCommitment", "PAGE_SIZE", "MAX_PAGES", "MAX_LENGTH"}
	vals := make([]interface{}, len(names))
	for n, name := range names {
		out, used, err := s.cb0View(s.as0Address, s.as0ABI, name, gas)
		h.GasUsed += used
		if err != nil {
			return h, err
		}
		v, err := s.as0ABI.Unpack(name, out)
		if err != nil || len(v) != 1 {
			return h, fmt.Errorf("cb0: malformed AS0 getter %s", name)
		}
		vals[n] = v[0]
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
	pages, ok := vals[4].(*big.Int)
	if !ok || pages.Sign() < 0 || !pages.IsUint64() || pages.Uint64() > uint64(as0.MaxPages) {
		return h, errors.New("cb0: AS0 page count")
	}
	h.PageCount = uint32(pages.Uint64())
	chain, ok1 := vals[5].([32]byte)
	content, ok2 := vals[6].([32]byte)
	h.PageSize, ok = vals[7].(uint32)
	if !ok {
		return h, errors.New("cb0: AS0 page size type")
	}
	h.MaxPages, ok = vals[8].(uint32)
	if !ok {
		return h, errors.New("cb0: AS0 max pages type")
	}
	h.MaxLength, ok = vals[9].(uint32)
	if !ok || !ok1 || !ok2 {
		return h, errors.New("cb0: AS0 hash or limit type")
	}
	h.ChainCommitment, h.ContentCommitment = common.Hash(chain), common.Hash(content)
	h.Controller, h.RuntimeCodeHash, h.StateRoot = s.as0Address, s.as0Hash, s.root
	if h.Owner == (common.Address{}) || s.state.GetCodeHash(h.Controller) != s.as0Hash || h.Owner != s.owner || h.DeclaredLength != s.length || h.Cursor > h.DeclaredLength || h.PageSize != as0.PageSize || h.MaxPages != as0.MaxPages || h.MaxLength != as0.MaxLength || h.ChainCommitment == (common.Hash{}) {
		return h, errors.New("cb0: AS0 identity/cap differs")
	}
	covered := uint64(h.PageCount) * uint64(as0.PageSize)
	if covered < uint64(h.Cursor) || covered > uint64(h.Cursor)+uint64(as0.PageSize-1) || (h.Cursor != h.DeclaredLength && h.Cursor%as0.PageSize != 0) {
		return h, errors.New("cb0: AS0 page/cursor geometry differs")
	}
	wantPages := (h.DeclaredLength + as0.PageSize - 1) / as0.PageSize
	if h.Sealed {
		if h.Cursor != h.DeclaredLength || h.PageCount != wantPages || h.ContentCommitment == (common.Hash{}) {
			return h, errors.New("cb0: AS0 sealed shape differs")
		}
	} else if h.ContentCommitment != (common.Hash{}) {
		return h, errors.New("cb0: AS0 content exists before seal")
	}
	if s.state.GetNonce(h.Controller) != uint64(h.PageCount)+1 {
		return h, errors.New("cb0: AS0 page creator nonce differs")
	}
	for at := uint32(0); at < h.PageCount; at++ {
		address := crypto.CreateAddress(h.Controller, uint64(at)+1)
		code := s.state.GetCode(address)
		want := as0.PageSize
		if at+1 == h.PageCount {
			want = h.Cursor - at*as0.PageSize
		}
		if len(code) == 0 || code[0] != 0 || uint32(len(code)-1) != want || s.state.GetCodeHash(address) != crypto.Keccak256Hash(code) {
			return h, errors.New("cb0: AS0 page code or geometry differs")
		}
	}
	if len(s.state.GetCode(crypto.CreateAddress(h.Controller, uint64(h.PageCount)+1))) != 0 {
		return h, errors.New("cb0: unexpected AS0 child route occupied")
	}
	return h, nil
}

func (s *Session) cb0IndexHead(gas uint64) (zi0.IndexHead, error) {
	var h zi0.IndexHead
	names := []string{"owner", "store", "content", "length", "phase", "eocd", "cdOffset", "cdSize", "count", "nextEntry", "cdCursor", "rolling", "finalRoot"}
	vals := make([]interface{}, len(names))
	for n, name := range names {
		out, used, err := s.cb0View(s.indexAddress, s.zi0ABI, name, gas)
		h.GasUsed += used
		if err != nil {
			return h, err
		}
		v, err := s.zi0ABI.Unpack(name, out)
		if err != nil || len(v) != 1 {
			return h, fmt.Errorf("cb0: malformed ZI0 getter %s", name)
		}
		vals[n] = v[0]
	}
	var ok bool
	h.Owner, ok = vals[0].(common.Address)
	if !ok {
		return h, errors.New("cb0: ZI0 owner type")
	}
	h.Store, ok = vals[1].(common.Address)
	if !ok {
		return h, errors.New("cb0: ZI0 store type")
	}
	content, ok := vals[2].([32]byte)
	if !ok {
		return h, errors.New("cb0: ZI0 content type")
	}
	h.Content = common.Hash(content)
	h.Length, ok = vals[3].(uint32)
	if !ok {
		return h, errors.New("cb0: ZI0 length type")
	}
	h.Phase, ok = vals[4].(uint8)
	if !ok {
		return h, errors.New("cb0: ZI0 phase type")
	}
	for at, p := range []*uint32{&h.EOCD, &h.CDOffset, &h.CDSize, &h.Count, &h.NextEntry, &h.CDCursor} {
		v, valid := vals[5+at].(uint32)
		if !valid {
			return h, errors.New("cb0: ZI0 scalar type")
		}
		*p = v
	}
	rolling, ok1 := vals[11].([32]byte)
	final, ok2 := vals[12].([32]byte)
	if !ok1 || !ok2 {
		return h, errors.New("cb0: ZI0 root type")
	}
	h.Rolling, h.FinalRoot = common.Hash(rolling), common.Hash(final)
	h.Address, h.RuntimeCodeHash = s.indexAddress, s.zi0Hash
	if h.Address == (common.Address{}) || s.state.GetCodeHash(h.Address) != s.zi0Hash || h.Owner != s.owner || h.Store != s.as0Address || h.Content == (common.Hash{}) || h.Length != s.length || h.Phase > 2 || h.Count > zi0.MaxEntries || h.CDSize > zi0.MaxCD || h.NextEntry > h.Count {
		return h, errors.New("cb0: ZI0 identity/cap differs")
	}
	if h.Phase == 0 {
		if h.EOCD != 0 || h.CDOffset != 0 || h.CDSize != 0 || h.Count != 0 || h.NextEntry != 0 || h.CDCursor != 0 || h.Rolling != (common.Hash{}) || h.FinalRoot != (common.Hash{}) {
			return h, errors.New("cb0: ZI0 bound shape differs")
		}
		return h, nil
	}
	end := uint64(h.CDOffset) + uint64(h.CDSize)
	if h.Length < 22 || end != uint64(h.EOCD) || uint64(h.EOCD)+22 > uint64(h.Length) || (h.Count == 0) != (h.CDSize == 0) || h.CDCursor < h.CDOffset || uint64(h.CDCursor) > end || h.Rolling == (common.Hash{}) || (h.FinalRoot != (common.Hash{}) && h.Phase != 2) || (h.NextEntry == 0 && h.CDCursor != h.CDOffset) {
		return h, errors.New("cb0: ZI0 staging shape differs")
	}
	if h.Phase == 2 && (h.NextEntry != h.Count || uint64(h.CDCursor) != end || h.FinalRoot == (common.Hash{}) || h.FinalRoot != h.Rolling) {
		return h, errors.New("cb0: ZI0 final shape differs")
	}
	return h, nil
}

func cb0CanonicalPackedRecord(p [32]byte) bool {
	for _, b := range p[:7] {
		if b != 0 {
			return false
		}
	}
	return p[7]&0xf8 == 0
}

func (s *Session) cb0DecoderHead(address common.Address, gas uint64) (di0.DI0Head, error) {
	var h di0.DI0Head
	names := []string{"owner", "index", "store", "indexRoot", "content", "packedRecord", "nameHash", "binding", "outputRolling", "publicationRolling", "finalRoot", "entryIndex", "dataStart", "compressedSize", "plainSize", "expectedCRC", "outputCount", "inputByte", "work", "crc", "pendingLength", "pendingDistance", "inputBit", "method", "phase", "blockMode", "blockFinal", "fixedBlock", "publishedPages"}
	vals := make([]interface{}, len(names))
	for n, name := range names {
		out, used, err := s.cb0View(address, s.di0ABI, name, gas)
		h.GasUsed += used
		if err != nil {
			return h, err
		}
		v, err := s.di0ABI.Unpack(name, out)
		if err != nil || len(v) != 1 {
			return h, fmt.Errorf("cb0: malformed DI0 getter %s", name)
		}
		vals[n] = v[0]
	}
	var ok bool
	h.Owner, ok = vals[0].(common.Address)
	if !ok {
		return h, errors.New("cb0: DI0 owner type")
	}
	h.Index, ok = vals[1].(common.Address)
	if !ok {
		return h, errors.New("cb0: DI0 index type")
	}
	h.Store, ok = vals[2].(common.Address)
	if !ok {
		return h, errors.New("cb0: DI0 store type")
	}
	for at, p := range []*common.Hash{&h.IndexRoot, &h.Content, &h.PackedRecord, &h.NameHash, &h.Binding, &h.OutputRolling, &h.PublicationRolling, &h.FinalRoot} {
		v, valid := vals[3+at].([32]byte)
		if !valid {
			return h, errors.New("cb0: DI0 hash type")
		}
		*p = common.Hash(v)
	}
	for at, p := range []*uint32{&h.EntryIndex, &h.DataStart, &h.CompressedSize, &h.PlainSize, &h.ExpectedCRC, &h.OutputCount, &h.InputByte, &h.Work, &h.CRC} {
		v, valid := vals[11+at].(uint32)
		if !valid {
			return h, errors.New("cb0: DI0 scalar type")
		}
		*p = v
	}
	h.PendingLength, ok = vals[20].(uint16)
	if !ok {
		return h, errors.New("cb0: DI0 pending length type")
	}
	h.PendingDistance, ok = vals[21].(uint16)
	if !ok {
		return h, errors.New("cb0: DI0 pending distance type")
	}
	for at, p := range []*uint8{&h.InputBit, &h.Method, &h.Phase, &h.BlockMode} {
		v, valid := vals[22+at].(uint8)
		if !valid {
			return h, errors.New("cb0: DI0 byte type")
		}
		*p = v
	}
	h.BlockFinal, ok = vals[26].(bool)
	if !ok {
		return h, errors.New("cb0: DI0 block final type")
	}
	h.FixedBlock, ok = vals[27].(bool)
	if !ok {
		return h, errors.New("cb0: DI0 fixed type")
	}
	h.PublishedPages, ok = vals[28].(uint8)
	if !ok {
		return h, errors.New("cb0: DI0 pages type")
	}
	h.Address, h.RuntimeCodeHash = address, s.di0Hash
	zero := common.Hash{}
	if h.Address == (common.Address{}) || s.state.GetCodeHash(h.Address) != s.di0Hash || h.Owner != s.owner || h.Index != s.indexAddress || h.Store != s.as0Address || h.IndexRoot == zero || h.Content == zero || !cb0CanonicalPackedRecord([32]byte(h.PackedRecord)) || h.NameHash == zero || h.Binding == zero || h.OutputRolling == zero || h.EntryIndex >= zi0.MaxEntries || h.PlainSize > di0.MaxOutput || uint64(h.DataStart)+uint64(h.CompressedSize) > uint64(s.length) || h.OutputCount > h.PlainSize || h.InputByte < h.DataStart || uint64(h.InputByte) > uint64(h.DataStart)+uint64(h.CompressedSize) || h.InputBit > 7 || (h.Method != 0 && h.Method != 8) || h.Phase < 1 || h.Phase > 4 || h.BlockMode > 2 || h.PublishedPages > di0.MaxOutputPages {
		return h, errors.New("cb0: DI0 identity/cap differs")
	}
	switch {
	case h.Method == 0:
		if h.BlockMode != 0 || h.InputBit != 0 || h.PendingLength != 0 || h.PendingDistance != 0 || h.FixedBlock || h.BlockFinal {
			return h, errors.New("cb0: DI0 method0 state differs")
		}
	case h.BlockMode == 1:
		if h.PendingDistance != 0 || h.FixedBlock || h.InputBit != 0 || (h.Phase == 1 && h.PendingLength == 0) {
			return h, errors.New("cb0: DI0 stored pending state differs")
		}
	case h.BlockMode == 0:
		if h.PendingLength != 0 || h.PendingDistance != 0 {
			return h, errors.New("cb0: DI0 header pending state differs")
		}
	default:
		if h.PendingLength > 258 || h.PendingDistance > uint16(di0.MaxHistory) || (h.PendingLength == 0) != (h.PendingDistance == 0) || (h.PendingLength > 0 && uint32(h.PendingDistance) > h.OutputCount) {
			return h, errors.New("cb0: DI0 Huffman pending state differs")
		}
	}
	if h.Phase >= 2 && (h.InputByte != h.DataStart+h.CompressedSize || h.InputBit != 0 || h.PendingLength != 0 || h.OutputCount != h.PlainSize || h.CRC^0xffffffff != h.ExpectedCRC) {
		return h, errors.New("cb0: DI0 completed cursor/CRC differs")
	}
	pages := uint8((h.PlainSize + di0.OutputPageSize - 1) / di0.OutputPageSize)
	if h.Phase == 1 && (h.FinalRoot != zero || h.PublicationRolling != zero || h.PublishedPages != 0) {
		return h, errors.New("cb0: DI0 decoding publication differs")
	}
	if h.Phase >= 2 && h.PublicationRolling == zero {
		return h, errors.New("cb0: DI0 complete publication root absent")
	}
	if h.Phase == 2 && (h.OutputCount != h.PlainSize || h.FinalRoot != zero || h.PublishedPages != 0) {
		return h, errors.New("cb0: DI0 verified shape differs")
	}
	if h.Phase == 3 && (h.PublishedPages == 0 || h.PublishedPages >= pages || h.FinalRoot != zero) {
		return h, errors.New("cb0: DI0 publishing shape differs")
	}
	if h.Phase == 4 && (h.OutputCount != h.PlainSize || h.PublishedPages != pages || h.FinalRoot == zero) {
		return h, errors.New("cb0: DI0 final shape differs")
	}
	if s.state.GetNonce(h.Address) != uint64(h.PublishedPages)+1 {
		return h, errors.New("cb0: DI0 output creator nonce differs")
	}
	for at := uint8(0); at < h.PublishedPages; at++ {
		pageAddress := crypto.CreateAddress(h.Address, uint64(at)+1)
		code := s.state.GetCode(pageAddress)
		want := di0.OutputPageSize
		if at+1 == pages {
			want = h.OutputCount - uint32(at)*di0.OutputPageSize
		}
		if len(code) == 0 || code[0] != 0 || uint32(len(code)-1) != want || s.state.GetCodeHash(pageAddress) != crypto.Keccak256Hash(code) {
			return h, errors.New("cb0: DI0 output page geometry differs")
		}
		if h.Phase == 4 {
			out, used, err := s.cb0View(h.Address, s.di0ABI, "page", gas, at)
			h.GasUsed += used
			if err != nil {
				return h, err
			}
			v, err := s.di0ABI.Unpack("page", out)
			if err != nil || len(v) != 4 {
				return h, errors.New("cb0: malformed final DI0 page")
			}
			gotAddress, aok := v[0].(common.Address)
			gotHash, hok := v[1].([32]byte)
			commitment, cok := v[2].([32]byte)
			length, lok := v[3].(uint32)
			if !aok || !hok || !cok || !lok || gotAddress != pageAddress || common.Hash(gotHash) != s.state.GetCodeHash(pageAddress) || common.Hash(commitment) == zero || length != want {
				return h, errors.New("cb0: DI0 final page metadata differs")
			}
		}
	}
	if len(s.state.GetCode(crypto.CreateAddress(h.Address, uint64(h.PublishedPages)+1))) != 0 {
		return h, errors.New("cb0: unexpected DI0 child route occupied")
	}
	return h, nil
}

func (s *Session) cb0CoordinatorHead(gas uint64) (CoordinatorHead, error) {
	var h CoordinatorHead
	names := []string{"owner", "finalIndex", "finalIndexRoot", "packageRoot", "instanceId", "totalClassBytes", "classCount"}
	vals := make([]interface{}, len(names))
	for n, name := range names {
		out, used, err := s.cb0View(s.coordinator, s.coordABI, name, gas)
		h.GasUsed += used
		if err != nil {
			return h, err
		}
		v, err := s.coordABI.Unpack(name, out)
		if err != nil || len(v) != 1 {
			return h, fmt.Errorf("cb0: malformed coordinator getter %s", name)
		}
		vals[n] = v[0]
	}
	var ok bool
	h.Owner, ok = vals[0].(common.Address)
	if !ok {
		return h, errors.New("cb0: coordinator owner type")
	}
	h.FinalIndex, ok = vals[1].(common.Address)
	if !ok {
		return h, errors.New("cb0: coordinator final index type")
	}
	for at, p := range []*common.Hash{&h.FinalIndexRoot, &h.PackageRoot, &h.InstanceID} {
		v, valid := vals[2+at].([32]byte)
		if !valid {
			return h, errors.New("cb0: coordinator root type")
		}
		*p = common.Hash(v)
	}
	h.TotalClassBytes, ok = vals[5].(uint32)
	if !ok {
		return h, errors.New("cb0: coordinator total type")
	}
	h.ClassCount, ok = vals[6].(uint8)
	if !ok {
		return h, errors.New("cb0: coordinator count type")
	}
	h.Address, h.RuntimeCodeHash = s.coordinator, s.coordHash
	if h.Owner != s.owner || h.FinalIndex != s.indexAddress || h.FinalIndexRoot == (common.Hash{}) || h.PackageRoot == (common.Hash{}) || h.InstanceID == (common.Hash{}) || h.ClassCount == 0 || h.ClassCount > MaxResources || h.ClassCount > uint8(len(s.decoders)) || h.TotalClassBytes == 0 || h.TotalClassBytes > MaxClassBytes {
		return h, errors.New("cb0: coordinator identity/cap differs")
	}
	for at := uint8(0); at < h.ClassCount; at++ {
		out, used, err := s.cb0View(s.coordinator, s.coordABI, "classBinding", gas, at)
		h.GasUsed += used
		if err != nil {
			return h, err
		}
		v, err := s.coordABI.Unpack("classBinding", out)
		if err != nil || len(v) != 4 {
			return h, errors.New("cb0: malformed coordinator binding")
		}
		address, aok := v[0].(common.Address)
		name, nok := v[1].([]byte)
		root, rok := v[2].([32]byte)
		size, sok := v[3].(uint32)
		if !aok || !nok || !rok || !sok || address == (common.Address{}) || !cb0RawClassName(name) || common.Hash(root) == (common.Hash{}) || size == 0 || size > MaxClassBytes {
			return h, errors.New("cb0: coordinator binding shape differs")
		}
		h.Classes = append(h.Classes, CoordinatorClass{address, append([]byte(nil), name...), common.Hash(root), size})
	}
	return h, nil
}

func (s *Session) cb0JavaHead(instance common.Hash, gas uint64) (vfs0a.Head, uint64, error) {
	a, err := vfs0a.ABI()
	if err != nil {
		return vfs0a.Head{}, 0, err
	}
	out, used, err := s.cb0View(cb0EngineAddress, a, "head", gas, instance)
	if err != nil {
		return vfs0a.Head{}, used, err
	}
	var h vfs0a.Head
	if err = a.UnpackIntoInterface(&h, "head", out); err != nil {
		return h, used, err
	}
	if h.Epoch == 0 {
		if h != (vfs0a.Head{}) {
			return h, used, errors.New("cb0: noncanonical absent Java engine head")
		}
		return h, used, nil
	}
	return h, used, nil
}
