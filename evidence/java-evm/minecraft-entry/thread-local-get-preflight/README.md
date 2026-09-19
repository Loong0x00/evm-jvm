# Bounded directly-created `ThreadLocal.get` source stage

This generated-only stage derives from accepted raw37 evidence
`parent-24250cb9d` / `classcount37-byte282358-preflight`. It replaces only
bootstrap slot 88 (`java/lang/ThreadLocal`, image 89) with a 193-byte Java 8
`-g:none` image:

```java
package java.lang;
public final class ThreadLocal {
  public ThreadLocal() {}
  public Object get() { return null; }
}
```

The exact image SHA-256 is
`cc0a43a9627fd7f6a1ec1b85711e4cb1ba3d988dab06e3fd5fbe795e175b1289`.
The final class flag enforces the stated direct/unoverridden boundary: a raw
subclass (including an `initialValue` declaration) is rejected by normal
hierarchy validation before execution. `get()` therefore has only the Java 8
unoverridden default-null result; it allocates no value map and reads no thread
state.

`set`, `remove`, `withInitial`, `initialValue`, subclass override behavior and
new-thread behavior are absent/refused. In particular, the two generated
subclass controls reject atomically as `HierarchyError(3,1)`; `set`, `remove`,
`withInitial`, and attempted thread construction each reject as `CallError(3,pc)`.
No value is fabricated and no Head is published on any refusal.

Raw limits remain `37 / 282358`; there are still 90 bootstrap images in the
same order, diagnostic bound 127, global native bindings 13, one selected
resource at 4096 bytes, 128 frames, 1 MiB checkpoint, Head 32768, 25M reserve,
and all prior resource/gas/toolchain semantics. The coordinator remains 5394
bytes.

The direct unshared dynamic-root layout was `393291 / 393216` bytes,
75 bytes over the cap. The accepted recovery preserves the exact raw37
runtime-derived ordered root: `_bootstrapRoot` allocates `bytes32[90]`, derives
every non-isolated image hash directly (including
`keccak256(_bootstrapObject())` at slot 0), and returns
`keccak256(abi.encode(DBOOT, h))`. The retained isolated raw37
`DBOOT_ENUMSET`, `DBOOT_ITERABLE`, and `DBOOT_MATH` commitments are unchanged.
The optimization is elsewhere: `_validateInitialMainRoot` receives only its
used `RuntimeState` argument after the canonical empty `String[]` allocation.
`root-commitment.json` records the ordered hashes and root; `verify_source.py`
independently reconstructs them with pinned local Keccak, checks every
untouched image byte, requires the complete raw37 root assignment sequence,
and rejects a full precomputed root. The recovered engine is
`392834 / 393216` bytes (457 bytes recovered, 382 bytes headroom), SHA-256
`7f4cd30f0cfeed3ba64b1d0be7663669bbd15e9cb388081052fe7643589f2a8b`.

The focused default-null fixture reaches 51 Java and 2 internal steps. q1/q7/
direct/reopen agree on machine root
`0x84ef50561366b5c653df1a621c831477a36da5b66b03aa32b739c479ee3dcea8`
and opaque payload SHA-256
`3626fd60d0999010c17ebf30dc9973954cb16e96736b90d2193f82dd635862f6`,
with epochs 51/8/1. The retained constructor identity fixture still agrees at
34/2 steps and epochs 34/5/1.

The corrected focused-plus-retained generated gate ran 111 rows and 390 commands
in 359.116 seconds under the fixed 1200-second limit, verifying 4683 canonical
receipts. It uses only trusted generated Java 8 fixtures; it never opens an
original artifact, JAR, class, resource, checkpoint, or world. No provider,
factory, set API, thread scheduler, world, or Done claim is made. Parent alone
runs unchanged original37.

Reproduce with pinned local tools only:

```sh
python3 evidence/java-evm/minecraft-entry/thread-local-get-preflight/tools/build.py build/java-diff-mc-thread-local-get-build-LOCAL
python3 evidence/java-evm/minecraft-entry/thread-local-get-preflight/tools/generate_fixtures.py build/java-diff-mc-thread-local-get-fixtures-LOCAL
python3 evidence/java-evm/minecraft-entry/thread-local-get-preflight/tools/gate.py build/java-diff-mc-thread-local-get-build-LOCAL build/java-diff-mc-thread-local-get-fixtures-LOCAL build/java-diff-mc-thread-local-get-gate-LOCAL
```
