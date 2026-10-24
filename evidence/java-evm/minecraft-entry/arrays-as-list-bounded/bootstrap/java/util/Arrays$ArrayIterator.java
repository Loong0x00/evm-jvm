package java.util;

/** Fresh cursor over the actual caller-owned array, never a snapshot. */
final class Arrays$ArrayIterator implements Iterator {
    private final Object[] array;
    private int cursor;

    Arrays$ArrayIterator(Object[] array) {
        this.array = array;
    }

    public boolean hasNext() {
        return cursor < array.length;
    }

    public Object next() {
        if (!hasNext()) throw new NoSuchElementException();
        return array[cursor++];
    }

    // Outside the traversal profile; keep it an honest unresolved native.
    public native void remove();
}
