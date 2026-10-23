# P45 — parent-verified Comparator SAM link/dispatch

## Accepted capability

The guest bootstrap appends one genuine Java8 `Comparator<T>` public/abstract interface declaring abstract `compare(T,T):int` and `equals(Object):boolean`. Comparisons are executed by ordinary concrete guest methods and compiler bridges. No host comparison, native binding or fake comparator result exists. Unmeasured default/static helpers, including reversed/thenComparing/naturalOrder, remain unsupported and explicitly refuse.

Parent rebuilt the256-byte image with `javac -g:none -source8 -target8` and matched the candidate byte-for-byte (SHA256 `32ebde62ff75e5e7226a2200d9990e390a461d7241bf6e2b1bc994dfa155b6ad`). The worker's295-byte source probe differed only because it retained SourceFile metadata; this was not a semantic classfile mismatch.

Parent independently reconstructed all108 ordered leaf commitments. The old107 P44 prefix is byte-identical. **The worker-reported root144cde... did not match source `keccak256(abi.encode(DBOOT,h))`; parent refused it and preserved the failed assertion/build and metadata before using the independently calculated actual root:**

`7796c48c62a0f714f39b5dcb38b110dd84f98d01992806a7c92ddfb08f45a7dd`.

This corrects metadata, not guest source or validation strength. The actual engine source/codehash was unchanged by that root-label correction.

- Engine422008B SHA256 `848bcc58408b9eda44a2d76575d65e40d8aed38abdc85ff1c13bcb6b79dcd1ac`, Keccak `31e1a12737c20987b6e81a9d07026ea0c9419f07cc49ef4dd7405c02854ae979`.
- Coordinator5411B SHA256 `6239e5af71c6c1bc82df8271c717c095c70b83c82b2b5c686c302422e4afd33a`.
- New leaf107,108 total; native21/String12 and all quotas fixed. Array8192/object4096/elements262144/handles12545/raw150/1063930/CP2MiB/runtime-artifact1MiB/frame128 and quantum limits unchanged.
- Only count/append/root/new image/reserved name and explicit domains/codehash change. Execute/virtual/native dispatch, eager heap, codec/schema, ABI/storage remain unchanged.

## Fresh parent EVM verification

Worker recovery was explicitly build-only. Parent—not the worker's host/Go checks—provided the new-artifact EVM evidence. Heavy compilation/EVM phases were serial after the reported crashes; no guest or gas rule was changed to achieve this.

Parent fixture executes a captured-direction length comparator, negative/zero/positive int returns, defined null handling, inherited subinterface, generic String bridge, wrong-type bridge CCE, null receiver NPE, and real Comparator[]/clone. It includes corrected PAT2/CRLF/fixed-width behavior. Stock Java8 is a generated-only oracle and never an execution input.

- Small raw3 q7/q1:6213 JVM steps;336.808s at1B; peak64938950gas; exact final machine/VFS/counters/heap and new-process EVM checkpoint/code/Head validation.
- Exact raw150 +108 bootstrap = **258 internal classes**, Comparator index **257**: q4096/q65536 exact same outcomes/roots/heap, new-process reopen. Two distinct real Comparator[] arrays encode class257 as metadata **0x201** with identical shallow cells. Current two-byte checkpoint class count/index represents this directly.
- Wide case preserved actual1B/2B shortages, then passed at **separate4B** in2.917s; peak3267616609gas. q4096 peak1850470633gas. Not ordinary1B/2B success.
- Fresh1B raw exact-image Comparator replacement and omitted `invokeinterface reversed()` tests raw-refused atomically. The prefix also tests inherited Object.equals fulfilling the interface declaration. No fake helper result, invented Java exception or failed-state continuation.

Coordinator count/index stays uint8 for at most150 **raw bindings**, not258 engine classes. No coordinator ABI/storage/hash-width migration or quota increase occurred.

## Genuine original progress

A fresh unchanged original116/815898B run under P45 resolved Java Comparator and entered original Guava `Ordering.natural()`. Actual original comparison invocation is **not claimed**; the generated fixture separately proves compare dispatch.

Precise result: **2223796 JVM instructions /116 internal steps**,43 verified successful canonical receipts, epoch43/lifecycle1. Checkpoint1283975B SHA256 `f4275f124af5d99c1a53f92f1f8246e14cdc6be7ff061fe2b1826bd53fa5fc59`. Discovery647.637s plus same-package precise562.094s. World `build/java-diff-mc-comparator-original116-parent-p45/official`.

Next exact q1 is original resource **com/google/common/collect/NaturalOrdering**, site4103/context0. The original ImmutableSortedMap initializer and Ordering.natural() method were authenticated/EVM-scanned for targeted next dependencies. All old worlds/terminal/failed states were preserved and never migrated to new code or package.

A parent archival helper initially copied the older P44 MAX-driver source into the P45 archive. A subsequent resource-measurement CLI correctly refused its P45 artifact before constructing a world. The actual P45 gates/original run had used the correct independently built P45 authorized driver throughout. The archive source pointer was corrected and the stale source/error retained; no validation or gas pin was relaxed.

All65536 sine raw bits still match the accepted read-only-oracle-verified table SHA256 `87a67a39fff59636acb04edcda4ef622831037291f11fb61586c57596771dac2`. Underlying geth core/vm/core/state/params remain equal to base95665d570; no EVM pricing/state/consensus/EIP170/EIP3860 change. Engine is oversized LOCAL StateDB.SetCode preinstallation through ordinary EVM Call, not standard CREATE deployability. Fixed block/time1 and checkpoints are not mined blocks. Still no main argument processing/world preparation/EULA startup/listening/Done.

## Evidence

`parent-comparator-interface/artifacts/natural-ordering-resource-blocker.json`, all108 root audit, class258/index257 array proof, parent small/wide/reopen/typed-refusal records and43 canonical original receipts/hashes. `review/` retains original wrong root metadata, initial failed assertion, Java image inspection and archive-driver mismatch history. Source and interrupted drafts remain preserved; current metadata is explicitly labeled parent-corrected.
