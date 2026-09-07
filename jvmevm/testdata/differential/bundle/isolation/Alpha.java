package bundle.isolation;

public class Alpha {
    private static int shared(int value) {
        return value * 3 + 11;
    }

    public static int apply(int value) {
        return shared(value) + 1000;
    }

    public static int pair(int first, int second) {
        return shared(first) - shared(second);
    }
}
