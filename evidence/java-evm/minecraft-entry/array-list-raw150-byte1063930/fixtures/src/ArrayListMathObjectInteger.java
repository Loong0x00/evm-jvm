import java.util.ArrayList;
public final class ArrayListMathObjectInteger {
    public static void main(String[] args) {
        Object first = new Object();
        Object second = new Object();
        ArrayList list = new ArrayList(3);
        if (Math.max(-42, 17) != 17 || Math.min(-42, 17) != -42) throw new AssertionError("Math max/min");
        if (Integer.parseInt("2147483647") != 2147483647) throw new AssertionError("Integer max");
        if (Integer.parseInt("-2147483648") != -2147483648) throw new AssertionError("Integer min");
        if (!first.equals(first) || first.equals(second)) throw new AssertionError("Object identity");
        if (!list.isEmpty() || list.size() != 0) throw new AssertionError("ArrayList control");
    }
}
