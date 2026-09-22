# Generated System.identityHashCode preparation

This generated-only stage implements `JAVA_EVM_MC_SYSTEM_IDENTITY_HASH_CODE_PREPARATION.md` from the frozen raw70/464925 capacity stage. It changes exactly the canonical bootstrap `java/lang/System` image and adds global native binding17. String-local binding12 is unchanged.

`System.identityHashCode(Object)` is exact public static native `(Ljava/lang/Object;)I`. Null returns zero. A valid non-null guest reference returns its existing low-uint32 heap handle after ordinary kind/assignability/reference validation. The implementation reads no host identity, does not invoke `Object.hashCode`, and has no allocation, initialization, or mutation path. `setOut`/`setErr`, the other bounded System members, raw70/464925, bootstrap96, diagnostic166, String lower-case/Locale, Map.Entry, and Integer are retained.

`tools/verify_source.py` independently recompiles the Java-8 System source, verifies exact method/field metadata and binding17 shape, reconstructs the Solidity delta from the frozen raw70 source, independently folds all 96 ordered image leaves, and proves only System leaf44 changed. It also pins the runtime and coordinator images, raw limits, String-local12, and non-System image hashes.

The generated Java-8 gate covers null, ordinary objects, distinct live references, `Object[]`, a canonical `Class` mirror, an overriding `hashCode`, q1/q7/direct/reopen, and a same-shape no-identity control. The read-only checkpoint diagnostic compares handle/type/size/reference state and canonical System statics, so binding17 cannot hide an allocation or state write. Retained System out/err setters, lower-case/Locale/String/Map/Integer, raw70, and exact capacity refusals remain. Raw System replacement, omitted `Object.hashCode`, and omitted general System API refusals are atomic.

No original/JAR/external class/resource/network/provider/world/EULA/Done input is opened, executed, or claimed. Parent genuine Validate replay remains deferred.

## Reproduction

From this worktree root with fresh ignored `build/` paths and pinned local dependencies:

```sh
python3 evidence/java-evm/minecraft-entry/system-identity-hash-code-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/system-identity-hash-code-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/system-identity-hash-code-preflight/tools/build.py build/java-diff-mc-system-identity-hash-code-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/system-identity-hash-code-preflight/tools/generate_fixtures.py build/java-diff-mc-system-identity-hash-code-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/system-identity-hash-code-preflight/tools/gate.py build/java-diff-mc-system-identity-hash-code-build-repro-LOCAL build/java-diff-mc-system-identity-hash-code-fixtures-repro-LOCAL build/java-diff-mc-system-identity-hash-code-gate-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/system-identity-hash-code-preflight/tools/verify_results.py
```