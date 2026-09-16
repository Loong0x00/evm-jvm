# Result: bounded generated `Properties.load(InputStream)` stage

**Status:** completed generated-only source stage from accepted URL parent
`parent-c96c326bc`. This is not an original-JAR, provider/factory, Minecraft,
world, EULA, or Done claim.

## Exact delta and pins

- Bootstrap slot 47 (`java/util/Properties`) is replaced with the Java 8
  ordinary class image SHA-256
  `bcc0cac41a4db6a00152ad922ac4372d3ec76925f2c639d25b23c68b9038735f`.
  Its ordinary `load(InputStream)` reads ISO-8859-1 units, supports CR/LF,
  leading space/tab/form-feed, `#`/`!` comments and `=`/`:`/first-whitespace
  separators, and stores copied guest `String` slices through inherited
  `Hashtable.put`.
- The bounded parser accepts a 4096-unit logical line; a backslash or the 4097th
  unit raises catchable guest `IOException`. It neither closes the supplied
  stream nor uses a host parser, resource callback, or native binding.
- The EVM AS0 → ZI0 → DI0 → read-only VFS selected-resource path remains
  scalar and unchanged. Generated raw mains materialize their canonical raw
  class mirror before using the system loader; this preserves the existing
  loader/mirror invariant rather than relying on implicit state.
- Built engine: 392032 bytes (cap 393216), runtime SHA-256
  `8598e222cade64f356d1ac041a724c33a27d53c3c023fef77f59c5d615864b09`,
  Keccak `5e4217c308539f75be185a25dcbea0747f1d1e56ac0f05d8da158fc829a988e4`.
  Coordinator: 5394 bytes, runtime SHA-256
  `1a34159d0ba563f0e0231d044da465d5f732a299b673c6bff51d5065cf3bae30`.
- Retained pins: 86 bootstraps, raw `32/262144`, global natives 13,
  diagnostic bound 118, frames 128, checkpoint 1048576, Head 32768, reserve
  25000000 and external LOCAL gas 1000000000.

## Reproducible generated gate

One pinned local source build and generated-Java-8 fixture build passed. The
fresh full gate completed in **2134.377 s**, with 66 result rows, 351 commands,
and 25777 independently canonicalized receipts. Durable outputs are
[build-pins.json](build-pins.json),
[fixture-summary.json](fixture-summary.json),
[generated-gate-summary.json](generated-gate-summary.json),
[canonical-receipts.json](canonical-receipts.json), and
[source-verification.log](source-verification.log).

- Enumeration → URL → ordinary guest `FileInputStream` → `Properties.load`
  parsed the generated resource under q1/q7/direct with equal terminal state:
  7752 Java and 8 internal steps, epochs 7752/1108/2, machine root
  `0xca0978bc993703b5e7b8138f9156476b2b64ad90ceef7d2ae1d02745bd59f3ff`.
- Null input follows the guest NPE path; the generated escape input follows the
  guest IOException path, each q1/q7/direct-equivalent. The 4096-line positive
  completed in 244702 Java steps; the custom 4097-line input completed through
  its catchable IOException control in 151687 Java steps.
- The full retained URL/Object/cap32/lock/TreeMap/String/StringBuilder/EnumSet/
  queue/OOM/reopen and canonical receipt corpus passed. Selected resource 4096
  remains accepted; 4097 is refused before a Head with scalar error 27.

Reproduce with the three commands in [README.md](README.md). Only generated
classes and generated ZIP resources are used; no original artifact was opened
or executed.

## Parent gate amendment

The worker's first all-history q1 sweep took 2134.377s and is retained above as
invalid under the fixed1200s whole-gate bound. Parent changed no runtime source:
only the gate now reserves q1/q7/direct equivalence for the newly measured
Properties parser, runs unsupported escape at q7/direct, and reruns accepted
parent controls direct/reopen. The amended fresh gate passed in954.772s with9502
canonical receipts across48 worlds. See `amended-gate-summary.json`.
