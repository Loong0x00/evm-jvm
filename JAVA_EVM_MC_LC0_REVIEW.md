# MC-LC0 acceptance review

Status: **accepted bounded LOCAL continuation**, after parent integration and fixes
through `f866ba5`. This accepts real EVM-owned Java state continuation and durable
new-process reopen, not Minecraft startup, a guest filesystem, full Java SE, or
standard CREATE/signed-transaction deployment.

## Artifact and authority

The frozen contract is `JAVA_EVM_MC_LC0_PLAN.md` (`7f56d6a`). Runtime, opaque Go
transport/fixtures and independent verifier deliveries were integrated as
`d6d163e`, `b3f6353`, and `59938e5`. Parent fixes are `3e4abe1` and `f866ba5`.

* Contract: `jvmevm/runtime/local/lc0/LC0Interpreter.sol`.
* Runtime: **206,163 bytes**, SHA-256
  `a1820864d8e846be4de8211158778150fdfde0e41e443aa66c44ec17f487e6cd`.
* Pinned compiler: solc `0.8.30+commit.73712a01.Emscripten.clang`, optimizer 200,
  viaIR, Cancun, metadata off. The builder checks all generated artifacts,
  including embedded combined ABI/runtime/provenance JSON.
* Accepted LB0 source/runtime/bootstrap and stock files remain byte-identical to
  `0f6f008`; the LB0 runtime remains `ea940755...`. Upstream EVM/state/consensus/
  protocol files were independently checked unchanged.
* Initial worker artifact descriptions were not acceptance evidence. The actual
  integrated files/build, subsequent fixes and independent replays determine the
  artifact above.

## Actual continuation evidence

These are linked start/resume chains, not fresh executions at different budgets.
Each row agrees with the trusted Java 8/21 oracles and accepted pure interpreter.
The final machine root and total counters agree across quantum choices.

| Fixture | Result | JVM/internal units | slices: 4096 / q7 / q1 / internal1 |
|---|---:|---:|---:|
| Call loop | 15 | 74 / 2 | 1 / 11 / 74 / 3 |
| Shared object and String aliases | 36 | 105 / 3 | 1 / 15 / 105 / 4 |
| Initializer/caught arithmetic | 10 | 18 / 5 | 1 / 3 / 18 / 6 |

At the accepted runtime, total chain gas (one/q7/q1/internal1) is respectively:

* loop: 2,006,699 / 19,278,629 / 126,964,739 / 5,444,337;
* alias/String: 5,910,899 / 68,163,127 / 466,928,193 / 14,484,990;
* initialization: 2,922,703 / 8,090,310 / 45,219,156 / 14,858,185.

These are sums across separate calls, not per-call or per-block gas claims.
Dedicated boundary tests additionally prove:

* valid terminal checkpoints of 1,048,568 and **1,048,576 bytes**, including
  read-only EVM validation under the existing 1B LOCAL boundary ceiling;
* the exact-limit start uses **257,213,254 gas**; eight bytes over the limit
  produce state error `(1,0)` without a head;
* a 524,927-byte parent survives a failed oversized child, then a larger quantum
  genuinely resumes it to a 1MiB terminal child using **384,036,558 gas**;
* disk/trie/code reopen occurs in new processes, including a `-trimpath` binary
  launched from an empty working directory. This rules out the former dependency
  on finding runtime artifacts beside source files. Code is not reinstalled.

Ordinary calls retain 100M/30s and dedicated boundary calls 1B/120s. No old budget
was raised. LOCAL code installation is explicit and oversized; it is not CREATE.

## Findings retained as regressions

1. Publication failures exposed speculative child checkpoints/logs. Failed
   publication now returns diagnostic gas only, not a slice, blob or event.
   Retry/reopen expectations come from independent successful controls.
2. The combined artifact was absent and the transport depended on source-tree
   artifact paths. Generation/checking and Go embedding fix both. Missing runtime
   artifacts fail tests rather than being skipped.
3. Legitimate private/super `invokespecial` frames retain `thisHandle` even when
   not constructors. Restoration now accepts the actual retained receiver. A
   second parent probe proves local slot zero may be overwritten by `istore_0`:
   JVM 8/21 and the base interpreter return 5, and q1 continuation now does too.
4. Entry/argument profile bounds now return the frozen control error 6.
5. Eight rehashed standalone mutations formerly passed validation despite invalid
   object/static references, reference-array components, or boolean/byte/short/
   char field normalization. Field layouts/types, reference assignability and
   interned String backing are checked; null does not force dormant type lookup.
6. Serialized cell bytes are bounded before heap-cell allocation. Child semantic
   state is checked before publication. Scalar and byte copying use bounded
   scratch/MCOPY rather than byte-at-a-time loops, allowing the 1MiB boundary to
   validate without increasing its gas ceiling.
7. Invalid store metadata previously created LevelDB files before rejection.
   Metadata and store-entry types are checked before opening the database.
8. An unpublished `.durable-head-*` temporary could strand an otherwise valid old
   head after a process stop. Regular owned temporaries are ignored and preserved,
   never parsed as heads or deleted. Unrelated entries still fail.
9. Reused orphan blobs now undergo file and directory sync before head publication.
   A retained failure-seam test proves this branch cannot publish through a failed
   sync. File reads are bounded; internal store entries/blob links are not followed.
   Explicit store-root aliases remain supported by resolving the requested root;
   the original alias/new-process tests remain intact.

Deep validation is not provenance: actual resume still requires the exact
EVM-stored owner/epoch/head/artifact/config/runtime commitments. Go transports
opaque bytes and does not decode Java, heap, machine state or class metadata.

## Verification and caveats

* Original independent verifier plus parent type, quota, valid-bytecode and disk
  regressions pass at the accepted artifact.
* `/tmp/mc-lc0-parent-gates.exit = 0`: historical 2231/full, smoke/fast, LB0,
  bootstrap/Python/artifacts, all stock profiles/demos, AOT and focused vet.
  That run's initial LC0 portion used the earlier `3cf2bc5f...` candidate; it is
  **not** substituted for the accepted artifact's later reruns below.
* `/tmp/mc-lc0-parent-current-final.log`: accepted-artifact reproducibility,
  `make java-mc-lc0-test java-mc-lc0-demo` pass.
* `/tmp/mc-lc0-parent-accepted-tests.log`: full current LC0 suite passes after all
  final Go changes. Focused LC0/runtime-assets vet passes.
* `/tmp/mc-lc0-parent-watchdog.{log,json}`: another complete current run passed
  under an external 1200s/4GiB process-group watchdog: 10.273s, observed peak group
  RSS 408,596,480 bytes. This measurement is machine-specific, not a universal bound.
* `/tmp/mc-lc0-parent-all-probes.log` and
  `/tmp/mc-lc0-parent-current-chains.log` retain measured parent evidence.

Two requested additional review workers were provider-blocked and produced no
commits. They are **not** counted as successful independent reviews. Parent took
those checks over, retained the concrete failures and fixes above, and reran them.
The original delivered independent verifier is separate evidence.

Durability tests cover returned-error seams, actual process reopen, retained
unpublished files and old-root recovery. They do not claim a physical power-loss
simulation or filesystem isolation against another process concurrently replacing
store paths. The driver is a bounded local experiment, not a production service.

No Minecraft server was executed, no EULA was accepted, and no listener or genuine
`Done` was produced. `JAVA_EVM_MC_VFS_PROPOSAL.md` is only a next-stage proposal;
Throwable/String construction, Java I/O, resources, main, scheduling and other
workload-needed platform support remain future work.
