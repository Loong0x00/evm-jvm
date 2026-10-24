package java.util;

/** Cached live ordered view. Unbounded E keeps add(Object) an unbound refusal, without a casting bridge. */
final class LinkedHashMapEntrySet<E> extends AbstractSet<E> {
    private final LinkedHashMap owner;

    LinkedHashMapEntrySet(LinkedHashMap owner) { this.owner = owner; }

    // Actual inherited storage, never a subclass's public size()/isEmpty() override.
    public int size() { return owner.size; }
    public boolean isEmpty() { return owner.size == 0; }

    public Iterator<E> iterator() { return (Iterator<E>) new LinkedHashMapEntryIterator(owner); }

    public <T> T[] toArray(T[] target) {
        int length = target.length;
        int count = owner.size;
        if (length < count) refuseTypedToArrayTooSmall();
        Iterator cursor = iterator();
        int index = 0;
        while (cursor.hasNext()) target[index++] = (T) cursor.next();
        if (index < length) target[index] = null;
        return target;
    }

    private native void refuseTypedToArrayTooSmall();
    public native boolean add(E entry);
    public native boolean equals(Object other);
    public native int hashCode();
}
