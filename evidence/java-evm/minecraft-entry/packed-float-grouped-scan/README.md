# P18 grouped float checkpoint validation scan

## Scope

This candidate changes exactly one function in the assigned P18 source:
`_checkpointArrayNonzeroCount` in
`../parent-e23eea569/artifacts/engine/MCEntryInterpreter.sol`. Its rank-one
`PRIMITIVE_FLOAT` path loads eight in-bounds `uint64[]` words per outer loop,
validates the complete group before counting, and uses the unchanged checked tail.
Each valid array cell is read once per scan. Values are narrowed to the stored
`uint64` domain before high-bit validation, preserving the prior typed
`LC0StateError(6, handle)` for bits above uint32 and the exact nonzero count.
The non-float/rank fallback is unchanged.

The guest heap stays eager and dense. Packed/sparse selection, grouped packed-u32
encoding/decoding, the single-scan/cap fallback, MR01 bytes, all 97 bootstrap
images, Java code, bindings, heap/authentication, COPY and transport are unchanged.
The fresh source audit proves `_checkpointArrayNonzeroCount` is the only changed
Solidity function and independently recomputes all 97 ordered bootstrap leaves
in the P18 domain.

## Verification

The durable run is [`results/01-local-b/`](results/01-local-b/). It records source
and artifact pins, the all-97 root audit, complete compressed focused/full gate
summaries, the direct-helper result matrix, and SHA256SUMS. Verify the package
with `sha256sum -c SHA256SUMS` from this directory, then verify the run files
with `sha256sum -c SHA256SUMS` from `results/01-local-b`.

- Candidate runtime: **392,090 bytes**, under the unchanged **393,216-byte** cap
  (1,126 bytes remaining; 178 bytes smaller than the 392,268-byte P18 baseline).
  Runtime SHA-256: `ac229a2cd8e92360bbde140ba9e6fe856891b03cec8ba390de5b9bab8a109e33`.
- Same-domain P18 bootstrap root: `828af33f62f6e92513d9605bf832437e1330b4d325bb04f913b97fd6f20596bd`,
  independently reconstructed from all 97 source leaves.
- Focused generated-only ordinary-1B gate: **444.539 seconds**, **6,765 verified
  canonical receipts**. It covers q1/q7/direct plus process reopen, lengths
  1024/1025/1031 tails, successful packed resume, malformed atomic refusals,
  old sparse/crossover records, retained Integer/Object/Math and raw71 controls.
  All six opaque MR01 payload comparisons to the exact pre-scan P18 baseline are
  byte-for-byte equal. The 471,911-byte generated raw71 probe reads all class bytes
  and retains the expected atomic ordinary-1B refusal; it is not a cap acceptance.
- Direct helper gate: **231.996 seconds**, ordinary 1B per EVM call, **14 exact
  count/selection cases** and **16 typed refusals**. It covers zero/mixed/full
  uint64 vectors at every length 1024/1025/1031, small boundary lengths, high-bit
  group lanes 0..7, and all eight tail positions across lengths 1025/1031. Every
  high-bit case returns the exact `LC0StateError(6,37)` selector and arguments.
  This uses a disposable test-only Solidity wrapper and does not alter the
  candidate artifact. Its 393,308-byte instrumented runtime is not a deployment
  artifact; the uninstrumented candidate remains 392,090 bytes.
- Retained full generated-only ordinary-1B gate: **939.226 seconds**, **11,814
  verified canonical receipts**. The full result is compressed in the run archive.

The focused direct-gas deltas versus the exact pre-scan P18 baseline are:
packed oracle **233,682**, sparse stress **13,042,610**, crossover **917,682**,
and tails 1024/1025/1031: **233,682 / 233,776 / 234,340** gas saved.

## Reproduction

All outputs are append-only; choose a new run ID and fresh output paths. Use the
local compiler cache only. The reproduction uses generated fixtures checked into
the repository and Go's offline module cache; it does not download inputs.

```sh
npm ci --prefix jvmevm/runtime --offline --ignore-scripts --no-audit --no-fund
python3 -B evidence/java-evm/minecraft-entry/packed-float-grouped-scan/build.py 01-rerun-a
python3 -B evidence/java-evm/minecraft-entry/packed-float-grouped-scan/focused_gate.py \
  build/java-diff-mc-packed-float-bulk-u32-build-01-rerun-a \
  build/java-diff-mc-packed-float-bulk-u32-fixtures-01-rerun-a \
  build/java-diff-mc-packed-float-bulk-u32-focused-01-rerun-a 01-rerun-a
python3 -B evidence/java-evm/minecraft-entry/parent-e23eea569/full_generated_gate.py \
  build/java-diff-mc-packed-float-bulk-u32-build-01-rerun-a \
  build/java-diff-mc-packed-float-bulk-u32-fixtures-01-rerun-a \
  build/java-diff-mc-packed-float-bulk-u32-gate-01-rerun-a
python3 -B evidence/java-evm/minecraft-entry/packed-float-grouped-scan/probe_gate.py \
  build/java-diff-mc-packed-float-bulk-u32-build-01-rerun-a \
  build/java-diff-mc-packed-float-grouped-scan-probe-01-rerun-a
```

Each gate enforces its 1,200-second timeout. `build.py` reconstructs the baseline
from the assigned `f867e6279` source and refuses any source delta beyond the
specified helper; it compiles both engines/coordinators independently. The probe
gate instruments only a disposable source copy to call the private helper with
synthetic arrays; the expanded compiler byte guard applies only to that direct
runtime-execution probe, never to the candidate engine.

## Limits

These are generated-only implementation and throughput tests, not a Minecraft
replay or readiness milestone. No original JAR/classes/resources/worlds were
used; no original replay, logger/world/EULA/`Done`, standard-chain, or push claim
is made. No sibling worktree, `/home/user/evm-jvm/geth`, or network was accessed.
