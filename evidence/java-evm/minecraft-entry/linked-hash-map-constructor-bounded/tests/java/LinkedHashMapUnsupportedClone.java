import java.util.LinkedHashMap;
public final class LinkedHashMapUnsupportedClone {
    public static void main(String[] args) { new LinkedHashMap<Object, Object>().clone(); }
}
