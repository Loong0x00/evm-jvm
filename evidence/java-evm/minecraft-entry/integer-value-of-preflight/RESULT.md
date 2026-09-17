# Result: bounded `Integer.valueOf(int)`

- Exact parent: accepted raw33 `parent-1b7a30656`; only the `java/lang/Integer`
  bootstrap image changed. The former 1667-byte image regenerates exactly from
  the same source with the new method removed; the new 1747-byte image is
  SHA-256 `1b0b1b25e935a2065f2af4d7e3bb1caa677fe08b16247c9d4a0cfbd0abd1d5c6`.
- Added ordinary Java-8 `valueOf(I)Ljava/lang/Integer;` as `new Integer(value)`.
  No cache/identity promise, String/radix overload, formatting, or host
  primitive is supplied.
- Runtime: 392454 / 393216 bytes (762 bytes remain), SHA-256
  `120854fb62f22ace08424c0782af229038d863b91df239486104e2914d594e96`;
  Keccak `28e4cdcd223867965af4468e961c9d2568984a455284d6de1e2b19a752f5a7c4`.
  Coordinator: 5394 bytes, Keccak
  `ee1b816d60ebf3e0ee72eecb65063fc34c944582e96c2962f9081b08edd0c0b6`.
- Focused `-1/0/min/max` q1/q7/direct/reopen agrees at 665 Java / 3 internal
  steps and epochs 665/95/1. No-init, raw replacement, and omitted String
  overload controls pass. Retained direct/reopen gate: 81 rows, 272 commands,
  1512 canonical receipts, 144.675 seconds (cap 1200).

No original artifact/JAR/class/resource was opened. Parent alone runs unchanged
original33; no Provider construction, factory, world, or Done claim is made.
