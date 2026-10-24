package java.util;

import java.io.Serializable;

/** Bounded Java 8 ArrayList constructors, append, and fail-fast owner/cursor iterator. */
public class ArrayList extends AbstractList
        implements RandomAccess, Cloneable, Serializable {
    private static final Object[] DEFAULTCAPACITY_EMPTY_ELEMENTDATA = new Object[0];
    private transient Object[] elementData;
    private int size;
    private int modCount;

    public ArrayList() {
        super();
        elementData = DEFAULTCAPACITY_EMPTY_ELEMENTDATA;
    }

    public ArrayList(int initialCapacity) {
        super();
        if (initialCapacity < 0) throw new IllegalArgumentException();
        elementData = new Object[initialCapacity];
    }

    public int size() { return size; }

    // Avoid AbstractCollection's virtual size() call for subclasses that lie.
    public boolean isEmpty() { return size == 0; }

    /** Bounded ordinary typed-target copy; other list mutations remain unbound. */
    public Object[] toArray(Object[] target) {
        int count = size;
        int capacity = target.length;
        if (capacity < count) rejectShortTarget();
        for (int i = 0; i < count; i++) target[i] = elementData[i];
        if (capacity > count) target[count] = null;
        return target;
    }

    // Deliberately unbound: an undersized target is outside this measured profile.
    private native void rejectShortTarget();

    public boolean add(Object value) {
        ensureCapacityInternal(size + 1);
        elementData[size] = value;
        size++;
        return true;
    }

    private void ensureCapacityInternal(int minCapacity) {
        if (elementData == DEFAULTCAPACITY_EMPTY_ELEMENTDATA) {
            if (minCapacity < 10) minCapacity = 10;
        }
        modCount++;
        if (minCapacity > elementData.length) grow(minCapacity);
    }

    private void grow(int minCapacity) {
        int oldCapacity = elementData.length;
        int newCapacity = oldCapacity + (oldCapacity >> 1);
        if (newCapacity < minCapacity) newCapacity = minCapacity;
        Object[] oldData = elementData;
        Object[] newData = new Object[newCapacity];
        for (int i = 0; i < size; i++) newData[i] = oldData[i];
        elementData = newData;
    }

    public Iterator iterator() { return new Itr(this); }

    private static final class Itr implements Iterator {
        private final ArrayList owner;
        private int cursor;
        private int expectedModCount;

        Itr(ArrayList owner) {
            this.owner = owner;
            this.expectedModCount = owner.modCount;
        }

        public boolean hasNext() { return cursor < owner.size; }

        public Object next() {
            if (expectedModCount != owner.modCount)
                throw new ConcurrentModificationException();
            if (cursor >= owner.size) throw new NoSuchElementException();
            return owner.elementData[cursor++];
        }

        public native void remove();
    }
}
