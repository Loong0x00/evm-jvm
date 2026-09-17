# Result: bounded `WeakReference`

- Exact parent: accepted Integer `parent-36ea2d7e6`; one Java-8 image appends
  after all 86 existing images. `java/lang/ref/WeakReference` is 281 bytes,
  SHA-256 `9e3ef194b9d08f98f8e99f45fe8e192e38f6120e214e46596b8f9351351f9a36`.
- Surface: direct `Object` subclass, one strong deterministic `referent` field,
  `(Object)V`, and `get()Object`; null stays null. There is no GC clearing,
  `Reference`/`ReferenceQueue`, clear/enqueue/isEnqueued, reachability, or
  finalization surface.
- Runtime: 391765 / 393216 bytes (1451-byte headroom; required 762-byte margin
  retained), SHA-256 `4c16833717e715a9d4dbc1f370cd96f63e897e4d275d0721fcfaba84561bd20e`;
  coordinator remains 5394 bytes. Diagnostic class bound is 120.
- Focused identity/null q1/q7/direct/reopen agrees at 72 Java / 2 internal
  steps and epochs 72/11/1. No-init, raw replacement, and omitted `clear()`
  controls pass. Retained direct/reopen gate: 85 rows, 286 commands, 1597
  canonical receipts, 148.051 seconds (cap 1200).

No original artifact/JAR/class/resource was opened. Parent alone runs unchanged
original33; no Provider construction, factory, world, or Done claim is made.
