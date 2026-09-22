# Java-on-EVM Minecraft raw70 / byte464925 preparation

## Measured dependency
Accepted `parent-629078bb6` genuinely executes bounded String.toLowerCase(Locale.ROOT), reaches87461J/79I, then q1 reports `MCEntryMissingClass(4107,48,org/apache/commons/lang3/Validate)`. Parent-only fresh EVM ZI0/DI0 measurement authenticated `org/apache/commons/lang3/Validate.class`: 15021 bytes, SHA-256 `693e978d1fb2e06708fe93f2f04e479401ec2458abaadd35c0a12533218dea23`. The canonical raw69 engine refused LinkError(1,70), committed no engine checkpoint, and the failed-call root remained unchanged. Parent replay is deferred.

## Required capacity-only delta
Raise raw classes 69→70, total raw class bytes449904→464925, diagnostic class bound165→166. Update coordinator fixed arrays/constructor bounds and driver declarations consistently. No semantic/interpreter/bootstrap/native/String/Locale change. Preserve bootstrap96 ordered root `39b4e365255c15cdf1de704a264e35b2574c77e653a72718a9a9861a76ad7f18`, String 1836B SHA-256 `259bed03edf8602dca9ad26e639cb7668b8da38d62422b80788d8339020017fe`, Locale 285B SHA-256 `8401495628aed9de6e7c7c0ad56f73ac563bd5e7a892b8eb8ca9fcf91bc03e31`, Map$Entry, Integer, global native16 and String-local12 exactly. Runtime<=393216 (prior379383).

## Gate
Generated-only exact 70/71 and464925/464926 boundaries; q1/q7/direct/reopen positives plus retained lower-case/Locale/String/Map/Integer controls; full DI0 reads; atomic existing refusal with no committed checkpoint/head when engine cannot commit; source-only capacity delta; independent fixed image/root commitments; canonical receipts; whole gate<=1200s; durable results/SHA256SUMS and clean commit. No original/JAR/class/resource/network access, other worktrees, provider/world/EULA/Done claim, push, review/delegation, or Fast.
