import java.util.*;
/** Generated-only, interface-typed capacity-admitted array copy witness. */
public final class ParentEntrySetArraySmoke {
    private static void check(boolean ok) { if (!ok) throw new ArithmeticException(); }
    public static void main(String[] args) {
        Map<Object,Object> map = new HashMap<Object,Object>();
        Collection<Map.Entry<Object,Object>> view = map.entrySet();
        Map.Entry[] zero = new Map.Entry[0];
        check(view.toArray(zero) == zero);
        Object tail = new Object();
        Object[] emptyOversized = new Object[] {tail, tail};
        check(view.toArray(emptyOversized) == emptyOversized);
        check(emptyOversized[0] == null && emptyOversized[1] == tail);
        try { view.toArray((Object[]) null); throw new ArithmeticException(); }
        catch (NullPointerException expected) { }
        Object key = new Object();
        Object value = new Object();
        Object second = new Object();
        map.put(null, null);
        map.put(key, value);
        Map.Entry[] exact = new Map.Entry[2];
        check(view.toArray(exact) == exact);
        Map.Entry keyed = null;
        int nullKeys = 0;
        for (int i=0; i<exact.length; i++) {
            if (exact[i].getKey() == key) { keyed = exact[i]; check(keyed.getValue() == value); }
            else { check(exact[i].getKey() == null && exact[i].getValue() == null); nullKeys++; }
        }
        check(keyed != null && nullKeys == 1);
        Object[] oversized = new Object[] {tail, tail, tail, tail};
        check(view.toArray(oversized) == oversized);
        check(oversized[0] instanceof Map.Entry && oversized[1] instanceof Map.Entry);
        check(oversized[2] == null && oversized[3] == tail);
        check(map.put(key, second) == value && keyed.getValue() == second);
        check(keyed.setValue(value) == second);
        Map.Entry[] repeated = new Map.Entry[2];
        check(view.toArray(repeated) == repeated);
        check(repeated[0] == exact[0] && repeated[1] == exact[1]);
        try { view.toArray(new String[2]); throw new ArithmeticException(); }
        catch (ArrayStoreException expected) { }
        ConcurrentModificationException[] faults = new ConcurrentModificationException[] {new ConcurrentModificationException()};
        ConcurrentModificationException[] faultCopy = faults.clone();
        check(faultCopy != faults && faultCopy[0] == faults[0]);
        check(view.size() == 2 && keyed.getValue() == value);
    }
}
