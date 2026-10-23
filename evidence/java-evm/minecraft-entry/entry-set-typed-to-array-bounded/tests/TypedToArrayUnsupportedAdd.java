import java.util.Collection;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;

public final class TypedToArrayUnsupportedAdd {
    public static void main(String[] args) {
        HashMap<String, String> map = new HashMap<String, String>();
        map.put("present", "value");
        Set<Map.Entry<String, String>> set = map.entrySet();
        Collection<Map.Entry<String, String>> collection = set;
        collection.add(null);
    }
}
