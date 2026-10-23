# P49 — independently verified LinkedHashMap construction subset

## Capability and refusal boundary

One actual Java8 generic LinkedHashMap<K,V> image extends the accepted HashMap. Its ordinary zero-argument constructor calls HashMap(), then sets private-final accessOrder=false. The inherited real fields retain lazy null table/entrySet, zero size/modCount/threshold and loadFactor0.75.

This is NOT ordered storage or LinkedHashMap mutation support. The explicit native put(K,V) override remains unbound, so LinkedHashMap-, HashMap- and Map-typed virtual/interface dispatch cannot silently execute unordered HashMap.put. Other get/default/equality/hash/clone/mutation surfaces remain explicit refusals. Genuine empty-state size/isEmpty/cache/view/iterator/NSEE/typed copy stay truthful because no admitted logical mutation can populate the map. Omitted ordered head/tail nodes and full JDK field layout are not claimed.

## Independent build and rejected metadata

Worker `53498db1b59fb7947b79f888178d672b33199869` provided generated coordinator/package EVM evidence. Parent independently rebuilt Java8 -g:none, Solidity, coordinator and Go/vet, and reviewed the full inherited surface. The431B image is SHA256 `746398af42137bb424040c85113cdd5f1296d29e983e0e819f320f2c108ddc3f`. All113 P48 image bytes/order remain exact; leaf113 appends,114 total. No other guest image or execute/dispatch/native/heap/codec/ABI/storage behavior changed.

The worker's root omitted the actual `JVMEVM:` DBOOT prefix, and its engine/coordinator byte counts used init lengths instead of runtime lengths. Parent rejected/preserved those claims and an initial size assertion, then verified actual source-domain ABI commitments. This is metadata correction only: runtime bytes/SHA/Keccak already matched the fresh parent build; no guest/compiler/gas rule changed.

**Actual root:** `302c3174aec4caf25a3bcd8d3fc6990cd9fd18d4e79e5701c92680e4151f00c9`.

- Engine runtime429953B (init429981B), SHA256 `732cb0e440706a312cd438a613fc874b132a3d43ccb3122c7e100b36c42d10b4`, Keccak `3a550030c24f223b479c293b941c5661c14b93d4ba56843e0c1e066843661226`.
- Coordinator runtime5411B (init10379B), SHA256 `fc0245c0765e00903e0720d291d6ccef3fc5bb4968cc3cb6b093559feb97a9a4`, authenticating that engine.
- Actual domains `MC-LINKED-HASH-MAP-CONSTRUCTOR-P49`; actual DBOOT literal `JVMEVM:MC-LINKED-HASH-MAP-CONSTRUCTOR-P49:BOOTSTRAP:1`.
- Native21/String12 and all bounds unchanged: arrays8192, objects4096, elements262144, handles12545, raw150/1063930B, CP2MiB, artifact1MiB, frames128, q65536/internal4096, reserve25M. Coordinator uint8 is still RAW count<=150, not internal264.

A stricter fresh receipt verifier also caught missing address/CP-cap fields in the parent's reduced metadata schema. The unchanged canonical address and2097152 cap were restored from the authenticated P48 baseline, without weakening verifier predicates; failure retained. Current candidate verification now derives both actual source DBOOT strings and verifies the full ordered root.

## Fresh parent EVM gates

Generated-only stock Java8 is a test oracle, never an execution input. Parent independently checks hierarchy, real empty state, private accessOrder, cache identity, iterator exhaustion, typed zero/oversized array copies, CCE/NPE and eager typed array cloning.

- Small raw1 q7/q1:410 JVM instructions,19.238s combined, canonical1B; peak48566726gas. Exact machine/VFS/counters/heap and separate-process EVM checkpoint/code/Head reopen.
- Raw150 +114 =264 internal classes, q4096/q65536:410 JVM instructions,1.237s combined at the SAME1B, peak413979584gas. Actual LinkedHashMap class263 arrays encode0x207, nonempty real reference cells and distinct cloned handles survive full wire audit/reopen. No test-budget escalation.
- Heap audits directly verify7 real fields: null table, real cached view where requested, zero size/modCount/threshold, float raw3f400000 and false accessOrder. No reflection/accessor was added.
- Eleven fresh1B atomic controls prove three typed put routes, get, equals/hash/clone/default, view.clear, missing int constructor and reserved raw replacement remain raw refusals. No fabricated null/false/default result or Java exception substitute.

Generated public watchdog30s is distinct from outer1200s. Original uint64.max/60s authorization remains separately labeled. Heavy compilers/EVM runs were serial for host stability only.

## Fresh unchanged original125

A new125-resource/889395B world through actual authenticated AS0/ZI0/DI0 and the coordinator genuinely returned LinkedHashMap8259/class238 with all7 expected fields. Original ordered insertion/access behavior is NOT claimed.

**2224106 JVM instructions /128 internal steps**,45 canonical verified receipts, epoch45/lifecycle1. Checkpoint1285628B SHA256 `ec8e521c584fa64c39ff6880219c72225fcd43a6ba8a34a45cbf11a7f5b850c4`. Discovery1363.897s (new non-missing failure localized through q1), then explicit same-package precision/reopen16.396s. World `build/java-diff-mc-linked-map-original125-parent-p49/official`.

Next exact q1 CallError(3,4) is authenticated original Guava Lists binding74/method1 newArrayList(): NEW ArrayList atPC0, missing <init>()V atPC4. Existing ArrayList only admits its int constructor; no default constructor is yet accepted.

All65536 sine raw bits retain SHA256 `87a67a39fff59636acb04edcda4ef622831037291f11fb61586c57596771dac2`. No original host Java/ZIP/class parser, rewrite, injection, oracle input, terminal resumption or cross-code/package checkpoint migration. Protected core/vm/core/state/params equal95665d570. Oversized LOCAL SetCode preinstall through ordinary EVM Call, NOT standard CREATE deployability. Gas/state/consensus/EIP170/EIP3860 unchanged; block/time1, checkpoints are not mined blocks. No world/EULA/listening/Done.

Evidence: `parent-linked-hash-map/artifacts/array-list-default-constructor-blocker.json`, all114 root audit, real private-field/array proofs, generated/refusal/reopen records, EVM selected-method metadata and45 ordered original receipt hashes. Worker worlds/logs and rejected metadata remain preserved.
