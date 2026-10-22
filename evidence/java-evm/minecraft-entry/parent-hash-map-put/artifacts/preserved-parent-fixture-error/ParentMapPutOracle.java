import java.lang.reflect.Field;
import java.util.HashMap;

/** Read-only Java8 oracle for generated fixtures only; never guest input. */
public final class ParentMapPutOracle {
    private static Object field(Object object, String name) throws Exception {
        Field f = HashMap.class.getDeclaredField(name);
        f.setAccessible(true);
        return f.get(object);
    }
    private static void audit(String name, HashMap<?, ?> map) throws Exception {
        Object[] table = (Object[]) field(map, "table");
        int nodes = 0;
        for (Object first : table) {
            Object node = first;
            while (node != null) {
                nodes++;
                Field next = node.getClass().getDeclaredField("next");
                next.setAccessible(true);
                node = next.get(node);
            }
        }
        System.out.println(name + ":size=" + map.size() + ",modCount=" + field(map, "modCount")
            + ",threshold=" + field(map, "threshold") + ",table=" + table.length + ",nodes=" + nodes);
    }
    public static void main(String[] args) throws Exception {
        ParentMapPutSmall.main(new String[0]);
        audit("small", ParentMapPutSmall.completedMap);
        ParentMapPutResize.main(new String[0]);
        audit("resize", ParentMapPutResize.completedMap);
    }
}
