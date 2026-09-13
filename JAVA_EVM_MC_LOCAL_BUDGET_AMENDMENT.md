# User-authorized LOCAL1B budget amendment

The user explicitly directed continuation after the proposed LOCAL-only1B budget:
"继续啊,问我干啥". This supersedes the prior no-automatic1B restriction for this
LOCAL experiment. Do not request the same confirmation again.

## Scope

Only the COPY Go harness external call ceiling changes100000000 ->1000000000.
Per-call30s and whole20min/4GiB protections remain. EVM gas accounting, source,
bytecode, code/address pins, ABI,25M reserve, heap/VFS/class/CP/engine caps and
accepted/core/consensus/Makefile artifacts are unchanged. Old100M measurements
remain labeled and preserved. This is not a standard-chain deployment claim.
Same-engine public checkpoints can continue: no cross-code state reuse occurs.
High-budget receipts explicitly mark LOCAL1B-USER-AUTHORIZED and suppliedGas.

## Immediate results

From genuine epoch249/1683J checkpoint,1B budget resumes past the old commit
reserve. The first nine q1 calls spend98767799..99847209 gas each, not1B each.
At epoch258 a **read-only diagnostic** erroneously asserted physical depth<=16.
Source verification shows the interpreter's existing MAX_FRAMES is **128**, and
was already128 in the parent basis. The checkpoint legitimately has17 frames.
The first observer failure is preserved; only its bound was corrected to128.
No runtime frame limit was raised. Earlier parent prose predicting a16-frame
runtime limit was incorrect and is superseded by this source-verified correction.

Normal q7 continuation then reaches **epoch261/1713J/12I**, with original
PropertiesUtil(String) atPC12, after completing Properties construction. Next
actual missing class is original LoaderUtil at static PC13.261 mixed-budget
receipts independently verify (epochs<250 retain100M; epochs>=250 require1B label).
Largest successful gas101587968; no main-body/EULA/world/Done claim.

Add genuine LoaderUtil ->fresh original21 (221382B) under the same engine and1B
budget: **epoch245/1715J/12I**, CP12213B SHA
`d69de8ca6f12480533d23362cf157e5c2fdce4c15ea95c10312af8c11cd1f51c`, root
`db35a32d33f99b82c7fd059aa5907852f5cb2bc3b30c9a896372b401bd2013da`.
Peak/last successful gas104302090. Next actual failure is **CallError(3,0)**
selector d631c3a4 at76644038gas, matching missing
`System.getSecurityManager()Ljava/lang/SecurityManager;` at original LoaderUtil
initializer PC0. Static TEST-only javap explains the member, not execution input.
The last successful checkpoint only schedules that initializer; no failed-slice
progress is credited. Original21 gate95.909880s/148795392B;245 receipts verified.

Next is only the measured System getter in the VM's no-installed-manager default
state, not a Java security framework or fake LoaderUtil/resource enumeration.
No push; last authorized public snapshot remains1e4027b9b. Evidence/recipes live
under `evidence/java-evm/minecraft-entry/local-budget-1b/`.
