# P50 — independently verified ArrayList() construction

## Accepted capability

ArrayList() now executes ordinary Java8 bytecode: the real AbstractList superclass chain, then elementData assignment from a private static final zero-length Object[] sentinel. Ordinary guest <clinit> allocates that shared real array. Multiple default instances reuse it; size remains the real zero field. No eager ten-element allocation, fake API result, mutation/growth/get/iterator/clone/typed-copy/equality/hash implementation was added.

The int constructor source/body is unchanged, including negative-capacity IAE and eager real arrays for zero/positive capacities. In this already-bounded int profile, int(0)'s array remains distinct from the new shared default sentinel. Full JDK private field/layout equivalence is not claimed.

## Independent source/build audit

Worker `1abaf645b5300830472e79c9564fb23bbd099bda` supplied source/build/generated EVM evidence. Parent verified all12 source-base hashes, reproduced the exact old ArrayList image from its Java8 source, independently compiled the candidate and rebuilt solc/coordinator/Go/vet. Only bootstrap leaf98 changes; all other113 image bytes/order stay exact. Still114 images, no append or count-width change. No parent guest-semantic correction was necessary.

The696B Java8 image is SHA256 `005397601fc3af39adb5a5d6cde2727abfeae2aee583790aae789048463e0114`. Compiler-only minimal interface/superclass symbols are build context, never runtime replacements or raw inputs.

**Actual source-domain root:** `eb09687d795ed3a252ed6662d594fc8ad81f36f71589a43a809f1e6ca8463e5a`.

- Engine runtime429653B, SHA256 `d50f942e99e2862c1b0214fbb2362bacd5946291e4a3be95c86886e0b19c1bf5`, Keccak `adc2e0015136b2c7a375e9ec618ff11257e2764d57fd7ab671a53cd6a534b390`.
- Coordinator runtime5411B, SHA256 `14dfe6d7b23a00ef62e1648cf19ffa134c7639ff7b67a1d4f90704c1d4f4b43b`, authenticating that engine.
- Domains `MC-ARRAYLIST-DEFAULT-CONSTRUCTOR-P50`; actual source DBOOT includes `JVMEVM:` and `:BOOTSTRAP:1`.
- Native21/String12, ABI/storage/codec/heap/dispatch/EVM gas and quotas unchanged: arrays8192, objects4096, elements262144, handles12545, raw150/1063930B, CP2MiB, artifact1MiB, frames128, q65536/internal4096, reserve25M.

## Independent fresh geth EVM gates

Generated-only stock Java8 is test oracle/build context, never execution input. Parent checks two default instances, int(0), int(3), caught int(-1) IAE, real size/isEmpty/hierarchy, eager arrays+clone, CCE/NPE, private storage and separate-process checkpoint/code/Head reopening.

- Raw1 q7/q1:269 JVM instructions,13.389s combined at canonical1B; peak60721416gas. Exact machine/VFS/heap/counters across quanta.
- Raw150 +114 =264 classes, q4096/q65536:269 JVM instructions,1.328s combined at the SAME1B; peak351135455gas. Real ArrayList[] class248 metadata0x1f8, four actual reference cells and distinct cloned handles survive wire audit/reopen. No generated budget escalation.
- Heap directly proves default objects4/5 share empty array3; int(0) object6 owns distinct empty array7; int(3) object8 owns dense zero-filled array9 of length3. Throwing negative constructor leaves its genuine partial null-backed object10; no fake successful object is inferred.
- Eight fresh1B atomic controls retain raw refusals for add, iterator, typed toArray, equals/hash, get/clone and raw ArrayList replacement. No AME or fake empty iterator/copy.

### Measured class-initialization cost

A separate identical generated int-only input, never calling the default constructor, ran fresh against accepted P49 and P50 at q1/q7 with independent process reopen. P49 executes56 JVM instructions/3 arrays; P50 executes60 instructions/4 arrays. The extra **4 guest instructions and1 real zero array** are the new ordinary <clinit> work, not skipped or hidden by host preparation. This is not an isolated gas attribution or full-startup speed claim. No quota increased.

Generated public watchdog30s remains distinct from outer1200s. Original uint64.max/60s is separately authorized. Heavy compiler/EVM stages remained serial for host stability only.

## Fresh unchanged original125

A new125-resource/889395B world through authenticated AS0/ZI0/DI0 and the actual coordinator passed the default-constructor blocker. Real ArrayList8261/8262 (class223) share empty sentinel5638, distinct from the earlier int-constructed ArrayList5639 backing. All sizes are real zero fields. Original add/growth use is NOT claimed.

**2224168 JVM instructions /129 internal steps**,39 canonical verified successful receipts, epoch39/lifecycle1. Checkpoint1286315B SHA256 `5279457e7d0949a84792611badc72845849dd6c96d462f0ca519d0cfd28a4f18`. Discovery669.728s plus same-code/package precision466.872s. World `build/java-diff-mc-arraylist-default-original125-parent-p50/official`.

Next exact q1 missing original **com/google/common/collect/Iterators**, site4107/context11. That resource is not a substituted platform implementation. All65536 sine bits retain SHA256 `87a67a39fff59636acb04edcda4ef622831037291f11fb61586c57596771dac2`.

No original host Java/ZIP/class parser, rewriting, injection, oracle input, failed-state/terminal resumption or cross-code/package checkpoint migration. Protected core/vm/core/state/params equal95665d570. Oversized LOCAL SetCode preinstall through ordinary EVM Call, NOT standard CREATE deployability. Gas/state/consensus/EIP170/EIP3860 unchanged; fixed block/time1, checkpoints are not mined blocks. No world/EULA/listening/Done.

Evidence: `parent-array-list-default/artifacts/iterators-resource-blocker.json`, all114 root audit, default/int storage/sentinel/class-init proofs, generated/refusal/reopen records and39 ordered original receipt hashes. Worker runs/failures remain preserved.
