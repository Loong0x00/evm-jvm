import java.util.NavigableSet;
/** A valid interface-typed call outside the link-only profile. */
public final class ParentNavigableSetOmitted {
    public static void main(String[] args) {
        NavigableSet<Object> set = new ParentNavigableSetLink.LocalSet(1);
        Object token = new Object();
        if (set == null || token == null) throw new ArithmeticException();
        set.lower(token);
    }
}
