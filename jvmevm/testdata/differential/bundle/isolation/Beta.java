package bundle.isolation;

public class Beta {
    private static int shared(int value) {
        return value * 7 - 13;
    }

    public static int apply(int value) {
        return shared(value) - 2000;
    }

    public static int pair(int first, int second) {
        return shared(first) - shared(second);
    }
}
