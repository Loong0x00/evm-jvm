public final class Checkpoint2MArrayBoundary {
  public static Object[] first;
  public static Object[] second;
  public static Object[] third;
  public static Object[] fourth;

  public static void main(String[] args) {
    first = new Object[65536];
    second = new Object[65536];
    third = new Object[65536];
    fourth = new Object[65536];
  }
}
