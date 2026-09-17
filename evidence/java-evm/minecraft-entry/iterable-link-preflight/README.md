# Bounded `Collection` → `Iterable` linkage stage

This generated-only stage derives exactly from accepted Integer/String parent
`parent-61fd1832a`. It appends Java-8 bootstrap image88
`java/lang/Iterable<T>` and replaces only the existing bootstrap
`java/util/Collection<E>` image. The appended 215-byte class has the sole
method `Iterator<T> iterator()` (compiled-class SHA-256
`d144cca13fbb5ae0bf97773e84efb4308acbf3fe31cd9b4b0488c8a8e447a17f`). The
368-byte replacement Collection image has SHA-256
`a7e0e47540fc39afc022acea939c81d9a2143ef53e59f3227e2dd0ffda16487c`; it now
extends `Iterable<E>` while retaining its accepted `add`, `size`, `iterator`,
and `isEmpty` declarations.

No other bootstrap position or library behavior is expanded. In particular,
`forEach`, `spliterator`, `Consumer`, `Spliterator`, streams, collection
mutation, and any host collection/iterator fallback are absent. Existing guest
collection implementations continue to provide their pre-existing `iterator`
methods.

The staged source verifier pins all parent inputs and confirms exactly 88
bootstrap hashes. The build measured runtime 393060 / 393216 bytes (156-byte
headroom) and a 5394-byte coordinator. Raw33/262158, native13, the String-local
binding10, 14 exception kinds, frames128, selected-resource count1/4096,
checkpoint1MiB, Head32768, the compiler/toolchain and outlined tail stay fixed;
the diagnostic class bound alone advances from120 to121.

Trusted Java-8 generated linkage fixtures prove `Collection` to `Iterable`
return assignment, identity, and iterator dispatch across q1/q7/direct/reopen:
140 Java and 4 internal steps, epochs 140/20/1, with identical terminal machine
root and opaque payload. The null path likewise agrees at13/3 steps and epochs
13/2/1. A no-use root leaves the appended image uninitialized. Raw `Iterable`
and raw replacement `Collection` controls both reject atomically before a Head.
The deliberately omitted Java-8 defaults reject atomically as member-resolution
CallError(3,10) for `forEach` and CallError(3,9) for `spliterator`.

The focused and retained direct/reopen gate completed 96 result rows, 347
commands, and 4489 canonical receipts in 305.613 seconds (fixed cap1200).
Only trusted generated Java-8 sources are compiled. No original artifact, JAR,
class, resource, Provider construction, factory, world, or Done input is read
or claimed; the parent alone reruns unchanged original33.

Reproduce with local pinned tools only:

```sh
python3 evidence/java-evm/minecraft-entry/iterable-link-preflight/tools/build.py build/java-diff-mc-iterable-link-build-LOCAL
python3 evidence/java-evm/minecraft-entry/iterable-link-preflight/tools/generate_fixtures.py build/java-diff-mc-iterable-link-fixtures-LOCAL
python3 evidence/java-evm/minecraft-entry/iterable-link-preflight/tools/gate.py build/java-diff-mc-iterable-link-build-LOCAL build/java-diff-mc-iterable-link-fixtures-LOCAL build/java-diff-mc-iterable-link-gate-LOCAL
```
