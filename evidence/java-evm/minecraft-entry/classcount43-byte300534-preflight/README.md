# Generated raw43 / byte300534 source stage

This generated-only capacity stage derives exactly from accepted raw42/byte300031
source evidence at `parent-ee1f62dc5`. It changes only selected raw-class count
`42→43`, aggregate raw bytes `300031→300534`, and the read-only checkpoint
diagnostic class bound `134→135`.

All 92 ordered bootstrap images and their bytes/positions remain unchanged.
Native13, String-local binding10, exception kinds14, frames128,
selected-resource count1/4096, checkpoint1MiB, Head32768, compiler/toolchain,
and every other fixed limit are source-pinned. The bootstrap root remains
runtime-derived as `keccak256(abi.encode(DBOOT,h))`; this stage's fresh-domain
92-image root is `cd5adb140cab52e71a90a91eeb220674e49d80bb79c12b36ccefd05e01f8a50f`,
never a hard-coded interpreter root.

The rebuilt runtime is exactly `391172 / 393216` bytes (2044-byte headroom);
the coordinator remains 5394 bytes. The source verifier mechanically rebuilds
every permitted delta from raw42 and independently encodes the committed
`uint32[11]` limits tuple. It permits only the fresh domain, raw count,
aggregate byte limit, coordinator fixed arrays/checks, driver count guards, and
diagnostic bound.

The generated raw43 q1/q7/direct/reopen chains, raw44 and byte300535 exact
refusals, and retained controls are recorded in `results/gate-summary.json`.
The gate uses only trusted generated Java-8 sources and completed under the
fixed 1200-second cap.

No original artifact/JAR/class/resource, LoggerContextFactory, provider
construction, factory execution, world, or Done input is read or claimed.
Parent alone owns the genuine interface append and genuine class/factory
execution or accelerated replay.

## Reproduction

From repository root (fresh ignored paths):

```sh
python3 evidence/java-evm/minecraft-entry/classcount43-byte300534-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/classcount43-byte300534-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/classcount43-byte300534-preflight/tools/build.py build/java-diff-mc-classcount43-byte300534-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount43-byte300534-preflight/tools/generate_fixtures.py build/java-diff-mc-classcount43-byte300534-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount43-byte300534-preflight/tools/gate.py build/java-diff-mc-classcount43-byte300534-build-repro-LOCAL build/java-diff-mc-classcount43-byte300534-fixtures-repro-LOCAL build/java-diff-mc-classcount43-byte300534-gate-repro-LOCAL
```
