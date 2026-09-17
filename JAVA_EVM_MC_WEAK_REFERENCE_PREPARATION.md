# Java-on-EVM Minecraft bounded `WeakReference` preparation

Accepted `parent-36ea2d7e6` advances unchanged original33 to51248J/45I and7322 canonical receipts, then q7/q1 atomically requests platform `java/lang/ref/WeakReference` at `Provider.<init>` PC10 (`new`, site4104/context10). The measured surface is constructor `(Object)V` and later `get()Object` for the provider class loader.

Scope:
1. Append one Java8-produced bootstrap image87 `java/lang/ref/WeakReference` after all accepted86 images. It is a bounded direct Object subclass with one referent field, constructor and get only.
2. Retain strong deterministic guest reference identity; null remains null. No GC clearing, Reference/ReferenceQueue hierarchy, enqueue/clear/isEnqueued, reachability/finalization or broad java.lang.ref claim.
3. Preserve raw33/262158,native13,selected resource/Properties/String/Integer pipeline and all limits/toolchain/outlined tail; diagnostic class bound119->120; runtime<=393216 (762-byte headroom).
4. Focused q1/q7/direct/reopen identity/null tests plus no-init/raw replacement/omitted API refusal; accepted parent controls direct/reopen; whole gate<=1200s and canonical receipts.

Parent alone reruns unchanged original33. No Provider/factory/world/Done claim before measured execution.
