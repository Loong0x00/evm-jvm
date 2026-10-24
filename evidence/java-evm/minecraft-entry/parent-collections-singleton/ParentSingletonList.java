import java.util.*;
import java.io.Serializable;
import java.lang.reflect.Array;
/** Generated-only genuine one-element list/independent iterator witness. */
public final class ParentSingletonList {
    private static void check(boolean ok) { if (!ok) throw new ArithmeticException(); }
    public static void main(String[] args) {
        Object[] empty = new Object[0];
        List<Object[]> list = Collections.singletonList(empty);
        check(list.size() == 1 && !list.isEmpty());
        check(list instanceof RandomAccess && list instanceof Serializable);
        check(list != Collections.singletonList(empty));
        Iterable<Object[]> iterable = list;
        Iterator<Object[]> first = iterable.iterator();
        Iterator<Object[]> second = iterable.iterator();
        check(first != second && first.hasNext() && second.hasNext());
        check(first.next() == empty && !first.hasNext() && second.hasNext());
        try { first.next(); throw new ArithmeticException(); }
        catch (NoSuchElementException expected) { }
        check(second.next() == empty && !second.hasNext());
        Iterator<Object> withNull = Collections.singletonList((Object) null).iterator();
        check(withNull.hasNext() && withNull.next() == null && !withNull.hasNext());
        try { withNull.next(); throw new ArithmeticException(); }
        catch (NoSuchElementException expected) { }
        Object value = new Object();
        List<Object> withValue = Collections.singletonList(value);
        check(withValue.size() == 1 && withValue.iterator().next() == value);
        Iterable[] reflected = (Iterable[]) Array.newInstance(Iterable.class, 0);
        check(Collections.singletonList(reflected).iterator().next() == reflected);
        Object[] target = new Object[0];
        check(new ArrayList().toArray(target) == target);
        check(new HashMap().entrySet().toArray(target) == target);
        java.util.function.Function[] functions = new java.util.function.Function[0];
        NavigableSet[] navigable = new NavigableSet[0];
        check(functions.length + navigable.length == 0);
        try { ((List) null).iterator(); throw new ArithmeticException(); }
        catch (NullPointerException expected) { }
        try { List bad = (List) new Object(); throw new ArithmeticException(); }
        catch (ClassCastException expected) { }
    }
}
