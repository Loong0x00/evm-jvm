package java.util;
public abstract class AbstractCollection<E> implements Collection<E> {
    protected AbstractCollection() { }
    public boolean isEmpty() { return size() == 0; }
}
