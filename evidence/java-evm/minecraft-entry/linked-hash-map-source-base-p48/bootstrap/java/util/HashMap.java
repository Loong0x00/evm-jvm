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
 * size/isEmpty/put are ordinary guest Java code. Unsupported Map/Object/default
 * methods remain explicit unbound native refusal points.
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
    // Deliberately unbound: interpreter/profile refusal, never a guest exception.
    private native void refuseTreeification();
    public native boolean containsKey(Object key);
    public native boolean containsValue(Object value);
    public native V get(Object key);
    public V put(K key, V value) {
        return putVal(key == null ? 0 : spread(key.hashCode()), key, value);
    }

    private static int spread(int hash) { return hash ^ (hash >>> 16); }

    private V putVal(int hash, K key, V value) {
        Node<K, V>[] tab = table;
        int n = tab == null ? 0 : tab.length;
        if (n == 0) {
            n = 16;
            tab = (Node<K, V>[]) new Node[n];
            table = tab;
            threshold = 12;
        }
        int index = (n - 1) & hash;
        Node<K, V> first = tab[index];
        if (first == null) {
            tab[index] = new Node<K, V>(hash, key, value, null);
        } else {
            Node<K, V> node = first;
            int binCount = 0;
            for (;;) {
                if (node.hash == hash && (node.key == key || (key != null && key.equals(node.key)))) {
                    V old = node.value;
                    node.value = value;
                    return old;
                }
                Node<K, V> next = node.next;
                if (next == null) {
                    if (binCount >= TREEIFY_THRESHOLD - 1 && n >= MIN_TREEIFY_CAPACITY)
                        refuseTreeification(); // refuse before mutating a bin requiring treeification
                    node.next = new Node<K, V>(hash, key, value, null);
                    break;
                }
                node = next;
                binCount++;
            }
            if (binCount >= TREEIFY_THRESHOLD - 1 && n < MIN_TREEIFY_CAPACITY) resize();
        }
        modCount++;
        if (++size > threshold) resize();
        return null;
    }

    private void resize() {
        Node<K, V>[] oldTab = table;
        int oldCap = oldTab == null ? 0 : oldTab.length;
        int oldThr = threshold;
        int newCap;
        int newThr = 0;
        if (oldCap > 0) {
            if (oldCap >= MAXIMUM_CAPACITY) {
                threshold = Integer.MAX_VALUE;
                return;
            }
            newCap = oldCap << 1;
            if (newCap < MAXIMUM_CAPACITY && oldCap >= DEFAULT_INITIAL_CAPACITY)
                newThr = oldThr << 1;
        } else if (oldThr > 0) {
            newCap = oldThr;
        } else {
            newCap = DEFAULT_INITIAL_CAPACITY;
            newThr = (int) (DEFAULT_LOAD_FACTOR * DEFAULT_INITIAL_CAPACITY);
        }
        if (newThr == 0) {
            float ft = (float) newCap * loadFactor;
            newThr = newCap < MAXIMUM_CAPACITY && ft < (float) MAXIMUM_CAPACITY
                    ? (int) ft : Integer.MAX_VALUE;
        }
        threshold = newThr;
        Node<K, V>[] newTab = (Node<K, V>[]) new Node[newCap];
        table = newTab;
        if (oldTab != null) {
            for (int i = 0; i < oldCap; i++) {
                Node<K, V> node = oldTab[i];
                if (node == null) continue;
                oldTab[i] = null;
                if (node.next == null) newTab[node.hash & (newCap - 1)] = node;
                else {
                    Node<K, V> loHead = null, loTail = null, hiHead = null, hiTail = null;
                    while (node != null) {
                        Node<K, V> next = node.next;
                        node.next = null;
                        if ((node.hash & oldCap) == 0) {
                            if (loTail == null) loHead = node; else loTail.next = node;
                            loTail = node;
                        } else {
                            if (hiTail == null) hiHead = node; else hiTail.next = node;
                            hiTail = node;
                        }
                        node = next;
                    }
                    newTab[i] = loHead;
                    newTab[i + oldCap] = hiHead;
                }
            }
        }
    }
    public native void putAll(Map<? extends K, ? extends V> source);
    public native V remove(Object key);
    public native void clear();
    public native Set<K> keySet();
    public native Collection<V> values();
    public Set<Map.Entry<K, V>> entrySet() {
        Set<Map.Entry<K, V>> view = entrySet;
        if (view == null) entrySet = view = new EntrySet<Map.Entry<K, V>>();
        return view;
    }

    /** A cached, live view over this map; mutation surfaces stay unbound. */
    private final class EntrySet<E> extends AbstractSet<E> {
        EntrySet() { }
        public int size() { return HashMap.this.size; }
        public boolean isEmpty() { return HashMap.this.size == 0; }
        @SuppressWarnings("unchecked")
        public Iterator<E> iterator() { return (Iterator<E>) new EntryIterator(); }
        public native boolean add(E entry);
        public native boolean addAll(Collection<? extends E> values);
        public native boolean contains(Object value);
        public native boolean containsAll(Collection<?> values);
        public native boolean remove(Object value);
        public native boolean removeAll(Collection<?> values);
        public native boolean retainAll(Collection<?> values);
        public native void clear();
        public native Object[] toArray();
        private native void refuseTypedToArrayTooSmall();
        @SuppressWarnings("unchecked")
        public <T> T[] toArray(T[] target) {
            int length = target.length;
            int count = size();
            if (length < count) refuseTypedToArrayTooSmall();
            Iterator<E> iterator = iterator();
            int index = 0;
            while (iterator.hasNext()) target[index++] = (T) iterator.next();
            if (index < length) target[index] = null;
            return target;
        }
        public native boolean equals(Object other);
        public native int hashCode();
        public native void forEach(java.util.function.Consumer<? super E> action);
        public native boolean removeIf(java.util.function.Predicate<? super E> filter);
        public native java.util.Spliterator<E> spliterator();
        public native java.util.stream.Stream<E> stream();
        public native java.util.stream.Stream<E> parallelStream();
    }

    /** Java 8 HashIterator traversal and fail-fast next() behavior. */
    private final class EntryIterator implements Iterator<Map.Entry<K, V>> {
        private Node<K, V> next;
        private int index;
        private int expectedModCount;

        EntryIterator() {
            expectedModCount = modCount;
            Node<K, V>[] tab = table;
            if (tab != null && size > 0) {
                while (index < tab.length && (next = tab[index++]) == null) { }
            }
        }

        public boolean hasNext() { return next != null; }

        public Map.Entry<K, V> next() {
            if (modCount != expectedModCount) throw new ConcurrentModificationException();
            Node<K, V> current = next;
            if (current == null) throw new NoSuchElementException();
            next = current.next;
            if (next == null) {
                Node<K, V>[] tab = table;
                while (index < tab.length && (next = tab[index++]) == null) { }
            }
            return current;
        }

        public native void remove();
    }

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

    private static final class Node<K, V> implements Map.Entry<K, V> {
        final int hash;
        final K key;
        V value;
        Node<K, V> next;

        Node(int hash, K key, V value, Node<K, V> next) {
            this.hash = hash;
            this.key = key;
            this.value = value;
            this.next = next;
        }
        public K getKey() { return key; }
        public V getValue() { return value; }
        public V setValue(V newValue) {
            V old = value;
            value = newValue;
            return old;
        }
        public boolean equals(Object other) {
            if (other == this) return true;
            if (!(other instanceof Map.Entry)) return false;
            Map.Entry<?, ?> entry = (Map.Entry<?, ?>) other;
            Object otherKey = entry.getKey();
            Object otherValue = entry.getValue();
            return (key == null ? otherKey == null : key.equals(otherKey))
                    && (value == null ? otherValue == null : value.equals(otherValue));
        }
        public int hashCode() {
            return (key == null ? 0 : key.hashCode()) ^ (value == null ? 0 : value.hashCode());
        }
    }
}
