# Result: generated raw36 / byte281175

- Exact runtime basis: accepted Math parent `parent-3af172306`; only raw
  classes `35→36`, aggregate raw bytes `268379→281175`, and diagnostic classes
  `125→126` changed.
- Runtime remains 393208 / 393216 bytes (8-byte headroom), SHA-256
  `44106ff6f9b60ad22467ab047ea640a814c663d8ec33270f209d358af30580db`;
  coordinator remains 5394 bytes.
- Raw36 q1/q7/direct/reopen agrees at144 Java/2 internal steps and epochs
  144/21/1. Raw37 is atomically refused by driver, coordinator `MR0Error(2)`,
  and widened-coordinator engine `LinkError(1,37)`.
- Exactly281175 bytes is coordinator-admitted and reaches the ordinary engine
  reserve refusal;281176 is atomically rejected as coordinator `MR0Error(12)`.
  Each aggregate-fixture class is at most229680 bytes, so neither outcome is a
  per-class DI0 limit artifact.
- Generated focused plus retained direct/reopen gate: 109 rows, 380 commands,
  4618 canonical receipts, 312.448 seconds (cap1200).

No original artifact/JAR/class/resource, ParameterFormatter, Provider/factory/
world, or Done claim is included. Parent alone handles genuine ParameterFormatter.
