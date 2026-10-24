# Bounded `ArrayList.add(Object)` implementation record

Status: **implementation candidate; not accepted**. This report covers only `java/util/ArrayList.add(Object):boolean` and fail-fast consistency in its existing iterator. Independent parent build/gating, a successful q1 replay, direct/q1/q7 equivalence, original143, and measured OOM/unsupported-path gates remain outstanding.

## Scope and provenance

- Worktree base: `2b0c5c61a07f2c40030b0168a04efc28d0a10043`; accepted guest base: `605113f812953d6d69af9cefc16336450e029bd6`.
- Approved source-only baseline: `../array-list-add-source-base-p59/`; its 16-file manifest was checked byte-for-byte and by SHA-256 before editing.
- Recompiled both baseline class images first with `/usr/lib/jvm/java-8-openjdk/bin/javac 1.8.0_504 -g:none -source 8 -target 8` and the manifest's minimal seven-Java-source context:
  - `ArrayList.class`: 1178 bytes, `566127a7444cdcc05de5ce43724e412c80108c775f1950b9a559a620e08f9fd2`.
  - `ArrayList$Itr.class`: 713 bytes, `340358b70e03af53ac4f696d19362c8c6615f24cbf6099357864eb983a02c029`.
- No original Minecraft inputs, parent reviews/perf evidence, other worktrees, network, or pushes were accessed. Generated fixture Java is an oracle/test input only; host Java did not execute guest methods.

## Implementation

`ArrayList` now performs ordinary private-state append in Java bytecode: identity-test only the actual default-capacity sentinel; request capacity 10 for that sentinel, otherwise use the real current array; increment this class's private `modCount` once before a possible growth allocation; on growth request `oldCapacity + (oldCapacity >> 1)` or the minimum required, allocate a real `Object[]`, and copy existing references in an ordinary loop. It then stores the opaque argument (including null) at the private `size`, increments size once, and returns true. Allocation/copy remain subject to existing EVM quotas; no host copy, fake capacity, clamp, native add, or rollback was introduced. Constructors and `<clinit>` are bytecode-identical to baseline; `elementData`, `size` field prefix is preserved, and `modCount` is appended.

`isEmpty()` reads private size so subclasses overriding public `size()` cannot lie to this operation. `Itr` retains owner/cursor field prefix and appends `expectedModCount`; constructor captures owner `modCount`; `next()` checks CME before exhaustion/NSEE and then reads private size/backing; `hasNext()` remains a non-fail-fast private-size check. `remove()` and all other unmeasured operations remain unimplemented.

No global native slot, exception kind, class count, ABI, storage schema, checkpoint codec, constructor policy, array/object quota, resource bound, or interpreter dispatch was changed.

## Java 8 images and committed commitments

- New `ArrayList.class`: 1620 bytes, SHA-256 `00f45238a3b8d18be113b2e4f6a789aec62cfc3947ad0e0f5b7433c531b6761e`, Keccak `3fae9b5e6773855d139433033768906b552b49958d4873dd16d89095257ddc42`.
- New `ArrayList$Itr.class`: 856 bytes, SHA-256 `5eb966be7c155031ba175038e48852582b1c8fa995b21e4826d4de414a03ef0c`, Keccak `74dcdbd75c1fd4a8d3a223403f4885fa500e34203217885650b4676f70d8d68b`.
- Ordered bootstrap leaves: **127 unchanged in count**; comparison against P59 found exactly slots 98 and 115 changed, the other 125 byte leaves exact. Raw class limit remains 150 / 1,063,930 bytes; diagnostic bound 277 / max class index 276; slots 105–126 and exception registry are retained.
- Full bootstrap domain: `JVMEVM:MC-ARRAY-LIST-ADD-BOUNDED-1:BOOTSTRAP:1`; ordered root `a34286fcbd75d2da7c02c3c803a825d1b77d7228a896da502973dbf15e1ad2ed`.
- All nine engine domains and four coordinator package/class/seed/VM domains use the fresh `MC-ARRAY-LIST-ADD-BOUNDED-1` profile. Coordinator's fixed engine code-hash pin matches the new deployed engine.
- Engine deployed runtime: 454,921 bytes, SHA-256 `42c0a3713ddbb8144a698bfdceae784174678afed0cf653a6c5d32d80fa8032d`, Keccak `ea27e41942b6d998d0264a8a393a131bc51f2cd94b9a45559e82ff370622c795`.
- Coordinator deployed runtime: 5,411 bytes, SHA-256 `b19d553c9dc998821c2de4cf2bb142cdb23633ea647eb28b4deaa39098675492`, Keccak `28ee7fa7a1d99ef8d2c7a2f82794d99aa147fa81f626560627fcea87908a77e5`.
- Engine/coordinator ABI and Solidity storage layouts compare exactly to the approved baseline. Solidity deltas are restricted to two bootstrap images and nine fresh engine-domain literals; coordinator deltas are four fresh domain literals and the engine runtime-codehash pin. Existing warnings note the oversized local interpreter is not EIP-170 / ordinary CREATE compatible.

## Candidate EVM evidence

The generated fixture `test-fixtures/src/probe/ArrayListAddProbe.java` checks the measured `invokeinterface List.add(Object):boolean` call, default and int(0/2) construction, append return/size/isEmpty, null and reference identity/order, repeated growth to 48 elements, independent iterators, exhausted iterator NSEE, mutation CME including iterators created while empty and already exhausted, private-state behavior with an overriding `size()==777`, typed-target identity/copy/null-slot/tail preservation, and null-target NPE. `javap` confirms the three initial append calls are `invokeinterface java/util/List.add:(Ljava/lang/Object;)Z`.

A fresh q7 session with the candidate engine/coordinator and two generated raw classes completed as VOID: lifecycle 2, epoch 1374, 9616 Java instructions, 15 internal steps. `verify` reopened the real checkpoint/world and confirmed engine head, coordinator package root, checkpoint hash and final roots. Durable head: machine `0x8e5a99d83299387cf181fb180fbcad62d2c16b60d4c31d599cd37f049c8f1ebc`, VFS `0x5615840caaa3387a8fbee1f3620815782cd35c20567a70755953734bbb09d382`, checkpoint `0x6710861fa3bd77f195526609c404807d5f7fd1e3f374c860f741679aa9ba1a2c`. Local ignored evidence (preserved, not committed):

- World: `build/worlds/q7-invokeinterface/` (disk world; do not remove).
- Reopen report: `build/worlds/reports/q7-invokeinterface/world-report.json`, SHA-256 `ca2ebc0d359b38e43003cdb540be6f6d499603544ffd461763c786f95366e528`.
- Durable head: `build/worlds/q7-invokeinterface/durable-head.json`, SHA-256 `808311c216da90169b46354fe3a59a121b8af55f4b1c6a642ad87355723f1ea3`.

A first q1 fixture run reached a terminal `ConcurrentModificationException` at the final lying-subclass check. Review of the fixture showed the test itself incorrectly expected an iterator created before `add` to consume the newly appended value; fail-fast CME is the specified behavior. The corrected fixture expects CME and then checks a fresh iterator. The q1 world `build/worlds/q1-fullnames/` and its terminal head (SHA-256 `c80ce7538800f5a227c1189128f3de448f26c6e5bec8866e201f4e82b385033a`) are preserved and not counted as a pass. A corrected q1 replay and cross-quantum/direct equivalence have not yet been run by this worker.

## Reproduction and remaining gates

Run `./reproduce-source.sh <unique-run-id>` to recompile both old Java 8 images and the new images with the pinned JDK, build isolated engine/coordinator artifact copies using the pinned local solc dependency, and verify class hashes, ABI/storage equality, and the full bootstrap root. Output is unique beneath ignored `build/`; script refuses overwrite.

Parent handoff should independently rebuild and run the frozen complete gates with fresh worlds: q1/q7/direct equality; growth and capacity boundaries; OOM ordering (including modCount invalidation while size/backing remain unchanged); short-target raw refusal, ASE and unsupported APIs; `global native 22`, String-local 12 and retained collection/map tails; raw150/high-state boundaries and reopen. Those outcomes are not asserted by this candidate report.
