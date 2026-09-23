# Result: Math.sin signed zero (generated candidate)

- Added exact global binding 19 for `java/lang/Math.sin(D)D`: category-2 binary64 validation, identity-preserving `+0/-0`, and distinct atomic profile refusal for all other inputs. No general trigonometry was added.
- Regenerated the genuine Java-8 Math bootstrap image: 289 bytes, SHA-256 `da512cb22203c78ff49b4e8ae13075081c60a89e79897cb65d5581a391adea60`, Keccak `e354be66a6f5f6eecabb17b461000b63b90bea635f692a0cf0c36b6b5a688748`. The ordered source-derived 97-image root is `e8d2682b12ee29790e98011eb4745d7f41706d085b11c649de02faffd633efac`.
- Generated-only full gate passed in 428.149760 seconds with 3,091 independently re-encoded canonical receipts. Engine is 384,631 bytes, below the unchanged 393,216-byte limit. q1/q7/direct/reopen signed-zero and prior sqrt results agree. Sparse float[65536] q1 checkpoint/resume/reopen and prior sparse refusals, raw71/capacity and regression controls passed. Positive/negative finite values, NaN and both infinities return `MathSinProfileError(1,28)` with unchanged EVM root and byte-exact durable Head; no child slice is published after refusal.
- Durable evidence and hashes: `results/generated-gate-v1/` and `results/SHA256SUMS`.

**Important review caveat:** the inherited baseline pin says root `7e17be...`, but its checked-in P2 `_bootstrapRoot` expression and ordered images recompute to `7d5bb2...`. The candidate records this discrepancy and derives the new root from the actual P2 Solidity expression and exact ordered image bytes; see `root-commitment.json` and archived proof. Parent should independently review this inherited pin mismatch while rebuilding.

This does not claim parent acceptance, original replay, full sine, or Minecraft readiness. Parent alone performs the original replay and measures the next input.
