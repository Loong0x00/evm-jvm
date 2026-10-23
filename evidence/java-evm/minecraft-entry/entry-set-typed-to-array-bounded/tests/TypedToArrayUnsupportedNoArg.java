import java.util.Collection;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;

public final class TypedToArrayUnsupportedNoArg {
    public static void main(String[] args) {
        HashMap<String, String> map = new HashMap<String, String>();
        Set<Map.Entry<String, String>> set = map.entrySet();
        Collection<Map.Entry<String, String>> collection = set;
        collection.toArray();
    }
}
