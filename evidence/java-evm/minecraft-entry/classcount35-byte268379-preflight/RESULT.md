# Result: generated raw35 / byte268379

- Exact runtime basis: accepted raw34 parent `parent-be5f9998e`; only raw
  classes `34→35`, aggregate raw bytes `268053→268379`, and diagnostic classes
  `122→123` changed.
- Runtime: 393060 / 393216 bytes (exactly156-byte headroom), SHA-256
  `648c3c2cc0755783ec5a2d00518ad7ef0fa920dd47b5286fde7f8d43e60ce309`;
  coordinator 5394 bytes.
- Raw35 q1/q7/direct/reopen agrees at140 Java/2 internal steps and epochs
  140/20/1. Raw36 is atomically refused by driver, coordinator `MR0Error(2)`,
  and widened-coordinator engine `LinkError(1,36)`.
- Exactly268379 bytes is coordinator-admitted, reaches the ordinary engine
  reserve refusal, and268380 is atomically rejected as coordinator
  `MR0Error(12)`. Each aggregate-fixture class is at most219149 bytes, so
  neither outcome is a per-class DI0 limit artifact.
- Generated focused plus retained direct/reopen gate: 96 rows, 347 commands,
  4498 canonical receipts, 303.120 seconds (cap1200).

No original artifact/JAR/class/resource, Provider/factory/world, or Done claim
is included. Parent alone runs original35; no message formatting/provider
factory/world/Done claim is made here.
