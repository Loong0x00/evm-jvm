# Independent Review Verdict — Bounded StringBuilder

## Verdict

**ACCEPT** — **high confidence (0.93)**.

The parent-amended package is internally coherent and satisfies the bounded task. The authoritative record reports passing source verification and generated gates, 1,607 canonical receipts, exact preservation of the prior 84 images, runtime-derived commitments, and a 386,100-byte engine under the 393,216-byte cap. It correctly makes no Minecraft/Done claim. [machine-parent-recovery.json:1](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/machine-parent-recovery.json#L1)

## Scores

| Category | Score / 10 |
|---|---:|
| Correctness | 9.5 |
| Architecture understanding | 9.6 |
| Modification minimality | 9.5 |
| Robustness | 9.0 |
| Maintainability | 9.1 |
| Completion | 9.5 |

## Findings by Severity

### Critical / High / Medium

None.

### Low — L-01: Python checks rely on assertions remaining enabled

The Python evidence tools encode many acceptance checks as `assert`. That is valid for the reported normal invocation, but a future `python -O` or inherited `PYTHONOPTIMIZE` run could suppress checks. This does not invalidate the authoritative run; a small hardening would explicitly reject optimized Python or use unconditional checks. [build.py:15-18](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/build.py#L15-L18) [build.py:38-55](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/build.py#L38-L55) [gate.py:23-32](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/gate.py#L23-L32)

### Informational — I-01: exact scope of the quota/OOM evidence

The large StringBuilder fixture cannot publish its live arrays within the unchanged 1 MiB checkpoint cap. The amended gate therefore correctly requires atomic `LC0StateError(1,0)` and an unchanged root, rather than claiming a caught terminal result. Catchable guest OOM remains demonstrated by the smaller independent field-arena fixture. This is honest, but the result must not be described as proving that the large second append completed and caught OOM. [generate_fixtures.py:126-142](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/generate_fixtures.py#L126-L142) [gate.py:127-137](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/gate.py#L127-L137) [gate.py:233-244](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/gate.py#L233-L244)

### Informational — I-02: explicit bounded null behavior

`append((String) null)` yields a catchable guest `NullPointerException` before destination allocation rather than Java SE's `"null"` text. The pin, implementation, fixture, and gate all disclose and enforce this bounded-profile divergence. [bootstrap-pins.json:2-8](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/bootstrap-pins.json#L2-L8) [verify_source.py:86-100](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/verify_source.py#L86-L100) [generate_fixtures.py:102-114](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/generate_fixtures.py#L102-L114)

## Technical Assessment

### Guest StringBuilder semantics

The exact pinned Java source:

- constructs an owned empty `char[]`;
- allocates a fresh exact-length array for each non-null append;
- copies old and appended characters in order;
- stores the fresh array and returns `this`; and
- constructs a new guest `String` from the current array in `toString()`.

The positive fixture checks empty/nonempty content, append receiver identity, ordering, non-interned/copy identity, and preservation of an earlier `toString()` snapshot after a later append. [verify_source.py:71-103](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/verify_source.py#L71-L103) [generate_fixtures.py:80-100](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/generate_fixtures.py#L80-L100) The verifier recompiles with Java 8 settings, checks classfile major 52, size 542, exact SHA-256 and exact class hex. [verify_source.py:104-137](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/verify_source.py#L104-L137)

### Image 85 and prior-image preservation

The bootstrap-root vector grows from 84 to 85 and folds StringBuilder only at index 84. Program capacity grows by exactly one. [engine.diff:41-64](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/engine.diff#L41-L64) StringBuilder is reserved against raw replacement. [engine.diff:124-130](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/engine.diff#L124-L130)

The strict reverse verifier requires 84 parent functions and 85 amended functions, byte-compares every parent image, and permits only the new StringBuilder image. It also requires the final assignment and unchanged fixed constants. [verify_source.py:211-234](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/verify_source.py#L211-L234)

### Safety of the post-VFS helper move

The helper refactor is semantically safe:

1. The verifier mechanically extracts the complete parent post-VFS assignment tail, inserts only the final StringBuilder assignment, moves that body into the helper, and then requires exact amended-source equality. [verify_source.py:170-209](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/verify_source.py#L170-L209)
2. The original `classSlot` formula and all offsets through PrintStream `+44` remain in the same order; StringBuilder is appended at `+45`, followed by the unchanged `classClass` and `loaderClass` assignments. [engine.diff:142-196](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/engine.diff#L142-L196)
3. `Program memory` and its memory array are reference types across private internal Solidity calls. Thus writes to `p.classes`, `p.classClass`, and `p.loaderClass` update the caller's same in-memory Program. The helper is `private pure`; it adds no ABI boundary, storage transition, external call, or reentrancy point.
4. The generated q1/q7/direct/reopen checks compare machine roots, opaque payload hashes, JVM steps, and internal steps, while canonical receipt verification checks runtime pins, checkpoint hashes, epochs, events, counters, read ranges, gas, and timeout bounds. [gate.py:72-106](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/gate.py#L72-L106) [verify_receipts.js:10-28](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/verify_receipts.js#L10-L28)

### Runtime commitments and retained limits

The build pins solc 0.8.30, optimizer runs 200, viaIR, Cancun, and metadata-off, then derives the engine hashes from the built runtime, patches the coordinator's engine pin, and finally rebinds the disposable driver to both built hashes. [build.py:25-55](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/build.py#L25-L55) [build.py:57-99](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/build.py#L57-L99)

The gate retains raw30, three-layer raw31 refusal, exact 262144-byte admission, 262145-byte rejection, System.err, failed initialization, EnumSet/ACC_ENUM, queue, and catchable OOM controls; replacement refusal includes StringBuilder. [gate.py:139-244](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/gate.py#L139-L244)

## Review Verification

Performed only lightweight package review:

- manually reviewed the task, diffs, pins, authoritative record, and all supplied tools;
- parsed all five Python tools with `ast.parse`;
- parsed both JSON records;
- ran `node --check` on `verify_receipts.js`.

Per instruction, no heavy gate/build was rerun and no original artifact, network resource, or other worktree was inspected.
