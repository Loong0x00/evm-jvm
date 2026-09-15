# Formal task 1 blind verdict

Both supplied `machine-results.json` files report passing source verification, artifact hashing, independent source build, and generated gate. I treated those results as authoritative and did not rerun heavy tests. Neither candidate has a critical machine failure.

## Decision summary

| Candidate | Decision | Overall | Confidence | Preference |
|---|---:|---:|---:|---|
| A | **Reject** | **7.8/10** | 93% | — |
| B | **Accept** | **9.3/10** | 96% | **Preferred** |

The preference is based on verification strength, isolation, and supplied canonical detail—not prose length or performance.

## Candidate A

### Findings by severity

**High — build/gate isolation violation.** `candidate-A/tools/build.py:12` hard-codes `NODE_PATH` to `/home/user/evm-jvm/geth/jvmevm/runtime/node_modules`; the same external path appears in `candidate-A/tools/gate.py:67,136`. This is a sibling worktree, contrary to the task's isolation rule. Since the recorded candidate commands come from another worktree and the machine build passed, the path was an effective dependency rather than dead configuration. This also undermines the report's isolated-worktree claim.

**Medium — inconsistent/weaker parent pin.** `candidate-A/parent-input.json:2-3` names `parent-3ed302a92` but records basis `5b55d0ce6`; `candidate-A/tools/verify_source.py:40,99` deliberately asserts that mismatch. In addition, the verifier computes `want_inputs` from the live parent directory (`verify_source.py:34-40`) instead of checking those files against immutable digest literals. Its exact reverse text comparisons remain valuable, but this is weaker and less clear than the requested strict pin.

**Medium — incomplete canonical/archive evidence in the supplied bundle.** The gate summary exposes canonical verification only as the integer `273` (`candidate-A/artifacts/generated-gate-summary.json:1498`), and the gate passes only six normal worlds to the canonical verifier, excluding reordered30 (`candidate-A/tools/gate.py:162-168`). The report claims a 62-file archive and manifest plus a clean checksum check (`candidate-A/candidate-report.md:51-52,81,86-87`), but the supplied `artifacts/` contains only the summary and checksum list; 61 paths named by `candidate-A/artifacts/SHA256SUMS:1-62` and the claimed manifest are absent.

**Low — boundary criterion is broader than the observed result.** The archived summary records the correct `0x71540d20` / `[1,0]` engine refusal with unchanged root (`candidate-A/artifacts/generated-gate-summary.json:1469-1475`), and the report correctly calls 262144 an honest infeasibility. However, `candidate-A/tools/gate.py:151-154` would accept any selector in the engine ABI other than the coordinator selector. That is less regression-specific than the report's exact observed result.

### Dimension scores

| Dimension | Score | Assessment |
|---|---:|---|
| Correctness | **7.5** | The authoritative machine gates pass (`candidate-A/machine-results.json:2-25`) and strict transformed-source comparisons are present (`tools/verify_source.py:45-99`). Deduction: prohibited external dependency and the resulting inaccurate isolation claim. |
| Architecture understanding | **9.0** | Checkpoint inspection requires lifecycle success, every raw class initialized, and total class count `n+83` (`tools/gate.py:52-60`). Driver/coordinator/engine ownership and root atomicity are explicitly separated (`tools/gate.py:109-158`), while parent-only original30 is correctly left out (`candidate-report.md:91-104`). |
| Modification minimality | **9.6** | Full reverse comparisons and all three diffs restrict production changes to the equal-length domain, cap/config, coordinator arrays/guard, driver guards, addresses, and derived pins (`tools/verify_source.py:45-89`; `engine.diff`; `coordinator.diff`; `driver.diff`). |
| Robustness | **8.0** | Exact29/30 q1/q7/direct/reopen, reordered30, three refusal layers, and byte boundaries passed (`tools/gate.py:83-158`). The weaker 262144 predicate and omission of reordered30 from canonical receipts reduce assurance. |
| Maintainability | **6.5** | `tools/stage.py:59-97` is clear and count-asserted. The live-derived parent digests, mismatched basis, and external tool dependency make the reproducer less trustworthy and portable. |
| Task completion | **6.0** | Machine-required implementation/gates completed, but formal isolation was breached and most claimed durable evidence is unavailable in the supplied package. |

**Decision: Reject.** The runtime mechanics themselves are strong, but the explicit no-other-worktree rule is a formal task requirement and was violated by both build and gate scripts.

## Candidate B

### Findings by severity

**Medium — most checksum-listed evidence is absent from the blind bundle.** The report says durable build, fixture, Head, failure, command, and checksum evidence is under `artifacts/` (`candidate-B/candidate-report.md:24-25`). In the supplied candidate directory, however, only `generated-gate-summary.json` and `SHA256SUMS` are present; 70 paths listed by `candidate-B/artifacts/SHA256SUMS:1-71` are unavailable. This limits artifact-level independent audit, though the authoritative machine results and detailed gate summary are enough for acceptance.

**Low — supplied reproducer subset is not stand-alone.** `candidate-B/tools/gate.py:48-50` imports `checkpoint_diagnostic.py`, and line 165 invokes `verify_receipts.js`; neither helper is supplied in the blind candidate directory. The embedded canonical summary mitigates the evidence gap.

No high or critical finding was identified.

### Dimension scores

| Dimension | Score | Assessment |
|---|---:|---|
| Correctness | **9.6** | All authoritative machine checks pass (`candidate-B/machine-results.json:2-24`). The verifier hard-codes exact parent input and output hashes and requires exact transformed text (`tools/verify_source.py:10-24,35-50,52-123`); boundary selectors, words, and atomic roots are exact (`tools/gate.py:145-160`). |
| Architecture understanding | **9.5** | The gate validates initialized raw classes and continuation state (`tools/gate.py:54-64`), compares q1/q7/direct terminal semantics (`tools/gate.py:75-100`), and correctly uses disposable transport/coordinator probes to expose each product refusal layer (`tools/gate.py:103-160`). Parent initialization-state behavior and fixed limits remain pinned (`tools/verify_source.py:71-72,113-123`). |
| Modification minimality | **9.8** | Exact full-text reverse verification allows only the requested cap/domain/array/guard/address/hash changes, and both build scripts are checked byte-identically (`tools/verify_source.py:52-111`; all three diffs). |
| Robustness | **9.5** | q1/q7/direct machine roots, opaque payloads, JVM steps, and internal steps must all agree (`tools/gate.py:75-89`). All refusal layers and byte boundaries use exact outcomes and unchanged roots. Canonical verification includes all six normal worlds plus reordered30 and embeds a 274-receipt per-world scope summary (`tools/gate.py:164-168`; `artifacts/generated-gate-summary.json:1499-1552`). |
| Maintainability | **8.8** | Build and gate resolve pinned dependencies from the current worktree (`tools/build.py:13-18`; `tools/gate.py:15-27`), with explicit immutable hashes and invariants. Missing helpers/evidence in the blind package prevent a fully stand-alone audit. |
| Task completion | **8.6** | Requested mechanics and generated gates are machine-validated, boundary wording is honest, and original30 remains parent-owned (`candidate-report.md:14-31`). The evidence omission is the principal deduction. |

**Decision: Accept.** The candidate meets the semantic task and formal isolation boundary, with only packaging/evidence-completeness caveats.

## Preference

**Candidate B, clearly preferred.** It combines the same authoritative machine success with an immutable parent pin, worktree-local tooling, exact 262144 error checking, stronger quantum invariance, and canonical coverage of reordered30.

## Remaining uncertainty

- Most durable evidence files referenced by both checksum manifests were not included in the blind directories, so they could not be inspected directly.
- Per task boundary, no original artifact and no parent-only original30 run were accessed or evaluated.
