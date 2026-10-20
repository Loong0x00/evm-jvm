# MAX_ARRAYS 4096 worker candidate

This isolated worker candidate changes exactly one semantic source constant in the accepted P22 engine:

```diff
-uint256 private constant MAX_ARRAYS = 2048;
+uint256 private constant MAX_ARRAYS = 4096;
```

`MAX_OBJECTS` remains 2048; `MAX_HANDLES` remains derived and evaluates to 6401. All other caps, images, ABI, and storage layout are unchanged. The worker candidate deliberately retains the P22 domain labels; the parent chooses any fresh acceptance domain separately.

## Build/source audit

- Solidity compiler: pinned `0.8.30+commit.73712a01.Emscripten.clang`, loaded offline from `jvmevm/runtime/node_modules` through `NODE_PATH`.
- Engine runtime: 392090 bytes (cap 393216), SHA-256 `980c57efa68750a161adcac3864f2bd1dcdff53b0d06e9d1c81748f02349ddac`.
- Derived handles: 6401.
- The independently recomputed ordered 97-leaf bootstrap root remains `663211851e33185b08b0616167ddc3c37ae6789c161de4cd19515e4192f8c1a9`; source-leaf fingerprints match P22.
- Full compiled ABI and storage layout compare equal to a fresh offline build of the preserved P22 engine source. `artifacts/source-build-audit-rerun.json` records a fresh byte-for-byte candidate compilation as well as the ABI/layout comparison; `source-build-audit.json` preserves the first build audit.

## Generated ordinary-1B capacity preflight

Four generated Java-8 fixtures were executed through the public local driver with q4096, ordinary gas ceiling 1,000,000,000, and fresh setup/finish/reopen chains. Requested totals include the implicit canonical empty `main(String[])` array. Results are in `artifacts/capacity-preflight-summary.json`:

| Requested total arrays | Actual ordinary arrays | Terminal | Java kind |
|---:|---:|---|---:|
| 2048 | 2048 | successful VOID | 0 |
| 2049 | 2049 | successful VOID | 0 |
| 4096 | 4096 | successful VOID | 0 |
| 4097 | 4096 | guest OutOfMemoryError | 7 |

The 4097 terminal's authenticated exception heap record is handle 4098, class index 10 = binding count 1 + OOM bootstrap leaf index 9. `javaClass` intentionally remains empty. ZIP binding names include `.class`. Four worlds have 25 independently canonicalized successful receipts; peak measured call gas is below 98M, and every checkpoint was reopened and its heap counters checked.

High-count capacity cases use q4096 only. There is no q1/q7 high-count capacity claim. The retained semantic controls use q1/q7/direct as described below.

## Retained generated gate

`artifacts/full-generated-gate-summary.json.gz` (inspect with `gzip -dc`) records the retained packed-float, sparse-array, malformed-checkpoint, Integer, Object, Math, locale/String/system/property, and exact raw-71 controls. It completed in 1005.83 seconds (within the 1200-second gate) with 11814 canonical successful receipts across 60 q1/q7/direct worlds. These controls use the existing ordinary 1B cap and each terminal world is reopened. Packed/sparse malformed checkpoint refusals and raw-count refusal controls are also recorded. `artifacts/malformed-quantum-summary.json` preserves the first 42 packed/sparse malformed-checkpoint refusal probes across q1/q7/q4096; `malformed-quantum-summary-run2.json` is the isolated-copy rerun. Both confirm root, durable Head, and logs stay unchanged (max call gas about 493.2M). `artifacts/ordered-receipt-hashes.json.gz` keeps ordered hashes/counters for the 25 capacity and 11814 retained receipts, without checkpoint/world bytes.

All execution inputs here are generated test fixtures. No original Minecraft JAR/classes/resources, original world/checkpoint, EULA acceptance, original-server replay, `Done`, or readiness claim is included. This is worker evidence, not independent parent acceptance.

## Reproduction

Run from the repository root; use a fresh unique suffix under `build/` for each run. Do not run `npm ci` or access the network.

```sh
export NODE_PATH="$PWD/jvmevm/runtime/node_modules"
python3 evidence/java-evm/minecraft-entry/max-arrays-4096/rebuild.py "$PWD/build/java-diff-mc-max-arrays-4096-audit-<run>.json"
python3 evidence/java-evm/minecraft-entry/max-arrays-4096/build_harness.py "$PWD/build/java-diff-mc-max-arrays-4096-build-<run>"
python3 evidence/java-evm/minecraft-entry/max-arrays-4096/generate_fixtures.py "$PWD/build/java-diff-mc-max-arrays-4096-fixtures-<run>"
python3 evidence/java-evm/minecraft-entry/max-arrays-4096/capacity_preflight.py "$PWD/build/java-diff-mc-max-arrays-4096-build-<run>" "$PWD/build/java-diff-mc-max-arrays-4096-fixtures-<run>" "$PWD/build/java-diff-mc-max-arrays-4096-preflight-<run>"
python3 evidence/java-evm/minecraft-entry/max-arrays-4096/full_generated_gate.py "$PWD/build/java-diff-mc-max-arrays-4096-build-<run>" "$PWD/build/java-diff-mc-max-arrays-4096-fixtures-<run>" "$PWD/build/java-diff-mc-max-arrays-4096-gate-<run>"
python3 evidence/java-evm/minecraft-entry/max-arrays-4096/malformed_quantum_gate.py "$PWD/build/java-diff-mc-max-arrays-4096-build-<run>" "$PWD/build/java-diff-mc-max-arrays-4096-fixtures-<run>" "$PWD/build/java-diff-mc-max-arrays-4096-gate-<run>" "$PWD/build/java-diff-mc-max-arrays-4096-malformed-<run>"
test ! -e "$PWD/evidence/java-evm/minecraft-entry/max-arrays-4096/artifacts/full-generated-gate-summary-<run>.json.gz"
gzip -n -9 -c "$PWD/build/java-diff-mc-max-arrays-4096-gate-<run>/summary.json" > "$PWD/evidence/java-evm/minecraft-entry/max-arrays-4096/artifacts/full-generated-gate-summary-<run>.json.gz"
python3 evidence/java-evm/minecraft-entry/max-arrays-4096/archive_receipts.py "$PWD/build/java-diff-mc-max-arrays-4096-preflight-<run>" "$PWD/build/java-diff-mc-max-arrays-4096-gate-<run>" "$PWD/evidence/java-evm/minecraft-entry/max-arrays-4096/artifacts/ordered-receipt-hashes-<run>.json.gz"
```

`generate_fixtures.py` reuses only the repository's previously generated packed/sparse fixture set and test-only Java-8 oracle source, then emits new array-capacity fixtures. Test worlds, ZIPs, class files, and checkpoints are disposable `build/` intermediates; durable reports, source, and hashes are kept in this directory.
