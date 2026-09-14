# Bounded `CopyOnWriteArrayList` bootstrap preflight

Basis: accepted `Class.newInstance()` source/evidence at `e742f0b38`. This is a fresh
LOCAL384 source profile, `MC-COPY-ON-WRITE-ARRAY-LIST-PREFLIGHT1`; it is not an
acceptance, original-artifact execution, Minecraft startup, world, or `Done` claim.

The immutable Java 8 bootstrap tail appends exactly four images at indexes 71--74:
`List`, `RandomAccess`, `CopyOnWriteArrayList`, and its package-private snapshot
iterator. The list extends the accepted `AbstractCollection` and implements the accepted
`Collection` through `List`; it also declares `RandomAccess`, `Cloneable`, and
`Serializable`. Its only supplied surface is `()V`, `add(Object)`, `size()`,
`iterator()`, plus inherited `isEmpty()`. `add` always creates a new `Object[]`, copies
all prior values, stores the new value, and permits duplicates and null. The iterator owns
that array snapshot and raises the existing `NoSuchElementException` on exhaustion.
There are no locks, host concurrency, or broader List/COW APIs.

`tools/verify_source.py` uses Java 8 `javac -g:none` against an rt.jar stripped of every
replacement. It verifies the 71 prior embedded bootstrap images are byte-identical,
rebuilds the four appended images, and reverses the allowed domain/append/reservation
edits to require exact equality with the accepted `Class.newInstance` source. It also
pins raw25/262144, bootstrap75, exception14, global-native11, String-local10,
frames128, CP4096, Code65535, heap/VFS/checkpoint1MiB, Head32768, LOCAL1B/25M reserve
and LOCAL384 cap. `tools/build.py` builds a clean ignored tree only.

The source tree deliberately contains no original Minecraft JAR/class/resource/page,
world/LevelDB, generated binary, or host Java execution route. Generated fixtures and
run evidence belong in a later evidence-only commit.
