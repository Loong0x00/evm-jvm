# MR0 atomicity COPY: independent parent review

**Narrow atomicity experiment verified after additional parent Go repairs; NOT
full MR0 Session/profile acceptance.** Worker88a851a25 integrated6b49d01c5.
No Solidity, accepted code, quotas, original JAR/classes or Minecraft execution.
Engine294795B SHA256`5cd308971f49e815ee8adf864133c05f44e675ae6efe6cabe771bd89ad8fb875`,
Keccak`2c841e15e382f6433adfbce3fddc225a5efeed5d0d87727c1eac4a0106f9d79f`;
coordinator3547B Keccak`06f642301333b90429e749951c7855cf954a379848d4643ef758f7853ff39a8c`.
Exact LOCAL route`0x4d52304d41494e454e47494e4500000000000001`, not ordinary CREATE
for the oversized engine. All other controllers/pages ordinary CREATE.

## Independent baseline and new findings

Parent rebuilt Go from source and independently reran the worker13-world fault
matrix plus12 normal generated worlds and the parent's427 ABI/event/opaque-CP
receipt verifier:19.681101s/334684160B, exit0. The original checkpoint EACCES
corruption is repaired. Parent then added controlled, read-only timing/storage
observers to the OWNED COPY driver's normal operation path, under Go `-race`.
No private accepted Session, reflection, host Java/ZIP/class evaluator, raw-class
input, state/page injection or failed-trace recovery is used.

Three further defects were reproduced before repair:

1. **Late cancellation leaked successful output.** The TEST-only1s deadline fires
   during an observer pause after an actual EVM CALL has completed but before Go
   accepts it. Although old root/Head are restored, failure returns1888 bytes of
   successful main ABI data as if they were error bytes (5987760 gas). A matching
   ordinary CREATE test leaks the new address and1 byte of runtime after host
   cancellation (218 gas). These are not genuine EVM reverts. Parent clears CALL
   output and CREATE output/address on timeout, retains actual consumed gas,
   joins the timer callback, restores old state and proves normal same-session
   Java retry matches the control root. The default deadline is still30s;1s is
   explicitly stricter TEST instrumentation, not a new production bound.
2. **Prior-Head read failure left a dirty live Session.** Actual chmod0000 at the
   storage read boundary after EVM success makes `readManifest` fail. The old file
   bytes/root remain intact, but the old candidate leaves the new EVM state usable;
   subsequent same-session resume fails with EVM revert/gas167408. Parent restores
   the last root, drops the staged blob, and poisons on unreadable/divergent prior
   authority. After permissions are restored, exact fresh reopen is required;
   CALL/CREATE/publication then refuse in the poisoned process with zero EVM gas.
3. **Published directory-fsync count was speculative.** Worker increments the
   serialized count before Head rename. `strace -f -yy` proves the after-rename
   fault performs zero subsequent directory fsyncs, yet count23→24 was published.
   Parent records the increment only after an actual successful `syncDir`.
   Published counters are conservative history snapshots and cannot include their
   own future post-rename fsync. Reopen never invents it. Actual process IO evidence
   is retained separately in syscall logs; rollback metadata counters are NOT
   claimed as exhaustive process IO totals.

Original race-probe traces,1888-byte failure data, CREATE address/runtime, both
Heads, missing-poison behavior and syscall evidence are retained. Repairs are
precise reproducible edits in `repair_copy.py`, not production changes.

## Final fresh combined parent gate

**73.404590s,368906240B sampled process-group RSS, exit0**, canonical20min/4GiB
whole-group watchdog. No child process-group escape, unconsumed stdout pipe,
per-command reset falsely called a whole budget, or1B rescue. This is a Go-only
fresh build against already independently rebuilt immutable Solidity artifacts;
no fresh Solidity compilation is claimed for this gate.

* All9 pre-rename points preserve captured byte-identical old Head/CP and return
  no failed slice/blob/log/output. Actual same-session normal retry produces the
  control root, checkpoint bytes, machine/VFS roots, lifecycle and Java counters.
* Both post-rename points preserve the newly published Head, then fresh reopen
  matches the control. Parent also actually attempts CALL, ordinary CREATE and
  Head publication while poisoned: all refuse without EVM gas or Head rewrite.
* Actual OS checkpoint-directory and manifest-directory EACCES paths preserve old
  bytes, allow normal public retry and fresh process reopen. All13 fault worlds
  compare against a separately generated normal two-slice control, not booleans
  alone. Same-session raw before/after-fault Head bytes are archived.
* `strace` observes0/1 real root-directory fsyncs after Head rename at the
  after-rename/after-dirsync points, respectively. No speculative fsync credit.
* Go-race probes cover late CALL/CREATE cancellation, unreadable prior authority,
  poisoned operations and fresh reopen. Fixed failure outputs are empty; cancelled
  CREATE address is zero. Normal Java retry root equals the control exactly.
*12 generated normal q1/q7/direct worlds still pass the independent427 canonical
  ABI/event/CP receipt verifier. Accepted CB0 regression passes; protected
  jvmevm/core/params/consensus/eth/Makefile diff against26e528965 is empty.

## Reproduction and remaining boundaries

`evidence/java-evm/main-root/atomicity-parent-88a851a25/final.py` reconstructs the
Go-only fixed matrix driver, runs its exact same normal public execution path,
checks before/after bytes, builds the independent verifier and Go-race test copy,
and runs accepted CB0 regression. Wrap it with the canonical watchdog; fresh
ignored output only, absolute scoped TMPDIR. Essential Go sources, patches,
fixtures, Heads, CPs, process receipts, raw failures, syscalls and logs are archived.

This does not establish a general Java loader or full MR0 transport: Open still
assumes a started checkpoint rather than every valid input/index/DI0/ready phase;
initial engine+AS0 installation is not yet one atomic accepted Session root;
full CAS/concurrency/capacity/metadata/refusal/read-return coverage remains. The
worker's explicit empty initial Head is not promoted to an accepted initial-state
format. MR0 has NOT merged Selected8/256KiB. Accepted4/65536 and38 bootstraps remain
unchanged. No original Minecraft Java, EULA, listener, world, Done or push.
