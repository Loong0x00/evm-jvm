package java.util;

import java.io.Serializable;
import java.util.function.BiConsumer;
import java.util.function.BiFunction;
import java.util.function.Function;

/**
 * Java 8 HashMap's constructor/state subset for the LOCAL Minecraft profile.
 *
 * The instance fields preserve the JDK 8 declarations used by the default
 * constructor. HashMap() sets only loadFactor to DEFAULT_LOAD_FACTOR. In
 * particular, table remains null: JDK 8 defers allocation until the first put.
 * size/isEmpty are ordinary guest Java code. Other Map/Object/default methods
 * are explicit unbound native refusal points; no map behavior is fabricated.
 */
public class HashMap<K, V> extends AbstractMap<K, V>
        implements Map<K, V>, Cloneable, Serializable {
    private static final long serialVersionUID = 362498820763181265L;
    static final int DEFAULT_INITIAL_CAPACITY = 1 << 4;
    static final int MAXIMUM_CAPACITY = 1 << 30;
    static final float DEFAULT_LOAD_FACTOR = 0.75f;
    static final int TREEIFY_THRESHOLD = 8;
    static final int UNTREEIFY_THRESHOLD = 6;
    static final int MIN_TREEIFY_CAPACITY = 64;

    transient Node<K, V>[] table;
    transient Set<Map.Entry<K, V>> entrySet;
    transient int size;
    transient int modCount;
    int threshold;
    final float loadFactor;

    public HashMap() {
        this.loadFactor = DEFAULT_LOAD_FACTOR;
    }

    public int size() { return size; }
    public boolean isEmpty() { return size == 0; }

    // Concrete map operations remain explicitly typed native refusal points.
    public native boolean containsKey(Object key);
    public native boolean containsValue(Object value);
    public native V get(Object key);
    public native V put(K key, V value);
    public native void putAll(Map<? extends K, ? extends V> source);
    public native V remove(Object key);
    public native void clear();
    public native Set<K> keySet();
    public native Collection<V> values();
    public native Set<Map.Entry<K, V>> entrySet();

    @Override public native boolean equals(Object other);
    @Override public native int hashCode();
    @Override public native Object clone();

    @Override public native V getOrDefault(Object key, V defaultValue);
    @Override public native void forEach(BiConsumer<? super K, ? super V> action);
    @Override public native void replaceAll(BiFunction<? super K, ? super V, ? extends V> function);
    @Override public native V putIfAbsent(K key, V value);
    @Override public native boolean remove(Object key, Object value);
    @Override public native boolean replace(K key, V oldValue, V newValue);
    @Override public native V replace(K key, V value);
    @Override public native V computeIfAbsent(K key, Function<? super K, ? extends V> mappingFunction);
    @Override public native V computeIfPresent(K key, BiFunction<? super K, ? super V, ? extends V> remappingFunction);
    @Override public native V compute(K key, BiFunction<? super K, ? super V, ? extends V> remappingFunction);
    @Override public native V merge(K key, V value, BiFunction<? super V, ? super V, ? extends V> remappingFunction);

    // The descriptor keeps the genuine JDK 8 private table type. This source
    // declaration exists only so javac can emit HashMap's field descriptor;
    // Node is NOT one of this profile's 101 bootstrapped class images and is
    // unreachable from the supported default constructor/state methods.
    private static final class Node<K, V> { }
}
