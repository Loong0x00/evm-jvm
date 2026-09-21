# Result: bounded `PrintStream(OutputStream)`

- Replaced only bootstrap image83/root leaf with a 507-byte direct-`OutputStream` PrintStream image.
- Added public `PrintStream(OutputStream)`: retained `OutputStream.<init>()` plus canonical guest-null check only. No `FilterOutputStream` field or forwarding behavior was added.
- Preserved no-arg construction, `println(String)`, `print(char)`, and low-byte `write(int)` guest sinks.
- Focused direct/subclass/non-forwarding witness: q1/q7/direct/reopen agree at 103 Java / 3 internal steps. Null-NPE witness: 25 Java / 4 internal steps. Uninitialized and raw-replacement controls, plus retained direct/reopen, passed.
- Runtime 373860 / 393216 bytes; 501-command, 625-receipt whole gate completed in 134.909576s (limit 1200s).

No original/JAR/resource/replay/network/provider/world/EULA/Done work was performed. Parent replay is deferred.
