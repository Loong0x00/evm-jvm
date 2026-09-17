# Result

Generated-only bounded `Integer.valueOf(String)` stage completed from accepted
WeakReference parent `parent-cb0c15e54`.

- Replaced only bootstrap `java/lang/Integer` image (1827 bytes, SHA-256
  `0fb2a617951eb2228ac6277a85ae44da1c59647904d82c2cb68b613c6e33ba03`).
  `valueOf(String)` is ordinary Java-8 `new Integer(parseInt(s))`; accepted
  `valueOf(int)` and all prior Integer methods remain.
- Runtime is 391802 / 393216 bytes; coordinator is 5394 bytes. Raw33/262158,
  87 bootstrap images, native13, diagnostic120, and all other limits are pinned.
- Valid/invalid/null/overflow focused q1/q7/direct/reopen chains agree. The
  retained direct/reopen gate completed 89 rows, 322 commands, and 4311 canonical
  receipts in 292.809 seconds (cap 1200). Radix, raw replacement, and no-init
  controls refuse as specified.

No original artifact/JAR/class/resource, Provider/factory/world, or Done claim.
Parent alone runs unchanged original33. Evidence:
`evidence/java-evm/minecraft-entry/integer-value-of-string-preflight/`.
