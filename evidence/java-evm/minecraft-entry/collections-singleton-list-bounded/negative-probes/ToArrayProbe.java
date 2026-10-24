import java.util.Collection;
import java.util.Collections;
public final class ToArrayProbe {
  public static void main(String[] args) {
    Collection<Object> value = Collections.singletonList(new Object());
    value.toArray(new Object[0]);
  }
}
