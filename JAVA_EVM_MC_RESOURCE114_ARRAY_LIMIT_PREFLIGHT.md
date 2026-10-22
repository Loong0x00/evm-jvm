# P40 — reboot resume, authenticated resources, actual4096-array exhaustion

## Result and limits

User explicitly authorized continuation after the saved P39 reboot stop. Parent reverified branch HEAD9456cf9ad, original JAR SHA256, the saved P39 checkpoint, all36 canonical receipts, the persistent EVM world, and unchanged protected geth paths before new work.

The guest engine/coordinator stayed **exactly P39**: runtime418986B SHA256 `694b1ea5686b03eab3c000de8b9bc6af573edb0ad06053f2279a6d4da748d1c6`,105 bootstrap images/root `ca3049ae9ad4e09e893a897c34ef016939d1595c01d090c5ee3e9699ac349fbd`, native21/String12. No JVM implementation, allocation representation, wire codec, quota, gas or underlying EVM change was made in P40. Only explicit authenticated original-resource packages changed; each new package started fresh.

Latest original114 package is114 classes /801758 bytes. It genuinely reached **2,086,784 JVM instructions /109 internal steps**, epoch32, then returned a real terminal **OutOfMemoryError (builtin Java kind7)**. All32 successful canonical receipts, including the guest terminal outcome, independently verified; persistent-world validation passed. Replay564.298s. This is **not** an EVM OOG, unsupported method, fake return or resumable RUNNING state.

Checkpoint1,216,824 bytes, SHA256 `06f76fea33340276cbb251fd30327adb502f134e2f4b1f85844f7fb5c1d5011c`; world `build/java-diff-mc-original114-objects-super-parent-p40/official`.

Measured terminal heap:

| Counter | Actual | Existing cap |
|---|---:|---:|
| Ordinary allocated arrays |**4096** |**4096** |
| Ordinary objects |3259 |4096 |
| Array elements |105535 |262144 |
| Checkpoint bytes |1216824 |2097152 |

The measured artificial shortage is specifically allocated-array **count**. The next authorized step doubles only that quota to8192; object, element, raw, runtime and checkpoint caps remain independent. Worker `sa_64d3e2aaaa264e69` in `/home/user/evm-jvm/max-arrays-8192` receives only a hashed P39 source-only snapshot, no original inputs/evidence. P41 is **not accepted yet**. Its code change requires a fresh original start: the terminal P40 checkpoint will never be continued or migrated.

All65536 sine raw bits still match the accepted read-only-oracle-verified table, SHA256 `87a67a39fff59636acb04edcda4ef622831037291f11fb61586c57596771dac2`. No world preparation, accepted EULA/configuration startup, listening or Done claim.

## Resource-only progression

Every new class below was decoded and size/root measured by genuine EVM AS0/ZI0/DI0 on the unchanged JAR, never a host ZIP/class parser/inflater or host original Java. Original source/JAR was not rewritten; bootstrap substitutions were not used for Guava classes.

| Package | Classes / raw bytes | Outcome |
|---|---:|---|
| P39 saved baseline |90 /658601 |precise bdc missing,1974606J/98I |
| bdc |91 /659577 |precise bcy missing,1974890J/100I,36 verified receipts |
| bcz selected initializer dependencies |95 /661345 |discovery plus same-package precise continuation: aty missing,1975794J/105I,38 verified receipts |
| aow constructor types |98 /671261 |discovery only: qf missing; not final acceptance |
| state-container selected dependencies |109 /787319 |discovery only: Guava Objects missing; not final acceptance |
| explicit hierarchy dependencies |113 /801301 |exact q1 HierarchyError(1,109),1976077J/107I,37 verified receipts; EVM header proves missing Objects superclass |
| Objects superclass |114 /801758 |real guest terminal OOM at4096 allocated arrays;32 verified receipts |

Added measured sizes: bdc976; bcy492/bcw469/bdb436/bcz$1=371; aty2470/awt663/awu6783; qf35495/awq137/aws906/awu$a9861/axj552/ImmutableList18853/ImmutableMap19116/ImmutableSortedMap25637/ew2845/fg1609/awu$1=1047; Guava Objects935/awp2837/ImmutableCollection5216/ImmutableSortedMapFauxverideShim4994; ExtraObjectsMethodsForWeb457.

Batching was driven by EVM-authenticated metadata from already triggered original constructors/initializers and required super/interfaces. This metadata only selects explicit resources; it is not guest execution authority or an oracle-provided Java result. All guest code still runs normally. The broad aow method113 is **w() registration**, not clinit; its1948 references were inspected in bounded windows but not all preloaded. Only targeted constructor dependencies were added.

## Read-only metadata and discovery safety

The existing authenticated BindingMethodInspector's128-reference ceiling was not raised. A whole598-byte bcz initializer correctly hit that ceiling; its refusal is preserved. New calls use96-PC windows, probing EVM-validated instruction boundaries, so every emitted window stays bounded. A separate diagnostic-only `header` API reuses the same authenticated DI0 reader and checked constant-pool/member parser to return actual class/super/interfaces/method signatures. It uses a bounded128-method output ceiling, checks trailing bytes and canonical ABI. All diagnostic deployments/queries run on copied successful worlds, with codehash/package/resource anchors checked, no Java execution, no committed deployment/checkpoint, and unchanged original world/Head. Source and exact query drivers are archived.

Discovery remains opt-in. The replay wrapper reuses the already-tested strict canonical `MCEntryMissingClass` classifier: exact selector/ABI/name/gas, byte-exact prior successful Head, root rollback and zero candidate checkpoint. Non-missing failures retain ordinary halving to q1; actual Java terminal outcomes are never resumed. Missing-class discovery reports explicitly deny final/q1 acceptance. Precise continuation resumes only a successful checkpoint of the **same package/code**, never failed output. Original95's455.313s discovery plus324.992s precise continuation produced its genuine q1 frontier. This is not a complete-startup speedup claim.

A diagnostic check using an archived post-verifier Head correctly failed the byte-exact Head guard (the verifier updates transport telemetry). The guard was not relaxed; live discovery validates against the actual pre-call Head and archives those exact bytes. A concurrent diagnostic read also found a refusal file while the precise driver archived/replaced it; no failed state was used. These are observer/tooling issues, not guest corrections.

## Evidence and reproduction

Entry point: `evidence/java-evm/minecraft-entry/parent-original114-objects-super/artifacts/array-count-4096-terminal.json`.

Other scoped evidence directories: `parent-original91-bdc`, `parent-original95-bcz-batch`, `parent-original98-aow-ctor-batch`, `parent-original109-state-container-batch`, `parent-original113-immutable-hierarchy`. They preserve explicit binding JSON, EVM size/root measurements, selected-method/header outputs, query drivers, discovery/precise records and receipt hashes. Existing profiles/worlds/failures were preserved, not cleaned or overwritten.

The oversized interpreter is still LOCAL StateDB.SetCode preinstalled code called through ordinary geth EVM execution. EIP170/EIP3860, opcode pricing and consensus remain unchanged. Fixed block/time1 and checkpoint counts are not mined blocks. Original replay's authorized uint64.max /60s watchdog is distinct from finite generated test allowances.
