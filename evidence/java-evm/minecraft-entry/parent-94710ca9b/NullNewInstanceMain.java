public final class NullNewInstanceMain {
  static int result;
  public static void main(String[] ignored) throws Exception {
    Class<?> c = null;
    try { c.newInstance(); result = 1; }
    catch (NullPointerException expected) { result = 7; }
    if (result != 7) throw new Error();
  }
}
