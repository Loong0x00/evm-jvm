# Generated raw69 / byte449904 capacity stage

This generated-only stage implements `JAVA_EVM_MC_CLASSCOUNT69_BYTE449904_PREPARATION.md`. It changes only raw package capacity `68→69`, aggregate raw bytes `394767→449904`, and the read-only checkpoint diagnostic class bound `163→164` from accepted `parent-e8569f01e`.

`tools/verify_source.py` reconstructs the engine, coordinator, and Go transport through literal capacity substitutions. It pins the unchanged 95-image bootstrap root `2741d34b1949eb3cdabe20d0aef3dedca113e311467f90269b7e363b18635a9d`, accepted `String.indexOf(int)` image (1773 bytes, SHA-256 `42b340085b6639cdcad9167a7089da2e1afd81866ee3182ace092796b23258ec`), immutable image95 `Map$Entry` (448 bytes, SHA-256 `5c0beea6f609e3573672ca67fc5f06d086011f2974c5db179d9d7da59c794ac5`), and Integer slot70/highestOneBit (2039 bytes, SHA-256 `5e224945101472050ed0837cc22b03f138c2e2409aec8fa058ccd531f6e410dd`). The rebuilt engine is `377043 / 393216` bytes; the coordinator is `5394` bytes.

The full generated gate pins exact `69/70` and `449904/449905` frontiers. Raw69 and retained String/Map/Integer roots run q1/q7/direct with terminal reopen. The exact byte-admitted input is fully DI0-read before the unchanged 1MiB checkpoint cap atomically returns `LC0StateError(1,0)` without a Head; 449905 atomically rejects at the coordinator. Generated input only; no original/JAR/external class/resource/network/provider/world/EULA/Done input or claim. Parent genuine `StringUtils.class` replay remains deferred.

Tracked `results/manifest.json` and `SHA256SUMS` are the durable generated-only result index and checksum manifest.

## Reproduction

From this worktree root with fresh ignored `build/` paths and pinned local dependencies:

```sh
python3 evidence/java-evm/minecraft-entry/classcount69-byte449904-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/classcount69-byte449904-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/classcount69-byte449904-preflight/tools/build.py build/java-diff-mc-classcount69-byte449904-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount69-byte449904-preflight/tools/generate_fixtures.py build/java-diff-mc-classcount69-byte449904-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount69-byte449904-preflight/tools/gate.py build/java-diff-mc-classcount69-byte449904-build-repro-LOCAL build/java-diff-mc-classcount69-byte449904-fixtures-repro-LOCAL build/java-diff-mc-classcount69-byte449904-gate-repro-LOCAL
```
