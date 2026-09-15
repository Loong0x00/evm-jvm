package java.util.concurrent;

import java.io.Serializable;
import java.lang.Cloneable;
import java.util.AbstractCollection;
import java.util.Iterator;
import java.util.List;
import java.util.RandomAccess;

public class CopyOnWriteArrayList<E> extends AbstractCollection<E>
        implements List<E>, RandomAccess, Cloneable, Serializable {
    private Object[] elements;

    public CopyOnWriteArrayList() {
        elements = new Object[0];
    }

    public boolean add(E e) {
        Object[] old = elements;
        Object[] next = new Object[old.length + 1];
        for (int i = 0; i < old.length; ++i) next[i] = old[i];
        next[old.length] = e;
        elements = next;
        return true;
    }

    public int size() { return elements.length; }

    public Iterator<E> iterator() {
        return new CopyOnWriteArrayListIterator<E>(elements);
    }
}
