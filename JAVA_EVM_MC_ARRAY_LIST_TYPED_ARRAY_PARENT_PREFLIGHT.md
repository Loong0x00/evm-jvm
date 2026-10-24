# P54 — independently verified bounded ArrayList typed-target copy

## Accepted surface

The raw bounded ArrayList now overrides the erased `toArray(Object[]):Object[]` descriptor with ordinary Java8 Code. It reads PRIVATE size and actual elementData, returns the identical supplied array with its runtime component type intact, copies the real prefix in order, nulls exactly the first unused slot when oversized and preserves the rest of the tail. Null targets raise genuine NPE even when empty. A target shorter than private size raw-refuses through a private unbound guard before writes; growth/reflection/component-type expansion is not implemented.

Because every admitted list mutator is still unbound, legal current lists have private size0. The copy loop and short-target branch are genuine field-based code, but **nonempty copying and undersized-target refusal were not executed**. No setter, host seed or oracle result was introduced to claim otherwise. Public size overrides are deliberately ignored, matching the admitted private-storage behavior. No-arg toArray/add/get/equality/hash/clone and iterator.remove remain raw refusals.

## Independent build and preservation

Worker `b0bed60bef307314ff144dc959804d8262d95b5a` supplied generated source/build/gates. Parent verified all16 base hashes, reproduced the exact old ArrayList class, compiled the new1178B image independently, and confirmed ArrayList$Itr115 is byte-exact. Only leaf98 changes; all other116 images/order remain exact. Class count stays117 and the actual five tail slots105..109 retain count-12..-8. No parent guest-semantic correction was needed.

- ArrayList image SHA256 `566127a7444cdcc05de5ce43724e412c80108c775f1950b9a559a620e08f9fd2`.
- Root `960dacb69402d356d78b20fb269611474742c17f3c4efbf6644a004a2ed8fd8c`.
- Engine435694B SHA256 `43ef610db287b0ca64f3cd5cc6c63661dc531a1f303cc687ae647ffdcf79ae5c`, Keccak `483082f0abdbfd1ec3b1b70a1d60c226e1e17bf4f81fbb870aa68a7e32b1fa06`.
- Coordinator5411B SHA256 `05a55d22f13a1beb083c94970741f043e7a21ed124c2ef67749598a6057866f4`, authenticating that engine.
- All9 engine/4 coordinator domains use `MC-ARRAYLIST-TYPED-TOARRAY-BOUNDED-1`.
- Existing native1..22 and String-local12, constructors/shared sentinel/clinit/private iterator, executor/dispatch/heap/codec/ABI/storage remain unchanged. No new native or quota.

Arrays8192, objects4096, elements262144, length65536, handles12545, raw150/1063930B, CP2MiB, artifact1MiB, frames128, q65536/internal4096, reserve25M remain fixed.

## Independent fresh geth EVM tests

Generated-only stock Java8 is test oracle/build context, never execution input. Parent executes interface List/Collection calls on default/int0/int3 and a subclass returning public size3 while private size0. Supplied zero/oversized Object[], reflected Iterable[], Map.Entry[] and String[] retain identity and type; null terminator/rest-tail sentinels, NPEs and old iterator NSEE pass. Full decoded arrays prove four Object targets retain their two tail sentinels and four String targets retain their second value.

- Raw2 q7/q1:1546 JVM instructions,127.098s combined at canonical1B; peak116352487gas. Exact machine/VFS/heap/counters and separate-process checkpoint/code/Head validation/reopen.
- Raw150 +117 =267 classes, q4096/q65536: separate2B after a preserved actual1B shortage,1546 JVM instructions,2.334s, peak1405435136gas. Actual native22-created ListIterator component264 array0x208, retained private Itr state and old bootstrap identities survive wire audit/reopen. Coordinator uint8 remains raw<=150, not internal267; no widening.
- A fresh P54 run reexecutes the independent P53 reference-array/Poison-no-init/NPE-NASE/ASE/clone/Class.getName/asSubclass/System.arraycopy/tail probes at q4096/q65536 and1B,619 JVM instructions, peak564767585gas, including new-process reopen. The unchanged allocator/old executor are not silently replaced.
- Eight fresh1B atomic controls retain noarg/add/get/equals/hash/clone/iterator.remove/raw ArrayList refusals. No fake empty iterator, AME or Java-error substitution.

The worker's historical q1 finish watchdog retry is preserved as its own runner evidence. Parent's fresh generated gates use the unchanged30s per-call watchdog and1200s outer process allowance, not a60s generated per-call claim. Original uint64.max/60s remains separately authorized. Heavy compiler/EVM phases stayed serial for host stability only.

## Fresh unchanged original131

A new131-resource/917284B world through real authenticated AS0/ZI0/DI0 and the coordinator passed List.toArray on real ArrayList8274/private size0 with the exact caller-provided Iterable[]8276/length0/metadata0x1da. The same array subsequently became the real field of initialized original ew$b8270 (other field is Class mirror8269). Thus original Cartesian iterable construction genuinely completed; Cartesian product iteration/results are NOT claimed.

**2224372 JVM instructions /133 internal steps**,42 canonical successful receipts, epoch42/lifecycle1. Checkpoint1287449B SHA256 `81638af9ae7ba84113e6e2a39d4b86e44dd18d51cdb41ab4ed5547c4462ad281`. Discovery679.484s plus same-code/package precision571.185s. World `build/java-diff-mc-arraylist-to-array-original131-parent-p54/official`.

Next exact q1 missing original resource **ew$a**, site4104/context1. All65536 sine bits retain SHA256 `87a67a39fff59636acb04edcda4ef622831037291f11fb61586c57596771dac2`.

No original host Java/ZIP/class parsing, rewriting, injection, oracle input, failed-state/terminal resumption or cross-code/package checkpoint migration. Protected core/vm/core/state/params equal95665d570. Oversized LOCAL SetCode preinstall through ordinary EVM Call, NOT standard CREATE deployability. Gas/state/consensus/EIP170/EIP3860 unchanged; block/time1, checkpoints are not mined blocks. No world/EULA/listening/Done.

Evidence: `parent-array-list-to-array/artifacts/ew-a-resource-blocker.json`, all117 root audit, target/private-state/wire proofs, parent retained/native/refusal/reopen records, initialized original ew$b and42 ordered original receipt hashes. Worker failed attempts and original worlds remain preserved.
