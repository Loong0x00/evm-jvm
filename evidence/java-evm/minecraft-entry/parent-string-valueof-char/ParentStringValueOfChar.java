import java.util.*;
/** Generated-only: no original classes or oracle-as-input. */
public final class ParentStringValueOfChar {
    private static void check(boolean ok) { if (!ok) throw new ArithmeticException(); }
    public static void main(String[] args) {
        int[] units = {44,0,9,10,13,32,48,65,127,128,255,256,32767,32768,55295,55296,56319,56320,57343,57344,65535};
        for (int i = 0; i < units.length; ++i) {
            char unit = (char) units[i];
            String a = String.valueOf(unit);
            String b = String.valueOf(unit);
            check(a != b && a.length() == 1 && !a.isEmpty() && a.charAt(0) == unit);
            check(a.equals(b) && a.hashCode() == units[i] && a.compareTo(b) == 0);
            check(a.getClass() == String.class && a instanceof CharSequence);
            char[] source = {unit};
            String c = new String(source);
            source[0] = (char) (unit + 1);
            check(a.equals(c) && c.charAt(0) == unit);
            String copy = new String(a);
            check(copy != a && copy.equals(a) && copy.charAt(0) == unit);
            check(a.intern() == b.intern());
            Object[] backing = {a, null};
            List list = Arrays.asList(backing);
            Iterator iterator = list.iterator();
            backing[0] = b;
            check(iterator.next() == b && iterator.next() == null && !iterator.hasNext());
            check(Collections.singletonList(a).iterator().next() == a);
        }
        check(String.valueOf(',').equals(","));
        check(String.valueOf('0').equals("0"));
        // Existing charAt bounds are a raw profile refusal, not a Java fault here;
        // keep that as a separate negative control instead of widening this task.
        try { ((String) null).length(); throw new ArithmeticException(); }
        catch (NullPointerException expected) { }
    }
}
