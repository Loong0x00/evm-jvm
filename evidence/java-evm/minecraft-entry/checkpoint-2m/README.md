# P33 checkpoint-only 2 MiB profile

This append-only generated-fixture profile starts from the parent-provisioned and
hash-verified P33 snapshot in `../checkpoint-2m-base-p33/`. It changes only the
engine's checkpoint serialization/validation ceiling and the coupled
application-config limit leaf from 1,048,576 to 2,097,152 bytes. The engine
runtime artifact ceiling remains 1,048,576 bytes. The paired coordinator keeps
the P33 domain, address, layout, and semantics and is repinned only to the new
engine runtime codehash.

Pinned invariants: 100 bootstrap images, 21 global native bindings (no new
binding), 150 raw classes / 1,063,930 aggregate raw bytes, 250 diagnostic
classes, 262,144 array elements, 128 frames, and all existing gas/quantum and
other limits. `pins.json` records the baseline and new artifact hashes. The
source verifier proves the exact engine delta against the separate P33 snapshot;
the ABI and storage layout are compared during the fresh build. The legacy
transport zero value and `Legacy1MiB` stay capped at 1 MiB; only an explicit
`MinecraftCheckpoint2MiB` selection accepts up to 2 MiB.

## Generated-only reproduction

From the repository root, with the pinned local Node modules, Go toolchain, and
Java 8 JDK already installed:

```sh
python3 evidence/java-evm/minecraft-entry/checkpoint-2m/tools/run_gate.py RUN_ID
```

The runner disables module/tool network access. It builds fresh P34 engine and
coordinator artifacts, creates only trusted generated Java fixtures, invokes
the standard geth EVM API, commits/reopens ordinary state-trie/LevelDB roots,
and archives logs/manifests/checkpoints under `runs/RUN_ID/`. The old pinned P33
artifacts are used only for generated 1 MiB compatibility controls.

The positive fixture eagerly allocates two genuine zero-filled `Object[65536]`
arrays (131,072 live reference cells) and must yield an authenticated checkpoint
larger than 1 MiB and no larger than 2 MiB for q1, q7, q4096, q65536, and direct
routes. The gate checks per-slice cumulative counters, source/runtime/artifact
hashes, EVM head/envelope roots, machine/VFS state, and a fresh-process q1
reopen. It also checks the unchanged P33 engine's actual 1 MiB serialization
refusal, the new engine's four-array output-cap refusal and atomicity, and an
exact 2 MiB+1 synthetic malformed-byte refusal through the read-only validator.
The ordinary-CREATE coordinator route uses a generated exact-150-class,
1,063,930-byte package and the same eager-array positive.

No official JAR/class/resource/world/checkpoint/receipt is read or executed;
there is no original-game replay, EULA acceptance, Minecraft startup, or `Done`
claim. The 2 MiB checkpoint cap is an application-profile change, not an EVM,
consensus, runtime-artifact, or standard-CREATE deployment-limit change. The
interpreter remains oversized and LOCAL/preinstalled-code execution only.
