# Generated raw66 / byte385532 capacity stage

This generated-only stage implements `JAVA_EVM_MC_CLASSCOUNT66_BYTE385532_PREPARATION.md`. It changes only raw package capacity `65→66`, aggregate raw bytes `381732→385532`, and the read-only checkpoint diagnostic class bound `160→161` from the accepted `map-entry-link-preflight` basis.

`tools/verify_source.py` reconstructs the engine, coordinator, and Go transport from that parent through literal capacity substitutions. It pins the unchanged 95-image bootstrap root `9d07387563bce3f95d4f47fb84819362307edb5deec455bf03cef2e2ce44a622`, the immutable image95 `Map$Entry` (448 bytes, SHA-256 `5c0beea6f609e3573672ca67fc5f06d086011f2974c5db179d9d7da59c794ac5`), and Integer slot70/highestOneBit (2039 bytes, SHA-256 `5e224945101472050ed0837cc22b03f138c2e2409aec8fa058ccd531f6e410dd`). The rebuilt engine is `376562 / 393216` bytes; the coordinator is `5394` bytes.

The full gate completed in `94.65792048093863` seconds: 60 commands and 991 independently canonicalized public receipts, below the fixed 1200-second bound. Generated raw66, Map.Entry, and retained Map/Integer roots agree across q1/q7/direct with terminal reopen. Raw67 is refused independently by driver, coordinator, and engine; exactly 385532 raw bytes are coordinator-admitted and fully DI0-read before the unchanged 1MiB checkpoint cap atomically returns `LC0StateError(1,0)` without a Head; 385533 is atomically rejected by coordinator error12.

Tracked `results/manifest.json` and `SHA256SUMS` are the durable generated-only result index and checksum manifest. The gate uses only trusted local Java-8 generated inputs. It does not open an original artifact, JAR, external class/resource, network input, provider, world, EULA, or Done marker. No qz behavior is claimed; parent genuine qz replay remains deferred.

## Reproduction

From this worktree root with fresh ignored `build/` paths and pinned local dependencies:

```sh
python3 evidence/java-evm/minecraft-entry/classcount66-byte385532-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/classcount66-byte385532-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/classcount66-byte385532-preflight/tools/build.py build/java-diff-mc-classcount66-byte385532-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount66-byte385532-preflight/tools/generate_fixtures.py build/java-diff-mc-classcount66-byte385532-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount66-byte385532-preflight/tools/gate.py build/java-diff-mc-classcount66-byte385532-build-repro-LOCAL build/java-diff-mc-classcount66-byte385532-fixtures-repro-LOCAL build/java-diff-mc-classcount66-byte385532-gate-repro-LOCAL
```
