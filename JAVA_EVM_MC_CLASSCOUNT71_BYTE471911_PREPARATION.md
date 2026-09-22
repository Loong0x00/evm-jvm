# Java-on-EVM Minecraft raw71 / byte471911 preparation

## Measured dependency
Accepted `parent-c87464056` genuinely executes System.identityHashCode(Object), reaches87528J/79I, then q1 reports `MCEntryMissingClass(4107,4,rk)`. Parent-only fresh EVM ZI0/DI0 measurement authenticated `rk.class`: 6986 bytes, SHA-256 `e1fe6f2ce983dd0a4ba16a062146025e0218c7ffeb603dee4091aafc39e6cf7b`. Canonical raw70 engine refused LinkError(1,71), committed no engine checkpoint, and failed-call root stayed unchanged. Parent replay deferred.

## Required capacity-only delta
Raise raw classes70→71, raw bytes464925→471911, diagnostic class bound166→167. Update coordinator arrays/constructor and driver declarations consistently. No semantic/interpreter/bootstrap/native change. Preserve bootstrap96 root `6fbfed767949708bacc0aebb58173f63c46bfd0b84cb0c5ac3a15f461c8a4a77`, System image SHA-256 `6e29f00abed753017741ad667314982061178298cb3fca5baa0d92f2f9d57564`, String/Locale/Map$Entry/Integer, global17 and String-local12 exactly. Runtime<=393216 (prior380017).

## Gate
Generated exact71/72 and471911/471912 boundaries; q1/q7/direct/reopen positives and retained identity-hash/System/lower-case/Locale/String/Map/Integer controls; full DI0 reads; atomic engine/coordinator/product-driver refusals and no failed checkpoint/head; source-only capacity delta; independent image/root commitments; canonical receipts; whole gate<=1200s; durable results/SHA256SUMS clean commit. No original/JAR/class/resource/network/other-worktree/provider/world/EULA/Done access/claim, push/review/delegation/Fast.
