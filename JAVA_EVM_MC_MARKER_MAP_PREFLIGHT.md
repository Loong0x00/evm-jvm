# MC-first MarkerManager platform-map COPY preflight

**Candidate only; generated fixtures only.  This is neither an accepted runtime nor
Minecraft execution.**  The isolated derivative of recovered class-literal candidate
`4cf97854e` is based at `52d973017`.  Its complete write set is
`evidence/java-evm/minecraft-entry/marker-map-preflight/`; accepted `jvmevm`, core,
quotas, artifacts, ABI, Makefiles and global manifests are untouched.

Fresh source-build/generated evidence now exists under that owned directory.  The
q1 and q7 worlds have equal terminal machine root after 1397 Java/9 internal steps
and a separately reopened durable process; q1 uses 1397 epochs and q7 200.  The
q4096/direct world deliberately records its actual ordinary-cap refusal
`LC0ControlError(7)`, 73548878 gas, zero epoch and unchanged root, rather than a
quota raise.  Thus direct terminal equivalence remains an explicit gap, not an
acceptance claim.

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

Fresh evidence uses full opaque generated Java-8 ZIP -> AS0 -> ZI0 -> DI0
metadata/DEFLATE/CRC/final <=4096-byte page reads -> coordinator/kernel calls.
The Java-8 TEST oracle covers caught null-key/null-value NPE, custom/String equal
keys, prior return, alias, growth and clear; it has no execution authority.  Eleven
whole-group watched commands total 251.185517s with 866557952B peak sampled RSS.
Receipts, raw direct refusal, roots, fresh-process verification, pins and hashes
are durable under `actual-receipts/` and `SHA256SUMS`.  Compilation or this
narrow generated success is not profile acceptance.  No original JAR,
Marker/Log4j substitute, logger fake, EULA, world or Done claim belongs here.
