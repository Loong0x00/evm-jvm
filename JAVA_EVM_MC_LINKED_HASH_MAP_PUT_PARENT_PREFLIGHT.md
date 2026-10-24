# P59 — real ordered LinkedHashMap.put, independently accepted

Parent evidence: `evidence/java-evm/minecraft-entry/parent-linked-hash-map-put/`.
Worker candidate a6e059a42bd1d30d6180ba52fa83f487d0d1b4da was **not** cherry-picked:
its1191-file commit includes test databases/checkpoints. Parent copied59 source/
artifact files and recorded1132 exclusions; worker worlds remain intact in its
branch/tree, not ancestors of integration. No original payload is tracked.

## Bounded genuine guest data

Only old LinkedHashMap image113 changes; all123 other P58 images remain byte-exact.
Three real entry/live-view/iterator images124..126 append,127 total. Ordinary guest
Java uses subclass-owned linked entries, inherited size/modCount/cache, stable
insertion order, single key-hash callback and incoming equals, old-value returns,
identity-preserving replacement, null keys/values and real fresh content hash.
The inherited HashMap bucket table is unused: no bucket/resizing claim. HashMap/
private-final Node and existing helpers are untouched. Actual empty-map key hashes
naturally0 from real empty state, not identity or an original-specific constant.

Stable Map.Entry aliases support getKey/getValue/hashCode and genuine setValue;
value replacement is nonstructural. Cached live ordered views, independent cursor,
CME-before-NSEE on next, and fitting typed toArray (same target, first-tail null,
rest untouched, NPE/ASE) work. Short typed target raw-refuses before writes.
Prospective ninth distinct same-spread-hash entry raw-refuses after ordinary key
matching and before mutation; <=8 matching-hash entries and matching overwrite
work. Distinct hashes are not capped8. Entry allocation completes before links/
counters; global4096 object allocator remains authority. Near-global-OOM dynamic
map testing was not run; allocation ordering was audited, not a full OOM claim.
Structural same-map callback reentry is an explicit raw boundary. Genuine thrown
callback exceptions retain callback sideeffects while not publishing outer insert.
Map/entry/view equality, get/remove/contains/access-order/more constructors/clone/
serialization remain unsupported, not fake empty/default answers.

## Parent corrections and immutable protocol

Parent found and corrected before any parent world:

- Worker view add(Map.Entry) generated an Object bridge that could throw CCE before
  refusal. An unbounded E erased add now has one native Object descriptor/no bridge.
- View size/isEmpty/typed-copy read actual inherited storage, not overridable public
  methods; a misleading subclass returning777/true passes the independent probe.
- Final head accessor avoids an unadmitted override hook; entry equality remains
  unbound instead of the plan-external, nonreflexive callback implementation.
- All four images rebuilt with pinned Java8-g:none, not host javac--release8.
  Compile-only HashMap Override annotations are removed without adding fake Map
  default bodies or changing access/finality. No compile-context image is embedded.
- Canonical product driver remains1B; larger tests have separate measured budgets.

Engine454237B SHA256 `9a8bacdd578fba25333b7c8423b1a9126b96bab287dd799b964ca27f1c3e8fe9`,
Keccak `5e8e31fa2ba856e0aab97b8fed661ed943450deb318519458e651fa5a892bb27`.
Coordinator5411B SHA256 `1a52808ba4eb2750a810e0dd9f9e7c3628fb0f1164c01622517060be32a3e423`.
Root127 `93e735cb4ba7ce52a6f49d6af7b8942f2f0b472e67365f1dfcb69e70c6461941`;
domain `MC-LINKED-HASH-MAP-PUT-P59-1`, all9/4 fresh tags and actual pins checked.
Raw150/internal277/max276 uses existing u16 wire; all old105..123 actual slots
preserved. Native22/String12, ABI/storage/codec/config-root13 leading-offset skip,
entrypoints/commit/envelope, quotas and protected geth rules remain exact.

## Independent verification and budgets

- Parent main fixture raw2 q7/q1:2384J/19I,180.085s schedule time,1B,peak115316868 gas.
- Raw150 q4096/q65536:2384J/19I; preserved actual1B/2B shortages, separate4B passed,
  peak2770677758 gas. Private entry/view/iterator indices274/275/276 and chains,
  owner sizes/modCounts/cache/node aliases verified from genuine checkpoints.
- Callback exceptions369J and callback-sideeffects770J q1/q7 at1B; equal roots,
  plus new-process reopens. Real inner insertion survives caught guest exception;
  outer insertion/replacement does not occur.
- Large put/order/growth9235J coarse: preserved actual1B/2B/4B shortages,8B passed,
  peak4357777923 gas. Eight-collision2576J coarse at1B,peak575142405 gas.
- Nineteen1B atomic controls cover collision ninth/reentry/hash traversal/short
  target/erased bad add/entry equality/deferred APIs and four raw owner replacements.
- Retained original HashMap put/regex/array clone, reflection/native22/Poison/
  arraycopy, P56 live Arrays and P58 EnumMap gates pass1B with new-process reopens.
- All successful pairs have equal terminal machine/VFS roots/counters; actual
  compiled-EVM config roots equal old flat13 ABI, including the original checkpoint.

Public generated watchdog30s differs from outer1200s; original MAX/60s is separate.
No MAX-generated, full Cartesian compatibility matrix, whole-process RSS or speedup
claim. Parent raw-super generic compile failure, fixture concrete-cast compilation,
refusal harness matcher count, and a read-only Python typo were retained; no failed
attempt became execution authority. Worker empty-directory rmdir attempt was not
parent-authorized; worker state was preserved, not deleted by integration.

## Fresh unchanged original143

143 resources/970853B, fresh P59 world (no P58 checkpoint migration) reached
**2225103 JVM /143 internal steps**,45 canonical receipts,epoch45/lifecycle RUNNING.
Original receiver8260 now has size/modCount1 and one real linked entry8296,
class267, hash0/key8285/value8292/next0. Key8285 is the real empty LinkedHashMap;
value8292 is original awu$a state. No original-state placeholder or injected result.

Checkpoint1289923B SHA256
`118714029d987d5336a8d52527f931409da1311002100ac9750ea678c179abfc`.
Discovery757.567s + same-package precision680.156s. All45 canonical nested ABI/
events/CP/counter chains/DI0 read ranges, reopen and sine65536 raw bits verified.
Next exact q1 CallError(4,171): original awu97 constructor PC171 invokesinterface
`java/util/List.add(Object):boolean`, dynamic receiver is ArrayList8261 with
private size0 and actual zero backing, argument is the same state8292. Descriptor
is from authenticated metadata of the unchanged original class, not a host parser.
Next add only genuine append/growth and necessary iterator consistency, not full
List/Java SE. No world/EULA/listening or genuine Done; LOCAL preinstallation only.
