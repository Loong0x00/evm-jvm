# Sparse primitive-array checkpoint candidate (generated-only)

This is the isolated candidate for `JAVA_EVM_MC_SPARSE_PRIMITIVE_ARRAY_CHECKPOINT_PREPARATION.md`; it changes only the checkpoint wire layout in `_machineSize`, `_encodeMachine`, and `_decodeMachine`. The accepted guest heap representation and Java semantics remain dense/ordinary: decoding allocates the full `uint64[]` array and fills the indexed nonzero cells before the machine can execute another JVM instruction.

## Canonical wire rule

For rank-1 primitive arrays with length at least 1024, the existing uint32 element-count word uses its high bit as a sparse discriminator. Low 31 bits are the unchanged logical length, followed by a uint32 nonzero count and sorted `(uint32 index, uint64 value)` pairs. The encoder chooses sparse form only when `(4 + 12*N)*4 <= (8*L)*3`, i.e. its record is at most 75% of the dense primitive-cell payload. All other arrays retain the exact old dense spelling. The decoder rejects sparse rank/type/length violations, excess count, truncation, zero values, duplicate/unsorted/out-of-range indexes, and sparse encodings that fail the strict saving rule. Re-encoding then rejects a valid-looking dense alternate spelling when sparse form is canonical.

No bootstrap image/root, raw-class/byte/diagnostic limit, binding, coordinator, VFS, CB0/session path, opcode accounting, or accepted engine limit changes. Candidate runtime is 385803 bytes under the unchanged 393216-byte LOCAL cap; bootstrap root remains `7e17be3151d9b2aa8b0fd0686069824995e772be6a4a6b41876ee4918812e887`. The harness stays at the currently authorized 1B ordinary LOCAL call ceiling and 30-second per-call timeout; it does not use a failed call as continuation evidence.

## Generated-only gate

The Java-8 fixture creates an actual `float[65536]` plus `int[65536]` and `double[65536]` arrays (respectively all zero, one nonzero at the last cell, and three distant nonzeros), then resumes and reads/mutates ordinary restored arrays. Small primitive, dense primitive, and reference arrays remain dense. A second fixture exercises the exact threshold: 511/1024 nonzero cells select sparse form; 512/1024 remain dense. q1/q7/direct terminal machine roots and opaque payloads agree, each world is reopened/verified, and the q1 chain proves an authenticated successful parent checkpoint containing a 65536-cell array was followed by a successful resume (epoch 2→3; 188797004 gas, 393 ms under the 1B/30s harness bounds).

The gate also verifies zero/duplicate/out-of-order/out-of-range/count/undersized/truncated sparse refusals and a rehashed noncanonical dense representation. Each refusal is an EVM `LC0StateError` with unchanged EVM root, durable Head, and logs. Retained Math/String/Locale/Map/Integer/System/identityHashCode/Random-construction and raw71/capacity controls are included. Full generated gate: 367.248 seconds, 3068 independently re-encoded canonical successful receipts; runtime and pins are recorded in `results/generated-gate-v1/` and authenticated by its `SHA256SUMS`.

**Important boundary caveat:** under the current 1B ordinary call cap, the generated 471911-byte raw71 fixture is admitted and all 471911 class bytes are read, but the call exhausts gas before reaching the historical 1MiB checkpoint-cap selector (empty revert, root unchanged, no candidate checkpoint). This is explicitly classified as a non-acceptance, not a successful boundary/refusal proof. The 471912-byte coordinator rejection remains exact. Do not infer 1MiB-cap acceptance from the 471911 OOG probe.

## Reproduce / inspect

From repository root, with the pinned local Node dependencies already present (no network):

```sh
python3 evidence/java-evm/minecraft-entry/sparse-primitive-array-checkpoint-preparation/tools/verify_source.py
python3 evidence/java-evm/minecraft-entry/sparse-primitive-array-checkpoint-preparation/tools/build.py build/java-diff-mc-sparse-array-build-<unique>
python3 evidence/java-evm/minecraft-entry/sparse-primitive-array-checkpoint-preparation/tools/generate_fixtures.py build/java-diff-mc-sparse-array-fixtures-<unique>
python3 evidence/java-evm/minecraft-entry/sparse-primitive-array-checkpoint-preparation/tools/gate.py build/java-diff-mc-sparse-array-build-<unique> build/java-diff-mc-sparse-array-fixtures-<unique> build/java-diff-mc-sparse-array-gate-<unique>
```

`verify_source.py` normalizes only the three checkpoint functions and sparse helpers back to the pinned `parent-511c20c4b` source, and proves bootstrap bodies/root remain identical. The archive includes exact generated class ZIPs, terminal and intermediate checkpoints, machine proof summaries, malformed refusal receipts, runtime hashes, and canonical receipt verification. Disposable `build/` worlds/logs are not acceptance evidence by themselves.

This candidate has not received parent independent rebuild/review or original Minecraft replay. No original JAR/class/resource/world/EULA data was opened or run. It is not an accepted profile, a Minecraft readiness result, or a claim that startup is complete; the parent alone performs the original replay.
