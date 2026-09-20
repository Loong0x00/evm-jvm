# Bounded `PrintStream.println(String)` generated-only correction

This LOCAL generated-only stage derives from accepted
`string-builder-append-char-preflight` (`c5a9e702a`). It replaces only bootstrap
image83 (`java/io/PrintStream`) in the unchanged 91-image order. The 243-byte
hand-assembled Java 8 image has a public no-argument constructor and exactly
one member, `println(String)`. Its ordinary guest Code performs
`aload_1; monitorenter; aload_1; monitorexit; aload_0; aload_1; putfield; return`.
The balanced pair makes null take ordinary guest NPE before the exact supplied
reference is stored in private `println`; it emits no host stdout/stderr and
implements no other `print`/`println` overload.

`bootstrap/build_print_stream.py` is the durable exact-image producer. It emits
243 bytes with SHA-256
`060f9aa1e9c6415ae6d6462678fdb19b8a7d0736e742821fa3130191eb497667`
and EVM keccak256
`03915016b845257751cbb6de613d95effdc3c84cd4b59216de7783d0ca95ff2e`.
The source verifier proves CP#1 is `Methodref java/lang/Object.<init>`, so the
constructor does not recurse into `PrintStream.<init>`. It mechanically derives
the engine from the accepted parent: `h[0]` remains
`keccak256(_bootstrapObject())`; image83 alone uses `DBOOT_PRINT_STREAM`; and
only three finite parser-bounded comparison loops use `unchecked` arithmetic.
The recomputed bootstrap root is
`ae89a2429eda938c946350008b1246f9a9cae9719ac8ba434db9838f2237edf7`.

The reproducible runtime is 393206 bytes, 10 bytes below the unchanged 393216
cap (baseline 393208), with SHA-256
`0639b249ebaf915836da08da734ba538da0a080d7425cc7d408aa9256694eecf`.
Image count91, raw38/285489, diagnostic129, native13, all quotas, compiler,
checkpoint/Head limits, and EVM accounting remain pinned.

Fresh trusted generated fixtures cover non-null empty, ASCII, surrogate-pair,
and replacement lines plus a caught-null case. Their q1/q7/direct/reopen chains
use a read-only checkpoint decoder to prove the sole image83 field preserves
the expected packed guest reference; the null case preserves the prior value.
Other `print`/`println` forms refuse atomically. The full focused-plus-retained
generated gate completed in 667.571 seconds (limit 1200) and canonicalized
9879 receipts. Durable pins and concise outputs are in `build-pins.json` and
`results/`; generated worlds remain disposable under ignored `build/`.

The prior 243-byte recovery artifact used `Methodref #1` with class index3
(`PrintStream`) instead of class index4 (`Object`), so its constructor recursed.
A fresh System.err probe exposed that defect; the exact rejected bytes, outcome,
and one-byte CP correction are retained in
`results/recovery-self-constructor-failure.json` rather than being silently
lost.

No original artifact, JAR, class, resource, StatusData, provider factory,
world, or Done input/claim is included. This does not claim a general
PrintStream, throwable output, Minecraft startup, or Done.

Reproduce from repository root using fresh ignored output paths:

```sh
python3 evidence/java-evm/minecraft-entry/print-stream-println-string-preflight/tools/verify_source.py --prebuild
python3 evidence/java-evm/minecraft-entry/print-stream-println-string-preflight/tools/build.py build/java-diff-mc-print-stream-println-string-build-final-LOCAL
python3 evidence/java-evm/minecraft-entry/print-stream-println-string-preflight/tools/generate_fixtures.py build/java-diff-mc-print-stream-println-string-fixtures-final-LOCAL
python3 evidence/java-evm/minecraft-entry/print-stream-println-string-preflight/tools/gate.py build/java-diff-mc-print-stream-println-string-build-final-LOCAL build/java-diff-mc-print-stream-println-string-fixtures-final-LOCAL build/java-diff-mc-print-stream-println-string-gate-final-LOCAL
```
