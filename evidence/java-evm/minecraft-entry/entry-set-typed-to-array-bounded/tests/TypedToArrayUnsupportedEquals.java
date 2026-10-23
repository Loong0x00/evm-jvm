import java.util.HashMap;
import java.util.Map;
import java.util.Set;

public final class TypedToArrayUnsupportedEquals {
    public static void main(String[] args) {
        HashMap<String, String> map = new HashMap<String, String>();
        Set<Map.Entry<String, String>> set = map.entrySet();
        set.equals(set);
    }
}
