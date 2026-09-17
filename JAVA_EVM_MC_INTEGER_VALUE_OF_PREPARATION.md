# Java-on-EVM Minecraft bounded `Integer.valueOf(int)` preparation

Accepted `parent-1b7a30656` loads genuine Provider.class and advances unchanged original33 to51213J/44I with7317 canonical receipts. q7/q1 atomically stop in `Provider.<clinit>` PC1 on `Integer.valueOf(I)Ljava/lang/Integer;` (`CallError(3,1)`), with measured argument -1 for `DEFAULT_PRIORITY`.

Scope:
1. Replace only existing bootstrap Integer image, preserving constructors, numeric conversions, equals/hash/compare/parseInt. Add ordinary Java8 guest `valueOf(int)` returning a genuine Integer object through the accepted constructor.
2. No cache/identity guarantee, String/radix overload, formatting or broad boxing claim. Cover -1,0,min,max/equality/value and distinct allocation; no host primitive.
3. Preserve raw33/262158,86 bootstraps,native13,diagnostic119, selected resource/Properties/String pipeline and all fixed limits/toolchain/outlined tail; runtime<=393216 (1140-byte current headroom).
4. Focused q1/q7/direct/reopen plus no-init/raw replacement/omitted-overload controls; accepted parent controls direct/reopen; whole gate<=1200s with canonical receipts.

Parent alone reruns unchanged original33. No Provider constructor/factory/world/Done claim before measured execution.
