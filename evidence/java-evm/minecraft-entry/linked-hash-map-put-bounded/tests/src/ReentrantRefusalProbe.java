import java.util.LinkedHashMap;

final class ReentrantKey {
    final LinkedHashMap<Object, Object> owner;
    boolean attempted;
    ReentrantKey(LinkedHashMap<Object, Object> owner) { this.owner = owner; }
    public int hashCode() {
        if (!attempted) {
            attempted = true;
            owner.put("nested", "value");
        }
        return 123;
    }
    public boolean equals(Object other) { return this == other; }
}

public final class ReentrantRefusalProbe {
    public static void main(String[] args) {
        LinkedHashMap<Object, Object> owner = new LinkedHashMap<Object, Object>();
        owner.put(new ReentrantKey(owner), "outer");
    }
}
