public final class TL0Identity {
  static Problem saved;
  static Problem[] array;

  static class Problem extends RuntimeException {
    int value;
    Problem(int value) { super(); this.value = value; }
  }

  static final class KnownChild extends ArithmeticException {
    KnownChild() { super(); }
  }

  static void callThrow(Problem value) { throw value; }

  public static int localCatch() {
    Problem made = new Problem(4);
    try { throw made; } catch (Problem caught) { return caught == made ? 1 : 0; }
  }

  public static int fieldCatch() {
    saved = new Problem(5);
    try { throw saved; } catch (Problem caught) { return caught == saved ? 1 : 0; }
  }

  public static int arrayCatch() {
    Problem made = new Problem(6);
    array = new Problem[] { made };
    try { throw array[0]; } catch (Problem caught) { return caught == made ? 1 : 0; }
  }

  public static int callUnwind() {
    Problem made = new Problem(7);
    try { callThrow(made); return 0; }
    catch (Problem caught) { return caught == made && caught.value == 7 ? 1 : 0; }
  }

  public static int rethrow() {
    Problem made = new Problem(8);
    try {
      try { throw made; }
      catch (Problem caught) { if (caught != made) return 0; throw caught; }
    } catch (Problem caughtAgain) { return caughtAgain == made ? 1 : 0; }
  }

  public static int knownSubclassCatch() {
    KnownChild made = new KnownChild();
    try { throw made; }
    catch (ArithmeticException caught) { return caught == made ? 1 : 0; }
  }
}
