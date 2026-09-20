# Generated raw39 / byte294891 source stage

This generated-only capacity stage derives exactly from accepted dynamic
Throwable message-sink evidence `parent-cbf4b0780` at commit `c7a69daef`.
It changes only selected raw-class count `38→39`, aggregate raw bytes
`285489→294891`, and the read-only checkpoint diagnostic class bound
`129→130`.

All 91 ordered bootstrap images and their bytes/positions—including dynamic
image5 `Throwable`—remain unchanged. Native13, String-local binding10,
exception kinds14, frames128, selected-resource count1/4096, checkpoint1MiB,
Head32768, compiler/toolchain, and every other fixed limit are source-pinned.
The bootstrap root remains runtime-derived as `keccak256(abi.encode(DBOOT,h))`;
this stage's fresh-domain 91-image root is
`531df01c78166a5af2956bd3f560c11547cbd2b36bc906368bdb5829660a81ec`, never a
hard-coded interpreter root.

The rebuilt runtime remains exactly `389150 / 393216` bytes (4066-byte
headroom); the coordinator remains 5394 bytes. `parent-input.json` is not
carried forward: the stage source verifier directly byte-pins the accepted
Throwable source and permits only the new domain, raw count, aggregate byte
limit, coordinator fixed arrays/checks, driver count guards, and diagnostic
bound.

The generated raw39 q1/q7/direct/reopen chains, raw40 and byte294892 exact
refusals, and retained dynamic-Throwable controls are recorded in
`results/gate-summary.json`. The gate uses only trusted generated Java-8
sources and completes under the fixed 1200-second cap.

No original artifact/JAR/class/resource, ReusableParameterizedMessage,
provider construction, factory, world, or Done input is read or claimed.
Parent alone appends the genuine class and performs accelerated replay.

## Reproduction

From repository root (fresh ignored paths):

```sh
python3 evidence/java-evm/minecraft-entry/classcount39-byte294891-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/classcount39-byte294891-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/classcount39-byte294891-preflight/tools/build.py build/java-diff-mc-classcount39-byte294891-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount39-byte294891-preflight/tools/generate_fixtures.py build/java-diff-mc-classcount39-byte294891-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount39-byte294891-preflight/tools/gate.py build/java-diff-mc-classcount39-byte294891-build-repro-LOCAL build/java-diff-mc-classcount39-byte294891-fixtures-repro-LOCAL build/java-diff-mc-classcount39-byte294891-gate-repro-LOCAL
```
