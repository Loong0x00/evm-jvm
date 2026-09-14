public final class NoInitClassAsSubclassProbe {
  static final class Target { static { if (true) throw new ArithmeticException(); } }
  public static void main(String[] ignored) { Target.class.asSubclass(Object.class); }
}
