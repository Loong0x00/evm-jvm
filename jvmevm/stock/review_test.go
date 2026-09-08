package stock

import (
	"testing"

	"github.com/ethereum/go-ethereum/crypto"
)

// This exact review input formerly failed its final coordinator batch at 2M.
// Reusing validated CP offsets now must complete it without raising any budget.
func TestStockReviewAcceptedBoundaryResume(t *testing.T) {
	page := stockVerifyLoadArtifact(t, ArtifactPage)
	module := stockVerifyLoadArtifact(t, TinyJvmStepModule)
	coord := stockVerifyLoadArtifact(t, VMCoordinator)
	e := stockVerifyNewEnv(t)
	defer e.close()

	moduleAddr, _ := e.mustCreate(module.init, stockVerifyCreateGas)
	moduleHash := crypto.Keccak256Hash(e.state.StateDB.GetCode(moduleAddr))

	// A valid selected Code body at the 256-byte cap: 252 reachable nops,
	// ldc_w #511, ireturn. The base class has cp_count=12; appending 500
	// legal CONSTANT_Integer entries makes cp_count exactly 512. Entry #511
	// contains 243. No payload padding or malformed attribute is involved.
	code := make([]byte, 256)
	code[252], code[253], code[254], code[255] = 0x13, 0x01, 0xff, 0xac
	class := stockVerifyBuildClass(stockVerifyClassOptions{code: code, maxStack: 1})
	insert := class.mark["classAccess"]
	extra := make([]byte, 0, 500*5)
	for i := 0; i < 500; i++ {
		extra = append(extra, 3, 0, 0, 0, byte(i))
	}
	payload := make([]byte, 0, len(class.bytes)+len(extra))
	payload = append(payload, class.bytes[:insert]...)
	payload = append(payload, extra...)
	payload = append(payload, class.bytes[insert:]...)
	payload[8], payload[9] = 2, 0 // big-endian cp_count=512
	if len(payload) != 2915 || len(payload) > 4096 {
		t.Fatalf("review payload size=%d, want 2915 within 4096", len(payload))
	}

	pageAddr, pageHash, payloadHash := stockVerifyDeployPage(t, e, page, payload)
	inspect := e.mustCall(moduleAddr, stockVerifyCallData(t, module, "inspect", pageAddr, pageHash, payloadHash), stockVerifyCallGas)
	metadata := stockVerifyUnpack(t, module, "inspect", inspect.result.ReturnData)
	wantOffset := uint32(class.mark["root.code0.bytes"] + len(extra))
	if metadata[0].(uint32) != wantOffset || metadata[1].(uint32) != 256 || metadata[2].(uint8) != 1 || metadata[3].(uint8) != 0 {
		t.Fatalf("accepted review metadata=%v, want offset=%d length=256 stack=1 locals=0", metadata, wantOffset)
	}

	// Isolate execution from the controller: from the sixteenth batch boundary,
	// the pinned module finishes normally under the same 2M transaction gas cap.
	directBefore := stockVerifyZeroMachine()
	directBefore.Pc = 240
	direct := stockVerifyStepResult(t, e, module, moduleAddr, pageAddr, pageHash, payloadHash, directBefore, 16)
	if direct.coreErr != nil || direct.result == nil || direct.result.Err != nil {
		t.Fatalf("accepted direct final batch failed: core=%v evm=%v data=%x", direct.coreErr, stockVerifyResultErr(direct.result), stockVerifyResultData(direct.result))
	}
	directOut := stockVerifyUnpack(t, module, "step", direct.result.ReturnData)
	directMachine := stockVerifyMachineFrom(directOut[0])
	if !directMachine.Done || directMachine.Pc != 256 || directMachine.Result != 243 || directOut[1].(uint8) != 14 {
		t.Fatalf("accepted direct final machine=%+v executed=%v", directMachine, directOut[1])
	}

	coordAddr, create := e.mustCreate(stockVerifyConstructor(t, coord, moduleAddr, pageAddr, moduleHash, pageHash, payloadHash), stockVerifyCreateGas)
	var successfulResumeGas uint64
	for epoch := uint64(0); epoch < 15; epoch++ {
		r := stockVerifyResume(t, e, coord, coordAddr, epoch, 16, 32, stockVerifyCallGas)
		if r.coreErr != nil || r.result == nil || r.result.Err != nil {
			t.Fatalf("prefix resume epoch=%d failed: core=%v evm=%v data=%x", epoch, r.coreErr, stockVerifyResultErr(r.result), stockVerifyResultData(r.result))
		}
		successfulResumeGas += r.result.UsedGas
	}
	beforeEpoch, beforeTotal, beforeDigest, beforeMachine := stockVerifyCheckpoint(t, e, coord, coordAddr)
	if beforeEpoch != 15 || beforeTotal != 240 || beforeMachine.Pc != 240 || beforeMachine.Done {
		t.Fatalf("pre-failure checkpoint=(epoch=%d total=%d machine=%+v)", beforeEpoch, beforeTotal, beforeMachine)
	}

	failed := stockVerifyResume(t, e, coord, coordAddr, beforeEpoch, 16, 1, stockVerifyCallGas)
	stockVerifyAssertRevert(t, failed, "StockControlError(uint256)", 6)
	stockVerifyAssertFailedRollback(t, e, coord, coordAddr, beforeEpoch, beforeTotal, beforeDigest, beforeMachine, failed)
	final := stockVerifyResume(t, e, coord, coordAddr, beforeEpoch, 16, 32, stockVerifyCallGas)
	if final.coreErr != nil || final.result == nil || final.result.Failed() {
		t.Fatalf("boundary must complete at unchanged2M: core=%v evm=%v data=%x", final.coreErr, stockVerifyResultErr(final.result), stockVerifyResultData(final.result))
	}
	epoch, total, digest, terminal := stockVerifyCheckpoint(t, e, coord, coordAddr)
	if epoch != 16 || total != 254 || !stockVerifyMachineEqual(terminal, directMachine) ||
		digest != stockVerifyDigest(t, module, payloadHash, moduleHash, terminal, epoch, total) {
		t.Fatalf("wrong boundary checkpoint epoch=%d total=%d machine=%+v", epoch, total, terminal)
	}
	stockVerifyCheckEvent(t, coord, final, epoch, total, terminal, 14, stockVerifyDirty(beforeMachine, terminal), digest)
	t.Logf("accepted-profile boundary passes: payload=%d cp_count=512 code=256 directFinalGas=%d coordinatorCreateGas=%d prefixResumeGas=%d finalResumeGas=%d",
		len(payload), direct.result.UsedGas, create.result.UsedGas, successfulResumeGas, final.result.UsedGas)
}
