# Measured java/lang/Enum bootstrap preparation

Accepted original29 now reaches `HierarchyError(1,28)` for genuine StandardLevel; its
pinned Java8 javap superclass is `java/lang/Enum`, which is absent from81 bootstraps and29
raw classes. Add one immutable Java8-built bounded `java/lang/Enum` bootstrap at tail82.
Preserve all81 prior image bytes/order, raw29/262144 and other limits. The minimum genuine
surface must support StandardLevel's measured active-use path: protected `(String,int)` constructor with EVM-owned private-final name/ordinal fields;
`name()`, `ordinal()`, direct-field `toString()`, and bounded ordinal `compareTo(E)` with
the Java8 bridge. Declare the already-present Comparable and Serializable bootstrap
interfaces. Inherit Object identity equality. Do not add hashCode/clone/finalize or
reflection-based valueOf/getDeclaringClass, fabricate results, fake initialization, or
bypass hierarchy.

Strict tests require Java8 host/guest constructor field effects, name/ordinal/toString,
Comparable bridge/type behavior, and active-use ordering; null/type failures remain guest
semantics. Verify82 hashes/order, inputCount+76 sizing, diagnostic bound111, reserved raw
Enum replacement refusal, q1/q7/direct/reopen/canonical, and all retained enum/cap gates. Parent alone reruns unchanged
original29 and measures the next blocker. DeepSeek may do isolated read-only scope review;
Terra is the sole semantic writer. LOCAL384 only; no original worker access/push.
