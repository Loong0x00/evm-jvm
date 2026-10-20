# Generated-only raw150 boundary gate (run 004)

This evidence is a fresh build and generated-fixture run from the source hashes
recorded in `run-report.json`. It does not use an original Minecraft archive or
parent/sibling receipts.

- `gate-summary.json`: q1/q7/q65536/q4096 terminal raw150 MR01 runs, exact
  1,063,930-byte positive, +1-byte and 151-class refusals, codehash refusal.
- `reopen-summary.json` and `q1-raw150.checkpoint.bin`: distinct-process q1
  checkpoint reopen/validation.
- `coordinator-summary.json` and `coordinator-raw-bytes-exact.checkpoint.bin`:
  EVM-built AS0/ZI0/150-DI0/coordinator route and exact-byte terminal engine
  call. The report contains dependency/runtime hashes and measured EVM gas/call
  counts.
- `fixture-manifest.json`, `paired-pins.json`, `logs/`: generated fixture
  hashes, paired artifact hashes, and build/test logs.
- `evidence-sha256.json`: SHA-256/size index for the other files in this run.

The 1 MiB checkpoint quota was sufficient (11,914-byte boundary checkpoints),
so no checkpoint budget was increased. Neither the original Minecraft replay
nor startup/Done was run.
