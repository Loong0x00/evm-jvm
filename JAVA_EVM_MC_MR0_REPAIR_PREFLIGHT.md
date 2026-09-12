# MR0 direct-main repair preflight

Status: **COPY-only repair preflight; unaccepted.** This is a new copied MR0
engine/coordinator/normal-owned transport under
`evidence/java-evm/main-root/repair-preflight/`. No accepted `jvmevm`, core ABI,
quota, artifact, or original MR0 candidate was edited. It handles generated Java
8 fixtures only; it did not handle an original JAR or execute Minecraft/EULA/
listener/world/Done.

## Preserved original failures

Before changing the copied Solidity, a fresh normal `StateDB`/LevelDB replay of
the immutable original engine was made in the worker-owned ignored output. The
raw replay is retained in `raw-original/replay/` (with the prior transport raw
receipts retained alongside it):

* `MainPositive` contains valid `main()` and the valid exact
  `main(String[])`; its actual opaque ZIP -> AS0 -> ZI0 -> DI0 -> coordinator
  call read 566 and 286 bytes then reverted `MethodError(2)`, selector
  `0x166ac6c3`, word `2`, 558386 gas, with no root change.
* Legal `MainRebind` saves the supplied array and writes `args=null`. At q1 it
  reached epoch 3 and the next real `resumeMain` reverted
  `LC0StateError(7,0)`, selector `0x71540d20`, 5146253 gas, with no root change;
  q7 instead reached VOID at epoch 1. These are execution observations, not
  source-only suspicions.

The old wrapper containing `rm -rf` was not run. `reproduce.sh` is a new
output-refusal wrapper: it accepts only a fresh ignored
`build/java-diff-mc-main-root-repair-*` path and refuses it if it already exists.

## Exact repair delta

The copied engine makes exactly two behavioral changes:

1. `_prepare` filters root candidates by both `main` and the exact descriptor
   `([Ljava/lang/String;)V` before duplicate/access/native/abstract/synchronized/
   Code checks. A missing exact descriptor remains `MethodError(1)`; duplicate
   exact candidates remain `MethodError(2)`. It does not choose `()V`, `(I)V`, or
   a reference-return overload.
2. `_freshState` validates the canonical non-null rank-one, String-leaf,
   zero-length array immediately after `_installEmptyMainStringArray`, before
   Java executes. `_validateInitAndFrames` no longer treats current root-frame
   local 0 as an immutable input. The ordinary serialized heap/reference/root,
   config/commitment/owner/package/anchor and opaque-checkpoint/CAS checks are
   otherwise retained; resume consumes the successful EVM-issued checkpoint and
   never recreates an argument array.

The coordinator has only its required fixed `ENGINE_CODEHASH` pin changed to the
fresh copied engine; its ABI and all AS0/ZI0/DI0 bindings are unchanged.
`original-candidate/` preserves a complete original copy for the scoped diff.

## Fresh pins and measured output

Build used `solc 0.8.30+commit.73712a01.Emscripten.clang`, optimizer 200,
viaIR, Cancun and metadata off. The new engine is 294795 runtime bytes (below
the disposable 320 KiB cap), SHA-256
`5cd308971f49e815ee8adf864133c05f44e675ae6efe6cabe771bd89ad8fb875`,
Keccak `2c841e15e382f6433adfbce3fddc225a5efeed5d0d87727c1eac4a0106f9d79f`;
init is 294823 bytes and is installed only at the isolated LOCAL engine route,
not by ordinary CREATE. The ABI-identical coordinator runtime is 3547 bytes,
Keccak `06f642301333b90429e749951c7855cf954a379848d4643ef758f7853ff39a8c`;
its init is 7381 bytes. Pins, source, compiler scripts and sums are tracked in
the evidence directory.

A fresh eight-world generated group was run using normal public EVM calls,
normal owned LevelDB/trie persistence, and ordinary CREATE for AS0/ZI0/each
DI0/coordinator. Class bytes entered only as an opaque generated ZIP; ZI0/DI0
performed the index/inflate/CRC/FINAL reads and coordinator observed every read
at <=4096 bytes. The only direct code installation was the new exact engine at
`0x4d52304d41494e454e47494e4500000000000001`. Complete JSON receipts,
terminal checkpoint blobs, roots, actual gas/counters and process IDs are in
`results/`; `RESULTS.sha256` covers the retained raw replay and result files.

| generated guest | q1 terminal | q7 terminal | equal guest outcome |
|---|---:|---:|---|
| overloaded `MainPositive` + helper | VOID, 319 epochs/steps, 3 internal | VOID, 46 epochs, 319 steps, 3 internal | yes; reserved `result=0` |
| `args=null` rebind | VOID, 7 epochs/steps, 2 internal | VOID, 1 epoch, 7 steps, 2 internal | yes |
| `args=new String[1]` rebind | VOID, 24 epochs/steps, 2 internal | VOID, 4 epochs, 24 steps, 2 internal | yes |
| uncaught `RuntimeException` | outcome/lifecycle 3, 19 epochs, 18 JVM/5 internal | outcome/lifecycle 3, 3 epochs, 18 JVM/5 internal | yes; kind 0, dynamic `java/lang/RuntimeException` |

Each terminal world was reopened in a third process and cross-checked against
engine head, checkpoint root/hash, coordinator package and code pins. Positive
q1/q7 aggregate gas was 1915121389/302356921 across slices; every individual
public call stayed <=100M and the driver records no 1B route. These aggregate
costs are evidence only, not a quota change. The q1 positive run is intentionally
many real ordinary slices, so its differing checkpoint/root history is not
claimed as byte-identical to q7.

## Reproduction and strict validation

Set `NODE_PATH` explicitly to a local pinned dependency tree containing solc
0.8.30 and js-sha3, then run:

```sh
TMPDIR=build/java-diff-mc-main-root-repair-tmp \
NODE_PATH=/path/to/node_modules \
sh evidence/java-evm/main-root/repair-preflight/reproduce.sh \
  build/java-diff-mc-main-root-repair-fresh
```

The wrapper scopes `TMPDIR`, has a 20-minute cumulative command watchdog, and
runs the strict verifier on the newly produced output. The declared 4 GiB bound
is recorded by the wrapper but this worker did not independently sample a
kernel-enforced RSS ceiling; parent must treat that as remaining acceptance work.
`strict_verify.py` refuses archived evidence as an input and checks freshly
built compiler/source/runtime pins, terminal checkpoint SHA/cap, actual
pipeline/read/create counters, new-process reopen records, non-refusal, typed
exception class, reserved-zero result and q1/q7 guest equivalence. It was run
against `build/java-diff-mc-main-root-repair-final` and emitted
`results/strict-verify-final.json`.

This remains a generated, bounded MR0 candidate. It is not accepted, an
accepted-profile change, standard CREATE deployment claim for the oversized
engine, a Selected-table optimization merge, or evidence for original Java or
Minecraft execution. Parent independent rebuild/replay remains required.
