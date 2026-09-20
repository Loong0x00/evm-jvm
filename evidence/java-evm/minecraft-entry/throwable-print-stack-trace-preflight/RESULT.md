# Result

Implemented the bounded image5 `Throwable.printStackTrace(PrintStream)`
preflight. The exact Java-8 image calls `PrintStream.println(String)` only for
a non-null `detailMessage`; null preserves the prior sink field and performs no
write. Runtime is 389150/393216 bytes. Generated q1/q7/direct/reopen and
retained gate: 629.098s, 10412 canonical receipts. No original artifact/JAR/
resource or Minecraft execution was used. Parent owns accelerated replay.
