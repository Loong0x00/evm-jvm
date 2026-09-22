# Generated raw56 / byte355643 capacity stage

This generated-only stage implements `JAVA_EVM_MC_CLASSCOUNT56_BYTE355643_PREPARATION.md` from accepted parent evidence `parent-0da61f0b5`. It changes only raw-class capacity `55→56`, aggregate raw bytes `355563→355643`, and the read-only checkpoint diagnostic bound `149→150`.

All 94 ordered bootstrap images, their runtime-derived root, native16, String-local11, exception kinds14, frames128, checkpoint1MiB, selected-resource cap, reserve, LOCAL call budget, address/owner, toolchain, and every other semantic remain pinned by `tools/verify_source.py`. The source verifier reconstructs the engine, coordinator, driver, fixture generators, and gate from literal capacity substitutions against the accepted parent/source stage; it rejects every other source or commitment change.

The rebuilt engine is `377312 / 393216` bytes and the coordinator is `5394` bytes. The full generated-only gate completed in 155.795587 seconds (511 commands; 883 canonical receipts), below the fixed 1200-second bound. Raw56 runs q1/q7/direct/reopen with matching terminal machine roots, opaque payload hashes, Java and internal steps. Raw57 is independently refused at driver, coordinator, and engine layers. Exact aggregate 355643 is admitted by the coordinator and fully read through DI0 before the fixed LOCAL1B call's empty EVM revert; 355644 is atomically rejected by the coordinator.

Tracked `results/` contains build/fixture/gate outputs, compact focus boundaries, canonical receipts, and timing. `SHA256SUMS` covers every tracked stage file other than itself. No original artifact/JAR/class/resource, network input, fc binding/replay, provider/factory, world, EULA, or Done input was read or claimed. Parent genuine fc replay remains deferred.

## Reproduction

From repository root with fresh ignored `build/` paths and only pinned local dependencies:

```sh
python3 evidence/java-evm/minecraft-entry/classcount56-byte355643-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/classcount56-byte355643-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/classcount56-byte355643-preflight/tools/build.py build/java-diff-mc-classcount56-byte355643-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount56-byte355643-preflight/tools/generate_retained_fixtures.py build/java-diff-mc-classcount56-byte355643-retained-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount56-byte355643-preflight/tools/generate_focused_fixtures.py build/java-diff-mc-classcount56-byte355643-focused-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount56-byte355643-preflight/tools/gate.py build/java-diff-mc-classcount56-byte355643-build-repro-LOCAL build/java-diff-mc-classcount56-byte355643-retained-fixtures-repro-LOCAL build/java-diff-mc-classcount56-byte355643-focused-fixtures-repro-LOCAL build/java-diff-mc-classcount56-byte355643-gate-repro-LOCAL
```
