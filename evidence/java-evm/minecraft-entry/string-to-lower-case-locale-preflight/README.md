# MC-STRING-LOWER-LOCALE-P1 generated preflight

This bounded generated-only stage changes bootstrap leaf 27 (zero-based slot 26)
`java/lang/String` from `parent-b664e751a`. It adds exactly public native
`String toLowerCase(java.util.Locale)` and String-local binding 12. Global native
bindings remain 16. Locale image 96 remains byte-for-byte unchanged.

The native path accepts the only constructible bounded Locale, `Locale.ROOT`.
A null Locale raises guest `NullPointerException`. Every String UTF-16 unit must
be ASCII; `A..Z` becomes `a..z`, all other ASCII units are preserved, and any
non-ASCII unit raises `StringProfileError(1, callPC)`. Empty and already-lowercase
inputs return the receiver. A changed result reserves then creates an owned
`char[]` and fresh String with standard profile defaults and zero hash; failed
allocation is atomic and raised as guest OOME by the caller. This is not Unicode,
default-locale, language/country, upper-case, or other String support.

Pinned facts:

- String image: 1836 bytes, SHA-256
  `259bed03edf8602dca9ad26e639cb7668b8da38d62422b80788d8339020017fe`
- Locale image unchanged: 285 bytes, SHA-256
  `8401495628aed9de6e7c7c0ad56f73ac563bd5e7a892b8eb8ca9fcf91bc03e31`
- independent 96-leaf root:
  `39b4e365255c15cdf1de704a264e35b2574c77e653a72718a9a9861a76ad7f18`
- runtime: 379383 bytes, below the 393216-byte LOCAL cap
- raw limits: 69 classes / 449904 bytes; bootstrap 96; diagnostic 165;
  exception kinds 14; String-local 12; global natives 16.

## Reproduction

From the repository root, using the pinned local Node modules and Java 8:

```sh
python3 evidence/java-evm/minecraft-entry/string-to-lower-case-locale-preflight/tools/build.py build/java-diff-mc-string-lower-locale-build-REPRO
python3 evidence/java-evm/minecraft-entry/string-to-lower-case-locale-preflight/tools/generate_fixtures.py build/java-diff-mc-string-lower-locale-fixtures-REPRO
python3 evidence/java-evm/minecraft-entry/string-to-lower-case-locale-preflight/tools/gate.py build/java-diff-mc-string-lower-locale-build-REPRO build/java-diff-mc-string-lower-locale-fixtures-REPRO build/java-diff-mc-string-lower-locale-gate-REPRO
```

`verify_source.py` compiler-rebuilds String and Locale, validates exact metadata,
proves Locale and every other leaf remain parent exact, and independently derives
the new ordered root. The gate uses generated Java-8 host-oracle positives for
empty/lower/upper/mixed/digits/punctuation and retained controls; it executes
q1/q7/direct/reopen equivalence, caught and uncaught NPE, non-ASCII atomic
refusal, upper-case omission, raw replacement refusals, and public receipt/DI0
read verification.

No original class/JAR, resource, network, world, EULA, Done, or Minecraft input
is opened, executed, or claimed. Parent genuine replay remains deferred.
