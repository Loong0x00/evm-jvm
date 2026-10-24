import java.util.*;
/** A caught guest callback exception keeps callback writes but never publishes the outer insertion. */
public final class ParentCallbackSideeffects {
    static final class HashKey {
        final LinkedHashMap map;
        int calls;
        HashKey(LinkedHashMap map) { this.map = map; }
        public int hashCode() { calls++; map.put("inner", "value"); throw new ArithmeticException(); }
    }
    static final class StoredKey {
        public int hashCode() { return 17; }
    }
    static final class EqualsKey {
        final LinkedHashMap map;
        int calls;
        EqualsKey(LinkedHashMap map) { this.map = map; }
        public int hashCode() { return 17; }
        public boolean equals(Object other) { calls++; map.put("inner", "value"); throw new ArithmeticException(); }
    }
    private static void check(boolean ok) { if (!ok) throw new ArithmeticException(); }
    public static void main(String[] args) {
        LinkedHashMap first = new LinkedHashMap();
        HashKey hash = new HashKey(first);
        try { first.put(hash, "outer"); throw new ArithmeticException(); }
        catch (ArithmeticException expected) { }
        check(hash.calls == 1 && first.size() == 1);
        Map.Entry inner = (Map.Entry) first.entrySet().iterator().next();
        check(inner.getKey().equals("inner") && inner.getValue().equals("value"));
        LinkedHashMap second = new LinkedHashMap();
        StoredKey stored = new StoredKey();
        second.put(stored, "old");
        Map.Entry original = (Map.Entry) second.entrySet().iterator().next();
        EqualsKey incoming = new EqualsKey(second);
        try { second.put(incoming, "outer"); throw new ArithmeticException(); }
        catch (ArithmeticException expected) { }
        check(incoming.calls == 1 && second.size() == 2 && original.getValue().equals("old"));
        Iterator cursor = second.entrySet().iterator();
        check(cursor.next() == original && ((Map.Entry) cursor.next()).getKey().equals("inner") && !cursor.hasNext());
    }
}
