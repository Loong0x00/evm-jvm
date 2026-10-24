package probe;

import java.lang.reflect.Array;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Iterator;
import java.util.NoSuchElementException;

public final class ArrayListTypedToArrayProbe {
    static final class MisleadingSizeList extends ArrayList {
        public int size() { return 3; }
    }

    private static void require(boolean ok) {
        if (!ok) throw new AssertionError();
    }

    public static void main(String[] args) {
        ArrayList defaultList = new ArrayList();
        ArrayList zeroList = new ArrayList(0);
        ArrayList capacityList = new ArrayList(3);
        List asList = defaultList;
        Collection asCollection = zeroList;

        Object[] objectTarget = new Object[0];
        require(defaultList.toArray(objectTarget) == objectTarget);
        Object[] exactTarget = new Object[0];
        require(asList.toArray(exactTarget) == exactTarget);
        Object[] collectionTarget = new Object[0];
        require(asCollection.toArray(collectionTarget) == collectionTarget);

        Object[] oversized = new Object[3];
        Object before = new Object();
        Object after = new Object();
        oversized[0] = before;
        oversized[1] = before;
        oversized[2] = after;
        require(capacityList.toArray(oversized) == oversized);
        require(oversized[0] == null);
        require(oversized[1] == before && oversized[2] == after);

        String[] strings = new String[2];
        strings[0] = "clear-me";
        strings[1] = "tail";
        require(defaultList.toArray(strings) == strings);
        require(strings[0] == null && strings[1] == "tail");

        Iterable[] iterables = new Iterable[2];
        iterables[0] = null;
        iterables[1] = null;
        require(defaultList.toArray(iterables) == iterables);
        require(iterables[0] == null && iterables[1] == null);

        Map.Entry[] entries = new Map.Entry[2];
        entries[0] = null;
        require(defaultList.toArray(entries) == entries);
        require(entries[0] == null && entries[1] == null);

        Object reflected = Array.newInstance(Object.class, 0);
        require(reflected instanceof Object[]);
        require(defaultList.toArray((Object[]) reflected) == reflected);

        boolean nullTargetNpe = false;
        try { defaultList.toArray((Object[]) null); }
        catch (NullPointerException expected) { nullTargetNpe = true; }
        require(nullTargetNpe);

        boolean nullReceiverNpe = false;
        try { ((ArrayList) null).toArray(new Object[0]); }
        catch (NullPointerException expected) { nullReceiverNpe = true; }
        require(nullReceiverNpe);

        Iterator iterator = defaultList.iterator();
        require(!iterator.hasNext());
        boolean exhaustedNsee = false;
        try { iterator.next(); }
        catch (NoSuchElementException expected) { exhaustedNsee = true; }
        require(exhaustedNsee);

        MisleadingSizeList misleading = new MisleadingSizeList();
        require(misleading.size() == 3);
        Object[] privateSizeTarget = new Object[0];
        require(misleading.toArray(privateSizeTarget) == privateSizeTarget);
    }
}
