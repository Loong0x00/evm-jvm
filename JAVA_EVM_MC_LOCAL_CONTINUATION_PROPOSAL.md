# LOCAL monolith continuation and virtual-platform proposal

Status: **architecture proposal only**. This document does not freeze a production
stage, implement continuation, execute Minecraft, accept the EULA, open a listener,
or establish Java SE/Minecraft compatibility. It is based on repository commit
`a6f9646` and the selected artistic target: unchanged official vanilla Minecraft
server 1.12.2, Java 8, through the genuine guest-produced startup marker. Standard
CREATE deployment, stock transaction budgets, a complete Java SE implementation,
and general parallel thread scheduling are deliberately not prerequisites for this
LOCAL route.

The recommendation is a separate experimental **LC0 local checkpoint kernel**
derived from the accepted monolith. It should first make the current VM state
canonical and resumable for three small trusted fixtures. It should not add a VFS,
threads, a JAR loader, or Minecraft in the same slice. Once that state boundary is
proved, the workload-needed VFS and cooperative scheduler can use it without
inventing a second continuation mechanism.

No Minecraft bytecode was executed for this proposal. Static `javap` inspection was
performed only after the local server JAR matched all three pins: 30,222,121 bytes,
SHA-1 `886945bfb2b978778c3a0288fd7fab09d315b25f`, and SHA-256
`fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e`.
The JAR remains ignored at its existing inventory-worktree path and is not
redistributed here.

## 1. Source-derived baseline

### The monolith resets every `Run`

The checked-in `JVMSubsetInterpreter.runtime.hex` decodes to **154,839 bytes**,
SHA-256 `dfc81dbbea8253c644be2532a809a417bb40cd07eaca8ab5be72a84721eae929`.
The Solidity source is 6,090 lines. Both public entry points are `pure` and return
only an `int32`:

* `interpret(bytes,string,int32[])`; and
* `interpretClasses(bytes[],string,string,int32[])`.

`interpretClasses` accepts at most 64 user classes. It parses and appends bootstrap
classes, allocates caches, and enters `_execute`. `_execute` creates all mutable
Java state in EVM **memory** on every invocation:

* `Frame[128]`, with class/method, current PC, call PC, stack pointer, tagged stack,
  locals and initialized bits, constructor/initializer/continuation flags, root
  entry state, and `thisHandle`;
* static tagged cells and class initialization state 0/1/2/3, plus the separate
  `initializerStarted` vector;
* a shared one-based heap-handle namespace, where 0 is null, for at most 1,024
  ordinary arrays, 1,024 ordinary objects, 256 exception objects, and one emergency
  OOM object; arrays are capped at 65,536 elements each and 262,144 total ordinary
  array elements, while objects are capped at 1,024 fields each and 65,536 total
  ordinary field slots;
* object/array class and shape tables, monotonically increasing `nextHandle`, and
  ordinary allocation counters;
* the exception arena, including `PendingException(active,kind,ref,faultPC)`,
  emergency OOM identity, exception counters/layouts, and the same heap tables; and
* hierarchy, member, handler, predecode, object-layout, and field-resolution caches.

No one of these values is contract storage. A normal int return discards them all;
an uncaught recognized Java exception returns only a canonical revert kind to Go;
an EVM revert/OOG discards the entire call. A later `RunClasses` starts with zeroed
statics, uninitialized classes, no frames from the prior run, and a fresh heap.
The current implementation's “initialization continuations” are Java-execution
frames within one call, not cross-EVM continuations.

The Go runner reinforces that lifecycle. `jvmevm.run` creates a new
`runtime.Config` without `State`, calls `runtime.Execute`, ignores the returned
`StateDB`, and ABI-decodes one `int32`. `runtime.Execute` creates an account named
`contract`, directly installs the oversized code with `State.SetCode`, and invokes
`EVM.Call`. It does not execute CREATE or a transaction state transition.

A small ignored mechanism probe, using ordinary EVM `SLOAD/SSTORE`, measured:

```text
runtime.Execute with one reused StateDB: returned 1, then 1
runtime.Call to the already-installed account: returned 2
runtime.Call with 2,000 gas: EVM OOG, retained slot value 2
next runtime.Call: returned 3
fresh runtime.Execute: returned 1
```

Thus merely passing the same `StateDB` back to **`Execute` is not a resume API**:
its repeated `CreateAccount` setup reset the storage in this probe. Addressing
already-installed code with `runtime.Call` retained storage, and the failed call
rolled back to the prior value. This proves only geth's local EVM storage/rollback
mechanism, not current-JVM continuation.

### Current reference and alias representation

Runtime values are one 64-bit payload plus a kind above bit 63 in a `uint256`.
`KIND_REF` payloads are 32-bit handles. Null is handle 0. Arrays and objects share
one handle sequence; metadata distinguishes them. Primitive/reference array cells
are `uint64`, object/static/frame cells are tagged `uint256`, and array rank/leaf
metadata decides whether a low 32-bit cell is a reference. Exception objects are
real handles in the same registry, including the lazily reserved emergency OOM
handle. Uninitialized-constructor references have their own value kind and can
alias through frame cells until constructor completion or poisoning.

This is useful for continuation because Java aliases already reduce to stable
handle numbers. It is dangerous to ABI-encode the Solidity memory structs
naively: memory assignments such as the exception arena heap and local heap
variables intentionally point to common dynamic arrays, but Solidity ABI encoding
serializes values, not memory-pointer identity. Encoding both views would duplicate
the tables; decoding could create divergent copies. A checkpoint must instead
contain exactly one canonical heap registry and references to it by handle.

### LOCAL invocation is not a signed transaction

The current local calls charge ordinary EVM opcode, memory, precompile, call, and
storage gas inside the supplied call. They do **not** include transaction intrinsic
or calldata-floor gas, block admission, CREATE/initcode/code-deposit cost, EIP-170
deployment, an EOA nonce/signature, or a receipt. `runtime.Execute`/`runtime.Call`
pass their finite `uint64` gas limit directly to `EVM.Call`.

In contrast, an Osaka-active signed state transition is subject to EIP-7825's
`2^24 = 16,777,216` maximum transaction gas as implemented by this geth version,
in addition to its block gas limit. The 154,839-byte monolith also exceeds
EIP-170's 24,576-byte deployed-code limit. A 250,000,000-gas direct local call is
therefore honest **LOCAL runtime-call evidence only**; it is not a transaction that
could be submitted unchanged, and splitting such work into signed transactions
does not waive EIP-170 or EIP-7825. The stock S0/S1/S2 track remains the separate
answer to those constraints.

No core/EVM relaxation is proposed. `core/vm/runtime/runtime.go` still has SHA-256
`822478c26ca1eb4313ab83da97576cbc4d93397f8f1cfddebbffcb6afd7d9c26`
and is byte-identical to pinned upstream `95665d5`; the repository diff contains no
changes under `core/vm`, `core/state`, `core/types`, `consensus`, or `params`.

## 2. Required local execution model

Use a distinct profile named `MC_LOCAL_MONOLITH_V1`:

1. Install the oversized experimental runtime into a local `StateDB` account once,
   exactly as an explicitly labeled harness operation. Subsequent slices address
   that code with `runtime.Call`, not repeated `runtime.Execute`.
2. Give the account a small authoritative checkpoint anchor in EVM storage:
   `(schema, instanceId, runtimeCodeHash, artifactRoot, configRoot, epoch,
   headStateRoot, lifecycle, outputRoot, authorizationPolicy)`.
3. Keep the canonical Java checkpoint in bounded, commitment-addressed pages. For
   LC0 the EVM may return the pages and the host may persist and resubmit the exact
   opaque bytes. The host must not create a frame, class ID, PC, heap handle,
   scheduler decision, VFS result, or exception state.
4. On `resume(expectedEpoch, expectedRoot, limits, pages)`, EVM code validates the
   anchor, every page and the complete canonical state; executes only its own
   deterministic transition; constructs the next pages; then atomically advances
   the storage anchor and returns the pages.
5. A successful yield is an EVM success with a new committed epoch/root. EVM OOG,
   revert, malformed input, insufficient commit reserve, or watchdog termination is
   not a yield and cannot be decoded as Java OOM, Java completion, or readiness.

This creates two persistence layers that reports must name precisely:

* **portable EVM-issued checkpoint bytes** preserve Java state between calls and can
  be copied to disk, but bytes on a host filesystem are not Ethereum state; and
* **anchored EVM state** is the account storage head/epoch in the reused local
  `StateDB`. It prevents an old otherwise-valid checkpoint from silently replacing
  the current run. A disk-backed StateDB committed at a recorded trie root is the
  eventual process-restart authority.

The current `RunClasses` has neither layer.

### Crash-safe local transport

A direct local call returns bytes to the caller; unlike a contract transaction,
return data is not a durable transaction receipt. The local driver should take a
`StateDB` snapshot before a slice, receive the EVM-issued pages, hash but not decode
them, write and `fsync` them under the returned root, and only then commit the new
StateDB trie root to its local database. If page persistence fails, it reverts the
in-memory `StateDB` snapshot and does not publish the epoch. On restart, it opens the
recorded trie root and supplies the opaque pages whose filename/root matches the
EVM anchor.

This ordering ensures either (old EVM head, old durable pages) or (new EVM head,
new durable pages). Extra unreferenced page files are harmless. The implementation
must additionally retain the parent checkpoint and deterministic transition record
until the child is durable so a crash cannot strand the only head. This is a LOCAL
storage protocol, not a claim of atomicity across a public chain and host disk.

An eventual signed-transaction design should put canonical state/pages in EVM
storage or another chain-available commitment protocol; it cannot assume large
return bytes are recoverable from a receipt. That is intentionally outside LC0.

## 3. Canonical checkpoint, not a Solidity memory dump

### Envelope and commitments

Use a strict, versioned custom encoding rather than ABI-encoding nested Solidity
structs wholesale. ABI remains the outer transport (`bytes[] pages`), while each
page is exact canonical bytes. All integers have fixed width and big-endian form;
records and sections are sorted by numeric ID; duplicate IDs, unknown required
flags, nonzero reserved bytes, overlong encodings, malformed offsets, and trailing
bytes reject. Proposed top-level fields are:

```text
magic="JVMELC01", schema:u32, instanceId:bytes32, epoch:u64
parentStateRoot:bytes32, runtimeCodeHash:bytes32
artifactRoot:bytes32, bootstrapRoot:bytes32, configRoot:bytes32
lifecycle:u8, totalJvmSteps:u64, totalPhases:u64, virtualTimeNanos:u64
activeFiber:u64, nextFiber:u64, nextHandle:u32
sectionCount:u16, section[tag:u16,length:u64,pageCount:u32,root:bytes32]...
```

`stateRoot = keccak256(domain || canonical header without stateRoot || ordered
section roots)`. Each section root commits domain, exact section length, page count,
and ordered `(pageIndex,pageLength,keccak256(pageBytes))`. A state root proves byte
integrity, not semantic validity or a valid transition; the EVM must strictly decode
and validate the old state and itself produce the anchored child transition.

Required sections are classes/statics/init, fibers/frames, heap, exception/unwind,
platform/VFS, scheduler/monitors, and output. LC0 uses one fiber and empty platform
sections but keeps their schema values explicit. Absence is canonical; it is not a
host-selected no-op.

### Raw-class and artifact provenance

For LC0, every resume resubmits the exact ordered raw-class bundle. EVM code computes
an artifact root over domain, count, each exact length, and exact bytes. It also
binds entry class, method, arguments, bootstrap class hashes, and runtime code hash
into `configRoot`. It may reparse immutable class/method/Code metadata and rebuild
pure caches each slice to avoid snapshotting the large `ClassInfo` graph. Class
indices are valid only under that exact ordered bundle and bootstrap layout. A
reordered, omitted, changed, or host-extracted replacement class must fail before
state execution.

For Minecraft, the source of truth must become the exact official JAR, not a host
list of extracted classes. EVM code must validate the registered 30,222,121 bytes
against the pinned SHA-1/SHA-256 (and an EVM-native page root), parse ZIP/manifest
and class/resource bytes itself, and bind that artifact root into every checkpoint.
A host may submit opaque pages. It may not supply class names, constant-pool offsets,
reachable methods, extracted Code, or a prebuilt world as execution metadata.
Incremental EVM-side hashing/parsing and its finite registration budget are future
measured work; this proposal does not claim the present 64-class ABI can carry the
JAR.

### Mutable state that cannot be regenerated

The checkpoint must preserve, without handle remapping:

* each class's four-state initialization value, `initializerStarted`, static tagged
  cells, and any phase needed to resume superclass/default-interface/`<clinit>`
  work; immutable hierarchy/resolution caches may be recomputed only from the bound
  bytes;
* active frame depth and every frame field, including dormant-root `entered`, PC as
  the next instruction at an instruction safepoint, invoking instruction `callPC`,
  stack occupancy/cells, local initialized bits/cells, initializer and synthetic
  continuation tags, constructor linked state, and `thisHandle`;
* one heap record for every allocated handle through `nextHandle`: kind, dynamic
  class, array rank/leaf type, exact `uint64` array cells or tagged object fields;
  cycles and repeated handles are legal and are never recursively expanded;
* ordinary array/object counts and aggregate element/field quotas, exception object
  and exception-field counters, lazy emergency OOM existence/identity, and all bits
  of primitive long/float/double payloads;
* pending exception active/kind/reference/fault PC and, once internal yielding is
  added, the exact unwind frame and handler-table cursor; and
* constructor-uninitialized aliases and poisoning state. Decoding must not turn a
  `KIND_UNINIT` alias into an initialized reference or allocate a replacement
  object.

Only live active frames are canonical; stale popped frame-array contents must be
zero/absent. Every non-null reference cell must name an allocated compatible handle,
but validation must permit aliasing and cycles. The heap is serialized once. On
resume, local Solidity memory aliases such as `heapKinds`, `arrayLeafTypes`, and the
exception arena must be reconstructed from that one registry, never decoded from
independent copies.

Method selections, constant pools, handler tables, hierarchy links, field offsets,
and default-layout templates are immutable derivatives and can initially be
recomputed under the exact artifact root. That costs local gas but reduces snapshot
malleability. If later cached persistently, cache records need their own schema and
must be checked against EVM-derived source metadata before use.

## 4. Bounded run, phases, and atomic effects

### Safepoints

The simplest LC0 safepoint is between complete JVM instructions, when the active
frame PC identifies the next opcode and no visible side effect is half-applied.
Count a faulting instruction exactly when the existing VM semantics do. A caller's
step budget cannot force a pause halfway through an indivisible `invoke*`, return,
field write, array write, allocation, monitor transition, VFS operation, or output
append.

Some current “one instruction” paths perform unbounded-for-MC helper work: member
resolution, hierarchy traversal, class initialization scheduling, multi-array
allocation, layout construction, and exception-handler scanning. Before large
inputs, introduce an internal `phase` record with bounded cursors. A phase may yield
only after committing a canonical private intermediate record and before any
repeatable Java-visible effect. Examples are `PARSE_CLASS`, `RESOLVE_MEMBER`,
`INIT_PREREQUISITE`, `ALLOCATE_ZERO_RANGE`, `UNWIND_HANDLER`, and `VFS_RENAME`.
Resumption checks the instruction start PC and phase input root; it cannot repeat an
allocation, output event, static write, handler entry, or rename.

LC0 should not phase-split all helpers. It should admit only its measured small
fixtures, require each selected current instruction to fit the slice reserve, and
revert otherwise. Later slices add a phase only when a real bounded dependency
needs it.

### Commit protocol

`resume` accepts both `maxJvmSteps` and `maxInternalPhases`. It stops before the next
unit when either limit is exhausted or the precomputed worst-case commit reserve
would be violated. `gasleft()` is a conservative gate, never a gas estimator and
never a source of Java time. At least one unit must execute for a new epoch unless
the lifecycle changes because an already-pending transition is completed.

The contract stages dirty state and output, validates the complete child state,
encodes/hashes pages, checks the expected old head again, writes the new anchor once,
and returns exactly one checkpoint result. Reentrancy is rejected. Any error before
that final success reverts storage and logs. The prior checkpoint remains usable;
intermediate EVM trace/memory is not recoverable and must not be scraped into a
checkpoint.

Lifecycle values must separate at least `RUNNABLE`, `WAITING`, `RETURNED`,
`UNCAUGHT_JAVA`, and `UNSUPPORTED`. A caller-imposed step/phase limit is a successful
`RUNNABLE` checkpoint, not a Java result. EVM OOG/revert is outside this lifecycle.

### Replay and branch authorization

A hash alone does not prevent replay. Require compare-and-swap on both anchored
`expectedEpoch` and `expectedRoot`; increment epoch exactly once per successful
child. Resubmitting a parent after its child commits fails stale-head validation,
even if every page is valid. Inputs/outbox acknowledgements additionally carry
monotonic sequence numbers and are consumed once by EVM state.

The local instance has an explicit owner/authorization policy bound at creation.
The harness sets a fixed test origin or verifies a signature over domain, instance,
current root/epoch, limits, and input root. Authorization allows paying for a
transition; it never supplies Java state. Creating a branch from an old checkpoint
requires a separate, explicitly authorized `forkInstance(oldRoot,newInstanceId)`;
it cannot mutate the live head and must be reported as a branch. A stateless export
can always be copied by its holder, so uniqueness claims apply only relative to the
anchored instance and recorded StateDB root.

Import/restart must never accept “well-formed latest state” directly into a live
instance. Normal restart loads the already-committed EVM head. A portable import
creates a new instance, verifies all pages and provenance, and requires explicit
owner authorization. A state digest is evidence, not an oracle proving that host
bytes came from valid Java execution.

## 5. Minecraft scheduling and genuine readiness

Hash-gated static inspection makes the control-flow issue concrete:

* `MinecraftServer.main` constructs `nz`, calls `nz.F()` at PC 403, registers a
  shutdown hook, and returns. `F()` constructs `Thread(this,"Server thread")` and
  calls `Thread.start()` at PC 19.
* The server thread executes `MinecraftServer.run()`: PC 1 invokes virtual `j()`.
  If it succeeds, the method loops while field `w` is true from PC 62 through a
  tick call `C()` and `Thread.sleep`, then jumps from PC 234 back to PC 62.
* `nz.j()` starts the console thread at PC 17, reads `eula.txt` and
  `server.properties`, performs the bind call at PC 535, prepares the world at PC
  950, then formats and calls Log4j with
  `Done ({})! For help, type "help" or "?"` at PC 994. Only later, if configured,
  it starts the watchdog at PC 1197 and returns true at PC 1213.

Therefore `main` returning is not server completion, and calling `Thread.start` as
a no-op would strand the real startup path. The eventual cooperative scheduler must
represent each started guest thread/fiber with stable ID, Java Thread object,
frame chain, daemon flag, lifecycle, wake condition, and pending exception. A
fixed deterministic round-robin queue runs a bounded quantum of complete JVM
instructions/phases, then checkpoints. `Thread.start` atomically creates/enqueues
`Runnable.run` exactly once; duplicate starts throw the modeled Java error. A
terminated main fiber does not terminate the VM while the non-daemon server fiber
is live. The console fiber may block on an explicitly empty virtual console, but it
must really start and reach that blocking operation.

Implement only synchronization exercised by the frozen startup path: reentrant
monitor owner/count, FIFO deterministic entry/wait sets, wait/notify transition,
join on target termination, sleep deadlines, and required atomics/volatile rules.
Unsupported thread operations fail explicitly. This is not parallelism, native OS
threads, fairness equivalence, asynchronous interruption, or a general scheduler
claim. The host never selects the next fiber from Minecraft state.

### Deterministic time

Pin a virtual epoch and monotonic clock in `configRoot`. Neither host wall time,
transaction count, gas used, block timestamp, sender order, nor scheduler runtime
silently advances Java time. A minimal deterministic policy is:

* add a fixed configured nanosecond quantum per committed guest scheduling unit;
* `nanoTime` reads monotonic virtual time;
* `currentTimeMillis` derives from pinned epoch plus monotonic time;
* `sleep(t)` blocks the fiber until its virtual deadline; and
* when no fiber is runnable, advance directly to the earliest deterministic timer,
  otherwise do not jump merely to wake a sleeper.

The exact quantum is workload configuration, not Java conformance, and must be
recorded. Entropy uses an EVM-maintained deterministic PRNG seeded in config; the
host does not answer `Random`/UUID calls. This makes the `%.3fs` Done duration
replayable without pretending it is physical elapsed time.

### Ready checkpoint rule

The Log4j call must append guest-formatted message bytes to a committed EVM outbox.
A host may display those bytes. It may not search the JAR at runtime, synthesize the
line, or map an earlier banner/main return to success.

The first acceptable ready record is a **successful checkpoint after the logger
call** whose state/output commitments include:

1. exact artifact/config/runtime roots and the guest output event matching
   `Done (<digits>.<exactly three digits>s)! For help, type "help" or "?"`;
2. provenance for actual `nz.j` PC 994 (and next PC 999 or a later genuine point),
   after the PC-950 world-preparation call returned;
3. all preceding heap/statics/VFS/world writes and outbox bytes under the same
   committed state root; and
4. lifecycle `RUNNABLE`, with the server fiber still live—not fabricated `RETURNED`
   because Java main ended.

Acceptance should then close and restart the local driver from that durable
checkpoint and resume far enough for the same server fiber to return from `j` and
reach its run-loop state. The already committed marker must remain exactly once in
the outbox. If the EVM call that traces PC 994 later OOGs before checkpoint commit,
there is no marker and no readiness. An uncommitted tracer observation is only a
failed attempt.

## 6. Minimum virtual platform after LC0

### EVM-backed VFS

The first VFS should be a deterministic private namespace, not host POSIX passthrough:

* normalized absolute/working-directory paths represented as exact guest bytes;
  reject NUL, escaping root, unsupported symlinks/devices and ambiguous encodings;
* monotonically allocated inode IDs for directories and regular files; directory
  entries keyed by `(parentInode,nameBytes)` with exact bytes retained to reject
  hash collisions;
* fixed-size chunked file bytes, exact logical length, bounded sparse-zero policy,
  deterministic directory iteration, and virtual timestamps from the pinned clock;
* persistent descriptor records `(fd,inode,openFlags,cursor,append,closed)` with
  monotonically allocated descriptor IDs; read/write, close, flush-as-checkpoint,
  and seek from start/current/end with checked signed bounds;
* atomic same-namespace rename that validates source, destination, replacement,
  nonempty-directory and cycle rules before changing either directory; and
* checkpointed per-operation phases for cross-chunk reads/writes/truncate/rename so
  retry cannot duplicate bytes or leave two names accidentally.

Start with only operations demonstrated reachable on startup: JAR/resource reads
from an immutable read-only artifact mount; `eula.txt`, `server.properties`, logs,
world/data files and directories on a writable mount; descriptors/seek needed by
ZIP/NBT/region code; and rename/replace used for durable saves. Do not promise
symlinks, mmap, host locks, POSIX permissions, arbitrary providers, watch service,
or crash semantics beyond the pinned model. Java exceptions/results are produced
by guest library/platform code, not host filesystem errors.

The VFS root, descriptor table, dirty chunks, and operation cursor belong in the
same Java checkpoint commitment. Host storage may carry opaque chunk bytes keyed by
an EVM-issued root. It must not inspect NBT, choose directory contents, convert host
paths, answer seeks, generate a world, or recover writes from a reverted OOG call.
The eventual `eula.txt` is a separately authorized exact input; LC0 contains none
and this proposal does not accept it.

### Other startup boundaries

The no-client milestone still reaches a bind before Done. Provide a minimal virtual
TCP namespace in EVM state: bind reserves an exact virtual address/port for an owner,
rejects collision, supports close, and creates bounded queues. It does **not** open
an OS socket or imply connectivity. Outbound/auth/telemetry and credentials are
explicitly unavailable unless separately modeled. Netty event-loop tasks that the
startup path requires must run as cooperative fibers; “successful bind” and
`Thread.start` cannot be blanket stubs.

Logging is an append-only guest outbox of formatted bytes plus sequence/provenance.
Console input is an explicit empty/nonblocking-or-blocking virtual source according
to the pinned policy. No listener or external byte adapter is needed for the first
marker.

## 7. Recommended next slice: LC0

Suggested freeze: **MC-LC0 canonical single-fiber checkpoint kernel**. It is a
LOCAL experimental prototype and current-JVM continuation proof for named fixtures,
not a platform or Minecraft stage.

### Exact scope

* Fork the current 154,839-byte monolith into a separate local experimental target;
  preserve the accepted pure artifact and all historical APIs unchanged.
* Add start/resume/checkpoint inspection for one fiber using the canonical frame,
  static/init, heap and pending-exception representation above. Reparse the exact
  raw bundle each resume; do not persist parser caches yet.
* Yield only between complete JVM instructions and the already explicit pending
  exception/init-continuation loop transitions. No arbitrary gas-derived PC and no
  VFS, scheduler, monitor, time, Strings, main launcher, JAR, network, MC, or EULA.
* Anchor epoch/root in reused local EVM storage and persist opaque pages plus a
  disk-backed test StateDB root. Keep old `Run`/`RunClasses` differential behavior
  untouched.

### Frozen candidate budgets

These are deliberately large but finite LOCAL prototype ceilings, to be measured
rather than silently increased:

| Resource | LC0 ceiling |
|---|---:|
| direct `runtime.Call` gas per start/resume | 250,000,000 |
| pre-commit gas reserve | 50,000,000 |
| JVM instructions per slice | 1..64 |
| internal continuation phases per slice | 1..4,096 |
| successful checkpoints per case | 64 |
| total JVM instructions per case | 4,096 |
| ordered raw user classes | existing cap 64 |
| aggregate raw class bytes for LC0 | 8 MiB |
| canonical checkpoint bytes | 2 MiB |
| committed output bytes | 64 KiB |
| active frames/heap quotas | existing monolith caps, never raised |
| wall watchdog | 60 s per EVM call, 20 min per LC0 test command |
| process RSS watchdog | 4 GiB |

The implementation must check sizes/counts before allocation and preserve ordinary
EVM charging. If canonical encoding plus commit cannot fit the 50M reserve or a
fixture cannot fit 250M, the slice reports the measurement and rolls back; it does
not disable gas, change EVM code, call the limit infinite, or quietly raise it.
These calls intentionally exceed Osaka's signed-transaction maximum and are not
reported as transaction/block evidence.

### Exact positive tests

All fixtures are trusted, compiled with `javac --release 8 -g:none`, and supplied as
unchanged bytes to both the current monolith and LC0. Host Java is oracle-only.

1. **Alias/state (`LC0Alias.run(3) == 33`)**: one `Box` starts at 3 and is referenced
   by a local, a static and a one-element reference array. Three iterations increment
   through one alias and sum through another; the result adds all three final reads.
   Run with quanta 1, 3 and 64. Require at least one checkpoint where all references
   retain the same nonzero handle and a later mutation is visible through each alias.
   No decoder may duplicate/remap the object.
2. **Frames (`LC0Frames.sum(5) == 15`)**: recursive static calls force checkpoints
   at depth greater than one and during returns. Require stable frame IDs/depth,
   caller `callPC`, expression prefix, locals and next PC across every resume. The
   sliced final value and Java exception outcome equal unsliced `RunClasses` and the
   Java 8 oracle.
3. **Initialization/exception (`LC0Init.run() == 9`)**: a lazy class initializer
   calls a helper whose integer divide faults inside a matching
   `catch (ArithmeticException)` and returns 9. Force checkpoints with class state 1,
   an active initializer frame, pending exception before handler search, and final
   state 2. Require the same exception handle on handler entry and no duplicate
   initializer or wrapper allocation.

For each test, every checkpoint is inspected through an EVM validation/view API,
not a host-created structure; exact roots, epochs, steps, PCs/depth/selected handles
and gas are recorded. Quanta may change epoch count but not the final Java value,
heap alias result, initialization result, or guest side-effect sequence.

### Exact rollback, provenance, replay, and restart tests

1. After epoch 2, call resume with 100,000 gas (or the first measured amount that
   deterministically reaches execution but cannot reserve/commit). Require EVM
   OOG/reserve failure, no checkpoint/output log, and byte-identical anchored
   epoch/root/output. Retry with 250M and require the same child root as an
   uninterrupted control.
2. Flip one byte separately in header, frame cell, heap record, page order and raw
   class. Each call must fail its exact canonical/provenance check without changing
   the anchor. No mutation becomes Java OOM/exception.
3. Commit epoch 3, then resubmit the valid epoch-2 pages: stale-head failure and no
   state/log changes. An explicitly authorized new-instance fork may accept the old
   root but has a distinct instance ID and history.
4. At a nonterminal alias checkpoint, write opaque pages and the EVM StateDB trie
   root to `build/java-diff-mc-local-continuation/restart/`, terminate the helper
   process, reopen a fresh process at that root, and resume to 33. Compare every
   post-restart checkpoint/root/output and gas with an uninterrupted replay under
   identical explicit context. Also restart at the pending-exception checkpoint and
   require final 9 with one initializer execution.
5. Attempt to resume the checkpoint with a fresh `runtime.Execute`; require rejection
   or fresh instance state, never accidental continuation. This pins the distinction
   between current execution setup and the new anchored `runtime.Call` path.

### Disjoint implementation write set

A future worker should own only these new paths:

```text
jvmevm/runtime/local/**
jvmevm/localcontinuation/**
jvmevm/testdata/mc-local-continuation/**
build/java-diff-mc-local-continuation/**   (ignored evidence only)
```

`jvmevm/runtime/local/**` contains the experimental Solidity source copied/derived
from the pinned monolith, its dedicated build script/lock/artifact, and does not
replace `jvmevm/runtime/JVMSubsetInterpreter.sol` or its hex artifact. The Go package
owns the local StateDB/session/checkpoint transport and tests without editing
`jvmevm/jvmevm.go`. No Makefile, plan, stock S0/S1/S2, core/state/vm/types,
consensus, params, precompile, global setting, peer/listener, or production path is
in the write set. One worker owns all local Solidity in this slice.

LC0 acceptance would prove that named current-monolith Java state survives genuine
EVM checkpoints, rollback, and a local disk/process restart. It would not prove all
2,231 accepted cases are resumable, standard deployment, a general JVM, VFS,
threads, Java main, JAR loading, Minecraft entry, EULA acceptance, or Done.

## 8. Dependency order after LC0

Keep subsequent work narrow and evidence-driven:

1. forced-yield replay across the full accepted monolith fixture set, adding bounded
   internal phases only where measured operations exceed LC0 limits;
2. scalable artifact/JAR registration and Java launch/String/class-library core;
3. VFS path/inode/chunk/descriptor/seek/rename slices with pure-Java microtests;
4. cooperative Thread.start/sleep/monitor/task-queue and deterministic time slices
   selected from the pinned startup path;
5. virtual bind/log/console boundaries;
6. explicit EULA/config authorization, then bounded unchanged-server progress; and
7. only then the committed genuine Done/restart acceptance described above.

A later profile may use larger finite per-call gas, checkpoints and state pages after
recording measurements and watchdogs. No number in LC0 is a prediction of Minecraft
startup cost. World generation, reachable library/native services, class count,
state growth, scheduler interactions, and total step count remain major unknowns.
The static control flow proves where Thread.start, world preparation, Done and the
tick loop occur; it does not prove the reachable dependency subset or that the
proposed local architecture will fit practical time, memory, disk, or gas.

## 9. Ignored evidence produced for this proposal

All files below are ignored and are not product artifacts:

* `build/java-diff-mc-local-continuation/runtime_execute_state_probe.go`: finite
  100,000/2,000-gas `runtime.Execute` versus `runtime.Call` mechanism probe, run
  under a 60-second shell watchdog;
* `runtime_execute_state_probe.log`: output quoted above;
* `source-and-artifact-hashes.log`: the JAR hash gate and source/runtime
  measurements, SHA-256
  `d2e5a8a7c97b468a319ceb0b6bb515208a9c090db462562544a683c109b8bd92`;
* `static/MinecraftServer.javap.txt`: SHA-256
  `7c00d11bc6efe0865647f483b33cd805ef1442b7c84ea6480d84d9088394ee6c`;
* `static/nz.javap.txt`: SHA-256
  `f02779977685aff3ba02f9eee59d32ac90f4f4c70624770606e6d492e1e6a95f`.

The probe source/log hashes are respectively
`c54bd220b944344567527031beab9db740f13f77a77fd83b07d2451692381df3`
and `eaa66e8cfebc9c3794a0e9193a684a6571c78f9c250810a26f3dffb25fd16080`.
The static files contain copyrighted class disassembly and remain ignored; only
source-derived facts and hashes are committed in this document.
