# Result: bounded empty Thread stack trace

- Built Java 8 `Thread` slot 50 (565B) and `StackTraceElement` slot 90 (142B).
  `getStackTrace()` returns a fresh non-null empty canonical-leaf array.
- The runtime-derived 91-image bootstrap root is
  `c8f6dad01aaba24b276dd90b4b4bf84ca74c9ae0586612bffa675f66fe7001fe`.
- Recovered the measured direct 395621B runtime to 393157B, below the 393216B
  cap by 59B; runtime SHA-256 is
  `20632e87ced24bcb91eb2370f54a2d5de7dec12e0526f1320b411088b0a450f5`.
- Generated q1/q7/direct/reopen plus retained gate passed: 480 commands,
  8329 canonical receipts, 534.248s. Focused chain: 51 Java/4 internal steps,
  epochs 51/8/1, identical machine/opaque roots.

No real frame trace, StackTraceElement API/construction, Minecraft execution,
provider/factory/world, or Done claim.
