# P41 — independent8192-array capacity acceptance

## Accepted result

Only `MAX_ARRAYS` changed4096->8192; the derived handle registry becomes12545. Ordinary object4096, elements262144, raw150/1063930, checkpoint2MiB, runtime-artifact1MiB, frames128, quantum65536/internal4096, codec/schema and native21/String12 remain unchanged. Arrays remain real, distinct, eagerly allocated dense guest heap objects.

Parent fresh compilation reproduced runtime418986B, SHA256 `32a16b78a9cec4b72835eaab094c715e3a5f310ed9f2b211d49e29237c5b5f02`; coordinator5411B SHA256 `a89f68c52a8fa4b49f103add3ece3f48619432628641a49a13babea10835d695`. Parent reconstructed **all105 actual ordered bootstrap leaves** and proved bytes/order/root unchanged: `ca3049ae9ad4e09e893a897c34ef016939d1595c01d090c5ee3e9699ac349fbd`. DBOOT intentionally stays P39; other profile/codehash domains explicitly distinguish P41. Full source normalization permits only the array-count constant and profile labels; ABI/storage exactly match. uint16 array counters represent8192 without a wire/schema change.

Fresh original114 /801758B started from the unchanged original JAR, **not** the old terminal state. It exceeded the old quota with **4676 actual arrays**,3560 objects,106125 elements, and reached **2210370 JVM instructions /111 internal steps**,40 verified successful canonical receipts, epoch40/lifecycle1. Checkpoint1282726B, SHA256 `19d9a0b6685b5a3138522803f2fed50dc06b853c2f6d938c23db323ea4155f2c`. Initial replay1111.362s plus final explicit precise-q1 verification15.645s. The old P39 4096-array terminal remains preserved and was never resumed or migrated.

Current world: `build/java-diff-mc-array8192-original114-parent-p41/official`.

## Fresh parent tests and budget separation

Parent independently rebuilt engine/coordinator/Go transport and regenerated Java8 fixtures, rather than trusting the worker's copied build artifacts or hardcoded root report. The source-only nine-file baseline is preserved with matching hashes; parent build/root outputs remain on disk.

At **separately labeled finite32B generated-only allowance**, q4096 boundary tests passed:

| Requested | Actual arrays | Result | Checkpoint bytes |
|---:|---:|---|---:|
|4096 |4096 |genuine void |210782 |
|4097 |4097 |genuine void |210833 |
|8192 |8192 |genuine void |419678 |
|8193 |8192 |genuine terminal OOM kind7 |419793 |

The outer Object[] holds distinct real zero-length int[] references; every dense record/alias was checked and all outputs validated/reopened in separate processes. A small8-array q1/q7/q4096 test matched machine/VFS roots, heap counters, records and aliases exactly. The worker separately rebuilt exact P39 and retained its real4097-request/4096-actual OOM control. Parent's earlier original P40 terminal independently measured the same4096-count shortage.

Fresh retained parent HashMap/null/collision/old-return/interface-put, String.replaceAll and shallow array.clone smoke passed q7/q1 at1B in106.581s. Retained resize/hash/spread fixture passed q4096/q65536 at **separate2B** in1.565s after a preserved actual1B shortage; new-process reopens passed. All105 image bytes are unchanged, supplementing these retained tests without replaying the old hour-long regex matrix.

The worker preserved generated shortages at1B/2B/4B (4096-array workload) and8B/16B (8192 workload), with unchanged committed Heads. They are not five identical-input trials and not ordinary1B successes. Final boundary allowance32B changes only a disposable generated driver, never EVM opcode pricing. Parent keeps canonical product1B, test32B and original authorized uint64.max transports separate. Original public Cancel watchdog is60s. **Generated public EVM-call watchdog is30s;1200s is the outer per-phase process timeout**, despite the worker summary field being named `watchdogSecondsPerCall`. The scope correction is archived explicitly.

Underlying `core/vm`, `core/state`, `params` still match base95665d570. No consensus/gas/EIP170/EIP3860 change. Oversized engine remains LOCAL StateDB.SetCode preinstalled code executed through ordinary Call, not standard CREATE deployment. Fixed block/time1 and checkpoint counts are not mined blocks.

## Next genuine blocker

Exact atomic q1 is **CallError(4,0)** at the existing Pattern refusal guard. Original raw97 `awu.<clinit>` method9 calls `Pattern.compile(String)` at PC3. A read-only authenticated EVM literal query proves the pattern at PC0 is **`^[a-z0-9_]+$`**. No host original class/JAR parser or Java execution was used. Diagnostic deployment/query ran on a copied successful P41 world, verified canonical ABI/code/package/resource anchors, did not commit deployment/Java/checkpoint state and cannot authorize continuation.

Existing bounded regex does not implement start/end anchors or plus. The next task must provide genuine general bounded semantics and a real compiled representation, not a literal-specific validator or fake compile/match. Unsupported syntax must continue to refuse explicitly. No P42 result is accepted here.

All65536 sine raw bits still match the prior read-only-oracle-verified table, SHA256 `87a67a39fff59636acb04edcda4ef622831037291f11fb61586c57596771dac2`. Still no main argument processing, world preparation, accepted EULA/configuration startup, listening, or Done.

## Evidence

`evidence/java-evm/minecraft-entry/parent-max-arrays-8192/artifacts/`:

- `pattern-anchor-plus-blocker.json`
- `all105-root-audit.json`, fresh source/artifacts/pins
- `capacity-boundaries-test32B.json`, `small-schedule-test32B.json`
- retained1B/2B smoke and new-process reopens
- `budget-and-watchdog-scope.json`
- original40 canonical receipts/hashes, Head, q1 refusal and `original-over4096-array-proof.json`
- `evm-next-pattern-literal.json`

Worker candidate/source-only evidence: `max-arrays-8192/`, commit9cfc717e442b1ec29f9943d1b44505d7b5cb6fa9. Parent `rebuild.py` performs an independent fresh build/root audit without deleting intermediate failures. `authorize_original.py`, `replay_original114.py`, `verify_original.js`, `retained_smoke.py`, `collect.py` preserve separate proof/budget roles. Use fresh output directories; never overwrite old worlds or continue a terminal/cross-profile checkpoint.
