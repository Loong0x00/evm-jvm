# ClassLoader.loadClass preflight

**PARENT RESULT:** worker success path accepted after parent OOM correction and
true whole gate. Original requested `javax.servlet.Servlet`, absent from pinned JAR;
next must raise catchable guest CNFE. See CLASSLOADER_LOADCLASS_PARENT_PREFLIGHT.


Bounded LOCAL candidate from `cb35a61f7`; this is not an accepted profile and does
not execute an original Minecraft class, JAR, world, main body, or `Class.forName`.

## Scope

Only the existing bootstrap `java/lang/ClassLoader` image at position 49 is replaced.
The root still has 66 bootstrap images: a static image comparison in the archived
source confirms all other 65 image bytes and positions remain exact. The replacement
is the 777-byte Java 8 class SHA-256
`2642b16dc68706079058f50f2b08544328c495a23217740499d4bb897ae69e3d`.
It retains `getSystemClassLoader`, private `resourceExists`, and the existing
`getResources` Code, and adds:

```java
public Class<?> loadClass(String name) throws ClassNotFoundException {
    return loadClass0(name);
}
private static native Class<?> loadClass0(String name);
```

Native bindings 1--7 are unchanged. Binding 8 accepts only that exact private static
native descriptor/access/Code shape, one reference argument, and a reference result.
The normal static-call initialization and stack path remains in the interpreter.
The public wrapper is ordinary instance Java Code, so a null `invokevirtual` receiver
raises the pre-existing catchable guest NPE before it can reach the primitive.
Thread's null default is unchanged.

Binding 8 reads only an owned, bounded (1..256 UTF-16 units) guest String backing,
requires a dotted binary name, MUTF-8-decodes each immutable parsed Program class name
with slash-to-dot conversion, and requires exactly one match. It does not use a host
loader/catalogue and does not initialize the target. `ClassLoaderLoadError(1,pc)` is
malformed name, `(2,pc)` missing, and `(3,pc)` inconsistent target; none fabricates a
null result or ClassNotFoundException. `Class.forName` remains absent.

`_classMirrorForTarget` is now shared by ldc and binding 8. It retains the existing
allocation reservation, layout, canonical-name, loader, and quota checks. Raw targets
use the canonical VMClassLoader; bootstrap targets use null. Crucially the binding
publishes any arena allocations back to the active execution heap/frontier before
ordinary wrapper `areturn` validates the new reference.

## Source-built pins

* Domain `MC-CLASSLOADER-LOADCLASS1`, all nine engine domain constants;
* engine `0x4d432d434c4f4144434c415353504152454e5401`, owner
  `0x4d432d434f4144434c4153534f574e4552000002`;
* solc `0.8.30+commit.73712a01.Emscripten.clang`, optimizer 200, viaIR, Cancun,
  metadata disabled;
* engine 354483 bytes, SHA-256
  `aae886a60a2bdbdf717f3e8155355b3f2b5c10bcf8fe89231f24ce90d5570862`, Keccak
  `1b9cde8fe2b4576bdb5f86ff887473ce787151413b7d172e53f56617bb6a0a85`;
* LOCAL384 headroom 38733 bytes; it is below 384KiB. Accepted 320KiB is unchanged;
* ordinary-CREATE coordinator 4146 bytes, Keccak
  `3da30fdfd36be176c99947454bff71ed493464922cee557c4cf41268f62691ac`.

The source-only Go driver pins LOCAL1B calls, 30-second per-call behavior, 25M reserve,
128 frames, 24/262144 raw caps, 1MiB checkpoint and 32768-byte Head. It is retained as
`tools/driver.go.txt`; no Go binary or LevelDB database is archived.

## Generated EVM evidence

`LoadClassProbe` creates a raw nested class literal first (the already-pinned canonical
VM loader creation prerequisite), gets the canonical system loader, loads the nested
class twice by dotted name, compares both results with `Nested.class`, confirms the raw
mirror's loader identity, confirms `java.lang.Boolean` has a null loader and matches
its literal, and confirms the nested `<clinit>` did not run. It returns static 733.

Direct, q1, and q7 EVM/reopen worlds all finish with 52 Java and 2 internal steps and
machine root `0x0bab6322afa659e17539681d8d885f0fee7d4b5197ebde121035a8e8fa8ddb52`.
Their opaque checkpoints differ only by slicing metadata: direct epoch 1, q1 epoch 52,
and q7 epoch 8. Durable Heads, all q1 checkpoints, reports, artifact bytecode, fixture
classes, build logs and `SHA256SUMS` are under
`evidence/java-evm/minecraft-entry/classloader-loadclass-preflight/`.

Negative generated EVM calls preserve their roots and refuse honestly:

* missing `missing.Nope`: `ClassLoaderLoadError(2,1)`;
* malformed `bad/name`: `ClassLoaderLoadError(1,1)`;
* raw ClassLoader replacement: existing reserved-family refusal `(1,1)`;
* omitted protected `loadClass(String,boolean)`: `CallError(3,13)`.

## Limits and remaining work

These generated calls used the authorized LOCAL1B ceiling. The source build and each
EVM run completed under the stated 384KiB code cap, but this worker did **not** obtain a
single watchdog measurement covering compiler plus every generated process as one true
whole-process-tree peak. Thus no true peak/RSS acceptance claim is made here; parent
must independently source-build and perform the required fresh original22 q7 then q1
replay. The expected original behavior is only explanatory: the measured null receiver
must NPE and be caught before the later, still-unimplemented `Class.forName` frontier.
