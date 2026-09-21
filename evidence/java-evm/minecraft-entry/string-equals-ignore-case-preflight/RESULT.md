# Result: generated `String.equalsIgnoreCase(String)` image26

- Replaced only bootstrap String root-leaf index26 (zero-based) with a
  1503-byte Java-8 image
  (`SHA-256 4cff1fc7c1ee49c0e070a7aec64963193e34206838c509003715f972aa8d58a0`).
  It returns false for null, compares UTF-16 units, and folds ASCII A-Z/a-z
  only. Non-ASCII unequal units remain unequal; this is not general Unicode
  case folding.
- Bootstrap count93, Objects image93, diagnostic141, raw48/314425, native13,
  limits/toolchain, and every non-String ordered leaf remain pinned. Dynamic
  root: `910d9bcec092acbd3476403e8fa6bb2a0079193a029908e5f1b368342d8b7731`.
- Runtime rebuilt at `391507 / 393216` bytes; coordinator remains 5394 bytes.
- Generated exact/lower-upper/mismatch/length/null/non-ASCII q1/q7/direct/reopen
  chains agree. The crafted omitted Object descriptor returns the unchanged
  `StringProfileError(1,4)` with an unchanged root.
- Full generated-only gate passed in 688.5122894980013 seconds (under 1200):
  709 commands and 11597 canonical receipts.

No original artifact/JAR/class/resource/world was read. No logger factory,
Minecraft world, or Done claim is made; parent genuine replay remains separate.
