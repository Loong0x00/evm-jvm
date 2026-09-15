# Measured java/lang/Enum bootstrap preparation

Accepted original29 now reaches `HierarchyError(1,28)` for genuine StandardLevel; its
pinned Java8 javap superclass is `java/lang/Enum`, which is absent from81 bootstraps and29
raw classes. Add one immutable Java8-built bounded `java/lang/Enum` bootstrap at tail82.
Preserve all81 prior image bytes/order, raw29/262144 and other limits. The minimum genuine
surface must support StandardLevel's measured active-use path: protected `(String,int)`
constructor with EVM-owned final name/ordinal fields, plus only methods justified by
Java8 structure/fixtures; no reflection-based valueOf/getDeclaringClass fabrication,
no fake initialization, no hierarchy bypass.

Strict tests require Java8 host/guest constructor field effects, name/ordinal/toString and
bounded Comparable behavior if included; null/type/identity failures must remain guest
semantics. Verify82 hashes/order, inputCount+76 sizing, q1/q7/direct/reopen/canonical,
raw replacement refusal and all retained enum/cap gates. Parent alone reruns unchanged
original29 and measures the next blocker. DeepSeek may do isolated read-only scope review;
Terra is the sole semantic writer. LOCAL384 only; no original worker access/push.
