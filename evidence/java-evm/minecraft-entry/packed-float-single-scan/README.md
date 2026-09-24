# P16 MR01 packed-float single-scan checkpoint optimization

## Result

Implemented the measured representation-preserving optimization on the exact accepted P16 engine source at `../parent-50541377b/artifacts/engine/MCEntryInterpreter.sol` (baseline SHA256 `e53932817b1537f0e06911e4114a2995d1bcf12c946c6529accaa3d75bb1d849`). Only `_machineSize` and `_encodeMachine` differ. The old packed/sparse wire selection, cell validation, eager decode, heap representation, roots, authentication and transport remain unchanged.

For precisely rank-one `PRIMITIVE_FLOAT` arrays of length at least 1024, `_machineSize` now reserves `43 + 4*length` without counting cells. `_encodeMachine` retains one `_checkpointArrayNonzeroCount` pass, which validates each cell's uint32 range and supplies the exact nonzero count for the historical strict selection. The bound follows directly:

- If packed wins, `4*length < 4 + 12*nonzero`; the serialized array record is exactly `43 + 4*length` bytes.
- Otherwise `4*length >= 4 + 12*nonzero`; the unchanged sparse predicate must accept this array, and its record size `47 + 12*nonzero` is no greater than the reservation `43 + 4*length`.

All other arrays retain their existing exact size calculation. After encoding the VFS tail, the function asserts `at <= out.length`, checks the actual serialized length against `MAX_CHECKPOINT_BYTES`, and then shrinks the `bytes` length to `at`. The cap check is based on actual output rather than the sparse-float upper reservation, avoiding false rejection near the checkpoint limit. No decoder or Java bytecode behavior changed.

## Verification

- Fresh P16 baseline compilation reproduces the accepted runtime exactly: 389,579 bytes, SHA256 `1c6390652b8eca5496cfca277fb1b6488eeacb8ef980e5770eea6ff79d98e050`.
- Candidate engine: 389,818 bytes (3,398 bytes below the 393,216-byte local cap), runtime SHA256 `ef6614d67b1d7a81877a2705de4361d0c2ecb43818e4ac002cbc6510ecff4be5`, Keccak `092371814f0714f41278b1901d183dbfaf4350437c118b8747d2046988264ed5`.
- Independently reconstructed P16 bootstrap root remains `8c5bc495513b12e7ee40f71f447c5f8f894d49ec9cf318d2744143f1d20ff310`; all 97 ordered leaves and image materializers are byte-identical. P16 global native bindings (21), String-local binding (12), raw class/byte limits (71/471911), Object/Integer/Math code, and coordinator/transport source are unchanged apart from the candidate coordinator's immutable engine code-hash pin.
- Generated-only gate used ordinary LOCAL 1B. It completed in 963.171 seconds (963.207 seconds measured wall), verified 11,814 canonical receipts, and passed q1/q7/direct/reopen, the generated Java-8 float[1024] raw-bit oracle, 341-tie/342-packed crossover, old sparse arrays, successful packed-checkpoint resume, malformed packed/sparse atomic refusals, retained Object/Integer/Math controls, and the raw71/471911 boundaries. The exact 471911-byte witness reads all bytes but reaches the existing 1B OOG before a checkpoint-cap result; this is **not** a checkpoint-cap acceptance.
- The required full candidate gate plus direct accepted-P16 MR01 equality for packed oracle, crossover and old sparse completed in **965.037 seconds wall total**, below the 1,200-second bound. Candidate q1/q7/direct/reopen are all in the gate; the three baseline direct MR01 payloads are byte-identical and have matching SHA256/Keccak under `results/opaque-equivalence-gate-04-direct/`.
- As supplemental evidence, all nine accepted-P16 comparisons (the same three fixtures at q1/q7/direct) also pass, but take 614.639 seconds separately. Exact bytes and hashes are in `results/opaque-equivalence-gate-04/`. `artifactRoot` and `vfsRoot` match; `configRoot`, `machineRoot`, and outer checkpoint hashes differ as expected because the authenticated runtime code hash changed.
- Terminal successful-call gas savings measured against fresh P16 range from 307,960 gas (packed 1024 oracle, q1/q7) to 9,950,957 gas (old sparse 65,536-cell stress, direct). The nine measurements are in `results/generated-gas-comparison-gate-04.json`.

The complete gate summary is preserved as `results/generated-gate-summary.json.gz`; receipt verification and build pins are in `results/canonical-receipts.json` and `results/build-pins.json`. `source-invariants.json` records the source-only delta, all 97 derived bootstrap leaves/root and raw/binding limits. `SHA256SUMS` covers this directory.

### Harness correction retained

The first MR01 comparator incorrectly required `machineRoot` equality. That root is bound to `configRoot`, which commits the differing runtime code hash. A generated diagnostic preserving this failed assertion and the correction is `results/opaque-equivalence/first-attempt-diagnostic.json`; the subsequent nine-case comparison checks full MR01 bytes and SHA256/Keccak instead.

The adapted P16 gate also turns the older P5 `object-hashcode-omitted` negative control into a positive inherited `Object.hashCode` control, because that binding exists in accepted P16. It is included as `object-hashcode-omitted` in the generated gate summary; no P5 unsupported behavior is claimed for P16.

## Reproduction (generated-only; local cached dependencies)

The fixture ZIPs are the already-generated Java-8 fixtures in `../float-packed-checkpoint-preparation/results/generated-gate-v5/fixtures/`; the test-only Math oracle is the generated data under `../math-sin-independent-oracle/`. No official JAR, original class/resource/world, sibling worktree, network source, or host-Java execution authority is used by the EVM tests.

```sh
npm ci --offline --prefix jvmevm/runtime
python3 evidence/java-evm/minecraft-entry/packed-float-single-scan/tools/verify_source.py
python3 evidence/java-evm/minecraft-entry/packed-float-single-scan/tools/build.py build/java-diff-mc-packed-float-single-scan-build-05
python3 evidence/java-evm/minecraft-entry/packed-float-single-scan/tools/gate.py build/java-diff-mc-packed-float-single-scan-build-05 build/java-diff-mc-packed-float-single-scan-fixtures-05 build/java-diff-mc-packed-float-single-scan-gate-05
python3 evidence/java-evm/minecraft-entry/packed-float-single-scan/tools/compare_p16.py build/java-diff-mc-packed-float-single-scan-build-05 build/java-diff-mc-packed-float-single-scan-fixtures-05 build/java-diff-mc-packed-float-single-scan-gate-05 direct-only
# Optional exhaustive P16 q1/q7/direct byte comparison and gas-delta report:
python3 evidence/java-evm/minecraft-entry/packed-float-single-scan/tools/compare_p16.py build/java-diff-mc-packed-float-single-scan-build-05 build/java-diff-mc-packed-float-single-scan-fixtures-05 build/java-diff-mc-packed-float-single-scan-gate-05
python3 evidence/java-evm/minecraft-entry/packed-float-single-scan/tools/gas_comparison.py build/java-diff-mc-packed-float-single-scan-build-05 build/java-diff-mc-packed-float-single-scan-gate-05 build/java-diff-mc-packed-float-single-scan-baseline-replay-05
```

Use fresh output IDs; scripts refuse to overwrite a run/archive. The direct-only accepted-P16 equality step is the timed <1,200-second acceptance path. The optional exhaustive q1/q7 baseline replay is additional evidence and takes longer. `build.py` disables Go module downloads (`GOPROXY=off`, `GOSUMDB=off`) and requires the locally cached Solidity compiler packages.

## Limits

This is a bounded generated-fixture optimization proof only. No original Minecraft replay was run; no EULA was accepted, no world was created, and no `Done` milestone was reached. It is not a standard-chain deployment claim. The changed runtime remains over EIP-170; only the existing explicit LOCAL engine path is in scope.
