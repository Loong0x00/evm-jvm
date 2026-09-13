package java.util;
import java.io.Serializable;
public class HashSet<E> extends AbstractSet<E> implements Set<E>, Cloneable, Serializable {
    Object[] elements;
    int used;
    public HashSet() { this(4); }
    public HashSet(int capacity) {
        if (capacity < 0) throw new IllegalArgumentException();
        elements = new Object[capacity == 0 ? 1 : capacity];
    }
    private int find(Object item) {
        for (int i = 0; i < used; ++i) {
            Object old = elements[i];
            if (old == item || (item != null && item.equals(old))) return i;
        }
        return -1;
    }
    private void grow() {
        Object[] next = new Object[elements.length * 2];
        System.arraycopy(elements, 0, next, 0, used);
        elements = next;
    }
    public boolean add(E item) {
        if (find(item) >= 0) return false;
        if (used == elements.length) grow();
        elements[used++] = item;
        return true;
    }
    public int size() { return used; }
    public Iterator<E> iterator() { return new HashSetIterator<E>(this); }
}
