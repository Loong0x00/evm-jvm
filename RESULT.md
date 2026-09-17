# Result

Generated-only bounded `Integer.valueOf(int)` stage completed from accepted
raw33 parent `parent-1b7a30656`.

- Replaced only the fixed `java/lang/Integer` bootstrap image. Existing source
  methods regenerate the exact parent 1667-byte image when the one new method
  is removed; the new 1747-byte image adds ordinary Java-8
  `valueOf(int) { return new Integer(value); }`.
- One source build produced engine `392454 / 393216` bytes (762 bytes remain),
  SHA-256 `120854fb62f22ace08424c0782af229038d863b91df239486104e2914d594e96`;
  coordinator remains 5394 bytes.
- Focused `-1`, `0`, min, max, equality/value/hash and distinct-allocation
  fixture passes q1/q7/direct/reopen at 665 Java / 3 internal steps and epochs
  665/95/1 with identical machine roots and opaque payloads. No-init, raw
  replacement, and omitted String overload controls pass.
- Full retained direct/reopen generated gate: 81 rows, 272 commands, 1512
  canonical receipts, 144.675 seconds (cap 1200).

No cache/identity guarantee, String/radix overload, formatting, host primitive,
or original artifact/JAR/class/resource is included. Parent alone runs unchanged
original33; no Provider construction, factory, world, or Done claim is made.

Evidence: `evidence/java-evm/minecraft-entry/integer-value-of-preflight/`.
