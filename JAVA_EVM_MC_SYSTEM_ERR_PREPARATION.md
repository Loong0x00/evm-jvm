# Java-on-EVM Minecraft `System.err` preparation

## Measured blocker

Accepted cap30 parent evidence is `evidence/java-evm/minecraft-entry/parent-de60a3245/` at commit `0f01f1ff9`. Unchanged original Minecraft 1.12.2 plus genuine `Strings.class` advanced from 5298J/36I to a last successful 8641J/39I. q7 and narrowed q1 both stop atomically at `FieldError(2,74)`.

Parent-only constant-pool decoding, recorded in `statuslogger-fieldref.json`, proves the active instruction is `StatusLogger.<init>` classIndex5/methodIndex0 PC74, `getstatic #20`, targeting exactly:

```
java/lang/System.err:Ljava/io/PrintStream;
```

All 1237 successful receipts were canonically re-encoded and verified. The durable lifecycle remains RUNNING. This is not a missing raw-JAR-class measurement and does not authorize raw cap31.

## Strict scope

Implement only a bounded Java 8 guest bootstrap sufficient for the measured active use:

1. `java/lang/System` exposes the exact public static final `err:Ljava/io/PrintStream;` field.
2. Genuine guest `<clinit>` execution constructs a non-null, canonical guest object for `System.err`; no preinitialized/fabricated handle and no host Java execution path.
3. Replace only the measured `java/lang/System` image at its fixed slot44, append one immutable Java-8-produced `java/io/PrintStream` image after all 83 accepted slots, and preserve the other82 prior image bytes/order plus EnumSet behavior exactly.
4. Reserve both `java/lang/System` and `java/io/PrintStream` against raw replacement.
5. Claim only field resolution, genuine initialization, non-nullness, stable identity, descriptor/type assignability, checkpoint persistence and the constructor surface actually needed by `System.<clinit>`. Do not silently claim print/println/output semantics. Any omitted API must fail explicitly/honestly when measured.
6. Preserve raw30/262144, CP4096, Code65535, frames128, heap/VFS/checkpoint1MiB, Head32768B, LOCAL1B gas with25M reserve,12 existing native bindings,14 exception kinds, and all other accepted limits.
7. Use a fresh equal-length LOCAL384 domain/address. Runtime must remain `<=393216` despite the accepted parent's 393205-byte runtime; optimization/size repair may not weaken checks or alter unrelated semantics.
8. Bootstrap count becomes84 and exact raw30 diagnostic class bound becomes114. Do not raise raw count or any resource bound.

## Required generated-only gates

- strict reverse verifier pinned to `parent-de60a3245` and the exact accepted runtime/source hashes;
- Java8 provenance and append-only first83 image equality/order;
- System.err positive q1/q7/direct/reopen/canonical equivalence proving non-null stable identity and successful handoff through a generated constructor-shaped probe;
- failed/uninitialized System initialization controls (including existing catchable failed-initialization semantics);
- raw replacement refusal for both System and PrintStream;
- exact raw30 positive and raw31 driver/coordinator/engine atomic refusals retained;
- retained EnumSet amendment, Enum/ACC_ENUM, queue, OOM, byte-boundary and fixed-limit controls in proportion to risk;
- source build, runtime-size evidence, hashes, receipts, monitoring and honest limitations.

No original JAR/class/resource/world access is allowed in candidate worktrees. Parent alone runs unchanged original30 after acceptance and measures the next blocker. One semantic Solidity change should be admitted at a time; stop rather than broad JVM redesign.
