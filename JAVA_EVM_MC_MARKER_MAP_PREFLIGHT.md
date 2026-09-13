# MC-first MarkerManager platform-map COPY preflight

**Work in progress; generated fixtures only.  This is neither accepted runtime nor
Minecraft execution.**  The candidate is an isolated derivative of recovered
class-literal candidate `4cf97854e`, at integration base `52d973017`.  Its complete
write set is `evidence/java-evm/minecraft-entry/marker-map-preflight/`; accepted
`jvmevm`, core, quotas, artifacts, ABI, Makefiles and global manifests are untouched.

## Measured reason and narrow target

Parent's opaque, unchanged-server-JAR transport reached Java step 4 / epoch 4 after
adding the genuine `MarkerManager` class.  Its next EVM refusal is
`MCEntryMissingClass(4104, PC0, java/util/concurrent/ConcurrentHashMap)` at
36,779,158 gas.  Parent alone owns all original-JAR selection and resumption.  This
worker never reads, parses, packages, or executes original classes.

The candidate supplies only the platform hierarchy and ordinary Java 8 guest
bytecode required by that observed `MarkerManager` path:

* `java/util/Map`, `java/util/concurrent/ConcurrentMap`, `java/util/AbstractMap`,
  and `java/util/concurrent/ConcurrentHashMap`, with the standard latter shape:
  `ConcurrentHashMap extends AbstractMap implements ConcurrentMap, Serializable`.
* A no-argument constructor and `get(Object)`, `putIfAbsent(Object,Object)`,
  `containsKey(Object)`, and `clear()`.  Small `put`, `size`, and `isEmpty` are
  only adjacent test surfaces; this does **not** claim a full `Map`/collections
  implementation.
* A linear ordinary guest field/`Object[]` representation is permitted.  Absence
  returns null; `putIfAbsent` preserves and returns an existing reference;
  equal-but-distinct String and well-behaved custom equal keys find one entry;
  values retain their object references.  Null key or value throws guest NPE.
  Growth must either succeed inside existing heap/array limits or produce the
  actual bounded outcome—never drop, overwrite, or host-store entries.
* Equality is guest virtual dispatch (`Object.equals` default identity, normal
  String override), never String-key specialization or a host equality evaluator.
  There is one guest-thread only: this does not claim locks, parallel threads, or
  Java concurrent-map linearizability.

## Frozen boundaries and proof obligation

The candidate preserves COPY limits: at most 16 raw images/262144 aggregate and
per image, CP4096, Code65535, existing heap/VFS/frame/1MiB checkpoint boundaries,
100M gas/30 seconds, 25M commit reserve, and engine <=320KiB.  It uses an exact
oversized LOCAL engine initial state (not standard-chain CREATE); controller and
resource contracts remain ordinary CREATE.  No 1B calls or quota changes are
allowed.  Existing bootstrap indices stay fixed.  Appending maps must derive the
actual Class bootstrap slot for both supplied/unsupplied Runnable tails rather
than retaining the prior `+34` assumption; duplicate/reserved binding checks must
not be weakened.

Acceptance evidence must be fresh, full opaque generated Java-8 ZIP -> AS0 -> ZI0
-> DI0 metadata/DEFLATE/CRC/final <=4096-byte page reads -> coordinator/kernel
runs.  Direct, q1, q7, durable continuation, and fresh-process reopen must agree
for constructor, mutation, repeated equal keys, growth, clear and reference alias;
separate Java 8 oracle output is TEST-only.  Record actual EVM reverts, roots,
checkpoint receipts, compiler/domain/address/runtime pins and group watchdogs
under the owned evidence path.  Compilation or a source-only design is not
acceptance.  No original JAR, Marker/Log4j substitutes, logger fake, EULA, world,
or Done claim belongs here.
