public final class LC0AliasString {
  static LC0AliasBox saved;
  static String text = "same";
  public static int run() {
    LC0AliasBox box = new LC0AliasBox(3);
    saved = box;
    Object[] aliases = new Object[] { box, text, box, "same" };
    for (int i = 0; i < 3; i++) box.value++;
    return box.value + saved.value + ((LC0AliasBox) aliases[0]).value
        + (text == aliases[1] ? 10 : 0) + (text == aliases[3] ? 4 : 0) + text.length();
  }
}
