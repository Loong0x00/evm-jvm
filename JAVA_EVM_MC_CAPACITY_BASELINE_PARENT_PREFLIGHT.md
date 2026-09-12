# Parent capacity baseline: useful positives, measured ordinary-gas limit

**VERIFIED DISPOSABLE EXPERIMENT, NOT an accepted runtime/profile or universal
feasibility result.** Accepted CB0 remains4 classes/65536B and all accepted EVM/JVM,
core, gas and resource code is unchanged. No original Minecraft Java has executed.

Worker97a926123 integrated5ed777fd5 as an explicitly incomplete draft. Parent added
independent reconstruction and repairs; fixture worker0bb097011 integrated96599b066
provided only generated Java8 fixtures/oracles, not EVM acceptance. Evidence lives
at evidence/java-evm/capacity-baseline/parent-97a926123/ and fixture-completion/.

## Reconstructed narrow prototype

Accepted source7b46769c5, independently byte/hash checked before copying. The only
experimental Solidity changes are raw input count4->8, aggregate65536->262144,
isolated artifact/package/resource/instance domains and corresponding coordinator
arrays/guards/code pins. All38 bootstraps, JVM opcodes/link/exception/heap/fields/
frames/args/VFS semantics, CP4096, Code65535, checkpoint1MiB and DI0 remain unchanged.

Pinned solc0.8.30+commit.73712a01.Emscripten.clang,opt200,viaIR,Cancun,metadataoff.
Fresh independently rebuilt VFS source SHA256
`dedcc9d8c4dbac108391ac4a073e52ec40a63b5517bbd4fe2e29cfb17f74b013`;
experimental runtime292968B, SHA256
`4a7f61989c5ec68edbee96d34cd97c7f0f54f26ffc30d8b351247bd26839f86f`, Keccak
`2beb5ef477d93f1479cdf7dfcb18e37792de9b0643b0ee57e15ba74f9e9d59e6`.
Its isolated LOCAL initial-state address is
`0x4a564d45564d564653304152554e5449ca000001`, not accepted VFS0a identity/CREATE/
standard-chain deployment. AS0/ZI0/DI0/coordinator/pages remain ordinary CREATE.

Coordinator runtime3792B, init7626B, runtime SHA256
`1fc9cc6be252cc9256e280fb2a5669fbdd6a92a03955639d83ddc5173f365363`, Keccak
`b1a044dc0d9a9752d0489031f0e61118ec8778b57d1bebe229af2d7cec71c115`;
combined artifact SHA256
`c0d3dfead16a7658b7deb3712f06c7c16e7cce75070d3d1d82e2aa81260cdc33`.
Actual ABI encoding of8 maximum256B names gives **3680B arguments/full init11306B**.
The draft's4096 was a conservative allowance and3744 was not the actual maximum.
Parent corrected the COPY build/Go guard to the measured3680, not accepted code.

Reconstruction also supplied missing explicit recipe steps for the VFS Go adapter
and embedded assets, preserving their accepted logic. Archived driver files were
renamed .go.txt (bytes unchanged) so disposable imports/duplicate mains do not enter
normal Go package discovery. Original source/patch/raw receipts remain evidence.

## A real draft bug found by parent

The coordinator's instance domain changed, but the COPY Session cached instance ID
using old `MC-CB0/vm/v1`. Setup then immediate same-process Start therefore rejected
its otherwise successful EVM candidate with `engine checkpoint event differs from
slice`: gas4906954, no slice/checkpoint/log/root/revert, published root/epoch unchanged.
A new process succeeds because Open derives instance ID from the EVM Head, masking
the bug in the draft's exclusively reopened paths. Parent reproduced both behaviors
before fixing ONLY the copied derived-cache domain. Same-process disk and memory
now agree with fresh-process Java and have one exact validated engine event.

COPY-only observer hooks read actual EVM call inputs/returns for DI0 fragments;
no private Session/StateDB inspection, input mutation or decoded-class injection.
A COPY-only post-real-trie/code-sync fault hook tests failure publication. These
are not new accepted APIs. Class bytes still travel opaque ZIP -> AS0 -> ZI0 ->
DI0 FINAL -> coordinator EVM reads<=4096 -> real interpreter. Host Java/ZIP/class
parsers appear only in generated TEST construction/oracles, never execution.

## Parent measured matrix

24 worlds,94 distinct process receipts,52 actual checkpoint-file hash checks,
566 actual DI0 read fragments. Setup and Java gas ranges, call timing, returned
fragment lengths/content counts, class binding roots, epochs/quantum/counters,
terminal checkpoint SHA and no reinstall/CREATE on reopen are strictly checked.

| generated package | result | Java/internal | ordinary Java gas |
|---|---:|---:|---:|
| exact4 accepted versus prototype |54|56/9|4906954 both|
| generated5-chain |583|71/11|5589741|
| generated6-chain |707|86/13|6209981|
| generated8-chain |964 (input19=976)|116/17|7563439 direct|
| original draft8-chain |148|116/17|7157937 direct|
| BigCaller+method-rich BigEntry |15|11/2|48451006 direct|
| exact262144 padded boundary |17|9/2|7879725|

BigEntry90874B, CP2565,2552 methods is a genuine method-rich class, NOT padding.
Its useful call uses24 actual fragments for91075B aggregate. q7 completes in2
slices; direct/q7 final machine/VFS/package/resource roots agree. A post-real-sync
failed Resume exposes no success data, retains old epoch/checkpoint/root, and an
ordinary fresh-process retry reaches the same final state. Warm disk and memory
same4-class paths also agree. The8-class q7 chains use17 slices and8 reads each.

Exact65536/65537 and262144 inputs pass in the COPY;262145 rejects aggregate
CB0Error12, with each individual DI0 resource still legal. BoundaryEntry4097 crosses
a4096 read boundary;262144 package uses65 real fragments, not a single huge read.
Accepted old65537 rejects Error12, old BigEntry rejects individual Error11. The
old fifth/new ninth decoder guards refuse BEFORE EVM (gas0) at4/8 slots respectively;
these are not EVM reverts. Padding fixtures are boundary-only, not performance proof.

## Density counterexample prevents a broad feasibility claim

Parent added two generated method-rich classes plus BigPair: **181969B/3 images**,
within the new8/256KiB input limits. A separate Java8 oracle returns23.

- Ordinary direct and q7 fail with exact **LC0ControlError7**, selector0xf15d7343,
  NOT OOG. Direct uses74874471 gas. No Java success checkpoint is published.
- q1 publishes epoch1/one Java step, then its next ordinary Resume also fails the
  reserve guard. A fresh pending-checkpoint read and another ordinary retry retain
  exactly the old head; retry repeats the same refusal/gas. Reducing quantum is
  therefore not a general remedy for this binding.
- Separately preauthorized **1B BOUNDARY ONLY** direct execution uses124505990 gas,
  result23. Boundary Resume of the real surviving q1 checkpoint uses127622437 gas,
  finishes epoch2/result23, with matching final machine/VFS/cumulative counters.
  This is NOT ordinary rescue/acceptance or a global gas-limit change.
- Each call, including refused calls, performs47 actual DI0 fragments totaling
 181969B. Failure return data is never used as a checkpoint.13 distinct recorded
 processes/7 Java calls in this control; terminal and pending bytes are retained.

Do not infer the precise expensive function from aggregate gas or a failed trace.
The contrast between cheap256KiB padding and costly method-rich181KiB motivates
actual EVM cost attribution of preparation/reference selection/continuation before
choosing caching, bounded preparation or demand loading. No such change is included.

## Final gate and remaining scope

Fresh reconstruction-through-regression gate **264.469s/865628160B sampled peak
process-group RSS, exit0**, within20min/4GiB. Includes fresh compiler/pins, original
warm-cache failure then repair,12 independently regenerated/oracle-verified fixture
sets,24-world matrix, density ordinary refusals+explicit1B measurements, strict
verifiers, Go vet and full accepted CB0 regression33.680s. Protected core/params/
jvmevm/Make diff versus7b46769c5 empty. No skipped failed capture or stub acceptance.

No production capacity promotion follows. In addition to measured preparation
costs, original-JAR launch needs explicit origin handling: current CB0 binds all
classes to one index/archive, while a separate generated launcher is absent from
the exact official JAR. Do not repack/insert it and still claim the original hash,
or bypass DI0 with host class bytes. Compare an origin-preserving fixed multi-archive
package against a separately specified main-root facility before implementation.

No original Minecraft Java/main, EULA, listener, world, genuine Done, or public push.
