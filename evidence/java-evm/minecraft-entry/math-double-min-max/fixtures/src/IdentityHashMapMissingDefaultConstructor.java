import java.util.IdentityHashMap;

public final class IdentityHashMapMissingDefaultConstructor {
    public static void main(String[] args) {
        IdentityHashMap map = new IdentityHashMap();
        map.size();
    }
}
