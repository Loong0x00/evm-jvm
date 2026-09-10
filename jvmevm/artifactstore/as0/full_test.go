package as0

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"strconv"
	"testing"

	"github.com/ethereum/go-ethereum/common"
)

type as0HarnessFullReport struct {
	Controller common.Address `json:"controller"`
	Root       common.Hash    `json:"root"`
	Content    common.Hash    `json:"content"`
	FirstPage  common.Address `json:"firstPage"`
	MidPage    common.Address `json:"midPage"`
	LastPage   common.Address `json:"lastPage"`
	TotalGas   uint64         `json:"totalGas"`
	MaxGas     uint64         `json:"maxGas"`
	SealGas    uint64         `json:"sealGas"`
	ReadGas    uint64         `json:"readGas"`
}

func as0HarnessUploadRange(t *testing.T, session *Session, controller common.Address, begin, end uint32) (uint64, uint64) {
	t.Helper()
	var total, maximum uint64
	for index := begin; index < end; index++ {
		raw := as0HarnessGeneratedPage(index, int(PageSize))
		result, err := session.Append(index*PageSize, raw, as0HarnessPageCommitment(t, controller, index, raw), as0HarnessAppendGas)
		if err != nil {
			t.Fatalf("append page %d: %v", index, err)
		}
		if result.GasUsed == 0 || result.GasUsed > as0HarnessAppendGas || result.StateRoot == (common.Hash{}) || len(result.Logs) != 1 {
			t.Fatalf("append page %d result=%+v", index, result)
		}
		total += result.GasUsed
		if result.GasUsed > maximum {
			maximum = result.GasUsed
		}
	}
	return total, maximum
}

func TestAS0HarnessFull32MiBMemory(t *testing.T) {
	owner := common.HexToAddress("0x4153300000000000000000000000000000000066")
	session, err := NewMemory(owner, MaxLength)
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	creation, _ := session.Creation()
	total, maximum := as0HarnessUploadRange(t, session, creation.Controller, 0, MaxPages)
	head, err := session.Head(as0HarnessOrdinaryGas)
	if err != nil || head.Cursor != MaxLength || head.PageCount != MaxPages || head.Sealed {
		t.Fatalf("full head=%+v err=%v", head, err)
	}
	sealed, err := session.Seal(MaxLength, head.ChainCommitment, as0HarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	read, err := session.Read(MaxLength-PageSize-2, MaxRead, as0HarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	want := append(as0HarnessGeneratedPage(MaxPages-2, int(PageSize))[PageSize-2:], as0HarnessGeneratedPage(MaxPages-1, int(PageSize))[:MaxRead-2]...)
	if !bytes.Equal(read.Bytes, want) {
		t.Fatal("full memory cross-page bytes differ")
	}
	t.Logf("full-memory bytes=%d pages=%d createGas=%d appendTotalGas=%d appendMaxGas=%d sealGas=%d readGas=%d root=%s", MaxLength, MaxPages, creation.GasUsed, total, maximum, sealed.GasUsed, read.GasUsed, sealed.StateRoot)
}

func TestAS0HarnessFull32MiBDiskPerAppendNewProcess(t *testing.T) {
	if os.Getenv("JVMEVM_AS0_FULL_CHILD") == "1" {
		as0HarnessFullDiskChild(t)
		return
	}
	owner := common.HexToAddress("0x4153300000000000000000000000000000000077")
	directory := t.TempDir()
	session, err := Open(directory, owner, MaxLength)
	if err != nil {
		t.Fatal(err)
	}
	creation, _ := session.Creation()
	const midpoint = MaxPages / 2
	firstTotal, firstMax := as0HarnessUploadRange(t, session, creation.Controller, 0, midpoint)
	firstPage, err := session.Page(0, as0HarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	midPage, err := session.Page(uint64(midpoint-1), as0HarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	midHead, err := session.Head(as0HarnessOrdinaryGas)
	if err != nil || midHead.Cursor != midpoint*PageSize || midHead.PageCount != midpoint || midHead.Sealed {
		t.Fatalf("mid head=%+v err=%v", midHead, err)
	}
	if err := session.Close(); err != nil {
		t.Fatal(err)
	}

	cmd := exec.Command(os.Args[0], "-test.run=^TestAS0HarnessFull32MiBDiskPerAppendNewProcess$")
	cmd.Env = append(os.Environ(), "JVMEVM_AS0_FULL_CHILD=1", "JVMEVM_AS0_FULL_DIR="+directory, "JVMEVM_AS0_FULL_OWNER="+owner.Hex(), "JVMEVM_AS0_FULL_CONTROLLER="+creation.Controller.Hex())
	output, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("full resume child: %v\n%s", err, output)
	}
	var child as0HarnessFullReport
	found := false
	for _, line := range bytes.Split(output, []byte{'\n'}) {
		if len(line) > 0 && line[0] == '{' {
			if err := json.Unmarshal(line, &child); err != nil {
				t.Fatal(err)
			}
			found = true
			break
		}
	}
	if !found {
		t.Fatalf("child report missing: %s", output)
	}
	if child.Controller != creation.Controller || child.FirstPage != firstPage.Address || child.MidPage != midPage.Address || child.LastPage == (common.Address{}) || child.Content == (common.Hash{}) || child.Root == (common.Hash{}) {
		t.Fatalf("child report=%+v", child)
	}

	// This process now reopens a head sealed by the other process. It verifies
	// code/getters without CREATE and reads the committed child code via the EVM.
	sealedSession, err := Open(directory, owner, MaxLength)
	if err != nil {
		t.Fatal(err)
	}
	defer sealedSession.Close()
	reopenCreation, _ := sealedSession.Creation()
	if reopenCreation.Performed || reopenCreation.GasUsed != 0 {
		t.Fatalf("sealed reopen redeployed: %+v", reopenCreation)
	}
	final, err := sealedSession.Head(as0HarnessOrdinaryGas)
	if err != nil || !final.Sealed || final.Cursor != MaxLength || final.PageCount != MaxPages || final.ContentCommitment != child.Content || final.StateRoot != child.Root {
		t.Fatalf("sealed reopen=%+v err=%v child=%+v", final, err, child)
	}
	firstAgain, _ := sealedSession.Page(0, as0HarnessOrdinaryGas)
	midAgain, _ := sealedSession.Page(uint64(midpoint-1), as0HarnessOrdinaryGas)
	lastAgain, _ := sealedSession.Page(uint64(MaxPages-1), as0HarnessOrdinaryGas)
	if firstAgain.Address != firstPage.Address || midAgain.Address != midPage.Address || lastAgain.Address != child.LastPage {
		t.Fatal("reopen recreated or changed child page addresses")
	}
	read, err := sealedSession.Read(MaxLength-PageSize-2, MaxRead, as0HarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	want := append(as0HarnessGeneratedPage(MaxPages-2, int(PageSize))[PageSize-2:], as0HarnessGeneratedPage(MaxPages-1, int(PageSize))[:MaxRead-2]...)
	if !bytes.Equal(read.Bytes, want) {
		t.Fatal("sealed new-process bytes differ")
	}
	maximum := firstMax
	if child.MaxGas > maximum {
		maximum = child.MaxGas
	}
	t.Logf("full-disk-per-call bytes=%d pages=%d createGas=%d appendTotalGas=%d appendMaxGas=%d sealGas=%d readGas=%d root=%s child=%s", MaxLength, MaxPages, creation.GasUsed, firstTotal+child.TotalGas, maximum, child.SealGas, child.ReadGas, child.Root, strconv.Quote(string(bytes.TrimSpace(output))))
}

func as0HarnessFullDiskChild(t *testing.T) {
	owner := common.HexToAddress(os.Getenv("JVMEVM_AS0_FULL_OWNER"))
	controller := common.HexToAddress(os.Getenv("JVMEVM_AS0_FULL_CONTROLLER"))
	session, err := Open(os.Getenv("JVMEVM_AS0_FULL_DIR"), owner, MaxLength)
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	creation, _ := session.Creation()
	if creation.Performed || creation.Controller != controller {
		t.Fatalf("child redeployed: %+v", creation)
	}
	head, err := session.Head(as0HarnessOrdinaryGas)
	if err != nil || head.PageCount != MaxPages/2 || head.Cursor != (MaxPages/2)*PageSize {
		t.Fatalf("child mid head=%+v err=%v", head, err)
	}
	first, _ := session.Page(0, as0HarnessOrdinaryGas)
	mid, _ := session.Page(uint64(MaxPages/2-1), as0HarnessOrdinaryGas)
	total, maximum := as0HarnessUploadRange(t, session, controller, MaxPages/2, MaxPages)
	full, err := session.Head(as0HarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	sealed, err := session.Seal(MaxLength, full.ChainCommitment, as0HarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	final, err := session.Head(as0HarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	last, err := session.Page(uint64(MaxPages-1), as0HarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	read, err := session.Read(MaxLength-PageSize-2, MaxRead, as0HarnessOrdinaryGas)
	if err != nil {
		t.Fatal(err)
	}
	want := append(as0HarnessGeneratedPage(MaxPages-2, int(PageSize))[PageSize-2:], as0HarnessGeneratedPage(MaxPages-1, int(PageSize))[:MaxRead-2]...)
	if !bytes.Equal(read.Bytes, want) {
		t.Fatal("child cross-page bytes differ")
	}
	report, _ := json.Marshal(as0HarnessFullReport{Controller: controller, Root: sealed.StateRoot, Content: final.ContentCommitment, FirstPage: first.Address, MidPage: mid.Address, LastPage: last.Address, TotalGas: total, MaxGas: maximum, SealGas: sealed.GasUsed, ReadGas: read.GasUsed})
	fmt.Println(string(report))
}
