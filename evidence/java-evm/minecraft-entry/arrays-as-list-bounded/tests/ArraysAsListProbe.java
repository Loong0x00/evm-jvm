import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import java.util.List;
import java.util.RandomAccess;

/** Host-JVM oracle and unchanged Java 8 classfile executed by the local EVM. */
public final class ArraysAsListProbe implements java.util.function.Function {
    private ArraysAsListProbe() { }

    public Object apply(Object value) { return value; }

    private static void check(boolean condition) {
        if (!condition) throw new AssertionError();
    }

    public static void main(String[] args) {
        Object marker = "marker";
        Object[] objects = new Object[] { marker, null, "last" };
        List list = Arrays.asList(objects);
        check(list.size() == 3);
        check(list instanceof RandomAccess);
        check(list instanceof Serializable);

        Iterator first = list.iterator();
        Iterator second = list.iterator();
        check(first != second);
        Object replacement = new Object();
        objects[0] = replacement; // Visible through an iterator created earlier.
        check(first.next() == replacement);
        check(second.next() == replacement);
        check(first.next() == null); // null is data, not exhaustion.
        objects[2] = marker; // Read the actual array at next(), not a snapshot.
        check(first.next() == marker);
        check(second.next() == null);
        check(second.next() == marker);
        check(!first.hasNext() && !second.hasNext());
        try {
            first.next();
            throw new AssertionError();
        } catch (java.util.NoSuchElementException expected) { }

        List secondList = Arrays.asList(objects);
        check(secondList != list);
        check(secondList.size() == objects.length);
        objects[1] = marker;
        check(secondList.iterator().next() == replacement);

        String[] strings = new String[] { "s", null };
        List stringList = Arrays.asList(strings);
        check(stringList.size() == 2);
        check(stringList.iterator().next() == strings[0]);
        strings[0] = "updated";
        check(stringList.iterator().next() == strings[0]);

        Serializable[] interfaces = new Serializable[] { (Serializable) marker, null };
        List interfaceList = Arrays.asList(interfaces);
        check(interfaceList.size() == 2);
        check(interfaceList.iterator().next() == marker);
        check(new ArraysAsListProbe().apply(marker) == marker); // retained Function interface
        check(!(list instanceof java.util.NavigableSet)); // retained interface mirror/link control

        // Retained P55 controls: stored ArrayList copy/iterator and singleton traversal.
        java.util.ArrayList oldList = new java.util.ArrayList(2);
        Object[] oldCopy = oldList.toArray(new Object[0]);
        check(oldCopy.length == 0);
        Iterator oldIterator = oldList.iterator();
        check(!oldIterator.hasNext());
        List singleton = java.util.Collections.singletonList(marker);
        check(singleton.size() == 1 && singleton.iterator().next() == marker);

        // Retained HashMap.entrySet traversal is independent of the new list.
        java.util.HashMap oldMap = new java.util.HashMap();
        oldMap.put("key", marker);
        java.util.Map.Entry oldEntry = (java.util.Map.Entry) oldMap.entrySet().iterator().next();
        check(oldEntry.getKey() == "key" && oldEntry.getValue() == marker);

        Object[] empty = new Object[0];
        List emptyList = Arrays.asList(empty);
        check(emptyList.size() == 0 && emptyList.isEmpty());
        Iterator emptyIterator = emptyList.iterator();
        check(!emptyIterator.hasNext());
        try {
            emptyIterator.next();
            throw new AssertionError();
        } catch (java.util.NoSuchElementException expected) { }

        List oneNull = Arrays.asList((Object) null);
        check(oneNull.size() == 1 && oneNull.iterator().next() == null);

        try {
            Arrays.asList((Object[]) null);
            throw new AssertionError();
        } catch (NullPointerException expected) { }
    }
}
