# Result: generated bounded `System.out`

- Added only image44 `System.out:Ljava/io/PrintStream;`, `public static final`, constructed after retained `System.err` as a distinct guest `PrintStream`.
- No host output or widened System/PrintStream API. Existing guest sink-only `println(String)` and `print(char)` behavior is exercised on both fields.
- Runtime: 373634 / 393216 bytes. Raw51/328000, diagnostic145, 94 images, native14, String-local11, and every fixed limit remain pinned.
- Final generated-only gate: 120.950734 seconds, 480 commands, 468 canonical receipts. Focused q1/q7/direct/reopen agrees at 202 Java / 6 internal steps with identical machine root and opaque payload; `out` handle11 and `err` handle10 are distinct.

No original/JAR/resource/replay/provider/world/EULA/Done work was performed or claimed.
