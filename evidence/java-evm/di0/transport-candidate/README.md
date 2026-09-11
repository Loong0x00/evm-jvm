# MC-DI0 Go transport candidate evidence

Status: transport worker evidence only; **not DI0 acceptance**.

The implementation starts from `b67ed0865e02be19764d8a577912a06e8b90bb03` and is
committed as `89de316b9`. Tests used the real runtime artifact committed by the
separate sole runtime writer at `fbe0f2381`; `04b4f8157` subsequently added that
worker's runtime verification without changing the artifact files.

Because the two production write sets were intentionally disjoint, the runtime
files were not copied into this worktree. The ignored test overlay was reconstructed
only from committed objects:

```sh
mkdir -p build/java-diff-mc-di0-harness-runtime-fbe0f2381/runtime/combinedartifacts
for f in assets.go combinedartifacts/DI0Resource.json; do
  git -C /home/user/evm-jvm/mc-di0-runtime show \
    fbe0f2381:jvmevm/artifactstore/di0/runtime/$f \
    > build/java-diff-mc-di0-harness-runtime-fbe0f2381/runtime/$f
done
```

`report.json` records commands, elapsed times, the combined child-process maximum
RSS sample, fixed budgets, artifact/code/source/ABI/layout hashes, and code sizes.
Logs preserve the final focused suite, vet, and accepted AS0/ZI0 regression output.
The focused package has 15 tests (plus two lifecycle subtests), including:

- exact 33-function ABI and independently pinned combined artifact;
- ordinary AS0/index/decoder CREATE routing and opaque input/index/output views;
- method 0 and raw-DEFLATE positive output, CRC negative selector, CAS selectors;
- requested q128 positive 64/129-empty-dynamic-header runs and one complete q1..128
  same-binding 64-header state-equality sweep;
- first-action 70,000-gas OOG rollback and successful retry;
- disk reopen at mid-upload, discovered index, dynamic-table decode, VERIFIED,
  mid-publication, and FINAL, with no reopen CREATE;
- actual post-trie/code-sync prepublication restore and same-child decoder CREATE
  retry, post-rename poisoning, namespace/metadata/symlink refusal, copied views,
  and serialized stale concurrent calls;
- final EVM-issued output page code/hash/commitment/length and full-byte reads.

The fixtures are generated tiny trusted ZIP/raw streams. `compress/flate` and CRC32
appear only in `_test.go` as fixture/oracle code. Production Go has no ZIP parser,
Inflater, Huffman/CRC evaluator, output installer, `SetCode`, or offset catalogue.
No official artifact, Java execution, ClassLoader, Minecraft, EULA, listener, or
Done marker was used.

## Gates deliberately still owned by the parent

This evidence is not the independent sixteen-group acceptance gate. In particular,
the parent still must integrate the runtime and transport commits, rerun the frozen
five complete q1..128 sweeps/six same-binding pairs and full malformed-tree matrix,
size 90309/158794/262144 boundaries, 32KiB overlap, late output-page CREATE OOG
same-child retry, all publication fault points, relocated embedded build, whole-gate
20-minute/4-GiB watchdog, and protected core/VFS/stock regressions. No acceptance or
Minecraft-readiness claim is made here.
