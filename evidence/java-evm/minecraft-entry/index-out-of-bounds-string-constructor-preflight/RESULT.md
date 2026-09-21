# Result: generated `IndexOutOfBoundsException(String)` constructor preflight

- The saved fresh generated-only gate passed in `843.585862` seconds (under the 1200-second limit): 498 commands and 12,877 strict canonical receipts.
- `RuntimeException(String)` and `IndexOutOfBoundsException(String)` preserve the caller-owned message through the retained `Exception(String)` / `Throwable.detailMessage` path. Empty, ASCII `index-42`, and null message cases agree across q1/q7/direct/reopen; an uncaught object terminates as `java/lang/IndexOutOfBoundsException`; roots not naming either class do not initialize them.
- The two unsupported RuntimeException cause overloads remain atomic root-unchanged member-resolution refusals. The source verifier pins only bootstrap leaves 16 and 22 as changed, plus raw `50/324338`, diagnostic bound 144, native13, and all other limits.
- Rebuilt engine is `367361 / 393216` bytes (`SHA-256 41e0325576951b56822b5b857192f31d36c040ece16349a60f46de1914e90c9a`); coordinator is 5394 bytes. Exact pins and the complete saved summaries are under `results/`.

No original artifact/JAR/class/resource, factory execution, world, network, or Done behavior was read, executed, or claimed.
