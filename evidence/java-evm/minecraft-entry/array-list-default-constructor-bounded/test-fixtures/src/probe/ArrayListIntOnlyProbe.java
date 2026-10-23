package probe;
import java.util.ArrayList;
public final class ArrayListIntOnlyProbe {
    public static void main(String[] args) {
        ArrayList zero = new ArrayList(0);
        ArrayList positive = new ArrayList(3);
        if (zero.size() != 0 || positive.size() != 0 || !zero.isEmpty() || !positive.isEmpty()) throw new IllegalStateException();
    }
}
