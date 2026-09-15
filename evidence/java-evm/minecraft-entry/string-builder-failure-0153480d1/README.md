# StringBuilder image85 bounded-build failure

This is durable failure evidence for the one allowed source build of the bounded
Java-8 `StringBuilder` image85 candidate at source commit `0153480d1`.

The strict reverse verifier completed first, including the six pinned
`parent-89928ece8` inputs, Java-8 compilation of the 542-byte image, append-only
84-to-85 bootstrap proof, raw30 and fixed-limit checks. The required pinned solc
then measured a 395319-byte deployed engine runtime. It is 2103 bytes above the
fixed 393216-byte cap (and 2544 bytes over the parent 392775-byte runtime).

The build stopped at that cap. No coordinator/driver build, generated fixture
gate, original artifact, Minecraft input, resource, world, or network access
occurred. The candidate is not accepted.
