import java.util.HashMap;

/** Generated-only collision, replacement, signed/spread-hash, and resize witness. */
public final class ParentMapPutResize {
    public static HashMap<Object, Object> completedMap;
    static final class Key {
        final int id;
        final int hash;
        Key(int id, int hash) { this.id = id; this.hash = hash; }
        public int hashCode() { return hash; }
        public boolean equals(Object other) {
            return other instanceof Key && ((Key) other).id == id;
        }
    }
    private static void check(boolean ok) { if (!ok) throw new ArithmeticException(); }
    public static void main(String[] args) {
        HashMap<Object, Object> map = new HashMap<Object, Object>();
        Object first = new Object();
        check(map.put(new Key(-1, -1), first) == null);
        check(map.put(new Key(-1, -1), null) == first);
        for (int i = 0; i < 30; i++) {
            int hash = i < 6 ? 7 : i << 16;
            check(map.put(new Key(i, hash), first) == null);
        }
        check(map.size() == 31);
        for (int i = 0; i < 30; i++) {
            int hash = i < 6 ? 7 : i << 16;
            check(map.put(new Key(i, hash), null) == first);
        }
        check(map.size() == 31);
        check(map.put(null, first) == null && map.size() == 32);
        completedMap = map;
    }
}
