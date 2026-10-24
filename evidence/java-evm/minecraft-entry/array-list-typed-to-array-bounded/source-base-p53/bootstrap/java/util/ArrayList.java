package java.util;

import java.io.Serializable;

/** Bounded Java 8 ArrayList constructor plus ordinary owner/cursor iterator. */
public class ArrayList extends AbstractList
        implements RandomAccess, Cloneable, Serializable {
    private static final Object[] DEFAULTCAPACITY_EMPTY_ELEMENTDATA = new Object[0];
    private transient Object[] elementData;
    private int size;

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

    public native boolean add(Object value);

    public Iterator iterator() { return new Itr(this); }

    private static final class Itr implements Iterator {
        private final ArrayList owner;
        private int cursor;

        Itr(ArrayList owner) {
            this.owner = owner;
        }

        public boolean hasNext() { return cursor < owner.size; }

        public Object next() {
            if (cursor >= owner.size) throw new NoSuchElementException();
            return owner.elementData[cursor++];
        }

        public native void remove();
    }
}
