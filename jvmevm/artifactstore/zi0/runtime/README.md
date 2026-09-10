# MC-ZI0 ZIP index EVM runtime

> Status: frozen-plan production runtime **candidate**, not accepted ZI0. Parent
> integration and independent acceptance gates remain authoritative.

This subtree is the runtime-writer delivery for `JAVA_EVM_MC_ZI0_PLAN.md` at
base revision `5e9ed0d3c`. `ZI0ZipIndex` derives and stores a bounded ZIP central
index using only `AS0.read` calls against one sealed accepted MC-AS0 controller.
Its constructor binds nonzero creator, AS0 address, accepted AS0 runtime code hash,
content commitment, and length in ordinary EVM storage. It has no immutables,
setters, events, fallback, receive function, import path, or measurement API.

The contract exposes exactly 18 functions (five explicit methods and 13 scalar
getters), one constructor, and `ZI0Error(uint256)`. It enforces the frozen three
phases (BOUND/STAGING/FINAL), all-field scan CAS, 1..64 units with no at-end no-op,
atomic transaction batches, exact full-name duplicate/collision checks, final-only
`entry`/`lookup`, the frozen packed record, and instance-bound rolling/final roots.
The constructor's zero-owner error 1 precedes dependency checks. Each operational
call rechecks accepted AS0 code, sealed content, and length binding.

ZIP parsing is performed in EVM in AS0 reads of at most 4096 bytes. The runtime
checks exact classic EOCD geometry/ambiguity, central and local framing, bounded
extras/comments/names, methods 0/8, allowed flags `0x080e` (method 0 refuses bits
1/2), CRC/size metadata agreement, signed/unsigned classic descriptors, strict
local order/nonoverlap, descriptor/data ends before the central directory, ZIP64
sentinels/extra ID 1, and the frozen empty-archive locator-position rule. Names
remain opaque bytes. Stated CRC and plaintext sizes remain untrusted metadata.

This component does **not** inflate bytes, compute plaintext CRC, parse classes,
mount a `ZipFile`/`ClassLoader`, verify an official whole-JAR SHA-256, execute Java
or Minecraft, accept an EULA, open a listener, or establish a genuine `Done` marker.
It changes no accepted AS0/VFS artifact, core EVM behavior, gas accounting,
precompile, consensus, or historical gas cap.

## Reproducible build and pins

Build/check in this directory:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run build
npm run check
# From the repository root:
go test ./jvmevm/artifactstore/zi0/runtime -count=1
```

Pinned build: solc `0.8.30+commit.73712a01.Emscripten.clang`, optimizer 200,
via-IR, Cancun, `appendCBOR=false`, `bytecodeHash=none`. `build.js` checks exact
ABI names/types/order/mutability, no events/fallback/receive, no immutables or
link references, runtime <=24,576 bytes, and complete init plus 64-byte constructor
arguments <=49,152 bytes.

Final generated candidate pins (hashes over binary bytecode unless noted):

- Solidity source: 17,317 bytes, SHA-256
  `78329d1610c0ba180c7e267989bf36190a9d9eb536020acce42234066a94a2ae`.
- Constructor bytecode: 9,873 bytes; complete input 9,937 bytes; SHA-256
  `f3d6d4614cf916cc4be4cd1ef58212642d829d63b710cea9d140181bafd00870`.
- Deployed runtime: 9,177 bytes; SHA-256
  `74ea23889368b3381843e39bb2caf53a66de8dbfdb3dc58dc4a066c97a33d7a3`;
  Keccak-256
  `0c22eca78e00865ce03e8e298708bfe51ce9856cff138d1046905fc285ad5a77`.
- Accepted AS0 deployed-runtime Keccak dependency:
  `c8cec283e80fd82b15254bd50a9f2aea3a91305ba71f756f834439280600f896`.
- Combined artifact file SHA-256:
  `424246923fd5a022ec7dabda19f6847ad36896d5fd34ca8598e7c3f32719443e`.
- Package-lock SHA-256:
  `e148137c7684e40f19b6eb1dca85be2befd8526dbd454142183cd89e31d35171`.

Generated outputs are `ZI0ZipIndex.init.hex`, `ZI0ZipIndex.runtime.hex`,
`ZI0ZipIndex.abi.json`, and `combinedartifacts/ZI0ZipIndex.json`. The combined
artifact includes compiler/settings, source/code/dependency pins, frozen limits,
and storage layout. `runtimeassets.Artifact()` embeds that file and returns a
fresh defensive copy; it has no compiler or source-tree fallback.

## Final-artifact runtime control

`runtime_test.go` creates the accepted embedded AS0 controller with ordinary
`core/vm/runtime.Create`, appends a generated ZIP through an AS0-created
`STOP || raw` page, seals it, then creates this exact embedded ZI0 init code with
ordinary EVM CREATE. The generated fixture includes a stored opaque binary name
and a DEFLATE-range entry with a signed data descriptor. The test independently
checks ZIP geometry, rolling root ABI encoding, every packed field, raw name
round trips, final-only publication, missing lookup, exact zero-owner error 1,
and exact correctly-CASed EOF/zero-unit error 11.

One final-artifact run under the pinned dev-chain context measured:

- AS0 CREATE 611,673 gas; append 234,585; seal 31,394;
- ZI0 CREATE 1,935,216 gas; discover 352,708;
- two q1 scans 128,163 and 120,949 gas; finish 43,329;
- final root
  `03377da41f9ed5dc837aff9f27c92103bbba5cc7dbd6f4733bdced2c812bd121`.

The existing Git-tracked preflight driver was also replayed against this exact
embedded final bytecode (artifact input mapping only, no runtime/source recompilation).
All six generated runs and all 54 parser/state controls passed in 13.877s with
309,432 KiB process `Maxrss`: target-shaped 20,554 entries with fresh-process reopen,
32,768-entry capacity, simultaneous maximum fields, empty ZIP, and q1/q64 root
equality. The target run used 823 publications; ZI0 CREATE was 1,935,216 gas,
discover 69,092,534, 322 scans totaled 2,387,173,354 with maximum 7,478,124, and
finish was 46,129. The unchanged JSON report is retained at
`testdata/preflight-suite-final-artifact.json`, SHA-256
`a8d619e6ca16ae5f41a521b030ad6a1d5bed0e9ace7f7e1f4bf74f07420c3f97`.

The strengthened parent probe driver was then replayed with its two historical gap
observations changed only to require the frozen production policy: zero-owner CREATE
must return error 1, and correctly-CASed empty/EOF scans must return error 11. Seven
runs, the same 54 controls, and all 12 strengthened probes passed in 14.634s with
347,512 KiB `Maxrss`. This includes 79,234,338-gas dense valid EOCD candidates,
47,642,407-gas q64 maximum zero-length-TLV framing, exact geometry errors 23/27,
full-name bucket mismatch 19, opaque names, bounds 31/32, and direct 100,000-gas OOG
after a completed changed SSTORE with exact rollback and successful retry. Its report
is `testdata/parent-probes-final-artifact.json`, SHA-256
`6bf17d9e7313cfe226785a6e1063496a9400ecb1838ca7dbbcaeddcc9a481deb`.
The exact adjusted driver and disposable-workspace wrapper are retained as
`testdata/final_replay.go.txt` and `testdata/replay.sh`; rerun from repository root:

```sh
jvmevm/artifactstore/zi0/runtime/testdata/replay.sh
```

The runtime-local Go test independently supplies the production-policy zero-owner
and correctly-CASed EOF refusals as a fast mandatory control.

These are generated-fixture measurements, not general upper bounds. Frozen limits remain
32 MiB AS0, 8192-byte pages, 4096-byte reads, 32,768 ZIP entries, 4 MiB central
directory, 256-byte names, 1024-byte extras/comments, 64 scan units, 100M/30s
ordinary calls, 1B/120s boundary calls, and the 20min/4GiB whole-gate watchdog.
