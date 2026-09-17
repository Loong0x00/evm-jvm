# Java-on-EVM Minecraft bounded `Integer.valueOf(String)` preparation

Accepted `parent-cb0c15e54` advances unchanged original33 through bounded WeakReference to51347J/45I and7337 canonical receipts. q7/q1 atomically stop in `Provider.<init>` PC43 on `Integer.valueOf(Ljava/lang/String;)Ljava/lang/Integer;` (`CallError(3,43)`), with measured value `"10"` for provider priority.

Scope:
1. Replace only Integer bootstrap image, preserving all accepted methods including `valueOf(int)`. Add ordinary Java8 `valueOf(String)` as genuine parseInt plus Integer construction.
2. Retain existing NumberFormatException behavior for null/empty/sign/invalid/overflow. No radix overload, cache identity, formatting or broad boxing claim.
3. Preserve87 bootstraps, raw33/262158,native13,diagnostic120,resource/Properties/String/WeakReference pipeline and all fixed limits/toolchain/outlined tail; runtime<=393216.
4. Focused q1/q7/direct/reopen valid/invalid/null/overflow tests and omitted radix control; accepted parent controls direct/reopen; whole gate<=1200s canonical receipts.

Parent alone reruns unchanged original33. No provider factory/world/Done claim before measured execution.
