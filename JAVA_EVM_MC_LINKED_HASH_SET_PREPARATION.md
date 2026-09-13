# Next measured platform collection: LinkedHashSet result path

Parent system-loader getter commits original22 to1802J/16I. Exact next q1 error is
`MCEntryMissingClass(4104,36,java/util/LinkedHashSet)` at
LoaderUtil.findUrlResources `new LinkedHashSet()` PC36. Later already-inspected
original bytecode also needs LinkedHashSet(int), Collection.add/size/iterator and
Iterator.hasNext/next to transform URL resources. No resource API has run yet.

Create a bounded genuine guest-Java ordered-set family with actual Java8 hierarchy:

* Iterator<E>: hasNext,next;
* Collection<E>: only add,size,iterator (and isEmpty if useful);
* Set<E> extends Collection<E>;
* AbstractCollection<E> implements Collection<E> with only derived/abstract surface;
* AbstractSet<E> extends AbstractCollection<E> implements Set<E>;
* HashSet<E> extends AbstractSet<E>, Cloneable, Serializable;
* LinkedHashSet<E> extends HashSet<E>, exact no-arg and int-capacity constructors;
* private/package iterator implementation class and genuine NoSuchElementException
  if required for exhausted next.

HashSet may use bounded growable Object[] linear storage with existing virtual
equality and System.arraycopy. It must allow one null, reject duplicates, preserve
insertion order for LinkedHashSet iteration, return correct size and independent
iterator cursor objects. This is not hash-performance/concurrency/full Collections.
Unsupported remove/containsAll/toArray/spliterator APIs remain honest.

Append after prior52 images, preserve all existing bytes/order/native bindings,
reserve every owned collection class/interface/iterator helper against caller
replacement. New engine/address/all-nine domains/store/pins and new worlds. Do not
fake empty sets or ClassLoader resources.

Use existing LOCAL384KiB because current runtime328695B exceeds accepted320; first
record exact new runtime against384. Do not raise beyond384 without an actual
failure. Accepted320 unchanged. LOCAL1B/30s/25Mreserve/20min4GiB,24/262144,
128frames,CP4096Code65535heap/VFS/1MiBCP/32768BHead remain.

Generated noarg/int constructors, duplicate/null/object equality, insertion order,
multiple iterator cursors, exhausted next exception and prior loader/Thread/
PrivilegedAction/System/Properties/arraycopy controls; q1/q7/direct/reopen/canonical
machine equality. Caller replacement and unsupported methods refuse. Worker uses
no original artifacts. Parent independently builds then NEW original22 q7+q1;
expected later getResources is explanatory, not permission to implement it now.
No failed-state recovery, accepted/core/ABI/Makefile/settings/push/Done.
DefaultTerra/high, one semantic writer, absolute fresh TMPDIR/true whole peak.
