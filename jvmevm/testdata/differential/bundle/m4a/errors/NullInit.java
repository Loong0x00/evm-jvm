package bundle.m4a.errors;

public class NullInit {
    static int[] VALUES;
    static int LENGTH = VALUES.length;

    public static int entry(int ignored) {
        return LENGTH;
    }
}
