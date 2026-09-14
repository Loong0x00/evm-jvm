# Measured `ConcurrentLinkedQueue` preparation — completed

Accepted original26 includes genuine same-JAR `StatusLogger$BoundedQueue`, but at
`StatusLogger` PC29 hierarchy validation returns `HierarchyError(1,25)`. Independent
Java8 `javap` on the pinned JAR proves raw class index25 directly extends absent platform
`java/util/concurrent/ConcurrentLinkedQueue`. Failed q7/q1 calls preserve trie/head.

Append a bounded single-guest-thread queue subset:

* `java/util/Queue<E> extends Collection<E>` and adds `poll()`;
* public `java/util/concurrent/ConcurrentLinkedQueue<E>` extends accepted
  `AbstractCollection<E>`, implements Queue/Serializable, and supplies `()V`, `add`,
  `poll`, `size`, `iterator`, plus inherited `isEmpty`.

Use only EVM-owned guest `Object[]` storage. `add` rejects null with the existing guest
NPE and otherwise publishes a newly allocated copied array preserving FIFO order; `poll`
returns null when empty or removes/returns the head by
publishing a copied tail. `iterator` may reuse the already accepted package-private COW
snapshot iterator because both classes are in `java.util.concurrent`; no helper image or
host queue/lock is needed. There is one guest Thread, so nonblocking/concurrent progress,
weakly-consistent iteration and broader Queue APIs are explicitly absent rather than
fabricated.

Compile against a fully stripped Java8 bootclasspath, prove all accepted79 images
byte-identical, append exactly two images (total81), update prepare/hash/reservation tables
and diagnostic max class count107 (raw26+bootstrap81). Fresh Java8 host oracle and guest
q1/q7/direct/reopen/canonical must verify hierarchy, empty poll, duplicate FIFO,
catchable null-add NPE, size/isEmpty transitions, snapshot isolation/exhaustion, queue
array-quota OOM and raw
replacement refusal. Retain lock/COW/Class.newInstance and prior controls.

Parent acceptance and the next measured frontier are recorded in
`JAVA_EVM_MC_CONCURRENT_LINKED_QUEUE_PARENT_PREFLIGHT.md`.

The accepted stage uses fresh LOCAL384 engine/coordinator/domain/address/world and keeps raw26/262144,
exception14, global native11, String-local10, frames128, CP4096, Code65535,
heap/VFS/checkpoint1MiB, Head32768, LOCAL1B/25M reserve/30s and whole20min/4GiB fixed.
Parent independently rebuilds/replays and starts fresh unchanged original26 q7→q1.
Worker must not access original Minecraft artifacts/worlds. No host execution path,
fabrication, failed-state recovery, main-body/world/Done claim, raw-cap growth or push.
