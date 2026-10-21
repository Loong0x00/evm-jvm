# P37 array `clone()` intrinsic — frozen worker scope

## Goal and source boundary

Implement Java 8's public array `clone()` behavior in the local preinstalled-code EVM interpreter. The target is a normal `invokevirtual` whose symbolic owner is an array class and whose name/descriptor are exactly `clone:()Ljava/lang/Object;`. Use only the pinned source-only P36 bundle at `evidence/java-evm/minecraft-entry/array-clone-source-base-p36/` plus generated Java 8 fixtures. Never read original Minecraft artifacts, world/checkpoint/receipt data, external binding lists, sibling worktrees, or network sources. Do not run Minecraft.

The exact source baseline commit is `1f604f3fc49aa92d4593114c0733177f5e841ce0`; its manifest and every listed file hash are checked in `source-proof.json`.

## Required semantics

1. Array-owner resolution is narrow: only `clone:()Ljava/lang/Object;` is intrinsic. Resolve the symbolic array descriptor with existing array/type logic; malformed, unsupported, incompatible, wrong-name, or wrong-descriptor calls retain typed interpreter refusals. Ordinary class owners continue through ordinary virtual method resolution; this work does not add `Object.clone()`.
2. A null receiver raises catchable guest `NullPointerException` kind 6. A non-null receiver must be an authenticated ordinary guest array whose runtime array type is assignable to the symbolic array owner.
3. Allocate a distinct eager ordinary array before returning. Copy exact rank and leaf type metadata and every raw `uint64` element cell; references are shallow-copied, primitive/raw floating-point bits are unchanged. No host JVM/classfile/ZIP execution, per-class special case, fabricated return, lazy/shared clone, or array backing alias.
4. Check existing array-count, length, element-count, handle, and allocation limits before publishing/mutating clone state. Resource exhaustion raises the existing catchable guest `OutOfMemoryError` kind 7 and leaves no clone published.
5. Type hierarchy scratch is per EVM invocation and is not checkpointed. Before covariance checks, validate the runtime reference-array leaf hierarchy in the current invocation; also do so for `checkcast`/`instanceof` array targets. This is required for resumed `String[]`-to-`Object[]` clone/cast behavior and prevents false `ClassCastException` after q1 checkpoints.

## Protected invariants

- Retain all 103 P36 bootstrap image bytes, order, and bootstrap commitment (`851a47c0…8725faa`). Keep the P36 bootstrap domain; only P37 runtime/package domains change.
- Add no native/operational binding. Keep global bindings at 21 and String-local bindings at 12; engine/coordinator ABI and storage layouts remain byte-identical.
- Keep raw inputs at 150 classes / 1,063,930 bytes, local engine runtime at or below 1 MiB, and checkpoints at or below 2 MiB. Keep the existing 4,096-array, 65,536-element-per-array, and 262,144-aggregate-array-element limits. No EVM gas rule, core, consensus, accepted quota, bootstrap image, wire format, or class-loader behavior changes.
- The interpreter runtime is oversized for EIP170 and is verified only via local preinstalled-code `Call`; this is not standard engine CREATE deployment evidence. The paired coordinator remains the ordinary CREATE route.

## Verification gates

- Build unchanged raw Java 8 fixture classes and run the generated-only host oracle.
- EVM clone matrix at q1/q7/q4096/q65536, requiring identical machine/VFS roots and Java/internal step totals; primitive/reference/multirank arrays, covariant `String[]`, shallow copy, raw float/double bits, zero length, and caught null NPE.
- Eager 65,536-element clone, caught array-count OOM at exactly 4,096 live arrays (including entry `String[] args`), caught aggregate-element OOM, and read-only heap audit proving counts were not incremented by failed clone.
- Typed atomic refusals for unsupported name/descriptor, malformed/incompatible/empty array owners, and ordinary `Object.clone` on both a non-array receiver and a generated normal `Cloneable` guest object.
- Fresh OS-process/LevelDB reopen of the q1 clone checkpoint, followed by the canonical AS0→ZI0→DI0 generated 150-class / exact-1,063,930-byte package route and local interpreter call.
- Retain the full P36 regression gate. If only clone fixtures change, cross-check every prior source hash, bundle manifest, and compiled fixture class hash against the retained full-run artifacts before reusing that gate.

## Test-only resource policy

Start clone-only EVM calls at 1,000,000,000 gas / 1,200 seconds per test attempt. If a measured test-only gas or wall budget is insufficient, double only that budget and rerun from a fresh report/world. The retained P36 suite starts at its preserved 2,000,000,000 gas / 2,400-second test-only profile. These are driver budgets, not changes to EVM charging or accepted runtime quotas.

## Worker completion boundary

Deliver source, fixtures, generator/driver, source proof, pins, and reproducible result summaries for independent parent review. Do not push or claim P37 parent acceptance, Minecraft execution, EULA acceptance, world generation, or `Done`.
