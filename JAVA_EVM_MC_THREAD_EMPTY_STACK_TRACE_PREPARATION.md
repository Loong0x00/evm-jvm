# Java-on-EVM Minecraft bounded `Thread.getStackTrace()` stage

Accepted `parent-bd1760569` reaches an unchanged original-JAR blocker at
`StatusLogger.logMessage` PC12: `Thread.getStackTrace()` yields a
`StackTraceElement[]`, which Log4j only scans to choose an optional caller
location. This is a narrow generated-only candidate, **not** Minecraft
execution or an accepted general stack-trace facility.

## Candidate scope

- Replace bootstrap image slot 50, `java/lang/Thread`, with a 565-byte genuine
  Java 8 `-g:none` image (SHA-256
  `7cd2263dd09f01a4e0d69601c0db63704eadf5461709f3b93b718352589163fd`).
- Append `java/lang/StackTraceElement` at slot 90 (the 91st image), a 142-byte
  Java 8 image (SHA-256
  `93235091dce65ab80a51b88fc294533e0a65bc2eefe0c02d052892bcde103a3c`).
- `Thread.currentThread().getStackTrace()` executes guest Code and creates a
  fresh non-null zero-length `StackTraceElement[]`. The class is present only
  for the canonical array leaf; no element is created and no real frames,
  constructor, `getClassName`, scheduling, second thread, or host callback is
  modeled.
- Raw replacement of the appended class and unsupported
  `StackTraceElement` construction or `getClassName()` references reject before
  publication.

The ordered 91-image commitment remains runtime-derived as
`keccak256(abi.encode(DBOOT,h))`, yielding
`c8f6dad01aaba24b276dd90b4b4bf84ca74c9ae0586612bffa675f66fe7001fe`.
`root-commitment.json` lists every leaf. Exact static image hash leaves are
checked against their materializing functions; there is no substituted final
root constant.

## Layout measurement

The direct two-image candidate was 395621 bytes, above the fixed 393216-byte
LOCAL deployment cap. The gated source is 393157 bytes (59-byte headroom),
SHA-256 `20632e87ced24bcb91eb2370f54a2d5de7dec12e0526f1320b411088b0a450f5`.
Recovery is restricted to exact verified static image leaf hashes and removal
of three unreferenced private interpreter parameters. It preserves root
construction, image Code, error precedence, limits and execution paths.

Raw class caps remain 37/282358; native bindings remain 13; diagnostics rise
only from 127 to 128 for the legal 91-image total. Exception kinds14,
frames128, selected-resource, CP/Code, 1MiB checkpoint, Head, compiler, gas
and reserve limits are unchanged.

## Gated candidate evidence

`evidence/java-evm/minecraft-entry/thread-empty-stack-trace-preflight/`
contains pinned sources, artifacts, root/layout commitments and reproducible
summaries. Its generated retained gate passed 480 commands in 534.248 seconds
with 8329 canonical receipts. The focused q1/q7/direct/reopen chain agrees at
51 Java and 4 internal steps, epochs 51/8/1, root
`0x6432a63c75132d056033aed54b110923304767e396d674cb0bfd534bc9ee16bf` and
opaque payload SHA-256
`95996f8dd8c7362a2c255d36603243f32b6106bec58b5f46a04f3a94ba08bb3c`.

This evidence has no original JAR/class/resource, provider/factory/world,
EULA, listener, Minecraft execution or Done claim. It awaits normal parent
review/integration; it does not alter accepted profiles.
