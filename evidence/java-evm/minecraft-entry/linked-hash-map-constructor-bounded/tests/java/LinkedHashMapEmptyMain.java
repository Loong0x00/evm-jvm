import java.util.HashMap;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.NoSuchElementException;

/** Generated Java 8 guest fixture: verifies only the admitted empty-state API. */
public final class LinkedHashMapEmptyMain {
    public static void main(String[] args) {
        LinkedHashMap<Object, Object> linked = new LinkedHashMap<Object, Object>();
        HashMap<Object, Object> hashTyped = linked;
        Map<Object, Object> mapTyped = linked;
        if (linked.size() != 0 || !linked.isEmpty()
                || hashTyped.size() != 0 || !hashTyped.isEmpty()
                || mapTyped.size() != 0 || !mapTyped.isEmpty()) {
            throw new ArithmeticException();
        }
        if (linked.entrySet() != linked.entrySet()
                || linked.entrySet().size() != 0 || !linked.entrySet().isEmpty()) {
            throw new ArithmeticException();
        }
        Iterator<Map.Entry<Object, Object>> iterator = linked.entrySet().iterator();
        if (iterator.hasNext()) throw new ArithmeticException();
        try {
            iterator.next();
            throw new ArithmeticException();
        } catch (NoSuchElementException expected) { }
        Map.Entry<?, ?>[] target = new Map.Entry<?, ?>[2];
        Object[] copied = linked.entrySet().toArray(target);
        if (copied != target || target[0] != null || target[1] != null) {
            throw new ArithmeticException();
        }
    }
}
