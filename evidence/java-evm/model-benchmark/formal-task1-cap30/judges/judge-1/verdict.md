# Formal task 1 — independent blind verdict

## Executive verdict

Both candidates receive full credit for the supplied mandatory machine facts: source build and generated gates passed. I did not rerun heavy tests.

| Candidate | Overall | Decision | Confidence |
|---|---:|---|---:|
| A | **8.2/10** | **Reject** | 94% |
| B | **9.2/10** | **Accept** | 95% |

**Preference: B.** It has the same narrowly mechanical product delta and valid machine behavior, but preserves isolated-worktree reproducibility, pins the named parent consistently, asserts the exact byte-boundary outcomes, and canonically checks reordered30. A is technically strong but its reproducer directly depends on a different worktree, contrary to an explicit task constraint.

## Candidate A

### Findings by severity

- **High — isolated-worktree/reproducibility violation (acceptance blocker).** `candidate-A/tools/build.py:12-13` and `tools/gate.py:67,136` hard-code JavaScript dependencies from a different worktree. That conflicts with the original “no other worktrees” rule and contradicts the isolated execution claim in `candidate-report.md:5-6,27-29`. This is a process/compliance blocker, not a machine-semantic failure.
- **Medium — inconsistent parent basis.** `candidate-A/parent-input.json:2` and `pins.json:2` say `5b55d0ce6`, while the required parent is `parent-3ed302a92`; `tools/verify_source.py:40,99` deliberately enforces the mismatch. The four hashes and diff headers do reference the correct parent evidence, so this does not invalidate the observed mechanical delta, but it weakens strict provenance.
- **Medium — evidence-completeness overclaim.** `candidate-report.md:50-53,86-87` claims a manifest and complete 62-file archive. In the supplied candidate archive only `generated-gate-summary.json` and `SHA256SUMS` exist, and `manifest.json` is not listed in `SHA256SUMS`. The authoritative machine pass remains credited, but the full archived evidence cannot be independently audited here.
- **Low — weaker future boundary assertion.** At 262144 bytes, `tools/gate.py:150-154` accepts any engine ABI custom error rather than asserting the observed `LC0StateError(1,0)` selector and words. The supplied summary does record the correct exact result and unchanged root.
- **Low — canonical receipt scope excludes reordered30.** `tools/gate.py:160-168` sends the six ordinary success worlds to the receipt verifier, not reordered30. The reordered checkpoint is still inspected and checked for a distinct package root at lines 99-106.

### Dimension scores

1. **Correctness — 8.5/10.** `machine-results.json:2-25` authoritatively passes source verification, artifact hashing, independent build, and all required gate cases. `engine.diff:7-12,40-47`, `coordinator.diff:28-46`, and `driver.diff:31-64` show the requested cap/config/array/guard changes only. The generated summary records exact three-layer and byte-boundary errors with unchanged roots. Deductions are for provenance/isolation claims rather than runtime semantics.
2. **Architecture understanding — 9.4/10.** `tools/gate.py:108-145` correctly pierces one refusal layer at a time: product driver, product coordinator through a disposable widened transport, then product engine through a disposable widened coordinator. `tools/gate.py:50-61` checks lifecycle, checkpoint hash, all raw classes initialized, and `classCount == n+83`. `candidate-report.md:91-100` accurately preserves the parent-only original-artifact boundary.
3. **Modification minimality — 9.4/10.** The three product diffs are exactly the measured mechanical delta: nine engine domain substitutions, one cap and one config word; four coordinator arrays and one guard; driver domains, pins, and two guards. The extra metadata at `pins.json:37` is unnecessary but non-semantic.
4. **Robustness — 8.8/10.** `tools/gate.py:86-106` covers 29/30 q1/q7/direct/reopen and reordered bindings; lines 108-158 cover all three refusal layers and both byte boundaries. Root/payload quantum invariance and checkpoint canonicality are checked. The generic 262144 custom-error assertion and six-world receipt scope leave minor regression gaps.
5. **Maintainability — 6.8/10.** The reverse reconstruction in `tools/verify_source.py:43-90` is clear and strict over product text. However, the cross-worktree absolute dependency is non-portable, and the verifier derives parent hashes at lines 34-40 rather than embedding the expected immutable values directly.
6. **Task completion — 6.8/10.** Mandatory technical gates passed, and boundary wording in `candidate-report.md:71-103` is notably precise. Completion is reduced by the explicit isolation breach, mismatched basis, and unavailable/overclaimed evidence archive.

**Decision: Reject.** No critical machine failure exists; rejection is for the high-severity explicit worktree-boundary violation.

## Candidate B

### Findings by severity

- **Medium — stale boundary wording.** `candidate-B/pins.json:36` says diagnostic bound112 was retained, while line 37, `candidate-report.md:16-18`, and `tools/verify_source.py:105-123` correctly establish bound113. This is contradictory metadata, not an operative cap error.
- **Low — total canonical class count is checked indirectly.** `tools/gate.py:53-66` verifies every raw class reaches initialized state but does not explicitly assert decoded `classCount == raw + 83`. Strict source equality and canonical receipt checks substantially mitigate this.
- **Low — build derives pins by mutating staged source.** `tools/build.py:42-72` updates coordinator and driver sources in place. It is bounded/idempotent for the expected state and passed the independent build, but output-tree-only staging would be easier to maintain.
- **Low — blind evidence archive incomplete.** The supplied `artifacts/` directory contains only the generated summary and checksum listing, although `SHA256SUMS` names 70 additional files. Unlike A, the available summary embeds the refusal evidence and canonical per-world breakdown, but full file-level audit is still unavailable.

### Dimension scores

1. **Correctness — 9.3/10.** `machine-results.json:2-24` authoritatively passes all mandatory checks. `engine.diff`, `coordinator.diff`, and `driver.diff` show exactly the requested mechanics. `tools/gate.py:150-161` strictly asserts `LC0StateError(1,0)` at 262144 and `MR0Error(12)` at 262145 with unchanged roots. Only the stale bound wording prevents a higher score.
2. **Architecture understanding — 9.5/10.** `tools/gate.py:102-148` validly reaches driver, coordinator, and engine refusals independently while keeping product artifacts intact. Lines 74-100 correctly exercise continuation/reopen and reordered package identity. `candidate-report.md:27-31` preserves the parent-owned Strings/original30 boundary and makes no Minecraft completion claim.
3. **Modification minimality — 9.8/10.** The product diffs contain no semantic expansion beyond cap/config, fixed arrays/guard, and fresh equal-length identity/pins. `tools/verify_source.py:50-103` reconstructs and compares the complete expected source. `pins.json:15-23` preserves all fixed resource limits.
4. **Robustness — 9.3/10.** `tools/gate.py:76-89` checks q1/q7/direct equivalence for roots, payloads, Java steps, and internal steps after reopen. Lines 127-160 assert exact refusal selectors/arguments and atomic roots. Lines 163-168 include all seven successful worlds, including reordered30, in canonical verification; the summary reports 274 receipts with per-world counts.
5. **Maintainability — 8.8/10.** `tools/verify_source.py:10-24` embeds exact parent hashes and consistent basis. `tools/build.py:13-18` derives dependencies from the current worktree and fails clearly when absent. In-place source pin updates are the principal maintainability deduction.
6. **Task completion — 8.8/10.** The report covers required source verification, LOCAL384 pins, all generated cases, evidence location, and parent-owned uncertainty (`candidate-report.md:14-31`). Provenance is consistent in `parent-input.json:2-8`. The stale bound phrase and blind-package evidence omissions are non-blocking completeness defects.

**Decision: Accept.** No critical or high-severity correctness blocker was found.

## Cross-candidate checks

- **Strict parent delta:** Both diff sets are mechanically narrow. B's verifier additionally embeds exact expected parent hashes and uses the requested basis consistently; A's content hashes are correct but basis metadata is not.
- **Three-layer refusal validity:** Both are valid. The driver rejects before world creation; a widened disposable driver exposes the product coordinator; a widened disposable coordinator exposes the product engine. Their summaries record `MR0Error(2)` and `LinkError(1,31)` with unchanged roots and no candidate checkpoint/head output.
- **Boundary wording and behavior:** A's prose most clearly distinguishes “262144 accepted by coordinator but honestly infeasible in engine” from the atomic 262145 refusal. B's executable assertion is stricter, but its `parentAmendment` metadata contains stale bound112 wording.
- **Canonical evidence:** A explicitly checks decoded `n+83` but receipt-verifies six worlds. B receipt-verifies all seven successful worlds and embeds a per-world canonical summary, but omits the direct decoded `n+83` assertion.
- **Reproducibility:** B uses worktree-local dependencies. A's hard-coded different-worktree dependency violates the formal isolation boundary.
- **Evidence completeness:** Both blind packets omit nearly all files named by their checksum listings. This limits independent archival audit but does not supersede the stipulated authoritative machine passes.
