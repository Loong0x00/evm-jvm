package p57;

public final class ValueOfCharOracle {
  private static final char[] REPRESENTATIVES = {
    0, 9, 10, 13, 32, 48, 65, 127, 128, 255, 256,
    0x7fff, 0x8000, 0xd7ff, 0xd800, 0xdbff,
    0xdc00, 0xdfff, 0xe000, 0xffff
  };

  private static void check(char value) {
    String first = String.valueOf(value);
    String second = String.valueOf(value);
    if (first == null || first.length() != 1 || first.charAt(0) != value) {
      throw new AssertionError("UTF-16 code unit mismatch: " + (int)value);
    }
    if (first == second) throw new AssertionError("factory identity was cached");
    if (!first.equals(second) || first.hashCode() != second.hashCode()
        || first.compareTo(second) != 0 || first.toString() != first) {
      throw new AssertionError("ordinary String behavior mismatch: " + (int)value);
    }
    String copied = new String(new char[] { value });
    if (!first.equals(copied) || first.charAt(0) != copied.charAt(0)) {
      throw new AssertionError("char[] constructor mismatch: " + (int)value);
    }
  }

  public static void main(String[] args) {
    for (char value : REPRESENTATIVES) check(value);
    for (int codeUnit = 0; codeUnit <= 0xffff; codeUnit++) check((char) codeUnit);
    System.out.println("PASS all 65536 UTF-16 code units");
  }
}
