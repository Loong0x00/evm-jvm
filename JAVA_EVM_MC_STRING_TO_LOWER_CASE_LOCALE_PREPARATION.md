# Java-on-EVM Minecraft `String.toLowerCase(Locale)` preparation

## Measured blocker
Accepted `parent-b664e751a` genuinely executes unchanged original69 through Locale.ROOT and reaches 87450J/79I. Atomic q1 refuses `StringProfileError(1,25)`. Fresh-domain EVM-only diagnostics identify exact method `java/lang/String.toLowerCase(Ljava/util/Locale;)Ljava/lang/String;` (sites4120/4121). No host class/JAR parsing established this dependency.

## Required one bounded semantic change
Add exactly `public String toLowerCase(java.util.Locale)` to bootstrap String and one String-local native binding12; global native bindings remain16. Implement Java8-compatible behavior only for the measured Locale.ROOT/ASCII domain: null Locale raises guest NullPointerException; the only constructible bounded Locale instance is ROOT; every UTF-16 unit must be ASCII or execution explicitly refuses with StringProfileError. Map `A..Z` to `a..z`, preserve all other ASCII units, return the receiver iff no unit changes (including empty), otherwise atomically allocate an owned char[] plus fresh String with canonical String defaults/hash. No host locale/text API, Unicode approximation, fabricated output, locale default, language/country, upper-case, or other String surface.

Preserve raw69/449904, bootstrap96 and diagnostic165. Preserve Locale image96 byte-for-byte and every prior image except the measured String image; independently verify the changed ordered bootstrap root. Preserve all other semantics/limits. Runtime<=393216 (prior378675).

## Required gate
Generated Java8 host-oracle fixtures prove exact metadata and ASCII results/identity for empty, already-lowercase, uppercase, mixed, digits/punctuation; q1/q7/direct/reopen equivalence; guest caught/uncaught null NPE; atomic non-ASCII refusal without committed continuation; omitted toUpperCase(Locale) refusal; raw String/Locale replacement refusals; prior Locale.ROOT, String indexOf/substring, Map$Entry and Integer retained controls. Verify only the String leaf changes, Locale and the other95 ordering inputs stay exact, root is independently derived, global16/String-local12, and all canonical receipts/DI0 reads. Whole gate<=1200s, durable results/SHA256SUMS, clean commit. No original/JAR/resource/network/world/EULA/Done input or claim; parent replay deferred.
