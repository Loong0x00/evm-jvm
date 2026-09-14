# Generated ConcurrentLinkedQueue evidence

This is a generated-fixture-only LOCAL384 evidence record for source commits
`7a20245af`, `84be3fb19`, and `0e1015624`. It contains no binaries, LevelDB world,
raw original-Minecraft class, server JAR, or original-world access.

* strict stripped-Java8/reverse source verifier: 79 accepted images unchanged; Queue
  and ConcurrentLinkedQueue append at 79/80 (81 total); raw cap26; diagnostic bound107;
* deterministic build: engine 388963 bytes (within LOCAL384 =393216), coordinator4146;
  wall time 233.478s; the shell timer available in this environment does not expose RSS;
* trusted Java8 fixture oracle: queue plus retained locks both exit0;
* guest q1/q7/direct/reopen/canonical gate: queue converged 822 Java steps at
  q1=822, q7=118, direct=1 slices; locks retained at218 Java steps q1=218/q7=32/direct=1;
  both raw replacements atomically rejected; whole generated gate 61.730s.

The queue fixture uses object identities (not unsupported Integer.valueOf) and checks
FIFO duplicates, empty poll, null-add NPE, size/inherited isEmpty, iterator snapshot
across a head removal, exhaustion, and later add/poll. The narrow subset does not claim
JDK concurrent progress or broader Queue APIs. Practical array-quota OOM and all-parent
controls remain parent work.
