# MC capacity baseline disposable preflight

**Original worker draft at base `7b46769c5`, preserved below.** Parent completed a
verified DISPOSABLE experiment with repairs AND an ordinary-gas density counterexample:
JAVA_EVM_MC_CAPACITY_BASELINE_PARENT_PREFLIGHT.md. Not an accepted profile promotion.

This records the narrowly authorized COPY-only experiment described in
`JAVA_EVM_MC_CAPACITY_COMPARISON_PREPARATION.md`. Its only experimental input
change is fixed generated raw images 4->8 and aggregate bytes 65536->262144,
with directly corresponding coordinator/profile metadata. Accepted CB0, VFS0a,
AS0, ZI0, DI0, core, ABI, artifacts, quotas and source remain untouched.

## Isolated reconstruction

The experiment was built only in ignored
`build/java-diff-mc-capacity-proto-smoke/` from exact accepted source:

* VFS copy changed `MAX_RAW_CLASSES` 4->8 and `MAX_RAW_BYTES` 65536->262144,
  plus isolated artifact domain.
* CB0 copy changed its fixed four-element binding storage/count guards,
  corresponding per-resource/aggregate limits and isolated package/resource/vm
  domains. It pins only the newly compiled experimental VFS copy.
* The experimental engine is a labelled LOCAL initial-state code installation at
  `0x4A564D45564D564653304152554e5449ca000001`; it is not accepted VFS0a,
  CREATE deployment, standard-chain evidence or a production route. AS0/ZI0/
  DI0/coordinator are ordinary CREATE.
* EVM Java inputs still traverse AS0 -> ZI0 -> DI0 FINAL and coordinator
  `_loadAll` retains actual <=4096-byte DI0 reads. No host class, ZIP, inflater,
  catalogue or evaluator exists on the execution path.

The compact patches, generated-only fixture sources, compiler receipts, public
transport drivers, terminal receipts and hashes are durable under
`evidence/java-evm/capacity-baseline/preflight/`. They are intentionally a
recipe/patch rather than an unexplained production-sized copy.

## Measured early results

All reported calls use the ordinary 100M cap:

| generated input | outcome | Java/internal | gas |
|---|---:|---:|---:|
| accepted CB0 four-class static chain | 54 | 56/9 | 4,906,954 |
| same four classes, isolated copy | 54 | 56/9 | 4,906,954 |
| eight-class transitive static chain | 148 | 116/17 | 7,157,937 direct |
| eight-class q7 terminal | 148 | 116/17 | 17 slices; max terminal 4,918,461 |
| BigCaller -> BigEntry(90,874B, CP2565, 2552 methods) -> m2549 | 15 | 11/2 | 48,451,006 |

The four-class comparison deliberately has different isolated package/machine
roots, but same result/counters/gas. For the eight-class direct/q7 pair, final
machine, VFS, package, AS0, index and decoder roots are equal. New-process
terminal reopens retain the exact checkpoint hashes and report no reinstall.

## Current limits of the draft

This is useful construction/positive evidence only. It lacks the required
5/6-class runs, 8-vs-9 and exact aggregate/+1 refusal receipts, strict DI0
fragment tracing and full raw-error decoder assertions, and a completed 20min/
4GiB group watchdog gate. It therefore does **not** establish that eager
capacity is feasible, that demand loading is unnecessary, or that either design
is Minecraft-ready. No 1B rescue call was made.

There was no official JAR/class handling or execution, Minecraft/EULA/listener/
world/Done action, push, or change outside this file and the evidence directory.
