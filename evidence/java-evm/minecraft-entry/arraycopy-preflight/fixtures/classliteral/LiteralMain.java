public class LiteralMain {
  static class Tracker { static int seen; }
  static class Target { static { Tracker.seen = 1; } static void touch() {} }
  interface Face { interface Inner {} }
  public static void main(String[] ignored) {
    Object o = Target.class;
    Class a = (Class)o, b = Target.class, c = Face.Inner.class;
    if (a != b || Tracker.seen != 0) throw new RuntimeException();
    if (!a.getName().equals("LiteralMain$Target")) throw new RuntimeException();
    if (!c.getName().equals("LiteralMain$Face$Inner")) throw new RuntimeException();
    Target.touch();
    if (Tracker.seen != 1) throw new RuntimeException();
  }
}
