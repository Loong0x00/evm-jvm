import java.util.Map;
import java.util.SortedMap;
import java.util.NavigableMap;
import java.util.TreeMap;
import java.util.regex.Pattern;

/** Generated-only type/link/ordinary inherited-interface dispatch witness. */
public final class ParentNavigableLink {
    static final class LocalMap extends TreeMap<Object, Object>
            implements NavigableMap<Object, Object> {
        final int answer;
        LocalMap(int answer) { super(); this.answer = answer; }
        public int size() { return answer; }
    }
    private static void check(boolean ok) { if (!ok) throw new ArithmeticException(); }
    public static void main(String[] args) {
        Object value = new LocalMap(21);
        check(value instanceof NavigableMap && value instanceof SortedMap && value instanceof Map);
        NavigableMap<Object, Object> nav = (NavigableMap<Object, Object>) value;
        check(nav.size() == 21 && ((Map) value).size() == 21);
        NavigableMap[] array = new NavigableMap[1];
        array[0] = nav;
        NavigableMap[] copy = array.clone();
        check(copy != array && copy[0] == nav);
        try { NavigableMap bad = (NavigableMap) new Object(); throw new ArithmeticException(); }
        catch (ClassCastException expected) { }
        try { ((NavigableMap) null).size(); throw new ArithmeticException(); }
        catch (NullPointerException expected) { }
        check(Pattern.compile("^[a-z0-9_]+$").matcher("map_1").matches());
        check("x\r\n".replaceAll("^x\r$", "X").equals("x\r\n"));
    }
}
