# MR01 packed-float checkpoint candidate (preparation only)

## Result

Candidate based on `parent-56f2377a5` adds a canonical raw-u32 encoding for eligible rank-one primitive-float arrays. The checkpoint stores the IEEE-754 binary32 raw cells; decoding eagerly rebuilds the existing dense `uint64[]` guest representation. It does not alter Java bytecode execution or guest arrays. Existing sparse primitive-array encoding remains available and unchanged for arrays that do not qualify.

The implementation delta is limited to `_machineSize`, `_encodeMachine`, `_decodeMachine`, two private layout helpers and three constants in `engine/MCEntryInterpreter.sol`. The source gate independently verifies all 97 bootstrap RHS images/root, global native 19, String-local 12, raw limits 71/471911, and byte-identical canonical Go transport driver and coordinator against the P5 baseline. No VFS, AS0, ZI0, DI0, MR0, CB0, authentication or transport behavior was changed.

This is a generated-fixture candidate, **not a parent acceptance or Minecraft readiness claim**. No original server JAR/class/resource/world/EULA data was opened. No EULA was accepted; no world or `Done` milestone was reached. In particular, it does not establish that q1 is fatal or that float packing advances the original guest workload.

## Wire selection and refusal rules

The low 30 bits of the existing count word carry length. Bit 31 remains the sparse-pair flag; bit 30 marks packed float. Packed is selected only for rank-one float arrays of at least 1024 cells, only when every cell fits `uint32`, and only when its `4*length` payload is strictly smaller than sparse's `4 + 12*nonzero` payload. Ties retain the existing sparse/dense canonical spelling. The entire 32-bit raw float domain is preserved, including signed zero and NaN payload bits; cells are never numerically converted. Decode rejects both flags, wrong rank/type, short length, invalid count, truncated payload, a noncanonical density, and impossible high bits. Refusals preserve machine root, durable Head and logs.

At length 1024, 341 nonzero cells tie at 4096 payload bytes and remain sparse; 342 qualify for packed. The Java-8 oracle fixture has 348 nonzero raw cells: 4096 packed payload bytes versus 4180 sparse payload bytes, an 84-byte strict saving for that small witness. It includes custom quiet-NaN payload `0x7fc12345`, both infinities, both signed minimum subnormals, maximum finite, and negative zero.

## Generated measurements

The successful candidate gate is archived under [`results/generated-gate-v5`](results/generated-gate-v5/). Key measurements:

- Engine runtime: **388,691 bytes**, under the 393,216-byte cap (4,525 bytes remaining); baseline P5 runtime was 386,037 bytes. Bootstrap root: `1651f62e6a1d02c7fe9935f2944f04dbc12d1423e0a69ed44fa9a1e2a5334f3b`.
- Fresh generated-only gate: **569.088 seconds**, 5,376 canonical receipts (under the 1,200-second gate limit).
- Java-8 generated `float[1024]`: q1 1,406 JVM steps; q1/q7/direct and process-reopen checkpoint machine roots and opaque payload hashes agree. All 1,024 decoded `uint64` cells match the Java-8 oracle's raw bits exactly, including the listed nonfinite and subnormal edge patterns.
- A q1 continuation from the successful packed-array head commits its next epoch and reopens: 21,793,173 gas, 45 ms in the captured local run. This is a generated fixture measurement only, not a comparative original-server performance result.
- Packed malformed-wire cases (both flags, wrong rank/type, bad count, noncanonical density, truncated payload, and dense float high bits) refuse atomically. Old sparse malformed cases and retained String/Locale/Map/Integer/System/Math/Random/identity controls are included.
- Raw71/471911 reads all bytes but hits the current 1B local-call OOG before a checkpoint-cap verdict; this is **not** a 471911-byte checkpoint-cap acceptance. The 471912 boundary refusal remains separate.

Exact source/runtime pins, Java-8 ZIPs and raw oracle data, terminal q1/q7/direct checkpoint/head pairs, packed resume parent/child checkpoints, refusal receipts, and the complete compressed report/receipt set are covered by `results/generated-gate-v5/SHA256SUMS` and top-level `results/SHA256SUMS`. `tools/verify_results.py` checks archive hashes, fixture hashes, runtime pins, raw-bit equality, sparse compatibility, refusal atomicity, and report coverage. `generated-gate-v1` and `generated-gate-v2` are preserved archive-tool iterations over the same earlier successful gate; their embedded verifiers had harness assertion/path mistakes (including expecting one class where the fixture correctly contains two), not Solidity or gate failures. `generated-gate-v3` is the corrected earlier gate archive. `generated-gate-v4` contains the expanded raw-float edge witness; v5 archives the same byte-identical fixtures and successful gate with whitespace-clean reproduction tools. Use v5 as the canonical self-verifying archive. The immutable v1-v4 snapshots also retain a few trailing spaces in their captured generator source; v5 and the live source are clean. Do not rewrite those historical, checksummed copies.

## Reproduction

Run from the repository root. Use fresh, unused output names; scripts refuse to overwrite an existing run. Requires the pinned local Solidity toolchain/dependencies, Go toolchain, and OpenJDK 8:

```sh
python3 evidence/java-evm/minecraft-entry/float-packed-checkpoint-preparation/tools/verify_source.py
python3 evidence/java-evm/minecraft-entry/float-packed-checkpoint-preparation/tools/generate_fixtures.py build/java-diff-mc-float-packed-fixtures-N
python3 evidence/java-evm/minecraft-entry/float-packed-checkpoint-preparation/tools/build.py build/java-diff-mc-float-packed-build-N
python3 evidence/java-evm/minecraft-entry/float-packed-checkpoint-preparation/tools/gate.py build/java-diff-mc-float-packed-build-N build/java-diff-mc-float-packed-fixtures-N build/java-diff-mc-float-packed-gate-N > build/float-packed-gate-N.log
```

The test-only bounded-sine check reads the pinned generated Java-8 oracle under `evidence/java-evm/minecraft-entry/math-sin-independent-oracle/`; it has no execution authority. To archive a completed run, call `tools/archive_results.py BUILD FIXTURES GATE` with the three matching `build/java-diff-mc-float-packed-*` paths; the destination is append-only and refuses overwrite. Run `python3 evidence/java-evm/minecraft-entry/float-packed-checkpoint-preparation/tools/verify_results.py` to verify archived evidence. Failed older long-loop gate attempts are not acceptance evidence; only the archived explicit-assignment fixture gate counts.

## Pending

Parent must independently rebuild/replay this source and verify the gate before integration/acceptance. Any subsequent original-server replay is separately governed by the current local budget authorization and must resume only from a successful canonical checkpoint. The user expressly authorized LOCAL4.2B for unchanged original replay (at most 30s/call); ordinary generated calls retain their 1B ceiling. This is not a standard-chain claim. No push permission is implied.
