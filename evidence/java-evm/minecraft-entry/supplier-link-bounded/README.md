# Java 8 `Supplier<T>` bounded link candidate

This is an **unaccepted candidate** based only on the approved P60 source snapshot. It adds one authentic Java 8 `java.util.function.Supplier<T>` interface image, reserves that binary name against raw replacement, and appends one class-program slot. It does not add native bindings, VM dispatch behavior, lambdas, `invokedynamic`, helper methods, or a result shortcut. Implementations—including the covariant `get():String` and compiler-generated bridge `get():Object`—execute as ordinary classfile bytecode through existing `invokeinterface` dispatch.

## Provenance and pins

- Base: `supplier-link-source-base-p60/` (manifest hashes verified before work); base commit `6268564fbf5cac672572ef9c1ee71f70917ba9ed`, accepted guest-code anchor `c32a351f3ae412015fa6eaa7df0cccf9590e719f`.
- Supplier class: 195 bytes, SHA-256 `67d3786e7e16a66579fae0687706c72b26c109ac94b0e77cc27eac39a431a1ff`, class version 52, public/abstract/interface, one public abstract erased `get()Ljava/lang/Object;`, no fields or Code/native method.
- Bootstrap leaves 0–126 equal the authoritative P60 ordered prefix and prior root `a34286fcbd75d2da7c02c3c803a825d1b77d7228a896da502973dbf15e1ad2ed`; Supplier is leaf 127. New root `cc8f91923d7ea181f19178b2f8d4e08bf7af5337fc58ebe4cc5cbaddf017f593`.
- Engine runtime: 455,564 bytes; SHA-256 `dfa8d02fb2556300f5dfdb5bed542eee0fcc1bf4e563ac5f9a7b2b627d0cbdeb`; Keccak `cb0719839a5b81d48d19ff0adfa8ea6e3bce8d8cc834165962d8364f8145cee2`.
- Coordinator runtime: 5,411 bytes; SHA-256 `30f84e9888c1a719ddabb2653918927b69c663e0a8ba21d2d96f6292bf419be2`; Keccak `81d2f439c5dd7bcbead3dbfa2f08b9621617a3870aab4e24146cd2cad69bb6f4`.
- All 9 engine and 4 coordinator profile domains are fresh. ABI and storage layouts compare byte-for-byte equal to the P60 snapshot. Raw/array/object/checkpoint/runtime/frame/quantum/internal-step/gas limits remain unchanged; see `pins.json`.

## Reproduction

Run from the repository root. The only Java host execution below is the trusted generated fixture oracle; no original game/JAR inputs are used.

```sh
/usr/lib/jvm/java-8-openjdk/bin/javac -g:none -source 8 -target 8 \
  -d evidence/java-evm/minecraft-entry/supplier-link-bounded/java/classes \
  evidence/java-evm/minecraft-entry/supplier-link-bounded/java/bootstrap/java/util/function/Supplier.java
/usr/lib/jvm/java-8-openjdk/bin/javap -verbose \
  evidence/java-evm/minecraft-entry/supplier-link-bounded/java/classes/java/util/function/Supplier.class
NODE_PATH="$PWD/jvmevm/runtime/node_modules" node evidence/java-evm/minecraft-entry/supplier-link-bounded/engine/build.js
NODE_PATH="$PWD/jvmevm/runtime/node_modules" node evidence/java-evm/minecraft-entry/supplier-link-bounded/coordinator/build.js
python3 evidence/java-evm/minecraft-entry/supplier-link-bounded/audit.py
/usr/lib/jvm/java-8-openjdk/jre/bin/java -cp \
  evidence/java-evm/minecraft-entry/supplier-link-bounded/fixtures/classes-v4 fixture.SupplierMain
```

The candidate-only `canonical-driver.go` uses the P60 public-EVM transport with the new runtime/coordinator hashes and profile domains. Build it with:

```sh
go build -o evidence/java-evm/minecraft-entry/supplier-link-bounded/bin/supplier-driver \
  evidence/java-evm/minecraft-entry/supplier-link-bounded/canonical-driver.go
```

Generated positive fixture: `fixtures/supplier-fixture-v4.zip`, bindings in `pins.json`. Raw-150 fixture: `fixtures/raw150/supplier-fixture-raw150.zip` (150 generated classfiles). All databases/checkpoints and attempt logs live only under the ignored `worlds/` tree; binaries live under ignored `bin/`.

## Evidence summary

- Generated fixture calls `Supplier.get()` through both JDK `Supplier` and a public child interface; checks the same returned reference and side-effect counter, covariant bridge execution, guest `ArithmeticException` catch, wrong-cast `ClassCastException`, null-receiver `NullPointerException`, a genuine `Supplier[]`, clone/length, `Array.newInstance(Supplier.class, 1)`, and `Class.getName()`.
- q1: lifecycle 2 after 143 epochs; q7: lifecycle 2 after 21 epochs; direct quantum 65,536: lifecycle 2 in one epoch. q1/q7/direct terminal machine-state root is `37e85a160b8aa25644654b4d262c970814742ff0d2522e463e2bf78dd496672a`; VFS roots agree. q1 and q7 were reopened and verified in fresh driver processes. The raw-150 run completed and was separately reopened; its Supplier class-program slot is 277 (`150 + classSlot(39) + appendOffset(88)`), exercising an index over 255.
- Raw Supplier replacement is refused as `BootstrapProfileError(1,3)` with the durable Head unchanged. A deliberately wrong invocation opcode is refused as `CallError(1,11)` with Head unchanged, not converted to `AbstractMethodError`.
- Every failed fixture/world attempt is preserved locally and excluded from Git. The earlier generated v1/v2/v3 probes document `Object.getClass`, array class-literal, and `Class.getSuperclass` limits in the approved P60 surface.

## Explicit limitation / boundary

The requested `Class.getSuperclass()` assertion cannot run against the approved P60 Class image: a generated v3 guest call produced `CallError(3,230)`, and that image has no `getSuperclass` declaration. It was not added here because the sole semantic writer scope is Supplier linking and no metadata API may be introduced. This is recorded as an unrelated base-profile blocker, not treated as Supplier functionality or silently skipped as a pass. The candidate is not an acceptance/Done claim and contains no original Minecraft artifacts, classes, resources, worlds, receipts, parent review, or performance-review evidence.
