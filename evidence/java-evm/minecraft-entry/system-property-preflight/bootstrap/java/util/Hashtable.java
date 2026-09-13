package java.util;

import java.io.Serializable;

/**
 * Deliberately bounded surface: a real, growable key/value store for the
 * Properties path. It is linear rather than a complete Java SE hash-table.
 */
public class Hashtable<K, V> extends Dictionary<K, V>
        implements Map<K, V>, Cloneable, Serializable {
    private Object[] keys;
    private Object[] values;
    private int used;

    public Hashtable() {
        keys = new Object[4];
        values = new Object[4];
    }

    private void requireKeyValue(Object key, Object value) {
        if (key == null || value == null) {
            throw new NullPointerException();
        }
    }

    private int find(Object key) {
        if (key == null) {
            throw new NullPointerException();
        }
        for (int i = 0; i < used; ++i) {
            Object prior = keys[i];
            if (prior == key || prior.equals(key)) {
                return i;
            }
        }
        return -1;
    }

    private void grow() {
        Object[] nextKeys = new Object[keys.length * 2];
        Object[] nextValues = new Object[values.length * 2];
        System.arraycopy(keys, 0, nextKeys, 0, used);
        System.arraycopy(values, 0, nextValues, 0, used);
        keys = nextKeys;
        values = nextValues;
    }

    public V get(Object key) {
        int at = find(key);
        return at < 0 ? null : (V) values[at];
    }

    public boolean containsKey(Object key) {
        return find(key) >= 0;
    }

    public V put(K key, V value) {
        requireKeyValue(key, value);
        int at = find(key);
        if (at >= 0) {
            V prior = (V) values[at];
            values[at] = value;
            return prior;
        }
        if (used == keys.length) {
            grow();
        }
        keys[used] = key;
        values[used] = value;
        ++used;
        return null;
    }

    public V remove(Object key) {
        int at = find(key);
        if (at < 0) {
            return null;
        }
        V prior = (V) values[at];
        int last = used - 1;
        keys[at] = keys[last];
        values[at] = values[last];
        keys[last] = null;
        values[last] = null;
        used = last;
        return prior;
    }

    public int size() {
        return used;
    }

    public boolean isEmpty() {
        return used == 0;
    }

    public void clear() {
        for (int i = 0; i < used; ++i) {
            keys[i] = null;
            values[i] = null;
        }
        used = 0;
    }
}
