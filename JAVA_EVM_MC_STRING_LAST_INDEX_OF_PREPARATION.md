# Java-on-EVM Minecraft `String.lastIndexOf(String)` preparation

## Measured blocker

The bounded StringBuilder parent `parent-31e5a573c` passed an optimizer200 source build at386100/393216 and the parent-amended generated gate. Fresh unchanged original30 advanced from8697J to a last successful11566J/39I, with1654 canonical receipts verified. q7 and narrowed q1 both stop atomically at `StringProfileError(1,56)`.

Parent-only frame and constant-pool decoding proves the active instruction is genuine `SimpleLogger.<init>` classIndex26/methodIndex0 PC56, `invokevirtual #12`:

```
java/lang/String.lastIndexOf(Ljava/lang/String;)I
```

The measured argument is the non-null one-character String `"."`. No raw class-count or new bootstrap-class increase is authorized.

## Strict scope

1. Replace only the existing bounded `java/lang/String` bootstrap image at its fixed slot26 with a Java-8-produced image that preserves every accepted field/method and adds exactly `lastIndexOf(String):int`.
2. Prefer ordinary guest Java Code implemented from the already accepted `length()`/`charAt(int)` primitives. Do not add a host implementation or global native binding. Null target must follow the ordinary guest NPE path.
3. Implement correct UTF-16 backward substring search for all bounded non-null guest Strings, including empty target, target longer than receiver, overlap and absent cases. Do not add the `lastIndexOf(String,int)` overload, substring, regex, encoding, or broad String APIs before measurement.
4. Preserve all other84 bootstrap image bytes/order, bootstrap count85, StringBuilder/System.err/PrintStream/EnumSet semantics, runtime-derived commitments, raw30/262144, CP4096, Code65535, frames128, heap/VFS/checkpoint1MiB, Head32768B, LOCAL1B/25M,12 global native bindings,14 exception kinds and the optimizer200 toolchain.
5. Retain the semantics-preserving outlined post-VFS bootstrap-tail layout and runtime <=393216.

## Required generated-only gates

- exact parent-pinned reverse verifier, Java8 provenance, sole slot26 replacement proof and unchanged other84 images;
- q1/q7/direct/reopen/canonical cases for suffix/middle/prefix, repeated/overlap, absent(-1), empty target(receiver length), empty receiver, longer target and UTF-16 chars;
- catchable null-target NPE and uninitialized String control;
- retained StringBuilder identity/content/null/replacement and honest quota-checkpoint refusal;
- retained System.err, failed-init, raw30/31 three-layer, byte boundaries, EnumSet/ACC_ENUM, queue and OOM controls;
- source build, size/hashes, receipts and monitoring.

No original artifact access in candidates; parent alone runs original30 after acceptance. No substring or Minecraft/Done claim.
