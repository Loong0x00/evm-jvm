# Result

- Image83 only: 243-byte Java 8 `PrintStream.println(String)` performs a balanced
  `monitorenter`/`monitorexit` null probe, then stores the exact guest `String`
  reference in private `println`. Null takes guest NPE before overwrite.
- Image SHA-256: `060f9aa1e9c6415ae6d6462678fdb19b8a7d0736e742821fa3130191eb497667`;
  bootstrap root: `ae89a2429eda938c946350008b1246f9a9cae9719ac8ba434db9838f2237edf7`.
- Runtime: 393206/393216 bytes (10-byte headroom), SHA-256
  `0639b249ebaf915836da08da734ba538da0a080d7425cc7d408aa9256694eecf`.
  `h[0]` stays dynamic; image83 is the sole `DBOOT_PRINT_STREAM` leaf; exactly
  three parser-bounded comparison loops use `unchecked` arithmetic.
- Fresh generated-only full gate passed in 667.571s (<1200s), with 9879
  canonical receipts. Empty/ASCII/surrogate/replacement/null q1/q7/direct/reopen
  chains agree; null retains the prior field reference.

The earlier 243-byte recovery artifact was rejected: its constructor CP entry
recursed to `PrintStream.<init>`. The corrected CP entry targets `Object.<init>`;
its durable failure/correction record is `results/recovery-self-constructor-failure.json`.

No original/JAR/resource/provider/world/Done input or claim; no host output or
other `PrintStream` overload is added.
