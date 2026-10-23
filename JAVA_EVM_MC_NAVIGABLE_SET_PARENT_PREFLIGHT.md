# P46 — parent-verified SortedSet / NavigableSet hierarchy linking

## Scope and independent build

Accepted only the proper minimal Java8 marker chain `Set<E> <- SortedSet<E> <- NavigableSet<E>`. Both new interfaces are public/abstract, declare no navigation operations, and reserve their raw platform names. This is not a Java SE navigation implementation; omitted interface calls raw-refuse, not fake return values or invented Java exceptions.

Parent independently compiled the175B SortedSet and190B NavigableSet source images using Java8 `javac -g:none`, matching the embedded bytes exactly. All108 P45 bootstrap images and their order remain unchanged. Appended indices108/109 give110 images and actual independently derived root:

`757e01b7866b698d05ccc88846659f750aae4bb0030dd678bab6761cc69de156`.

- Engine423747B SHA256 `19a612b28b26d5d9a3bf470318417cf01f980f7d014e1905aa27a4768d437200`, Keccak `74d9fe8f41f15b889fdbbe59abda76a8555e70d9e2cc5ba91893de063090c6d7`.
- Coordinator5411B SHA256 `c719ef906361d13cca71604760a22b0c3b834c9d3a31a6785b0abd6f9abcf63d`, authenticating that exact engine.
- Friendly milestone P46; actual protocol domain is `MC-NAVIGABLE-SET-LINK-P45`. DBOOT retains the accepted P45 Comparator domain; actual new root and engine codehash bind the changed program. No label-based checkpoint migration.
- Native21/String12 and all limits unchanged: arrays8192, objects4096, elements262144, handles12545, raw150/1063930B, checkpoint2MiB, artifact1MiB, frames128, q65536/internal4096, reserve25M. No execute/dispatch/native/heap/codec/ABI/storage change.

The worker commit `e196b3c0b173c9ffd1497498e3b7d417ebc2b3f2` was explicitly build-only and unaccepted. Parent provided all fresh-artifact EVM evidence below. Heavy compiler/EVM phases ran serially for host stability only.

## Fresh genuine EVM gates

The generated Java8 fixture implements a custom Tagged subinterface and custom HashSet subclass with a captured integer. It proves ordinary guest dispatch, inherited Set dispatch, transitive instance-of/checkcast, wrong-type CCE, null-receiver NPE, typed arrays and eager shallow clones. Its custom size override is a dispatch witness, not a claim of standard navigation/storage behavior. Retained PAT2 and CRLF/fixed-width regex controls also pass. Stock Java8 is test-only, never an execution input.

- Small raw3: q7/q1,6096 JVM instructions, exact final canonical machine/heap/counters/VFS and independent-process EVM checkpoint validation/reopen.388.112s at canonical1B; peak71458800gas.
- Raw150 +110 bootstrap = **260 internal classes**: SortedSet index258 and NavigableSet index259. Real arrays encode **0x202** and **0x203**, not truncated bytes. Distinct handles5/7 and6/8 respectively retain the same real shallow object cell3. Both q4096/q65536 and separate-process reopen pass with exact final outcomes/heap/counters/roots.
- Wide case preserved measured1B and2B shortages, then passed at separately labeled **4B** in3.117s, peak3228617597gas. Not ordinary1B/2B success; generated public watchdog30s, outer process1200s.
- Fresh1B controls atomically refuse exact raw SortedSet and NavigableSet images, and a valid interface-typed `lower` call outside the profile. No failed call changes Head/root or publishes a checkpoint.

The coordinator uint8 count still counts only <=150 **raw resources**, independently of260 internal classes. Existing u16 checkpoint IDs already represent258/259. No count-width migration was necessary.

## Fresh unchanged original123

From a new P46 world, unchanged123-resource package/865014B genuinely passed the prior NavigableSet link blocker and reached original RegularImmutableSortedSet initialization. No original navigation operation is claimed.

**2223838 JVM instructions /123 internal steps**,45 verified canonical successful receipts, epoch45/lifecycle1. Checkpoint1285407B SHA256 `b17def7021c6ba9f1629d561ed594220c6667e1cc9d63c7580e039ccbd336401`. Discovery662.179s plus same-code/package precise633.426s; exact q1 missing original resource **com/google/common/collect/ObjectArrays**, site4103/context4. World `build/java-diff-mc-navigable-set-original123-parent-p46/official`.

Original heap:3568 objects/4681 eager arrays/106145 elements. All65536 sine raw bits retain SHA256 `87a67a39fff59636acb04edcda4ef622831037291f11fb61586c57596771dac2`.

A read-only archival review caught a stale P44 MAX-driver pointer inherited from the older helper before resource measurement. The actual gates/replay always used fresh P46 binaries; the stale archive was never executed. Source/copy retained under `review/`, archive pointer corrected and exact match asserted. No execution or gas validation weakened.

Underlying geth `core/vm core/state params` remain equal to base95665d570. Oversized runtime is LOCAL StateDB.SetCode preinstallation through ordinary EVM Call, not standard CREATE deployability. EIP170/EIP3860, gas/state/consensus rules unchanged; fixed block/time1, checkpoints are not mined blocks. No host original Java/ZIP/class parser, rewriting, injection, oracle-as-input, cross-code/package continuation or terminal resumption. Still no world/EULA/listening/Done.

Evidence: `parent-navigable-set/artifacts/guava-object-arrays-resource-blocker.json`, all110 ordered-root audit, high-index arrays proof, small/wide/reopen/refusal records and45 ordered original receipt hashes.
