import java.util.LinkedHashMap;

public final class InheritedGetRefusalProbe {
    public static void main(String[] args) {
        LinkedHashMap<Object, Object> map = new LinkedHashMap<Object, Object>();
        map.put("key", "value");
        map.get("key");
    }
}
