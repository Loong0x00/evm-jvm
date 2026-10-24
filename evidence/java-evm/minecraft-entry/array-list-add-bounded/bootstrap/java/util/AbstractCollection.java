package java.util;

public abstract class AbstractCollection<E> implements Collection<E> {
    protected AbstractCollection() { }
    // Keep unsupported inherited typed-array APIs as raw profile refusals.
    public native <T> T[] toArray(T[] target);
    public boolean isEmpty() { return size() == 0; }
}
