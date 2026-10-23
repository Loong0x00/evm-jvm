import java.util.LinkedHashMap;
public final class LinkedHashMapUnsupportedDefault {
    public static void main(String[] args) { new LinkedHashMap<Object, Object>().putIfAbsent(null, null); }
}
