import java.util.IdentityHashMap;

public final class IdentityHashMapMaximumControl {
    public static void main(String[] args) {
        try {
            new IdentityHashMap(Integer.MAX_VALUE);
            throw new AssertionError("maximum capacity unexpectedly allocated");
        } catch (OutOfMemoryError expected) { }
    }
}
