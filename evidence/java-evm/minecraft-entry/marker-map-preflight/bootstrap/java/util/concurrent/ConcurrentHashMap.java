package java.util.concurrent;
import java.io.Serializable;
import java.util.AbstractMap;
/** Linear single-guest-thread map substrate, not a concurrency implementation. */
public class ConcurrentHashMap<K,V> extends AbstractMap<K,V>
        implements ConcurrentMap<K,V>, Serializable {
    private Object[] keys;
    private Object[] values;
    private int used;
    public ConcurrentHashMap() { keys = new Object[4]; values = new Object[4]; }
    private void check(Object key, Object value) {
        if (key == null || value == null) throw new NullPointerException();
    }
    private int find(Object key) {
        for (int i = 0; i < used; i++) if (keys[i].equals(key)) return i;
        return -1;
    }
    private void grow() {
        Object[] nk = new Object[keys.length << 1];
        Object[] nv = new Object[values.length << 1];
        for (int i = 0; i < used; i++) { nk[i] = keys[i]; nv[i] = values[i]; }
        keys = nk; values = nv;
    }
    public V get(Object key) {
        if (key == null) throw new NullPointerException();
        int i = find(key); return i < 0 ? null : (V) values[i];
    }
    public boolean containsKey(Object key) {
        if (key == null) throw new NullPointerException();
        return find(key) >= 0;
    }
    public V putIfAbsent(K key, V value) {
        check(key, value); int i = find(key);
        if (i >= 0) return (V) values[i];
        if (used == keys.length) grow();
        keys[used] = key; values[used++] = value; return null;
    }
    public V put(K key, V value) {
        check(key, value); int i = find(key);
        if (i >= 0) { V old = (V) values[i]; values[i] = value; return old; }
        if (used == keys.length) grow();
        keys[used] = key; values[used++] = value; return null;
    }
    public int size() { return used; }
    public boolean isEmpty() { return used == 0; }
    public void clear() { keys = new Object[4]; values = new Object[4]; used = 0; }
}
