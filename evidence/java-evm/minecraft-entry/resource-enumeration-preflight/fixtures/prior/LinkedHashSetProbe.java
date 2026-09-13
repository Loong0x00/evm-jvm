import java.util.Iterator;
import java.util.LinkedHashSet;
import java.util.NoSuchElementException;

public final class LinkedHashSetProbe {
    static int result;

    static final class Equal {
        final int value;
        Equal(int value) { this.value = value; }
        public boolean equals(Object other) {
            return other instanceof Equal && value == ((Equal) other).value;
        }
        public int hashCode() { return 0; }
    }

    public static void main(String[] args) {
        LinkedHashSet<Object> set = new LinkedHashSet<Object>(0);
        Equal first = new Equal(1);
        Equal second = new Equal(2);
        if (!set.add(first) || !set.add(null) || !set.add(second)) return;
        if (set.add(new Equal(1)) || set.size() != 3 || set.isEmpty()) return;
        Iterator<Object> left = set.iterator();
        Iterator<Object> right = set.iterator();
        if (left.next() != first || right.next() != first) return;
        if (left.next() != null || !left.hasNext() || left.next() != second || left.hasNext()) return;
        try {
            left.next();
            return;
        } catch (NoSuchElementException expected) {
            result = right.hasNext() && right.next() == null && right.hasNext() ? 631 : -1;
        }
    }
}
