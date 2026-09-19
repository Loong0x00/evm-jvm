# Result: generated raw37 / byte282358

- Exact source basis: accepted raw36 evidence `9c0ebbb5f`; only raw classes
  `36→37`, aggregate raw bytes `281175→282358`, and diagnostic classes
  `126→127` changed.
- Runtime remains 393208 / 393216 bytes (8-byte headroom), SHA-256
  `b20db2e8e8507e635dc7b64cba0a53d0f3a7dd22c673f4ed1838eedd4fb8a7bd`;
  coordinator remains 5394 bytes.
- Raw37 q1/q7/direct/reopen agrees at148 Java/2 internal steps and epochs
  148/22/1. Raw38 is atomically refused by driver, coordinator `MR0Error(2)`,
  and widened-coordinator engine `LinkError(1,38)`.
- Exactly282358 bytes is coordinator-admitted and reaches the ordinary engine
  reserve refusal;282359 is atomically rejected as coordinator `MR0Error(12)`.
  Each aggregate-fixture class is at most230532 bytes, so neither outcome is a
  per-class DI0 limit artifact.
- Generated focused plus retained direct/reopen gate: 109 rows, 380 commands,
  4623 canonical receipts, 311.549 seconds (cap1200).

No original artifact/JAR/class/resource, StatusMessage, Provider/factory/world,
or Done claim is included. Parent alone handles genuine StatusMessage.
