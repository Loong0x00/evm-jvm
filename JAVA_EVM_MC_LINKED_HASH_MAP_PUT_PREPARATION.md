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
