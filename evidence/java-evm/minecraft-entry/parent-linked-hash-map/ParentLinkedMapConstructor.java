import java.util.*;
import java.io.Serializable;
/** Generated-only construction/empty-state witness, not an ordered-map operation test. */
public final class ParentLinkedMapConstructor {
    private static void check(boolean value) { if (!value) throw new ArithmeticException(); }
    public static void main(String[] args) {
        LinkedHashMap<Object,Object> linked = new LinkedHashMap<Object,Object>();
        Object object = linked;
        check(object instanceof HashMap && object instanceof Map);
        check(object instanceof Cloneable && object instanceof Serializable);
        HashMap<Object,Object> asHash = linked;
        Map<Object,Object> asMap = linked;
        check(asHash.size() == 0 && asMap.isEmpty());
        Set<Map.Entry<Object,Object>> view = asMap.entrySet();
        check(view == linked.entrySet() && view.isEmpty() && view.size() == 0);
        Iterator<Map.Entry<Object,Object>> iterator = view.iterator();
        check(!iterator.hasNext());
        try { iterator.next(); throw new ArithmeticException(); }
        catch (NoSuchElementException expected) { }
        Map.Entry[] target = new Map.Entry[0];
        check(view.toArray(target) == target);
        Object sentinel = new Object();
        Object[] oversized = new Object[] {sentinel, sentinel};
        check(view.toArray(oversized) == oversized && oversized[0] == null && oversized[1] == sentinel);
        LinkedHashMap[] array = new LinkedHashMap[] {linked};
        LinkedHashMap[] copy = array.clone();
        check(copy != array && copy[0] == linked);
        try { LinkedHashMap bad = (LinkedHashMap) new Object(); throw new ArithmeticException(); }
        catch (ClassCastException expected) { }
        try { ((Map) null).isEmpty(); throw new ArithmeticException(); }
        catch (NullPointerException expected) { }
    }
}
