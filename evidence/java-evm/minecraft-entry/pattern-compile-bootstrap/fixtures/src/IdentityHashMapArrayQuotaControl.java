import java.util.IdentityHashMap;

public final class IdentityHashMapArrayQuotaControl {
    public static void main(String[] args) {
        try {
            new IdentityHashMap(21846);
            throw new AssertionError("table beyond VM array bound unexpectedly allocated");
        } catch (OutOfMemoryError expected) { }
    }
}
