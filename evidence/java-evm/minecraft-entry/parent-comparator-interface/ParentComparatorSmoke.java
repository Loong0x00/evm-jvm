import java.util.Comparator;
import java.util.regex.Pattern;

/** Parent-owned generated-only compare/bridge/null/high-index-array witness. */
public final class ParentComparatorSmoke {
    interface Tagged<T> extends Comparator<T> { }
    static final class Lengths implements Tagged<String> {
        final int direction;
        Lengths(int direction) { this.direction = direction; }
        public int compare(String a, String b) {
            if (a == b) return 0;
            if (a == null) return -direction;
            if (b == null) return direction;
            return (a.length() - b.length()) * direction;
        }
    }
    private static void check(boolean ok) { if (!ok) throw new ArithmeticException(); }
    public static void main(String[] args) {
        Comparator<String> cmp = new Lengths(-1);
        check(cmp.compare("a", "bbb") == 2);
        check(cmp.compare("bbbb", "b") == -3);
        check(cmp.compare("aa", "bb") == 0);
        check(cmp.compare(null, "x") == 1 && cmp.compare("x", null) == -1);
        check(cmp.compare(null, null) == 0);
        check(cmp instanceof Tagged && cmp instanceof Comparator);
        try { ((Comparator) cmp).compare(new Object(), "x"); throw new ArithmeticException(); }
        catch (ClassCastException expected) { }
        try { ((Comparator) null).compare("a", "b"); throw new ArithmeticException(); }
        catch (NullPointerException expected) { }
        Comparator[] source = new Comparator[] {cmp};
        Comparator[] copy = source.clone();
        check(source != copy && copy[0] == cmp);
        check(Pattern.compile("^[a-z0-9_]+$").matcher("cmp_1").matches());
        check("x\r\n".replaceAll("[^\n]+$", "X").equals("X\r\n"));
        check("x\r\n".replaceAll("^x\r$", "X").equals("x\r\n"));
    }
}
