# Generated raw45 / byte306227 source stage

This generated-only capacity stage derives exactly from accepted raw44/byte305539
source evidence at `parent-00928f555`. It changes only selected raw-class count
`44→45`, aggregate raw bytes `305539→306227`, and the read-only checkpoint
diagnostic class bound `136→137`.

All 92 ordered bootstrap images and their bytes/positions remain unchanged.
Native13, String-local binding10, exception kinds14, frames128,
selected-resource count1/4096, checkpoint1MiB, Head32768, compiler/toolchain,
and every other fixed limit are source-pinned. The bootstrap root remains
runtime-derived as `keccak256(abi.encode(DBOOT,h))`; this stage's fresh-domain
92-image root is `77235f26181174b0a102dc18e55e3dee075fd9e31c99f6396a372cb50438f12a`,
never a hard-coded interpreter root.

The rebuilt runtime is exactly `391172 / 393216` bytes (2044-byte headroom);
the coordinator remains 5394 bytes. The source verifier mechanically rebuilds
every permitted delta from raw44 and independently encodes the committed
`uint32[11]` limits tuple. It permits only the fresh domain, raw count,
aggregate byte limit, coordinator fixed arrays/checks, driver count guards, and
diagnostic bound.

The generated raw45 q1/q7/direct/reopen chains, raw46 and byte306228 exact
refusals, and retained controls are recorded in `results/gate-summary.json`.
The gate uses only trusted generated Java-8 sources and completed under the
fixed 1200-second cap.

No original artifact/JAR/class/resource, `LoggerContext`, provider construction,
factory execution, world, or Done input is read or claimed. Parent alone owns
the genuine interface append and genuine class/factory execution or accelerated
replay.

## Reproduction

From repository root (fresh ignored paths):

```sh
python3 evidence/java-evm/minecraft-entry/classcount45-byte306227-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/classcount45-byte306227-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/classcount45-byte306227-preflight/tools/build.py build/java-diff-mc-classcount45-byte306227-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount45-byte306227-preflight/tools/generate_fixtures.py build/java-diff-mc-classcount45-byte306227-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount45-byte306227-preflight/tools/gate.py build/java-diff-mc-classcount45-byte306227-build-repro-LOCAL build/java-diff-mc-classcount45-byte306227-fixtures-repro-LOCAL build/java-diff-mc-classcount45-byte306227-gate-repro-LOCAL
```
