# Bounded `monitorenter` / `monitorexit` generated-only stage

This LOCAL generated-only stage starts from `parent-886800502`, whose unchanged
91-image runtime is 393123 bytes. It adds Java opcodes `0xc2` and `0xc3` to the
one-byte predecoder and to execution. Each operation pops one packed reference.
A null reference raises the existing catchable guest `NullPointerException`; a
valid non-null reference completes as a no-op. This is deliberately only the
balanced, reentrant, single-guest-thread subset: it has no monitor ownership
state, cross-thread contention, scheduling, `wait`, or `notify` claim.

The only source cleanup shares the existing `ifnull`/`ifnonnull` reference-pop
and packed-reference validation path with the new monitor pair. The strict
source verifier reconstructs the complete engine from the parent and permits
only this grouping, the two one-byte predecode additions, and fresh domain /
address commitments. All 91 image leaves and their runtime-derived root order
are unchanged. Raw38/285489, diagnostic129, native13, all quotas, compiler and
gas limits are pinned.

The trusted Java 8 fixture uses nested `synchronized (lock)` blocks on the same
object, then catches `synchronized ((Object) null)`'s NPE. `javap` confirms
three `monitorenter` instructions and at least three `monitorexit`
instructions. The EVM q1/q7/direct/reopen chains all terminate at 34 Java and
4 internal steps with identical machine root
`0x6e31793ae5581c4e45fe1515958753112b8b89d70798101c59aecba46f8690ef`
and opaque payload SHA-256
`bd1b5d9b28a61bf3d4899ae31ac6465c792cdcdb6b99709eef48200df1334bb7`.

The reproducible runtime is 393191 bytes, 25 bytes below the unchanged
393216-byte cap. The full focused-plus-retained generated gate completed in
570.255 seconds (limit: 1200) and verified 8516 canonical receipts. Durable
pins and concise outputs are in `build-pins.json` and `results/`; large worlds
remain disposable under ignored `build/`.

No original artifact, JAR, class, resource, StatusData, provider factory,
world, or Done input/claim is included. Parent-owned accelerated original
replay is outside this stage.

Reproduce from repository root:

```sh
python3 evidence/java-evm/minecraft-entry/monitor-enter-exit-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/monitor-enter-exit-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/monitor-enter-exit-preflight/tools/build.py build/java-diff-mc-monitor-enter-exit-build-LOCAL
python3 evidence/java-evm/minecraft-entry/monitor-enter-exit-preflight/tools/generate_fixtures.py build/java-diff-mc-monitor-enter-exit-fixtures-LOCAL
python3 evidence/java-evm/minecraft-entry/monitor-enter-exit-preflight/tools/gate.py build/java-diff-mc-monitor-enter-exit-build-LOCAL build/java-diff-mc-monitor-enter-exit-fixtures-LOCAL build/java-diff-mc-monitor-enter-exit-gate-LOCAL
```
