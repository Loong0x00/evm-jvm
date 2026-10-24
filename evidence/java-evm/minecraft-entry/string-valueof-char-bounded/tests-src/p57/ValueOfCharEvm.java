package p57;

public final class ValueOfCharEvm {
  private static void verify(char value) {
    String result = String.valueOf(value);
    String second = String.valueOf(value);
    if (result.length() != 1 || result.charAt(0) != value || result == second) {
      throw new ArithmeticException("String.valueOf(char) UTF-16 unit/identity mismatch");
    }
    if (!result.equals(second) || result.hashCode() != second.hashCode()
        || result.compareTo(second) != 0 || result.toString() != result) {
      throw new ArithmeticException("ordinary String methods mismatch");
    }
    char[] source = { value };
    String copied = new String(source);
    String copyOfCopy = new String(copied);
    source[0] = (char)(value ^ 1);
    if (copied.charAt(0) != value || !copied.equals(copyOfCopy)
        || copied.compareTo(copyOfCopy) != 0
        || copied.intern() != copyOfCopy.intern()) {
      throw new ArithmeticException("constructor-copy/intern controls mismatch");
    }
  }
  public static void main(String[] args) {
    verify((char) 44);
    verify((char) 0);
    verify((char) 255);
    verify((char) 256);
    verify((char) 0xd800);
    verify((char) 0xdc00);
    verify((char) 0xffff);
  }
}
