# Parent link-frontier correction and measured controls

Canonical review: JAVA_EVM_MC_LINK_FRONTIER_PARENT_PREFLIGHT.md. Original worker
9047772b2 integrated249bb6f0b; fresh original replay passed, but attribution was
wrong: checkcast is PC35 (null fast path); observed LinkError at38 is invokevirtual.
The original worker artifacts remain unchanged. Parent's separate CastEntry has
no invocation following the cast: null/missing returns61; nonnull/missing fails
at actual cast17; nonnull/present becomes ordinary Java ClassCastException kind8.
Separate Java8 TEST full/missing classpaths corroborate the null and value behavior.

Parent also preselects missing dependencies: SAME DemandEntry modes1/2 return51/52,
mode3 becomes guest NPE6, and missing-super/interface cases become normal return9.
This supports an eager-capacity comparison before deciding demand continuation;
it does not prove a dynamic loader necessary or sufficient for Minecraft.

Copied public-API driver checks failed receipts empty, no recreate/install, reopened
prior root, old published root/epoch/CP equality; full-width raw EVM refusal decoding.
Actual checkpoint bytes are hash checked, and positive/pending terminal reopens use
fresh processes. Final fresh15.961s/336994304B gate:97 distinct processes,59 CP-file
hash checks,66 Java calls, max8929319 ordinary gas. Accepted production unchanged.
final/ contains all real per-process JSON, reports, terminal/pending checkpoints,
cast/javap evidence and pin/regression/protected checks. No original server bytes.

surviving-early-drafts/ is read-only salvage of earlier worker files, with original
paths/hashes. Earlier outer logs/watchdogs seen during work no longer existed at
review. Exact earlier gate failures/outcomes are UNKNOWN; do not claim preserved
full transcripts or credit them as successful. Empty reports remain evidence.

Reproduce in NEW ignored build/java-diff-mc-link-frontier-* paths, scope TMPDIR
only to those outputs, never overwrite archive captures. No production code, quota,
ABI, core, general ClassLoader, original Java/Minecraft execution or implicit push.
