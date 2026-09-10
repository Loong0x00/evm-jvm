public final class SC0CopyIntern {
  public static int copyDistinct() {
    String source = new String(new char[]{'c', 'o', 'p', 'y'});
    String copy = new String(source);
    return copy != source && copy.equals(source) ? 1 : 0;
  }

  public static int copyHash() {
    String source = new String(new char[]{'B', 'B'});
    int hash = source.hashCode();
    String copy = new String(source);
    return copy.hashCode() == hash ? hash : 0;
  }

  public static int category2Caller() {
    long before = 0x1122334455667788L;
    double around = 1.5d;
    String source = new String(new char[]{'w', 'i', 'd', 'e'});
    String copy = new String(source);
    long after = before + (long)around;
    return before == 0x1122334455667788L && after == 0x1122334455667789L && copy != source && copy.equals(source) ? 1 : 0;
  }

  public static int literalCopyIntern() {
    String literal = "same";
    String copy = new String(literal);
    return (copy != literal ? 100 : 0) + (copy.equals(literal) ? 10 : 0)
        + (copy.intern() == literal ? 1 : 0);
  }

  public static int constructedFirst() {
    String first = new String(new char[]{'u', 'n', 'i', 'q'});
    String second = new String(new char[]{'u', 'n', 'i', 'q'});
    String canonical = first.intern();
    return (canonical == first ? 100 : 0) + (second.intern() == first ? 10 : 0)
        + (first != second ? 1 : 0);
  }

  public static int earlierHandleInsert() {
    String early = new String(new char[]{'e', 'a', 'r', 'l', 'y'});
    String later = "later-literal";
    String canonical = early.intern();
    return canonical == early && later.intern() == later ? 1 : 0;
  }

  public static int hashCollision() {
    String first = new String(new char[]{'A', 'a'});
    String second = new String(new char[]{'B', 'B'});
    if (first.hashCode() != second.hashCode()) return 0;
    return first.intern() == first && second.intern() == second && first.intern() != second.intern() ? 1 : 0;
  }

  public static int interfaceDispatch() {
    CharSequence sequence = new String(new char[]{'a', 'b', 'c'});
    Comparable<String> comparable = (String)sequence;
    return sequence.length() == 3 && sequence.charAt(1) == 'b'
        && comparable.compareTo("abc") == 0 ? 1 : 0;
  }
}
