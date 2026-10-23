import java.util.*;
import java.io.Serializable;
/** Generated constructor-only witness; private storage audited separately from checkpoints. */
public final class ParentArrayListDefault {
    private static void check(boolean ok) { if (!ok) throw new ArithmeticException(); }
    public static void main(String[] args) {
        ArrayList first = new ArrayList();
        ArrayList second = new ArrayList();
        ArrayList zero = new ArrayList(0);
        ArrayList positive = new ArrayList(3);
        check(first != second && first.size() == 0 && second.size() == 0);
        check(zero.size() == 0 && positive.size() == 0);
        Collection collection = first;
        List list = second;
        check(collection.isEmpty() && list.isEmpty());
        check(first instanceof RandomAccess && first instanceof Cloneable && first instanceof Serializable);
        try { new ArrayList(-1); throw new ArithmeticException(); }
        catch (IllegalArgumentException expected) { }
        ArrayList[] array = new ArrayList[] {first, second, zero, positive};
        ArrayList[] copy = array.clone();
        check(copy != array && copy[0] == first && copy[1] == second && copy[2] == zero && copy[3] == positive);
        try { ArrayList bad = (ArrayList) new Object(); throw new ArithmeticException(); }
        catch (ClassCastException expected) { }
        try { ((List) null).size(); throw new ArithmeticException(); }
        catch (NullPointerException expected) { }
    }
}
