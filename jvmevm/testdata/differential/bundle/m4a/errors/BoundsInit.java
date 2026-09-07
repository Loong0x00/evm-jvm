package bundle.m4a.errors;

public class BoundsInit {
    static int[] VALUES = create();
    static int FIRST = VALUES[VALUES.length];

    public static int entry(int ignored) {
        return FIRST;
    }

    private static int[] create() {
        return new int[1];
    }
}
