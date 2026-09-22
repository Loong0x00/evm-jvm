# Generated raw71 / byte471911 capacity preparation

This generated-only stage implements `JAVA_EVM_MC_CLASSCOUNT71_BYTE471911_PREPARATION.md` as a literal capacity delta from the checked-in System.identityHashCode stage.

The only product changes are raw-class count `70→71`, aggregate raw bytes `464925→471911`, the matching coordinator fixed arrays/guards, product-driver declarations, and read-only diagnostic bound `166→167`. The engine configuration tuple changes with the two engine limits. Rebuilt code identities are pinned because those literal changes alter bytecode.

The source verifier proves that every other engine byte is identical, including all native/opcode behavior, the 96 bootstrap images, and the bootstrap domain. It independently folds the exact ordered bootstrap leaves to the unchanged root `6fbfed767949708bacc0aebb58173f63c46bfd0b84cb0c5ac3a15f461c8a4a77`. In particular System remains 1113 bytes with SHA-256 `6e29f00abed753017741ad667314982061178298cb3fca5baa0d92f2f9d57564`; global native17 and String-local12 remain exact.

The generated gate covers exact raw71/72 and byte471911/471912 frontiers, q1/q7/direct/reopen positives, all raw bytes read at the admitted aggregate boundary, and atomic product-driver/coordinator/engine refusals with no failed checkpoint or Head. It also retains generated identity-hash, System out/err, lower-case/Locale, String, Map, and Integer controls. Runtime is 380017 bytes, below the 393216-byte cap.

No original/JAR/external class/resource/network/provider/world/EULA/Done input is opened, executed, or claimed. Parent genuine replay is deferred.

## Reproduction

From this worktree root with fresh ignored `build/` paths and pinned local dependencies:

```sh
python3 evidence/java-evm/minecraft-entry/classcount71-byte471911-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/classcount71-byte471911-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/classcount71-byte471911-preflight/tools/build.py build/java-diff-mc-classcount71-byte471911-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount71-byte471911-preflight/tools/generate_fixtures.py build/java-diff-mc-classcount71-byte471911-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount71-byte471911-preflight/tools/gate.py build/java-diff-mc-classcount71-byte471911-build-repro-LOCAL build/java-diff-mc-classcount71-byte471911-fixtures-repro-LOCAL build/java-diff-mc-classcount71-byte471911-gate-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount71-byte471911-preflight/tools/verify_results.py
```
