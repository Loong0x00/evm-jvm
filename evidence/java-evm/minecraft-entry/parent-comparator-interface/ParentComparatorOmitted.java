import java.util.Comparator;
/** reversed() is deliberately outside this compare-only interface profile. */
public final class ParentComparatorOmitted {
    static final class Lengths implements Comparator<String> {
        public int compare(String a, String b) { return a.length() - b.length(); }
    }
    public static void main(String[] args) {
        Comparator<String> cmp = new Lengths();
        if (cmp.compare("a", "bb") != -1) throw new ArithmeticException();
        if (!cmp.equals(cmp) || cmp.equals(new Lengths())) throw new ArithmeticException();
        cmp.reversed();
    }
}
