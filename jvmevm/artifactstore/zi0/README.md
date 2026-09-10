# MC-ZI0 opaque transport

This package is the Go transport for the frozen `ZI0ZipIndex` EVM artifact. It
creates one accepted AS0 store and, after sealing, one ZI0 controller in the
same StateDB/trie. All ZIP directory decisions remain in EVM bytecode: Go only
packs ABI calls, transports opaque bytes, commits/reloads state, and exposes
copied getter results. It contains no production ZIP parser, name catalogue,
offset map, page installer, class extraction, compiler fallback, or host-side
resource authority.

`NewMemory` and a fresh `Open` initially perform an ordinary AS0 `CREATE` only.
Upload uses separate `Append` and `Seal` calls; `CreateIndex` is a separate
ordinary EVM `CREATE`. `Discover`, `Scan`, and `Finish` are exact CAS operations.
Disk publication synchronously commits trie and code, writes and fsyncs a unique
manifest temporary, renames it, then fsyncs the directory. Every successful
mutation is reloaded. Pre-publication failure restores the previous published
root; failure after manifest rename poisons the session until exact reopen.
Reopen verifies metadata before LevelDB, then code, nonce, EVM getters, lifecycle
shape, and cross-controller bindings. It never deploys missing code.

## Embedded production pins

The loader accepts only the generated combined-artifact schema and independent
hard-coded candidate pins, not hash/settings fields merely asserted by that JSON:

- combined artifact SHA-256
  `424246923fd5a022ec7dabda19f6847ad36896d5fd34ca8598e7c3f32719443e`
- source SHA-256
  `78329d1610c0ba180c7e267989bf36190a9d9eb536020acce42234066a94a2ae`
- constructor bytecode: 9,873 bytes; complete input with 64-byte arguments:
  9,937 bytes; SHA-256
  `f3d6d4614cf916cc4be4cd1ef58212642d829d63b710cea9d140181bafd00870`
- runtime: 9,177 bytes; SHA-256
  `74ea23889368b3381843e39bb2caf53a66de8dbfdb3dc58dc4a066c97a33d7a3`;
  EVM Keccak
  `0c22eca78e00865ce03e8e298708bfe51ce9856cff138d1046905fc285ad5a77`
- accepted AS0 runtime Keccak
  `c8cec283e80fd82b15254bd50a9f2aea3a91305ba71f756f834439280600f896`
- solc `0.8.30+commit.73712a01.Emscripten.clang`, optimizer 200, via-IR,
  Cancun, CBOR disabled, bytecode hash `none`, no immutable substitutions
- exact ABI: constructor + `ZI0Error` + 18 functions (20 entries), no events,
  fallback, receive, aliases, or additional callable surface

`Runtime`, `InitCode`, and `ABI` return defensive embedded copies only.

## Real-artifact test coverage

The package tests execute the embedded production AS0 and ZI0 bytecode in the
real EVM runtime. Trusted test-only ZIP/DEFLATE builders provide opaque fixtures;
they are not linked into production authority. Coverage includes:

- fresh memory/disk AS0 CREATE, nonce/address/code/publication, seal, separate
  index CREATE, BOUND/STAGING/FINAL lifecycle, copied views, close and mutex
- strict combined schema/ABI/settings/source/code/dependency/limit pins and
  negative asset/ABI forms
- EOCD ambiguity, dense maximum tail, prefix, empty, bounded ZIP64 policy;
  CEN/LOC framing, flags, methods 0/8, extras, descriptors, range and geometry
- opaque binary names, duplicates, isolated TEST-only occupied-bucket redirect
  proving the EVM full-byte guard, and independent packed-record/root derivation
- CAS/units/at-end refusal, wrong/zero owner, constructor rollback/retry, direct
  OOG rollback/retry, atomic failed batches, and concurrent stale-call refusal
- entry/lookup/AS0 range boundaries and explicit noncanonical decoder errors,
  including AS0 `pageCount` overflow and index phase/root/cap/binding alteration
- every-call durable publication, pre-publication rollback, ambiguous-rename
  poison/reopen, manifest namespace/pins/bounds, incomplete/orphan preservation,
  root aliases, fixed links and nested `state/CURRENT` refusal
- actual fresh-process mid-upload, sealed-AS0, BOUND, STAGING and FINAL reopens;
  one stage runs from a relocated test binary with embedded assets
- 20,554 entries with exact 2,100,796-byte CD and 823 durable publications;
  32,768 entries with exact 4 MiB CD plus a +1 refusal; q1/q64 equal roots;
  64 simultaneous maximum name/extra/comment records; exact 32 MiB AS0 archive
  and high 25-bit packed offsets

The final worker run and per-call aggregate measurements are retained at
`testdata/final-suite-52d45b3e7-r3.log` (preceding runs are retained, not
overwritten). The key production-transport measurements
from that run are:

- target 20,554: 496 appends, 322 scans, exactly 823 publications;
  append sum 881,638,867 gas, scan sum 2,387,173,374 gas; 41,513,628 disk bytes
- capacity 32,768/exact 4 MiB CD: 997 appends, 512 scans; append sum
  1,772,693,340 gas, scan sum 4,470,603,173 gas
- exact 32 MiB: 4,096 appends, append sum 7,289,399,396 gas; high-offset scan
  150,317 gas
- shared observed calls: AS0 CREATE 611,673 gas, max append 1,830,926 gas,
  ZI0 CREATE 1,935,216 gas, discovery about 69.09M gas, finish 46,129 gas;
  dense EOCD ambiguity 79,223,750 gas

These are aggregate/local measurements, not single-call limits, EVM instruction
counts, Java heap, official-JAR verification, or acceptance. Frozen limits remain
100M/30s ordinary, 1B/120s explicit boundary, 32 MiB AS0, 8 KiB pages, 4 KiB reads,
32,768 entries, 4 MiB CD, 64 scan units, and 20min/4GiB whole gate.

## Scope

ZI0 supplies only an EVM ZIP central-directory index and committed compressed
ranges. It does not inflate data, verify plaintext CRC, implement `ZipFile` or a
class loader, execute Minecraft, accept an EULA, create a listener, or prove the
genuine startup-complete marker. Package completion is not parent acceptance.
