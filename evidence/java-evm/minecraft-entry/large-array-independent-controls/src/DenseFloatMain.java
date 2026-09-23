public final class DenseFloatMain {
  private DenseFloatMain() {}

  private static void require(boolean ok) {
    if (!ok) throw new RuntimeException();
  }

  /** Full-size zero baseline, dense write, and full-size readback control. */
  public static int verify() {
    float[] values = new float[65536];
    for (int i = 0; i < values.length; ++i) {
      if (values[i] != 0.0f) throw new RuntimeException();
    }
    for (int i = 0; i < values.length; ++i) values[i] = 1.0f;
    int checked = 0;
    for (int i = 0; i < values.length; ++i) {
      if (values[i] != 1.0f) throw new RuntimeException();
      ++checked;
    }
    return checked;
  }

  public static void main(String[] args) {
    require(args != null);
    require(verify() == 65536);
  }
}
