# Generated lockInterruptibly source stage

This generated-only source stage derives from accepted cap31 parent
`parent-1e0e9e9aa`. It replaces exactly the existing bootstrap slots for
`java/util/concurrent/locks/Lock` and `ReentrantLock`; all other 84 image bytes
and the 86-slot ordering remain pinned by `tools/verify_source.py`.

The Java-8 sources declare `lockInterruptibly()V throws InterruptedException`.
In this bounded single-guest-thread model its successful path increments the
same private `holds` field as `lock()`. It does **not** observe interrupt state,
block, schedule, arbitrate ownership/fairness, implement conditions/timed locks,
or claim general JUC behavior.

The generated fixture/gate covers interface dispatch, repeated/reentrant calls
and unlock, null-receiver NPE, no initialization, raw replacement of both
changed names, then every retained cap31 TreeMap/String/EnumSet/queue/OOM and
canonical receipt control. It does not read original artifacts, JARs, classes,
resources, worlds, or checkpoints.

Reproduce using local pinned dependencies only:

```sh
python3 evidence/java-evm/minecraft-entry/lock-interruptibly-preflight/tools/build.py build/java-diff-mc-lock-interruptibly-build-LOCAL
python3 evidence/java-evm/minecraft-entry/lock-interruptibly-preflight/tools/generate_fixtures.py build/java-diff-mc-lock-interruptibly-fixtures-LOCAL
python3 evidence/java-evm/minecraft-entry/lock-interruptibly-preflight/tools/gate.py build/java-diff-mc-lock-interruptibly-build-LOCAL build/java-diff-mc-lock-interruptibly-fixtures-LOCAL build/java-diff-mc-lock-interruptibly-gate-LOCAL
```

Parent alone may run unchanged original31 after independent review. No provider
result, factory, Minecraft execution, world, or Done claim is made here.
