import java.util.HashMap;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

final class ProbeKey {
    final int code;
    final int identity;
    final boolean acceptsEqual;
    int hashCalls;
    int equalsCalls;

    ProbeKey(int code, int identity, boolean acceptsEqual) {
        this.code = code;
        this.identity = identity;
        this.acceptsEqual = acceptsEqual;
    }

    public int hashCode() { hashCalls++; return code; }
    public boolean equals(Object other) {
        equalsCalls++;
        return acceptsEqual && other instanceof ProbeKey
                && identity == ((ProbeKey) other).identity;
    }
}

public final class PutProbe {
    private static void require(boolean condition) {
        if (!condition) throw new ArithmeticException();
    }

    public static void main(String[] args) {
        // Real content hash for an empty LHM key is naturally zero. The first
        // actual insertion value is deliberately opaque and is never hashed.
        LinkedHashMap<Object, Object> emptyKey = new LinkedHashMap<Object, Object>();
        require(emptyKey.hashCode() == 0);
        Object opaqueValue = new Object();
        LinkedHashMap<Object, Object> map = new LinkedHashMap<Object, Object>();
        Map<Object, Object> mapTyped = map;
        HashMap<Object, Object> hashTyped = map;
        require(mapTyped.put(emptyKey, opaqueValue) == null);
        require(map.size() == 1 && !map.isEmpty());
        Set<Map.Entry<Object, Object>> view = map.entrySet();
        require(view == map.entrySet() && view.size() == 1);
        Iterator<Map.Entry<Object, Object>> beforeOverwrite = view.iterator();
        Map.Entry<Object, Object> firstEntry = beforeOverwrite.next();
        require(firstEntry.getKey() == emptyKey && firstEntry.getValue() == opaqueValue);
        Object replacement = new Object();
        require(hashTyped.put(emptyKey, replacement) == opaqueValue);
        boolean initialNsee = false;
        try { beforeOverwrite.next(); }
        catch (java.util.NoSuchElementException expected) { initialNsee = true; }
        require(initialNsee);
        require(firstEntry.getValue() == replacement);
        require(view.iterator().next() == firstEntry);
        require(map.put(emptyKey, null) == replacement);
        require(firstEntry.getValue() == null && map.size() == 1);

        // Incoming-key equals direction, exactly-one hash callback per put,
        // and replacement of the same entry object without structural change.
        LinkedHashMap<Object, Object> callbacks = new LinkedHashMap<Object, Object>();
        ProbeKey oldKey = new ProbeKey(17, 9, false);
        ProbeKey incoming = new ProbeKey(17, 9, true);
        require(callbacks.put(oldKey, "old") == null);
        Map.Entry<Object, Object> callbackEntry = callbacks.entrySet().iterator().next();
        require(callbacks.put(incoming, "new") == "old");
        require(oldKey.hashCalls == 1 && incoming.hashCalls == 1);
        require(oldKey.equalsCalls == 0 && incoming.equalsCalls == 1);
        require(callbacks.size() == 1 && callbacks.entrySet().iterator().next() == callbackEntry);
        require(callbackEntry.getKey() == oldKey && callbackEntry.getValue().equals("new"));

        // Content hash uses fresh raw key/value hashes on every invocation,
        // rather than the spread hash cached for put or object identity.
        LinkedHashMap<Object, Object> freshHashes = new LinkedHashMap<Object, Object>();
        ProbeKey hashKey = new ProbeKey(5, 1, false);
        ProbeKey hashValue = new ProbeKey(8, 2, false);
        require(freshHashes.put(hashKey, hashValue) == null);
        require(hashKey.hashCalls == 1 && hashValue.hashCalls == 0);
        require(freshHashes.hashCode() == (5 ^ 8));
        require(hashKey.hashCalls == 2 && hashValue.hashCalls == 1);
        require(freshHashes.hashCode() == (5 ^ 8));
        require(hashKey.hashCalls == 3 && hashValue.hashCalls == 2);

        // Distinct spread hashes do not have an artificial small-map cap.
        for (int i = 0; i < 20; i++) {
            ProbeKey k = new ProbeKey(100 + i * 65537, i, false);
            callbacks.put(k, "v");
        }
        require(callbacks.size() == 21);
        int order = 0;
        Iterator<Map.Entry<Object, Object>> ordered = callbacks.entrySet().iterator();
        require(ordered.next().getKey() == oldKey);
        while (ordered.hasNext()) {
            Map.Entry<Object, Object> e = ordered.next();
            require(e.getValue() != null);
            order++;
        }
        require(order == 20);

        // Null key/value support and null-aware map hash contribution.
        LinkedHashMap<String, String> content = new LinkedHashMap<String, String>();
        require(content.put(null, null) == null);
        require(content.put("a", "x") == null);
        require(content.put("b", null) == null);
        int expectedHash = ("a".hashCode() ^ "x".hashCode()) + "b".hashCode();
        require(content.hashCode() == expectedHash);
        Map.Entry<String, String> contentEntry = content.entrySet().iterator().next();
        require(contentEntry.getKey() == null && contentEntry.getValue() == null);
        require(contentEntry.hashCode() == 0);
        require(contentEntry.setValue("changed") == null);
        require(contentEntry.getValue().equals("changed") && content.size() == 3);
        require(content.hashCode() == expectedHash + ("changed".hashCode()));

        // A value overwrite and Entry.setValue are non-structural for existing iterators.
        Iterator<Map.Entry<String, String>> overwriteCursor = content.entrySet().iterator();
        content.put("a", "y");
        content.entrySet().iterator().next().setValue("changed-again");
        require(overwriteCursor.next().getKey() == null);

        // Insertion is structural and next checks CME before exhaustion.
        Iterator<Map.Entry<String, String>> failFast = content.entrySet().iterator();
        content.put("c", "z");
        boolean cme = false;
        try { failFast.next(); } catch (java.util.ConcurrentModificationException expected) { cme = true; }
        require(cme);
        LinkedHashMap<String, String> emptyBeforeInsert = new LinkedHashMap<String, String>();
        Iterator<Map.Entry<String, String>> emptyCursor = emptyBeforeInsert.entrySet().iterator();
        emptyBeforeInsert.put("after-cursor", "value");
        boolean cmeBeforeNsee = false;
        try { emptyCursor.next(); }
        catch (java.util.ConcurrentModificationException expected) { cmeBeforeNsee = true; }
        require(cmeBeforeNsee);
        Iterator<Map.Entry<String, String>> exhausted = content.entrySet().iterator();
        while (exhausted.hasNext()) exhausted.next();
        boolean nsee = false;
        try { exhausted.next(); } catch (java.util.NoSuchElementException expected) { nsee = true; }
        require(nsee);

        // Typed-array target identity, aliases, first-tail null, later-tail preservation.
        Set<Map.Entry<String, String>> live = content.entrySet();
        Object[] target = new Object[live.size() + 2];
        target[target.length - 1] = "tail";
        Object[] returned = live.toArray(target);
        require(returned == target && returned[0] == live.iterator().next());
        require(returned[live.size()] == null && returned[target.length - 1].equals("tail"));
        Map.Entry[] entryTarget = new Map.Entry[live.size()];
        require(live.toArray(entryTarget) == entryTarget);
        require(entryTarget[0] == live.iterator().next());
        boolean npe = false;
        try { live.toArray((Object[]) null); }
        catch (NullPointerException expected) { npe = true; }
        require(npe);
        String[] wrongArrayType = new String[live.size()];
        boolean ase = false;
        try { live.toArray(wrongArrayType); }
        catch (ArrayStoreException expected) { ase = true; }
        require(ase && content.size() == live.size());

        // The view is cached/live and insertion-order iteration remains stable.
        require(live == content.entrySet() && live.size() == 4);
        require(content.entrySet().iterator().next() == contentEntry);
    }
}
