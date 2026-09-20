# Bounded non-null `PrintStream.println(String)` generated-only stage

This LOCAL generated-only stage starts from accepted
`string-builder-append-char-preflight` (`c5a9e702a`) and changes only bootstrap
image83 (`java/io/PrintStream`) in the unchanged 91-image order. The exact
239-byte Java 8 image has a public no-argument constructor and a single
non-null `println(String)` member. Its ordinary guest Code is exactly
`aload_0; aload_1; putfield; return`, retaining the exact String reference in
the sole private `println` field. It has no host stdout/stderr or byte-encoding
behavior. Null and every other `print`/`println` overload are outside this
profile.

The measured direct-store candidate was 393217 bytes, one byte over the fixed
393216 cap. The fitting source-equivalent layout recovery is restricted to
three private byte-slice comparison loops. Their existing parser-validated
finite offsets and lengths make overflow unreachable, so their `unchecked`
placement removes only redundant Solidity overflow branches; it changes no
guest image, root, limit, error precedence, or supported execution path. The
pinned compiler produces 393200 bytes (16-byte headroom).

`h[0]` remains `keccak256(_bootstrapObject())` and all unchanged historical
leaves remain runtime-derived. Only image83 is an exact
`DBOOT_PRINT_STREAM` leaf; no Object leaf, folded whole root, or other
historical-image commitment is allowed. The strict verifier reconstructs the
engine from the accepted parent, recomputes all 91 ordered root leaves, and
proves that only leaf83 changed.

Trusted generated fixtures cover non-null empty, ASCII, surrogate-pair, and
replacement lines q1/q7/direct/reopen. A read-only checkpoint decoder proves
image83's sole field equals the exact packed guest String reference retained by
each fixture. `println()`, `println(int)`, and `print(String)` remain atomic
CallError refusals. The full focused-plus-retained generated gate completed in
597.792 seconds and canonically verified 9818 receipts.

Image count91, raw38/285489, diagnostic129, native13, all quotas,
compiler/toolchain, checkpoint/Head limits, and EVM accounting remain pinned.
No original artifact, JAR, class, resource, StatusData, provider factory,
world, or Done input/claim is included. This is not throwable output, a general
PrintStream, Minecraft startup, or Done.

Reproduce from repository root:

```sh
python3 evidence/java-evm/minecraft-entry/print-stream-println-string-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/print-stream-println-string-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/print-stream-println-string-preflight/tools/build.py build/java-diff-mc-print-stream-println-string-build-final-LOCAL
python3 evidence/java-evm/minecraft-entry/print-stream-println-string-preflight/tools/generate_fixtures.py build/java-diff-mc-print-stream-println-string-fixtures-final-LOCAL
python3 evidence/java-evm/minecraft-entry/print-stream-println-string-preflight/tools/gate.py build/java-diff-mc-print-stream-println-string-build-final-LOCAL build/java-diff-mc-print-stream-println-string-fixtures-final-LOCAL build/java-diff-mc-print-stream-println-string-gate-final-LOCAL
```
