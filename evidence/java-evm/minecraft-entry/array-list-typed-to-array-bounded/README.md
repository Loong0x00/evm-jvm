# Bounded `ArrayList.toArray(Object[])` candidate (P53)

This worker candidate is based on accepted GuestCode `52cc8e84594698c92d119eca158a094cd27ec2a4`. Before changes, `source-base-verification.json` records exact SHA-256/size verification of all 16 files in the archived `source-base-p53/` snapshot. The snapshot is included so verification does not depend on an untracked worktree input.

## Exact semantic surface

Only existing bootstrap leaf 98 (`java/util/ArrayList`) changes. The new public ordinary method has the erased descriptor `([Ljava/lang/Object;)[Ljava/lang/Object;`. It reads the private `size` field, evaluates `target.length` (so null throws a guest NPE), refuses a target shorter than private size by calling a private unbound native guard before any write, copies the actual `elementData` prefix in order with `aastore`, nulls exactly the first unused element for an oversized array, leaves later tail cells unchanged, and returns the identical target reference. No reflection, replacement allocation, growth, collection mutation, or new native binding is added. The private short-target guard is intentionally unbound.

The bounded admitted ArrayLists have no working mutator, so actual lists remain logically empty. The EVM guest tested target identity; empty/exact/oversized `Object[]`, `Iterable[]`, `Map.Entry[]`, and `String[]`; preserved tail sentinels; target-null and receiver-null NPEs; reflective `Array.newInstance(Object.class,0)`; a misleading `size()` override returning 3 while the actual private size remains 0; and inherited iterator exhaustion/NSEE. The implementation's element-copy and undersized-target branches are real field-based code, but **neither was executed**: nonempty-list copy and undersized-target refusal remain future work requiring a separately admitted mutator/populated list.

Separate fresh EVM packages demonstrated raw refusals for inherited no-arg `toArray`, `add`, `get`, `equals`, `hashCode`, and `clone`, plus replacement of the bootstrap-owned ArrayList raw image. Their exact receipts and atomic root/Head checks are retained in `runs/`. These do not expand this method's implementation scope.

## Pinned artifacts and limits

`pins.json` contains the complete 117-leaf DBOOT root and ordered leaves, exact image hashes, engine deployed-runtime and init hashes, coordinator hashes and all 9 engine / 4 coordinator profile domains. Only leaf 98 differs from the P53 base; the other 116 image commitments are exact. Parser slots, raw-class bound 150, raw-byte bound 1,063,930, global native inventory 22, String-local binding 12, arrays/objects/elements/handles, checkpoint/runtime caps, frame limit, gas reserve, and EVM accounting remain unchanged. The coordinator authenticates the newly built engine runtime code hash. This is LOCAL preinstalled-code execution evidence, not CREATE/EIP-170 compatibility.

## Reproduction

Run sequentially (one compiler/EVM-heavy process at a time):

```sh
./build-candidate.sh
python3 ./pin-candidate.py
python3 ./verify-candidate.py
```

The scripts pin `/usr/lib/jvm/java-8-openjdk/bin/javac` Java 8 (`-source 8 -target 8 -g:none`), `solc 0.8.30`, offline Go (`GOPROXY=off GOSUMDB=off`) and local `NODE_PATH=/home/user/evm-jvm/array-list-to-array/jvmevm/runtime/node_modules`. Host javac is used only to produce generated fixtures/oracle classfiles. The tests consume those raw generated classes through the regular EVM/DI0 path; no host Java class execution or Minecraft inputs are used.

`runs/typed-to-array-final-q1`, `runs/typed-to-array-final-q7-002` and `runs/typed-to-array-final-q128` are independent fresh local EVM sessions. Each was driven through a new-process resume and reopen check. Successful Java outcomes, machine roots and VFS roots agree across quanta; opaque checkpoint roots differ as expected. An initial 30-second q1 finish watchdog expired after 421 committed Java steps; the same preserved session completed after coherently doubling only that finite driver watchdog to 60 seconds. Other budgets and Java/EVM semantics were unchanged. Earlier failed attempts/logs are retained under their original names.

This candidate is not independently reviewed or accepted by the parent and is not a Minecraft execution/readiness claim. HashMap EntrySet/Function/old-tail and other P53 controls remain unchanged by source comparison; no claim is made that this task retests all those controls or reaches nonempty `toArray` behavior.
