import java.util.LinkedHashMap;

final class CollisionKey {
    final int id;
    int hashes;
    int equalsCalls;
    CollisionKey(int id) { this.id = id; }
    public int hashCode() { hashes++; return 77; }
    public boolean equals(Object other) {
        equalsCalls++;
        return other instanceof CollisionKey && id == ((CollisionKey) other).id;
    }
}

public final class CollisionRefusalProbe {
    public static void main(String[] args) {
        LinkedHashMap<Object, Object> map = new LinkedHashMap<Object, Object>();
        for (int i = 0; i < 8; i++) map.put(new CollisionKey(i), "v");
        // The ninth unmatched key must reach the explicit raw refusal boundary.
        map.put(new CollisionKey(8), "v");
    }
}
