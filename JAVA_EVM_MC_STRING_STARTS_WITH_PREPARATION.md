# Java-on-EVM Minecraft bounded `String.startsWith(String)` preparation

Accepted `parent-1fc13ef12` parses the genuine904B provider properties entirely in guest Java and advances unchanged original32 to51074J/43I with7298 canonical receipts. q7/q1 then atomically stop in `ProviderUtil.validVersion` PC22 at `java/lang/String.startsWith(Ljava/lang/String;)Z` (`StringProfileError(1,22)`).

Scope:
1. Replace only bootstrap String slot26, preserving every accepted constructor/native and ordinary `lastIndexOf(String)` byte-for-byte in behavior. Add ordinary Java8 guest `startsWith(String)` using existing length/charAt UTF-16 primitives.
2. Implement only offset0: empty prefix true, longer/absent false, exact/prefix true, UTF-16 code-unit semantics; null prefix follows catchable guest NPE. No offset overload, substring, normalization or broad String expansion.
3. Preserve selected resource/Properties pipeline, raw32/262144,86 bootstraps,native13,diagnostic118 and all fixed limits/toolchain/outlined tail; runtime<=393216.
4. Generated gate gives startsWith q1/q7/direct/reopen cases plus null/no-init/raw String controls. Accepted parent controls run direct/reopen so the complete whole gate remains<=1200s; canonical receipts required.

Parent alone reruns unchanged original32. No provider/factory/world/Done claim before measured execution.
