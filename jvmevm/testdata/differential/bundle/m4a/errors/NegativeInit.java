package bundle.m4a.errors;

public class NegativeInit {
    static int[] VALUES = create();

    public static int entry(int ignored) {
        return VALUES.length;
    }

    private static int[] create() {
        return new int[-1];
    }
}
