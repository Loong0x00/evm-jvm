# NavigableMap link-only implementation result

Status: scoped implementation and worker-side EVM verification complete; parent independent review and fresh original replay remain outside this worker task.

## Change

Starting from the exact source-only P43 baseline, append one genuine Java 8 public abstract `java/util/NavigableMap<K,V>` interface extending the already-bounded `SortedMap<K,V>` marker. It declares no methods and does not implement any navigation behavior. The existing 106 bootstrap images remain the identical prefix; the new image is ordered bootstrap index 106. `NavigableMap` is added to the actual raw namespace reservation guard. No new opcode/native/dispatch behavior, API semantics, quota, engine/checkpoint wire schema, core protocol, or coordinator class-count migration was added. Existing SortedMap and TreeMap images are untouched.

The P44 bootstrap domain and coordinator package/class/resource/VM domains were coherently versioned, and the coordinator's fixed engine codehash was updated to authenticate this rebuilt engine. The coordinator continues to bind only raw decoder resources (`uint8`, capacity 150); derived engine classes are separate. With 150 raw bindings, the EVM engine class list is 257, and the new interface occupies class index 256. The engine's frame/heap class IDs are `uint256`; checkpoint class count and frame/heap class indices use the existing two-byte encoding. No uint8 class-index cast was found.

- Engine runtime: 422,246 bytes; SHA256 `990d44aa156e1392379494311d27326efe19ed886cb659c596ede35046306cae`; Keccak `c6d83a5101673e785ccb03e191d522743c3f401b6b0fb43a52d1b421bdec6065`.
- Coordinator runtime: 5,411 bytes; Keccak `fec02a9b7446aa43bcad5e7f47f9750e9d557a5d3950d587722d35d781da04d1`.
- New Java classfile: Java 8 classfile major 52; `ACC_PUBLIC|ACC_INTERFACE|ACC_ABSTRACT`; one direct superinterface `java/util/SortedMap`; zero fields and methods; 254 bytes; SHA256 `44efe011ca8062c1bb5bb1e8519bb0ab9fe7eb76c1133b7eea678609055d14e1`.
- New 107-leaf bootstrap root: `e7d9456b75653a4945e184c8a48c7af83ac4b17dd7fea813af53a2a420504dff`.

## Actual EVM checks

Fresh Go canonical driver worlds used public geth EVM/StateDB APIs, ordinary EVM artifact installation and the existing AS0/ZI0/DI0 path. No host Java interpreter, original Minecraft input, or symbolic execution supplied a guest result.

1. **Exact maximum raw/derived index.** Generated fixture bound 150 distinct classes. The real EVM reached terminal guest lifecycle 2 / outcome 2 / result 0. Checkpoint diagnostic independently reads 257 engine classes; the generated implementation and subinterface exercised `instanceof NavigableMap`, `checkcast NavigableMap`, child-interface hierarchy, and ordinary method dispatch. Checkpoint was 2,713 bytes and independently reopened by a different OS process. See `results/selected-results.json`, `results/receipts/raw150-q4096-start.json`, `raw150-checkpoint-class-index-diagnostic.json`, and `raw150-q4096-reopen.json`.
2. **Quantum equivalence.** A small generated implementation/subinterface fixture ran at q1, q7 and q4096 in separate worlds. Each completed with identical machine root `0x0adb287ab10b52f99f1a7c220365bf01de78655cb96807d4d3dd36b6ff976ecf`, VFS root `0x3a60e6910a09a982ef14fa7a04196953c1fa5f7e28a54344e930967401fb788d`, and guest counters 29 JVM / 2 internal steps. Each world was reopened in a distinct process. Epoch/checkpoint roots and physical transaction/call/read counters differ with quantum, as expected; they are separately recorded rather than misreported as equal. Final-slice receipts are under `results/receipts/small-q*-final-slice.json`.
3. **Raw namespace protection.** Supplying raw `java/util/NavigableMap.class` with bytes identical to the new bootstrap image returned `BootstrapProfileError(1,1)` (`0x6a23ad80`) and left trie root and durable head unchanged. The earlier non-identical raw replacement also refused; both receipts are preserved.
4. **Omitted API protection.** A separately generated class emits `invokeinterface NavigableMap.descendingMap`; because the bootstrap marker intentionally declares no navigation methods, execution refuses with typed `CallError(3,7)` (`0xd631c3a4`) and leaves root/head unchanged. The first draft called through concrete `Impl` (`invokevirtual`), so it did not test the intended interface surface; it is retained but not counted. Corrected v2 uses the interface-typed call and is the passing negative gate.

## Verification

- Verified all nine P43 source-manifest file lengths and SHA256 hashes before editing.
- `python3 tools/verify_source.py`: old 106 leaf prefix exactly identical; new genuine image materializer and leaf at 106 match the Java 8 classfile; root and engine/coordinator codehash pins match artifacts; fixed raw150 limit and two-byte engine class-index representation audited.
- Java 8 `javac -source 8 -target 8` rebuilt the classfile byte-identically; `javap -verbose` output is retained as `generatedfixtures/NavigableMap.javap.txt`.
- Pinned solc 0.8.30 build scripts rebuilt engine and coordinator; runtime hashes and sizes above. Engine is oversized for ordinary CREATE/EIP-170, as with this local interpreter profile; no deployment compatibility claim.
- `GOPROXY=off GOSUMDB=off GOTOOLCHAIN=local go build .../canonical-driver.go`, `go vet .../canonical-driver.go`, and `go test ./evidence/java-evm/minecraft-entry/checkpoint-2m/transport` passed.
- Worker scope did not include original Minecraft execution; parent alone performs original replay/review. No push performed.

## Reproduction

From repository root, first build with the pinned Node dependencies and Java 8 compiler:

```sh
NODE_PATH=/home/user/evm-jvm/navigable-map-link/jvmevm/runtime/node_modules node evidence/java-evm/minecraft-entry/navigable-map-link/engine/build.js
NODE_PATH=/home/user/evm-jvm/navigable-map-link/jvmevm/runtime/node_modules node evidence/java-evm/minecraft-entry/navigable-map-link/coordinator/build.js
python3 evidence/java-evm/minecraft-entry/navigable-map-link/tools/generate_fixture.py
python3 evidence/java-evm/minecraft-entry/navigable-map-link/tools/generate_refusal_fixtures.py
python3 evidence/java-evm/minecraft-entry/navigable-map-link/tools/verify_source.py
```

Then build `tools/canonical-driver.go` from repo root. The raw150 world command uses `MC_ENTRY_BINDINGS=EntryMain.class,Impl.class,Child.class,Filler000.class,...,Filler146.class` and q4096. The compact equivalence fixture uses the first three bindings with the same ZIP and q1/q7/q4096; run `setup-chain`, then `finish`, then `verify` in distinct processes. Negative runs set bindings to `CollisionMain.class,java/util/NavigableMap.class` or `OmittedMain.class,Impl.class` and use their corresponding generated ZIPs. Exact commands and canonical event/read receipts are retained under `results/receipts/`; transient LevelDB world directories are intentionally ignored.
