public final class IntegerProbe {
  static int result;
  private static int fail(int n) { result = n; return n; }
  public static void main(String[] args) {
    if (Integer.parseInt("1") != 1) { fail(1); return; }
    if (Integer.parseInt("8") != 8) { fail(2); return; }
    if (Integer.parseInt("+7") != 7 || Integer.parseInt("-0") != 0) { fail(3); return; }
    if (Integer.parseInt("0000000012") != 12) { fail(4); return; }
    if (Integer.parseInt("2147483647") != Integer.MAX_VALUE) { fail(5); return; }
    if (Integer.parseInt("-2147483648") != Integer.MIN_VALUE) { fail(6); return; }
    try { Integer.parseInt(""); fail(7); return; } catch (NumberFormatException e) {} catch (IllegalArgumentException e) { fail(8); return; }
    try { Integer.parseInt(null); fail(9); return; } catch (NumberFormatException e) {}
    try { new Integer((String)null); fail(10); return; } catch (NumberFormatException e) {}
    try { Integer.parseInt("+"); fail(11); return; } catch (NumberFormatException e) {}
    try { Integer.parseInt("12x"); fail(12); return; } catch (NumberFormatException e) {}
    try { Integer.parseInt("2147483648"); fail(13); return; } catch (NumberFormatException e) {}
    try { Integer.parseInt("-2147483649"); fail(14); return; } catch (NumberFormatException e) {}
    Integer a = new Integer(5), b = new Integer("5"); Number n = a;
    if (a.intValue()!=5 || n.longValue()!=5L || n.floatValue()!=5.0f || n.doubleValue()!=5.0d || n.byteValue()!=(byte)5 || n.shortValue()!=(short)5) { fail(15); return; }
    if (!a.equals(b) || a.hashCode()!=5 || Integer.hashCode(6)!=6 || Integer.compare(2,3)>=0 || Integer.compare(3,3)!=0 || a.compareTo(b)!=0) { fail(16); return; }
    Comparable c = a;
    if (c.compareTo(b) != 0) { fail(17); return; }
  }
}
