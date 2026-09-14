public final class ClassAsSubclassProbe {
  static int result;
  static void fail(int n) { result = n; }
  public static void main(String[] ignored) {
    Class<RawReusableMessageFactory> raw = RawReusableMessageFactory.class;
    Class<? extends RawMessageFactory> asInterface = raw.asSubclass(RawMessageFactory.class);
    if (asInterface != raw || asInterface.getClassLoader() != raw.getClassLoader()) { fail(1); return; }
    Class<? extends RawMessageFactory> self = RawMessageFactory.class.asSubclass(RawMessageFactory.class);
    if (self != RawMessageFactory.class) { fail(2); return; }
    Class<? extends Object> object = Boolean.class.asSubclass(Object.class);
    if (object != Boolean.class || object.getClassLoader() != null) { fail(3); return; }
    try { RawMessageFactory.class.asSubclass(Boolean.class); fail(4); return; }
    catch (ClassCastException ok) {} catch (RuntimeException wrong) { fail(5); return; }
    try { Boolean.class.asSubclass(RawMessageFactory.class); fail(6); return; }
    catch (ClassCastException ok) {}
    try { raw.asSubclass(null); fail(7); return; }
    catch (NullPointerException ok) {}
    if (raw.asSubclass(RawMessageFactory.class) != raw) fail(8);
  }
}
