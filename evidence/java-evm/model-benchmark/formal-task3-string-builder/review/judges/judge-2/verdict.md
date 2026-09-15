# Independent Review Verdict — Bounded StringBuilder

## Verdict

**ACCEPT** `MC-STRING-BUILDER-P1` for its explicitly bounded scope: genuine guest `StringBuilder.<init>()V`, `append(String)`, and `toString()`, including the documented null-to-guest-NPE bound and unchanged LOCAL limits.

This is **not** acceptance of full Java SE `StringBuilder`, Minecraft startup, or `Done`.

**Confidence:** High (0.97)

## Scores

| Dimension | Score (0–10) |
|---|---:|
| Correctness | 9.6 |
| Architecture understanding | 9.7 |
| Modification minimality | 9.8 |
| Robustness | 9.3 |
| Maintainability | 9.4 |
| Completion | 9.6 |

## Findings by Severity

- Critical: **0**
- High: **0**
- Medium: **0**
- Low: **0**
- Informational: **2**

### INFO-001 — OOM evidence is correctly scoped

The StringBuilder-specific large-array witness is an **atomic checkpoint refusal**, not a catchable terminal receipt. Its live arrays exceed the unchanged 1 MiB checkpoint representation, so requiring `LC0StateError(1,0)` and an unchanged root is honest. The separate small field-arena case retains catchable guest-OOM coverage. This distinction must remain explicit; the large witness must not be cited as a successful catchable append-OOM execution. [gate.py:127-137](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/gate.py#L127-L137), [gate.py:233-244](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/gate.py#L233-L244), [machine-parent-recovery.json:1](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/machine-parent-recovery.json#L1)

### INFO-002 — Deliberately bounded Java surface

The image intentionally omits the broader Java SE hierarchy and API surface. Only the no-arg constructor, `append(String)`, and `toString()` are supported; null append raises guest NPE rather than appending `"null"`. This is pinned and tested, so it is not a defect within this task, but no broader compatibility should be inferred. [bootstrap-pins.json:2-8](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/bootstrap-pins.json#L2-L8), [verify_source.py:71-114](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/verify_source.py#L71-L114), [generate_fixtures.py:102-114](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/generate_fixtures.py#L102-L114)

## Review Assessment

### Guest behavior: pass

The pinned Java source:

- creates an owned empty `char[]` in the constructor;
- allocates a fresh exact-length array for each non-null append;
- copies old and input UTF-16 code units in order;
- returns the same receiver;
- constructs output through guest `String(char[])`.

The positive fixture checks empty/non-interned output, chained identity, ordered content, distinct outputs, and preservation of the earlier output. The null fixture checks catchable guest NPE. [verify_source.py:71-114](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/verify_source.py#L71-L114), [generate_fixtures.py:80-114](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/generate_fixtures.py#L80-L114), [gate.py:108-125](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/gate.py#L108-L125)

### Image85, prior84, and replacement: pass

The bootstrap root expands from 84 to 85 hashes; StringBuilder is appended at index 84 after PrintStream; the class-array count increases by one; and raw StringBuilder replacement is reserved. The exact reverse verifier recompiles the 542-byte Java 8 image, checks its hash and class shape, proves all prior 84 embedded images byte-identical, and requires StringBuilder only at the new final slot. [engine.diff:38-64](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/engine.diff#L38-L64), [engine.diff:124-140](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/engine.diff#L124-L140), [engine.diff:189-206](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/engine.diff#L189-L206), [verify_source.py:116-137](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/verify_source.py#L116-L137), [verify_source.py:211-227](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/verify_source.py#L211-L227)

### Post-VFS helper move: pass

The parent-amended helper is semantically safe:

1. The original tail body is removed at one call site and reproduced in the private internal helper without reordering.
2. `Program memory` and its nested memory array are reference types for an internal call, so writes to `p.classes`, `p.classClass`, and `p.loaderClass` remain visible to `_prepare`.
3. The original `classSlot` formula and Runnable conditional are unchanged.
4. The only semantic addition is the final `classSlot + 45` StringBuilder materialization.
5. The reverse verifier mechanically derives this layout from the pinned parent and requires complete source equality.

[engine.diff:65-120](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/engine.diff#L65-L120), [engine.diff:142-196](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/engine.diff#L142-L196), [verify_source.py:170-227](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/verify_source.py#L170-L227)

### Runtime pins, commitments, and limits: pass

The build pins solc `0.8.30`, optimizer runs 200, viaIR, Cancun, and metadata off. It builds the engine first, injects the resulting runtime Keccak into a disposable coordinator copy, then rebinds a disposable driver to both built runtime hashes. The runtime cap is enforced, while raw classes/bytes, checkpoint, frame, reserve, and related limits are asserted unchanged. Domain-separated runtime commitments are updated consistently. [build.py:22-55](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/build.py#L22-L55), [build.py:57-99](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/build.py#L57-L99), [engine.diff:3-34](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/engine.diff#L3-L34), [coordinator.diff:7-19](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/coordinator.diff#L7-L19), [verify_source.py:228-256](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/verify_source.py#L228-L256)

### Regression and transport evidence: pass

The generated gate covers q1/q7/direct equality and reopen, initialized/uninitialized behavior, replacement refusal, raw30/raw31 at driver/coordinator/engine layers, 262144/262145-byte boundaries, retained System.err/failed-init/EnumSet/ACC_ENUM/queue/OOM controls, and canonical ABI/event/checkpoint/counter/resource-read validation. [gate.py:72-106](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/gate.py#L72-L106), [gate.py:139-165](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/gate.py#L139-L165), [gate.py:175-244](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/gate.py#L175-L244), [verify_receipts.js:10-28](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/tools/verify_receipts.js#L10-L28)

The authoritative recovery record reports source verification pass, exact prior84 images, runtime-derived commitments, a 386100-byte runtime with 7116-byte headroom, and a passed generated gate with 1607 canonical receipts. [machine-parent-recovery.json:1](../../evidence/java-evm/model-benchmark/formal-task3-string-builder/review/machine-parent-recovery.json#L1)

## Lightweight Verification Performed

- Extracted the embedded class from `engine.diff`: **542 bytes**, SHA-256 `463d7859579627eff6065316f7c9759fb4648768c80ed29656e988db0a662832`, Java 8 classfile header.
- Normalized the diff and confirmed all **39 prior post-VFS operations** are preserved in identical order, with one final StringBuilder delegation added.
- Ran `javap` directly on the extracted packaged classfile; it confirmed one private `char[]` field and only `<init>()`, `append(String)`, and `toString()` with the expected allocation/copy/identity/guest-constructor bytecode.
- Validated the final verdict JSON syntax.

Per instruction, I did **not** run a build, generated gate, heavy test, original artifact, network access, or inspect another worktree.
