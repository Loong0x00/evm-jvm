package probe;

import java.util.ArrayList;
import java.util.ConcurrentModificationException;
import java.util.Iterator;
import java.util.List;
import java.util.NoSuchElementException;

/** Generated-fixture-only behavioral checks; no host execution authority. */
public final class ArrayListAddProbe {
    private static void fail() { int zero = 0; int ignored = 1 / zero; }

    private static void check(boolean condition) { if (!condition) fail(); }

    private static final class Liar extends ArrayList {
        public int size() { return 777; }
    }

    public static void main(String[] args) {
        ArrayList defaults = new ArrayList();
        check(defaults.isEmpty());
        Object a = new Object();
        Object b = new Object();
        List appendView = defaults;
        check(appendView.add(a));
        check(appendView.add(null));
        check(appendView.add(b));
        check(defaults.size() == 3 && !defaults.isEmpty());

        Iterator first = defaults.iterator();
        Iterator second = defaults.iterator();
        check(first.hasNext() && first.next() == a);
        check(second.hasNext() && second.next() == a);
        check(first.next() == null && second.next() == null);
        check(first.next() == b && second.next() == b);
        check(!first.hasNext() && !second.hasNext());
        try { first.next(); fail(); } catch (NoSuchElementException expected) { }

        Object tail = new Object();
        Object[] target = new Object[5];
        target[4] = tail;
        check(defaults.toArray(target) == target);
        check(target[0] == a && target[1] == null && target[2] == b);
        check(target[3] == null && target[4] == tail);
        try { defaults.toArray(null); fail(); } catch (NullPointerException expected) { }

        Iterator beforeAppend = defaults.iterator();
        check(beforeAppend.next() == a);
        Object c = new Object();
        check(defaults.add(c));
        try { beforeAppend.next(); fail(); } catch (ConcurrentModificationException expected) { }

        ArrayList initiallyEmpty = new ArrayList(0);
        Iterator emptyCursor = initiallyEmpty.iterator();
        check(!emptyCursor.hasNext());
        check(initiallyEmpty.add(null));
        check(emptyCursor.hasNext());
        try { emptyCursor.next(); fail(); } catch (ConcurrentModificationException expected) { }
        Iterator fresh = initiallyEmpty.iterator();
        check(fresh.next() == null && !fresh.hasNext());
        try { fresh.next(); fail(); } catch (NoSuchElementException expected) { }

        ArrayList exhaustedOwner = new ArrayList();
        check(exhaustedOwner.add(a));
        Iterator exhaustedCursor = exhaustedOwner.iterator();
        check(exhaustedCursor.next() == a && !exhaustedCursor.hasNext());
        check(exhaustedOwner.add(b));
        try { exhaustedCursor.next(); fail(); } catch (ConcurrentModificationException expected) { }

        ArrayList small = new ArrayList(2);
        Object[] refs = new Object[48];
        for (int i = 0; i < refs.length; i++) {
            refs[i] = new Object();
            check(small.add(refs[i]));
            check(small.size() == i + 1);
        }
        Iterator ordered = small.iterator();
        for (int i = 0; i < refs.length; i++) check(ordered.next() == refs[i]);
        check(!ordered.hasNext());

        Liar liar = new Liar();
        check(liar.size() == 777 && liar.isEmpty());
        Iterator liarCursor = liar.iterator();
        check(!liarCursor.hasNext());
        Object only = new Object();
        check(liar.add(only));
        check(liar.size() == 777 && !liar.isEmpty());
        check(liarCursor.hasNext());
        try { liarCursor.next(); fail(); } catch (ConcurrentModificationException expected) { }
        Iterator liarFresh = liar.iterator();
        check(liarFresh.next() == only && !liarFresh.hasNext());
    }
}
