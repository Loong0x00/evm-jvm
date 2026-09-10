# LOCAL MC-IOE0 continuation transport

Package `ioe0` is the bounded opaque Go transport for the frozen MC-IOE0
`IOException0Interpreter` profile. It copies the accepted SC0 durability and
13-field ABI contract into a new namespace while loading only
`ioe0assets.Artifact()`:

* the embedded compiler-checked artifact must name `IOException0Interpreter` and
  contain exactly `start`, `resume`, `head`, `validateCheckpoint`, and the frozen
  `CheckpointCommitted` event;
* the oversized runtime is explicitly installed once at LOCAL address
  `0x4a564d45564d494f453052554e54494d45000001`; this is not CREATE or standard
  deployment evidence;
* unchanged class bytes, entry strings, signed `int32` arguments, checkpoints,
  and `SliceResult.JavaClass` are transported as opaque bytes;
* production Go contains no Java, String, message, cause, heap, graph, or machine
  parser and provides no fallback artifact, legacy runtime, or code reinstall;
* calls keep the fixed dev-chain context, 1..1,000,000,000 gas range, one-MiB
  checkpoint limit, owner/epoch/root CAS, and exact head/event ABI.

`Open` initializes only an empty directory or reopens format 1 marked
`JVMEVM-MC-IOE0-DISK-STORE-1`. It resolves an explicitly requested root alias,
checks marker/manifest/owner/context/address/code hash before opening LevelDB, and
loads committed trie code on reopen. Publication remains checkpoint write plus
file/directory fsync, trie commit plus database sync, then an owned manifest
temporary, atomic rename, and directory fsync. Existing blobs are synced before
reuse. Pre-publication failures restore the old root; ambiguous post-rename failure
poisons the session until close/reopen. Failed publication returns diagnostic gas
only, never speculative tuple/checkpoint/log output. Reads are bounded and linked
internal entries are rejected.

The trusted corpus pins exactly 24 Java-8 roots in three groups. It runs 24
one-call controls and q1/q7 chains for the frozen ten roots (20 chains), comparing
IOE0 outcomes, counters, and final roots. Java 8 is primary and Java 21 secondary.
The roots exercise real Throwable/I/O constructor field writes, exact String and
cause identity, virtual dispatch, VM and ordinary EIIE, rethrow, error propagation,
failed classes, and post-super escape; paired positives deliberately exclude the
unsupported VM ArithmeticException `getMessage` profile. Tests also retain all
SC0/TL0 24-root outcomes, all three LC0 outcomes, representative continuations,
new-process mid-message/cause/pending-wrapper reopen, CAS/OOG rollback/retry,
existing-blob sync, root aliases, and no reinstall. Test-only checkpoint inspection
never supplies interpreted data back to execution.

Ordinary cases use at most 4,096 dispatch units, 256 slices, 100,000,000 gas, and
30-second oracle/call watchdogs. Dedicated quota boundaries may use 65,536 units
and 1,000,000,000 gas with 120-second calls; the whole gate is externally bounded
to 20 minutes and 4 GiB RSS. This package adds no host Java fallback, VFS, file
bridge, logging, Minecraft/EULA execution, listener, or readiness claim.
