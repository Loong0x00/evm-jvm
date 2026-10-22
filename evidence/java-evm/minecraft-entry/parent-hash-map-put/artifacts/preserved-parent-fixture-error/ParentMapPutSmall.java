import java.util.HashMap;
import java.util.Map;

/** Parent-owned generated-only witness, not an original-server input. */
public final class ParentMapPutSmall {
    public static HashMap<Object, Object> completedMap;
    private static void check(boolean ok) { if (!ok) throw new ArithmeticException(); }
    public static void main(String[] args) {
        Map<Object, Object> map = new HashMap<Object, Object>();
        Object value = new Object();
        check(map.put(null, null) == null);
        check(map.put(null, value) == null);
        check(map.put(null, "null-value") == value);
        check(map.put("Aa", value) == null);
        check(map.put("BB", null) == null);
        check(map.put(new String(new char[] {'A', 'a'}), null) == value);
        check(map.size() == 3 && !map.isEmpty());
        check("a!b".replaceAll("[^a-z]", "").equals("ab"));
        Object[] source = new Object[] {map, value};
        Object[] copy = source.clone();
        check(copy != source && copy[0] == map && copy[1] == value);
        completedMap = (HashMap<Object, Object>) map;
    }
}
