import java.util.*;
/** Generated-only proposed P59 witness. Not compiled or accepted until design approval. */
public final class ParentLinkedMapPut {
    private static void check(boolean ok) { if (!ok) throw new ArithmeticException(); }
    public static void main(String[] args) {
        LinkedHashMap map = new LinkedHashMap();
        Map viaMap = map;
        HashMap viaHashMap = map;
        Set view = map.entrySet();
        check(view == map.entrySet() && view.isEmpty() && map.hashCode() == 0);
        Object b = "b", a = "a", v1 = "one", v2 = "two", v3 = "three";
        check(viaMap.put(b, v1) == null && viaHashMap.put(a, v2) == null);
        check(map.put(null, null) == null && map.size() == 3 && view.size() == 3);
        Iterator old = view.iterator();
        Map.Entry first = (Map.Entry) old.next();
        check(first.getKey() == b && first.getValue() == v1);
        check(map.put(b, v3) == v1 && first.getValue() == v3 && map.size() == 3);
        Map.Entry second = (Map.Entry) old.next();
        check(second.getKey() == a && second.getValue() == v2);
        check(((Map.Entry) old.next()).getKey() == null && !old.hasNext());
        try { old.next(); throw new ArithmeticException(); }
        catch (NoSuchElementException expected) { }
        check(map.hashCode() == (b.hashCode() ^ v3.hashCode()) + (a.hashCode() ^ v2.hashCode()));
        Object[] target = {null, null, null, new Object(), new Object()};
        Object tail = target[4];
        check(view.toArray(target) == target && target[0] == first && target[1] == second);
        check(target[3] == null && target[4] == tail);
        Iterator stale = view.iterator();
        check(map.put("four", "value") == null);
        try { stale.next(); throw new ArithmeticException(); }
        catch (ConcurrentModificationException expected) { }
        LinkedHashMap emptyKey = new LinkedHashMap();
        LinkedHashMap states = new LinkedHashMap();
        Object state = new Object();
        check(emptyKey.hashCode() == 0 && states.put(emptyKey, state) == null);
        check(states.size() == 1 && !states.isEmpty() && states.hashCode() == state.hashCode());
        Map.Entry stateEntry = (Map.Entry) states.entrySet().iterator().next();
        check(stateEntry.getKey() == emptyKey && stateEntry.getValue() == state);
        check(!(map instanceof EnumMap));
        String unit = String.valueOf((char) 65535);
        check(unit.length() == 1 && unit.charAt(0) == (char) 65535);
        Object[] backing = {state};
        Iterator arrayIterator = Arrays.asList(backing).iterator();
        backing[0] = unit;
        check(arrayIterator.next() == unit && !arrayIterator.hasNext());
    }
}
