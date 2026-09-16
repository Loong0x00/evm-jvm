# Generated raw-class cap31 evidence

Source commit `9d0007d46` derives this generated-only stage from accepted
TreeMap parent `parent-4fc3c418b`.  The source verifier pins six parent source
inputs and proves that the only semantic bound changes are raw selected classes
`30 -> 31` and the diagnostic checkpoint class bound `116 -> 117`.  It retains
all 86 bootstrap images/order, raw bytes `262144`, CP `4096`, Code `65535`,
frames `128`, 1MiB heap/VFS/checkpoint, Head `32768`, 12 native bindings, 14
exception kinds, optimizer 200/viaIR/Cancun/metadata-off, the outlined tail,
and the local runtime cap `393216`.

The one source build produced a `386844`-byte engine (6372-byte headroom) and
`4146`-byte coordinator.  `build-pins.json`, build logs, source manifest and
hash manifest identify the exact outputs.

The complete generated-only gate passed in `190.9644386850414` seconds: 227
successful commands plus the expected exit-2 pre-mutation raw32 driver guard;
2610 canonical receipts across 71 successful q1/q7/direct/reopen worlds.
Raw31 completed with equal q1/q7/direct machine root
`0x199e62dafe8e7835db81a82a8aea7a652db9e258f2f07fc8b10d59f222866c34`,
124 Java and 2 internal steps, and matching opaque checkpoint hash
`40b4ed37e4dbb2b3a0cf4438e5b6a0dc92ae4be4ef67b2ea2f3ceefc2584037e`.

Raw32 was atomically refused at all required boundaries: no driver world;
coordinator `MR0Error(2)` selector `0xab23ed08`; and product engine
`LinkError(1,32)` selector `0x427cfac5`, each with unchanged root.  The exact
262144-byte raw31 package was admitted through the coordinator and reached the
parser, which returned the expected atomic `LinkError(1,0)` profile refusal;
262145 bytes was atomically rejected by coordinator `MR0Error(12)`.  Retained
TreeMap/String/StringBuilder/EnumSet/queue/OOM controls and canonical receipt
verification are in the full summary and synopsis.

Reproduce with local pinned dependencies only:

```sh
python3 evidence/java-evm/minecraft-entry/classcount31-preflight/tools/build.py build/java-diff-mc-classcount31-build-20260916
python3 evidence/java-evm/minecraft-entry/classcount31-preflight/tools/generate_fixtures.py build/java-diff-mc-classcount31-fixtures-20260916
python3 evidence/java-evm/minecraft-entry/classcount31-preflight/tools/gate.py build/java-diff-mc-classcount31-build-20260916 build/java-diff-mc-classcount31-fixtures-20260916 build/java-diff-mc-classcount31-gate-20260916r2
```

No ProviderUtil, original artifact/JAR/class/resource, LoggerContextFactory,
Minecraft execution, world, or Done claim is present.  Parent alone may append
the genuine ProviderUtil class and run original31.
