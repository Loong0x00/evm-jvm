public final class NewInstanceMain {
  static int result;
  public static void main(String[] ignored) throws Exception {
    NewInstanceTarget first = NewInstanceTarget.class.newInstance();
    NewInstanceTarget second = NewInstanceTarget.class.newInstance();
    if (NewInstanceTarget.initialized != 1 || NewInstanceTarget.constructed != 2
        || first.value != 41 || second.value != 41 || first == second) throw new Error();
    result = first.value + second.value + NewInstanceTarget.initialized + NewInstanceTarget.constructed;
  }
}
