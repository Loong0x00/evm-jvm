# Blind qualitative verdict — EnumSet recovery

This is an **asymmetric recovery comparison, not a fair model benchmark**. Candidate
identities were not inferred or considered. I treated each supplied
`machine-results.json` as authoritative and did not rerun heavy tests.

## Summary

| Candidate | Correctness | Architecture | Minimality | Robustness | Maintainability | Completion | Mean | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A | 6.5 | 8.5 | 9.0 | 5.5 | 7.5 | 6.5 | 7.25 | **Reject as completed stage; preferred recovery basis** |
| B | 6.0 | 8.5 | 3.0 | 6.5 | 7.0 | 1.5 | 5.42 | **Reject — mandatory machine failure** |

**Preference:** A, clearly, but only for repair and re-gating—not unconditional
acceptance. It is the only under-cap candidate with targeted EVM execution evidence.

## Candidate A

### Machine result and decision

The authoritative result is a **provisional pass**, not full acceptance: source verifier
and engine build pass; runtime is 393,027/393,216 bytes (189-byte headroom); targeted
q1/q7/direct, host-oracle, and iterator-exhaustion checks pass. Retained gates are
`not-yet-run` (`candidate-A/machine-results.json`).

**Decision: reject as a completed stage submission.** Confidence: **88/100**. The design
is the better recovery base, but it has one explicit semantic violation and incomplete
required regression evidence.

### Dimension scores

- **Correctness — 6.5/10.** Strong evidence exists for the measured path and equivalent
  q1/q7/direct outcomes. Null and non-enum operands become catchable guest NPE/CCE
  (`candidate-A/engine.diff:162-189`). However, the native path never checks
  `initializationState`; `_enumUniverse` only finds `$VALUES` and checks non-null REF
  (`engine.diff:210-224`). If `$VALUES` is published and later `<clinit>` code fails,
  `allOf` can still succeed. That contradicts both the task's no-failed-state-recovery
  rule and the report's claim at `candidate-report.md:27-29`.
- **Architecture understanding — 8.5/10.** Canonical mirror resolution, a single exact
  private-static native binding, append-only image 83, reserved replacement, unchanged
  limits, and no host execution are all appropriate (`engine.diff:83-98,106-177`). The
  reverse verifier also checks old-image order and fixed limits
  (`verify_source.py:247-265`). Explicit erroneous-class state is the important omission.
- **Modification minimality — 9.0/10.** One 457-byte Java image, one small reader, and
  reuse of the accepted HashSet are tightly scoped (`candidate-report.md:39-44`). It fits
  the fixed cap without quota growth. The 189-byte margin is extremely fragile.
- **Robustness — 5.5/10.** Canonical/null/non-enum and focused exhaustion paths are sound,
  but `$VALUES` authority is under-validated: no descriptor, uniqueness, heap kind/rank,
  leaf class, contents, identity, ordinal, duplicate, or failed-state check
  (`engine.diff:213-224`). The implementation deliberately inherits HashSet and has no
  dedicated immutable iterator (`verify_source.py:58-65`), so the set is a copied
  universe but its inherited iterator remains live over a mutable set. Requested
  replacement/quota/OOM/reopen/retained matrices have no supplied pass.
- **Maintainability — 7.5/10.** The delta is localized and the verifier recompiles the
  Java image, reconstructs the exact parent delta, checks bootstrap order/limits, and
  verifies coordinator pins (`verify_source.py:41-81,247-270`). Hard-coding `$VALUES`
  while documenting failed-state safety that is not enforced is a maintenance hazard.
- **Task completion — 6.5/10.** The capped build and focused EVM gate are meaningful.
  Nevertheless, the report explicitly says generated/retained matrices and Go-driver
  execution were not run (`candidate-report.md:66-69`), and labels historical gate copies
  as scaffolding (`candidate-report.md:80-81`). Leaving original-artifact execution to
  the parent was correct; leaving all generated/retained work incomplete was not.

### Findings

- **High — failed-state recovery:** no `initializationState == 3` guard exists before
  accepting a non-null `$VALUES` table (`engine.diff:154-178,210-224`).
- **High — incomplete required gates:** retained gates are explicitly not run, and broad
  negative/quota/reopen matrices are not supplied as passing evidence.
- **Medium — under-validated universe:** a static field named `$VALUES` with any non-null
  REF is accepted (`engine.diff:213-224`).
- **Medium — iterator contract only partially justified:** the universe is copied into a
  HashSet, but mutation and a live inherited iterator remain exposed
  (`verify_source.py:58-65`; `candidate-report.md:31-32`).
- **Low — cap fragility:** only 189 bytes remain, so the necessary state guard may require
  additional size optimization.

## Candidate B

### Machine result and decision

The authoritative machine result is **403,767 bytes**, exceeding the mandatory
393,216-byte cap by **10,551 bytes**. The targeted EVM gate was not run because the build
was ineligible (`candidate-B/machine-results.json`).

**Decision: reject.** Confidence: **99/100**. The mandatory cap failure is dispositive,
even though the qualitative design contains valuable ideas.

### Dimension scores

- **Correctness — 6.0/10.** The source derives constants from actual ACC_ENUM static
  fields, validates exact declaration descriptors, genuine object identity, complete
  unique ordinals, and declaration ordering (`candidate-B/engine.diff:152-249`). It also
  models fresh/active/failed initialization (`engine.diff:348-385`). But it initializes
  the target at lines 357-380 **before** `_enumSetUniverse` checks at lines 386-389 and
  204-219 that the target is an enum. Thus `allOf(nonEnum.class)` may run unrelated
  `<clinit>` side effects before rejection. Also, exact `heap.classes[handle] == target`
  (`engine.diff:234-238`) rejects legal constants with per-constant class bodies. There
  is no EVM execution evidence.
- **Architecture understanding — 8.5/10.** This is a strong EVM-owned design: canonical
  mirrors, continuation-safe genuine initialization, erroneous-class NCDFE, ordinary
  heap ownership, explicit quota/OOM handling, exact native metadata, and replacement
  refusal (`engine.diff:96-145,204-318,327-412`).
- **Modification minimality — 3.0/10.** The change is EnumSet-scoped, but adds two images
  and about 172 lines of metadata/layout/allocation machinery. The 10,551-byte cap
  overflow proves it is not sufficiently minimal for this bounded task.
- **Robustness — 6.5/10.** Field shape, ancestry, identity, ordinal coverage, destination
  layout, allocation caps, guest OOM, and failed class state receive careful checks
  (`engine.diff:152-318,348-401`). Non-enum initialization side effects, rejection of
  constant-specific subclasses, and no q1/q7/direct/reopen execution materially reduce
  confidence.
- **Maintainability — 7.0/10.** Helpers cleanly separate recognition, ordinal layout,
  universe validation, and installation. The verifier rebuilds both Java8 images and
  reverses the exact source delta (`verify_source.py:23-72,74-164`). The large monolithic
  addition, repeated class scans, and hard-coded layouts make future changes costly and
  contributed to the cap failure.
- **Task completion — 1.5/10.** Only source verification and a host oracle completed
  (`candidate-report.md:15-23`). The authoritative artifact is over cap and therefore
  cannot run targeted or retained EVM gates. This misses the central deliverable.

### Findings

- **Critical — mandatory runtime-cap failure:** 403,767 > 393,216 by 10,551 bytes;
  machine eligibility is `reject`.
- **High — no EVM/retained evidence:** targeted gate is `not-run-build-ineligible`; q1,
  q7, direct, reopen, canonical-root, and quota behavior remain unproved.
- **High — non-enum target initialized before validation:** initialization occurs at
  `engine.diff:344-381`; enum validation occurs only afterward at `204-219,386-389`.
- **Medium — constant-specific enum classes rejected:** exact dynamic-class equality at
  `engine.diff:234-238` excludes legal per-constant subclasses.
- **Medium — bounded-target incompatibility:** the extensive helper machinery and second
  iterator image (`engine.diff:136-318,421-423`) cannot be installed under LOCAL384.
- **Low — report/machine mismatch:** the report records only an unresolved `solc`
  attempt (`candidate-report.md:5-7`), while the authoritative machine result supplies
  the actual over-cap size. This is not fabricated success, but the machine result must
  control.

## Final comparison

A is preferable because it actually fits the frozen cap and passes the focused EVM
execution across quanta. B's ACC_ENUM/ordinal/snapshot validation is qualitatively
stronger, but its artifact is mandatorily ineligible. Neither is acceptable as a finished
stage: A needs an erroneous-class guard plus retained/negative/quota/reopen gates; B needs
a major size redesign before any EVM validation can begin.
