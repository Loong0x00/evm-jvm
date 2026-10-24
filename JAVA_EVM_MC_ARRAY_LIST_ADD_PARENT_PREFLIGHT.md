# P60 — ordinary ArrayList append/growth and fail-fast iteration, independently accepted

Worker candidate `b79dc40163dbd31ae51ce60b2507e84e11b3f4d1`; authoritative parent
proofs in `evidence/java-evm/minecraft-entry/parent-array-list-add/`.

## Coupled capability and measured parent correction

Ordinary Java8 add(Object) appends exact references/null and returns true, using
private size/storage. Real Object[] growth preserves the actual default sentinel
identity (first capacity10) vs explicit int0 (first1), then1.5x/min-required growth.
Constructor/clinit zero arrays are not skipped. Private modCount precedes growth
allocation, and Itr captures it/checks CME before NSEE, including empty/exhausted
iterators. isEmpty and typed fit-copy read private size, not overridable public
size. Fitting target identity/order/tail-null/rest-tail/NPE/ASE are real. Short
copy/get/set/remove/indexed add/addAll/listIterator/noarg/equals/hash/clone remain
explicit raw profile boundaries, not UOE/AME or invented values.

Only bootstrap98 ArrayList1178→1620B and115 Itr713→856B change; other125 images
remain byte-exact (including P59 corrected ordered map and P58 EnumMap532B debug
image). Count127, actual slots and existing u16 high-index wire are unchanged.

Parent coarse-first gates exposed an older VM resume bug, not an add algorithm
failure: an all-null String[] passed to Object[] after checkpoint could have no
component object to warm scratch source hierarchy links. `_requireAssignable`
validated only the wanted leaf. A small parent addition validates the actual
reference-array leaf using the existing hierarchy resolver before normal array
covariance. No new API/type rule/wire/native/quota was added. Exact old-function
normalization checks that this is the sole extra shared-method change.

The counterexample is independent of ArrayList: generated cold String[]/Sub[]/
Tagged[] argument arrays. Accepted P59 direct succeeded while q1 raw-refused with
ReferenceError2; evidence retained. Corrected P60 q1/q7/direct agree. Incompatible
Object[]→String[] generated argument still raw-refuses, not an always-true shortcut.

- Root127 `a34286fcbd75d2da7c02c3c803a825d1b77d7228a896da502973dbf15e1ad2ed`.
- Domain `MC-ARRAY-LIST-ADD-BOUNDED-1`, all9 engine/4 coordinator tags and pins fresh.
- Engine455023B SHA256 `829545f33510d28879685dc26928a33f454ba88b4f729e1f9d7c3085bccd35ce`,
  Keccak `f16a96a46bec49a5c7fb00072571dbd60d07ca5bf3b1420a2ce551452d5ce369`.
- Coordinator5411B SHA256 `09a45def3bb69a10528a0846d06309cef1d4ceecbeee4e70b8f426dca04bee93`.

Native22/String12, ABI/storage/codec, config-root13 encoder/offset, entrypoints/
commit/envelope, all quotas, EVM charging and protected geth source remain exact.
Pinned Java8-g:none and solc0.8.30/200/viaIR/Cancun/metadata-off independently rebuilt.

## Generated gates, budgets and real OOM

Parent core4434J/17I: raw2 q7/q1 at1B,316.148s schedule time,peak109248970 gas.
Raw150 q4096/q65536 same steps: preserved1B/2B/4B shortages, separate8B passed,
peak6191590987 gas. Actual private capacity/size/modCount triples are22/22/22,
1/1/1,3/3/3; a public-size777 subclass has private2/cap10/mod2. Itr index265 at
raw150 and three-field owner/cursor/expected-state wire are genuine checkpoint data.

Cold-array regression57J q1/q7/direct at1B,peak40302124 gas. Ordinary generated
byte-array pools and unit allocations saturate the **unchanged262144 element
quota**, no host/private/checkpoint injection. Failed add growth preserves cap10/
size10 but modCount11, and failed first int0 add leaves cap0/size0/mod1. Old iterators
throw CME; a fresh iterator still reads the ten real references. This1990J profile
quota test (not stock Java heap oracle) passes q4096/direct at2B after preserved1B
shortage,peak1385595199 gas. Sparse primitive checkpoints remain lossless and fresh
process reopens pass.

Seventeen1B atomic unsupported/raw-owner/incompatible-array controls pass. Retained
native22/Class/Poison/arraycopy, Arrays live views, EnumMap, HashMap put/regex/clone,
and corrected P59 ordered map gates pass1B coarse with reopens. All successful
quantum pairs have equal machine/VFS roots/counters; actual compiled-EVM config
commitments match old flat13-field ABI, including the original checkpoint.

Old two-field/zero-size read-only observer was updated to typed third modCount and
0<=size<=backing length, not used as guest execution input. Preserved failures are
observer001, cold-array q7 under worker binary002, worker's wrong q1 iterator test,
and measured budget shortages. No failed checkpoint becomes execution authority.
Public generated watchdog30s and outer1200s differ; original MAX/60s is separate.
No full Java SE/Cartesian matrix/RSS or performance speedup claim.

## Fresh original143

Unchanged143 resources/970853B, no P59 or worker checkpoint migration. Fresh
corrected P60 reached **2225278 JVM /143 internal steps**,46 canonical successful
receipts,epoch46/lifecycle RUNNING. Actual ArrayList8261 now has size/modCount1,
real capacity10 backing8297, slot0=original state8292, remaining slots null.

Checkpoint1290587B SHA256
`b58f1772600d5e8f2e45f4e9142d41a3faec7c10026c4339a50c00884bd70798`.
One owned60s deadline cancellation was preserved atomically; quantum reduced from
65536 to32768, no watchdog increase. Phases717.523+270.332+42.521+353.838s. Prior
public JVM-step telemetry chose one finite current-code quantum29647 to approach
the previous frontier; it was **budget planning only**, not old guest state or an
oracle result. All progress still executed current EVM code, then256→1 localization.
All46 canonical nested ABI/events/CP/counter chains/DI0 reads, reopen and sine raw
bits verified. Next exact q1 missing class is `com/google/common/collect/HashBasedTable`,
site4107/context15, original awu$a method8. Next authenticate needed original
resource/hierarchy, not host parse or guess table behavior.

LOCAL oversized preinstallation + ordinary EVM Call only. No world preparation,
accepted EULA/configuration startup, listening server or genuine Done yet.
