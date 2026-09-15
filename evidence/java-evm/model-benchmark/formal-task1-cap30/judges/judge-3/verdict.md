# Formal task 1 — independent blind verdict

Both supplied mandatory parent builds and generated gates are treated as authoritative passes. I did not rerun heavy tests and did not use candidate identity or performance.

## Decision summary

| Candidate | Decision | Overall | Confidence |
|---|---:|---:|---:|
| A | **ACCEPT** | **9.6/10** | 97% |
| B | **REJECT** | **8.4/10** | 96% |

**Preference: Candidate A (not a tie).** A has the stronger immutable parent pin, worktree-relative reproducer, exact boundary checks, and canonical receipt coverage for reordered30.

## Candidate A — ACCEPT

### Scores

| Dimension | Score | Assessment |
|---|---:|---|
| Correctness | 9.7 | `machine-results.json` passes source verification, artifact hashes, independent build, and generated gate. `generated-gate-summary.json` shows q1/q7/direct convergence and the expected refusal outcomes without an original-server or Done claim. |
| Architecture understanding | 9.6 | `engine.diff`, `coordinator.diff`, and `driver.diff` preserve domain/code-hash ownership and fixed limits. `tools/gate.py:74-161` correctly exercises continuations, reopen, canonical initialization, and disposable transports to reach deeper product guards. |
| Modification minimality | 9.8 | The three production diffs contain only equal-length domain/pin changes, cap/config 29→30, coordinator arrays/guard, and driver guards. `tools/verify_source.py:50-108` reconstructs expected files from the accepted parent and requires whole-file equality. |
| Robustness | 9.5 | `tools/gate.py:74-168` covers 29/30 at three quanta, reopen, reordered30, all three 31-class layers, and both byte boundaries. The summary records unchanged roots and empty candidate publication fields. Canonical verification covers 274 receipts, including reordered30. |
| Maintainability | 9.3 | Parent digests and built pins are immutable literals (`tools/verify_source.py:10-48`), paths are worktree-relative (`tools/build.py:6-18`), and generated ZIPs are checksummed. Minor stale pin wording remains. |
| Task completion | 9.6 | All requested functional gates and evidence classes are represented. `artifacts/SHA256SUMS` indexes build artifacts, fixture JSON/ZIPs, commands, failures, Heads, canonical receipts, and tool versions. `candidate-report.md` correctly leaves original30 to the parent. |

### Findings by severity

- **Low — stale pin wording.** `pins.json.parentAmendment` says diagnostic bound112 was “retained,” while the same file and verifier correctly set `diagnosticClassBound` to 113 (`tools/verify_source.py:121-122`). This is descriptive inconsistency, not runtime drift.
- **Low — incomplete executable assertions for publication atomicity.** `tools/gate.py:127-160` asserts selectors, words, and unchanged roots, while the archived summary additionally shows empty `candidateCheckpoint`, `candidateHead`, and `candidateRoot` plus zero checkpoint bytes. Those fields should ideally be asserted too.
- **Critical/high/medium blockers:** none.

### Key validity checks

- **Strict parent delta:** strong. Parent source hashes are hard-coded, build scripts are checked against parent copies, and whole engine/coordinator/driver text is reconstructed.
- **Three-layer refusal:** valid. Driver refusal precedes world creation; a widened disposable driver reaches the product coordinator; a widened disposable coordinator reaches the unchanged product engine. Product refusal roots remain unchanged.
- **Boundary wording:** valid. Exact 262144 is described as honest infeasibility and records engine `0x71540d20` with words `[1,0]`; 262145 records atomic coordinator `MR0Error(12)`.
- **Canonical evidence:** strong; 274 receipts cover all seven successful worlds.
- **Reproducibility/evidence:** strong and worktree-relative; the checksum inventory is broad.

## Candidate B — REJECT

The runtime delta and generated behavior are technically strong and machine-green. Rejection is for an explicit task-boundary violation in the runnable tooling, not for a machine-gate failure.

### Scores

| Dimension | Score | Assessment |
|---|---:|---|
| Correctness | 9.0 | `machine-results.json` and `generated-gate-summary.json` establish correct cap30 behavior. The score is reduced because the claimed isolated procedure is contradicted by operational external-worktree paths. |
| Architecture understanding | 9.4 | `candidate-report.md` accurately distinguishes the driver/coordinator/engine refusal layers and describes 262144 as engine-side infeasibility. `tools/gate.py:83-158` uses proper disposable transports and preserves product pins. |
| Modification minimality | 9.1 | Production diffs are mechanical and whole-file reverse comparisons reject semantic drift. `tools/stage.py:99-130` nevertheless adds unrequested worker metadata and drops the explicit parent-amendment metadata. |
| Robustness | 9.0 | All required paths plus an EnumSet regression are represented. The 262144 executable assertion is broader than the observed result, and nested canonical receipt verification omits reordered30. |
| Maintainability | 7.2 | Deterministic staging is useful, but `tools/build.py:12-13` and `tools/gate.py:67,136` hard-code another worktree’s `node_modules`. `tools/verify_source.py:33-40` also lacks immutable expected parent digest literals. |
| Task completion | 7.0 | Functional gates pass and parent-only work is correctly excluded, but the current-worktree-only restriction is not satisfied. Evidence is substantial, though fixture ZIPs are intentionally omitted and reordered canonical receipts are absent. |

### Findings by severity

- **High — forbidden external-worktree dependency.** `tools/build.py:12-13` checks and exports an absolute `node_modules` path under a different worktree. `tools/gate.py:67,136` repeats it for selector verification and coordinator-probe compilation. This violates the explicit isolated-worktree rule and makes reproduction environment-dependent. **Acceptance blocker.**
- **Medium — reverse verifier does not immutably pin parent hashes.** `tools/verify_source.py:33-40` hashes the current contents of the named parent directory and compares them with editable `parent-input.json`; it does not contain a trusted expected digest table. A jointly changed parent snapshot and receipt could pass.
- **Low — canonical receipt scope omits reordered30.** Despite the “every successful world” comment, `tools/gate.py:160-168` verifies only six labels. Reordered30 is still checkpoint-inspected, so this is an evidence gap rather than a functional failure.
- **Low — broad 262144 assertion.** `tools/gate.py:147-154` accepts any engine ABI error other than the coordinator selector. The archive records the intended `0x71540d20`/`[1,0]`, but the gate does not require it.
- **Critical findings:** none; the supplied machine gates pass.

### Key validity checks

- **Strict parent delta:** production text delta is valid, but parent hash pinning is weaker than requested.
- **Three-layer refusal:** valid; archived roots are unchanged and publication candidates are empty.
- **Boundary wording:** the report is careful and accurate; the executable exact-262144 assertion is under-specific.
- **Canonical evidence:** valid for six ordinary quantum worlds; reordered30 lacks nested receipt verification.
- **Reproducibility/evidence:** evidence is substantial, but the hard-coded external path is a decisive isolation and portability defect.

## Final preference

**Candidate A.** Both candidates demonstrate the requested runtime semantics, but only A provides a self-contained worktree-relative procedure with a genuinely immutable parent pin and the broader canonical/evidence coverage.
