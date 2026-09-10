public final class TL0ConstructorSelf {
  static Escaped escaped;
  static InitSelf initSaved;

  static final class Direct extends RuntimeException {
    int value;
    Direct() { super(); value = 101; throw this; }
  }

  static final class Through extends RuntimeException {
    int value;
    Through() { super(); value = 102; throwThrough(this); }
  }

  static final class Escaped extends RuntimeException {
    int value;
    Escaped() { super(); value = 103; escaped = this; throw this; }
  }

  static final class InitSelf extends RuntimeException {
    int value;
    InitSelf() { super(); value = 201; initSaved = this; throw this; }
  }

  static final class InitHolder {
    static { if (yes()) new InitSelf(); }
    static int value = 9;
  }

  static boolean yes() { return true; }
  static void throwThrough(Through value) { throw value; }

  public static int direct() {
    try { new Direct(); return 0; }
    catch (Direct exact) { return exact.value; }
  }

  public static int throughCall() {
    try { new Through(); return 0; }
    catch (Through exact) { return exact.value; }
  }

  public static int escapedAfterFailure() {
    escaped = null;
    try { new Escaped(); }
    catch (Escaped first) { if (first != escaped) return 0; }
    try { throw escaped; }
    catch (Escaped second) { return second == escaped ? second.value : 0; }
  }

  public static int inClassInit() {
    initSaved = null;
    try { return InitHolder.value; }
    catch (ExceptionInInitializerError wrapped) {
      return initSaved != null ? initSaved.value : 0;
    }
  }
}
