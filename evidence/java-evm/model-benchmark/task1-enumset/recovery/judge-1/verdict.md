# Blind qualitative verdict — JVM-for-EVM EnumSet recovery

## Scope and method

This review treats the supplied `machine-results.json` files as authoritative and does not rerun heavy tests. Candidate identities were neither inferred nor used. This is an **asymmetric recovery comparison**, not a fair model benchmark.

## Summary

| Candidate | Correctness | Architecture | Minimality | Robustness | Maintainability | Completion | Average | Decision | Confidence |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| A | 5.5 | 7.5 | 9.0 | 4.5 | 7.5 | 5.0 | 6.5 | **Reject as complete submission**; preferred recovery base | 92% |
| B | 6.5 | 8.5 | 2.5 | 6.5 | 7.0 | 2.0 | 5.5 | **Reject — mandatory machine failure** | 99% |

**Preference:** Candidate A, not a tie. A is cap-compatible and passes the focused EVM gate; B has a more rigorous initialization/ordinal/snapshot design but is mandatorily disqualified by runtime size. Both still have blockers.

---

## Candidate A

### Decision

**Reject as a completed task submission.** Machine eligibility is only `provisional-pass`. A is nevertheless the preferred recovery basis because its focused measured-path gate passes and its runtime fits the fixed cap.

### Dimension scores

1. **Correctness — 5.5/10**
   - Positive: authoritative results pass q1, q7, direct, host oracle, and guest-caught `NoSuchElementException` (`candidate-A/machine-results.json:1`). Null and ordinary non-enum operands become catchable guest NPE/CCE (`candidate-A/engine.diff:162-189`).
   - Negative: binding 12 never checks `initializationState`; it only finds a static field named `$VALUES` and accepts a non-null reference (`candidate-A/engine.diff:154-178, 210-224`). If `<clinit>` publishes `$VALUES` and subsequently fails, a later call can consume the retained table, contrary to the no-failed-state-recovery requirement (`original-task.txt:3`).
   - Negative: state-0 `allOf` is intentionally refused rather than genuinely initializing the enum (`candidate-A/candidate-report.md:75-79`).
   - Negative: the inherited HashSet iterator is live rather than snapshot-based.
   - Uncertainty: the focused machine summary does not enumerate all fixture cases, and retained gates are absent.

2. **Architecture understanding — 7.5/10**
   - Strong EVM ownership: canonical Class mirror recovery, guest static state, private native binding, reserved bootstrap replacement, append-only bootstrap order, and no host reflection/loading (`candidate-A/engine.diff:92-111, 154-178`; `candidate-A/verify_source.py:247-262`).
   - Weakness: publication of a compiler-synthetic field is used as a proxy for target initialization and validated enum metadata.
   - Uncertainty: no reopen/retained evidence validates the new path across full checkpoint handling.

3. **Modification minimality — 9.0/10**
   - One 457-byte Java image and one narrow binding reuse accepted HashSet behavior (`candidate-A/bootstrap/java/util/EnumSet.java:23-34`; `candidate-A/candidate-report.md:39-44`).
   - Runtime is 393027 B under the unchanged 393216 B cap, with 189 B headroom (`candidate-A/machine-results.json:1`). Prior 82 images remain append-only and byte-identical (`candidate-A/verify_source.py:247-258`).
   - Caveat: inheriting HashSet exposes a broader and different hierarchy/API surface than a narrow EnumSet abstraction.

4. **Robustness — 4.5/10**
   - Positive: q1/q7/direct equality and ordinary NPE/CCE/exhaustion behavior have focused evidence.
   - Negative: no failed-state guard; shallow `$VALUES` checks; no intrinsic immutable/snapshot iterator; no retained, replacement, quota/OOM, or reopen gate evidence (`candidate-A/candidate-report.md:66-80`).
   - The accepted HashSet exposes `add` and its iterator reads `owner.used`/`owner.elements` dynamically (`evidence/java-evm/minecraft-entry/linked-hash-set-preflight/source/bootstrap/java/util/HashSet.java:23-30`; `evidence/java-evm/minecraft-entry/linked-hash-set-preflight/source/bootstrap/java/util/HashSetIterator.java:3-10`).

5. **Maintainability — 7.5/10**
   - The reverse verifier is strong: parent hashes, Java8 rebuild, exact delta reconstruction, fixed limits, bootstrap order, native ownership, and coordinator pinning (`candidate-A/verify_source.py:25-65, 80-110, 247-268`).
   - Comments overstate the implementation: they describe ACC_ENUM-derived constants, failed-state refusal, and a fixed snapshot, while the code checks only `$VALUES` and inherits a live iterator (`candidate-A/bootstrap/java/util/EnumSet.java:9-18`; `candidate-A/engine.diff:202-224`).

6. **Task completion — 5.0/10**
   - Completed: source verifier, capped build, coordinator pin, focused EVM/host gate.
   - Missing: required generated negative/quota/replacement/reopen matrices and retained Enum/ACC_ENUM/cap/queue gates. The report explicitly says the matrices and driver were not run, and machine results say `retainedGates: not-yet-run` (`candidate-A/candidate-report.md:66-81`; `candidate-A/machine-results.json:1`).
   - Original-artifact execution was correctly parent-owned and is not counted against A.

### Findings

#### Critical

None machine-verified.

#### High

1. **Failed enum initialization can be silently recovered.** The report claims failed `<clinit>` is refused (`candidate-A/candidate-report.md:27-29`), but neither the native branch nor `_enumUniverse` reads initialization state (`candidate-A/engine.diff:154-178, 210-224`). A non-null `$VALUES` published before a later initializer failure remains usable.
2. **Iterator is neither immutable nor a snapshot.** `EnumSet extends HashSet` and does not override `add` or `iterator` (`build/blind/candidate-A/bootstrap/java/util/EnumSet.java:23-31`). Accepted HashSet is mutable and its iterator consults live owner state (`evidence/java-evm/minecraft-entry/linked-hash-set-preflight/source/bootstrap/java/util/HashSet.java:23-30`; `evidence/java-evm/minecraft-entry/linked-hash-set-preflight/source/bootstrap/java/util/HashSetIterator.java:3-10`), contrary to the mandatory immutable-or-snapshot coverage (`build/blind/original-task.txt:5`).
3. **Mandatory generated/retained gate matrix is incomplete.** Only a focused gate passed; the report and machine result explicitly identify the missing work (`candidate-A/candidate-report.md:66-81`; `candidate-A/machine-results.json:1`).

#### Medium

1. **State-0 `allOf` does not actively initialize.** It returns a hard profile error for an unpublished universe (`candidate-A/candidate-report.md:75-79`; `candidate-A/verify_source.py:255-262`).
2. **`$VALUES` authority validation is shallow.** `_enumUniverse` checks static/name/non-null REF only; it does not verify descriptor, array kind/rank/component, synthetic/final flags, constant object classes, ordinals, identity, or duplicates (`candidate-A/engine.diff:210-224`).

#### Low

1. **Runtime headroom is fragile.** Only 189 bytes remain (`candidate-A/machine-results.json:1`).

---

## Candidate B

### Decision

**Reject.** Authoritative machine results force rejection: 403767 B exceeds the fixed 393216 B runtime cap by 10551 B, the engine build is failed/ineligible, and no targeted EVM gate ran (`candidate-B/machine-results.json:1`; `judge-rubric.md:4,15-17`).

### Dimension scores

1. **Correctness — 6.5/10**
   - Strong source-level design: derives only exact ACC_ENUM static fields, validates each object and inherited ordinal, enforces a complete ordinal permutation, schedules genuine state-0 initialization, and refuses erroneous state 3 (`candidate-B/engine.diff:152-249, 327-389`).
   - The iterator is an immutable snapshot over a private array and throws `NoSuchElementException` at exhaustion (`candidate-B/bootstrap/java/util/EnumSetIterator.java:3-18`).
   - Defect: a canonical non-enum target reverts `EnumSetProfileError(5)` rather than raising catchable guest CCE (`candidate-B/engine.diff:204-219`).
   - Uncertainty: no compiled EVM run validates these source-level semantics.

2. **Architecture understanding — 8.5/10**
   - Strong handling of canonical mirrors, continuation/re-entry, failed initialization, guest heap ownership, inherited enum layout, quota/OOM, private native ownership, and bootstrap replacement (`candidate-B/engine.diff:96-114, 152-318, 342-389`).
   - No workload special case or host authority is introduced.
   - Uncertainty: continuation serialization and heap invariants were not exercised in EVM.

3. **Modification minimality — 2.5/10**
   - Two new Java images plus a large helper suite and full-class scans produce a runtime 10551 B over cap (`candidate-B/engine.diff:168-318`; `candidate-B/machine-results.json:1`).
   - The behavior is bounded but not a cap-compatible smallest recovery.

4. **Robustness — 6.5/10**
   - Positive source checks cover malformed constant fields, object identity/class, duplicate/out-of-range ordinals, initialization states, snapshot storage, quotas, OOM, and exhaustion (`candidate-B/engine.diff:204-317, 327-401`).
   - Negative: non-enum is a hard profile error; the wrapper allocates the EnumSet before validating the operand; no EVM/retained/reopen evidence exists.
   - Uncertainty: fault precedence, OOM atomicity, and checkpoint behavior remain untested.

5. **Maintainability — 7.0/10**
   - Java surfaces and helper responsibilities are clear. The verifier rebuilds both Java8 images and proves exact reversal/fixed limits (`candidate-B/verify_source.py:23-72, 74-173`).
   - The 170-plus-line native implementation and repeated class scans are costly under a hard code cap and increase optimization burden (`candidate-B/engine.diff:152-318`).

6. **Task completion — 2.0/10**
   - Completed only source verification and a focused host oracle.
   - Candidate report states compilation never started and all EVM/retained work remains (`candidate-B/candidate-report.md:5-29`). Machine results confirm build failure, cap rejection, and no targeted EVM gate (`candidate-B/machine-results.json:1`).

### Findings

#### Critical

1. **Mandatory runtime-cap failure.** Runtime is 403767 B versus 393216 B, over by 10551 B; targeted EVM execution is build-ineligible (`candidate-B/machine-results.json:1`). This forces rejection under `judge-rubric.md:4,15-17`.

#### High

1. **Non-enum Class produces hard profile failure, not guest CCE.** `_enumSetUniverse` reverts `EnumSetProfileError(5)` for failed ACC_ENUM/direct-Enum checks (`candidate-B/engine.diff:204-219`), missing an explicitly required negative behavior (`original-task.txt:5`).
2. **No EVM or retained execution evidence.** Only source and host checks completed (`candidate-B/candidate-report.md:15-29`; `candidate-B/machine-results.json:1`).

#### Medium

1. **Operand failures allocate before validation.** `new EnumSet<E>()` is evaluated before `allOf0` validates null/non-enum (`candidate-B/bootstrap/java/util/EnumSet.java:10-16`; `candidate-B/engine.diff:327-347`), consuming an object and potentially changing caught-failure quota/OOM precedence.
2. **Repeated global metadata scans inflate the recovery.** Helpers rediscover `java/lang/Enum` and `java/lang/Object` by scanning all classes (`candidate-B/engine.diff:168-179, 298-306`).

#### Low

None.

---

## Final preference

**Candidate A is preferred as a recovery base**, because it is the only cap-compatible candidate and has authoritative focused q1/q7/direct EVM success. **Neither candidate is accepted as task-complete**: A still needs failed-state and iterator semantics corrected plus mandatory retained/negative gates; B must first be reduced below the immutable runtime cap and then pass EVM gates, in addition to fixing non-enum CCE behavior.
