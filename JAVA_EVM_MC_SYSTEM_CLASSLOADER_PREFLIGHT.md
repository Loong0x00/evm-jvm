# System ClassLoader getter preflight

**PARENT RESULT:** exact320 cap failure and LOCAL384 source build/replay verified.
Original22 commits all three canonical loader-array entries and next requires
LinkedHashSet at PC36. See JAVA_EVM_MC_SYSTEM_CLASSLOADER_PARENT_PREFLIGHT.md.


Scoped LOCAL Minecraft startup COPY from parent basis `6d6b8ea0e` /
`MC-CLASS-DEFINING-LOADER-PARENT1`. The sole proposed semantic addition is
`java.lang.ClassLoader.getSystemClassLoader()Ljava/lang/ClassLoader;`, a public
static native zero-argument getter. It must return the already-existing,
validated concrete `VMClassLoader` that raw `Class` mirrors use. It neither
installs nor creates a loader.

The getter is limited to exact ClassLoader/name/descriptor metadata. Existing
native bindings 1--4 (Float/Double) and 5 (`System.arraycopy`) retain their
existing behavior. Active-use initialization and normal operand-stack capacity
remain in the static invocation path. Missing, duplicate, malformed, or
wrong-state canonical-loader state fails with `LC0StateError`; no resource or
class-loading API is added.

## Measured worker result

The Java 8 ClassLoader image is 195 bytes, SHA-256
`9a2d38f5b25e30aee6f0b494d23bba28aeb686ea8e338a21616b8ac6a6118f86`.
Its only addition is the exact public static native getter. Binding 6 validates
that exact metadata and pushes the reference through `_push`; it scans the
existing VMClassLoader object with the same canonical loader scan used by raw
Class mirrors. Missing/duplicate/malformed state is `LC0StateError(7,0)` and
never allocates a loader.

The unchanged 320 KiB compiler guard failed and is retained: the candidate is
328695 bytes. The separately labeled authorized **LOCAL384KiB** compile passed:
engine SHA-256 `0f7c5fdf07a9cff27c1030dfd72b04dd1f6b9e05aa301449908fa41d06a6e8d6`,
Keccak `dbbd4e3ec0d7346164b514671918ee8410b08947568977b34a1eec7663475211`.
The new fixed LOCAL engine address is
`0x4d432d53595354454d2d434c4153534c4f414401`; all nine engine domains use
`MC-SYSTEM-CLASSLOADER-PREFLIGHT1`. Coordinator Keccak is
`4e385c96461766e0a91d8e401bfa91d3acf352b5ee5074cf459a8a1e66399b8b`.
Accepted 320 KiB is not changed.

Generated three-raw-class control succeeds after 332 JVM/8 internal steps:
q1/q7/direct epochs are 332/48/1, with equal machine root
`0x4dfd6f2020431fdaba40cbba2c8d855382db7b54404a29ba3f2974b65d4faf63`
and equal opaque SHA-256
`e74ac608a58987300118be3d9c605f8e41498108fc7e59a2a9c703d6c2bd6011`.
It asserts two raw mirrors and repeated system getter share the same nonnull
identity, while bootstrap Class/ClassLoader mirrors are null; it also retains
Thread, PrivilegedAction, System, Properties, and arraycopy controls. Reopen
is exercised for each quantum. Public refusal controls retain missing
`getResources` as `CallError(3,21)` and reject a raw VMClassLoader replacement
as `BootstrapProfileError(1,1)` with unchanged roots.

A fresh bounded whole compiler/q1/q7/direct/reopen group (including the
preserved 320 failure and LOCAL384 rebuild) exited 0 with recursive process-group
peak **914752 KiB** across 14794 samples; its monitor receipt is archived.

Full generated artifacts, sources, receipts/checkpoints, refusal receipts and
hash list are under
`evidence/java-evm/minecraft-entry/system-classloader-preflight/`. No original
JAR/class, Minecraft world, resource lookup, or parent original22 replay was
run by this worker.

This is an unaccepted LOCAL experiment. It is not a JVM, resource lookup, or
Minecraft readiness/Done claim. Other existing LOCAL limits remain unchanged.
