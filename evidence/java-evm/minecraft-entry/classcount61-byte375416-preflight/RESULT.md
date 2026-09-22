# Result: generated raw61 / byte375416 capacity stage

- Raised only raw capacity `60/373340/154 → 61/375416/155`.
- Preserved all 94 bootstrap images and runtime-derived root, native16, String-local11, System setters, and every non-capacity limit/semantic. Engine: `377312 / 393216` bytes; coordinator: `5394` bytes.
- Full generated gate passed in `160.938569` seconds: 511 commands and 906 canonical receipts (under 1200 seconds). Raw61 q1/q7/direct/reopen agree; raw62 is refused at driver/coordinator/engine boundaries. Exact 375416 is coordinator-admitted and fully DI0-read, then the unchanged 1MiB checkpoint cap rejects it as `LC0StateError(1,0)` without root mutation; 375417 is atomically rejected with coordinator error12.

No original artifact/JAR/class/resource, CollectPreconditions binding/replay, provider/factory, world, EULA, or Done input was read or claimed. Parent genuine `CollectPreconditions` replay remains deferred.
