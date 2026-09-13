# System.arraycopy generated COPY candidate

This isolated candidate derives from the parent marker-map engine, but contains
only generated Java-8 fixtures. It has no original-JAR argument or handling and
is not an accepted JVM/profile/Minecraft run.

## Surface

The appended, caller-reserved `java/lang/System` image has only private
construction and static native
`arraycopy(Object,int,Object,int,int):void`. Its one EVM binding is bounded by
existing array/heap limits. It uses raw primitive array cells only when primitive
leaves are identical; reference cells use the normal array component predicate,
so an ArrayStoreException retains an already-valid destination prefix. Overlap
selects a backward or forward loop. Null, structural/type and range faults use
the ordinary guest NPE, ArrayStoreException, and ArrayIndexOutOfBoundsException
paths—not an EVM success/revert substitute. There is no host copying.

System is bootstrap-root position 44; map, Class, Runnable, Object.equals,
lazy Selected and MR0 behavior are retained. `Program` keeps the conditional
Runnable tail calculation and places System after the map appends. All
candidate domains are `MC-ARRAYCOPY-PREFLIGHT/.../v1`, intentionally preventing
cross-code/checkpoint reuse.

## Reproduction

Set `NODE_PATH` to a local pinned solc 0.8.30 module, then run:

```sh
NODE_PATH=/path/to/node_modules python3 \
  evidence/java-evm/minecraft-entry/arraycopy-preflight/run-smokes.py \
  "$PWD/build/java-diff-mc-arraycopy-replay"
```

The runner refuses an existing output, builds source with solc 0.8.30/opt200/
viaIR/Cancun/metadata-off, and uses a single 20-minute/4GiB child process group.
It records generated ZIP -> AS0 -> ZI0 -> DI0 receipts and a TEST-only Java
oracle; it never accepts an archive path.

The committed `actual-receipts/` run has engine 314445 B, SHA-256
`bd937b517bde7ab82e55e8cf4576a3d9bbd9f9e2997dfa253d916a7fb8d321e3`, Keccak
`e26868d0da83a19f81db91913b72f0b8e64141c660dcd9fd4ab9c1faa01ef5ba`;
coordinator Keccak
`4f20d3f559992bb986d66e94b56286a5eae0e3c2ec8d5349e066c0f725abe2b8`.

## Retained failure

The generated assertions and host oracle pass, and q1/q7 both terminate VOID
and reopen. Their terminal machine roots differ (q1 176 Java steps; q7 175),
so this run is deliberately recorded as a semantic/checkpoint equivalence
blocker. q4096/direct additionally records panic `0x32` before publication.
Neither result is an acceptance claim or a reason to raise a limit.
