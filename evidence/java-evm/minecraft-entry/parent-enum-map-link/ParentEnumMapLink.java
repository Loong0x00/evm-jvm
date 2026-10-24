import java.util.*;
import java.io.Serializable;
import java.lang.reflect.Array;
/** Generated-only type linkage. No EnumMap instance is constructed or fabricated. */
public final class ParentEnumMapLink {
    private static void check(boolean ok) { if (!ok) throw new ArithmeticException(); }
    public static void main(String[] args) {
        Map map = new LinkedHashMap();
        check(!(map instanceof EnumMap));
        check(!((Object) new HashMap() instanceof EnumMap));
        Object none = null;
        check(!(none instanceof EnumMap) && (EnumMap) none == null);
        try { EnumMap wrong = (EnumMap) map; throw new ArithmeticException(); }
        catch (ClassCastException expected) { }
        check(EnumMap.class.getName().equals("java.util.EnumMap"));
        EnumMap[] array = new EnumMap[2];
        check(array instanceof Object[] && array instanceof Map[] && array instanceof AbstractMap[]);
        check(array instanceof Serializable[] && array instanceof Cloneable[]);
        check(array.length == 2 && array[0] == null && array[1] == null);
        EnumMap[] copy = array.clone();
        check(copy != array && copy.length == 2 && copy[0] == null);
        Object[] opaque = array;
        try { opaque[0] = new HashMap(); throw new ArithmeticException(); }
        catch (ArrayStoreException expected) { }
        check(array[0] == null);
        EnumMap[] reflected = (EnumMap[]) Array.newInstance(EnumMap.class, 3);
        check(reflected.length == 3 && reflected[2] == null && reflected instanceof Cloneable[]);
        check(new EnumMap[0] instanceof Serializable[]);
        String unit = String.valueOf((char) 55296);
        check(unit.length() == 1 && unit.charAt(0) == (char) 55296);
        Object[] backing = {unit, null};
        List list = Arrays.asList(backing);
        Iterator iterator = list.iterator();
        backing[0] = String.valueOf((char) 65535);
        check(iterator.next() == backing[0] && iterator.next() == null && !iterator.hasNext());
        check(Collections.singletonList(unit).iterator().next() == unit);
        Object[] target = new Object[0];
        check(new ArrayList().toArray(target) == target && new HashMap().entrySet().toArray(target) == target);
        java.util.function.Function[] functions = new java.util.function.Function[0];
        NavigableSet[] navigable = new NavigableSet[0];
        check(functions.length + navigable.length == 0);
    }
}
