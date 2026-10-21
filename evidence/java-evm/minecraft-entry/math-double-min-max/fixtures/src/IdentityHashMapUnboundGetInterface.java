import java.util.IdentityHashMap;
import java.util.Map;

public final class IdentityHashMapUnboundGetInterface {
    public static void main(String[] args) {
        Map map = new IdentityHashMap(1);
        map.get(null);
    }
}
