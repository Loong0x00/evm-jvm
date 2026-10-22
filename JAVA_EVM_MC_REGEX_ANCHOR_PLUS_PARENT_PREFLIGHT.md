# P42 — parent-corrected bounded regex anchors/plus acceptance

## Genuine original result

A fresh unchanged original114-class /801758-byte run completed the previously blocked `Pattern.compile("^[a-z0-9_]+$")`. Original `awu.<clinit>` stored real Pattern8246 backed by eager int[14]8244:

```text
[PAT2,0,1,1,4,0,3,97,122,48,57,95,95,0]
```

The source expression is compiled as generic start/end anchors plus a greedy positive repetition of one character-class atom. It is not a caller-specific validator or host result. Generated tests also execute real `Matcher.matches` and `replaceAll` over other admitted patterns.

Latest precise original: **2223741 JVM instructions /111 internal steps**,45 verified canonical successful checkpoint receipts, epoch45/lifecycle1; checkpoint1282836B SHA256 `87bc05265855254e8c01b2b88f9e08b789b1b090e58c325318fc4d98a29cb23a`. Fresh discovery640.836s plus same-package precise continuation603.874s. World: `build/java-diff-mc-regex-original114-parent-p42-fixed/official`.

Next exact q1 is authenticated `MCEntryMissingClass`, name **com/google/common/base/Function**, site4098/context108. No original P41 checkpoint, terminal state or failed-call output was migrated into this P42 run. Still no main argument processing, world preparation, accepted EULA/configuration startup, listening or Done claim.

## Independent review corrections

Worker candidates5992b5d00 andd135b2c5 were **not accepted**. Parent-generated stock-Java8/custom-image comparisons found:

1. Candidate5992 missed admitted plus/end-anchor matches when the atom consumed CR but not LF of a final CRLF. It also invented PatternSyntaxException for valid but unsupported quantified zero-width anchors (`^+`, `^*`, `^?`, `^+$`).
2. Candidate d135 fixed those cases, but its endpoint retry also affected fixed-width patterns: `^x\r$` wrongly replaced `x\r\n`.
3. Parent's final correction restricts that one-CR retry to PAT2 plus opcodes3/4 only, preserving min1. Fixed-width tokens never backtrack. Matcher revalidates mutable CharSequence input for surrogates before each operation.

Both worker commits, worlds/failures and original review fixtures remain preserved in the worker worktree/branch. Main integrates scoped source, generated fixtures and selected reports, not thousands of transient DB files or the cached ELF binary. Parent final Java8 differential has **0 admitted mismatches across60 cases**;20 valid-outofsubset cases explicitly raw-refuse, not an oracle-equality/full-regex claim. Parent's separate small/matrix fixtures passed stock and custom Java8, then genuine EVM tests.

## Bounded semantics and source/build proof

Admitted: old fixed-width PAT1 literals/classes/ranges/negation; optional ASCII `(?i)`; optional leading`^`/trailing`$`; and greedy `+` only on the sole literal or class atom. PAT2 contains real private eager int[] words. `$` recognizes Java8 final LF/CR/CRLF/NEL/LS/PS boundaries; matches requires whole-region consumption. Existing replacement escapes/$0, no-match identity and empty-match advancement are retained. Other valid regex syntax and surrogate text remain explicit profile refusals. This is not full regex/Matcher support.

Parent independently compiled the frozen13-file P41 baseline and current four Java sources, verifying exact baseline materializer correspondence. String/PSE remain byte-identical. Parent reconstructed all105 actual ordered leaves: only Pattern101 and Matcher103 change; other103 remain fixed.

- Runtime421118B SHA256 `be1b8b7606fd9b095fecdf46a9a20e1a10d695fc229e7f8d7ad89973a89cab94`, Keccak `73c5c366f6fbcb51f6cec238c206410d7d17da6de78c9f304ce0c3c12e0322e5`.
- Coordinator5411B SHA256 `ea78a31d4f8a5df30f04d9f5f4a324ccddead61db6bf3d10d09861e6ab693a55`.
- Bootstrap root `bfb007b494bdf84191396b03e8fd1b69a70a4d034a22d4fdb2fb1c08e1b0c26b`.
- Only two image bodies change in interpreter source; coordinator changes only authenticated engine codehash. ABI/storage, dispatch/native handlers, clone/heap/codec/schema unchanged.
- All quotas fixed at P41: arrays8192,objects4096,elements262144,handles12545,raw150/1063930,CP2MiB,runtime-artifact1MiB,frames128,quantum65536/internal4096,native21/String12.

Actual protocol-domain strings intentionally remain P41. New runtime codehash and actual changed bootstrap root authenticate this P42 library revision; no old code/package checkpoint migration is allowed. Friendly P42 metadata does not pretend a domain-string rewrite occurred.

## Fresh parent EVM tests and budgets

| Fixture | Quantum | Genuine void JVM steps | Explicit budget |
|---|---:|---:|---:|
| Parent small: anchored names, min1, case rejection, CRLF backoff, old replacement |q7/q1 |8321 /8321 |1B each |
| Parent matrix: all final terminators, fixed-width no-backoff, literal CR plus, greedy/$0, ASCII flags, empty anchors, no-match identity |q4096/q65536 |45316 /45316 |**separate32B allowance** |

Both pairs match exact final machine/VFS roots, counters and audited heap and pass new-process EVM checkpoint/code/Head validation. Small pair411.535s, peak62068610gas. Matrix pair6.821s, peak21953256621gas; q4096 peak829646847gas. Parent preserved1B/2B/4B/8B/16B coarse-matrix shortages before fresh32B success. **This larger parent matrix is not the worker's8B workload, and neither is ordinary1B success.** Canonical product1B, generated overrides and original authorized uint64.max/60s transports remain separate; EVM pricing is unchanged.

Fresh parent1B refusal controls passed in6.270s: valid-outofsubset `^+`, post-matcher surrogate mutation, and raw Pattern/Matcher namespace substitution. Refusals are typed CallError/BootstrapProfileError with unchanged latest successful Head/root, never invented Java PSE or fake false. Worker q1 outer1200s timeout followed by successful-checkpoint continuation is recorded as such; parent small q1 is a separate fresh run, not reuse of that long matrix.

All65536 sine raw bits still match the accepted read-only-oracle-verified table. Protected geth core/vm/core/state/params remain equal to base95665d570. Oversized engine is LOCAL StateDB.SetCode preinstalled code invoked through ordinary EVM Call, not standard CREATE deployment. EIP170/EIP3860 and consensus/gas remain intact; fixed block/time1 and checkpoints are not mined blocks.

## Evidence

`evidence/java-evm/minecraft-entry/parent-regex-anchor-plus/artifacts/guava-function-resource-blocker.json`, `original-pat2-compile-return-proof.json`, all105 root/image audit, fresh Java8 differential, finite-budget failures, q1/q7/matrix/reopen/refusal records, original45 receipt hashes/Head/q1 refusal. Rejected-counterexample evidence is under `review/` and `review/d135/`.

Current source: `regex-anchor-plus-bounded/`; historical worker metadata is labeled separately. Parent `rebuild.py` performs fresh Java/Solidity/Go builds while preserving all intermediates. `generated_gate.py`, `refusal_gate.py`, `replay_original114.py`, `verify_original.js`, `collect.py` preserve test/original roles. Precise continuation now explicitly avoids quantum regrowth after a discovery refusal; earlier runs' first continuation calls already refused, so that latent wrapper issue did not change their schedules.
