import java.util.NavigableMap;
import java.util.TreeMap;
/** Profile explicitly omits navigation-method API behavior. */
public final class ParentNavigableOmitted {
    static final class LocalMap extends TreeMap<Object, Object>
            implements NavigableMap<Object, Object> { public LocalMap() { super(); } }
    public static void main(String[] args) {
        NavigableMap<Object, Object> map = new LocalMap();
        Object token = new Object();
        if (map == null || token == null) throw new ArithmeticException();
        map.descendingMap();
    }
}
