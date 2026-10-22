# P41 array-count capacity doubling (candidate)

## Scope and base

This is the bounded `MAX_ARRAYS` change on the exact accepted P39 source-only snapshot at `../max-arrays-8192-source-base-p39/`. The nine snapshot files were checked against `source-manifest.json` before edits (all SHA-256 and byte lengths matched). The source base commit is `9456cf9ad7116f0436acaf53416c51f74d7f3428`; the candidate was compiled from that snapshot, not from a stale VM artifact or another worktree. No original Minecraft input or parent execution evidence was read or used.

**Only guest heap quota changed:** `MAX_ARRAYS: 4096 -> 8192`. `MAX_HANDLES` remains derived from arrays + objects + exception objects + the emergency handle, so it now evaluates to `12545` (previously `8449`) to provide registry slots for the larger array quota. This is coupled capacity, not a changed object quota. The heap array counter is encoded in 16 bits; `8192 <= 65535`. Dense eager arrays and checkpoint schema/codec are unchanged.

Unchanged: `MAX_OBJECTS=4096`, `MAX_ARRAY_ELEMENTS=262144`, `MAX_CONSTANT_POOL=4096`, `MAX_RAW_CLASSES=150`, `MAX_RAW_BYTES=1063930`, runtime cap `1048576`, checkpoint cap `2097152`, frame cap `128`, reserve `25000000`, quantum max `65536`, internal steps max `4096`, bootstrap image count/order/bytes, exception behavior, ABI, storage layout, and EVM charging/consensus rules. No lazy/truncated/sparse array representation was introduced. P39 `DBOOT` is intentionally byte-for-byte unchanged; other package/profile domains are versioned `P41-ARRAY-8192` so new-capacity state/code is distinguished.

## Source/build proof

`results/source-audit.json` is a fresh offline solc build comparison of exact P39 source vs candidate engine and coordinator. It records:

- all 105 ordered bootstrap leaves and root preserved; root `ca3049ae9ad4e09e893a897c34ef016939d1595c01d090c5ee3e9699ac349fbd`;
- engine and coordinator ABI/storage layout equal to freshly compiled P39;
- runtime `418986` bytes (under LOCAL1M), SHA-256 `32a16b78a9cec4b72835eaab094c715e3a5f310ed9f2b211d49e29237c5b5f02`, Keccak `ee8a4ee454fed308072ac87510eab964a1ae816af5a2109706ad1206693fe277`;
- only engine constant/profile-domain edits, with DBOOT untouched; coordinator changes are profile domains and the pinned new engine codehash.

Coordinator runtime: `5411` bytes, SHA-256 `a89f68c52a8fa4b49f103add3ece3f48619432628641a49a13babea10835d695`, Keccak `d2a74f94190e6a565595b5af71855a40ec3cd1b0493fedcd439d1a96ce47bbc7`. `pins.json` and candidate `source-manifest.json` record exact inputs/artifacts.

## Generated execution evidence

All workload classes are generated locally by Java 8 from `generate_capacity_fixtures.py`; the Java code allocates an outer `Object[]`, creates/stores distinct ordinary zero-length `int[]` objects in it, and reads the references back. It does not use unsupported `multianewarray`. The implicit `main(String[])` array is counted. Binary names include `.class`. Fixture source, class hashes, and ZIP hashes are under `fixtures/generated-java8/`.

`results/capacity-boundaries.json` comes from the public local EVM driver at q4096, ordinary local-test allowance 32B, with setup, continuation, and distinct-process verify/reopen. The final checkpoint parser counted every explicit dense ordinary-array record and preserved reference-array handles; no sparse or packed/lazy array record is accepted.

| Requested arrays | Ordinary arrays | Ordinary objects | Array elements | Terminal | Java kind | Checkpoint bytes |
|---:|---:|---:|---:|---|---:|---:|
| 4096 | 4096 | 0 | 4094 | successful guest void | 0 | 210782 |
| 4097 | 4097 | 0 | 4095 | successful guest void | 0 | 210833 |
| 8192 | 8192 | 0 | 8190 | successful guest void | 0 | 419678 |
| 8193 | 8192 | 0 | 8191 | genuine terminal guest OOM | 7 | 419793 |

All terminal records were reopened in a separate driver process. For the OOM row, the authenticated emergency exception object is separate from ordinary arrays. All successful arrays and reference aliases survived checkpoint restore. The unchanged object and element caps are isolated: zero ordinary objects and at most 8191 array elements in these boundary workloads.

`results/p39-4097-regression.json` rebuilds and executes the exact P39 source snapshot with generated-only input: requested 4097, actual 4096 arrays, terminal Java kind 7 OOM, 0 ordinary objects, 4095 array elements, and a separate-process verify. Thus P39's real shortage remains and P41 accepts the same workload.

`results/schedule-equivalence.json` runs the small 8-array generated fixture at q1, q7, and q4096, each with public checkpoint/reopen. Machine root, VFS root, heap counters, dense records, and alias cells match exactly; checkpoint bytes/roots may differ by schedule.

## Local execution budget measurement

A generated large checkpoint chain needs more local test-driver gas than the formerly established 1B allowance. Preserved failures are in `results/budget-failures.json`: calls at 1B/2B/4B (4096 target) and 8B/16B (8192 target) reverted near the supplied budget; each failed call left the committed durable Head byte-identical. After each measured failure the disposable generated-test allowance was coherently doubled, ending at 32B, where all four P41 boundaries completed. This is a test-driver-only finite local allowance; no engine/EVM gas rule, gas accounting, reserve, EVM core, or consensus parameter changed. Do not interpret this as a higher-budget general profile claim.

## Reproduction

From `/home/user/evm-jvm/max-arrays-8192`, offline:

```sh
export NODE_PATH=/home/user/evm-jvm/max-arrays-8192/jvmevm/runtime/node_modules
export GOPROXY=off GOSUMDB=off GOTOOLCHAIN=local
python3 evidence/java-evm/minecraft-entry/max-arrays-8192/source_audit.py
python3 evidence/java-evm/minecraft-entry/max-arrays-8192/build_harness.py /home/user/evm-jvm/max-arrays-8192/build/java-diff-mc-max-arrays-8192-build-REPRO
python3 evidence/java-evm/minecraft-entry/max-arrays-8192/generate_capacity_fixtures.py /home/user/evm-jvm/max-arrays-8192/build/java-diff-mc-max-arrays-8192-fixtures-REPRO
python3 evidence/java-evm/minecraft-entry/max-arrays-8192/capacity_gate.py /home/user/evm-jvm/max-arrays-8192/build/java-diff-mc-max-arrays-8192-build-REPRO /home/user/evm-jvm/max-arrays-8192/build/java-diff-mc-max-arrays-8192-fixtures-REPRO /home/user/evm-jvm/max-arrays-8192/build/java-diff-mc-max-arrays-8192-gate-REPRO
python3 evidence/java-evm/minecraft-entry/max-arrays-8192/schedule_smoke.py /home/user/evm-jvm/max-arrays-8192/build/java-diff-mc-max-arrays-8192-build-REPRO /home/user/evm-jvm/max-arrays-8192/build/java-diff-mc-max-arrays-8192-fixtures-REPRO /home/user/evm-jvm/max-arrays-8192/build/java-diff-mc-max-arrays-8192-schedule-REPRO
```

`p39_control.py` additionally rebuilds the exact supplied P39 source-only baseline and reproduces its 4097-array terminal OOM. Build/test attempts are append-only; use unique `REPRO` suffixes. No original Minecraft data/JAR/classes/resources/worlds/checkpoints/receipts, EULA acceptance, `Done` claim, push, or consensus change is involved.

This is a worker candidate and reproducible local evidence, not parent acceptance. Parent owns the independent build/checks and original-data execution. The retained HashMap/array-clone/String replacement suite was not rerun here; the candidate's only semantic change is the count bound, and those gates remain for independent parent verification.
