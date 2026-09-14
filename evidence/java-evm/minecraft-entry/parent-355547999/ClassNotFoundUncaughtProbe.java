public final class ClassNotFoundUncaughtProbe {
  public static void main(String[] ignored) throws Exception {
    Class.forName("missing.parent.UncaughtForName");
  }
}
