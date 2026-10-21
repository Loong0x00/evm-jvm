# MC P35: append-only Java 8 `HashMap()` constructor

This is a source-only candidate based on the exact accepted P34 snapshot at
`evidence/java-evm/minecraft-entry/performance-base-p34/` (source commit
`2c2107d253c6fb879a5bbdf108de4c17bcdeae33`). `tools/verify_source.py` checks the
snapshot manifest, recreates the Java 8 classfile with the pinned local JDK 8
compiler, compares the engine against the exact append-only source delta, and
recomputes the 101-leaf bootstrap root. It also checks that the coordinator
change is only the paired engine-codehash pin.

## Semantic boundary

- Appends `java/util/HashMap` as bootstrap image/root slot 101 (zero-based slot
  100); the prior 100 leaves retain their exact bytes and order.
- Supplies Java 8 `HashMap()V`, `size()I`, and `isEmpty()Z` as ordinary guest
  bytecode, with the genuine `AbstractMap`, `Map`, `Cloneable`, and `Serializable`
  type closure.
- The genuine no-argument constructor initializes only `loadFactor` to
  `0.75f` (`0x3f400000`). `table`, `entrySet`, `size`, `modCount`, and `threshold`
  retain Java's default null/zero state. No table or other backing storage is
  allocated. The private `$Node` type appears only in the authentic array-field
  descriptor and is not an added image.
- The 24 declared native Map/Object operations intentionally have no native
  binding; generated controls require typed, atomic refusals. No map operations,
  table allocation, reflection, or host Java semantics are provided.
- Raw-class admission remains 150 classes / 1,063,930 bytes. The MR01 u16 class
  count remains unchanged; its *derived* maximum rises from 250 to 251 because
  this profile has 101 bootstraps. Other P34 resource, heap, checkpoint, gas,
  frame, and engine caps remain pinned.

The local Java 8 reflection oracle is limited to trusted JDK behavior and checks
that a newly constructed real `HashMap` has null `table`/`entrySet`, zero
`size`/`modCount`/`threshold`, and the exact `loadFactor` bits. It is not used in
the EVM execution path.

## Build and gates

```sh
python3 evidence/java-evm/minecraft-entry/hash-map-default-constructor/tools/verify_source.py
python3 evidence/java-evm/minecraft-entry/hash-map-default-constructor/tools/run_gate.py <fresh-run-id>
```

The generated-only gate rebuilds the engine/coordinator, checks constructor,
type assignability, fresh-object identity, null/zero field state from MR01, and
q1/q7/q65536/q4096 equivalence. It also requires a fresh-process q1 checkpoint
reopen, typed refusals for `put` and the absent capacity overload, and raw-name
replacement rejection. All earlier copied generated P34 controls remain in the
gate. These are local preinstalled-code `runtime.Call`/EVM results, not standard
CREATE/EIP-170 deployment claims and not Minecraft execution.

The durable run report and exact hashes go under `runs/<run-id>/`. Nothing in
this stage executes or reads the original Minecraft JAR, classes, resources,
worlds, checkpoints, receipts, or original Java program. Parent integration and
acceptance remain separate.
