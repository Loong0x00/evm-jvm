# MC-first MarkerManager platform-map COPY preflight

**Candidate only: generated Java-8 fixtures, not an accepted runtime/profile and
not original-JAR/Minecraft execution.**  This derivative of `4cf97854e` is based
at `52d973017`.  It has no original archive argument; only parent owns unchanged
server selection/resumption.

## Narrow implementation

Four owned, non-overridable bootstrap appends are `java/util/Map`,
`java/util/concurrent/ConcurrentMap`, `java/util/AbstractMap`, and
`java/util/concurrent/ConcurrentHashMap`.  The last has the ordinary hierarchy
`extends AbstractMap implements ConcurrentMap, Serializable`.  `Object.equals`
is also an owned ordinary Java identity method; a dynamic String key uses the
existing String override and a custom key uses its own Java override.  There is
no host map, key evaluator, Marker/Log4j substitute, registry, locking, or
thread/concurrency claim.

`ConcurrentHashMap` is Java-8 source compiled by `bootstrap/build_platform_map.py`
and pinned as a raw bootstrap image.  It holds `Object[] keys`, `Object[] values`,
and an integer count, scans with `keys[i].equals(key)`, doubles arrays when full,
and resets them on `clear`.  It exposes only no-arg construction, get,
putIfAbsent, containsKey, clear, plus test-adjacent put/size/isEmpty.  Null key
or value takes the ordinary guest NPE path.  It is a single-guest-thread linear
map, not a general Map implementation or ConcurrentHashMap linearizability
claim.

The program keeps every old bootstrap position.  Since Runnable may be supplied,
`Program.classClass` records `at + (suppliedRunnable ? 33 : 34)` and the arena
uses that stored slot; the four map images are appended after it.  User raw
classes named by the map substrate are rejected before use.  No duplicate/cache
or ABI weakening is involved.

## Pins and limits

Solc is `0.8.30+commit.73712a01.Emscripten.clang`, optimize 200/viaIR/Cancun,
metadata off.  Engine runtime is 310375 bytes, SHA-256
`df1418eae9dbdad7fe455ea6b8d3d1270be20527f84aa18837b80351985c2f70`, Keccak
`edc205611814164dea1c67b9c62f5de9ba5ad39e6126a87720fcf1323a238c30`.
Coordinator runtime is 3547 bytes, Keccak
`213d900ca684872adf26d842e321ea11301256486fd7a25c7c8d11161120a25f`.
The exact LOCAL initial-state engine is
`0x4d434d41524b45524d4150000000000000000001`; coordinator/resources remain
ordinary CREATE.  Domains use `MC-MARKER-MAP-PREFLIGHT/.../v1`; old checkpoint
compatibility is intentionally not claimed.

The candidate preserves 16 raw images/262144 bytes, CP4096, Code65535, existing
heap/VFS/frame/1MiB checkpoint limits, 100M ordinary gas with 25M reserve, 30s
and 320KiB runtime.  It uses no 1B call or quota increase.

## Fresh generated opaque evidence

`run-smokes.py OUT` rejects an existing OUT, uses an absolute private TMPDIR and
per-command 20-minute/4GiB process-group watchdog (file-backed output and
`start_new_session`), then runs generated Java through ZIP -> AS0 -> ZI0 -> DI0
metadata/DEFLATE/CRC/final <=4096-byte reads -> coordinator/engine.  The host
JDK run is a TEST-only oracle.

Fresh evidence in `actual-receipts/` records 11 watched commands, 251.185517s
aggregate and 866557952B maximum sampled group RSS.  `MapMain` catches the three
actual guest NPE cases, tests equal distinct custom/String keys, prior-value and
reference alias behavior, a 4-to-8 growth, clear and interface dispatch.

* q1 reaches VOID after 1397 Java/9 internal steps, 1397 durable epochs; q7
  reaches the same machine root after 1397/9 and 200 epochs.  Each is reopened
  by a separate driver process and has retained final head/root receipts.
* q4096/direct is retained as an ordinary-cap failure, not papered over:
  `LC0ControlError(7)` at 73548878 gas, before checkpoint and with unchanged
  EVM root.  It needs no cap increase; direct terminal equivalence is therefore
  an explicit gap.

Retained hashes, watchdogs, opaque ZIP, raw start refusal, process receipts and
final durable heads are listed in `actual-receipts/SHA256SUMS`.  These results do
not process an original class/JAR and do not establish Minecraft, EULA, world or
Done progress.
