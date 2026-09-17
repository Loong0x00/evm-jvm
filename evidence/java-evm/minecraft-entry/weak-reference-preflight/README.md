# Bounded `WeakReference` source stage

This generated-only stage derives exactly from accepted Integer parent
`parent-36ea2d7e6`. It appends one Java-8-produced bootstrap image at index 86
(total 87): `java/lang/ref/WeakReference`, a direct `Object` subclass with one
private final `Object referent` field, public `(Object)V` constructor, and
public `get()Object`. The 281-byte image is SHA-256
`9e3ef194b9d08f98f8e99f45fe8e192e38f6120e214e46596b8f9351351f9a36`.

The referent is a strong deterministic guest reference: `get()` returns the
identical supplied guest object, and a null referent remains null. This is not a
general `java.lang.ref` implementation: there is no `Reference` or
`ReferenceQueue` superclass/hierarchy, GC clearing, `clear`, `enqueue`,
`isEnqueued`, reachability, finalization, or other API.

Only the append, raw-name reservation, domain/address rebinding, and read-only
checkpoint diagnostic class bound `119 -> 120` change from the accepted parent.
Raw33/262158, native13, selected resource/Properties/String/Integer pipeline,
all prior bootstrap images and positions, frames, checkpoint/Head, compiler,
and outlined tail remain pinned. One source build produced runtime 391765 /
393216 bytes (1451 bytes headroom, exceeding the required 762-byte margin) and
a 5394-byte coordinator.

The focused trusted Java-8 fixture checks non-null referent identity on repeated
`get`, null retention, and field-backed retention q1/q7/direct/reopen. It
finishes at 72 Java / 2 internal steps and epochs 72/11/1 with identical machine
root and opaque payload. No-init, raw replacement, and omitted `clear()`
controls are atomic. The retained direct/reopen gate completed 85 result rows,
286 commands, 1597 canonical receipts, and 148.051 seconds (cap 1200).

Only trusted generated Java-8 sources are compiled. No original artifact, JAR,
class, resource, Provider construction, factory, world, or Done input is read or
claimed. Parent alone reruns unchanged original33.

Reproduce with local pinned tools only:

```sh
python3 evidence/java-evm/minecraft-entry/weak-reference-preflight/tools/build.py build/java-diff-mc-weak-reference-build-LOCAL
python3 evidence/java-evm/minecraft-entry/weak-reference-preflight/tools/generate_fixtures.py build/java-diff-mc-weak-reference-fixtures-LOCAL
python3 evidence/java-evm/minecraft-entry/weak-reference-preflight/tools/gate.py build/java-diff-mc-weak-reference-build-LOCAL build/java-diff-mc-weak-reference-fixtures-LOCAL build/java-diff-mc-weak-reference-gate-LOCAL
```
