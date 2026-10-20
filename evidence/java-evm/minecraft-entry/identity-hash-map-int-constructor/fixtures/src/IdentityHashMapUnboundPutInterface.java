import java.util.IdentityHashMap;
import java.util.Map;

public final class IdentityHashMapUnboundPutInterface {
    public static void main(String[] args) {
        Map map = new IdentityHashMap(1);
        map.put(new Object(), new Object());
    }
}
