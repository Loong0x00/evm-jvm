# Independent verdict: ACCEPT

**Confidence:** High (0.94). Acceptance is for the bounded `MC-STRING-BUILDER-P1` slice only. It is not a full Java `StringBuilder` or Minecraft/Done claim.

## Scores

| Dimension | Score / 10 |
|---|---:|
| Correctness | 9.4 |
| Architecture understanding | 9.6 |
| Modification minimality | 9.5 |
| Robustness | 9.2 |
| Maintainability | 9.1 |
| Completion | 9.4 |

## Findings by severity

- **Critical / High / Medium / Low:** None.
- **Informational — quota witness scope:** The large StringBuilder case cannot publish a terminal catchable-OOM result because its live 65536-char arrays exceed the unchanged 1 MiB checkpoint. Requiring atomic `LC0StateError(1,0)` with `rootUnchanged` is honest. The separate retained field-arena case remains the catchable guest-OOM proof; the large case must not later be described as one. [`tools/gate.py:127-137`, `tools/gate.py:233-244`, `tools/generate_fixtures.py:126-142`, `machine-parent-recovery.json:1`]
- **Informational — explicit null bound:** `append(null)` deliberately throws guest NPE before destination allocation instead of appending `"null"`. This is clearly pinned and tested, so it is a bounded-profile constraint, not a defect. [`bootstrap-pins.json:2-8`, `tools/verify_source.py:75-100`, `tools/generate_fixtures.py:102-114`, `tools/gate.py:116-117`]

## Review assessment

### Guest behavior

The pinned guest source is ordinary Java bytecode, not a native shortcut: construction owns an empty `char[]`; each non-null append allocates an exact-length array, copies old content then input content, updates the field, and returns `this`; `toString()` calls guest `String(char[])`. The generated positive checks empty and appended content, receiver identity, non-interned output, distinct output objects, and preservation of an earlier result after later mutation. [`tools/verify_source.py:71-137`, `tools/generate_fixtures.py:80-100`, `tools/gate.py:108-125`]

### Image 85, prior images, and replacement

The bootstrap commitment array grows exactly from 84 to 85 and runtime-folds `_bootstrapStringBuilder()` at `h[84]`; Program capacity grows by one and raw replacement is reserved. The strict reverse verifier requires all 84 parent image bodies to remain byte-identical and permits only the new 542-byte image. [`engine.diff:41-64`, `engine.diff:124-130`, `tools/verify_source.py:139-168`, `tools/verify_source.py:211-227`]

### Post-VFS helper move

The helper move is semantically safe:

1. The same `classSlot` expression, conditional Runnable insertion, prior assignments, `classClass`, and `loaderClass` remain in the same sequence.
2. StringBuilder is the sole added assignment, at final `classSlot + 45`.
3. `Program memory` and its memory array are reference types across an internal Solidity call, so the helper updates the caller's memory graph; there is no external call, reentrancy point, or storage transition.
4. The reverse verifier derives the helper body wholesale from the accepted parent tail and then exact-compares the complete engine source. [`engine.diff:65-123`, `engine.diff:136-196`, `tools/verify_source.py:170-209`]

My package-only comparison independently found all **39** pre-existing executable tail statements unchanged and in order.

### Toolchain, commitments, and retained limits

The build pins solc 0.8.30, optimizer 200, viaIR, Cancun, and metadata off; it derives the built engine/coordinator hashes before rebinding disposable build copies. Runtime, raw-class/byte, checkpoint, frame, reserve, and diagnostic bounds remain asserted. [`tools/build.py:25-55`, `tools/build.py:57-98`, `tools/verify_source.py:228-248`]

The gate covers q1/q7/direct/reopen equivalence, initialization/no-init, replacement, raw30, raw31 at all three layers, 262144/262145 bytes, retained System.err/PrintStream, failed initialization, EnumSet/ACC_ENUM, queue, OOM, and canonical public receipts. [`tools/gate.py:96-106`, `tools/gate.py:139-249`, `tools/verify_receipts.js:10-28`]

The authoritative parent recovery reports source verification and generated gate pass, 1,607 canonical receipts, and a 386,100-byte engine under the 393,216-byte cap with 7,116 bytes headroom. It explicitly makes no Done claim. [`machine-parent-recovery.json:1`]

## Verification performed

No heavy tests or original artifacts were used. I only:

- parsed the five packaged Python tools with `ast.parse`;
- ran `node --check` on `tools/verify_receipts.js`;
- extracted the embedded class hex and independently confirmed **542 bytes** and SHA-256 `463d7859579627eff6065316f7c9759fb4648768c80ed29656e988db0a662832`;
- compared the deleted and helperized tail statement sequences.

The full build/gate was not rerun, as required; `machine-parent-recovery.json` was treated as authoritative.
