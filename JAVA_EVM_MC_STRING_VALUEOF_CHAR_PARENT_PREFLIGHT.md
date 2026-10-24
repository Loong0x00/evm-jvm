# P57 — ordinary one-unit String.valueOf(char), independently accepted

Evidence: `evidence/java-evm/minecraft-entry/parent-string-valueof-char/`.
Worker candidate `df6c37e4c664435bf9ccacadc1b12d3298c0d8f9` used only its approved
10-file source snapshot. Parent independently reproduced old and new Java8 images,
rebuilt pinned solc artifacts, strengthened controls, and ran a fresh original138.

## Narrow implementation and parent correction

`String.valueOf(char)` is ordinary Java bytecode: allocate `char[1]`, `castore`,
then the existing copying `String(char[])` constructor. It produces one exact
UTF-16 code unit, including NUL and isolated surrogates, not decimal integer text,
an ASCII-only conversion or an intern/literal shortcut. Existing String fields,
old method Code (CP indices normalized), bridges and native declarations remain.
Only bootstrap leaf26 changes,2198→2285B, SHA256
`fe68ab4a5124d504c2a56805cf8766b4c5f5ccdbb646733351b67bac8ddfef2a`.
All122 other images and actual123-class program assembly remain exact.

The sole resolver change admits exact non-interface ordinary symbolic reference
`java/lang/String.valueOf:(C)Ljava/lang/String;`, then uses normal method/access/
signature/Code validation. Other String overloads and Comparable/CharSequence
static references keep the old refusal path. Native global22/String-local12,
constructors, restore rules, config-root encoder, entrypoints, commit/envelope,
ABI/storage/codec, quotas and geth charging/consensus rules are unchanged.

The worker failed to refresh P56 protocol domains. Parent preserved that candidate
and its reports, then corrected **all9 engine/4 coordinator domains**, rebuilt and
repinned before any parent execution. Historical worker worlds are not acceptance.

- Domain: `MC-STRING-VALUEOF-CHAR-BOUNDED-1`.
- Root123: `10dffc603774551e32da71d0b20c9002460ec64b4d48cf23d6a29cbf195ffd7c`.
- Engine445564B SHA256 `6a91e222d7406511a5cbacf27a3b349eeebba240227b9e908199c36ba4aba4b7`;
  Keccak `1d3300d57b13ba527e7263285457b800e54d764504bbd75a7e45cc583b9aa162`.
- Coordinator5411B SHA256 `0c11c4dfd2dfb7997a01954aeacdcec8df5796398beae78f5ca48005f753e6b4`.

## Independent gates, not a complete String profile

Parent21-unit fixture covers44,0,9,10,13,32,48,65,127,128,255,256,32767,32768,
55295,55296,56319,56320,57343,57344,65535; real independent results/backings,
constructor-copy isolation, copy constructor, intern/hash/compare/charAt/equals,
canonical Class mirror and retained live Arrays/Singleton traversal. Private heap
proofs show at least4 String objects and3 distinct backing arrays per unit.
The worker separately ran a stock-Java8 all65536-unit oracle: test-only, not an
exhaustive EVM claim or oracle-as-input.

Fresh raw1 q7/q1: **9458J/5I**,1106.413s schedule time,1B per-call budget,
peak210723063 gas. Raw150 q4096/q65536 started1B, then2B/4B/8B only after actual
preserved shortages; separate16B schedules passed with peak11433296028 gas.
This is not an ordinary1B or U64MAX generated-gate claim. Actual273-class wire,
String class176 and retained iterator272 are proven in checkpoint records.
Terminal machine/VFS roots/counters agree and new-process reopens pass.

Eighteen1B atomic controls include deferred valueOf overloads/copyValueOf,
wrong call kind, malformed descriptor, interface-owner/reference rules, raw
String/Comparable/CharSequence replacements and existing charAt bounds refusal.
Existing charAt OOB remains raw StringProfileError2, not a new Java exception.
A first harness wrongly demanded a prior RUNNING Head for an immediate start
refusal; preserved, fixed only control routing, then fresh worlds rerun.
Retained reflection/native22/Poison/arraycopy and full P56 generated backing/tail/
AL/HashMap controls pass at1B with separate-process reopens.

Generated public watchdog30s differs from outer1200s; original MAX/60s is separate.
No whole-process RSS or optimization/speedup claim. Actual compiled-EVM config
roots match old flat13-field encoding for every generated schedule and original.

## Fresh unchanged original138

138 resources/947894B, no P56 checkpoint migration. Fresh P57 reached
**2224810 JVM /138 internal steps**,42 canonical successful receipts,epoch42,
lifecycle RUNNING. Original Joiner8287 stores real factory String8289, whose
owned char[]8290 contains only44; temporary char[]8288 is a distinct object also
containing44. No native char-conversion binding or fabricated separator was used.

Checkpoint1288844B SHA256
`d006e49e06c4497180542fd25eeb484e2fb6062d4d08f9f5d9cc8469fc05e06b`.
Discovery700.754s plus same-package precision594.819s. All42 canonical nested
ABI/events/CP hashes/counter chains/DI0 reads, genuine reopen and sine65536 raw
bits independently verified. Exact q1 next missing class is **awp$1**,site4104,
context8, current original awp.<clinit> PC8. Next authenticate that class through
EVM resource/header inspection; do not guess its behavior from a host parser.

LOCAL oversized StateDB.SetCode + ordinary EVM Call only. No world preparation,
accepted EULA/configuration startup, listening server or genuine `Done` yet.
