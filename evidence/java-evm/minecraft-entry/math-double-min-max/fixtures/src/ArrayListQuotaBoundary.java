import java.util.ArrayList;

public final class ArrayListQuotaBoundary {
    public static void main(String[] args) {
        ArrayList list = new ArrayList(65536);
        if (list.size() != 0 || !list.isEmpty()) {
            throw new AssertionError("maximum legal backing array capacity");
        }
    }
}
