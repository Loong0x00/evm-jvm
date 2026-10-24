import java.util.EnumSet;
public final class Probe {
 enum Choice { A, B }
 public static void main(String[] args) {
  Choice first=Choice.A;
  EnumSet<Choice> values=EnumSet.allOf(Choice.class);
  if (first==null || values.size()!=2) throw new RuntimeException();
 }
}
