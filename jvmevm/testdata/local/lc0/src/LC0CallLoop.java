public final class LC0CallLoop {
  static int add(int a, int b) { return a + b; }
  public static int run(int n) {
    int sum = 0;
    for (int i = 1; i <= n; i++) sum = add(sum, i);
    return sum;
  }
}
