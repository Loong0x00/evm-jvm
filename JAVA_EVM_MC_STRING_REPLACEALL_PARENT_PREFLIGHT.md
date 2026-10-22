# P38 — bounded String.replaceAll parent acceptance

## Result

The unchanged original Minecraft 1.12.2 input, with the same90 authenticated raw classes /658,601 bytes, advanced from1,922,305 to **1,923,759 JVM instructions**,95 internal steps. **39 successful canonical checkpoint receipts** were independently verified. Fresh precise replay took765.901s. It remains in early bootstrap, before main argument processing, world preparation, EULA/configuration startup, listening, or `Done`.

Latest successful world: `build/java-diff-mc-string-replaceall-original90-parent-p38/official`.
Checkpoint:1,083,002 bytes, SHA256 `936e9e53347cbc63efb35a29b12b7c9a13782ef3fd44efc96f3795be79f9532e`, lifecycle1/epoch39. Only this authenticated RUNNING state, under the identical package/code, may continue. The next q1 call atomically refuses; no failed state was used.

## Implementation and independent build

Candidate preservation commit: `89ba868f2`, based on accepted P37 `a07dc7b2c`. Ordinary guest Java `String.replaceAll` delegates to `Pattern.compile(...).matcher(...).replaceAll(...)`. The bounded grammar supports BMP literals, escaped punctuation, literal classes/ranges/negation, and optional ASCII `(?i)`; replacement supports quoting and group zero. It implements leftmost non-overlapping and empty-match progress, no-match String identity, and real exceptions. Other valid regex syntax and surrogate-bearing matcher patterns/inputs explicitly refuse. This is not full Java regex/Matcher support and contains no original-caller/literal-specific filtering path.

Parent compilation independently reproduced:

- Engine414,732 bytes, SHA256 `f0959a98ba75f8f6bd013fc87a4a7ff633065d8d283f3857efde863b2fd313ef`.
- Bootstrap104, root `3896630440a69732a4acda4b8f5c5eec4898768ad074623b522a46a936efae4b`.
- Only prior leaves26/String and101/Pattern change; append103/Matcher. All other101 prior leaves, including PatternSyntaxException, are identical. String's prior source is unchanged except import/new wrapper; ordinary interpreter execution/native dispatch functions are unchanged from P37. Global operational natives21 and String bindings12 stay fixed.
- ABI/storage, eager normal heap arrays, packed checkpoint codec, raw150/1,063,930, runtime-artifact1MiB and checkpoint2MiB caps are unchanged. The derived diagnostic class bound is254, not an independent enlarged heap quota.
- `git diff --exit-code 95665d570 HEAD -- core/vm core/state params` and the working-tree protected-path diff are clean. No EVM opcode/gas/state/consensus change.

The oversized interpreter is LOCAL `StateDB.SetCode` preinstalled code executed through ordinary EVM Call, **not** a standard CREATE deployment. EIP-170/EIP-3860 were not disabled. Block/time remain1; receipts/checkpoints are not mined blocks.

## Generated testing: fresh parent work versus reused worker evidence

The worker's complete matrix had39 Java8 generated-only oracle cases. All q65536/q4096/q7/q1 schedules genuinely completed void after34,992 JVM /15 internal steps, with identical final machine/VFS roots and Pattern/Matcher heap. Call counts1/9/4,999/34,992. This complete run took4,189.546s, then its *post-run harness comparison* rejected the expected call-count ordering. Final worker v4 reused those same-source/same-input completed receipts after correcting that comparison; it did not freshly rerun the whole hour-long matrix. A refusal control also needed correction to resume successful q1 slices until the later unsupported call. Both histories remain preserved.

Parent independently verified exact engine/coordinator/root/fixture-byte pins, all reused terminal schedules/counters/heap, and reproduced the complete matrix's identical terminal state in **fresh q65536/q4096 EVM runs**. Parent also copied the worker q1 world/checkpoint and validated its installed code, Head and checkpoint through read-only EVM calls in a new process. The53,316-byte checkpoint SHA256 is `67a771608a6f46d3c9ce6c33ef3c003f99f8a41e2fb90afaf316d71d4efc3611`. This is independent provenance/reopen validation, **not a parent rerun of34,992 q1 calls**.

Fresh parent tests:

| Test | Explicit per-call budget | Measured seconds |
|---|---:|---:|
| Complete matrix q65536/q4096 + heap equality |16B gas |5.118 |
| Parent-owned replacement and `$0` fixture q7/q1,2,754 JVM steps |1B gas |119.389 |
| Unsupported regex/surrogate q1/q7 and raw Matcher refusal controls |16B gas |13.929 |
| Retained generic array.clone regression |1B gas |31.197 |
| Coordinator/AS0/ZI0/DI0 transport,3,224 calls |1B gas |16.931 |

Fresh process reopens passed for both parent schedules, retained clone, and copied worker q1. The small parent test's peak was42,649,848gas; coordinator peak243,790,533gas. Worker full retained P36 regression also passed at separately labeled2B/2,400s in1,118.896s; parent did not rerun that whole suite. Source/image invariants and fresh clone/coordinator checks supplement it.

**16B is test-only, not ordinary1B.** Full-matrix q65536 used12,295,643,615gas. Budget history distinguishes clean1B failure from earlier generated diagnostic2B/4B/8B probes;8B exhausted to the25M reserve.1,200/2,400s wall shortages and20,000-call shortage were preserved; full P38 allowance is16B/4,800s/40,000 calls, without changing retained P36/P37 budgets or EVM charging. Parent's original replay separately used authorized uint64.max external gas /60s watchdog, q≤65,536/internal4,096.

Parent harness failures (wrong fixture base path, missing custom reopen emission, missing fixture bundle) are also preserved. Corrections changed transport/test tooling only. A whitespace-only JSON correction and inherited historical pin-label correction are explicitly recorded.

## Genuine original return and next measured blocker

Original guest `a.c(String)String` returned from `replaceAll("[^a-z]", "")`. At the next original `a.<clinit>` PC628:

- Map receiver is real HashMap5980.
- Key is String5991 backed by char[5]5990 containing `black`; it is the lowercased source identity, since this first input has no rejected characters. This does **not** claim an original matched-character deletion; generated parent/worker tests exercise deletion.
- Matcher6000 links actual Pattern5999/input5991. Pattern's eager int[8]5997 contains `[PAT1,0,CLASS,1,1,97,122,END]` for the generic negated range.
- Value is original enum5706. Clone5989 still has22 shallow reference cells identical to source5970, with distinct normal eager arrays.
- All65,536 sine raw bits equal the accepted P37 read-only-oracle-verified table, SHA256 `87a67a39fff59636acb04edcda4ef622831037291f11fb61586c57596771dac2`.

Next atomic q1 error: **CallError(4,628)**, selector `0xd631c3a4`. An authenticated read-only EVM inspector on a copied successful world confirms original raw83/method15 `a.<clinit>`, PC628 `invokeinterface java/util/Map.put(Object,Object)Object`. The actual receiver is HashMap. Diagnostic deployment/state was not committed and the original world was not opened by that query. The initial non-instruction-boundary window failure is preserved. No host original class parser, host original Java, rewritten JAR, oracle input, or fabricated replacement result was used.

## Evidence and reproduction

- `evidence/java-evm/minecraft-entry/parent-string-replaceall/artifacts/map-put-blocker.json`
- `artifacts/source-proof.json`, `root-audit.json`, `worker-reuse-parent-audit.json`
- `artifacts/original-replaceall-return-proof.json`, `verified-original90.json`, ordered receipt hashes, q1 refusal
- `artifacts/evm-next-call-metadata.json` (diagnostic only)
- Worker histories: `pattern-compile-bootstrap/reference/string-replaceall-bounded/results/`

Parent scripts are scoped to `parent-string-replaceall/`: `rebuild.py`, `generated_gate.py`, `audit_worker_reuse.py`, `authorize_original.py`, `precise_replay.py`, `verify_original.js`, and `collect.py`. Generated gate run paths are intentionally fresh-only; choose new explicit paths before reproduction. The worker `run_gate.py UNIQUE_ID` supports a full no-reuse matrix run. Generated Java8 fixtures/oracles are test-only; original execution remains entirely in the authenticated EVM path.
