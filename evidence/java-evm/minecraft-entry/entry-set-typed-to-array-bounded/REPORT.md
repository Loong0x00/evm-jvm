# Bounded `Collection.toArray(T[])` / HashMap EntrySet candidate

Status: **candidate only; parent independent review/rebuild/gates pending.** This task read and verified only the 12-file P47 source-only manifest plus ordinary local Go runtime sources. Its exact 12-file P47 source-only snapshot is preserved under `source-basis/` for independent reproduction. It did not open any original Minecraft JAR/class/resource/world/receipt, parent review, performance review, other worktree, or network source.

## Source and image changes

The verified base is commit `1631a3201672da593f82c7bb4008b93de14ebd6d`, bootstrap root `f17b95bad49e93149b028bcc14c1df26926ec7916494d3faf1b787d590457ee2`. Before editing, the supplied minimal `Collection.java` compiled with Java 8 `-g:none` to leaf 53's accepted Keccak `2678bac4...`; the supplied `Map.java` compiled separately and its `Map.class` / nested `Map$Entry.class` match accepted leaves 40 and 94. `HashMap.java` was first compiled against stock JDK 8 (successful); its unsupported override declarations are thus not judged against the minimal Map interface.

The only changed bootstrap images are:

| Leaf | Image | Base Keccak | Candidate Keccak | Bytes |
|---:|---|---|---|---:|
| 53 | `java/util/Collection` | `2678bac4e6565a8811acff77acfe0cdb01159742c92990e59d2554bbe6157701` | `abb24b1c624154293e389f78a4ca372a92a25e3a93d7bc78fa9eb0385b296120` | 472 |
| 110 | `java/util/HashMap$EntrySet` | `7c958cceb7026a9a82536ace0e0c0ab99692be903a69ee7a764a24e4ec0d0575` | `81693417e6e192c9b88c2f3b800e59fe945f47264cb2cdbec08fbc98ab007166` | 1,856 |

Candidate bootstrap count/order remains 113; candidate root is `becacc3754a4006b0add9bfd79c9cb68fc966508b1c23701184a6105ad360c02`. `HashMap` leaf 100 is byte-exact; `HashMap$Node` leaf 104 is byte-exact. `Map` leaf 40 and `Map$Entry` leaf 94 are also unchanged. The exact all-leaf comparison is in `pins.json` and can be rerun with `verify.py`.

The interface now declares only the measured generic `<T> T[] toArray(T[])` method. The ordinary EntrySet body checks `target.length`, obtains the live view's size, invokes its existing iterator, stores its actual Entry references in iteration order, nulls exactly the first unused slot when oversized, and returns the same target. It invokes a new **unbound private native refusal guard before any writes** when the supplied array is shorter than the view. It has no empty-map shortcut and adds no allocation, reflection, copy, stream, native binding, ABI/storage/codec/quota, or other bootstrap behavior. The existing no-arg native `toArray()`, add, equals and other guards remain unbound.

## Verification

- P47 source manifest: all 12 declared files and byte/hash pins verified.
- Java 8 builds used `/usr/lib/jvm/java-8-openjdk/bin/javac`, `-g:none -source 8 -target 8`. `HashMap.java` stock-JDK compile passed first; minimal Collection and Map were compiled separately; candidate source builds and generated guest fixtures passed.
- `javap` confirms an abstract generic declaration in `Collection`, ordinary `EntrySet.toArray(T[])` bytecode with the refusal call before the loop, and generated test bytecode invoking `Collection.toArray(Object[])` through `invokeinterface`.
- Stock Java 8 host oracle for the generated positive fixture passed. This host run is test-only and was not an execution input to EVM.
- Fresh geth EVM `runtime.Call` gates used the candidate runtime as explicitly preinstalled local code, never CREATE. Generated positive `main` completed under q1, q7, and q65536. Each run had lifecycle/outcome 2, 3,862 guest Java steps and 7 internal steps. Machine root `18688116cf5b5ff8285aca15698c0eed1eb4e890814168aa226796c97cfc9a41` and VFS root `3a60e6910a09a982ef14fa7a04196953c1fa5f7e28a54344e930967401fb788d` agree across quanta. The test verifies empty size-zero reuse, the interface call, exact and oversized arrays, null terminator/tail preservation, null key/value, insertion/live view, collision entries, iterator order/reference identity, Entry.setValue aliasing, caught null-array NPE and caught incompatible-array ASE.
- A shorter-than-size array and existing add/equals/no-arg toArray paths all refused through raw EVM reverts with selector `d631c3a4`; pre/post StateDB roots matched for each. These were not guest Java exceptions. Reflection remains unmodified and was not separately invoked.
- Exact gate receipts and reproduction logs are under `build/generated-evm-gates-v3.json` and `build/logs/`.

The run called the EVM directly with a fresh in-memory `StateDB`; this verifies neither the coordinator/DI0 package path nor durable cross-process reopen. Those gates remain honestly unverified because the worker's permitted source-only manifest did not include those package runtimes/artifacts. The candidate coordinator was rebuilt with the candidate engine codehash and candidate package domains; its ABI and storage layout match P47. No Minecraft/original Java run occurred, no accepted-profile claim is made, and no push was performed.

## Reproduction

From the repository root, with the pinned offline dependencies available:

```sh
/usr/lib/jvm/java-8-openjdk/bin/javac -g:none -source 8 -target 8 -d build/typed-copy-classes evidence/java-evm/minecraft-entry/entry-set-typed-to-array-bounded/source/bootstrap/java/util/HashMap.java
# The preceding HashMap compile is specifically against stock JDK 8.
/usr/lib/jvm/java-8-openjdk/bin/javac -g:none -source 8 -target 8 -d build/typed-copy-collection evidence/java-evm/minecraft-entry/entry-set-typed-to-array-bounded/source/bootstrap/java/util/Collection.java
/usr/lib/jvm/java-8-openjdk/bin/javac -g:none -source 8 -target 8 -d build/typed-copy-map evidence/java-evm/minecraft-entry/entry-set-typed-to-array-bounded/source/bootstrap/java/util/Map.java
NODE_PATH=/home/user/evm-jvm/entry-set-to-array/jvmevm/runtime/node_modules node evidence/java-evm/minecraft-entry/entry-set-typed-to-array-bounded/engine/build.js
NODE_PATH=/home/user/evm-jvm/entry-set-to-array/jvmevm/runtime/node_modules node evidence/java-evm/minecraft-entry/entry-set-typed-to-array-bounded/coordinator/build.js
NODE_PATH=/home/user/evm-jvm/entry-set-to-array/jvmevm/runtime/node_modules python3 evidence/java-evm/minecraft-entry/entry-set-typed-to-array-bounded/verify.py
```

The checked-in `build/` tree preserves this run's compiler logs, fixture classes and gate output. For another full EVM replay use `GOPROXY=off GOSUMDB=off go run ./evidence/java-evm/minecraft-entry/entry-set-typed-to-array-bounded/driver <candidate-engine-json> <compiled-fixture-class-dir> generated <new-output-path>`; use a new output path so earlier evidence remains intact. Each EVM call was capped at 1,000,000,000 gas; the outer test timeout was 1,200 seconds. No measured per-call gas-budget shortage was encountered.
