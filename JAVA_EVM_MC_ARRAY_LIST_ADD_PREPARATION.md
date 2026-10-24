# P60 preparation — measured ordinary ArrayList.add plus iterator consistency

P59 is independently accepted. Fresh original143/970853B now reaches2225103J/143I,
45 canonical receipts, epoch45 RUNNING, CP1289923B SHA256
`118714029d987d5336a8d52527f931409da1311002100ac9750ea678c179abfc`.
Next exact q1 CallError(4,171): original awu constructor PC171 invokeinterface
`List.add(Object):boolean`. Actual ArrayList8261/class241 has private size0,
real shared zero backing5638; argument8292 is real original state. This follows
successful genuine ordered-map insertion, not a speculative unused API reference.

## Narrow next capability

Replace only ArrayList's erased add(Object) native refusal with ordinary guest
Java append, returning true. Accept null/references with identity preservation;
write elementData[size], increment private size once. Grow eagerly via a real
Object[] and ordinary reference-copy loop when full. No host or fabricated array,
no Arrays.copyOf/full reflection/new native. Match default-first capacity10 from
shared DEFAULTCAPACITY_EMPTY_ELEMENTDATA identity, int-capacity0 first growth1,
and normal1.5x/min-required growth. Keep existing constructor/clinit behavior and
real zero-array allocations; do not treat every zero backing as default. Resource
allocation is still governed by existing array length/elements/object bounds;
do not clamp/raise quotas or fake successful oversized capacity.

Existing iterators become observably mutable, so append a private structural
modCount in ArrayList (not AbstractList), capture it in Itr, and perform genuine
CME-before-NSEE on next after add, including exhausted/empty iterators. hasNext
can retain JDK-style cursor-vs-private-size behavior. Keep independent cursors,
actual backing reads, null element vs exhaustion distinction and remove refusal.
Keep old instance field prefix elementData/size and Itr owner/cursor where possible.
Reuse existing CME bootstrap; no new class image or global binding expected.

Match Java8 failed-growth ordering: ensureCapacity's modCount increment precedes
new-array allocation; if allocation OOM, private size/old backing remain but the
structural attempt may invalidate an iterator. Do not assert map-style blanket
rollback for caught guest OOM. No new global free-space oracle. Existing isEmpty
can be overridden with private-size code (rather than inherited virtual size),
and typed toArray must read private logical size/storage, not user size overrides.
Its existing short-target raw refusal stays until measured; now test nonempty
fit copies/aliases/tail-null/rest-tail/NPE/ASE for real.

Only old images98 ArrayList and115 Itr may change; all other125 P59 images exact,
including corrected LHM113/helpers124..126 and EnumMap123. Count127 and actual
program positions unchanged. ArrayList1178B SHA566127a7... and Itr713B SHA340358b7...
were independently reproduced byte-exact by parent Java8-g:none with the minimal
7-file source context before handoff. Other context outputs are never embedded.

Required generated gates: default/int0/int-capacity append; >10 and repeated growth;
null/order/same references; callbacks absent; private storage/capacity/size/modCount;
nonempty iterators/NSEE/CME and typed fit copies; mutable subclass lying public size;
retained constructors/clinit/new arrays/arraycopy/String/Arrays/EnumMap/LHM+HashMap;
unsupported getters/setters/remove/addAll/listIterator/noarg/short-copy APIs remain
raw; raw owner replacement, high u16 actual state, independent reopens.

Fresh all9 engine/4 coordinator domains and actual pins/root; native22/String12,
ABI/storage/codec/config-root13 offset, entrypoints/commit/envelope, all quotas and
protected geth semantics unchanged. Pinned Java8-g:none and solc0.8.30/200/viaIR/
Cancun/metadata-off. Generated1B/30s starts, finite measured-shortage doubling only;
outer1200s distinct, no MAX-generated. Parent alone independently rebuilds/gates
and then a fresh original143; worker never reads original/parent/perf evidence.
Preserve all worlds/logs, no reset/clean/gc/deletion/rmdir/fixed-sleep polling,
one guest writer/heavy process. No world preparation/EULA/listening/Done yet.
