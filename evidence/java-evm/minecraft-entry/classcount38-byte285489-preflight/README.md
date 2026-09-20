# Generated raw38 / byte285489 source stage

This generated-only capacity stage derives from accepted 91-image evidence
`parent-0f8778735` at commit `95cc5d977`. It changes only selected raw-class
count `37→38`, aggregate raw bytes `282358→285489`, and the read-only
checkpoint diagnostic class bound `128→129`. The fixture compiler is pinned to
the accepted generated `thread-empty-stack-trace-preflight` corpus and only
adds the count-39 refusal and the two exact 38-class aggregate-byte witnesses.

All 91 ordered bootstrap images and their bytes/positions, native13,
String-local binding10, exception kinds14, frames128, selected-resource
count1/4096, checkpoint1MiB, Head32768, compiler/toolchain, and every other
limit are source-pinned. The root is still calculated by the runtime as
`keccak256(abi.encode(DBOOT, h))`; this stage records its new domain-derived
91-image root `5aa3c7604fb3742bf27b9aa7237f587292f9373a1143529ff4829e6fc0bcdae8`,
not a hard-coded root in the interpreter source.

The rebuilt runtime is exactly `393157 / 393216` bytes (59-byte headroom),
SHA-256 `40f8a862c49b5b05246ca7fd81f7184a96c0810129e9abe4f7be0c20269962bd`.
The coordinator remains 5394 bytes. `parent-input.json` hashes only the
whitelisted generated/runtime sources used for the delta; it does not open an
original artifact, JAR, class, resource, checkpoint, or world.

The generated raw38 q1/q7/direct/reopen chains agree at 152 Java and 2
internal steps, epochs `152/22/1`, machine root
`0xc00ab69d590f3ecb2e70dca560c32d55fdd3b4114803065469c3676fcdf7e1b0`, and
opaque payload SHA-256
`971a15210ad4844aa38c14defe2d77b3b914f1ea495a74533e9b5f0a83583785`.
Raw39 is refused before mutation by the product driver, then by coordinator
`MR0Error(2)` through a disposable driver, and by the engine as
`LinkError(1,39)` only through a disposable widened coordinator. Exactly
285489 aggregate bytes is admitted by coordinator and reaches the ordinary
engine reserve refusal; 285490 is atomically refused as `MR0Error(12)`.
Both aggregate fixtures have 38 classes and largest class sizes 233007/233008,
well below the separate 262144-byte DI0 class input limit.

The focused plus retained generated gate completed 127 result rows, 480
commands, and 8333 canonical receipts in 511.676 seconds (fixed cap 1200).
It uses only trusted generated Java-8 sources. No original artifact/JAR/class/
resource, StatusData, provider construction, factory, world, or Done input is
read or claimed. Parent alone appends/runs genuine `StatusData` and performs
the accelerated replay.

Reproduce with pinned local tools only:

```sh
python3 evidence/java-evm/minecraft-entry/classcount38-byte285489-preflight/tools/build.py build/java-diff-mc-classcount38-byte285489-build-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount38-byte285489-preflight/tools/generate_fixtures.py build/java-diff-mc-classcount38-byte285489-fixtures-LOCAL
python3 evidence/java-evm/minecraft-entry/classcount38-byte285489-preflight/tools/gate.py build/java-diff-mc-classcount38-byte285489-build-LOCAL build/java-diff-mc-classcount38-byte285489-fixtures-LOCAL build/java-diff-mc-classcount38-byte285489-gate-LOCAL
```
