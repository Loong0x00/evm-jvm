# Result: generated raw68 / byte394767 capacity

- Raised only raw capacity to 68 classes / 394767 bytes and diagnostic class bound to 163. Runtime is 376562/393216 bytes.
- Preserved the 95-image bootstrap root, `Map$Entry` image95, and Integer slot70/highestOneBit byte-for-byte.
- Generated raw68 succeeds identically through q1/q7/direct/reopen (272 JVM / 2 internal steps). Raw69 is atomically refused at driver, coordinator (`MR0Error(2)`), and engine (`LinkError(1,69)`).
- Exact 394767 bytes are fully DI0-read then atomically refuse at unchanged `LC0StateError(1,0)` without a Head; 394768 atomically refuses at coordinator `MR0Error(12)`.
- Full generated/retained gate: 97.91024294798262 seconds, 60 commands, 1000 canonical receipts; fixed bound is 1200 seconds.

No original/JAR/external class/resource/network/provider/world/EULA/Done input or claim. Parent genuine `nf.class` replay remains deferred.
