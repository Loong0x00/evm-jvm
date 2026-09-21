# Generated raw53 / byte350161 capacity stage

This generated-only stage implements `JAVA_EVM_MC_CLASSCOUNT53_BYTE350161_PREPARATION.md` from accepted generated evidence `parent-7e9332014`. It changes only raw-class capacity `52→53`, aggregate raw bytes `329162→350161`, and the read-only checkpoint diagnostic bound `146→147`.

All 94 ordered bootstrap images, their runtime-derived root, native16, String-local11, System setters, exception kinds14, frames128, checkpoint1MiB, selected-resource cap, reserve, LOCAL call budget, address/owner, toolchain, and every other semantic remain byte-for-byte pinned by `tools/verify_source.py`. The source verifier reconstructs engine, coordinator, driver, fixture generators, and gate from literal capacity substitutions against `parent-7e9332014`; it rejects every other source or commitment change.

The rebuilt engine is `377312 / 393216` bytes and the coordinator is 5394 bytes. The full generated-only gate completed in 155.385806 seconds (511 commands; 870 canonical receipts), below the fixed 1200-second bound. Raw53 runs q1/q7/direct/reopen with matching terminal machine roots, opaque payload hashes, Java and internal steps. Raw54 is independently refused at driver, coordinator, and engine layers. Exact aggregate 350161 is accepted by the coordinator and fully read through DI0 before the fixed LOCAL1B call returns the inherited empty EVM revert; 350162 is atomically rejected by the coordinator.

Tracked `results/` contains build/fixture/gate outputs, compact focus boundaries, canonical receipts, and timing. `SHA256SUMS` covers every tracked stage file other than itself. No original artifact/JAR/class/resource, network input, qe binding/replay, provider/factory, world, EULA, or Done input was read or claimed. Parent genuine qe replay remains deferred.

## Reproduction

From repository root with fresh ignored `build/` paths and only pinned local dependencies:

```sh
python3 evidence/java-evm/minecraft-entry/classcount53-byte350161-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/classcount53-byte350161-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/classcount53-byte350161-preflight/tools/build.py build/java-diff-mc-classcount53-byte350161-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount53-byte350161-preflight/tools/generate_retained_fixtures.py build/java-diff-mc-classcount53-byte350161-retained-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount53-byte350161-preflight/tools/generate_focused_fixtures.py build/java-diff-mc-classcount53-byte350161-focused-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount53-byte350161-preflight/tools/gate.py build/java-diff-mc-classcount53-byte350161-build-repro-LOCAL build/java-diff-mc-classcount53-byte350161-retained-fixtures-repro-LOCAL build/java-diff-mc-classcount53-byte350161-focused-fixtures-repro-LOCAL build/java-diff-mc-classcount53-byte350161-gate-repro-LOCAL
```
