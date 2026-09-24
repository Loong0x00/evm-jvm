# P17 packed-float grouped u32 checkpoint codec

This is a bounded candidate based only on the accepted P17 source at
`../parent-485ccd8d4/artifacts/engine/MCEntryInterpreter.sol`. The historical P17
artifact is unchanged. Only `_encodeMachine` and `_decodeMachine` differ in the
candidate engine; `tools/verify_source.py` normalizes those two function bodies
and proves the rest of the Solidity source is byte-identical.

## Implementation

- Encoding preserves the existing `_checkpointArrayNonzeroCount` validation and
  strict `_usePackedFloatArray` choice. It packs eight validated u32 cells into
  one big-endian 32-byte store; remaining cells use bounded four-byte `_put`
  writes, so a tail cannot overwrite the following record or exceed `out`.
- Decoding preserves `_requireCellBytes` before reading. It loads only complete,
  in-bounds 32-byte groups, reconstructs the ordinary eager dense `uint64[]`,
  counts nonzero cells, and uses bounds-checked `_get` for the tail. Existing
  nonzero-count and strict canonical rejection remain in place. There is no
  packed guest heap, lazy view, or alias representation.
- P17's strict packed/sparse wire selection, sizing/cap fallback, MR01 envelope,
  Java/bootstrap images, native bindings, heap/authentication, COPY, transport,
  and raw/checkpoint limits are unchanged. The coordinator's only source change
  is its immutable engine-code-hash pin for the candidate runtime.

## Verified result

Fresh pinned-solc builds reproduce the P17 reference and candidate independently.
The candidate runtime is **392,268 bytes / 393,216-byte cap** (948 bytes spare),
SHA-256 `c0d3be5e0af7bb0649ab802716970f91fab7a39965cb94677185942d416a8deb`,
Keccak-256 `5839b8e20b67c056268db041427350cbed00ba859779fee0217a04afb878a963`.
The P17 reference rebuild is 392,176 bytes with its pinned hash. The candidate
retains the same P17 domain and recomputes all 97 ordered bootstrap leaves; the
root remains `aae001d9449928180fe6daf66cc3a7bffa4686a7823f69bb994cd882fa89ec0d`.
A later clean build (`01-run-d`) reproduced identical engine/coordinator hashes,
verified identical engine ABI/storage layout, and verified the candidate coordinator
differs from P17 only by its immutable engine-codehash pin, with ABI unchanged.

The focused generated-only ordinary-LOCAL-1B gate passed in **450.436 seconds**
with **6,765 canonical receipts**. It exercised candidate q1/q7/direct terminal
reopen chains for packed arrays, lengths 1024/1025/1031 (including 1- and 7-cell
tails), and the exact generated raw-71 control; retained Integer, Object, and
Math controls; a successful q1 packed-checkpoint resume; old sparse arrays; and
six malformed atomic refusals. Every candidate MR01 byte stream is compared
across q1/q7/direct where applicable. Six direct-quantum generated cases
(packed, old sparse, crossover, and all three tail sizes) have byte-for-byte and
SHA-256 equality to a fresh P17 replay of the complete opaque `checkpoint[280:]`
MR01 machine payload. Envelope hashes are intentionally not compared across
runtime code hashes.

Direct ordinary-gas savings versus P17, summed over each generated case's
successful slices, were:

| Generated case | Gas saved |
| --- | ---: |
| packed float[1024] | 259,479 |
| old sparse-array stress | 1,763,952 |
| packed/sparse crossover | 281,161 |
| packed tail 1024 | 259,479 |
| packed tail 1025 | 259,561 |
| packed tail 1031 | 260,053 |

Malformed packed truncation, both flags, high-bit dense floats, and noncanonical
packed records refuse atomically with their expected `LC0StateError` codes.
Sparse truncation and noncanonical dense spelling also refuse atomically. The q1
packed resume decodes a prior packed record (parent epoch 1372, successful child
epoch 1373). The generated 71-class/471,911-byte aggregate reads all class bytes,
then retains the expected atomic ordinary-1B ceiling refusal without publishing
a checkpoint; it is not treated as an acceptance of a larger budget.

## Durable evidence

- `results/build-pins.json`: candidate/P17 runtime and coordinator hashes.
- `results/source-audit-01-run-d.json`: all 97 ordered leaf hashes and same-domain root.
- `results/generated-gate-summary.json`: q1/q7/direct, resume, malformed, capacity,
  receipt and gas results.
- `results/p17-mr01-equivalence.json`: byte/hash comparisons and gas deltas.
- `results/failure-ledger.json`: non-accepted exploratory attempts and corrections.
- `SHA256SUMS`: hashes for the tracked source, artifacts, tools, and results.

## Reproduction (generated fixtures only)

Dependencies and Go modules are offline/local-cache only; no network is required.
Build IDs/output paths are append-only and must be new on every run.

```sh
npm ci --prefix jvmevm/runtime --offline --ignore-scripts --no-audit --no-fund
python3 -B evidence/java-evm/minecraft-entry/packed-float-bulk-u32/tools/build.py 01-rerun-1
python3 -B evidence/java-evm/minecraft-entry/packed-float-bulk-u32/tools/focused_gate.py \
  build/java-diff-mc-packed-float-bulk-u32-build-01-rerun-1 \
  build/java-diff-mc-packed-float-bulk-u32-fixtures-01-rerun-1 \
  build/java-diff-mc-packed-float-bulk-u32-focused-01-rerun-1 01-rerun-1
```

`build.py` copies only the tracked generated Java-8 fixtures under
`float-packed-checkpoint-preparation/results/generated-gate-v5/fixtures`; it
creates the three tail variants by patching the generated fixture's two existing
`sipush 1024` operands and uses `RawFloatOracle.java` on those synthetic classes
for their float-bit expectations. `verify_source.py` records every ordered leaf
and verifies the P17 same-domain root. The gate verifies all successful candidate
ABI/event/checkpoint/counter receipts. Ignored `build/` outputs are disposable
reproduction intermediates; durable hashes and summaries are under `results/`.

## Scope and limitations

No original JAR, original class/resource input, world, EULA, original replay, or
Minecraft `Done` claim is part of this work. No sibling worktree, `/home/user/evm-jvm/geth`,
or network input was accessed. This is not a profile promotion or a claim that
Minecraft reached a later startup frontier.

An exploratory copy of the broader historical generated suite exceeded its
1,200-second ceiling and is not counted. The final bounded gate above is the
passing result; the earlier attempts and their harness-only corrections are
recorded in `results/failure-ledger.json`.
