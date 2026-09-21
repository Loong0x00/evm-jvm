# Result: generated `StringBuilder.append(int)` preflight

- Changed only bootstrap slot 84 / `java/lang/StringBuilder` with guest Java 8 `append(int)`; it returns the same builder and produces exact decimal text for MIN, `-1`, `0`, positive, MAX, and a prefixed builder.
- Image: 1097 bytes, SHA-256 `a3d2543ce4401a36011be7bdd8e24ef9ee475f5361c615ab8964456c94728020`; only leaf 84 changes in the runtime-derived 94-leaf root `876bf37291d10bc755d30f52c07f2a2fcf122f331a2e2c3302f2cea03bb4ec9d`.
- Clean parent replay: engine 367072 / 393216 bytes, coordinator 5394 bytes; whole generated gate 865.708077s (<1200s), 443 commands, 14349 canonical receipts.
- All six focused q1/q7/direct/reopen chains agree; omitted `append(long)` and `append(Object)` remain atomic `CallError(3,8)` / `CallError(3,9)` refusals. Retained raw50/raw51, byte-boundary, no-init, raw-replacement, and prior direct/reopen controls pass.

No original Minecraft input, resource, world, or Done behavior was used or claimed. This remains generated-only preflight evidence, not production/profile acceptance.
