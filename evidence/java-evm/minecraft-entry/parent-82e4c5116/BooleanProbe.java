public final class BooleanProbe {
  static int result;
  public static void main(String[] args) {
    Boolean t = Boolean.valueOf(true), f = Boolean.valueOf(false);
    Boolean nt = new Boolean(true), nf = new Boolean(false);
    int r = 0;
    if (t == Boolean.TRUE && f == Boolean.FALSE && t == Boolean.valueOf(true) && f == Boolean.valueOf(false)) r += 1;
    if (nt != t && nf != f && nt.equals(t) && nf.equals(f) && !nt.equals(nf)) r += 2;
    if (t.booleanValue() && !f.booleanValue()) r += 4;
    if (t.hashCode() == 1231 && f.hashCode() == 1237) r += 8;
    if ("true".equals(t.toString()) && "false".equals(Boolean.toString(false))) r += 16;
    if (Boolean.compare(false, true) < 0 && Boolean.compare(true, false) > 0 && Boolean.compare(true, true) == 0) r += 32;
    Comparable c = t;
    if (c.compareTo(f) > 0 && t.compareTo(nt) == 0) r += 64;
    result = r;
  }
}
