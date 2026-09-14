# Bounded `Class.newInstance()` preflight source

Basis: `a0cfa9bc1`, with the accepted raw-class-25 source retained at
`evidence/java-evm/minecraft-entry/classcount25-preflight/`. This is a new isolated
LOCAL384 domain, `MC-CLASS-NEW-INSTANCE-PREFLIGHT1`; it is not an accepted profile,
original-artifact execution, world, Minecraft startup, or Done claim.

Only the Java 8 replacement `java/lang/Class` image changes. It adds the exact public
native `T newInstance() throws InstantiationException, IllegalAccessException` signature.
The two checked types are declaration metadata only: this profile does not add bootstraps
or fabricate either exception. The EVM has global Class binding 11 (String-local binding
10 remains distinct), validated as exactly public/native/no-Code `()Ljava/lang/Object;`.

Binding 11 accepts only an existing canonical mirror for a raw public, concrete,
non-interface target that has exactly one public `()V` constructor. The selected ordinary
constructor descriptor and Code are parsed/predecoded before active use or allocation.
Unsupported bootstrap, abstract, non-public, duplicate/missing/invalid-constructor shapes
revert `ClassNewInstanceProfileError` before guest allocation; this intentionally is not
Java reflection breadth. Null follows the existing guest NPE path.

A successful target uses the ordinary class-initialization continuation (the native PC is
rewound if `<clinit>` schedules), ordinary String/VFS/Throwable profile guards and object
quotas, a `KIND_UNINIT` caller alias, and an ordinary constructor child frame. Existing
constructor return code upgrades aliases to initialized references. The profile keeps raw
25/262144, 71 bootstraps, 14 exception kinds, 128 frames, CP4096, Code65535, 1MiB
heap/VFS/checkpoint, Head32768, and LOCAL1B/25M reserve/30-second call caps.

`tools/verify_source.py` rebuilds the Java 8 image and guards source/pins. `tools/build.py`
creates a clean ignored build tree, compiles solc 0.8.30 optimizer-200/viaIR/Cancun/
metadata-off artifacts, and builds/vets the bounded driver. Generated-only fixtures and
run evidence are added separately; this directory must never contain an original JAR,
original class/resource/page, world/LevelDB, or Go binary.
