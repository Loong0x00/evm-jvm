import java.util.HashMap;

public final class HashMapPutBasic {
    static final class Key {
        final int value;
        Key(int value) { this.value = value; }
        public int hashCode() { return value; }
        public boolean equals(Object other) {
            return other instanceof Key && ((Key) other).value == value;
        }
    }

    private static void check(boolean ok) { if (!ok) throw new Error(); }

    public static void main(String[] args) {
        HashMap<Object, Object> map = new HashMap<Object, Object>();
        check(map.size() == 0 && map.isEmpty());
        check(map.put(null, null) == null);
        check(map.size() == 1 && map.put(null, "null-key") == null);
        check(map.put(null, "replaced-null-key").equals("null-key"));
        check(map.size() == 1);
        check(map.put("Aa", "first") == null);
        check(map.put("BB", "second") == null); // String hash collision
        check(map.put("Aa", "updated").equals("first"));
        check(map.size() == 3);
        Key negative = new Key(-1);
        check(map.put(negative, "negative") == null);
        check(map.put(new Key(-1), "negative-updated").equals("negative"));
        check(map.put(new Key(0x12340000), "spread-hi") == null);
        check(map.put(new Key(0x00001234), "spread-lo") == null);
        String[] keys = {"r00", "r01", "r02", "r03", "r04", "r05", "r06", "r07", "r08", "r09",
                         "r10", "r11", "r12", "r13", "r14", "r15", "r16", "r17", "r18", "r19"};
        for (int i = 0; i < keys.length; i++) check(map.put(keys[i], keys[i]) == null);
        check(map.size() == 26);
        check(map.put("r03", "replacement").equals("r03"));
        check(map.size() == 26);
    }
}
