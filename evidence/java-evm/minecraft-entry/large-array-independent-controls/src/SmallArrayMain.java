public final class SmallArrayMain {
  private SmallArrayMain() {}

  private static void require(boolean ok) {
    if (!ok) throw new RuntimeException();
  }

  public static int verify() {
    int[] ints = new int[8];
    float[] floats = new float[16];
    for (int i = 0; i < ints.length; ++i) require(ints[i] == 0);
    for (int i = 0; i < floats.length; ++i) require(floats[i] == 0.0f);
    ints[0] = 11;
    ints[7] = -13;
    floats[1] = 2.0f;
    floats[15] = -4.0f;
    require(ints[0] == 11 && ints[7] == -13);
    require(floats[1] == 2.0f && floats[15] == -4.0f);
    require(ints[3] == 0 && floats[8] == 0.0f);
    return 31;
  }

  public static void main(String[] args) {
    require(args != null);
    require(verify() == 31);
  }
}
