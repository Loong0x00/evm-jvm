# P47 parent-corrected bounded HashMap.entrySet

The historical worker candidate below was **not accepted as written**. Parent preserved and corrected an unsupported add(Object) casting bridge, then a full original replay exposed the missing Map.entrySet interface declaration. Both failed versions/worlds remain preserved; no checkpoint crossed code/package boundaries.

Current independently rebuilt113-image root is `f17b95bad49e93149b028bcc14c1df26926ec7916494d3faf1b787d590457ee2`, engine429415B SHA256 `db0b3a5ed75c268a3d52d4b9b0c21766f1bba186a5d6d8ce3ece0ea9e0297e22`. Changed prior leaves40(Map declaration) and100(HashMap); Node104 and all other108 prior leaves unchanged. New helpers110/111/112. Current pins/artifacts are parent-corrected; old worker EVM receipts below concern only the original candidate, not this code. See `../parent-hash-map-entry-set/` and root `JAVA_EVM_MC_HASH_MAP_ENTRY_SET_PARENT_PREFLIGHT.md` for independent fresh EVM/reopen/original acceptance.

---

## Historical unaccepted worker report (retained verbatim)

# Bounded `HashMap.entrySet` candidate (P47)

This is an **unaccepted source candidate** based only on the manifest-verified, owned P46 source-only snapshot at `../hash-map-entry-set-source-base-p46`. The 10 declared manifest entries were checked byte-for-byte before copying or editing. No Minecraft/original-input/parent review evidence was read. No bindings, EVM ABI, storage layout, checkpoint codec, quota, or interpreter semantics were changed.

## Guest capability

* `HashMap.entrySet()` now lazily caches and returns a live `EntrySet` backed by that map. `size()` and `isEmpty()` read the map's real size; repeated calls return the same view.
* `EntryIterator` scans the actual `Node[]` table and linked bins, returns the existing `Node` objects as `Map.Entry`, and uses JDK 8 `HashIterator.next()` ordering: check `modCount` first, then raise `NoSuchElementException` on exhaustion. `hasNext()` does not fail fast. A structural `put` invalidates an iterator; replacing an existing value and `Map.Entry.setValue` do not. Entries therefore preserve node/value aliasing.
* The existing `HashMap$Node.class` image is byte-exact. Only the `HashMap` image changes among the original 110 leaves. Three actual Java 8 `-g:none` images append at leaves 110–112: `HashMap$EntrySet`, `HashMap$EntryIterator`, and a minimal, genuine `ConcurrentModificationException` (ordinary `RuntimeException` subclass with a no-arg constructor). The maximum remains 150 raw classes; bindings remain 21 global / 12 String-local.
* The view explicitly overrides unsupported mutation, query, equality/hash, array, callback, and stream surfaces as unbound native refusal points. It does not inherit identity `Object.equals`/`hashCode` or implement `remove`, `clear`, `contains`, `toArray`, etc. Existing HashMap `get`, defaults, `keySet`, `values`, and other unimplemented operations remain refusal points. Existing `put`, spread/resize, and treeification refusal code are unchanged.

## Reproduction and checks

From `/home/user/evm-jvm/hash-map-entry-set`:

```sh
cd /home/user/evm-jvm/hash-map-entry-set/evidence/java-evm/minecraft-entry/hash-map-entry-set-bounded
/usr/lib/jvm/java-8-openjdk/bin/javac -g:none -source 8 -target 8 -d builds/java8-p2 bootstrap/java/util/HashMap.java bootstrap/java/util/ConcurrentModificationException.java
/usr/lib/jvm/java-8-openjdk/bin/javac -g:none -source 8 -target 8 -d builds/fixture-classes fixtures/EntrySetProbe.java
/usr/lib/jvm/java-8-openjdk/bin/javac -g:none -source 8 -target 8 -d builds/negative-classes fixtures/EntrySetUnsupportedProbe.java
python3 materialize-java8-images.py
cp builds/java8-p2/java/util/HashMap.class builds/fixture-classes/
cp builds/negative-classes/EntrySetUnsupportedProbe.class builds/fixture-classes/
NODE_PATH=/home/user/evm-jvm/hash-map-entry-set/jvmevm/runtime/node_modules node engine/build.js
NODE_PATH=/home/user/evm-jvm/hash-map-entry-set/jvmevm/runtime/node_modules node coordinator/build.js
go run /home/user/evm-jvm/hash-map-entry-set/evidence/java-evm/minecraft-entry/hash-map-entry-set-bounded/entryset-evm-gate.go /home/user/evm-jvm/hash-map-entry-set/evidence/java-evm/minecraft-entry/hash-map-entry-set-bounded/engine/MCEntryInterpreter.json /home/user/evm-jvm/hash-map-entry-set/evidence/java-evm/minecraft-entry/hash-map-entry-set-bounded/builds/fixture-classes /home/user/evm-jvm/hash-map-entry-set/evidence/java-evm/minecraft-entry/hash-map-entry-set-bounded/results/direct-q1-q7-reproduced.json
go run /home/user/evm-jvm/hash-map-entry-set/evidence/java-evm/minecraft-entry/hash-map-entry-set-bounded/entryset-negative-evm.go /home/user/evm-jvm/hash-map-entry-set/evidence/java-evm/minecraft-entry/hash-map-entry-set-bounded/engine/MCEntryInterpreter.json /home/user/evm-jvm/hash-map-entry-set/evidence/java-evm/minecraft-entry/hash-map-entry-set-bounded/builds/fixture-classes /home/user/evm-jvm/hash-map-entry-set/evidence/java-evm/minecraft-entry/hash-map-entry-set-bounded/results/negative-evm-reproduced.json
```

The Solidity class materializers embed the generated helper byte images; `root_helper.py` recomputes every ordered leaf from those materializers. The final 113-leaf root is `c9ddc8ee198293fc87a08490042672caca58de15c181df5b09744425ff8fd7e9`. A full ordered comparison against the source-only P46 root confirms the sole changed inherited leaf is HashMap index 100; Node remains byte-exact and the three helpers are appended. Engine runtime is 429,809 bytes (LOCAL artifact, not standard CREATE/EIP-170 compatible). Engine/coordinator ABI and storage layout compare equal to P46; coordinator's engine codehash pin and all four coordinator domains were updated explicitly.

The generated-only `EntrySetProbe` was run in the real geth EVM against the fresh engine artifact using direct `startMain`/`resumeMain` calls and independently initialized state for q1 and q7. Both reached normal guest completion after 8,707 Java / 10 internal steps and agreed on machine root `0x94a9745636ffec5599296e72c29993073efcf66abed0bf2e992e793d3872ccf8`, VFS root `0x3a60e6910a09a982ef14fa7a04196953c1fa5f7e28a54344e930967401fb788d`, counters, and outcome. This test covers an initially empty cached view and its empty-to-populated transition (including null key/value), a genuine collision chain, resize, iteration over real entries, `setValue` and replacement aliasing, exhaustion NSEE, structural fail-fast CME, and legal nonstructural iteration. Evidence is `results/direct-q1-q7-p2.json` and `results/direct-q1-q7-p2.log`; earlier immutable attempts remain in `results/direct-q1-q7-attempt*.log`.

A second fresh-artifact EVM check confirms `EntrySet.equals` yields exact `CallError(4,15)` rather than identity semantics, and raw HashMap replacement yields `BootstrapProfileError(1,1)`. Both refusals leave the instance head at epoch zero. Evidence: `results/negative-evm-p3.json` and `results/negative-evm-p3.log`; prior failed runner attempts are preserved.

## Limitations / handoff

This is not parent acceptance. The worker performed direct engine-artifact EVM runs, not a coordinator/AS0/ZI0 package deployment or a separate-process durable-state reopen. The Go runner uses a 1,000,000,000 gas limit per EVM call; its whole q1/q7 run took 682.625 seconds. Per-call wall time was not independently instrumented against a 30-second watchdog. The source and EVM cases are generated-only; no original Java/Minecraft artifact was accessed or executed. The unsuccessful runs and the discovered/repair of helper-leaf placement are preserved in the `results` logs. Parent should independently rebuild and review semantics, exact error/refusal precedence, all inherited Set surface, and persistence before any acceptance claim.
