# Result: generated raw66 / byte385532 capacity

- Raised only raw capacity to 66 classes / 385532 bytes and diagnostic class bound to 161. Runtime is 376562/393216 bytes.
- Preserved the 95-image bootstrap root, `Map$Entry` image95, and Integer slot70/highestOneBit byte-for-byte.
- Generated raw66 succeeds identically through q1/q7/direct/reopen (264 JVM / 2 internal steps). Raw67 is atomically refused at driver, coordinator (`MR0Error(2)`), and engine (`LinkError(1,67)`).
- Exact 385532 bytes are DI0-read then refuse at unchanged `LC0StateError(1,0)` without a Head; 385533 atomically refuses at coordinator `MR0Error(12)`.
- Full generated/retained gate: 94.65792048093863 seconds, 60 commands, 991 canonical receipts; fixed bound is 1200 seconds.

No original/JAR/external class/resource/network/provider/world/EULA/Done input or claim. Parent genuine qz replay remains deferred.
