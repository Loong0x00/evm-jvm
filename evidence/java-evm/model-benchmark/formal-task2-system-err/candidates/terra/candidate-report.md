# BENCHMARK_RESULT

## Result
BLOCKED — staged bounded `System.err`/`PrintStream` source and generated-only verifier are present, but no local pinned `solc`/`node_modules` exists in this isolated worktree. The sole build attempt stopped before compilation; no runtime or generated gate result is claimed.

## Files Changed
- `evidence/java-evm/minecraft-entry/system-err-preflight/` — staged engine/coordinator/driver templates, Java-8 `System` replacement, appended `PrintStream`, strict reverse verifier, and generated-only build/fixture/gate scripts.
- `evidence/java-evm/minecraft-entry/system-err-preflight/artifacts/` — source-verifier result and build-block evidence.

## Verification
- Successful source-only reverse verifier pinned to `parent-de60a3245`: 84 images; exactly 82 unaffected image bytes; Java-8 `System` (913 B) and `PrintStream` (134 B) hashes; raw30/fixed-limit constants; 14 exception kinds and 12 native bindings.
- One build attempt stopped before invoking Node because the required dependency directory is absent locally. The generated gate did not run.

## Remaining Uncertainty
- Runtime byte size (must be `<=393216`), artifact hashes, q1/q7/direct/reopen/canonical receipts, raw replacement/refusal behavior, and retained EnumSet/Enum/queue/OOM/boundary controls remain unverified until the pinned compiler dependencies are available inside this worktree.
- No PrintStream output/println behavior is implemented or claimed.
