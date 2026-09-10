# LOCAL MC-SC0 trusted fixtures

This directory pins the frozen 24-root MC-SC0 String corpus: eight roots each in
`SC0Chars`, `SC0CopyIntern`, and `SC0Flow`. Sources are compiled with
`javac --release 8 -g:none`; `manifest.json` records source and class SHA-256,
ordered bundles, entries, arguments, and exact outcomes. Every bundle is at most
four unchanged classfiles and 64 KiB.

The roots perform genuine `String(char[])` defensive-copy loops and
`String(String)` construction, UTF-16/NUL/surrogate reads, hash-cache use, distinct
identity and shared-copy behavior, category-2 caller state, literal and constructed
interning, earlier-handle insertion, equal-hash/distinct-content discrimination,
interface dispatch, null construction, recovery after failed allocations, class
initialization/EIIE then NCDFE, a 64-character copy loop, pre-constructor argument
failure, and storage through a fresh Throwable subclass before throw/catch. Their
results are effects-based, not constant-only stand-ins.

Regenerate deterministically with `./build_fixtures.py`. Harness tests byte-compare
a clean Java 8 rebuild and run all 24 roots on required Java 8 and Java 21 host-only
oracles. Java is only a trusted fixture builder and test oracle; production Go
transports raw classes and opaque EVM checkpoints and never parses or executes Java.
Synthetic Object-profile and malformed-state tests are intentionally not stock-JVM
oracles and belong to the independent SC0 verifier.
