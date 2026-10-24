package java.util;

/** The measured Java 8 Arrays.asList factory only. */
public final class Arrays {
    private Arrays() { }

    @SafeVarargs
    public static <T> List asList(T... array) {
        return new ArrayList(array);
    }

    /** Genuine fixed-size, live array-backed holder for the bounded profile. */
    private static final class ArrayList extends AbstractList
            implements RandomAccess, java.io.Serializable {
        private final Object[] array;

        ArrayList(Object[] array) {
            if (array == null) throw new NullPointerException();
            this.array = array;
        }

        public int size() {
            return array.length;
        }

        public Iterator iterator() {
            return new Arrays$ArrayIterator(array);
        }

        // Explicit erased override avoids inheriting Collection's abstract add.
        public native boolean add(Object value);
    }
}
