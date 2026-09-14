import java.util.Iterator;
import java.util.Queue;
import java.util.concurrent.ConcurrentLinkedQueue;

public final class ConcurrentLinkedQueueMain {
    private static int checks;
    private static void check(boolean value) { if (!value) throw new AssertionError(); ++checks; }

    public static void main(String[] args) {
        Queue<Integer> q = new ConcurrentLinkedQueue<Integer>();
        check(q.isEmpty());
        check(q.size() == 0);
        check(q.poll() == null);
        check(q.add(7));
        check(q.add(7));
        check(q.add(9));
        check(q.size() == 3 && !q.isEmpty());
        Iterator<Integer> snapshot = q.iterator();
        check(q.poll().intValue() == 7);
        check(snapshot.hasNext() && snapshot.next().intValue() == 7);
        check(snapshot.hasNext() && snapshot.next().intValue() == 7);
        check(snapshot.hasNext() && snapshot.next().intValue() == 9);
        check(!snapshot.hasNext());
        try { snapshot.next(); throw new AssertionError(); }
        catch (java.util.NoSuchElementException expected) { ++checks; }
        check(q.poll().intValue() == 7);
        check(q.poll().intValue() == 9);
        check(q.add(11));
        check(q.poll().intValue() == 11);
        check(q.poll() == null && q.isEmpty() && q.size() == 0);
        try { q.add(null); throw new AssertionError(); }
        catch (NullPointerException expected) { ++checks; }
        check(q.isEmpty());
        if (checks != 20) throw new AssertionError();
    }
}
