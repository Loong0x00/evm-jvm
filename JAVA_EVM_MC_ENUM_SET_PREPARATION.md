# Measured java/util/EnumSet preparation — benchmark task 1/3

Accepted original29 reaches epoch601/4183J/35 internal and misses `java/util/EnumSet` at
`StandardLevel.<clinit>` PC187: `EnumSet.allOf(StandardLevel.class)`. Pinned javap also
shows later `LEVELSET.iterator()` in `getStandardLevel(int)`. Implement the smallest
genuine EVM-owned bounded EnumSet/allOf/immutable-or-snapshot iteration behavior justified
by that path. Do not special-case Log4j/StandardLevel, fabricate constants, use host
reflection, bypass class initialization, or import host classes. Any enum universe must be
derived generically from canonical guest class metadata/static fields after genuine init.

This is paired benchmark task1. Terra-max and DeepSeek-max receive byte-identical task and
context manifests in separate worktrees and execute sequentially to avoid machine
contention. One candidate at a time may write semantic Solidity. Parent machine gates
supersede judges. Three independent Sol-xhigh judges receive anonymized artifacts and score
correctness, architecture understanding, minimality, robustness, maintainability and
completion. Raw29/262144, bootstrap82, runtime393216,1B/25M, frames/checkpoint/head and all
prior enum/cap/queue gates remain fixed. Workers cannot access original artifacts/worlds;
parent alone reruns original29. No push or Done claim.
