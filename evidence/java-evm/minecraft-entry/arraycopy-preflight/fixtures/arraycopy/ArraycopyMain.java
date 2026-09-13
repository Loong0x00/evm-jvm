import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/** Generated Java-8 TEST fixture for the sole owned System.arraycopy surface. */
public final class ArraycopyMain {
  static int state;
  static final class A {}
  static final class B {}
  private static void require(boolean b) { if (!b) throw new RuntimeException(); }

  public static void main(String[] args) {
    // Retain small map and class-literal controls from the parent COPY profile.
    Map<Object,Object> map = new ConcurrentHashMap<Object,Object>();
    Object marker = ArraycopyMain.class;
    map.put(marker, marker);
    require(map.get(marker) == marker);

    A a0 = new A(), a1 = new A(), a2 = new A(), a3 = new A();
    Object[] same = new Object[] { a0, a1, a2, a3 };
    System.arraycopy(same, 0, same, 1, 3); // backwards memmove
    require(same[0] == a0 && same[1] == a0 && same[2] == a1 && same[3] == a2);
    System.arraycopy(same, 1, same, 0, 3); // forwards memmove
    require(same[0] == a0 && same[1] == a1 && same[2] == a2 && same[3] == a2);

    Object[] distinct = new Object[] { null, null, null, null };
    System.arraycopy(same, 1, distinct, 0, 3);
    System.arraycopy(distinct, 3, distinct, 3, 0); // exact end, zero length
    require(distinct[0] == a1 && distinct[1] == a2 && distinct[2] == a2 && distinct[3] == null);

    try { System.arraycopy(null, -1, distinct, -1, -1); throw new RuntimeException(); }
    catch (NullPointerException expected) {}
    try { System.arraycopy(distinct, -1, null, -1, -1); throw new RuntimeException(); }
    catch (NullPointerException expected) {}
    try { System.arraycopy(new Object(), -1, distinct, -1, -1); throw new RuntimeException(); }
    catch (ArrayStoreException expected) {}
    try { System.arraycopy(new int[] { 1 }, -1, distinct, -1, -1); throw new RuntimeException(); }
    catch (ArrayStoreException expected) {}
    try { System.arraycopy(distinct, -1, distinct, 0, 1); throw new RuntimeException(); }
    catch (ArrayIndexOutOfBoundsException expected) {}

    Object[] mixed = new Object[] { a0, new B(), a2 };
    A[] typed = new A[] { null, null, null };
    try { System.arraycopy(mixed, 0, typed, 0, 3); throw new RuntimeException(); }
    catch (ArrayStoreException expected) {}
    require(typed[0] == a0 && typed[1] == null && typed[2] == null);
    state = 4107;
  }
}
