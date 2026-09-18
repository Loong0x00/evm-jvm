# Result: bounded Java 8 `Math` int min/max

- Appended only 253-byte `java/lang/Math` at bootstrap index 89 (90 images
  total), with private `<init>()V` and ordinary static `max(II)I` / `min(II)I`;
  diagnostic class bound `124→125`.
- Raw35/268379, the existing 89 bootstrap slots, native13, resource pipeline,
  and fixed limits remain pinned. The recovered runtime is 393208 / 393216
  bytes (8-byte headroom), SHA-256
  `40f0fc6ea00b91a84e3bbf68798f9c09f127054f29603cce8407d96b8b1265c7`.
- Equal, sign-crossing, and `INT_MIN`/`INT_MAX` q1/q7/direct/reopen executions
  agree at 63 Java/2 internal steps and epochs 63/9/1. No-init, raw replacement,
  and omitted `abs`/`addExact` controls are bounded atomic outcomes.
- Focused plus retained direct/reopen gate: 109 rows, 380 commands, 4613
  canonical receipts, 318.462 seconds (cap1200).

No long/floating/abs/round/random/exact arithmetic, original artifact/JAR/class/
resource, Provider/factory/world, or Done claim. Parent alone runs original35.
