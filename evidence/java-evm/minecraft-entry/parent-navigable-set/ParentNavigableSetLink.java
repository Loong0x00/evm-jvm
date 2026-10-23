import java.util.Set;
import java.util.SortedSet;
import java.util.NavigableSet;
import java.util.HashSet;
import java.util.Comparator;
import java.util.Iterator;
import java.util.regex.Pattern;

/** Generated custom set used only for hierarchy/ordinary dispatch, not real navigation. */
public final class ParentNavigableSetLink {
    interface Tagged extends NavigableSet<Object> { int value(); }
    static final class LocalSet extends HashSet<Object> implements Tagged {
        final int answer;
        LocalSet(int answer) { super(); this.answer = answer; }
        public int value() { return answer; }
        public int size() { return answer; }
        public Comparator<Object> comparator() { throw new UnsupportedOperationException(); }
        public Object first() { throw new UnsupportedOperationException(); }
        public Object last() { throw new UnsupportedOperationException(); }
        public SortedSet<Object> subSet(Object a,Object b) { throw new UnsupportedOperationException(); }
        public SortedSet<Object> headSet(Object a) { throw new UnsupportedOperationException(); }
        public SortedSet<Object> tailSet(Object a) { throw new UnsupportedOperationException(); }
        public Object lower(Object a) { throw new UnsupportedOperationException(); }
        public Object floor(Object a) { throw new UnsupportedOperationException(); }
        public Object ceiling(Object a) { throw new UnsupportedOperationException(); }
        public Object higher(Object a) { throw new UnsupportedOperationException(); }
        public Object pollFirst() { throw new UnsupportedOperationException(); }
        public Object pollLast() { throw new UnsupportedOperationException(); }
        public NavigableSet<Object> descendingSet() { throw new UnsupportedOperationException(); }
        public Iterator<Object> descendingIterator() { throw new UnsupportedOperationException(); }
        public NavigableSet<Object> subSet(Object a,boolean x,Object b,boolean y) { throw new UnsupportedOperationException(); }
        public NavigableSet<Object> headSet(Object a,boolean x) { throw new UnsupportedOperationException(); }
        public NavigableSet<Object> tailSet(Object a,boolean x) { throw new UnsupportedOperationException(); }
    }
    private static void check(boolean ok) { if (!ok) throw new ArithmeticException(); }
    public static void main(String[] args) {
        Object object = new LocalSet(17);
        check(object instanceof Set && object instanceof SortedSet && object instanceof NavigableSet);
        Tagged set = (Tagged) object;
        check(set.value() == 17 && ((Set) object).size() == 17);
        SortedSet[] sorted = new SortedSet[] {set};
        NavigableSet[] nav = new NavigableSet[] {set};
        SortedSet[] sortedCopy = sorted.clone();
        NavigableSet[] navCopy = nav.clone();
        check(sortedCopy != sorted && navCopy != nav && sortedCopy[0] == set && navCopy[0] == set);
        try { NavigableSet bad = (NavigableSet) new Object(); throw new ArithmeticException(); }
        catch (ClassCastException expected) { }
        try { ((Tagged) null).value(); throw new ArithmeticException(); }
        catch (NullPointerException expected) { }
        check(Pattern.compile("^[a-z0-9_]+$").matcher("set_1").matches());
        check("x\r\n".replaceAll("[^\n]+$", "X").equals("X\r\n"));
        check("x\r\n".replaceAll("^x\r$", "X").equals("x\r\n"));
    }
}
