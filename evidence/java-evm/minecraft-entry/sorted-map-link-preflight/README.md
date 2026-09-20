# Generated `SortedMap` link stage

This generated-only stage implements the bounded link required by
`JAVA_EVM_MC_SORTED_MAP_LINK_PREPARATION.md`. It appends exactly image 92,
Java-8 `java/util/SortedMap<K,V> extends Map<K,V> {}`, after the fixed
91-image bootstrap tail. The image is 198 bytes, SHA-256
`c59e7d5cb3219d4fe2844d720a5f74158c8760d58f34ab3d8bb8d81ba8bb9b06`.

The EVM bootstrap root remains dynamically derived from the complete ordered
leaf list. In this fresh domain the 92-image root is
`d7dd6b101c64ad66314e7d36dc5e36ea20e60369d31dd89a3edce39a9c04a308`;
it is not a fixed root literal. The runtime is 390931 bytes, below the
393216-byte LOCAL cap (baseline 389150). Only bootstrap count `91→92` and
read-only diagnostic bound `131→132` change. Raw limits remain `40/295438`,
native bindings remain 13, and all other pinned limits/toolchain semantics
remain unchanged.

`TreeMap` remains the existing constructor-only `Object` subclass. It does
not implement `Map` or `SortedMap`; no ordering, mutation, comparators, views,
methods, provider/factory, world, or Done behavior is implemented or claimed.
The historical `SortedMap.put` fixture now reaches the actual post-link
receiver refusal `ReferenceError(2,13)`, selector `0xfe0674d5`, after its real
`TreeMap` constructor, rather than the old missing-class error.

## Generated-only reproduction

From repository root, using fresh ignored `build/` paths:

```sh
python3 evidence/java-evm/minecraft-entry/sorted-map-link-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/sorted-map-link-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/sorted-map-link-preflight/tools/build.py build/java-diff-mc-sorted-map-link-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/sorted-map-link-preflight/tools/generate_fixtures.py build/java-diff-mc-sorted-map-link-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/sorted-map-link-preflight/tools/gate.py build/java-diff-mc-sorted-map-link-build-repro-LOCAL build/java-diff-mc-sorted-map-link-fixtures-repro-LOCAL build/java-diff-mc-sorted-map-link-gate-repro-LOCAL
```

The source verifier and scripts reject original artifacts, JARs, generated
class inputs, resources, and worlds. The checked-in bootstrap is source plus
hex only; compiled fixture outputs stay in ignored `build/` paths.
