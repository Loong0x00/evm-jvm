# Generated `Map$Entry` link stage

This bounded generated-only stage implements
`JAVA_EVM_MC_MAP_ENTRY_LINK_PREPARATION.md`.

It appends immutable bootstrap image 95, Java-8 `java/util/Map$Entry`, produced
from a public static nested `Map.Entry<K,V>` declaration. The 448-byte image has
only these five public abstract methods: `getKey`, `getValue`, `setValue`,
`equals`, and `hashCode`. It has no `Code`, initializer, default/comparator
helper, or implementation behavior. Its SHA-256 is
`5c0beea6f609e3573672ca67fc5f06d086011f2974c5db179d9d7da59c794ac5`.

Raw limits remain 65 classes / 381732 bytes. Bootstrap count is 95 and the
read-only diagnostic class bound is 160. The source verifier proves every prior
Map and Integer image is byte-identical to raw65, verifies the generated image
metadata, and independently derives the ordered root
`9d07387563bce3f95d4f47fb84819362307edb5deec455bf03cef2e2ce44a622`.
The runtime is 376562 bytes, below the 393216-byte LOCAL cap. Native16,
String-local11, checkpoint, frame, and all other limits are unchanged.

## Reproduction

From this worktree root, with the locally pinned Node dependencies and JDK8:

```sh
python3 evidence/java-evm/minecraft-entry/map-entry-link-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/map-entry-link-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/map-entry-link-preflight/tools/build.py build/java-diff-mc-map-entry-link-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/map-entry-link-preflight/tools/generate_fixtures.py build/java-diff-mc-map-entry-link-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/map-entry-link-preflight/tools/gate.py build/java-diff-mc-map-entry-link-build-repro-LOCAL build/java-diff-mc-map-entry-link-fixtures-repro-LOCAL build/java-diff-mc-map-entry-link-gate-repro-LOCAL
```

The gate runs generated type-link/core-dispatch and retained Map/Integer fixtures
at q1/q7/direct, with durable reopen after each terminal chain. It also proves
omitted comparator-helper, malformed-input, and bootstrap raw-replacement
refusals at all three quanta. It uses no original artifact, JAR, external class,
selected resource, network, provider, world, EULA, or Done input/claim. Parent
replay is intentionally deferred.
