# Result: bounded directly-created `ThreadLocal.set`

- Replaced only bootstrap image89 (`java/lang/ThreadLocal`) from
  `parent-15aa4b8b0` with the 305-byte Java 8 final direct class carrying one
  private `Object value` field, SHA-256
  `041db70026c508194d1b13ccdc988e82fb07316a4900c3955b2d5aa3e0664d9b`.
  `get()` returns default null and the exact object stored/replaced/nulled by
  `set(Object)` for the only guest thread.
- Raw37/282358, all 90 image positions, diagnostic127, native13, resource
  pipeline, gas policy, frames/checkpoint/Head caps, and toolchain remain
  pinned. The full root stays runtime-derived over ordered image hashes:
  `85fbf6a9abd54f7fbc872c0387cc129782adb52f753bc448bc099dabeef62ab1`.
- Runtime is 393072 / 393216 bytes (144-byte headroom) from the 392934-byte
  baseline; no layout recovery was used. Coordinator remains 5394 bytes.
- Focused get/set/null/replace/identity q1/q7/direct/reopen agrees at 148 Java
  and 2 internal steps, epochs 148/22/1, one machine root and opaque payload.
  Retained constructor identity agrees at 40/2 and epochs 40/6/1.
- `remove`, `withInitial`, subclass/`initialValue`, and multithread controls
  refuse atomically with unchanged roots. The generated gate completed 429
  commands, 5412 canonical receipts, in 356.189 seconds (cap1200).

No original artifact/JAR/class/resource execution, `StringBuilder.setLength`,
provider/factory/world, or Done claim. Parent alone reruns original37.
