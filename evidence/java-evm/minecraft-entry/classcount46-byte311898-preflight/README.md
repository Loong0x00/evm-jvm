# Generated raw46 / byte311898 source stage

This generated-only capacity stage derives exactly from accepted raw45/byte306227
source evidence at `parent-db2653e21`. It changes only selected raw-class count
`45→46`, aggregate raw bytes `306227→311898`, and the read-only checkpoint
diagnostic class bound `137→138`.

All 92 ordered bootstrap images and their bytes/positions remain unchanged.
Native13, String-local binding10, exception kinds14, frames128,
selected-resource count1/4096, checkpoint1MiB, Head32768, compiler/toolchain,
and every other fixed limit are source-pinned. The bootstrap root remains
runtime-derived as `keccak256(abi.encode(DBOOT,h))`; this stage's fresh-domain
92-image root is `c7a5dce384ac935c312b4c2bebe0bf774fd994ded41fc7a621516cd506c9f114`,
never a hard-coded interpreter root.

The rebuilt runtime is exactly `391172 / 393216` bytes (2044-byte headroom);
the coordinator remains 5394 bytes. The source verifier mechanically rebuilds
every permitted delta from raw45 and independently encodes the committed
`uint32[11]` limits tuple. It permits only the fresh domain, raw count,
aggregate byte limit, coordinator fixed arrays/checks, driver count guards, and
diagnostic bound.

The generated raw46 q1/q7/direct/reopen chains, raw47 and byte311899 exact
refusals, and retained controls are recorded in `results/gate-summary.json`.
The gate uses only trusted generated Java-8 sources and completed under the
fixed 1200-second cap.

No original artifact/JAR/class/resource, provider construction, factory
execution, world, or Done input is read or claimed. Parent alone owns the
genuine append and class/factory execution or accelerated replay.

## Reproduction

From repository root (fresh ignored paths):

```sh
python3 evidence/java-evm/minecraft-entry/classcount46-byte311898-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/classcount46-byte311898-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/classcount46-byte311898-preflight/tools/build.py build/java-diff-mc-classcount46-byte311898-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount46-byte311898-preflight/tools/generate_fixtures.py build/java-diff-mc-classcount46-byte311898-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount46-byte311898-preflight/tools/gate.py build/java-diff-mc-classcount46-byte311898-build-repro-LOCAL build/java-diff-mc-classcount46-byte311898-fixtures-repro-LOCAL build/java-diff-mc-classcount46-byte311898-gate-repro-LOCAL
```
