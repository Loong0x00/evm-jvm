# Result: generated raw64 / byte379594 capacity stage

- Raised only `63/377990/157 → 64/379594/158`.
- Preserved the 94-image bootstrap root and `Integer.highestOneBit` image exactly.
- Full focused q1/q7/direct/reopen plus retained direct/reopen gate passed in `199.569528` seconds: 523 commands and 1731 verified canonical receipts (under 1200 seconds). Raw64 agrees across quanta/reopen; raw65 is refused at driver/coordinator/engine. Exact 379594 is coordinator-admitted and fully DI0-read, then the unchanged 1MiB checkpoint cap refuses `LC0StateError(1,0)` without Head/root mutation; 379595 is atomically rejected with coordinator error12.
- No original artifact/JAR/external class/resource or ImmutableEntry replay was used. Parent genuine replay remains deferred.
