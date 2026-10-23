import java.util.HashMap;
import java.util.LinkedHashMap;
public final class LinkedHashMapPutHashTyped {
    public static void main(String[] args) {
        HashMap<Object, Object> map = new LinkedHashMap<Object, Object>();
        map.put("k", "v");
    }
}
