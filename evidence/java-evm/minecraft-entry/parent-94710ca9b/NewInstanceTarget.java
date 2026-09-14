public final class NewInstanceTarget {
  static int initialized;
  static int constructed;
  int value;
  static { initialized++; }
  public NewInstanceTarget() { value = 41; constructed++; }
}
