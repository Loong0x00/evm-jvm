# MR0 owned Session COPY preflight

**Status: bounded generated positive transport evidence only; unaccepted.** This is a
Go-only COPY under `evidence/java-evm/main-root/session-preflight/`, based at
`6b10a6f25`. It does not edit accepted `jvmevm`, core, quotas, ABIs, artifacts,
Solidity, Makefiles, or any Minecraft/original-JAR path.

## What this COPY does

`transport/session.go.txt` is an owned normal-StateDB/trie/LevelDB Session driver,
not a reflection or private reach-through to CB0 Session. It uses only ordinary
public EVM calls for AS0, ZI0, DI0 and the pinned MR0 coordinator. It accepts the
fixture ZIP as opaque AS0 input; ZIP indexing, DEFLATE/CRC/FINAL page reads and all
class handling remain EVM-side. It does not parse ZIP/class bytes, inflate, evaluate
Java, inject decoded pages, use raw-class APIs, or recover a failed trace.

The exact repaired artifacts are pinned in the copied driver before installation:

* engine: 294795 bytes, SHA-256
  `5cd308971f49e815ee8adf864133c05f44e675ae6efe6cabe771bd89ad8fb875`, Keccak
  `2c841e15e382f6433adfbce3fddc225a5efeed5d0d87727c1eac4a0106f9d79f`;
* coordinator: 3547 bytes, Keccak
  `06f642301333b90429e749951c7855cf954a379848d4643ef758f7853ff39a8c`.

The engine is `SetCode` only at
`0x4d52304d41494e454e47494e4500000000000001`, marked LOCAL initial-state
installation with nonce zero. AS0 and every other controller use ordinary CREATE.
No CREATE/standard-chain claim is made for the oversized engine.

The COPY has a fixed ordinary 100M gas maximum and uses `vm.EVM.Cancel` timers for
each owned CALL/CREATE (30 seconds), rather than merely recording elapsed time. It
stages an opaque checkpoint, checks its Keccak root and typed slice/event/head before
publication, writes/syncs the blob before its matching trie/manifest root, and poisons
after a post-rename directory-sync ambiguity. Reopen validates a real non-symlink
store tree, regular marker/manifest with unknown-field/trailing-data refusal, route
nonces/code pins, package/instance, typed lifecycle and persisted CP/head roots before
LevelDB open. Observer reports live outside the Session namespace and are never
reopen authority.

Each successful slice requires canonical outer and engine ABI re-encoding, reserved
`result == 0`, one exact nested `CheckpointCommitted`, matching instance/epoch/roots/
lifecycle/counters, and a matching EVM `head`. Java exceptions require nonzero
`javaRef`; the manifest retains it instead of silently dropping it. Returned nested
logs are defensively copied before observer recording and only recorded after the
blob/trie/manifest publication succeeds.

## Fresh generated gate

The complete fresh run is retained at
`evidence/java-evm/main-root/session-preflight/results/final3/` (including LevelDB,
trie/code data, opaque checkpoint blobs, all per-slice public receipts, external
process receipts, compiler output and watchdog). It rebuilt sources with pinned solc
0.8.30, generated Java 8 test-only fixtures/oracles, and ran all 12 worlds under the
canonical watchdog:

* watchdog: exit 0, **191.677683 s**, sampled process-group peak **6488064 B**,
  neither 20-minute nor 4 GiB limit hit;
* `positive`: q1/q7/direct epochs **319/46/1**, `VOID`, 319 Java/3 internal;
* `args=null` rebind: **7/1/1**, `VOID`, 7/2;
* `args=new String[1]` rebind: **24/4/1**, `VOID`, 24/2;
* uncaught `RuntimeException`: **19/3/1**, typed Java exception, 18/5,
  nonzero JavaRef 3 and dynamic `java/lang/RuntimeException`.

For all fixture triples, the strict fresh verifier checks the same guest outcome,
reserved zero, code pins, EVM re-open head, terminal blob integrity, all DI0 reads
<=4096, per-call gas/time receipts, exactly one nested log per slice, three external
process receipts, and byte-identical opaque terminal checkpoint tail after the fixed
280-byte envelope. It also preserves the real direct-terminal-exception fact: the
finish process exists in external receipts but does not fabricate a third manifest
PID publication. The verifier result is `{"ok":true,"worlds":12,...}`.

Reproduce only into a new ignored directory:

```sh
NODE_PATH=/absolute/path/to/pinned/node_modules \
python3 evidence/java-evm/watchdog.py build/mr0-session-watchdog.log \
  build/mr0-session-watchdog.json sh \
  evidence/java-evm/main-root/session-preflight/reproduce.sh \
  build/java-diff-mc-main-root-session-fresh
```

The wrapper rejects an existing/non-scoped output and sets an absolute TMPDIR below
that ignored output. `SHA256SUMS` and `results/final3/PINS.sha256` bind tracked source,
receipts and the fresh observer executable.

## Remaining blockers (not hidden by this preflight)

This is **not** full Session/transport acceptance. In particular, it does not yet
supply the required independently reviewed public fault matrix (after blob/trie/sync/
manifest/rename including real OS failures), concurrent stale-CAS races, malformed
ABI/tamper/schema/head/config/owner/package/binding/name/index/resource/code-pin
refusals, exact 4/65536/+1 capacity suite, page/corrupt-checkpoint metadata suite,
warm/in-memory/fresh/disk/separate-process equivalence at every start/resume/finish,
or the legal integer local-0 reuse fixture. The retained `publicationProbe` is a
self-owned observer-only after-trie rollback exercise, not evidence of that matrix.

The bounded generated fixture resource-name declarations are test configuration
assertions only; they are not a host ZIP catalogue and DI0/CB0 still validates them
against EVM index/FINAL state. No official JAR, Minecraft Java, EULA, listener, world
or Done marker was handled or executed. Parent independent source review,
rebuild/replay and any acceptance decision remain required.
