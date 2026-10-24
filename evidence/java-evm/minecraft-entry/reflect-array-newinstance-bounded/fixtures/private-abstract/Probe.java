import java.lang.reflect.Array;
public final class Probe {
 private static abstract class Hidden { }
 public static void main(String[] args) { Hidden[] a=(Hidden[])Array.newInstance(Hidden.class,2); Object[] alias=a; alias[0]=null; }
}
