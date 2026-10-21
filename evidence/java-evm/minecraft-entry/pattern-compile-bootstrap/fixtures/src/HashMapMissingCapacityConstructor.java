import java.util.HashMap;

public final class HashMapMissingCapacityConstructor {
    public static void main(String[] args) {
        HashMap<Object, Object> map = new HashMap<>(1);
        if (!map.isEmpty()) throw new AssertionError("unsupported capacity constructor resolved");
    }
}
