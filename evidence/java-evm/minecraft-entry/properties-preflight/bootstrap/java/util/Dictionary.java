package java.util;

/** Minimal guest-Java Dictionary base retained only for Properties storage. */
public abstract class Dictionary<K, V> {
    public Dictionary() {}

    public abstract V get(Object key);
    public abstract V put(K key, V value);
    public abstract V remove(Object key);
    public abstract int size();
}
