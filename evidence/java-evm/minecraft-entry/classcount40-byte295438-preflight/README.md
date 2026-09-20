# Generated raw40 / byte295438 source stage

This generated-only capacity stage derives exactly from the raw39/byte294891
stage recorded at `23ed15203`. It changes only selected raw-class count
`39→40`, aggregate raw bytes `294891→295438`, and the read-only checkpoint
diagnostic class bound `130→131`.

All 91 ordered bootstrap images and their bytes/positions—including dynamic
image5 `Throwable`—remain unchanged. Native13, String-local binding10,
exception kinds14, frames128, selected-resource count1/4096, checkpoint1MiB,
Head32768, compiler/toolchain, and every other fixed limit are source-pinned.
The bootstrap root remains runtime-derived as `keccak256(abi.encode(DBOOT,h))`;
this stage's fresh-domain 91-image root is
`5e564b084add9fce889d92e5c081b8dfcc0b39cb34f6445f99465cc83670f6e0`,
never a hard-coded interpreter root.

The rebuilt runtime remains exactly `389150 / 393216` bytes (4066-byte
headroom); the coordinator remains 5394 bytes. The source verifier directly
byte-pins the raw39 stage and permits only the fresh domain, raw count,
aggregate byte limit, coordinator fixed arrays/checks, driver count guards,
and diagnostic bound.

The generated raw40 q1/q7/direct/reopen chains, raw41 and byte295439 exact
refusals, and retained controls are recorded in `results/gate-summary.json`.
The gate uses only trusted generated Java-8 sources and completes under the
fixed 1200-second cap.

No original artifact/JAR/class/resource, `ReusableMessage`, provider
construction, factory, world, or Done input is read or claimed. Parent alone
handles the genuine interface append and accelerated replay.

## Reproduction

From repository root (fresh ignored paths):

```sh
python3 evidence/java-evm/minecraft-entry/classcount40-byte295438-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/classcount40-byte295438-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/classcount40-byte295438-preflight/tools/build.py build/java-diff-mc-classcount40-byte295438-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount40-byte295438-preflight/tools/generate_fixtures.py build/java-diff-mc-classcount40-byte295438-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount40-byte295438-preflight/tools/gate.py build/java-diff-mc-classcount40-byte295438-build-repro-LOCAL build/java-diff-mc-classcount40-byte295438-fixtures-repro-LOCAL build/java-diff-mc-classcount40-byte295438-gate-repro-LOCAL
```
