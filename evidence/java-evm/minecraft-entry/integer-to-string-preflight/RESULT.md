# Result: generated `Integer.toString(int)` preflight

- Changed only bootstrap slot 70 with guest Java 8 static `Integer.toString(int)` delegating to `new StringBuilder().append(value).toString()`.
- Exact signed decimal and fresh content/identity checks pass for MIN, `-1`, `0`, `123456789`, and MAX under q1/q7/direct/reopen. Radix and unsigned methods remain atomic `CallError(3,4)` and `CallError(3,1)` omissions.
- Integer image is 1959 bytes, SHA-256 `56b891f66fbab31669688a128b8a888291183461adb3aaf667aba394cd1455a8`; only leaf 70 changes in the runtime-derived 94-leaf root `acc183127fc38ae8594433310d91c91617814f764dc6d5407ffd4a3741a9f2c6`.
- Rebuilt engine is 367235/393216 bytes; coordinator is unchanged at 5394 bytes. The fresh generated gate passed in 798.433708s (<1200s), with 457 commands and 12237 canonical receipts.

No original Minecraft input, resource, world, or Done behavior was used or claimed. Parent genuine replay remains separate.
