import java.util.HashMap;
import java.util.Set;
import java.util.Iterator;
import java.util.Map;
import java.util.NoSuchElementException;
import java.util.ConcurrentModificationException;

/** Generated-only independent backing/alias/iteration test; no original input. */
public final class ParentEntrySetSmoke {
    static final class Key {
        final int id;
        final int hash;
        Key(int id, int hash) { this.id = id; this.hash = hash; }
        public int hashCode() { return hash; }
        public boolean equals(Object other) {
            return other instanceof Key && ((Key) other).id == id;
        }
    }
    private static void check(boolean value) { if (!value) throw new ArithmeticException(); }
    public static void main(String[] args) {
        Map<Key,Object> map = new HashMap<Key,Object>();
        HashMap<Key,Object> other = new HashMap<Key,Object>();
        Set<Map.Entry<Key,Object>> view = map.entrySet();
        check(view == map.entrySet() && view != other.entrySet());
        check(view.size() == 0 && view.isEmpty());
        Iterator<Map.Entry<Key,Object>> empty = view.iterator();
        check(!empty.hasNext());
        try { empty.next(); throw new ArithmeticException(); }
        catch (NoSuchElementException expected) { }
        Iterator<Map.Entry<Key,Object>> staleEmpty = view.iterator();
        Object first = new Object();
        Object second = new Object();
        check(map.put(null, null) == null);
        check(view.size() == 1 && !view.isEmpty() && other.entrySet().isEmpty());
        // JDK8 next checks modCount before testing whether the cached next is null.
        check(!staleEmpty.hasNext());
        try { staleEmpty.next(); throw new ArithmeticException(); }
        catch (ConcurrentModificationException expected) { }
        Iterator<Map.Entry<Key,Object>> one = view.iterator();
        Map.Entry<Key,Object> entry = one.next();
        check(entry.getKey() == null && entry.getValue() == null);
        check(map.put(null, first) == null && entry.getValue() == first);
        check(entry.setValue(second) == first && entry.getValue() == second);
        check(map.put(null, first) == second && entry.getValue() == first);
        check(!one.hasNext());
        try { one.next(); throw new ArithmeticException(); }
        catch (NoSuchElementException expected) { }
        Key a = new Key(1, 7);
        Key b = new Key(2, 7);
        map.put(a, first);
        Iterator<Map.Entry<Key,Object>> stale = view.iterator();
        map.put(b, second);
        try { stale.next(); throw new ArithmeticException(); }
        catch (ConcurrentModificationException expected) { }
        Iterator<Map.Entry<Key,Object>> live = view.iterator();
        check(map.put(new Key(1, 7), second) == first);
        check(view.size() == 3 && view == map.entrySet());
        int count = 0;
        int found = 0;
        while (live.hasNext()) {
            Map.Entry<Key,Object> item = live.next();
            Key key = item.getKey();
            if (key == null) { check(item.getValue() == first); found |= 1; }
            else if (key == a) { check(item.getValue() == second); found |= 2; }
            else if (key == b) { check(item.getValue() == second); found |= 4; }
            else throw new ArithmeticException();
            count++;
        }
        ConcurrentModificationException[] faults = new ConcurrentModificationException[] {new ConcurrentModificationException()};
        ConcurrentModificationException[] faultCopy = faults.clone();
        check(faultCopy != faults && faultCopy[0] == faults[0]);
        check(count == 3 && found == 7);
        try { live.next(); throw new ArithmeticException(); }
        catch (NoSuchElementException expected) { }
    }
}
