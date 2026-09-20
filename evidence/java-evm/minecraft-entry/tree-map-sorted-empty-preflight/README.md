# Generated `TreeMap` `SortedMap.isEmpty` stage

This generated-only stage implements
`JAVA_EVM_MC_TREE_MAP_SORTED_EMPTY_PREPARATION.md`. It changes only existing
bootstrap image85 `java/util/TreeMap`; image92 `SortedMap extends Map` and the
92-image ordering are retained.

The checked-in Java 8 source is deliberately `abstract`, because Java source
will not permit a concrete class to omit the other inherited `Map` methods. The
source verifier compiles it with `javac -source 8 -target 8 -g:none`, validates
its superclass, sole `SortedMap` interface, two method bodies, and then strips
only class-header `ACC_ABSTRACT` (`0x0421 -> 0x0021`). The resulting 315-byte
bootstrap image has SHA-256
`fea296c4b5c54dbd9b66c490cafe8cf30316158b44933afe61c97542cbcbc3f3` and
contains only public `<init>()V` plus public `isEmpty()Z` returning `true`.
It has no `put`, `get`, `size`, `clear`, `containsKey`, ordering, comparator,
or view member.

The dynamic ordered bootstrap root is recomputed from all 92 image bytes at
runtime; it is not a Solidity root literal. In this fresh domain the evidence
record is `32459057504c70e6cc1066ddd5fb4558c1dab4eed1ad86ad9acf07f3fa241b33`.
Only TreeMap's leaf hash differs from the parent record; Object and every other
leaf remain runtime-derived and byte-identical. Runtime is `391172 / 393216`
bytes (baseline `390931`). Bootstrap count92, diagnostic132, raw40/295438,
native13, limits, compiler, and all other profile bounds remain pinned.

A generated fresh `SortedMap` receiver probe calls only `isEmpty()` on two new
TreeMaps. q1/q7/direct/reopen agree at 42 Java and 2 internal steps, with the
same machine root and opaque checkpoint payload. Raw TreeMap replacement still
atomically rejects with `BootstrapProfileError(1,1)` / `0x6a23ad80`.

Because `TreeMap` deliberately has no `put`, direct `TreeMap.put` and typed
`SortedMap.put` now reach retained abstract `Map.put` after the type-link and
finish as the exact unsupported `AbstractMethodError` kind11 (12 Java / 3
internal steps), never a map result or mutation. This is an unsupported-method
outcome, not an implementation of any other Map or SortedMap API.

## Generated-only reproduction

From repository root, using new ignored `build/` paths:

```sh
python3 evidence/java-evm/minecraft-entry/tree-map-sorted-empty-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/tree-map-sorted-empty-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/tree-map-sorted-empty-preflight/tools/build.py build/java-diff-mc-tree-map-sorted-empty-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/tree-map-sorted-empty-preflight/tools/generate_fixtures.py build/java-diff-mc-tree-map-sorted-empty-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/tree-map-sorted-empty-preflight/tools/gate.py build/java-diff-mc-tree-map-sorted-empty-build-repro-LOCAL build/java-diff-mc-tree-map-sorted-empty-fixtures-repro-LOCAL build/java-diff-mc-tree-map-sorted-empty-gate-repro-LOCAL
```

The source verifier and scripts reject original artifacts, JARs, generated
class inputs, resources, and worlds. Checked-in bootstrap material is source
plus hex only; compiled fixture outputs remain under ignored `build/`. Parent
alone performs any genuine replay. No provider/factory/world/Done claim is
made.
