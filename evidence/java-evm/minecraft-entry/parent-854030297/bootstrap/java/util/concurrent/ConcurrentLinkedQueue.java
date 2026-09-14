package java.util.concurrent;

import java.io.Serializable;
import java.util.AbstractCollection;
import java.util.Iterator;
import java.util.Queue;

public class ConcurrentLinkedQueue<E> extends AbstractCollection<E>
        implements Queue<E>, Serializable {
    private Object[] elements;

    public ConcurrentLinkedQueue() {
        elements = new Object[0];
    }

    public boolean add(E e) {
        if (e == null) throw new NullPointerException();
        Object[] old = elements;
        Object[] next = new Object[old.length + 1];
        for (int i = 0; i < old.length; ++i) next[i] = old[i];
        next[old.length] = e;
        elements = next;
        return true;
    }

    @SuppressWarnings("unchecked")
    public E poll() {
        Object[] old = elements;
        if (old.length == 0) return null;
        E value = (E) old[0];
        Object[] next = new Object[old.length - 1];
        for (int i = 1; i < old.length; ++i) next[i - 1] = old[i];
        elements = next;
        return value;
    }

    public int size() { return elements.length; }

    public Iterator<E> iterator() {
        return new CopyOnWriteArrayListIterator<E>(elements);
    }
}
