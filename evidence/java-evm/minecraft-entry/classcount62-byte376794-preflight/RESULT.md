# Result: generated raw62 / byte376794 capacity stage

- Raised only raw capacity `61/375416/155 → 62/376794/156`.
- Preserved all 94 bootstrap images and runtime-derived root, native16, String-local11, System setters, and every non-capacity limit/semantic. Engine: `377312 / 393216` bytes; coordinator: `5394` bytes.
- Full generated gate passed in `160.542056` seconds: 511 commands and 911 canonical receipts (under 1200 seconds). Raw62 q1/q7/direct/reopen agree; raw63 is refused at driver/coordinator/engine boundaries. Exact 376794 is coordinator-admitted and fully DI0-read, then the unchanged 1MiB checkpoint cap rejects it as `LC0StateError(1,0)` without root mutation; 376795 is atomically rejected with coordinator error12.

No original artifact/JAR/class/resource, Hashing binding/replay, provider/factory, world, EULA, or Done input was read or claimed. Parent genuine `Hashing` replay remains deferred.
