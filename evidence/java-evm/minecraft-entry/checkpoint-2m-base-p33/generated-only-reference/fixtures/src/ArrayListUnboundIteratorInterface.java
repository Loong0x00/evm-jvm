import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
public final class ArrayListUnboundIteratorInterface {
    public static void main(String[] args) {
        List list = new ArrayList(0);
        Iterator iterator = list.iterator();
        if (iterator.hasNext()) throw new AssertionError("interface iterator state");
    }
}
