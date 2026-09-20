# Generated raw42 / byte300031 source stage

This generated-only capacity stage derives exactly from accepted raw41/byte298630
source evidence at `parent-806561af7`. It changes only selected raw-class count
`41→42`, aggregate raw bytes `298630→300031`, and the read-only checkpoint
diagnostic class bound `133→134`.

All 92 ordered bootstrap images and their bytes/positions remain unchanged.
Native13, String-local binding10, exception kinds14, frames128,
selected-resource count1/4096, checkpoint1MiB, Head32768, compiler/toolchain,
and every other fixed limit are source-pinned. The bootstrap root remains
runtime-derived as `keccak256(abi.encode(DBOOT,h))`; this stage's fresh-domain
92-image root is `30c9537bdd5dc001efa3d8f7513d23a52195638b30e8c196de661d662a379a91`,
never a hard-coded interpreter root.

The rebuilt runtime is exactly `391172 / 393216` bytes (2044-byte headroom);
the coordinator remains 5394 bytes. The source verifier mechanically rebuilds
every permitted delta from raw41 and independently encodes the committed
`uint32[11]` limits tuple. It permits only the fresh domain, raw count,
aggregate byte limit, coordinator fixed arrays/checks, driver count guards, and
diagnostic bound.

The generated raw42 q1/q7/direct/reopen chains, raw43 and byte300032 exact
refusals, and retained controls are recorded in `results/gate-summary.json`.
The gate uses only trusted generated Java-8 sources and completes under the
fixed 1200-second cap.

No original artifact/JAR/class/resource, SimpleMessage,
SimpleLoggerContextFactory, provider construction, or factory execution is
read or claimed. Parent alone appends the genuine class and performs genuine
class/factory execution and accelerated replay.

## Reproduction

From repository root (fresh ignored paths):

```sh
python3 evidence/java-evm/minecraft-entry/classcount42-byte300031-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/classcount42-byte300031-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/classcount42-byte300031-preflight/tools/build.py build/java-diff-mc-classcount42-byte300031-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount42-byte300031-preflight/tools/generate_fixtures.py build/java-diff-mc-classcount42-byte300031-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount42-byte300031-preflight/tools/gate.py build/java-diff-mc-classcount42-byte300031-build-repro-LOCAL build/java-diff-mc-classcount42-byte300031-fixtures-repro-LOCAL build/java-diff-mc-classcount42-byte300031-gate-repro-LOCAL
```
