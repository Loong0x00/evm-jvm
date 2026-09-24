# P16 packed-float checkpoint cap-fallback follow-up

Follow-up to commit `0110df3d9` (`Optimize P16 packed-float checkpoint sizing`). This fixes the acceptance blocker where `_encodeMachine` compared `MAX_CHECKPOINT_BYTES` to the conservative upper reservation instead of the exact canonical MR01 size.

## Change

`_machineSize(..., false)` remains the fast first pass. Large rank-one `PRIMITIVE_FLOAT` arrays (length >=1024) reserve `43 + 4*length`, without counting float cells. If that reservation plus the 280-byte envelope header fits the 1,048,576-byte cap, encoding proceeds on the existing packed/sparse path with its one validating `_checkpointArrayNonzeroCount` scan; the packed P16 path therefore keeps the single-scan benefit.

Only when the upper reservation exceeds the cap, `_encodeMachine` calls `_machineSize(..., true)`. This exact mode scans and validates the float cells (including the existing uint32 bound), uses the unchanged P16 strict packed predicate and sparse fallback, then applies the cap to that exact size before allocation. The existing `at <= out.length`, final exact-output cap check, and shrink-to-`at` remain. Only `_machineSize` and `_encodeMachine` differ from accepted P16; the rest of the engine, including `_checkpointArrayNonzeroCount`, `_usePackedFloatArray`, wire decoding, authentication, and transport is byte-identical.

## Cap-boundary source/algebra controls

`tools/verify_source.py` mechanically verifies the false-mode first call, true-mode fallback ordering, exact-size cap check before allocation, validating scan, final output check/shrink, and that the source delta is limited to the two sizing/encoding functions. It independently reconstructs the unchanged 97-leaf P16 root. Its bounded algebra checks every possible nonzero count for lengths 1024, 1025, 2048, 32768, 65535, and 65536 (167,942 counts):

- If P16 selects packed, the exact record is the reserved `43 + 4*length` bytes.
- If packed loses, P16 necessarily selects sparse and the exact record `47 + 12*nonzero` is no larger than the reservation.
- With `length=65536`, a synthetic fixed remainder of 1,048,249 bytes, and zero nonzero cells, the upper envelope is 1,310,716 bytes (>cap), while the exact sparse envelope is exactly 1,048,576 bytes (at cap). The exact-mode branch accepts this sizing case.
- With the same fixed remainder and one nonzero cell, the exact sparse envelope is 1,048,588 bytes (12 bytes over cap), so the exact-mode cap check preserves refusal.

These are source-mechanical and algebraic controls. The synthetic fixed remainder does **not** prove that a corresponding guest state is reachable. No full-EVM near-cap positive or exact-over-cap fallback case was executed under the ordinary 1B LOCAL gas budget; the gate below is not represented as such a test.

## Verification run 06

- Fresh pinned Solidity build: engine runtime 392,176 bytes, SHA256 `39d6d33a7925a7ee015ea4502bc4c32ff2c6c83bd1e5ceec7a758c632504696d`, Keccak `775f179ebc3fa127438a315ab987ee2b502cd3ea9ef36e38eea29f869ff841ca`; runtime cap remains 393,216 bytes (1,040 bytes headroom). Candidate coordinator runtime SHA256 `0364573e1d85971a8ce260b053a6b1a4e421c200e4bd8bd5970ca5add8c86a18`.
- Full generated-only EVM gate at ordinary LOCAL 1B: **942.715 seconds**, 11,814 verified canonical receipts. This remains below the 1,200-second gate bound. It retains q1/q7/direct/reopen controls; packed raw-float oracle; the 341-tie/342-packed crossover; old sparse-float arrays; successful packed-checkpoint resume; all existing malformed packed/sparse atomic refusals; and retained P16/Object/Integer/Math/raw-boundary controls.
- Fresh accepted-P16 MR01 comparisons: all nine packed, crossover, and sparse payloads at q1/q7/direct are byte-identical, with matching SHA256 and Keccak (`results/opaque-equivalence-gate-06/`). The required direct-only comparison took 1.806 seconds; full gate plus this required equality check is 944.522 seconds. Supplemental all-quantum comparison took 614.038 seconds separately.
- Fresh baseline gas comparisons: all nine measurements remain positive, saving 307,770 to 9,950,820 gas (`results/generated-gas-comparison-gate-06.json`).
- Packed/sparse malformed-refusal atomicity and successful packed resume remained green. Exact float raw cells, sparse encodings, and the 341/342 crossover remain identical to accepted P16.

Durable summary: `results/cap-fallback-followup-gate-06.json`, `results/generated-gate-summary.json.gz`, `results/canonical-receipts.json`, `results/build-pins.json`, and `source-invariants.json`. `SHA256SUMS` covers the evidence directory. Run 04 remains preserved in its original suffixed summaries and opaque-comparison directories.

## Reproduction

The generated-only, offline commands used for run 06 are recorded in the previous task README; use new output IDs because scripts reject overwrites. No original Minecraft JAR/class/resource/world, sibling worktree, or network input was accessed. These tests establish only the bounded packed-float checkpoint-sizing result: no original Minecraft replay, EULA, world, or `Done` claim.
