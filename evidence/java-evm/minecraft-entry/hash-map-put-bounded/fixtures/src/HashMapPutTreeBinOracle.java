import java.util.HashMap;

public final class HashMapPutTreeBinOracle {
    static final class Key {
        final int id;
        Key(int id) { this.id = id; }
        public int hashCode() { return -7; }
        public boolean equals(Object other) {
            return other instanceof Key && ((Key) other).id == id;
        }
    }
    public static void main(String[] args) {
        HashMap<Object, Object> map = new HashMap<Object, Object>();
        for (int i = 0; i < 11; i++) map.put(new Key(i), "v");
        if (map.size() != 11) throw new AssertionError();
    }
}
