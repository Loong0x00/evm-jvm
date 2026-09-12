# MR0 Session COPY: parent findings, not acceptance

Worker2cf366518 positive probe independently rebuilt/replayed in a fresh parent
source-only artifact directory.12 generated worlds pass the supplied worker
verifier. **Full Session acceptance is rejected pending actual defects below.**
No Solidity/accepted core/profile/quotas/official-JAR edits or original Java claim.

## Resource-monitoring defect, reproduced

Worker `run()` wraps every compiler/driver invocation with GNU `timeout`, which
creates a new process group. Canonical watchdog samples only the wrapper group;
worker6,488,064B is NOT a whole compiler/driver group peak. Parent calibration
allocated and touched96MiB: escaped invocation records4,247,552B; identical
`timeout --foreground` invocation records118,788,096B. Both children and process
groups are logged. Parent fresh source-only gate using foreground timeout:
**197.469617s,877002752B sampled group peak, exit0**,20min/4GiB envelope.
No runtime semantics/bytecode changed. Historical undercount remains archived.

## Actual OS publication failure corrupts the durable Head

Reproducer `probe_blob_failure.py` uses the unchanged public worker CLI, a NEW
owned world, and chmod0500 on its checkpoints directory (UID1000, not root).
Directory shape/readability and old checkpoint remain valid. No private Session,
reflection, fake EVM output, manifest edit, code/page injection or recovery trace.

After real epoch1 StartMain, Resume executes successfully in EVM but cannot create
the child checkpoint file: actual EACCES. Receipt gas5987760, no EVM revert bytes.
The failed call retains trie root
`0xb88dacf4fbaea51beacb82147f056fcae039e19caa81ef88c5217520f494277d`,
but **published Head advances epoch1→2**, checkpoint root
`0x253f04b7d85c39b03324278a0a25e385d5892fba4f9c20fc09398583d1a2aff2`.
That child blob was never written. The old blob is unchanged, SHA256
`d9a74ee3019cb4e85ab39567ad4c4bd5ad79873aefea92f004decd97d7c42c71`.
After restoring the original directory permissions, normal resume exits2 trying
to read the absent child checkpoint. This is NOT a successful atomic rollback.

Source cause: `persist` returns on checkpoint-write error BEFORE defining/using
its restore path, leaving applied child manifest and live candidate StateDB.
`doResume` then unconditionally republishes `resume-refused` metadata. Even after
fixing the early rollback, error observers must not republish state metadata merely
to record stage/counters/PID. Preserve byte-identical prior published Head/CP on
prepublication failure; postrename ambiguity must poison until exact reopen.

## Supplied strict verifier accepts four invalid negative TEST copies

`probe_verifier.py` does NOT execute or supply any mutated bytes to Java/EVM.
Each deliberately invalid copied evidence set is incorrectly accepted (exit0):

* all exception manifests changed to null JavaRef/empty dynamic class;
* a zero package root and zero instance ID;
* a successful slice log forged to the zero emitter address;
* coordinator runtime bytes changed without changing its self-declared Keccak.

Runtime checks and external evidence verification are distinct. Actual raw positive
calls may be valid; a verifier accepting these mutations cannot be called strict.
Need canonical ABI/event decoding, actual cryptographic hashes, exact expected
exception identity, nonzero/consistent identities, full epoch/counter/CP receipt
chains and evidence-versus-observation failure distinctions.

## Other source-level gaps (not all independently triggered yet)

* Current implementation remains a monolithic owned `env` driver; Open requires an
  already-started checkpoint, so valid input/index/live-DI0/ready states cannot
  reopen. Engine and AS0 are separately published, not atomic initial installation.
* DI0 observer still records requests on enter only; actual returned fragments,
  exact decoder identity/offset/length/success are not captured.
* Timer callback shares a plain bool; callback completion is not joined if Stop
  loses a race. Cancellation must restore staged CALL state even if EVM Cancel
  exits without a revert error. Preserve CREATE nonce semantics distinctions.
* Slice validation checks local inequalities, not exact prior+executed totals;
  Open lacks complete names/sizes/resource roots/class sums/CP content/head checks.
* No full public fault matrix, stale concurrent CAS, malformed output/head/schema,
  page/capacity/owner/binding/refusal coverage or legal integer local0 reuse proof.

Next narrow Go-only work: repair atomic publication/cancellation and make error
paths usable, prove actual faults and same-session/process retry before claiming
full coverage. Prefer accepted CB0 public Session/persistence invariants rather
than accreting unsupported claims to this probe. Immutable repaired MR0 engine/
coordinator pins stay exact; no Selected optimization/capacity merge here.

Evidence: `evidence/java-evm/main-root/session-parent-2cf366518/`: foreground
source-only reproducer, canonical watchdogs, calibration, actual OS failure,
negative verifier copies/reproducers, full captured heads/checkpoints/logs. Accepted
CB0 remains4/65536. Still no original Minecraft Java, EULA, listener, world or Done.

## Parent receipt verifier follow-up (still not transport acceptance)

A separate Go evidence verifier now checks actual runtime/init bytes and hashes,
immutable source/compiler/ABI; recomputes constructor package and instance
commitments; canonically decodes all427 outer/engine ABI packets, compares typed
recorded slices, exact epoch/prior+executed counter chains and reserved VOID/Java
exception semantics; verifies every published opaque blob's SHA/Keccak/size/bytes,
all exact nested event emitters/topics/data, Head-vs-ABI terminal identity and
same-code machine/VFS/opaque payload equality for the12 worlds. It does not parse
ZIP/classes or evaluate Java. It explicitly labels recorded DI0 sizes as REQUESTS:
return fragments and per-slice StateDB root chains are absent from this producer,
so no new observation or full transport proof is fabricated.

Fresh verifier build/vet + original positive +9 deliberate negative controls:
**1.059866s,193449984B group peak, exit0**. The4 prior false positives now reject;
so do zero gas, wrong epoch/schema/counter and a modified checkpoint byte. Full
genuine pending blobs are supplied to negative copies so each rejection targets
the intended corruption rather than unrelated missing files. These mutations
never enter EVM execution. `verify-reproduce.sh`, `verify_receipts.go.txt`, tests,
raw rejection logs and copies are retained. Actual publication-corruption repair
is a separate active Go-only worker scope, not fixed by an evidence verifier.
