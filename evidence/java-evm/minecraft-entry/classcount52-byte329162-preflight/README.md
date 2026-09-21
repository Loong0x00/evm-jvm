# Generated raw52 / byte329162 capacity stage

This generated-only stage implements `JAVA_EVM_MC_CLASSCOUNT52_BYTE329162_PREPARATION.md` from accepted generated evidence `parent-ff10121f9`. It changes only raw-class capacity `51→52`, aggregate raw bytes `328000→329162`, and the read-only checkpoint diagnostic bound `145→146`.

All 94 ordered bootstrap images, their runtime-derived root, native14, String-local11, System `out`/`err`, exception kinds14, frames128, checkpoint1MiB, selected-resource cap, reserve, LOCAL call budget, address/owner, toolchain, and every other semantic remain byte-for-byte pinned by `tools/verify_source.py`. The source verifier reconstructs the engine, coordinator, driver, fixture generator, and gate through exact literal capacity substitutions from `parent-ff10121f9`; it rejects every extra source or commitment change.

The rebuilt engine is `373634 / 393216` bytes and the coordinator is 5394 bytes. The full generated-only gate completed in 136.432962 seconds (486 commands; 706 canonical receipts), below the fixed 1200-second bound. Raw52 runs q1/q7/direct/reopen with matching terminal machine roots, opaque payload hashes, Java and internal steps. Raw53 is independently refused at driver, coordinator, and engine layers. Exact aggregate `329162` reaches the retained engine reserve refusal after coordinator acceptance; `329163` is atomically rejected at the coordinator.

Tracked `results/` contains the gate output summaries and fixture/build pins. `SHA256SUMS` covers every tracked stage file other than itself. No original artifact/JAR/class/resource, network input, provider/factory, world, EULA, Done, or genuine `no` binding/replay is read or claimed. Parent genuine `no` replay remains deferred.

## Reproduction

From repository root with fresh ignored `build/` paths and only pinned local dependencies:

```sh
python3 evidence/java-evm/minecraft-entry/classcount52-byte329162-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/classcount52-byte329162-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/classcount52-byte329162-preflight/tools/build.py build/java-diff-mc-classcount52-byte329162-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount52-byte329162-preflight/tools/generate_fixtures.py build/java-diff-mc-classcount52-byte329162-retained-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/string-substring-int-preflight/tools/generate_fixtures.py build/java-diff-mc-string-substring-int-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount52-byte329162-preflight/tools/gate.py build/java-diff-mc-classcount52-byte329162-build-repro-LOCAL build/java-diff-mc-classcount52-byte329162-retained-fixtures-repro-LOCAL build/java-diff-mc-string-substring-int-fixtures-repro-LOCAL build/java-diff-mc-classcount52-byte329162-gate-repro-LOCAL
```
