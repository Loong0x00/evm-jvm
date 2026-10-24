import java.lang.reflect.Array;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.util.NavigableSet;
import java.util.function.Function;

public final class SingletonListRetainedControlsSafeProbe {
    private static void require(boolean value) { if (!value) { int fail = 1 / 0; } }

    public static void main(String[] args) {
        Object[] reflected = (Object[]) Array.newInstance(Object.class, 0);
        require(reflected.length == 0);

        Object token = new Object();
        ArrayList<Object> arrayList = new ArrayList<Object>(1);
        Object[] target = new Object[] { token };
        Object[] copied = arrayList.toArray(target);
        require(copied == target && copied.length == 1 && copied[0] == null);
        Iterator<Object> iterator = arrayList.iterator();
        require(!iterator.hasNext());

        HashMap<Object, Object> map = new HashMap<Object, Object>();
        Iterator<Map.Entry<Object, Object>> entries = map.entrySet().iterator();
        require(!entries.hasNext());

        Function<Object, Object> identity = new Function<Object, Object>() {
            public Object apply(Object input) { return input; }
        };
        require(identity.apply(token) == token);
        require(NavigableSet.class != null);
    }
}
