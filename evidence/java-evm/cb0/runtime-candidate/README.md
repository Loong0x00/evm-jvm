# MC-CB0 runtime candidate build record

Status: **candidate only; not accepted**. This record pins the reproducible
controller source and generated artifact initially built on the CB0 frozen revision.
It does not record a transport acceptance, original-JAR handling, Java/Minecraft
execution, EULA acceptance, listener, world, or `Done` marker.

Run `./reproduce.sh` from this directory's repository checkout. It uses the tracked
`jvmevm/localcontinuation/cb0/runtime` source and exact local npm lock, rebuilds,
checks generated artifacts, and prints fresh SHA-256 sums. `build-check.log` is the
first generated-artifact consistency check; the committed `SHA256SUMS` gives the
corresponding source and output hashes.

## Controller-only EVM replay

`reproduce-e2e.sh` records a durable reproducer for the actual EVM controller
replay performed against the committed production-domain artifact. It derives an
ignored adapter from the retained parent generated-fixture driver solely to read
the DI0/ZI0/AS0 package and call the CB0 ABI/schema; the adaptation is tracked in
`adapt_parent_driver.py`. `e2e-summary.json` pins the artifact, adapter and fixture
hashes plus direct/q1/q7/input-sensitive outcomes, coded negative failures and the
exact-65536 paging result. This is deliberately not a claim that the separate CB0
transport has passed its memory/disk/actual-IO gate or that this candidate is
accepted.
