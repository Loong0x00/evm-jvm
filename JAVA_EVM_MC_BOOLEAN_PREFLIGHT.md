# Bounded `java.lang.Boolean` preflight

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
