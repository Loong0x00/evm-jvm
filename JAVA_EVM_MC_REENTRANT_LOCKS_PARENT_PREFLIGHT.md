# Parent acceptance: bounded single-guest-thread reentrant locks

The parent independently accepts the measured LOCAL-only lock bootstrap family. Worker
commits `4bcfc4ab6`/`bfa5ce174` were integrated as `4b5a2ed18`/`355547999`.
Evidence is `evidence/java-evm/minecraft-entry/parent-355547999/`.

## Append-only scope

Four Java8 images append after the accepted75-image tail:

| index | image | bytes | SHA256 |
|---:|---|---:|---|
|75|`Lock`|121|`2a42b9f6c7c67e7996d7506cab1a4eeefb880c64a5bd6a29f22ce07a6bf23752`|
|76|`ReadWriteLock`|169|`a23b234f1764b1f8630fc5b9deb0e1da73e95894b032eb99dfdda90bc8efae66`|
|77|`ReentrantLock`|342|`aa33a72cddd3f1263bfe7418d885583504fa5a378aba7ec253cdfc3cde80471d`|
|78|`ReentrantReadWriteLock`|535|`f79e87954391ca6cb4f9ebf71123a1b0d58badb0df2f6ad6db03fa97f799331b`|

Strict Java8/reverse-source verification proves all75 prior images byte-identical and
permits only domain isolation, counts75→79/69→73, four append assignments/images and
reserved-name additions. `ReentrantLock` uses ordinary guest integer field mutations for
balanced reentrant `lock`/`unlock`. `ReentrantReadWriteLock` constructs distinct stable
read/write lock objects. There is one bounded guest Thread and no scheduler/host lock.
Fairness, condition, interrupt/timing/contention/ownership-transfer and unbalanced-unlock
semantics are absent, not fabricated; no Java concurrency-completeness claim is made.

## Build and gates

Parent domain is `MC-REENTRANT-LOCKS-PARENT1`, engine address
`0x4d432d524c4f434b532d504152454e5400000001`. Independent solc0.8.30
optimizer200/viaIR/Cancun/metadata-off build produced a 385212-byte runtime, SHA256
`3123fe6d9512abf22b50814f7dd113eb9382171c0b1cfa37cefcb597cb1fda5d`,
Keccak `0d9224c30cc236728ce70aa0b76cf6a7c0f612a5f21e78ae5747827899464f84`.
The 4146-byte coordinator Keccak is
`e93a98671668757d39dd3b81c7eb2ad888806a3226f285d801ebe7472cc4ca31`.
The build took231.19s and peaked at984485888 bytes group RSS, within LOCAL384.
Raw25/262144, exception14, global native11, String-local10, frames128, CP4096,
Code65535, heap/VFS/checkpoint1MiB, Head32768 and LOCAL1B/25M reserve/30s remain fixed;
diagnostic max class count is104.

A fresh Java8 host oracle and guest q1/q7/direct/reopen/canonical gate pass hierarchy,
stable distinct accessors, standalone and nested balanced write/read reentrancy at218
Java/2 internal steps. The retained COW gate also converges at748/8; all1107 receipts
verify canonically. All four raw replacement attempts refuse atomically. Parent reruns of
COW quota OOM, Class.newInstance initialization/UNINIT/throw/failing-init/OOM,
Class/asSubclass, Integer/NFE and complete q7 retained controls pass. The known large
all-retained direct4096 fixture remains an honestly recorded fixed-1B atomic capacity
refusal at984382020 gas; no failed state is resumed and no limit is raised.

## Unchanged original Minecraft result

A fresh world used the pinned untouched server JAR SHA256
`fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e`
and unchanged genuine25-class/228073-byte package. q7 reached epoch554/3878 Java/32
internal steps; five q1 checkpoints reached epoch559/3883. All559 successful receipts
passed canonical nested ABI/event/checkpoint/counter/resource-range verification.

The real `ReentrantReadWriteLock` replacement constructor (class index103) executes both
nested lock constructors, publishes stable fields, returns, and is stored in
`StatusLogger.listenersLock`. The next measured blocker at `StatusLogger.<init>` PC29 is
genuine same-JAR `StatusLogger$BoundedQueue.class` (1377 bytes, SHA256 recorded in
parent evidence). A raw26 package would be229450 bytes under262144; the user has already
authorized measured count increments. q7/q1 failed calls preserve trie/head. No Minecraft
main body, world creation or `Done` is claimed.
