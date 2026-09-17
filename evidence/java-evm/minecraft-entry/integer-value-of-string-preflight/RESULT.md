# Result: bounded `Integer.valueOf(String)`

- Exact parent: accepted WeakReference `parent-cb0c15e54`. Only bootstrap image70
  `java/lang/Integer` changed: 1827 bytes, SHA-256
  `0fb2a617951eb2228ac6277a85ae44da1c59647904d82c2cb68b613c6e33ba03`.
- Added ordinary Java-8 `valueOf(String)` as `new Integer(parseInt(s))`; retained
  `valueOf(int)`, constructors, conversions, equality/hash/compare, and decimal
  `parseInt`. Null/empty/sign/invalid/overflow raise guest NumberFormatException.
- Runtime: 391802 / 393216 bytes (1414-byte headroom); coordinator 5394 bytes.
  Raw33/262158, 87 bootstraps, native13, diagnostic120, and all other limits stay
  pinned.
- Valid/invalid/null/overflow q1/q7/direct/reopen agree respectively at
  1240/3, 320/11, 38/8, and 771/9 Java/internal steps. No-init/raw replacement
  and omitted radix controls pass. Retained direct/reopen gate: 89 rows,
  322 commands, 4311 canonical receipts, 292.809 seconds (cap 1200).

No radix overload, cache identity, formatting, host parser/primitive, original
artifact/JAR/class/resource, Provider/factory/world, or Done claim is included.
Parent alone runs unchanged original33.
