# Generated raw55 / byte355563 capacity stage

This generated-only stage implements `JAVA_EVM_MC_CLASSCOUNT55_BYTE355563_PREPARATION.md` from accepted parent evidence `parent-0fd9ef7f5`. It changes only raw-class capacity `54→55`, aggregate raw bytes `352504→355563`, and the read-only checkpoint diagnostic bound `148→149`.

All 94 ordered bootstrap images, their runtime-derived root, native16, String-local11, exception kinds14, frames128, checkpoint1MiB, selected-resource cap, reserve, LOCAL call budget, address/owner, toolchain, and every other semantic remain pinned by `tools/verify_source.py`. The source verifier reconstructs the engine, coordinator, driver, fixture generators, and gate from literal capacity substitutions against the accepted parent/source stage; it rejects every other source or commitment change.

The rebuilt engine is `377312 / 393216` bytes and the coordinator is `5394` bytes. The full generated-only gate completed in 155.444549 seconds (511 commands; 879 canonical receipts), below the fixed 1200-second bound. Raw55 runs q1/q7/direct/reopen with matching terminal machine roots, opaque payload hashes, Java and internal steps. Raw56 is independently refused at driver, coordinator, and engine layers. Exact aggregate 355563 is admitted by the coordinator and fully read through DI0 before the fixed LOCAL1B call's empty EVM revert; 355564 is atomically rejected by the coordinator.

Tracked `results/` contains build/fixture/gate outputs, compact focus boundaries, canonical receipts, and timing. `SHA256SUMS` covers every tracked stage file other than itself. No original artifact/JAR/class/resource, network input, fo binding/replay, provider/factory, world, EULA, or Done input was read or claimed. Parent genuine fo replay remains deferred.

## Reproduction

From repository root with fresh ignored `build/` paths and only pinned local dependencies:

```sh
python3 evidence/java-evm/minecraft-entry/classcount55-byte355563-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/classcount55-byte355563-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/classcount55-byte355563-preflight/tools/build.py build/java-diff-mc-classcount55-byte355563-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount55-byte355563-preflight/tools/generate_retained_fixtures.py build/java-diff-mc-classcount55-byte355563-retained-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount55-byte355563-preflight/tools/generate_focused_fixtures.py build/java-diff-mc-classcount55-byte355563-focused-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount55-byte355563-preflight/tools/gate.py build/java-diff-mc-classcount55-byte355563-build-repro-LOCAL build/java-diff-mc-classcount55-byte355563-retained-fixtures-repro-LOCAL build/java-diff-mc-classcount55-byte355563-focused-fixtures-repro-LOCAL build/java-diff-mc-classcount55-byte355563-gate-repro-LOCAL
```
