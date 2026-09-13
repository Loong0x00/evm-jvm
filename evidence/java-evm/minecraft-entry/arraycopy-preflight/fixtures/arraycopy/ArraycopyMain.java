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

    // The EVM native has separate primitive leaves; copies retain cells exactly.
    boolean[] zs = new boolean[] { true, false }; boolean[] zd = new boolean[2];
    byte[] bs = new byte[] { -7, 9 }; byte[] bd = new byte[2];
    char[] cs = new char[] { 1, 0xfffe }; char[] cd = new char[2];
    short[] ss = new short[] { -9, 300 }; short[] sd = new short[2];
    int[] is = new int[] { -11, 12 }; int[] id = new int[2];
    long[] ls = new long[] { -13L, 0x1122334455667788L }; long[] ld = new long[2];
    float[] fs = new float[] { Float.intBitsToFloat(0x7fc00001), -0.0f }; float[] fd = new float[2];
    double[] ds = new double[] { Double.longBitsToDouble(0x7ff8000000000001L), -0.0d }; double[] dd = new double[2];
    System.arraycopy(zs,0,zd,0,2); System.arraycopy(bs,0,bd,0,2);
    System.arraycopy(cs,0,cd,0,2); System.arraycopy(ss,0,sd,0,2);
    System.arraycopy(is,0,id,0,2); System.arraycopy(ls,0,ld,0,2);
    System.arraycopy(fs,0,fd,0,2); System.arraycopy(ds,0,dd,0,2);
    require(zd[0] && !zd[1] && bd[0] == -7 && bd[1] == 9 && cd[1] == 0xfffe);
    require(sd[0] == -9 && id[1] == 12 && ld[1] == 0x1122334455667788L);
    require(Float.floatToRawIntBits(fd[0]) == 0x7fc00001 && Float.floatToRawIntBits(fd[1]) == 0x80000000);
    require(Double.doubleToRawLongBits(dd[0]) == 0x7ff8000000000001L && Double.doubleToRawLongBits(dd[1]) == 0x8000000000000000L);

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
