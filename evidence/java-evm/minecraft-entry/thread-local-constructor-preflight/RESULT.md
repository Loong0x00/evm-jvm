# Result: constructor-only `ThreadLocal`

- Exact runtime parent: accepted raw35 `parent-7183e57f8`; append only
  `java/lang/ThreadLocal` at bootstrap index 88 (89 images total), 136 bytes,
  SHA-256 `3b492a73fe71c60d5594f5116e813b857e248d7ca29270a8e33974143dc595d0`.
- Surface: direct `Object` subclass and public `<init>()V` only. No get/set/
  remove/initialValue/withInitial, per-thread state, inheritance, or
  `InheritableThreadLocal` claim.
- Raw35/268379, all prior image slots, native13, fixed resource pipeline and
  limits stay pinned. Read-only diagnostic class bound is 124.
- Semantics-preserving root layout recovery avoids a duplicate image literal:
  runtime 392326 / 393216 bytes (890-byte headroom), SHA-256
  `a917fa3454e39140ab114f1211b69270c5a980b13a4976f71d7060c38edcbd71`;
  coordinator 5394 bytes.
- Constructor identity q1/q7/direct/reopen agrees at 34 Java/2 internal
  steps and epochs 34/5/1. No-init, raw replacement, and five omitted API
  controls pass as bounded atomic outcomes.
- Focused plus retained direct/reopen gate: 104 rows, 365 commands, 4539
  canonical receipts, 312.287 seconds (cap1200).

No original artifact/JAR/class/resource, Provider/factory/world, or Done claim
is included. Parent alone runs original35.
