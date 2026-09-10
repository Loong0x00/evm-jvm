# MC-VFS0a parent acceptance

Status: **ACCEPTED — bounded LOCAL Java/EVM filesystem profile** after parent fixes
and final-artifact reruns at implementation `6eafabfe7`. This does NOT accept full
Java SE, a world-capable filesystem, mainnet deployment or Minecraft startup.
No Minecraft/EULA/listener/real Done has occurred.

## Final artifact and reproducibility

- Runtime **292968B**, SHA256 `717683f8ba67141bb7b5640a7079d396cda661dd53cd2afb7ab4eb6032ac3e86`.
- Source SHA256 `b95f0788f3a45b580216697866e32814e590670a55144186fc130391986497f3`.
- Combined SHA256 `849d7e1bdae3a403239b9f84b5d32d446040b31ad4508b3e55e27426ab4aca6a`.
- ABI unchanged `16346751accb944db73a8a8b33bee6923c9ccabca1896af41f4926a2895e6520`.
- Pinned solc0.8.30/optimizer200/viaIR/Cancun/metadataoff normal check passed
 177.783s/826277888B groupRSS; `/tmp/mc-vfs0a-parent-fixed-repro.{log,json}`.
-38 bootstrap identities:30 IOE0 unchanged plus8 totaling6050B. Parent recompiled
 all8; final FIS1515B/cdda6fb5... and FOS1618B/50aa63fa... carry real Java ENOTDIR
 suffix Code. All six other new images remain unchanged. Exact pins in REVISION1.

## What is accepted

Real File/FIS/FOS and generic base stream Java Code invokes ten exact private native
EVM primitives. EVM owns all path interpretation, inodes, descriptors, cursors, bytes,
permissions, codec validation and head publication. No production host Java/filesystem
executor, native Java message allocation, world fallback or fabricated outcome.

File lexical strings remain separate from operation-specific traversal. Open/stat/
mkdir do not erase invalid intermediate traversal; ENOTDIR messages are Java Code.
mkdirs retains the observed Java8 canonical fallback. Inspect is explicitly a canonical
read-only namespace view, not proof of Java File traversal or authority to resume.

Real pending-open/truncate-before-handle-store checkpoints validate exact parsed FIS/
FOS method/frame/stack/owner/putfield corridors. Resume never reopens/truncates. Partial
or failed constructors retain legal default states; a bound failing subclass can keep
an escaped usable stream. NEW File/InputStream/OutputStream families use the explicit
canonical no-callback Object profile; Object Code still executes. Other IOE0 objects
retain their constructor semantics. Base close/flush empty Code is exactly scoped to
Java8 defaults; File* close changes descriptors. No GC/finalizer/implicit close.

## Acceptance evidence and32-group accounting

The following are coverage groups, not32 independent agent completions. One boundary
reviewer delivered; the other provider-blocked review contributed NO passing evidence.
Parent took over the missing groups, found/fixed six validation gaps, then independently
ran ALL tests on the new292968B artifact (not either worker's earlier artifact).

| groups | Final evidence |
|---|---|
|01|38image pins,8Java8 recompiles, final source/ABI/artifact rebuild; namespace/code hashes|
|02|all8 reserved-image refusals, ordinary lookalike native refusal, virtual/special/static foreign private call refusals|
|03|File Comparable/cast bridge; actual VFS generic OutputStream/AutoCloseable/default Code; InputStream Code controls|
|04|path regressions and empty/control/non-ASCII/component64/65/depth16/17/path256/257 controls|
|05|NEW-family Object restriction with successful plain Object/Throwable controls and three inherited fields|
|06|failed File/FIS constructors retain typed null/zero fields; one/q1 equality, no filesystem effect|
|07–09|both six-PC FIS/FOS corridors; wrong method/depth/owner/local0/ref kind/ID/handle/stack and extra operand view refusals|
|10|149-slice native truncate/bind/write/close, independent machine/VFS/FILE roots and EVM views|
|11|five Java open failures and quota failures with no committed filesystem effects|
|12|initialized escaped stream survives later subclass constructor failure, one/q7 equality|
|13–14|byte sign/low8/null/bounds/zero/closed; gaps/stale reads/current-EOF append|
|15|repeated genuine FNFE/String identity, exact messages and cause getters, one/q7 equality|
|16|genuine message-frame OOM under explicit1024-object quota,247 calls/10327 JVM steps; no descriptor/file effect|
|17–21|raw seeds/order/RO/count/bytes;64/65inodes;32/33closed descriptors;64KiB perfile/all-files;4096/4097 transfers|
|22|actual combined exact1MiB checkpoint and +1 atomic rejection, no padding/rehash-as-live|
|23–24|parent fixes reject file-parent/noncanonical names/readonly writers; duplicate/cycle/bool and root/counter/framing controls|
|25–28|owner/epoch/root/artifact/budgets, OOG/reserve/retry, quantum/internal1 equality, copied inspect/view-versus-live authority|
|29–31|distinct stores/old blob refusals, bounded reads, durability failure outputs, native-write and pending-bind true new-process reopening|
|32|final-artifact whole suite/repro, inherited profile preservation and recorded legacy phases|

Final whole package: **PASS364.919s**, external365.259s, **290459648B** peak groupRSS,
no FAIL/SKIP or watchdog limit hit. Log `/tmp/mc-vfs0a-parent-fixed-full-suite.log`,
watchdog `/tmp/mc-vfs0a-parent-fixed-full-suite.json`. This includes the boundary
reviewer tests with their artifact assertion deliberately repinned and rerun, not
retroactively relabeling the reviewer's293010B measurements.

Core corpus24 Java8/EVM controls +20 full q1/q7 chains passes; seven additional path
roots and selected chains pass; Java21 agrees on this declared corpus. IOE0's earlier
helpful-NPE differences are still separately documented, not erased by this profile.
Final exact1MiB uses130950 primitive cells plus119 seed bytes, **293704621gas**;
+1 rejects LC0StateError(1,0). No unreachable quota combination is substituted.

The initial combined legacy Make command hit its20min wall bound, not a runtime
failure; preserved logs show passed IOE0/SC0/TL0/LC0/interpreter2231/smoke/fast/LB0/
AOT/stockS0 before stockS1. A separate bounded remainder S1/S2a/S2b-L+vet passed
124.462s/628736000B. These are TWO phases, not a claim the timed-out command passed.
Protected accepted-profile/core paths have no diff from IOE0 acceptance.

## Resource and scope honesty

Initial256KiB VFS candidate failed its size gate; REVISION1 explicitly selected a
VFS0a-only320KiB LOCAL installation policy under the user's artistic priority. Old
caps/core/EVM semantics unchanged.100M/30s ordinary,1B/120s boundary,25M reserve,
1MiB checkpoint,64KiB ALL file contents,64inodes,32descriptors including closed,
16seeds,4096transfer;1..4096 units/call,4096 ordinary/65536 dedicated total units,
VFS-only4096 slices/case;20min/4GiB external gate. This is tiny LOCAL capacity, not
Minecraft-world capacity/performance evidence. Code is still oversized for CREATE.

Run `make java-mc-vfs0a-test java-mc-vfs0a-demo`. The example is Java/EVM file work,
NOT Minecraft readiness. Next dependency work is separate; static entry-frontier
preparation does not authorize server/EULA execution.

---
Earlier NOT ACCEPTED labels, old hashes, failed commands and worker-only observations
below are retained historical evidence. The current disposition is the summary above.

# Historical parent review log — pre-acceptance records

Frozen input/implementation contract: `cca4841`, JAVA_EVM_MC_VFS0A_PLAN.md.
Last accepted profile remains IOE0 `8f29f8c`. No production VFS runtime/continuation,
Minecraft execution, EULA, listener or Done has been demonstrated by this note.

## Independently confirmed preparation

- Integrated wrapper preflight `c18262a` as `0d3ffa1`, kernel `36bdf62` as `c9c317a`.
- Parent replayed standalone kernel actual EVM driver from its own copied directory.
  `/tmp/mc-vfs0a-parent-kernel-replay.json` matches SHA256
  `1eafceafc8aa303a4f0ffb1b5c713abb7be941f334fdb8eec276a7936d11b104`.
- Parent rebuilt that standalone Solidity source with pinned solc0.8.30/settings.
  Runtime16241B SHA256 `90a4f5e0d106cd9fb77c65a03aeaeb61e8109f1f27dbb4d3dd0224ae71985c43`;
  source22343B SHA256 `f810f199d2d3e8c5e5df387e42963c37b112d7e7d5e387224c33fd8ff2b26ab3`.
  Log `/tmp/mc-vfs0a-parent-kernel-rebuild.json`. This has NO Java-native bindings,
  combined continuation validator, production anchor or durable session proof.
- Parent corrected the candidate File graph and three stream-base concrete/default
  method shapes, rather than allowing false instanceof or AbstractMethodError results.
  Added genuine small Java Code for Comparable and generic base methods; exact empty
  Java8 base close/flush defaults are not File* close or physical sync substitutes.
  Both stock JVMs agreed on six parent base/Comparable observations; see plan/logs.
- Eight frozen source/class pairs (5976B) were recompiled from TRACKED inputs using
  Java8u504 -source8 -target8 -g:none and compared byte-for-byte with class.hex.
  All eight are classfile52. Five unchanged candidate images plus three parent fixes;
  the30 accepted IOE0 images must still be copied unchanged by the runtime worker.
- Initial attempt to edit an ignored copied source failed due to preserved read-only
  permissions; no resulting old-image compile was counted as the corrected evidence.
  Only parent-owned copies were made writable; peer evidence was not altered.
- Fresh accepted IOE0 control: `go test ./jvmevm/localcontinuation/ioe0 -count=1`
  passed38.328s under120s timeout (`/tmp/mc-vfs0a-parent-ioe0-control.log`). This is not
  a new VFS gate or a measured4GiB whole-gate RSS claim.
- At freeze, diff from IOE0 acceptance consists solely of guides and new-profile
  bootstrap inputs. No existing interpreter/accepted artifact/upstream EVM changes.

## Parent Code-only EVM probes while implementation proceeds

Committed parent_test.go adds frozen-image hash checks and two independent trusted
Java8/21/EVM probes. Exact File/InputStream/Closeable/AutoCloseable candidate images
are supplied as raw guest classes to the unchanged accepted IOE0 interpreter. No
VFS native is invoked; this is not testing VFS0a's reserved image/native/NEW gates.

- File slash normalization, Comparable graph, compare bridge/cast: result15;
  one-call control21915481gas;581 JVM/3 internal units;2504B checkpoint;
  q7/internal1 finishes86 slices with the same terminal machine root/counters.
- InputStream generic bulk partial-success catch, first-read exception, close
  default, null/bounds/zero ordering: result31; one-call18687095gas;
  269 JVM/10 internal units;1337B checkpoint; q7/internal1 finishes46 slices,
  same terminal machine root/counters.
- These probes retain IOE0's ordinary100M/4096-unit/256-slice limits, not VFS0a's
  new slice allowance. No accepted implementation or budget was changed.
- Reproduce: `go test -v jvmevm/localcontinuation/vfs0a/parent_test.go -count=1`.
  All pass1.921s; `/tmp/mc-vfs0a-parent-code-final.log`. Named-file execution tests
  this independent Code evidence without pretending unfinished VFS assets exist.
  OutputStream's full candidate graph exceeds IOE0's4-raw-class limit with a custom
  root; its EVM checks remain pending on actual VFS0a, rather than changing that cap.

## Newly reproduced path blocker

See `JAVA_EVM_MC_VFS0A_PATH_REVIEW.md`: a pure lexical `..` collapse incorrectly
opens paths through missing/non-directory intermediate components in the standalone
kernel, and the three-status wrapper cannot represent ENOTDIR. Java8/21 also
separate mkdir (false) from mkdirs (canonical fallback true) for these prefixes.
These are acceptance blockers pending parent reconciliation with the runtime worker,
not a passed production VFS test. Permanent host oracles and original failing kernel
observations are retained. Combined Code-only/host-oracle tests pass2.634s; they do
not resolve the native mismatch.

## Pending acceptance, do not promote preparation to completion

Two disjoint runtime/harness workers started from `cca4841`, model Sol/high with
Fast disabled. Parent retains validation_test.go/parent_test.go and32 groups in the
plan. Pending: actual integrated runtime<=256KiB; genuine24 roots/20 continuation
chains; real Java messages and private identity gates; pending-bind field corridor;
full VFS+heap codec/commitments; exact1MiB/+1; all quotas/rollback/inspection;
new-process disk continuation and failures; final-artifact independent32 groups;
whole20min/4GiB gate and all historical regressions.

The new4096-slice test allowance is explicit and VFS0a-only, for q1 wrapper loops.
No code/gas/checkpoint cap was raised, and no aggregate-gas estimate or standalone
size addition proves a production artifact fits. Report any real size blocker before
parent scope/module review; never edit upstream limits or silently raise the ceiling.

## Integrated initial candidate — no behavioral acceptance

Runtime32a159b->f2b64ff and harness7913c85->06e39c2 are integrated. Initial287440B
artifact hashes independently agree; initial256KiB gate failed as required. Parent
revision410a32b explicitly selects a VFS0a-only320KiB LOCAL code allowance under the
user's artistic priority (REVISION1), no core/gas/checkpoint changes. The original
size failure remains evidence; initial256KiB statements above are historical.

First actual corpus now reaches EVM and ALL24 one-call controls revert with
ThrowableProfileError(2,37-or-38,0),0.925s. See CANDIDATE_FINDINGS: integer handles
incorrectly use a reference-only helper; stat status kinds also conflict; pending
bind corridor/PC checks need correction. Path amendment remains mandatory. No q1/q7
VFS chain or production filesystem result has passed yet. IOE0 remains last accepted.

## Parent decoder preparation (not a passed VFS behavioral gate)

Parent validation_test.go now has a bounded TEST-only VFA1 Java/VFS wire reader,
frame/heap/inode/descriptor mutation offsets and independently computed VFS/machine
roots for read-only malformed-state probes. It never issues or authorizes resume.
The layout unit fixture is explicitly synthetic, has no valid guest program/heap,
and is NEVER presented as EVM-issued state. It verifies the75-byte initial VFS section,
root rehash layout, bounded counts, trailing bytes and every truncation (with outer
length repaired to exercise inner bounds too). All parent preparation tests pass2.798s
and package vet passes; the initial actual24-root EVM failures are still unresolved.

Parent independent initial-artifact normal `build.js --check` under revision1 passed:
175.839s,834547712B peak process-group RSS, no watchdog limit hit; source/runtime/ABI/
combined output remained identical to the recorded initial candidate. Logs
`/tmp/mc-vfs0a-parent-initial-rebuild.{log,json}`. This proves reproducibility and
new LOCAL size compliance only, not functional correctness.

Parent reran the24 fixture pins/rebuild and Java8/21 C-locale host oracles: all pass
1.232s (external1.587s,285679616B peak groupRSS). Logs
`/tmp/mc-vfs0a-parent-corpus-oracles.{log,json}`. Protected existing EVM/core and
accepted profile paths have no diff from IOE0 acceptance. Two revision1 runtime/
harness correction workers are active from9653767; no third/Fast worker or VFS
acceptance. All24 initial actual EVM controls remain recorded failures pending fixes.

## Parent FINAL artifact execution (still awaiting boundary/adversarial review)

The integrated FINAL293010B artifact, not the intermediate292377B overlay, passed
the entire existing package suite:298.715s (external299.429s),283287552B peak groupRSS,
exit0/no limit hit. Includes original24/20chains, seven path regressions, corrected
contract address/empty inspection, Java8/21 and durability/newprocess tests.
Logs `/tmp/mc-vfs0a-parent-final-artifact-suite.{log,json}`. This run predates the two
extra parent native controls below; those were run separately on the same artifact.

Parent independently ran the full OutputStream generic/default/interface Code on
VFS0a (not raw IOE0): result63, one22566152gas/JVM300/internal4; q7/internal1 has47
slices, same roots;1144B checkpoint. Also a real149-slice q1 truncate-before-bind
chain: parent independently decoded the zero INT handle, top frame PC22..29,
PENDING_BIND/BOUND/CLOSED phases; checked all machine/VFS roots plus FILE content
roots and EVM inspect views; final one-byte file17,1352B checkpoint,max9861807gas.
Logs `/tmp/mc-vfs0a-parent-native-extra.log`, both pass3.168s. This is genuine Java/EVM
file work, NOT Minecraft or a complete-filesystem acceptance claim.

Two isolated adversarial/boundary review workers are now examining the FINAL artifact;
parent keeps reserved tests/production fixes and independently replays the32 acceptance
groups/findings. At most two reviewers; no third/Fast worker. New Make targets expose
the development file-layer test/example without claiming startup; old targets unchanged.

## Independent reviewer disposition and parent takeover

Boundary reviewer2662b18da integrated9c4fda304: assigned boundary/rollback groups pass
on293010B, including genuine exact1MiB/+1. Parent is independently replaying them.
The other reviewer was blocked by its provider and produced NO tests or acceptance
evidence. Parent takes over those remaining local VM-state checks; no blocked review
is counted as a pass and no attempt is made to bypass the provider restriction.

Parent already reproduced six gaps in read-only checkpoint validation on293010B:
a regular file accepted as another inode's parent; slash, dot, non-ASCII and control
bytes accepted as inode components; and WRITE descriptor accepted on a read-only
inode. All use genuine EVM-issued successful controls, then TEST-only changed/root-
rehashed blobs sent only to validateCheckpoint views, NOT live resume. Live ownership/
head integrity is not shown bypassed. Logs `/tmp/mc-vfs0a-parent-directory-rules-initial.log`
and `/tmp/mc-vfs0a-parent-readonly-writer-initial.log` preserve actual failures and
successful duplicate/cycle/noncanonical-bool rejection controls. Production correction
is now parent-owned; new artifact and final reruns are required before acceptance.

The combined historical Make gate hit its20min WALL watchdog while reaching stockS1;
peak855453696B. It is NOT a full pass. Earlier IOE0/SC0/TL0/LC0/interpreter2231/smoke/
fast/LB0/AOT/stockS0 stages passed in its preserved log. A separate bounded remaining
S1/S2a/S2b-L+vet run is in progress, without raising a timeout or altering old artifacts.
Logs `/tmp/mc-vfs0a-parent-legacy-watchdog.json` and
`/tmp/mc-vfs0a-parent-legacy-remainder.{log,json}` distinguish the two phases.

## Parent state correction and completed takeover checks

Parent corrected `_validateVFS`: every non-root parent must be a directory; components
must be printable ASCII without slash and cannot be dot/dotdot; WRITE descriptors
(including closed) cannot target effective-readonly inodes. Error offsets now identify
actual VFS record starts rather than section-base-plus-ordinal. The original successful
issued states still validate; all six reproduced invalid-view cases now reject.
No live-head bypass was demonstrated or claimed. Source/ABI/heap/native quotas and
accepted profiles stay scoped as before; ABI and all38 bootstrap images unchanged.

New parent artifact292968B, SHA717683f8ba67141bb7b5640a7079d396cda661dd53cd2afb7ab4eb6032ac3e86;
sourceb95f0788f3a45b580216697866e32814e590670a55144186fc130391986497f3.
Build completed175.377s/842190848B peakRSS, no limit hit. Boundary test artifact pin
was deliberately updated for rerunning the same checks, not retroactively changing
the reviewer's293010B evidence. New full-suite/repro reruns are pending below.

Parent takeover additionally covers both FIS and FOS six-PC pending corridors with
wrong depth/owner/method/local0/ID/handle/stack and inserted extra operand views;
Object NEW-family restrictions with plain Object/Throwable successful controls and
three inherited fields; escaped-after-failing stream subclass; null constructors'
retained default fields; eight reserved-image refusals/lookalike native and three
foreign private invocation modes; repeated genuine message identity/cause; live
owner/epoch/root/artifact/budget controls and proof that a well-formed rehashed VIEW
cannot authorize resume; empty/ASCII/control/component/depth/path exact boundaries.

A dedicated1024-object test reached the real FIS.errorMessage Java frame with no
filesystem effects, then genuinely OOMed allocating its message:247 calls,10327JVM/
7internal,45344B checkpoint. Stock JVMs return FNFE instead under their unbounded
heap, explicitly expected. Initial1020-object fixture OOMed earlier at FNFE receiver
allocation (Java evaluates new before constructor arguments); corrected1019 leaves
that receiver slot and observes the intended message frame. Earlier coarse-slice and
wrong-phase observations were not counted as proof. All caps remain unchanged.

Historical regression disposition: the initial combined Make command timed out at
20min after passing its earlier stages. The separately bounded remaining S1/S2a/
S2b-L and vet run passed124.462s/628736000B. This is two recorded phases, NOT a claim
that the original timed-out command passed or that a wall limit was increased.
