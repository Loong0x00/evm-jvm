import java.util.*;
/** Generated profile-quota test only; stock Java heap limits are not an oracle for these caps. */
public final class ParentArrayListGrowOOM {
    private static void check(boolean ok) { if (!ok) throw new ArithmeticException(); }
    public static void main(String[] args) {
        Object value = new Object();
        ArrayList list = new ArrayList();
        for (int i = 0; i < 10; ++i) list.add(value);
        Iterator stale = list.iterator();
        ArrayList zero = new ArrayList(0);
        Iterator oldEmpty = zero.iterator();
        byte[] a = new byte[65536];
        byte[] b = new byte[65536];
        byte[] c = new byte[65536];
        byte[] d = new byte[65500];
        check(a.length + b.length + c.length + d.length == 262108);
        boolean full = false;
        for (int i = 0; i < 64; ++i) {
            try { byte[] remainder = new byte[1]; check(remainder.length == 1); }
            catch (OutOfMemoryError expected) { full = true; break; }
        }
        check(full);
        boolean failed = false;
        try { list.add(value); }
        catch (OutOfMemoryError expected) { failed = true; }
        check(failed && list.size() == 10 && !list.isEmpty());
        try { stale.next(); throw new ArithmeticException(); }
        catch (ConcurrentModificationException expected) { }
        failed = false;
        try { zero.add(value); }
        catch (OutOfMemoryError expected) { failed = true; }
        check(failed && zero.size() == 0 && zero.isEmpty());
        try { oldEmpty.next(); throw new ArithmeticException(); }
        catch (ConcurrentModificationException expected) { }
        Iterator fresh = list.iterator();
        int count = 0;
        while (fresh.hasNext()) { check(fresh.next() == value); ++count; }
        check(count == 10);
    }
}
