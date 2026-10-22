import java.util.HashMap;

/** get remains unsupported; it must not fabricate a null result. */
public final class ParentMapGetRefusal {
    public static HashMap<Object, Object> map;
    public static void main(String[] args) {
        map = new HashMap<Object, Object>();
        Object value = new Object();
        map.put(null, value);
        if (map.get(null) != value) throw new ArithmeticException();
    }
}
