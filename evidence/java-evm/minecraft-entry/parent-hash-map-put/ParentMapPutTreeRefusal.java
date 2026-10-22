import java.util.HashMap;

/** Valid on Java8; this bounded guest profile must atomically refuse treeification. */
public final class ParentMapPutTreeRefusal {
    public static HashMap<Object, Object> map;
    static final class Key {
        final int id;
        Key(int id) { this.id = id; }
        public int hashCode() { return -7; }
        public boolean equals(Object other) {
            return other instanceof Key && ((Key) other).id == id;
        }
    }
    public static void main(String[] args) {
        map = new HashMap<Object, Object>();
        Object value = new Object();
        for (int i = 0; i < 11; i++) map.put(new Key(i), value);
        if (map.size() != 11) throw new ArithmeticException();
    }
}
