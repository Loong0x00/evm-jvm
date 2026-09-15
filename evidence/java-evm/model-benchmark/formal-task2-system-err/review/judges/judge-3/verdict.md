# Independent System.err Acceptance Review

## Verdict

**ACCEPT** — high confidence (**0.97**).

The parent-amended change supports the exact measured `java/lang/System.err:Ljava/io/PrintStream;` access through ordinary guest class initialization. The delta is tightly constrained to a fresh domain/address, the one System replacement, the appended constructor-only PrintStream image, its reservation, and required count changes. Machine facts establish the runs=200 runtime fits the unchanged LOCAL384 cap and that the generated gate passed.

## Scores

| Category | Score / 10 |
|---|---:|
| Correctness | 9.6 |
| Architecture understanding | 9.8 |
| Modification minimality | 10.0 |
| Robustness | 9.3 |
| Maintainability | 9.4 |
| Task completion | 9.7 |

## Findings by severity

### Critical

None.

### High

None.

### Medium

None.

### Low

**L-001 — The failed-initialization control is generic, not a forced failure inside `System.<clinit>`.**

The gate proves unused System/PrintStream are not preinitialized, and separately verifies catchable first-use and subsequent-use initialization failure with generated `Broken`. It deliberately asserts System remains untouched. Thus it does not force a quota or other failure partway through the shipped System initializer. This is residual coverage risk, not a blocker: the initialization machinery is unchanged by the exact reverse-verified source delta, while successful System initialization is exercised under q1/q7/q4096 and reopen.

Citations: `tools/gate.py:119-134`; `tools/generate_fixtures.py:80-103`; `tools/verify_source.py:226-280`; `machine-parent-result.json:13-17`.

### Informational

**I-001 — Scope is intentionally field-only.**

The appended PrintStream has only `()V`; output, `print`, and `println` are omitted and explicitly not claimed. This matches the task.

Citations: `engine.diff:83-88`; `tools/verify_source.py:149-164`; `tools/gate.py:219-221`.

## Acceptance basis

- **Genuine guest initialization:** The pinned System class declares `public static final err` with the exact descriptor and its guest `<clinit>` executes `new PrintStream()`, then stores the reference. PrintStream has ordinary guest constructor Code calling `Object.<init>`; no native or host construction path was introduced. The probe rejects null/identity drift and performs a typed constructor/field handoff. The checkpoint gate requires System and PrintStream initialized and the err slot nonzero. Citations: `bootstrap-pins.json:2-15`; `engine.diff:83-88`; `tools/verify_source.py:118-176,195-224`; `tools/generate_fixtures.py:61-78`; `tools/gate.py:108-117`.
- **Exact bootstrap preservation:** The reverse verifier pins accepted parent inputs, constructs the only allowed source transformation, and requires exact equality. It proves 83 images become 84, all 82 unaffected images remain byte-identical, System remains root slot44, EnumSet remains slot82, and PrintStream appends at83. Citations: `tools/verify_source.py:110-116,226-280`; `engine.diff:38-78`.
- **Minimal coordinator/driver changes:** These remain exact parent transformations limited to the new fixed engine address and equal-length domains; product bounds are unchanged. Disposable build copies alone receive runtime-derived engine/coordinator hashes and size literals. Citations: `coordinator.diff:7-19`; `driver.diff:3-44`; `tools/build.py:50-86`; `tools/verify_source.py:282-306`.
- **Limits and commitments:** Exact parent-source preservation plus explicit checks retain raw30/262144, frames128, checkpoint1MiB, path/transfer bounds, 25M reserve, 12 native bindings, and 14 exception kinds. The new bootstrap hash is runtime-derived; no candidate-specific `DLIMITS` or `DBOOT_PRINTSTREAM` shortcut exists. The authoritative runs=200 runtime is 392775 bytes, leaving 441 bytes under 393216. Citations: `tools/verify_source.py:224-280`; `tools/build.py:38-61,88-105`; `machine-parent-result.json:11-16`.
- **Negative and retained controls:** Raw System and PrintStream replacements refuse atomically. Raw30 executes; raw31 is rejected at driver, coordinator, and engine layers. Exact/+1 byte boundaries, EnumSet/ACC_ENUM and failure cases, queue, and OOM are retained. Citations: `tools/gate.py:136-213`; `machine-parent-result.json:17`.
- **Receipt integrity and honest claims:** Successful receipts are checked against pinned code hashes, checkpoint roots, canonical nested ABI/events, counters, bounds, and decoder read ranges. Machine facts report 1086 canonical receipts. Original30 advances only to the next StringBuilder blocker and remains RUNNING; Minecraft Done is explicitly not claimed. Citations: `tools/verify_receipts.js:10-28`; `machine-parent-result.json:17-19`.

## Verification constraints

No heavy build or EVM replay was run. No original JAR, class, resource, or world was accessed. A lightweight in-memory classfile check confirmed both added byte lengths/SHA-256 pins, the exact System err flags/descriptor, and constructor bytecode shape. Runtime, compiler, receipt, and original30 execution facts are accepted from `machine-parent-result.json` as authoritative.
