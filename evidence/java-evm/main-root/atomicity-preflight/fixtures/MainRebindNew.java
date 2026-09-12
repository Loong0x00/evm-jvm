public final class MainRebindNew {
  static Object saved; static int marker;
  public static void main(String[] args) {
    saved = args;
    args = new String[1];
    marker = saved == null ? -1 : (args == saved ? -2 : args.length);
    if (marker != 1 || !(saved instanceof String[]) || ((String[]) saved).length != 0)
      throw new RuntimeException();
  }
}
