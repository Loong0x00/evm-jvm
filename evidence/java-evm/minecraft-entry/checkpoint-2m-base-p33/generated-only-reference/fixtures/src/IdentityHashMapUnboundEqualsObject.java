import java.util.IdentityHashMap;

public final class IdentityHashMapUnboundEqualsObject {
    public static void main(String[] args) {
        Object map = new IdentityHashMap(1);
        map.equals(new IdentityHashMap(1));
    }
}
