# Measured reentrant-lock bootstrap preparation — completed

Accepted bounded `CopyOnWriteArrayList` original25 reaches epoch556/3856 Java steps.
Its genuine constructor and backing array are stored in `StatusLogger.listeners`. At
`StatusLogger.<init>(String,MessageFactory)` PC18, exact bytecode `new
java/util/concurrent/locks/ReentrantReadWriteLock` returns
`MCEntryMissingClass(4104,18,...)`; q7/q1 failures preserve the published trie/head.

Append a bounded single-guest-thread Java8 lock family:

* `java/util/concurrent/locks/Lock` interface with `lock()`/`unlock()`;
* `ReadWriteLock` with stable `readLock()`/`writeLock()` accessors;
* `ReentrantLock` implementing Lock/Serializable, no-arg construction and balanced
  reentrant hold accounting;
* `ReentrantReadWriteLock` implementing ReadWriteLock/Serializable, constructing and
  retaining distinct read/write Lock objects and returning stable identities.

There is only one bounded guest Thread and no scheduler or host concurrency authority.
Balanced nested lock/unlock must be genuine guest field mutation; unsupported fairness,
conditions, interruptibility, timed acquisition, ownership transfer, contention and
unbalanced-unlock exception semantics remain absent rather than fabricated. Do not call
host lock APIs or label this Java concurrency completeness.

Compile against a Java8 bootclasspath stripped of all replacements. Prove the accepted75
bootstrap images byte-identical and append exactly four new immutable images (total79).
Update bootstrap hash/image tables, reserved replacement names and diagnostic class bound
to104 (raw25+bootstrap79), with no other semantic change.

Generated Java8 host-oracle plus guest q1/q7/direct/reopen/canonical gates must verify
interface/class hierarchy, stable distinct read/write handles, nested balanced read/write
and standalone reentrant lock operations, constructor/field effects, and raw replacement
refusal for all four names. Retain COW snapshot/OOM, Class.newInstance init/failure/OOM,
Class/asSubclass, Integer/split/CNFE/resource/loader/VFS controls.

Parent acceptance and the next measured frontier are recorded in
`JAVA_EVM_MC_REENTRANT_LOCKS_PARENT_PREFLIGHT.md`.

The accepted stage uses a fresh LOCAL384 engine/coordinator/domain/address/world and keeps raw25/262144,
exception14, global native11, String-local10, frames128, CP4096, Code65535,
heap/VFS/checkpoint1MiB, Head32768, LOCAL1B/25M reserve/30s and whole20min/4GiB fixed.
Parent independently rebuilds/replays then starts a fresh unchanged original25 q7→q1
world. Worker must not access original Minecraft artifacts/worlds. No host execution path,
fabrication, failed-state recovery, main-body/world/Done claim, push, or preemptive raw
class-count change.
