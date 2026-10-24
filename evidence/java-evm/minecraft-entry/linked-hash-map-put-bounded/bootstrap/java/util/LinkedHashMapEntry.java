package java.util;

/** Genuine insertion-order Map.Entry used only by the bounded LinkedHashMap backend. */
final class LinkedHashMapEntry<K, V> implements Map.Entry<K, V> {
    final int hash;
    final K key;
    V value;
    LinkedHashMapEntry<K, V> next;

    LinkedHashMapEntry(int hash, K key, V value) {
        this.hash = hash;
        this.key = key;
        this.value = value;
    }

    public K getKey() { return key; }
    public V getValue() { return value; }

    /** Value replacement is non-structural and preserves this entry alias. */
    public V setValue(V newValue) {
        V oldValue = value;
        value = newValue;
        return oldValue;
    }

    public int hashCode() {
        int keyHash = key == null ? 0 : key.hashCode();
        int valueHash = value == null ? 0 : value.hashCode();
        return keyHash ^ valueHash;
    }

    /** Entry equality is outside this bounded profile. */
    public native boolean equals(Object other);
}
