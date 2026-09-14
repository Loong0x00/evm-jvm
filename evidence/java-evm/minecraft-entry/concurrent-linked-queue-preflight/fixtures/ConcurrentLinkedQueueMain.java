import java.util.Iterator;
import java.util.Queue;
import java.util.concurrent.ConcurrentLinkedQueue;

public final class ConcurrentLinkedQueueMain {
    private static int checks;
    private static void check(boolean value) { if (!value) throw new AssertionError(); ++checks; }

    public static void main(String[] args) {
        Queue<Object> q = new ConcurrentLinkedQueue<Object>();
        Object first = "first";
        Object last = "last";
        Object addedLater = "added-later";
        check(q.isEmpty());
        check(q.size() == 0);
        check(q.poll() == null);
        check(q.add(first));
        check(q.add(first));
        check(q.add(last));
        check(q.size() == 3 && !q.isEmpty());
        Iterator<Object> snapshot = q.iterator();
        check(q.poll() == first);
        check(snapshot.hasNext() && snapshot.next() == first);
        check(snapshot.hasNext() && snapshot.next() == first);
        check(snapshot.hasNext() && snapshot.next() == last);
        check(!snapshot.hasNext());
        try { snapshot.next(); throw new AssertionError(); }
        catch (java.util.NoSuchElementException expected) { ++checks; }
        check(q.poll() == first);
        check(q.poll() == last);
        check(q.add(addedLater));
        check(q.poll() == addedLater);
        check(q.poll() == null && q.isEmpty() && q.size() == 0);
        try { q.add(null); throw new AssertionError(); }
        catch (NullPointerException expected) { ++checks; }
        check(q.isEmpty());
        if (checks != 20) throw new AssertionError();
    }
}
