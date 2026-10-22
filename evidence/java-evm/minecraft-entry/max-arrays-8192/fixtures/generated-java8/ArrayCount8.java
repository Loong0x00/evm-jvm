package generated; public final class ArrayCount8 {
 public static void main(String[] args) {
  Object[] refs = new Object[6];
  for (int i=0;i<6;i++) refs[i]=new int[0];
  for (int i=0;i<6;i++) if (refs[i]==null) throw new AssertionError();
 }
}
