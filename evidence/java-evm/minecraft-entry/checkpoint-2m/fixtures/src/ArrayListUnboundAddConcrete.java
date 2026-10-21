import java.util.ArrayList;
public final class ArrayListUnboundAddConcrete {
    public static void main(String[] args) {
        if (!new ArrayList(1).add(new Object())) throw new AssertionError("add result");
    }
}
