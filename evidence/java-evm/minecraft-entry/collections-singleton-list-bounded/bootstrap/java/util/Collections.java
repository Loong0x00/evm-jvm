package java.util;

public class Collections {
    private Collections() { }

    @SuppressWarnings("unchecked")
    public static <T> List<T> singletonList(T element) {
        return (List<T>) new SingletonList(element);
    }

    static final class SingletonList extends AbstractList implements RandomAccess, java.io.Serializable {
        private final Object element;

        SingletonList(Object element) { this.element = element; }

        public int size() { return 1; }

        public Iterator iterator() { return new SingletonIterator(element); }

        // Collection.add is abstract; an explicit unresolved native declaration
        // prevents AME or a fabricated mutation result for this immutable list.
        public native boolean add(Object value);
    }

    static final class SingletonIterator implements Iterator {
        private final Object element;
        private boolean available;

        SingletonIterator(Object element) {
            this.element = element;
            this.available = true;
        }

        public boolean hasNext() { return available; }

        public Object next() {
            if (!available) throw new NoSuchElementException();
            available = false;
            return element;
        }

        public native void remove();
    }
}
