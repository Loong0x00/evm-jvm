import java.util.ArrayList;
public final class ArrayListMissingDefaultConstructor {
    public static void main(String[] args) {
        ArrayList list = new ArrayList();
        if (!list.isEmpty()) throw new AssertionError("default constructor");
    }
}
