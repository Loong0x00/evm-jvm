public final class SparseFloatMain {
  private SparseFloatMain() {}

  private static void require(boolean ok) {
    if (!ok) throw new RuntimeException();
  }

  /** One nonzero at the far end of an initially-zero, 65536-element array. */
  public static int oneDistantNonzero() {
    float[] values = new float[65536];
    for (int i = 0; i < values.length; ++i) {
      if (values[i] != 0.0f) throw new RuntimeException();
    }
    values[65535] = 3.5f;
    require(values[65535] == 3.5f);
    require(values[0] == 0.0f);
    return 1;
  }

  /** Three distant nonzeros; every element is first read and checked as zero. */
  public static int severalDistantNonzeros() {
    float[] values = new float[65536];
    for (int i = 0; i < values.length; ++i) {
      if (values[i] != 0.0f) throw new RuntimeException();
    }
    values[0] = 1.25f;
    values[32768] = -2.5f;
    values[65535] = 17.0f;
    require(values[0] == 1.25f);
    require(values[32768] == -2.5f);
    require(values[65535] == 17.0f);
    require(values[1] == 0.0f);
    require(values[32767] == 0.0f);
    require(values[65534] == 0.0f);
    return 7;
  }

  public static void main(String[] args) {
    require(args != null);
    // Keep exactly one 65536-element guest array live in this invocation.
    require(severalDistantNonzeros() == 7);
  }
}
