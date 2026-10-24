import java.lang.reflect.Array;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.util.NavigableSet;
import java.util.function.Function;

public final class SingletonListRetainedControlsProbe {
    private static void require(boolean value) { if (!value) { int fail = 1 / 0; } }

    public static void main(String[] args) {
        Object[] reflected = (Object[]) Array.newInstance(Object.class, 0);
        require(reflected.length == 0);

        Object token = new Object();
        ArrayList<Object> arrayList = new ArrayList<Object>();
        arrayList.add(token);
        Object[] copied = arrayList.toArray(new Object[0]);
        require(copied.length == 1 && copied[0] == token);
        Iterator<Object> iterator = arrayList.iterator();
        require(iterator.hasNext() && iterator.next() == token && !iterator.hasNext());

        Object key = new Object();
        Object value = new Object();
        HashMap<Object, Object> map = new HashMap<Object, Object>();
        map.put(key, value);
        Iterator<Map.Entry<Object, Object>> entries = map.entrySet().iterator();
        Map.Entry<Object, Object> entry = entries.next();
        require(entry.getKey() == key && entry.getValue() == value);

        Function<Object, Object> identity = new Function<Object, Object>() {
            public Object apply(Object input) { return input; }
        };
        require(identity.apply(token) == token);
        require(NavigableSet.class != null);
    }
}
