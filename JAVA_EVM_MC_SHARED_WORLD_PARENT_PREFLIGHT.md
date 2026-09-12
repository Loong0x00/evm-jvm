# Shared-world coordinator — parent takeover and measured proof

Status: **preflight independently completed; NOT production/ClassLoader acceptance**.
The interrupted worker left uncommitted drafts and failing reports, not a completed
result. Parent preserved those drafts byte-for-byte under
 evidence/java-evm/class-bridge/shared-world-parent-d76a45057/draft/ and inspected,
repaired and independently rebuilt/replayed a separate copy. No blocked review is
credited, no provider retry or accepted production change. Host driver now owns its
StateDB/triedb/DB directly; no reflection/unsafe/private Session attachment.

## Actual path and outcomes

Generated SharedEntry.class299B + SharedHelper.class303B in ONE ZIP/index; accepted
AS0/ZI0/DI0 contracts compute resources and pages; a constructor-fixed coordinator
EVM-loads them and invokes exact accepted VFS0a. Both classes execute real static
initializers and cross-class static calls. Java8 oracle: input7=317,input9=299.
EVM matches:36 Java bytecodes/5 internal units, direct1 slice, q1=36 slices, q7=6.
Package/index/resource/terminal machine/VFS roots match across direct/q1/q7 and
memory/disk. Input9 changes guest result/machine root. The engine anchor owner is
the coordinator, not the host EOA. All class execution inputs come from EVM reads,
never Go-decoded or caller-supplied raw class images.

Fifteen actual processes were recorded across the full run. The q1 disk chain has
setup/start, a separate refusal process, a separate resume/publication-failure/retry,
a finish process and a FINAL reopen. At least four appear in the persisted chain;
all five have independent per-process reports. Reopen neither reinstalls the LOCAL
engine nor CREATEs controllers. Terminal checkpoints are retained and their hashes
checked against the actual EVM anchor on FINAL reopen, not discarded after return.

The exact accepted LOCAL VFS0a runtime is installed once per fresh world at its
frozen address, nonce0, as an explicit non-EVM initial-state operation. This is NOT
standard CREATE deployment or gas-charged execution. All AS0/ZI0/DI0/coordinator/data/
output pages are ordinary EVM CREATE. Accepted code/opcode/quotas remain unchanged.

## Parent corrections to drafts and verification

- Runtime now rejects repeated raw names even with different DI0 controllers, and
  checks the pinned engine plus final index identity at every load, not only ctor.
- Draft inferred fsync/rename/directory-sync counts by adding1 on reopen. Parent
  REMOVED that inference: readability does not prove directory fsync. Actual totals
  are sums of observed counter DELTAS inside each process. All real EVM calls,
  including failing probes, are observed once; snapshot metadata counters alone are
  not treated as lifetime totals.
- For example, q1 has78 DI0 fragment reads:72 for36 published Java slices,2 for a
  low-budget start refusal,2 before an engine CAS refusal,2 from a successful EVM
  execution whose publication fails. None are quietly dropped to satisfy a desired72.
- Manifest temp uses unique owned files instead of truncating a fixed path. Actual
  successful file/code syncs are counted only after success. A post-rename error
  poisons rather than restoring an older root over an already published manifest.
  Prepublication restoration keeps the old routing/checkpoint metadata too.
- Coordinator route/package/instance getters are captured before the CREATE root's
  publication rather than being a later metadata-only fixup. Terminal EVM-issued
  checkpoint blobs are checked and persisted for all lifecycle values.
- The first parent500K probe was mislabeled as an OOG test; it actually reached the
  existing VFS commit-reserve refusal. That failed proof gate is preserved. Correct
  test requires exact LC0ControlError(7), selectorf15d7343, completed CHANGED guard
  SSTORE observed, and actual before/after trie roots equal BEFORE host restoration.
  It is **not OOG**. The ordinary retry then genuinely executes Java.

## Bounded gates

1..4 class packages construct; exact aggregate65536 executesP1.run(7)=9 using18
actual DI0 fragments, all<=4096 (including4097/8193/cross-page resources). Class5,
aggregate65537, wrong references/names/index/F/package/owner, duplicate controller,
duplicate name with distinct controller, non-FINAL and empty inputs reject exact
coded errors. A valid ZIP name whose class declares a different name bubbles the
existing engine LinkError. Ordered package roots differ when reordered explicitly.

Direct EVM CALL rollback checks compare roots before any host reload: AS0 wrong-Pi
fails after a real child CREATE; VFS budget/CAS failure follows actual guard storage
writes. Failed top-level CREATE can advance the creator nonce outside the child
frame; those constructor probes explicitly normalize to the last published root
and are NOT presented as raw-ROOT-equality proofs.

Actual per-process observed counts:

| world | successful EVM mutations | commit/reload | trie+code sync | DI0 reads incl failed calls |
|---|---:|---:|---:|---:|
| disk direct |17|18|18|4|
| disk q1 |52|53|54|78|
| disk q7 |22|23|23|14|
| disk input9 |17|18|18|4|
| memory q1 |52|53|53|74|
| memory q7 |22|23|23|14|
| boundary |84|85|85|20|

One extra commit per world is explicit LOCAL installation, not EVM execution. The
q1 extra sync is the injected failure AFTER actual trie/code sync, before manifest.
It restores the old root/anchor/checkpoint, then retries byte-identically; failed
candidate output is inspected only diagnostically, not used as a continuation.
Metadata-only stage/report publications are separately counted and can exceed EVM
mutations; this prototype is not a final transport receipt/schema contract.

## Pins and replay

Coordinator source9963B SHAbdb3b2f717e1e782f65d9985046d65aef7624d2cae022d1362725a5d46e5eff4;
init8279B SHAaf9e15e1bb678575c7db0e83eec20c077ce55d0bb32919cc7a20bfec04498fac;
runtime4197B SHAf505c798082f338b20adf32ff4785ce846fd04e89fa9ba0f50c0adc306653a39;
max constructor args2016B/full init10295B; artifact
508656cddeee6f01fb99dd5dc171c317b292e88d82d581bfb654cc90ddae468e.
Pinned solc0.8.30+commit.73712a01,opt200,viaIR,Cancun,metadataoff.
Final fresh full reconstruction **7.456s/325885952B sampled groupRSS**, exit0 under
20min/4GiB. Aggregate gas1130063323 across all experiments, NOT a single-call budget;
maximum observed call14771377gas. All calls ordinary100M, no1B boundary call used.

Sources, draft provenance, corrected driver/coordinator, generated fixture builders,
original failures, terminal-complete watchdog, fresh per-process reports and strict
verifier live in evidence/java-evm/class-bridge/shared-world-parent-d76a45057/.
No official JAR/class payload or original Java execution. Parent checked the actual
outputs, not merely the worker's failed verifier or the process exit code.

## Production decision

Freeze a separate CB0 LOCAL class coordinator/transport using this byte path, not
reflection or this diagnostic manifest. Keep the fixed package<=4/65536 and unchanged
engine/checkpoint/heap/VFS/resource limits. Production must have atomic routing,
strict bounded manifest/ABI/pins, real per-call receipts and current checkpoint
publication without diagnostic-only metadata rewrites. Fresh initialization installs
the exact LOCAL engine plus one ordinary AS0 CREATE before a SINGLE published initial
root: there is no reopen-repair CREATE or exposed engine-only intermediate namespace.
This is an explicit new profile initialization contract, not retargeted preflight
counts or a change to existing DI0/VFS0a. See JAVA_EVM_MC_CB0_PLAN.md.
