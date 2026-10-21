import java.util.ArrayList;
public final class ArrayListMathObjectInteger {
    public static void main(String[] args) {
        Object first = new Object();
        Object second = new Object();
        ArrayList list = new ArrayList(3);
        if (Math.max(-42, 17) != 17 || Math.min(-42, 17) != -42) throw new AssertionError("Math int max/min");
        if (Double.doubleToRawLongBits(Math.sqrt(4.0d)) != 0x4000000000000000L) throw new AssertionError("Math.sqrt control");
        if (Double.doubleToRawLongBits(Math.sin(0.0d)) != 0L) throw new AssertionError("Math.sin control");
        if (Double.doubleToRawLongBits(Math.asin(0.0d)) != 0L) throw new AssertionError("Math.asin control");
        if (Double.doubleToRawLongBits(Math.cos(0.0d)) != 0x3ff0000000000000L) throw new AssertionError("Math.cos control");
        if (Integer.parseInt("2147483647") != 2147483647) throw new AssertionError("Integer max");
        if (Integer.parseInt("-2147483648") != -2147483648) throw new AssertionError("Integer min");
        if (!first.equals(first) || first.equals(second)) throw new AssertionError("Object identity");
        if (!list.isEmpty() || list.size() != 0) throw new AssertionError("ArrayList control");
    }
}
