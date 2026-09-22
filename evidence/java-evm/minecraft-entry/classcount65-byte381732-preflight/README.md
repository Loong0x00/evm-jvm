# Generated raw65 / byte381732 capacity stage

This generated-only stage implements `JAVA_EVM_MC_CLASSCOUNT65_BYTE381732_PREPARATION.md`. It advances only raw-class capacity `64→65`, aggregate raw bytes `379594→381732`, and the read-only checkpoint diagnostic bound `158→159`.

`tools/verify_source.py` pins raw64 source inputs and reconstructs the engine, coordinator, driver, diagnostic, fixture, and gate edits through those literal capacity substitutions. It pins the unchanged ordered 94-image bootstrap root and the `Integer` slot-70 image (`2039` bytes, SHA-256 `5e224945101472050ed0837cc22b03f138c2e2409aec8fa058ccd531f6e410dd`). The rebuilt engine is `377409 / 393216` bytes; the coordinator remains `5394` bytes.

The full generated gate completed in `201.59890630003065` seconds (523 commands; 1736 verified canonical receipts), below the fixed 1200-second bound. Raw65 q1/q7/direct/reopen runs agree; raw66 is independently refused at driver, coordinator, and engine layers. Exactly 381732 aggregate bytes are coordinator-admitted and fully DI0-read before the unchanged 1MiB checkpoint cap atomically returns `LC0StateError(1,0)` without Head/root mutation; 381733 is atomically rejected by coordinator error12.

Tracked `results/manifest.json` and `SHA256SUMS` are the durable generated-only result index and checksum manifest. The gate uses only trusted locally generated fixture inputs. It reads no original artifact, JAR, external class/resource, network input, provider/factory, world, EULA, or Done marker. It makes no AbstractMapEntry behavior claim; parent genuine AbstractMapEntry replay remains deferred.

## Reproduction

From repository root with fresh ignored `build/` output directories and pinned local dependencies:

```sh
python3 evidence/java-evm/minecraft-entry/classcount65-byte381732-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/classcount65-byte381732-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/classcount65-byte381732-preflight/tools/build.py build/java-diff-mc-classcount65-byte381732-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount65-byte381732-preflight/tools/generate_retained_fixtures.py build/java-diff-mc-classcount65-byte381732-retained-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount65-byte381732-preflight/tools/generate_focused_fixtures.py build/java-diff-mc-classcount65-byte381732-focused-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount65-byte381732-preflight/tools/gate.py build/java-diff-mc-classcount65-byte381732-build-repro-LOCAL build/java-diff-mc-classcount65-byte381732-retained-fixtures-repro-LOCAL build/java-diff-mc-classcount65-byte381732-focused-fixtures-repro-LOCAL build/java-diff-mc-classcount65-byte381732-gate-repro-LOCAL
```
