# Parent acceptance: measured raw-class cap 25

The parent independently accepted the authorized LOCAL-only raw class-count change
from 24 to 25. The unchanged aggregate raw-byte cap remains 262144. The integrated
commits are `34f5daf53` (source; worker `d21757333`) and `7a067b5d9`
(preflight; worker `cff7a63e0`). Evidence is
`evidence/java-evm/minecraft-entry/parent-cff7a63e0/`.

## Independent source build and scope

The parent verified the source delta against accepted `feca8b5d2`: the engine's
nine identity-domain strings, `MAX_RAW_CLASSES` and committed count word change
24→25; coordinator fixed arrays/guard and both durable-driver guards change to25;
the read-only diagnostic bound changes95→96. The 262144-byte cap, 71 bootstrap
images, 10 global natives, String-local binding10, 14 exception kinds, 128 frames,
1MiB heap/VFS/checkpoint limits, 32768-byte Head limit, LOCAL1B/25M reserve, and
30-second call limit are unchanged. Accepted320 and the prior accepted24 world are
not modified.

The isolated parent domain is `MC-CLASSCOUNT25-PARENT1`, engine address
`0x4d432d434f554e5432352d504152454e54000001`. A source build with solc0.8.30,
optimizer200, viaIR, Cancun and metadata disabled produced a 370032-byte runtime,
SHA256 `15800c0846af3863a5ebdb282583658744797dc34b705efdcad43cccc0bc11d8`,
Keccak `e06f1a6b52a664d84c4698b02eee8f5dbf2924ebea7331866b5524a5f1bcf5df`.
The 4146-byte coordinator Keccak is
`3808223eeb407ea1991e28bf381045973efe02df382eae99784f596d2efd395e`.
Java8 rebuilt all replaced platform images byte-identically.

## Parent gates

A fresh monitored generated gate passed exact24 and25 under q1, q7 and direct
q4096, reopen/canonical verification, and reordered package commitment. Exact26
was refused by the input guard before world creation. Exact25/262145 returned
`MR0Error(12)` without CREATE-root mutation. The valid exact262144 fixture read all
resources then returned the unchanged parser's `LinkError(1,0)` at877620983 gas;
this is recorded as infeasible, not successful. The gate took27.745s and peaked at
122003456 bytes group RSS. Parent Class.asSubclass, Integer/NFE, split/CNFE and all
retained focused controls also passed in isolated fresh worlds.

## Unchanged original JAR execution

The parent created a fresh original25 world from the pinned untouched Minecraft
server JAR SHA256
`fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e`.
The prior24 names/sizes are identical and the sole append is genuine same-JAR
`org/apache/logging/log4j/message/ParameterizedNoReferenceMessageFactory.class`
(1488 bytes, SHA256
`a326dc3cbea653393855100cd6a463f08ed1e7c80c8928bf3feddb4cc3cb3db6`).
The package is25 classes/228073 bytes.

q7 published a successful checkpoint at epoch545/3815 Java/32 internal steps.
Four successful q1 slices then reached epoch549/3819 Java steps. Canonical
verification covered all549 successful receipts, nested ABI, events, checkpoint
hashes, counter chains and resource-read ranges. Both failed calls preserved the
successful trie root. The next measured blocker is genuine
`java/lang/Class.newInstance:()Ljava/lang/Object;` at
`AbstractLogger.createDefaultFlowMessageFactory` bytecode PC3, reported as
`CallError(3,3)`. The target mirror denotes the already-packaged
`DefaultFlowMessageFactory`; its genuine zero-argument constructor has not been
executed.

No original JAR, class/resource page, checkpoint payload, Go binary or LevelDB is
in the evidence archive. Minecraft main body, world creation and `Done` remain
unreached and are not claimed.
