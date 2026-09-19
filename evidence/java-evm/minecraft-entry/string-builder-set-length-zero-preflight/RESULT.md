# Result: bounded `StringBuilder.setLength(0)`

- Replaced only bootstrap image84 (`java/lang/StringBuilder`) from
  `parent-b8102b85b` with the 736-byte Java 8 image, SHA-256
  `a4de489af0ceb96ff8611c460a4611701b66828774e55baf2dad0a39729e151a`.
  Existing constructors, `append(String)`, and `toString()` remain intact.
  `setLength(0)` installs a new empty guest `char[]`; any nonzero argument
  throws guest `IllegalArgumentException` without mutation.
- Raw37/282358, all 90 image positions, diagnostic127, native13, resource
  pipeline, gas policy, frames/checkpoint/Head caps, and toolchain remain
  pinned. The full runtime-derived root is
  `260897f23948c98feb09c9d5fd10a705173f967edcfe5196ac01fd2e029ce269`.
- Runtime is 393206 / 393216 bytes (10-byte headroom) from the 393072-byte
  baseline; no unrelated layout recovery was used. Coordinator remains 5394
  bytes.
- Focused zero-reset and nonzero-IAE controls each pass q1/q7/direct/reopen;
  the zero fixture is 364 Java/2 internal steps and nonzero is 272/7. The
  generated focused-plus-retained gate completed 446 commands, 6141 canonical
  receipts, in 393.146 seconds (cap1200).

No original artifact/JAR/class/resource execution, general setLength/capacity,
provider/factory/world, or Done claim. Parent alone performs accelerated replay.
