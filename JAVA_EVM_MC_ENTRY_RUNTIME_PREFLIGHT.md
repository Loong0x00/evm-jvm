# MC-ENTRY runtime COPY preflight

**Status: compiler-built and narrow generated opaque-ZIP smoke only; unaccepted.** This sole Solidity COPY is confined to `evidence/java-evm/minecraft-entry/runtime-preflight/`. It follows the Minecraft-first entry preparation, not a general JVM/session completion claim. It does not inspect an official JAR, execute an original class/instruction, accept a quota/profile, or claim Minecraft/EULA/listener/world/Done.

## Candidate

The new `MCEntryInterpreter` combines the repaired MR0 exact `main(String[])V` behavior with the verified lazy `Selected[][][]` table. Exact-root lookup remains descriptor-specific; the non-null empty `String[]` is installed before Java may legally overwrite local 0. Root argument/max-local checks run before predecode, and all Selected reads are direct typed `[0]` reads: the discarded pure getter allocation is absent. Method indexes, loaded guards, method-local handler cache ownership, restore loading, serializer and call-family logic remain copied.

The only library addition is a generated Java 8 `java/lang/Runnable` bootstrap. It is appended after the fixed existing tail, preserving Object/Cloneable/Serializable and every throwable/string/file index. The no-supplied case has 39 bootstrap images (`33 + 5 optionals + Runnable`), hence `inputCount + 39`; no Thread or Minecraft shim exists.

The isolated cap is 16 images / 262144 aggregate, with each coordinator-bound DI0 resource <=262144. The engine and coordinator both enforce it; coordinator fixed arrays are 16. This is a COPY rationale for an entry hierarchy/logging resources, not a promotion from accepted 4/65536 or proof that 8 is uniquely insufficient. No demand loader, cache, opcode, Java SE feature, heap/VFS/frame/CP/Code/AS0/ZI0/DI0 cap change exists.

## Pins, ABI and diagnostics

Engine local-install address is `0x4D43454e545259454E47494E4500000000000001`, runtime 296529 bytes, SHA-256 `b1c9d04ad9ef7f4eb0183a92fb944c9a87dcbd748e0f70bf17d19c4a9fe5cabb`, Keccak `9d4fdaec87e8e21f243f4cc994da134646311f02cc0141da649085e2c5ada61c`. Coordinator runtime is 3547 bytes, Keccak `1d08028ae55a3a43471cdc417ba48ba7900ba70b29398d2e15ef58d6044df694`, and pins that exact engine. Compiler is pinned solc 0.8.30+commit.73712a01 / opt200 / viaIR / Cancun / metadata off.

`startMain`, `resumeMain`, typed receipt fields and all established errors remain intact. New COPY-only `MCEntryMissingClass(uint256,uint256,bytes)` returns the actual validated EVM class-data UTF slice and immediately reverts. Site/context mapping is recorded in the evidence README; interface edge context is owner index, not Java PC. It does not cause host loading, fallback, continuation, counters or branch changes.

New engine/coordinator/package/resource/VM domains are explicitly `MC-ENTRY-PREFLIGHT`, detailed in evidence README. AS0/ZI0/DI0 pins remain their accepted dependencies but are not borrowed as a new profile identity.

## Narrow execution

Fresh generated Java 8 classes were archived only as opaque deflated ZIP input. EVM AS0, ZI0 and DI0 performed index/inflate/CRC/final reads (all <=4096) before normal coordinator calls. `RESULTS.json` records q1/q7 overload, legal null/new-array local0 rebind, typed RuntimeException, and a real Runnable implementation `invokeinterface` terminal outcomes. Each individual call stayed below 100M gas. A missing interface class returned `MCEntryMissingClass` selector `0x555db429`, site 4098, owner index 0, `missing/Nope`, with unchanged root.

The raw smoke output is deliberately ignored; essential source, compiler products, fixture builders, ABI, driver recipe, result metrics and error receipt are tracked under the evidence directory. It is not a full phase/Open/publication/CAS/session matrix, a density/capacity proof, or an original-JAR attempt. Parent independently rebuild/replay and any original resource selection remain required.
