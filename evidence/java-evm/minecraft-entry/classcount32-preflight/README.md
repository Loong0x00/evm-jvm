# Generated raw class cap32 source stage

This generated-only source stage derives exactly from accepted lockInterruptibly
parent `parent-850386373`. It raises only the selected raw-class count `31→32`
and the derived diagnostic checkpoint class bound `117→118`.

`tools/verify_source.py` pins the six accepted parent inputs, proves all 86
bootstrap image bytes and their order are unchanged, and proves all remaining
limits/toolchain settings are retained: aggregate raw bytes 262144, frames128,
checkpoint1MiB, head32768, 12 native bindings, 14 exception kinds, optimizer200,
viaIR/Cancun/metadata-off, and runtime cap393216. The coordinator arrays and
constructor limit plus the generated-only driver boundary are changed only for
the new raw count.

The generated fixture/gate proves raw32 q1/q7/direct/reopen success, raw33
atomic refusal independently at driver, coordinator, and engine boundaries,
unchanged 262144/262145 aggregate-byte boundaries, and the full retained
lockInterruptibly/String/TreeMap/EnumSet/queue/OOM canonical-receipt gate.
It uses only generated Java-8 sources and does not open an original artifact,
JAR, class, resource, checkpoint, or world.

Reproduce with pinned local dependencies only:

```sh
python3 evidence/java-evm/minecraft-entry/classcount32-preflight/tools/build.py build/java-diff-mc-classcount32-build-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount32-preflight/tools/generate_fixtures.py build/java-diff-mc-classcount32-fixtures-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount32-preflight/tools/gate.py build/java-diff-mc-classcount32-build-LOCAL build/java-diff-mc-classcount32-fixtures-LOCAL build/java-diff-mc-classcount32-gate-LOCAL
```

Parent alone may append the pinned genuine raw32 class and run original32. No
loader/resource result, Minecraft execution, world, or Done claim is made here.
