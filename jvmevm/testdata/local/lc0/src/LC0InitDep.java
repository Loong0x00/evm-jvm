public final class LC0InitDep {
  static int count;
  static int value;
  static {
    count++;
    try { value = 10 / (count - 1); }
    catch (ArithmeticException expected) { value = 9; }
  }
}
