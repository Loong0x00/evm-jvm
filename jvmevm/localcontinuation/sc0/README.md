# LOCAL MC-SC0 continuation transport

Package `sc0` is the bounded, opaque Go transport for the frozen MC-SC0
`String0Interpreter` profile. It copies the accepted TL0 durability and API
contract into a new namespace while loading only `sc0assets.Artifact()`:

* the embedded compiler-checked artifact must name `String0Interpreter` and must
  contain the exact frozen four-method ABI and nonempty deployed runtime;
* the oversized runtime is installed once at LOCAL address
  `0x4a564d45564d53433052554e54494d4500000001`; this is not CREATE or standard
  deployment evidence;
* unchanged class bytes, entry strings, signed `int32` arguments, opaque
  checkpoints, and opaque `SliceResult.JavaClass` bytes are only ABI-transported;
* production Go contains no Java class, String, heap, graph, checkpoint-machine,
  or constructor parser and has no fallback artifact/runtime;
* calls retain the accepted fixed dev-chain context, 1..1,000,000,000 gas range,
  one-MiB checkpoint limit, owner/epoch/root CAS, and exact head/event ABI.

`Open` initializes only an empty directory or reopens format 1 marked
`JVMEVM-MC-SC0-DISK-STORE-1`. It resolves an explicitly requested root alias,
checks marker/manifest/owner/context/address/code hash before opening LevelDB,
and on reopen loads committed trie code without reinstalling it. Publication is
checkpoint write+file/directory fsync, trie commit+database sync, then an owned
manifest temporary, atomic rename, and directory fsync. Existing orphan blobs
are synced again. Failures before manifest publication restore the old root;
ambiguous post-rename failure poisons the session until close/reopen. A failed
publication exposes diagnostic gas only, never speculative result/checkpoint/log
output. Reads are bounded and internal linked entries are refused.

The trusted test corpus pins exactly 24 Java-8 roots (eight each in `SC0Chars`,
`SC0CopyIntern`, and `SC0Flow`) and checks clean Java 8 and Java 21 oracles. It
runs 24 one-call controls, q1 and q7 for the frozen ten roots, and loop64 q7: 21
actual continuation chains. It also reruns all 24 accepted TL0 roots with their
ten q1/q7 selections and all three accepted LC0 raw bundles under one/q1/q7/
internal1, comparing outcomes and counters rather than cross-profile roots.
Durable tests cover old-root restoration, ambiguous reopen, existing-blob sync,
root aliases, no reinstall, a genuine mid-copy restart, and pending null String
constructor/EIIE-cause restart. Detailed malformed/profile/quota/state probes are
owned by the separate SC0 verifier.

The corpus observes defensive copying, copy identity/hash/backing behavior,
constructed-receiver intern self-return, earlier-handle sorted insertion, full
content discrimination under a hash collision, initializer and Throwable graph
effects. It does not fabricate a live full-pool miss: with 1,024 ordinary objects
that state has no extra legal noninterned receiver. Nor does it claim maximum
field/element states that exceed the one-MiB publication bound.

Ordinary cases use at most 4,096 dispatch units, 256 slices, 100,000,000 gas and
an external 30-second call watchdog. Dedicated copy/quota boundaries may use up
to 65,536 units and 1,000,000,000 gas with 120-second calls; the full gate has a
20-minute/4-GiB RSS watchdog. There is no RPC, P2P, VFS, Minecraft execution,
EULA acceptance, server-readiness claim, or listener surface.
