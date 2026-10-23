package probe;
import java.util.ArrayList;
public final class ArrayListNegativeProbe {
    public static void main(String[] args) {
        try { new ArrayList(-1); }
        catch (IllegalArgumentException expected) { return; }
        throw new IllegalStateException();
    }
}
