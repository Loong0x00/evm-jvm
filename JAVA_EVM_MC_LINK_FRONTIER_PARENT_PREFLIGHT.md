# Parent-verified fixed-package link frontier

**Generated preflight verified with corrections; no new loader/profile.** Worker
9047772b2 integrated249bb6f0b. Accepted CB0 0fdb9dcf7/VFS0a and all production hashes,
quotas/ABI/core remain unchanged. Parent main-launch proof270ef50ee also remains valid.

## Independent result and correction

Original worker replay passed freshly in7.184s/327450624B, but its mode3 attribution
is WRONG: generated javap shows `checkcast` at PC35 and `invokevirtual` at PC38.
The actual refusal is LinkError(4,38). VFS0a opcode0xc0/0xc1 handling explicitly
returns/continues for null BEFORE class lookup. The null cast did not bind the
missing class; the subsequent virtual method reference did. Do not call the
observed PC38 refusal a checkcast failure or silently retarget that positive.

Parent preserved the worker's immutable inputs/results and added a separate
CastEntry with NO call after the cast. This distinguishes operand-dependent demand:

| current selected package | operation/outcome |
|---|---|
| original four-class closed main chain |10724(mode0),10731(mode7),44Java/6internal; direct/q1=1/44, roots agree|
| DemandEntry only, unused MissingTarget reference |returns41|
| DemandEntry only, invokestatic at12/new at21 |exact LinkError(4,12)/(4,21)|
| DemandEntry only, null cast35 then invokevirtual38 |cast passes; exact LinkError(4,38) at invocation|
| SuperEntry without MissingSuper |HierarchyError(1,0),0xa52e829f|
| InterfaceEntry without MissingInterface |LinkError(4,0),0x427cfac5|
| independent CastEntry only, null cast |returns61 WITHOUT loading MissingTarget|
| independent CastEntry only, nonnull Object cast at17 |LinkError(4,17)|
| CastEntry + MissingTarget, nonnull Object cast |ordinary typed guest ClassCastException,kind8|

Separate Java8u504 TEST classpaths corroborate cast behavior: full/missing null
casts both return61; nonnull full target gives ClassCastException, while genuinely
missing target gives host NoClassDefFoundError. EVM profile LinkError is NOT
misreported as that Java exception. Java test execution never supplies EVM results.

Crucial additional controls: preselecting DemandEntry+MissingTarget (two images)
makes modes1/2 return51/52 and mode3 yield a normal guest NPE kind6. Selecting the
omitted superclass or interface makes the SAME respective entry return9. Thus
closed preloading repairs these small cases WITHOUT implementing a demand loader.
Demand resolution is a candidate design, not a necessity proven by omitted classes.

## Real continuation/failure evidence

The original q1 missing-invokestatic world commits epochs1..5, then refuses the
sixth call atPC12. Its prior EVM-issued checkpoint remains the only published head
and is hash-checked/read by a new process. No failed slice is reused, and no host
class injection/rebinding is attempted. A fifth decoder remains the unchanged
public CB0 pre-EVM guard: actual gas0,4 registered decoders, same published root.
Do not call that an EVM revert or a successful fifth-class load.

The parent COPY driver checks no installed engine or AS0 CREATE on reopen, records
the prior loaded trie root, and asserts a failed call returns no slice/checkpoint/
logs/success root. Parent verification compares actual before/after roots/epoch/CP
fields rather than merely trusting stateUnchanged. Raw68B EVM refusal data is decoded
at full uint256 width and compared with selector/code/detail. All successful q1
quantum/counter/event/identity fields are checked, and each actual opaque checkpoint
file SHA matches its receipt. Independent terminal/pending reopens compare all
published roots/epoch/lifecycle/blob hashes. Original decoder/name assertions still
come only from EVM Head; only public CB0 APIs, no host class/ZIP decoder or StateDB.

Corrected suite:97 distinct actual processes,59 actual checkpoint-file hash checks,
66 Java success/refusal calls, max8929319 gas, aggregate430530782 across calls.
EVM gas always ordinary<=100M, no1B or new quota. Full actual terminal blobs and
pending epoch5 blob, per-process receipts, reports and javap evidence are archived.

Final fresh combined gate **15.961s/336994304B/exit0**, under20min/4GiB sampled group
watchdog: regenerated inputs, independent Java oracles, all worker cases PLUS parent
cast/preloaded controls, both verifiers, Go vet, pinned CB0 check, accepted CB0
pipeline/process/publication/class-boundary/CAS regression and empty protected diff.
Sources/repro/failures: evidence/java-evm/link-frontier/parent-9047772b2/.

Worker provenance caveat: earlier final/final2 output directories survived, but
outer logs/watchdogs seen as untracked during work were no longer present at review.
Exact earlier gate outcomes cannot be recovered or credited. Parent preserved the
remaining copied Go drafts, empty reports and selected raw results with original
paths/hashes; do not claim a complete historical failure transcript. The actual
misattributed final result remains intact and is corrected by new measurements.

## Next measured decision, not a speculative full-Java rewrite

Current hard limits remain4 raw images/65536 aggregate, CP4096, Code65535 and
checkpoint1MiB. STATIC archive evidence says MinecraftServer/bn/tr/um=34977B;
adding LogManager gives5 classes/46841B, before the extra launcher. This is NOT a
complete dependency closure or instruction-reachability proof. Previously EVM-
decoded AbstractLogger90309 alone exceeds current64KiB. Neither capacity nor target
bootstrap/platform dependencies can be dismissed.

User prioritizes LOCAL artistic EVM->JVM->game, not complete Java SE. Before committing
to complex load/yield/registry/checkpoint machinery, compare a narrowly labeled
DISPOSABLE enlarged fixed-package baseline (8 images/256KiB input only) against
current behavior. Keep all accepted code/quotas unchanged; no production promotion
from that experiment. Measure5..8 small closed graphs and a genuine method-rich
>=90309B generated class under ordinary gas, parse/replay/checkpoint costs, explicit
refusals/ceilings. A cap-only prototype cannot solve arbitrary missing references,
reflection or lazy loading; if it fails budgets, that is evidence for demand work.

Demand-continuation proposal must also account for stable class IDs (current user
classes precede appended bootstraps), fixed artifact/checkpoint binding, re-parsing
on resume, hierarchy/static initialization and atomic retry. These are not solved
by replacing LinkError with a flag. No such implementation has occurred.

No original Minecraft Java/main/EULA/listener/world/Done and no push.
