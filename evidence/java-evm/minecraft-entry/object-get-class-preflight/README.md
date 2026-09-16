# Generated bounded `Object.getClass()` source stage

This generated-only source stage derives exactly from accepted raw32 parent
`parent-5f01fbbdf`. It replaces only bootstrap `java/lang/Object` slot0 with
the checked Java 8 `public final native Class<?> getClass()` declaration and
adds global native binding13. Constructor and identity-`equals` Code remain
identical; the remaining 85 bootstrap images and their positions are byte
identical.

`tools/verify_source.py` pins six accepted parent inputs and proves the exact
engine/coordinator/driver delta. It retains raw32/262144, diagnostic118,
frames128, checkpoint1MiB, head32768, exception kinds14, String-local binding10,
optimizer200, viaIR/Cancun/metadata-off and runtime cap393216. Binding13 routes
only a non-null ordinary receiver through the established canonical Class-mirror
allocator: it has no host type query, does not initialize the target, preserves
raw defining-loader identity and quota/OOM behavior, and refuses arrays,
primitive literals and forged Class objects. A supplied raw Object remains its
own ordinary Code and cannot claim binding13.

The generated fixture/gate covers dynamic subclass/class-literal identity,
repeated and distinct-object canonical identity, Class-mirror reopen/checkpoint
validation, no-init, null NPE, array/primitive/forged-mirror refusal, raw Object
replacement, allocator OOM, and all retained raw32/lock/TreeMap/String/EnumSet/
queue/OOM/canonical-receipt gates. It uses only generated Java-8 sources and
does not open an original artifact, JAR, class, resource, checkpoint, or world.

Reproduce with pinned local dependencies only:

```sh
python3 evidence/java-evm/minecraft-entry/object-get-class-preflight/tools/build.py build/java-diff-mc-object-get-class-build-LOCAL
python3 evidence/java-evm/minecraft-entry/object-get-class-preflight/tools/generate_fixtures.py build/java-diff-mc-object-get-class-fixtures-LOCAL
python3 evidence/java-evm/minecraft-entry/object-get-class-preflight/tools/gate.py build/java-diff-mc-object-get-class-build-LOCAL build/java-diff-mc-object-get-class-fixtures-LOCAL build/java-diff-mc-object-get-class-gate-LOCAL
```

Parent alone runs unchanged original32. No provider/factory/world/Done claim is
made here.
