package probe;
import java.util.ArrayList;
public final class ArrayListRefusalCloneProbe {
 static final class CloneList extends ArrayList { Object copy() throws CloneNotSupportedException { return clone(); } }
 public static void main(String[] args) throws Exception { ArrayList list = new ArrayList(); new CloneList().copy(); }
}
