package java.util;

import java.io.Serializable;
import java.util.function.BiConsumer;
import java.util.function.BiFunction;
import java.util.function.Function;

/**
 * Java 8 IdentityHashMap constructor subset for the LOCAL Minecraft bootstrap.
 * The int constructor owns the genuine eagerly allocated Object[] table. Only
 * size/isEmpty are executable; map operations are refusal-only native methods.
 */
public class IdentityHashMap<K, V> extends AbstractMap<K, V>
        implements Map<K, V>, Cloneable, Serializable {
    transient Object[] table;
    int size;

    public IdentityHashMap(int expectedMaxSize) {
        super();
        if (expectedMaxSize < 0) throw new IllegalArgumentException();
        init(capacity(expectedMaxSize));
    }

    private static int capacity(int expectedMaxSize) {
        if (expectedMaxSize > 178956970) return 536870912;
        if (expectedMaxSize <= 2) return 4;
        return Integer.highestOneBit(expectedMaxSize + (expectedMaxSize << 1));
    }

    private void init(int capacity) {
        table = new Object[2 * capacity];
    }

    public int size() { return size; }
    public boolean isEmpty() { return size == 0; }

    // Map operations remain explicit, typed refusals. In particular equals and
    // hashCode must not fall through to Object identity semantics.
    public native boolean containsKey(Object key);
    public native boolean containsValue(Object value);
    public native V get(Object key);
    public native V put(K key, V value);
    public native V remove(Object key);
    public native void putAll(Map<? extends K, ? extends V> source);
    public native void clear();
    public native Set<K> keySet();
    public native Collection<V> values();
    public native Set<Map.Entry<K, V>> entrySet();

    @Override public native boolean equals(Object other);
    @Override public native int hashCode();
    @Override public native String toString();
    @Override public native Object clone();

    // Java 8 Map default methods are also refusal-only when referenced through
    // the concrete class; the bounded bootstrap does not execute their bodies.
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
}
