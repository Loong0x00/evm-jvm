import java.util.ArrayList;
import java.util.Iterator;
public final class ArrayListUnboundIteratorConcrete {
    public static void main(String[] args) {
        Iterator iterator = new ArrayList(0).iterator();
        if (iterator.hasNext()) throw new AssertionError("iterator state");
    }
}
