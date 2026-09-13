package java.util;
public interface Map<K,V> {
    V get(Object key);
    V put(K key, V value);
    int size();
    boolean isEmpty();
    void clear();
    boolean containsKey(Object key);
}
