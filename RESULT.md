# Result

Generated-only bounded `Collection` → `Iterable` linkage stage completed from
accepted Integer/String parent `parent-61fd1832a`.

- Appended bootstrap image88 `java/lang/Iterable` (215 bytes; SHA-256
  `d144cca13fbb5ae0bf97773e84efb4308acbf3fe31cd9b4b0488c8a8e447a17f`) with
  only `Iterator iterator()`. Replaced only `java/util/Collection` (368 bytes;
  SHA-256 `a7e0e47540fc39afc022acea939c81d9a2143ef53e59f3227e2dd0ffda16487c`) so
  it extends Iterable and retains add/size/iterator/isEmpty declarations.
- Runtime: 393060 / 393216 bytes; coordinator: 5394 bytes. Bootstrap count88,
  raw33/262158, native13, and all fixed limits remain pinned; diagnostic bound
  advances only from120 to121.
- Focused Collection→Iterable q1/q7/direct/reopen chains agree at 140 Java / 4
  internal steps (epochs140/20/1); the null path agrees at13/3 (epochs13/2/1).
  No-init, both raw replacement, and omitted `forEach`/`spliterator` controls
  are atomic. Retained gate: 96 rows, 347 commands, 4489 canonical receipts,
  305.613 seconds (cap1200).

No default Iterable APIs beyond iterator, host fallback, original artifact/JAR/
class/resource, Provider/factory/world, or Done claim. Parent alone reruns
unchanged original33. Evidence:
`evidence/java-evm/minecraft-entry/iterable-link-preflight/`.
