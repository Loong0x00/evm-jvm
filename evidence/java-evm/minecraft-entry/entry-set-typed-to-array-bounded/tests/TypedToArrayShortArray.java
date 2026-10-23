import java.util.Collection;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;

public final class TypedToArrayShortArray {
    public static void main(String[] args) {
        HashMap<String, String> map = new HashMap<String, String>();
        map.put("one", "1");
        map.put("two", "2");
        Set<Map.Entry<String, String>> set = map.entrySet();
        Collection<Map.Entry<String, String>> collection = set;
        Map.Entry<String, String>[] tooShort = new Map.Entry[1];
        collection.toArray(tooShort);
    }
}
