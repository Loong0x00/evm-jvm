# Generated raw70 / byte464925 capacity stage

This generated-only stage implements `JAVA_EVM_MC_CLASSCOUNT70_BYTE464925_PREPARATION.md`. From `parent-629078bb6`, it changes only raw package capacity `69→70`, aggregate raw bytes `449904→464925`, and the read-only checkpoint diagnostic class bound `165→166`.

`tools/verify_source.py` reconstructs the engine, coordinator, and Go transport through literal capacity substitutions. It independently re-enumerates the frozen 96-image root `39b4e365255c15cdf1de704a264e35b2574c77e653a72718a9a9861a76ad7f18`; recompiles and checks String (1836 bytes, SHA-256 `259bed03edf8602dca9ad26e639cb7668b8da38d62422b80788d8339020017fe`) and Locale (285 bytes, SHA-256 `8401495628aed9de6e7c7c0ad56f73ac563bd5e7a892b8eb8ca9fcf91bc03e31`); and pins Map.Entry, Integer, global native16, String-local12, all other bootstrap images, and every non-capacity engine source byte. The rebuilt runtime is 379383/393216 bytes; the coordinator is 5394 bytes.

The full generated gate checks exact `70/71` and `464925/464926` frontiers. Raw70 and retained lower-case/Locale/String/Map/Integer controls run q1/q7/direct with terminal reopen verification. Raw71 is atomically rejected by the product driver, coordinator, and engine widening probes. The exact byte-admitted input is fully DI0-read before the unchanged 1MiB checkpoint cap atomically returns `LC0StateError(1,0)` without a durable Head; 464926 atomically rejects at the coordinator. Canonical receipt/event/checkpoint/read-range encoding is independently verified.

No original/JAR/external class/resource/network/provider/world/EULA/Done input is opened, executed, or claimed. Parent genuine Validate replay remains deferred. Tracked `results/manifest.json` and `SHA256SUMS` are the durable generated-only result index and checksum manifest.

## Reproduction

From this worktree root with fresh ignored `build/` paths and pinned local dependencies:

```sh
python3 evidence/java-evm/minecraft-entry/classcount70-byte464925-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/classcount70-byte464925-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/classcount70-byte464925-preflight/tools/build.py build/java-diff-mc-classcount70-byte464925-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount70-byte464925-preflight/tools/generate_fixtures.py build/java-diff-mc-classcount70-byte464925-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount70-byte464925-preflight/tools/gate.py build/java-diff-mc-classcount70-byte464925-build-repro-LOCAL build/java-diff-mc-classcount70-byte464925-fixtures-repro-LOCAL build/java-diff-mc-classcount70-byte464925-gate-repro-LOCAL
```
