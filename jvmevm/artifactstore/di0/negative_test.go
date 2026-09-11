package di0

import (
	"bytes"
	"compress/flate"
	"testing"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
)

func di0HarnessDeflate(t testing.TB, raw []byte) []byte {
	t.Helper()
	var b bytes.Buffer
	w, err := flate.NewWriter(&b, flate.DefaultCompression)
	if err != nil {
		t.Fatal(err)
	}
	if _, err = w.Write(raw); err != nil {
		t.Fatal(err)
	}
	if err = w.Close(); err != nil {
		t.Fatal(err)
	}
	return b.Bytes()
}

func TestDI0HarnessConstructorFailureRollbackAndSameChildRetry(t *testing.T) {
	z := di0HarnessZIP1(t, []byte("ctor"), []byte("value"), 0)
	owner := common.HexToAddress("0xd1003001")
	s, err := NewMemory(owner, uint32(len(z.raw)))
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()
	di0HarnessUpload(t, s, z.raw)
	h := di0HarnessFinishIndex(t, s)
	wrong := h.Index.FinalRoot
	wrong[0] ^= 1
	beforeRoot := s.state.Copy().IntermediateRoot(true)
	beforeNonce := s.state.GetNonce(owner)
	op, err := s.CreateDecoder(wrong, z.name, OrdinaryGas)
	if err == nil || op.GasUsed == 0 || op.StateRoot != (common.Hash{}) || op.CreatedAddress != (common.Address{}) || len(op.Logs) != 0 {
		t.Fatalf("wrong-root constructor op=%+v err=%v", op, err)
	}
	di0HarnessError(t, op, 3)
	if s.state.Copy().IntermediateRoot(true) != beforeRoot || s.state.GetNonce(owner) != beforeNonce || len(s.state.GetCode(crypto.CreateAddress(owner, beforeNonce))) != 0 {
		t.Fatal("failed decoder CREATE changed root/nonce/same-child route")
	}
	retry, err := s.CreateDecoder(h.Index.FinalRoot, z.name, OrdinaryGas)
	if err != nil || retry.CreatedAddress != crypto.CreateAddress(owner, beforeNonce) {
		t.Fatalf("same-child retry=%+v err=%v", retry, err)
	}
}

func TestDI0HarnessCRCNegativeExactSelectorAndRollback(t *testing.T) {
	// Metadata declares abc while the raw stream genuinely expands to abd. The
	// mismatch is produced and detected in EVM; host flate is fixture oracle only.
	z := di0HarnessZIPPayload([]byte("crc"), []byte("abc"), di0HarnessDeflate(t, []byte("abd")), 8)
	s, h := di0HarnessPrepared(t, z, common.HexToAddress("0xd1003002"))
	defer s.Close()
	before := di0HarnessHeadNoGas(h)
	op, err := s.Step(h.Decoder.Work, 128, OrdinaryGas)
	if err == nil || op.GasUsed == 0 || op.StateRoot != (common.Hash{}) || len(op.Logs) != 0 {
		t.Fatalf("CRC failure op=%+v err=%v", op, err)
	}
	di0HarnessError(t, op, 25)
	after, _ := s.Head(OrdinaryGas)
	if after.StateRoot != before.StateRoot || after.Decoder.Work != before.Decoder.Work || after.Decoder.OutputCount != 0 {
		t.Fatalf("CRC failure exposed speculative progress: before=%+v after=%+v", before.Decoder, after.Decoder)
	}
}

func TestDI0HarnessPublishCASAndBoundsExactSelectors(t *testing.T) {
	z := di0HarnessZIP1(t, []byte("pub"), bytes.Repeat([]byte{1}, 33), 0)
	s, _ := di0HarnessPrepared(t, z, common.HexToAddress("0xd1003003"))
	defer s.Close()
	h := di0HarnessDecode(t, s, 128)
	wrong := h.Decoder.PublicationRolling
	wrong[0] ^= 1
	op, err := s.Publish(h.Decoder.PublishedPages, wrong, 1, OrdinaryGas)
	if err == nil || op.StateRoot != (common.Hash{}) || len(op.Logs) != 0 {
		t.Fatalf("publish CAS op=%+v err=%v", op, err)
	}
	di0HarnessError(t, op, 28)
	op, err = s.Publish(h.Decoder.PublishedPages, h.Decoder.PublicationRolling, 0, OrdinaryGas)
	if err == nil || op.StateRoot != (common.Hash{}) {
		t.Fatalf("publish units op=%+v err=%v", op, err)
	}
	di0HarnessError(t, op, 29)
	di0HarnessPublish(t, s)
	r, err := s.Read(uint32(len(z.plain)), 1, OrdinaryGas)
	if err == nil || r.GasUsed == 0 {
		t.Fatalf("read bound result=%+v err=%v", r, err)
	}
}
