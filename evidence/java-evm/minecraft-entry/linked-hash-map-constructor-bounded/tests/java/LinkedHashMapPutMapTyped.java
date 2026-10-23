import java.util.Map;
import java.util.LinkedHashMap;
public final class LinkedHashMapPutMapTyped {
    public static void main(String[] args) {
        Map<Object, Object> map = new LinkedHashMap<Object, Object>();
        map.put("k", "v");
    }
}
