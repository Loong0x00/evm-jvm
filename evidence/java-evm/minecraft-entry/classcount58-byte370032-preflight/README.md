# Generated raw58 / byte370032 capacity stage

This generated-only stage implements `JAVA_EVM_MC_CLASSCOUNT58_BYTE370032_PREPARATION.md` from accepted parent evidence `parent-01d17b7cf`. It changes only raw-class capacity `57→58`, aggregate raw bytes `355926→370032`, and the read-only checkpoint diagnostic bound `151→152`.

All 94 ordered bootstrap images, their runtime-derived root, native16, String-local11, exception kinds14, frames128, checkpoint1MiB, selected-resource cap, reserve, LOCAL call budget, address/owner, toolchain, and every other semantic remain pinned by `tools/verify_source.py`. The verifier reconstructs engine, coordinator, driver, fixture generators, and gate through literal capacity substitutions against accepted raw57 evidence; it rejects every other source or commitment change.

The rebuilt engine is `377312 / 393216` bytes and the coordinator is `5394` bytes. The generated-only gate completed in 157.928617 seconds (511 commands; 893 canonical receipts), below the fixed 1200-second bound. Raw58 runs q1/q7/direct/reopen with equal terminal machine root, opaque payload hash, Java and internal steps; raw59 is independently refused at driver, coordinator, and engine layers. Exact aggregate 370032 is coordinator-admitted and fully read through DI0, then the unchanged 1MiB checkpoint cap atomically refuses `LC0StateError(1,0)` with no Head/root mutation; 370033 is atomically rejected by coordinator error12.

Tracked `results/` contains durable generated-only summaries and receipts. `SHA256SUMS` covers every tracked stage file other than itself. No original artifact/JAR/class/resource, network input, HashBiMap behavior/binding/replay, provider/factory, world, EULA, or Done input was read or claimed. Parent genuine HashBiMap replay remains deferred.

## Reproduction

From repository root with fresh ignored `build/` paths and only pinned local dependencies:

```sh
python3 evidence/java-evm/minecraft-entry/classcount58-byte370032-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/classcount58-byte370032-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/classcount58-byte370032-preflight/tools/build.py build/java-diff-mc-classcount58-byte370032-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount58-byte370032-preflight/tools/generate_retained_fixtures.py build/java-diff-mc-classcount58-byte370032-retained-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount58-byte370032-preflight/tools/generate_focused_fixtures.py build/java-diff-mc-classcount58-byte370032-focused-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount58-byte370032-preflight/tools/gate.py build/java-diff-mc-classcount58-byte370032-build-repro-LOCAL build/java-diff-mc-classcount58-byte370032-retained-fixtures-repro-LOCAL build/java-diff-mc-classcount58-byte370032-focused-fixtures-repro-LOCAL build/java-diff-mc-classcount58-byte370032-gate-repro-LOCAL
```
