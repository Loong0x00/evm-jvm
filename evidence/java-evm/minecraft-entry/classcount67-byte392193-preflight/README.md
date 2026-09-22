# Generated raw67 / byte392193 capacity stage

This generated-only stage implements `JAVA_EVM_MC_CLASSCOUNT67_BYTE392193_PREPARATION.md`. It changes only raw package capacity `66→67`, aggregate raw bytes `385532→392193`, and the read-only checkpoint diagnostic class bound `161→162` from the generated raw66 basis.

`tools/verify_source.py` reconstructs the engine, coordinator, and Go transport from that parent through literal capacity substitutions. It pins the unchanged 95-image bootstrap root `9d07387563bce3f95d4f47fb84819362307edb5deec455bf03cef2e2ce44a622`, immutable image95 `Map$Entry` (448 bytes, SHA-256 `5c0beea6f609e3573672ca67fc5f06d086011f2974c5db179d9d7da59c794ac5`), and Integer slot70/highestOneBit (2039 bytes, SHA-256 `5e224945101472050ed0837cc22b03f138c2e2409aec8fa058ccd531f6e410dd`). The rebuilt engine is `376562 / 393216` bytes; the coordinator is `5394` bytes.

The full generated gate pins exact 67/68 and 392193/392194 frontiers. The raw67 capacity focus and retained Map.Entry, Map, and Integer roots run q1/q7/direct with terminal reopen. The exact byte-admitted input is fully DI0-read before the unchanged 1MiB checkpoint cap can atomically return `LC0StateError(1,0)` without a Head; 392194 is atomically rejected by the coordinator. Generated input only; no original/JAR/external class/resource/network/provider/world/EULA/Done input or claim. Parent genuine `HashBiMap$Inverse` replay remains deferred.

Tracked `results/manifest.json` and `SHA256SUMS` are the durable generated-only result index and checksum manifest.

## Reproduction

From this worktree root with fresh ignored `build/` paths and pinned local dependencies:

```sh
python3 evidence/java-evm/minecraft-entry/classcount67-byte392193-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/classcount67-byte392193-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/classcount67-byte392193-preflight/tools/build.py build/java-diff-mc-classcount67-byte392193-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount67-byte392193-preflight/tools/generate_fixtures.py build/java-diff-mc-classcount67-byte392193-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount67-byte392193-preflight/tools/gate.py build/java-diff-mc-classcount67-byte392193-build-repro-LOCAL build/java-diff-mc-classcount67-byte392193-fixtures-repro-LOCAL build/java-diff-mc-classcount67-byte392193-gate-repro-LOCAL
```
