# P38 bounded `String.replaceAll`

## Status and boundary

This is the P38 worker implementation/evidence record, based only on the authorized P37 source-only snapshot at `evidence/java-evm/minecraft-entry/string-replaceall-source-base-p37/` (`a07dc7b2c`, source-manifest SHA-256 `861696c7dfc0dcb0c5661c749c221a25c77e6d1b75d8fc8b3849d5d5a115e0f4`). No original Minecraft JAR/class/resource, world, checkpoint, receipt, binding list, or other-worktree evidence was inspected. No Minecraft process was run.

The candidate is a LOCAL preinstalled-code `runtime.Call` profile, not standard CREATE/EIP-170 deployment compatibility. It does not change core EVM gas accounting, consensus, accepted budgets, ABI/storage protocol, or operational native bindings. Parent integration/acceptance remains separate from this worker gate.

## Implementation

- `String.replaceAll(String,String)` delegates through Java guest `Pattern.compile(regex).matcher(this).replaceAll(replacement)`.
- Pattern matching is bounded to optional leading `(?i)` (ASCII-only case folding), BMP literals, escaped punctuation, positive/negated BMP literal classes, and inclusive ranges. Matching is Java-style leftmost/non-overlapping. Unsupported otherwise-valid regex syntax refuses through the deliberately unbound profile branch; malformed syntax raises guest `PatternSyntaxException`.
- Matcher replacement supports literal text, backslash quoting, `$0`, and Java-compatible `$00`/`$01` group-zero handling. Since the admitted grammar has no capturing groups, `$1`..`$9` raise the ordinary guest index exception and named-group syntax raises the ordinary guest argument exception. A no-match result preserves source identity; a matched result owns a new String even if its text equals the input. Empty-pattern progress and null/invalid-replacement cases are covered by generated Java 8 oracle fixtures.
- Surrogate-bearing matcher patterns/inputs are conservatively refused; this is not supplementary-code-point regex support.
- Only one bootstrap image is appended: `java.util.regex.Matcher` at P38 slot 103. The final bootstrap count is 104. P37 order is retained; only prior slots 26 (`String`) and 101 (`Pattern`) change; `PatternSyntaxException` remains byte-identical. Operational global-native count remains 21 and String-local binding count remains 12; P38 adds no native binding.
- The raw platform `Matcher` fixture is refused. The guest Matcher is intentionally minimal; it does not claim `find`, capture/group APIs, append operations, or full Java regex/Matcher compatibility.

## Independent limits

The candidate is pinned in `pins.json`: engine runtime 414,732 bytes (SHA-256 `f0959a98ba75f8f6bd013fc87a4a7ff633065d8d283f3857efde863b2fd313ef`, Keccak `c1b3d9995ca626aff790ff721fe23a2dcd64538c69c1cfa7ff1866bc0da65ce8`); coordinator runtime 5,411 bytes (SHA-256 `c21f48b7cd43e5f28c1f148cd6ad13bf00aa5950bf54aa4e3b5336e42941dc84`); bootstrap root `3896630440a69732a4acda4b8f5c5eec4898768ad074623b522a46a936efae4b`. The runtime and checkpoint ceilings remain 1 MiB and 2 MiB respectively; raw package limits remain 150 classes / 1,063,930 bytes, with the 254-class diagnostic bound. None is a claim about stock CREATE deployment.

P38 test-only allowances were coherently doubled from measured insufficiency without changing EVM rules or P36/P37 budgets: per-call gas selected 16,000,000,000 (the final clean q65536 matrix used 12,295,643,615 in its single call; the clean 1B probe and earlier generated 2B/4B/8B diagnostic probes failed; the diagnostic 8B call used 7,975,559,063 and left 24,440,937, below the 25M reserve); wall selected 4,800 seconds (1,200 and 2,400 timed out); and P38-only continuation calls selected 40,000 (the prior 20,000 driver ceiling stopped the q1 matrix before terminal). P37/retained test ceilings remain 1B ordinary gas, 20,000 driver continuation calls, and the retained P36 suite remains 2B / 2,400 seconds. These are harness allowances, not modified interpreter/consensus limits. Measurement and interruption details plus the exact generated gas-probe classfiles/manifests/failure records are preserved in `results/p38-final-v1/measurement-record.json` and `results/p38-final-v1/gas-probes/`.

## Verification

`results/p38-final-v4/` contains the final fresh source build, fixture manifest, source proof, run manifest, and durable P38 summary/control/reopen receipts. The generated fixture/oracle build has 75 cases, 150 raw classes / 27,018 bytes for the exact raw-150 control, 1,063,930-byte exact envelope and 1,063,931-byte over-limit refusal, diagnostic maximum 254, and 39 host-oracle cases. All P38 Java 8 host oracles passed.

The completed P38 EVM schedules used identical final machine/VFS roots, Java/internal step totals, and audited Pattern/Matcher heap at q=1, 7, 4,096, and 65,536. The terminal is genuine `void` (`lifecycle=outcome=2`, Java kind 0), 34,992 Java steps / 15 internal steps; Matcher links are valid (32 Matcher and 33 Pattern objects); q schedule call counts are 34,992 / 4,999 / 9 / 1. The 53,316-byte q1 checkpoint reopened and validated in a distinct OS process. Four unsupported-regex/surrogate q1/q7 controls reached the later unbound call after successful running checkpoints, then proved the failed call left the last running Head and state root unchanged; the raw platform Matcher replacement was atomically refused.

The first complete q schedule run (`p38-final-v2`) emitted all four successful terminal receipts, then failed only because a post-schedule harness inequality was reversed (it rejected the expected fact that larger quantum uses fewer calls). That comparison was corrected and independently applied to the cached complete receipts. To avoid replaying the 4,189-second q1 schedule, final run `p38-final-v4` verified exact engine/coordinator hashes, bootstrap/source proof, fixture-manifest hash, all four schedules and their roots/heap/monotonic call counts; it then ran a current-driver fresh-process reopen and all fresh refusal controls. The run also passed the ArrayClone gate (1B/1,200s), retained P36/P37 gate (2B/2,400s), and coordinator route (2B/2,400s). Source proof confirms 101 unchanged prior leaves, changed prior slots 26/101, 104 bootstraps, no original execution, and no new operational native bindings.

The refusal harness was also corrected after the first control attempt (`results/p38-final-v3/run-progress.json`) assumed q1 errors happen in the first EVM call. The final q1/q7 control now resumes successful running checkpoints until the unsupported native call, then asserts rollback against the latest committed Head; the failed EVM call is never continued.

Important durable records:

- Final run: `results/p38-final-v4/run-summary.json` (SHA-256 `8d339b57de75111f6b0ce146319b51956e51a768d6da5c0c8256172b5519855b`).
- Fresh source proof: `results/p38-final-v4/source-proof.json` (SHA-256 `6f4dc6c10757e18107fbf36eb87e644a3cc650bf1ff491f3c3c784d2ff1cd8de`).
- P38 matrix/schedule provenance and corrected cross-quantum check: `results/p38-final-v4/string-replaceall-attempt-1/reused-schedule-summary.json` (SHA-256 `4c27335f2f7337f2a65c94a89c2f2693397a9fa43d1b8867b79b8ae50aaef6da`); original complete EVM schedule report is beside it as `schedule-source-gate-failure.json` and records the harness-only failure.
- Fresh refusal controls: `results/p38-final-v4/string-replaceall-attempt-1/controls-summary.json` (SHA-256 `44e30f8ebedbe36fd21d3524983eb2f8f200e6fcc1fcf4c0eb983a6378ae0b18`).
- Distinct-process checkpoint reopen: `results/p38-final-v4/string-replaceall-attempt-1/reopen-summary.json` (SHA-256 `fd1e9c0f1c8abd5e26b94b656e911bfef5cad8796425519cc4a2505e08416dd8`).
- Build-generated fixture manifest: `results/p38-final-v4/fixture-manifest.json` (SHA-256 `bfc8e0428a12509370151504a0a22471b489f3bf193725b91ba6d60213e4a5df`).
- Budget measurements / outer-tool interruption: `results/p38-final-v1/measurement-record.json`.
- Comparator-only schedule failure: `results/p38-final-v2/string-replaceall-attempt-1/gate-failure.json` (SHA-256 `45672afced87f9c8f20d5701959b4cd056081d9cbfa613ac30a05285af965a4f`).

## Reproduction

Run from the repository root with a fresh unique run ID. A no-reuse run rebuilds the engine and coordinator, regenerates Java 8 fixtures, replays all P38 schedules, performs fresh reopen, refusal controls, and retained gates. It is expected to take over an hour because q1 persists/reopens every one of 34,992 slices.

```sh
PYTHONDONTWRITEBYTECODE=1 \
NODE_PATH="$PWD/jvmevm/runtime/node_modules" \
GOPROXY=off GOSUMDB=off GOTOOLCHAIN=local \
python3 evidence/java-evm/minecraft-entry/pattern-compile-bootstrap/tools/string-replaceall-bounded/run_gate.py p38-repro-unique
```

Build/source-proof-only command:

```sh
PYTHONDONTWRITEBYTECODE=1 NODE_PATH="$PWD/jvmevm/runtime/node_modules" \
python3 evidence/java-evm/minecraft-entry/pattern-compile-bootstrap/tools/string-replaceall-bounded/build_candidate.py build/java-diff-mc-string-replaceall-bounded-build-proof
```

No Minecraft, EULA acceptance, client/server readiness, or World/Done claim is included.
