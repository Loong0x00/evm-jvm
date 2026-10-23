import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.util.Set;

/** Generated-only EVM guest probe; never a Minecraft or external input. */
public final class EntrySetProbe {
    public static final class Key {
        final int id;
        final int hash;
        Key(int id, int hash) { this.id = id; this.hash = hash; }
        public int hashCode() { return hash; }
        public boolean equals(Object other) {
            return other instanceof Key && ((Key) other).id == id;
        }
    }

    private static void check(boolean ok) {
        if (!ok) throw new RuntimeException();
    }

    public static void main(String[] ignored) {
        HashMap<Key, String> map = new HashMap<Key, String>();
        Set<Map.Entry<Key, String>> view = map.entrySet();
        check(view == map.entrySet() && view.size() == 0 && view.isEmpty());
        map.put(null, null);
        check(view.size() == 1 && !view.isEmpty());

        Key a = new Key(1, 7);
        Key b = new Key(2, 7); // genuine linked-bin collision
        map.put(a, "a");
        check(view.size() == 2 && !view.isEmpty());
        map.put(b, "b");
        check(view.size() == 3);

        Iterator<Map.Entry<Key, String>> alias = view.iterator();
        Map.Entry<Key, String> first = alias.next();
        String old = first.setValue("changed");
        check(old == null && "changed".equals(first.getValue()));
        map.put(null, "replaced"); // nonstructural value replacement must not fail fast
        check(alias.next().getKey() == a);
        boolean replacementVisible = false;
        Iterator<Map.Entry<Key, String>> replacement = view.iterator();
        while (replacement.hasNext()) {
            Map.Entry<Key, String> entry = replacement.next();
            if (entry.getKey() == null) replacementVisible = "replaced".equals(entry.getValue());
        }
        check(replacementVisible);

        Iterator<Map.Entry<Key, String>> exhausted = view.iterator();
        exhausted.next();
        exhausted.next();
        exhausted.next();
        boolean noSuch = false;
        try { exhausted.next(); } catch (java.util.NoSuchElementException expected) { noSuch = true; }
        check(noSuch);

        Iterator<Map.Entry<Key, String>> structural = view.iterator();
        map.put(new Key(3, 9), "c");
        boolean concurrent = false;
        try { structural.next(); } catch (java.util.ConcurrentModificationException expected) { concurrent = true; }
        check(concurrent);

        // Cross the ordinary 0.75 threshold to exercise the actual resized Node[] table.
        for (int i = 4; i <= 15; i++) map.put(new Key(i, i), "v" + i);
        check(view.size() == 16);
        int seen = 0;
        Iterator<Map.Entry<Key, String>> resized = view.iterator();
        while (resized.hasNext()) {
            Map.Entry<Key, String> entry = resized.next();
            check(entry.getValue() != null);
            seen++;
        }
        check(seen == 16);
    }
}
