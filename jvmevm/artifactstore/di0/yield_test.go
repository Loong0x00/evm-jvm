package di0

import (
	"reflect"
	"testing"

	"github.com/ethereum/go-ethereum/common"
)

func di0HarnessRunEmptyHeaders(t testing.TB, blocks int, units uint16, owner common.Address) Head {
	t.Helper()
	stream := di0HarnessEmptyDynamic(blocks)
	z := di0HarnessZIPPayload([]byte("headers.deflate"), nil, stream, 8)
	s, _ := di0HarnessPrepared(t, z, owner)
	defer s.Close()
	h := di0HarnessDecode(t, s, units)
	if h.Decoder.Phase != 4 || h.Decoder.OutputCount != 0 || h.Decoder.PublishedPages != 0 || h.Decoder.FinalRoot == (common.Hash{}) || h.Decoder.Work != uint32(blocks*2) {
		t.Fatalf("headers=%d units=%d final=%+v", blocks, units, h.Decoder)
	}
	return h
}

func TestDI0HarnessBudgetYield64And129DynamicHeaders(t *testing.T) {
	// Each empty dynamic block costs two bounded actions (header + EOB). These
	// retain the production requested q128 rather than reducing the request to
	// hide an ordinary-gas OOG. Actual work comes back from EVM getters.
	for _, blocks := range []int{64, 129} {
		di0HarnessRunEmptyHeaders(t, blocks, 128, common.BytesToAddress([]byte{0xd1, 0x20, byte(blocks)}))
	}
}

func TestDI0HarnessSameBindingQ1Q128StateEquality(t *testing.T) {
	owner := common.HexToAddress("0xd1002001")
	one := di0HarnessRunEmptyHeaders(t, 64, 1, owner)
	max := di0HarnessRunEmptyHeaders(t, 64, 128, owner)
	if !reflect.DeepEqual(di0HarnessHeadNoGas(one), di0HarnessHeadNoGas(max)) {
		t.Fatalf("same binding differs by grouping:\nq1=%+v\nq128=%+v", one, max)
	}
}
