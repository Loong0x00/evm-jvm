import java.util.IdentityHashMap;

public final class IdentityHashMapUnboundViews {
    public static void main(String[] args) {
        IdentityHashMap map = new IdentityHashMap(1);
        map.entrySet();
    }
}
