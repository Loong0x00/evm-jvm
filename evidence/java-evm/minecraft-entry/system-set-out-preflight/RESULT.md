# Result: bounded canonical `System.setOut(PrintStream)`

- Added only public static native `System.setOut(PrintStream)` to bootstrap image44 and global binding16.
- Binding16 consumes a guest `PrintStream` reference (null allowed) after ordinary resolution/initialization/assignability checks and mutates canonical `System.out` only. `System.err`, all other statics, and final field metadata remain unchanged.
- Focused direct/subclass/null/reset identity witness passed q1/q7/direct plus durable reopen: 209 Java / 7 internal steps, identical terminal root and opaque checkpoint payload.
- Raw same-name System replacement rejected atomically before acquiring binding16.
- Full focused + retained direct/reopen gate: 511 commands, 865 canonical receipts, 153.731347 seconds (limit 1200); runtime 377312 bytes (cap 393216).

No host output, security, console, file, forwarding, provider, original artifact/JAR/class/resource, world, EULA, or Done behavior is added. Parent original52 replay remains deferred.
