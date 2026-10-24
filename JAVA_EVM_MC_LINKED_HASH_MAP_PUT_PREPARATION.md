# P59 preparation — measured LinkedHashMap insertion frontier; design first

P58 guest code remains unchanged. EVM-authenticated targeted original closure:
ImmutableBiMap7898B → necessary superclass FauxverideShim2061B → actual zero-arg
of() linear getstatic RegularImmutableBiMap.EMPTY8844B → constructor/field type
ImmutableMapEntry2212B. Packages140..143 q1 are **metadata only**, not startup
acceptance. The actual current ImmutableMap.of method2 and BiMap.of method1 are
both4B and their unconditional member references are authenticated. No stream,
Collector, Builder or unrelated overload resources were admitted. One wrong caller
index1 metadata query is retained; corrected index2 evidence is authoritative.

Fresh143-resource/970853B package under unchanged P58 reached **2225009J/143I**,
43 canonical receipts, epoch43 RUNNING, CP1289676B SHA256
`3d65e79eaa4ce2804477325c3768b7bbad01d5e43793d14a31efd624cfa94335`.
Discovery759.896s + same-package precision605.144s; no old package checkpoint used.
All43 ABI/events/CP/counters/DI0 reads/reopen checks passed. Actual RegularImmutable
BiMap construction executed; no fabricated empty-map result was injected.

Next exact q1 **CallError(4,161)**. EVM metadata proves original awu constructor
raw97/method0 PC161 **invokeinterface Map.put(Object,Object):Object**, not a symbolic
LinkedHashMap call. Actual stack: receiver8260 and key8285 are real empty
LinkedHashMaps (class256=143+113); value8292 is real original awu$a state.
The receiver's existing P49 native put guard refuses. Crucially ordinary put must
call the key's hashCode; HashMap.hashCode is currently unbound, so merely removing
the put guard or returning identity/constant hash would be wrong.

## Proposed bounded implementation boundary — parent design review required

Genuine insertion-order put: null/value/key identity, one real key hash callback,
matching hash + incoming equals, return old value/null, replacement keeps order,
structural modCount, proper size/isEmpty and cached/live **ordered** entry view.
Real LinkedHashMap content hashCode is needed for the actual empty map key; compute
it from stored entries, including real0 when empty, never special-case original
handles or pretend Object identity. Deferred map equality can remain an explicit
unbound refusal, not false identity semantics for distinct maps.

Keep HashMap/Node/current helpers exact if a coherent subclass-owned real ordered
backend suffices. Accepted HashMap.Node is **private final**; do not silently
change its access/finality or old byte image. HashMap storage/size/modCount/cache
fields are package-private. A real ordinary Java linked-entry backend may preserve
inherited size/modCount and override entrySet/hashCode; do not claim inherited
bucket-table resizing if it is not used. Alternative hook/Node refactors require
parent approval before code changes. No duplicate key hash callback, no exposing
unordered inherited entrySet after admitting put, no synthetic API results.

Plan must describe entry aliases, iterator cursors/NSEE/CME, value replacement
without structural invalidation, typed toArray fitting-target copy/NPE/ASE and
short-target raw refusal consistent with the existing bounded entry-view profile.
Other get/remove/clear/access-order/map constructors/Map.equals remain unsupported
unless separately justified. Explicit collision/treeification refusal before any
mutation is preferable to silently missing JDK callback semantics.

Prefer changing only LinkedHashMap113 and appending at most3 private helper images;
all other123 P58 images exact. Preserve old fields/loadFactor/accessOrder=false,
P58 EnumMap marker, P57 String factory, native22/String12, ABI/storage/codec,
config-root/entrypoints/commit/envelope, all resource bounds and EVM rules. Fresh
9/4 domains/root/actual pins and real high-index/retained gates are mandatory.

The next worker must first write a source-only PLAN and request parent review
before semantic Solidity edits or heavy compiler/EVM work. Original inputs and
all parent review/performance evidence stay excluded. Parent alone later rebuilds,
tests and runs a fresh original143. No world/EULA/listening/Done yet.

## Parent design approval — sa_ad855681dba448f2.r1

The source-only18-file plan/audit were reviewed. Implementation is now approved,
not accepted: subclass-owned real entry chain, only old image113 changed, exactly
3 helpers appended (entry/view/iterator),127 bootstrap images/raw150 count277/max276.
No HashMap/Node privacy/finality or other old-image change. No inherited bucket/
resize claim; inherited size/modCount/cache must stay coherent. Genuine Entry.setValue
is approved with return-old/stable alias/no structural invalidation and focused gates.

Entry upper bound4096 follows existing global object cap, not a new larger quota
or host/precompile free-space oracle. Global allocator remains sole authority.
Allocate an entry completely before linking/counters; no later allocating step in
publication. View/iterator OOM must precede cache publication. Permit8 distinct
same-spread-hash entries; prospective ninth new nonmatching key raw-refuses before
allocation/mutation, after ordinary hash/equals matching search. Matching overwrite
remains possible at the bound. Other hashes do not share an artificial8-entry cap.

Key hash once, before outer receiver writes; incoming equals direction/identity
shortcircuit. Detect same-map structural callback reentry via modCount and raw-refuse
before outer mutation, rather than locking/making fake results. No mutable active-put
lock without review. A thrown guest exception may retain genuine callback sideeffects:
promise only no outer insertion, not a blanket Java rollback. Content hash traverses
real entries with fresh callback hashes/Java32 sum, plus coherence/reentry checks.
Distinct-map equals stays unbound. Typed array fit/tail/NPE/ASE and short-target raw
boundary remain; iterator next checks CME before NSEE, overwrite/setValue no CME.

Protocol/layout-only Solidity integration, all9/4 new domains and actual pins,
helper raw-name reservations/count positions are approved; no generic dispatcher,
ABI/storage/codec/config-root/entrypoint/commit/envelope/native22/String12/quota/EVM
rule change. CHECKPOINT2MiB/runtime1MiB, not a CP-pool2MiB/checkpoint1MiB label.
New Java images-g:none; old P58 EnumMap532B default debug remains exact.
Fresh generated1B/30s with measured-shortage doubling only; outer1200s separate.
Parent alone later rebuilds/replays fresh original143. No acceptance or Done claim.
