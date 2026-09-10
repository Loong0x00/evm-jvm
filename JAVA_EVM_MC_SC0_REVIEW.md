# MC-SC0 acceptance review

Status: **ACCEPTED bounded LOCAL String construction/continuation**, after parent
integration and corrections through `fe0c435`. Authority is frozen
`JAVA_EVM_MC_SC0_PLAN.md` (`20a160d`). This is not Java I/O, VFS, main, builders,
Throwable message APIs, a standard deployment or Minecraft startup claim.

## Artifact and preservation

Worker commits402131d/d014970/6844b59 integrated as7adb7ed/b9b53ac/1252721.
The first actual combined suite passed, but parent probes below found further
validator/resource defects. Worker reports and intermediate snapshots were not
substituted for final acceptance evidence.

* Contract `jvmevm/runtime/local/sc0/String0Interpreter.sol`.
* Runtime **225303bytes**, SHA256
  `a3fdedbcb6d517d567eb9ee0c9ab69955027a56859db8c26d9ef38e328a67e60`.
* Source SHA256
  `c983cd99ea1cb2139d978508ebc3fd935cdb28453bd0b3be46c19bee5d169a38`.
* Runtime Keccak/code hash
  `99d35386f146722a67d59c876154ac916068379819974e114fda49377cc33297`.
* New String984B SHA256
  `7999610c7686c7622667ee57fef88d6bf576e61595ec09310dc3905cd18aedad`;
  source95542f5d4b869cc96ee395c322f8368a275fe3338ae60c7810afded6d4b81f2e.
  Parent recompiled it with javac --release8/-g:none and compared exact bytes.
* The other26 bootstrap images were independently compared identical to TL0.
  All accepted TL0/LC0/LB0/stock files and their old27 images remain unchanged.
  Upstream EVM/state/types/consensus/protocol changes remain absent.
* Exact solc0.8.30+commit73712a01 guard, optimizer200/viaIR/Cancun/metadataoff;
  runtime, ABI, embedded combined provenance and pinned String image reproduce.

Initial worker982b6351..., reported temporarya29a5a59..., parent1ac31ba8...,
1d62b807... ande1de31c0... are historical candidates, not the artifact above.

## Genuine capability and bounded restriction

`String(char[])` performs a defensive copy through the pinned Java constructor's
real allocation/loop/load/store/return bytecodes. `String(String)` executes its
real Code, preserves distinct identity, shares immutable backing and copies hash
cache. Nonliteral intern compares full UTF16 content and inserts/returns the receiver
itself without allocating another String/array or mutating its hash cache. Existing
canonical hits, handle-sorted insertion and collision distinctions are preserved.

OptionB is explicit: **only String new** requires the exact no-callback Object()V
Code profile. The actual Object frame/return still execute. Valid noncanonical
Object constructor shape hard-fails StringProfileError(4,newPC); it is never silently
skipped. Other object/Throwable constructors, inherited Object fields, String
literals/CV preparation and prior fault/cause behavior remain supported as before.
This does not claim unrestricted partially constructed String native behavior.

SCS1/JVMSC001/SC0-domain checkpoints are separate from TLS1/LC0. EVM owns constructor
state, shared heap, graph checks, sorted pool and anchored head. Go carries opaque
ABI/checkpoint/trie bytes; it does not implement Java/String/graph semantics.

## Actual gates

*24 ordinary roots pass Java8primary/Java21secondary and24 one-call EVM controls.
*Ten selected roots pass q1 andq7, plus loop64 q7: **21 linked chains**, with equal
 terminal outcome/counters/machine root within SC0. No repeated-fresh-run claim.
*All24 TL0 fixture controls and its ten q1/q7 selections remain valid on SC0;
 the three LC0 bundles also pass one/q1/q7/internal1. Cross-profile roots are not
 compared as equal because runtime/config commitments differ.
*All32 independent probe groups execute on the integrated artifact, including
 default/failed/active String state, Object guard/error precedence, inherited layout,
 heap quotas, exact1MiB/plus-one, intern/cause checks, CAS/OOG/retry and real process
 reopen during copy and constructor failure. Source/fixture regeneration matches.
*At final artifact, highest core one-call cost is13030492gas; largest core terminal
 checkpoint1776bytes. These are fixture measurements, not Minecraft estimates.

Parent additionally retained eight probe groups, including32 seeded UTF16 vectors
compared on Java8/21 and EVM one/q7 (64 EVM runs), two field-write receiver variants,
null-NPE and null-constructor emergency-OOM continuation variants, and a2048-char
copy. That larger copy uses51242 JVM units and completes in13/51 slices atq4096/1024
with the same33761 result and33449-byte terminal state. It is a dedicated bounded
copy test, not a maximum-length String or whole-server cost guarantee.

## Parent findings and fixes

1. Constructor temporary-alias recognition checked descriptors but not declaring
   class. A foreign user constructor with `([C)V` could gain String-local2 backing
   privileges in standalone validation. Privileges now require exact String class.
2. String-copy stack validation allowed any backing array rather than the source's
   actual backing. The receiver/value at the three pinned constructor field-write
   safepoints are now checked, and copy backing permission is limited to its source
   temporary. Tests also retain attempts to substitute another String as receiver.
3. A checkpoint after null dereference could clear pending state and still validate
   with the handler-free String constructor at its already-advanced PC. It now
   requires the real pending NPE or arena-exhaustion OOM at that pinned phase, and
   cannot advance beyond it. Positive emergency-OOM chains are retained for both
   constructors; no blanket rejection of valid failure states was introduced.
4. Full-pool validation exceeded1B gas around500 entries even in a sliced run.
   Intern membership now uses a handle-indexed bitmap. Duplicate checking filters
   by verified Java hash and EVM-computed content digest; filter hits STILL use full
   UTF16 comparison. Hash collisions never define String identity. No Java hash
   cache, heap state or budget is changed by validation.

All changed/checksummed probe blobs remain read-only validator tests. Live resume
always required the exact stored owner/epoch/checkpoint/config/runtime commitments;
these findings were not checkpoint issuance or live-state import paths.

The retained1024-entry full-pool test now passes with1024 objects/1024 arrays:

* one-call control355789997gas,203239-byte checkpoint;
* q128 chain17 slices, matching terminal root, maximum call760458534gas;
* final checkpoint read-only validation also passes within1B.

The initial unsliced and sliced OOG reproductions are retained in /tmp logs. A
full-pool MISS still cannot coexist with an extra nonintern String under1024 ordinary
objects, and is not claimed as a live probe. Smaller-pool receiver insertion at full
ordinary/array quota is separately executed. Dominating checkpoint limits are not
relabelled Java OOM or bypassed by fabricated live heads.

## Verification records and limits

`/tmp/mc-sc0-parent-gates.exit=0` covers historical2231/smoke/fast, TL0/LC0/LB0,
bootstrap/Python/artifacts/Go/CLI/allstock/demos/AOT/focusedvet. Its initial SC0 portion
used1d62b807...; final-artifact evidence is the later reruns below, not that candidate.

* `/tmp/mc-sc0-parent-watchdog.{log,json}`: complete current suite passed under an
  external1200s/4GiB process-group watchdog:46.254s, peak observed RSS272977920bytes.
  Those are machine-specific observations, not universal performance guarantees.
* `/tmp/mc-sc0-parent-reproducibility.log`: final pinned artifacts reproduce;
  parent also compared all26 unchanged images and rebuilt String/fixture copies.
* `/tmp/mc-sc0-parent-current-corpus.log`:24 controls/21 chains at the final hash.
* `/tmp/mc-sc0-parent-full-pool-final.log`: final1024-entry one-call/q128 measurements.
* Parent initial alias/copy/null-pending/pool failures remain in
  `/tmp/mc-sc0-parent-*-initial.log`, `full-pool.log` and `full-pool-sliced.log`;
  tracked `parent_test.go` retains regressions. A combined build/test shell exceeded
  its180s tool timeout; it was not counted green, and the tests were rerun separately.

100M/30s ordinary,1B/120s boundary,25Mreserve and1MiB checkpoints remain unchanged;
dedicated SC0 quota/copy cases use the explicitly frozen65536-total-unit allowance.
Maximum65536-char copy completion, physical power-loss simulation, adversarial
external filesystem isolation, standard CREATE/signed-transaction compatibility and
MC startup feasibility are not claimed.

No Minecraft server, EULA acceptance, listener or guest Done occurred. The next
`JAVA_EVM_MC_IO_EXCEPTION_PREFLIGHT.md` is an oracle-only proposal, not an implemented
message/cause/I/O stage or VFS.
