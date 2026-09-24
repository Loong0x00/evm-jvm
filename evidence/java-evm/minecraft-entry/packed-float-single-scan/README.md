# P16 MR01 packed-float single-scan checkpoint optimization

## Current result

The cap-reservation acceptance blocker found after commit `0110df3d9` is fixed in the current source. See [`CAP_FALLBACK_FOLLOWUP.md`](CAP_FALLBACK_FOLLOWUP.md) for the exact change, boundary algebra, generated gate results, and caveats.

The initial optimization still reserves `43 + 4*length` for exactly rank-one `PRIMITIVE_FLOAT` arrays of length >=1024, avoiding the pre-encode nonzero scan. When that upper reservation plus the 280-byte envelope would exceed `MAX_CHECKPOINT_BYTES`, `_encodeMachine` now recomputes the validated exact P16 size before deciding whether to refuse. If the upper reservation fits, the ordinary packed path retains one validating float scan. Final output bound-check and shrink remain.

Run 06 results:

- Engine runtime: 392,176 bytes / 393,216-byte LOCAL cap; SHA256 `39d6d33a7925a7ee015ea4502bc4c32ff2c6c83bd1e5ceec7a758c632504696d`; P16 bootstrap root unchanged.
- Full generated-only gate: 942.715 seconds, 11,814 canonical receipts, ordinary LOCAL 1B.
- Required direct accepted-P16 MR01 equality: all three packed/crossover/sparse controls byte-identical; full gate plus direct-only comparison: 944.522 seconds. Supplemental q1/q7/direct equality also passes (nine comparisons, 614.038 seconds separately).
- Nine fresh terminal gas comparisons remain positive: 307,770–9,950,820 gas saved.
- Packed and sparse malformed-refusal atomicity, packed checkpoint resume, packed raw-cell oracle, 341/342 crossover, and old sparse arrays remain green.

No full-EVM near-cap fallback case was run. Its upper>cap/exact-at-cap and exact-over-cap behavior is proved by bounded source-order and algebra checks only; the synthetic fixed remainder does not establish guest-state reachability. No original Minecraft JAR/class/resource/world, sibling worktree, or network source was accessed. No original Minecraft replay, EULA, world, or `Done` claim.

## Evidence

- Latest run record: `results/cap-fallback-followup-gate-06.json`
- Source/order/root checks and cap algebra: `source-invariants.json`
- Full generated gate and receipts: `results/generated-gate-summary.json.gz`, `results/canonical-receipts.json`
- Current compiler/build pins: `results/build-pins.json`
- Fresh P16 MR01 equality: `results/opaque-equivalence-gate-06/` and `results/opaque-equivalence-gate-06-direct/`
- Fresh gas comparison: `results/generated-gas-comparison-gate-06.json`
- Initial run 04 summaries are preserved with `-04` suffixes; its opaque result archives remain unchanged.

`SHA256SUMS` covers this evidence directory.

## Reproduction (generated-only, cached dependencies, no network)

Use new output IDs because scripts reject overwrite. The checked-in fixtures are generated Java-8 test inputs; baseline comparison recompiles the tracked accepted-P16 source. No original workload input is used.

```sh
python3 evidence/java-evm/minecraft-entry/packed-float-single-scan/tools/verify_source.py
python3 evidence/java-evm/minecraft-entry/packed-float-single-scan/tools/build.py build/java-diff-mc-packed-float-single-scan-build-07
python3 evidence/java-evm/minecraft-entry/packed-float-single-scan/tools/gate.py build/java-diff-mc-packed-float-single-scan-build-07 build/java-diff-mc-packed-float-single-scan-fixtures-07 build/java-diff-mc-packed-float-single-scan-gate-07
python3 evidence/java-evm/minecraft-entry/packed-float-single-scan/tools/compare_p16.py build/java-diff-mc-packed-float-single-scan-build-07 build/java-diff-mc-packed-float-single-scan-fixtures-07 build/java-diff-mc-packed-float-single-scan-gate-07 direct-only
# Optional exhaustive fresh P16 q1/q7/direct baseline replay and gas report:
python3 evidence/java-evm/minecraft-entry/packed-float-single-scan/tools/compare_p16.py build/java-diff-mc-packed-float-single-scan-build-07 build/java-diff-mc-packed-float-single-scan-fixtures-07 build/java-diff-mc-packed-float-single-scan-gate-07 all-quanta
python3 evidence/java-evm/minecraft-entry/packed-float-single-scan/tools/gas_comparison.py build/java-diff-mc-packed-float-single-scan-build-07 build/java-diff-mc-packed-float-single-scan-gate-07 build/java-diff-mc-packed-float-single-scan-baseline-replay-07
python3 evidence/java-evm/minecraft-entry/packed-float-single-scan/tools/verify_results.py
```
