import java.util.EnumSet;
public final class Probe {
 enum Choice { A, B }
 public static void main(String[] args) {
  if (!Object.class.getName().equals("java.lang.Object")) throw new RuntimeException();
  Object[] source = new Object[2]; Object[] dest = new Object[2];
  source[0] = "ok"; System.arraycopy(source, 0, dest, 0, 1);
  if (dest[0] != source[0]) throw new RuntimeException();
  EnumSet<Choice> values = EnumSet.allOf(Choice.class);
  if (values.size() != 2) throw new RuntimeException();
 }
}
