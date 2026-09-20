# Generated raw41 / byte298630 source stage

This generated-only capacity stage derives exactly from accepted bounded TreeMap
SortedMap/fresh-empty evidence at `parent-2323d952f`. It changes only selected
raw-class count `40→41`, aggregate raw bytes `295438→298630`, and the read-only
checkpoint diagnostic class bound `132→133`.

All 92 ordered bootstrap images and their bytes/positions—including the bounded
TreeMap `SortedMap.isEmpty()` surface—remain unchanged. Native13,
String-local binding10, exception kinds14, frames128, selected-resource count
1/4096, checkpoint1MiB, Head32768, compiler/toolchain, and every other fixed
limit are source-pinned. The bootstrap root remains runtime-derived as
`keccak256(abi.encode(DBOOT,h))`; this stage's fresh-domain 92-image root is
`f638184aef5517ca80bbecd1e81d7e2f75270e348f13e57fd86877e86a4756c0`, never
a hard-coded interpreter root.

The rebuilt runtime is exactly `391172 / 393216` bytes (2044-byte headroom);
the coordinator remains 5394 bytes. The source verifier directly byte-pins the
TreeMap sorted-empty stage and permits only the fresh domain, raw count,
aggregate byte limit, coordinator fixed arrays/checks, driver count guards, and
diagnostic bound.

The generated raw41 q1/q7/direct/reopen chains, raw42 and byte298631 exact
refusals, and retained controls are recorded in `results/gate-summary.json`.
The gate uses only trusted generated Java-8 sources and completes under the
fixed 1200-second cap.

No original artifact/JAR/class/resource, SimpleMessage, provider construction,
factory, world, or Done input is read or claimed. Parent alone appends the
genuine class and performs accelerated replay.

## Reproduction

From repository root (fresh ignored paths):

```sh
python3 evidence/java-evm/minecraft-entry/classcount41-byte298630-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/classcount41-byte298630-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/classcount41-byte298630-preflight/tools/build.py build/java-diff-mc-classcount41-byte298630-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount41-byte298630-preflight/tools/generate_fixtures.py build/java-diff-mc-classcount41-byte298630-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount41-byte298630-preflight/tools/gate.py build/java-diff-mc-classcount41-byte298630-build-repro-LOCAL build/java-diff-mc-classcount41-byte298630-fixtures-repro-LOCAL build/java-diff-mc-classcount41-byte298630-gate-repro-LOCAL
```
