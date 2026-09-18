# Result: generated raw34 / byte268053

- Exact runtime basis: accepted Iterable parent `parent-cc433baf7`; only raw
  classes `33→34`, aggregate raw bytes `262158→268053`, and diagnostic classes
  `121→122` changed.
- Runtime: 393060 / 393216 bytes (exactly156-byte headroom), SHA-256
  `a994cffb3270ec253c0ea818733f96a7bb2f1e65399b537380a31ab9829693ff`;
  coordinator 5394 bytes.
- Raw34 q1/q7/direct/reopen agrees at136 Java/2 internal steps and epochs
  136/20/1. Raw35 is atomically refused by driver, coordinator
  `MR0Error(2)`, and widened-coordinator engine `LinkError(1,35)`.
- Exactly268053 bytes is coordinator-admitted, reaches 97 genuine DI0 reads,
  and retains the ordinary engine reserve refusal; 268054 is atomically
  rejected as coordinator `MR0Error(12)`. Each aggregate-fixture class is at
  most219010 bytes, so neither outcome is a per-class DI0 limit artifact.
- Generated focused plus retained direct/reopen gate: 96 rows, 347 commands,
  4494 canonical receipts, 299.275 seconds (cap1200).

No original artifact/JAR/class/resource, Provider/factory/world, or Done claim
is included. Parent alone appends the genuine class and reruns original34.
