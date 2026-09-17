package java.util;
public interface Collection<E> extends java.lang.Iterable<E> {
  boolean add(E value);
  int size();
  Iterator<E> iterator();
  boolean isEmpty();
}
