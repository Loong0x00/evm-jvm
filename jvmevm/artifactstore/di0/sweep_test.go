package di0

import (
	"reflect"
	"testing"

	"github.com/ethereum/go-ethereum/common"
)

func TestDI0HarnessCompleteQ1Through128Sweep64Headers(t *testing.T) {
	owner := common.HexToAddress("0xd1004001")
	baseline := di0HarnessHeadNoGas(di0HarnessRunEmptyHeaders(t, 64, 1, owner))
	for units := uint16(2); units <= MaxStepUnits; units++ {
		got := di0HarnessHeadNoGas(di0HarnessRunEmptyHeaders(t, 64, units, owner))
		if !reflect.DeepEqual(got, baseline) {
			t.Fatalf("q%d changed same-binding final state", units)
		}
	}
}
