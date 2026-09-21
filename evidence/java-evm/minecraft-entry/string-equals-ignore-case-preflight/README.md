# Generated `String.equalsIgnoreCase(String)` image26

This generated-only stage implements
`JAVA_EVM_MC_STRING_EQUALS_IGNORE_CASE_PREPARATION.md`. It changes only the
existing bootstrap `java/lang/String` image at root-leaf index26 (zero-based;
the 27th ordered leaf, image1 in the String profile), retaining all other 92
image leaves, including image93
`java/util/Objects`.

`equalsIgnoreCase(String)` is ordinary Java-8 bytecode over the retained
String `length()` and `charAt()` primitives. It returns false for a null
argument, compares equal UTF-16 units as equal, and folds only ASCII `A-Z` /
`a-z` pairs. It makes **no general Unicode case-folding claim**. The changed
String image is 1503 bytes, SHA-256
`4cff1fc7c1ee49c0e070a7aec64963193e34206838c509003715f972aa8d58a0`.

The engine dynamically derives the ordered bootstrap root. `root-commitment.json`
records the new String leaf and fresh domain root
`910d9bcec092acbd3476403e8fa6bb2a0079193a029908e5f1b368342d8b7731`; every
other leaf is mechanically compared to the accepted image93 Objects parent.
Bootstrap count remains93, diagnostic bound141, raw48/314425, native13, and
all limits/toolchain remain pinned. The rebuilt runtime is
`391507 / 393216` bytes (1709-byte headroom); the measured image93 baseline
was 390985 bytes.

The generated gate has q1/q7/direct/reopen chains for exact, ASCII
lower/upper, mismatch, length, null-false, and non-ASCII exact/no-fold cases.
A generated equal-width constant-pool descriptor mutation confirms the absent
`equalsIgnoreCase(Object)` control remains `StringProfileError(1,4)`. It also
reruns the inherited generated controls and canonical receipt verifier.

This stage uses only trusted generated Java-8 sources and its generated String
image. It does not read or execute original artifacts, JARs, classes,
resources, worlds, providers, logger factories, or Done behavior. Parent owns
any genuine replay separately.

## Reproduction

From repository root with fresh ignored `build/` paths:

```sh
python3 evidence/java-evm/minecraft-entry/string-equals-ignore-case-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/string-equals-ignore-case-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/string-equals-ignore-case-preflight/tools/build.py build/java-diff-mc-string-equals-ignore-case-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/string-equals-ignore-case-preflight/tools/generate_fixtures.py build/java-diff-mc-string-equals-ignore-case-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/string-equals-ignore-case-preflight/tools/gate.py build/java-diff-mc-string-equals-ignore-case-build-repro-LOCAL build/java-diff-mc-string-equals-ignore-case-fixtures-repro-LOCAL build/java-diff-mc-string-equals-ignore-case-gate-repro-LOCAL
```
