# Java-on-EVM Minecraft bounded `Object.getClass()` preparation

Accepted `parent-5f01fbbdf` runs unchanged original32 to12452J/42I and1784 canonical receipts, then q7/q1 atomically stop at `LoaderUtil$UrlResource.equals` PC12 on genuine `invokevirtual java/lang/Object.getClass:()Ljava/lang/Class;` (`CallError(3,12)`).

Implement only this measured surface:

1. Replace only bootstrap `java/lang/Object` slot0 with a Java8 `public final native getClass()` declaration while preserving its accepted constructor/equals behavior and all other85 images.
2. Add exactly one global native binding13 for non-null ordinary guest objects. Return/create the existing canonical guest `Class` mirror for the receiver's dynamic class via the established mirror allocator, preserving raw defining-loader identity, quotas, OOM behavior, uniqueness, checkpoint persistence and no target initialization.
3. Normal invokevirtual null receiver remains catchable guest NPE before native execution. Arrays, primitive mirrors, forged mirrors and broad reflection remain explicitly unsupported/refusing; no host type oracle.
4. Preserve raw32/262144, diagnostic118, all fixed limits/toolchain/outlined tail, runtime<=393216.
5. Generated gates cover dynamic subclass identity vs class literal, repeated canonical identity, distinct same-class objects, null NPE, array refusal, no-init/raw Object replacement controls, mirror reopen/checkpoint behavior and all retained cap32/lock/TreeMap/String/EnumSet/queue/OOM/canonical receipt gates.

Parent alone reruns unchanged original32. No provider/factory/world/Done claim before measured execution.
