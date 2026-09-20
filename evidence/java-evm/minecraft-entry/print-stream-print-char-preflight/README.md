# Bounded `PrintStream.print(char)` corrected-image gate

This generated-only LOCAL preflight derives from accepted
`print-stream-println-string-preflight` (`3dee801e7`). It changes only bootstrap
image83 (`java/io/PrintStream`) in the fixed 91-image order: retained
`println(String)` performs its balanced monitor/null probe and stores the exact
String reference, while `print(char)` stores exactly one UTF-16 code unit in a
second private field. There is no host output, character encoding, concatenation,
throwable printing, provider factory, original artifact, world, or Done claim.

## Critical classfile correction

The earlier 305-byte candidate was invalid: it used the field descriptor `C` as
the `print` method descriptor. It must not be used as an engine image or gate
basis. The durable producer `bootstrap/build_print_stream.py` and
`bootstrap/java/io/PrintStream.class.hex` now pin the valid 317-byte Java-8
class:

- field `print`: `C`;
- method `print`: `(C)V`;
- SHA-256: `af8d5e198451494ab7a20f6f92c1559dedc3591a082268e50b9b6c9ccca16017`;
- EVM keccak256 leaf: `3731cc740c09a9df0c76d9775252bff86b931e928d443a2e340f9d7076deca45`.

`tools/verify_source.py` parses the entire member table and exact Code
attributes, requires the two fields and all three method descriptors, and
mutates the `print` descriptor index to bare `C` to prove rejection. The stale
305-byte SHA and correction are retained in
`results/rejected-invalid-print-descriptor.json`; Java-8 `javap` output is in
`results/javap-printstream.txt`.

The corrected image is injected into both the derived pre-layout source and the
selected-cleanup engine. It alone replaces leaf83; the corrected bootstrap root
is `09a9cc5db29c035f2b4ca32375d09f7ac55706628773579449a9bceff612f636`.
`h[0]` remains the runtime-derived Object leaf and every other image/root-order
commitment remains parent-derived.

## Cap measurement and gate

A current corrected-image pre-layout build measured 393308 runtime bytes, 92
bytes above the unchanged 393216 cap. The verifier allows only ten exact
private unchecked regions comprising twelve already-bounded loops (parsed
methods/names, bounded byte copies, raw-class accumulation, and <=8 checkpoint
arguments); its selected engine measures **393185/393216** bytes, leaving 31
bytes. The exact source and hashes are in `results/cap-measure.json` and
`build-pins.json`.

The final generated-only full gate passed in 607.788 seconds (<1200), with 591
commands, 180 terminal worlds, and 10007 independently canonicalized receipts.
The focused NUL, ASCII, unpaired-surrogate, and replacement-char states agree
across q1, q7, and direct/q4096, and each is checked through a reopen
verification. Their exact packed UTF-16 cells are retained in
`results/focused-char-summary.json`; the full result and receipt verification
are in `results/gate-summary.json` and `results/canonical-receipts.json`.

All raw38/285489, diagnostic129, native13, frames, checkpoint/Head, compiler,
EVM accounting, and gas limits are pinned. This is a bounded PrintStream image
correction, not general Java I/O or Minecraft readiness.

## Reproduction

From repository root, use fresh ignored paths (the committed stage is already in
its built state):

```sh
python3 evidence/java-evm/minecraft-entry/print-stream-print-char-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/print-stream-print-char-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/print-stream-print-char-preflight/tools/build.py build/java-diff-mc-print-stream-print-char-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/print-stream-print-char-preflight/tools/generate_fixtures.py build/java-diff-mc-print-stream-print-char-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/print-stream-print-char-preflight/tools/gate.py build/java-diff-mc-print-stream-print-char-build-repro-LOCAL build/java-diff-mc-print-stream-print-char-fixtures-repro-LOCAL build/java-diff-mc-print-stream-print-char-gate-repro-LOCAL
```
