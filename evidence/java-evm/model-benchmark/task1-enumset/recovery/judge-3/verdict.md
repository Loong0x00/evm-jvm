# Independent blind verdict — EnumSet recovery

This review treats `machine-results.json` as authoritative and does not rerun heavy tests. It is an **asymmetric recovery comparison, not a fair model benchmark**. Candidates are judged independently; the preference at the end is not an acceptance waiver.

## Summary

| Candidate | Correctness | Architecture | Minimality | Robustness | Maintainability | Completion | Decision | Confidence |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| A | 5.0 | 8.0 | 3.0 | 6.5 | 6.5 | 2.0 | **Reject (mandatory machine rejection)** | 96% |
| B | 6.0 | 6.5 | 9.0 | 4.0 | 7.0 | 6.0 | **Reject (not acceptance-ready)** | 93% |

## Candidate A

### Scores

- **Correctness — 5.0/10.** The design genuinely derives declaration order from validated `ACC_ENUM` fields and object ordinals (`candidate-A/engine.diff:152-249`), handles initialization state 3 and continuation scheduling (`:344-388`), and creates an owned immutable array. However, it initializes state-0 targets before `_enumSetUniverse` proves they are enums. A non-enum can therefore run `<clinit>` and then receive hard `EnumSetProfileError(5)` rather than an ordinary guest `ClassCastException` (`:204-219`, `:344-388`). No EVM gate ran (`candidate-A/machine-results.json:1`).
- **Architecture understanding — 8.0/10.** Canonical mirrors, genuine initialization, failed-state handling, hierarchy validation, guest heap ownership, quota accounting, guest exception unwind, append-only bootstrap order, and replacement reservation are all explicitly modeled (`candidate-A/engine.diff:152-318`, `:327-390`; `candidate-A/pins.json:5-23`). The validation/initialization ordering is the material architecture error. Static-only assessment remains uncertain.
- **Modification minimality — 3.0/10.** The scope is only EnumSet, but it adds two images and a large native metadata/heap implementation (`candidate-A/bootstrap/java/util/EnumSet.java:7-23`; `EnumSetIterator.java:4-18`; `engine.diff:49-59,152-318`). The authoritative runtime is 10,551 bytes over cap (`machine-results.json:1`). True immutable snapshot semantics justify some complexity, not an ineligible runtime.
- **Robustness — 6.5/10.** The source validates descriptors, ancestry, object class, ordinal uniqueness/range, array quotas, failed init, NPE, OOM, and replacement (`engine.diff:155-318,333-390`). But non-enum initialization has side effects, and none of these paths ran in EVM (`candidate-report.md:25-29`).
- **Maintainability — 6.5/10.** Helpers are well named, while `verify_source.py` recompiles and pins both Java 8 images, checks fixed limits/special-case absence, and reverses exactly to the accepted basis (`verify_source.py:23-76,151-173`). The bespoke Solidity and extra iterator increase audit and cap cost, and structural verification cannot replace behavioral tests.
- **Task completion — 2.0/10.** Source verification and a reported host oracle completed, but authoritative evidence says build failure, cap failure, and no targeted EVM gate (`candidate-report.md:15-29`; `machine-results.json:1`). The generated/retained/reopen/quota matrix required by `original-task.txt:5` is absent. Rejection is certain because the machine cap is dispositive.

### Findings

- **Critical — mandatory runtime-cap failure.** Runtime is 403,767 B versus 393,216 B, over by 10,551 B; machine eligibility is `reject` and the EVM gate is build-ineligible (`candidate-A/machine-results.json:1`).
- **High — non-enum target initialized before rejection.** `_initializeClass` runs before the `ACC_ENUM` and direct-`Enum` checks (`candidate-A/engine.diff:204-219,344-388`), violating side-effect-safe non-enum behavior and the no-init-bypass constraint (`original-task.txt:3-5`).
- **High — required EVM/retained gates absent.** No q1/q7/direct/reopen/canonical, replacement, quota/OOM, or retained Enum/ACC_ENUM/cap/queue evidence exists (`candidate-report.md:25-29`; `machine-results.json:1`).
- **Medium — implementation bulk.** Two images plus roughly 170 lines of specialized metadata and heap logic are not viable in the frozen envelope (`engine.diff:49-59,152-318`).
- **Low — honest reporting.** The report clearly discloses that compilation and EVM gates did not complete (`candidate-report.md:3-7,25-29`).

### Decision

**Reject.** The runtime-cap failure alone mandates rejection, regardless of the thoughtful static design.

## Candidate B

### Scores

- **Correctness — 6.0/10.** Authoritative evidence passes q1/q7/direct equivalence, the host oracle, and guest-caught iterator exhaustion within the cap (`candidate-B/machine-results.json:1`). Canonical mirror lookup, null NPE, and non-enum CCE are visible in `engine.diff:154-193`. Correctness is limited by absent initialization-state checks, under-validated universe authority, and non-snapshot inherited iteration (`engine.diff:202-224`; `bootstrap/java/util/EnumSet.java:23-34`). The positive measured fixture passes, but required negative/lifecycle behavior remains uncertain.
- **Architecture understanding — 6.5/10.** The operation stays EVM-owned, uses canonical guest mirrors/static storage, preserves limits, reserves its image, reuses guest HashSet bytecode, and avoids host reflection (`engine.diff:93-111,154-177`; `pins.json:5-23`). It omits the class lifecycle and direct `java/lang/Enum` hierarchy from authority, both central to `original-task.txt:3`.
- **Modification minimality — 9.0/10.** One 457-byte bootstrap image, one exact private native binding, and reuse of existing HashSet/iterator machinery form a compact append-only change (`bootstrap/java/util/EnumSet.java:23-34`; `engine.diff:54-84`). It fits at 393,027 B with 189 B headroom and preserves fixed limits (`machine-results.json:1`; `pins.json:6-23`). The semantic cost of that reuse is scored elsewhere.
- **Robustness — 4.0/10.** Positive quantum equivalence passes, but `_enumUniverse` accepts the first static field named `$VALUES` after only a non-null REF check. It does not validate descriptor, synthetic/final status, array metadata, element classes, ordinals, duplicates, or direct Enum ancestry (`engine.diff:202-224`). It also cannot distinguish active, complete, uninitialized, and failed initialization. Retained gates are not run (`machine-results.json:1`; `candidate-report.md:66-80`).
- **Maintainability — 7.0/10.** The one-image implementation is compact. The verifier pins parent inputs, recompiles Java 8 bytecode, reconstructs the delta independently, verifies all prior image order, and checks fixed limits/coordinator pins (`verify_source.py:25-81,247-268`). But comments overclaim `ACC_ENUM`-field derivation, immutable snapshot behavior, and failed-state refusal (`bootstrap/java/util/EnumSet.java:9-18`; `candidate-report.md:16-29`), while the verifier only proves that initialization/allocation calls are absent from the native branch.
- **Task completion — 6.0/10.** Engine/coordinator builds and one focused EVM path completed. Deferring original artifacts is correct, but the machine result says retained gates are `not-yet-run`, and the report leaves all generated/retained matrices to the parent (`candidate-report.md:54-69,80-81`). The task required those lifecycle, malformed, replacement, OOM, reopen, canonical, and retained gates (`original-task.txt:5-7`).

### Findings

- **Critical — none.** No mandatory failure is reported for B; machine eligibility is provisional rather than final.
- **High — failed-state recovery remains possible.** Binding 12 never reads `initializationState`; any non-null `$VALUES` is returned (`candidate-B/engine.diff:154-193,202-224`). If an enum publishes `$VALUES` and later fails `<clinit>`, a later call can still recover it, contradicting both the task and the report's claim (`candidate-report.md:21-29`). A state-0 enum is refused instead of genuinely initialized (`candidate-report.md:75-79`).
- **High — iterator is neither immutable nor a snapshot.** `EnumSet` publicly extends mutable `HashSet` and does not block inherited `add` (`bootstrap/java/util/EnumSet.java:23-31`; `evidence/java-evm/minecraft-entry/parent-7625023ff/bootstrap/java/util/HashSet.java:23-30`). The report assumes no later mutation (`candidate-report.md:30-32`), but the accepted iterator stores the owner and compares its cursor to live `owner.used` (`evidence/java-evm/minecraft-entry/parent-7625023ff/bootstrap/java/util/HashSetIterator.java:3-10`), so additions after iterator creation become visible. That does not meet the frozen immutable-or-snapshot behavior (`JAVA_EVM_MC_ENUM_SET_PREPARATION.md:5-9`).
- **High — `$VALUES` is under-validated authority.** The helper checks class `ACC_ENUM`, then only field static-ness/name and non-null REF; it does not prove direct Enum ancestry or validate array/element/ordinal metadata (`engine.diff:166-177,202-224`). This is weaker than genuine canonical enum-constant derivation required by `original-task.txt:3`.
- **High — required retained/negative matrices are incomplete.** Machine evidence marks retained gates not run, and the focused result does not establish the full wrong/non-enum/null/init/replacement/OOM/reopen/canonical/retained matrix (`machine-results.json:1`; `candidate-report.md:66-69`; `original-task.txt:5`).
- **Medium — documentation overstates invariants.** Source/report prose says the primitive reads `ACC_ENUM` fields, iteration is fixed-snapshot, and failed states are refused, but the implementation does not enforce those properties (`bootstrap/java/util/EnumSet.java:9-18`; `candidate-report.md:16-29`; `engine.diff:202-224`).
- **Low — only 189 B headroom.** The current build passes, but every semantic correction must be remeasured (`machine-results.json:1`; `candidate-report.md:71-74`).

### Decision

**Reject as acceptance-ready**, despite `provisional-pass` machine eligibility. The focused measured path and cap pass are valuable, but lifecycle, universe validation, snapshot semantics, and retained gates are requirements rather than optional polish.

## Preference

**Candidate B is preferred as the next repair basis; no tie.** It fits the mandatory cap, passes the focused q1/q7/direct gate, and is substantially smaller. This preference does not mean acceptance: A is machine-disqualified, and B still needs semantic hardening plus the required retained/negative gates.
