# Class-count 29 blind review, round 1

## Conclusion

The recorded blocker is sufficiently measured to justify a **narrow raw-class-count
28 -> 29 experiment**, not a platform-feature change.  The accepted original-28
frontier is at 3946 JVM / 34 internal steps and 568 verified receipts; it records
only `org/apache/logging/log4j/spi/StandardLevel.class`, context 16, as the next
missing class.  Its recorded size/hash are 2239 bytes and
`3302ed556149697655f1c6ee87f6f531a6b1ae1969f2321c9eb3ab3e67d6e836`.
Adding that one declared binding changes 245930 to 248169 bytes: it remains under
the unchanged 262144-byte ceiling with 13975 bytes left.

Thus a cap of 29 is adequate to admit the *measured* missing binding, provided all
three count enforcers and the committed configuration are moved together.  It is
not evidence for any later original-JAR frontier, nor for main-body, world, or Done.

The preparation is directionally sufficient, but its abbreviated gate list should
be made explicit before acceptance.  In particular, a normal 30-class setup tests
the driver's early guard only; it does not by itself exercise the coordinator's
constructor count guard or the engine's direct raw-class guard.

## Exact allowed source delta from the accepted count-28 parent baseline

Baseline inputs are the pinned files in
`evidence/java-evm/minecraft-entry/parent-b985a6add/` (their SHA-256 entries were
checked against its `SHA256SUMS`).  A reverse verifier should reconstruct the
candidate solely by the following substitutions; every other source byte must
remain equal to that baseline.

| Component | Exact delta |
|---|---|
| `artifacts/engine/MCEntryInterpreter.sol` | Replace the nine `MC-CLASSCOUNT28-PARENT1` domain occurrences (empty-args, root, artifact, bootstrap, config, machine, seed, VFS, file) with one fresh isolated count-29 LOCAL384 profile domain; `MAX_RAW_CLASSES = 28` -> `29`; and the first `_configRoot` limits word `uint32(28)` -> `uint32(29)`. Keep `MAX_RAW_BYTES = 262144`, the other ten limits words, 81 bootstrap images, 14 exception kinds, native bindings, frames, checkpoint and Head caps unchanged. |
| `artifacts/coordinator/MCEntryCoordinator.sol` | Install a fresh fixed engine address and the fresh rebuilt engine Keccak pin; replace the three package/resource/VM domain occurrences with the same fresh profile; change all four fixed arrays `address[28]`, `bytes32[28]`, `uint32[28]`, `bytes[28]` to `[29]`; change constructor `n > 28` to `n > 29`. Do not alter DI0/ZI0/AS0 pins, constructor checks, or byte aggregate logic. |
| `executed-driver.go.txt` | Use the matching fresh format, owner, engine address, package/resource domains, fixture-instance domain occurrences, and rebuilt engine SHA-256/Keccak plus coordinator Keccak pins. Change exactly the two `> 28` cardinality checks (manifest validation and binding parsing) to `> 29`. Retain gas, reserve, persistence, package-root algorithm and all non-count checks. |
| `checkpoint_frames.py` | Diagnostic-only `classes<=109` -> `classes<=110`; no checkpoint codec/runtime semantic change. |
| Pins/build/gate metadata | Re-pin fresh source/artifact hashes, compiler settings and profile/address/owner. The new reverse verifier must take the accepted parent-28 source hashes as its input, assert the substitutions above exactly, and reassert byte-identical bootstrap images and all unchanged limits. |

The count-28 source establishes the substitution counts: engine domains 9, one
engine max, one config word; coordinator domains 3, arrays 4, one constructor guard;
and driver count guards 2.  `uint8 classCount` already represents 29 and needs no
widening.

## Required gates

1. **Reverse/source and pin gate.** Verify the exact delta above against
   `parent-b985a6add`, including fresh engine/coordinator hash wiring and unchanged
   81 bootstrap image bytes, native 11/String-local 10, exception 14, 262144 raw
   bytes, 128 frames, 1 MiB checkpoint, 32768 Head, 25M reserve and LOCAL384
   runtime cap (393216 bytes).
2. **Fresh reproducible source build.** Pin the actual engine and coordinator
   bytecode/hash outputs under the existing compiler settings. Reject an engine
   exceeding 393216 bytes; count 28's 388963-byte engine leaves only 4253 bytes, so
   fit is a measurement gate, not an assumption.
3. **Generated exact-count behavior.** Use trusted generated Java-8 fixtures only:
   retained exact28 and new exact29 must each run q1, q7 and direct/q4096, reopen,
   and agree on canonical machine root and opaque checkpoint payload across quanta.
   A reordered exact29 package must have the expected distinct package root while
   retaining the appropriate canonical execution result.
4. **All count refusal layers, atomically.** (a) normal 30-binding setup must fail
   before world-directory creation; (b) a direct coordinator-constructor test with
   30 valid-shaped entries must return its count refusal (`MR0Error(2)`) with root
   unchanged; and (c) a direct engine `startMain` with 30 raw entries must return
   the raw-count `LinkError(1,30)` with no persisted anchor/root mutation.  The last
   two cannot be inferred from the driver's early rejection.
5. **Raw-byte boundary and canonical receipts.** Retain exact-262144 and 262145
   generated boundary cases at the new count profile, with unchanged-root receipts;
   preserve the honest 262144 parser-infeasible outcome rather than relabeling it
   success, and the 262145 constructor aggregate refusal.  Independently re-encode
   successful public checkpoint ABI/events, checkpoint hashes, counters and DI0
   read ranges; retain q1/q7/direct/reopen receipt verification.
6. **Parent-only original29 step.** Only after all generated gates and archived
   pins pass, append precisely the recorded StandardLevel binding to the accepted
   original28 continuation and measure the resulting frontier.  Do not assert or
   pre-name any subsequent blocker.

## Risks / omissions to close

- The existing preparation says “30 refusal”; without the two direct tests it may
  cover only the Go driver.  Coordinator fixed-array/constructor and engine limits
  would then be source-proved but not EVM-exercised.
- A fresh profile/address/domain is mandatory: reusing count-28 domains or code
  pins could make an incompatible count/config appear resumable or collide in
  package/resource roots.
- The 384 KiB cap is close enough that compilation output, not source-line size,
  decides feasibility.  No size result for count29 has been measured.
- The 262144 fixture is known to be Java-8-valid yet parser-infeasible in this
  profile.  It is a boundary/atomicity regression, not a claim that every package
  at the byte ceiling executes.
- Generated fixtures establish the count transition only.  They do not replace the
  parent-only original29 measurement, and neither recorded evidence nor this review
  supports claims beyond the StandardLevel frontier.

## Parent flow

Finish the two anonymous, identical read-only reviews and blind comparison; nominate
one semantic writer only if the review requirements are reconciled.  That writer
implements the strictly verified count-only delta and generated gates.  The parent
then independently rebuilds, reverse-verifies, archives pins/receipts and runs the
single original29 continuation.  Stop at its actually observed result.

## Static checks performed

- Read the two count-29/count-28 plans; count-28 generated evidence, source
  verifier, pins and gate; and `parent-b985a6add` pins, frontier, bindings, parent
  verifier output and archived sources.
- SHA-256-checked the six consulted parent evidence inputs (engine source,
  coordinator source, driver, checkpoint diagnostic, frontier and pins) against
  the archived manifest.
- Arithmetic checked: `248169 - 245930 = 2239`; `262144 - 248169 = 13975`.
- No build, original artifact/world access, network access, tracked-file edit or
  commit was performed.
