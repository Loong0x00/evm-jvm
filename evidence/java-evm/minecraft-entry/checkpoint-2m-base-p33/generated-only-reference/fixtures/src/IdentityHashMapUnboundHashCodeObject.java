import java.util.IdentityHashMap;

public final class IdentityHashMapUnboundHashCodeObject {
    public static void main(String[] args) {
        Object map = new IdentityHashMap(1);
        map.hashCode();
    }
}
