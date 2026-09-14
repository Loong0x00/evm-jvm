# Bounded `java.lang.Boolean` preflight

**PARENT RESULT:** semantic image accepted after independent build. Worker109MB
monitor covered smoke only, not compilation; parent whole peak is961515520B. Original
advances to ClassLoader.loadClass PC15. See BOOLEAN_PARENT_PREFLIGHT.


## Scope

Append exactly one self-contained Java 8 `java/lang/Boolean` bootstrap at index 65
(total 66) to the frozen 65-image System-property parent basis. The image provides
canonical `TRUE`/`FALSE`, `Boolean(boolean)`, `valueOf(boolean)`, `booleanValue`,
`equals`, `hashCode`, string conversions, and comparison/bridge behavior emitted by
Java 8. It deliberately omits `TYPE`, String construction, parsing, and property
lookup.

This is a LOCAL-only Minecraft-entry dependency preflight. It does not execute an
original JAR, Minecraft main body, a world, EULA handling, or host Java substitution.
All generated fixtures and EVM transport evidence are archived below
`evidence/java-evm/minecraft-entry/boolean-preflight/`; disposable rebuild trees use
ignored `build/java-diff-mc-boolean-*` paths.

## Frozen limits

The preflight retains raw inputs `24/262144`, 128 frames, CP 4096, Code 65535,
heap/VFS 1 MiB, checkpoint 1 MiB, Head 32768, and 25M reserve. The authorized
LOCAL external ceiling is 1B with 30s/call and a 20 minute/4 GiB process-tree guard.
The measured runtime must remain at or below LOCAL384; accepted LOCAL320 is unchanged.

## Generated-only result

`evidence/java-evm/minecraft-entry/boolean-preflight/run-final-20260913T231151Z/`
contains the allowlisted compressed source-build artifacts, generated resources/classes,
full receipts and opaque checkpoints, plus hashes. It contains neither a Go binary nor
LevelDB/original payloads. The generated gate exited 0 in **490.673317s**, with a true
process-tree peak of **109244416 B**; the 1200s/4GiB watchdog did not fire.

The fresh solc 0.8.30 (`opt=200`, via-IR, Cancun, metadata off) engine is **352122 B**
(**41094 B** below LOCAL384), SHA-256
`ffd14e68b414419d4a8e6b4ea3555986877ca5d7529c5ea8997025abd8ef651a`,
Keccak `eddfc253b123ac8a7370cb1ab5729eabbbd42db7ea5457dbe71a0799e10388f6`.
The ordinary-CREATE coordinator is 4146 B, Keccak
`91d8c70d6aa7f0bf3c1865db3e24dd997e549cc450ccf2e4f7db1865fdea87b6`.
All nine engine and three coordinator commitments use `MC-BOOLEAN-PREFLIGHT1`, with
engine `0x4d432d424f4f4c45414e2d505245464c49474854` and a distinct owner.

The Java 8 source-built Boolean image is 1241 B, SHA-256
`6f0938b496e361caf4066648f0bfa6c73fe340d54245d36a73d1cb82e2d8b846`; it is tail
index 65 of a 66-image root. q1/q7/direct-q4096/reopen Boolean witnesses agree at
290 JVM / 4 internal steps (epochs 290/42/1), including `TRUE`/`FALSE` identity,
constructor distinction/equality, values, hashes, strings, comparison and erased
Comparable bridge. Retained combined System/resource/set/loader/thread/PA/security/
Properties/arraycopy controls also agree at 3156/18 steps (epochs 3156/451/1).
Raw Boolean replacement refuses; omitted `parseBoolean` and `getBoolean` each refuse
with `CallError(3,2)`. Existing omitted System/URL APIs retain their measured
`CallError` refusals.

No original JAR, original class, Minecraft main body, EULA or world was executed by
this worker. The parent must make a fresh original22 q7 then q1 continuation against
these new pins; no later blocker is claimed here.
