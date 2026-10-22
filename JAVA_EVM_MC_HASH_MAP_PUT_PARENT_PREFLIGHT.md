# P39 — HashMap.put parent acceptance and requested reboot stop

## Accepted result

The unchanged Minecraft1.12.2 input (same90 authenticated raw classes /658,601 bytes) genuinely completed the previously blocked HashMap insertion loop. Original HashMap5980 now has **22 real Nodes**, an eager Node[32] table, size22, modCount22, threshold24 and float loadFactor0.75. All22 original enum references are present as values, all key hashes/buckets are consistent, the original enum initializer completed, and no HashMap/enum-initializer frame remains. This is a real guest return, not a fabricated success or host-produced map.

Fresh original replay reached **1,974,606 JVM instructions /98 internal steps**,36 independently verified successful canonical checkpoint receipts, in728.490s. It advanced50,847 JVM instructions beyond P38. The next q1 call atomically reports **MCEntryMissingClass: `bdc`**, site4103/context10. Per the user's stop instruction, `bdc` was **not measured, added or implemented**; no P40 was started.

Latest successful world: `build/java-diff-mc-hash-map-put-original90-parent-p39/official`, epoch36/lifecycle1.
Checkpoint1,133,360 bytes, SHA256 `865ec98871892c0d359acada9719a261e7b23cd7f3c3d1d96c0dc093b1dc78dc`.

Still before main argument processing, world preparation, accepted EULA/configuration startup, listening, or `Done`.

## Implementation and independent proof

The bounded library implementation uses ordinary guest Java for put, null keys/values, real guest key-side hashCode/equals, Java8 spread, collisions, replacement return values, size/modCount, real Nodes and resize splitting. Only the default constructor and this admitted subset are claimed. Unsupported treeification uses a deliberately unbound native refusal guard; other unimplemented APIs such as get still explicitly refuse. No new operational native was added.

Parent independently compiled and reconstructed all ordered images:

- Runtime418,986 bytes, SHA256 `694b1ea5686b03eab3c000de8b9bc6af573edb0ad06053f2279a6d4da748d1c6`.
- Bootstrap105, root `ca3049ae9ad4e09e893a897c34ef016939d1595c01d090c5ee3e9699ac349fbd`.
- Only prior HashMap leaf100 changes; append real HashMap$Node leaf104. All other103 prior leaves, including String/Pattern/Matcher/Math, are byte-identical.
- Engine delta is restricted to prepare/count, reserved map namespace, append/root/materializers; interpreter execute, virtual resolution and native dispatch are unchanged. ABI and recursive storage slots/offsets/type shape are unchanged. Source-only AST identifiers are not protocol fields.
- Global natives21/String12; runtime-artifact1MiB, checkpoint2MiB, raw150/1,063,930, objects4096/arrays4096/elements262144 remain fixed. Diagnostic255 is derived105+150, not a new quota.
- Protected geth `core/vm`, `core/state`, `params` match base95665d570; EVM behavior, gas, state and consensus were not changed.

The oversized interpreter remains **LOCAL StateDB.SetCode preinstalled code invoked through ordinary EVM Call**, not a standard CREATE/EIP170 deployment. EIP170/EIP3860 remain intact; block/time are fixed1 and checkpoint counts are not mined blocks.

## Review corrections and preserved failures

Before acceptance parent rejected and preserved three draft errors: a catchable invented Error for unsupported treeification, an unmeasured4096 resize cap/OOM, and `newThr=oldCap<<1` (incorrect12->32). Final source uses an explicit profile refusal, existing global allocation quotas, and `oldThr<<1` (12->24), plus Java8 maximum-capacity threshold saturation/order. No old-draft test is presented as final-source evidence.

Independent read-only review passed for final Java source SHA256 `3b195082b4c7ca83610274b18b9b13149b7749e6c6cba690549fb583041a9ae0`. It covered admitted put/resize and Node Map.Entry behavior, not complete Map or runtime acceptance. The parent performed the final source correction and all fresh runtime checks. Both prior semantic worker jobs were stopped, not allowed to continue editing; all their drafts/worlds/failures remain preserved.

Two parent harness/input issues were also preserved: a generated hash distribution accidentally required host tree bins (final witness avoids unsupported treeification), and a coordinator diagnostic used old P38 package/class domains, correctly receiving MR0Error(16). The latter was a namespace/harness failure, **not gas shortage**; a fresh P39-domain coordinator run passed without raising its1B allowance.

## Fresh parent verification

| Test | Explicit budget | Measured result |
|---|---:|---|
| Parent small q7/q1, including interface put/null/old return/collisions/real replacement and array clone |1B/call |2,212 JVM steps;316/2,212 calls;105.692s;peak44,709,726gas |
| Parent signed/high-bit hash, replacement, resize q4096/q65536 |**separate2B/call** after measured1B refusal |10,312 JVM steps;3/1 calls;1.565s;peak1,470,770,178gas |
| New-process reopen of both schedule pairs |same labeled budgets |EVM checkpoint/code/Head validation passed |
| Treeification and unsupported get after successful q7 slices; raw Node and raw HashMap rejection |1B/call |26.947s; all four typed refusals preserve Head/root |
| AS0/ZI0/DI0 + real coordinator, exact150 classes /1,063,930 bytes, retained clone workload |1B/call |3,224 calls,17.435s,peak245,300,932gas,checkpoint4,685 bytes,class count255 |

Generated Java8 oracle checks are test-only, never execution input. Small-map heap is size/modCount3,threshold12,Node[16]/3 reachable Nodes. Resize-map heap is size/modCount32,threshold48,Node[64]/32 Nodes. Both quantum pairs have identical final machine/VFS roots, counters and audited heap. Refused treeification's last successful state is size/modCount10,threshold48,Node[64]/10 Nodes; unsupported get preserves a real one-entry map and does not fake null.

The large resize1B failure and fresh2B success are separately archived and **not labeled ordinary1B success**. The original run separately uses authorized uint64.max external gas /60s public Cancel watchdog, q≤65536/internal4096. No failed state or cross-profile/package checkpoint was continued.

All65,536 guest sine raw bits still equal the accepted read-only-oracle-verified table, SHA256 `87a67a39fff59636acb04edcda4ef622831037291f11fb61586c57596771dac2`.

## Evidence / reboot handoff

- `evidence/java-evm/minecraft-entry/parent-hash-map-put/artifacts/bdc-resource-blocker.json`
- `original-map-put-return-proof.json`, `generated-map-heap-proof.json`
- `root-audit.json`, `independent-readonly-source-review.json`, `failure-history.json`
- canonical receipt verification/hashes, original Head/q1 refusal, generated/reopen/control/coordinator records
- Source and rejected drafts: `hash-map-put-bounded/`; source-only P38 baseline: `hash-map-put-source-base-p38/`

Reproducible tooling: candidate `tools/stage_and_build.py`; parent `rebuild.py`, `generate_fixtures.py`, `generated_gate.py`, `controls.py`, `authorize_original.py`, `precise_replay.py`, `verify_original.js`, `audit_and_collect.py`. Use fresh uniquely named output directories; existing evidence/worlds are intentionally not overwritten.

**Stop here.** Resume only on a new user instruction, following [JAVA_EVM_MC_REBOOT_HANDOFF.md](JAVA_EVM_MC_REBOOT_HANDOFF.md). Do not add `bdc` or start another worker during this requested stop.
