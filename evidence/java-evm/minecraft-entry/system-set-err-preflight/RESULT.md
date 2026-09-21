# Result: bounded canonical `System.setErr(PrintStream)`

- Added only public static native `System.setErr(PrintStream)` to bootstrap image44 and global binding15.
- Binding15 mutates only canonical initialized `System.err`; `System.out` remains unchanged. Null and `PrintStream` subclasses are accepted after ordinary descriptor/assignability checks.
- Focused direct/subclass/null/reset witness q1/q7/direct/reopen agrees at 209 Java / 7 internal steps. Raw exact-native `System` replacement rejects atomically.
- Runtime 375425 / 393216 bytes; 511-command, 865-receipt full gate completed in 159.293139s (limit 1200s).

No host output/security behavior, original/JAR/resource, provider/world/EULA/Done work, or original52 replay was performed. Parent replay remains deferred.
