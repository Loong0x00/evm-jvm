# Java-on-EVM Minecraft `System.identityHashCode(Object)` preparation

## Measured blocker
Accepted `parent-d03bd329d` genuinely loads Validate.class and reaches87527J/79I. Atomic q1 refuses `CallError(3,1)`. Fresh-domain EVM-only diagnostics identify exact owner `java/lang/System`, method `identityHashCode`, descriptor `(Ljava/lang/Object;)I` (sites4122/4123/4124; static-resolution site code3013). No host class/JAR parsing established this dependency.

## Required one bounded semantic change
Add exact public static native `int System.identityHashCode(Object)` and global native binding17 (String-local remains12). Null returns0. Every valid non-null guest reference returns the deterministic low uint32 guest heap handle, independent of dynamic class and overridden guest hashCode; handles are nonzero, stable across calls/checkpoints/reopen, never host addresses/hashes, and are not allocated or mutated by this call. Validate normal reference kind/handle invariants; provide no Object.hashCode, synchronization, GC, host identity, or other System API.

Preserve raw70/464925, bootstrap96, diagnostic166. Preserve every prior image except measured System; String lower-case, Locale, Map$Entry and Integer exact. Independently derive changed ordered bootstrap root. Preserve setOut/setErr isolation and all earlier System fields/methods. Runtime<=393216 (prior379383).

## Gate
Generated Java8 fixtures prove exact class/method metadata; null=0; same ordinary object/array/Class mirror gives stable nonzero identity; distinct simultaneously-live guest handles give distinct values; overridden hashCode is never invoked; no allocation/state mutation; q1/q7/direct/reopen equivalence. Retain System out/err/setters, lower-case/Locale/String/Map/Integer, raw70 and exact capacity refusals. Add omitted Object.hashCode/general System refusal and raw System replacement refusal. Verify only System image leaf changes, independent root, global17/String-local12, canonical receipts/DI0 reads, atomic refusals, <=1200s, durable results/SHA256SUMS, clean commit. No original/JAR/resource/network/provider/world/EULA/Done input/claim, other worktrees, push/review/delegation/Fast; parent replay deferred.
