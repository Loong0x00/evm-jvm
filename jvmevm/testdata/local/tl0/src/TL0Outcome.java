public final class TL0Outcome {
  static final class Problem extends RuntimeException {
    Problem() { super(); }
  }

  static final class KnownChild extends ArithmeticException {
    KnownChild() { super(); }
  }

  public static int exactKnown() { throw new ArithmeticException(); }
  public static int custom() { throw new Problem(); }
  public static int subclassKnown() { throw new KnownChild(); }
}
