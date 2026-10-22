# Bounded ordinary-guest `HashMap.put` on P38

## Baseline and scope

This task uses only the source-only P38 package in `../hash-map-put-source-base-p38/`; its nine pinned files were independently SHA-256/length checked before any edits. P38 runtime pin is 414732 bytes / `f0959a98ba75f8f6bd013fc87a4a7ff633065d8d283f3857efde863b2fd313ef`, 104 eager images / root `3896630440a69732a4acda4b8f5c5eec4898768ad074623b522a46a936efae4b`, 21 global natives and String-local binding 12. Existing budgets remain runtime 1 MiB, CP 2 MiB, raw classes 150 / bytes 1063930, arrays 4096, objects 4096, elements 262144, checkpoint 2 MiB, and established LOCAL gas 1B with 25M reserve. No underlying VM/StateDB/consensus or legacy profile changes.

Goal: append real Java 8 `HashMap$Node` and replace HashMap's put refusal with ordinary guest Java code. Null keys/values, key-side `hashCode`/`equals`, Java 8 spread, default initial table 16 / .75 threshold, resize, existing-key value replacement and return semantics are in scope. Tree bins and unrelated Map APIs remain explicit refusal boundaries, not fabricated success. No operational native or host-side map behavior is allowed.

## Work sequence

1. Create an isolated task tree, preserve P38 engine/coordinator/build/reference inputs byte-for-byte, and independently derive the actual ordered 104-image root (not regex occurrence counts).
2. Add the minimal faithful Java 8 Node image and put implementation; preserve all prior images and verify raw-class replacement remains reserved. Compile guest bootstrap sources with the pinned Java 8 compiler.
3. Record source/build deltas and candidate runtime/root/ABI/storage/native counts. Keep all budgets fixed; only the derived diagnostic class-count bound may become 255 (=105+150).
4. Build generated-only fixtures and compare Java 8 oracle outcomes. Focus on insertion/null/replacement/key equality/hash spread/collision/resize and actual heap. Exercise q1/q7 and larger q4096/q65536 witnesses without repeating the hour-long P38 matrix. Preserve every failed attempt.
5. Where feasible, verify checkpoint reopen using only generated data and the real coordinator/accepted transport. Commit only scoped files after verification; no push. Parent performs independent build/replay and alone handles original-workload replay.

## Explicit limits and refusal policy

Only ordinary HashMap operations supported by the implemented paths may complete. A would-be treeification or any valid operation that the implementation cannot execute must fail as a typed guest exception or interpreter refusal before falsely reporting a successful map state. No fake null/get result is introduced. Keep codec/eager heap semantics, all old native behavior, all accepted P38 image bytes, engine/coordinator ABI and storage layout, and runtime limits unchanged. No original Minecraft inputs, receipts, worlds, checkpoints, or parent evidence are used here.

## Initial measured boundary

At plan creation no put implementation or added image has been built or measured. The only verified baseline measurement is the pinned P38 runtime/root above. Gas/time/RSS ceilings for new generated-only runs start at 1B gas / 1200s / 4 GiB, and will be reported as actual measurements; a shortage is not relabeled ordinary-budget success.


## Parent review / final source revision (before runtime acceptance)

User stop boundary: finish P39 ONLY, then save and stop for reboot; no next blocker. Both semantic worker jobs were stopped with their files/worlds/results preserved. Parent became the sole semantic writer.

Rejected draft choices are preserved under `draft-archive/`: catchable `Error` for unsupported treeification, an invented4096 resize OOM cap, and subsequent `newThr = oldCap << 1` (wrong12->32). Final source uses a deliberately unbound treeification refusal guard, no new capacity quota, `oldThr << 1` (12->24), Java8 maximum-capacity saturation, and Java8 threshold/table assignment order. Existing global allocation quotas apply.

Independent READ-ONLY source review passed for Java source SHA256 `3b195082b4c7ca83610274b18b9b13149b7749e6c6cba690549fb583041a9ae0` (job sa_a2bea9ac1a44468e), without code modifications or original inputs. Runtime acceptance remains separate.

Reproducible source/platform build: `tools/stage_and_build.py FRESH_REPO_BUILD_PATH` verifies baseline, compiles only guest HashMap/Node against a stripped Java8 PLATFORM boot jar, updates actual image/root/code authentication, and compiles engine/coordinator. No original workload inputs. Final staged runtime418986B SHA694b1ea5686b03eab3c000de8b9bc6af573edb0ad06053f2279a6d4da748d1c6;105 images/rootca3049ae9ad4e09e893a897c34ef016939d1595c01d090c5ee3e9699ac349fbd; only prior leaf100 changes, Node104 appended,103 other prior leaves unchanged. Native21/String12, eager heap, quotas and underlying EVM remain fixed.

All earlier tests under old draft engines are development history, not final-source evidence. Parent will independently rebuild and run fresh generated q1/q7/resize/heap/reopen/refusal checks and alone replay the unchanged original. Do not represent old worlds as final-source runs.
