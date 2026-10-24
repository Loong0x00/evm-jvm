import java.util.*;
/** Generated-only hierarchy and inherited iterator dispatch witness. */
public final class ParentListIteratorLink {
    interface Tagged extends ListIterator<Object> { int value(); }
    static final class Empty implements Tagged {
        final int captured;
        Empty(int captured) { this.captured = captured; }
        public int value() { return captured; }
        public boolean hasNext() { return false; }
        public Object next() { throw new NoSuchElementException(); }
        public boolean hasPrevious() { return false; }
        public Object previous() { throw new NoSuchElementException(); }
        public int nextIndex() { return 0; }
        public int previousIndex() { return -1; }
        public void remove() { throw new UnsupportedOperationException(); }
        public void set(Object value) { throw new UnsupportedOperationException(); }
        public void add(Object value) { throw new UnsupportedOperationException(); }
    }
    private static void check(boolean ok) { if (!ok) throw new ArithmeticException(); }
    public static void main(String[] args) {
        // Retain old tail class identities, not merely the new marker's slot.
        java.util.function.Function[] functions = new java.util.function.Function[0];
        NavigableMap[] maps = new NavigableMap[0];
        Comparator[] comparators = new Comparator[0];
        SortedSet[] sorted = new SortedSet[0];
        NavigableSet[] navigable = new NavigableSet[0];
        check(functions.length + maps.length + comparators.length + sorted.length + navigable.length == 0);
        Map<Object,Object> map = new HashMap<Object,Object>();
        Collection<Map.Entry<Object,Object>> entries = map.entrySet();
        Map.Entry[] target = new Map.Entry[0];
        check(entries.toArray(target) == target && entries.isEmpty());
        Tagged tagged = new Empty(23);
        Object object = tagged;
        check(object instanceof ListIterator && object instanceof Iterator);
        check(((Tagged) object).value() == 23);
        ListIterator<Object> iterator = (ListIterator<Object>) object;
        check(!iterator.hasNext() && !((Iterator<Object>) object).hasNext());
        try { iterator.next(); throw new ArithmeticException(); }
        catch (NoSuchElementException expected) { }
        ListIterator[] array = new ListIterator[] {iterator};
        ListIterator[] copy = array.clone();
        check(copy != array && copy[0] == iterator);
        try { ListIterator bad = (ListIterator) new Object(); throw new ArithmeticException(); }
        catch (ClassCastException expected) { }
        try { ((ListIterator) null).hasNext(); throw new ArithmeticException(); }
        catch (NullPointerException expected) { }
    }
}
