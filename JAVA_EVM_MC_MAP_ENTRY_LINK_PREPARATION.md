# Java-on-EVM Minecraft `java/util/Map$Entry` link preparation

## Measured blocker
Accepted `parent-6ac48e5e1` genuinely loads AbstractMapEntry.class and reaches87147J/74I, then q1 requests exact platform interface binary name `java/util/Map$Entry` at link site4098/context64. This is not a JAR raw class.

## Required bounded change
Append one immutable bootstrap image95 for `java/util/Map$Entry`, preserving every prior image byte/order including Map and Integer/highestOneBit. Build it as the public static nested interface of `java.util.Map`, but retain the already-pinned Map.class image; append only the javac-produced Map$Entry.class. Bounded core abstract surface: `getKey()`, `getValue()`, `setValue(V)`, `equals(Object)`, `hashCode()`; do not add Java8 comparator helpers or implementation behavior. Ensure exact interface/public/abstract metadata, Object superclass, no Code, no initialization behavior. Reserve the binary name against raw replacement.

Keep raw65/381732. Bootstrap count94->95 and diagnostic class bound159->160; update count/layout/root commitments only as required by the append. Preserve native16, String-local11 and all other limits/semantics. Runtime<=393216 (prior377409).

## Gate
Generated Java8 fixtures must prove type link/assignability and core interface dispatch with a generated implementation, exact metadata/no Code, q1/q7/direct/reopen, malformed/omitted/raw-replacement refusal, prior Map image exact preservation, independent ordered-root verification, plus retained direct/reopen regression. Whole gate<=1200s; durable results/SHA256SUMS/clean commit. No originals/JAR/classes/resources/network; parent replay deferred. No provider/world/Done claim.
