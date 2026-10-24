import java.util.*;
import java.lang.reflect.Array;
/** Generated-only private-size based same-target ArrayList copies; no mutation admitted. */
public final class ParentArrayListTypedArray {
    static final class Liar extends ArrayList {
        public int size() { return 3; }
    }
    private static void check(boolean ok) { if (!ok) throw new ArithmeticException(); }
    public static void main(String[] args) {
        ArrayList[] lists = new ArrayList[] {new ArrayList(), new ArrayList(0), new ArrayList(3), new Liar()};
        check(lists[3].size() == 3);
        Object sentinel = new Object();
        for (int i=0; i<lists.length; i++) {
            Collection collection = lists[i];
            Object[] zero = new Object[0];
            check(collection.toArray(zero) == zero);
            Object[] oversized = new Object[] {sentinel, sentinel, sentinel};
            check(collection.toArray(oversized) == oversized);
            check(oversized[0] == null && oversized[1] == sentinel && oversized[2] == sentinel);
            Iterable[] iterable = (Iterable[]) Array.newInstance(Iterable.class, 0);
            check(((List) collection).toArray(iterable) == iterable);
            Map.Entry[] entries = new Map.Entry[0];
            check(collection.toArray(entries) == entries);
            String[] strings = new String[] {"tail", "tail"};
            check(collection.toArray(strings) == strings && strings[0] == null && strings[1].equals("tail"));
            try { collection.toArray((Object[]) null); throw new ArithmeticException(); }
            catch (NullPointerException expected) { }
            Iterator iterator = collection.iterator();
            check(!iterator.hasNext());
            try { iterator.next(); throw new ArithmeticException(); }
            catch (NoSuchElementException expected) { }
        }
        Object[] target = new Object[0];
        check(new HashMap().entrySet().toArray(target) == target);
        ListIterator[] markerArray = (ListIterator[]) Array.newInstance(ListIterator.class, 1);
        check(markerArray.length == 1 && markerArray[0] == null);
        java.util.function.Function[] functions = new java.util.function.Function[0];
        NavigableSet[] navigable = new NavigableSet[0];
        check(functions.length + navigable.length == 0);
    }
}
