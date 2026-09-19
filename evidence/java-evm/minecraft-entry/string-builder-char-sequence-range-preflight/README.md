# Bounded Java 8 `StringBuilder.append(CharSequence,int,int)` source stage

This generated-only stage derives from accepted `parent-baeda70ed`. It replaces
only bootstrap slot 84 (`java/lang/StringBuilder`, image 85) with the 914-byte
Java 8 `-g:none` image whose SHA-256 is
`22ca3088c0cebccc5714beefd40cf187dbaebe5930477559e20ab8709249ffa4`.

The added ordinary overload accepts only a genuine guest `String` passed as a
`CharSequence`. For a valid `start`/exclusive-`end` range it preserves the
existing logical content and appends exactly `input[start,end)`. It allocates an
owned range `char[]`, makes an owned `String`, then uses the retained
`append(String)` implementation. `null`, a non-`String` `CharSequence`, a
negative start, `end < start`, or `end > input.length()` each construct and
throw guest `IllegalArgumentException` before mutation. This deliberately is
not general Java `CharSequence` behavior.

The no-argument and `(int)` constructors, `append(String)`, copy-producing
`toString()`, and exactly-zero `setLength(int)` are retained. The `append(String)`
copy loops are direction-reversed only as an equal-result image layout cleanup:
they allocate the same one exact-length destination array, retain null's
ordinary `length()` NPE before allocation, and copy the same UTF-16 units.
`setLength(0)` still installs a new empty guest `char[]`; any nonzero value
still throws guest `IllegalArgumentException` without mutation. No capacity
surface, general resizing, one-argument `append(CharSequence)`, primitive
append, or other append overload is supplied.

There remain 90 bootstrap images in the same order, raw limits `37 / 282358`,
diagnostic bound 127, global native bindings 13, string-local binding 10,
14 exception kinds, 128 frames, one selected 4096-byte resource, 1 MiB
checkpoint, Head 32768, and a 25M reserve. The bootstrap root is derived at
runtime over all ordered image hashes, including slot 0:
`keccak256(abi.encode(DBOOT, h))` =
`cd603ccfebe00cbc0df9b81f65165af6c411d18470cf2839e00ff08abde524fb`.
No root constant is embedded.

The parent runtime baseline was 393206 bytes against the fixed 393216-byte
cap. The final runtime is 393185 bytes (31-byte cap headroom), SHA-256
`6fd885e700a28076b44eac81b35faaff3276cced18718c0c0431487054d56b1a`.
The source verifier proves parent-to-stage equality except the equal-width
staging domain, image84, and explicit layout-only `unchecked` increments. Each
such frame, JVM/internal-step, handle, ordinary-object, and ordinary-array
counter already has a finite pre-increment cap/guard in the inherited source;
no cap, root, error precedence, or commitment was weakened. The coordinator
remains 5394 bytes.

Focused valid-range tests cover a preexisting prefix plus empty, middle UTF-16,
and full String ranges. q1/q7/direct/reopen agree at 1085 Java and 2 internal
steps, epochs 1085/155/1, machine root
`0x940ff7775487f75d6055044a70400a9fe8a86fa7131bc75f752e32b9c3f8759f`,
and opaque payload SHA-256
`20b3f16b85ddb302a9eed875430358a8abb6453e3827694982c6ffb179be72d8`.
The null/non-String/three-invalid-range control preserves its `"pre"` prefix,
then proves a later valid range; q1/q7/direct/reopen agree at 825 Java and 10
internal steps, epochs 825/118/1. The absent one-argument `append(CharSequence)`
remains an atomic pre-Head `CallError(3,9)` refusal.

The focused-plus-retained generated gate ran 465 commands in 513.225 seconds
under the fixed 1200-second cap and independently canonicalized 8268 receipts.
It uses only trusted generated Java 8 fixtures; it does not open an original
artifact, JAR, class, resource, provider, factory, checkpoint, or world. Parent
alone performs accelerated replay.

Reproduce with pinned local tools only:

```sh
python3 evidence/java-evm/minecraft-entry/string-builder-char-sequence-range-preflight/tools/build.py build/java-diff-mc-string-builder-charsequence-range-build-LOCAL
python3 evidence/java-evm/minecraft-entry/string-builder-char-sequence-range-preflight/tools/generate_fixtures.py build/java-diff-mc-string-builder-charsequence-range-fixtures-LOCAL
python3 evidence/java-evm/minecraft-entry/string-builder-char-sequence-range-preflight/tools/gate.py build/java-diff-mc-string-builder-charsequence-range-build-LOCAL build/java-diff-mc-string-builder-charsequence-range-fixtures-LOCAL build/java-diff-mc-string-builder-charsequence-range-gate-LOCAL
```
