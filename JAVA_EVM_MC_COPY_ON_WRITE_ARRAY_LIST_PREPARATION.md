# Measured `CopyOnWriteArrayList` preparation

Accepted bounded `Class.newInstance()` original25 reaches epoch552/3840 Java steps.
`DefaultFlowMessageFactory` is genuinely initialized/constructed and
`AbstractLogger` returns. At `StatusLogger.<init>(String,MessageFactory)` PC7, exact
bytecode `new java/util/concurrent/CopyOnWriteArrayList` returns
`MCEntryMissingClass(4104,7,java/util/concurrent/CopyOnWriteArrayList)`; q7 and q1
failed calls preserve the published trie/head.

Implement a bounded Java8 bootstrap replacement rather than a raw JAR binding. Preserve
the relevant genuine hierarchy and behavior by appending:

* subset `java/util/List<E> extends Collection<E>` and marker
  `java/util/RandomAccess` interfaces;
* public `java/util/concurrent/CopyOnWriteArrayList<E>` extending the accepted
  `AbstractCollection<E>` and implementing List, RandomAccess, Cloneable and
  Serializable;
* a package-private iterator implementation over an immutable array snapshot.

The accepted subset must provide public `()V`, `add(E)`, `size()`, `iterator()` and
inherited `isEmpty()`. Every add allocates/copies a new backing `Object[]`, permits null
and duplicates, and existing iterators retain their prior snapshot. Iterator
`hasNext()`/`next()` must be genuine and `next()` raises existing
`NoSuchElementException` at exhaustion. Do not model concurrency with host locks or
claim broader List/COW APIs. Any unimplemented method remains absent rather than fake.

Rebuild all dependent subset util sources with Java8 against a stripped bootclasspath;
prove existing Collection/AbstractCollection/Iterator images remain byte-identical.
Append only the four new immutable EVM-owned images, update bootstrap hash/image tables
and diagnostic total-class bound from96 to100 (raw25+bootstrap75). Add exact bootstrap
replacement-reservation controls.

Focused generated gates must compare a Java8 host oracle and guest q1/q7/direct/reopen/
canonical behavior for empty/add duplicate/add null, List/RandomAccess/Collection type
checks, iterator snapshot isolation/order/exhaustion, field/array quota OOM, and raw
replacement refusal. Retain Class.newInstance failure/init/OOM controls and all prior
Class/asSubclass/Integer/split/CNFE/resource/loader/VFS controls.

Use a fresh LOCAL384 engine/coordinator/domain/address/world. Keep raw25/262144,
exception kinds14, global native11, String-local10, frames128, CP4096, Code65535,
heap/VFS/checkpoint1MiB, Head32768, LOCAL1B/25M reserve/30s per call and whole
20min/4GiB fixed. Parent independently source-builds/replays and then starts a fresh
unchanged original25 q7→q1 world. Worker must not access original Minecraft artifacts or
worlds. No host execution path, fabricated result, failed-state recovery, main-body,
world, `Done`, push, or broad Java concurrency claim.
