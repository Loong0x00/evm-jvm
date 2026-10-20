import java.util.IdentityHashMap;

public final class IdentityHashMapUnboundDefaultMethod {
    public static void main(String[] args) {
        IdentityHashMap map = new IdentityHashMap(1);
        map.getOrDefault(null, null);
    }
}
