# Bounded Java 8 `StringBuilder.setLength(0)` source stage

This generated-only stage derives from accepted `parent-b8102b85b`. It replaces
only bootstrap slot 84 (`java/lang/StringBuilder`, image 85) with this 736-byte
Java 8 `-g:none` image:

```java
public void setLength(int length) {
    if (length != 0) {
        throw new IllegalArgumentException();
    }
    value = new char[0];
}
```

The image SHA-256 is
`a4de489af0ceb96ff8611c460a4611701b66828774e55baf2dad0a39729e151a`.
It preserves the accepted no-argument and `(int)` constructors, `append(String)`,
and copy-producing `toString()`. Exactly zero replaces the exact logical content
with a new empty guest `char[]`; subsequent append starts at index zero. Every
nonzero argument, including negative values, takes ordinary guest construction of
`IllegalArgumentException` and leaves logical content unchanged. This is not a
general resizing, capacity, or growth claim.

There remain 90 bootstrap images in the same order, raw limits `37 / 282358`,
diagnostic bound 127, global native bindings 13, one selected resource at 4096
bytes, 128 frames, 1 MiB checkpoint, Head 32768, and 25M reserve. The exact
raw37 bootstrap root is derived at runtime over every ordered image hash,
including direct `_bootstrapObject()` hashing at slot 0:
`keccak256(abi.encode(DBOOT, h))` =
`260897f23948c98feb09c9d5fd10a705173f967edcfe5196ac01fd2e029ce269`.

The parent baseline was 393072 bytes. The built engine is 393206 / 393216 bytes,
leaving 10 bytes. No unrelated layout recovery was used; `layout.json` and
`verify_source.py` reject a precomputed root and prove all non-image84 engine
bytes are the parent source after only the equal-width staging-domain change.
The coordinator remains 5394 bytes.

The focused zero-reset fixture covers zero before append, append/reset,
copy independence, append after reset, and repeated reset. q1/q7/direct/reopen
agree at 364 Java and 2 internal steps, epochs 364/52/1, machine root
`0x782d34c188fc731d4b619dbfc614881d74d3beb934821fbaf0ded64e5bc51819`,
and opaque payload SHA-256
`46107d633762b4948368d614152a324906cefb74acd8ec42ee351cee6022c86c4`.
The nonzero `1` and `-1` fixture catches guest `IllegalArgumentException`,
retains pre-throw content, then performs its supported zero reset; q1/q7/direct/
reopen agree at 272 Java and 7 internal steps, epochs 272/39/1.

The focused-plus-retained generated gate ran 446 commands in 393.146 seconds
under the fixed 1200-second limit and verified 6141 canonical receipts. It uses
only trusted generated Java 8 fixtures; it does not open an original artifact,
JAR, class, resource, checkpoint, or world. No provider/factory, general
`setLength`, capacity, world, or Done claim is made. Parent alone performs its
accelerated replay.

Reproduce with pinned local tools only:

```sh
python3 evidence/java-evm/minecraft-entry/string-builder-set-length-zero-preflight/tools/build.py build/java-diff-mc-string-builder-set-length-zero-build-LOCAL
python3 evidence/java-evm/minecraft-entry/string-builder-set-length-zero-preflight/tools/generate_fixtures.py build/java-diff-mc-string-builder-set-length-zero-fixtures-LOCAL
python3 evidence/java-evm/minecraft-entry/string-builder-set-length-zero-preflight/tools/gate.py build/java-diff-mc-string-builder-set-length-zero-build-LOCAL build/java-diff-mc-string-builder-set-length-zero-fixtures-LOCAL build/java-diff-mc-string-builder-set-length-zero-gate-LOCAL
```
