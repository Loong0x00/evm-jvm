package java.util;
public interface Map<K,V> {
    V get(Object key);
    V put(K key, V value);
    int size();
    boolean isEmpty();
    void clear();
    boolean containsKey(Object key);
    Set<Map.Entry<K,V>> entrySet();
    // Compile-time nested declaration only. The engine retains its accepted
    // independently built Map$Entry image byte-for-byte.
    interface Entry<K,V> {
        K getKey(); V getValue(); V setValue(V value);
        boolean equals(Object other); int hashCode();
    }
}
