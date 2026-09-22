# Java-on-EVM Minecraft `Integer.highestOneBit(int)` preparation

## Measured blocker
Accepted `parent-bbecbd532` genuinely loads Hashing.class and reaches87094J/74I. Canonical q1 refuses `CallError(3,7)`. Fresh-domain EVM-only diagnostics identify static resolution line7964, bootstrap class index132 = raw62 + classSlot101 + Integer offset31, method `highestOneBit`, descriptor `(I)I`.

## Required bounded change
Append exactly `public static int highestOneBit(int i)` to the current canonical bootstrap `java/lang/Integer`, with exact Java8 32-bit semantics: zero->0; positive selects highest set bit; negative->`MIN_VALUE`. A valid implementation may use the JDK bit-smear formula. Do not add any other Integer API (especially rotateLeft).

Preserve raw62/376794/diagnostic156, native16, String-local11, all non-Integer bootstrap images/order and all limits/semantics. Rebuild slot Integer only and independently verify its ordered bootstrap hash/root. Runtime must remain <=393216.

## Required generated gate
Use Java8 generated fixtures and host oracle for `0,1,2,3,4,7,8,0x12345678,MAX_VALUE,MIN_VALUE,-1` and deterministic additional values. Exercise q1/q7/direct/reopen equivalence, retained direct/reopen regression, malformed/omitted/raw-Integer replacement refusal, exact method metadata and source/image pinning. Whole gate <=1200s; durable results/SHA256SUMS/clean commit. No originals/JAR/classes/resources/network; parent genuine replay deferred. No provider/world/Done claim.
