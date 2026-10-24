package java.util;
public interface Collection<E> {
    int size();
    boolean add(E value);
    Iterator<E> iterator();
    <T> T[] toArray(T[] target);
}
