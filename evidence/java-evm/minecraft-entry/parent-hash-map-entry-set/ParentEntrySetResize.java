import java.util.*;
/** Generated resize/live-node witness; only measured entry view/iterator APIs. */
public final class ParentEntrySetResize {
    private static void check(boolean ok) { if (!ok) throw new ArithmeticException(); }
    public static void main(String[] args) {
        Map<ParentEntrySetSmoke.Key,Object> map = new HashMap<ParentEntrySetSmoke.Key,Object>();
        Set<Map.Entry<ParentEntrySetSmoke.Key,Object>> view = map.entrySet();
        Object value = new Object();
        map.put(null, null);
        for (int i=0; i<40; i++) map.put(new ParentEntrySetSmoke.Key(i, i*17), value);
        check(view == map.entrySet() && view.size() == 41);
        Iterator<Map.Entry<ParentEntrySetSmoke.Key,Object>> it = view.iterator();
        int count=0, sum=0, nulls=0;
        while (it.hasNext()) {
            Map.Entry<ParentEntrySetSmoke.Key,Object> entry = it.next();
            ParentEntrySetSmoke.Key key = entry.getKey();
            if (key == null) { check(entry.getValue() == null); nulls++; }
            else { check(entry.getValue() == value); sum += key.id; }
            count++;
        }
        check(count == 41 && sum == 780 && nulls == 1);
        try { it.next(); throw new ArithmeticException(); }
        catch (NoSuchElementException expected) { }
    }
}
