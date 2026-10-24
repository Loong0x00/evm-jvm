package java.util;

/** Independent fail-fast cursor over a LinkedHashMap's insertion-order chain. */
final class LinkedHashMapEntryIterator<K, V> implements Iterator<Map.Entry<K, V>> {
    private final LinkedHashMap<K, V> owner;
    private LinkedHashMapEntry<K, V> next;
    private final int expectedModCount;

    LinkedHashMapEntryIterator(LinkedHashMap<K, V> owner) {
        this.owner = owner;
        this.next = owner.firstEntry();
        this.expectedModCount = owner.modCount;
    }

    public boolean hasNext() { return next != null; }

    public Map.Entry<K, V> next() {
        if (owner.modCount != expectedModCount)
            throw new ConcurrentModificationException();
        LinkedHashMapEntry<K, V> current = next;
        if (current == null) throw new NoSuchElementException();
        next = current.next;
        return current;
    }

    public native void remove();
}
