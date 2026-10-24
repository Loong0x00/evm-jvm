import java.util.*;
/** Generated-only proposed P60 witness. Not compiled while worker owns the heavy slot. */
public final class ParentArrayListAdd {
    private static void check(boolean ok) { if (!ok) throw new ArithmeticException(); }
    static final class LyingSize extends ArrayList {
        public int size() { return 777; }
    }
    public static void main(String[] args) {
        ArrayList list = new ArrayList();
        List viaList = list;
        Collection viaCollection = list;
        Object first = new Object();
        Object second = new Object();
        Iterator empty = list.iterator();
        check(viaList.add(first));
        try { empty.next(); throw new ArithmeticException(); }
        catch (ConcurrentModificationException expected) { }
        check(viaCollection.add(null) && list.add(second));
        for (int i = 0; i < 18; ++i) check(list.add(first));
        check(list.size() == 21 && !list.isEmpty());
        Iterator one = list.iterator(), two = list.iterator();
        check(one != two && one.next() == first && two.next() == first);
        check(one.next() == null && one.hasNext());
        check(one.next() == second);
        int count = 3;
        while (one.hasNext()) { check(one.next() == first); ++count; }
        check(count == 21);
        try { one.next(); throw new ArithmeticException(); }
        catch (NoSuchElementException expected) { }
        Object[] target = new Object[23];
        Object tail = new Object();
        target[21] = tail; target[22] = tail;
        check(list.toArray(target) == target && target[0] == first && target[1] == null && target[2] == second);
        check(target[21] == null && target[22] == tail);
        try { list.toArray(new String[21]); throw new ArithmeticException(); }
        catch (ArrayStoreException expected) { }
        try { list.toArray((Object[]) null); throw new ArithmeticException(); }
        catch (NullPointerException expected) { }
        check(list.add(second));
        try { one.next(); throw new ArithmeticException(); }
        catch (ConcurrentModificationException expected) { }
        try { two.next(); throw new ArithmeticException(); }
        catch (ConcurrentModificationException expected) { }
        ArrayList zero = new ArrayList(0);
        ArrayList capacity = new ArrayList(2);
        check(zero.add(first) && zero.size() == 1);
        check(capacity.add(first) && capacity.add(null) && capacity.add(second) && capacity.size() == 3);
        LyingSize lying = new LyingSize();
        check(lying.isEmpty());
        check(lying.add(first) && lying.add(null) && !lying.isEmpty());
        Object[] privateTarget = new Object[2];
        check(lying.toArray(privateTarget) == privateTarget && privateTarget[0] == first && privateTarget[1] == null);
        Iterator privateCursor = lying.iterator();
        check(privateCursor.next() == first && privateCursor.next() == null && !privateCursor.hasNext());
        LinkedHashMap states = new LinkedHashMap();
        LinkedHashMap key = new LinkedHashMap();
        check(states.put(key, first) == null && states.size() == 1);
        Map.Entry entry = (Map.Entry) states.entrySet().iterator().next();
        check(entry.getKey() == key && entry.getValue() == first);
        check(!((Object) list instanceof EnumMap));
        String unit = String.valueOf((char) 55296);
        check(unit.length() == 1 && unit.charAt(0) == (char) 55296);
        Object[] backing = {first};
        Iterator arrayIterator = Arrays.asList(backing).iterator();
        backing[0] = second;
        check(arrayIterator.next() == second && !arrayIterator.hasNext());
    }
}
