# Independent Review Verdict

## Verdict: ACCEPT

**Confidence:** 0.96

| Category | Score / 10 |
|---|---:|
| Correctness | 9.6 |
| Architecture understanding | 9.7 |
| Minimality | 9.8 |
| Robustness | 9.4 |
| Maintainability | 8.6 |
| Completion | 9.4 |

## Basis

1. **Narrow append-only runtime delta — pass.** `engine.diff` changes the P2 domain commitments, expands the bootstrap root from 85 to 86, appends TreeMap at slot 85, raises the prepared-class count by one, and adds only `java/util/TreeMap` to the reserved platform set (`engine.diff:43-93`). Final pins retain raw `30/262144`, frames 128, checkpoint 1 MiB, head 32768, 12 global natives, 14 exception kinds, and the existing limits commitment (`parent-pins.json:16-31`). Runtime is 386844 bytes, leaving 6372 bytes under 393216 (`parent-pins.json:45-49`; `machine-result.json:1`).

2. **Exact constructor-only Java 8 image — pass.** Independent in-memory decoding of `bootstrap/TreeMap.class.hex` found a 132-byte classfile, major 52, `ACC_PUBLIC|ACC_SUPER`, `java/lang/Object` superclass, zero interfaces, zero fields, and exactly one public `<init>()V`. Its five code bytes are `aload_0; invokespecial Object.<init>; return`. SHA-256 is `c203bc1cf3e4f7d9901b49f0415e10e0aa6331eb99c366e24f68b6fc2a60e067`, matching the pins and embedded bootstrap (`bootstrap/pins.json:2-9`; `engine.diff:103`). The construction fixture checks two distinct non-null objects and stable aliases (`tools/generate_fixtures.py:151-167`), under q1/q7/direct/reopen equivalence (`tools/gate.py:82-105,151-159`).

3. **Omissions remain honest — pass.** The class has no `Map`, `SortedMap`, `NavigableMap`, mutation, lookup, or provider API. Generated omission controls require `put` to refuse with `CallError(3,13)` and explicit `SortedMap` resolution to refuse as missing class (`tools/gate.py:217-238`), rather than producing fabricated Java values.

4. **Gate coverage — pass.** The design covers construction, no-use initialization, raw replacement, retained String/`lastIndexOf`/StringBuilder/System.err/failed-initialization behavior, raw count and byte boundaries, EnumSet, queue, OOM, reopen, and canonical receipt re-encoding (`tools/gate.py:72-105,108-215,240-317`). The authoritative result records 71 candidate worlds and 2606 canonical receipts, followed by a final P2 parent gate with the same 2606-receipt pass (`machine-result.json:1`).

5. **Final pins and original frontier — pass.** P2 engine/coordinator addresses and hashes agree across `coordinator.diff`, `driver.diff`, `parent-pins.json`, and `machine-result.json`. Optimizer 200, viaIR, Cancun, and metadata-off remain pinned (`parent-pins.json:32-43`). Original30 claims only 12005 Java/40 internal steps, lifecycle 1, 1715 canonical receipts, then atomic missing `org/apache/logging/log4j/util/ProviderUtil`; it explicitly disclaims provider result, world, and Done (`provider-util-blocker.json:1`; `verified-original30.json:1-12`).

## Findings

### Low — candidate helper scripts still identify P1

The archived `tools/build.py`, `tools/verify_source.py`, and gate summary retain `MC-TREE-MAP-P1` and P1 addresses (`tools/build.py:87-101`; `tools/verify_source.py:30-34`; `tools/gate.py:315`), while final pins are P2 (`parent-pins.json:5,29-30`). The authoritative machine result clearly separates the candidate and final parent builds/gates, and final P2 hashes cross-pin exactly, so this is **not an acceptance blocker**. It is a maintainability/traceability sharp edge: those helper scripts are candidate evidence, not a direct final-P2 rebuild recipe.

## Review Constraints

No heavy gate/build was rerun. No network, original artifacts, or other worktrees were accessed. Checks were limited to the supplied package, in-memory class decoding/hash verification, and cross-checking the supplied diffs, pins, scripts, and authoritative machine result.
