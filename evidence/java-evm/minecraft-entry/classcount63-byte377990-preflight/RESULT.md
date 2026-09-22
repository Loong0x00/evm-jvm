# Result: generated raw63 / byte377990 capacity stage

- Raised only raw capacity `62/376794/156 → 63/377990/157`.
- Preserved the 94-image bootstrap root and `Integer.highestOneBit` image exactly.
- Full generated gate passed in `197.963590` seconds: 523 commands and 1726 canonical receipts (under 1200 seconds). Raw63 q1/q7/direct/reopen agree; raw64 is refused at driver/coordinator/engine. Exact 377990 is coordinator-admitted and fully DI0-read, then the unchanged 1MiB checkpoint cap refuses `LC0StateError(1,0)` without Head/root mutation; 377991 is atomically rejected with coordinator error12.
- No original artifact/JAR/external class/resource or HashBiMap$BiEntry replay was used. Parent genuine replay remains deferred.
