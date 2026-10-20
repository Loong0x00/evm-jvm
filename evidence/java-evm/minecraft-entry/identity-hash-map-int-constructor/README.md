# LOCAL IdentityHashMap(int) constructor candidate

This append-only stage is based on `array-list-raw150-byte1063930/`. It preserves
its first 99 Java 8 bootstrap images and appends one 2,682-byte
`java.util.IdentityHashMap` image at slot 100. The new image implements only the
real `IdentityHashMap(int expectedMaxSize)` construction path, including its
Java 8 table-capacity calculation, eager zero-filled `Object[]`, and
`size()`/`isEmpty()`. Negative capacities throw guest
`IllegalArgumentException`. Map reads/writes/views, equality/hash/string/clone,
and Java 8 `Map` defaults are refusal-only native declarations; no map behavior
is claimed. Missing no-arg construction and raw platform replacement are
negative controls.

The independent local Java 8 reflection oracle recorded table lengths 8, 8, 8,
16, 32, 64, 2,048, 4,096, and 65,536 for expected sizes 0, 1, 2, 3, 10, 21,
512, 1,024, and 21,845. The 21,846 control crosses the existing VM array bound
and throws guest `OutOfMemoryError`; the `Integer.MAX_VALUE` control verifies
that capacity arithmetic does not overflow before that guest allocation
failure. Neither boundary test changes the existing 65,536-element array cap.

The generated-only gate is recorded in `runs/idmap-complete/`. It passed with
the initial 1-billion per-call gas and 1,200-second test-only wall budgets (no
budget doubling): 34 generated fixtures, 17 host-oracle rows, 11 direct q1/q7/
q4096/q65536 schedules, all refusal/replacement controls, exact raw150 and
1,063,930-byte controls, and the paired ordinary-CREATE coordinator route.
The q1 matrix checkpoint is 577,938 bytes and independently reopens in a
separate process. Its inspected heap has nine distinct zero-filled `Object[]`
tables with the reflection-oracle lengths above, nine IdentityHashMap objects,
size zero, and bootstrap count 100. The engine runtime is 398,071 bytes; the
coordinator runtime is 5,411 bytes. `runs/idmap-initial2/` preserves a separate
harness-report failure from before the missing README was added; it is not the
passing run.

The candidate uses a 1,048,576-byte local runtime/checkpoint ceiling, preserves
the 150 raw-class / 1,063,930 raw-byte limits, and updates the diagnostic class
frontier from 249 to 250 only because the bootstrap image count is now 100. No
native bindings, EVM opcodes/gas rules, consensus limits, accepted profiles, or
original Minecraft inputs were changed or used. Parent independent review and
stage acceptance remain pending; this generated-fixture result is not Minecraft
execution or a general-JVM claim.

Run the generated-only gate from the repository root with:

```sh
python3 evidence/java-evm/minecraft-entry/identity-hash-map-int-constructor/tools/run_gate.py RUN_ID
```
