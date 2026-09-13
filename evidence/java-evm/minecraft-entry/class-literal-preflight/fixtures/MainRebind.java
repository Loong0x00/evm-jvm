public final class MainRebind {
  public static void main(String[] args) {
    Object saved = args;
    args = null;
    if (saved == null) throw new RuntimeException();
  }
}
