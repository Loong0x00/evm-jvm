import java.util.LinkedHashMap;

public final class MapEqualsRefusalProbe {
    public static void main(String[] args) {
        LinkedHashMap<Object, Object> left = new LinkedHashMap<Object, Object>();
        LinkedHashMap<Object, Object> right = new LinkedHashMap<Object, Object>();
        left.equals(right);
    }
}
