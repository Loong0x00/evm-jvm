package java.util;
final class HashSetIterator<E> implements Iterator<E> {
    private HashSet<E> owner;
    private int cursor;
    HashSetIterator(HashSet<E> owner) { this.owner = owner; }
    public boolean hasNext() { return cursor < owner.used; }
    @SuppressWarnings("unchecked")
    public E next() {
        if (cursor >= owner.used) throw new NoSuchElementException();
        return (E) owner.elements[cursor++];
    }
}
