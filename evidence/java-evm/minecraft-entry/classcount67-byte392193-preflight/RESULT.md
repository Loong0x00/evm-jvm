# Result: generated raw67 / byte392193 capacity

- Raised only raw capacity to 67 classes / 392193 bytes and diagnostic class bound to 162. Runtime is 376562/393216 bytes.
- Preserved the 95-image bootstrap root, `Map$Entry` image95, and Integer slot70/highestOneBit byte-for-byte.
- Generated raw67 succeeds identically through q1/q7/direct/reopen (268 JVM / 2 internal steps). Raw68 is atomically refused at driver, coordinator (`MR0Error(2)`), and engine (`LinkError(1,68)`).
- Exact 392193 bytes are fully DI0-read then refuse at unchanged `LC0StateError(1,0)` without a Head; 392194 atomically refuses at coordinator `MR0Error(12)`.
- Full generated/retained gate: 98.80816338700242 seconds, 60 commands, 996 canonical receipts; fixed bound is 1200 seconds.

No original/JAR/external class/resource/network/provider/world/EULA/Done input or claim. Parent genuine `HashBiMap$Inverse` replay remains deferred.
