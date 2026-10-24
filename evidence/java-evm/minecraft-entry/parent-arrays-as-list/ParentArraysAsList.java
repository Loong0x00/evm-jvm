import java.util.*;
import java.io.Serializable;
import java.lang.reflect.Array;
/** Generated-only fixed-size live array-backed traversal witness. */
public final class ParentArraysAsList {
    private static void check(boolean ok) { if (!ok) throw new ArithmeticException(); }
    public static void main(String[] args) {
        Object first = new Object();
        Object second = new Object();
        Object[] backing = new Object[] {first, null};
        List<Object> list = Arrays.asList(backing);
        check(list.size() == 2 && !list.isEmpty());
        check(list instanceof RandomAccess && list instanceof Serializable);
        check(list != Arrays.asList(backing));
        Iterator<Object> one = list.iterator();
        Iterator<Object> two = list.iterator();
        check(one != two && one.hasNext() && two.hasNext());
        backing[0] = second;
        check(one.next() == second && two.next() == second);
        backing[1] = first;
        check(one.next() == first && !one.hasNext() && two.hasNext());
        check(two.next() == first && !two.hasNext());
        try { one.next(); throw new ArithmeticException(); }
        catch (NoSuchElementException expected) { }
        List<Object> empty = Arrays.asList(new Object[0]);
        check(empty.size() == 0 && empty.isEmpty() && !empty.iterator().hasNext());
        check(Collections.singletonList(new Object[0]).size() == 1);
        Iterator<Object> nullElement = Arrays.asList((Object) null).iterator();
        check(nullElement.hasNext() && nullElement.next() == null && !nullElement.hasNext());
        String[] strings = new String[] {"x", "y"};
        List<String> stringList = Arrays.asList(strings);
        strings[0] = "z";
        check(stringList.iterator().next().equals("z"));
        Iterable[] interfaces = (Iterable[]) Array.newInstance(Iterable.class, 2);
        List<Iterable> interfaceList = Arrays.asList(interfaces);
        List<Object> singleton = Collections.singletonList(first);
        interfaces[0] = singleton;
        check(interfaceList.iterator().next() == singleton);
        Object[] target = new Object[0];
        check(new ArrayList().toArray(target) == target && new HashMap().entrySet().toArray(target) == target);
        java.util.function.Function[] functions = new java.util.function.Function[0];
        NavigableSet[] navigable = new NavigableSet[0];
        check(functions.length + navigable.length == 0);
        try { Arrays.asList((Object[]) null); throw new ArithmeticException(); }
        catch (NullPointerException expected) { }
        try { ((List) null).iterator(); throw new ArithmeticException(); }
        catch (NullPointerException expected) { }
        try { List bad = (List) new Object(); throw new ArithmeticException(); }
        catch (ClassCastException expected) { }
    }
}
