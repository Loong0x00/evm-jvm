# Bounded `Integer.valueOf(int)` source stage

This generated-only stage derives exactly from accepted raw33 parent
`parent-1b7a30656`. It changes only the fixed `java/lang/Integer` bootstrap
image, plus the required fresh domain/address and generated-artifact hash
rebinding. The existing 1667-byte Java-8 image is reproduced from the stage
source with `valueOf` removed and must match the parent's exact SHA-256. The
new 1747-byte Java-8 image adds exactly:

```java
public static Integer valueOf(int value) { return new Integer(value); }
```

It allocates through the existing public `Integer(int)` constructor. All
existing source methods, constructors, numeric conversions, equality/hash,
comparison, and decimal `parseInt` source remain unchanged. There is no cache
or identity guarantee, String/radix overload, formatting surface, or host
primitive/parser.

The focused generated fixture exercises `-1`, `0`, `Integer.MIN_VALUE`, and
`Integer.MAX_VALUE`; it checks value/equality/hash and requires each two
`valueOf` calls and an explicit constructor allocation to be distinct. Its
q1/q7/direct/reopen chains agree at 665 Java / 3 internal steps, with epochs
665/95/1 and identical machine root and opaque payload. A no-use root leaves
Integer uninitialized; raw `java/lang/Integer` replacement and the omitted
`valueOf(String)` overload are atomic EVM refusals.

All raw33/262158 limits, 86 bootstrap positions (other than Integer), native13,
diagnostic119, selected resource 1/4096, Properties/String pipeline, frames,
checkpoint/Head limits, compiler and outlined tail are parent-pinned. The one
source build produced a 392454-byte runtime, under the 393216-byte cap (762
bytes remain); the coordinator remains 5394 bytes.

The full generated gate retained direct/reopen controls and completed 81 result
rows, 272 commands, and 1512 canonical receipts in 144.675 seconds (cap 1200).
It uses only trusted generated Java-8 sources and no original artifact, JAR,
class, resource, Provider construction, factory, world, or Done input or
claim. Parent alone reruns unchanged original33.

Reproduce with local pinned tools only:

```sh
python3 evidence/java-evm/minecraft-entry/integer-value-of-preflight/tools/build.py build/java-diff-mc-integer-value-of-build-LOCAL
python3 evidence/java-evm/minecraft-entry/integer-value-of-preflight/tools/generate_fixtures.py build/java-diff-mc-integer-value-of-fixtures-LOCAL
python3 evidence/java-evm/minecraft-entry/integer-value-of-preflight/tools/gate.py build/java-diff-mc-integer-value-of-build-LOCAL build/java-diff-mc-integer-value-of-fixtures-LOCAL build/java-diff-mc-integer-value-of-gate-LOCAL
```
