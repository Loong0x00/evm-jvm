import java.util.IdentityHashMap;

public final class IdentityHashMapUnboundPutConcrete {
    public static void main(String[] args) {
        IdentityHashMap map = new IdentityHashMap(1);
        map.put(new Object(), new Object());
    }
}
