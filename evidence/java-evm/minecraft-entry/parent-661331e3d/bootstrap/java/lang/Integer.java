package java.lang;
public final class Integer extends Number implements Comparable<Integer>, java.io.Serializable {
  public static final int MIN_VALUE = 0x80000000;
  public static final int MAX_VALUE = 0x7fffffff;
  public static final int SIZE = 32;
  public static final int BYTES = 4;
  private final int value;
  public Integer(int value) { this.value = value; }
  public Integer(String s) { this.value = parseInt(s); }
  public int intValue() { return value; }
  public long longValue() { return (long)value; }
  public float floatValue() { return (float)value; }
  public double doubleValue() { return (double)value; }
  public byte byteValue() { return (byte)value; }
  public short shortValue() { return (short)value; }
  public boolean equals(Object obj) { return obj instanceof Integer && value == ((Integer)obj).value; }
  public int hashCode() { return value; }
  public static int hashCode(int value) { return value; }
  public static int compare(int x, int y) { return x < y ? -1 : (x == y ? 0 : 1); }
  public int compareTo(Integer other) { return compare(value, other.value); }
  public static int parseInt(String s) {
    if (s == null) throw new NumberFormatException();
    int len = s.length();
    if (len == 0) throw new NumberFormatException();
    int i = 0, limit = -MAX_VALUE;
    char first = s.charAt(0);
    if (first == '-') { limit = MIN_VALUE; i++; }
    else if (first == '+') i++;
    if (i == len) throw new NumberFormatException();
    int multmin = limit / 10;
    int result = 0;
    while (i < len) {
      int digit = s.charAt(i++) - '0';
      if (digit < 0 || digit > 9 || result < multmin) throw new NumberFormatException();
      result *= 10;
      if (result < limit + digit) throw new NumberFormatException();
      result -= digit;
    }
    return first == '-' ? result : -result;
  }
}
