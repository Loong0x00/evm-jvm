# Result: generated `PrintStream` direct `OutputStream` subtype

- Replaced only bootstrap image83: canonical `PrintStream` directly extends retained `OutputStream`, and its constructor chains to `OutputStream.<init>()`.
- Retained guest-only `println(String)` and `print(char)` sinks. Added only concrete `write(int)`, storing `value & 0xff` in the existing char sink; no host or broader stream behavior.
- Focused q1/q7/direct/reopen matches at 64 Java / 3 internal steps, retains the line sink, and records low byte `0x34` from virtual `OutputStream.write(0x1234)`.
- Runtime: 373704 / 393216 bytes. Raw52/329162, diagnostic146, 94 images, native14, String-local11, and all fixed limits remain pinned.
- Final generated-only gate: 129.924868 seconds, 492 commands, 551 canonical receipts; retained controls passed direct/reopen.

No original/JAR/resource/replay/network/provider/world/EULA/Done work was performed or claimed. Parent replay is deferred.
