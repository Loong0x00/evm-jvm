import java.io.Serializable;
import java.util.AbstractMap;
import java.util.HashMap;
import java.util.Map;

public final class HashMapConstructorMatrix {
    private static void check(HashMap<Object, Object> map) {
        if (map.size() != 0 || !map.isEmpty()) throw new AssertionError("empty state");
        if (!(map instanceof AbstractMap)) throw new AssertionError("AbstractMap");
        if (!(map instanceof Map)) throw new AssertionError("Map");
        if (!(map instanceof Cloneable)) throw new AssertionError("Cloneable");
        if (!(map instanceof Serializable)) throw new AssertionError("Serializable");
        if (map.getClass() != HashMap.class) throw new AssertionError("canonical class mirror");
    }

    public static void main(String[] args) {
        HashMap<Object, Object> first = new HashMap<>();
        HashMap<Object, Object> second = new HashMap<>();
        check(first);
        check(second);
        if (first == second) throw new AssertionError("fresh object identity");
        Map<Object, Object> interfaceView = first;
        if (interfaceView.size() != 0 || !interfaceView.isEmpty()) {
            throw new AssertionError("Map interface empty state");
        }
    }
}
