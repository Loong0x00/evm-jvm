public final class SparseOneFloatMain {
  private SparseOneFloatMain() {}

  public static void main(String[] args) {
    if (args == null || SparseFloatMain.oneDistantNonzero() != 1) {
      throw new RuntimeException();
    }
  }
}
