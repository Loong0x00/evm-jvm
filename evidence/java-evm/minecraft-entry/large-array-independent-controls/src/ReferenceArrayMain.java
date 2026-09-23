public final class ReferenceArrayMain {
  private ReferenceArrayMain() {}

  private static void require(boolean ok) {
    if (!ok) throw new RuntimeException();
  }

  public static int verify() {
    Object[] values = new Object[8];
    for (int i = 0; i < values.length; ++i) require(values[i] == null);
    Object first = new Object();
    Object last = new Object();
    values[0] = first;
    values[7] = last;
    require(values[0] == first);
    require(values[7] == last);
    require(values[3] == null);
    return 5;
  }

  public static void main(String[] args) {
    require(args != null);
    require(verify() == 5);
  }
}
