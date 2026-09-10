public final class SC0Chars {
  public static int empty() {
    return new String(new char[0]).length();
  }

  public static int asciiLength() {
    return new String(new char[]{'h', 'e', 'l', 'l', 'o'}).length();
  }

  public static int nulUnits() {
    String value = new String(new char[]{'A', 0, 'B'});
    return value.length() == 3 && value.charAt(1) == 0 ? 1 : 0;
  }

  public static int surrogatePair() {
    String value = new String(new char[]{'\ud83d', '\ude00'});
    return value.length() == 2 && value.charAt(0) == '\ud83d' && value.charAt(1) == '\ude00' ? 1 : 0;
  }

  public static int isolatedHigh() {
    return new String(new char[]{'\ud800'}).charAt(0);
  }

  public static int isolatedLow() {
    return new String(new char[]{'\udc00'}).charAt(0);
  }

  public static int defensive() {
    char[] source = new char[]{'a', 'b', 'c'};
    String value = new String(source);
    source[0] = 'z';
    return value.charAt(0) * 1000 + value.charAt(2);
  }

  public static int hashCache() {
    String value = new String(new char[]{'B', 'B'});
    int first = value.hashCode();
    int second = value.hashCode();
    return first == second ? second : 0;
  }
}
