# Generated raw63 / byte377990 capacity stage

This generated-only stage implements `JAVA_EVM_MC_CLASSCOUNT63_BYTE377990_PREPARATION.md` from parent evidence `parent-ddca01a33`. It advances only raw-class capacity `62→63`, aggregate raw bytes `376794→377990`, and the read-only checkpoint diagnostic bound `156→157`.

`tools/verify_source.py` pins the accepted parent source and reconstructs the engine, coordinator, driver, and diagnostic changes through those literal capacity substitutions. It also pins the unchanged 94-image bootstrap root and the accepted `Integer` slot 70 image (`2039` bytes, SHA-256 `5e224945101472050ed0837cc22b03f138c2e2409aec8fa058ccd531f6e410dd`). The rebuilt engine is `377409 / 393216` bytes and the coordinator is `5394` bytes.

The full generated gate completed in `197.963590` seconds (523 commands; 1726 canonical receipts), below the fixed 1200-second bound. Raw63 q1/q7/direct/reopen runs agree; raw64 is refused independently at driver, coordinator, and engine layers. Exactly 377990 aggregate bytes are admitted and fully read before the unchanged 1MiB checkpoint cap atomically returns `LC0StateError(1,0)` without Head/root mutation; 377991 is atomically refused by coordinator error12.

Tracked `results/` contains the durable generated-only summaries and canonical receipts. The gate uses only trusted locally generated Java-8 fixtures. It reads no original artifact, JAR, external class, resource, network input, provider/factory, world, EULA, or Done marker. No HashBiMap behavior or `HashBiMap$BiEntry` replay is included; parent genuine replay remains deferred.

## Reproduction

From repository root with fresh ignored `build/` output directories and pinned local dependencies:

```sh
python3 evidence/java-evm/minecraft-entry/classcount63-byte377990-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/classcount63-byte377990-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/classcount63-byte377990-preflight/tools/build.py build/java-diff-mc-classcount63-byte377990-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount63-byte377990-preflight/tools/generate_retained_fixtures.py build/java-diff-mc-classcount63-byte377990-retained-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount63-byte377990-preflight/tools/generate_focused_fixtures.py build/java-diff-mc-classcount63-byte377990-focused-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount63-byte377990-preflight/tools/gate.py build/java-diff-mc-classcount63-byte377990-build-repro-LOCAL build/java-diff-mc-classcount63-byte377990-retained-fixtures-repro-LOCAL build/java-diff-mc-classcount63-byte377990-focused-fixtures-repro-LOCAL build/java-diff-mc-classcount63-byte377990-gate-repro-LOCAL
```
