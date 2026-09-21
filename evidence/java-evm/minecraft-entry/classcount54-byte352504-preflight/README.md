# Generated raw54 / byte352504 capacity stage

This generated-only stage implements `JAVA_EVM_MC_CLASSCOUNT54_BYTE352504_PREPARATION.md` from accepted parent evidence `parent-462bcc352`. It changes only raw-class capacity `53→54`, aggregate raw bytes `350161→352504`, and the read-only checkpoint diagnostic bound `147→148`.

All 94 ordered bootstrap images, their runtime-derived root, native16, String-local11, exception kinds14, frames128, checkpoint1MiB, selected-resource cap, reserve, LOCAL call budget, address/owner, toolchain, and every other semantic remain pinned by `tools/verify_source.py`. The source verifier reconstructs the engine, coordinator, driver, fixture generators, and gate from literal capacity substitutions against the accepted parent/source stage; it rejects every other source or commitment change.

The rebuilt engine is `377312 / 393216` bytes and the coordinator is `5394` bytes. The full generated-only gate completed in 154.561957 seconds (511 commands; 874 canonical receipts), below the fixed 1200-second bound. Raw54 runs q1/q7/direct/reopen with matching terminal machine roots, opaque payload hashes, Java and internal steps. Raw55 is independently refused at driver, coordinator, and engine layers. Exact aggregate 352504 is admitted by the coordinator and fully read through DI0 before the fixed LOCAL1B call's empty EVM revert; 352505 is atomically rejected by the coordinator.

Tracked `results/` contains build/fixture/gate outputs, compact focus boundaries, canonical receipts, and timing. `SHA256SUMS` covers every tracked stage file other than itself. No original artifact/JAR/class/resource, network input, fh binding/replay, provider/factory, world, EULA, or Done input was read or claimed. Parent genuine fh replay remains deferred.

## Reproduction

From repository root with fresh ignored `build/` paths and only pinned local dependencies:

```sh
python3 evidence/java-evm/minecraft-entry/classcount54-byte352504-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/classcount54-byte352504-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/classcount54-byte352504-preflight/tools/build.py build/java-diff-mc-classcount54-byte352504-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount54-byte352504-preflight/tools/generate_retained_fixtures.py build/java-diff-mc-classcount54-byte352504-retained-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount54-byte352504-preflight/tools/generate_focused_fixtures.py build/java-diff-mc-classcount54-byte352504-focused-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount54-byte352504-preflight/tools/gate.py build/java-diff-mc-classcount54-byte352504-build-repro-LOCAL build/java-diff-mc-classcount54-byte352504-retained-fixtures-repro-LOCAL build/java-diff-mc-classcount54-byte352504-focused-fixtures-repro-LOCAL build/java-diff-mc-classcount54-byte352504-gate-repro-LOCAL
```
