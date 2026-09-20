# Bounded Java 8 `Thread.getStackTrace()` source stage

This generated-only stage derives from accepted `parent-bd1760569`. It replaces
bootstrap slot 50 (`java/lang/Thread`) with the 565-byte Java 8 `-g:none` image
`7cd2263dd09f01a4e0d69601c0db63704eadf5461709f3b93b718352589163fd`, and
appends the 142-byte `java/lang/StackTraceElement` image at slot 90
(`93235091dce65ab80a51b88fc294533e0a65bc2eefe0c02d052892bcde103a3c`).

`Thread.currentThread().getStackTrace()` executes ordinary guest Code and
allocates a fresh non-null zero-length `StackTraceElement[]`. The array leaf is
canonical and bootstrap-owned. There is no frame capture, element construction,
`StackTraceElement` API, scheduler, second thread, host callback, provider,
world, or Done claim. A raw leaf replacement and `getClassName()` member
reference refuse before a Head is published.

The 91-image root remains runtime-derived:
`keccak256(abi.encode(DBOOT, h))`, with ordered root
`c8f6dad01aaba24b276dd90b4b4bf84ca74c9ae0586612bffa675f66fe7001fe`.
`root-commitment.json` independently lists every hash. Exact static leaf hashes
avoid duplicate code materialization only; they are checked against the actual
materialized image functions. No final root constant is embedded.

Direct staging measured 395621 bytes, over the fixed 393216-byte LOCAL cap.
The verified layout recovery is 393157 bytes (59 bytes headroom), SHA-256
`20632e87ced24bcb91eb2370f54a2d5de7dec12e0526f1320b411088b0a450f5`.
It removes only three unreferenced interpreter parameters and uses the exact
static leaves described above. All raw37/282358, native13,
diagnostic128, exception kinds14, frames128, resource, checkpoint, Head,
compiler, gas/reserve and opcode limits stay fixed.

The focused `ThreadEmptyStackTraceMain` q1/q7/direct/reopen chains agree at
51 Java and 4 internal steps, epochs 51/8/1, machine root
`0x6432a63c75132d056033aed54b110923304767e396d674cb0bfd534bc9ee16bf`,
and opaque payload SHA-256
`95996f8dd8c7362a2c255d36603243f32b6106bec58b5f46a04f3a94ba08bb3c`.
The generated retained gate completed 480 commands in 534.248 seconds and
canonicalized 8329 receipts. It does not read an original JAR/class/resource or
run Minecraft.

Reproduce with pinned local dependencies only:

```sh
python3 evidence/java-evm/minecraft-entry/thread-empty-stack-trace-preflight/tools/build.py build/java-diff-mc-thread-empty-stack-trace-build-LOCAL
python3 evidence/java-evm/minecraft-entry/thread-empty-stack-trace-preflight/tools/generate_fixtures.py build/java-diff-mc-thread-empty-stack-trace-fixtures-LOCAL
python3 evidence/java-evm/minecraft-entry/thread-empty-stack-trace-preflight/tools/gate.py build/java-diff-mc-thread-empty-stack-trace-build-LOCAL build/java-diff-mc-thread-empty-stack-trace-fixtures-LOCAL build/java-diff-mc-thread-empty-stack-trace-gate-LOCAL
```
