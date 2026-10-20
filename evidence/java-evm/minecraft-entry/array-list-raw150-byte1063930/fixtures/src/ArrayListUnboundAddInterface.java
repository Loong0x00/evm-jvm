import java.util.ArrayList;
import java.util.List;
public final class ArrayListUnboundAddInterface {
    public static void main(String[] args) {
        List list = new ArrayList(1);
        if (!list.add(new Object())) throw new AssertionError("interface add result");
    }
}
