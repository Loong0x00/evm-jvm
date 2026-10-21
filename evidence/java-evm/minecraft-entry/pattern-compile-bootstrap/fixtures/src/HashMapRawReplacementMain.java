import java.util.HashMap;

public final class HashMapRawReplacementMain {
    public static void main(String[] args) {
        HashMap<Object, Object> map = new HashMap<>();
        if (!map.isEmpty()) throw new AssertionError("raw HashMap replacement was accepted");
    }
}
