# Selected-table COPY: independent parent preflight

**Verified disposable allocation experiment, not accepted-profile promotion.**
Worker f92946751/3c68ec0f2/b55892680 integrated as0c92aad0e/cd81899e5/b4338dda5.
Parent rebuilt from pinned7b46769c5 accepted source plus archived capacity/Selected
patches, found and repaired two COPY issues, and ran a fresh full gate. Accepted
CB0 remains4 images/65536 aggregate;8/262144 remains an isolated experiment.
No MR0 merge, original JAR/class input, original Java instruction, EULA, listener,
world or Minecraft Done. No push. Protected jvmevm/core/params/consensus/eth/Make
source diff againstba28a4ad6 is empty.

## Parent findings and narrow corrections

1. Worker moved `_predecode` before original argument-count/max-locals checks.
   Generated OrderProbe has run(int,int) but receives one public int argument.
   With valid code both profiles return MethodError9; with deliberately malformed
   opcode0xff the accepted baseline still returns9 (409727 gas) but candidate
   returns BytecodeError(6,0), selector62d5596d (410648 gas). Actual EVM receipts,
   opaque ZIP fixture, roots and reproducer retained. Frozen root-order repair
   restores original precedence; no accepted-code edit or invalid-code acceptance.
2. Even with lazy table slots, emitted `fun_selectedAt` begins
   `pop(allocate_and_zero_memory_struct_struct_Selected())`. Read-only opcode/
   memory observation and optimized IR show a **discarded736-byte allocation on
   every helper read**, not merely allocations for loaded methods. The intermediate
   parent had15/20/35 Selected allocations for padded/big/dense respectively and
   made the214-Java-step alias case more expensive than baseline. Parent removes
   only this pure helper and substitutes its identical typed indexed read at11
   call sites. No assembly, shared Selected sentinel, fallback, parsed-class cache,
   new instruction, ABI, capacity, reserve or checkpoint-codec change.

`Selected[][][]` keeps original class/method indexes; an unloaded slot is an empty
array, a loaded slot owns a singleton Selected array. Loaded guards and validation
precede reads. `_putSelection` does not share mutable handler caches between methods.
The compiler still allocates a singleton placeholder plus actual loaded descriptor;
we report measured allocation counts, not the false claim of one object per method.

## Final independent evidence

Whole **fresh source rebuild + all replay gates + accepted CB0 regression**:
**331.597450s, sampled peak process-group RSS874287104B**, exit0;20min/4GiB limits.
Ordinary100M/30s calls only. No automatic1B rescue in parent density reproducer.
Compiler0.8.30+commit.73712a01, optimizer200, viaIR, Cancun, metadataoff,38 bootstraps.

* Original24-world matrix independently rerun:94 process receipts,52 checkpoint
  files,566 actual DI0 fragments, warm/memory/disk/terminal,4/5/6/8 images,65536/
  65537/262144 positives, old/new overlimits and actual publication-failure/retry.
* Dedicated3247B/4-class alias fixture: **524 distinct processes,504 Java calls**.
  Results525/561,214 Java/16 internal; direct/q7/q1 =1/31/214 slices.32 unused
  methods, distinct loaded signatures/long arguments, root/parent/child clinit,
  constructors, superclass/private special, virtual/interface/default dispatch,
  repeated separate ArithmeticException/NPE/RuntimeException handler caches,
  caught athrow, String.equals native and uncaught dynamic RuntimeException.
  Uncaught mode99 is lifecycle3, kind0, nonzero ref, exact runtime class name—not
  an indiscriminate kind0 success. Every same-quantum baseline/new opaque machine
  payload after280-byte envelope compares byte-for-byte, including pending epochs.
  Guest results/counters/VFS agree; same-profile terminal machine roots agree.
  Final alias direct gas15261705 vs baseline15436349; the intermediate regression
 16383517 remains archived rather than erased.
* Dense181969B/3-image package now completes at **63485032 ordinary gas**, genuine
  int23/20 Java steps; q7=3 and q1=20 successful slices,47 actual<=4096B reads each.
  Same-profile final machine/VFS roots agree. Exact terminal opaque payload equals
  the prior successful explicitly1B-boundary capacity reference; unlike-code
  package/config/instance/envelope roots are NOT required to match or weakened.
* Public Resume wrong epoch/root/opaque checkpoint/package produces exact EVM
  LC0ControlError3/4/4 and CB0Error18, respectively; gas721135/721195/721936/4903.
  No receipt/CP/log/root leakage. Prior checkpoint bytes remain intact and normal
  retry reaches genuine15/11 Java steps. Publication failure remains gas-only,
  not synthetic revert data (matrix test).
* Read-only allocator entry/free-pointer observations and normal fresh replay
  have identical gas/budget/quantum/Head/receipt/roots/slices/checkpoint SHA/bytes.
  Each736B allocation histogram matches the compiler Selected allocator entry
  count. EVM expansion exactly reconciles C(w)=3w+floor(w²/512). This is scratch
  EVM memory, not guest heap, process RSS or host Java execution.

|Case|Old gas|New gas|Old→new Selected allocations|Old→new peak EVM bytes|Old→new expansion gas|
|---|---:|---:|---:|---:|---:|
|Padded262144|7879725|7875964|6→4|863648→862400|1503635→1499409|
|BigEntry|48451006|31412686|2557→6|3137568→1260320|19070722→3147799|
|Dense3|124505990 (1B boundary)|63485032|5111→10|5957824→2203904|68261157→9470976|

Loaded-slot writes are2/3/5, respectively. Actual results17/15/23 and opaque terminal
payloads match prior references. No universal speedup theorem, Java SE completeness,
demand loading or readiness for original Minecraft follows from these fixtures.

## Pins and reproduction

Final engine runtime291802B, SHA256
`9369af312aae789eb9a778ba4458a639e7f7a9ccbab461c127f7f06b4caa8702`, Keccak
`2d32ae8ad244ddf5fa475324bfe310182ca6603215c8d3c4ff641bca22041309`.
Source SHA256`d451384f82a7c85ed7a6fb3cc579f7074cd98bca49cb7aa8e144a851976e3eb8`.
Coordinator3792B/init7626B, Keccak
`9a2b3b7a4e18722cc6e99f9de02e9b5f38057241dc2485d9427d16bbe3ddc767`.
8 maximal names still3680 constructor args/full11306. LOCAL engine address stays
`0x4a564d45564d564653304152554e5449ca000001` with exact new code; separately labeled
initial state, not CREATE/standard chain. All controllers/resources/pages ordinary
CREATE. DomainMC-SELECTED-TABLE-PREFLIGHT, exact new engine/coordinator pins bound.

Evidence: `evidence/java-evm/selected-table/parent-b55892680/`. `run.py` refuses
existing output, reconstructs fresh isolated source and drivers, runs all gates;
wrap it using canonical evidence watchdog. `rebuild.py --root-order --direct-read`
is final; omitting direct-read reproduces the measured discarded-allocation
intermediate, omitting both reproduces original candidate. `probe_order.py`
retains and distinguishes original refusal precedence. Archives contain source,
compiler products/IR/debug entries, actual drivers, generated fixtures, raw errors,
receipts and opaque checkpoints; LevelDB may be reconstructed, not used as hidden
execution authority. TMPDIR scoped to ignored builds. Original failures remain.

Next dependency: parent-independent MR0 repaired-main transport/kernel review and
replay. MR0 workera2efa63fa remains unaccepted; combine neither experiment into the
accepted profile without its own scoped pins, persistence and entry gates.
