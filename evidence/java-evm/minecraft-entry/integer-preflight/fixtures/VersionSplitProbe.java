public final class VersionSplitProbe {
  private static final String R = "-|\\.";
  private static int same(String[] a, String... b) {
    if (a.length != b.length) return 0;
    for (int i = 0; i < b.length; i++) if (!a[i].equals(b[i])) return 0;
    return 1;
  }
  public static int run() {
    if (!"1.8".equals(System.getProperty("java.version"))) return 1;
    if (same("1.8".split(R), "1", "8") == 0) return 2;
    if (same("a..b-".split(R), "a", "", "b") == 0) return 3;
    if (same("a--".split(R), "a") == 0) return 4;
    String noMatch = "abc", empty = "";
    if (noMatch.split(R).length != 1 || noMatch.split(R)[0] != noMatch) return 5;
    if (empty.split(R).length != 1 || empty.split(R)[0] != empty) return 6;
    String[] derived = "a.b".split(R);
    if (derived[0] == "a" || derived[1] == "b") return 7;
    try { ((String)null).split(R); return 8; } catch (NullPointerException expected) {}
    try { "a".split(null); return 9; } catch (NullPointerException expected) {}
    return 0;
  }
}
