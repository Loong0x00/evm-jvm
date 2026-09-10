public final class SC0Flow {
  static int effects;
  static String saved;

  static boolean yes() { return true; }

  static final class CharsHolder {
    static String value = new String(new char[]{'o', 'k'});
  }

  static final class BrokenHolder {
    static String value = new String((char[])null);
  }

  static final class StringThrowable extends RuntimeException {
    String value;
    StringThrowable(String value) { super(); this.value = value; }
  }

  static char[] failArgument() {
    effects++;
    int[] missing = null;
    int ignored = missing.length;
    return new char[]{(char)ignored};
  }

  public static int nullChars() {
    try { new String((char[])null); return 0; }
    catch (NullPointerException expected) { return expected != null ? 1 : 0; }
  }

  public static int nullCopy() {
    try { new String((String)null); return 0; }
    catch (NullPointerException expected) { return expected != null ? 1 : 0; }
  }

  public static int failThenValid() {
    int caught = 0;
    try { new String((char[])null); }
    catch (NullPointerException expected) { caught = 10; }
    return caught + new String(new char[]{'o', 'k'}).length();
  }

  public static int charsInClinit() {
    return CharsHolder.value.length() == 2 && CharsHolder.value.charAt(1) == 'k' ? 1 : 0;
  }

  public static int initFailureThenNCDFE() {
    int score = 0;
    try { String ignored = BrokenHolder.value; score += ignored.length(); }
    catch (ExceptionInInitializerError first) {
      if (first != null) score += 1;
    }
    try { String ignored = BrokenHolder.value; score += ignored.length(); }
    catch (NoClassDefFoundError second) { score += 2; }
    return score;
  }

  public static int loop64() {
    int n = 64;
    char[] source = new char[n];
    for (int i = 0; i < n; i++) source[i] = (char)(65 + (i % 26));
    String value = new String(source);
    source[n - 1] = 0;
    return value.length() * 1000 + value.charAt(n - 1);
  }

  public static int argumentFailure() {
    effects = 0;
    try { new String(failArgument()); return 0; }
    catch (NullPointerException expected) { return effects == 1 ? 1 : 0; }
  }

  public static int throwableIntegration() {
    String made = new String(new char[]{'c', 'a', 'u', 's', 'e'});
    saved = made;
    try { throw new StringThrowable(made); }
    catch (StringThrowable caught) {
      return caught.value == saved && caught.value == made && caught.value.equals("cause") ? 1 : 0;
    }
  }
}
