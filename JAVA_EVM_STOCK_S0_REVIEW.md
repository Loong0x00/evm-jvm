# Independent stock S0 correctness review

Reviewed integration base: `1f45125dc8c1b71d9d4fe4f3a27e7e6f56a8fb9b`.

## Result

**At the review base, one gas-feasibility defect blocked acceptance.** Parent
resolution and the now-success-required regression are recorded below. The class
parser and step module accept a class inside every frozen structural limit, and a
direct 2,000,000-gas module call completes its final batch, but the coordinator's
required 800,000-gas commit reservation leaves the module too little gas. The same
final batch therefore exceptional-halts through `resume` at the frozen 2,000,000-
gas transaction cap.

This is a stock S0 finding only. S0 remains the frozen tiny straight-line integer
slice; it is not deployment or modularization of M5d-a and does not run the 2,231-
case M5d-a corpus.

## Blocking finding S0-R1: accepted boundary class cannot resume within 2M gas

`TestStockReviewAcceptedBoundaryResumeReproducer` deterministically constructs this
trusted classfile:

- Java classfile 52.0, 2,915-byte payload, SHA-256
  `a6ccdc7288cbbb2a52731c791f74aac7557465b689f662ddc5f3918063f92288`;
- `cp_count=512`, consisting of legal entries, with `CONSTANT_Integer` #511 equal
  to 243;
- selected `public static run()I` Code at payload offset 2,653, length 256,
  `max_stack=1`, `max_locals=0`, and no handlers;
- reachable code is 252 `nop` instructions, `ldc_w #511`, `ireturn`.

The deployed module's `inspect` returns exactly `(2653,256,1,0)`. Starting at JVM-
relative PC 240, a signed direct call to `step(...,budget=16)` with a 2M gas limit
returns `done=true`, PC 256, result 243 and `executed=14`; measured gas was
1,145,167.

Through the coordinator, fifteen 16-instruction resumes succeed and persist
`epoch=15,totalSteps=240,pc=240`; their aggregate resume gas was 12,628,781. The
sixteenth `resume(15,16,32)` at 2M gas fails with an empty nested EVM revert after
944,210 gas. It emits no log and leaves epoch, total steps, digest, and every
Machine field unchanged. Coordinator construction consumed 1,789,089 gas. A
separate diagnostic call at 2.1M gas completed the final resume using 995,864 gas,
confirming that the guest and state are valid and that the failure is caused by the
2M envelope plus reserve/stipend arithmetic rather than bytecode semantics.

The exact checked reproducer is:

```sh
go test ./jvmevm/stock \
  -run TestStockReviewAcceptedBoundaryResumeReproducer -count=1 -v
```

An exported copy of the exact generated class was also loaded by the local JVM;
`javac --release 8 -g:none` compiled a trivial caller and `java` returned `243`.
No downloaded Java or untrusted input was executed.

The frozen plan explicitly says to report an insufficient measured bound rather
than raise protocol limits or waive rollback. The parent Solidity writer should
reduce parse/lookup/call overhead enough to preserve both the 800,000 reserve and
the 2,000,000 resume cap. Acceptance should then change this reproducer to require
a successful terminal checkpoint; a larger gas cap is not a conforming fix.

## Source and test audit

Apart from S0-R1, I found no additional confirmed semantic defect in the reviewed
scope:

- **Page and commitments:** `ArtifactPage` returns exact `STOP || payload` and has
  no mutable runtime API. The module checks size, prefix, `EXTCODEHASH`, and payload
  hash. The coordinator pins all five constructor values as immutables and checks
  the module hash on construction and resume. The arbitrary module/hash pair remains
  only a configuration commitment, as the frozen plan states; acceptance still
  depends on deployed module bytes matching the pinned artifact.
- **Parser/profile/predecode:** bounds use the actual outer or Code-attribute
  boundary, two-slot CP entries consume their reserved slot, selected class/name/
  superclass/root/Code constraints are checked, nested attributes are bounded, and
  exact class consumption is required. All selected bytes, including unreachable
  bytes, are predecoded for width, supported opcode, integer `ldc` tag, local range,
  and instruction starts.
- **Machine semantics:** execution uses tagged uint32 bits with unchecked modulo-
  2^32 add/subtract/multiply/negate/iinc, exact signed immediates, initialized-local
  tracking, JVM-relative PC, stack clearing, and canonical inactive cells. Direct
  malformed-state and execution failures retain the specified structured errors.
- **Controller:** the review observed an early stipend guard; parent threshold
  testing later proved it insufficient after state/calldata preparation (see below).
  Module failures bubble, returned ABI words are manually range/canonicality checked, and
  no persistent machine/header write precedes response and dirty-budget validation.
  Schema-1 digest encoding, numeric checkpoint equality, conservative dirty counts,
  one success event, terminal rejection, and failed-call rollback matched the
  independent tests. S0-R1 is a feasibility failure of the reservation under the
  fixed cap, not evidence that the reservation can be consumed by the module.
- **Ordinary execution:** reviewed tests use signed ordinary `CREATE` and calls,
  sender recovery and enabled nonce/transaction checks. Simulated execution disables
  listeners/peers, while direct replay uses explicit contexts. EIP-170, EIP-3860 and
  Osaka transaction-gas rejection are tested at their actual layers. No `SetCode`,
  `SetState`, host Java execution fallback, precompile, consensus, opcode, or gas-
  schedule modification appears in the stock path.

## Artifact and run evidence

Pinned artifact measurements from the reviewed JSON:

| Artifact | init bytes | init SHA-256 | runtime bytes | runtime SHA-256 |
|---|---:|---|---:|---|
| ArtifactPage | 457 | `69c0c488c937e7c1378239b3cf060836f09d2ae00ed93c4be3c86af31438a135` | 3 | `0668b20e4ee135e7cac4091998933a5123658a8e777994fdb4b4ee2d553e6438` |
| TinyJvmStepModule | 11,566 | `a370ac4875a0c5993bcfcfac8db341eaae0b449c8e82ec742d04da2ecc47cdc8` | 11,540 | `ace4f95158d70a3b7e961255b67262e330f3382b6dd50936a5055c6028fe681c` |
| VMCoordinator | 4,855 | `12a4781feb73737d12b668140acb362d6eee3b72b85f3c47a8d60f71faf76209` | 3,713 | `6401f7e6000a4cfc69d764ff10ee73b9c0a562c9898a3611226e1750f3770cde` |

The deployed module Keccak code hash observed by the signed/direct tests was
`0x08926287b37b068306372feeac0d88671d2f23183b625e60df513e7766ff45e6`.
All artifact source-hash metadata matched the four reviewed Solidity source files.

`go test ./jvmevm/stock -count=1 -v` passed, including the explicit defect
reproducer. Existing measured examples included the canonical signed path at six
successful transactions/4,319,610 gas and deterministic direct replay at
4,251,912 aggregate gas with equal explicit-context state root
`0x8d544ca8ef71fc6f33bfe12ea80f03d40a906da5781e9b79e2db7f5eb53fd24e`.

`npm run check` could not be rerun in this worktree because the local `solc` Node
module is absent (`Cannot find module 'solc'`). I did not install or substitute a
compiler. Artifact loader/deployment tests passed, metadata source hashes matched,
and the checked artifact bytes were exercised, but reproducible recompilation
remains for a worktree with the pinned dependency installed.

## Parent resolution after review

Parent reproduced the original S0-R1 log on the review base, independently of the
reviewer's report. The module parsed/validated CP offsets but discarded them, then
rescanned the entire CP for each ldc. Reusing that already-validated in-call array
removes the duplicate scan without changing class bytes, CP/Code/page limits,
instruction semantics, transaction cap or 800k commit reserve.

The SAME2915-byte class now completes its last coordinator resume at **799224 gas**
inside the unchanged2M transaction cap; direct final batch899343gas. After16 successful
resumes the exact terminal state is epoch16,totalSteps254,pc256,result243. The test
now REQUIRES success, matching the actual JVM oracle243; a too-small dirty-word
budget at the same boundary separately proves rollback before the successful retry.
`TestStockReviewAcceptedBoundaryResume` replaces the success-on-reproduced-failure
test. Thus no defect reproducer is counted as semantic success.

Separately, parent generated80 Java8/21/signed-ApplyMessage resume probes and42 gas
threshold probes. The latter exposed20 panic0x11 cases at855000..900000 gas before
and after a nonzero checkpoint: the early guard preceded lock/state loads/calldata
encoding, so the later subtraction could underflow. Commit861c8c2 checks actual
available gas again at the call boundary. These failures now return the defined
reserve error, not Solidity panic, with unchanged VM state/log rollback behavior.

The harness's initial numeric-zero check also needed correction: ABI big.Int zero
can have a different nil/empty internal word slice than new(big.Int). Parent1f45125
checks all scalar fields and numeric canonical cell values plus the independent
digest rather than using reflect.DeepEqual on math/big internals. Nothing is skipped.

Final module runtime11132bytes, SHA256
`3f36c84abdb4701faa36fa5ce1490ce179fc5c395a17f7e6fe45de861acdbfd4`;
coordinator template3724bytes, SHA256
`720f7ee7a175fa2af9b1000abaf58d4528e81666f9fa300312ae2108125f561e`.
Coordinator actual deployed hashes include constructor immutables, verified separately.
Parent recompiled with pinned solc and reran the complete stock tests; the review's
missing-node-dependency caveat does not apply to those parent gates. Evidence:
/tmp/stock-s0-parent-boundary-repro.log, /tmp/stock-s0-parent-reserve-red.log,
/tmp/stock-s0-cp-rebuild.log, /tmp/stock-s0-cp-green.log.
