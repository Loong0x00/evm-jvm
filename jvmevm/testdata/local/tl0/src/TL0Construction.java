public final class TL0Construction {
  static int effects;

  static class Problem extends RuntimeException {
    int value;
    Problem() { super(); }
    Problem(int value) { super(); this.value = value; }
    Problem(int value, boolean effect) {
      super();
      this.value = value;
      if (effect) effects += value;
    }
  }

  static final class Child extends Problem {
    int extra;
    Child(int value, int extra) { super(value); this.extra = extra; }
  }

  public static int exactException() {
    Exception made = new Exception();
    try { throw made; } catch (Exception caught) { return caught == made ? 1 : 0; }
  }

  public static int exactArithmetic() {
    ArithmeticException made = new ArithmeticException();
    try { throw made; } catch (ArithmeticException caught) { return caught == made ? 1 : 0; }
  }

  public static int customFields(int value) {
    Problem made = new Problem(value);
    try { throw made; } catch (Problem caught) { return caught.value; }
  }

  public static int hierarchyFields() {
    Child made = new Child(12, 25);
    try { throw made; } catch (Problem caught) {
      Child child = (Child) caught;
      return child.value + child.extra;
    }
  }

  public static int distinct() {
    Problem first = new Problem();
    Problem second = new Problem();
    return first != second ? 1 : 0;
  }

  public static int ctorEffects() {
    effects = 0;
    Problem made = new Problem(11, true);
    return made.value == 11 ? effects : 0;
  }
}
