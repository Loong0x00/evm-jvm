# MAX_OBJECTS 4096 scoped P23 worker candidate

This bounded stage starts from the exact accepted P23 source
`parent-max-arrays-4096/artifacts/engine/MCEntryInterpreter.sol` and changes one
Solidity constant only:

```diff
-uint256 private constant MAX_OBJECTS = 2048;
+uint256 private constant MAX_OBJECTS = 4096;
```

`MAX_ARRAYS` remains 4096. `MAX_HANDLES` remains formula-derived as
`MAX_ARRAYS + MAX_OBJECTS + MAX_EXCEPTION_OBJECTS + 1`, evaluating to 8449.
The candidate retains the P23 domain labels; this worker does not relabel them.
No other interpreter limits, checkpoint/wire format, bootstrap images, Java
semantics, or ABI/storage fields are changed.

## Source/build audit

`artifacts/source-audit.json` records the exact base/candidate hashes, all 97
ordered bootstrap leaf identities and same-domain P23 root, fresh pinned compiler
output, and ABI/storage-layout equality. The base source SHA-256 is
`99de296ccbbdb1fe2890b52a70f9c217690fa858c443ccec7d0028963ccbbbd6`; the candidate
source SHA-256 is `4e4e404209eb21581785aa02254f11dd0ad8f070fe5c1768e1cc25b6134406d1`.
The root remains
`3488aad418a50e641220126a44a1b5dd9ce190505611a0f20f50e8814311a33c`.
Pinned solc is `0.8.30+commit.73712a01.Emscripten.clang`, loaded offline from the
already provisioned `jvmevm/runtime/node_modules`. Candidate runtime is 392090
bytes against the 393216-byte ceiling; ABI and storage layout match the accepted
P23 source exactly. The coordinator harness changes only its immutable engine
code-hash pin. A test-only `resume-one-q` driver mode is added for the smaller-q
blocker diagnostic; it does not change the 1B gas budget or EVM code.

## Generated object capacity result: BLOCKED at 1B gas

The fixtures are generated Java-8 zero-field `java/lang/Object` allocations, with
class-file ZIP entry names including `.class`. Durable class/ZIP hashes and
fixture-generation expectations are in `artifacts/generated-capacity-fixtures-worker3.json`.
No guest program is run on the host.

The q4096 ordinary-1B preflight completed and reopened targets 2048 and 2049.
They contain exactly 2048/2049 ordinary objects, zero ordinary fields, one
implicit `main(String[])` ordinary array, and zero array elements; both finish
successfully with Java kind 0. The capacity runs do not claim high-count q1/q7.

The requested 4096-object completion is **blocked before reaching the object
cap**. At the q4096-configured world, a full q4096 resume hits an ordinary-1B
EVM out-of-gas refusal at epoch 7 / 28672 Java steps with 2867 ordinary objects
(gas 984377212); durable Head and root remain unchanged. A diagnostic sequence of
q256 resume slices advances to 2995 objects (epoch 12 / 29952 Java steps), then
also refuses at 984377271 gas with Head/root unchanged. Its reopened checkpoint
is 130406 bytes, below the unchanged 1 MiB checkpoint cap. Thus the measured
blocker is per-call gas, not the checkpoint-size cap. Target4097 is not attempted,
and no guest OutOfMemoryError at the new limit is claimed. See
`artifacts/capacity-preflight-summary-worker8.json` and
`artifacts/capacity-gas-blocker-worker8.json` for receipts, counters, roots, and
atomic refusal details. Do not infer guest OOM from EVM OOG.

The retained generated packed/sparse/malformed/Integer/Object/Math/raw71 gate
passes: 11814 canonical receipts across 60 q1/q7/direct worlds in 940.688 seconds
(under the 1200-second ceiling). An additional 42 malformed-checkpoint q1/q7/q4096
probes pass with Head/root/logs unchanged; maximum measured call gas is 505392827.
Durable summaries are `artifacts/full-generated-gate-summary-worker4.json.gz` and
`artifacts/malformed-quantum-summary-worker3.json`.

This is a worker candidate with an unresolved required capacity preflight, not
parent acceptance. Parent review/build and the separate fresh-domain untouched
original max-gas replay remain pending. No original Minecraft JAR/classes,
original world, EULA acceptance, Minecraft replay, `Done`, or readiness claim is
part of this worker task.

## Reproduction

Run from this repository root. Use fresh unique names; outputs are append-only.
The compiler and `js-sha3` must already exist in the local runtime `node_modules`;
no npm install or network access is used.

```sh
export NODE_PATH="$PWD/jvmevm/runtime/node_modules"
python3 evidence/java-evm/minecraft-entry/max-objects-4096/rebuild.py \
  "$PWD/build/java-diff-mc-max-objects-4096-build-<run>"
python3 evidence/java-evm/minecraft-entry/max-objects-4096/generate_fixtures.py \
  "$PWD/build/java-diff-mc-max-objects-4096-fixtures-<run>"
python3 evidence/java-evm/minecraft-entry/max-objects-4096/capacity_preflight.py \
  "$PWD/build/java-diff-mc-max-objects-4096-build-<run>" \
  "$PWD/build/java-diff-mc-max-objects-4096-fixtures-<run>" \
  "$PWD/build/java-diff-mc-max-objects-4096-preflight-<run>"
python3 evidence/java-evm/minecraft-entry/max-objects-4096/full_generated_gate.py \
  "$PWD/build/java-diff-mc-max-objects-4096-build-<run>" \
  "$PWD/build/java-diff-mc-max-objects-4096-fixtures-<run>" \
  "$PWD/build/java-diff-mc-max-objects-4096-gate-<run>"
python3 evidence/java-evm/minecraft-entry/max-objects-4096/malformed_quantum_gate.py \
  "$PWD/build/java-diff-mc-max-objects-4096-build-<run>" \
  "$PWD/build/java-diff-mc-max-objects-4096-fixtures-<run>" \
  "$PWD/build/java-diff-mc-max-objects-4096-gate-<run>" \
  "$PWD/build/java-diff-mc-max-objects-4096-malformed-<run>"
python3 evidence/java-evm/minecraft-entry/max-objects-4096/archive_receipts.py \
  "$PWD/build/java-diff-mc-max-objects-4096-preflight-<run>" \
  "$PWD/build/java-diff-mc-max-objects-4096-gate-<run>" \
  "$PWD/evidence/java-evm/minecraft-entry/max-objects-4096/artifacts/ordered-receipt-hashes-<run>.json.gz"
```
