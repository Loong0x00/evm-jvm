# Java-on-EVM Minecraft bounded Iterable hierarchy preparation

Accepted `parent-61fd1832a` advances unchanged original33 to51753J/45I and7395 canonical receipts, then q7/q1 atomically stops at `ProviderUtil.getProviders` PC6 `areturn`: its declared return type `java/lang/Iterable` is absent (`LinkError(4,6)`), while the genuine value is the PROVIDERS HashSet through Collection.

Scope:
1. Append Java8 bootstrap image88 `java/lang/Iterable<T>` with only `Iterator<T> iterator()`.
2. Replace only existing `java/util/Collection` image so it extends Iterable and preserves accepted add/size/iterator/isEmpty declarations. Preserve every other86 image/order.
3. This is hierarchy/linkage only: no forEach/spliterator/default methods, mutation, stream or broad collections expansion. Existing guest collection implementations supply their existing iterator methods.
4. Preserve raw33/262158,native13,resource pipeline and all fixed limits/toolchain/outlined tail; diagnostic120->121; runtime<=393216.
5. Focused q1/q7/direct/reopen Collection->Iterable return/assignment/iterator tests, null and omitted default-API controls; accepted parent controls direct/reopen; whole gate<=1200s canonical receipts.

Parent alone reruns unchanged original33. No provider factory/world/Done claim before measured execution.
