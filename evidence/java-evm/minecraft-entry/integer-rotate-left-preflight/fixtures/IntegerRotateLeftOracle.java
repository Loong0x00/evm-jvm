/** Generated-only differential oracle; run only with trusted stage vector arguments. */
public final class IntegerRotateLeftOracle {
  private IntegerRotateLeftOracle() {}
  public static void main(String[] operands) {
    for (String operand : operands) {
      int separator = operand.indexOf(',');
      if (separator != 8) throw new IllegalArgumentException();
      int value = (int) Long.parseLong(operand.substring(0, separator), 16);
      int distance = Integer.parseInt(operand.substring(separator + 1));
      System.out.println(Integer.rotateLeft(value, distance));
    }
  }
}
