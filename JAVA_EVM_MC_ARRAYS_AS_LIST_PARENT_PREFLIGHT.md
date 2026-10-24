# P56 — real live-array-backed Arrays.asList, independently accepted

Parent evidence: `evidence/java-evm/minecraft-entry/parent-arrays-as-list/`.
Worker `sa_95568c7af65d4248` returned uncommitted source/evidence in its isolated
worktree (base `41b88053b`); no worker commit is invented. The parent verified the
15-file source-only baseline, copied hashed candidate files, independently rebuilt
Java8 and pinned solc artifacts, and executed fresh generated and original gates.

## Bounded semantics and immutable prefix

`Arrays.asList(Object[])` creates a fresh fixed-size list holding the **same**
caller-owned reference array. Empty/nonempty arrays, null elements, and typed
String/interface arrays work; null array input genuinely throws NPE. Independent
iterators keep their own cursor, read current backing-array cells, return exact
reference identity (including null), and genuinely throw NSEE on exhaustion.
Caller writes after factory/iterator creation are observable. This is neither a
snapshot nor a singleton/empty-array shortcut. RandomAccess/Serializable markers
are retained; full serialization and general List conformance are not claimed.

All120 old bootstrap images and order are exact. Appended images are Arrays458B,
Arrays$ArrayList647B, Arrays$ArrayIterator534B, at120..122. Correct123-image root:
`27088ed35f9d324cba2f737fc19f693af2de8010790e9aa269b630c87399155c`.
Actual old105..119 program placements are preserved, including reflect Array116
at count-7 and Singleton helpers118/119 at count-5/-4. New iterator is actual class
**272** at raw150/internal273, proven from checkpoint records, not count arithmetic.

- Engine445645B SHA256 `09f4dc97001895a489f261c44972eb0d51eca024eb5c0d96177243c2bece84b3`;
  Keccak `f40e81cc3baa62152bdd5b3aafcf8cde1976c5f3511118ebdd48545a65a5d0d6`.
- Coordinator5411B SHA256 `ae071a0ba0634fb4deb8a7981f911503d81027d4507ccc4cb65bf86a33de9627`.
- Domain `MC-ARRAYS-AS-LIST-BOUNDED-1`; all9 engine/4 coordinator domains and actual
  hash pins checked. Native global22/String-local12, ABI/storage/codec, quotas,
  gas reserve and geth rules unchanged. No entrypoint/commit/envelope/config-root
  refactor in P56. Actual compiled-EVM config roots equal old flat13-field ABI in
  every generated schedule and the original checkpoint.

## Independent gates and honest budgets

Parent fresh raw1 q7/q1: **996J/15I**,58.044s schedule time,1B per-call budget,
peak85052950 gas. Raw150 q4096/q65536 first genuinely exhausted1B; failure retained,
then separate fresh2B schedules passed996J/15I, peak1043018160 gas. Each pair has
identical terminal machine/VFS roots/counters and fresh-process reopen validation.
Dense private-state proofs show two wrapper objects and two cursor objects sharing
one actual array, updated cells, and independent cursor fields. Generated stock
Java8 oracle is test-only, never original execution input.

Thirteen1B atomic refusal controls cover add/get/set/equals/hashCode/typed and
noarg toArray/iterator.remove, other Arrays APIs and all3 new raw owners. Explicit
add(Object) guard prevents an inherited abstract AME. Retained native22/Class/
Poison/arraycopy controls pass on fresh P56 code, with separate-process reopens.
Generated public watchdog30s differs from outer1200s; original MAX/60s is separate.

Preserved parent harness issue: the copied read-only root helper initially assumed
123 even while the parent verified the old120 root. Only the parent diagnostic
was generalized; first failed build remains. Worker pins confuse12288 allocatable
object+array slots with12545 handle frontier and label checkpoint bytes as constant
pool bytes; original pins remain evidence, parent pins distinguish these. No
whole-process RSS measurement or speedup claim is made.

## Fresh unchanged original138

The package remains138 resources/947894B. No P55 checkpoint was migrated. Fresh
P56 execution produced **2224752 JVM /138 internal steps**,41 canonical successful
receipts, epoch41/lifecycle RUNNING. The original created Arrays$ArrayList8284
(class259) storing the real Object[]8280 of length0. The original Singleton
iterator8282 is already consumed. Full Cartesian-product behavior is not claimed.

Checkpoint1288813B SHA256
`0c9da3098fe43c013be6221c44c273c731afd33a334d7d95ef1cfcd7a68054ac`.
All41 nested ABIs/events/checkpoint hashes/counter chains/DI0 reads and the sine
65536 raw bits were independently checked.

The initial outer controller timed out at1200s before its summary, after reaching
that successfully published RUNNING checkpoint. Partial logs/processes are retained,
not mislabeled a completed discovery. No heavy child remained. A **new process**
then made an exact q1 call from the same code/package checkpoint: atomic refusal,
Head unchanged, followed by genuine reopen verification (17.148s). This is not
failed-state recovery or continuation from a terminal Java exception.

**Next measured blocker:** original `Joiner.on(char)` (raw86/method1) PC5 calls
`String.valueOf(C)String`, char44. EVM-authenticated selected-method metadata proves
that descriptor and the caller `awp.<clinit>` PC2. Exact StringProfileError(1,5),
selector0x32e310eb. Next work should add only genuine one-UTF16-unit conversion,
prefer ordinary guest bytecode using existing char[]/String construction, no
additional native binding or decimal-char substitution.

LOCAL oversized StateDB.SetCode preinstallation + ordinary EVM Call only; no
standard CREATE deployability, world preparation, accepted EULA/configuration,
listening server or genuine `Done` yet.
