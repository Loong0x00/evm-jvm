# Constructor-only `ThreadLocal` source stage

This generated-only stage derives its runtime exactly from accepted raw35 parent
`parent-7183e57f8`. It appends Java-8 image 89 at bootstrap index 88:
`java/lang/ThreadLocal`, a 136-byte SHA-256
`3b492a73fe71c60d5594f5116e813b857e248d7ca29270a8e33974143dc595d0`
direct `Object` subclass with only public `<init>()V`.

The append is deliberately narrower than Java `ThreadLocal`: no `get`, `set`,
`remove`, `initialValue`, `withInitial`, value map, per-thread isolation,
inheritance, `InheritableThreadLocal`, or callback API. The raw name is
bootstrap-owned, so a bundle cannot replace it.

Only the append, its name reservation, bootstrap vector/allocation count
`88→89`, read-only checkpoint diagnostic bound `123→124`, and required
namespace/address/runtime-hash rebind change from raw35. Raw35/268379,
all prior 88 image bytes and positions, native13, String-local10, exception
kinds14, resource pipeline, frames128, checkpoint1MiB, Head32768, compiler,
and all other fixed limits remain pinned.

The naïve constant-folded root commitment duplicated the 136-byte image layout
and measured 393811 bytes, 595 above the 393216 cap. The accepted root computes
`keccak256(_bootstrapThreadLocal())` at index 88 instead, preserving the exact
same image/root semantics while using one literal. It measures 392326 / 393216
bytes (890-byte headroom); the coordinator is 5394 bytes. See
`layout-recovery.json`.

The trusted focused constructor fixture verifies two distinct non-null guest
allocations and a stable alias q1/q7/direct/reopen: 34 Java/2 internal steps,
epochs 34/5/1, identical machine root and opaque payload. A no-use root leaves
slot 88 uninitialized. Raw replacement is atomically refused. Separate
`get`, `set`, `remove`, `initialValue`, and `withInitial` bytecode controls all
produce an atomic EVM `CallError(3, pc)` refusal; no result or state is
fabricated.

The retained direct/reopen gate completed 104 rows, 365 commands, and 4539
canonical receipts in 312.287 seconds (cap 1200). It uses only trusted
generated Java-8 fixtures. No original artifact/JAR/class/resource, Provider
construction, factory, world, or Done input is opened or claimed. Parent alone
runs original35.

Reproduce with pinned local tools only:

```sh
python3 evidence/java-evm/minecraft-entry/thread-local-constructor-preflight/tools/build.py build/java-diff-mc-thread-local-constructor-build-LOCAL
python3 evidence/java-evm/minecraft-entry/thread-local-constructor-preflight/tools/generate_fixtures.py build/java-diff-mc-thread-local-constructor-fixtures-LOCAL
python3 evidence/java-evm/minecraft-entry/thread-local-constructor-preflight/tools/gate.py build/java-diff-mc-thread-local-constructor-build-LOCAL build/java-diff-mc-thread-local-constructor-fixtures-LOCAL build/java-diff-mc-thread-local-constructor-gate-LOCAL
```
