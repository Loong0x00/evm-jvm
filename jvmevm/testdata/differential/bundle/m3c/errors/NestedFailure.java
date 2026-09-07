package bundle.m3c.errors;

public class NestedFailure {
    public static int value = initialize();

    private static int initialize() {
        return 99 % zero();
    }

    private static int zero() {
        return 0;
    }
}
