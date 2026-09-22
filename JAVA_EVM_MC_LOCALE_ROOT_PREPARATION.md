# Java-on-EVM Minecraft `Locale.ROOT` preparation

## Measured blocker
Accepted `parent-949992642` genuinely loads StringUtils.class and reaches87439J/77I. q1 requests owner `java/util/Locale` at field-resolution site4103/pc22. Fresh-domain EVM diagnostics identify exact field `ROOT` and descriptor `Ljava/util/Locale;`.

## Required bounded change
Append immutable bootstrap image96 `java/util/Locale`. Bounded Java8-compatible surface only: public final class implementing Serializable and Cloneable; `public static final Locale ROOT`; private Object-chaining no-arg constructor; `<clinit>` creates exactly one fresh non-null ROOT. No language/country state, default locale, factories, formatting or case APIs. Reserve raw Locale replacement.

Preserve all prior95 bootstrap images/order byte-for-byte, including String.indexOf, Map$Entry and Integer. Keep raw69/449904. Bootstrap96 makes diagnostic bound165. Update only append/layout/count/root commitments required by Locale. Preserve native16/String-local11 and all other semantics/limits. Runtime<=393216 (prior377043).

## Gate
Generated Java8 fixtures prove Locale class/field/method flags, one ROOT singleton, stable non-null identity across q1/q7/direct/reopen, no extra surface/instance state, no initialization fabrication, raw replacement and malformed/omitted refusals, all prior image hashes unchanged, independent ordered-root verification, and retained direct/reopen regression. Whole gate<=1200s; durable results/SHA256SUMS/clean commit. No originals/JAR/classes/resources/network; parent replay deferred. No provider/world/Done claim.
