# Supplier-link candidate test summary (not acceptance)

- P60 snapshot manifest: all 9 pinned source/artifact/driver/helper hashes verified before edits.
- `audit.py`: PASS. It reconstructs the exact engine/coordinator delta from the approved snapshot, checks the 195-byte Java 8 classfile, all 127 prior bootstrap leaves, Supplier leaf/root, class staging offsets, raw/cap invariants, and unchanged engine/coordinator ABI and storage layout.
- Java 8 source compile and `javap -verbose`: class version 52, flags `ACC_PUBLIC, ACC_INTERFACE, ACC_ABSTRACT`; `get()` is abstract/public, erased to Object, signature `()TT;`; no fields, Code, native, default or static helper.
- Trusted generated Java 8 fixture oracle: exit 0. No original Java/JAR inputs.
- Actual EVM fixture: q1 (143 epochs), q7 (21 epochs), and direct q=65,536 (1 epoch) all complete normally. Terminal machine and VFS roots match for q1/q7/direct. q1/q7/direct reopen checks pass in fresh processes.
- Actual EVM raw-150 fixture (150 generated classes): normal completion and fresh-process reopen pass. With no optional-class collisions, Supplier is physical class-program index 277 in a 278-entry program.
- Negative raw replacement: `BootstrapProfileError(1,3)`, Head unchanged. Wrong invoke kind: `CallError(1,11)`, Head unchanged; not an AME-fabricated result.
- Preserved discovery failures: first driver pin check failed before execution; raw names without `.class` were refused by DI0; generated v1 `Object.getClass()` failed at bytecode PC 148; v2 array class literal failed at PC 146; v3 `Class.getSuperclass()` failed as `CallError(3,230)`. Each attempt has its own retained world/logs. The approved Class bootstrap has no `getSuperclass`; this stage intentionally did not add it.

All generated world/checkpoint/log material is under the ignored local `worlds/` directory and is not staged. No original Minecraft input or parent review/performance evidence was read; no push/network action was taken.
