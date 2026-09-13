/** Parent-generated TEST oracle: real interface arrays and boundary precedence. */
public final class EdgeMain {
  interface Marker {}
  static final class A implements Marker {}
  static final class B implements Marker {}
  static int state;
  static void require(boolean b) { if (!b) throw new RuntimeException(); }
  public static void main(String[] args) {
    A a = new A(); B b = new B();
    Marker[] from = new Marker[] {a, b, null, a};
    Marker[] to = new Marker[4];
    System.arraycopy(from, 0, to, 0, 4);
    require(to[0] == a && to[1] == b && to[2] == null && to[3] == a);
    Marker[] alias = to;
    System.arraycopy(to, 0, alias, 1, 3);
    require(alias[0] == a && alias[1] == a && alias[2] == b && alias[3] == null);
    System.arraycopy(alias, 1, to, 0, 3);
    require(to[0] == a && to[1] == b && to[2] == null && to[3] == null);
    System.arraycopy(from, 4, to, 4, 0); // actual exact ends
    System.arraycopy(new B[0], 0, new A[0], 0, 0); // no reference elements to reject
    try { System.arraycopy(new Object(), 0, null, 0, 0); throw new RuntimeException(); }
    catch (NullPointerException expected) {}
    try { System.arraycopy(null, 0, new Object(), 0, 0); throw new RuntimeException(); }
    catch (NullPointerException expected) {}
    try { System.arraycopy(to, -1, new Object(), -1, -1); throw new RuntimeException(); }
    catch (ArrayStoreException expected) {}
    try { System.arraycopy(new int[0], -1, new float[0], -1, 0); throw new RuntimeException(); }
    catch (ArrayStoreException expected) {}
    try { System.arraycopy(new byte[0], 0, new boolean[0], 0, 0); throw new RuntimeException(); }
    catch (ArrayStoreException expected) {}
    try { System.arraycopy(to, 4, to, 4, 1); throw new RuntimeException(); }
    catch (ArrayIndexOutOfBoundsException expected) {}
    try { System.arraycopy(to, 2147483647, to, 0, 1); throw new RuntimeException(); }
    catch (ArrayIndexOutOfBoundsException expected) {}
    try { System.arraycopy(to, 0, to, 2147483647, 1); throw new RuntimeException(); }
    catch (ArrayIndexOutOfBoundsException expected) {}
    try { System.arraycopy(to, 0, to, 0, 2147483647); throw new RuntimeException(); }
    catch (ArrayIndexOutOfBoundsException expected) {}
    try { System.arraycopy(to, 0, to, 0, -1); throw new RuntimeException(); }
    catch (ArrayIndexOutOfBoundsException expected) {}
    try { System.arraycopy(new B[1], -1, new A[1], 0, 1); throw new RuntimeException(); }
    catch (ArrayIndexOutOfBoundsException expected) {}
    A[] typed = new A[3];
    try { System.arraycopy(from, 0, typed, 0, 3); throw new RuntimeException(); }
    catch (ArrayStoreException expected) {}
    require(typed[0] == a && typed[1] == null && typed[2] == null);
    Object[] nested = new Object[] {new A[0], new int[0]};
    Object[][] nestedTo = new Object[2][];
    try { System.arraycopy(nested, 0, nestedTo, 0, 2); throw new RuntimeException(); }
    catch (ArrayStoreException expected) {}
    require(nestedTo[0] == nested[0] && nestedTo[1] == null);
    state = 0x1234;
  }
}
