# P52 — independently verified ordinary ArrayList.iterator

## Accepted scope

ArrayList.iterator() constructs a fresh genuine private owner/cursor helper in ordinary Java8 bytecode. hasNext reads the owner's PRIVATE size, not capacity, public overridable size(), or a constant false. next checks that same field, raises genuine NoSuchElementException on exhaustion, and has an ordinary elementData/cursor read path. remove remains unbound, as do add/growth/get/typed-copy/equality/hash/clone and other unmeasured APIs.

All admitted lists are currently logically empty because mutation is unsupported. Neither populated-list iteration nor fail-fast/concurrency behavior is claimed. This is not a fabricated shared empty iterator: helper identity, owner references, cursor state and actual field reads are independently verified. A subclass reporting public size3 still iterates according to its true private size0, matching the admitted JDK behavior.

## Independent source/build proof

Worker `9ee94a4d7f515d52c67e4034aa7e01c093bf04f5` supplied source/build/generated EVM evidence. Parent verified all16 source-only hashes, reproduced the exact old ArrayList image, independently compiled the candidate/helpers and rebuilt solc/coordinator/Go/vet. No parent guest-semantic correction was needed.

Only old leaf98 changes; all other114 prior image bytes/order remain exact. One helper appends115:116 total. The five historical parser writes correctly shift to count-11..-7, preserving actual slots105..109 and EntrySet110. All9 engine and4 coordinator domains are fresh, and the coordinator binds the actual engine hash.

- Actual116-image root: `c1b50cfbeb974b541531c6f931ddc5ebc42b6047779525bfb99a72618848e97b`.
- Engine runtime431490B, SHA256 `4a25323e450c256efeee6a41519166a06c908beb8812dceca2c1e6c44238866a`, Keccak `5604d91a05e1ed9c4693b258654adaf3b7d33bdce765df3fb93d2aa9ccee30bc`.
- Coordinator5411B, SHA256 `6c1e9cee5a30b42d9d8bfeb89092c259ceb883134760e77f7fc53b9b62063415`, authenticating that engine.
- Actual domains `MC-ARRAYLIST-ITERATOR-BOUNDED-1`; friendly milestone P52.
- Constructor source, shared sentinel/clinit and negative/int-capacity behavior remain unchanged. No native binding, base modCount field, reflection accessor, heap/codec/ABI/storage or geth execution/gas rule was added.
- Native21/String12 and quotas fixed: arrays8192, objects4096, elements262144, handles12545, raw150/1063930B, CP2MiB, artifact1MiB, frames128, q65536/internal4096, reserve25M.

## Independent fresh geth EVM gates

Generated-only stock Java8 is a test oracle, never execution input. Parent fixtures verify defaults/int0/int3, capacity versus size, distinct iterator identities, NSEE, null receiver NPE, wrong-cast CCE and a subclass with misleading public size3.

- Raw2 q7/q1:938 JVM instructions,71.366s combined at canonical1B; peak88832065gas. Exact machine/VFS/heap/counters and separate-process checkpoint/code/Head reopen.
- Raw150 +116 =266 classes, q4096/q65536:938 JVM instructions,2.050s at the SAME1B; peak922437005gas. Actual private helper class265 is preserved in wire metadata with8 real helpers,4 genuine owners,2 distinct helpers per owner and zero cursors. Public Iterator[] and its distinct shallow clone retain those exact references; no private-class accessor was added.
- Retained tail Function/NavMap/Comparator/SortedSet/NavSet array identities and real HashMap EntrySet/typed-copy behavior independently pass. Thus image-root preservation is not mistaken for program-slot preservation.
- Eight fresh1B atomic controls retain raw refusals for iterator.remove, add/get/typed-array/equality/hash/clone and raw helper replacement. No invented Java error or fake successful collection operation.

The initial read-only heap audit used an incorrect diagnostic Iterator leaf54; the actual accepted root identifies leaf52. The audit was corrected from the source assignment, with no fixture/program/validation weakening; record retained.

Generated watchdog30s remains distinct from outer1200s; original uint64.max/60s is separately authorized. Heavy builds/EVM stages stayed serial for host stability only.

## Fresh unchanged original131

A new131-resource/917284B world through real authenticated AS0/ZI0/DI0 and the coordinator passed the iterator blocker. Actual ArrayList iterator8275/class246 has owner8262 and cursor0; its true owner is class229/private size0. The original hasNext call returned false and argument preparation advanced. Nonempty iteration/mutation is NOT claimed; ew$b construction still awaits its argument completion.

**2224321 JVM instructions /133 internal steps**,40 canonical successful receipts, epoch40/lifecycle1. Checkpoint1287918B SHA256 `674613edb6e58c0c29cbc093c154da6b446c25989236b2632f1f6df18f024ee1`. Discovery676.809s plus same-code/package precision506.082s. World `build/java-diff-mc-arraylist-iterator-original131-parent-p52/official`.

Next exact q1 missing **java/lang/reflect/Array**. Authenticated original ew binding106/method4 PC2 calls newInstance(Class,int):Object. The actual canonical Class mirror8273 names java.lang.Iterable, with length0. Metadata/wire observations remain read-only, never execution input.

All65536 sine bits retain SHA256 `87a67a39fff59636acb04edcda4ef622831037291f11fb61586c57596771dac2`. No original host Java/ZIP/class parsing, rewriting, injection, oracle input, terminal/failed-state resumption or cross-code/package checkpoint migration. Protected core/vm/core/state/params equal95665d570. Oversized LOCAL SetCode preinstall through ordinary EVM Call, NOT standard CREATE deployability. Gas/state/consensus/EIP170/EIP3860 unchanged; block/time1, checkpoints are not mined blocks. No world/EULA/listening/Done.

Evidence: `parent-array-list-iterator/artifacts/reflect-array-newinstance-blocker.json`, all116 root audit, private owner/cursor/high-index/retained-tail proofs, gates/refusals/reopen records, actual component-mirror graph and40 ordered original receipt hashes.
