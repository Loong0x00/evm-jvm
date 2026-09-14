import java.util.Collection;
import java.util.Iterator;
import java.util.List;
import java.util.NoSuchElementException;
import java.util.RandomAccess;
import java.util.concurrent.CopyOnWriteArrayList;

/** Trusted generated-only Java 8 oracle/guest fixture. */
public final class CopyOnWriteArrayListMain {
  private static void check(boolean value) { if (!value) throw new Error(); }

  public static void main(String[] ignored) {
    CopyOnWriteArrayList<Object> list = new CopyOnWriteArrayList<Object>();
    check(list instanceof List);
    check(list instanceof Collection);
    check(list instanceof RandomAccess);
    check(list.isEmpty());
    check(list.size() == 0);

    Iterator<Object> empty = list.iterator();
    check(!empty.hasNext());
    try { empty.next(); throw new Error(); } catch (NoSuchElementException expected) { }

    Object first = new Object();
    Object second = new Object();
    check(list.add(first));
    check(list.add(first));
    check(list.add(null));
    Iterator<Object> snapshot = list.iterator();
    check(list.add(second));
    check(!list.isEmpty());
    check(list.size() == 4);

    check(snapshot.hasNext()); check(snapshot.next() == first);
    check(snapshot.hasNext()); check(snapshot.next() == first);
    check(snapshot.hasNext()); check(snapshot.next() == null);
    check(!snapshot.hasNext());
    try { snapshot.next(); throw new Error(); } catch (NoSuchElementException expected) { }

    Iterator<Object> current = list.iterator();
    check(current.next() == first);
    check(current.next() == first);
    check(current.next() == null);
    check(current.next() == second);
    check(!current.hasNext());
  }
}
