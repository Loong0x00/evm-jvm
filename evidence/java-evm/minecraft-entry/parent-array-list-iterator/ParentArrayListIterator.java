import java.util.*;
/** Generated-only real owner/cursor iterator witness; no list mutation admitted. */
public final class ParentArrayListIterator {
    static final class Liar extends ArrayList {
        public int size() { return 3; }
    }
    private static void check(boolean ok) { if (!ok) throw new ArithmeticException(); }
    public static void main(String[] args) {
        ArrayList[] lists = new ArrayList[] {new ArrayList(), new ArrayList(0), new ArrayList(3), new Liar()};
        check(lists[3].size() == 3);
        Iterator[] iterators = new Iterator[lists.length];
        for (int i=0; i<lists.length; i++) {
            Iterable iterable = lists[i];
            Iterator first = iterable.iterator();
            Iterator second = iterable.iterator();
            check(first != second && first instanceof Iterator);
            check(!first.hasNext() && !second.hasNext());
            try { first.next(); throw new ArithmeticException(); }
            catch (NoSuchElementException expected) { }
            check(!first.hasNext() && !second.hasNext());
            iterators[i] = first;
        }
        Iterator[] copy = iterators.clone();
        check(copy != iterators && copy[0] == iterators[0] && copy[3] == iterators[3]);
        // Retained bootstrap helpers must still occupy their actual old slots.
        Map<Object,Object> map = new HashMap<Object,Object>();
        Collection<Map.Entry<Object,Object>> entries = map.entrySet();
        Map.Entry[] target = new Map.Entry[0];
        check(entries.toArray(target) == target);
        java.util.function.Function[] functions = new java.util.function.Function[0];
        NavigableMap[] navigationMaps = new NavigableMap[0];
        Comparator[] comparators = new Comparator[0];
        SortedSet[] sorted = new SortedSet[0];
        check(navigationMaps.length + comparators.length + sorted.length == 0);
        NavigableSet[] navigable = new NavigableSet[0];
        check(functions.length + navigable.length == 0);
        try { ((Iterable) null).iterator(); throw new ArithmeticException(); }
        catch (NullPointerException expected) { }
        try { Iterator bad = (Iterator) new Object(); throw new ArithmeticException(); }
        catch (ClassCastException expected) { }
    }
}
