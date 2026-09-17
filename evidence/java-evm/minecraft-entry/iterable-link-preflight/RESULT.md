# Result: bounded `Collection` → `Iterable` linkage

- Exact basis: accepted Integer/String parent `parent-61fd1832a`. Appended
  bootstrap image88 `java/lang/Iterable` (215 bytes, compiled SHA-256
  `d144cca13fbb5ae0bf97773e84efb4308acbf3fe31cd9b4b0488c8a8e447a17f`) with
  only `Iterator iterator()`, and replaced only `java/util/Collection` (368
  bytes, SHA-256
  `a7e0e47540fc39afc022acea939c81d9a2143ef53e59f3227e2dd0ffda16487c`) so it
  extends Iterable while retaining add/size/iterator/isEmpty declarations.
- Runtime is 393060 / 393216 bytes (156-byte headroom); coordinator is5394
  bytes. There are 88 bootstrap images; raw33/262158, native13, diagnostic121,
  and all other fixed limits remain pinned.
- Collection→Iterable return/assignment/identity/iterator completes q1/q7/direct
  at140 Java/4 internal steps and epochs140/20/1. The null chain agrees at13/3
  and13/2/1. No-init, both raw replacement, omitted `forEach` CallError(3,10),
  and omitted `spliterator` CallError(3,9) controls are atomic.
- Focused plus retained direct/reopen gate: 96 rows, 347 commands, 4489 canonical
  receipts, 305.613 seconds (cap1200).

No default Iterable APIs beyond `iterator`, host collection fallback, original
artifact/JAR/class/resource, Provider/factory/world, or Done claim is included.
Parent alone runs unchanged original33.
