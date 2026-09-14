package java.util.concurrent;

import java.util.Iterator;
import java.util.NoSuchElementException;

class CopyOnWriteArrayListIterator<E> implements Iterator<E> {
    private Object[] snapshot;
    private int cursor;

    CopyOnWriteArrayListIterator(Object[] snapshot) {
        this.snapshot = snapshot;
    }

    public boolean hasNext() { return cursor < snapshot.length; }

    @SuppressWarnings("unchecked")
    public E next() {
        if (!hasNext()) throw new NoSuchElementException();
        return (E) snapshot[cursor++];
    }
}
