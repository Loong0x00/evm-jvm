import java.util.LinkedHashMap;
public final class LinkedHashMapUnsupportedInheritedApi {
    public static void main(String[] args) {
        LinkedHashMap<Object, Object> map = new LinkedHashMap<Object, Object>();
        map.get("x");
    }
}
