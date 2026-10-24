package probe;
import java.util.ArrayList;
public final class ArrayListRefusalEqualsProbe {
  public static void main(String[] args) throws Exception { ArrayList list = new ArrayList(); list.equals(new Object()); }
}
