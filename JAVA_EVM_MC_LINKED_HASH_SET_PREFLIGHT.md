# LinkedHashSet bounded guest collection preflight

**Worker candidate only; not parent acceptance and not Minecraft Done.**  This is a
LOCAL384KiB engine-only candidate based exactly on `48cd1693560677cd97c9aacc6604fd414c0baace`
(the parent system-loader result).  It does not read, package, or execute an
original JAR/class/world.  The full reproducible generated-only archive is
`evidence/java-evm/minecraft-entry/linked-hash-set-preflight/`.

## Narrow change

The prior 52 bootstrap images are byte-identical and retain their positions.
Nine images append after them, in this order:

1. `java/util/Iterator`
2. `java/util/Collection`
3. `java/util/Set`
4. `java/util/AbstractCollection`
5. `java/util/AbstractSet`
6. `java/util/HashSet`
7. `java/util/LinkedHashSet`
8. package helper `java/util/HashSetIterator`
9. `java/util/NoSuchElementException`

`HashSet` is deliberately bounded to a growable `Object[]`, linear uniqueness
comparison (`==` then virtual `equals`), one null, `System.arraycopy` growth,
size and independent-cursor iteration. `LinkedHashSet` has only the exact
`()V` and `(I)V` constructors and inherits that insertion order. `Iterator`
has `hasNext/next`; exhausted `next` genuinely throws the appended
`NoSuchElementException`. `Collection`/`Set` retain Java 8 hierarchy and
`AbstractCollection.isEmpty` is derived from `size`.

There is intentionally no remove/containsAll/toArray/spliterator/full hashing
or concurrency surface. A generated caller of `remove(Object)` gets the normal
`CallError(3,8)`, selector `0xd631c3a4`; no fake result is supplied. All nine
owned names (including interfaces and helper) are reserved against caller
replacement before execution.

## Pins and capacity

* engine address `0x4d432d4c48532d505245464c4947485431000001`;
  domain `MC-LINKED-HASH-SET-PREFLIGHT1` (all nine engine domain embeds replaced);
* engine 340269 bytes, SHA-256
  `2b82ce741d4c844648200e7fed3e9ac117912ea16aab9c6acc7ed9229c0dfdf1`,
  Keccak `1e3d315ea44034ff73f64e27d639839ebfe426cdfb0a88a0535301762d063ff7`;
* LOCAL384 cap 393216 bytes, leaving 52947 bytes. Accepted LOCAL320 remains
  untouched; no cap above384 was used;
* coordinator 3547 bytes, Keccak
  `2a4b08da4ac44367667439a7c1312711c9759a4adec42e610e2f30af2584f347`.

LOCAL1B calls, 30 seconds/call, 25M reserve, whole 20 minutes/4GiB, 24 raw/
262144 slices, 128 frames, CP4096, Code65535, heap/VFS1MiB and checkpoint Head
32768 stay fixed. The one persistent whole generated gate recorded an actual
process-tree RSS peak of 952131584 bytes in 239.565 seconds; it exited zero
under its 1200-second/4GiB monitor.

## Generated result

Java 8 trusted generated controls cover zero/reasonable capacity constructors,
growth, duplicate virtual equality, null, insertion order, two independent
iterators, `hasNext`, exhaustion/NSEE and derived `isEmpty`, while retaining the
existing native loader/Thread/PrivilegedAction/System/Properties/arraycopy
engine bytes. q1, q7 and direct-q4096 all finish with `VOID`, static sentinel
631 and identical machine root/opaque payload:

* 563 Java and 9 internal steps;
* q1 epoch563, q7 epoch81, direct epoch1;
* machine root `0x906b10cc5adc81743da72a7a36c365debb5c79309f376c53ea3c596a5a7dd489`;
* opaque SHA-256 `5aad42ec5c41dbadb0e61bb6d1adcdf5dbd222008d09f780b717acabf0bc11b7`.

Each world also executes an independent fresh-process `verify` reopen. The
archive has generated sources, Java8 class/zip bytes, compiler/oracle/driver
logs, all generated receipt reports and opaque checkpoints, artifact/pin
hashes, and an explicit prior-52-image identity report. It deliberately omits
Go binaries, LevelDB state, and original payloads.

Parent must independently rebuild this exact source and only then perform a
new original22 q7+q1 run from the recorded 1802J/16I frontier. The anticipated
later `getResources` member is explanatory only: it is not implemented here.

## Preserved development failures

Two pre-gate failures are retained under `logs/development-failures/`: a host
oracle fixture initially omitted `hashCode` (so JDK HashSet did not call its
`equals`), and an initial coordinator still pointed at the parent engine address
and honestly reverted `MR0Error(3)`. Both are fixed in the final whole gate;
these logs are not counted as positive evidence.
