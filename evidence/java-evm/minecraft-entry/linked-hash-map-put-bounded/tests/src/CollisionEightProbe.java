import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Map;

public final class CollisionEightProbe {
    public static void main(String[] args) {
        LinkedHashMap<Object, Object> map = new LinkedHashMap<Object, Object>();
        for (int i = 0; i < 8; i++) map.put(new CollisionKey(i), "v");
        if (map.size() != 8) throw new ArithmeticException();
        Iterator<Map.Entry<Object, Object>> iterator = map.entrySet().iterator();
        for (int i = 0; i < 8; i++) {
            Map.Entry<Object, Object> entry = iterator.next();
            if (((CollisionKey) entry.getKey()).id != i) throw new ArithmeticException();
        }
        if (iterator.hasNext()) throw new ArithmeticException();
    }
}
