# Result: bounded generated `URL.openStream()` stage

**Status:** completed generated-only stage from accepted `parent-f7e2ad683`.
It is not an original-JAR, provider/factory, Minecraft, world, or Done claim.

## Exact delta and pins

- Slot 62 alone is replaced in the engine with the Java 8 `java/net/URL` image
  SHA-256 `cc6bed564970075fce6bcaeb3560b5ac816a0804633fe02045dbb6f48a2647f5`.
  Its ordinary `openStream()` constructs `File("/ro/" + resourceName)` and a
  guest `FileInputStream`; its constructor, `equals`, `hashCode`, and
  `toString` remain ordinary Java. The source verifier proves the other 85 of
  86 images are byte-identical to the accepted parent and that the engine
  differs only in its fresh domain and this slot.
- The coordinator and raw-byte driver accept zero or one explicit generated
  resource: ASCII name 1..256 bytes and at most 4096 uncompressed bytes. EVM
  AS0/ZI0/DI0 validates the decoder/index/final-root package commitment and
  reads the exact bytes into a read-only `/ro/<name>` initial VFS seed.
  `resumeMain` uses its checkpointed VFS and does not reload that seed. No host
  ZIP parser, inflater, content injection, or resource catalogue is present.
- Built engine: 388986 bytes (cap 393216), runtime SHA-256
  `a1ee856160ed709bcc0cc9d9afc432ba2ee937e9011bd06d4421d9b8cf1c3c21`,
  Keccak `712cd54a0d19cd6705b353bdd8fcee7b70ada0ef35aaed0b2638f8ac53636b9`.
  Coordinator: 5394 bytes, runtime SHA-256
  `84f07a8dc983282abab18d727c8f156ee7461cfbb853f1d604245348ac0a537a`.
- Retained pins: raw `32/262144`, 86 bootstrap images, global natives 13,
  diagnostic bound 118, frames 128, checkpoint 1048576, head 32768,
  reserve 25000000, and external LOCAL gas 1000000000. The exact accepted
  parent input hashes are recorded in [parent-input.json](parent-input.json).

## Reproducible generated gate

One source build at `build/java-diff-mc-url-open-stream-build-final` passed the
source verifier and produced the tracked build pins. Fixtures at
`build/java-diff-mc-url-open-stream-fixtures-final` and the full receipt gate at
`build/java-diff-mc-url-open-stream-gate-final2` completed in **1019.736 s**:

- 61 result rows, 318 commands, and 13184 independently canonicalized public
  receipts passed. The durable outputs are
  [generated-gate-summary.json](generated-gate-summary.json),
  [canonical-receipts.json](canonical-receipts.json),
  [fixture-summary.json](fixture-summary.json),
  [source-verification.log](source-verification.log), and
  [build-pins.json](build-pins.json).
- Generated ZIP enumeration → `URL.openStream()` returns exact bytes, EOF, and
  close behavior with matching q1/q7/direct terminal state: 5769 Java and 8
  internal steps, machine root
  `0x61199377038cdf91ca93ff5c60dd4e54470837afbb0956017417b1c33c885a3c`,
  opaque SHA-256
  `75261310a928b66e8d132bedaf23dcebde9397a665f55bd0c47c766f0b599c36`.
  The q1/q7/direct epoch counts are 5769/825/2 respectively.
- The absent-resource path also agrees at q1/q7/direct (3306 Java, 7 internal
  steps). The 4096-byte selected resource passes; 4097 rejects before a head
  with scalar error 27. Two resources are refused. Package-root and decoder
  address tampering reject without mutation (errors 26 and 25 respectively).
- The retained Object.getClass, cap32, lock, TreeMap, String,
  StringBuilder, EnumSet, queue, OOM, raw-replacement, checkpoint/reopen and
  canonical ABI/event/read-range receipt gates all passed.

The tracked full-gate summary SHA-256 is
`63a0a0888a86a7eea7abf01cc2dcb9cd75987f5ce8db189ff94c03c061a56c6f`.
Reproduce with the three commands in [README.md](README.md). Only generated
Java 8 classes and generated ZIP resources are used.
