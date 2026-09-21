# Result: generated image5 `Throwable.getStackTrace()` stage

- Changed only bootstrap `java/lang/Throwable` image5. Its bounded `getStackTrace()` returns a fresh, non-null zero-length `StackTraceElement[]`.
- Preserved the inherited Throwable API, 94 bootstrap leaves, raw50/324338, native13, diagnostic bound144, all other limits, and runtime-derived ordered-root construction. Only leaf5 changed; root: `43a87c0dfe115b957cac7c16049b2b54f15420dd57252957c100173f4a350525`.
- Rebuilt engine: `393145 / 393216` bytes (71-byte headroom; baseline 393007). Coordinator remains 5394 bytes.
- A clean parent replay rebuilt artifacts and generated fixtures in fresh ignored directories, then passed the full gate in `699.558816s` (<1200s): 736 commands and 11,703 canonical receipts.
- Focused q1/q7/direct/reopen array freshness runs agree (39 Java / 2 internal steps; epochs 39/6/1); dormant, raw-replacement (`0x427cfac5`, `[6,1]`), raw50, and byte-boundary controls pass.

No original artifact/JAR/class/resource, network, provider/factory execution, Minecraft world, or Done behavior was read, run, or claimed.
