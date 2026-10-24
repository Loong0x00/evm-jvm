package java.util;

public interface Collection<E> extends Iterable<E> {
    boolean add(E value);
    <T> T[] toArray(T[] target);
    int size();
    Iterator<E> iterator();
    boolean isEmpty();
}
