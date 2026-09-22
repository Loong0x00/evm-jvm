# Generated raw64 / byte379594 capacity stage

This generated-only stage implements `JAVA_EVM_MC_CLASSCOUNT64_BYTE379594_PREPARATION.md`. It advances only raw-class capacity `63→64`, aggregate raw bytes `377990→379594`, and the read-only checkpoint diagnostic bound `157→158`.

`tools/verify_source.py` pins raw63 source inputs and reconstructs the engine, coordinator, driver, diagnostic, fixture, and gate edits through those literal capacity substitutions. It pins the unchanged ordered 94-image bootstrap root and the `Integer` slot-70 image (`2039` bytes, SHA-256 `5e224945101472050ed0837cc22b03f138c2e2409aec8fa058ccd531f6e410dd`). The rebuilt engine is `377432 / 393216` bytes; the coordinator remains `5394` bytes.

The full generated gate completed in `199.569528` seconds (523 commands; 1731 verified canonical receipts), below the fixed 1200-second bound. Raw64 q1/q7/direct/reopen runs agree; raw65 is independently refused at driver, coordinator, and engine layers. Exactly 379594 aggregate bytes are coordinator-admitted and fully DI0-read before the unchanged 1MiB checkpoint cap atomically returns `LC0StateError(1,0)` without Head/root mutation; 379595 is atomically rejected by coordinator error12.

Tracked `results/manifest.json` and `SHA256SUMS` are the durable generated-only result index and checksum manifest. The gate uses only trusted locally generated fixture inputs. It reads no original artifact, JAR, external class/resource, network input, provider/factory, world, EULA, or Done marker. It makes no ImmutableEntry behavior claim; parent genuine ImmutableEntry replay remains deferred.

## Reproduction

From repository root with fresh ignored `build/` output directories and pinned local dependencies:

```sh
python3 evidence/java-evm/minecraft-entry/classcount64-byte379594-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/classcount64-byte379594-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/classcount64-byte379594-preflight/tools/build.py build/java-diff-mc-classcount64-byte379594-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount64-byte379594-preflight/tools/generate_retained_fixtures.py build/java-diff-mc-classcount64-byte379594-retained-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount64-byte379594-preflight/tools/generate_focused_fixtures.py build/java-diff-mc-classcount64-byte379594-focused-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount64-byte379594-preflight/tools/gate.py build/java-diff-mc-classcount64-byte379594-build-repro-LOCAL build/java-diff-mc-classcount64-byte379594-retained-fixtures-repro-LOCAL build/java-diff-mc-classcount64-byte379594-focused-fixtures-repro-LOCAL build/java-diff-mc-classcount64-byte379594-gate-repro-LOCAL
```
