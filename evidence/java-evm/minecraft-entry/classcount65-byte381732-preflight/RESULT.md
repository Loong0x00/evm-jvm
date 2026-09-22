# Result: generated raw65 / byte381732 capacity stage

- Raised only `64/379594/158 → 65/381732/159`.
- Preserved the 94-image bootstrap root and `Integer.highestOneBit` image exactly.
- Full focused q1/q7/direct/reopen plus retained direct/reopen gate passed in `201.59890630003065` seconds: 523 commands and 1736 verified canonical receipts (under 1200 seconds). Raw65 agrees across quanta/reopen; raw66 is refused at driver/coordinator/engine. Exact 381732 is coordinator-admitted and fully DI0-read, then the unchanged 1MiB checkpoint cap refuses `LC0StateError(1,0)` without Head/root mutation; 381733 is atomically rejected with coordinator error12.
- No original artifact/JAR/external class/resource or AbstractMapEntry replay was used. Parent genuine replay remains deferred.
