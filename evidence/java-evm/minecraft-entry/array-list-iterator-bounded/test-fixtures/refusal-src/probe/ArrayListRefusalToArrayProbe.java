package probe;
import java.util.ArrayList;
public final class ArrayListRefusalToArrayProbe {
  public static void main(String[] args) throws Exception { ArrayList list = new ArrayList(); list.toArray(new Object[0]); }
}
