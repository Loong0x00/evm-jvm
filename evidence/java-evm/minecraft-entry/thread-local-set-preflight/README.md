# Bounded directly-created `ThreadLocal.set` source stage

This generated-only stage derives from accepted `parent-15aa4b8b0`. It replaces
only bootstrap slot 88 (`java/lang/ThreadLocal`, image 89) with this 305-byte
Java 8 `-g:none` image:

```java
package java.lang;
public final class ThreadLocal {
  private Object value;
  public ThreadLocal() {}
  public Object get() { return value; }
  public void set(Object value) { this.value = value; }
}
```

The exact SHA-256 is
`041db70026c508194d1b13ccdc988e82fb07316a4900c3955b2d5aa3e0664d9b`.
`ThreadLocal` remains final and directly extends `Object`, so normal hierarchy
validation refuses a subclass before execution. The sole private `Object`
field is the value for the one guest thread: `get()` initially returns null;
`set(Object)` stores/replaces (including null) the exact reference read by the
next `get()`. There is no value map, default factory, thread object state, or
native/host binding.

`remove`, `withInitial`, `initialValue`, subclass overrides, and multithread
behavior are absent/refused. The generated omitted controls all preserve their
root: absent members return `CallError(3,pc)` and final-subclass controls return
`HierarchyError(3,1)`.

Raw limits remain `37 / 282358`; there are still 90 bootstrap images in the
same order, diagnostic bound 127, global native bindings 13, one selected
resource at 4096 bytes, 128 frames, 1 MiB checkpoint, Head 32768, and 25M
reserve. The exact raw37 root is derived at runtime over every ordered image
hash, including direct `_bootstrapObject()` hashing at slot 0:
`keccak256(abi.encode(DBOOT, h))` =
`85fbf6a9abd54f7fbc872c0387cc129782adb52f753bc448bc099dabeef62ab1`.

The parent baseline was 392934 bytes. The built engine is 393072 / 393216
bytes, leaving 144 bytes. No layout recovery was needed; `layout.json` and
`verify_source.py` reject a precomputed root and prove all non-image89 engine
bytes are the parent source after only the equal-width staging-domain change.
The coordinator remains 5394 bytes.

The focused set/default-null/replace/null/identity fixture reaches 148 Java
and 2 internal steps. q1/q7/direct/reopen agree on machine root
`0x6e4b883ea5a81e08c183861f30f23cfbfe7702f4a92ae488eddd9f3a5c983ac4`
and opaque payload SHA-256
`2a4777aae0391382edd9859678ad24f778b9892d63544d006c0ab547db865505`,
with epochs 148/22/1. The retained direct-constructor identity fixture agrees
at 40/2 steps and epochs 40/6/1.

The focused-plus-retained generated gate ran 429 commands in 356.189 seconds
under the fixed 1200-second limit and verified 5412 canonical receipts. It uses
only trusted generated Java 8 fixtures; it does not open an original artifact,
JAR, class, resource, checkpoint, or world. No `StringBuilder.setLength`,
provider/factory, world, or Done claim is made. Parent alone reruns original37.

Reproduce with pinned local tools only:

```sh
python3 evidence/java-evm/minecraft-entry/thread-local-set-preflight/tools/build.py build/java-diff-mc-thread-local-set-build-LOCAL
python3 evidence/java-evm/minecraft-entry/thread-local-set-preflight/tools/generate_fixtures.py build/java-diff-mc-thread-local-set-fixtures-LOCAL
python3 evidence/java-evm/minecraft-entry/thread-local-set-preflight/tools/gate.py build/java-diff-mc-thread-local-set-build-LOCAL build/java-diff-mc-thread-local-set-fixtures-LOCAL build/java-diff-mc-thread-local-set-gate-LOCAL
```
