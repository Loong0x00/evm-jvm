import java.util.HashMap;

public final class HashMapPutTreeBinRefusal {
    static final class Key {
        final int id;
        Key(int id) { this.id = id; }
        public int hashCode() { return -7; }
        public boolean equals(Object other) {
            return other instanceof Key && ((Key) other).id == id;
        }
    }

    private static void check(boolean ok) { if (!ok) throw new Error(); }

    public static void main(String[] args) {
        HashMap<Object, Object> map = new HashMap<Object, Object>();
        for (int i = 0; i < 10; i++) map.put(new Key(i), "v");
        check(map.size() == 10);
        // Java8 can complete this operation; the bounded guest profile must
        // produce an interpreter refusal, never a catchable invented Error.
        map.put(new Key(10), "tree-required");
        check(map.size() == 11);
    }
}
