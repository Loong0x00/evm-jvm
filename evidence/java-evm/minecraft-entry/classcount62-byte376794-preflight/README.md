# Generated raw62 / byte376794 capacity stage

This generated-only stage implements `JAVA_EVM_MC_CLASSCOUNT62_BYTE376794_PREPARATION.md` from accepted parent evidence `parent-cc2b7556b`. It changes only raw-class capacity `61→62`, aggregate raw bytes `375416→376794`, and the read-only checkpoint diagnostic bound `155→156`.

All 94 ordered bootstrap images, their runtime-derived root, native16, String-local11, exception kinds14, frames128, checkpoint1MiB, selected-resource cap, reserve, LOCAL call budget, address/owner, toolchain, and every other semantic remain pinned by `tools/verify_source.py`. The verifier reconstructs engine, coordinator, driver, fixture generators, and gate through literal capacity substitutions against accepted raw61 evidence; it rejects every other source or commitment change.

The rebuilt engine is `377312 / 393216` bytes and the coordinator is `5394` bytes. The generated-only gate completed in `160.542056` seconds (511 commands; 911 canonical receipts), below the fixed 1200-second bound. Raw62 runs q1/q7/direct/reopen with equal terminal machine root, opaque payload hash, Java and internal steps; raw63 is independently refused at driver, coordinator, and engine layers. Exact aggregate 376794 is coordinator-admitted and fully read through DI0, then the unchanged 1MiB checkpoint cap atomically refuses `LC0StateError(1,0)` with no Head/root mutation; 376795 is atomically rejected with coordinator error12.

Tracked `results/` contains durable generated-only summaries and receipts. `SHA256SUMS` covers every tracked stage file other than itself. No original artifact/JAR/class/resource, network input, Hashing behavior/binding/replay, provider/factory, world, EULA, or Done input was read or claimed. Parent genuine `Hashing` replay remains deferred.

## Reproduction

From repository root with fresh ignored `build/` paths and only pinned local dependencies:

```sh
python3 evidence/java-evm/minecraft-entry/classcount62-byte376794-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/classcount62-byte376794-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/classcount62-byte376794-preflight/tools/build.py build/java-diff-mc-classcount62-byte376794-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount62-byte376794-preflight/tools/generate_retained_fixtures.py build/java-diff-mc-classcount62-byte376794-retained-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount62-byte376794-preflight/tools/generate_focused_fixtures.py build/java-diff-mc-classcount62-byte376794-focused-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount62-byte376794-preflight/tools/gate.py build/java-diff-mc-classcount62-byte376794-build-repro-LOCAL build/java-diff-mc-classcount62-byte376794-retained-fixtures-repro-LOCAL build/java-diff-mc-classcount62-byte376794-focused-fixtures-repro-LOCAL build/java-diff-mc-classcount62-byte376794-gate-repro-LOCAL
```
