public final class TL0Initialization {
  static int effect;

  static boolean yes() { return true; }

  static class Problem extends RuntimeException {
    Problem() { super(); }
  }

  static final class Broken {
    Broken() { effect = 7; throw new Problem(); }
  }

  static final class BeforeNew {
    static { effect = 1; }
    BeforeNew() { effect += 2; }
  }

  static final class WrapInit {
    static { if (yes()) throw new Problem(); }
    static int value = 9;
  }

  static final class CustomError extends Error {
    CustomError() { super(); }
  }

  static final class ErrorInit {
    static { if (yes()) throw new CustomError(); }
    static int value = 9;
  }

  static final class SecondInit {
    static { if (yes()) throw new Problem(); }
    static int value = 9;
  }

  public static int failingConstructor() {
    effect = 0;
    try { new Broken(); return 0; }
    catch (Problem expected) { return effect; }
  }

  public static int initBeforeNew() {
    effect = 0;
    BeforeNew made = new BeforeNew();
    return made != null ? effect : 0;
  }

  public static int wrapsNonError() {
    try { return WrapInit.value; }
    catch (ExceptionInInitializerError wrapped) { return 1; }
  }

  public static int propagatesCustomError() {
    try { return ErrorInit.value; }
    catch (CustomError exact) { return 1; }
  }

  public static int secondUse() {
    int score = 0;
    try { score += SecondInit.value; }
    catch (ExceptionInInitializerError first) { score += 1; }
    try { score += SecondInit.value; }
    catch (NoClassDefFoundError second) { score += 2; }
    return score;
  }
}
