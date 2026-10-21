import java.util.HashMap;

public final class HashMapPutRefusal {
    public static void main(String[] args) {
        HashMap<Object, Object> map = new HashMap<>();
        map.put(null, null);
        throw new AssertionError("unimplemented HashMap.put unexpectedly returned");
    }
}
