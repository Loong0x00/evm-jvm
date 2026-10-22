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
        boolean refused = false;
        try {
            map.put(new Key(10), "must-not-link");
        } catch (Error expectedUnsupportedTreeBin) {
            refused = true;
        }
        check(refused && map.size() == 10);
        check(map.put("after-refusal", "ok") == null);
        check(map.size() == 11);
    }
}
