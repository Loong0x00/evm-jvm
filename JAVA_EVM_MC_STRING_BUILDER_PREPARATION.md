# Java-on-EVM Minecraft bounded `StringBuilder` preparation

## Measured blocker

The parent-amended bounded `System.err` engine in `parent-89928ece8` (required solc optimizer200, runtime392775/393216) passed source verification and the full generated gate. Fresh unchanged original30 advanced through the former `System.err` failure to 8697J/39I. q7 and narrowed q1 both stop atomically with `MCEntryMissingClass` at site4104/context9 for exactly `java/lang/StringBuilder`; all1245 successful receipts verify canonically.

The last successful frame is genuine `org/apache/logging/log4j/simple/SimpleLogger.<init>` classIndex26/methodIndex0 PC9, called by `StatusLogger.<init>` at PC80. Parent-only constant-pool decoding records the immediately required bounded surface:

- `new java/lang/StringBuilder`
- `<init>:()V`
- `append:(Ljava/lang/String;)Ljava/lang/StringBuilder;` (three non-null strings on this measured path)
- `toString:()Ljava/lang/String;`

No raw class-count increase is measured or authorized.

## Strict scope

1. Append one immutable Java-8-produced bounded `java/lang/StringBuilder` bootstrap image after the accepted84 images; preserve all84 prior image bytes/order, including amended System, PrintStream and EnumSet.
2. Reserve `java/lang/StringBuilder` against raw replacement.
3. Implement genuine guest bytecode for construction, same-object chained `append(String)`, ordered character accumulation, and a String result with normal guest allocation/copy semantics. No host StringBuilder or execution path.
4. The accepted claim is limited to the measured constructor, `append(String)` and `toString()` surface. Do not claim capacity APIs, primitive/Object append overloads, `AbstractStringBuilder`, `Serializable`, or broad Java SE compatibility. Null handling must either match Java8 `"null"` append semantics or be explicitly bounded and tested without hiding a failure.
5. Bootstrap count becomes85; exact raw30 diagnostic class bound becomes115. Preserve raw30/262144, CP4096, Code65535, frames128, heap/VFS/checkpoint1MiB, Head32768B, LOCAL1B/25M reserve, 12 native bindings,14 exception kinds, optimizer200/viaIR/Cancun/metadata-off, and every other accepted limit.
6. Runtime must remain <=393216 (441-byte current headroom). Any size repair must preserve runtime-derived limit/bootstrap commitments and must not weaken prior checks.

## Required generated-only gates

- strict reverse verifier pinned to parent-89928ece8 and exact parent source/runtime hashes;
- Java8 provenance and append-only first84 proof;
- q1/q7/direct/reopen/canonical probes for empty, repeated/chained non-null append, identity, ordered content and toString copy behavior;
- bounded null behavior and quota/OOM control;
- uninitialized and raw-replacement refusal controls;
- retained System.err, failed initialization, raw30/31 three-layer,262144/262145, EnumSet/ACC_ENUM, queue and OOM gates;
- source build, runtime size/hashes, receipts and monitoring.

Candidates may use only generated fixtures and local Java8/compiler inputs. No original JAR/classes/resources/worlds, sibling worktrees, network, push, or Minecraft/Done claim. Parent alone runs original30 after acceptance and measures the next blocker.
