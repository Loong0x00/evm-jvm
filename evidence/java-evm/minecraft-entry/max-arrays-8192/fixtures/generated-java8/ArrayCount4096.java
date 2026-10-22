package generated; public final class ArrayCount4096 {
 public static void main(String[] args) {
  Object[] refs = new Object[4094];
  for (int i=0;i<4094;i++) refs[i]=new int[0];
  for (int i=0;i<4094;i++) if (refs[i]==null) throw new AssertionError();
 }
}
