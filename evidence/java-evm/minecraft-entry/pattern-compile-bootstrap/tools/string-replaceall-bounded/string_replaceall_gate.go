package main

import (
	"errors"
	"fmt"
	"path/filepath"
	"reflect"
	"time"
)

// stringReplaceAllControls runs the refusal matrix independently from the
// expensive positive schedules so completed EVM schedule results need not be
// replayed merely to rerun negative controls or fresh-process verification.
func (r *runner) stringReplaceAllControls() error {
	// Regex/surrogate errors occur inside Java after earlier q1/q7 slices may
	// have committed a running Head. Refuse atomically relative to that Head.
	for _, spec := range []struct {
		name, fixture, errorName, code string
		quantum                        uint64
	}{
		{"valid-quantifier-refusal-q1", "string-replaceall-unsupported-valid", "CallError", "4", 1},
		{"valid-quantifier-refusal-q7", "string-replaceall-unsupported-valid", "CallError", "4", 7},
		{"surrogate-input-refusal-q1", "string-replaceall-surrogate-unsupported", "CallError", "4", 1},
		{"surrogate-input-refusal-q7", "string-replaceall-surrogate-unsupported", "CallError", "4", 7},
	} {
		row, err := r.runResumedRefusal(spec.name, spec.fixture, spec.errorName, spec.code, spec.quantum, maxInternal)
		if err != nil {
			return err
		}
		r.report.Controls = append(r.report.Controls, row)
	}
	row, err := r.runRejection("raw-matcher-replacement-refusal", "matcher-raw-platform-replacement",
		"BootstrapProfileError", "1", maxJvm, maxInternal)
	if err != nil {
		return err
	}
	r.report.Controls = append(r.report.Controls, row)
	return nil
}

func (r *runner) stringReplaceAllControlsGate() error {
	started := time.Now()
	r.report.Mode = "replaceall-controls"
	if err := r.stringReplaceAllControls(); err != nil {
		return err
	}
	r.report.Status = "generated P38 bounded-regex/surrogate/raw-Matcher refusal controls passed"
	r.report.ElapsedMS = time.Since(started).Milliseconds()
	return writeJSON(filepath.Join(r.reportDir, "string-replaceall-controls-summary.json"), r.report)
}

// stringReplaceAllGate exercises only the new P38 guest API with a 16B per-call
// test-only gas budget, a 4,800-second wall budget, and 40,000 continuation-call
// ceiling. Isolated fresh-world trials measured 1B/2B/4B/8B insufficient; the 8B
// call exhausted to the 25M reserve floor, and full schedules exceeded 1,200s and
// 2,400s. These limits change neither EVM accounting nor retained P36/P37
// budgets and ceilings, which remain separately pinned.
func (r *runner) stringReplaceAllGate() error {
	started := time.Now()
	var rows []scheduleReport
	for _, spec := range []struct {
		name string
		q    uint64
	}{
		{"q65536-string-replaceall-matrix", maxJvm},
		{"q4096-string-replaceall-matrix", 4096},
		{"q7-string-replaceall-matrix", 7},
		{"q1-string-replaceall-matrix", 1},
	} {
		row, world, err := r.runSchedule(spec.name, spec.q, "StringReplaceAllMatrix", true, true)
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
			rows[0].Final.TotalInternalSteps != rows[i].Final.TotalInternalSteps ||
			!reflect.DeepEqual(rows[0].HeapAudit, rows[i].HeapAudit) {
			return errors.New("String.replaceAll machine/VFS roots, step totals, or audited Pattern/Matcher heap differ across q1/q7/q65536/q4096")
		}
		if rows[i-1].CallCount > rows[i].CallCount {
			return fmt.Errorf("smaller-quantum replaceAll schedule used more calls than the preceding larger quantum: %s=%d %s=%d",
				rows[i].Name, rows[i].CallCount, rows[i-1].Name, rows[i-1].CallCount)
		}
	}

	if err := r.stringReplaceAllControls(); err != nil {
		return err
	}

	r.report.Status = "generated Java 8 String.replaceAll profile, rejection, schedule-equivalence, and bounded Matcher heap gates passed; no original-JAR execution"
	r.report.ElapsedMS = time.Since(started).Milliseconds()
	return writeJSON(filepath.Join(r.reportDir, "string-replaceall-gate-summary.json"), r.report)
}
