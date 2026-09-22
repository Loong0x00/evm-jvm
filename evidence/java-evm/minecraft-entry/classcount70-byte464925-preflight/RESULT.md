# Result: generated raw70 / byte464925 capacity

- Raised only raw capacity to 70 classes / 464925 bytes and diagnostic class bound to 166. Runtime is 379383/393216 bytes.
- Preserved the frozen 96-image root, String lower-case image, Locale image, Map.Entry, Integer, global native16, String-local12, and all non-capacity source text byte-for-byte.
- Generated raw70 succeeds identically through q1/q7/direct/reopen. Raw71 is atomically refused at driver, coordinator (`MR0Error(2)`), and engine (`LinkError(1,71)`).
- Exact 464925 bytes are fully DI0-read then atomically refuse at unchanged `LC0StateError(1,0)` without a durable Head; 464926 atomically refuses at coordinator `MR0Error(12)`.
- Full generated/retained gate: 147.19057744299062 seconds, 94 commands, 1621 canonical receipts; fixed bound is 1200 seconds. `results/independent-verification.json` rechecks the durable boundaries, equivalence and receipt count.

No original/JAR/external class/resource/network/provider/world/EULA/Done input or claim. Parent genuine Validate replay remains deferred.
