# MC class bytes -> existing EVM JVM bridge preflight

Status: **DISPOSABLE PREFLIGHT COMPLETED, NOT ACCEPTED**. Base `73e17afbb`. This demonstrates a bounded generated-fixture path and measures the smallest adapter found. It changes no production/accepted runtime, ABI, quota, opcode, gas rule, VFS, Make target, or core file. Parent replay/review is still required before any freeze. No official server/JAR/class was read, uploaded, inflated, or executed; no EULA, listener, world, startup, or Done activity occurred.

## Selected existing engine and exact boundary

The selected entry is the latest accepted LOCAL VFS0a `VFS0aInterpreter`, not a new API:

- runtime 292,968B, SHA256 `717683f8ba67141bb7b5640a7079d396cda661dd53cd2afb7ab4eb6032ac3e86`, Keccak `e7f4de699588a3d58624e8ab717a00809759d112952ca1fac8bbc74637118c84`;
- frozen LOCAL address `0x4a564d45564d564653304152554e54494d450001`;
- `start(bytes32,bytes[],string,string,int32[],SeedFile[],uint64,uint32)` and `resume(bytes32,uint64,bytes32,bytes[],bytes,uint64,uint32)` are the only execution entries used;
- `start` takes 1..4 raw classes, at most 65,536 aggregate raw bytes, JVM-internal slash-separated `entryClass`, an entry name, at most eight int32 arguments, and 1..4096 JVM/internal units;
- `resume` requires exact instance/epoch/checkpoint CAS, the same raw-class artifact root, and an EVM-issued checkpoint. Checkpoint maximum remains 1MiB. The VFS limits remain 64 inodes, 32 descriptors, 64KiB per/all files, and all other accepted limits;
- `_prepare` parses each class in EVM, rejects malformed classes and duplicate/reserved names, resolves declared `this_class`, requires the requested entry class/method and supported static Code, and appends the accepted fixed 38-image bootstrap graph. No host class parser/catalogue participates;
- the runtime is deliberately over EIP-170. The harness installs only these exact accepted bytes at the frozen LOCAL address. This is not CREATE or standard-chain full-JVM deployment proof.

VFS0a anchors bind `owner = msg.sender`. A direct nested call is legal. Therefore the adapter, not the host EOA, owns every VFS instance. The adapter stores its own constructor caller and gates both `start` and `resume`; the measured VFS head owner is adapter address `0xac487a04804410a554ce30b62bf6f3328ece69fa`. This prevents an arbitrary caller from using the adapter to bypass VFS0a's otherwise-correct caller check.

## Disposable adapter

`ClassBridge.sol` is ordinary-CREATEd and has only constructor, `owner`, `previewBinding`, `start`, `resume`, and `BridgeError(uint256)`. It has no fallback/receive/event, class-byte input, decoded-byte import, page installer, host callback, class limit change, or engine patch.

For every start/resume it:

1. checks caller ownership and exact accepted DI0/VFS0a code hashes;
2. requires raw ZIP name = exact JVM-internal `entryClass || ".class"` (slashes remain slashes; dotted source names are not substituted);
3. reads DI0 `phase`, `nameHash`, `indexRoot`, `finalRoot`, and `plainSize`; requires FINAL phase 4, exact caller assertions, nonzero roots, and size 1..65,536;
4. invokes DI0 `read(0,plainSize)` by EVM `STATICCALL`; DI0 itself reads only its verified EVM-created FINAL pages;
5. computes a distinct package/input commitment over decoder/code/index/name/resource F/size/plain Keccak/engine/code/entry class; and
6. places those EVM-returned bytes into VFS0a's existing `bytes[]` ABI and makes the nested EVM call. Resume repeats the same EVM read/binding and transports only the prior successful EVM-issued checkpoint supplied back by the driver.

The wrapper never exposes plaintext class bytes. It returns only its input binding and the existing engine's result/checkpoint encoding. Resource F, adapter input binding, checkpoint root, machine root and VFS root remain separate domains and measured values.

Pinned disposable build: solc `0.8.30+commit.73712a01.Emscripten.clang`, optimizer 200, viaIR, Cancun, `appendCBOR=false`, `bytecodeHash=none`. Source SHA256 `76f95867bbb9714aa4cd49b9222529be64236282d8e06a94f5e8d63f2678342b`; init 3,823B SHA256 `f24b8b115bf42afc2d83eb22dc1654b132c40167fec4664c3110a636790531cb`; runtime 3,780B SHA256 `49f81b97402bf95f000c4bfaa5cf2f901df5e5b2788c0e1bc77e89951456c7a9`; ordinary CREATE gas 778,934. Combined disposable artifact SHA256 `cfdb6298ab3a5b2add12d74ac8b9f310fd59c936afe0d29a20d2e16448c38657`.

## Actual EVM proof

Trusted Java 8u504 classes are compiled with `-source 8 -target 8 -g:none`. Each has a loop, branch, arithmetic/bit operations, and an actually invoked private static helper. The separately labeled Java 8 reflection oracle returned `BridgeAlpha(7)=76` and `BridgeBeta(8)=203`; those outputs never enter the ZIP, adapter, or EVM calls.

Each success starts from only one opaque deterministic ZIP upload and follows ordinary EVM AS0 controller/page CREATE -> ZI0 name/range discovery -> DI0 DEFLATE/CRC/FINAL page CREATE -> adapter EVM read -> unchanged VFS0a parse/link/bytecode execution:

| chain | ZIP / class | result | slices | bridge gas | JVM/internal | input binding | resource F | machine root |
|---|---|---:|---:|---:|---:|---|---|---|
| alpha direct | 386B / 295B | 76 | 1 | 4,110,646 | 181/2 | `e33fe6b6...a5e7` | `e3c0a96c...1c94` | `ba2f3365...4643` |
| alpha q7 | same EVM resource | 76 | 26 | 92,686,438 total | 181/2 | same | same | same |
| beta direct | 384B / 301B | 203 | 1 | 4,289,248 | 225/2 | `cc12e525...e1ed` | `ad0957c9...6489` | `4a2dd523...15c9` |

Alpha q7 consists of one real start plus 25 successful resumes. Every checkpoint came from the preceding successful EVM call; no failed-call output, trace, OOG state, or recovery was used. Direct and q7 terminal machine/VFS roots and total counters agree. Their checkpoint roots differ honestly because instance/epoch framing differs. Alpha and Beta have distinct ZIPs, classes, resource/index/input/machine roots and results.

Five independent generated resource sessions were used (the malformed archive appears once bound/unverified and once fully FINAL). DI0 final examples used q128 decoding, one output page, 255/260 work for Alpha/Beta, and retained accepted 100M calls. Across the final run the tracked driver recorded 140 operations and 163,019,716 gas including accepted getter views; `final-report-73e17afbb.json` contains every operation. Its `accountedGetterMutationAndAdapterCalls=1751` is an accounting subtotal (individual accepted Head getters, mutations, and source-counted adapter calls), not a claim to be a complete internal EVM message-frame census. Exact workload counts are 28 successful bridge slices, six failed bridge calls, five wrapper CREATEs, five AS0/ZI0/DI0 controller sets, five AS0 data pages, and four DI0 FINAL output pages. All top-level calls used the ordinary 100M allowance; no 1B boundary call was used. Maximum measured top-level operation wall was 9ms.

## Refusals and authority checks

All failed calls left the tested VFS instance head absent; no Java outcome/checkpoint was consumed:

| case | EVM outcome | gas | point |
|---|---|---:|---|
| unauthorized caller | `BridgeError(10)` | 3,488 | before DI/JVM call |
| unverified DI0 phase | `BridgeError(4)` | 23,361 | before DI read/JVM call |
| wrong archive-name binding | `BridgeError(5)` | 22,389 | DI name hash mismatch, before read/JVM |
| wrong resource F | `BridgeError(7)` | 31,717 | before read/JVM |
| ZIP `BridgeAlias.class` containing declared `BridgeAlpha` | existing VFS0a `LinkError`, selector `427cfac5` | 180,985 | actual engine declared-name/link verification |
| CRC-valid ZIP containing a deliberately bad class magic | existing VFS0a `ClassError`, selector `8e473891` | 117,393 | actual engine class parser |

Thus a caller root is only an assertion: it cannot import or bless bytes. DI0 must establish FINAL/name/index/F first, and VFS0a independently parses declared class identity. A correctly named archive containing a differently declared valid class does not become executable under the archive name.

## Harness honesty and measured blocker

The accepted DI0 and VFS0a Go sessions each own separate private StateDBs and expose no legal shared-world/coordinator attachment API. The disposable replay therefore takes DI0's StateDB pointer using reflection/unsafe solely to install the exact accepted LOCAL engine and ordinary-CREATE the adapter in that world. It never obtains class plaintext from the pointer. This is test scaffolding, not production authority, but it proves the Solidity/EVM bridge itself is possible.

The smallest next production profile is a shared-world class coordinator/transport, not an engine callback or quota change:

- ordinary-CREATE a fixed owner-gated coordinator in the AS0/ZI0/DI0 world;
- register up to the existing four FINAL DI0 decoders with exact index/name/F/code bindings, total plaintext <=65,536;
- derive each JVM-internal class name exactly from `name.class`, EVM-read each FINAL resource, and call unchanged VFS0a start/resume;
- persist coordinator/VFS anchors/checkpoints under one durable root with explicit owner/epoch/CAS and no Go class parser or raw-class execution input;
- keep exact accepted DI0, VFS0a runtime, bootstrap, heap/image/checkpoint/VFS and gas limits. Parent must define ordinary LOCAL installation/persistence semantics for the oversized engine and independently test stale bindings, ordering, multi-class totals, rollback, reopen and owner transfer policy.

No accepted legal interface currently provides that shared-state lifecycle, so this preflight does **not** propose treating reflection as production or modifying either accepted session.

## Original-server frontier (static only)

The already documented original `MinecraftServer.class` is 33,457B and therefore individually below DI0's 262,144B and VFS0a's 65,536 aggregate raw-byte ceiling. That arithmetic is not loading, linking, initialization, reachability, or execution evidence. Its transitive class graph is not demonstrated to fit four classes/64KiB; VFS0a has only its fixed 38 bootstraps, no general ClassLoader/JAR/resource mechanism, and only the accepted opcode/library/platform subset. Resolution, `<clinit>`, heap/image quotas, Java SE APIs, threading/scheduling, logging, resources/configuration and startup work remain blockers. No cap should be raised from this small-fixture result.

## Durable evidence and replay

Final evidence is under `evidence/java-evm/class-bridge/preflight/`; see its README. Canonical report SHA256 `f0bd014dc90f1a4f0f0c9597ad8f35cdd140b0b17c89b04906df6e3003266c4c`. The final whole run exited 0 in 1.687s with sampled peak process-group RSS 248,274,944B and no watchdog limit. Reproduce with a fresh ignored path via the tracked `run.sh`; it refuses overwrite. Historical failed/corrected attempts remain separately named and are not counted as final proof.

This is a minimal bridge preflight only. It is not self-acceptance, ClassLoader acceptance, a full JVM, EIP-170 deployment, Minecraft class execution, or Minecraft readiness.
