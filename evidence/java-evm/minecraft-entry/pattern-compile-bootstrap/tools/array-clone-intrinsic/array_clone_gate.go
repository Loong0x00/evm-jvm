package main

import (
	"errors"
	"fmt"
	"path/filepath"
	"time"
)

func (r *runner) arrayCloneGate() error {
	started := time.Now()
	var rows []scheduleReport
	for _, spec := range []struct {
		name string
		q    uint64
	}{
		{"q1-array-clone-matrix", 1},
		{"q7-array-clone-matrix", 7},
		{"q4096-array-clone-matrix", 4096},
		{"q65536-array-clone-matrix", maxJvm},
	} {
		row, world, err := r.runSchedule(spec.name, spec.q, "ArrayCloneMatrix", false, true)
		if err != nil {
			if world != nil {
				world.close()
			}
			return err
		}
		world.close()
		r.report.Schedules = append(r.report.Schedules, row)
		rows = append(rows, row)
	}
	for i := 1; i < len(rows); i++ {
		if rows[0].Final.MachineStateRoot != rows[i].Final.MachineStateRoot ||
			rows[0].Final.VfsStateRoot != rows[i].Final.VfsStateRoot ||
			rows[0].Final.TotalJvmSteps != rows[i].Final.TotalJvmSteps ||
			rows[0].Final.TotalInternalSteps != rows[i].Final.TotalInternalSteps {
			return errors.New("array-clone matrix machine/VFS roots or step totals differ across q1/q7/q4096/q65536")
		}
		if rows[i-1].CallCount < rows[i].CallCount {
			return fmt.Errorf("smaller-quantum clone schedule used fewer calls: %s=%d %s=%d",
				rows[i-1].Name, rows[i-1].CallCount, rows[i].Name, rows[i].CallCount)
		}
	}

	row, err := r.runTerminal(
		"array-clone-null-receiver", "typed guest NullPointerException caught; normal void return",
		"ArrayCloneNullReceiver", 2, "", 0, false,
	)
	if err != nil {
		return err
	}
	r.report.Cases = append(r.report.Cases, row)

	for _, spec := range []struct {
		name, expectation, fixture string
		arrays                     int
		elements                   uint64
	}{
		{"array-clone-maximum-length", "distinct eager dense 65536-element double[] with preserved raw bits", "ArrayCloneMaximumLength", 3, 131072},
		{"array-clone-array-quota-oom", "typed guest OOM at the unchanged 4096 ordinary-array quota; clone is not published", "ArrayCloneArrayQuotaOOM", 4096, 4094},
		{"array-clone-element-quota-oom", "typed guest OOM when the eager clone exceeds the unchanged 262144-element quota", "ArrayCloneElementQuotaOOM", 5, 196611},
	} {
		row, err := r.runTerminal(spec.name, spec.expectation, spec.fixture, 2, "", 0, true)
		if err != nil {
			return err
		}
		if row.HeapAudit == nil || row.HeapAudit.ArrayCount != spec.arrays ||
			row.HeapAudit.ArrayElements != spec.elements {
			return fmt.Errorf("%s heap atomicity/layout mismatch: arrays=%v expected=%d elements=%v expected=%d",
				spec.name, row.HeapAudit, spec.arrays, func() uint64 {
					if row.HeapAudit == nil {
						return 0
					}
					return row.HeapAudit.ArrayElements
				}(), spec.elements)
		}
		r.report.Cases = append(r.report.Cases, row)
	}

	for _, spec := range []struct {
		name, fixture, errorName, code string
	}{
		{"unsupported-array-member", "clone-unsupported-array-member", "CallError", "3"},
		{"wrong-array-clone-descriptor", "clone-wrong-array-descriptor", "CallError", "3"},
		{"malformed-array-owner", "clone-malformed-array-owner", "TypeError", "1"},
		{"incompatible-symbolic-array-owner", "clone-incompatible-array-owner", "ReferenceError", "2"},
		{"Object-clone-unmodified-resolution-control", "object-clone-protected-control", "CallError", "3"},
		{"empty-symbolic-owner-control", "clone-empty-owner-control", "CallError", "1"},
		{"Object-clone-virtual-control", "object-clone-virtual-control", "CallError", "3"},
	} {
		row, err := r.runRejection("array-clone-"+spec.name, spec.fixture, spec.errorName, spec.code,
			maxJvm, maxInternal)
		if err != nil {
			return err
		}
		r.report.Controls = append(r.report.Controls, row)
	}

	if rows[0].HeapAudit != nil || rows[len(rows)-1].Final.Lifecycle != 2 {
		return errors.New("array-clone matrix did not complete a void main with normal dense-array validation")
	}
	for _, row := range rows {
		if row.Final.Lifecycle != 2 || row.Final.Outcome != 2 || row.Final.JavaKind != 0 {
			return fmt.Errorf("array-clone matrix terminal outcome mismatch: %+v", row.Final)
		}
	}
	r.report.Status = "generated Java 8 primitive/reference/multirank array-clone EVM matrix and quota/owner controls passed"
	r.report.ElapsedMS = time.Since(started).Milliseconds()
	return writeJSON(filepath.Join(r.reportDir, "array-clone-gate-summary.json"), r.report)
}
