# Minecraft class-count 24 COPY preflight

**Unaccepted generated-fixture derivative only.** This is the narrow 24-image /
262144-byte COPY required before the parent may independently select/retry an
original 18-image package. It is not an accepted-cap promotion, class loader,
generic Session work, or Minecraft execution result.

## Exact source basis and delta

`evidence/java-evm/minecraft-entry/classcount-preflight/parent-input.json`
pins the six parent inputs from
`evidence/java-evm/minecraft-entry/parent-f780f1a13/`, including its actual
`executed_bounded_driver.go.txt` (not the broken worker driver). The mechanical
source guard checks those input hashes, the 45 bootstrap images/order (System
at index 44), all pre-existing native arity assignments including
`_loadNativeCallee`'s `s.argumentCount = s.argumentKinds.length`, and the only
class-count changes:

* engine `MAX_RAW_CLASSES` and config commitment: 16 -> 24;
* coordinator four fixed binding arrays and constructor maximum: 16 -> 24;
* bounded Go transport metadata/reopen maximum: 16 -> 24.

The byte bound remains 262144. CP4096, Code65535, heap/VFS/frame limits, 1MiB
checkpoint, 32768B Head, 320KiB engine ceiling, 100M ordinary calls/30s,
25M reserve, and all other bootstrap/map/Class/mirror/main semantics are
unchanged. The conditional supplied-Runnable tail is deliberately exercised.

Fresh identities prevent checkpoint/domain/store reuse:

* domain: `MC-CLASSCOUNT24-PREFLIGHT1`;
* LOCAL initial-state-only engine address:
  `0x4d43434c415353434f554e543234000000000001`;
* engine: 314365 bytes, SHA256
  `9f272f78fb59ffc827a7456073cbfefa70c8b1f6c7b70731d505161194f2ee3c`,
  Keccak `b840a1368591f665791e3a2458e311c06a6ec47a68116e26748adaf0c9e74b60`;
* ordinary-CREATE coordinator: 3547 bytes, SHA256
  `b93a77ff5e4c4321360c178069738d4cb13e5fe5f6577271dcbca0e15acbed1f`,
  Keccak `16b9c3624206cbd7a183bd270df3608f199047cb29b09dd742ac184ef4eb46ba`.

Compilation is pinned to solc 0.8.30+commit.73712a01.Emscripten.clang,
optimizer 200, viaIR, Cancun and metadata off. Controllers, AS0, ZI0 and DI0
are all ordinary CREATE; only the oversized engine uses the explicit LOCAL
initial-state installation mechanism.

## Generated-only measured gate

`actual-gate-20260913/` contains allowlisted sources, Java-8 oracle fixture
ZIPs, artifacts/pins, external process receipts, Heads and EVM-issued
checkpoints. It deliberately excludes LevelDB, resource pages, original
payloads and compiled Go binaries. The generated package has exactly
17/18/24 selected images: `CountMain`, every statically invoked Tail image,
and a supplied `java/lang/Runnable`; it uses interface dispatch, shifted-tail
Class literal identity/non-initialization plus `getName`, and System.arraycopy.
The final checkpoint proves every Tail was initialized and the EVM static
sentinel is 122/138/255 respectively.

All q1/q7/direct runs reached actual terminal `lifecycle=outcome=2`, result 0,
with canonical outer/nested ABI, exactly one nested `CheckpointCommitted` event
per successful slice, fresh-process reopen, checkpoint SHA and Head checks.
No call timeout/cancel occurred and no direct reserve refusal occurred:

| bindings | q1 / q7 / direct epochs | Java/internal | machine root |
|---:|---:|---:|---|
| 17 | 208 / 30 / 1 | 208 / 4 | `f25e2bbb75f30862a34acea321fe998d065b415f3fc48899acdea70e37088a45` |
| 18 | 212 / 31 / 1 | 212 / 4 | `dcca08d326a0cea6b4d243d7a1800cc3f28751918c089f009817e1f9ca426613` |
| 24 | 236 / 34 / 1 | 236 / 4 | `cf44d5131a024c4a9908518612f5d2072afe353c0025117a0e9f35ecc7a5805a` |

The generated 25-image boundary first provisions real AS0->ZI0->DI0 bindings,
then gets an **actual EVM coordinator constructor** `MR0Error(2)` selector
`0xab23ed08` at ordinary 100M gas; its EVM root is unchanged. It is not a host
JSON-length refusal. The full sampled process-group gate completed in 45.344s,
peak 43520000 bytes, below its 20-minute/4GiB bounds.

## Reproduction

From this worktree, with a fresh ignored `build/` directory:

```sh
python3 evidence/java-evm/minecraft-entry/classcount-preflight/verify_source.py
python3 evidence/java-evm/minecraft-entry/classcount-preflight/build.py build/java-diff-mc-classcount-rebuild
python3 evidence/java-evm/minecraft-entry/classcount-preflight/generate-fixtures.py build/java-diff-mc-classcount-fixtures
python3 evidence/java-evm/minecraft-entry/classcount-preflight/gate.py \
  build/java-diff-mc-classcount-rebuild build/java-diff-mc-classcount-fixtures \
  build/java-diff-mc-classcount-gate
```

The parent, not this derivative, must independently rebuild/replay these
sources and select any original 18-image retry under these fresh pins. No
original JAR/class/resource/world was read, indexed, parsed, packaged or
probed here; no EULA, server main body, world, listener, or genuine Done ran.
