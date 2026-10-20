package java.util;

import java.io.Serializable;

/**
 * Bounded Java 8 ArrayList constructor profile. The int constructor eagerly
 * owns real Object[] storage and leaves size at Java's zero default. The
 * native declarations exist only to make this concrete class close the
 * inherited Collection method set; the interpreter binds neither method, so
 * attempts to use add/iterator fail atomically rather than fabricate results.
 */
public class ArrayList extends AbstractList
        implements RandomAccess, Cloneable, Serializable {
    private transient Object[] elementData;
    private int size;

    public ArrayList(int initialCapacity) {
        super();
        if (initialCapacity < 0) throw new IllegalArgumentException();
        elementData = new Object[initialCapacity];
    }

    public int size() { return size; }

    public native boolean add(Object value);

    public native Iterator iterator();
}
