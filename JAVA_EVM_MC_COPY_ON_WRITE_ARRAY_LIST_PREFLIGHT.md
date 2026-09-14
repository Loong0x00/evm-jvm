# CopyOnWriteArrayList bounded source/gate preflight

This local source/gate preflight follows `JAVA_EVM_MC_COPY_ON_WRITE_ARRAY_LIST_PREPARATION.md`.
It is **not accepted**, does not run an original Minecraft artifact, and makes no startup,
world, or `Done` claim.

## Source pin and bounded surface

Source commit `478776fb07a765d00c7a66e16c62f8a575b51265` creates the isolated
`MC-COPY-ON-WRITE-ARRAY-LIST-PREFLIGHT1` profile at engine address
`0x4d432d434f572d41525241592d4c4953542d3031`. It appends exactly four immutable
Java 8 images after the accepted 71-image tail:

| index | image | SHA-256 |
|---:|---|---|
| 71 | `java/util/List` | `e85defcb38f6b005ccc3c39bfca726e742760a50b184f0e1389a4bf04fbaa126` |
| 72 | `java/util/RandomAccess` | `ce6e8526c112ff3642eafbb6685836f23b5350e2bf0a6857ed0b97eb5812cf74` |
| 73 | `java/util/concurrent/CopyOnWriteArrayList` | `c74c8e413a68d5422683e07b530e4a2f711539442596d5e2c81eaa89518362b0` |
| 74 | package-private `CopyOnWriteArrayListIterator` | `997efeeb7306e89999b0a45d185af5a1794f15aa046d62dba0602664fe3dff7d` |

The List subset extends the accepted Collection; the list extends accepted
AbstractCollection and implements List, RandomAccess, Cloneable and Serializable. It
has only a no-argument constructor, `add`, `size`, `iterator`, and inherited `isEmpty`.
Each `add` uses ordinary Java bytecode to allocate a fresh Object array and copy old
references; it permits null and duplicates. Its iterator holds that array as an immutable
snapshot and uses the already accepted NoSuchElementException at exhaustion. No host lock,
concurrency, fake broader List API, or native binding was added.

`tools/verify_source.py` compiles all replacements using Java 8 `-g:none` and a stripped
rt.jar. It proves the previous 71 embedded images byte-identical, pins all four new
images, and reverses the only allowed domain/append/reservation changes to exact accepted
Class.newInstance source. The diagnostic class count is now raw25+bootstrap75 = 100.
Raw25/262144, exception14, global-native11, String-local10, frames128, CP4096,
Code65535, heap/VFS/checkpoint1MiB, Head32768, LOCAL1B/25M reserve and accounting stay
fixed.

Solc 0.8.30 optimizer-200/viaIR/Cancun/metadata-off source builds produced engine
380285 B, init SHA-256 `7b9fd92fce498b950ca6d681b27101434b449034686312e13d09694488eab5c9`,
runtime SHA-256 `b3bdfd4dc2625b61b5a54606ca357efc078e7c71fddc47f2ae70fcb74a91d9c8`,
Keccak `0b1215626372b160fea2a13dd804bcb13628ca70e85c8f576c9745e74a147da4`.
The coordinator is 4146 B, init SHA-256
`4c3cf13ca28d42fc0dcbd9be307c1db50395b736cc58b86835a2f4b10e5d0804`, runtime
SHA-256 `f8d4076c4626e5416417a213654e32682099a858a2f3d28204ffc89a48321d41`,
Keccak `b0600466f3340ba27856031bf871a960c864fd4f2fb86ef274a5f721352b0f13`.

## Generated-only gate

The trusted Java 8 host oracle and guest fixture assert empty/inherited-isEmpty, hierarchy
(`List`/`Collection`/`RandomAccess`), duplicate and null append, snapshot isolation and
ordered iteration, plus both exhaustion paths. q1/q7/direct/reopen all terminally agree
at 748 Java / 8 internal steps and machine root
`0xba356d5e752a6869d73c6112d50cfc3927ae6c591ed094723e51f269c43a7f8d`; q1/q7/direct
epochs are 748/107/1. The focused gate completed in 42.55 seconds. Exact raw replacement
reservations for all four new platform names reverted before publication with selector
`0x6a23ad80`, words `[1,1]`, and unchanged roots (373415, 379977, 387001 and 389943 gas).

A generated Class.newInstance replay on the new 75-image profile retained success, caught
null NPE, and bootstrap/abstract/private-constructor profile refusals across q1/q7/direct
and reopen (6.89 seconds). Its durable summary is archived alongside the focused summary.

## Evidence and caveats

Tracked source, fixture, hashes and summaries are under
`evidence/java-evm/minecraft-entry/copy-on-write-array-list-preflight/`; no Go binary,
LevelDB/world, original JAR/class/resource/page or original-world result is present.

This worker run did **not** claim the expensive array-quota exhaustion path: repeated COW
copies interact with checkpoint capacity and needs a dedicated parent measurement. It also
did not rerun every retained Integer/split/CNFE/resource/loader/VFS control or a whole
20-minute/4-GiB monitored parent gate. Those are parent-only retained reruns, as is the
fresh original25 q7-to-q1 frontier; no original artifact or world was accessed here.
