import java.util.Collection;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.util.Set;

public final class TypedToArrayPositive {
    private static void check(boolean value) {
        if (!value) throw new RuntimeException("typed-toArray assertion");
    }

    @SuppressWarnings("unchecked")
    public static void main(String[] args) {
        HashMap<String, String> map = new HashMap<String, String>();
        Set<Map.Entry<String, String>> set = map.entrySet();
        Collection<Map.Entry<String, String>> collection = set;

        Map.Entry<String, String>[] empty = new Map.Entry[0];
        check(collection.toArray(empty) == empty);
        check(empty.length == 0);

        check("Aa".hashCode() == "BB".hashCode());
        map.put(null, null);
        map.put("Aa", "first");
        map.put("BB", "second");
        map.put("tail", "third");
        check(map.size() == 4);

        Map.Entry<String, String>[] exact = new Map.Entry[map.size()];
        check(collection.toArray(exact) == exact);
        int seen = 0;
        Iterator<Map.Entry<String, String>> it = collection.iterator();
        while (it.hasNext()) {
            check(exact[seen++] == it.next());
        }
        check(seen == map.size());
        check(exact[0].getKey() == null);
        check(exact[0].getValue() == null);

        Map.Entry<String, String>[] oversized = new Map.Entry[map.size() + 2];
        Map.Entry<String, String> sentinel = exact[0];
        oversized[map.size() + 1] = sentinel;
        check(collection.toArray(oversized) == oversized);
        for (int i = 0; i < map.size(); i++) check(oversized[i] == exact[i]);
        check(oversized[map.size()] == null);
        check(oversized[map.size() + 1] == sentinel);

        Object[] supertype = new Object[map.size()];
        check(collection.toArray(supertype) == supertype);
        for (int i = 0; i < map.size(); i++) check(supertype[i] == exact[i]);

        Map.Entry<String, String> collisionA = null;
        Map.Entry<String, String> collisionB = null;
        for (int i = 0; i < exact.length; i++) {
            if ("Aa".equals(exact[i].getKey())) collisionA = exact[i];
            if ("BB".equals(exact[i].getKey())) collisionB = exact[i];
        }
        check(collisionA != null && collisionB != null);
        check(collisionA.setValue("changed") == "first");
        check("changed".equals(collisionA.getValue()));
        boolean sawUpdatedNode = false;
        for (Map.Entry<String, String> entry : collection) {
            if ("Aa".equals(entry.getKey())) {
                check(entry == collisionA);
                check("changed".equals(entry.getValue()));
                sawUpdatedNode = true;
            }
        }
        check(sawUpdatedNode);

        try {
            collection.toArray((Map.Entry<String, String>[]) null);
            throw new RuntimeException("null array accepted");
        } catch (NullPointerException expected) { }

        try {
            ((Collection) collection).toArray(new String[map.size()]);
            throw new RuntimeException("incompatible array accepted");
        } catch (ArrayStoreException expected) { }
    }
}
