# Parent acceptance: bounded `CopyOnWriteArrayList`

The parent independently accepts the measured LOCAL-only bootstrap subset. Worker
commits `478776fb0`/`1b14b430e` were integrated as `35c05fce1`/`1cdc3be88`.
Parent evidence is `evidence/java-evm/minecraft-entry/parent-1cdc3be88/`.

## Append-only Java8 bootstrap source

Four immutable Java8 images append after the accepted71-image tail:

| index | class | SHA256 |
|---:|---|---|
|71|`java/util/List`|`e85defcb38f6b005ccc3c39bfca726e742760a50b184f0e1389a4bf04fbaa126`|
|72|`java/util/RandomAccess`|`ce6e8526c112ff3642eafbb6685836f23b5350e2bf0a6857ed0b97eb5812cf74`|
|73|`java/util/concurrent/CopyOnWriteArrayList`|`c74c8e413a68d5422683e07b530e4a2f711539442596d5e2c81eaa89518362b0`|
|74|package-private snapshot iterator|`997efeeb7306e89999b0a45d185af5a1794f15aa046d62dba0602664fe3dff7d`|

The parent rebuilt all dependent subset sources against a stripped Java8 bootclasspath
and proved the previous71 embedded images byte-identical. Strict reverse-source checking
allows only the nine domain strings, bootstrap hash/table count71→75, class-array
constant65→69, four append assignments/images, and exact reserved-name additions.

The bounded list extends accepted `AbstractCollection`, implements List, RandomAccess,
Cloneable and Serializable, and supplies only public `()V`, `add`, `size`, `iterator`
plus inherited `isEmpty`. Every append publishes a newly allocated/copied EVM-owned
`Object[]`; duplicates and null are preserved. Iterators hold immutable ordered snapshots
and throw the existing guest `NoSuchElementException` at exhaustion. There are no host
locks, host collection objects, native methods or claims for omitted List/concurrency API.

## Independent build and gates

Parent domain is `MC-COPY-ON-WRITE-ARRAY-LIST-PARENT1`; engine address is
`0x4d432d434f572d4c4953542d504152454e540001`. solc0.8.30,
optimizer200/viaIR/Cancun/metadata-off produced a 380285-byte runtime, SHA256
`bef2b55c8a35d9284d5d4138c5dd5f2d141bf946c1b0b098a025b5693b0c1738`,
Keccak `8e37aba5dda277bf830dc97f99490491dd5dd2e2c2f6ada963144f50061382b5`.
The 4146-byte coordinator Keccak is
`5a2c2cc9b84bd158905771daecad4066f1e131047c982ae034ac6cb2f9482905`.
The source build took237.57s and peaked at978046976 bytes group RSS, within LOCAL384.
Raw25/262144, exception14, global native11, String-local10, frames128, CP4096,
Code65535, heap/VFS/checkpoint1MiB, Head32768, LOCAL1B/25M reserve/30s and accepted
prior worlds remain unchanged. The diagnostic-only max class count is100.

A Java8 host oracle and fresh guest q1/q7/direct/reopen/canonical gate pass hierarchy,
empty/size, duplicate/null append, snapshot isolation/order and exhaustion at748 Java/8
internal steps. All856 successful receipts verify canonically; direct4096 peaks at
76057595 gas. Raw replacement of each new reserved class refuses atomically.

A dedicated array-count quota gate retains1021 zero-length inner arrays, reaches the
1024-array cap in the list constructor, and proves the next copy-on-write append raises
catchable guest OOM kind7 without changing size. q1/q7/direct converge in49 Java/4
internal steps with a53640-byte checkpoint. All bounded Class.newInstance success,
initialization/UNINIT, constructor-throw, failing-init/NCDFE, OOM, Class/asSubclass,
Integer/NFE and remaining retained q7 controls pass.

The old large eight-class all-retained fixture no longer fits a single direct4096 call:
it atomically exhausts the fixed1B budget at984382020 gas before any checkpoint. This is
recorded as a capacity refusal, not success and not recovered state; its complete q7 run
still terminates and verifies canonically. No limit was raised.

## Unchanged original Minecraft result

A fresh world used the pinned untouched server JAR SHA256
`fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e`
and the unchanged genuine25-class/228073-byte package. q7 reached epoch550/3850 Java/32
internal steps. Six q1 checkpoints then reached epoch556/3856 Java steps. All556
successful receipts passed canonical nested ABI/event/checkpoint/counter/resource-range
verification.

The EVM executes the genuine appended `CopyOnWriteArrayList` constructor (class index98),
publishes its backing array, stores it into `StatusLogger.listeners`, and reaches PC18.
The next measured blocker is exact `new
java/util/concurrent/locks/ReentrantReadWriteLock`, reported as
`MCEntryMissingClass(4104,18,...)`; both q7/q1 failed calls preserve the published
trie/head. Minecraft main body, world creation and `Done` remain unreached.
