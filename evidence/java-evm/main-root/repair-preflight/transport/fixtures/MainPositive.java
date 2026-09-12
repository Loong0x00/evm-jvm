public final class MainPositive {
  static Object saved; static int state;
  static { state = 11; }
  public static void main() {} // valid overload, not the root
  public static void main(String[] args) {
    if (args == null || args.length != 0 || !(args instanceof String[])) throw new RuntimeException();
    saved = args; MainHelper.check(args);
    for (int i = 0; i < 32; i++) state += i;
    if (saved != args || state != 507) throw new RuntimeException();
  }
}
