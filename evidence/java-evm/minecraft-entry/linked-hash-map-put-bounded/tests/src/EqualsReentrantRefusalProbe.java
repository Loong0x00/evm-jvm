import java.util.LinkedHashMap;

final class StableCollisionKey {
    public int hashCode() { return 17; }
    public boolean equals(Object other) { return this == other; }
}

final class EqualsReentrantKey {
    final LinkedHashMap<Object, Object> owner;
    boolean attempted;
    EqualsReentrantKey(LinkedHashMap<Object, Object> owner) { this.owner = owner; }
    public int hashCode() { return 17; }
    public boolean equals(Object other) {
        if (!attempted) {
            attempted = true;
            owner.put("nested", "value");
        }
        return false;
    }
}

public final class EqualsReentrantRefusalProbe {
    public static void main(String[] args) {
        LinkedHashMap<Object, Object> owner = new LinkedHashMap<Object, Object>();
        owner.put(new StableCollisionKey(), "old");
        owner.put(new EqualsReentrantKey(owner), "outer");
    }
}
